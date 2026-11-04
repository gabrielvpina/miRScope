"""Assembly of analysis results into a storage-neutral payload.

Both modes reduce to the same shape: a list of **families** (a seed family in
macro mode, a cohesion cluster in strict mode), each holding its member miRNAs,
plus the **intersections** of species those families span. The payload built
here is serialised as-is to JSON and mapped onto tables in SQLite.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import __version__
from .models import MiRNA


@dataclass
class Member:
    """One miRNA inside a family."""

    id: str
    species: str
    sequence: str
    source_file: str = ""
    aligned: Optional[str] = None  # strict mode only

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "species": self.species,
            "sequence": self.sequence,
            "source_file": self.source_file,
        }
        if self.aligned is not None:
            data["aligned"] = self.aligned
        return data


@dataclass
class Family:
    """A seed family (macro) or an orthologous cohesion cluster (strict)."""

    id: str
    seed: str
    members: List[Member]

    @property
    def species(self) -> List[str]:
        return sorted({member.species for member in self.members})

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "seed": self.seed,
            "species": self.species,
            "members": [member.to_dict() for member in self.members],
        }


@dataclass
class Intersection:
    """A set of species and the families present in exactly that set."""

    id: str
    species: List[str]
    families: List[str]

    @property
    def size(self) -> int:
        return len(self.families)

    @property
    def degree(self) -> int:
        return len(self.species)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "species": self.species,
            "degree": self.degree,
            "size": self.size,
            "families": self.families,
        }


# ---------------------------------------------------------------------------
# Families
# ---------------------------------------------------------------------------


def split_record_id(record_id: str) -> Tuple[str, str]:
    """Split a ``<id>|<Genus_species>`` alignment id into ``(id, species_token)``."""
    if "|" in record_id:
        identifier, token = record_id.rsplit("|", 1)
        return identifier, token
    return record_id, ""


def macro_families(mirnas: Iterable[MiRNA]) -> List[Family]:
    """Group miRNAs into families by exact seed identity."""
    by_seed: Dict[str, List[Member]] = {}
    for mirna in mirnas:
        by_seed.setdefault(mirna.seed, []).append(
            Member(mirna.identifier, mirna.species, mirna.sequence, mirna.source_file)
        )
    return [
        Family(seed, seed, sorted(members, key=lambda m: (m.species, m.id)))
        for seed, members in sorted(by_seed.items())
    ]


def strict_families(
    clusters_by_seed: Dict[str, List[list]], mirnas: Iterable[MiRNA]
) -> List[Family]:
    """Turn cohesion clusters of aligned ``SeqRecord``s into families.

    Family ids follow the ``<seed>_Clust_<n>`` convention. The original
    (unaligned) sequence and source file are recovered from ``mirnas``.
    """
    lookup = {
        (mirna.identifier, mirna.species.replace(" ", "_")): mirna for mirna in mirnas
    }
    families: List[Family] = []
    for seed in sorted(clusters_by_seed):
        for index, cluster in enumerate(clusters_by_seed[seed], start=1):
            members: List[Member] = []
            for record in cluster:
                identifier, token = split_record_id(record.id)
                aligned = str(record.seq).upper()
                original = lookup.get((identifier, token))
                if original is not None:
                    members.append(
                        Member(
                            identifier,
                            original.species,
                            original.sequence,
                            original.source_file,
                            aligned,
                        )
                    )
                else:
                    members.append(
                        Member(
                            identifier,
                            token.replace("_", " ") or "Unknown",
                            aligned.replace("-", ""),
                            "",
                            aligned,
                        )
                    )
            families.append(Family(f"{seed}_Clust_{index}", seed, members))
    return families


# ---------------------------------------------------------------------------
# Intersections
# ---------------------------------------------------------------------------


def compute_intersections(families: Iterable[Family]) -> List[Intersection]:
    """Group families by their exact species set (UpSet-style intersections).

    Sorted by size (descending), then degree (descending), then species names,
    so the ordering is deterministic. Ids are ``I1``, ``I2``, … in that order.
    """
    groups: Dict[Tuple[str, ...], List[str]] = {}
    for family in families:
        key = tuple(family.species)
        if key:
            groups.setdefault(key, []).append(family.id)
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), -len(kv[0]), kv[0]))
    return [
        Intersection(f"I{rank}", list(species), family_ids)
        for rank, (species, family_ids) in enumerate(ordered, start=1)
    ]


def filter_intersections(
    intersections: Sequence[Intersection],
    top_n: Optional[int] = None,
    min_size: int = 1,
    min_degree: int = 1,
) -> Tuple[List[Intersection], int]:
    """Apply the UpSet filters. Returns ``(kept, total_before_top_n)``.

    * ``min_size`` — keep intersections with at least that many families.
    * ``min_degree`` — keep intersections spanning at least that many species.
    * ``top_n`` — keep the N largest (applied last; ``None``/``0`` keeps all).
    """
    kept = [
        item
        for item in intersections
        if item.size >= max(1, min_size) and item.degree >= max(1, min_degree)
    ]
    total = len(kept)
    if top_n is not None and top_n > 0:
        kept = kept[:top_n]
    return kept, total


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------


def build_result(
    mode: str,
    mirnas: Sequence[MiRNA],
    species: Sequence[str],
    families: Sequence[Family],
    *,
    data_dir: Optional[str],
    inputs: Optional[Sequence[str]] = None,
    cutoff: Optional[float] = None,
    top_n: Optional[int] = None,
    min_size: int = 1,
    min_degree: int = 1,
    failed_seeds: Optional[Sequence[str]] = None,
) -> dict:
    """Build the JSON-ready result payload shared by the JSON and SQLite writers."""
    intersections = compute_intersections(families)
    upset, upset_total = filter_intersections(
        intersections, top_n=top_n, min_size=min_size, min_degree=min_degree
    )
    return {
        "run": {
            "tool": "mirscope",
            "version": __version__,
            "mode": mode,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "parameters": {
                "cutoff": cutoff,
                "data_dir": data_dir,
                "inputs": list(inputs or []),
                "top_n": top_n,
                "min_size": min_size,
                "min_degree": min_degree,
            },
            "counts": {
                "mirnas": len(mirnas),
                "species": len(species),
                "families": len(families),
                "intersections": len(intersections),
            },
            "failed_seeds": list(failed_seeds or []),
        },
        "species": list(species),
        "families": [family.to_dict() for family in families],
        "intersections": {
            "all": [item.to_dict() for item in intersections],
            "upset": {
                "ids": [item.id for item in upset],
                "total_matching": upset_total,
            },
        },
    }
