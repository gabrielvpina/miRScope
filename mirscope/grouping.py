"""Grouping of miRNAs by their seed region."""
from __future__ import annotations

from typing import Dict, List

from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from .logging_config import get_logger
from .models import MiRNA


class SeedGrouper:
    """Group miRNAs into seed families and prepare them for alignment."""

    def __init__(self) -> None:
        self.logger = get_logger("grouping")

    def group_species_by_seed(self, mirnas: List[MiRNA]) -> Dict[str, List[str]]:
        """Map each seed to the sorted list of species carrying it."""
        groups: Dict[str, set] = {}
        for mirna in mirnas:
            groups.setdefault(mirna.seed, set()).add(mirna.species)

        result = {seed: sorted(species) for seed, species in groups.items()}
        self.logger.info("Identified %d seed family(ies).", len(result))
        return result

    def group_records_by_seed(self, mirnas: List[MiRNA]) -> Dict[str, List[dict]]:
        """Map each seed to the raw records (id, species, sequence) it contains."""
        groups: Dict[str, List[dict]] = {}
        for mirna in mirnas:
            groups.setdefault(mirna.seed, []).append(
                {
                    "identifier": mirna.identifier,
                    "species": mirna.species,
                    "sequence": mirna.sequence,
                }
            )
        return groups

    def prepare_alignment_records(
        self, seed_groups: Dict[str, List[dict]]
    ) -> Dict[str, List[SeqRecord]]:
        """Convert grouped records into Biopython ``SeqRecord`` objects.

        The record id encodes both the original id and the species,
        ``<id>|<Genus_species>``, so downstream steps can recover the species.
        """
        prepared: Dict[str, List[SeqRecord]] = {}
        for seed, members in seed_groups.items():
            records = []
            for member in members:
                species_token = member["species"].replace(" ", "_")
                composite_id = f"{member['identifier']}|{species_token}"
                records.append(
                    SeqRecord(Seq(member["sequence"]), id=composite_id, description="")
                )
            prepared[seed] = records
        return prepared
