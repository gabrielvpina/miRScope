"""Tests for family/intersection assembly and the result payload."""
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from mirscope.models import MiRNA
from mirscope.results import (
    Family,
    Member,
    build_result,
    compute_intersections,
    filter_intersections,
    macro_families,
    split_record_id,
    strict_families,
)


def _mirna(identifier, species, sequence):
    return MiRNA(identifier, species, sequence, f"mirna_{species.replace(' ', '_')}.fasta")


def _family(family_id, *species):
    return Family(family_id, family_id, [Member(f"{family_id}-{s}", s, "AUGC") for s in species])


def test_split_record_id():
    assert split_record_id("hsa-1|Homo_sapiens") == ("hsa-1", "Homo_sapiens")
    assert split_record_id("a|b|Homo_sapiens") == ("a|b", "Homo_sapiens")
    assert split_record_id("plain") == ("plain", "")


def test_macro_families_group_by_seed():
    mirnas = [
        _mirna("b", "Mus musculus", "AUGAGAUUC"),
        _mirna("a", "Homo sapiens", "AUGAGAUUC"),
        _mirna("c", "Homo sapiens", "ACCCCCCCC"),
    ]
    families = macro_families(mirnas)
    assert [f.id for f in families] == ["CCCCCCC", "UGAGAUU"]
    shared = families[1]
    assert shared.seed == "UGAGAUU"
    assert shared.species == ["Homo sapiens", "Mus musculus"]
    assert [m.id for m in shared.members] == ["a", "b"]
    assert shared.members[0].aligned is None


def test_strict_families_recover_original_sequence():
    mirnas = [_mirna("hsa-1", "Homo sapiens", "AUGAGAUUC")]
    cluster = [SeqRecord(Seq("aug-agauuc"), id="hsa-1|Homo_sapiens", description="")]
    families = strict_families({"UGAGAUU": [cluster]}, mirnas)
    assert families[0].id == "UGAGAUU_Clust_1"
    member = families[0].members[0]
    assert member.species == "Homo sapiens"
    assert member.sequence == "AUGAGAUUC"
    assert member.aligned == "AUG-AGAUUC"
    assert member.source_file == "mirna_Homo_sapiens.fasta"


def test_compute_intersections_sorted_by_size():
    families = [
        _family("F1", "A", "B"),
        _family("F2", "A"),
        _family("F3", "A", "B"),
    ]
    intersections = compute_intersections(families)
    assert [(i.id, i.species, i.size) for i in intersections] == [
        ("I1", ["A", "B"], 2),
        ("I2", ["A"], 1),
    ]
    assert intersections[0].families == ["F1", "F3"]


def test_filter_intersections():
    intersections = compute_intersections(
        [_family("F1", "A", "B"), _family("F2", "A"), _family("F3", "B")]
    )
    kept, total = filter_intersections(intersections, min_degree=2)
    assert total == 1 and kept[0].species == ["A", "B"]

    kept, total = filter_intersections(intersections, top_n=1)
    assert total == 3 and len(kept) == 1

    kept, total = filter_intersections(intersections, top_n=0)
    assert len(kept) == 3

    kept, total = filter_intersections(intersections, min_size=5)
    assert kept == [] and total == 0


def test_build_result_payload():
    mirnas = [
        _mirna("a", "Homo sapiens", "AUGAGAUUC"),
        _mirna("b", "Mus musculus", "AUGAGAUUC"),
    ]
    payload = build_result(
        "macro",
        mirnas,
        ["Homo sapiens", "Mus musculus"],
        macro_families(mirnas),
        data_dir="data",
        top_n=10,
        min_degree=2,
    )
    run = payload["run"]
    assert run["mode"] == "macro"
    assert run["parameters"]["min_degree"] == 2
    assert run["counts"] == {"mirnas": 2, "species": 2, "families": 1, "intersections": 1}
    assert payload["families"][0]["species"] == ["Homo sapiens", "Mus musculus"]
    assert payload["intersections"]["upset"] == {"ids": ["I1"], "total_matching": 1}
