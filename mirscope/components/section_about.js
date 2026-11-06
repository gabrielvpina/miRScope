/* ============================================================
   section_about.js — About tab
   Tool description, how to read the modes, output files.
   Exposes: msInitAbout(data)
   ============================================================ */
(function () {
'use strict';

const GITHUB_URL = 'https://github.com/gabrielvpina/miRScope';

function msInitAbout(data) {
  const el = document.getElementById('section-about');
  const mode = data.run.mode;
  el.innerHTML = `
    <div class="ms-about">
      <div class="ms-about__hero">
        ${MS_LOGO ? `<img class="ms-about__logo" src="${MS_LOGO}" alt="miRScope">` : ''}
        <p class="ms-about__tagline">
          Comparative analysis and evolutionary conservation of microRNAs, centred on the
          seed region (nucleotides 2–8).
        </p>
        <span class="ms-pill">v${MS.esc(data.run.version)}</span>
      </div>

      <div class="ms-grid ms-grid--2">
        ${MS.card({
          title: 'macro — broad conservation',
          cls: mode === 'macro' ? 'ms-card--current' : '',
          body: `<p>Groups miRNAs purely by exact seed identity, without alignment. Each
                 <strong>seed family</strong> is reported with the species that carry it.
                 Fast; ideal for a wide view of family spread.</p>`,
        })}
        ${MS.card({
          title: 'strict — orthology by cohesion',
          cls: mode === 'strict' ? 'ms-card--current' : '',
          body: `<p>Aligns each seed family with MAFFT and splits it into
                 <strong>cohesion clusters</strong>: a miRNA joins a cluster only if its
                 identity to <em>every</em> member reaches the cutoff (default 85%).
                 Single-member families are kept as species-specific clusters.</p>`,
        })}
      </div>

      ${MS.card({
        title: 'Reading this report',
        body: `
          <ul class="ms-list">
            <li><strong>Intersection</strong> — a set of species plus the families present in
                <em>exactly</em> those species (UpSet logic). Ids <code>I1</code>, <code>I2</code>, …
                are sorted by size.</li>
            <li><strong>Degree</strong> — the number of species in a family or intersection.</li>
            <li>The UpSet filters only change the view; the data files keep every row.</li>
            <li><strong>Sequence logo</strong> — letter height is the nucleotide frequency, or
                frequency × information content (bits, max 2). The seed (nt 2–8) is shaded.</li>
            <li><strong>Jaccard distance</strong> — 1 − shared / union of the families of two species;
                the species tree joins the closest species first (UPGMA).</li>
            ${mode === 'strict' ? `<li><strong>Cutoff</strong> — the clustering is recomputed in the browser
                from the stored alignments, so other identity thresholds can be explored without re-running.</li>` : ''}
          </ul>`,
      })}

      ${MS.card({
        title: 'Files from this run',
        body: `
          <table class="ms-table">
            <tbody>
              <tr><td><code>mirscope_${mode}.db</code></td><td>SQLite database (tables <code>run</code>, <code>species</code>, <code>family</code>, <code>mirna</code>, <code>presence</code>, <code>intersection</code>, …)</td></tr>
              <tr><td><code>mirscope_${mode}.json</code></td><td>The same data as JSON — this page is built from it</td></tr>
              <tr><td><code>mirscope_${mode}.html</code></td><td>This self-contained report</td></tr>
              ${mode === 'strict' ? '<tr><td><code>output_mode2_alignments.fasta</code></td><td>MAFFT alignments grouped by seed</td></tr>' : ''}
            </tbody>
          </table>`,
      })}

      <p class="ms-about__foot">
        Developed by Tatyana Chagas Moura / BiovirLab ·
        <a href="${GITHUB_URL}" target="_blank" rel="noopener noreferrer">GitHub</a>
      </p>
    </div>`;
}

window.msInitAbout = msInitAbout;
})();
