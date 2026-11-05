/* ============================================================
   section_upset.js — Intersections tab (interactive UpSet plot)
   Live filters (top-n, min-size, min-degree, required species),
   click a column to list its families, SVG/PNG/CSV export.
   Exposes: msInitUpset(data)
   ============================================================ */
(function () {
'use strict';

const MAX_COLUMNS = 300;   // hard cap so "all" stays responsive

let state = null;

function msInitUpset(data) {
  const el = document.getElementById('section-upset');
  const p = data.params;
  state = {
    topN: p.top_n == null ? 10 : p.top_n,
    minSize: p.min_size || 1,
    minDegree: p.min_degree || 1,
    required: [],
    selected: null,
  };

  el.innerHTML = `
    <header class="ms-hero ms-hero--compact">
      <div>
        <h1 class="ms-hero__title">Species intersections</h1>
        <p class="ms-hero__sub">
          Each column is a set of species; its bar counts the ${data.familyPlural} found in
          <em>exactly</em> those species. Defaults come from the run's
          <code>--top-n</code>, <code>--min-size</code> and <code>--min-degree</code>.
        </p>
      </div>
    </header>

    <div class="ms-controls">
      <label class="ms-field">Top N <span class="ms-muted">(0 = all)</span>
        <input type="number" id="up-topn" min="0" step="1" value="${state.topN}">
      </label>
      <label class="ms-field">Min size
        <input type="number" id="up-minsize" min="1" step="1" value="${state.minSize}">
      </label>
      <label class="ms-field">Min degree
        <input type="number" id="up-mindeg" min="1" step="1" value="${state.minDegree}">
      </label>
      <label class="ms-field ms-field--grow">Must include species
        <input type="text" id="up-species" list="up-species-list" placeholder="Type a species and press Enter">
        <datalist id="up-species-list">
          ${data.species.map(s => `<option value="${MS.esc(s)}">`).join('')}
        </datalist>
      </label>
      <button class="ms-btn ms-btn--ghost" id="up-reset">Reset to run defaults</button>
    </div>
    <div class="ms-chips" id="up-chips"></div>

    ${MS.card({
      title: 'UpSet plot',
      subtitle: '<span id="up-summary"></span>',
      actions: `${MS.exportButtons('up-plot')}
                <button class="ms-btn ms-btn--ghost" id="up-csv">CSV</button>`,
      body: '<div id="up-plot" class="ms-chart ms-chart--scroll"></div>',
    })}

    <div id="up-detail"></div>
  `;

  const num = (id, key, min) => {
    el.querySelector(id).addEventListener('input', e => {
      const v = parseInt(e.target.value, 10);
      if (!Number.isNaN(v) && v >= min) { state[key] = v; state.selected = null; render(data); }
    });
  };
  num('#up-topn', 'topN', 0);
  num('#up-minsize', 'minSize', 1);
  num('#up-mindeg', 'minDegree', 1);

  const speciesInput = el.querySelector('#up-species');
  const addSpecies = () => {
    const v = speciesInput.value.trim();
    if (data.species.includes(v) && !state.required.includes(v)) {
      state.required.push(v);
      state.selected = null;
      render(data);
    }
    speciesInput.value = '';
  };
  speciesInput.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); addSpecies(); } });
  speciesInput.addEventListener('change', addSpecies);

  el.querySelector('#up-reset').addEventListener('click', () => {
    state.topN = p.top_n == null ? 10 : p.top_n;
    state.minSize = p.min_size || 1;
    state.minDegree = p.min_degree || 1;
    state.required = [];
    state.selected = null;
    el.querySelector('#up-topn').value = state.topN;
    el.querySelector('#up-minsize').value = state.minSize;
    el.querySelector('#up-mindeg').value = state.minDegree;
    render(data);
  });

  el.querySelector('#up-csv').addEventListener('click', () => {
    const { shown } = filtered(data);
    MS.downloadCSV(shown, [
      { label: 'intersection', value: r => r.id },
      { label: 'degree', value: r => r.degree },
      { label: 'size', value: r => r.size },
      { label: 'species', value: r => r.species.join('; ') },
      { label: 'families', value: r => r.families.join('; ') },
    ], `mirscope_${data.run.mode}_intersections.csv`);
  });

  MS.bindExports(el, 'mirscope_' + data.run.mode, {
    'up-plot': () => {
      const { total, shown } = filtered(data);
      return `${MS.captionPrefix(data)} · top-n ${state.topN || 'all'} · min-size ${state.minSize}` +
        ` · min-degree ${state.minDegree}` +
        (state.required.length ? ` · must include: ${state.required.join(', ')}` : '') +
        ` · showing ${shown.length} of ${total} matching intersections`;
    },
  });
  render(data);
}

