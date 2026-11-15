import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .middleware import (
    ProcessTimeMiddleware,
    RateLimiterMiddleware,
    SecurityHeadersMiddleware,
)
from .models import (
    CoachRequest,
    CoachResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    MessageResponse,
    TranscribeResponse,
)
from .services.ai import coach_service, generate_replies_service
from .services.stt import transcribe_audio_service

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("wingman.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("Starting WINGMAN API [env=%s]", settings.ENVIRONMENT)
    logger.info("Gemini provider configured: %s", settings.is_gemini_configured)
    logger.info("Groq provider configured: %s", settings.is_groq_configured)
    logger.info("Gnani STT configured: %s", settings.is_gnani_configured)
    yield
    logger.info("Shutting down WINGMAN API")


app = FastAPI(
    title="WINGMAN API",
    description="Production-ready conversational assistant and voice transcription backend.",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" or settings.DEBUG else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" or settings.DEBUG else None,
    lifespan=lifespan,
)

# 1. Timing middleware
app.add_middleware(ProcessTimeMiddleware)

# 2. Rate limiter
app.add_middleware(RateLimiterMiddleware)

# 3. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 4. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "An unexpected internal server error occurred.",
            "status_code": 500,
        },
    )


# ---------------- Routes ----------------


@app.api_route("/", methods=["GET", "HEAD"], tags=["Info"])
def root():
    return {
        "message": "Welcome to WINGMAN API",
        "status": "running",
        "version": "1.0.0",
    }


@app.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse, tags=["Health"])
def health_check():
    return HealthResponse(
        status="healthy",
        service="wingman-backend",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        providers={
            "gemini": settings.is_gemini_configured,
            "groq": settings.is_groq_configured,
            "gnani": settings.is_gnani_configured,
        },
    )


@app.get("/api/test", response_model=MessageResponse, tags=["Diagnostics"])
def test_connection():
    return MessageResponse(
        success=True,
        message="React and FastAPI are connected!",
        product="WINGMAN",
    )


@app.post("/api/generate", response_model=GenerateResponse, tags=["Conversational AI"])
def generate_replies(request: GenerateRequest):
    """Generate 3 contextual text replies across selected tone with automatic fallback."""
    return generate_replies_service(request)


@app.post("/api/coach", response_model=CoachResponse, tags=["Conversational AI"])
def coach_conversation(request: CoachRequest):
    """Analyze a conversation message to extract vibe, subtext, interest, and tactical strategy."""
    return coach_service(request)


@app.post("/api/transcribe", response_model=TranscribeResponse, tags=["Speech To Text"])
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """Transcribe user-uploaded voice notes using Gnani Prisma speech-to-text."""
    return await transcribe_audio_service(audio_file)
