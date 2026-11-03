from fastapi import APIRouter, HTTPException, Request
from app.api.schemas import AccommodationRequest, ActivityRequest, PreferenceRequest
from app.recommenders.user_profile import UserPreferenceProfile

router = APIRouter(prefix="/api/v1")

def service(request: Request): return request.app.state.models

def profile(payload: PreferenceRequest): return UserPreferenceProfile.from_dict(payload.model_dump())

@router.post("/profile")
def create_profile(payload: PreferenceRequest):
    item = profile(payload); return {"human_readable": item.human_readable(), "feature_vector": item.feature_vector()}

@router.post("/recommend/destinations")
def recommend_destinations(payload: PreferenceRequest, request: Request):
    results = service(request).destination.recommend(profile(payload), payload.top_n); return {"success": True, "count": len(results), "recommendations": results}

@router.post("/recommend/accommodations")
def recommend_accommodations(payload: AccommodationRequest, request: Request):
    results = service(request).accommodation.recommend(payload.destination_id, payload.max_price_per_night, payload.accommodation_type, payload.min_rating, payload.family_friendly, payload.accessibility_required, payload.preferred_facilities, payload.top_n); return {"success": True, "count": len(results), "recommendations": results}

@router.post("/recommend/activities")
def recommend_activities(payload: ActivityRequest, request: Request):
    results = service(request).activity.recommend(payload.destination_id, payload.interests, payload.preferred_activities, payload.remaining_budget, payload.available_hours, payload.family_friendly, payload.accessibility_required, payload.top_n); return {"success": True, "count": len(results), "recommendations": results}

@router.post("/recommend/full-trip")
def recommend_full_trip(payload: PreferenceRequest, request: Request): return service(request).full_trip.recommend(profile(payload), payload.top_n)

@router.get("/destinations")
def destinations(request: Request): return service(request).destination.data.to_dict(orient="records")

@router.get("/accommodations")
def accommodations(request: Request): return service(request).accommodation.data.to_dict(orient="records")

@router.get("/activities")
def activities(request: Request): return service(request).activity.data.to_dict(orient="records")

@router.get("/destinations/{destination_id}")
def destination(destination_id: str, request: Request):
    data = service(request).destination.data
    found = data[data.destination_id == destination_id]
    if found.empty: raise HTTPException(status_code=404, detail="Destination not found")
    return found.iloc[0].to_dict()
