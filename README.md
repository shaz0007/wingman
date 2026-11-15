# WINGMAN ✳

**WINGMAN** is a production-ready AI communication companion designed to help people craft natural, spontaneous text replies, decode conversational dynamics, and transcribe audio voice notes.

---

## ✨ Features

- **✳ Wingman (Reply Generator)**:
  - Generates 3 human-sounding, distinct reply options matching real texting cadence (5–15 words).
  - Four curated conversational tones: `Natural`, `Playful`, `Thoughtful`, and `Flirty`.
  - Contextual awareness: optional support for chat history, relationship notes, personal bios, and custom texting style.
  - High availability multi-provider architecture: **Google Gemini API** with automatic instant failover to **Groq Cloud API**.
  - One-click copy with non-intrusive toast notification and word-count indicators.

- **◈ Coach (Conversation Intelligence)**:
  - Analyzes the emotional vibe, unspoken subtext, and perceived interest level.
  - Generates actionable, tactical response strategies and warns against conversational traps to avoid.
  - Seamless bridge to transfer analyzed insights directly into the Wingman reply generator.

- **◉ Voice Notes (Speech-to-Text)**:
  - **Live in-browser recording** with real-time waveform timer and audio playback preview via MediaRecorder API.
  - **Multi-format file upload** supporting `.wav`, `.mp3`, `.ogg`, `.flac`, `.aac`, `.m4a`, and `.webm`.
  - Powered by **Gnani Prisma v3 STT** with auto-detection for multilingual and code-mixed speech.
  - One-click transfer of transcribed text directly into the Wingman or Coach workspace.

- **🛡 Production-Hardened Security & Reliability**:
  - In-memory sliding-window IP rate limiter preventing API abuse and budget drain.
  - Security headers enforced (`nosniff`, `DENY` framing, referrer policy, permissions policy).
  - Upload file size verification (15 MB safety ceiling) and payload validation.
  - Configurable CORS origins via environment variables.
  - Structured application logging and standard RFC-compliant error envelopes.

---

## 🏗 Architecture

```
┌────────────────────────────────────────────────────────┐
│                   React 19 Frontend                    │
│     (TypeScript + Vite + Modern DM Sans/Playfair UI)    │
└───────────────────────────┬────────────────────────────┘
                            │ /api/*, /health
                            ▼
┌────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                 │
│         (SPA Routing, Gzip, Security Headers)          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                    FastAPI Backend                     │
│  (Rate Limiting, Security Headers, Pydantic Validation)│
└───────┬───────────────────┬────────────────────┬───────┘
        │                   │                    │
        ▼                   ▼                    ▼
┌──────────────┐    ┌──────────────┐     ┌──────────────┐
│Google Gemini │    │  Groq Cloud  │     │ Gnani Prisma │
│ (Primary AI) │    │  (Fallback)  │     │  (Voice STT) │
└──────────────┘    └──────────────┘     └──────────────┘
```

---

## 🚀 Quickstart with Docker Compose

The fastest way to spin up the entire production stack:

1. **Clone the repository and prepare environment files:**
   ```bash
   cp backend/.env.example backend/.env
   ```
   Add your API keys to `backend/.env`:
   - `GEMINI_API_KEY`: Primary reply generation and coach analysis.
   - `GROQ_API_KEY`: Secondary fallback AI provider.
   - `GNANI_API_KEY`: Voice note transcription.

2. **Launch with Docker Compose:**
   ```bash
   docker compose up --build
   ```

3. **Access the application:**
   - **Frontend**: [http://localhost:3000](http://localhost:3000)
   - **Backend API & Health**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 💻 Local Development Setup

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment variables
cp .env.example .env
# Fill in your GEMINI_API_KEY, GROQ_API_KEY, or GNANI_API_KEY

# Start the FastAPI server with hot reload
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be live at `http://localhost:8000` (API documentation at `http://localhost:8000/docs`).

### 2. Frontend Setup

In the root directory:

```bash
# Install dependencies
npm install

# Start Vite development server
npm run dev
```

Frontend will be running at `http://localhost:5173` with automatic API proxying to `http://localhost:8000`.

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Runtime mode (`development`, `production`, `test`) |
| `DEBUG` | `false` | Enable verbose debug logging |
| `HOST` | `0.0.0.0` | Host bind address |
| `PORT` | `8000` | Server listen port |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated list of allowed frontend origins |
| `RATE_LIMIT_ENABLED` | `true` | Enable or disable in-memory IP rate limiter |
| `RATE_LIMIT_PER_MINUTE` | `60` | Maximum requests per client IP per minute |
| `MAX_AUDIO_SIZE_BYTES` | `15728640` | Maximum upload size in bytes (15 MB default) |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key (Primary AI) |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Gemini model name |
| `GROQ_API_KEY` | *(empty)* | Groq API key (Fallback AI) |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Groq model name |
| `GNANI_API_KEY` | *(empty)* | Gnani Prisma STT API key |
| `GNANI_API_URL` | `https://api.vachana.ai/stt/v3`| Gnani endpoint URL |

### Frontend (`.env`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Base backend URL (leave empty when using reverse proxy) |

---

## 📡 API Reference

### `GET /health`
Returns system status, service version, environment, and availability of upstream AI providers.

### `GET /api/test`
Verifies frontend-to-backend communication.

### `POST /api/generate`
Generates 3 contextual response options.
```json
{
  "message": "Hey! Are you free this Friday evening?",
  "tone": "Natural",
  "chat_history": "Met on coffee chat yesterday",
  "their_profile": "Loves live music",
  "my_profile": "Available after 7pm",
  "my_style": "Casual and direct"
}
```

### `POST /api/coach`
Analyzes conversation psychology, vibe, unspoken signals, and recommended next moves.
```json
{
  "message": "Haha maybe, depends on what you have planned",
  "chat_history": "Invited them to dinner",
  "context": "Second date invitation"
}
```

### `POST /api/transcribe`
Uploads audio (`multipart/form-data` with `audio_file`) and returns transcribed text with detected language.

---

## 🧪 Running Tests

### Backend Tests (Python Unit Tests)
```bash
./backend/venv/bin/python -m unittest discover -s backend/tests -v
```
Covers:
- Root & health check endpoints
- AI generation & multi-provider fallback logic
- Coach analysis endpoint
- Speech-to-text upload validation (empty files, invalid extensions, size caps)
- Security headers and rate limiting

### Frontend Tests (Node Native Test Runner)
```bash
npm test
```
Covers:
- Time formatting & word counters
- Text sanitization and boundary constraints

### Linter & Type Check
```bash
npm run lint   # Oxlint
npx tsc -b     # TypeScript strict compilation
npm run build  # Vite production bundle
```

---

## 🚢 Production Deployment

### Option 1: Docker (Single or Multi-host)
Run the pre-configured multi-stage Docker setup:
```bash
docker compose -f docker-compose.yml up -d --build
```

### Option 2: Cloud Platforms (Railway, Render, AWS, Fly.io)
- **Backend**: Point to `backend/Dockerfile` with `PORT=8000`. Provide environment variables via dashboard.
- **Frontend**: Deploy static assets from `npm run build` (`dist/`) or use the root `Dockerfile` (Nginx).

---

## 📄 License

Proprietary / All Rights Reserved © 2026 WINGMAN.
