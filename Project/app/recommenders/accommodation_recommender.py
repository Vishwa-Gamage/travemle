from pathlib import Path
from app.config.settings import ACCOMMODATION_WEIGHTS, DATA_DIR
from app.services.data_loader import load_csv
from app.services.scoring import weighted_score

class AccommodationRecommender:
    def __init__(self, data_path: Path = DATA_DIR / "accommodations.csv"):
        self.data = load_csv(data_path, ["accommodation_id", "destination_id", "price_per_night", "rating"])

    def recommend(self, destination_id: str, max_price: float, accommodation_type: str | None = None, min_rating: float = 0, family_friendly: bool = False, accessibility_required: bool = False, preferred_facilities: list[str] | None = None, top_n: int = 5) -> list[dict]:
        preferred_facilities = [value.lower() for value in (preferred_facilities or [])]
        subset = self.data[self.data.destination_id.astype(str).str.lower() == destination_id.lower()].copy()
        subset = subset[(subset.price_per_night <= max_price) & (subset.rating >= min_rating)]
        if family_friendly: subset = subset[subset.family_friendly.astype(bool)]
        if accessibility_required: subset = subset[subset.accessible.astype(bool)]
        rows = []
        for _, item in subset.iterrows():
            facilities = [name for name in ["wifi", "pool", "breakfast", "parking", "air_conditioning"] if bool(item[name])]
            facility_match = len(set(preferred_facilities) & set(facilities)) / max(len(preferred_facilities), 1)
            score = weighted_score({"price": max(0, 1 - float(item.price_per_night) / max_price), "rating": float(item.rating) / 5, "type": 1 if not accommodation_type or item.accommodation_type == accommodation_type else .2, "facilities": facility_match, "constraints": 1}, ACCOMMODATION_WEIGHTS)
            rows.append({"accommodation_id": item.accommodation_id, "name": str(item["name"]), "type": str(item.get("accommodation_type", "hotel")), "destination": item.destination_name, "price_per_night": round(float(item.price_per_night)), "rating": float(item.rating), "recommendation_score": round(score, 4), "match_percentage": round(score * 100), "matched_features": facilities, "reason": "Within your budget and matches your accommodation preferences."})
        return sorted(rows, key=lambda row: row["recommendation_score"], reverse=True)[:top_n]
