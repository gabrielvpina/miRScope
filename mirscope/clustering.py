"""Cohesion-based clustering of aligned seed families."""
from __future__ import annotations

from typing import List

from Bio.SeqRecord import SeqRecord

from .logging_config import get_logger


def aligned_identity(seq1: str, seq2: str) -> float:
    """Return the base-to-base identity (percent) between two aligned sequences.

    Positions where both sequences hold a gap are ignored.
    """
    matches = 0
    effective_length = 0
    for base1, base2 in zip(seq1, seq2):
        if base1 == "-" and base2 == "-":
            continue
        if base1 == base2:
            matches += 1
        effective_length += 1
    return (matches / effective_length) * 100.0 if effective_length else 0.0


class CohesionClusterer:
    """Split an aligned seed family into complete-linkage cohesion clusters.

    A record joins an existing cluster only if its identity against **every**
    current member is at least ``cutoff`` percent; otherwise it seeds a new one.
    """

    def __init__(self, cutoff: float) -> None:
        self.cutoff = cutoff
        self.logger = get_logger("clustering")

    def cluster(self, alignment: List[SeqRecord]) -> List[List[SeqRecord]]:
        """Return the list of clusters for a single aligned family."""
        if not alignment:
            return []

        clusters: List[List[SeqRecord]] = []
        for record in alignment:
            sequence = str(record.seq).lower()
            placed = False
            for group in clusters:
                cohesive = all(
                    aligned_identity(str(member.seq).lower(), sequence) >= self.cutoff
                    for member in group
                )
                if cohesive:
                    group.append(record)
                    placed = True
                    break
            if not placed:
                clusters.append([record])
        return clusters
