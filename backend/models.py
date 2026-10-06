# Pydantic data schemas and models. Imported by backend/main.py and external testing tools.
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

InputModality = Literal["text", "voice", "quick_button"]
Urgency = Literal["high", "medium", "low", "none"]

class PassengerRequest(BaseModel):
    seat: str = Field(..., pattern=r"^(?:[1-9]|[12][0-9]|30)[A-F]$", examples=["22A"])
    text: str = Field(..., min_length=1, max_length=500, examples=["I feel dizzy. Can someone help?"])
    input_modality: InputModality = "text"

    @field_validator("text", mode="before")
    @classmethod
    def clean_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('seat', mode='before')
    @classmethod
    def normalize_seat(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().upper()
        return v

class ParsedRequest(BaseModel):
    task_id: int | None = None
    seat: str
    intent: str
    urgency: Urgency
    slots: dict[str, Any] = Field(default_factory=dict)
    crew_required: bool
    assigned_zone: str | None = None
    status: str
    confidence: float = 0.0
    action: str

class FlightContext(BaseModel):
    flight_phase: Literal["boarding", "taxi", "takeoff", "cruise", "landing_preparation", "landing"]
    seatbelt_sign: bool
    meal_service_active: bool
    minutes_to_landing: int = Field(..., ge=0, le=1440)

class PassengerAuth(BaseModel):
    seat: str = Field(..., pattern=r"^(?:[1-9]|[12][0-9]|30)[A-F]$")
    booking_reference: str = Field(..., min_length=4, max_length=20)

    @field_validator('seat', mode='before')
    @classmethod
    def normalize_seat(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().upper()
        return v

class CrewAuth(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=256)

class Announcement(BaseModel):
    id: int | None = None
    timestamp: str = ""
    speaker: Literal["Captain", "Cabin Crew", "First Officer"]
    text: str = Field(..., min_length=1, max_length=2000)
