import logging
from typing import Tuple
from fastapi import HTTPException, UploadFile
import requests

from backend.app.config import settings
from backend.app.models import TranscribeResponse

logger = logging.getLogger("wingman.stt")

ALLOWED_EXTENSIONS: Tuple[str, ...] = (
    ".wav",
    ".mp3",
    ".ogg",
    ".flac",
    ".aac",
    ".m4a",
    ".webm",
)


async def transcribe_audio_service(audio_file: UploadFile) -> TranscribeResponse:
    """Transcribes an uploaded audio file using Gnani Prisma STT with validation."""
    if not settings.is_gnani_configured:
        raise HTTPException(
            status_code=503,
            detail="Speech-to-text service is not configured. Please set GNANI_API_KEY.",
        )

    filename = audio_file.filename or "recording.wav"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported formats: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    try:
        # Read content while monitoring size limit
        content = await audio_file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        if len(content) > settings.MAX_AUDIO_SIZE_BYTES:
            max_mb = settings.MAX_AUDIO_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"Audio file is too large. Maximum allowed size is {max_mb} MB.",
            )

        content_type = audio_file.content_type or "audio/wav"

        logger.info("Sending %d bytes of audio (%s) to Gnani STT", len(content), filename)

        response = requests.post(
            settings.GNANI_API_URL,
            headers={
                "X-API-Key-ID": settings.GNANI_API_KEY,
            },
            files={
                "audio_file": (filename, content, content_type),
            },
            data={
                "model": "prisma-v3.0",
                "language_code": "indic-auto",
                "format": "codemix",
            },
            timeout=45,
        )

        try:
            result = response.json()
        except ValueError:
            logger.error("Gnani STT returned non-JSON response (status: %d)", response.status_code)
            raise HTTPException(
                status_code=502,
                detail="Speech-to-text provider returned an unexpected response format.",
            )

        if not response.ok:
            error_detail = result.get("message") or result.get("detail") or "Transcription failed"
            logger.warning("Gnani STT API error (%d): %s", response.status_code, error_detail)
            raise HTTPException(status_code=response.status_code, detail=str(error_detail))

        transcript = result.get("transcript", "").strip()
        if not transcript:
            raise HTTPException(
                status_code=422,
                detail="No spoken words were detected in the audio.",
            )

        return TranscribeResponse(
            success=True,
            transcript=transcript,
            language=result.get("detected_language_code") or result.get("language"),
            model=result.get("model") or "prisma-v3.0",
        )

    except requests.Timeout:
        logger.error("Gnani STT request timed out")
        raise HTTPException(
            status_code=504,
            detail="Speech-to-text service timed out. Please try a shorter audio clip.",
        )
    except requests.RequestException as e:
        logger.error("Gnani STT network error: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Could not establish connection to the transcription service.",
        )
    finally:
        await audio_file.close()
