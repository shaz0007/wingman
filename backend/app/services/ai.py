import json
import logging
import re
from typing import Any, Dict, List, Optional
import requests
from fastapi import HTTPException

from ..config import settings
from ..models import (
    CoachRequest,
    CoachResponse,
    GenerateRequest,
    GenerateResponse,
    Reply,
)

logger = logging.getLogger("wingman.ai")

# Tone guides
TONE_GUIDE = {
    "Natural": "relaxed and easygoing, like texting someone you already get along with. Plain words, no performance.",
    "Playful": "light teasing, a bit cheeky, never mean. Banter, not jokes.",
    "Thoughtful": "warm and genuinely interested, reacts to something specific they said. Calm, not heavy or poetic.",
    "Flirty": "warm and a little bold, subtle rather than cheesy. No pickup lines, no over-the-top compliments.",
}

MAX_WORDS = 20


def extract_json(raw_text: str) -> Dict[str, Any]:
    """Robustly extracts JSON from an LLM response even if wrapped in markdown fences."""
    text = raw_text.strip()

    # If wrapped in ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    # Attempt to locate the outer JSON object { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace + 1]

    return json.loads(text)


def build_generate_prompt(request: GenerateRequest) -> str:
    tone = request.tone
    tone_desc = TONE_GUIDE.get(tone, TONE_GUIDE["Natural"])

    return f"""You are WINGMAN, an AI communication companion.
Help someone write replies that sound like genuine human texting.

TONE: {tone} ({tone_desc})

CONTEXT
Their latest message: {request.message}
Recent chat (oldest to newest): {request.chat_history or "none"}
About them: {request.their_profile or "unknown"}
About me: {request.my_profile or "unknown"}
How I usually text: {request.my_style or "unknown"}

HOW REAL PEOPLE TEXT
- Keep replies SHORT by default: aim for 5-12 words.
- Usually stay within 5-15 words.
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

FACTS & BOUNDARIES
- Never invent hobbies, jobs, places or plans.
- If personal information is unknown, don't pretend to know it.
- Respect disinterest and personal limits. Never pressure or manipulate.

THREE DIFFERENT APPROACHES
1. Direct: answers plainly with personality.
2. Tease or twist: a playful angle, softer for Thoughtful.
3. Open/relaxed: a short statement or light prompt.

The three replies must feel meaningfully different. Do not just reword the same sentence three times.

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
Each explanation must be under 12 words describing the conversational approach.
"""


def build_coach_prompt(request: CoachRequest) -> str:
    return f"""You are WINGMAN Coach, an expert interpersonal communication advisor.
Analyze the following conversation message and provide concise, insightful tactical guidance.

LATEST MESSAGE:
"{request.message}"

CHAT HISTORY:
{request.chat_history or "None provided"}

ADDITIONAL CONTEXT:
{request.context or "None provided"}

Analyze the psychological dynamic, sentiment, and unspoken subtext.
Keep your analysis grounded, honest, empowering, and actionable.

OUTPUT FORMAT:
Return valid JSON only matching this exact schema:
{{
  "vibe": "Concise summary of their tone and energy (e.g., Warm & inviting, Guarded curiosity, Playful banter)",
  "subtext": "What they are really saying or hinting at beneath the surface (1-2 sentences)",
  "interest_level": "One of: High, Moderate, Cautious, or Low",
  "recommended_strategy": "Actionable, direct advice on how to steer the conversation effectively (2-3 sentences)",
  "avoid": [
    "First specific pitfall or trap to avoid",
    "Second specific pitfall to avoid",
    "Third specific pitfall to avoid"
  ]
}}
"""


def sanitize_reply(raw: dict, tone: str) -> Reply:
    text = str(raw.get("text", "")).strip()
    text = text.replace("\u2014", ", ").replace("\u2013", ", ")
    text = " ".join(text.split())

    explanation = str(raw.get("explanation", "")).strip()
    explanation = explanation.replace("\u2014", ", ").replace("\u2013", ", ")
    explanation = " ".join(explanation.split())

    # Ensure words limit is gracefully enforced if model runs slightly over
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS])

    exp_words = explanation.split()
    if len(exp_words) > 15:
        explanation = " ".join(exp_words[:12])

    if not text:
        text = "hey, sounds good"
    if not explanation:
        explanation = "Direct and natural response"

    return Reply(
        tone=tone,
        text=text,
        explanation=explanation
    )


