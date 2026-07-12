"""First-run environment bootstrap.

On the very first execution of the ``mirscope`` command this module checks
whether `pixi <https://pixi.sh>`_ is available and, if it is not, offers to
install it and run ``pixi install`` so every dependency (including MAFFT) is
set up. A marker file guarantees the check only runs once.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .logging_config import get_logger

PIXI_INSTALL_URL = "https://pixi.sh/install.sh"
PIXI_HOME_BIN = Path.home() / ".pixi" / "bin" / "pixi"


def default_marker() -> Path:
    """Return the path of the marker file that records the first-run check."""
    return Path.home() / ".config" / "mirscope" / "bootstrap_done"


def pixi_path() -> Optional[str]:
    """Return the path to the pixi executable, or ``None`` if not installed."""
    found = shutil.which("pixi")
    if found:
        return found
    if PIXI_HOME_BIN.exists():
        return str(PIXI_HOME_BIN)
    return None


def pixi_available() -> bool:
    return pixi_path() is not None


def project_root() -> Path:
    """Return the directory holding ``pixi.toml`` (repo root), or the CWD."""
    candidate = Path(__file__).resolve().parent.parent
    if (candidate / "pixi.toml").exists():
        return candidate
    return Path.cwd()


def _prompt_yes_no(question: str) -> bool:
    try:
        answer = input(f"{question} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def _write_marker(marker: Path) -> None:
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("ok\n")
    except OSError:  # pragma: no cover - best effort only
        pass


def _install_pixi(logger) -> bool:
    """Download and run the official pixi installer. Returns success."""
    logger.info("Installing pixi from %s ...", PIXI_INSTALL_URL)
    try:
        result = subprocess.run(
            f"curl -fsSL {PIXI_INSTALL_URL} | bash",
            shell=True,
            check=False,
        )
    except OSError as error:
        logger.error("Could not launch the pixi installer: %s", error)
        return False
    if result.returncode != 0:
        logger.error("Pixi installation failed (exit code %d).", result.returncode)
        return False
    return True


def _run_pixi_install(logger) -> bool:
    """Run ``pixi install`` inside the project root. Returns success."""
    executable = pixi_path()
    if executable is None:
        logger.error("Pixi executable not found after installation.")
        return False
    root = project_root()
    logger.info("Running 'pixi install' in '%s' ...", root)
    try:
        result = subprocess.run([executable, "install"], cwd=str(root), check=False)
    except OSError as error:
        logger.error("Could not run 'pixi install': %s", error)
        return False
    if result.returncode != 0:
        logger.error("'pixi install' failed (exit code %d).", result.returncode)
        return False
    return True


def ensure_pixi(marker_path: Optional[Path] = None) -> None:
    """Run the one-time first-run pixi check.

    Silent and non-blocking when pixi is already present, when disabled via the
    ``MIRSCOPE_NO_BOOTSTRAP`` environment variable, or in non-interactive
    sessions (so it never hangs a script or CI).
    """
    logger = get_logger("bootstrap")
    marker = marker_path or default_marker()

    if os.environ.get("MIRSCOPE_NO_BOOTSTRAP"):
        return
    if marker.exists():
        return
    if pixi_available():
        _write_marker(marker)
        return
    if not sys.stdin.isatty():
        logger.info("Pixi not found; skipping setup (non-interactive session).")
        _write_marker(marker)
        return

    print("\nPixi was not found on your system.")
    print("Pixi manages MIRSCOPE's dependencies, including the MAFFT aligner.")
    if not _prompt_yes_no("Install pixi and run 'pixi install' now?"):
        print("Skipped. You can install pixi later from https://pixi.sh\n")
        _write_marker(marker)
        return

    if _install_pixi(logger) and _run_pixi_install(logger):
        print("\nPixi environment is ready. From now on run: pixi run mirscope ...\n")
        _write_marker(marker)
    else:
        # Leave the marker unset so the setup is retried on the next run.
        print("\nPixi setup did not complete. See the log above; it will retry next time.\n")
