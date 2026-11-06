<p align="center">
  <img src="mirscope/assets/logo.svg" alt="miRScope" width="440">
</p>

<p align="center">
  <b>Comparative analysis and evolutionary conservation of microRNAs (miRNAs).</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.4.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="python">
  <img src="https://img.shields.io/badge/aligner-MAFFT-3fb950" alt="MAFFT">
  <img src="https://img.shields.io/badge/output-SQLite%20%2B%20JSON-6e7781" alt="output">
  <img src="https://img.shields.io/badge/reference-miRBase-orange" alt="miRBase">
</p>

## Introduction

MIRSCOPE compares miRNAs across species centered on the **seed region**
(nucleotides 2–8), the functionally most important part for target recognition.
It groups miRNAs by their seed and reports which species share them, revealing
how conserved (evolutionarily widespread) each miRNA family is.

It offers two analysis modes:

- **macro** — broad conservation. Groups miRNAs purely by exact seed identity,
  without alignment. Fast; ideal for a quick view of large family spread.
- **strict** — orthology by cohesion. Aligns each seed family with **MAFFT** and
  applies a base-to-base identity cutoff (default **85%**) to isolate true
  mature orthologs, while still rescuing species-specific miRNAs.

The full miRBase reference database ships inside the package
(`mirscope/data/`, ~259 species), so analyses work out of the box. Results are
written as a **SQLite database** and a **JSON file** holding every family, its
member miRNAs and the species intersections (UpSet-ready); strict mode also
writes the MAFFT alignments as FASTA. Every run also produces a **self-contained
interactive HTML report** (open it with a double click, works offline).

## Installation

Requires **Python 3.8+**. The only Python dependency is Biopython.

```bash
git clone https://github.com/gabrielvpina/miRScope.git
cd miRScope
pip install .
```

### MAFFT (strict mode only)

MAFFT is a native binary that `pip` cannot install. Install it with your system
package manager — `mirscope` finds it on the `PATH`:

```bash
brew install mafft                 # macOS
sudo apt install mafft             # Debian/Ubuntu
conda install -c bioconda mafft    # conda/mamba
```

To use a MAFFT that is not on the `PATH`, set `MIRSCOPE_MAFFT=/path/to/mafft`.
The macro mode does not need MAFFT.

### Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest mirscope/test -v
```

### Docker

A `Dockerfile` is included. MAFFT is installed from the OS repositories, so the
image is fully self-contained.

```bash
docker build -t mirscope .
docker run --rm -v "$PWD/results:/app/results" mirscope strict --out results
```

## Usage

```
mirscope {macro,strict} [cutoff] [--data DIR] [--input FASTA ...] [--out DIR]
                        [--top-n N] [--min-size N] [--min-degree N] [-v]
```

| Argument | Description | Default |
|---|---|---|
| `mode` | `macro` (broad conservation) or `strict` (orthology by cohesion) | — |
| `cutoff` | Identity cutoff percent (strict mode only) | `85` |
| `--data DIR` | Reference FASTA folder. Resolves to the **bundled** miRBase database if omitted | bundled `mirscope/data/` |
| `--input FASTA ...` | One or more input FASTA files added to the analysis, compared against the reference | — |
| `--out DIR` | Output directory (created if missing) | current directory |
| `--top-n N` | Keep only the N largest intersections in the UpSet view (`0` = all) | `10` |
| `--min-size N` | Keep only intersections with at least N families | `1` |
| `--min-degree N` | Keep only intersections spanning at least N species (`2` = shared-only) | `1` |
| `-v`, `--verbose` | Enable DEBUG-level logging | off |

The filter flags (`--top-n`, `--min-size`, `--min-degree`) only select which
intersections form the **UpSet view** (`intersections.upset` in the JSON,
`intersection.upset_rank` in SQLite). The full intersection tables always keep
every row.

### Input data

- The reference database (`--data`) is one FASTA file per species. The bundled
  default already contains the full miRBase.
- Your own `--input` files must be named `mirna_Genus_species.fasta`
  (e.g. `mirna_Homo_sapiens.fasta`) so the species is recognized; otherwise the
  file name is used as the species label.

### Examples

```bash
# Broad conservation across the whole bundled reference
mirscope macro --out results

# Strict orthology, adding your own species, showing only shared intersections
mirscope strict --input mirna_My_species.fasta --out results --min-degree 2

