"""Multiple sequence alignment of seed families using the external MAFFT tool."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from io import StringIO
from pathlib import Path
from typing import List, Optional

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from .config import MafftConfig
from .logging_config import get_logger

MAFFT_ENV_VAR = "MIRSCOPE_MAFFT"


def resolve_mafft(executable: str) -> Optional[str]:
    """Resolve the MAFFT executable path.

    Search order: ``MIRSCOPE_MAFFT`` env var, then the global PATH (which the
    CLI seeds via :func:`mirscope.bootstrap.activate_pixi_env`), then the pixi
    environment bin directories directly.
    """
    override = os.environ.get(MAFFT_ENV_VAR)
    if override:
        if os.path.isfile(override):
            return override
        located = shutil.which(override)
        if located:
            return located

    on_path = shutil.which(executable)
    if on_path:
        return on_path

    # Imported lazily to avoid a circular import at module load time.
    from .bootstrap import pixi_env_bin_dirs

    for bin_dir in pixi_env_bin_dirs():
        candidate = Path(bin_dir) / executable
        if candidate.exists():
            return str(candidate)
    return None


class MafftAligner:
    """Align seed families with MAFFT, anchored on the shared seed sequence.

    Two synthetic anchor records carrying the seed sequence are supplied both
    as a ``--seed`` guide and in the input, then removed from the result. Seeds
    that fail to align are recorded in :attr:`failed_seeds` for reporting.
    """

    def __init__(self, config: Optional[MafftConfig] = None) -> None:
        self.config = config or MafftConfig()
        self.logger = get_logger("alignment")
        self.failed_seeds: List[str] = []

    def resolve_executable(self) -> Optional[str]:
        """Return the usable MAFFT path (env var, PATH, or pixi env)."""
        return resolve_mafft(self.config.executable)

    def is_available(self) -> bool:
        """Return ``True`` if a usable MAFFT executable can be found."""
        return self.resolve_executable() is not None

    def align(
        self, records: List[SeqRecord], seed_sequence: str
    ) -> Optional[List[SeqRecord]]:
        """Align ``records`` for one seed family.

        Returns the aligned records (anchors stripped), the input unchanged when
        there are fewer than two records, or ``None`` if MAFFT failed.
        """
        if len(records) < 2:
            return records

        executable = self.resolve_executable()
        if executable is None:
            self.logger.error(
                "MAFFT not found for seed '%s' (checked %s, PATH, and pixi env).",
                seed_sequence,
                MAFFT_ENV_VAR,
            )
            self.failed_seeds.append(seed_sequence)
            return None

        anchor_a = SeqRecord(Seq(seed_sequence), id="ANCHOR_A", description="")
        anchor_b = SeqRecord(Seq(seed_sequence), id="ANCHOR_B", description="")
        seed_path: Optional[str] = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".fasta", delete=False
            ) as seed_file:
                SeqIO.write([anchor_a, anchor_b], seed_file, "fasta")
                seed_path = seed_file.name

            all_records = [anchor_a, anchor_b] + records
            fasta_input = "\n".join(f">{rec.id}\n{str(rec.seq)}" for rec in all_records)

            command = [
                executable,
                "--seed",
                seed_path,
                *self.config.extra_args,
                "-",
            ]
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(input=fasta_input.encode())

            if process.returncode != 0:
                raise RuntimeError(stderr.decode("utf-8"))

            aligned = list(SeqIO.parse(StringIO(stdout.decode("utf-8")), "fasta"))
            return [rec for rec in aligned if "anchor" not in rec.id.lower()]

        except Exception as error:  # noqa: BLE001 - report and continue
            self.logger.error("MAFFT failed for seed '%s': %s", seed_sequence, error)
            self.failed_seeds.append(seed_sequence)
            return None
        finally:
            if seed_path and os.path.exists(seed_path):
                os.remove(seed_path)
