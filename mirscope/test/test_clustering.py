"""Tests for aligned_identity and CohesionClusterer."""
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from mirscope.clustering import CohesionClusterer, aligned_identity


def _record(identifier, sequence):
    return SeqRecord(Seq(sequence), id=identifier, description="")


def test_aligned_identity_identical():
    assert aligned_identity("AUGC", "AUGC") == 100.0


def test_aligned_identity_half():
    assert aligned_identity("AUGC", "AUCC") == 75.0


def test_aligned_identity_ignores_double_gaps():
    # Double gap column is skipped, remaining are identical.
    assert aligned_identity("A-GC", "A-GC") == 100.0


def test_aligned_identity_empty_returns_zero():
    assert aligned_identity("--", "--") == 0.0


def test_cluster_groups_identical_sequences_together():
    alignment = [
        _record("a", "AUGCAUGC"),
        _record("b", "AUGCAUGC"),
    ]
    clusters = CohesionClusterer(cutoff=85.0).cluster(alignment)
    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_cluster_splits_divergent_sequences():
    alignment = [
        _record("a", "AAAAAAAA"),
        _record("b", "UUUUUUUU"),
    ]
    clusters = CohesionClusterer(cutoff=85.0).cluster(alignment)
    assert len(clusters) == 2


def test_cluster_empty_alignment_returns_empty():
    assert CohesionClusterer(cutoff=85.0).cluster([]) == []
