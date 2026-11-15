
import json
import logging
import os
import requests
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger("uvicorn.error")

# API CONFIGURATION
GNANI_API_KEY = os.getenv("GNANI_API_KEY")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

gemini_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY else None
)

# APPLICATION
app = FastAPI(
    title="WINGMAN API",
    description="Your AI communication companion",
    version="1.0.0"
)

def get_allowed_origins() -> list[str]:
    """Read comma-separated browser origins; default to local Vite dev origins."""
    configured_origins = os.getenv("WEB_ORIGIN") or os.getenv("web_origin")

    if not configured_origins:
        return [
            "http://localhost:4000",
            "http://localhost:5173",
            "http://localhost:5174",
        ]

    origins = []
    for value in configured_origins.split(","):
        origin = value.strip().rstrip("/")
        if not origin:
            continue

        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
            or origin == "*"
        ):
            raise RuntimeError(
                "WEB_ORIGIN must contain one or more comma-separated "
                "origins (scheme + host only), for example "
                "'https://your-app.vercel.app'."
            )

        if origin not in origins:
            origins.append(origin)

    if not origins:
        raise RuntimeError("WEB_ORIGIN must contain at least one valid origin.")

    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# DATA MODELS
class GenerateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    tone: Literal[
        "Natural", "Playful", "Thoughtful", "Flirty"
    ] = "Natural"

    chat_history: Optional[str] = Field(default=None, max_length=4000)
    their_profile: Optional[str] = Field(default=None, max_length=1500)
    my_profile: Optional[str] = Field(default=None, max_length=1500)
    my_style: Optional[str] = Field(default=None, max_length=1000)


class Reply(BaseModel):
    tone: str
    text: str
    explanation: str


class GenerateResponse(BaseModel):
    success: bool
    replies: list[Reply]
    provider: str


# TONE CONFIGURATION
TONE_GUIDE = {
    "Natural": "relaxed and easygoing, like texting someone you already get along with. Plain words, no performance.",
    "Playful": "light teasing, a bit cheeky, never mean. Banter, not jokes.",
    "Thoughtful": "warm and genuinely interested, reacts to something specific they said. Calm, not heavy or poetic.",
    "Flirty": "warm and a little bold, subtle rather than cheesy. No pickup lines, no over-the-top compliments."
}

MAX_WORDS = 20


# SHARED PROMPT
def build_prompt(request: GenerateRequest, message: str) -> str:
    tone = request.tone
    tone_desc = TONE_GUIDE[tone]

    return f"""You are WINGMAN, an AI communication companion.
Help someone write replies that sound like genuine human texting.

TONE: {tone} ({tone_desc})

CONTEXT
Their latest message: {message}
Recent chat (oldest to newest): {request.chat_history or "none"}
About them: {request.their_profile or "unknown"}
About me: {request.my_profile or "unknown"}
How I usually text: {request.my_style or "unknown"}

HOW REAL PEOPLE TEXT
- Keep replies SHORT by default: aim for 5-12 words.
- Usually stay within 5-15 words.
- Only exceed 15 words when the conversation genuinely needs it.
- Never exceed 20 words.
- One line per reply.
- Use simple, everyday language.
- Lowercase and light punctuation are fine.
- Sound spontaneous, not carefully scripted.
- React to something specific instead of being generic.
- Answer what they asked before steering the conversation.
- At most ONE reply may end with a question.
- Emojis: none or one, only if appropriate.
- Match the user's texting style if provided.
- Prefer a natural short sentence over a clever but unnatural one.

STRICTLY AVOID
- Long explanations or unnecessary details.
- Em dashes, semicolons, and words like indeed, delightful, certainly.
- Openers like Ah, Well well, Oh, Haha that's.
- Rehearsed jokes or pickup lines.
- Generic templates.
- Compliments on appearance in early conversations.
- Repeating their words back to them.
- Making every reply end with a question.

FACTS
- Never invent hobbies, jobs, places or plans.
- Only use facts from the profile or chat.
- If personal information is unknown, don't pretend to know it.

BOUNDARIES
- Respect disinterest and personal limits.
- Never pressure, guilt or manipulate.

THREE DIFFERENT APPROACHES
1. Direct: answers plainly with personality.
2. Tease or twist: a playful angle, softer for Thoughtful.
3. Open/relaxed: a short statement or light prompt.

The three replies must feel meaningfully different.
Do not just reword the same sentence three times.

EXAMPLES

Message: "Hey! What do you usually do on weekends?"
About me: likes hiking, bad at cooking, dog named Biscuit

Good:
- "hiking if i'm feeling ambitious, biscuit's walk if i'm not"
- "attempting to cook something and ordering pizza when it fails"
- "depends on the weekend honestly. what's this one looking like"

Message: "I'm so tired today lol"
About me: unknown

Good:
- "long day? what happened"
- "ugh same energy. hope you get to crash early"
- "coffee count?"

Message: "What are you doing tonight?"
About me: unknown

Good:
- "nothing planned yet, you?"
- "keeping it low-key tonight"
- "open to suggestions honestly"

OUTPUT
Return valid JSON only:
{{
  "replies": [
    {{"tone": "{tone}", "text": "...", "explanation": "..."}},
    {{"tone": "{tone}", "text": "...", "explanation": "..."}},
    {{"tone": "{tone}", "text": "...", "explanation": "..."}}
  ]
}}

Exactly three replies.
Each explanation must be under 12 words.
Explanations should be short and describe the conversational approach.
"""


