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

When `web_origin` is not configured, the backend permits the local Vite origins `http://localhost:4000`, `http://localhost:5173`, and `http://localhost:5174`.

## Deploy to Render and Vercel

The repository includes `render.yaml` and `vercel.json`. Deploy the FastAPI backend to Render and the React frontend to Vercel. The frontend calls the backend directly; the backend allows only the origin(s) configured through `web_origin`.

### 1. Render: FastAPI backend

Create a Render Blueprint from this repository using `render.yaml`, or configure the existing Web Service with:

| Setting | Value |
| --- | --- |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

Set these variables in the Render service:

| Variable | Value |
| --- | --- |
| `web_origin` | `https://wingman-src.vercel.app` |
| `GEMINI_API_KEY` | Your Gemini API key |
| `GROQ_API_KEY` | Your Groq API key |
| `GNANI_API_KEY` | Your Gnani key; needed only for voice transcription |

The backend also accepts the conventional uppercase alias `WEB_ORIGIN`. Set `web_origin` to the exact Vercel site origin: scheme plus hostname, with no path. For a custom domain or additional preview domain, add each exact origin separated by commas, for example:

```text
https://wingman-src.vercel.app,https://your-custom-domain.com
```

Do not use `*`. CORS is restricted to these origins and does not allow credentialed cross-origin requests.

At least one of `GEMINI_API_KEY` or `GROQ_API_KEY` is required for reply generation. Configure both to enable fallback. `GNANI_API_KEY` is optional unless voice transcription is needed.

### 2. Vercel: React frontend

Import the repository into Vercel and use the repository root as the project root. The included `vercel.json` configures the Vite build.

Set this environment variable in Vercel:

| Variable | Value |
| --- | --- |
| `vite_api_base_url` | Your Render service URL, e.g. `https://wingman-backend.onrender.com` |

Vite is configured to expose the requested lowercase `vite_api_base_url` value to the frontend bundle. The conventional uppercase alias `VITE_API_BASE_URL` is also supported. Set the variable for Production and Preview environments as needed, then redeploy so Vite embeds the value in the frontend build.

The API base URL is public. Never put Gemini, Groq, or Gnani keys in Vercel or in any `VITE_*` or `vite_*` variable. Keep provider secrets on Render only.

### 3. Verify deployment

1. Open `https://<your-render-service>.onrender.com/health`. It should return `{"status":"healthy","service":"wingman-backend"}`.
2. Open the Vercel site and select **Test Backend Connection**.
3. Generate a reply. Test voice transcription after configuring `GNANI_API_KEY`.

If the browser reports a CORS error, verify that Render's `web_origin` exactly matches the frontend's deployed origin, then redeploy the backend. If API requests target the wrong host, verify `vite_api_base_url` in Vercel and redeploy the frontend.

## Environment variable reference

- Frontend on Vercel: `vite_api_base_url` (also accepts `VITE_API_BASE_URL`). It is optional locally and defaults to `http://localhost:8000`.
- Backend on Render: `web_origin` (also accepts `WEB_ORIGIN`), `GEMINI_API_KEY`, `GROQ_API_KEY`, and optionally `GNANI_API_KEY`.
- Optional backend model overrides: `GEMINI_MODEL` and `GROQ_MODEL`.

See [.env.example](.env.example) and [backend/.env.example](backend/.env.example) for local templates.
