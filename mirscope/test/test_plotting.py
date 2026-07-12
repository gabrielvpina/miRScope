"""Tests for the UpSet plotter."""
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from mirscope.matrix import BooleanMatrixBuilder
from mirscope.plotting import UpSetPlotter


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


def test_plot_skips_when_single_species(tmp_path):
    clusters = {
        "SEED1": [[SeqRecord(Seq("AUGC"), id="hsa-1|Homo_sapiens", description="")]]
    }
    matrix = BooleanMatrixBuilder().from_clusters(clusters)
    output = tmp_path / "single.png"
    UpSetPlotter().plot(matrix, str(output), "Test")
    # Only one species column -> no plot is produced.
    assert not output.exists()