def validate_and_clean_replies(raw_replies: Any, tone: str) -> List[Reply]:
    if not isinstance(raw_replies, list) or len(raw_replies) == 0:
        raise ValueError("AI response did not contain a valid replies list.")

    replies: List[Reply] = []
    for item in raw_replies[:3]:
        if isinstance(item, dict):
            replies.append(sanitize_reply(item, tone))

    # Pad if model returned fewer than 3 replies
    while len(replies) < 3:
        replies.append(
            Reply(
                tone=tone,
                text="sounds good, let me know",
                explanation="Relaxed alternative option"
            )
        )

    return replies


def call_gemini(prompt: str) -> str:
    """Calls the Google Gemini API using google-genai SDK."""
    if not settings.is_gemini_configured:
        raise RuntimeError("Gemini API key is not configured.")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=1.0,
                top_p=0.95,
                response_mime_type="application/json"
            ),
            http_options=types.HttpOptions(timeout=15000)
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        return response.text
    except Exception as e:
        logger.warning("Gemini generation failed: %s", e)
        raise


def call_groq(prompt: str) -> str:
    """Calls Groq API as a resilient fallback provider."""
    if not settings.is_groq_configured:
        raise RuntimeError("Groq API key is not configured.")

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 1.0,
                "response_format": {"type": "json_object"},
            },
            timeout=(5, 25),
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("Groq generation failed: %s", e)
        raise


def generate_replies_service(request: GenerateRequest) -> GenerateResponse:
    """Generates 3 curated replies using Gemini with automatic Groq fallback."""
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Please provide a message.")

    prompt = build_generate_prompt(request)
    provider_used = "gemini"
    raw_response: Optional[str] = None

    # 1. Try Gemini
    if settings.is_gemini_configured:
        try:
            raw_response = call_gemini(prompt)
            data = extract_json(raw_response)
            replies = validate_and_clean_replies(data.get("replies", []), request.tone)
            logger.info("Successfully generated replies using Gemini")
            return GenerateResponse(success=True, replies=replies, provider="gemini")
        except Exception as e:
            logger.warning("Gemini failed, falling back to Groq: %s", e)

    # 2. Try Groq fallback
    if settings.is_groq_configured:
        try:
            raw_response = call_groq(prompt)
            data = extract_json(raw_response)
            replies = validate_and_clean_replies(data.get("replies", []), request.tone)
            logger.info("Successfully generated replies using Groq fallback")
            return GenerateResponse(success=True, replies=replies, provider="groq")
        except Exception as e:
            logger.error("Groq fallback also failed: %s", e)

    # If neither succeeded
    if not settings.is_gemini_configured and not settings.is_groq_configured:
        raise HTTPException(
            status_code=503,
            detail="No AI providers are configured. Please set GEMINI_API_KEY or GROQ_API_KEY.",
        )

    raise HTTPException(
        status_code=502,
        detail="All AI providers are currently unavailable. Please try again shortly.",
    )


def coach_service(request: CoachRequest) -> CoachResponse:
    """Analyzes a conversation snippet to provide deep coaching insights."""
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Please provide a message to analyze.")

    prompt = build_coach_prompt(request)

    # 1. Try Gemini
    if settings.is_gemini_configured:
        try:
            raw_response = call_gemini(prompt)
            data = extract_json(raw_response)
            return CoachResponse(
                success=True,
                vibe=str(data.get("vibe", "Warm & receptive")),
                subtext=str(data.get("subtext", "They are engaged and open to continuing.")),
                interest_level=str(data.get("interest_level", "Moderate")),
                recommended_strategy=str(data.get("recommended_strategy", "Keep the energy balanced and match their pacing.")),
                avoid=list(data.get("avoid", ["Over-analyzing", "Writing a wall of text"])),
                provider="gemini",
            )
        except Exception as e:
            logger.warning("Gemini coach analysis failed: %s", e)

    # 2. Try Groq fallback
    if settings.is_groq_configured:
        try:
            raw_response = call_groq(prompt)
            data = extract_json(raw_response)
            return CoachResponse(
                success=True,
                vibe=str(data.get("vibe", "Warm & receptive")),
                subtext=str(data.get("subtext", "They are engaged and open to continuing.")),
                interest_level=str(data.get("interest_level", "Moderate")),
                recommended_strategy=str(data.get("recommended_strategy", "Keep the energy balanced and match their pacing.")),
                avoid=list(data.get("avoid", ["Over-analyzing", "Writing a wall of text"])),
                provider="groq",
            )
        except Exception as e:
            logger.error("Groq coach analysis failed: %s", e)

    if not settings.is_gemini_configured and not settings.is_groq_configured:
        raise HTTPException(
            status_code=503,
            detail="No AI providers are configured. Please set GEMINI_API_KEY or GROQ_API_KEY.",
        )

    raise HTTPException(
        status_code=502,
        detail="Conversation coach is currently unavailable. Please try again shortly.",
    )
