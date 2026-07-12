"""Loading and parsing of FASTA files into :class:`MiRNA` objects."""
from __future__ import annotations

import glob
import os
from typing import List, Tuple

from Bio import SeqIO

from .config import FASTA_EXTENSIONS, MIN_SEQUENCE_LENGTH
from .logging_config import get_logger
from .models import MiRNA


class FastaLoader:
    """Load every FASTA file in a folder and build the miRNA database.

    One file is expected per species, named with the ``mirna_Genus_species``
    convention (e.g. ``mirna_Homo_sapiens.fasta``). Parsing is delegated to
    Biopython's :func:`Bio.SeqIO.parse`, which correctly handles multi-line
    (wrapped) sequences.
    """

    def __init__(
        self,
        extensions: Tuple[str, ...] = FASTA_EXTENSIONS,
        min_length: int = MIN_SEQUENCE_LENGTH,
    ) -> None:
        self.extensions = extensions
        self.min_length = min_length
        self.logger = get_logger("loader")

    @staticmethod
    def extract_species(filename: str) -> str:
        """Derive the species name from a FASTA file name.

        ``mirna_Homo_sapiens.fasta`` -> ``Homo sapiens``. If the file does not
        follow the convention, the bare file stem is returned as a fallback.
        """
        stem = os.path.splitext(filename)[0]
        parts = stem.split("_")
        if len(parts) >= 3 and parts[0].lower() == "mirna":
            return " ".join(parts[1:])
        return stem

    def _list_files(self, folder: str) -> List[str]:
        files: List[str] = []
        for extension in self.extensions:
            files.extend(glob.glob(os.path.join(folder, extension)))
        return sorted(set(files))

    def load(self, folder: str) -> Tuple[List[MiRNA], List[str]]:
        """Return ``(mirnas, species)`` parsed from every FASTA file in ``folder``."""
        files = self._list_files(folder)
        if not files:
            self.logger.error("No FASTA files found in folder '%s'.", folder)
            return [], []

        self.logger.info("Found %d FASTA file(s) in '%s'.", len(files), folder)

        database: List[MiRNA] = []
        species_found = set()
        skipped_short = 0

        for path in files:
            filename = os.path.basename(path)
            species = self.extract_species(filename)
            species_found.add(species)

            loaded = 0
            for record in SeqIO.parse(path, "fasta"):
                sequence = str(record.seq)
                if len(sequence) < self.min_length:
                    skipped_short += 1
                    continue
                database.append(MiRNA(record.id, species, sequence, filename))
                loaded += 1

            self.logger.debug(
                "Parsed %d sequence(s) for species '%s' (%s).", loaded, species, filename
            )

        if skipped_short:
            self.logger.warning(
                "Skipped %d sequence(s) shorter than %d nt.", skipped_short, self.min_length
            )

        species_list = sorted(species_found)
        self.logger.info(
            "Loaded %d sequences from %d species.", len(database), len(species_list)
        )
        return database, species_list
