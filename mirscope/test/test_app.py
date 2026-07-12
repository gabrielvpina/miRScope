"""Tests for the app's pure helpers (no Streamlit required)."""
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from mirscope.app.data_io import load_matrix
from mirscope.app.plotly_upset import build_upset_figure
from mirscope.app.ui import records_to_table
from mirscope.matrix import BooleanMatrixBuilder
from mirscope.plotting import intersections_with_members


def _shared_matrix():
    # SEED1 cluster: Homo + Mus (shared). SEED2 cluster: Homo only.
    clusters = {
        "SEED1": [
            [
                SeqRecord(Seq("AUGC"), id="a|Homo_sapiens", description=""),
                SeqRecord(Seq("AUGC"), id="b|Mus_musculus", description=""),
            ]
        ],
        "SEED2": [[SeqRecord(Seq("AUGC"), id="c|Homo_sapiens", description="")]],
    }
    return BooleanMatrixBuilder().from_clusters(clusters)


def test_intersections_with_members_keeps_cluster_ids():
    records, total = intersections_with_members(_shared_matrix())
    assert total == 2
    # Largest first; each record carries its member cluster ids.
    assert all("clusters" in r and r["clusters"] for r in records)
    shared = [r for r in records if len(r["species"]) == 2]
    assert shared and shared[0]["clusters"] == ["SEED1_Clust_1"]


def test_intersections_with_members_min_degree():
    records, total = intersections_with_members(_shared_matrix(), min_degree=2)
    assert total == 1
    assert records[0]["species"] == ["Homo sapiens", "Mus musculus"]


def test_records_to_table_columns():
    records, _ = intersections_with_members(_shared_matrix())
    table = records_to_table(records)
    assert list(table.columns) == ["Species", "Degree", "Size", "Clusters"]


def test_build_upset_figure_returns_figure():
    records, _ = intersections_with_members(_shared_matrix())
    figure = build_upset_figure(records, list(_shared_matrix().columns))
    assert figure is not None
    assert len(figure.data) > 0


def test_build_upset_figure_empty_records():
    assert build_upset_figure([], ["Homo sapiens", "Mus musculus"]) is None


def test_load_matrix_csv_roundtrip():
    matrix = _shared_matrix().astype(int)
    out = load_matrix("m.csv", matrix.to_csv().encode())
    assert out.dtypes.unique().tolist() == [bool]
    assert out.shape[1] == 2
