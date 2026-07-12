"""Data loading helpers for the Streamlit app (no Streamlit imports here)."""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd


def load_matrix(name: str, data: bytes) -> pd.DataFrame:
    """Load a boolean presence/absence matrix from raw bytes.

    Accepts ``.xlsx`` (as produced by the strict mode), ``.csv`` or ``.parquet``.
    The first column is treated as the row index (cluster/seed id).
    """
    suffix = Path(name).suffix.lower()
    buffer = io.BytesIO(data)
    if suffix in (".parquet", ".pq"):
        df = pd.read_parquet(buffer)
    elif suffix == ".csv":
        df = pd.read_csv(buffer, index_col=0)
    else:  # .xlsx / .xls
        df = pd.read_excel(buffer, sheet_name=0, index_col=0)
    return df.fillna(False).astype(bool)