function filtered(data) {
  const req = state.required;
  const kept = data.intersections.filter(i =>
    i.size >= state.minSize &&
    i.degree >= state.minDegree &&
    req.every(s => i.species.includes(s)));
  const limit = state.topN > 0 ? Math.min(state.topN, MAX_COLUMNS) : MAX_COLUMNS;
  return { total: kept.length, shown: kept.slice(0, limit) };
}

function render(data) {
  const chips = document.getElementById('up-chips');
  chips.innerHTML = state.required.map((s, i) =>
    `<span class="ms-chip">${MS.esc(s)}<button data-i="${i}" aria-label="Remove ${MS.esc(s)}">×</button></span>`).join('');
  chips.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
    state.required.splice(+b.dataset.i, 1);
    state.selected = null;
    render(data);
  }));

  const { total, shown } = filtered(data);
  const capped = state.topN === 0 && total > MAX_COLUMNS;
  document.getElementById('up-summary').innerHTML =
    `Showing <strong>${MS.fmt(shown.length)}</strong> of ${MS.fmt(total)} matching intersections` +
    ` (${MS.fmt(data.intersections.length)} in total)` +
    (capped ? ` — capped at ${MAX_COLUMNS} columns` : '');

  drawUpset(data, shown);
  drawDetail(data);
}

