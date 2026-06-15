# PCOP — Deployment Guide

> Only two services need to deploy: **Express backend** (`server/`) and **Next.js frontend** (`client/`).
> Everything else (ML layers, Kafka, PostgreSQL) is optional — the demo runs fully in-memory with simulation mode.

---

## What Actually Runs at Demo Time

| Service | Needed | Notes |
|---------|--------|-------|
| Express backend (`server/`) | ✅ | API, auth, in-memory data, Kafka sim |
| Next.js frontend (`client/`) | ✅ | Dashboard, customer pages, analytics |
| NVIDIA API | ✅ | DeepSeek V4 Pro for live HERALD outreach |
| CHRONOS FastAPI (`chronos/`) | ❌ | Scores are pre-computed in `chronos/data/` |
| PostgreSQL | ❌ | Replaced by `server/services/localData.js` |
| Kafka broker | ❌ | Auto-simulation kicks in when broker absent |
| Redis | ❌ | Not wired into the demo server |
| `bank/` data server | ❌ | `localData.js` is the fallback |

---

## Local Development

```bash
# Terminal 1 — backend (http://localhost:8000)
cd server
npm install
node index.js

# Terminal 2 — frontend (http://localhost:3000)
cd client
npm install
npm run dev
```

Create `server/.env` before starting the backend:

```env
PORT=8000
JWT_SECRET=any-random-string-here

# NVIDIA DeepSeek V4 Pro — required only for live HERALD generation
NVIDIA_ENDPOINT=https://integrate.api.nvidia.com/v1/chat/completions
NVIDIA_API_KEY=<your-nvidia-api-key>
NVIDIA_MODEL=deepseek-ai/deepseek-v4-pro
```

If `NVIDIA_API_KEY` is not set, HERALD falls back to pre-cached content in `server/data/herald.json`. Everything else works without it.

---

## Deploying to Render (Free Tier)

### Backend

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repo, branch **main**
3. Set:

   | Field | Value |
   |-------|-------|
   | Root Directory | *(leave blank)* |
   | Environment | `Node` |
   | Build Command | `cd server && npm install --production` |
   | Start Command | `node server/index.js` |
   | Instance Type | Free |

4. Environment variables:

   | Key | Value |
   |-----|-------|
   | `PORT` | `10000` |
   | `NODE_ENV` | `production` |
   | `JWT_SECRET` | *(random 32+ char string)* |
   | `NVIDIA_ENDPOINT` | `https://integrate.api.nvidia.com/v1/chat/completions` |
   | `NVIDIA_API_KEY` | *(your key)* |
   | `NVIDIA_MODEL` | `deepseek-ai/deepseek-v4-pro` |

5. Deploy. Note the public URL — this is your `BACKEND_URL`.

> **Free tier tip:** Render spins down after 15 min idle. Open `<BACKEND_URL>/auth/login` in a browser before your demo to wake it up.

### Frontend

1. **New** → **Web Service**, same repo
2. Set:

   | Field | Value |
   |-------|-------|
   | Root Directory | `client` |
   | Environment | `Node` |
   | Build Command | `npm install && npm run build` |
   | Start Command | `npm start` |

3. Environment variable:

   | Key | Value |
   |-----|-------|
   | `API_BACKEND_URL` | Your backend URL from above |
   | `NODE_ENV` | `production` |

---

## Deploying to Railway

### Backend

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select your repo, branch **main**
3. Settings:

   | Setting | Value |
   |---------|-------|
   | Build Command | `cd server && npm install --production` |
   | Start Command | `node server/index.js` |
   | Port | `8000` |

4. Variables tab — same keys as Render above (use `PORT=8000`)
5. Note the public URL.

### Frontend

1. Add a second service from the same repo
2. Settings:

   | Setting | Value |
   |---------|-------|
   | Root Directory | `client` |
   | Build Command | `npm install && npm run build` |
   | Start Command | `npm start` |
   | Port | `3000` |

3. Set `API_BACKEND_URL` to the backend URL.

---

## Environment Variables Reference

### Backend (`server/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | Yes | `8000` (Railway) or `10000` (Render) |
| `NODE_ENV` | Yes | `production` |
| `JWT_SECRET` | Yes | Any random 32+ char string |
| `NVIDIA_ENDPOINT` | For HERALD | `https://integrate.api.nvidia.com/v1/chat/completions` |
| `NVIDIA_API_KEY` | For HERALD | Your NVIDIA key |
| `NVIDIA_MODEL` | For HERALD | `deepseek-ai/deepseek-v4-pro` |

### Frontend (`client/.env`)

| Variable | When | Value |
|----------|------|-------|
| `API_BACKEND_URL` | Build time | Full HTTPS URL of the backend |
| `NODE_ENV` | Runtime | `production` |

---

## Demo Credentials

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Administrator |
| `manager` | `manager123` | Portfolio Manager |
| `analyst` | `analyst123` | Risk Analyst |

---

## Troubleshooting

**Dashboard shows all zeros**
Frontend can't reach backend. Check `API_BACKEND_URL` includes `https://`. Open the backend URL directly — you should see `{"status":"error","message":"Route not found"}`.

**Login returns "Invalid credentials"**
`JWT_SECRET` is not set in the backend environment.

**HERALD outreach generation fails**
Check `NVIDIA_API_KEY` and `NVIDIA_ENDPOINT`. The rest of the platform works without these — it falls back to cached content.

**Render — 503 on first load**
Free tier cold start takes ~90 seconds. Pre-warm the backend URL before your demo.
