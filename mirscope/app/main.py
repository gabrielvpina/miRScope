"""MIRSCOPE interactive UpSet explorer (Streamlit).

Launch with:  mirscope-explore   (or: streamlit run mirscope/app/main.py)
"""
from __future__ import annotations

import streamlit as st

from mirscope.app.data_io import load_matrix
from mirscope.app.plotly_upset import build_upset_figure
from mirscope.app.ui import records_to_table
from mirscope.plotting import intersections_with_members

st.set_page_config(page_title="MIRSCOPE Explorer", layout="wide")

# Base styling: hide the Deploy button and footer, tighten the layout.
_BASE_CSS = """
<style>
[data-testid="stAppDeployButton"], .stAppDeployButton,
[data-testid="stDeployButton"] { display: none !important; }
footer { visibility: hidden; }
.block-container { padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1250px; }
h1 { font-weight: 700; letter-spacing: -0.02em; }
.mirscope-sub { color: #6b7280; font-size: 0.95rem; margin-top: -0.6rem; }
section[data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,0.15); }
[data-testid="stMetricValue"] { font-size: 1.5rem; }
</style>
"""
st.markdown(_BASE_CSS, unsafe_allow_html=True)

_DARK_CSS = """
<style>
.stApp { background-color: #0e1117; color: #e6e6e6; }
section[data-testid="stSidebar"] { background-color: #111722; }
.mirscope-sub { color: #9aa4b2; }
</style>
"""


@st.cache_data(show_spinner="Loading matrix...")
def _cached_matrix(name: str, data: bytes):
    return load_matrix(name, data)


def _sidebar_matrix():
    st.sidebar.header("Data")
    upload = st.sidebar.file_uploader(
        "Presence/absence matrix",
        type=["xlsx", "csv", "parquet"],
        help="The 'output_mode2_matrix_upset.xlsx' produced by a strict run "
        "(or any CSV/Parquet with miRNA_ID as rows and species as columns).",
    )
    if upload is None:
        return None
    return _cached_matrix(upload.name, upload.getvalue())


def _render(matrix, dark: bool) -> None:
    species = list(matrix.columns)

    st.sidebar.header("Filters")
    selected = st.sidebar.multiselect(
        "Species",
        species,
        default=species,
        help="Restrict the analysis to these species. Only intersections that "
        "involve the selected species are shown.",
    )
    max_degree = max(2, len(species))
    min_degree = st.sidebar.number_input(
        "min-degree",
        min_value=1,
        max_value=max_degree,
        value=1,
        step=1,
        help="Minimum number of species an intersection must span. 1 shows "
        "everything; set to 2 to hide species-specific groups and keep only "
        "intersections shared between species.",
    )
    top_n = st.sidebar.number_input(
        "top-n",
        min_value=0,
        value=15,
        step=1,
        help="Show only the N largest intersections (by number of miRNAs). "
        "Set to 0 to show all of them.",
    )
    min_size = st.sidebar.number_input(
        "min-size",
        min_value=1,
        value=1,
        step=1,
        help="Minimum number of miRNAs (clusters) an intersection must contain "
        "to be displayed.",
    )

    if len(selected) < 2:
        st.info("Select at least two species in the sidebar.")
        return

    sub = matrix[selected]
    sub = sub[sub.any(axis=1)]
    top = None if top_n == 0 else int(top_n)

    records, total = intersections_with_members(
        sub, min_size=int(min_size), min_degree=int(min_degree), top_n=top
    )
    if not records:
        st.warning("No intersection passes the current filters.")
        return

    shown_species = sorted({s for record in records for s in record["species"]})
    col1, col2, col3 = st.columns(3)
    col1.metric("Species shown", len(shown_species))
    col2.metric("Intersections", f"{len(records)} / {total}")
    col3.metric("Clusters (matrix)", f"{matrix.shape[0]:,}")

    figure = build_upset_figure(
        records, selected, title="miRNA intersections", dark=dark
    )
    st.plotly_chart(figure, use_container_width=True, theme=None)

    st.subheader("Intersections")
    table = records_to_table(records)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button(
        "Download intersections (CSV)",
        table.to_csv(index=False).encode(),
        "mirscope_intersections.csv",
        "text/csv",
    )


# --- appearance (light default) -----------------------------------------
st.sidebar.header("Appearance")
dark = st.sidebar.toggle(
    "Dark mode",
    value=False,
    help="Switch between light (default) and dark appearance.",
)
if dark:
    st.markdown(_DARK_CSS, unsafe_allow_html=True)

st.title("MIRSCOPE Explorer")
st.markdown(
    '<p class="mirscope-sub">Interactive UpSet exploration of miRNA conservation. '
    "Adjust the filters on the left; hover a bar to see its shared miRNA_IDs.</p>",
    unsafe_allow_html=True,
)

matrix = _sidebar_matrix()
if matrix is None:
    st.info("Upload a presence/absence matrix in the sidebar to begin.")
else:
    _render(matrix, dark)
