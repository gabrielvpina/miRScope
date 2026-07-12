"""Tests for SeedGrouper."""
from mirscope.grouping import SeedGrouper
from mirscope.models import MiRNA


def _mirna(identifier, species, sequence):
    return MiRNA(identifier, species, sequence, "f.fasta")


def test_group_species_by_seed_deduplicates_and_sorts():
    mirnas = [
        _mirna("a", "Zebra species", "AUGAGAUUC"),
        _mirna("b", "Alpha species", "AUGAGAUUC"),
        _mirna("c", "Alpha species", "AUGAGAUUC"),  # duplicate species
    ]
    groups = SeedGrouper().group_species_by_seed(mirnas)
    seed = "UGAGAUU"
    assert groups[seed] == ["Alpha species", "Zebra species"]


def test_group_records_by_seed_keeps_all_members():
    mirnas = [
        _mirna("a", "sp1", "AUGAGAUUC"),
        _mirna("b", "sp2", "AUGAGAUUC"),
    ]
    groups = SeedGrouper().group_records_by_seed(mirnas)
    assert len(groups["UGAGAUU"]) == 2


def test_prepare_alignment_records_builds_composite_id():
    grouper = SeedGrouper()
    raw = grouper.group_records_by_seed([_mirna("hsa-1", "Homo sapiens", "AUGAGAUUC")])
    prepared = grouper.prepare_alignment_records(raw)
    record = prepared["UGAGAUU"][0]
    assert record.id == "hsa-1|Homo_sapiens"
