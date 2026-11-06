/* ============================================================
   section_input.js — Inputs tab (only when --input was used)
   Focus on the species that came from the user's FASTA files:
   what they share with the reference, which reference species
   are closest, and which families are new (absent from every
   reference species).
   Exposes: msInitInput(data)
   ============================================================ */
(function () {
'use strict';

let state;

function msInitInput(data) {
  const el = document.getElementById('section-input');
  const inputs = [...data.inputSpecies.keys()].sort();
  if (!inputs.length) {
    el.innerHTML = '<div class="ms-empty">This run had no --input files.</div>';
    return;
  }
  state = { sp: inputs[0], rankBy: 'shared' };

  el.innerHTML = `
    <header class="ms-hero ms-hero--compact">
      <div>
        <h1 class="ms-hero__title">Your input</h1>
        <p class="ms-hero__sub">
          The species from <code>--input</code> compared with the reference database.
          A ${data.familyLabel} is <strong>new</strong> when no reference species carries it.
        </p>
      </div>
    </header>

    <div class="ms-controls">
      <label class="ms-field">Input species
        <select id="in-sp">${inputs.map(s =>
          `<option value="${MS.esc(s)}">${MS.esc(s)} (${MS.esc(data.inputSpecies.get(s))})</option>`).join('')}
        </select>
      </label>
    </div>

    <div class="ms-kpis" id="in-kpis"></div>

    <div class="ms-grid ms-grid--2">
      ${MS.card({
        title: 'Conservation profile',
        subtitle: `${data.familyPlural} of this species by the number of species that carry them.`,
        actions: MS.exportButtons('in-profile'),
        body: '<div id="in-profile" class="ms-chart"></div>',
      })}
      ${MS.card({
        title: 'Closest species',
        subtitle: `Species sharing the most ${data.familyPlural} with the input.`,
        actions: `
          <select id="in-rank" class="ms-input-sm">
            <option value="shared">Rank by shared families</option>
            <option value="jaccard">Rank by Jaccard index</option>
          </select>
          ${MS.exportButtons('in-closest')}`,
        body: '<div id="in-closest" class="ms-chart"></div>',
      })}
    </div>

    ${MS.card({
      title: `New ${data.familyPlural} (not in the reference)`,
      subtitle: 'Candidate novel or lineage-specific miRNAs. Click a row to open it in the Families tab.',
      actions: '<button class="ms-btn ms-btn--ghost" id="in-new-csv">CSV</button>',
      body: '<div id="in-new"></div>',
    })}
    ${MS.card({
      title: `Conserved ${data.familyPlural}`,
      subtitle: 'Shared with at least one reference species, widest first.',
      actions: '<button class="ms-btn ms-btn--ghost" id="in-cons-csv">CSV</button>',
      body: '<div id="in-cons"></div>',
    })}
  `;

  const $ = s => el.querySelector(s);
  $('#in-sp').addEventListener('change', e => { state.sp = e.target.value; draw(data); });
  $('#in-rank').addEventListener('change', e => { state.rankBy = e.target.value; drawClosest(data); });
  const csvCols = [
    { label: 'family', value: f => f.id },
    { label: 'seed', value: f => f.seed },
    { label: 'species_count', value: f => f.degree },
    { label: 'input_mirnas', value: f => f.members.filter(m => m.species === state.sp).map(m => m.id).join('; ') },
    { label: 'input_sequences', value: f => f.members.filter(m => m.species === state.sp).map(m => m.sequence).join('; ') },
    { label: 'species', value: f => f.species.join('; ') },
  ];
  const fileName = kind => `mirscope_${data.run.mode}_${state.sp.replace(/\W+/g, '_')}_${kind}.csv`;
  $('#in-new-csv').addEventListener('click', () => MS.downloadCSV(state.novel, csvCols, fileName('new')));
  $('#in-cons-csv').addEventListener('click', () => MS.downloadCSV(state.conserved, csvCols, fileName('conserved')));
  MS.bindExports(el, 'mirscope_' + data.run.mode, {
    'in-profile': () => `${MS.captionPrefix(data)} · ${state.sp} · conservation profile`,
    'in-closest': () => `${MS.captionPrefix(data)} · ${state.sp} · closest species by ${state.rankBy === 'jaccard' ? 'Jaccard index' : 'shared families'}`,
  });
  draw(data);
}

function draw(data) {
  const sp = state.sp;
  const isRef = s => !data.inputSpecies.has(s);
  const mine = data.families.filter(f => f.species.includes(sp));
  state.mine = mine;
  state.novel = mine.filter(f => !f.species.some(isRef)).sort((a, b) => b.size - a.size || a.id.localeCompare(b.id));
  state.conserved = mine.filter(f => f.species.some(isRef))
    .sort((a, b) => b.degree - a.degree || b.size - a.size || a.id.localeCompare(b.id));

  // Shared counts with every other species.
  const shared = new Map();
  mine.forEach(f => f.species.forEach(s => { if (s !== sp) shared.set(s, (shared.get(s) || 0) + 1); }));
  const stat = new Map(data.speciesStats.map(s => [s.name, s]));
  state.closest = [...shared.entries()].map(([name, n]) => ({
    name, n, jaccard: n / (mine.length + stat.get(name).families - n), input: !isRef(name),
  }));

  const mirnas = d3.sum(mine, f => f.members.filter(m => m.species === sp).length);
  const best = d3.greatest(state.closest.filter(c => !c.input), c => c.jaccard);
  const kpi = (label, value, hint = '') => `
    <div class="ms-kpi"><div class="ms-kpi__value">${value}</div>
    <div class="ms-kpi__label">${label}</div>${hint ? `<div class="ms-kpi__hint">${hint}</div>` : ''}</div>`;
  document.getElementById('in-kpis').innerHTML =
    kpi('miRNAs', MS.fmt(mirnas)) +
    kpi(data.familyPlural, MS.fmt(mine.length)) +
    kpi('Conserved', MS.fmt(state.conserved.length), MS.pct(state.conserved.length, mine.length) + ' shared with the reference') +
    kpi('New', MS.fmt(state.novel.length), MS.pct(state.novel.length, mine.length) + ' absent from the reference') +
    kpi('Closest species', best ? `<span style="font-size:1rem;font-style:italic">${MS.esc(best.name)}</span>` : '—',
      best ? `Jaccard ${best.jaccard.toFixed(3)} · ${MS.fmt(best.n)} shared` : '');

  drawProfile(data);
  drawClosest(data);
  drawTables(data);
}

function drawProfile(data) {
  const host = document.getElementById('in-profile');
  host.innerHTML = '';
  const bins = d3.rollups(state.mine, v => v.length, f => f.degree).map(([degree, n]) => ({ degree, n }))
    .sort((a, b) => a.degree - b.degree);
  if (!bins.length) { host.innerHTML = '<div class="ms-empty">No families.</div>'; return; }
  const width = MS.widthOf(host, 600), height = 280;
  const m = { top: 14, right: 12, bottom: 42, left: 52 };
  const maxDeg = d3.max(bins, d => d.degree);
  const x = d3.scaleBand().domain(d3.range(1, maxDeg + 1)).range([m.left, width - m.right]).padding(0.15);
  const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.n)]).nice().range([height - m.bottom, m.top]);
  const svg = d3.select(host).append('svg').attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
  svg.append('g').attr('class', 'ms-axis').attr('transform', `translate(${m.left},0)`)
    .call(d3.axisLeft(y).ticks(5, ',d').tickSize(-(width - m.left - m.right))).call(g => g.select('.domain').remove());
  const step = Math.max(1, Math.ceil(maxDeg / Math.floor((width - m.left - m.right) / 26)));
  svg.append('g').attr('class', 'ms-axis ms-axis--x').attr('transform', `translate(0,${height - m.bottom})`)
    .call(d3.axisBottom(x).tickValues(x.domain().filter(d => d === 1 || d % step === 0)).tickSizeOuter(0));
  svg.append('text').attr('class', 'ms-axis-label').attr('x', m.left + (width - m.left - m.right) / 2)
    .attr('y', height - 6).attr('text-anchor', 'middle').text('Number of species carrying the family');
  svg.append('g').selectAll('rect').data(bins).join('rect')
    .attr('class', d => 'ms-bar' + (d.degree === 1 ? ' ms-bar--muted' : ''))
    .attr('x', d => x(d.degree)).attr('width', x.bandwidth())
    .attr('y', d => y(d.n)).attr('height', d => y(0) - y(d.n)).attr('rx', 2)
    .on('mouseenter', (e, d) => MS.tooltip.show(`<strong>${MS.fmt(d.n)}</strong> ${data.familyPlural} in ${d.degree} species`, e))
    .on('mousemove', e => MS.tooltip.move(e))
    .on('mouseleave', () => MS.tooltip.hide());
}

