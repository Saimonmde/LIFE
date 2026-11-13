/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Rueda de configuración, modo edición y paneles que se cierran o minimizan. */
(() => {
  'use strict';
  const Core = window.HudLayoutCore;
  const PIECES = [
    ['hud-perfil', 'Perfil y tiempo', 'hud'],
    ['hud-reloj', 'Reloj', 'hud'],
    ['hud-top', 'Botones', 'hud'],
    ['hud-mapa', 'Minimapa', 'hud'],
    ['p-misiones', 'Misiones', 'hud'],
    ['p-cercanos', 'Jugadores cercanos', 'hud'],
    ['hud-chat', 'Chat', 'hud'],
    ['hotbar', 'Barra rápida', 'hud'],
    ['hud-recursos', 'Bolsa, SMC y Plata', 'hud'],
    ['sai-legal', 'Aviso SMC', 'hud'],
    ['pow-panel', 'Minado SMC', 'hud'],
    ['plata-panel', 'Plata', 'hud'],
    ['objetivo', 'Objetivo', 'hud'],
    ['aviso', 'Aviso', 'hud'],
    ['dialogo', 'Diálogo', 'hud'],
    ['world-tools', 'Herramientas', 'hud'],
    ['w-inv', 'Inventario', 'window'],
    ['w-hab', 'Habilidades', 'window'],
    ['w-libro', 'Libro Mayor', 'window'],
    ['w-libro-madre', 'Libro madre', 'window'],
    ['ayuda', 'Ayuda', 'window'],
    ['tutorial', 'Cómo jugar', 'window'],
    ['banquito', 'Banquito', 'window'],
    ['furnace-panel', 'Horno', 'window'],
    ['memories', 'Memorias', 'window'],
    ['camera-panel', 'Cámara', 'window'],
    ['casa-editor', 'Editor de casa', 'window'],
    ['world-routes', 'Recorrido', 'window'],
    ['forge-chat-card', 'Fundición', 'window'],
    ['city-map-panel', 'Mapa', 'window'],
  ];
  const BUTTONS = new Set(['sai-legal']);
  const managed = new Map();
  let dirty = false;
  let profileKey = '';
  let drag = null;

  function profile() {
    const mobile = document.documentElement.classList.contains('movil') || innerWidth < 820;
    const portrait = innerHeight >= innerWidth;
    return { mobile, portrait, key: Core.storageKey(mobile, portrait), tight: mobile || portrait || innerHeight < 520 };
  }
  function editing() { return document.body.classList.contains('hud-editando'); }
  function pieceEl(id) { return managed.get(id) || null; }
  function keyOf(el) { return el.dataset.hudKey || el.id; }

  function place(el, x, y, scale) {
    const s = Core.clampScale(scale);
    el.classList.add('hud-puesto');
    el.dataset.hudX = String(Math.round(x));
    el.dataset.hudY = String(Math.round(y));
    el.dataset.hudScale = String(s);
    el.style.setProperty('--hud-tf', 'translate(' + Math.round(x) + 'px,' + Math.round(y) + 'px) scale(' + s + ')');
  }
  function readBox(el) {
    return {
      x: Number(el.dataset.hudX),
      y: Number(el.dataset.hudY),
      scale: Number(el.dataset.hudScale) || 1,
    };
  }
  function clampEl(el) {
    if (!el.classList.contains('hud-puesto') || el.classList.contains('hud-cerrado')) return;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return;
    let scale = readBox(el).scale;
    const fitted = Core.fitScale(scale, rect.width, rect.height, innerWidth, innerHeight, 8);
    if (fitted < scale - 0.01) {
      place(el, Number(el.dataset.hudX) || rect.left, Number(el.dataset.hudY) || rect.top, fitted);
    }
    const now = el.getBoundingClientRect();
    const box = Core.clampBox(now.left, now.top, now.width, now.height, innerWidth, innerHeight, 8);
    if (Math.abs(box.x - now.left) > 1 || Math.abs(box.y - now.top) > 1) place(el, box.x, box.y, readBox(el).scale);
  }

  function defaults(id, view) {
    const vw = innerWidth;
    const vh = innerHeight;
    const edge = 8;
    const right = (w) => Math.max(edge, vw - w - edge);
    const bottom = (h) => Math.max(edge, vh - h - edge);
    const phone = view.mobile;
    const portrait = view.portrait;
    const table = {
      'hud-perfil': { x: edge, y: edge, scale: phone ? 0.62 : (portrait ? 0.78 : 1) },
      'hud-reloj': { x: edge, y: phone ? (portrait ? bottom(130) : 70) : 8, scale: phone ? 0.92 : 1 },
      'hud-mapa': { x: right(phone ? 130 : 188), y: edge, scale: phone ? 0.55 : (portrait ? 0.7 : 1) },
      'hud-top': { x: edge, y: phone ? (portrait ? 132 : 86) : (portrait ? 210 : 8), scale: phone ? 0.82 : 1 },
      'hud-recursos': { x: right(phone ? 150 : 210), y: bottom(phone ? 58 : 52), scale: phone ? 0.85 : 1 },
      'plata-panel': { x: edge, y: phone ? (portrait ? 430 : 250) : 420, scale: phone ? 0.78 : 1 },
      'hotbar': { x: Math.max(edge, (vw - (phone ? 280 : 420)) / 2), y: bottom(phone ? 64 : 62), scale: phone ? 0.8 : 1 },
      'chat-toggle': { x: edge, y: bottom(portrait ? 128 : 96), scale: 1 },
      'hud-toggle': { x: right(148), y: bottom(portrait ? 124 : 58), scale: 1 },
      'hud-chat': { x: edge, y: bottom(portrait ? 280 : 230), scale: phone ? 0.9 : 1, minimized: portrait },
      'p-misiones': { x: right(230), y: portrait ? 168 : 200, scale: phone ? 0.85 : 1, minimized: true },
      'p-cercanos': { x: right(230), y: portrait ? 220 : 300, scale: phone ? 0.85 : 1, minimized: true },
      'objetivo': { x: edge, y: portrait ? 188 : 120, scale: phone ? 0.85 : 1, minimized: phone || portrait },
      'sai-legal': { x: edge, y: bottom(portrait ? 190 : 150), scale: 0.85, minimized: true },
      'world-tools': { x: edge, y: portrait ? 230 : 176, scale: phone ? 0.85 : 1, minimized: phone || portrait },
      'mine-route': { x: right(170), y: bottom(168), scale: 1 },
      'mine-exit-route': { x: right(170), y: bottom(214), scale: 1 },
      'b-descansar': { x: right(150), y: bottom(portrait ? 70 : 16), scale: phone ? 0.85 : 1 },
      'touch-extra': { x: right(120), y: bottom(portrait ? 280 : 220), scale: 1 },
      'movil-menu': { x: right(120), y: phone ? 78 : 8, scale: 1 },
      'aviso': { x: Math.max(edge, (vw - 320) / 2), y: bottom(140), scale: phone ? 0.85 : 1, minimized: portrait },
      'dialogo': { x: Math.max(edge, (vw - 360) / 2), y: 64, scale: phone ? 0.85 : 1 },
    };
    return table[id] || null;
  }

  function setMinimized(el, on) {
    el.classList.toggle('hud-minimo', !!on);
    const btn = el.querySelector(':scope > header .hud-min');
    if (btn) {
      btn.textContent = on ? '+' : '−';
      btn.setAttribute('aria-label', (on ? 'Restaurar ' : 'Minimizar ') + (el.dataset.hudTitle || 'panel'));
    }
  }
  function userClose(el) {
    el.dataset.hudUserClosed = '1';
    if ((el.dataset.hudKind || 'hud') === 'hud') el.classList.add('hud-cerrado');
    if (el.dataset.hudKey === 'hud-chat' && window.ChatUI) window.ChatUI.setOpen(false);
    const map = el.closest('#city-map');
    if (map) map.hidden = true;
    if (el.classList.contains('ventana') || el.classList.contains('panel') || ['ayuda', 'tutorial', 'banquito', 'furnace-panel', 'memories', 'camera-panel', 'casa-editor', 'world-routes'].includes(el.id)) el.hidden = true;
    dirty = true;
    persist();
    paintReopen();
  }
  function userOpen(id) {
    const el = pieceEl(id);
    if (!el) return;
    el.classList.remove('hud-cerrado');
    el.dataset.hudUserClosed = '0';
    if (id === 'hud-chat' && window.ChatUI) window.ChatUI.setOpen(true);
    else if (id === 'city-map-panel') { const map = document.getElementById('city-map'); if (map) map.hidden = false; }
    else el.hidden = false;
    setMinimized(el, false);
    if (!el.classList.contains('hud-puesto')) pinCurrent(el);
    dirty = true;
    persist();
    paintReopen();
  }

  function ensureChrome(el, title) {
    el.classList.add('hud-pieza');
    el.dataset.hudTitle = title;
    if (el.querySelector(':scope > .info-fold') && !el.querySelector(':scope > header')) {
      if (!el.querySelector(':scope > .hud-asa')) addHandle(el);
      if (!el.dataset.hudDrag) bindPointer(el);
      return;
    }
    let header = el.querySelector(':scope > header');
    if (!header) {
      header = document.createElement('header');
      header.className = 'hud-chrome';
      const name = document.createElement('span');
      name.className = 'hud-title';
      name.textContent = title;
      header.appendChild(name);
      el.prepend(header);
    }
    if (!header.querySelector('.hud-escala')) {
      const smaller = document.createElement('button');
      smaller.type = 'button';
      smaller.className = 'hud-escala';
      smaller.textContent = '–';
      smaller.setAttribute('aria-label', 'Achicar ' + title);
      const bigger = document.createElement('button');
      bigger.type = 'button';
      bigger.className = 'hud-escala';
      bigger.textContent = '+';
      bigger.setAttribute('aria-label', 'Agrandar ' + title);
      smaller.addEventListener('click', (e) => { e.stopPropagation(); bump(el, -1); });
      bigger.addEventListener('click', (e) => { e.stopPropagation(); bump(el, 1); });
      header.append(smaller, bigger);
    }
    if (!header.querySelector('.hud-min')) {
      const min = document.createElement('button');
      min.type = 'button';
      min.className = 'hud-min';
      min.textContent = el.classList.contains('hud-minimo') ? '+' : '−';
      min.setAttribute('aria-label', 'Minimizar ' + title);
      min.addEventListener('click', (e) => {
        e.stopPropagation();
        const on = !el.classList.contains('hud-minimo');
        setMinimized(el, on);
        dirty = true;
        persist();
      });
      header.appendChild(min);
    }
    let close = header.querySelector('.hud-x, .x, [data-cierra]');
    if (!close) {
      close = document.createElement('button');
      close.type = 'button';
      close.className = 'hud-x';
      close.textContent = '×';
      close.setAttribute('aria-label', 'Cerrar ' + title);
      header.appendChild(close);
    } else close.classList.add('hud-x');
    if (!close.dataset.hudClose) {
      close.dataset.hudClose = '1';
      close.addEventListener('click', (e) => { e.stopPropagation(); userClose(el); });
    }
    if (header.lastElementChild !== close) header.appendChild(close);
    if (!header.dataset.hudTap) {
      header.dataset.hudTap = '1';
      header.addEventListener('click', (e) => {
        if (editing() || e.target.closest('button')) return;
        if (el.classList.contains('hud-minimo')) { setMinimized(el, false); dirty = true; persist(); }
      });
    }
    if (!el.querySelector(':scope > .hud-asa')) addHandle(el);
    if (!el.dataset.hudDrag) bindPointer(el);
  }
  function addHandle(el) {
    const handle = document.createElement('div');
    handle.className = 'hud-asa';
    handle.setAttribute('role', 'slider');
    handle.setAttribute('aria-label', 'Cambiar tamaño');
    handle.addEventListener('pointerdown', (e) => {
      if (!editing()) return;
      e.preventDefault();
      e.stopPropagation();
      const start = e.clientX;
      const box = readBox(el);
      const origin = el.getBoundingClientRect();
      drag = { type: 'resize', el, start, scale: box.scale, width: Math.max(48, origin.width), x: box.x, y: box.y };
      handle.setPointerCapture(e.pointerId);
    });
    el.appendChild(handle);
  }
  function bindPointer(el) {
    el.dataset.hudDrag = '1';
    el.addEventListener('pointerdown', (e) => {
      if (!editing()) return;
      if (e.target.closest('button, a, input, select, textarea, label, .hud-asa')) return;
      e.preventDefault();
      e.stopPropagation();
      if (!el.classList.contains('hud-puesto')) pinCurrent(el);
      const box = readBox(el);
      drag = { type: 'move', el, dx: e.clientX - box.x, dy: e.clientY - box.y };
      el.setPointerCapture(e.pointerId);
    }, true);
  }
  function pinCurrent(el) {
    const rect = el.getBoundingClientRect();
    if (rect.width < 2) return false;
    place(el, rect.left, rect.top, readBox(el).scale || 1);
    return true;
  }
  function bump(el, dir) {
    if (!el.classList.contains('hud-puesto')) pinCurrent(el);
    const box = readBox(el);
    place(el, box.x, box.y, Core.stepScale(box.scale, dir));
    clampEl(el);
    dirty = true;
    persist();
  }
  function wrapButton(el, id) {
    if (el.parentElement && el.parentElement.classList.contains('hud-shell')) return el.parentElement;
    const rect = el.getBoundingClientRect();
    const shell = document.createElement('div');
    shell.className = 'hud-shell hud-pieza';
    shell.id = 'shell-' + id;
    shell.dataset.hudKey = id;
    el.parentElement.insertBefore(shell, el);
    shell.appendChild(el);
    el.classList.add('hud-in-shell');
    if (rect.width > 2) place(shell, rect.left, rect.top, 1);
    return shell;
  }
  function syncShell(el) {
    if (!el.classList.contains('hud-shell')) return;
    const inner = el.querySelector('.hud-in-shell');
    if (!inner) return;
    const gone = inner.hidden || getComputedStyle(inner).display === 'none';
    el.classList.toggle('hud-shell-off', gone && !el.classList.contains('hud-cerrado'));
  }

  function findRaw(id) {
    if (id === 'city-map-panel') {
      const panel = document.querySelector('#city-map .city-map-panel');
      if (panel && !panel.id) panel.id = 'city-map-panel';
      return panel;
    }
    return document.getElementById(id);
  }
  function register(id, title, kind) {
    const raw = findRaw(id);
    if (!raw) return;
    let el = managed.get(id);
    if (!el) {
      el = raw.tagName === 'BUTTON' || BUTTONS.has(id) ? wrapButton(raw, id) : raw;
      el.dataset.hudKey = id;
      el.dataset.hudKind = kind;
      managed.set(id, el);
    }
    ensureChrome(el, title);
    syncShell(el);
    noteIfShown(el);
  }
  function noteIfShown(el) {
    if (el.dataset.hudKind !== 'window' || el.dataset.hudUserClosed !== '1') return;
    const host = el.id === 'city-map-panel' ? document.getElementById('city-map') : el;
    if (host && !host.hidden) {
      el.dataset.hudUserClosed = '0';
      paintReopen();
    }
  }
  function scan() {
    for (const [id, title, kind] of PIECES) register(id, title, kind);
  }

  function snapshot() {
    const panels = {};
    for (const [id, el] of managed) {
      if (!el.classList.contains('hud-puesto') && el.dataset.hudUserClosed !== '1' && !el.classList.contains('hud-minimo')) continue;
      const box = readBox(el);
      const entry = {};
      if (Number.isFinite(box.x)) entry.x = box.x;
      if (Number.isFinite(box.y)) entry.y = box.y;
      if (Number.isFinite(box.scale)) entry.scale = box.scale;
      if (el.classList.contains('hud-minimo')) entry.minimized = true;
      if (el.dataset.hudUserClosed === '1') entry.closed = true;
      panels[id] = entry;
    }
    return panels;
  }
  function persist(key) {
    if (!dirty) return;
    try { Core.saveLayout(localStorage, key || profile().key, snapshot()); } catch (e) {}
  }
  function clearOwned() {
    for (const el of managed.values()) {
      el.classList.remove('hud-puesto', 'hud-minimo', 'hud-cerrado');
      el.style.removeProperty('--hud-tf');
      delete el.dataset.hudX;
      delete el.dataset.hudY;
      delete el.dataset.hudScale;
      delete el.dataset.hudUserClosed;
      setMinimized(el, false);
      syncShell(el);
    }
  }
  function applyEntry(id, entry) {
    const el = pieceEl(id);
    if (!el || !entry) return;
    if (Number.isFinite(entry.x) && Number.isFinite(entry.y)) place(el, entry.x, entry.y, entry.scale || 1);
    setMinimized(el, !!entry.minimized);
    if (entry.closed) {
      el.dataset.hudUserClosed = '1';
      el.classList.add('hud-cerrado');
    }
  }
  function applyDefaults(view) {
    for (const [id] of PIECES) {
      const spot = defaults(id, view);
      const el = pieceEl(id);
      if (!spot || !el) continue;
      place(el, spot.x, spot.y, spot.scale || 1);
      setMinimized(el, !!spot.minimized);
    }
  }
  function layoutNow() {
    const view = profile();
    profileKey = view.key;
    let saved = {};
    try { saved = Core.loadLayout(localStorage, view.key); } catch (e) { saved = {}; }
    if (saved && Object.keys(saved).length) {
      for (const [id, entry] of Object.entries(saved)) applyEntry(id, entry);
    } else if (view.tight) applyDefaults(view);
    for (const el of managed.values()) {
      if (el.classList.contains('hud-shell') && !el.classList.contains('hud-puesto')) {
        const inner = el.querySelector('.hud-in-shell');
        const rect = inner ? inner.getBoundingClientRect() : el.getBoundingClientRect();
        if (rect.width > 2) place(el, rect.left, rect.top, 1);
      }
      clampEl(el);
      syncShell(el);
    }
  }
  function resetLayout() {
    try { localStorage.removeItem(profile().key); } catch (e) {}
    dirty = false;
    clearOwned();
    const view = profile();
    if (view.tight) applyDefaults(view);
    for (const el of managed.values()) clampEl(el);
    paintReopen();
  }

  function paintReopen() {
    const box = document.getElementById('hud-reopen');
    if (!box) return;
    box.replaceChildren();
    for (const [id, el] of managed) {
      if (el.dataset.hudUserClosed !== '1' && !el.classList.contains('hud-cerrado')) continue;
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = 'Mostrar ' + (el.dataset.hudTitle || id);
      b.addEventListener('click', () => userOpen(id));
      box.appendChild(b);
    }
  }
  function setEditing(on) {
    document.body.classList.toggle('hud-editando', !!on);
    const bar = document.getElementById('hud-edit-bar');
    const menu = document.getElementById('hud-gear-menu');
    const gear = document.getElementById('hud-gear');
    if (bar) bar.hidden = !on;
    if (on) {
      if (menu) menu.hidden = true;
      if (gear) gear.setAttribute('aria-expanded', 'false');
      for (const el of managed.values()) if (!el.classList.contains('hud-puesto')) pinCurrent(el);
    }
  }
  function mountGear() {
    if (document.getElementById('hud-gear')) return;
    const gear = document.createElement('button');
    gear.id = 'hud-gear';
    gear.type = 'button';
    gear.className = 'hud';
    gear.textContent = '⚙';
    gear.setAttribute('aria-label', 'Configuración');
    gear.setAttribute('aria-expanded', 'false');
    gear.setAttribute('aria-controls', 'hud-gear-menu');
    const menu = document.createElement('div');
    menu.id = 'hud-gear-menu';
    menu.className = 'hud';
    menu.hidden = true;
    menu.innerHTML = '<button type="button" id="hud-edit-start">Modo edición de interfaz</button><button type="button" id="hud-reset">Restablecer diseño</button><div id="hud-reopen"></div>';
    const bar = document.createElement('div');
    bar.id = 'hud-edit-bar';
    bar.className = 'hud';
    bar.hidden = true;
    bar.innerHTML = '<strong>Edición de interfaz</strong><button type="button" id="hud-edit-reset">Restablecer diseño</button><button type="button" id="hud-edit-done">Listo</button>';
    document.body.append(gear, menu, bar);
    gear.addEventListener('click', (e) => {
      e.stopPropagation();
      if (editing()) { menu.hidden = !menu.hidden; return; }
      menu.hidden = !menu.hidden;
      gear.setAttribute('aria-expanded', String(!menu.hidden));
      paintReopen();
    });
    menu.querySelector('#hud-edit-start').addEventListener('click', () => setEditing(true));
    menu.querySelector('#hud-reset').addEventListener('click', () => { resetLayout(); menu.hidden = true; });
    bar.querySelector('#hud-edit-reset').addEventListener('click', resetLayout);
    bar.querySelector('#hud-edit-done').addEventListener('click', () => setEditing(false));
  }

  addEventListener('pointermove', (e) => {
    if (!drag) return;
    if (drag.type === 'move') {
      place(drag.el, e.clientX - drag.dx, e.clientY - drag.dy, readBox(drag.el).scale);
      clampEl(drag.el);
    } else if (drag.type === 'resize') {
      const next = Core.clampScale(drag.scale * ((drag.width + (e.clientX - drag.start)) / drag.width));
      place(drag.el, drag.x, drag.y, next);
      clampEl(drag.el);
    }
  });
  addEventListener('pointerup', () => {
    if (!drag) return;
    drag = null;
    dirty = true;
    persist();
  });
  addEventListener('pointercancel', () => { if (drag) { drag = null; dirty = true; persist(); } });
  addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && editing()) { e.preventDefault(); setEditing(false); }
  });
  function onResize() {
    const next = profile().key;
    if (next !== profileKey) {
      if (dirty) persist(profileKey);
      dirty = false;
      clearOwned();
      scan();
      layoutNow();
      return;
    }
    for (const el of managed.values()) { clampEl(el); syncShell(el); }
  }
  addEventListener('resize', onResize);
  addEventListener('orientationchange', () => setTimeout(() => { onResize(); dispatchEvent(new Event('resize')); }, 60));

  function boot() {
    mountGear();
    scan();
    layoutNow();
    new MutationObserver(() => scan()).observe(document.body, { childList: true, subtree: true });
    setInterval(() => {
      for (const el of managed.values()) { syncShell(el); noteIfShown(el); }
    }, 700);
  }
  function clockZone() {
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (tz) { new Intl.DateTimeFormat('es-CO', { timeZone: tz }).format(); return tz; }
    } catch (e) {}
    return 'America/Bogota';
  }
  function paintClock() {
    const el = document.getElementById('reloj-ahora');
    if (!el || !window.HudLayoutCore) return;
    const now = new Date();
    const zone = clockZone();
    el.dateTime = now.toISOString();
    el.textContent = window.HudLayoutCore.formatClock(now, zone);
  }
  function startClock() {
    paintClock();
    setInterval(paintClock, 1000);
  }
  function start() { startClock(); boot(); }
  if (document.body) start();
  else addEventListener('DOMContentLoaded', start);

  const reopenButtons = { 'w-inv': 'b-inv', 'w-hab': 'b-hab', 'p-misiones': 'b-mis', 'p-cercanos': 'b-soc', 'ayuda': 'b-ayuda', 'w-libro': 'b-libro', 'hud-chat': 'chat-toggle' };
  function clearClosed(id) {
    const el = pieceEl(id);
    if (!el || (el.dataset.hudUserClosed !== '1' && !el.classList.contains('hud-cerrado'))) return;
    el.classList.remove('hud-cerrado');
    el.dataset.hudUserClosed = '0';
    dirty = true;
    persist();
    paintReopen();
  }
  addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn || !btn.id) return;
    for (const [panel, opener] of Object.entries(reopenButtons)) {
      if (btn.id === opener || (panel === 'w-libro' && btn.id === 'b-libro-movil')) clearClosed(panel);
    }
  }, true);

  window.HudLayout = {
    scan, setEditing, resetLayout, userOpen, userClose, place,
    piece: pieceEl,
    minimize(id, on) { const el = pieceEl(id); if (el) { setMinimized(el, on !== false); dirty = true; persist(); } },
    profile,
  };
  window.Paneles = window.Paneles || {};
  window.Paneles.scan = scan;
})();
