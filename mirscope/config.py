"""Central configuration values and small config dataclasses for MIRSCOPE."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


def packaged_data_dir() -> Path:
    """Return the reference FASTA database bundled inside the package.

    Resolved relative to this file, so it always points at the shipped ``data/``
    directory regardless of the working directory or install type (editable or
    wheel).
    """
    return Path(__file__).resolve().parent / "data"


# ---------------------------------------------------------------------------
# Seed definition
# ---------------------------------------------------------------------------
# The seed region corresponds to nucleotides 2-8 of the mature miRNA.
# On a 0-indexed sequence that is the slice [SEED_START:SEED_END].
SEED_START: int = 1
SEED_END: int = 8

# Minimum sequence length (in nucleotides) required to keep a miRNA.
MIN_SEQUENCE_LENGTH: int = 8

# Default base-to-base identity cutoff (percent) used by the strict mode.
DEFAULT_CUTOFF: float = 85.0

# FASTA file extensions recognised by the loader.
FASTA_EXTENSIONS: Tuple[str, ...] = ("*.fasta", "*.fa")


@dataclass(frozen=True)
class MafftConfig:
    """Options used when invoking the external MAFFT aligner."""

    executable: str = "mafft"
    # High-accuracy preset kept identical to the original implementation.
    extra_args: Tuple[str, ...] = ("--nuc", "--genafpair", "--maxiterate", "1000")


@dataclass(frozen=True)
class MacroOutputs:
    """Output file names produced by the macro (broad conservation) mode."""

    excel_detailed: str = "output_mode1_macro_detailed.xlsx"
    matrix_excel: str = "output_mode1_matrix_upset.xlsx"
    upset_plot: str = "results_mode1_macro.png"


@dataclass(frozen=True)
class StrictOutputs:
    """Output file names produced by the strict (orthology by cohesion) mode."""

    alignments_fasta: str = "output_mode2_alignments.fasta"
    clusters_excel: str = "output_mode2_clusters_detailed.xlsx"
    matrix_excel: str = "output_mode2_matrix_upset.xlsx"
    intersections_excel: str = "output_mode2_intersection_groups.xlsx"
    upset_plot: str = "output_mode2_strict_upset.png"
