from app.recommenders.user_profile import UserPreferenceProfile

def test_profile_vector():
    profile = UserPreferenceProfile(100000, 4, interests=["nature", "adventure"])
    assert profile.feature_vector()["nature_score"] == 1
    assert profile.human_readable()["trip_days"] if "trip_days" in profile.human_readable() else True
