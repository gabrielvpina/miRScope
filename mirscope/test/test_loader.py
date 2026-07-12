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


def test_load_combines_reference_folder_and_input_file(tmp_path):
    reference = tmp_path / "ref"
    reference.mkdir()
    (reference / "mirna_Homo_sapiens.fasta").write_text(">hsa-1\nUGAGAUUCUUGA\n")

    user_input = tmp_path / "mirna_My_species.fasta"
    user_input.write_text(">my-1\nUUCCACAGCUUU\n")

    mirnas, species = FastaLoader().load(str(reference), [str(user_input)])

    assert species == ["Homo sapiens", "My species"]
    assert len(mirnas) == 2


def test_load_input_only_without_folder(tmp_path):
    user_input = tmp_path / "mirna_My_species.fasta"
    user_input.write_text(">my-1\nUUCCACAGCUUU\n")

    mirnas, species = FastaLoader().load(None, [str(user_input)])

    assert species == ["My species"]
    assert len(mirnas) == 1


def test_load_skips_missing_input_file(tmp_path):
    reference = tmp_path / "ref"
    reference.mkdir()
    (reference / "mirna_Homo_sapiens.fasta").write_text(">hsa-1\nUGAGAUUCUUGA\n")

    mirnas, species = FastaLoader().load(str(reference), [str(tmp_path / "missing.fasta")])

    assert species == ["Homo sapiens"]
    assert len(mirnas) == 1


def test_load_deduplicates_input_already_in_folder(tmp_path):
    reference = tmp_path / "ref"
    reference.mkdir()
    shared = reference / "mirna_Homo_sapiens.fasta"
    shared.write_text(">hsa-1\nUGAGAUUCUUGA\n")

    mirnas, _ = FastaLoader().load(str(reference), [str(shared)])

    # The same file passed both ways must be counted only once.
    assert len(mirnas) == 1
