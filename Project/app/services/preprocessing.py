from typing import Iterable
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


def normalize_text(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_")


def as_bool(value: object) -> bool:
    if isinstance(value, bool): return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def numeric_frame(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0)
    return result


def minmax(values: Iterable[float]) -> np.ndarray:
    array = np.asarray(list(values), dtype=float).reshape(-1, 1)
    if len(array) == 0: return np.array([])
    return MinMaxScaler().fit_transform(array).ravel()


def clip_score(value: float) -> float:
    return float(max(0.0, min(1.0, value)))
