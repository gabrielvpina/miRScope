"""Native UpSet plot rendering for the boolean presence/absence matrices."""
from __future__ import annotations

from typing import Optional

import matplotlib

matplotlib.use("Agg")  # headless-safe backend

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .logging_config import get_logger  # noqa: E402


def active_species(species, intersections):
    """Return the species that appear in at least one intersection.

    ``species`` is the ordered list of species (matrix columns); ``intersections``
    is an iterable of boolean tuples aligned to ``species``. Species that are
    absent from every intersection are dropped, so the plot does not render
    empty rows.
    """
    intersections = list(intersections)
    return [
        name
        for i, name in enumerate(species)
        if any(index[i] for index in intersections)
    ]


def compute_intersections(
    boolean_df: pd.DataFrame,
    min_size: int = 1,
    min_degree: int = 1,
    top_n: Optional[int] = None,
):
    """Aggregate a boolean matrix into filtered, sorted intersections.

    Returns ``(grouped, shown_species, total)`` where ``grouped`` is a Series
    indexed by boolean membership tuples (value = intersection size), sorted
    descending; ``shown_species`` are the species appearing in ``grouped``; and
    ``total`` is the number of intersections before the ``top_n`` cut. If nothing
    remains, ``grouped`` is ``None``.
    """
    if boolean_df.empty:
        return None, [], 0
    species = boolean_df.columns.tolist()
    if len(species) < 2:
        return None, [], 0

    grouped = boolean_df.groupby(species).size()
    grouped = grouped[grouped >= max(1, min_size)]
    if min_degree > 1:
        grouped = grouped[grouped.index.map(lambda index: sum(index) >= min_degree)]
    grouped = grouped.sort_values(ascending=False)
    total = len(grouped)

    if top_n is not None and top_n > 0:
        grouped = grouped.head(top_n)
    if grouped.empty:
        return None, [], total

    return grouped, active_species(species, grouped.index), total


def intersections_with_members(
    boolean_df: pd.DataFrame,
    min_size: int = 1,
    min_degree: int = 1,
    top_n: Optional[int] = None,
):
    """Aggregate intersections keeping the member cluster ids of each one.

    Returns ``(records, total)`` where each record is a dict with keys
    ``species`` (list), ``size`` (int) and ``clusters`` (list of row ids), sorted
    by size descending and filtered by ``min_size``/``min_degree``/``top_n``.
    ``total`` is the count before the ``top_n`` cut.
    """
    if boolean_df.empty:
        return [], 0
    species = list(boolean_df.columns)
    if len(species) < 2:
        return [], 0

    groups: dict = {}
    for cluster_id, row in zip(boolean_df.index, boolean_df.to_numpy()):
        key = tuple(bool(value) for value in row)
        groups.setdefault(key, []).append(cluster_id)

    records = []
    degree_floor = max(1, min_degree)
    for pattern, ids in groups.items():
        degree = sum(pattern)
        if len(ids) < max(1, min_size) or degree < degree_floor:
            continue
        records.append(
            {
                "species": [species[i] for i, flag in enumerate(pattern) if flag],
                "size": len(ids),
                "clusters": list(ids),
            }
        )

    records.sort(key=lambda record: record["size"], reverse=True)
    total = len(records)
    if top_n is not None and top_n > 0:
        records = records[:top_n]
    return records, total


class UpSetPlotter:
    """Draw a fully native UpSet plot from a boolean species matrix."""

    def __init__(self) -> None:
        self.logger = get_logger("plotting")

    def plot(
        self,
        boolean_df: pd.DataFrame,
        output_path: str = "mirscope_upset.png",
        title: str = "Evolutionary Conservation of miRNAs",
        top_n: Optional[int] = None,
        min_size: int = 1,
        min_degree: int = 1,
    ) -> None:
        """Render the UpSet plot to ``output_path`` (see :meth:`build_figure`)."""
        figure = self.build_figure(
            boolean_df, title=title, top_n=top_n, min_size=min_size, min_degree=min_degree
        )
        if figure is None:
            return
        figure.savefig(output_path, bbox_inches="tight", dpi=300, facecolor="white")
        plt.close(figure)
        self.logger.info("UpSet plot written to '%s'.", output_path)

    def build_figure(
        self,
        boolean_df: pd.DataFrame,
        title: str = "Evolutionary Conservation of miRNAs",
        top_n: Optional[int] = None,
        min_size: int = 1,
        min_degree: int = 1,
    ):
        """Build and return the UpSet ``Figure`` (or ``None`` if nothing to plot).

        Filters (plot only — exported tables always keep every row):

        * ``min_size`` — keep intersections with at least that many members.
        * ``min_degree`` — keep intersections spanning at least that many
          species. Use ``2`` to drop species-specific groups and show only the
          intersections *shared between* species.
        * ``top_n`` — keep the N largest intersections (applied last).
        """
        species = boolean_df.columns.tolist()
        grouped, shown_species, total_intersections = compute_intersections(
            boolean_df, min_size=min_size, min_degree=min_degree, top_n=top_n
        )
        if grouped is None:
            self.logger.warning(
                "Nothing to plot (empty, <2 species, or filters removed everything: "
                "min_size=%d, min_degree=%d, top_n=%s).",
                min_size,
                min_degree,
                top_n,
            )
            return None

        num_intersections = len(grouped)
        num_species = len(shown_species)
        if num_intersections < total_intersections:
            self.logger.info(
                "Plotting %d of %d intersections (min_size=%d, min_degree=%d, top_n=%s).",
                num_intersections,
                total_intersections,
                min_size,
                min_degree,
                top_n,
            )

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
        species_reversed = list(reversed(shown_species))
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
        # Padding so the dots on the first/last rows are not clipped.
        matrix_axis.set_ylim(-0.6, num_species - 0.4)
        for spine in ("top", "right", "bottom", "left"):
            matrix_axis.spines[spine].set_visible(False)

        bar_axis.margins(x=0.02)
        return figure
