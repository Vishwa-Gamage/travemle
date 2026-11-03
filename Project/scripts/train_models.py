"""Persist lightweight feature configuration; recommenders rebuild automatically if absent."""
from pathlib import Path
import sys
import joblib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config.settings import MODEL_DIR, INTERESTS

if __name__ == "__main__":
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump({"interests": INTERESTS, "method": "content_based_weighted_cosine"}, MODEL_DIR / "feature_config.joblib")
    print(f"Saved feature configuration to {MODEL_DIR}")
