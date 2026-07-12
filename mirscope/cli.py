"""Command-line interface for MIRSCOPE."""
from __future__ import annotations

import argparse
import logging
from typing import Optional, Sequence

from .bootstrap import activate_pixi_env, ensure_pixi
from .config import DEFAULT_CUTOFF, packaged_data_dir
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
        default=None,
        help="Reference folder with the FASTA database. Defaults to the "
        "reference database bundled inside the package (always resolvable, "
        "in editable and wheel installs alike). Pass a path to override it.",
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
        "--top-n",
        type=int,
        default=10,
        metavar="N",
        help="Show only the N largest intersections in the UpSet plot "
        "(default: 10; use 0 for all). Affects the plot only; exported tables "
        "keep everything.",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=1,
        metavar="N",
        help="Show only intersections with at least N members in the UpSet plot "
        "(default: 1). Affects the plot only.",
    )
    parser.add_argument(
        "--min-degree",
        type=int,
        default=1,
        metavar="N",
        help="Show only intersections spanning at least N species in the UpSet "
        "plot (default: 1). Use 2 to hide species-specific groups and show only "
        "intersections shared between species. Affects the plot only.",
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

    # Technique 2: put the pixi env bin (with MAFFT) on PATH for this process,
    # so the plain `mirscope` command works outside `pixi run`.
    activate_pixi_env()

    # First-run only: make sure pixi (and thus the dependencies) is set up.
    # Best-effort — must never break the actual pipeline.
    try:
        ensure_pixi()
    except Exception as error:  # noqa: BLE001
        get_logger("bootstrap").debug("Bootstrap check skipped: %s", error)

    # Default to the bundled reference database, resolved via the package path
    # so it works from any working directory and in wheel installs.
    data_folder = args.data if args.data else str(packaged_data_dir())

    if args.mode == "macro":
        MacroMode().run(
            data_folder, args.input, args.out, args.top_n, args.min_size, args.min_degree
        )
    else:
        StrictMode(args.cutoff).run(
            data_folder, args.input, args.out, args.top_n, args.min_size, args.min_degree
        )


if __name__ == "__main__":
    main()
