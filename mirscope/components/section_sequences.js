/* ============================================================
   section_sequences.js — Sequences tab
   Sequence logos of the seed region (or the whole mature miRNA)
   for all families, families shared across species and
   species-specific families, so their composition can be compared.
   Each family weighs the same, however many members it has.
   Exposes: msInitSequences(data)
   ============================================================ */
(function () {
'use strict';

const REGIONS = {
  seed:   { label: 'Seed region (nt 1–9)', len: 9,  shade: [1, 7] },
  mature: { label: 'Mature miRNA (nt 1–24)', len: 24, shade: [1, 7] },
};

let state;

function msInitSequences(data) {
  const el = document.getElementById('section-sequences');
  state = { region: 'seed', unit: 'prob', minShared: 2, species: '' };
  const maxDeg = data.families.reduce((m, f) => Math.max(m, f.degree), 1);

  el.innerHTML = `
    <header class="ms-hero ms-hero--compact">
      <div>
        <h1 class="ms-hero__title">Sequences</h1>
        <p class="ms-hero__sub">
          Nucleotide composition per position. The seed (nt 2–8) is
          <span class="ms-seq"><span class="ms-seq__seed">shaded</span></span>.
          Every ${data.familyLabel} counts once (its members share its weight), so large
          paralog families do not dominate. Letter height = frequency (or frequency × information, in bits:
          seeds differ between families, so the information across many families is low).
        </p>
      </div>
    </header>

    <div class="ms-controls">
      <label class="ms-field">Region
        <select id="sq-region">${Object.entries(REGIONS).map(([k, r]) => `<option value="${k}">${r.label}</option>`).join('')}</select>
      </label>
      <label class="ms-field">Scale
        <select id="sq-unit"><option value="prob">Frequency</option><option value="bits">Information (bits)</option></select>
      </label>
      <label class="ms-field">"Shared" means ≥ N species
        <input type="number" id="sq-min" min="2" max="${Math.max(2, maxDeg)}" value="2">
      </label>
      <label class="ms-field">Species
        <select id="sq-species">
          <option value="">All species</option>
          ${data.species.map(s => `<option value="${MS.esc(s)}">${MS.esc(s)}</option>`).join('')}
        </select>
      </label>
    </div>

    <div class="ms-grid ms-grid--3">
      ${['all', 'shared', 'excl'].map(k => MS.card({
        title: `<span id="sq-title-${k}"></span>`,
        subtitle: `<span id="sq-sub-${k}"></span>`,
        actions: MS.exportButtons('sq-logo-' + k),
        body: `<div id="sq-logo-${k}" class="ms-chart ms-chart--scroll"></div>`,
      })).join('')}
    </div>

    ${MS.card({
      title: 'Composition per position',
      subtitle: 'Frequency of each nucleotide (shared vs. species-specific). Large differences point to positions under constraint.',
      body: '<div id="sq-table"></div>',
    })}
  `;

  const $ = s => el.querySelector(s);
  $('#sq-region').addEventListener('change', e => { state.region = e.target.value; draw(data); });
  $('#sq-unit').addEventListener('change', e => { state.unit = e.target.value; draw(data); });
  $('#sq-min').addEventListener('input', e => { const v = +e.target.value; if (v >= 2) { state.minShared = v; draw(data); } });
  $('#sq-species').addEventListener('change', e => { state.species = e.target.value; draw(data); });

  const cap = k => () => `${MS.captionPrefix(data)} · ${groupLabel(k)} · ${REGIONS[state.region].label}` +
    ` · ${state.unit === 'bits' ? 'bits' : 'frequency'}` + (state.species ? ` · ${state.species}` : '');
  MS.bindExports(el, 'mirscope_' + data.run.mode, {
    'sq-logo-all': cap('all'), 'sq-logo-shared': cap('shared'), 'sq-logo-excl': cap('excl'),
  });
  draw(data);
}

function groupLabel(k) {
  return { all: 'all families', shared: `shared (≥ ${state.minShared} species)`, excl: 'species-specific' }[k];
}

function draw(data) {
  const region = REGIONS[state.region];
  const groups = { all: [], shared: [], excl: [] };
  data.families.forEach(f => {
    if (state.species && !f.species.includes(state.species)) return;
    groups.all.push(f);
    if (f.degree >= state.minShared) groups.shared.push(f);
    else if (f.degree === 1) groups.excl.push(f);
  });

  const columns = {};
  Object.entries(groups).forEach(([k, fams]) => {
    const cols = MS.logoColumns(region.len);
    fams.forEach(f => {
      const members = state.species ? f.members.filter(m => m.species === state.species) : f.members;
      MS.logoAdd(cols, members.map(m => m.sequence));
    });
    columns[k] = cols;
    document.getElementById('sq-title-' + k).textContent =
      k === 'all' ? `All ${data.familyPlural}` : k === 'shared' ? `Shared (≥ ${state.minShared} species)` : 'Species-specific';
    document.getElementById('sq-sub-' + k).textContent = `${MS.fmt(fams.length)} ${data.familyPlural}`;
    const host = document.getElementById('sq-logo-' + k);
    if (!fams.length) { host.innerHTML = '<div class="ms-empty">No families in this group.</div>'; return; }
    MS.drawLogo(host, cols, {
      unit: state.unit, shade: region.shade,
      colWidth: region.len > 12 ? 18 : 30, height: 150,
    });
  });
  drawTable(columns, region);
}

function drawTable(columns, region) {
  const freq = (col, k) => {
    const nt = MS.NUCS.reduce((s, q) => s + col[q], 0);
    return nt ? col[k] / nt : 0;
  };
  const rows = d3.range(region.len).map(i => {
    const sh = columns.shared[i], ex = columns.excl[i];
    const diff = MS.NUCS.reduce((s, k) => s + Math.abs(freq(sh, k) - freq(ex, k)), 0) / 2;
    return { pos: i + 1, sh, ex, diff };
  });
  const maxDiff = d3.max(rows, r => r.diff) || 1;
  const cell = (col, k) => `${(100 * freq(col, k)).toFixed(0)}%`;
  document.getElementById('sq-table').innerHTML = `
    <div class="ms-chart--scroll">
    <table class="ms-table">
      <thead><tr>
        <th>Position</th>
        ${MS.NUCS.map(k => `<th class="num">${k} shared</th>`).join('')}
        ${MS.NUCS.map(k => `<th class="num">${k} specific</th>`).join('')}
        <th>Difference (total variation)</th>
      </tr></thead>
      <tbody>${rows.map(r => `
        <tr>
          <td>${r.pos}${r.pos >= 2 && r.pos <= 8 ? ' <span class="ms-pill">seed</span>' : ''}</td>
          ${MS.NUCS.map(k => `<td class="num">${cell(r.sh, k)}</td>`).join('')}
          ${MS.NUCS.map(k => `<td class="num">${cell(r.ex, k)}</td>`).join('')}
          <td><div class="ms-meter" title="${r.diff.toFixed(3)}"><span style="width:${(100 * r.diff / maxDiff).toFixed(1)}%"></span></div></td>
        </tr>`).join('')}
      </tbody>
    </table></div>`;
}

window.msInitSequences = msInitSequences;
})();