function drawUpset(data, shown) {
  const host = document.getElementById('up-plot');
  host.innerHTML = '';
  if (!shown.length) {
    host.innerHTML = '<div class="ms-empty">No intersection matches the current filters.</div>';
    return;
  }

  // Species rows: those used by the shown columns, most families first.
  const statsByName = new Map(data.speciesStats.map(s => [s.name, s]));
  const used = new Set(shown.flatMap(i => i.species));
  const rows = [...used].sort((a, b) =>
    (statsByName.get(b)?.families || 0) - (statsByName.get(a)?.families || 0) || a.localeCompare(b));

  const available = MS.widthOf(host, 900);
  const setW = 120;                      // left: set-size bars
  const labelW = Math.min(220, 12 + 7 * d3.max(rows, r => r.length));
  const plotLeft = setW + labelW;
  const colW = Math.max(14, Math.min(44, (available - plotLeft - 20) / shown.length));
  const rowH = rows.length > 40 ? 14 : 20;
  const barsH = 200;
  const top = 24;
  const width = Math.max(available, plotLeft + colW * shown.length + 20);
  const height = top + barsH + 10 + rowH * rows.length + 10;
  const matrixTop = top + barsH + 10;

  const x = i => plotLeft + i * colW + colW / 2;
  const y = d3.scaleLinear().domain([0, d3.max(shown, d => d.size)]).nice().range([top + barsH, top]);
  const rowY = r => matrixTop + rows.indexOf(r) * rowH + rowH / 2;
  const setX = d3.scaleLinear()
    .domain([0, d3.max(rows, r => statsByName.get(r)?.families || 0) || 1])
    .range([0, setW - 16]);

  const svg = d3.select(host).append('svg')
    .attr('width', width).attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`);

  // Intersection-size axis + bars.
  svg.append('g')
    .attr('class', 'ms-axis')
    .attr('transform', `translate(${plotLeft - 4},0)`)
    .call(d3.axisLeft(y).ticks(5, ',d').tickSize(-(colW * shown.length + 4)))
    .call(g => g.select('.domain').remove());
  svg.append('text')
    .attr('class', 'ms-axis-label')
    .attr('x', plotLeft - 40).attr('y', top + barsH / 2)
    .attr('text-anchor', 'end')
    .text(data.isStrict ? 'Clusters' : 'Seed families');

  const cols = svg.append('g').selectAll('g').data(shown).join('g')
    .attr('class', 'ms-upset-col')
    .classed('selected', d => d.id === state.selected)
    .style('cursor', 'pointer')
    .on('mouseenter', (e, d) => MS.tooltip.show(
      `<strong>${MS.fmt(d.size)}</strong> ${d.size === 1 ? data.familyLabel : data.familyPlural} · ${d.degree} species<br>` +
      `<span class="ms-tooltip__list">${d.species.slice(0, 12).map(MS.esc).join('<br>')}` +
      `${d.species.length > 12 ? '<br>…' : ''}</span>`, e))
    .on('mousemove', e => MS.tooltip.move(e))
    .on('mouseleave', () => MS.tooltip.hide())
    .on('click', (e, d) => {
      state.selected = state.selected === d.id ? null : d.id;
      cols.classed('selected', c => c.id === state.selected);
      drawDetail(data);
    });

  cols.append('rect')            // full-height hit area / highlight band
    .attr('class', 'ms-upset-col__band')
    .attr('x', (d, i) => x(i) - colW / 2).attr('width', colW)
    .attr('y', top).attr('height', height - top - 4);

  cols.append('rect')
    .attr('class', 'ms-bar')
    .attr('x', (d, i) => x(i) - colW * 0.35).attr('width', colW * 0.7)
    .attr('y', d => y(d.size)).attr('height', d => y(0) - y(d.size))
    .attr('rx', 2);

  if (colW >= 20) {
    cols.append('text')
      .attr('class', 'ms-bar-label')
      .attr('x', (d, i) => x(i)).attr('y', d => y(d.size) - 4)
      .attr('text-anchor', 'middle')
      .text(d => d.size);
  }

  // Matrix: zebra rows (drawn underneath), empty dots, filled dots + connector line.
  const matrix = svg.insert('g', ':first-child');
  matrix.selectAll('rect').data(rows).join('rect')
    .attr('class', (r, i) => 'ms-upset-row' + (i % 2 ? '' : ' ms-upset-row--alt'))
    .attr('x', setW).attr('width', plotLeft + colW * shown.length + 6 - setW)
    .attr('y', r => rowY(r) - rowH / 2).attr('height', rowH);

  const dotR = Math.min(colW, rowH) * 0.3;
  cols.each(function (d, i) {
    const g = d3.select(this);
    const members = new Set(d.species);
    g.selectAll('circle').data(rows).join('circle')
      .attr('cx', x(i)).attr('cy', r => rowY(r)).attr('r', dotR)
      .attr('class', r => members.has(r) ? 'ms-dot ms-dot--on' : 'ms-dot');
    const ys = d.species.filter(s => used.has(s)).map(rowY);
    if (ys.length > 1) {
      g.append('line')
        .attr('class', 'ms-dot-line')
        .attr('x1', x(i)).attr('x2', x(i))
        .attr('y1', d3.min(ys)).attr('y2', d3.max(ys));
      g.select('line').lower();
      g.select('.ms-upset-col__band').lower();
    }
  });

  // Species labels + set-size bars.
  svg.append('g').selectAll('text').data(rows).join('text')
    .attr('class', 'ms-upset-label')
    .attr('x', plotLeft - 8).attr('y', r => rowY(r))
    .attr('dy', '0.35em').attr('text-anchor', 'end')
    .style('font-size', rowH < 18 ? '10px' : '12px')
    .text(r => r.length > 30 ? r.slice(0, 29) + '…' : r)
    .append('title').text(r => r);

  svg.append('g').selectAll('rect').data(rows).join('rect')
    .attr('class', 'ms-bar ms-bar--set')
    .attr('x', r => setW - 8 - setX(statsByName.get(r)?.families || 0))
    .attr('width', r => setX(statsByName.get(r)?.families || 0))
    .attr('y', r => rowY(r) - rowH * 0.32).attr('height', rowH * 0.64)
    .on('mouseenter', (e, r) => MS.tooltip.show(
      `<strong>${MS.esc(r)}</strong><br>${MS.fmt(statsByName.get(r)?.families || 0)} ${data.familyPlural} in total`, e))
    .on('mousemove', e => MS.tooltip.move(e))
    .on('mouseleave', () => MS.tooltip.hide());
  svg.append('text')
    .attr('class', 'ms-axis-label')
    .attr('x', setW - 8).attr('y', matrixTop - 4)
    .attr('text-anchor', 'end')
    .text('Set size');
}

function drawDetail(data) {
  const host = document.getElementById('up-detail');
  const item = state.selected ? data.intersectionById.get(state.selected) : null;
  if (!item) {
    host.innerHTML = '<p class="ms-hint">Click a column to list its ' + data.familyPlural + '.</p>';
    return;
  }
  const fams = item.families.map(id => data.familyById.get(id)).filter(Boolean);
  host.innerHTML = MS.card({
    title: `Intersection ${MS.esc(item.id)} · ${MS.fmt(item.size)} ${item.size === 1 ? data.familyLabel : data.familyPlural}`,
    subtitle: item.species.map(s => `<span class="ms-chip ms-chip--static">${MS.esc(s)}</span>`).join(' '),
    body: `
      <table class="ms-table ms-table--hover">
        <thead><tr><th>${data.isStrict ? 'Cluster' : 'Seed family'}</th><th>Seed</th><th class="num">miRNAs</th><th>miRNA ids</th></tr></thead>
        <tbody>${fams.slice(0, 500).map(f => `
          <tr data-family="${MS.esc(f.id)}">
            <td><code>${MS.esc(f.id)}</code></td>
            <td><code class="ms-seed">${MS.esc(f.seed)}</code></td>
            <td class="num">${f.size}</td>
            <td class="ms-ellipsis">${f.members.slice(0, 8).map(m => MS.esc(m.id)).join(', ')}${f.size > 8 ? ', …' : ''}</td>
          </tr>`).join('')}
        </tbody>
      </table>
      ${fams.length > 500 ? `<p class="ms-hint">Showing the first 500 of ${MS.fmt(fams.length)}.</p>` : ''}`,
  });
  host.querySelectorAll('tr[data-family]').forEach(tr => tr.addEventListener('click', () => {
    MS.activate('families');
    MS.emit('families:open', tr.dataset.family);
  }));
}

window.msInitUpset = msInitUpset;
})();
