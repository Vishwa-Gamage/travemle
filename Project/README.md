# TRAVEMLE Smart Tour Planner ML Service

A standalone Python 3.11+ recommendation service for the **Personalised Smart Tour Planner (TRAVEMLE)**. It is intentionally independent of Django and exposes clean JSON over FastAPI.

This is a **Content-Based Recommendation System using feature engineering, weighted ranking and cosine similarity**. It is not a neural network or a claim of real-world predictive accuracy.

## Architecture

`Client frontend -> external Django backend -> TRAVEMLE ML REST API -> recommendation engine`

The service contains four modules:

1. User preference profiling: validates preferences and produces human-readable and numerical feature representations.
2. Destination recommendation: cosine interest similarity plus budget, duration, climate, type, rating, and popularity ranking.
3. Accommodation recommendation: destination and hard-constraint filtering plus weighted price, rating, type, facility, and constraint scoring.
4. Activity recommendation: destination filtering, interest/category matching, budget/time constraints, and category diversity.

`FullTripRecommender` composes these modules and provides a budget summary. Route optimization is deliberately separate and is not implemented at this stage.

## Demo data

`data/` contains generated development/demo catalogs: 40 destinations, 120 accommodations, 180 activities, and synthetic interactions. Values are illustrative and must not be represented as official tourism statistics or current verified prices. Replace these CSVs later with public data, PostgreSQL records, APIs, the client database, or real user-generated data without changing recommender interfaces.

The supplied review CSVs remain available as source material for future feature engineering; they are not used as the primary recommender input.

## Installation and running

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scripts\generate_sample_data.py
python run.py
```

The service runs at `http://127.0.0.1:8000`. Swagger UI is at `/docs`; OpenAPI JSON is at `/openapi.json`.

Useful checks:

```powershell
python -m pytest -q
python scripts\train_models.py
python scripts\evaluate_models.py
```

The recommender rebuilds in memory from CSV files if saved preprocessing artifacts are absent. `train_models.py` demonstrates Joblib persistence for feature configuration under `saved_models/`.

## API endpoints

- `GET /`, `GET /health`
- `POST /api/v1/profile`
- `POST /api/v1/recommend/destinations`
- `POST /api/v1/recommend/accommodations`
- `POST /api/v1/recommend/activities`
- `POST /api/v1/recommend/full-trip`
- `GET /api/v1/destinations`
- `GET /api/v1/accommodations`
- `GET /api/v1/activities`
- `GET /api/v1/destinations/{destination_id}`

Example destination request:

```json
{
  "budget": 100000,
  "trip_days": 4,
  "interests": ["nature", "adventure", "culture"],
  "preferred_activities": ["hiking", "sightseeing"],
  "travel_type": "couple",
  "preferred_climate": "cool",
  "destination_type": "mountain",
  "top_n": 5
}
```

Responses contain `recommendation_score`, `match_percentage`, matched interests/features, and a short reason. Full-trip responses also contain alternative destinations, ranked stays, ranked activities, and estimated/remaining budget.

## Evaluation and notebooks

`python scripts/evaluate_models.py` runs 21 synthetic preference scenarios and reports demo Hit Rate@K, coverage, and a diversity indicator. Precision@K and Recall@K require real relevance labels, so no real-world accuracy is claimed. The four notebooks demonstrate data exploration, destination cosine ranking across five profiles, accommodation ranking, and activity ranking.

Example scenarios supported by the same API are beach, cultural, adventure, family, budget, and luxury profiles. Results vary because interests, constraints, cost compatibility, and catalog features are scored directly.

## Django integration

Django remains responsible for authentication, users, trip records, application business logic, and frontend communication. This service remains responsible for preference transformation, recommendation ranking, and explanations.

```python
import requests

payload = {
    "budget": 100000,
    "trip_days": 4,
    "interests": ["nature", "adventure"],
    "preferred_climate": "cool"
}
response = requests.post(
    "http://127.0.0.1:8000/api/v1/recommend/destinations",
    json=payload,
    timeout=10,
)
data = response.json()
```

In production, place the ML service behind network authentication and request logging. Do not move Django user authentication into this service.

## Future improvements and limitations

Current ranking is content-based because historical interaction volume is insufficient. Once enough real behavior is available, add a user-item matrix, matrix factorization, implicit-feedback ranking, or a hybrid content/collaborative model. Add real relevance labels, model monitoring, catalog freshness, geographic distance features, itinerary optimization, and production data access as separate layers.

The generated catalog is deterministic for reproducible tests. Verify availability, prices, accessibility, and safety with trusted live sources before using recommendations for an actual trip.

## Structure

```text
app/                 FastAPI, schemas, services, and recommenders
data/                Generated demo catalogs and supplied review CSVs
notebooks/           Four university-project demonstrations
scripts/             Data generation, persistence, and evaluation
saved_models/        Optional Joblib artifacts
tests/               Pytest unit and API tests
run.py               Local Uvicorn entry point
requirements.txt     Compatible pinned dependencies
```
