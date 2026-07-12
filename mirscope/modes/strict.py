"""Mode 2 — strict orthology via MAFFT alignment and cohesion clustering."""
from __future__ import annotations

import os
import time
from typing import Dict, List, Optional, Sequence

from ..alignment import MafftAligner
from ..clustering import CohesionClusterer
from ..config import StrictOutputs
from ..exporter import (
    AlignmentWriter,
    ExcelExporter,
    build_cluster_dataframe,
    build_intersection_dataframe,
)
from ..grouping import SeedGrouper
from ..loader import FastaLoader
from ..logging_config import get_logger
from ..matrix import BooleanMatrixBuilder
from ..plotting import UpSetPlotter


class StrictMode:
    """Align each seed family and isolate true orthologs by an identity cutoff."""

    def __init__(self, cutoff: float, outputs: StrictOutputs | None = None) -> None:
        self.cutoff = cutoff
        self.outputs = outputs or StrictOutputs()
        self.logger = get_logger("mode.strict")
        self.loader = FastaLoader()
        self.grouper = SeedGrouper()
        self.aligner = MafftAligner()
        self.clusterer = CohesionClusterer(cutoff)
        self.matrix_builder = BooleanMatrixBuilder()
        self.exporter = ExcelExporter()
        self.alignment_writer = AlignmentWriter()
        self.plotter = UpSetPlotter()
        self.output_dir = "."
        self.top_n: Optional[int] = None
        self.min_size: int = 1
        self.min_degree: int = 1

    def _out(self, name: str) -> str:
        """Resolve an output file name inside the configured output directory."""
        return os.path.join(self.output_dir, name)

    def run(
        self,
        data_folder: str,
        input_files: Optional[Sequence[str]] = None,
        output_dir: str = ".",
        top_n: Optional[int] = None,
        min_size: int = 1,
        min_degree: int = 1,
    ) -> None:
        self.logger.info("=" * 60)
        self.logger.info("MIRSCOPE — MODE 2 (Strict Orthology by Cohesion)")
        self.logger.info("Identity cutoff: %.1f%%", self.cutoff)
        self.logger.info("=" * 60)

        if not self.aligner.is_available():
            self.logger.error(
                "MAFFT executable not found on PATH; strict mode requires MAFFT."
            )
            return

        self.output_dir = output_dir
        self.top_n = top_n
        self.min_size = min_size
        self.min_degree = min_degree
        os.makedirs(output_dir, exist_ok=True)
        self.logger.info("Output directory: '%s'", os.path.abspath(output_dir))

        self.logger.info("Loading data...")
        mirnas, species = self.loader.load(data_folder, input_files)
        if not mirnas:
            self.logger.error("No data loaded; aborting strict mode.")
            return

        raw_groups = self.grouper.group_records_by_seed(mirnas)
        prepared = self.grouper.prepare_alignment_records(raw_groups)
        self.logger.info("Seed families to process: %d", len(prepared))

        aligned_results = self._align_all(prepared)
        self.alignment_writer.save(aligned_results, self._out(self.outputs.alignments_fasta))

        clusters_by_seed = self._cluster_all(aligned_results, prepared)

        self.logger.info("Exporting detailed cluster table...")
        cluster_df = build_cluster_dataframe(clusters_by_seed)
        self.exporter.save_grouped(
            cluster_df, self._out(self.outputs.clusters_excel), group_column="Cluster_ID"
        )

        self._export_matrix_and_plot(clusters_by_seed)

    # -- internal steps -----------------------------------------------------

    def _align_all(self, prepared: Dict[str, List]) -> Dict[str, List]:
        self.logger.info("Starting MAFFT alignment route...")
        start = time.perf_counter()
        aligned_results: Dict[str, List] = {}
        for seed, records in prepared.items():
            alignment = self.aligner.align(records, seed)
            if alignment:
                aligned_results[seed] = alignment
        elapsed = time.perf_counter() - start
        if self.aligner.failed_seeds:
            self.logger.warning(
                "%d seed family(ies) failed to align and were dropped.",
                len(self.aligner.failed_seeds),
            )
        self.logger.info(
            "Alignments finished in %.2fs (%d families aligned).",
            elapsed,
            len(aligned_results),
        )
        return aligned_results

    def _cluster_all(
        self, aligned_results: Dict[str, List], prepared: Dict[str, List]
    ) -> Dict[str, List]:
        self.logger.info("Running cohesion clustering (all-against-all)...")
        start = time.perf_counter()
        clusters_by_seed: Dict[str, List] = {}
        for seed, alignment in aligned_results.items():
            clusters_by_seed[seed] = self.clusterer.cluster(alignment)

        # Rescue single-member families that skipped alignment.
        rescued = 0
        for seed, records in prepared.items():
            if len(records) == 1:
                clusters_by_seed[seed] = [records]
                rescued += 1
        if rescued:
            self.logger.info(
                "Rescued %d exclusive family(ies) that skipped alignment.", rescued
            )
        self.logger.info(
            "Clustering finished in %.2fs.", time.perf_counter() - start
        )
        return clusters_by_seed

    def _export_matrix_and_plot(self, clusters_by_seed: Dict[str, List]) -> None:
        self.logger.info("Building final boolean matrix...")
        matrix = self.matrix_builder.from_clusters(clusters_by_seed)
        if matrix.empty:
            self.logger.warning("Not enough data to build the matrix and plot.")
            return

        self.exporter.save_formatted(
            matrix, self._out(self.outputs.matrix_excel), keep_index=True
        )

        intersections = build_intersection_dataframe(matrix)
        self.exporter.save_formatted(
            intersections, self._out(self.outputs.intersections_excel)
        )

        self.logger.info("Drawing UpSet plot...")
        self.plotter.plot(
            matrix,
            self._out(self.outputs.upset_plot),
            f"miRNA Orthology - Total Cohesion (Cutoff: {self.cutoff}%)",
            top_n=self.top_n,
            min_size=self.min_size,
            min_degree=self.min_degree,
        )
