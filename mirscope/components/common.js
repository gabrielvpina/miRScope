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

  function _svgString(svgEl) {
    const clone = svgEl.cloneNode(true);
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    // Resolve var(--x) references so the file renders outside the page.
    const root = getComputedStyle(document.documentElement);
    clone.querySelectorAll('*').forEach(node => {
      ['fill', 'stroke'].forEach(attr => {
        const v = node.getAttribute(attr);
        if (v && v.startsWith('var(')) {
          node.setAttribute(attr, root.getPropertyValue(v.slice(4, -1).trim()).trim());
        }
      });
    });
    const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    style.textContent = 'text{font-family:' + cssVar('--ms-font') + ';}';
    clone.insertBefore(style, clone.firstChild);
    return new XMLSerializer().serializeToString(clone);
  }

  function exportSVG(svgEl, filename) {
    if (!svgEl) return;
    const blob = new Blob([_svgString(svgEl)], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    _download(url, filename);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportPNG(svgEl, filename, scale = 2) {
    if (!svgEl) return;
    const box = svgEl.getBoundingClientRect();
    const w = Math.round(box.width * scale), h = Math.round(box.height * scale);
    const url = URL.createObjectURL(new Blob([_svgString(svgEl)], { type: 'image/svg+xml;charset=utf-8' }));
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = w; canvas.height = h;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, w, h);
      ctx.drawImage(img, 0, 0, w, h);
      URL.revokeObjectURL(url);
      _download(canvas.toDataURL('image/png'), filename);
    };
    img.src = url;
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

  /** Wire SVG/PNG buttons inside `root` to the <svg> inside `#<target>`. */
  function bindExports(root, basename) {
    root.querySelectorAll('[data-export]').forEach(btn => {
      btn.addEventListener('click', () => {
        const svg = document.querySelector('#' + btn.dataset.target + ' svg');
        const name = basename + '_' + btn.dataset.target + '.' + btn.dataset.export;
        if (btn.dataset.export === 'svg') exportSVG(svg, name); else exportPNG(svg, name);
      });
    });
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
    esc, fmt, pct, cssVar, on, emit, tooltip,
    exportSVG, exportPNG, downloadCSV,
    card, exportButtons, bindExports, seqHtml, widthOf,
    data: buildModel(typeof MS_REPORT !== 'undefined' ? MS_REPORT : {}),
  };
})();
