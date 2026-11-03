from fastapi import FastAPI
from app.api.routes import router
from app.services.model_service import ModelService

app = FastAPI(title="TRAVEMLE Smart Tour Planner ML API", version="1.0.0", description="Content-Based Recommendation System using feature engineering, weighted ranking and cosine similarity.")
app.state.models = ModelService()
app.include_router(router)

@app.get("/")
def root(): return {"name": "TRAVEMLE ML API", "status": "running", "docs": "/docs"}

@app.get("/health")
def health(): return {"status": "healthy"}
