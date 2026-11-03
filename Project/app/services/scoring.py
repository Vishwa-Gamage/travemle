from typing import Iterable
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .preprocessing import clip_score


def cosine_interest(user_values: Iterable[float], item_values: Iterable[float]) -> float:
    left, right = np.asarray(list(user_values), dtype=float), np.asarray(list(item_values), dtype=float)
    if not left.any() or not right.any(): return 0.0
    return clip_score(float(cosine_similarity([left], [right])[0][0]))


def weighted_score(parts: dict[str, float], weights: dict[str, float]) -> float:
    total = sum(weights.get(key, 0) * clip_score(value) for key, value in parts.items())
    denominator = sum(weights.get(key, 0) for key in parts)
    return clip_score(total / denominator) if denominator else 0.0
