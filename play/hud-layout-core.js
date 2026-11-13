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

  function formatClock(date, timeZone) {
    const zone = timeZone || 'America/Bogota';
    const dtf = new Intl.DateTimeFormat('es-CO', {
      timeZone: zone,
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
    const map = {};
    for (const part of dtf.formatToParts(date)) if (part.type !== 'literal') map[part.type] = part.value;
    const period = String(map.dayPeriod || '').replace(/\u202f/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
    return map.weekday + ' ' + map.day + ' ' + map.month + ' ' + map.year + ' · ' + map.hour + ':' + map.minute + ' ' + period;
  }

  function minimapTile(px, py, view, size) {
    const span = Number(view && view.span);
    const x0 = Number(view && view.x0);
    const y0 = Number(view && view.y0);
    const pxN = Number(px);
    const pyN = Number(py);
    const sizeN = Number(size);
    if (![span, x0, y0, pxN, pyN, sizeN].every(Number.isFinite) || span <= 0 || sizeN <= 0) return null;
    const k = sizeN / span;
    return { x: Math.floor(x0 + pxN / k), y: Math.floor(y0 + pyN / k) };
  }

  function rectsOverlap(a, b) {
    if (!a || !b) return false;
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }

  function staminaStep(energy, locked, wantSprint, moving, dt) {
    let e = Number.isFinite(Number(energy)) ? Number(energy) : 100;
    let lock = !!locked;
    const step = Number.isFinite(Number(dt)) ? Math.max(0, Number(dt)) : 0;
    const sprint = !!wantSprint && !lock && e > 0;
    if (sprint) {
      e = Math.max(0, e - step * 14);
      if (e <= 0) lock = true;
    } else if (e < 100) {
      e = Math.min(100, e + step * (moving ? 5 : 9));
      if (lock && e >= 30) lock = false;
    }
    return { energy: e, locked: lock, sprint: sprint };
  }

  function healthStep(hp, hurtUntil, nowMs, dt) {
    let h = Number.isFinite(Number(hp)) ? Number(hp) : 100;
    const step = Number.isFinite(Number(dt)) ? Math.max(0, Number(dt)) : 0;
    if ((Number(nowMs) || 0) >= (Number(hurtUntil) || 0) && h < 100) h = Math.min(100, h + step * 4);
    return Math.max(0, Math.min(100, h));
  }

  function applyDamage(hp, amount) {
    const h = Number.isFinite(Number(hp)) ? Number(hp) : 100;
    const n = Math.max(0, Number(amount) || 0);
    return Math.max(0, Math.min(100, h - n));
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
    formatClock: formatClock,
    minimapTile: minimapTile,
    rectsOverlap: rectsOverlap,
    staminaStep: staminaStep,
    healthStep: healthStep,
    applyDamage: applyDamage,
  };
})(typeof window === 'undefined' ? globalThis : window);
