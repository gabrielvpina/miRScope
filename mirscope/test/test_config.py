"""Tests for configuration helpers, including the bundled data path."""
from mirscope.config import packaged_data_dir


def test_packaged_data_dir_is_inside_package():
    data_dir = packaged_data_dir()
    assert data_dir.name == "data"
    assert data_dir.parent.name == "mirscope"


def test_packaged_data_dir_is_absolute():
    assert packaged_data_dir().is_absolute()


def test_packaged_data_dir_contains_reference_fastas():
    data_dir = packaged_data_dir()
    assert data_dir.is_dir()
    assert any(data_dir.glob("*.fasta"))
