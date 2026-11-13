/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Casa bancaria, junto al Parque de Envigado y fuera del bloque reservado.
   El banquito y el baúl de la casa son el mismo depósito. */
(() => {
  'use strict';
  const DOOR = { x: 113, y: 256 };
  const OUTSIDE = { x: 113, y: 257 };
  const SPAWN = { x: 6, y: 7, dir: 'up' };
  const SOLIDS = [];
  for (let y = 254; y <= 256; y++) {
    for (let x = 111; x <= 115; x++) SOLIDS.push([x, y]);
  }
  const MAP_W = 12;
  const MAP_H = 10;

  function stamp(world) {
    for (const [x, y] of SOLIDS) {
      if (y >= 0 && y < world.height && x >= 0 && x < world.width) world.collision[y][x] = 1;
    }
    world.nodes.push({
      id: 'puerta_banco', type: 'bank_door', x: DOOR.x, y: DOOR.y, solid: true,
      initialState: 'active', states: ['active'], sprites: { active: 'bank_door' },
    });
    world.sprites.bank_door = Object.assign({}, world.sprites.rock_piedra || {});
    world.signs3d = world.signs3d || [];
    world.signs3d.push({ text: 'CASA BANCARIA', x: DOOR.x + 2, y: DOOR.y + 1 });
    world.bankDoor = { x: DOOR.x, y: DOOR.y, standX: OUTSIDE.x, standY: OUTSIDE.y };
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
      floor.set(x + ',3', 'counter');
    }
    collision[9][6] = 0;
    floor.set('6,9', 'door');
    const nodes = [
      { id: 'salida_banco', type: 'bank_exit', x: 6, y: 9, solid: false, initialState: 'active', states: ['active'], sprites: { active: 'bank_door' } },
      { id: 'banquito', type: 'banquito', x: 8, y: 6, solid: false, initialState: 'active', states: ['active'], sprites: { active: 'bank_door' } },
      { id: 'banquero', type: 'banker', x: 6, y: 4, solid: false, initialState: 'active', states: ['active'], sprites: { active: 'bank_door' } },
    ];
    return {
      width: MAP_W, height: MAP_H, ground, collision, floor,
      elevation: Array.from({ length: MAP_H }, () => Array(MAP_W).fill(0)),
      nodes, npcs: [], doors: [], animals: [],
      regions: [{ id: 'casa_bancaria', name: 'Casa bancaria', x: 0, y: 0, w: MAP_W, h: MAP_H }],
      waypoints: [], roads3d: [], memories: [], riverLayouts: [], bridges: [], parkDetails: [],
      surfaceZones: [], signs3d: [], scenery3d: [], waterBodies: {}, decorations: [], landmarks: [], areas: [],
      spawn: { x: SPAWN.x, y: SPAWN.y },
    };
  }

  function openPanel() {
    const panel = document.getElementById('banquito');
    if (!panel) return;
    panel.hidden = false;
    if (window.Simulacion && Simulacion.requestVault) Simulacion.requestVault();
    else paint();
  }

  function paint(account) {
    const saldo = document.getElementById('banquito-saldo');
    const items = document.getElementById('banquito-items');
    if (!saldo) return;
    const box = account || (window.Simulacion && Simulacion.localVault && Simulacion.localVault()) || { smcSubs: 0, items: {} };
    const smh = box.smh != null ? box.smh : (box.smcSubs || 0);
    const texto = window.Simulacion && Simulacion.formatPair ? Simulacion.formatPair(smh) : `${smh} SMH`;
    saldo.innerHTML = 'En el depósito: <span class="smc">' + texto.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])) + '</span>';
    const rows = Object.entries(box.items || {});
    const carried = (window.LiveInk && LiveInk.state && LiveInk.state.inv || []).filter(Boolean);
    const deposit = carried.map(slot => `<button type="button" data-dep="${slot.item}" data-qty="1">Depositar 1 ${slot.item}</button>`).join(' ');
    const withdraw = rows.map(([id, qty]) => `<button type="button" data-ret="${id}" data-qty="1">Retirar 1 ${id} (${qty})</button>`).join(' ');
    items.innerHTML = (rows.length ? '' : '<p>No hay objetos en el depósito.</p>') + deposit + withdraw;
    items.querySelectorAll('[data-dep]').forEach(b => b.onclick = () => Simulacion.bankItem('in', b.dataset.dep, 1));
    items.querySelectorAll('[data-ret]').forEach(b => b.onclick = () => Simulacion.bankItem('out', b.dataset.ret, 1));
  }
  document.getElementById('banquito-depositar')?.addEventListener('click', () => {
    const amount = document.getElementById('banquito-monto').value;
    if (window.Simulacion) Simulacion.bankSmc('in', amount);
  });
  document.getElementById('banquito-retirar')?.addEventListener('click', () => {
    const amount = document.getElementById('banquito-monto').value;
    if (window.Simulacion) Simulacion.bankSmc('out', amount);
  });

  window.Banco = {
    DOOR, OUTSIDE, SPAWN, SOLIDS, stamp, buildMap, openPanel, paint,
  };
})();
