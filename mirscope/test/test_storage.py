"""Tests for the SQLite/JSON writers."""
import json
import sqlite3

from mirscope.models import MiRNA
from mirscope.results import build_result, macro_families
from mirscope.storage import ResultStore


def _payload():
    mirnas = [
        MiRNA("hsa-1", "Homo sapiens", "AUGAGAUUC", "h.fasta"),
        MiRNA("mmu-1", "Mus musculus", "AUGAGAUUC", "m.fasta"),
        MiRNA("hsa-2", "Homo sapiens", "ACCCCCCCC", "h.fasta"),
    ]
    return build_result(
        "macro",
        mirnas,
        ["Homo sapiens", "Mus musculus"],
        macro_families(mirnas),
        data_dir="data",
        top_n=10,
        min_degree=2,
    )


def test_sqlite_round_trip(tmp_path):
    path = tmp_path / "out.db"
    ResultStore().write_sqlite(_payload(), str(path))
    con = sqlite3.connect(path)
    assert con.execute("SELECT mode, min_degree FROM run").fetchone() == ("macro", 2)
    assert con.execute("SELECT COUNT(*) FROM species").fetchone()[0] == 2
    assert con.execute("SELECT COUNT(*) FROM family").fetchone()[0] == 2
    assert con.execute("SELECT COUNT(*) FROM mirna").fetchone()[0] == 3
    assert con.execute(
        "SELECT species_count FROM family WHERE id = 'UGAGAUU'"
    ).fetchone()[0] == 2
    # Two intersections; only the shared one survives min_degree=2 in the UpSet view.
    rows = con.execute(
        "SELECT id, degree, size, upset_rank FROM intersection ORDER BY id"
    ).fetchall()
    assert rows == [("I1", 2, 1, 1), ("I2", 1, 1, None)]
    con.close()


def test_sqlite_overwrites_existing_file(tmp_path):
    path = tmp_path / "out.db"
    store = ResultStore()
    store.write_sqlite(_payload(), str(path))
    store.write_sqlite(_payload(), str(path))
    con = sqlite3.connect(path)
    assert con.execute("SELECT COUNT(*) FROM run").fetchone()[0] == 1
    con.close()


def test_json_round_trip(tmp_path):
    path = tmp_path / "out.json"
    payload = _payload()
    ResultStore().write_json(payload, str(path))
    assert json.loads(path.read_text()) == payload


def _strict_payload():
    from mirscope.results import Family, Member

    families = [
        Family("UGAGAUU_Clust_1", "UGAGAUU", [
            Member("hsa-1", "Homo sapiens", "AUGAGAUUC", "h.fasta", "AUGAGAUUC-"),
            Member("mmu-1", "Mus musculus", "AUGAGAUUCA", "m.fasta", "AUGAGAUUCA"),
        ]),
        Family("CCCCCCC_Clust_1", "CCCCCCC", [
            Member("hsa-2", "Homo sapiens", "ACCCCCCCC", "h.fasta", "ACCCCCCCC"),
        ]),
    ]
    mirnas = [
        MiRNA("hsa-1", "Homo sapiens", "AUGAGAUUC", "h.fasta"),
        MiRNA("mmu-1", "Mus musculus", "AUGAGAUUCA", "m.fasta"),
        MiRNA("hsa-2", "Homo sapiens", "ACCCCCCCC", "h.fasta"),
    ]
    return build_result(
        "strict", mirnas, ["Homo sapiens", "Mus musculus"], families,
        data_dir="data", inputs=["in/h.fasta"], cutoff=85.0, top_n=1, failed_seeds=["AAAAAAA"],
    )


def test_read_sqlite_rebuilds_the_payload(tmp_path):
    for payload in (_payload(), _strict_payload()):
        path = tmp_path / f"{payload['run']['mode']}.db"
        ResultStore().write_sqlite(payload, str(path))
        assert ResultStore.read_sqlite(str(path)) == payload
