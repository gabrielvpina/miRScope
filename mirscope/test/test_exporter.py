"""Tests for the alignment FASTA writer."""
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from mirscope.exporter import AlignmentWriter


def test_alignment_writer_saves_fasta(tmp_path):
    records = [SeqRecord(Seq("AUGC"), id="hsa-1|Homo_sapiens", description="")]
    output = tmp_path / "aln.fasta"
    AlignmentWriter().save({"SEED": records}, str(output))
    content = output.read_text()
    assert "SEED: SEED" in content
    assert ">hsa-1|Homo_sapiens" in content