function drawClosest(data) {
  const host = document.getElementById('in-closest');
  host.innerHTML = '';
  const key = state.rankBy === 'jaccard' ? 'jaccard' : 'n';
  const rows = [...state.closest].sort((a, b) => b[key] - a[key] || a.name.localeCompare(b.name)).slice(0, 15);
  if (!rows.length) { host.innerHTML = '<div class="ms-empty">Shares nothing with other species.</div>'; return; }
  const width = MS.widthOf(host, 600), rowH = 18;
  const m = { top: 24, right: 60, bottom: 6, left: Math.min(220, 14 + 6.6 * d3.max(rows, r => r.name.length)) };
  const height = m.top + rows.length * rowH + m.bottom;
  const x = d3.scaleLinear().domain([0, d3.max(rows, r => r[key]) || 1]).nice().range([m.left, width - m.right]);
  const svg = d3.select(host).append('svg').attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
  svg.append('g').attr('class', 'ms-axis').attr('transform', `translate(0,${m.top - 4})`)
    .call(d3.axisTop(x).ticks(5, key === 'n' ? ',d' : '.2f').tickSize(-(rows.length * rowH + 4)))
    .call(g => g.select('.domain').remove());
  const g = svg.append('g').selectAll('g').data(rows).join('g')
    .attr('transform', (d, i) => `translate(0,${m.top + i * rowH})`)
    .on('mouseenter', (e, d) => MS.tooltip.show(`<strong>${MS.esc(d.name)}</strong>${d.input ? ' (input)' : ''}<br>` +
      `${MS.fmt(d.n)} shared ${data.familyPlural}<br>Jaccard ${d.jaccard.toFixed(3)}`, e))
    .on('mousemove', e => MS.tooltip.move(e))
    .on('mouseleave', () => MS.tooltip.hide());
  g.append('text').attr('class', d => 'ms-upset-label' + (d.input ? ' ms-tree-leaf--input' : ''))
    .attr('x', m.left - 6).attr('y', rowH / 2).attr('dy', '0.35em').attr('text-anchor', 'end')
    .style('font-size', '11px').text(d => d.name);
  g.append('rect').attr('class', 'ms-bar').attr('x', m.left).attr('y', 3).attr('height', rowH - 6).attr('rx', 2)
    .attr('width', d => x(d[key]) - m.left);
  g.append('text').attr('class', 'ms-bar-label').attr('x', d => x(d[key]) + 5).attr('y', rowH / 2).attr('dy', '0.35em')
    .text(d => key === 'n' ? MS.fmt(d.n) : d.jaccard.toFixed(3));
}

