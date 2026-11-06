"""Assemble the self-contained interactive HTML report from a result payload.

The page is built from the files in ``mirscope/components/``:

* ``shell.html`` — page skeleton with ``{{MS_*}}`` placeholders;
* ``base.css`` — the whole design system (colours live in ``:root``);
* ``common.js`` — shared helpers (tooltip, formatting, exports, tables);
* ``section_*.js`` — one module per tab, each exposing an ``msInit*`` function.

Everything (CSS, scripts, D3 and the JSON payload) is inlined, so the resulting
``.html`` opens offline with a double click.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List

from .logging_config import get_logger

_HERE = Path(__file__).resolve().parent
COMPONENTS_DIR = _HERE / "components"
ASSETS_DIR = _HERE / "assets"
D3_VERSION = "7.9.0"
D3_PATH = _HERE / "vendor" / f"d3-{D3_VERSION}.min.js"

# Placeholder -> component file (inlined in this order in shell.html).
SCRIPT_COMPONENTS: Dict[str, str] = {
    "{{MS_COMMON}}": "common.js",
    "{{MS_OVERVIEW}}": "section_overview.js",
    "{{MS_UPSET}}": "section_upset.js",
    "{{MS_FAMILIES}}": "section_families.js",
    "{{MS_SPECIES}}": "section_species.js",
    "{{MS_INPUT}}": "section_input.js",
    "{{MS_SEQUENCES}}": "section_sequences.js",
    "{{MS_CUTOFF}}": "section_cutoff.js",
    "{{MS_ABOUT}}": "section_about.js",
}

_PLACEHOLDER = re.compile(r"\{\{MS_\w+\}\}")


def _read(name: str) -> str:
    return (COMPONENTS_DIR / name).read_text(encoding="utf-8")


def _data_uri(path: Path) -> str:
    if not path.is_file():
        return ""
    mime = {"png": "image/png", "svg": "image/svg+xml"}.get(
        path.suffix.lower().lstrip("."), "application/octet-stream"
    )
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _json_for_script(payload: dict) -> str:
    """Serialise ``payload`` so it is safe inside an inline ``<script>``."""
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # Escape "<" so "</script>" or "<!--" inside the data can never end the tag.
    return text.replace("<", "\\u003c")


def render_report(payload: dict) -> str:
    """Return the complete HTML document for ``payload``."""
    run = payload.get("run", {})
    mode = run.get("mode", "")
    title = f"miRScope — {mode} mode" if mode else "miRScope report"

    replacements = {
        "{{MS_TITLE}}": title,
        "{{MS_LOGO}}": _data_uri(ASSETS_DIR / "logo.svg"),
        "{{MS_ICON}}": _data_uri(ASSETS_DIR / "logo-icon.svg"),
        "{{MS_STYLES}}": _read("base.css"),
        "{{MS_DATA}}": _json_for_script(payload),
        "{{MS_D3}}": D3_PATH.read_text(encoding="utf-8"),
    }
    replacements.update({key: _read(name) for key, name in SCRIPT_COMPONENTS.items()})

    # Substitute in a single pass so placeholder-like text inside the data or
    # scripts is never re-substituted.
    html = _PLACEHOLDER.sub(
        lambda match: replacements.get(match.group(0), match.group(0)), _read("shell.html")
    )
    missing = [key for key in _PLACEHOLDER.findall(_read("shell.html")) if key not in replacements]
    if missing:
        get_logger("report").warning("Unresolved report placeholders: %s", missing)
    return html


def write_report(payload: dict, output_path: str) -> None:
    """Render ``payload`` and write the self-contained HTML to ``output_path``."""
    Path(output_path).write_text(render_report(payload), encoding="utf-8")
    get_logger("report").info("HTML report written to '%s'.", output_path)


def _is_payload(payload: object) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("run"), dict)
        and payload["run"].get("tool") == "mirscope"
        and "families" in payload
    )


def reload_reports(directories: Iterable[str]) -> List[str]:
    """Re-render the HTML report of every result found in ``directories``.

    Development helper behind the hidden ``mirscope --reload`` flag: picks up
    each ``*.json`` result (or, when no JSON with the same name exists, the
    ``*.db`` database) and rewrites ``<name>.html`` with the current
    components, without re-running the analysis. Returns the written paths.
    """
    from .storage import ResultStore

    logger = get_logger("report")
    written: List[str] = []
    for directory in directories:
        folder = Path(directory)
        if not folder.is_dir():
            logger.warning("Not a directory: '%s'.", folder)
            continue
        sources: Dict[str, Path] = {}
        for path in sorted(folder.glob("*.db")):
            sources[path.stem] = path
        for path in sorted(folder.glob("*.json")):
            sources[path.stem] = path   # JSON wins over the database
        for stem, path in sorted(sources.items()):
            try:
                if path.suffix == ".json":
                    payload = ResultStore.read_json(str(path))
                else:
                    payload = ResultStore.read_sqlite(str(path))
            except Exception as exc:  # not a miRScope result: skip quietly
                logger.debug("Skipping '%s': %s", path, exc)
                continue
            if not _is_payload(payload):
                logger.debug("Skipping '%s': not a miRScope result.", path)
                continue
            target = path.with_suffix(".html")
            write_report(payload, str(target))
            written.append(str(target))
    if not written:
        logger.warning("No miRScope JSON or SQLite results found to reload.")
    return written
