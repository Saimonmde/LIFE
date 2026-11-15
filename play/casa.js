/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Casa colonial privada (Antioquia, siglos XVII–XIX).
   Cada jugador tiene su propio interior. El plano queda en este navegador
   y, con cuenta, también en el servidor. */
(() => {
  'use strict';
  const MAP_W = 14, MAP_H = 12;
  const DOOR = { x: 4, y: 9 };
  const SPAWN = { x: 4, y: 6, dir: 'down' };
  // Único desplazamiento del Parque de Envigado. Lo escribe tools/valle_aburra.py.
  const VALLE_OFFSET = { x: -133, y: 203 };
  const PARK_DOOR = { x: 226 + VALLE_OFFSET.x, y: 64 + VALLE_OFFSET.y };
  const PARK_STAND = { x: 227 + VALLE_OFFSET.x, y: 64 + VALLE_OFFSET.y };
  const CATALOG = {
    bed: { name: 'Camita', w: 2, h: 1, solid: true, styles: { retazos: 'Cobija de retazos', colonial: 'Cama colonial', dosel: 'Cama con dosel', catre: 'Catre de madera' } },
    altar: { name: 'Altar', w: 1, h: 1, solid: true, styles: { madera: 'Mesa de madera', velas: 'Altar de velas', hornacina: 'Hornacina', familiar: 'Altar familiar' } },
    bacenilla: { name: 'Bacenilla', w: 1, h: 1, solid: true },
    cocina: { name: 'Cocina', w: 2, h: 1, solid: true, styles: { lena: 'Fogón de leña', barro: 'Cocina de barro', carbon: 'Anafe de carbón', estufa: 'Estufa de hierro' } },
    ventana: { name: 'Ventanita', w: 1, h: 1, solid: true },
    matica: { name: 'Matica', w: 1, h: 1, solid: true, styles: { flores: 'Flores en matera', helecho: 'Helecho', sabila: 'Sábila', orquidea: 'Orquídea', cinta: 'Cinta' } },
    table: { name: 'Mesa', w: 2, h: 1, solid: true },
    chair: { name: 'Silla', w: 1, h: 1, solid: true },
    chest: { name: 'Baúl', w: 1, h: 1, solid: true },
    stove: { name: 'Cocina', w: 1, h: 1, solid: true },
    pots: { name: 'Ollas', w: 1, h: 1, solid: true },
    plant: { name: 'Matera', w: 1, h: 1, solid: true },
    rug: { name: 'Tapete', w: 2, h: 2, solid: false },
    candle: { name: 'Vela', w: 1, h: 1, solid: false },
    painting: { name: 'Cuadro', w: 1, h: 1, solid: false },
    shelf: { name: 'Estante', w: 1, h: 1, solid: true },
  };
  const ORDER = ['bed', 'altar', 'bacenilla', 'cocina', 'ventana', 'matica', 'table', 'chair', 'chest', 'stove', 'pots', 'plant', 'rug', 'candle', 'painting', 'shelf'];
  const MAX_ITEMS = 36;
  const VARIANTS = {
    bed: [{ id: 'colonial', name: 'Colonial' }, { id: 'nogal', name: 'Nogal' }, { id: 'hamaca', name: 'Hamaca' }],
    altar: [{ id: 'madera', name: 'Madera' }, { id: 'piedra', name: 'Piedra' }, { id: 'dorado', name: 'Dorado' }],
    plant: [{ id: 'barro', name: 'Barro' }, { id: 'blanca', name: 'Blanca' }, { id: 'colgante', name: 'Colgante' }],
    stove: [{ id: 'fogon', name: 'Fogón' }, { id: 'lena', name: 'Leña' }, { id: 'mesa', name: 'Mesa' }],
  };
  const WALLS = [
    { id: 'bahareque', name: 'Bahareque', color: '#e4c48a' },
    { id: 'ocre', name: 'Ocre', color: '#c9894a' },
    { id: 'cal', name: 'Cal', color: '#f4f0e6' },
    { id: 'blanco', name: 'Cal blanca', color: '#f7f1e4' },
    { id: 'crema', name: 'Crema', color: '#efe2c4' },
    { id: 'sol', name: 'Sol', color: '#e7d39a' },
    { id: 'salvia', name: 'Salvia', color: '#d5ddc8' },
    { id: 'anil', name: 'Añil', color: '#6f8f9a' },
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
      v: 2, wall: '#e4c48a', floor: '#c45c38',
      items: [
        { id: 'bed', type: 'bed', x: 1, y: 1, rot: 0, style: 'retazos' },
        { id: 'bacenilla', type: 'bacenilla', x: 3, y: 1, rot: 0, style: '' },
        { id: 'altar', type: 'altar', x: 5, y: 1, rot: 0, style: 'velas' },
        { id: 'cocina', type: 'cocina', x: 6, y: 1, rot: 0, style: 'lena' },
        { id: 'ventana', type: 'ventana', x: 1, y: 3, rot: 0, style: '' },
        { id: 'matica-flores', type: 'matica', x: 2, y: 3, rot: 0, style: 'flores' },
        { id: 'table', type: 'table', x: 5, y: 3, rot: 0, style: '' },
        { id: 'chair', type: 'chair', x: 7, y: 4, rot: 0, style: '' },
        { id: 'cuadro', type: 'painting', x: 8, y: 2, rot: 0, style: '' },
        { id: 'matica-helecho', type: 'matica', x: 8, y: 5, rot: 0, style: 'helecho' },
        { id: 'tapete', type: 'rug', x: 3, y: 5, rot: 0, style: '' },
        { id: 'vela', type: 'candle', x: 6, y: 6, rot: 0, style: '' },
        { id: 'chest', type: 'chest', x: 1, y: 7, rot: 0, style: '' },
        { id: 'estante', type: 'shelf', x: 8, y: 7, rot: 0, style: '' },
        { id: 'matica-sabila', type: 'matica', x: 11, y: 3, rot: 0, style: 'sabila' },
        { id: 'matica-orquidea', type: 'matica', x: 12, y: 5, rot: 0, style: 'orquidea' },
        { id: 'matica-cinta', type: 'matica', x: 10, y: 6, rot: 0, style: 'cinta' },
      ],
    };
  }
  function stylesOf(type) {
    const spec = CATALOG[type];
    return spec && spec.styles ? Object.keys(spec.styles) : [];
  }
  function styleOf(type, raw) {
    const styles = stylesOf(type);
    if (!styles.length) return '';
    return styles.includes(raw) ? raw : styles[0];
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
      if (!raw || !CATALOG[raw.type] || items.length >= MAX_ITEMS) continue;
      let id = String(raw.id || raw.type).replace(/[^\w-]/g, '').slice(0, 24) || raw.type;
      if (seen.has(id)) id = raw.type + '-' + items.length;
      const item = { id, type: raw.type, x: raw.x | 0, y: raw.y | 0, rot: ((raw.rot | 0) % 4 + 4) % 4, style: styleOf(raw.type, raw.style) };
      if ((VARIANTS[raw.type] || []).some(v => v.id === raw.variant)) item.variant = raw.variant;
      if (!canPlace(items, item)) continue;
      seen.add(id);
      items.push(item);
    }
    return items.length ? { v: 1, wall, floor: tint, items } : base;
  }

  let layout = defaultLayout();
  let visitLayout = null, visitInfo = null;
  let editing = false, armed = null, armedStyle = '', selected = null, variantPick = null;
  const legacyKey = (name) => 'lifeinc.casa.v1:' + encodeURIComponent(String(name || 'viajero').trim().toLowerCase().slice(0, 16) || 'viajero');
  const storageKey = (name) => {
    const owner = window.Casa.ownerKey ? window.Casa.ownerKey() : name;
    return 'lifeinc.casa.v1:' + encodeURIComponent(String(owner || name || 'viajero').slice(0, 64));
  };
  function load(name) {
    try {
      let raw = localStorage.getItem(storageKey(name));
      const mid = window.SaimonSession && window.SaimonSession.municipio;
      if (!raw && (!mid || mid === 'envigado')) raw = localStorage.getItem(legacyKey(name));
      const parsed = raw ? JSON.parse(raw) : null;
      layout = parsed && Array.isArray(parsed.items) ? sanitize(parsed) : defaultLayout();
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
    if (visitLayout) return;
    save(window.Casa.playerName ? window.Casa.playerName() : 'viajero');
    if (window.Hogar) window.Hogar.guardar({ casa: layout });
    if (window.Casa.onLayout) window.Casa.onLayout();
    renderEditor();
  }
  function apply(data) {
    layout = sanitize(data || defaultLayout());
    selected = null;
    save(window.Casa.playerName ? window.Casa.playerName() : 'viajero');
    if (window.Casa.onLayout) window.Casa.onLayout();
    renderEditor();
    return layout;
  }
  function reemplazar(data) {
    if (visitLayout || !data) return layout;
    layout = sanitize(data);
    save(window.Casa.playerName ? window.Casa.playerName() : 'viajero');
    if (window.Casa.onLayout) window.Casa.onLayout();
    return layout;
  }
  function ponerVisita(data) {
    visitLayout = sanitize(data.casa || data);
    visitInfo = {
      codigo: String(data.codigo || ''),
      dueno: String(data.dueno || 'alguien'),
      mascotas: Array.isArray(data.mascotas) ? data.mascotas : [],
    };
    document.body.classList.add('casa-visita');
    setEditing(false);
    if (window.Casa.onLayout) window.Casa.onLayout();
    return visitLayout;
  }
  function quitarVisita(silent) {
    visitLayout = null;
    visitInfo = null;
    document.body.classList.remove('casa-visita');
    const banda = document.getElementById('visita-banda');
    if (banda) banda.hidden = true;
    if (!silent && window.Casa.onLayout) window.Casa.onLayout();
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
    panel.innerHTML = '<header>Editar casa <button type="button" id="casa-done">Listo</button></header><p class="casa-hint">Elige un mueble y toca el suelo para colocarlo. Toca uno puesto para moverlo, rotarlo o quitarlo. La camita, el altar, la cocina y las maticas tienen varios tipos. El plano se guarda en el servidor.</p><div id="casa-catalog"></div><div id="casa-estilos"></div><div id="casa-variants"></div><div id="casa-actions"><button type="button" id="casa-rot" disabled>Rotar</button><button type="button" id="casa-del" disabled>Quitar</button></div><div id="casa-walls"><span>Pared</span></div><div id="casa-floors"><span>Piso</span></div><p id="casa-status" role="status"></p>';
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
      b.onclick = () => { armed = type; armedStyle = styleOf(type, ''); variantPick = (VARIANTS[type] && VARIANTS[type][0].id) || null; selected = null; renderEditor(); };
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
    const variants = root.querySelector('#casa-variants');
    if (variants) {
      variants.replaceChildren();
      for (const variant of VARIANTS[armed] || []) {
        const b = document.createElement('button');
        b.type = 'button';
        b.textContent = variant.name;
        b.classList.toggle('armed', variant.id === variantPick);
        b.onclick = () => { variantPick = variant.id; renderEditor(); };
        variants.append(b);
      }
    }
    const item = layout.items.find(i => i.id === selected);
    root.querySelector('#casa-rot').disabled = root.querySelector('#casa-del').disabled = !item;
    const estilo = root.querySelector('#casa-estilos');
    estilo.replaceChildren();
    const tipo = item ? item.type : armed;
    const estilos = stylesOf(tipo);
    if (estilos.length) {
      const etiqueta = document.createElement('span');
      etiqueta.textContent = 'Tipo';
      estilo.append(etiqueta);
      for (const id of estilos) {
        const b = document.createElement('button');
        b.type = 'button';
        b.textContent = CATALOG[tipo].styles[id];
        const activo = item ? item.style === id : armedStyle === id;
        b.classList.toggle('armed', activo);
        b.onclick = () => {
          if (item) { item.style = id; commit(); return; }
          armedStyle = id;
          renderEditor();
        };
        estilo.append(b);
      }
    }
    const nombre = (it) => CATALOG[it.type].name + (CATALOG[it.type].styles && it.style ? ' · ' + CATALOG[it.type].styles[it.style] : '');
    statusEl.textContent = item
      ? 'Seleccionado: ' + nombre(item) + '. Toca otra baldosa para moverlo.'
      : armed ? 'Colocar: ' + nombre({ type: armed, style: armedStyle }) + '. Toca el suelo.' : 'Toca un mueble o elige uno del catálogo.';
  }
  function setEditing(on) {
    if (on && visitLayout) { if (statusEl) statusEl.textContent = 'Estás de visita: no puedes editar esta casa.'; return; }
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
    if (visitLayout) return false;
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
      if (layout.items.length >= MAX_ITEMS) { statusEl.textContent = 'La casa ya está llena (' + MAX_ITEMS + ' muebles).'; return true; }
      const item = { id: armed + '-' + Math.random().toString(36).slice(2, 7), type: armed, x, y, rot: 0, style: styleOf(armed, armedStyle) };
      if (VARIANTS[armed]) item.variant = variantPick || VARIANTS[armed][0].id;
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
    MAP_W, MAP_H, DOOR, SPAWN, VALLE_OFFSET, PARK_DOOR, PARK_STAND, CATALOG, WALLS, FLOORS, floor, MAX_ITEMS,
    get layout() { return visitLayout || layout; },
    get propio() { return layout; },
    get editing() { return editing; },
    get selected() { return selected; },
    get visita() { return visitInfo; },
    cellsOf, canPlace, load, save, apply, buildMap, mount, setEditing, clickTile, renderEditor, reemplazar, ponerVisita, quitarVisita, styleOf,
    playerName: () => 'viajero',
    onLayout: null, onEdit: null, enter: null,
  };
})();
