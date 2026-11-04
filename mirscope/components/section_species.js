/* ============================================================
   section_species.js — Species tab
   Per-species stacked bars (shared vs. species-specific families)
   and a pairwise heatmap of families shared between species.
   Exposes: msInitSpecies(data)
   ============================================================ */
(function () {
'use strict';

let state;

function msInitSpecies(data) {
  const el = document.getElementById('section-species');
  state = { sort: 'families', heatN: Math.min(25, data.species.length), heatNorm: false, q: '' };

  el.innerHTML = `
    <header class="ms-hero ms-hero--compact">
      <div>
        <h1 class="ms-hero__title">Species</h1>
        <p class="ms-hero__sub">
          How many ${data.familyPlural} each species carries, how many of them are
          species-specific, and how much each pair of species shares.
        </p>
      </div>
    </header>

    ${MS.card({
      title: `${data.isStrict ? 'Clusters' : 'Seed families'} per species`,
      subtitle: `<span class="ms-legend"><i class="ms-legend__sw ms-legend__sw--shared"></i>shared with other species
                 <i class="ms-legend__sw ms-legend__sw--excl"></i>species-specific</span>`,
      actions: `
        <input type="search" id="sp-q" class="ms-input-sm" placeholder="Filter species">
        <select id="sp-sort" class="ms-input-sm">
          <option value="families">Most families</option>
          <option value="exclusive">Most species-specific</option>
          <option value="name">Name (A–Z)</option>
        </select>
        ${MS.exportButtons('sp-bars')}`,
      body: '<div id="sp-bars" class="ms-chart ms-chart--tall"></div>',
    })}

    ${MS.card({
      title: 'Shared families between species',
      subtitle: `Cell = number of ${data.familyPlural} present in both species (diagonal = total).
                 Species are the ones with the most ${data.familyPlural}.`,
      actions: `
        <label class="ms-field ms-field--inline">Species
          <input type="number" id="sp-heatn" class="ms-input-sm" min="2" max="${Math.min(80, data.species.length)}" value="${state.heatN}">
        </label>
        <label class="ms-toggle"><input type="checkbox" id="sp-norm"> Jaccard index</label>
        ${MS.exportButtons('sp-heat')}`,
      body: '<div id="sp-heat" class="ms-chart ms-chart--scroll"></div>',
    })}
  `;

  const $ = s => el.querySelector(s);
  $('#sp-sort').addEventListener('change', e => { state.sort = e.target.value; drawBars(data); });
  $('#sp-q').addEventListener('input', e => { state.q = e.target.value.trim().toLowerCase(); drawBars(data); });
  $('#sp-heatn').addEventListener('input', e => {
    const v = parseInt(e.target.value, 10);
    if (v >= 2) { state.heatN = Math.min(v, 80, data.species.length); drawHeat(data); }
  });
  $('#sp-norm').addEventListener('change', e => { state.heatNorm = e.target.checked; drawHeat(data); });
  MS.bindExports(el, 'mirscope_' + data.run.mode);

  drawBars(data);
  if (data.species.length >= 2) drawHeat(data);
  else document.getElementById('sp-heat').innerHTML = '<div class="ms-empty">Needs at least two species.</div>';
}

function drawBars(data) {
  const host = document.getElementById('sp-bars');
  host.innerHTML = '';
  const cmp = {
    families: (a, b) => b.families - a.families || a.name.localeCompare(b.name),
    exclusive: (a, b) => b.exclusive - a.exclusive || a.name.localeCompare(b.name),
    name: (a, b) => a.name.localeCompare(b.name),
  }[state.sort];
  const rows = data.speciesStats.filter(s => !state.q || s.name.toLowerCase().includes(state.q)).sort(cmp);
  if (!rows.length) { host.innerHTML = '<div class="ms-empty">No species match.</div>'; return; }

  const width = MS.widthOf(host, 900);
  const rowH = 18;
  const m = { top: 28, right: 70, bottom: 8, left: Math.min(230, 14 + 6.6 * d3.max(rows, r => r.name.length)) };
  const height = m.top + rows.length * rowH + m.bottom;
  const x = d3.scaleLinear().domain([0, d3.max(rows, r => r.families) || 1]).nice()
    .range([m.left, width - m.right]);
  const y = (d, i) => m.top + i * rowH;

  const svg = d3.select(host).append('svg')
    .attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);

  svg.append('g').attr('class', 'ms-axis')
    .attr('transform', `translate(0,${m.top - 4})`)
    .call(d3.axisTop(x).ticks(6, ',d').tickSize(-(rows.length * rowH + 4)))
    .call(g => g.select('.domain').remove());

  const g = svg.append('g').selectAll('g').data(rows).join('g')
    .attr('transform', (d, i) => `translate(0,${y(d, i)})`)
    .on('mouseenter', (e, d) => MS.tooltip.show(
      `<strong>${MS.esc(d.name)}</strong><br>` +
      `${MS.fmt(d.families)} ${data.familyPlural} · ${MS.fmt(d.mirnas)} miRNAs<br>` +
      `${MS.fmt(d.shared)} shared · ${MS.fmt(d.exclusive)} species-specific (${MS.pct(d.exclusive, d.families)})`, e))
    .on('mousemove', e => MS.tooltip.move(e))
    .on('mouseleave', () => MS.tooltip.hide());

  g.append('text').attr('class', 'ms-upset-label')
    .attr('x', m.left - 6).attr('y', rowH / 2).attr('dy', '0.35em').attr('text-anchor', 'end')
    .style('font-size', '11px')
    .text(d => d.name);
  g.append('rect').attr('class', 'ms-bar')
    .attr('x', m.left).attr('y', 3).attr('height', rowH - 6).attr('rx', 2)
    .attr('width', d => x(d.shared) - m.left);
  g.append('rect').attr('class', 'ms-bar ms-bar--excl')
    .attr('x', d => x(d.shared)).attr('y', 3).attr('height', rowH - 6).attr('rx', 2)
    .attr('width', d => x(d.families) - x(d.shared));
  g.append('text').attr('class', 'ms-bar-label')
    .attr('x', d => x(d.families) + 5).attr('y', rowH / 2).attr('dy', '0.35em')
    .text(d => MS.fmt(d.families));
}

function drawHeat(data) {
  const host = document.getElementById('sp-heat');
  host.innerHTML = '';
  const picked = [...data.speciesStats]
    .sort((a, b) => b.families - a.families || a.name.localeCompare(b.name))
    .slice(0, state.heatN).map(s => s.name);
  const n = picked.length;
  const idx = new Map(picked.map((s, i) => [s, i]));

  // Co-occurrence counts restricted to the picked species.
  const M = Array.from({ length: n }, () => new Array(n).fill(0));
  data.families.forEach(f => {
    const ii = f.species.map(s => idx.get(s)).filter(i => i !== undefined);
    for (let a = 0; a < ii.length; a++) {
      for (let b = a; b < ii.length; b++) {
        M[ii[a]][ii[b]] += 1;
        if (a !== b) M[ii[b]][ii[a]] += 1;
      }
    }
  });
  const value = (i, j) => {
    if (!state.heatNorm) return M[i][j];
    const union = M[i][i] + M[j][j] - M[i][j];
    return union ? M[i][j] / union : 0;
  };

  const labelW = Math.min(220, 14 + 6.6 * d3.max(picked, s => s.length));
  const avail = MS.widthOf(host, 900) - labelW - 30;
  const cell = Math.max(12, Math.min(34, avail / n));
  const top = labelW;   // rotated column labels
  const width = labelW + cell * n + 30;
  const height = top + cell * n + 10;

  let maxOff = 0;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j) maxOff = Math.max(maxOff, value(i, j));
  const color = d3.scaleLinear()
    .domain([0, maxOff || 1])
    .range([MS.cssVar('--ms-heat-low'), MS.cssVar('--ms-heat-high')])
    .interpolate(d3.interpolateLab)
    .clamp(true);

  const svg = d3.select(host).append('svg')
    .attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);

  const cells = [];
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) cells.push({ i, j, v: value(i, j), raw: M[i][j] });

  svg.append('g').selectAll('rect').data(cells).join('rect')
    .attr('x', d => labelW + d.j * cell).attr('y', d => top + d.i * cell)
    .attr('width', cell - 1).attr('height', cell - 1).attr('rx', 2)
    .attr('fill', d => d.i === d.j ? MS.cssVar('--ms-primary') : color(d.v))
    .on('mouseenter', (e, d) => MS.tooltip.show(d.i === d.j
      ? `<strong>${MS.esc(picked[d.i])}</strong><br>${MS.fmt(d.raw)} ${data.familyPlural}`
      : `<strong>${MS.esc(picked[d.i])}</strong> × <strong>${MS.esc(picked[d.j])}</strong><br>` +
        `${MS.fmt(d.raw)} shared ${data.familyPlural}` +
        (state.heatNorm ? `<br>Jaccard ${d.v.toFixed(3)}` : ''), e))
    .on('mousemove', e => MS.tooltip.move(e))
    .on('mouseleave', () => MS.tooltip.hide());

  if (cell >= 26) {
    svg.append('g').selectAll('text').data(cells.filter(d => d.i !== d.j)).join('text')
      .attr('class', 'ms-heat-val')
      .attr('x', d => labelW + d.j * cell + cell / 2).attr('y', d => top + d.i * cell + cell / 2)
      .attr('dy', '0.35em').attr('text-anchor', 'middle')
      .classed('ms-heat-val--light', d => d.v > maxOff * 0.55)
      .text(d => state.heatNorm ? d.v.toFixed(2) : (d.raw >= 1000 ? d3.format('.2~s')(d.raw) : d.raw));
  }

  const fs = cell < 16 ? '9px' : '11px';
  svg.append('g').selectAll('text').data(picked).join('text')
    .attr('class', 'ms-upset-label')
    .attr('x', labelW - 6).attr('y', (s, i) => top + i * cell + cell / 2)
    .attr('dy', '0.35em').attr('text-anchor', 'end').style('font-size', fs)
    .text(s => s);
  svg.append('g').selectAll('text').data(picked).join('text')
    .attr('class', 'ms-upset-label')
    .attr('transform', (s, i) => `translate(${labelW + i * cell + cell / 2},${top - 6}) rotate(-60)`)
    .attr('dy', '0.35em').style('font-size', fs)
    .text(s => s);
}

window.msInitSpecies = msInitSpecies;
})();
