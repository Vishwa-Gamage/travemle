from pathlib import Path
from app.config.settings import ACTIVITY_WEIGHTS, DATA_DIR, INTERESTS
from app.services.data_loader import load_csv
from app.services.scoring import cosine_interest, weighted_score

class ActivityRecommender:
    def __init__(self, data_path: Path = DATA_DIR / "activities.csv"):
        self.data = load_csv(data_path, ["activity_id", "destination_id", "category", "cost", "duration_hours", "rating"])

    def recommend(self, destination_id: str, interests: list[str], preferred_activities: list[str], remaining_budget: float, available_hours: float = 8, family_friendly: bool = False, accessibility_required: bool = False, top_n: int = 5) -> list[dict]:
        subset = self.data[self.data.destination_id.astype(str).str.lower() == destination_id.lower()]
        if family_friendly: subset = subset[subset.family_friendly.astype(bool)]
        if accessibility_required: subset = subset[subset.accessible.astype(bool)]
        user_vector = [float(value.lower() in [x.lower() for x in interests]) for value in INTERESTS]
        rows = []
        for _, item in subset.iterrows():
            item_vector = [float(item.get(f"{value}_score", 0)) for value in INTERESTS]
            interest = cosine_interest(user_vector, item_vector)
            category_match = 1.0 if str(item.category).lower() in [x.lower() for x in preferred_activities] else .25
            budget = max(0, min(1, 1 - float(item.cost) / remaining_budget))
            duration = max(0, min(1, 1 - abs(float(item.duration_hours) - min(available_hours, 4)) / max(available_hours, 1)))
            score = weighted_score({"interest": interest, "category": category_match, "budget": budget, "duration": duration, "rating": float(item.rating) / 5, "constraints": 1}, ACTIVITY_WEIGHTS)
            rows.append({"activity_id": item.activity_id, "activity_name": item.activity_name, "category": item.category, "cost": round(float(item.cost)), "duration_hours": float(item.duration_hours), "rating": float(item.rating), "recommendation_score": round(score, 4), "match_percentage": round(score * 100), "matched_features": [item.category] if category_match > .5 else [], "reason": f"Recommended because it matches your {item.category.replace('_', ' ')} interests and fits your available time and budget."})
        result = sorted(rows, key=lambda row: row["recommendation_score"], reverse=True)
        # Pass 1: pick one per category (diversity)
        selected, categories = [], set()
        for row in result:
            if row["category"] not in categories:
                selected.append(row)
                categories.add(row["category"])
            if len(selected) == top_n:
                break
        # Pass 2: if we still have budget in top_n, add more activities (same category ok)
        if len(selected) < top_n:
            added_ids = {r["activity_id"] for r in selected}
            for row in result:
                if row["activity_id"] not in added_ids:
                    selected.append(row)
                    added_ids.add(row["activity_id"])
                if len(selected) == top_n:
                    break
        return selected
