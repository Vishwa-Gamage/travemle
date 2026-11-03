from pathlib import Path
from typing import Iterable
import pandas as pd


def load_csv(path: Path, required_columns: Iterable[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required catalog not found: {path}")
    frame = pd.read_csv(path)
    missing = set(required_columns) - set(frame.columns)
    if missing:
        raise ValueError(f"Catalog {path.name} is missing columns: {sorted(missing)}")
    if frame.duplicated().any():
        frame = frame.drop_duplicates().reset_index(drop=True)
    return frame
