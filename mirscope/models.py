"""Domain model for a single microRNA."""
from __future__ import annotations

from dataclasses import dataclass

from .config import SEED_END, SEED_START


@dataclass
class MiRNA:
    """A single mature microRNA sequence and its metadata.

    Sequences are normalised on creation: uppercased and converted from DNA to
    RNA alphabet (``T`` -> ``U``) so that RNA and DNA inputs group into the same
    seed family instead of being split apart.
    """

    identifier: str
    species: str
    sequence: str
    source_file: str

    def __post_init__(self) -> None:
        self.sequence = self.normalize(self.sequence)

    @staticmethod
    def normalize(sequence: str) -> str:
        """Uppercase, strip whitespace and convert DNA (T) to RNA (U)."""
        return sequence.strip().upper().replace("T", "U")

    @property
    def seed(self) -> str:
        """Return the seed region (nucleotides 2-8)."""
        return self.sequence[SEED_START:SEED_END]
