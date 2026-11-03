from app.config.settings import INTERESTS


def validate_interests(interests: list[str]) -> list[str]:
    return [item.lower().strip() for item in interests if item.lower().strip() in INTERESTS]
