"""Persistence of result payloads to JSON and SQLite (standard library only)."""
from __future__ import annotations

import json
import os
import sqlite3

from .logging_config import get_logger

SCHEMA = """
CREATE TABLE run (
    id INTEGER PRIMARY KEY,
    tool TEXT NOT NULL,
    version TEXT NOT NULL,
    mode TEXT NOT NULL,
    created_at TEXT NOT NULL,
    cutoff REAL,
    data_dir TEXT,
    inputs TEXT,              -- JSON array
    top_n INTEGER,
    min_size INTEGER,
    min_degree INTEGER,
    n_mirnas INTEGER,
    n_species INTEGER,
    n_families INTEGER,
    n_intersections INTEGER,
    failed_seeds TEXT         -- JSON array
);
CREATE TABLE species (
    name TEXT PRIMARY KEY
);
CREATE TABLE family (
    id TEXT PRIMARY KEY,      -- seed (macro) or <seed>_Clust_<n> (strict)
    seed TEXT NOT NULL,
    species_count INTEGER NOT NULL,
    member_count INTEGER NOT NULL
);
CREATE TABLE mirna (
    family_id TEXT NOT NULL REFERENCES family(id),
    mirna_id TEXT NOT NULL,
    species TEXT NOT NULL REFERENCES species(name),
    sequence TEXT NOT NULL,
    aligned_sequence TEXT,    -- strict mode only
    source_file TEXT
);
CREATE TABLE presence (
    family_id TEXT NOT NULL REFERENCES family(id),
    species TEXT NOT NULL REFERENCES species(name),
    PRIMARY KEY (family_id, species)
);
CREATE TABLE intersection (
    id TEXT PRIMARY KEY,      -- I1, I2, ... (sorted by size desc)
    degree INTEGER NOT NULL,
    size INTEGER NOT NULL,
    upset_rank INTEGER        -- position in the filtered UpSet view, NULL if filtered out
);
CREATE TABLE intersection_species (
    intersection_id TEXT NOT NULL REFERENCES intersection(id),
    species TEXT NOT NULL REFERENCES species(name),
    PRIMARY KEY (intersection_id, species)
);
CREATE TABLE intersection_family (
    intersection_id TEXT NOT NULL REFERENCES intersection(id),
    family_id TEXT NOT NULL REFERENCES family(id),
    PRIMARY KEY (intersection_id, family_id)
);
CREATE INDEX idx_mirna_family ON mirna(family_id);
CREATE INDEX idx_mirna_species ON mirna(species);
CREATE INDEX idx_presence_species ON presence(species);
CREATE INDEX idx_family_seed ON family(seed);
"""


