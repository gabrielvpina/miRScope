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

    return {
      run,
      params: run.parameters || {},
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
    data: buildModel(typeof MS_REPORT !== 'undefined' ? MS_REPORT : {}),
  };
})();
