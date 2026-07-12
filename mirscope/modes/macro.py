"""Mode 1 — broad conservation grouped purely by seed identity."""
from __future__ import annotations

import os
import time
from typing import Optional, Sequence

from ..config import MacroOutputs
from ..exporter import ExcelExporter, build_macro_dataframe
from ..grouping import SeedGrouper
from ..loader import FastaLoader
from ..logging_config import get_logger
from ..matrix import BooleanMatrixBuilder
from ..plotting import UpSetPlotter


class MacroMode:
    """Group miRNAs by seed and report cross-species conservation, no alignment."""

    def __init__(self, outputs: MacroOutputs | None = None) -> None:
        self.outputs = outputs or MacroOutputs()
        self.logger = get_logger("mode.macro")
        self.loader = FastaLoader()
        self.grouper = SeedGrouper()
        self.matrix_builder = BooleanMatrixBuilder()
        self.exporter = ExcelExporter()
        self.plotter = UpSetPlotter()

    def run(
        self,
        data_folder: str,
        input_files: Optional[Sequence[str]] = None,
        output_dir: str = ".",
        top_n: Optional[int] = None,
        min_size: int = 1,
    ) -> None:
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
            return

        seed_species = self.grouper.group_species_by_seed(mirnas)

        self.logger.info("Exporting detailed macro table...")
        macro_df = build_macro_dataframe(mirnas)
        self.exporter.save_grouped(
            macro_df,
            os.path.join(output_dir, self.outputs.excel_detailed),
            group_column="Seed",
        )

        self.logger.info("Building boolean matrix...")
        matrix = self.matrix_builder.from_seed_species(seed_species)
        if matrix.empty:
            self.logger.warning("Not enough data to build the plot.")
            return

        self.logger.info("Drawing UpSet plot...")
        self.plotter.plot(
            matrix,
            os.path.join(output_dir, self.outputs.upset_plot),
            "Evolutionary Conservation by Seed Family (Macro Mode)",
            top_n=top_n,
            min_size=min_size,
        )

        self.logger.info("Macro analysis finished in %.2fs.", time.perf_counter() - start)
