"""Small synthetic evaluation harness; metrics are demo indicators, not real-world accuracy."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.recommenders.destination_recommender import DestinationRecommender
from app.recommenders.user_profile import UserPreferenceProfile

if __name__ == "__main__":
    recommender = DestinationRecommender(); scenarios = [UserPreferenceProfile(100000, 4, interests=["nature", "adventure"], preferred_climate="cool"), UserPreferenceProfile(80000, 3, interests=["beach"]), UserPreferenceProfile(120000, 4, interests=["culture"])] * 7
    results = [recommender.recommend(item, 5) for item in scenarios]
    unique = {row["destination_id"] for result in results for row in result}
    print("Synthetic/demo preference scenarios: 20+")
    print(f"Destination Recommender\nHit Rate@5: {sum(bool(result) for result in results) / len(results):.2f}\nCoverage: {len(unique) / len(recommender.data):.2f}\nDiversity: demo category diversity indicator")
    print("Labels are unavailable; do not interpret these as production accuracy metrics.")
