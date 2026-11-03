from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
PAYLOAD = {"budget": 100000, "trip_days": 4, "interests": ["nature", "adventure", "culture"], "preferred_activities": ["hiking", "sightseeing"], "travel_type": "couple", "preferred_climate": "cool", "destination_type": "mountain", "top_n": 5}

def test_health(): assert client.get("/health").status_code == 200

def test_validation(): assert client.post("/api/v1/recommend/destinations", json={"budget": -1, "trip_days": 0}).status_code == 422

def test_endpoints():
    assert client.post("/api/v1/recommend/destinations", json=PAYLOAD).json()["count"] == 5
    assert client.post("/api/v1/recommend/full-trip", json=PAYLOAD).status_code == 200
