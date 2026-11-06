/* ============================================================
   section_cutoff.js — Cutoff tab (strict mode only)
   Re-runs the cohesion clustering in the browser for a sweep of
   identity cutoffs, using the MAFFT alignments stored in the
   report. Same rule as mirscope/clustering.py: a miRNA joins a
   cluster only if its aligned identity (double gaps ignored) to
   EVERY member is >= cutoff; otherwise it starts a new cluster.
   Members are replayed cluster by cluster, which reproduces the
   report exactly at the run cutoff.
   Exposes: msInitCutoff(data)
   ============================================================ */
(function () {
'use strict';

const SWEEP_FROM = 50;
const SWEEP_TO = 100;

let state, result = null;

/** Aligned identity in percent, identical to clustering.aligned_identity. */
function identity(a, b) {
  let match = 0, len = 0;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) {
    const x = a.charCodeAt(i), y = b.charCodeAt(i);
    if (x === 45 && y === 45) continue;   // '-' in both
    if (x === y) match++;
    len++;
  }
  return len ? (match / len) * 100 : 0;
}

/** Group the report's clusters back into their seed families, in replay order. */
function seedGroups(data) {
  const bySeed = new Map();
  data.families.forEach(f => {
    const m = /_Clust_(\d+)$/.exec(f.id);
    const k = m ? +m[1] : 1;
    (bySeed.get(f.seed) || bySeed.set(f.seed, []).get(f.seed)).push({ k, f });
  });
  return [...bySeed.entries()].map(([seed, list]) => {
    list.sort((a, b) => a.k - b.k);
    const members = [];
    list.forEach(({ f }) => f.members.forEach(mb => members.push({
      seq: String(mb.aligned || mb.sequence).toUpperCase(),
      species: mb.species,
    })));
    return { seed, members, reported: list.length };
  });
}

/** Complete-linkage greedy clustering on a precomputed identity matrix. */
function cluster(n, sim, cutoff) {
  const clusters = [];
  for (let i = 0; i < n; i++) {
    let placed = false;
    for (const g of clusters) {
      let ok = true;
      for (let j = 0; j < g.length; j++) { if (sim[i * n + g[j]] < cutoff) { ok = false; break; } }
      if (ok) { g.push(i); placed = true; break; }
    }
    if (!placed) clusters.push([i]);
  }
  return clusters;
}

function msInitCutoff(data) {
  const el = document.getElementById('section-cutoff');
  const runCut = +data.params.cutoff;
  const cutoffs = [...new Set([...d3.range(SWEEP_FROM, SWEEP_TO + 1), runCut])]
    .filter(c => Number.isFinite(c)).sort((a, b) => a - b);
  state = { cutoffs, runCut, sel: runCut };

  el.innerHTML = `
    <header class="ms-hero ms-hero--compact">
      <div>
        <h1 class="ms-hero__title">Cutoff sensitivity</h1>
        <p class="ms-hero__sub">
          The cohesion clustering re-run in your browser from the stored MAFFT alignments,
          for every identity cutoff from ${SWEEP_FROM}% to ${SWEEP_TO}%. The run used
          <strong>${runCut}%</strong>. Use it to see how robust the clusters are, and which
          seed families split or merge as the threshold moves.
        </p>
      </div>
    </header>
    <div id="cu-progress-wrap">
      <div class="ms-progress"><span id="cu-progress"></span></div>
      <p class="ms-hint" id="cu-progress-label">Computing pairwise identities…</p>
    </div>
    <div id="cu-body" hidden>
      <div class="ms-controls">
        <label class="ms-field">Explore cutoff: <span id="cu-sel-label"></span>
          <input type="range" class="ms-range" id="cu-sel" min="0" max="${cutoffs.length - 1}" step="1"
                 value="${cutoffs.indexOf(runCut)}">
        </label>
        <div class="ms-kpis ms-kpis--sm" id="cu-kpis" style="flex:1"></div>
      </div>
      ${MS.card({
        title: 'Clusters per identity cutoff',
        subtitle: `<span class="ms-legend">
          <i class="ms-legend__sw ms-legend__sw--total"></i>all clusters
          <i class="ms-legend__sw ms-legend__sw--shared"></i>shared (≥ 2 species)
          <i class="ms-legend__sw ms-legend__sw--excl"></i>species-specific</span>
          · dashed line = run cutoff, red line = explored cutoff. Click the chart to move it.`,
        actions: MS.exportButtons('cu-chart'),
        body: '<div id="cu-chart" class="ms-chart"></div><p class="ms-hint" id="cu-check"></p>',
      })}
      ${MS.card({
        title: 'Seed families that change the most',
        subtitle: 'Number of clusters at the run cutoff vs. the explored cutoff. Click a row to open the seed in the Families tab.',
        actions: '<button class="ms-btn ms-btn--ghost" id="cu-csv">CSV</button>',
        body: '<div id="cu-table"></div>',
      })}
    </div>`;

  MS.bindExports(el, 'mirscope_' + data.run.mode, {
    'cu-chart': () => `${MS.captionPrefix(data)} · clusters per identity cutoff · explored ${state.sel}%`,
  });
  el.querySelector('#cu-sel').addEventListener('input', e => {
    state.sel = cutoffs[+e.target.value];
    update(data);
  });
  el.querySelector('#cu-csv').addEventListener('click', () => {
    if (!result) return;
    MS.downloadCSV(result.groups, [
      { label: 'seed', value: g => g.seed },
      { label: 'mirnas', value: g => g.members.length },
      { label: 'species', value: g => g.nSpecies },
      ...cutoffs.map((c, i) => ({ label: `clusters_${c}`, value: g => g.counts[i] })),
    ], `mirscope_${data.run.mode}_cutoff_sweep.csv`);
  });

  compute(data, () => {
    el.querySelector('#cu-progress-wrap').hidden = true;
    el.querySelector('#cu-body').hidden = false;
    update(data);
  });
}

/** Run the sweep in time-sliced chunks so the page stays responsive. */
function compute(data, done) {
  const groups = seedGroups(data);
  const C = state.cutoffs.length;
  const totals = state.cutoffs.map(() => ({ total: 0, shared: 0, excl: 0 }));
  const bar = document.getElementById('cu-progress');
  const label = document.getElementById('cu-progress-label');
  const totalPairs = d3.sum(groups, g => g.members.length ** 2) || 1;
  let i = 0, donePairs = 0;

  function step() {
    const t0 = performance.now();
    while (i < groups.length && performance.now() - t0 < 40) {
      const g = groups[i++];
      const n = g.members.length;
      g.nSpecies = new Set(g.members.map(m => m.species)).size;
      g.counts = new Array(C);
      if (n === 1) {
        g.counts.fill(1);
        totals.forEach(t => { t.total += 1; t.excl += 1; });
        continue;
      }
      const sim = new Float64Array(n * n);
      for (let a = 0; a < n; a++) {
        sim[a * n + a] = 100;
        for (let b = a + 1; b < n; b++) {
          const v = identity(g.members[a].seq, g.members[b].seq);
          sim[a * n + b] = v; sim[b * n + a] = v;
        }
      }
      state.cutoffs.forEach((cut, ci) => {
        const cl = cluster(n, sim, cut);
        g.counts[ci] = cl.length;
        const t = totals[ci];
        cl.forEach(members => {
          const deg = new Set(members.map(k => g.members[k].species)).size;
          t.total += 1;
          if (deg >= 2) t.shared += 1; else t.excl += 1;
        });
      });
      donePairs += n * n;
    }
    bar.style.width = (100 * donePairs / totalPairs).toFixed(1) + '%';
    label.textContent = `Re-clustering seed families… ${MS.fmt(i)} / ${MS.fmt(groups.length)}`;
    if (i < groups.length) setTimeout(step, 0);
    else { result = { groups, totals }; done(); }
  }
  step();
}

function update(data) {
  const { cutoffs, runCut, sel } = state;
  const ri = cutoffs.indexOf(runCut), si = cutoffs.indexOf(sel);
  const R = result.totals[ri], S = result.totals[si];
  document.getElementById('cu-sel-label').textContent = sel + '%';

  const delta = (a, b) => {
    const d = a - b;
    return d === 0 ? 'same as run' : `${d > 0 ? '+' : ''}${MS.fmt(d)} vs. run`;
  };
  const kpi = (label, v, ref) => `
    <div class="ms-kpi"><div class="ms-kpi__value">${MS.fmt(v)}</div>
    <div class="ms-kpi__label">${label}</div><div class="ms-kpi__hint">${delta(v, ref)}</div></div>`;
  document.getElementById('cu-kpis').innerHTML =
    kpi('Clusters', S.total, R.total) + kpi('Shared', S.shared, R.shared) + kpi('Species-specific', S.excl, R.excl);

  const reported = data.families.length;
  document.getElementById('cu-check').innerHTML = R.total === reported
    ? `Check: at ${runCut}% the recomputation gives ${MS.fmt(R.total)} clusters, the same as the report.`
    : `<span class="ms-warn">At ${runCut}% the recomputation gives ${MS.fmt(R.total)} clusters, the report has ${MS.fmt(reported)}.</span>`;

  drawChart(data);
  drawTable(data, ri, si);
}

function drawChart(data) {
  const host = document.getElementById('cu-chart');
  host.innerHTML = '';
  const { cutoffs, runCut, sel } = state;
  const pts = cutoffs.map((c, i) => ({ c, ...result.totals[i] }));
  const width = MS.widthOf(host, 900), height = 320;
  const m = { top: 16, right: 24, bottom: 44, left: 64 };
  const x = d3.scaleLinear().domain(d3.extent(cutoffs)).range([m.left, width - m.right]);
  const y = d3.scaleLinear().domain([0, d3.max(pts, p => p.total) || 1]).nice().range([height - m.bottom, m.top]);

  const svg = d3.select(host).append('svg')
    .attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`)
    .style('cursor', 'crosshair');
  svg.append('g').attr('class', 'ms-axis').attr('transform', `translate(${m.left},0)`)
    .call(d3.axisLeft(y).ticks(6, ',d').tickSize(-(width - m.left - m.right)))
    .call(g => g.select('.domain').remove());
  svg.append('g').attr('class', 'ms-axis ms-axis--x').attr('transform', `translate(0,${height - m.bottom})`)
    .call(d3.axisBottom(x).ticks(10).tickFormat(d => d + '%'));
  svg.append('text').attr('class', 'ms-axis-label')
    .attr('x', m.left + (width - m.left - m.right) / 2).attr('y', height - 8).attr('text-anchor', 'middle')
    .text('Identity cutoff');
  svg.append('text').attr('class', 'ms-axis-label')
    .attr('transform', `translate(14,${m.top + (height - m.top - m.bottom) / 2}) rotate(-90)`).attr('text-anchor', 'middle')
    .text('Clusters');

  [['ms-ref-line', runCut], ['ms-cursor-line', sel]].forEach(([cls, c]) => {
    svg.append('line').attr('class', cls).attr('x1', x(c)).attr('x2', x(c)).attr('y1', m.top).attr('y2', height - m.bottom);
  });
  svg.append('text').attr('class', 'ms-ref-label').attr('x', x(runCut) + 4).attr('y', m.top + 10).text(`run ${runCut}%`);

  const series = [['total', 'ms-line--total'], ['shared', 'ms-line--shared'], ['excl', 'ms-line--excl']];
  series.forEach(([k, cls]) => {
    svg.append('path').datum(pts).attr('class', 'ms-line ' + cls)
      .attr('d', d3.line().x(p => x(p.c)).y(p => y(p[k])));
  });
  const selPt = pts[cutoffs.indexOf(sel)];
  series.forEach(([k, cls]) => {
    svg.append('circle').attr('class', 'ms-line-dot').attr('r', 4.5)
      .attr('cx', x(sel)).attr('cy', y(selPt[k]))
      .style('fill', MS.cssVar({ total: '--ms-primary', shared: '--ms-accent', excl: '--ms-sand' }[k]));
  });

  svg.on('mousemove', e => {
    const [mx] = d3.pointer(e);
    const p = pts[d3.minIndex(pts, q => Math.abs(x(q.c) - mx))];
    MS.tooltip.show(`<strong>${p.c}%</strong><br>${MS.fmt(p.total)} clusters<br>` +
      `${MS.fmt(p.shared)} shared · ${MS.fmt(p.excl)} species-specific`, e);
  }).on('mouseleave', () => MS.tooltip.hide())
    .on('click', e => {
      const [mx] = d3.pointer(e);
      const idx = d3.minIndex(pts, q => Math.abs(x(q.c) - mx));
      state.sel = cutoffs[idx];
      document.getElementById('cu-sel').value = idx;
      update(data);
    });
}

function drawTable(data, ri, si) {
  const rows = result.groups
    .filter(g => g.members.length > 1)
    .map(g => ({ g, run: g.counts[ri], sel: g.counts[si], min: d3.min(g.counts), max: d3.max(g.counts) }))
    .sort((a, b) => Math.abs(b.sel - b.run) - Math.abs(a.sel - a.run) || (b.max - b.min) - (a.max - a.min) ||
      b.g.members.length - a.g.members.length)
    .slice(0, 25);
  const host = document.getElementById('cu-table');
  if (!rows.length) { host.innerHTML = '<div class="ms-empty">No multi-member seed families.</div>'; return; }
  host.innerHTML = `
    <table class="ms-table ms-table--hover">
      <thead><tr>
        <th>Seed</th><th class="num">miRNAs</th><th class="num">Species</th>
        <th class="num">Clusters at ${state.runCut}%</th><th class="num">Clusters at ${state.sel}%</th>
        <th class="num">Range ${SWEEP_FROM}–${SWEEP_TO}%</th>
      </tr></thead>
      <tbody>${rows.map(r => `
        <tr data-seed="${MS.esc(r.g.seed)}">
          <td><code class="ms-seed">${MS.esc(r.g.seed)}</code></td>
          <td class="num">${MS.fmt(r.g.members.length)}</td>
          <td class="num">${MS.fmt(r.g.nSpecies)}</td>
          <td class="num">${MS.fmt(r.run)}</td>
          <td class="num">${MS.fmt(r.sel)}${r.sel !== r.run ? ` <span class="ms-muted">(${r.sel > r.run ? '+' : ''}${r.sel - r.run})</span>` : ''}</td>
          <td class="num">${r.min}–${r.max}</td>
        </tr>`).join('')}
      </tbody>
    </table>`;
  host.querySelectorAll('tr[data-seed]').forEach(tr => tr.addEventListener('click', () => {
    MS.activate('families');
    MS.emit('families:open', tr.dataset.seed);
  }));
}

window.msInitCutoff = msInitCutoff;
})();
