#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy-azure-vm.sh — Deploy PCOP to a single Azure VM with Docker Compose
# Usage:
#   ./deploy-azure-vm.sh [location] [vm-size]
#   ./deploy-azure-vm.sh westus Standard_B2ms
#   ./deploy-azure-vm.sh --list-sizes [location]
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
RG="pcop-rg"
VM_NAME="pcop-vm"
LOCATION="${1:-southeastasia}"
VM_SIZE="${2:-Standard_B1s}"
ADMIN_USER="azureuser"
DNS_PREFIX="pcop-app"
AUTO_SHUTDOWN_TIME="0000"   # UTC (midnight) — saves money

# Show help / list sizes
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  sed -n '2,7p' "$0"
  exit 0
fi
if [ "${1:-}" = "--list-sizes" ]; then
  LOC="${2:-$LOCATION}"
  echo "Available B-series sizes in ${LOC}:"
  az vm list-skus --location "$LOC" \
    --query "[?contains(name, 'Standard_B')].name" -o tsv | sort
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Pre-flight checks ────────────────────────────────────────────────────────
for envfile in server/.env chronos/.env; do
  [ -f "$PROJECT_DIR/$envfile" ] || echo "⚠️  Missing $envfile — Azure AI keys may not be set"
done

# ── Prerequisites ────────────────────────────────────────────────────────────
command -v az >/dev/null 2>&1 || { echo "❌ Install Azure CLI first: brew install azure-cli"; exit 1; }

az account show --query name -o tsv 2>/dev/null || {
  echo "❌ Not logged in. Run: az login"; exit 1
}

echo "=== Deploying PCOP to Azure ==="
echo "  Resource Group: $RG"
echo "  Location:       $LOCATION"
echo "  VM Size:        $VM_SIZE"
echo "  DNS:            ${DNS_PREFIX}.${LOCATION}.cloudapp.azure.com"
echo ""

# ── Resource Group ───────────────────────────────────────────────────────────
EXISTING_LOCATION=$(az group show --name "$RG" --query location -o tsv 2>/dev/null || true)
if [ -n "$EXISTING_LOCATION" ] && [ "$EXISTING_LOCATION" != "$LOCATION" ]; then
  echo "  ⚠️  Resource group '$RG' exists in '$EXISTING_LOCATION' but you requested '$LOCATION'."
  echo "     Deleting and recreating (may take ~1 min)..."
  az group delete --name "$RG" --yes --no-wait
  az group wait --name "$RG" --deleted --timeout 180
  az group create --name "$RG" --location "$LOCATION" --output none
elif [ -n "$EXISTING_LOCATION" ]; then
  echo "  Resource group '$RG' already exists in '$LOCATION' — reusing"
else
  az group create --name "$RG" --location "$LOCATION" --output none
fi
FQDN="${DNS_PREFIX}.${LOCATION}.cloudapp.azure.com"

# ── NSG Rules ────────────────────────────────────────────────────────────────
echo "=== Creating NSG rules ==="
az network nsg create --resource-group "$RG" --name "${VM_NAME}-nsg" --output none

for rule in \
  "client-3000:3000:3000:*" \
  "server-8000:8000:8000:*" \
  "scoring-8001:8001:8001:*" \
  "ssh:22:22:*"; do
  IFS=':' read -r name port dest _ <<< "$rule"
  az network nsg rule create \
    --resource-group "$RG" --nsg-name "${VM_NAME}-nsg" \
    --name "$name" --priority "${dest}" \
    --access Allow --protocol Tcp \
    --destination-port-ranges "$port" \
    --source-address-prefixes '*' \
    --output none 2>/dev/null || true
done

# ── VM with cloud-init ───────────────────────────────────────────────────────
echo "=== Creating VM (this takes ~2 min) ==="
az vm create \
  --resource-group "$RG" \
  --name "$VM_NAME" \
  --image Ubuntu2404 \
  --size "$VM_SIZE" \
  --admin-username "$ADMIN_USER" \
  --nsg "${VM_NAME}-nsg" \
  --public-ip-address-dns-name "$DNS_PREFIX" \
  --custom-data "$SCRIPT_DIR/cloud-init.yml" \
  --generate-ssh-keys \
  --output table

# ── Open additional ports ────────────────────────────────────────────────────
# (VM create already opened SSH; ensure app ports are open)
az vm open-port \
  --resource-group "$RG" --name "$VM_NAME" \
  --port 3000,8000,8001 \
  --output none 2>/dev/null || true

# ── Auto-shutdown (saves $$$) ────────────────────────────────────────────────
echo "=== Setting auto-shutdown (${AUTO_SHUTDOWN_TIME} UTC) ==="
az vm auto-shutdown \
  --resource-group "$RG" --name "$VM_NAME" \
  --time "$AUTO_SHUTDOWN_TIME" \
  --output none 2>/dev/null || true

# ── Get connection info ──────────────────────────────────────────────────────
IP=$(az vm show \
  --resource-group "$RG" --name "$VM_NAME" \
  --query publicIpAddress -o tsv)
FQDN="${DNS_PREFIX}.${LOCATION}.cloudapp.azure.com"

echo ""
echo "=== VM ready ==="
echo "  Public IP:  $IP"
echo "  FQDN:       $FQDN"
echo "  SSH:        ssh ${ADMIN_USER}@${FQDN}"
echo ""

# ── Wait for SSH ─────────────────────────────────────────────────────────────
echo "=== Waiting for SSH (cloud-init may still be running) ==="
for i in $(seq 1 30); do
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    "${ADMIN_USER}@${FQDN}" "systemctl is-active docker" 2>/dev/null && break
  echo "  attempt $i/30 — retrying in 10s..."
  sleep 10
done

# ── Upload project ───────────────────────────────────────────────────────────
echo "=== Uploading project (excluding node_modules, .next, etc.) ==="
rsync -avz --delete \
  --exclude='node_modules' --exclude='.next' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.venv' --exclude='.git' \
  --exclude='chronos/ml/checkpoints' --exclude='chronos/data' \
  --exclude='mlruns' --exclude='*.db' \
  -e "ssh -o StrictHostKeyChecking=no" \
  "${PROJECT_DIR}/" "${ADMIN_USER}@${FQDN}:/opt/pcop/"

# ── Run Docker Compose ───────────────────────────────────────────────────────
echo "=== Building and starting containers ==="
ssh -o StrictHostKeyChecking=no "${ADMIN_USER}@${FQDN}" \
  "cd /opt/pcop && \
   export NEXT_PUBLIC_API_URL=http://${FQDN}:8000 && \
   export JWT_SECRET=$(openssl rand -hex 32) && \
   docker compose up -d --build"

# ── Wait for health ──────────────────────────────────────────────────────────
echo "=== Waiting for services ==="
for i in $(seq 1 30); do
  sleep 5
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://${FQDN}:8000/health" 2>/dev/null || echo "000")
  echo "  attempt $i/30 — server: ${STATUS}"
  [ "$STATUS" = "200" ] && break
done

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   ✅  PCOP is live on Azure!                ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                            ║"
echo "║  Frontend:  http://${FQDN}:3000                            ║"
echo "║  API:       http://${FQDN}:8000/api                        ║"
echo "║  Scoring:   http://${FQDN}:8001/health                     ║"
echo "║  Login:     admin / admin123                               ║"
echo "║                                                            ║"
echo "║  SSH:       ssh ${ADMIN_USER}@${FQDN}                      ║"
echo "║  Logs:      ssh ${ADMIN_USER}@${FQDN} 'docker compose logs -f'  ║"
echo "║                                                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
