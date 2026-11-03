from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
MODEL_DIR = ROOT_DIR / "saved_models"
DESTINATION_WEIGHTS = {"interest": .45, "budget": .20, "duration": .10, "climate": .08, "type": .07, "rating": .05, "popularity": .05}
ACCOMMODATION_WEIGHTS = {"price": .35, "rating": .25, "type": .15, "facilities": .15, "constraints": .10}
ACTIVITY_WEIGHTS = {"interest": .40, "category": .20, "budget": .15, "duration": .10, "rating": .10, "constraints": .05}
INTERESTS = ["nature", "adventure", "culture", "beach", "wildlife", "wellness", "nightlife", "shopping", "family", "luxury"]
