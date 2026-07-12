"""Loading and parsing of FASTA files into :class:`MiRNA` objects."""
from __future__ import annotations

import glob
import os
from typing import List, Optional, Sequence, Tuple

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

    def _collect_files(
        self, folder: Optional[str], input_files: Optional[Sequence[str]]
    ) -> List[str]:
        """Gather FASTA paths from the reference folder plus explicit inputs."""
        collected: List[str] = []

        if folder:
            folder_files = self._list_files(folder)
            if folder_files:
                self.logger.info(
                    "Reference folder '%s': %d FASTA file(s).", folder, len(folder_files)
                )
            else:
                self.logger.warning(
                    "No FASTA files found in reference folder '%s'.", folder
                )
            collected.extend(folder_files)

        for path in input_files or []:
            if os.path.isfile(path):
                self.logger.info("Input file added to analysis: '%s'.", path)
                collected.append(path)
            else:
                self.logger.error("Input file not found (skipped): '%s'.", path)

        # De-duplicate by absolute path so an input already in the folder is counted once.
        return sorted({os.path.abspath(path) for path in collected})

    def load(
        self,
        folder: Optional[str] = None,
        input_files: Optional[Sequence[str]] = None,
    ) -> Tuple[List[MiRNA], List[str]]:
        """Return ``(mirnas, species)`` parsed from the reference folder and inputs.

        ``folder`` is the reference database (e.g. ``data/``); ``input_files`` are
        extra user FASTA files added to the same analysis.
        """
        files = self._collect_files(folder, input_files)
        if not files:
            self.logger.error(
                "No FASTA files to load (folder=%r, input=%r).", folder, input_files
            )
            return [], []

        self.logger.info("Loading %d FASTA file(s)...", len(files))

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
