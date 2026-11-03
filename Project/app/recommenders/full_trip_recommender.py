from .user_profile import UserPreferenceProfile
from .destination_recommender import DestinationRecommender
from .accommodation_recommender import AccommodationRecommender
from .activity_recommender import ActivityRecommender

class FullTripRecommender:
    def __init__(self):
        self.destinations = DestinationRecommender(); self.accommodations = AccommodationRecommender(); self.activities = ActivityRecommender()

    def recommend(self, profile: UserPreferenceProfile, top_n: int = 5) -> dict:
        destinations = self.destinations.recommend(profile, top_n)
        chosen = destinations[0]

        # Use 85% of daily budget for accommodation (was 55% — too restrictive)
        daily_budget = profile.budget / max(profile.trip_days, 1)
        max_night = profile.max_accommodation_price_per_night or daily_budget * 0.85

        dest_id = chosen["destination_id"]
        stays = self.accommodations.recommend(
            dest_id, max_night, profile.accommodation_type,
            profile.min_hotel_rating, profile.family_friendly,
            profile.accessibility_required, top_n=top_n
        )

        # Fallback 1: if no stays found (price too low), relax price constraint to full daily budget
        if not stays:
            stays = self.accommodations.recommend(
                dest_id, daily_budget, None, 0,
                profile.family_friendly, profile.accessibility_required,
                top_n=top_n
            )

        # Fallback 2: if still no stays, ignore price limit to always provide an accommodation
        if not stays:
            stays = self.accommodations.recommend(
                dest_id, 1000000.0, None, 0,
                False, False, top_n=top_n
            )

        # Fallback 3: if destination has no records in CSV, pick lowest priced from entire dataset
        if not stays:
            cheapest = self.accommodations.data.sort_values(by="price_per_night").head(top_n)
            stays = [
                {
                    "accommodation_id": str(r["accommodation_id"]),
                    "name": str(r["name"]),
                    "type": str(r.get("accommodation_type", "hotel")),
                    "destination": str(r.get("destination_name", chosen.get("destination_name", "Sri Lanka"))),
                    "price_per_night": round(float(r["price_per_night"])),
                    "rating": float(r.get("rating", 4.0)),
                    "recommendation_score": 0.8,
                    "match_percentage": 80,
                    "matched_features": ["wifi", "breakfast"],
                    "reason": "Best value accommodation for your stay."
                }
                for _, r in cheapest.iterrows()
            ]

        activity_budget = profile.activity_budget or max(profile.budget * .5, 25000.0)
        activities = self.activities.recommend(
            dest_id, profile.interests, profile.preferred_activities,
            activity_budget, profile.trip_days * 12,
            profile.family_friendly, profile.accessibility_required, top_n
        )

        accommodation_cost = (stays[0]["price_per_night"] * profile.trip_days) if stays else 0
        activity_cost = sum(item["cost"] for item in activities)
        general_cost = round(profile.budget * .2)
        estimated = accommodation_cost + activity_cost + general_cost

        return {
            "user_profile": profile.to_dict(),
            "recommended_destination": chosen,
            "alternative_destinations": destinations[1:],
            "recommended_accommodations": stays,
            "recommended_activities": activities,
            "budget_summary": {
                "total_budget": profile.budget,
                "estimated_accommodation_cost": accommodation_cost,
                "estimated_activity_cost": activity_cost,
                "estimated_general_cost": general_cost,
                "estimated_total": estimated,
                "remaining_budget": profile.budget - estimated,
            },
        }
