/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Banco Central, aparte de la Casa bancaria. La bóveda sólo se abre al dueño o al personal. */
(() => {
  'use strict';
  const DOOR = { x: 118, y: 260 };
  const OUTSIDE = { x: 118, y: 261 };
  const SPAWN = { x: 6, y: 7, dir: 'up' };
  const SOLIDS = [];
  for (let y = 258; y <= 260; y++) {
    for (let x = 116; x <= 120; x++) SOLIDS.push([x, y]);
  }
  const MAP_W = 12;
  const MAP_H = 10;

  function markup(allowed) {
    if (!allowed) return '';
    return [
      '<section id="banco-central" class="banco-central" role="dialog" aria-label="Banco Central">',
      '<header><img src="../graphics/mining/lingote_oro.svg" alt="" width="42" height="42"><h2>Banco Central</h2><button type="button" id="bc-cerrar" aria-label="Cerrar">✕</button></header>',
      '<p class="bc-lead">Ventanilla de lingotes. No acuña Simoncoin.</p>',
      '<label>Metal<select id="bc-metal"><option value="oro">Oro</option><option value="plata">Plata</option><option value="cobre">Cobre</option></select></label>',
      '<label>Cantidad<input id="bc-qty" type="number" min="1" max="12" value="1"></label>',
      '<button type="button" id="bc-fundir">Fundir en la bóveda</button>',
      '<a href="#bc-reserva" id="bc-reserva-link">Reserva de oro</a>',
      '<section id="bc-reserva"><h3>Reserva de oro</h3><p id="bc-reserva-n">0 lingotes de oro</p></section>',
      '<section id="bc-series"><h3>Series</h3><ol id="bc-series-list"></ol></section>',
      '<section id="bc-historia"><h3>Historial</h3><ol id="bc-historia-list"></ol></section>',
      '<p id="bc-estado" role="status"></p>',
      '</section>',
    ].join('');
  }

  function allowed() {
    const state = window.LiveInk && LiveInk.state;
    return !!(state && state.canMintIngots);
  }

  function esc(text) {
    return String(text == null ? '' : text).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  function stamp(world) {
    for (const [x, y] of SOLIDS) {
      if (y >= 0 && y < world.height && x >= 0 && x < world.width) world.collision[y][x] = 1;
    }
    if (world.collision[OUTSIDE.y] && world.collision[OUTSIDE.y][OUTSIDE.x] != null) world.collision[OUTSIDE.y][OUTSIDE.x] = 0;
    world.nodes.push({
      id: 'puerta_central', type: 'central_door', x: DOOR.x, y: DOOR.y, solid: true,
      initialState: 'active', states: ['active'], sprites: { active: 'central_door' },
    });
    world.sprites.central_door = Object.assign({}, world.sprites.rock_piedra || {});
    world.signs3d = world.signs3d || [];
    world.signs3d.push({ text: 'BANCO CENTRAL', x: DOOR.x + 2, y: DOOR.y + 1 });
    world.waypoints = world.waypoints || [];
    world.waypoints.push({ id: 'banco_central', name: 'Banco Central', x: OUTSIDE.x, y: OUTSIDE.y });
    world.centralDoor = { x: DOOR.x, y: DOOR.y, standX: OUTSIDE.x, standY: OUTSIDE.y };
  }

  function buildMap() {
    const collision = Array.from({ length: MAP_H }, () => Array(MAP_W).fill(0));
    const ground = Array.from({ length: MAP_H }, () => Array(MAP_W).fill(0));
    const floor = new Map();
    for (let y = 0; y < MAP_H; y++) {
      for (let x = 0; x < MAP_W; x++) {
        const wall = x === 0 || y === 0 || x === MAP_W - 1 || y === MAP_H - 1;
        collision[y][x] = wall ? 1 : 0;
        floor.set(x + ',' + y, wall ? 'wall' : 'floor');
      }
    }
    for (let x = 3; x <= 8; x++) {
      collision[3][x] = 1;
      floor.set(x + ',3', 'vault');
    }
    collision[9][6] = 0;
    floor.set('6,9', 'door');
    collision[6][9] = 1;
    floor.set('9,6', 'chest');
    const nodes = [
      { id: 'salida_central', type: 'central_exit', x: 6, y: 9, solid: false, initialState: 'active', states: ['active'], sprites: { active: 'central_door' } },
      { id: 'boveda', type: 'central_vault', x: 6, y: 4, solid: false, initialState: 'active', states: ['active'], sprites: { active: 'central_door' } },
      { id: 'baul_central', type: 'bank_chest', x: 9, y: 6, solid: true, label: 'BAÚL', initialState: 'active', states: ['active'], sprites: { active: 'central_door' } },
    ];
    return {
      width: MAP_W, height: MAP_H, ground, collision, floor,
      elevation: Array.from({ length: MAP_H }, () => Array(MAP_W).fill(0)),
      nodes, npcs: [], doors: [], animals: [],
      regions: [{ id: 'banco_central', name: 'Banco Central', x: 0, y: 0, w: MAP_W, h: MAP_H }],
      waypoints: [], roads3d: [], memories: [], riverLayouts: [], bridges: [], parkDetails: [],
      surfaceZones: [], signs3d: [], scenery3d: [], waterBodies: {}, decorations: [], landmarks: [], areas: [],
      spawn: { x: SPAWN.x, y: SPAWN.y },
    };
  }

  function close() {
    const box = document.getElementById('banco-central');
    if (box) box.hidden = true;
  }

  function send(obj) {
    const net = window.LiveInk && LiveInk.state && LiveInk.state.net;
    if (!net || !net.ok || !net.ws) {
      const status = document.getElementById('bc-estado');
      if (status) status.textContent = 'Hace falta el servidor.';
      return;
    }
    net.ws.send(JSON.stringify(obj));
  }

  function paint(data) {
    const reserve = (data && data.reserve) || {};
    const gold = document.getElementById('bc-reserva-n');
    if (gold) gold.textContent = (reserve.oro || 0) + ' lingotes de oro en la reserva';
    const series = document.getElementById('bc-series-list');
    if (series) {
      const rows = (data && data.serials) || [];
      series.innerHTML = rows.map((row) => '<li>' + esc(row.serial) + ' · ' + esc(row.metal) + '</li>').join('') || '<li>Todavía no hay series.</li>';
    }
    const history = document.getElementById('bc-historia-list');
    if (history) {
      const rows = (data && data.history) || [];
      history.innerHTML = rows.map((row) => '<li>' + esc((row.serials || []).join(', ')) + ' · ' + esc(row.qty) + ' ' + esc(row.metal) + '</li>').join('') || '<li>Sin movimientos.</li>';
    }
  }

  function open() {
    if (!allowed()) return;
    const old = document.getElementById('banco-central');
    if (old) old.remove();
    const holder = document.createElement('div');
    holder.innerHTML = markup(allowed());
    const box = holder.firstElementChild;
    document.body.append(box);
    const closer = box.querySelector('#bc-cerrar');
    if (closer) closer.onclick = close;
    if (!allowed()) return;
    const fundir = box.querySelector('#bc-fundir');
    if (fundir) fundir.onclick = () => {
      const metal = (document.getElementById('bc-metal') || {}).value || 'oro';
      const qty = Number((document.getElementById('bc-qty') || {}).value || 1);
      send({ t: 'lingote', metal, qty });
    };
    send({ t: 'lingote_ver' });
  }

  function onNet(message) {
    if (!message || (message.t !== 'lingote_result' && message.t !== 'lingote_estado')) return false;
    if (!document.getElementById('banco-central') && message.ok && allowed()) open();
    const status = document.getElementById('bc-estado');
    if (message.ok) paint(message);
    if (status) status.textContent = message.reason || (message.ok && message.serials ? 'Serie ' + message.serials.join(', ') : '');
    return true;
  }

  const root = typeof window === 'undefined' ? globalThis : window;
  root.Central = { DOOR, OUTSIDE, SPAWN, SOLIDS, stamp, buildMap, open, close, markup, onNet, allowed };
})();