function familyTable(data, list, limit = 100) {
  if (!list.length) return '<div class="ms-empty">None.</div>';
  const sp = state.sp;
  return `
    <table class="ms-table ms-table--hover">
      <thead><tr>
        <th>${data.isStrict ? 'Cluster' : 'Seed family'}</th><th>Seed</th><th class="num">Species</th>
        <th>Input miRNAs</th><th>Mature sequence</th>
      </tr></thead>
      <tbody>${list.slice(0, limit).map(f => {
        const all = f.members.filter(m => m.species === sp);
        const own = all.slice(0, 4);
        const more = all.length > 4 ? `<br><span class="ms-muted">+${all.length - 4} more</span>` : '';
        return `
        <tr data-family="${MS.esc(f.id)}">
          <td><code>${MS.esc(f.id)}</code></td>
          <td><code class="ms-seed">${MS.esc(f.seed)}</code></td>
          <td class="num">${f.degree}</td>
          <td>${own.map(m => `<code>${MS.esc(m.id)}</code>`).join('<br>')}${more}</td>
          <td>${own.map(m => MS.seqHtml(m.sequence)).join('<br>')}</td>
        </tr>`;
      }).join('')}
      </tbody>
    </table>
    ${list.length > limit ? `<p class="ms-hint">Showing ${limit} of ${MS.fmt(list.length)} — download the CSV for all.</p>` : ''}`;
}

function drawTables(data) {
  ['new', 'cons'].forEach(k => {
    const host = document.getElementById('in-' + k);
    host.innerHTML = familyTable(data, k === 'new' ? state.novel : state.conserved);
    host.querySelectorAll('tr[data-family]').forEach(tr => tr.addEventListener('click', () => {
      MS.activate('families');
      MS.emit('families:open', tr.dataset.family);
    }));
  });
}

window.msInitInput = msInitInput;
})();
