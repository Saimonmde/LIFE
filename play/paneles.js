/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Cada panel flotante se cierra, se pliega y se arrastra. La posición se recuerda. */
(() => {
  'use strict';
  const KEY = 'lifeinc.paneles.v1';
  const seen = new WeakSet();

  function read() {
    try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch { return {}; }
  }
  function write(data) {
    try { localStorage.setItem(KEY, JSON.stringify(data)); } catch {}
  }
  function clamp(el) {
    const r = el.getBoundingClientRect();
    const maxX = Math.max(8, innerWidth - r.width - 8);
    const maxY = Math.max(8, innerHeight - 48);
    const x = Math.min(maxX, Math.max(8, r.left));
    const y = Math.min(maxY, Math.max(8, r.top));
    el.style.position = 'fixed';
    el.style.left = x + 'px';
    el.style.top = y + 'px';
    el.style.right = 'auto';
    el.style.bottom = 'auto';
    el.style.transform = 'none';
    el.style.zIndex = '12';
    return { x, y };
  }
  function remember(el) {
    if (!el.id) return;
    const data = read();
    const r = el.getBoundingClientRect();
    data[el.id] = { x: r.left, y: r.top, folded: el.classList.contains('plegado') };
    write(data);
  }
  function arm(el) {
    if (seen.has(el) || el.hidden && !el.id) return;
    const header = el.querySelector('header');
    if (!header) return;
    seen.add(el);
    if (!header.querySelector('.plegar')) {
      const fold = document.createElement('button');
      fold.type = 'button';
      fold.className = 'plegar';
      fold.textContent = '–';
      fold.setAttribute('aria-label', 'Plegar');
      const close = header.querySelector('.x, [data-cierra]');
      header.insertBefore(fold, close || null);
      fold.onclick = (event) => {
        event.stopPropagation();
        el.classList.toggle('plegado');
        fold.textContent = el.classList.contains('plegado') ? '+' : '–';
        remember(el);
      };
    }
    const saved = read()[el.id];
    if (saved && Number.isFinite(saved.x)) {
      el.style.position = 'fixed';
      el.style.left = saved.x + 'px';
      el.style.top = saved.y + 'px';
      el.style.transform = 'none';
      if (saved.folded) el.classList.add('plegado');
      clamp(el);
    }
    let drag = null;
    const point = (event) => event.touches ? event.touches[0] : event;
    const start = (event) => {
      if (event.target.closest('button, a, input, select, textarea')) return;
      const p = point(event);
      const r = el.getBoundingClientRect();
      drag = { dx: p.clientX - r.left, dy: p.clientY - r.top };
      el.style.position = 'fixed';
      el.style.transform = 'none';
    };
    const move = (event) => {
      if (!drag) return;
      const p = point(event);
      el.style.left = (p.clientX - drag.dx) + 'px';
      el.style.top = (p.clientY - drag.dy) + 'px';
      clamp(el);
    };
    const end = () => { if (!drag) return; drag = null; remember(el); };
    header.addEventListener('pointerdown', start);
    header.addEventListener('touchstart', start, { passive: true });
    addEventListener('pointermove', move);
    addEventListener('touchmove', move, { passive: true });
    addEventListener('pointerup', end);
    addEventListener('touchend', end);
  }
  function scan() {
    document.querySelectorAll('.ventana, .panel, #ayuda, #banquito, #furnace-panel, #city-map .city-map-panel').forEach(arm);
  }
  addEventListener('DOMContentLoaded', scan);
  if (document.body) {
    scan();
    new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  }
  window.Paneles = { scan };
})();
