# WINGMAN

WINGMAN is an AI communication companion built with React, TypeScript, Vite, and FastAPI. It generates short, natural reply suggestions and can transcribe voice notes through Gnani.

## Run locally

### Frontend

```bash
npm install
cp .env.example .env.local
npm run dev -- --port 4000
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend allows the local Vite origins `http://localhost:4000`, `http://localhost:5173`, and `http://localhost:5174` when `web_origin` (also accepts `web_origin`) is not set.

## Deploy

The repository includes `render.yaml` and `vercel.json`. Deploy the backend to Render and the frontend to Vercel. The frontend calls the backend directly; CORS is restricted to the origin(s) configured on Render.

### 1. Render (FastAPI backend)

Create a Render Blueprint from this repository using `render.yaml`, or configure the existing Web Service with:

| Setting | Value |
| --- | --- |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

Set these environment variables in the Render service. The CORS setting uses the exact lowercase key `web_origin` (the backend also accepts `WEB_ORIGIN`):

| Variable | Value |
| --- | --- |
| `web_origin` | `https://wingman-src.vercel.app` |
| `GEMINI_API_KEY` | Your Gemini API key (or configure Groq instead) |
| `GROQ_API_KEY` | Your Groq API key (or configure Gemini instead) |
| `GNANI_API_KEY` | Your Gnani API key; required only for voice transcription |

At least one of `GEMINI_API_KEY` or `GROQ_API_KEY` is needed for reply generation. Set both to enable automatic fallback. `GNANI_API_KEY` is only needed for voice-note transcription.

If you use a custom Vercel domain or want Vercel preview deployments to call this backend, add each exact origin to `web_origin`, separated by commas. Example:

```text
https://wingman-src.vercel.app,https://your-custom-domain.com
```

Origins must include `https://` (or `http://` for local development) and must not include a path. Do not use `*`. The backend intentionally does not enable credentialed cross-origin requests.

### 2. Vercel (React frontend)

Import the same repository into Vercel and use the repository root as the project root. The included `vercel.json` configures the Vite build.

Set this environment variable in Vercel:

| Variable | Value |
| --- | --- |
| `vite_api_base_url` (also accepts `vite_api_base_url`) | Your Render service URL, e.g. `https://wingman-backend.onrender.com` |

Set `vite_api_base_url` for Production and Preview environments as needed, then redeploy so Vite can embed the value into the frontend build. The frontend also accepts the conventional `VITE_API_BASE_URL` alias.

`vite_api_base_url` is a public API base URL, not a secret. Never put Gemini, Groq, or Gnani keys in Vercel or in any `VITE_*` variable. Keep provider keys on Render only.

### 3. Verify the deployment

After both services deploy:

1. Open `https://<your-render-service>.onrender.com/health`; it should return `{"status":"healthy","service":"wingman-backend"}`.
2. Open the Vercel site and use **Test Backend Connection**.
3. Generate a reply. Test voice transcription after adding `GNANI_API_KEY`.

If the browser reports a CORS error, check that Render's `web_origin` exactly matches the deployed site's origin (scheme + hostname, no path or trailing slash), then redeploy the backend. If the frontend points to the wrong API, check `vite_api_base_url` in Vercel and redeploy the frontend.

## Environment variable reference

- Frontend: `vite_api_base_url` (Vercel; also accepts `VITE_API_BASE_URL`; optional locally, where it defaults to `http://localhost:8000`).
- Backend: `web_origin` (also accepts `WEB_ORIGIN`), `GEMINI_API_KEY`, `GROQ_API_KEY`, and `GNANI_API_KEY` (Render).
- Backend model overrides: `GEMINI_MODEL` and `GROQ_MODEL`.

See [.env.example](.env.example) and [backend/.env.example](backend/.env.example) for local templates.
