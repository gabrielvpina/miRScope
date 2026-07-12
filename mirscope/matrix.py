"""Construction of boolean presence/absence matrices (seed or cluster x species)."""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from .logging_config import get_logger


class BooleanMatrixBuilder:
    """Build boolean matrices where rows are seeds/clusters and columns species.

    Species columns are always emitted in sorted order so that outputs are
    deterministic across runs.
    """

    def __init__(self) -> None:
        self.logger = get_logger("matrix")

    def from_seed_species(self, seed_species: Dict[str, List[str]]) -> pd.DataFrame:
        """Build the matrix from a ``seed -> [species]`` mapping (macro mode)."""
        rows = []
        all_species = set()
        for seed, species_list in seed_species.items():
            species_set = set(species_list)
            all_species.update(species_set)
            if species_set:
                row = {"miRNA_ID": seed}
                for species in sorted(species_set):
                    row[species] = True
                rows.append(row)
        return self._finalize(rows, sorted(all_species))

    def from_clusters(
        self, clusters_by_seed: Dict[str, List[list]]
    ) -> pd.DataFrame:
        """Build the matrix from cohesion clusters (strict mode)."""
        rows = []
        all_species = set()
        for seed, clusters in clusters_by_seed.items():
            for index, cluster in enumerate(clusters, start=1):
                cluster_id = f"{seed}_Clust_{index}"
                species_set = set()
                for record in cluster:
                    parts = record.id.split("|")
                    if len(parts) > 1:
                        species_set.add(parts[1].replace("_", " "))
                all_species.update(species_set)
                if species_set:
                    row = {"miRNA_ID": cluster_id}
                    for species in sorted(species_set):
                        row[species] = True
                    rows.append(row)
        return self._finalize(rows, sorted(all_species))

    def _finalize(self, rows: List[dict], all_species: List[str]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()
        # Build a boolean matrix directly (columns already sorted) to keep the
        # result deterministic and avoid object-dtype fill warnings.
        ids = [row["miRNA_ID"] for row in rows]
        index = pd.Index(ids, name="miRNA_ID")
        df = pd.DataFrame(False, index=index, columns=all_species)
        for row in rows:
            row_id = row["miRNA_ID"]
            for species, present in row.items():
                if species != "miRNA_ID" and present:
                    df.at[row_id, species] = True
        self.logger.debug(
            "Built boolean matrix: %d rows x %d species.", len(df), len(all_species)
        )
        return df
