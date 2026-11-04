"""FASTA writer for the strict-mode MAFFT alignments."""
from __future__ import annotations

from typing import Dict

from .logging_config import get_logger


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