# Strict with a stricter cutoff (95%) and the top 40 intersections
mirscope strict 95 --out results --top-n 40
```

## Outputs

All files are written to `--out` (default: current directory).

| Mode | Files |
|---|---|
| macro | `mirscope_macro.db`, `mirscope_macro.json`, `mirscope_macro.html` |
| strict | `mirscope_strict.db`, `mirscope_strict.json`, `mirscope_strict.html`, `output_mode2_alignments.fasta` |

A **family** is a seed family in macro mode (id = seed) or an orthologous
cohesion cluster in strict mode (id = `<seed>_Clust_<n>`). An **intersection**
is a set of species together with the families present in exactly those
species (ids `I1`, `I2`, … sorted by size).

### SQLite schema

| Table | Content |
|---|---|
| `run` | One row: mode, version, timestamp, parameters (cutoff, data dir, inputs, UpSet filters), counts, failed seeds |
| `species` | Every species in the analysis |
| `family` | `id`, `seed`, `species_count`, `member_count` |
| `mirna` | One row per family member: `family_id`, `mirna_id`, `species`, `sequence`, `aligned_sequence` (strict), `source_file` |
| `presence` | Long-form presence/absence matrix: (`family_id`, `species`) |
| `intersection` | `id`, `degree` (species), `size` (families), `upset_rank` (NULL if filtered out of the UpSet view) |
| `intersection_species` / `intersection_family` | Members of each intersection |

Example — seed families shared by at least 10 species:

```bash
sqlite3 mirscope_macro.db \
  "SELECT id, species_count FROM family WHERE species_count >= 10 ORDER BY species_count DESC"
```

### JSON structure

```json
{
  "run": {"tool": "mirscope", "version": "...", "mode": "strict", "created_at": "...",
          "parameters": {"cutoff": 85.0, "data_dir": "...", "inputs": [],
                         "top_n": 10, "min_size": 1, "min_degree": 1},
          "counts": {"mirnas": 0, "species": 0, "families": 0, "intersections": 0},
          "failed_seeds": []},
  "species": ["Homo sapiens", "..."],
  "families": [{"id": "GAGAUUC_Clust_1", "seed": "GAGAUUC", "species": ["..."],
                "members": [{"id": "...", "species": "...", "sequence": "...",
                             "source_file": "...", "aligned": "..."}]}],
  "intersections": {
    "all": [{"id": "I1", "species": ["..."], "degree": 2, "size": 40, "families": ["..."]}],
    "upset": {"ids": ["I1", "..."], "total_matching": 120}
  }
}
```

### HTML report

`mirscope_<mode>.html` is a single file with the JSON, CSS, D3 and all scripts
inlined. Tabs:

- **Overview** — key numbers, run parameters, conservation spectrum (families
  per number of species) and the most conserved families.
- **Intersections** — interactive UpSet plot; `--top-n`, `--min-size` and
  `--min-degree` are the defaults and can be changed live, plus a "must include
  species" filter. Click a column to list its families. SVG/PNG/CSV export.
- **Your input** (only with `--input`) — for each input species: conserved vs.
  new families (absent from every reference species), conservation profile,
  closest reference species (shared families or Jaccard) and CSV tables.
- **Families** — searchable, sortable table; expanding a row shows a sequence
  logo of its members, each miRNA with the seed (nt 2–8) highlighted and, in
  strict mode, the aligned sequence.
- **Species** — families per species (shared vs. species-specific), a pairwise
  heatmap of shared families (counts or Jaccard index), ordered by UPGMA
  clustering of the Jaccard distance with its dendrogram.
- **Sequences** — sequence logos of the seed region or the whole mature miRNA
  for all, shared and species-specific families (each family weighs the same),
  plus the per-position composition.
- **Cutoff** (strict only) — re-runs the cohesion clustering in the browser
  from the stored alignments for every cutoff from 50% to 100%: clusters,
  shared and species-specific counts per cutoff, and the seed families that
  change the most. At the run cutoff it reproduces the report exactly.

Tabs can be deep-linked with a hash, e.g. `mirscope_macro.html#upset`.

The page is assembled by `mirscope/report.py` from modular components in
`mirscope/components/`: `shell.html` (skeleton with `{{MS_*}}` placeholders),
`base.css` (design system — colours are custom properties in `:root`),
`common.js` (shared helpers and data model) and one `section_*.js` per tab.
D3 v7.9.0 is vendored in `mirscope/vendor/` (ISC licence).

## Authorship and citation

Developed by Tatyana Chagas Moura / BiovirLab.
