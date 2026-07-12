"""Tests for DataFrame builders and Excel/FASTA writers."""
import pandas as pd
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from mirscope.exporter import (
    AlignmentWriter,
    ExcelExporter,
    build_cluster_dataframe,
    build_intersection_dataframe,
    build_macro_dataframe,
)
from mirscope.matrix import BooleanMatrixBuilder
from mirscope.models import MiRNA


def test_build_macro_dataframe_columns_and_count():
    mirnas = [
        MiRNA("a", "Homo sapiens", "AUGAGAUUC", "f.fasta"),
        MiRNA("b", "Mus musculus", "AUGAGAUUC", "f.fasta"),
    ]
    df = build_macro_dataframe(mirnas)
    assert list(df.columns) == ["Seed", "Species_Count", "Species", "Original_ID", "Sequence"]
    assert df["Species_Count"].iloc[0] == 2


def test_build_cluster_dataframe():
    cluster = [SeqRecord(Seq("AUGC"), id="hsa-1|Homo_sapiens", description="")]
    df = build_cluster_dataframe({"SEED": [cluster]})
    assert df["Cluster_ID"].iloc[0] == "SEED_Clust_1"
    assert df["Species"].iloc[0] == "Homo sapiens"


def test_build_intersection_dataframe():
    cluster_a = [
        SeqRecord(Seq("AUGC"), id="hsa-1|Homo_sapiens", description=""),
        SeqRecord(Seq("AUGC"), id="mmu-1|Mus_musculus", description=""),
    ]
    matrix = BooleanMatrixBuilder().from_clusters({"SEED": [cluster_a]})
    df = build_intersection_dataframe(matrix)
    assert df["Intersection (Species)"].iloc[0] == "Homo sapiens + Mus musculus"
    assert df["Total Clusters"].iloc[0] == 1


def test_excel_exporter_save_grouped_creates_file(tmp_path):
    df = pd.DataFrame(
        {"Seed": ["S1", "S1", "S2"], "Species": ["a", "b", "c"], "Value": [1, 2, 3]}
    )
    output = tmp_path / "out.xlsx"
    ExcelExporter().save_grouped(df, str(output), group_column="Seed")
    assert output.exists()
    reloaded = pd.read_excel(output)
    assert len(reloaded) == 3


def test_excel_exporter_save_formatted_creates_file(tmp_path):
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    output = tmp_path / "fmt.xlsx"
    ExcelExporter().save_formatted(df, str(output))
    assert output.exists()


def test_alignment_writer_saves_fasta(tmp_path):
    records = [SeqRecord(Seq("AUGC"), id="hsa-1|Homo_sapiens", description="")]
    output = tmp_path / "aln.fasta"
    AlignmentWriter().save({"SEED": records}, str(output))
    content = output.read_text()
    assert "SEED: SEED" in content
    assert ">hsa-1|Homo_sapiens" in content
