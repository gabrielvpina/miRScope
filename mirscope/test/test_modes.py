"""Integration tests for the analysis modes."""
import json
import sqlite3

import pytest

from mirscope.alignment import MafftAligner
from mirscope.modes.macro import MacroMode
from mirscope.modes.strict import StrictMode


def _write_reference(folder):
    folder.mkdir()
    (folder / "mirna_Homo_sapiens.fasta").write_text(
        ">hsa-1\nUGAGAUUCUUGAUGAU\n>hsa-2\nUAGCUUAUCAGACUGAU\n"
    )
    (folder / "mirna_Mus_musculus.fasta").write_text(">mmu-1\nUGAGAUUCUUGAUGAU\n")


def test_macro_writes_sqlite_and_json(tmp_path):
    data = tmp_path / "data"
    _write_reference(data)
    out = tmp_path / "results"

    assert MacroMode().run(str(data), None, str(out)) is True

    payload = json.loads((out / "mirscope_macro.json").read_text())
    assert payload["run"]["mode"] == "macro"
    assert payload["run"]["counts"]["families"] == 2
    assert payload["species"] == ["Homo sapiens", "Mus musculus"]

    con = sqlite3.connect(out / "mirscope_macro.db")
    assert con.execute("SELECT COUNT(*) FROM family").fetchone()[0] == 2
    assert con.execute("SELECT COUNT(*) FROM mirna").fetchone()[0] == 3
    con.close()


def test_macro_creates_nested_output_dir(tmp_path):
    data = tmp_path / "data"
    _write_reference(data)
    out = tmp_path / "nested" / "run1"

    MacroMode().run(str(data), None, str(out))

    assert (out / "mirscope_macro.db").exists()
    assert (out / "mirscope_macro.json").exists()


def test_macro_without_data_returns_false(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert MacroMode().run(str(empty), None, str(tmp_path / "out")) is False


def test_strict_without_mafft_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("MIRSCOPE_MAFFT", "")
    monkeypatch.setattr("mirscope.alignment.shutil.which", lambda name: None)
    data = tmp_path / "data"
    _write_reference(data)
    assert StrictMode(85).run(str(data), None, str(tmp_path / "out")) is False


@pytest.mark.skipif(
    not MafftAligner().is_available(), reason="MAFFT executable not available"
)
def test_strict_writes_sqlite_json_and_fasta(tmp_path):
    data = tmp_path / "data"
    _write_reference(data)
    out = tmp_path / "results"

    assert StrictMode(85).run(str(data), None, str(out)) is True

    assert (out / "output_mode2_alignments.fasta").exists()
    payload = json.loads((out / "mirscope_strict.json").read_text())
    assert payload["run"]["parameters"]["cutoff"] == 85
    ids = [family["id"] for family in payload["families"]]
    assert "GAGAUUC_Clust_1" in ids
    con = sqlite3.connect(out / "mirscope_strict.db")
    assert con.execute(
        "SELECT COUNT(*) FROM mirna WHERE aligned_sequence IS NOT NULL"
    ).fetchone()[0] == 3
    con.close()
