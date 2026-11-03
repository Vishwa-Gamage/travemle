from app.recommenders.destination_recommender import DestinationRecommender
from app.recommenders.accommodation_recommender import AccommodationRecommender
from app.recommenders.activity_recommender import ActivityRecommender
from app.recommenders.full_trip_recommender import FullTripRecommender

class ModelService:
    def __init__(self):
        self.destination = DestinationRecommender(); self.accommodation = AccommodationRecommender(); self.activity = ActivityRecommender(); self.full_trip = FullTripRecommender()
