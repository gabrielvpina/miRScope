"""Tests for the MiRNA model and U/T normalization."""
from mirscope.models import MiRNA


def test_normalize_uppercases_and_strips():
    assert MiRNA.normalize("  ugaga\n") == "UGAGA"


def test_normalize_converts_dna_to_rna():
    assert MiRNA.normalize("TGAGATTC") == "UGAGAUUC"


def test_sequence_is_normalized_on_creation():
    mirna = MiRNA("id1", "Homo sapiens", "tgagauuc", "mirna_Homo_sapiens.fasta")
    assert mirna.sequence == "UGAGAUUC"


def test_seed_is_nucleotides_two_to_eight():
    # sequence: A U G A G A U U C  -> seed = positions 2..8 = "UGAGAUU"
    mirna = MiRNA("id1", "Homo sapiens", "AUGAGAUUC", "f.fasta")
    assert mirna.seed == "UGAGAUU"
    assert len(mirna.seed) == 7


def test_rna_and_dna_share_the_same_seed():
    rna = MiRNA("a", "sp", "AUGAGAUUC", "f.fasta")
    dna = MiRNA("b", "sp", "ATGAGATTC", "f.fasta")
    assert rna.seed == dna.seed
