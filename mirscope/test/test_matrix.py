"""Tests for BooleanMatrixBuilder."""
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from mirscope.matrix import BooleanMatrixBuilder


def test_from_seed_species_builds_sorted_boolean_matrix():
    seed_species = {
        "SEEDAAA": ["Mus musculus", "Homo sapiens"],
        "SEEDBBB": ["Homo sapiens"],
    }
    df = BooleanMatrixBuilder().from_seed_species(seed_species)

    # Columns are sorted deterministically.
    assert list(df.columns) == ["Homo sapiens", "Mus musculus"]
    assert bool(df.loc["SEEDAAA", "Mus musculus"]) is True
    assert bool(df.loc["SEEDBBB", "Mus musculus"]) is False
    assert df.dtypes.unique().tolist() == [bool]


def test_from_clusters_parses_species_from_record_id():
    cluster = [
        SeqRecord(Seq("AUGC"), id="hsa-1|Homo_sapiens", description=""),
        SeqRecord(Seq("AUGC"), id="mmu-1|Mus_musculus", description=""),
    ]
    df = BooleanMatrixBuilder().from_clusters({"SEED": [cluster]})

    assert list(df.columns) == ["Homo sapiens", "Mus musculus"]
    assert df.index.tolist() == ["SEED_Clust_1"]
    assert bool(df.loc["SEED_Clust_1", "Homo sapiens"]) is True


def test_empty_input_returns_empty_dataframe():
    assert BooleanMatrixBuilder().from_seed_species({}).empty
