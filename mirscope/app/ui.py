"""Pure UI helpers for the app (no Streamlit imports, so they stay testable)."""
from __future__ import annotations

from typing import Sequence

import pandas as pd


def records_to_table(records: Sequence[dict]) -> pd.DataFrame:
    """Turn intersection records into a readable, downloadable table."""
    rows = [
        {
            "Species": " + ".join(record["species"]),
            "Degree": len(record["species"]),
            "Size": record["size"],
            "Clusters": ", ".join(str(cluster) for cluster in record["clusters"]),
        }
        for record in records
    ]
    table = pd.DataFrame(rows)
    if not table.empty:
        table = table.sort_values("Size", ascending=False).reset_index(drop=True)
    return table
