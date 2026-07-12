"""Tabular result builders and Excel/FASTA writers."""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from .logging_config import get_logger
from .models import MiRNA

# ---------------------------------------------------------------------------
# DataFrame builders
# ---------------------------------------------------------------------------


def build_macro_dataframe(mirnas: List[MiRNA]) -> pd.DataFrame:
    """Build the detailed per-seed table used by the macro mode."""
    data = [
        {
            "Seed": mirna.seed,
            "Species": mirna.species,
            "Original_ID": mirna.identifier,
            "Sequence": mirna.sequence,
        }
        for mirna in mirnas
    ]
    df = pd.DataFrame(data)
    if not df.empty:
        df["Species_Count"] = df.groupby("Seed")["Species"].transform("nunique")
        df = df[["Seed", "Species_Count", "Species", "Original_ID", "Sequence"]]
        df = df.sort_values(by=["Seed", "Species"])
    return df


def build_cluster_dataframe(clusters_by_seed: Dict[str, List[list]]) -> pd.DataFrame:
    """Build the detailed per-cluster table used by the strict mode."""
    data = []
    for seed, clusters in clusters_by_seed.items():
        for index, cluster in enumerate(clusters, start=1):
            cluster_id = f"{seed}_Clust_{index}"
            for record in cluster:
                parts = record.id.split("|")
                original_id = parts[0]
                species = parts[1].replace("_", " ") if len(parts) > 1 else "Unknown"
                data.append(
                    {
                        "Seed": seed,
                        "Cluster_ID": cluster_id,
                        "Species": species,
                        "Original_ID": original_id,
                        "Aligned_Sequence": str(record.seq),
                    }
                )
    df = pd.DataFrame(data)
    if not df.empty:
        df["Species_Count"] = df.groupby("Cluster_ID")["Species"].transform("nunique")
        df = df[
            [
                "Seed",
                "Cluster_ID",
                "Species_Count",
                "Species",
                "Original_ID",
                "Aligned_Sequence",
            ]
        ]
    return df


def build_intersection_dataframe(boolean_df: pd.DataFrame) -> pd.DataFrame:
    """Turn a boolean cluster matrix into a human-readable intersection table."""
    if boolean_df.empty:
        return pd.DataFrame()

    species_columns = boolean_df.columns.tolist()
    rows = []
    for profile, group_df in boolean_df.groupby(species_columns):
        if not isinstance(profile, tuple):  # single-species edge case
            profile = (profile,)
        present = [species_columns[i] for i, flag in enumerate(profile) if flag]
        if present:
            members = group_df.index.tolist()
            rows.append(
                {
                    "Intersection (Species)": " + ".join(present),
                    "Total Clusters": len(members),
                    "Member Clusters (miRNAs)": ", ".join(members),
                }
            )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by="Total Clusters", ascending=False)
    return df


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


class ExcelExporter:
    """Write DataFrames to styled ``.xlsx`` files (auto-filter, zebra colors)."""

    def __init__(self) -> None:
        self.logger = get_logger("exporter")

    def save_grouped(
        self, df: pd.DataFrame, output_path: str, group_column: str
    ) -> None:
        """Write ``df`` with an auto-filter and alternating colors per group."""
        if df.empty:
            df.to_excel(output_path, index=False)
            self.logger.warning("Wrote empty sheet to '%s'.", output_path)
            return

        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet("Results")

            header_format = workbook.add_format(
                {"bold": True, "bg_color": "#D3D3D3", "border": 1}
            )
            odd_format = workbook.add_format(
                {"bg_color": "#FCE4D6", "border": 1, "border_color": "#E0E0E0"}
            )
            even_format = workbook.add_format(
                {"bg_color": "#FFFFFF", "border": 1, "border_color": "#E0E0E0"}
            )

            for col_num, col_name in enumerate(df.columns):
                worksheet.write(0, col_num, col_name, header_format)

            group_index = df.columns.get_loc(group_column)
            current_group = None
            use_odd = False

            for row_num, row_data in enumerate(df.values, start=1):
                group_value = row_data[group_index]
                if group_value != current_group:
                    use_odd = not use_odd
                    current_group = group_value
                row_format = odd_format if use_odd else even_format
                for col_num, cell_value in enumerate(row_data):
                    worksheet.write(row_num, col_num, cell_value, row_format)

            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
            worksheet.freeze_panes(1, 0)
            self._autofit_columns(worksheet, df)

        self.logger.info("Excel written to '%s'.", output_path)

    def save_formatted(
        self, df: pd.DataFrame, output_path: str, keep_index: bool = False
    ) -> None:
        """Write ``df`` with a styled header and auto-fitted columns."""
        if df.empty:
            df.to_excel(output_path, index=keep_index)
            self.logger.warning("Wrote empty sheet to '%s'.", output_path)
            return

        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=keep_index, sheet_name="Results")
            workbook = writer.book
            worksheet = writer.sheets["Results"]
            header_format = workbook.add_format(
                {"bold": True, "bg_color": "#D3D3D3", "border": 1}
            )
            worksheet.freeze_panes(1, 0)
            offset = 1 if keep_index else 0
            self._autofit_columns(worksheet, df, offset=offset, header_format=header_format)

        self.logger.info("Excel written to '%s'.", output_path)

    @staticmethod
    def _autofit_columns(worksheet, df, offset=0, header_format=None):
        for i, col in enumerate(df.columns):
            largest = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
            width = min(largest, 60)
            column_index = i + offset
            worksheet.set_column(column_index, column_index, width)
            if header_format is not None:
                worksheet.write(0, column_index, col, header_format)


class AlignmentWriter:
    """Write all MAFFT alignments to a single FASTA-like text file."""

    def __init__(self) -> None:
        self.logger = get_logger("exporter")

    def save(self, aligned_results: Dict[str, list], output_path: str) -> None:
        with open(output_path, "w") as handle:
            for seed, records in aligned_results.items():
                handle.write(f"\n# ================= SEED: {seed} =================\n")
                for record in records:
                    handle.write(f">{record.id}\n{str(record.seq)}\n")
        self.logger.info("Alignments written to '%s'.", output_path)