class ResultStore:
    """Write a result payload (see :func:`mirscope.results.build_result`)."""

    def __init__(self) -> None:
        self.logger = get_logger("storage")

    def save(self, payload: dict, sqlite_path: str, json_path: str) -> None:
        self.write_sqlite(payload, sqlite_path)
        self.write_json(payload, json_path)

    def write_json(self, payload: dict, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        self.logger.info("JSON written to '%s'.", path)

    @staticmethod
    def read_json(path: str) -> dict:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def read_sqlite(path: str) -> dict:
        """Rebuild the result payload from a database written by :meth:`write_sqlite`."""
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            return ResultStore._load(connection)
        finally:
            connection.close()

    @staticmethod
    def _load(connection: sqlite3.Connection) -> dict:
        run = connection.execute("SELECT * FROM run ORDER BY id LIMIT 1").fetchone()
        if run is None:
            raise ValueError("database has no run row")
        species = [r["name"] for r in connection.execute("SELECT name FROM species ORDER BY rowid")]

        members: dict = {}
        for r in connection.execute(
            "SELECT family_id, mirna_id, species, sequence, aligned_sequence, source_file"
            " FROM mirna ORDER BY rowid"
        ):
            member = {
                "id": r["mirna_id"],
                "species": r["species"],
                "sequence": r["sequence"],
                "source_file": r["source_file"] or "",
            }
            if r["aligned_sequence"] is not None:
                member["aligned"] = r["aligned_sequence"]
            members.setdefault(r["family_id"], []).append(member)
        families = []
        for r in connection.execute("SELECT id, seed FROM family ORDER BY rowid"):
            fam_members = members.get(r["id"], [])
            families.append(
                {
                    "id": r["id"],
                    "seed": r["seed"],
                    "species": sorted({m["species"] for m in fam_members}),
                    "members": fam_members,
                }
            )

        inter_species: dict = {}
        for r in connection.execute(
            "SELECT intersection_id, species FROM intersection_species ORDER BY rowid"
        ):
            inter_species.setdefault(r["intersection_id"], []).append(r["species"])
        inter_families: dict = {}
        for r in connection.execute(
            "SELECT intersection_id, family_id FROM intersection_family ORDER BY rowid"
        ):
            inter_families.setdefault(r["intersection_id"], []).append(r["family_id"])
        intersections = []
        upset = []
        for r in connection.execute("SELECT * FROM intersection ORDER BY rowid"):
            intersections.append(
                {
                    "id": r["id"],
                    "species": inter_species.get(r["id"], []),
                    "degree": r["degree"],
                    "size": r["size"],
                    "families": inter_families.get(r["id"], []),
                }
            )
            if r["upset_rank"] is not None:
                upset.append((r["upset_rank"], r["id"]))
        min_size = run["min_size"] if run["min_size"] is not None else 1
        min_degree = run["min_degree"] if run["min_degree"] is not None else 1
        total_matching = sum(
            1
            for i in intersections
            if i["size"] >= max(1, min_size) and i["degree"] >= max(1, min_degree)
        )

        return {
            "run": {
                "tool": run["tool"],
                "version": run["version"],
                "mode": run["mode"],
                "created_at": run["created_at"],
                "parameters": {
                    "cutoff": run["cutoff"],
                    "data_dir": run["data_dir"],
                    "inputs": json.loads(run["inputs"] or "[]"),
                    "top_n": run["top_n"],
                    "min_size": run["min_size"],
                    "min_degree": run["min_degree"],
                },
                "counts": {
                    "mirnas": run["n_mirnas"],
                    "species": run["n_species"],
                    "families": run["n_families"],
                    "intersections": run["n_intersections"],
                },
                "failed_seeds": json.loads(run["failed_seeds"] or "[]"),
            },
            "species": species,
            "families": families,
            "intersections": {
                "all": intersections,
                "upset": {
                    "ids": [item_id for _, item_id in sorted(upset)],
                    "total_matching": total_matching,
                },
            },
        }

    def write_sqlite(self, payload: dict, path: str) -> None:
        """Write ``payload`` to a fresh SQLite database (an existing file is replaced)."""
        if os.path.exists(path):
            os.remove(path)
        connection = sqlite3.connect(path)
        try:
            with connection:
                connection.executescript(SCHEMA)
                self._insert(connection, payload)
        finally:
            connection.close()
        self.logger.info("SQLite database written to '%s'.", path)

    @staticmethod
    def _insert(connection: sqlite3.Connection, payload: dict) -> None:
        run = payload["run"]
        params = run["parameters"]
        counts = run["counts"]
        connection.execute(
            "INSERT INTO run (tool, version, mode, created_at, cutoff, data_dir, inputs,"
            " top_n, min_size, min_degree, n_mirnas, n_species, n_families,"
            " n_intersections, failed_seeds) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                run["tool"],
                run["version"],
                run["mode"],
                run["created_at"],
                params["cutoff"],
                params["data_dir"],
                json.dumps(params["inputs"]),
                params["top_n"],
                params["min_size"],
                params["min_degree"],
                counts["mirnas"],
                counts["species"],
                counts["families"],
                counts["intersections"],
                json.dumps(run["failed_seeds"]),
            ),
        )

        connection.executemany(
            "INSERT INTO species (name) VALUES (?)",
            [(name,) for name in payload["species"]],
        )

        families = payload["families"]
        connection.executemany(
            "INSERT INTO family (id, seed, species_count, member_count) VALUES (?,?,?,?)",
            [
                (f["id"], f["seed"], len(f["species"]), len(f["members"]))
                for f in families
            ],
        )
        connection.executemany(
            "INSERT INTO mirna (family_id, mirna_id, species, sequence,"
            " aligned_sequence, source_file) VALUES (?,?,?,?,?,?)",
            [
                (
                    f["id"],
                    m["id"],
                    m["species"],
                    m["sequence"],
                    m.get("aligned"),
                    m.get("source_file"),
                )
                for f in families
                for m in f["members"]
            ],
        )
        connection.executemany(
            "INSERT INTO presence (family_id, species) VALUES (?,?)",
            [(f["id"], species) for f in families for species in f["species"]],
        )

        intersections = payload["intersections"]
        upset_rank = {
            item_id: rank
            for rank, item_id in enumerate(intersections["upset"]["ids"], start=1)
        }
        connection.executemany(
            "INSERT INTO intersection (id, degree, size, upset_rank) VALUES (?,?,?,?)",
            [
                (i["id"], i["degree"], i["size"], upset_rank.get(i["id"]))
                for i in intersections["all"]
            ],
        )
        connection.executemany(
            "INSERT INTO intersection_species (intersection_id, species) VALUES (?,?)",
            [(i["id"], s) for i in intersections["all"] for s in i["species"]],
        )
        connection.executemany(
            "INSERT INTO intersection_family (intersection_id, family_id) VALUES (?,?)",
            [(i["id"], fid) for i in intersections["all"] for fid in i["families"]],
        )
