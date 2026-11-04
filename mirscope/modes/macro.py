"""Mode 1 — broad conservation grouped purely by seed identity."""
from __future__ import annotations

import os
import time
from typing import Optional, Sequence

from ..config import MacroOutputs
from ..loader import FastaLoader
from ..logging_config import get_logger
from ..results import build_result, macro_families
from ..storage import ResultStore


class MacroMode:
    """Group miRNAs by seed and report cross-species conservation, no alignment."""

    def __init__(self, outputs: MacroOutputs | None = None) -> None:
        self.outputs = outputs or MacroOutputs()
        self.logger = get_logger("mode.macro")
        self.loader = FastaLoader()
        self.store = ResultStore()

    def run(
        self,
        data_folder: str,
        input_files: Optional[Sequence[str]] = None,
        output_dir: str = ".",
        top_n: Optional[int] = None,
        min_size: int = 1,
        min_degree: int = 1,
    ) -> bool:
        """Run the analysis and write the outputs. Returns ``True`` on success."""
        self.logger.info("=" * 60)
        self.logger.info("MIRSCOPE — MODE 1 (Broad Conservation by Seed)")
        self.logger.info("=" * 60)
        start = time.perf_counter()

        os.makedirs(output_dir, exist_ok=True)
        self.logger.info("Output directory: '%s'", os.path.abspath(output_dir))

        self.logger.info("Loading data...")
        mirnas, species = self.loader.load(data_folder, input_files)
        if not mirnas:
            self.logger.error("No data loaded; aborting macro mode.")
            return False

        families = macro_families(mirnas)
        self.logger.info("Identified %d seed family(ies).", len(families))

        payload = build_result(
            "macro",
            mirnas,
            species,
            families,
            data_dir=data_folder,
            inputs=input_files,
            top_n=top_n,
            min_size=min_size,
            min_degree=min_degree,
        )
        self.logger.info(
            "Found %d species intersection(s).", payload["run"]["counts"]["intersections"]
        )
        self.store.save(
            payload,
            os.path.join(output_dir, self.outputs.sqlite),
            os.path.join(output_dir, self.outputs.json),
        )

        self.logger.info("Macro analysis finished in %.2fs.", time.perf_counter() - start)
        return True
