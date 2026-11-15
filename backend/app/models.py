from typing import List, Literal, Optional
from pydantic import BaseModel, Field

ToneType = Literal["Natural", "Playful", "Thoughtful", "Flirty"]


class GenerateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="The message received")
    tone: ToneType = Field(default="Natural", description="Desired response tone")
    chat_history: Optional[str] = Field(default=None, max_length=4000, description="Recent conversation history")
    their_profile: Optional[str] = Field(default=None, max_length=1500, description="Info about the other person")
    my_profile: Optional[str] = Field(default=None, max_length=1500, description="Info about user")
    my_style: Optional[str] = Field(default=None, max_length=1000, description="Personal texting style preferences")


class Reply(BaseModel):
    tone: str
    text: str
    explanation: str


class GenerateResponse(BaseModel):
    success: bool = True
    replies: List[Reply]
    provider: str


class CoachRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Message or conversation snippet to analyze")
    chat_history: Optional[str] = Field(default=None, max_length=4000, description="Preceding context")
    context: Optional[str] = Field(default=None, max_length=1500, description="Relationship context or background")


class CoachResponse(BaseModel):
    success: bool = True
    vibe: str = Field(description="Overall emotional tone and vibe of the conversation")
    subtext: str = Field(description="Underlying meaning and unsaid signals")
    interest_level: str = Field(description="Perceived interest level: High, Moderate, Cautious, Low")
    recommended_strategy: str = Field(description="Best angle/strategy for your next move")
    avoid: List[str] = Field(description="Specific conversational traps or things to avoid")
    provider: str


class TranscribeResponse(BaseModel):
    success: bool = True
    transcript: str
    language: Optional[str] = None
    model: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    providers: dict


class MessageResponse(BaseModel):
    success: bool
    message: str
    product: str = "WINGMAN"
