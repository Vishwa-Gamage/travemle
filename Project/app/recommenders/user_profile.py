from dataclasses import asdict, dataclass, field
from typing import Any
from app.config.settings import INTERESTS

@dataclass
class UserPreferenceProfile:
    budget: float
    trip_days: int
    interests: list[str] = field(default_factory=list)
    preferred_activities: list[str] = field(default_factory=list)
    travel_type: str = "solo"
    accommodation_type: str | None = None
    preferred_climate: str | None = None
    destination_type: str | None = None
    min_hotel_rating: float = 0
    max_accommodation_price_per_night: float | None = None
    activity_budget: float | None = None
    preferred_activity_duration: str | None = None
    family_friendly: bool = False
    accessibility_required: bool = False
    preferred_transport: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "UserPreferenceProfile":
        data = dict(values); data["interests"] = [str(x).lower() for x in data.get("interests", [])]
        data["preferred_activities"] = [str(x).lower() for x in data.get("preferred_activities", [])]
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})

    def feature_vector(self) -> dict[str, float]:
        features = {f"{interest}_score": float(interest in self.interests) for interest in INTERESTS}
        features["budget_score"] = min(1.0, self.budget / 200000)
        features["trip_days_normalized"] = min(1.0, self.trip_days / 14)
        return features

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def human_readable(self) -> dict[str, Any]:
        return {"summary": f"{self.travel_type.title()} traveller for {self.trip_days} days", "interests": self.interests, "budget_lkr": self.budget, "climate": self.preferred_climate, "destination_type": self.destination_type}
