/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Reglas puras del diseño de la interfaz: claves, límites y escala. */
(function (root) {
  'use strict';
  const MIN_SCALE = 0.55;
  const MAX_SCALE = 1.8;

  function storageKey(mobile, portrait) {
    return 'lifeinc.hud.layout.' + (mobile ? 'movil' : 'desktop') + '.' + (portrait ? 'vertical' : 'horizontal');
  }

  function clampBox(x, y, w, h, vw, vh, margin) {
    const m = Number.isFinite(margin) ? margin : 8;
    if (![x, y, w, h, vw, vh].every(Number.isFinite)) return { x: m, y: m };
    const mw = Math.max(1, w);
    const mh = Math.max(1, h);
    const maxX = Math.max(m, vw - mw - m);
    const maxY = Math.max(m, vh - mh - m);
    return {
      x: Math.min(maxX, Math.max(m, x)),
      y: Math.min(maxY, Math.max(m, y)),
    };
  }

  function clampScale(scale) {
    const n = Number(scale);
    if (!Number.isFinite(n)) return 1;
    return Math.min(MAX_SCALE, Math.max(MIN_SCALE, Math.round(n * 100) / 100));
  }

  function stepScale(scale, direction) {
    const dir = direction < 0 ? -1 : 1;
    return clampScale(Number(scale) + dir * 0.1);
  }

  function pack(panels) {
    return JSON.stringify({ v: 1, panels: panels || {} });
  }

  function unpack(raw) {
    try {
      const data = JSON.parse(raw || '');
      if (!data || typeof data.panels !== 'object' || !data.panels) return {};
      const out = {};
      for (const [id, entry] of Object.entries(data.panels)) {
        if (!entry || typeof entry !== 'object') continue;
        const item = {};
        if (Number.isFinite(entry.x)) item.x = entry.x;
        if (Number.isFinite(entry.y)) item.y = entry.y;
        if (Number.isFinite(entry.scale)) item.scale = clampScale(entry.scale);
        if (entry.minimized) item.minimized = true;
        if (entry.closed) item.closed = true;
        out[id] = item;
      }
      return out;
    } catch (e) {
      return {};
    }
  }

  function saveLayout(store, key, panels) {
    store.setItem(key, pack(panels));
  }

  function loadLayout(store, key) {
    return unpack(store.getItem(key));
  }

  function fitScale(scale, width, height, vw, vh, margin) {
    const m = Number.isFinite(margin) ? margin : 8;
    let next = clampScale(scale);
    if (width > 0 && width > vw - m * 2) next = clampScale(next * ((vw - m * 2) / width));
    if (height > 0 && height > vh - m * 2) next = clampScale(next * ((vh - m * 2) / height));
    return next;
  }

  root.HudLayoutCore = {
    MIN_SCALE: MIN_SCALE,
    MAX_SCALE: MAX_SCALE,
    storageKey: storageKey,
    clampBox: clampBox,
    clampScale: clampScale,
    stepScale: stepScale,
    pack: pack,
    unpack: unpack,
    saveLayout: saveLayout,
    loadLayout: loadLayout,
    fitScale: fitScale,
  };
})(typeof window === 'undefined' ? globalThis : window);