# REPLY VALIDATION
def clean_reply(raw: dict, tone: str) -> dict:
    text = str(raw.get("text", "")).strip()
    text = text.replace("\u2014", ", ").replace("\u2013", ", ")
    text = " ".join(text.split())

    explanation = str(raw.get("explanation", "")).strip()
    explanation = explanation.replace("\u2014", ", ").replace("\u2013", ", ")

    return {
        "tone": tone,
        "text": text,
        "explanation": explanation
    }


def validate_replies(raw_replies: list, tone: str) -> list[dict]:
    if not isinstance(raw_replies, list) or len(raw_replies) != 3:
        raise ValueError("Expected exactly three replies.")

    replies = []

    for item in raw_replies:
        if not isinstance(item, dict):
            raise ValueError("Invalid reply format.")

        reply = clean_reply(item, tone)

        if not reply["text"] or not reply["explanation"]:
            raise ValueError("Reply text or explanation is empty.")

        if len(reply["text"].split()) > MAX_WORDS:
            raise ValueError("Reply is too long.")

        if len(reply["explanation"].split()) >= 12:
            raise ValueError("Explanation is too long.")

        replies.append(reply)

    questions = sum(
        reply["text"].rstrip().endswith("?")
        for reply in replies
    )

    if questions > 1:
        raise ValueError("Too many question-ending replies.")

    return replies


# GEMINI: ONE ATTEMPT ONLY
def generate_with_gemini(prompt: str, tone: str) -> list[dict]:
    if not gemini_client:
        raise RuntimeError("Gemini API key is not configured.")

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=1.1,
            top_p=0.95,
            response_mime_type="application/json"
        ),
        http_options=types.HttpOptions(timeout=12000)
    )

    result = json.loads(response.text)

    return validate_replies(
        result.get("replies", []),
        tone
    )


# GROQ: BACKUP PROVIDER
def generate_with_groq(prompt: str, tone: str) -> list[dict]:
    if not GROQ_API_KEY:
        raise RuntimeError("Groq API key is not configured.")

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 1.0,
            "response_format": {
                "type": "json_object"
            }
        },
        timeout=(5, 25)
    )

    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    result = json.loads(content)

    return validate_replies(
        result.get("replies", []),
        tone
    )


# BASIC ROUTES
@app.get("/")
def home():
    return {
        "message": "Welcome to WINGMAN API",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "wingman-backend"
    }


@app.get("/api/test")
def test_connection():
    return {
        "success": True,
        "message": "React and FastAPI are connected!",
        "product": "WINGMAN"
    }


# GENERATE REPLIES
@app.post("/api/generate", response_model=GenerateResponse)
def generate_replies(request: GenerateRequest):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Please provide a conversation message."
        )

    prompt = build_prompt(request, message)

    # Try Gemini first.
    try:
        replies = generate_with_gemini(prompt, request.tone)

        logger.info("AI provider used: Gemini")

        return {
            "success": True,
            "replies": replies,
            "provider": "gemini"
        }

    except Exception as gemini_error:
        logger.warning("Gemini generation failed; attempting Groq fallback", exc_info=True)

    # Try Groq immediately if Gemini fails.
    try:
        replies = generate_with_groq(prompt, request.tone)

        logger.info("AI provider used: Groq")

        return {
            "success": True,
            "replies": replies,
            "provider": "groq"
        }

    except Exception as groq_error:
        logger.error("Groq generation failed", exc_info=True)

        raise HTTPException(
            status_code=502,
            detail="Both AI providers are unavailable. Please try again."
        )


# GNANI PRISMA SPEECH-TO-TEXT
@app.post("/api/transcribe")
def transcribe_audio(audio_file: UploadFile = File(...)):
    if not GNANI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Gnani API key is not configured."
        )

    allowed_extensions = (
        ".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a"
    )

    filename = audio_file.filename or "audio.wav"

    if not filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="Upload a WAV, MP3, OGG, FLAC, AAC, or M4A file."
        )

    try:
        response = requests.post(
            "https://api.vachana.ai/stt/v3",
            headers={
                "X-API-Key-ID": GNANI_API_KEY
            },
            files={
                "audio_file": (
                    filename,
                    audio_file.file,
                    audio_file.content_type or "application/octet-stream"
                )
            },
            data={
                "model": "prisma-v3.0",
                "language_code": "indic-auto",
                "format": "codemix"
            },
            timeout=60
        )

        try:
            result = response.json()
        except ValueError:
            raise HTTPException(
                status_code=502,
                detail="Gnani returned an invalid response."
            )

        if not response.ok:
            raise HTTPException(
                status_code=response.status_code,
                detail=result
            )

        return {
            "success": True,
            "transcript": result.get("transcript", ""),
            "language": result.get("detected_language_code"),
            "model": result.get("model")
        }

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Gnani's transcription service."
        )

    finally:
        audio_file.file.close()
