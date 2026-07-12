"""Native UpSet plot rendering for the boolean presence/absence matrices."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless-safe backend

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .logging_config import get_logger  # noqa: E402


class UpSetPlotter:
    """Draw a fully native UpSet plot from a boolean species matrix."""

    def __init__(self) -> None:
        self.logger = get_logger("plotting")

    def plot(
        self,
        boolean_df: pd.DataFrame,
        output_path: str = "mirscope_upset.png",
        title: str = "Evolutionary Conservation of miRNAs",
    ) -> None:
        """Render the UpSet plot to ``output_path``."""
        if boolean_df.empty:
            self.logger.warning("Boolean matrix is empty; no plot generated.")
            return

        species = boolean_df.columns.tolist()
        if len(species) < 2:
            self.logger.warning(
                "Only species '%s' formed clusters; UpSet plot needs at least 2.",
                species[0],
            )
            return

        grouped = boolean_df.groupby(species).size()
        grouped = grouped[grouped > 0].sort_values(ascending=False)

        num_intersections = len(grouped)
        num_species = len(species)

        width = max(10.0, num_intersections * 0.7)
        height = max(6.0, (num_species * 0.5) + 4.0)

        figure = plt.figure(figsize=(width, height))
        grid = figure.add_gridspec(
            2, 1, height_ratios=[3, max(1, num_species * 0.4)], hspace=0.05
        )
        bar_axis = figure.add_subplot(grid[0])
        matrix_axis = figure.add_subplot(grid[1], sharex=bar_axis)

        x_positions = np.arange(num_intersections)
        counts = grouped.values

        # Intersection size bars.
        bar_axis.bar(x_positions, counts, color="#404040", width=0.6, zorder=3)
        bar_axis.grid(axis="y", linestyle="--", alpha=0.3, zorder=0)
        for i, count in enumerate(counts):
            bar_axis.text(
                i,
                count + (max(counts) * 0.02),
                str(count),
                ha="center",
                va="bottom",
                fontweight="bold",
                fontsize=10,
            )
        bar_axis.set_title(title, fontsize=16, pad=20, fontweight="bold")
        bar_axis.set_ylabel("Intersection Size", fontsize=12)
        for spine in ("top", "right", "bottom"):
            bar_axis.spines[spine].set_visible(False)
        bar_axis.tick_params(
            axis="x", which="both", bottom=False, top=False, labelbottom=False
        )

        # Membership matrix (dots).
        species_reversed = list(reversed(species))
        y_positions = np.arange(num_species)
        matrix_axis.grid(axis="y", linestyle="-", color="whitesmoke", zorder=0)

        for x_index, intersection in enumerate(grouped.index):
            filled_y = []
            for y_index, current_species in enumerate(species_reversed):
                original_index = species.index(current_species)
                if intersection[original_index]:
                    matrix_axis.plot(
                        x_index, y_index, marker="o", color="black", markersize=14, zorder=5
                    )
                    filled_y.append(y_index)
                else:
                    matrix_axis.plot(
                        x_index, y_index, marker="o", color="#E0E0E0", markersize=14, zorder=4
                    )
            if len(filled_y) > 1:
                matrix_axis.plot(
                    [x_index, x_index],
                    [min(filled_y), max(filled_y)],
                    color="black",
                    lw=3.5,
                    zorder=3,
                )

        matrix_axis.set_yticks(y_positions)
        matrix_axis.set_yticklabels(species_reversed, fontsize=12)
        matrix_axis.set_xticks([])
        for spine in ("top", "right", "bottom", "left"):
            matrix_axis.spines[spine].set_visible(False)

        plt.margins(x=0.02)
        plt.savefig(output_path, bbox_inches="tight", dpi=300, facecolor="white")
        plt.close(figure)
        self.logger.info(
            "UpSet plot written to '%s' (%d intersections).", output_path, num_intersections
        )
