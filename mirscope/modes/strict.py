"""Mode 2 — strict orthology via MAFFT alignment and cohesion clustering."""
from __future__ import annotations

import os
import time
from typing import Dict, List, Optional, Sequence

from ..alignment import MAFFT_ENV_VAR, MafftAligner
from ..clustering import CohesionClusterer
from ..config import StrictOutputs
from ..exporter import AlignmentWriter
from ..grouping import SeedGrouper
from ..loader import FastaLoader
from ..logging_config import get_logger
from ..results import build_result, strict_families
from ..storage import ResultStore

MAFFT_INSTALL_HINT = (
    "Strict mode requires the MAFFT aligner, which was not found. Install it with "
    "one of:\n"
    "    brew install mafft                 (macOS)\n"
    "    sudo apt install mafft             (Debian/Ubuntu)\n"
    "    conda install -c bioconda mafft    (conda/mamba)\n"
    f"or point {MAFFT_ENV_VAR} at an existing executable "
    f"(e.g. export {MAFFT_ENV_VAR}=/path/to/mafft)."
)


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
        self.alignment_writer = AlignmentWriter()
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
        self.logger.info("MIRSCOPE — MODE 2 (Strict Orthology by Cohesion)")
        self.logger.info("Identity cutoff: %.1f%%", self.cutoff)
        self.logger.info("=" * 60)
        start = time.perf_counter()

        if not self.aligner.is_available():
            self.logger.error(MAFFT_INSTALL_HINT)
            return False

        os.makedirs(output_dir, exist_ok=True)
        self.logger.info("Output directory: '%s'", os.path.abspath(output_dir))

        self.logger.info("Loading data...")
        mirnas, species = self.loader.load(data_folder, input_files)
        if not mirnas:
            self.logger.error("No data loaded; aborting strict mode.")
            return False

        raw_groups = self.grouper.group_records_by_seed(mirnas)
        prepared = self.grouper.prepare_alignment_records(raw_groups)
        self.logger.info("Seed families to process: %d", len(prepared))

        aligned_results = self._align_all(prepared)
        self.alignment_writer.save(
            aligned_results, os.path.join(output_dir, self.outputs.alignments_fasta)
        )

        clusters_by_seed = self._cluster_all(aligned_results, prepared)
        families = strict_families(clusters_by_seed, mirnas)
        self.logger.info("Built %d orthologous cluster(s).", len(families))

        payload = build_result(
            "strict",
            mirnas,
            species,
            families,
            data_dir=data_folder,
            inputs=input_files,
            cutoff=self.cutoff,
            top_n=top_n,
            min_size=min_size,
            min_degree=min_degree,
            failed_seeds=self.aligner.failed_seeds,
        )
        self.logger.info(
            "Found %d species intersection(s).", payload["run"]["counts"]["intersections"]
        )
        self.store.save(
            payload,
            os.path.join(output_dir, self.outputs.sqlite),
            os.path.join(output_dir, self.outputs.json),
        )

        self.logger.info("Strict analysis finished in %.2fs.", time.perf_counter() - start)
        return True

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
