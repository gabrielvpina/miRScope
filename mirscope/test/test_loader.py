"""Tests for FastaLoader, including SeqIO-based multi-line parsing."""
from mirscope.loader import FastaLoader


def test_extract_species_from_convention():
    assert FastaLoader.extract_species("mirna_Homo_sapiens.fasta") == "Homo sapiens"
    assert FastaLoader.extract_species("mirna_Mus_musculus.fa") == "Mus musculus"


def test_extract_species_fallback_when_no_convention():
    assert FastaLoader.extract_species("random.fasta") == "random"


def test_load_reads_sequences_and_species(tmp_path):
    fasta = tmp_path / "mirna_Homo_sapiens.fasta"
    fasta.write_text(">hsa-miR1\nUGAGAUUCUUGA\n>hsa-miR2\nUUCCACAGCUUU\n")

    mirnas, species = FastaLoader().load(str(tmp_path))

    assert len(mirnas) == 2
    assert species == ["Homo sapiens"]
    assert {m.identifier for m in mirnas} == {"hsa-miR1", "hsa-miR2"}


def test_load_handles_multiline_sequences(tmp_path):
    # A wrapped sequence would be truncated by the old manual parser.
    fasta = tmp_path / "mirna_Test_species.fasta"
    fasta.write_text(">seq1\nUGAGAUUC\nUUGAUGAU\nGCUGCAU\n")

    mirnas, _ = FastaLoader().load(str(tmp_path))

    assert len(mirnas) == 1
    assert mirnas[0].sequence == "UGAGAUUCUUGAUGAUGCUGCAU"


def test_load_skips_sequences_below_minimum_length(tmp_path):
    fasta = tmp_path / "mirna_Short_one.fasta"
    fasta.write_text(">ok\nUGAGAUUC\n>tooshort\nUGA\n")

    mirnas, _ = FastaLoader(min_length=8).load(str(tmp_path))

    assert [m.identifier for m in mirnas] == ["ok"]


def test_load_returns_empty_when_no_files(tmp_path):
    mirnas, species = FastaLoader().load(str(tmp_path))
    assert mirnas == []
    assert species == []
