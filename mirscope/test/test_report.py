"""Tests for the self-contained HTML report builder."""
import json
import re

from mirscope.models import MiRNA
from mirscope.report import COMPONENTS_DIR, SCRIPT_COMPONENTS, render_report
from mirscope.results import build_result, macro_families


def _payload(identifier="hsa-1"):
    mirnas = [
        MiRNA(identifier, "Homo sapiens", "AUGAGAUUC", "h.fasta"),
        MiRNA("mmu-1", "Mus musculus", "AUGAGAUUC", "m.fasta"),
    ]
    return build_result(
        "macro", mirnas, ["Homo sapiens", "Mus musculus"], macro_families(mirnas), data_dir="data"
    )


def test_all_placeholders_resolved():
    html = render_report(_payload())
    assert not re.search(r"\{\{MS_\w+\}\}", html)
    assert "<title>miRScope — macro mode</title>" in html


def test_components_are_inlined():
    html = render_report(_payload())
    for name in SCRIPT_COMPONENTS.values():
        first_line = (COMPONENTS_DIR / name).read_text().splitlines()[1]
        assert first_line in html
    assert "--ms-primary" in html  # CSS
    assert "d3" in html and "version" in html  # vendored D3


def test_embedded_data_round_trips():
    payload = _payload()
    html = render_report(payload)
    match = re.search(r"const MS_REPORT = (.*?);</script>", html, re.S)
    assert json.loads(match.group(1)) == payload


def test_script_close_in_data_is_escaped():
    html = render_report(_payload("evil</script><script>alert(1)"))
    data = re.search(r"const MS_REPORT = (.*?);</script>", html, re.S).group(1)
    assert "</script>" not in data
    assert "evil</script>" in json.loads(data)["families"][0]["members"][0]["id"]
