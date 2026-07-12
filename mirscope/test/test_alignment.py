"""Tests for MafftAligner.

The real MAFFT invocation is exercised only when the executable is available;
otherwise those tests are skipped so the suite stays runnable everywhere.
"""
import pytest
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from mirscope.alignment import MafftAligner


def _record(identifier, sequence):
    return SeqRecord(Seq(sequence), id=identifier, description="")


def test_single_record_is_returned_unchanged():
    aligner = MafftAligner()
    records = [_record("a", "AUGCAUGC")]
    assert aligner.align(records, "UGCAUGC") == records


def test_is_available_returns_bool():
    assert isinstance(MafftAligner().is_available(), bool)


def test_failed_alignment_is_recorded():
    # Point the aligner at a non-existent executable to force a failure.
    from mirscope.config import MafftConfig

    aligner = MafftAligner(MafftConfig(executable="mafft_does_not_exist_xyz"))
    records = [_record("a", "AUGCAUGC"), _record("b", "AUGCAUGG")]
    result = aligner.align(records, "UGCAUGC")
    assert result is None
    assert aligner.failed_seeds == ["UGCAUGC"]


@pytest.mark.skipif(
    not MafftAligner().is_available(), reason="MAFFT executable not available"
)
def test_real_alignment_strips_anchors():
    aligner = MafftAligner()
    records = [_record("a", "AUGCAUGCAU"), _record("b", "AUGCAUGCAU")]
    result = aligner.align(records, "UGCAUGC")
    assert result is not None
    ids = [rec.id for rec in result]
    assert ids == ["a", "b"]
    assert all("anchor" not in rec.id.lower() for rec in result)
