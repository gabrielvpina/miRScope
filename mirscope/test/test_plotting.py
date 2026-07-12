"""Tests for the UpSet plotter."""
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from mirscope.matrix import BooleanMatrixBuilder
from mirscope.plotting import UpSetPlotter, active_species, compute_intersections


def test_active_species_drops_unused():
    species = ["sp1", "sp2", "sp3"]
    # Intersections use sp1 and sp3 only; sp2 never appears.
    intersections = [(True, False, False), (True, False, True)]
    assert active_species(species, intersections) == ["sp1", "sp3"]


def test_active_species_keeps_order():
    species = ["a", "b", "c"]
    intersections = [(False, True, True)]
    assert active_species(species, intersections) == ["b", "c"]


def _matrix():
    clusters = {
        "SEED1": [
            [
                SeqRecord(Seq("AUGC"), id="hsa-1|Homo_sapiens", description=""),
                SeqRecord(Seq("AUGC"), id="mmu-1|Mus_musculus", description=""),
            ]
        ],
        "SEED2": [[SeqRecord(Seq("AUGC"), id="hsa-2|Homo_sapiens", description="")]],
    }
    return BooleanMatrixBuilder().from_clusters(clusters)


def test_plot_creates_png_file(tmp_path):
    output = tmp_path / "upset.png"
    UpSetPlotter().plot(_matrix(), str(output), "Test")
    assert output.exists()
    assert output.stat().st_size > 0


def _two_species_matrix():
    # Two intersections: {sp1,sp2} (size 1) and {sp1} (size 1).
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


def test_plot_top_n_limits_intersections(tmp_path):
    output = tmp_path / "topn.png"
    UpSetPlotter().plot(_two_species_matrix(), str(output), "Test", top_n=1)
    # Still produces a plot (with only the largest intersection kept).
    assert output.exists()


def test_plot_min_size_filters_out_everything(tmp_path):
    output = tmp_path / "minsize.png"
    # All intersections have size 1, so min_size=5 removes them all → no plot.
    UpSetPlotter().plot(_two_species_matrix(), str(output), "Test", min_size=5)
    assert not output.exists()


def test_compute_intersections_filters_and_sorts():
    grouped, shown, total = compute_intersections(_two_species_matrix(), min_degree=2)
    assert grouped is not None
    assert total == 1  # only the shared (degree 2) intersection survives
    assert set(shown) == {"Homo sapiens", "Mus musculus"}


def test_compute_intersections_returns_none_when_filtered_out():
    grouped, shown, total = compute_intersections(_two_species_matrix(), min_size=99)
    assert grouped is None
    assert shown == []


def test_build_figure_returns_figure_or_none():
    fig = UpSetPlotter().build_figure(_two_species_matrix(), "T")
    assert fig is not None
    empty = UpSetPlotter().build_figure(_two_species_matrix(), "T", min_size=99)
    assert empty is None


def test_plot_min_degree_keeps_shared_intersection(tmp_path):
    # _two_species_matrix has one shared (degree 2) and one single-species (degree 1).
    output = tmp_path / "deg.png"
    UpSetPlotter().plot(_two_species_matrix(), str(output), "Test", min_degree=2)
    assert output.exists()


def test_plot_min_degree_removes_species_specific_only(tmp_path):
    # A matrix with only single-species clusters -> min_degree=2 leaves nothing.
    clusters = {
        "S1": [[SeqRecord(Seq("AUGC"), id="a|Homo_sapiens", description="")]],
        "S2": [[SeqRecord(Seq("AUGC"), id="b|Mus_musculus", description="")]],
    }
    matrix = BooleanMatrixBuilder().from_clusters(clusters)
    output = tmp_path / "nodeg.png"
    UpSetPlotter().plot(matrix, str(output), "Test", min_degree=2)
    assert not output.exists()


def test_plot_skips_when_single_species(tmp_path):
    clusters = {
        "SEED1": [[SeqRecord(Seq("AUGC"), id="hsa-1|Homo_sapiens", description="")]]
    }
    matrix = BooleanMatrixBuilder().from_clusters(clusters)
    output = tmp_path / "single.png"
    UpSetPlotter().plot(matrix, str(output), "Test")
    # Only one species column -> no plot is produced.
    assert not output.exists()
