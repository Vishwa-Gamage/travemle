from app.recommenders.destination_recommender import DestinationRecommender
from app.recommenders.user_profile import UserPreferenceProfile

def test_destination_top_n():
    result = DestinationRecommender().recommend(UserPreferenceProfile(100000, 4, ["nature", "adventure"]), 3)
    assert len(result) == 3
    assert result[0]["recommendation_score"] >= result[-1]["recommendation_score"]
