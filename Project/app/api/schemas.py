from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.config.settings import INTERESTS

class PreferenceRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    budget: float = Field(gt=0)
    trip_days: int = Field(gt=0, le=60)
    interests: list[str] = Field(default_factory=list)
    preferred_activities: list[str] = Field(default_factory=list)
    travel_type: str = "solo"
    accommodation_type: str | None = None
    preferred_climate: str | None = None
    destination_type: str | None = None
    min_hotel_rating: float = Field(default=0, ge=0, le=5)
    max_accommodation_price_per_night: float | None = Field(default=None, gt=0)
    activity_budget: float | None = Field(default=None, gt=0)
    preferred_activity_duration: str | None = None
    family_friendly: bool = False
    accessibility_required: bool = False
    preferred_transport: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    top_n: int = Field(default=5, ge=1, le=50)

    @field_validator("interests", "preferred_activities")
    @classmethod
    def clean_list(cls, values: list[str]) -> list[str]:
        return [value.strip().lower() for value in values if value.strip()]

class AccommodationRequest(BaseModel):
    destination_id: str
    max_price_per_night: float = Field(gt=0)
    accommodation_type: str | None = None
    min_rating: float = Field(default=0, ge=0, le=5)
    family_friendly: bool = False
    accessibility_required: bool = False
    preferred_facilities: list[str] = Field(default_factory=list)
    top_n: int = Field(default=5, ge=1, le=50)

class ActivityRequest(BaseModel):
    destination_id: str
    interests: list[str] = Field(default_factory=list)
    preferred_activities: list[str] = Field(default_factory=list)
    remaining_budget: float = Field(gt=0)
    available_hours: float = Field(default=8, gt=0)
    family_friendly: bool = False
    accessibility_required: bool = False
    top_n: int = Field(default=5, ge=1, le=50)

class ProfileResponse(BaseModel):
    human_readable: dict[str, Any]
    feature_vector: dict[str, float]
