#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy-aca.sh  —  Deploy PCOP to Azure Container Apps
#
# Creates managed PostgreSQL + Redis, builds images via ACR, and deploys
# bank / server / client / scoring as container apps.
#
# Usage:  ./deploy-aca.sh [location]   (default: westus)
#         ./deploy-aca.sh --force      rebuild all images even if cached in ACR
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
RG="pcop-rg"
FORCE_REBUILD=false
[ "${1:-}" = "--force" ] && { FORCE_REBUILD=true; set -- "${2:-}"; }
LOCATION="${1:-westus}"
ACR_NAME=""  # resolved below from existing RG or generated
ACA_ENV="pcop-env"
PG_SERVER="pcop-pg"
PG_USER="pcop"
PG_PASS="PcopDev2024!"
PG_DB="pcop"
REDIS_NAME="pcop-cache"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ═══════════════════════════════════════════════════════════════════════════════
#  Prerequisites & Provider Registration
# ═══════════════════════════════════════════════════════════════════════════════
command -v az >/dev/null 2>&1 || { echo "❌ Install Azure CLI: brew install azure-cli"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Install Python 3"; exit 1; }
az account show --query name -o tsv 2>/dev/null >/dev/null || { echo "❌ Run: az login"; exit 1; }

RP_LIST="Microsoft.ContainerRegistry Microsoft.App Microsoft.DBforPostgreSQL Microsoft.Cache Microsoft.OperationalInsights"
for ns in $RP_LIST; do
  state=$(az provider show --namespace "$ns" --query registrationState -o tsv 2>/dev/null || echo "NotRegistered")
  if [ "$state" != "Registered" ]; then
    echo "  Registering $ns..."
    az provider register --namespace "$ns" --output none
  fi
done
all_done() {
  for ns in $RP_LIST; do
    state=$(az provider show --namespace "$ns" --query registrationState -o tsv 2>/dev/null || echo "NotRegistered")
    [ "$state" != "Registered" ] && return 1
  done
  return 0
}
all_done && echo "  All providers already registered" || {
  for ns in $RP_LIST; do
    for i in $(seq 1 30); do
      state=$(az provider show --namespace "$ns" --query registrationState -o tsv 2>/dev/null || echo "NotRegistered")
      [ "$state" = "Registered" ] && break
      echo "  Waiting for $ns... ($i/30)"
      sleep 10
    done
  done
}

# ═══════════════════════════════════════════════════════════════════════════════
#  Resource Group
# ═══════════════════════════════════════════════════════════════════════════════
echo ">>> Resource group"
EXISTING_LOC=$(az group show --name "$RG" --query location -o tsv 2>/dev/null || true)
if [ -n "$EXISTING_LOC" ] && [ "$EXISTING_LOC" != "$LOCATION" ]; then
  echo "  RG exists in '$EXISTING_LOC' — deleting for '$LOCATION'..."
  az group delete --name "$RG" --yes --no-wait
  az group wait --name "$RG" --deleted --timeout 300
  az group create --name "$RG" --location "$LOCATION" --output none
elif [ -z "$EXISTING_LOC" ]; then
  az group create --name "$RG" --location "$LOCATION" --output none
fi

# Resolve ACR name — reuse existing one in RG if present
if [ -z "$ACR_NAME" ]; then
  EXISTING_ACR=$(az acr list --resource-group "$RG" --query "[0].name" -o tsv 2>/dev/null || true)
  if [ -n "$EXISTING_ACR" ]; then
    ACR_NAME="$EXISTING_ACR"
    echo "  Reusing existing ACR: $ACR_NAME"
  else
    ACR_NAME="pcopacr$(openssl rand -hex 4 | tr '[:upper:]' '[:lower:]')"
  fi
fi

# ── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      Deploying PCOP to Azure Container Apps                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  Location:       $LOCATION"
echo "  Resource Group: $RG"
echo "  ACR:            $ACR_NAME"
echo "  ACA Env:        $ACA_ENV"
echo "  PostgreSQL:     $PG_SERVER"
echo "  Redis:          $REDIS_NAME"
echo ""

# ── Helpers ──────────────────────────────────────────────────────────────────
env_pairs() {
  # Convert key value pairs to --env-vars arguments
  local pairs=()
  while [ $# -gt 0 ]; do
    pairs+=("$1=$2")
    shift 2
  done
  echo "${pairs[@]}"
}

create_app() {
  local name="$1" image="$2" port="$3" ingress="$4" tag="$5"
  shift 5
  local deploy_ref="${REGISTRY}/${image}:${tag:-latest}"
  if az containerapp show --resource-group "$RG" --name "$name" &>/dev/null; then
    echo "  Updating $name → $deploy_ref..."
    az containerapp update \
      --resource-group "$RG" --name "$name" \
      --image "$deploy_ref" --output none
    return 0
  fi
  echo "  Creating $name..."
  # shellcheck disable=SC2086
  az containerapp create \
    --resource-group "$RG" --name "$name" --environment "$ACA_ENV" \
    --image "$deploy_ref" \
    --target-port "$port" --ingress "$ingress" \
    --registry-server "$REGISTRY" \
    --min-replicas 1 --max-replicas 1 \
    --env-vars $(env_pairs "$@") --output none
}

# ═══════════════════════════════════════════════════════════════════════════════
#  1. ACR — build & push images
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo ">>> Container Registry"
if ! az acr show --name "$ACR_NAME" --resource-group "$RG" &>/dev/null; then
  az acr create --resource-group "$RG" --name "$ACR_NAME" --sku Basic \
    --admin-enabled true --output none
fi

REGISTRY=$(az acr show --name "$ACR_NAME" --resource-group "$RG" --query loginServer -o tsv)

# Build locally & push to ACR (ACR Tasks may be disabled on this subscription)
docker_login() { az acr login --name "$ACR_NAME" --output none; }
build_and_push() {
  local base="$1" path="$2" dockerfile="$3"
  local tag="${base}:latest" extra=""
  # Pass server URL as build arg for client (bakes NEXT_PUBLIC_API_URL into JS)
  if [ "$base" = "pcop/client" ] && [ -n "${SERVER_URL:-}" ]; then
    extra="--build-arg NEXT_PUBLIC_API_URL=$SERVER_URL"
  fi
  # Rebuild client when SERVER_URL changes (always), or when --force
  if [ "$base" = "pcop/client" ] && [ -n "${SERVER_URL:-}" ]; then
    :  # always rebuild (don't check ACR cache)
  elif [ "$FORCE_REBUILD" = "false" ]; then
    if az acr repository show-tags --registry "$ACR_NAME" --repository "$base" \
         --query "contains(@, 'latest')" -o tsv 2>/dev/null | grep -q true; then
      echo "  Skipping $tag — already in ACR (use --force to rebuild)" >&2
      return 0
    fi
  fi
  local ts=$(date +%s)
  local utag="build-${ts}"
  echo "  Building ${base}:${utag} (linux/amd64)..." >&2
  DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build $extra \
    -t "${REGISTRY}/${tag}" -t "${REGISTRY}/${base}:${utag}" -f "$dockerfile" "$path" --quiet >&2
  echo "  Pushing images..." >&2
  docker push "${REGISTRY}/${tag}" >&2
  docker push "${REGISTRY}/${base}:${utag}" >&2
  echo "$utag"
}

docker_login
if [ "$FORCE_REBUILD" = "true" ]; then
  echo "  Removing stale ARM images..."
  IMGS=$(docker images -q)
  [ -n "$IMGS" ] && docker rmi -f $IMGS 2>/dev/null || true
fi
echo ""
echo "  Building & pushing initial images..."
BANK_TAG=$(build_and_push "pcop/bank"    "${PROJECT_DIR}/bank"       "${PROJECT_DIR}/bank/Dockerfile")
SERVER_TAG=$(build_and_push "pcop/server"  "${PROJECT_DIR}/server"     "${PROJECT_DIR}/server/Dockerfile")
echo "  Skipping pcop/scoring — can be built manually later"
echo "  (client will be built after server is deployed so API URL is known)"
SCORING_SKIPPED=true

# ═══════════════════════════════════════════════════════════════════════════════
#  2. Managed PostgreSQL
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo ">>> PostgreSQL Flexible Server"
# Discover existing PG server in RG, or create a new one
EXISTING_PG=$(az postgres flexible-server list --resource-group "$RG" --query "[0].name" -o tsv 2>/dev/null || true)
if [ -n "$EXISTING_PG" ]; then
  PG_SERVER="$EXISTING_PG"
  echo "  Reusing existing PostgreSQL: $PG_SERVER"
else
  # Append random suffix for global uniqueness
  PG_SERVER="pcop-pg-$(openssl rand -hex 2 | tr '[:upper:]' '[:lower:]')"
  echo "  Creating PostgreSQL: $PG_SERVER"
  az postgres flexible-server create \
    --resource-group "$RG" --name "$PG_SERVER" \
    --admin-user "$PG_USER" --admin-password "$PG_PASS" \
    --sku-name Standard_B1ms --tier Burstable \
    --public-access 0.0.0.0 --output none
fi
PG_HOST="${PG_SERVER}.postgres.database.azure.com"
az postgres flexible-server db create \
  --resource-group "$RG" --server-name "$PG_SERVER" \
  --database-name "$PG_DB" --output none 2>/dev/null || true
echo "  Connection: $PG_HOST"
DATABASE_URL="postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:5432/${PG_DB}?sslmode=require"

# ═══════════════════════════════════════════════════════════════════════════════
#  3. Azure Cache for Redis
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo ">>> Redis Cache (optional — skip if unavailable)"
# Discover existing Redis in RG, or create one
EXISTING_REDIS=$(az redis list --resource-group "$RG" --query "[0].name" -o tsv 2>/dev/null || true)
if [ -n "$EXISTING_REDIS" ]; then
  REDIS_NAME="$EXISTING_REDIS"
  echo "  Reusing existing Redis: $REDIS_NAME"
elif ! az redis create --resource-group "$RG" --name "$REDIS_NAME" \
       --location "$LOCATION" --sku Basic --vm-size c0 --output none 2>/dev/null; then
  echo "  ⚠️  Redis creation failed — proceeding without cache"
  REDIS_URL=""
fi
if az redis show --resource-group "$RG" --name "$REDIS_NAME" &>/dev/null 2>&1; then
  REDIS_HOST=$(az redis show --resource-group "$RG" --name "$REDIS_NAME" --query hostName -o tsv)
  REDIS_KEY=$(az redis list-keys --resource-group "$RG" --name "$REDIS_NAME" --query primaryKey -o tsv 2>/dev/null || true)
  if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_KEY" ]; then
    REDIS_URL="redis://:${REDIS_KEY}@${REDIS_HOST}:6380"
  else
    REDIS_URL=""
  fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  4. ACA Environment
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo ">>> Container Apps Environment"
if ! az containerapp env show --resource-group "$RG" --name "$ACA_ENV" &>/dev/null; then
  az containerapp env create \
    --resource-group "$RG" --name "$ACA_ENV" --location "$LOCATION" --output none
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  5. Deploy Container Apps
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo ">>> Deploying Bank API"
create_app "pcop-bank" "pcop/bank" 3001 "internal" "$BANK_TAG" \
  "PORT" "3001" \
  "DATABASE_URL" "$DATABASE_URL"

echo ""
echo ">>> Deploying Server Gateway"
create_app "pcop-server" "pcop/server" 8000 "external" "$SERVER_TAG" \
  "PORT" "8000" \
  "JWT_SECRET" "$(openssl rand -hex 32)" \
  "BANK_API_BASE_URL" "http://pcop-bank:3001"

SERVER_FQDN=$(az containerapp show --resource-group "$RG" --name "pcop-server" \
  --query properties.configuration.ingress.fqdn -o tsv)
SERVER_URL="https://${SERVER_FQDN}"

# Build client NOW with known SERVER_URL (NEXT_PUBLIC_* baked at build time)
echo ""
echo ">>> Building client with API URL: $SERVER_URL"
CLIENT_TAG=$(build_and_push "pcop/client"  "${PROJECT_DIR}/client"     "${PROJECT_DIR}/client/Dockerfile")

echo ""
echo ">>> Deploying Client"
create_app "pcop-client" "pcop/client" 3000 "external" "$CLIENT_TAG" \
  "NEXT_PUBLIC_API_URL" "$SERVER_URL"

if [ "${SCORING_SKIPPED:-false}" = "false" ] && \
   az acr repository show-tags --registry "$ACR_NAME" --repository "pcop/scoring" -o tsv 2>/dev/null | grep -q latest; then
  echo ""
  echo ">>> Deploying Scoring"
  create_app "pcop-scoring" "pcop/scoring" 8003 "internal" "latest" \
    "DATABASE_URL" "$DATABASE_URL" \
    "REDIS_URL" "$REDIS_URL" \
    "PYTHONPATH" "/app"
else
  echo ""
  echo ">>> Skipping Scoring — no image in ACR"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  6. Output
# ═══════════════════════════════════════════════════════════════════════════════
CLIENT_FQDN=$(az containerapp show --resource-group "$RG" --name "pcop-client" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ✅  PCOP is live on ACA!                      ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                            ║"
echo "║  Frontend:  https://${CLIENT_FQDN}                         ║"
echo "║  API:       ${SERVER_URL}/api                              ║"
echo "║  Login:     admin / admin123                               ║"
echo "║                                                            ║"
echo "║  Portal:    https://portal.azure.com                       ║"
echo "║  Cleanup:   az group delete --name $RG --yes               ║"
echo "║                                                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
