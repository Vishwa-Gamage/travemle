from app.recommenders.activity_recommender import ActivityRecommender

def test_activity_recommendations():
    result = ActivityRecommender().recommend("DEST001", ["nature"], ["hiking"], 25000, top_n=4)
    assert 0 < len(result) <= 4
    assert all("recommendation_score" in item for item in result)
