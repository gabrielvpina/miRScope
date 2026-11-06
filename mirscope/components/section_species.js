/* ============================================================
   section_species.js — Species tab
   Per-species stacked bars (shared vs. species-specific families)
   a pairwise heatmap of families shared between species (optionally
   ordered by UPGMA clustering) and a similarity tree of all species
   built from the Jaccard distance of their family repertoires.
   Exposes: msInitSpecies(data)
   ============================================================ */
(function () {
'use strict';

let state;

function msInitSpecies(data) {
  const el = document.getElementById('section-species');
  state = { sort: 'families', heatN: Math.min(25, data.species.length), heatNorm: false, q: '', heatOrder: 'tree' };

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
        <select id="sp-order" class="ms-input-sm">
          <option value="tree">Order: similarity (UPGMA)</option>
          <option value="size">Order: most families</option>
        </select>
        <label class="ms-toggle"><input type="checkbox" id="sp-norm"> Jaccard index</label>
        ${MS.exportButtons('sp-heat')}`,
      body: '<div id="sp-heat" class="ms-chart ms-chart--scroll"></div>',
    })}

    ${MS.card({
      title: 'Species similarity tree',
      subtitle: `UPGMA tree of the Jaccard distance between the ${data.familyPlural} each species carries
                 (1 − shared / union). Species with similar miRNA repertoires join early (left = similar).
                 It reflects shared content, not a phylogeny.` +
                 (data.inputSpecies.size ? ` <span class="ms-legend"><i class="ms-legend__sw ms-legend__sw--input"></i>input species</span>` : ''),
      actions: MS.exportButtons('sp-tree'),
      body: '<div id="sp-tree" class="ms-chart ms-chart--scroll ms-chart--tall"></div>',
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
  $('#sp-order').addEventListener('change', e => { state.heatOrder = e.target.value; drawHeat(data); });
  const sortLabel = { families: 'most families', exclusive: 'most species-specific', name: 'name' };
  MS.bindExports(el, 'mirscope_' + data.run.mode, {
    'sp-bars': () => `${MS.captionPrefix(data)} · ${data.familyPlural} per species · sorted by ${sortLabel[state.sort]}` +
      (state.q ? ` · filter: "${state.q}"` : ''),
    'sp-heat': () => `${MS.captionPrefix(data)} · top ${state.heatN} species · ` +
      (state.heatNorm ? 'Jaccard index' : `shared ${data.familyPlural}`) +
      (state.heatOrder === 'tree' ? ' · UPGMA order' : ''),
    'sp-tree': () => `${MS.captionPrefix(data)} · UPGMA tree of Jaccard distances (${data.familyPlural})`,
  });

  drawBars(data);
  if (data.species.length >= 2) { drawHeat(data); drawTree(data); }
  else ['sp-heat', 'sp-tree'].forEach(id => {
    document.getElementById(id).innerHTML = '<div class="ms-empty">Needs at least two species.</div>';
  });
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
  let picked = [...data.speciesStats]
    .sort((a, b) => b.families - a.families || a.name.localeCompare(b.name))
    .slice(0, state.heatN).map(s => s.name);
  let M = MS.cooccurrence(data.families, picked);
  let tree = null;
  if (state.heatOrder === 'tree' && picked.length > 2) {
    tree = MS.upgma(picked, MS.jaccardDistance(M));
    const order = leaves(tree).map(l => l.index);
    picked = order.map(i => picked[i]);
    M = order.map(i => order.map(j => M[i][j]));
  }
  const n = picked.length;

  const value = (i, j) => {
    if (!state.heatNorm) return M[i][j];
    const union = M[i][i] + M[j][j] - M[i][j];
    return union ? M[i][j] / union : 0;
  };

  const treeW = tree ? 90 : 0;
  const labelW = Math.min(220, 14 + 6.6 * d3.max(picked, s => s.length)) + treeW;
  const avail = MS.widthOf(host, 900) - labelW - 30;
  const cell = Math.max(12, Math.min(34, avail / n));
  const top = labelW - treeW;   // rotated column labels
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

  if (tree) {
    const g = svg.append('g');
    drawDendrogram(g, tree, { x0: 4, width: treeW - 10, top, rowH: cell, maxH: tree.height });
  }

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
    .attr('class', s => 'ms-upset-label' + (data.inputSpecies.has(s) ? ' ms-tree-leaf--input' : ''))
    .attr('x', labelW - 6).attr('y', (s, i) => top + i * cell + cell / 2)
    .attr('dy', '0.35em').attr('text-anchor', 'end').style('font-size', fs)
    .text(s => s);
  svg.append('g').selectAll('text').data(picked).join('text')
    .attr('class', 'ms-upset-label')
    .attr('transform', (s, i) => `translate(${labelW + i * cell + cell / 2},${top - 6}) rotate(-60)`)
    .attr('dy', '0.35em').style('font-size', fs)
    .text(s => s);
}

/** Leaves of an UPGMA tree, top to bottom. */
function leaves(node, out = []) {
  if (node.children) node.children.forEach(c => leaves(c, out));
  else out.push(node);
  return out;
}

/**
 * Draw `tree` as a left-to-right elbow dendrogram: leaves at x0 + width,
 * the root at x0. Leaf k sits at y = top + k*rowH + rowH/2.
 */
function drawDendrogram(g, tree, { x0, width, top, rowH, maxH }) {
  const x = d3.scaleLinear().domain([maxH || 1, 0]).range([x0, x0 + width]);
  let k = 0;
  (function layout(node) {
    if (node.children) {
      node.children.forEach(layout);
      node._y = d3.mean(node.children, c => c._y);
    } else {
      node._y = top + (k++) * rowH + rowH / 2;
    }
    node._x = x(node.height);
  })(tree);
  const links = [];
  (function collect(node) {
    if (!node.children) return;
    node.children.forEach(c => { links.push([node, c]); collect(c); });
  })(tree);
  g.selectAll('path').data(links).join('path')
    .attr('class', 'ms-tree-link')
    .attr('d', ([p, c]) => `M${p._x},${p._y}V${c._y}H${c._x}`);
  return x;
}

function drawTree(data) {
  const host = document.getElementById('sp-tree');
  host.innerHTML = '';
  const names = data.speciesStats.filter(s => s.families > 0).map(s => s.name);
  if (names.length < 2) { host.innerHTML = '<div class="ms-empty">Needs at least two species.</div>'; return; }
  const M = MS.cooccurrence(data.families, names);
  const tree = MS.upgma(names, MS.jaccardDistance(M));
  const order = leaves(tree);

  const rowH = 15;
  const labelW = Math.min(260, 20 + 6.6 * d3.max(names, s => s.length));
  const width = Math.max(560, MS.widthOf(host, 900) - 20);
  const treeW = width - labelW - 20;
  const m = { top: 30, bottom: 10 };
  const height = m.top + order.length * rowH + m.bottom;

  const svg = d3.select(host).append('svg')
    .attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
  const x = drawDendrogram(svg.append('g'), tree, { x0: 10, width: treeW, top: m.top, rowH, maxH: tree.height });
  svg.append('g').attr('class', 'ms-axis')
    .attr('transform', `translate(0,${m.top - 6})`)
    .call(d3.axisTop(x).ticks(6, '.2f').tickSize(-(order.length * rowH + 6)))
    .call(g => g.select('.domain').remove())
    .call(g => g.selectAll('line').attr('stroke-opacity', 0.5));
  svg.append('text').attr('class', 'ms-axis-label').attr('x', 10).attr('y', 10).text('Jaccard distance');

  const stat = new Map(data.speciesStats.map(s => [s.name, s]));
  svg.append('g').selectAll('text').data(order).join('text')
    .attr('class', d => 'ms-tree-leaf' + (data.inputSpecies.has(d.name) ? ' ms-tree-leaf--input' : ''))
    .attr('x', 10 + treeW + 6).attr('y', (d, i) => m.top + i * rowH + rowH / 2).attr('dy', '0.35em')
    .text(d => d.name)
    .on('mouseenter', (e, d) => {
      const s = stat.get(d.name);
      MS.tooltip.show(`<strong>${MS.esc(d.name)}</strong><br>${MS.fmt(s.families)} ${data.familyPlural}` +
        ` · ${MS.fmt(s.exclusive)} species-specific` + (data.inputSpecies.has(d.name) ? '<br>input species' : ''), e);
    })
    .on('mousemove', e => MS.tooltip.move(e))
    .on('mouseleave', () => MS.tooltip.hide());
}

window.msInitSpecies = msInitSpecies;
})();
