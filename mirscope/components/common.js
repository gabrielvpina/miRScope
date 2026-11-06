/* ============================================================
   common.js — shared helpers and the derived data model.
   Everything lives on the global `MS` object so section modules
   can use it without relying on bare global names.
   ============================================================ */
'use strict';

const MS = (function () {

  // ── Formatting / escaping ────────────────────────────────────────────────

  function esc(v) {
    if (v == null) return '';
    return String(v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  const _nf = new Intl.NumberFormat('en-US');
  function fmt(n) { return n == null ? '—' : _nf.format(n); }
  function pct(a, b) { return b ? (100 * a / b).toFixed(1) + '%' : '—'; }

  /** CSS custom property value from :root (used to keep D3 colours in base.css). */
  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  // ── Tiny event bus (cross-section links) ─────────────────────────────────

  const _handlers = {};
  function on(evt, fn) { (_handlers[evt] = _handlers[evt] || []).push(fn); }
  function emit(evt, payload) { (_handlers[evt] || []).forEach(fn => fn(payload)); }

  // ── Tooltip ──────────────────────────────────────────────────────────────

  const tooltip = {
    el() { return document.getElementById('ms-tooltip'); },
    show(html, event) {
      const el = this.el();
      el.innerHTML = html;
      el.classList.add('visible');
      this.move(event);
    },
    move(event) {
      const el = this.el();
      const pad = 14;
      let x = event.clientX + pad;
      let y = event.clientY + pad;
      const r = el.getBoundingClientRect();
      if (x + r.width > window.innerWidth - 8) x = event.clientX - r.width - pad;
      if (y + r.height > window.innerHeight - 8) y = event.clientY - r.height - pad;
      el.style.left = x + 'px';
      el.style.top = y + 'px';
    },
    hide() { this.el().classList.remove('visible'); },
  };

  // ── Downloads ────────────────────────────────────────────────────────────

  function _download(href, filename) {
    const a = document.createElement('a');
    a.href = href;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  // Presentation properties copied from the live page onto the exported SVG.
  // Chart colours come from CSS classes in base.css, which do not travel with
  // the file, so each element gets its computed style inlined.
  const _SVG_PROPS = [
    'fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-opacity',
    'stroke-dasharray', 'stroke-linecap', 'opacity',
    'font-family', 'font-size', 'font-weight', 'font-style',
  ];

  function _isTransparent(v) {
    return v === 'transparent' || /^rgba\(.*,\s*0\)$/.test(v);
  }

  /**
   * Standalone SVG markup for `svgEl`: computed styles inlined, hidden nodes
   * dropped, white background, and an optional caption line at the bottom
   * (used to record the active filters).
   */
  function svgMarkup(svgEl, caption = '') {
    const clone = svgEl.cloneNode(true);
    const src = [svgEl, ...svgEl.querySelectorAll('*')];
    const dst = [clone, ...clone.querySelectorAll('*')];
    const drop = [];
    src.forEach((node, i) => {
      const out = dst[i];
      out.removeAttribute('class');
      out.removeAttribute('style');
      if (node.tagName.toLowerCase() === 'title') return;
      const cs = getComputedStyle(node);
      if (cs.display === 'none' || cs.visibility === 'hidden') { drop.push(out); return; }
      const style = _SVG_PROPS.map(p => {
        let v = cs.getPropertyValue(p);
        if (!v) return '';
        if ((p === 'fill' || p === 'stroke') && _isTransparent(v)) v = 'none';
        return `${p}:${v}`;
      }).filter(Boolean).join(';');
      out.setAttribute('style', style);
    });
    drop.forEach(n => n.remove());

    // Crop the empty space to the right of the drawing (charts are as wide as
    // their card, the content often is not).
    const box = svgEl.getBoundingClientRect();
    let w = Math.ceil(box.width);
    const h = Math.ceil(box.height);
    try {
      const bb = svgEl.getBBox();
      if (bb.width > 0) w = Math.min(w, Math.ceil(bb.x + bb.width + 16));
    } catch (e) { /* getBBox can throw on detached nodes; keep full width */ }
    if (caption) w = Math.max(w, Math.ceil(caption.length * 6.2) + 24);   // never clip the caption
    const capH = caption ? 30 : 0;
    const ns = 'http://www.w3.org/2000/svg';
    clone.setAttribute('xmlns', ns);
    clone.setAttribute('width', w);
    clone.setAttribute('height', h + capH);
    clone.setAttribute('viewBox', `0 0 ${w} ${h + capH}`);

    const bg = document.createElementNS(ns, 'rect');
    bg.setAttribute('width', '100%');
    bg.setAttribute('height', '100%');
    bg.setAttribute('fill', '#ffffff');
    clone.insertBefore(bg, clone.firstChild);

    if (caption) {
      const t = document.createElementNS(ns, 'text');
      t.setAttribute('x', 12);
      t.setAttribute('y', h + 20);
      t.setAttribute('style', `font-family:${cssVar('--ms-font')};font-size:11px;fill:${cssVar('--ms-text-2')}`);
      t.textContent = caption;
      clone.appendChild(t);
    }
    return { markup: new XMLSerializer().serializeToString(clone), width: w, height: h + capH };
  }

  /** Small non-blocking notice (used when an export fails). */
  function toast(message) {
    let el = document.getElementById('ms-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'ms-toast';
      el.className = 'ms-toast';
      el.setAttribute('role', 'status');
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.classList.add('visible');
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove('visible'), 4000);
  }

  function exportSVG(svgEl, filename, caption = '') {
    if (!svgEl) { toast('Nothing to export yet.'); return; }
    const { markup } = svgMarkup(svgEl, caption);
    const url = URL.createObjectURL(new Blob([markup], { type: 'image/svg+xml;charset=utf-8' }));
    _download(url, filename);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportPNG(svgEl, filename, caption = '', scale = 2) {
    if (!svgEl) { toast('Nothing to export yet.'); return; }
    const { markup, width, height } = svgMarkup(svgEl, caption);
    const img = new Image();
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(width * scale);
        canvas.height = Math.round(height * scale);
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(blob => {
          if (!blob) { toast('PNG export failed (image too large?). Try SVG instead.'); return; }
          const url = URL.createObjectURL(blob);
          _download(url, filename);
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        }, 'image/png');
      } catch (err) {
        console.error(err);
        toast('PNG export failed: ' + err.message + '. Try SVG instead.');
      }
    };
    img.onerror = () => toast('PNG export failed while rendering the chart. Try SVG instead.');
    // A data URL (not a blob URL) keeps the canvas untainted on file:// pages.
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(markup);
  }

  function downloadCSV(rows, columns, filename) {
    const cell = v => {
      const s = v == null ? '' : String(v);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    };
    const lines = [columns.map(c => cell(c.label)).join(',')]
      .concat(rows.map(r => columns.map(c => cell(c.value(r))).join(',')));
    const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' }));
    _download(url, filename);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // ── UI building blocks ───────────────────────────────────────────────────

  /** Card wrapper markup. `actions` is extra HTML for the header (buttons). */
  function card({ title, subtitle = '', body = '', actions = '', cls = '' }) {
    return `
      <div class="ms-card ${cls}">
        <div class="ms-card__head">
          <div>
            <h3 class="ms-card__title">${title}</h3>
            ${subtitle ? `<p class="ms-card__sub">${subtitle}</p>` : ''}
          </div>
          <div class="ms-card__actions">${actions}</div>
        </div>
        <div class="ms-card__body">${body}</div>
      </div>`;
  }

  function exportButtons(prefix) {
    return `
      <button class="ms-btn ms-btn--ghost" data-export="svg" data-target="${prefix}">SVG</button>
      <button class="ms-btn ms-btn--ghost" data-export="png" data-target="${prefix}">PNG</button>`;
  }

  /**
   * Wire SVG/PNG buttons inside `root` to the <svg> currently inside
   * `#<target>` (looked up at click time, so it reflects the live filters).
   * `captions[target]` may return a line describing the active filters; it is
   * printed under the exported image.
   */
  function bindExports(root, basename, captions = {}) {
    root.querySelectorAll('[data-export]').forEach(btn => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.target;
        const svg = document.querySelector('#' + target + ' svg');
        const name = basename + '_' + target + '.' + btn.dataset.export;
        const caption = captions[target] ? captions[target]() : '';
        if (btn.dataset.export === 'svg') exportSVG(svg, name, caption);
        else exportPNG(svg, name, caption);
      });
    });
  }

  /** "miRScope v0.4.0 · strict · cutoff 85%" prefix for export captions. */
  function captionPrefix(data) {
    const run = data.run;
    return `miRScope v${run.version} · ${run.mode}` +
      (run.mode === 'strict' ? ` · cutoff ${data.params.cutoff}%` : '');
  }

  /**
   * Render a sequence with the seed region (nucleotides 2–8 of the ungapped
   * sequence) highlighted. Gaps in aligned sequences are kept and dimmed.
   */
  function seqHtml(seq) {
    let pos = 0, out = '';
    for (const ch of String(seq || '')) {
      if (ch === '-' || ch === '.') { out += '<span class="ms-seq__gap">-</span>'; continue; }
      const inSeed = pos >= 1 && pos <= 7;
      out += inSeed ? `<span class="ms-seq__seed">${esc(ch)}</span>` : esc(ch);
      pos += 1;
    }
    return `<span class="ms-seq">${out}</span>`;
  }

  /** Width available inside an element (falls back when it is still hidden). */
  function widthOf(el, fallback = 900) {
    const w = el ? el.getBoundingClientRect().width : 0;
    return w > 50 ? w : fallback;
  }


  // ── Sequence logos ───────────────────────────────────────────────────────

  const NUCS = ['A', 'C', 'G', 'U'];

  /** Empty per-position counter for `len` columns. */
  function logoColumns(len) {
    return Array.from({ length: len }, () => ({ A: 0, C: 0, G: 0, U: 0, gap: 0, n: 0 }));
  }

  /**
   * Add `seqs` to `cols` (from logoColumns). Each sequence set contributes a
   * total weight of `weight`, split evenly between its sequences, so a family
   * with 50 paralogs counts as much as a family with one. `offset` skips that
   * many leading residues of every sequence (0 = start at position 1).
   */
  function logoAdd(cols, seqs, weight = 1, offset = 0) {
    if (!seqs.length) return;
    const w = weight / seqs.length;
    seqs.forEach(seq => {
      for (let i = 0; i < cols.length; i++) {
        const ch = seq[i + offset];
        if (ch === undefined) continue;
        const col = cols[i];
        col.n += w;
        if (ch === 'A' || ch === 'C' || ch === 'G' || ch === 'U') col[ch] += w;
        else if (ch === 'T') col.U += w;
        else col.gap += w;
      }
    });
  }

  /**
   * Draw a sequence logo into `host`. `cols` come from logoColumns/logoAdd.
   * opts: { unit: 'bits'|'prob', labels: [..], shade: [from,to] (column
   * indexes highlighted as the seed), height, colWidth, title }.
   * Letter heights are frequency × information content (bits) or plain
   * frequency (prob). Gap-rich columns shrink with their occupancy.
   */
  function drawLogo(host, cols, opts = {}) {
    host.innerHTML = '';
    const unit = opts.unit || 'bits';
    const colW = opts.colWidth || 30;
    const H = opts.height || 150;
    const m = { top: opts.title ? 24 : 10, right: 10, bottom: 26, left: 44 };
    const width = m.left + cols.length * colW + m.right;
    const height = m.top + H + m.bottom;
    const yMax = unit === 'bits' ? 2 : 1;
    const y = d3.scaleLinear().domain([0, yMax]).range([m.top + H, m.top]);

    const svg = d3.select(host).append('svg')
      .attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);

    if (opts.title) {
      svg.append('text').attr('class', 'ms-axis-label').attr('x', m.left).attr('y', 14).text(opts.title);
    }
    if (opts.shade) {
      const [a, b] = opts.shade;
      svg.append('rect').attr('class', 'ms-logo-seed')
        .attr('x', m.left + a * colW).attr('y', m.top)
        .attr('width', (b - a + 1) * colW).attr('height', H);
    }
    svg.append('g').attr('class', 'ms-axis')
      .attr('transform', `translate(${m.left},0)`)
      .call(d3.axisLeft(y).ticks(unit === 'bits' ? 4 : 5, unit === 'bits' ? '.1f' : '.0%'))
      .call(g => g.select('.domain').remove());
    svg.append('text').attr('class', 'ms-axis-label')
      .attr('transform', `translate(12,${m.top + H / 2}) rotate(-90)`).attr('text-anchor', 'middle')
      .text(unit === 'bits' ? 'bits' : 'frequency');
    svg.append('line').attr('class', 'ms-logo-base')
      .attr('x1', m.left).attr('x2', m.left + cols.length * colW).attr('y1', m.top + H).attr('y2', m.top + H);

    const labels = opts.labels || cols.map((c, i) => i + 1);
    const CAP = 72;   // cap height of a 100px bold sans-serif glyph
    cols.forEach((col, i) => {
      const nt = NUCS.reduce((s, k) => s + col[k], 0);
      const x0 = m.left + i * colW;
      svg.append('text').attr('class', 'ms-logo-pos')
        .attr('x', x0 + colW / 2).attr('y', m.top + H + 16).attr('text-anchor', 'middle').text(labels[i]);
      if (!nt) return;
      const occ = col.n ? nt / col.n : 0;
      const freqs = NUCS.map(k => ({ k, f: col[k] / nt })).filter(d => d.f > 0);
      const entropy = -freqs.reduce((s, d) => s + d.f * Math.log2(d.f), 0);
      const scale = unit === 'bits' ? (2 - entropy) * occ : occ;
      let yb = m.top + H;
      freqs.sort((a, b) => a.f - b.f).forEach(d => {
        const h = (y(0) - y(d.f * scale));
        if (h < 0.5) return;
        svg.append('text').attr('class', 'ms-logo-nt ms-nt-' + d.k)
          .attr('transform', `translate(${x0 + 1},${yb}) scale(1,${h / CAP})`)
          .attr('textLength', colW - 2).attr('lengthAdjust', 'spacingAndGlyphs')
          .style('font-size', '100px')
          .text(d.k)
          .on('mouseenter', e => tooltip.show(
            `Position <strong>${labels[i]}</strong><br>` +
            freqs.slice().sort((a, b) => b.f - a.f).map(q => `${q.k}: ${(100 * q.f).toFixed(1)}%`).join(' · ') +
            `<br>${(2 - entropy).toFixed(2)} bits` + (occ < 0.999 ? ` · ${(100 * (1 - occ)).toFixed(0)}% gaps` : ''), e))
          .on('mousemove', e => tooltip.move(e))
          .on('mouseleave', () => tooltip.hide());
        yb -= h;
      });
    });
    return svg.node();
  }

  // ── Clustering ───────────────────────────────────────────────────────────

  /**
   * UPGMA on a symmetric distance matrix. Returns a d3.hierarchy-ready tree:
   * leaves {name, index}, internal nodes {children:[a,b], height}. `height`
   * is the merge distance (leaves 0).
   */
  function upgma(names, dist) {
    const n = names.length;
    let nodes = names.map((name, index) => ({ name, index, height: 0, size: 1 }));
    const D = dist.map(r => r.slice());
    let active = d3.range(n);
    while (active.length > 1) {
      let best = Infinity, bi = -1, bj = -1;
      for (let a = 0; a < active.length; a++) {
        for (let b = a + 1; b < active.length; b++) {
          const v = D[active[a]][active[b]];
          if (v < best) { best = v; bi = active[a]; bj = active[b]; }
        }
      }
      const A = nodes[bi], B = nodes[bj];
      const merged = { children: [A, B], height: best, size: A.size + B.size };
      // Re-use slot bi for the merged node.
      active.forEach(k => {
        if (k === bi || k === bj) return;
        const v = (D[bi][k] * A.size + D[bj][k] * B.size) / (A.size + B.size);
        D[bi][k] = D[k][bi] = v;
      });
      nodes[bi] = merged;
      active = active.filter(k => k !== bj);
    }
    return nodes[active[0]];
  }

  /** Pairwise shared-family counts between `names` (diagonal = families per species). */
  function cooccurrence(families, names) {
    const idx = new Map(names.map((s, i) => [s, i]));
    const n = names.length;
    const M = Array.from({ length: n }, () => new Float64Array(n));
    families.forEach(f => {
      const ii = [];
      f.species.forEach(s => { const i = idx.get(s); if (i !== undefined) ii.push(i); });
      for (let a = 0; a < ii.length; a++) {
        M[ii[a]][ii[a]] += 1;
        for (let b = a + 1; b < ii.length; b++) { M[ii[a]][ii[b]] += 1; M[ii[b]][ii[a]] += 1; }
      }
    });
    return M;
  }

  /** Jaccard distance matrix (1 − |A∩B| / |A∪B|) from a co-occurrence matrix. */
  function jaccardDistance(M) {
    return M.map((row, i) => Array.from(row, (v, j) => {
      if (i === j) return 0;
      const union = M[i][i] + M[j][j] - v;
      return union ? 1 - v / union : 1;
    }));
  }

  // ── Derived data model ───────────────────────────────────────────────────

  function buildModel(report) {
    const run = report.run || {};
    const species = report.species || [];
    const families = (report.families || []).map(f => ({
      ...f,
      degree: f.species.length,
      size: f.members.length,
    }));
    const familyById = new Map(families.map(f => [f.id, f]));

    const intersections = ((report.intersections || {}).all || []);
    const intersectionOfFamily = new Map();
    intersections.forEach(i => i.families.forEach(fid => intersectionOfFamily.set(fid, i.id)));

    // Per-species statistics.
    const stats = new Map(species.map(name => [name, {
      name, families: 0, exclusive: 0, shared: 0, mirnas: 0,
    }]));
    families.forEach(f => {
      f.species.forEach(name => {
        const s = stats.get(name) || stats.set(name, { name, families: 0, exclusive: 0, shared: 0, mirnas: 0 }).get(name);
        s.families += 1;
        if (f.degree === 1) s.exclusive += 1; else s.shared += 1;
      });
      f.members.forEach(m => { const s = stats.get(m.species); if (s) s.mirnas += 1; });
    });

    // Species that came from --input files (matched by file name).
    const inputFiles = new Set(((run.parameters || {}).inputs || []).map(p => String(p).split(/[\\/]/).pop()));
    const inputSpecies = new Map();   // species -> source file
    if (inputFiles.size) {
      families.forEach(f => f.members.forEach(m => {
        if (inputFiles.has(m.source_file)) inputSpecies.set(m.species, m.source_file);
      }));
    }

    return {
      run,
      params: run.parameters || {},
      inputSpecies,
      isStrict: run.mode === 'strict',
      familyLabel: run.mode === 'strict' ? 'cluster' : 'seed family',
      familyPlural: run.mode === 'strict' ? 'clusters' : 'seed families',
      species,
      families,
      familyById,
      intersections,
      intersectionById: new Map(intersections.map(i => [i.id, i])),
      intersectionOfFamily,
      upsetIds: ((report.intersections || {}).upset || {}).ids || [],
      speciesStats: [...stats.values()],
    };
  }

  return {
    esc, fmt, pct, cssVar, on, emit, tooltip, toast,
    svgMarkup, exportSVG, exportPNG, downloadCSV,
    card, exportButtons, bindExports, captionPrefix, seqHtml, widthOf,
    NUCS, logoColumns, logoAdd, drawLogo, upgma, cooccurrence, jaccardDistance,
    data: buildModel(typeof MS_REPORT !== 'undefined' ? MS_REPORT : {}),
  };
})();
