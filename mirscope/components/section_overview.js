/* ============================================================
   section_overview.js — Overview tab
   KPI cards · run parameters · conservation spectrum (histogram
   of species per family) · most conserved families.
   Exposes: msInitOverview(data)
   ============================================================ */
(function () {
'use strict';

function kpi(label, value, hint = '') {
  return `
    <div class="ms-kpi">
      <div class="ms-kpi__value">${value}</div>
      <div class="ms-kpi__label">${label}</div>
      ${hint ? `<div class="ms-kpi__hint">${hint}</div>` : ''}
    </div>`;
}

function paramRow(label, value) {
  return `<div class="ms-params__row"><dt>${label}</dt><dd>${value}</dd></div>`;
}

function msInitOverview(data) {
  const el = document.getElementById('section-overview');
  const { run, params, families, species } = data;
  const counts = run.counts || {};
  const shared = families.filter(f => f.degree > 1).length;
  const maxDegree = families.reduce((m, f) => Math.max(m, f.degree), 0);
  const famWord = data.isStrict ? 'Orthologous clusters' : 'Seed families';

  const inputs = (params.inputs || []).length
    ? params.inputs.map(p => `<code>${MS.esc(p.split('/').pop())}</code>`).join(' ')
    : '<span class="ms-muted">none</span>';
  const failed = run.failed_seeds || [];

  el.innerHTML = `
    <header class="ms-hero">
      <div>
        <h1 class="ms-hero__title">${data.isStrict ? 'Strict orthology' : 'Broad conservation'}</h1>
        <p class="ms-hero__sub">
          ${data.isStrict
            ? `Seed families aligned with MAFFT and split into cohesion clusters at ${params.cutoff}% identity.`
            : 'miRNAs grouped by exact seed identity (nucleotides 2–8), no alignment.'}
        </p>
      </div>
    </header>

    <div class="ms-kpis">
      ${kpi('miRNAs', MS.fmt(counts.mirnas))}
      ${kpi('Species', MS.fmt(counts.species ?? species.length))}
      ${kpi(famWord, MS.fmt(counts.families ?? families.length))}
      ${kpi('Shared across species', MS.fmt(shared), MS.pct(shared, families.length) + ' of ' + data.familyPlural)}
      ${kpi('Species intersections', MS.fmt(counts.intersections))}
      ${kpi('Widest conservation', MS.fmt(maxDegree), 'species in one ' + data.familyLabel)}
    </div>

    <div class="ms-grid ms-grid--2-1">
      ${MS.card({
        title: 'Conservation spectrum',
        subtitle: `How many ${data.familyPlural} are present in N species. Click a bar to list them.`,
        actions: `
          <label class="ms-toggle"><input type="checkbox" id="ov-log"> log scale</label>
          ${MS.exportButtons('ov-spectrum')}`,
        body: '<div id="ov-spectrum" class="ms-chart"></div>',
      })}
      ${MS.card({
        title: 'Run parameters',
        body: `
          <dl class="ms-params">
            ${paramRow('Mode', `<span class="ms-pill">${MS.esc(run.mode)}</span>`)}
            ${data.isStrict ? paramRow('Identity cutoff', params.cutoff + '%') : ''}
            ${paramRow('Reference', `<code title="${MS.esc(params.data_dir)}">${MS.esc((params.data_dir || '').split('/').slice(-2).join('/'))}</code>`)}
            ${paramRow('Input files', inputs)}
            ${paramRow('UpSet top-n', params.top_n ? params.top_n : 'all')}
            ${paramRow('UpSet min-size', params.min_size)}
            ${paramRow('UpSet min-degree', params.min_degree)}
            ${data.isStrict ? paramRow('Failed alignments', failed.length
              ? `<span class="ms-warn" title="${MS.esc(failed.join(', '))}">${failed.length} seed(s)</span>`
              : '0') : ''}
            ${paramRow('miRScope', 'v' + MS.esc(run.version))}
          </dl>`,
      })}
    </div>

    ${MS.card({
      title: `Most conserved ${data.familyPlural}`,
      subtitle: 'Ranked by number of species. Click a row to open it in the Families tab.',
      body: '<div id="ov-top"></div>',
    })}
  `;

  drawSpectrum(data, false);
  el.querySelector('#ov-log').addEventListener('change', e => drawSpectrum(data, e.target.checked));
  MS.bindExports(el, 'mirscope_' + run.mode);
  drawTop(data);
}

function drawSpectrum(data, logScale) {
  const host = document.getElementById('ov-spectrum');
  host.innerHTML = '';
  const byDegree = d3.rollup(data.families, v => v.length, f => f.degree);
  const bins = [...byDegree.entries()].map(([degree, n]) => ({ degree, n })).sort((a, b) => a.degree - b.degree);
  if (!bins.length) { host.innerHTML = '<div class="ms-empty">No families.</div>'; return; }

  const width = MS.widthOf(host, 700);
  const height = 300;
  const m = { top: 16, right: 16, bottom: 44, left: 56 };
  const maxDeg = d3.max(bins, d => d.degree);

  const x = d3.scaleBand()
    .domain(d3.range(1, maxDeg + 1))
    .range([m.left, width - m.right])
    .padding(0.15);
  const yMax = d3.max(bins, d => d.n);
  const y = logScale
    ? d3.scaleLog().domain([1, yMax * 1.2]).range([height - m.bottom, m.top]).clamp(true)
    : d3.scaleLinear().domain([0, yMax]).nice().range([height - m.bottom, m.top]);

  const svg = d3.select(host).append('svg')
    .attr('width', width).attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`);

  svg.append('g')
    .attr('class', 'ms-axis')
    .attr('transform', `translate(${m.left},0)`)
    .call(d3.axisLeft(y).ticks(5, logScale ? '~s' : ',d').tickSize(-(width - m.left - m.right)))
    .call(g => g.select('.domain').remove());

  const step = Math.max(1, Math.ceil(maxDeg / Math.floor((width - m.left - m.right) / 28)));
  svg.append('g')
    .attr('class', 'ms-axis ms-axis--x')
    .attr('transform', `translate(0,${height - m.bottom})`)
    .call(d3.axisBottom(x).tickValues(x.domain().filter(d => d === 1 || d % step === 0)).tickSizeOuter(0));

  svg.append('text')
    .attr('class', 'ms-axis-label')
    .attr('x', m.left + (width - m.left - m.right) / 2).attr('y', height - 8)
    .attr('text-anchor', 'middle')
    .text('Number of species');
  svg.append('text')
    .attr('class', 'ms-axis-label')
    .attr('transform', `translate(14,${m.top + (height - m.top - m.bottom) / 2}) rotate(-90)`)
    .attr('text-anchor', 'middle')
    .text(data.isStrict ? 'Clusters' : 'Seed families');

  svg.append('g').selectAll('rect').data(bins).join('rect')
    .attr('class', d => 'ms-bar' + (d.degree === 1 ? ' ms-bar--muted' : ''))
    .attr('x', d => x(d.degree))
    .attr('width', x.bandwidth())
    .attr('y', d => y(Math.max(d.n, logScale ? 1 : 0)))
    .attr('height', d => y(logScale ? 1 : 0) - y(Math.max(d.n, logScale ? 1 : 0)))
    .attr('rx', 2)
    .style('cursor', 'pointer')
    .on('mouseenter', (e, d) => MS.tooltip.show(
      `<strong>${MS.fmt(d.n)}</strong> ${d.n === 1 ? data.familyLabel : data.familyPlural}<br>in exactly ${d.degree} species`, e))
    .on('mousemove', e => MS.tooltip.move(e))
    .on('mouseleave', () => MS.tooltip.hide())
    .on('click', (e, d) => {
      MS.tooltip.hide();
      MS.activate('families');
      MS.emit('families:filter', { minDegree: d.degree, maxDegree: d.degree });
    });
}

function drawTop(data) {
  const host = document.getElementById('ov-top');
  const top = [...data.families].sort((a, b) => b.degree - a.degree || b.size - a.size).slice(0, 12);
  const total = data.species.length || 1;
  host.innerHTML = `
    <table class="ms-table ms-table--hover">
      <thead><tr>
        <th>${data.isStrict ? 'Cluster' : 'Seed family'}</th><th>Seed</th>
        <th class="num">Species</th><th class="num">miRNAs</th><th>Coverage</th>
      </tr></thead>
      <tbody>
        ${top.map(f => `
          <tr data-family="${MS.esc(f.id)}">
            <td><code>${MS.esc(f.id)}</code></td>
            <td><code class="ms-seed">${MS.esc(f.seed)}</code></td>
            <td class="num">${MS.fmt(f.degree)}</td>
            <td class="num">${MS.fmt(f.size)}</td>
            <td><div class="ms-meter"><span style="width:${(100 * f.degree / total).toFixed(1)}%"></span></div></td>
          </tr>`).join('')}
      </tbody>
    </table>`;
  host.querySelectorAll('tr[data-family]').forEach(tr => tr.addEventListener('click', () => {
    MS.activate('families');
    MS.emit('families:open', tr.dataset.family);
  }));
}

window.msInitOverview = msInitOverview;
})();
