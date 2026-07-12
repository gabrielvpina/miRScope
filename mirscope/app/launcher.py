"""Entry point for the ``mirscope-explore`` command: launches the Streamlit app."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_explore(argv: Optional[List[str]] = None) -> int:
    """Launch the MIRSCOPE Explorer (Streamlit). Returns a process exit code."""
    try:
        import streamlit  # noqa: F401
    except ImportError:
        print(
            "Streamlit is not installed. Reinstall MIRSCOPE:  pip install mirscope"
        )
        return 1

    if argv is None:
        argv = sys.argv[1:]  # forward extra streamlit flags (e.g. --server.port)

    main_script = Path(__file__).resolve().parent / "main.py"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(main_script),
        "--theme.base=light",  # light appearance by default
    ]
    if argv:
        command += list(argv)
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(run_explore(sys.argv[1:]))
