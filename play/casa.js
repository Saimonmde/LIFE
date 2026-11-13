/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Casa colonial privada (Antioquia, siglos XVII–XIX).
   Cada jugador tiene su propio interior; el plano se guarda en localStorage por nombre. */
(() => {
  'use strict';
  const MAP_W = 14, MAP_H = 12;
  const DOOR = { x: 4, y: 9 };
  const SPAWN = { x: 4, y: 6, dir: 'down' };
  const PARK_DOOR = { x: 226, y: 64 };
  const PARK_STAND = { x: 227, y: 64 };
  const CATALOG = {
    bed: { name: 'Cama', w: 2, h: 1, solid: true },
    table: { name: 'Mesa', w: 2, h: 1, solid: true },
    chair: { name: 'Silla', w: 1, h: 1, solid: true },
    chest: { name: 'Baúl', w: 1, h: 1, solid: true },
    stove: { name: 'Fogón', w: 1, h: 1, solid: true },
    pots: { name: 'Ollas', w: 1, h: 1, solid: true },
    plant: { name: 'Planta', w: 1, h: 1, solid: true },
    rug: { name: 'Alfombra', w: 2, h: 2, solid: false },
    candle: { name: 'Vela', w: 1, h: 1, solid: false },
    painting: { name: 'Cuadro', w: 1, h: 1, solid: false },
    shelf: { name: 'Estante', w: 1, h: 1, solid: true },
  };
  const ORDER = ['bed', 'table', 'chair', 'chest', 'stove', 'pots', 'plant', 'rug', 'candle', 'painting', 'shelf'];
  const WALLS = [
    { id: 'cal', name: 'Cal', color: '#f4f0e6' },
    { id: 'crema', name: 'Crema', color: '#efe2c4' },
    { id: 'sol', name: 'Sol', color: '#e7d39a' },
    { id: 'salvia', name: 'Salvia', color: '#d5ddc8' },
  ];
  const FLOORS = [
    { id: 'teja', name: 'Teja', color: '#c45c38' },
    { id: 'barro', name: 'Barro', color: '#a84832' },
    { id: 'ladrillo', name: 'Ladrillo', color: '#d4895c' },
    { id: 'piedra', name: 'Piedra', color: '#b7a48a' },
  ];
  const floor = new Map();
  const mark = (x, y, kind) => floor.set(x + ',' + y, kind);
  for (let y = 1; y <= 8; y++) for (let x = 1; x <= 8; x++) mark(x, y, 'room');
  for (const [x, y] of [[9, 3], [9, 4], [9, 5]]) mark(x, y, 'hall');
  for (let y = 2; y <= 7; y++) for (let x = 10; x <= 12; x++) mark(x, y, 'patio');
  mark(DOOR.x, DOOR.y, 'door');
  mark(DOOR.x, DOOR.y - 1, 'threshold');
  mark(DOOR.x - 1, DOOR.y - 1, 'threshold');
  mark(DOOR.x + 1, DOOR.y - 1, 'threshold');

  function defaultLayout() {
    return {
      v: 1, wall: '#f4f0e6', floor: '#c45c38',
      items: [
        { id: 'bed', type: 'bed', x: 1, y: 1, rot: 0 },
        { id: 'stove', type: 'stove', x: 7, y: 1, rot: 0 },
        { id: 'pots', type: 'pots', x: 8, y: 1, rot: 0 },
        { id: 'table', type: 'table', x: 5, y: 3, rot: 0 },
        { id: 'chair-a', type: 'chair', x: 5, y: 4, rot: 0 },
        { id: 'chair-b', type: 'chair', x: 7, y: 3, rot: 0 },
        { id: 'shelf', type: 'shelf', x: 1, y: 4, rot: 0 },
        { id: 'candle', type: 'candle', x: 6, y: 4, rot: 0 },
        { id: 'painting', type: 'painting', x: 8, y: 5, rot: 0 },
        { id: 'rug', type: 'rug', x: 5, y: 6, rot: 0 },
        { id: 'chest', type: 'chest', x: 1, y: 7, rot: 0 },
        { id: 'plant-a', type: 'plant', x: 11, y: 3, rot: 0 },
        { id: 'plant-b', type: 'plant', x: 12, y: 5, rot: 0 },
      ],
    };
  }

  function sizeOf(item) {
    const spec = CATALOG[item.type];
    if (!spec) return null;
    const turn = ((item.rot % 4) + 4) % 4;
    const swap = turn % 2 === 1;
    return { w: swap ? spec.h : spec.w, h: swap ? spec.w : spec.h, solid: spec.solid, turn };
  }
  function cellsOf(item) {
    const s = sizeOf(item);
    if (!s) return [];
    const out = [];
    for (let dy = 0; dy < s.h; dy++) for (let dx = 0; dx < s.w; dx++) out.push([item.x + dx, item.y + dy]);
    return out;
  }
  function occupied(items, ignoreId) {
    const map = new Map();
    for (const it of items) {
      if (it.id === ignoreId) continue;
      const solid = !!CATALOG[it.type]?.solid;
      for (const [x, y] of cellsOf(it)) {
        const key = x + ',' + y;
        if (solid || !map.has(key)) map.set(key, solid ? 'solid' : 'soft');
      }
    }
    return map;
  }
  function canPlace(items, item, ignoreId) {
    const spec = CATALOG[item.type];
    if (!spec || item.x < 0 || item.y < 0) return false;
    const occ = occupied(items, ignoreId);
    for (const [x, y] of cellsOf(item)) {
      const kind = floor.get(x + ',' + y);
      if (!kind || kind === 'door' || kind === 'threshold') return false;
      if (spec.solid && x === SPAWN.x && y === SPAWN.y) return false;
      const prev = occ.get(x + ',' + y);
      if (spec.solid && prev) return false;
      if (!spec.solid && prev === 'soft') return false;
    }
    return true;
  }
  function sanitize(data) {
    const base = defaultLayout();
    const wall = WALLS.some(w => w.color === data.wall) ? data.wall : base.wall;
    const tint = FLOORS.some(w => w.color === data.floor) ? data.floor : base.floor;
    const items = [];
    const seen = new Set();
    for (const raw of data.items || []) {
      if (!raw || !CATALOG[raw.type] || items.length >= 30) continue;
      let id = String(raw.id || raw.type).replace(/[^\w-]/g, '').slice(0, 24) || raw.type;
      if (seen.has(id)) id = raw.type + '-' + items.length;
      const item = { id, type: raw.type, x: raw.x | 0, y: raw.y | 0, rot: ((raw.rot | 0) % 4 + 4) % 4 };
      if (!canPlace(items, item)) continue;
      seen.add(id);
      items.push(item);
    }
    return items.length ? { v: 1, wall, floor: tint, items } : base;
  }

  let layout = defaultLayout();
  let editing = false, armed = null, selected = null;
  const storageKey = (name) => 'lifeinc.casa.v1:' + encodeURIComponent(String(name || 'viajero').trim().toLowerCase().slice(0, 16) || 'viajero');
  function load(name) {
    try {
      const raw = JSON.parse(localStorage.getItem(storageKey(name)) || 'null');
      layout = raw && Array.isArray(raw.items) ? sanitize(raw) : defaultLayout();
    } catch (e) { layout = defaultLayout(); }
    selected = null;
    if (window.Casa.onLayout) window.Casa.onLayout();
    return layout;
  }
  function save(name) {
    try { localStorage.setItem(storageKey(name), JSON.stringify(layout)); return true; }
    catch (e) { return false; }
  }
  function commit() {
    save(window.Casa.playerName ? window.Casa.playerName() : 'viajero');
    if (window.Casa.onLayout) window.Casa.onLayout();
    renderEditor();
  }
  function buildMap(current) {
    const L = current || layout;
    const collision = Array.from({ length: MAP_H }, () => Array(MAP_W).fill(1));
    const ground = Array.from({ length: MAP_H }, () => Array(MAP_W).fill(0));
    const elevation = Array.from({ length: MAP_H }, () => Array(MAP_W).fill(0));
    for (const [key, kind] of floor) {
      const [x, y] = key.split(',').map(Number);
      collision[y][x] = 0;
      ground[y][x] = kind === 'patio' ? 1 : 0;
    }
    for (const it of L.items) {
      if (!CATALOG[it.type]?.solid) continue;
      for (const [x, y] of cellsOf(it)) {
        if (floor.has(x + ',' + y) && !(x === DOOR.x && y === DOOR.y) && !(x === SPAWN.x && y === SPAWN.y)) collision[y][x] = 1;
      }
    }
    return {
      width: MAP_W, height: MAP_H, ground, collision, elevation,
      nodes: [{ id: 'puerta_salida', type: 'casa_exit', x: DOOR.x, y: DOOR.y, initialState: 'active', states: ['active'], sprites: { active: 'home_door' }, solid: false }],
      npcs: [], doors: [], animals: [],
      regions: [{ id: 'casa', name: 'Tu casa · Medellín', x: 0, y: 0, w: MAP_W, h: MAP_H }],
      waypoints: [], roads3d: [], memories: [], riverLayouts: [], bridges: [], parkDetails: [],
      surfaceZones: [], signs3d: [], scenery3d: [], waterBodies: {}, decorations: [], landmarks: [], areas: [],
      spawn: { x: SPAWN.x, y: SPAWN.y, facing: SPAWN.dir },
    };
  }

  let root, catalogEl, statusEl;
  function mount() {
    if (document.getElementById('b-editar-casa')) return;
    const edit = document.createElement('button');
    edit.id = 'b-editar-casa'; edit.type = 'button'; edit.textContent = 'Editar casa';
    edit.setAttribute('aria-pressed', 'false');
    edit.onclick = () => setEditing(!editing);
    const home = document.createElement('button');
    home.id = 'b-casa'; home.type = 'button'; home.textContent = 'Casa';
    home.onclick = () => { if (window.Casa.enter) window.Casa.enter(); };
    const leave = document.createElement('button');
    leave.id = 'b-salir-parque'; leave.type = 'button'; leave.textContent = 'Salir al Parque';
    leave.onclick = () => { if (window.Casa.exit) window.Casa.exit(); };
    const panel = document.createElement('section');
    panel.id = 'casa-editor'; panel.hidden = true; panel.setAttribute('aria-label', 'Editar la casa');
    panel.innerHTML = '<header>Editar casa <button type="button" id="casa-done">Listo</button></header><p class="casa-hint">Elige un mueble y toca el suelo para colocarlo. Toca uno puesto para moverlo, rotarlo o quitarlo.</p><div id="casa-catalog"></div><div id="casa-actions"><button type="button" id="casa-rot" disabled>Rotar</button><button type="button" id="casa-del" disabled>Quitar</button></div><div id="casa-walls"><span>Pared</span></div><div id="casa-floors"><span>Piso</span></div><p id="casa-status" role="status"></p>';
    document.body.append(edit, home, leave, panel);
    root = panel;
    catalogEl = panel.querySelector('#casa-catalog');
    statusEl = panel.querySelector('#casa-status');
    panel.querySelector('#casa-done').onclick = () => setEditing(false);
    panel.querySelector('#casa-rot').onclick = rotateSelected;
    panel.querySelector('#casa-del').onclick = removeSelected;
    for (const type of ORDER) {
      const b = document.createElement('button');
      b.type = 'button'; b.dataset.type = type; b.textContent = CATALOG[type].name;
      b.onclick = () => { armed = type; selected = null; renderEditor(); };
      catalogEl.append(b);
    }
    for (const w of WALLS) {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'swatch'; b.title = 'Pared ' + w.name; b.style.background = w.color;
      b.onclick = () => { layout.wall = w.color; commit(); };
      panel.querySelector('#casa-walls').append(b);
    }
    for (const w of FLOORS) {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'swatch'; b.title = 'Piso ' + w.name; b.style.background = w.color;
      b.onclick = () => { layout.floor = w.color; commit(); };
      panel.querySelector('#casa-floors').append(b);
    }
  }
  function renderEditor() {
    if (!root) return;
    root.hidden = !editing;
    document.body.classList.toggle('casa-editando', editing);
    const btn = document.getElementById('b-editar-casa');
    if (btn) { btn.textContent = editing ? 'Cerrar edición' : 'Editar casa'; btn.setAttribute('aria-pressed', String(editing)); }
    for (const b of catalogEl.querySelectorAll('button')) b.classList.toggle('armed', b.dataset.type === armed);
    const item = layout.items.find(i => i.id === selected);
    root.querySelector('#casa-rot').disabled = root.querySelector('#casa-del').disabled = !item;
    for (const b of root.querySelectorAll('#casa-walls .swatch')) b.classList.toggle('armed', b.style.backgroundColor && false);
    statusEl.textContent = item
      ? 'Seleccionado: ' + CATALOG[item.type].name + '. Toca otra baldosa para moverlo.'
      : armed ? 'Colocar: ' + CATALOG[armed].name + '. Toca el suelo.' : 'Toca un mueble o elige uno del catálogo.';
  }
  function setEditing(on) {
    editing = !!on;
    if (!editing) { armed = null; selected = null; }
    renderEditor();
    if (window.Casa.onEdit) window.Casa.onEdit(editing);
  }
  function rotateSelected() {
    const item = layout.items.find(i => i.id === selected);
    if (!item) return;
    const next = { ...item, rot: (item.rot + 1) % 4 };
    if (!canPlace(layout.items, next, item.id)) { statusEl.textContent = 'No cabe al rotar.'; return; }
    item.rot = next.rot;
    commit();
  }
  function removeSelected() {
    layout.items = layout.items.filter(i => i.id !== selected);
    selected = null;
    commit();
  }
  function clickTile(x, y, itemId) {
    if (!editing) return false;
    x |= 0; y |= 0;
    if (itemId) {
      const known = layout.items.some(i => i.id === itemId);
      if (known) { selected = itemId; armed = null; renderEditor(); return true; }
    }
    if (selected) {
      const item = layout.items.find(i => i.id === selected);
      if (!item) { selected = null; renderEditor(); return true; }
      const next = { ...item, x, y };
      if (!canPlace(layout.items, next, item.id)) { statusEl.textContent = 'Ahí no cabe.'; return true; }
      item.x = x; item.y = y;
      commit();
      return true;
    }
    if (armed) {
      if (layout.items.length >= 30) { statusEl.textContent = 'La casa ya está llena (30 muebles).'; return true; }
      const item = { id: armed + '-' + Math.random().toString(36).slice(2, 7), type: armed, x, y, rot: 0 };
      if (!canPlace(layout.items, item)) { statusEl.textContent = 'Ahí no cabe.'; return true; }
      layout.items.push(item);
      selected = item.id;
      armed = null;
      commit();
      return true;
    }
    statusEl.textContent = 'Elige un mueble del catálogo o toca uno de la casa.';
    return true;
  }

  window.Casa = {
    MAP_W, MAP_H, DOOR, SPAWN, PARK_DOOR, PARK_STAND, CATALOG, WALLS, FLOORS, floor,
    get layout() { return layout; },
    get editing() { return editing; },
    get selected() { return selected; },
    cellsOf, canPlace, load, save, buildMap, mount, setEditing, clickTile, renderEditor,
    playerName: () => 'viajero',
    onLayout: null, onEdit: null, enter: null,
  };
})();
