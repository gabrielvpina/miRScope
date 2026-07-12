"""Interactive UpSet plot built with Plotly (hover shows the member clusters)."""
from __future__ import annotations

from typing import List, Optional, Sequence

import plotly.graph_objects as go
from plotly.subplots import make_subplots

_DARK = "#2e3440"
_BAR = "#3b4252"
_ABSENT = "#dfe3ea"

# Palette-neutral single-hue matrix; kept monochrome to read as one system.


def build_upset_figure(
    records: Sequence[dict],
    all_species: Sequence[str],
    title: str = "miRNA intersections",
    max_clusters_in_hover: int = 25,
) -> Optional[go.Figure]:
    """Return a Plotly UpSet figure, or ``None`` when there is nothing to show.

    ``records`` come from :func:`mirscope.plotting.intersections_with_members`.
    Hovering a bar reveals the species combination, the intersection size and
    the member cluster ids.
    """
    if not records:
        return None

    active = [
        species
        for species in all_species
        if any(species in record["species"] for record in records)
    ]
    if not active:
        return None

    num_intersections = len(records)
    num_species = len(active)
    rank = {species: i for i, species in enumerate(active)}

    def y_of(species: str) -> int:
        # First active species at the top of the matrix.
        return num_species - 1 - rank[species]

    x_values = list(range(num_intersections))
    sizes = [record["size"] for record in records]

    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.06,
    )

    # --- top: intersection-size bars, hover shows only the shared miRNA_IDs
    hover_text = []
    for record in records:
        clusters = record["clusters"]
        shown = "<br>".join(str(cluster) for cluster in clusters[:max_clusters_in_hover])
        if len(clusters) > max_clusters_in_hover:
            shown += f"<br>... (+{len(clusters) - max_clusters_in_hover} more)"
        hover_text.append(f"<b>miRNA_ID</b><br>{shown}")

    figure.add_trace(
        go.Bar(
            x=x_values,
            y=sizes,
            marker_color=_BAR,
            customdata=hover_text,
            hovertemplate="%{customdata}<extra></extra>",
            text=sizes,
            textposition="outside",
            textfont=dict(size=11),
            cliponaxis=False,
        ),
        row=1,
        col=1,
    )

    # --- bottom: membership matrix ---------------------------------------
    background_x, background_y = [], []
    for x_index in x_values:
        for species in active:
            background_x.append(x_index)
            background_y.append(y_of(species))
    figure.add_trace(
        go.Scatter(
            x=background_x,
            y=background_y,
            mode="markers",
            marker=dict(size=13, color=_ABSENT),
            hoverinfo="skip",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    for x_index, record in enumerate(records):
        ys = [y_of(species) for species in record["species"] if species in rank]
        if not ys:
            continue
        if len(ys) > 1:
            figure.add_trace(
                go.Scatter(
                    x=[x_index, x_index],
                    y=[min(ys), max(ys)],
                    mode="lines",
                    line=dict(color=_DARK, width=3),
                    hoverinfo="skip",
                    showlegend=False,
                ),
                row=2,
                col=1,
            )
        combo = " + ".join(record["species"])
        figure.add_trace(
            go.Scatter(
                x=[x_index] * len(ys),
                y=ys,
                mode="markers",
                marker=dict(size=13, color=_DARK),
                hovertemplate=f"{combo}<extra></extra>",
                showlegend=False,
            ),
            row=2,
            col=1,
        )

    # Taller per-species allocation gives more vertical breathing room between
    # the shared points in the membership matrix.
    height = max(480, 300 + num_species * 44)
    figure.update_layout(
        template="simple_white",
        height=height,
        title=dict(text=title, x=0.02, xanchor="left", font=dict(size=18)),
        margin=dict(l=10, r=24, t=64, b=10),
        showlegend=False,
        bargap=0.35,
        hoverlabel=dict(align="left"),
    )
    figure.update_yaxes(title_text="Intersection size", row=1, col=1)
    figure.update_xaxes(showticklabels=False, showgrid=False, row=1, col=1)
    figure.update_xaxes(
        showticklabels=False, showgrid=False, range=[-0.5, num_intersections - 0.5], row=2, col=1
    )
    figure.update_yaxes(
        tickmode="array",
        tickvals=[y_of(species) for species in active],
        ticktext=list(active),
        range=[-0.6, num_species - 0.4],
        showgrid=False,
        row=2,
        col=1,
    )
    return figure
