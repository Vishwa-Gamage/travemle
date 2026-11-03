from pathlib import Path
import pandas as pd
from app.config.settings import DATA_DIR, DESTINATION_WEIGHTS, INTERESTS
from app.services.data_loader import load_csv
from app.services.scoring import cosine_interest, weighted_score
from .user_profile import UserPreferenceProfile

class DestinationRecommender:
    def __init__(self, data_path: Path = DATA_DIR / "destinations.csv"):
        self.data = load_csv(data_path, ["destination_id", "destination_name", "average_daily_cost", "rating", "popularity_score"])

    def recommend(self, profile: UserPreferenceProfile, top_n: int = 5) -> list[dict]:
        rows = []
        user_vector = [float(profile.interests.count(item) > 0) for item in INTERESTS]
        for _, item in self.data.iterrows():
            item_vector = [float(item[f"{interest}_score"]) for interest in INTERESTS]
            interest = cosine_interest(user_vector, item_vector)
            cost = float(item.average_daily_cost); budget = max(0.0, min(1.0, profile.budget / max(cost * profile.trip_days, 1)))
            duration = 1.0 if item.recommended_min_days <= profile.trip_days <= item.recommended_max_days else .55
            climate = 1.0 if not profile.preferred_climate or str(item.climate).lower() == profile.preferred_climate.lower() else .25
            kind = 1.0 if not profile.destination_type or str(item.destination_type).lower() == profile.destination_type.lower() else .25
            score = weighted_score({"interest": interest, "budget": budget, "duration": duration, "climate": climate, "type": kind, "rating": float(item.rating) / 5, "popularity": float(item.popularity_score)}, DESTINATION_WEIGHTS)
            matched = [interest_name for interest_name in profile.interests if float(item.get(f"{interest_name}_score", 0)) >= .55]
            rows.append({"destination_id": item.destination_id, "destination_name": item.destination_name, "recommendation_score": round(score, 4), "match_percentage": round(score * 100), "estimated_daily_cost": round(cost), "recommended_days": f"{int(item.recommended_min_days)}-{int(item.recommended_max_days)}", "matched_interests": matched, "reason": f"Strong match for {', '.join(matched) or 'your stated'} preferences and fits the selected budget."})
        return sorted(rows, key=lambda row: row["recommendation_score"], reverse=True)[:top_n]
