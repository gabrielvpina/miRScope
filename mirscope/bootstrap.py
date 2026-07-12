"""Environment provisioning and discovery for the pixi-managed MAFFT binary.

MAFFT is a native tool that pip cannot install, so it is provided by a pixi
environment. This module locates that environment in any install layout and
makes it usable by the plain ``mirscope`` command:

* **Technique 1 — walk-up manifest search** (:func:`find_pixi_toml`): in an
  editable/repository install the project ``pixi.toml`` is found by walking up
  from this file.
* **Technique 2 — PATH injection** (:func:`activate_pixi_env`): the pixi env's
  ``bin`` directory is prepended to ``PATH`` so MAFFT (and its helper binaries)
  resolve by name, instead of pointing at a single absolute path.

For wheel installs (no project on disk) the environment is provisioned **inside
the installed package** (:func:`managed_env_dir` → ``mirscope/_env/.pixi``) from
a manifest shipped in the package (``mirscope/_env/pixi.toml``). Co-locating it
with the code keeps everything in one place; note that ``pip uninstall`` will
not delete this generated environment (pip only removes files it recorded at
install time), so use ``mirscope-setup --clean`` to remove it.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .logging_config import get_logger, setup_logging

PIXI_INSTALL_URL = "https://pixi.sh/install.sh"
PIXI_HOME_BIN = Path.home() / ".pixi" / "bin" / "pixi"
_PIXI_TOML = "pixi.toml"
_MANIFEST_WALK_UP = 5


# ---------------------------------------------------------------------------
# pixi executable
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Locating manifests and environments
# ---------------------------------------------------------------------------

def find_pixi_toml() -> Optional[Path]:
    """Walk up from this file looking for a project ``pixi.toml`` (technique 1).

    Returns the manifest in editable/repository installs; ``None`` in a wheel
    install where no project checkout is on disk.
    """
    search = Path(__file__).resolve().parent
    for _ in range(_MANIFEST_WALK_UP):
        candidate = search / _PIXI_TOML
        if candidate.exists():
            return candidate
        if search.parent == search:  # reached filesystem root
            break
        search = search.parent
    return None


def project_root() -> Path:
    """Return the directory holding the project ``pixi.toml``, or the CWD."""
    manifest = find_pixi_toml()
    return manifest.parent if manifest else Path.cwd()


def managed_env_dir() -> Path:
    """Directory holding the managed pixi environment, inside the package.

    Co-locating the environment with the installed package keeps everything in
    one folder. The shipped manifest already lives here as ``pixi.toml``; a
    ``.pixi/`` subtree is created next to it by ``pixi install``.
    """
    return Path(__file__).resolve().parent / "_env"


def _env_bin(root: Path) -> Path:
    return root / ".pixi" / "envs" / "default" / "bin"


def _existing(path: Path) -> Optional[Path]:
    return path if path.exists() else None


def managed_env_bin() -> Optional[Path]:
    return _existing(_env_bin(managed_env_dir()))


def repo_env_bin() -> Optional[Path]:
    manifest = find_pixi_toml()
    if manifest is None:
        return None
    return _existing(_env_bin(manifest.parent))


def pixi_env_bin_dirs() -> List[Path]:
    """Existing pixi env bin dirs: managed (user data) first, then repo (dev)."""
    dirs: List[Path] = []
    for candidate in (managed_env_bin(), repo_env_bin()):
        if candidate and candidate not in dirs:
            dirs.append(candidate)
    return dirs


def activate_pixi_env() -> Optional[Path]:
    """Prepend the first available pixi env bin dir to ``PATH`` (technique 2).

    Returns the activated bin directory, or ``None`` if none exists yet.
    """
    for bin_dir in pixi_env_bin_dirs():
        entries = os.environ.get("PATH", "").split(os.pathsep)
        if str(bin_dir) not in entries:
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        return bin_dir
    return None


# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------

def _packaged_manifest() -> Path:
    """Path to the minimal manifest shipped inside the package."""
    return Path(__file__).resolve().parent / "_env" / _PIXI_TOML


def _prepare_env_dir(logger) -> Optional[Path]:
    """Return the directory to run ``pixi install`` in, ensuring a manifest.

    Dev/editable installs use the project manifest in place; wheel installs get
    a manifest copied into the per-user managed environment directory.
    """
    manifest = find_pixi_toml()
    if manifest is not None:
        logger.info("Using project manifest: %s", manifest)
        return manifest.parent

    env_dir = managed_env_dir()
    env_dir.mkdir(parents=True, exist_ok=True)
    template = _packaged_manifest()
    if not template.exists():
        logger.error("Packaged pixi manifest not found at '%s'.", template)
        return None
    target = env_dir / _PIXI_TOML
    # When the managed dir is the package's own _env, the manifest is already
    # in place — avoid copying a file onto itself.
    if target.resolve() != template.resolve():
        shutil.copyfile(template, target)
    logger.info("Managed environment: %s", env_dir)
    return env_dir


# ---------------------------------------------------------------------------
# Interactive + install helpers
# ---------------------------------------------------------------------------

def default_marker() -> Path:
    """Return the marker file path recording the first-run check."""
    return managed_env_dir() / "bootstrap_done"


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
            f"curl -fsSL {PIXI_INSTALL_URL} | bash", shell=True, check=False
        )
    except OSError as error:
        logger.error("Could not launch the pixi installer: %s", error)
        return False
    if result.returncode != 0:
        logger.error("Pixi installation failed (exit code %d).", result.returncode)
        return False
    return True


def _run_pixi_install(logger) -> bool:
    """Provision a manifest and run ``pixi install``. Returns success."""
    executable = pixi_path()
    if executable is None:
        logger.error("Pixi executable not found.")
        return False
    env_dir = _prepare_env_dir(logger)
    if env_dir is None:
        return False
    logger.info("Running 'pixi install' in '%s' ...", env_dir)
    try:
        result = subprocess.run([executable, "install"], cwd=str(env_dir), check=False)
    except OSError as error:
        logger.error("Could not run 'pixi install': %s", error)
        return False
    if result.returncode != 0:
        logger.error("'pixi install' failed (exit code %d).", result.returncode)
        return False
    activate_pixi_env()
    return True


def _verify_mafft(logger) -> bool:
    """Check that MAFFT is reachable after activating the pixi env."""
    activate_pixi_env()
    mafft = shutil.which("mafft")
    if mafft is None:
        for bin_dir in pixi_env_bin_dirs():
            candidate = bin_dir / "mafft"
            if candidate.exists():
                mafft = str(candidate)
                break
    if mafft is None:
        return False
    try:
        result = subprocess.run(
            [mafft, "--version"], check=False, capture_output=True, text=True
        )
    except OSError:
        return False
    if result.returncode != 0:
        return False
    output = (result.stderr or result.stdout or "").strip()
    version = output.splitlines()[-1] if output else "unknown version"
    logger.info("MAFFT is available: %s (%s)", version, mafft)
    return True


# ---------------------------------------------------------------------------
# Entry point: mirscope-setup
# ---------------------------------------------------------------------------

def _clean_managed_env(logger) -> int:
    # Remove only the generated pixi environment and the first-run marker,
    # preserving the shipped manifest (pixi.toml) so setup can run again.
    pixi_dir = managed_env_dir() / ".pixi"
    marker = default_marker()
    removed = False
    if pixi_dir.exists():
        shutil.rmtree(pixi_dir, ignore_errors=True)
        logger.info("Removed pixi environment: %s", pixi_dir)
        removed = True
    if marker.exists():
        marker.unlink()
        removed = True
    if not removed:
        logger.info("Nothing to remove (%s).", managed_env_dir())
    return 0


def run_setup(argv: Optional[List[str]] = None) -> int:
    """Entry point for ``mirscope-setup``.

    Run once after ``pip install``: ensures pixi is present, provisions the
    environment (installing MAFFT), and verifies it. ``--clean`` removes the
    user-level managed environment. Returns a process exit code.
    """
    parser = argparse.ArgumentParser(
        prog="mirscope-setup",
        description="Set up the MIRSCOPE environment (pixi + MAFFT).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the user-level managed environment and exit.",
    )
    args = parser.parse_args(argv)

    setup_logging()
    logger = get_logger("setup")

    if args.clean:
        return _clean_managed_env(logger)

    logger.info("=" * 60)
    logger.info("MIRSCOPE — environment setup (pixi + MAFFT)")
    logger.info("=" * 60)

    if pixi_available():
        logger.info("Pixi found: %s", pixi_path())
    else:
        logger.warning("Pixi is not installed; it is required to install MAFFT.")
        if sys.stdin.isatty():
            if not _prompt_yes_no("Install pixi now?"):
                logger.error("Setup aborted: pixi is required to install MAFFT.")
                return 1
        else:
            logger.info("Non-interactive session: installing pixi automatically.")
        if not _install_pixi(logger):
            return 1

    logger.info("Installing dependencies with 'pixi install' (includes MAFFT)...")
    if not _run_pixi_install(logger):
        return 1

    if _verify_mafft(logger):
        logger.info("Setup complete. You can now run: mirscope ...")
        return 0

    logger.warning(
        "Dependencies were installed, but MAFFT could not be verified. "
        "Try running 'mirscope strict ...' or check the log above."
    )
    return 0


# ---------------------------------------------------------------------------
# First-run passive check (used by the CLI)
# ---------------------------------------------------------------------------

def ensure_pixi(marker_path: Optional[Path] = None) -> None:
    """One-time first-run check that pixi (and thus MAFFT) is set up.

    Silent and non-blocking when the environment is already usable, when
    disabled via ``MIRSCOPE_NO_BOOTSTRAP``, or in non-interactive sessions.
    """
    logger = get_logger("bootstrap")
    marker = marker_path or default_marker()

    if os.environ.get("MIRSCOPE_NO_BOOTSTRAP"):
        return
    if marker.exists():
        return
    if pixi_available() or pixi_env_bin_dirs():
        _write_marker(marker)
        return
    if not sys.stdin.isatty():
        logger.info("Pixi not found; skipping setup (non-interactive session).")
        _write_marker(marker)
        return

    print("\nPixi was not found on your system.")
    print("Pixi manages MIRSCOPE's dependencies, including the MAFFT aligner.")
    if not _prompt_yes_no("Install pixi and provision the environment now?"):
        print("Skipped. Run 'mirscope-setup' later to finish setup.\n")
        _write_marker(marker)
        return

    if _install_pixi(logger) and _run_pixi_install(logger):
        print("\nEnvironment is ready.\n")
        _write_marker(marker)
    else:
        print("\nSetup did not complete; it will retry next time.\n")
