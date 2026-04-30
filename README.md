# StrikeIQ Backend

FastAPI proxy that keeps the Anthropic API key server-side so it is never
shipped inside the mobile app bundle.

## Local development

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then paste your key into .env
uvicorn main:app --reload
```

Server starts at **http://localhost:8000**.  
Interactive docs at **http://localhost:8000/docs**.

### Test it

```bash
curl -X POST http://localhost:8000/advisor \
  -H "Content-Type: application/json" \
  -d '{
    "water_clarity": "Slightly Stained",
    "species": ["Largemouth Bass"],
    "water_temp": 68,
    "water_level": "Normal",
    "conditions": ["Heavy Grass"],
    "notes": "",
    "time_of_day": "7:00 AM",
    "month": "April"
  }'
```

---

## Deploy to Railway

Railway gives you a free tier and deploys straight from GitHub in ~2 minutes.

### 1 — Push backend to GitHub

If your StrikeIQ3 repo is already on GitHub, Railway can deploy just the
`backend/` subfolder.

### 2 — Create a new Railway project

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select your repo
3. Under **Root Directory** set it to `backend`

### 3 — Set the environment variable

In Railway → your service → **Variables** tab:

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |

Railway injects this at runtime — the key never touches your codebase.

### 4 — Set the start command

Railway auto-detects Python. If it doesn't pick up the right command, set
it manually under **Settings → Deploy → Start Command**:

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Railway sets `$PORT` automatically — do **not** hardcode 8000 in production.

### 5 — Get your public URL

Railway generates a URL like `https://strikeiq-backend-production.up.railway.app`.

### 6 — Update the mobile app

In `services/claude.ts`, replace the `BACKEND_URL` constant:

```ts
const BACKEND_URL = 'https://strikeiq-backend-production.up.railway.app';
```

Rebuild and submit to the App Store / Play Store. The Anthropic key is now
100% server-side and can be rotated any time without a new app release.

---

## Alternative hosts

| Host | Free tier | Notes |
|------|-----------|-------|
| **Railway** | $5 credit/mo | Easiest, auto-detects Python |
| **Render** | 750 hrs/mo | Spins down after 15 min idle on free plan |
| **Fly.io** | 3 shared VMs | Needs a `fly.toml`; more config |
| **Google Cloud Run** | 2M req/mo | Scales to zero, pay-per-request |

For a production app, Railway or Render are the fastest path to ship.
