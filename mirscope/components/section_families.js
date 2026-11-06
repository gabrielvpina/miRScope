/* ============================================================
   section_families.js — Families tab
   Searchable / sortable / paginated table of seed families
   (macro) or orthologous clusters (strict). Expanding a row shows
   its miRNAs with the seed (nt 2–8) highlighted, the aligned
   sequence in strict mode, and a sequence logo of the members
   (per-position conservation).
   Listens: families:filter {minDegree,maxDegree}, families:open id
   Exposes: msInitFamilies(data)
   ============================================================ */
(function () {
'use strict';

const PAGE = 50;

const SORTS = {
  degree: { label: 'Species (most first)', fn: (a, b) => b.degree - a.degree || b.size - a.size || a.id.localeCompare(b.id) },
  size:   { label: 'miRNAs (most first)',  fn: (a, b) => b.size - a.size || b.degree - a.degree || a.id.localeCompare(b.id) },
  id:     { label: 'Id (A–Z)',             fn: (a, b) => a.id.localeCompare(b.id) },
};

let state, rows = [];

function msInitFamilies(data) {
  const el = document.getElementById('section-families');
  const maxDeg = data.families.reduce((m, f) => Math.max(m, f.degree), 1);
  state = { q: '', species: '', minDeg: 1, maxDeg, sort: 'degree', page: 0, open: new Set() };

  // Pre-compute a lowercase search haystack per family once.
  data.families.forEach(f => {
    f._hay = (f.id + ' ' + f.seed + ' ' + f.members.map(m => m.id).join(' ')).toLowerCase();
  });

  el.innerHTML = `
    <header class="ms-hero ms-hero--compact">
      <div>
        <h1 class="ms-hero__title">${data.isStrict ? 'Orthologous clusters' : 'Seed families'}</h1>
        <p class="ms-hero__sub">
          ${data.isStrict
            ? 'Cohesion clusters inside each seed family. Expand a row to see the aligned mature sequences.'
            : 'miRNAs sharing an identical seed. Expand a row to see its members.'}
          The seed region (nt 2–8) is <span class="ms-seq"><span class="ms-seq__seed">highlighted</span></span>.
        </p>
      </div>
    </header>

    <div class="ms-controls">
      <label class="ms-field ms-field--grow">Search
        <input type="search" id="fa-q" placeholder="Family id, seed or miRNA id (e.g. let-7, GAGGUAG)">
      </label>
      <label class="ms-field">Species
        <select id="fa-species">
          <option value="">Any species</option>
          ${data.species.map(s => `<option value="${MS.esc(s)}">${MS.esc(s)}</option>`).join('')}
        </select>
      </label>
      <label class="ms-field">Min species <input type="number" id="fa-min" min="1" max="${maxDeg}" value="1"></label>
      <label class="ms-field">Max species <input type="number" id="fa-max" min="1" max="${maxDeg}" value="${maxDeg}"></label>
      <label class="ms-field">Sort
        <select id="fa-sort">${Object.entries(SORTS).map(([k, s]) => `<option value="${k}">${s.label}</option>`).join('')}</select>
      </label>
    </div>

    ${MS.card({
      title: '<span id="fa-count"></span>',
      actions: '<button class="ms-btn ms-btn--ghost" id="fa-csv">CSV</button>',
      body: '<div id="fa-table"></div><div class="ms-pager" id="fa-pager"></div>',
    })}
  `;

  const $ = s => el.querySelector(s);
  let timer = null;
  $('#fa-q').addEventListener('input', e => {
    clearTimeout(timer);
    timer = setTimeout(() => { state.q = e.target.value.trim().toLowerCase(); state.page = 0; refresh(data); }, 150);
  });
  $('#fa-species').addEventListener('change', e => { state.species = e.target.value; state.page = 0; refresh(data); });
  $('#fa-min').addEventListener('input', e => { state.minDeg = +e.target.value || 1; state.page = 0; refresh(data); });
  $('#fa-max').addEventListener('input', e => { state.maxDeg = +e.target.value || maxDeg; state.page = 0; refresh(data); });
  $('#fa-sort').addEventListener('change', e => { state.sort = e.target.value; refresh(data); });
  $('#fa-csv').addEventListener('click', () => MS.downloadCSV(rows, [
    { label: 'family', value: f => f.id },
    { label: 'seed', value: f => f.seed },
    { label: 'species_count', value: f => f.degree },
    { label: 'mirna_count', value: f => f.size },
    { label: 'species', value: f => f.species.join('; ') },
    { label: 'mirnas', value: f => f.members.map(m => m.id).join('; ') },
  ], `mirscope_${data.run.mode}_families.csv`));

  MS.on('families:filter', ({ minDegree, maxDegree }) => {
    state.minDeg = minDegree; state.maxDeg = maxDegree; state.q = ''; state.species = ''; state.page = 0;
    $('#fa-min').value = minDegree; $('#fa-max').value = maxDegree; $('#fa-q').value = ''; $('#fa-species').value = '';
    refresh(data);
  });
  MS.on('families:open', id => {
    state.q = id.toLowerCase(); state.species = ''; state.minDeg = 1; state.maxDeg = maxDeg; state.page = 0;
    state.open = new Set([id]);
    $('#fa-q').value = id; $('#fa-species').value = ''; $('#fa-min').value = 1; $('#fa-max').value = maxDeg;
    refresh(data);
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  refresh(data);
}

function refresh(data) {
  rows = data.families.filter(f =>
    f.degree >= state.minDeg && f.degree <= state.maxDeg &&
    (!state.species || f.species.includes(state.species)) &&
    (!state.q || f._hay.includes(state.q)));
  rows.sort(SORTS[state.sort].fn);

  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  state.page = Math.min(state.page, pages - 1);
  const slice = rows.slice(state.page * PAGE, (state.page + 1) * PAGE);

  document.getElementById('fa-count').textContent =
    `${MS.fmt(rows.length)} of ${MS.fmt(data.families.length)} ${data.familyPlural}`;

  const host = document.getElementById('fa-table');
  if (!slice.length) {
    host.innerHTML = '<div class="ms-empty">Nothing matches these filters.</div>';
  } else {
    host.innerHTML = `
      <table class="ms-table">
        <thead><tr>
          <th></th><th>${data.isStrict ? 'Cluster' : 'Seed family'}</th><th>Seed</th>
          <th class="num">Species</th><th class="num">miRNAs</th><th>Species</th>
        </tr></thead>
        <tbody>${slice.map(f => familyRow(f, data)).join('')}</tbody>
      </table>`;
    host.querySelectorAll('tr.ms-fam').forEach(tr => tr.addEventListener('click', () => {
      const id = tr.dataset.family;
      if (state.open.has(id)) state.open.delete(id); else state.open.add(id);
      refresh(data);
    }));
    host.querySelectorAll('.ms-fam-logo').forEach(box => drawFamilyLogo(box, data));
  }
  drawPager(pages, data);
}

function familyRow(f, data) {
  const open = state.open.has(f.id);
  const species = f.species.slice(0, 4).map(MS.esc).join(', ') + (f.degree > 4 ? `, +${f.degree - 4}` : '');
  let html = `
    <tr class="ms-fam${open ? ' open' : ''}" data-family="${MS.esc(f.id)}">
      <td class="ms-caret" aria-hidden="true">${open ? '▾' : '▸'}</td>
      <td><code>${MS.esc(f.id)}</code></td>
      <td><code class="ms-seed">${MS.esc(f.seed)}</code></td>
      <td class="num">${f.degree}</td>
      <td class="num">${f.size}</td>
      <td class="ms-ellipsis" title="${MS.esc(f.species.join(', '))}">${species}</td>
    </tr>`;
  if (open) {
    const inter = data.intersectionOfFamily.get(f.id);
    html += `
      <tr class="ms-fam-detail"><td></td><td colspan="5">
        ${f.size >= 2 ? `
          <div class="ms-fam-logo" data-family="${MS.esc(f.id)}">
            <div class="ms-fam-logo__head">
              <strong>Sequence logo</strong>
              <span>${data.isStrict ? `${f.size} aligned sequences` : `${f.size} mature sequences, aligned at the 5' end`}</span>
              <button class="ms-btn ms-btn--ghost" data-logo-export="svg">SVG</button>
              <button class="ms-btn ms-btn--ghost" data-logo-export="png">PNG</button>
            </div>
            <div class="ms-fam-logo__plot"></div>
          </div>` : ''}
        <table class="ms-table ms-table--inner">
          <thead><tr><th>miRNA</th><th>Species</th><th>Mature sequence</th>${data.isStrict ? '<th>Aligned</th>' : ''}</tr></thead>
          <tbody>${f.members.map(m => `
            <tr>
              <td><code>${MS.esc(m.id)}</code></td>
              <td><em>${MS.esc(m.species)}</em></td>
              <td>${MS.seqHtml(m.sequence)}</td>
              ${data.isStrict ? `<td>${MS.seqHtml(m.aligned)}</td>` : ''}
            </tr>`).join('')}
          </tbody>
        </table>
        ${inter ? `<p class="ms-hint">Belongs to intersection <code>${MS.esc(inter)}</code> (${f.degree} species).</p>` : ''}
      </td></tr>`;
  }
  return html;
}

/** Logo of a family's members: aligned sequences (strict) or 5'-anchored (macro). */
function drawFamilyLogo(box, data) {
  const f = data.familyById.get(box.dataset.family);
  if (!f) return;
  const seqs = f.members.map(m => String((data.isStrict && m.aligned) || m.sequence).toUpperCase());
  const len = d3.max(seqs, q => q.length);
  const cols = MS.logoColumns(len);
  MS.logoAdd(cols, seqs);

  // Seed columns: nt 2–8 of the first member, mapped onto alignment columns.
  let shade = [1, 7];
  const first = seqs[0];
  const at = [];
  for (let i = 0, pos = 0; i < first.length; i++) if (first[i] !== '-') { if (pos >= 1 && pos <= 7) at.push(i); pos++; }
  if (at.length) shade = [at[0], at[at.length - 1]];

  const plot = box.querySelector('.ms-fam-logo__plot');
  const svg = MS.drawLogo(plot, cols, { unit: 'bits', shade, colWidth: 16, height: 90 });
  svg.addEventListener('click', e => e.stopPropagation());
  box.querySelectorAll('[data-logo-export]').forEach(btn => btn.addEventListener('click', e => {
    e.stopPropagation();
    const name = `mirscope_${data.run.mode}_logo_${f.id}.${btn.dataset.logoExport}`;
    const caption = `${MS.captionPrefix(data)} · ${f.id} · ${f.size} miRNAs · ${f.degree} species`;
    if (btn.dataset.logoExport === 'svg') MS.exportSVG(svg, name, caption);
    else MS.exportPNG(svg, name, caption);
  }));
}

function drawPager(pages, data) {
  const host = document.getElementById('fa-pager');
  if (pages <= 1) { host.innerHTML = ''; return; }
  host.innerHTML = `
    <button class="ms-btn ms-btn--ghost" data-p="${state.page - 1}" ${state.page === 0 ? 'disabled' : ''}>‹ Prev</button>
    <span>Page ${state.page + 1} of ${pages}</span>
    <button class="ms-btn ms-btn--ghost" data-p="${state.page + 1}" ${state.page >= pages - 1 ? 'disabled' : ''}>Next ›</button>`;
  host.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
    state.page = +b.dataset.p;
    refresh(data);
  }));
}

window.msInitFamilies = msInitFamilies;
})();
