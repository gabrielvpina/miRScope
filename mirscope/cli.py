"""Command-line interface for MIRSCOPE."""
from __future__ import annotations

import argparse
import logging
from typing import Optional, Sequence

from .bootstrap import ensure_pixi
from .config import DEFAULT_CUTOFF
from .logging_config import get_logger, setup_logging
from .modes.macro import MacroMode
from .modes.strict import StrictMode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mirscope",
        description="MIRSCOPE - microRNA conservation and orthology pipeline",
    )
    parser.add_argument(
        "mode",
        choices=["macro", "strict"],
        help="Analysis mode: 'macro' (Mode 1) or 'strict' (Mode 2).",
    )
    parser.add_argument(
        "cutoff",
        type=float,
        nargs="?",
        default=DEFAULT_CUTOFF,
        help=f"Identity cutoff percent for strict mode (default: {DEFAULT_CUTOFF}). "
        "Ignored in macro mode.",
    )
    parser.add_argument(
        "--data",
        default="data",
        help="Reference folder with the FASTA database (default: 'data').",
    )
    parser.add_argument(
        "--input",
        nargs="+",
        metavar="FASTA",
        help="One or more input FASTA files to add to the analysis, compared "
        "against the reference database in --data. Each file must be named "
        "'mirna_Genus_species.fasta' (e.g. 'mirna_Homo_sapiens.fasta') so the "
        "species is recognised; otherwise the file name is used as the species.",
    )
    parser.add_argument(
        "--out",
        default=".",
        metavar="DIR",
        help="Directory where output files are written (created if missing; "
        "default: current directory).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level)

    # First-run only: make sure pixi (and thus the dependencies) is set up.
    # Best-effort — must never break the actual pipeline.
    try:
        ensure_pixi()
    except Exception as error:  # noqa: BLE001
        get_logger("bootstrap").debug("Bootstrap check skipped: %s", error)

    if args.mode == "macro":
        MacroMode().run(args.data, args.input, args.out)
    else:
        StrictMode(args.cutoff).run(args.data, args.input, args.out)


if __name__ == "__main__":
    main()
