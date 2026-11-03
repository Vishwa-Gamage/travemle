from app.recommenders.accommodation_recommender import AccommodationRecommender

def test_accommodation_filters():
    result = AccommodationRecommender().recommend("DEST001", 30000, min_rating=4, top_n=5)
    assert all(item["price_per_night"] <= 30000 and item["rating"] >= 4 for item in result)
