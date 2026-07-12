"""Tests for MafftAligner.

The real MAFFT invocation is exercised only when the executable is available;
otherwise those tests are skipped so the suite stays runnable everywhere.
"""
import pytest
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

import mirscope.alignment as alignment_module
from mirscope.alignment import MafftAligner, resolve_mafft


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


def test_resolve_mafft_prefers_env_var(tmp_path, monkeypatch):
    fake = tmp_path / "my_mafft"
    fake.write_text("#!/bin/sh\n")
    monkeypatch.setenv("MIRSCOPE_MAFFT", str(fake))
    assert resolve_mafft("mafft") == str(fake)


def test_resolve_mafft_falls_back_to_pixi_env(tmp_path, monkeypatch):
    env_bin = tmp_path / ".pixi" / "envs" / "default" / "bin"
    env_bin.mkdir(parents=True)
    mafft_bin = env_bin / "mafft"
    mafft_bin.write_text("x")

    monkeypatch.delenv("MIRSCOPE_MAFFT", raising=False)
    monkeypatch.setattr(alignment_module.shutil, "which", lambda name: None)
    monkeypatch.setattr("mirscope.bootstrap.pixi_env_bin_dirs", lambda: [env_bin])

    assert resolve_mafft("mafft") == str(mafft_bin)


def test_resolve_mafft_returns_none_when_absent(monkeypatch):
    monkeypatch.delenv("MIRSCOPE_MAFFT", raising=False)
    monkeypatch.setattr(alignment_module.shutil, "which", lambda name: None)
    monkeypatch.setattr("mirscope.bootstrap.pixi_env_bin_dirs", lambda: [])
    assert resolve_mafft("mafft") is None


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
