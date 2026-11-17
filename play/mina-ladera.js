/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Mina de La Ladera. La boca queda junto al cafetal de Las Palmas.
   El pago lo confirma el servidor: cobre 0,001, plata 0,01, oro 0,1 SMC. */
(function (root) {
  'use strict';
  const NAME = 'Mina de La Ladera';
  const ZONE = 'mina2';
  const WIDTH = 48;
  const HEIGHT = 40;
  const SPAWN = { x: 24, y: 35 };
  const RATES = { cobre: 0.001, plata: 0.01, oro: 0.1 };
  const RECURSO = 'cobre 0,001 · plata 0,01 · oro 0,1 SMC';

  function grid(xs, ys) {
    const out = [];
    ys.forEach((y) => xs.forEach((x) => out.push([x, y])));
    return out;
  }
  function spots() {
    return {
      cobre: grid([6, 11, 16], [6, 12, 20, 28]).slice(0, 10),
      plata: grid([34, 40], [6, 14, 22, 30]),
      oro: grid([22, 28], [6, 14, 24, 32]).concat([[18, 10], [38, 18], [24, 28], [32, 20]]),
    };
  }
  function walk(world, x, y) {
    return x > 1 && y > 1 && x < world.width - 1 && y < world.height - 1 && world.collision[y] && world.collision[y][x] === 0;
  }
  function firstEntrance(world, palmas) {
    for (let ring = 2; ring < 10; ring++) {
      for (let dx = -ring; dx <= ring; dx++) {
        for (let dy = -ring; dy <= ring; dy++) {
          const x = palmas.x + dx;
          const y = palmas.y + dy;
          if (walk(world, x, y) && walk(world, x, y + 1)) return { x: x, y: y };
        }
      }
    }
    return null;
  }
  function fincaAnchor(world, palmas) {
    let best = null;
    for (let dy = 6; dy <= 16; dy++) {
      for (let dx = -8; dx <= 8; dx++) {
        const x = palmas.x + dx;
        const y = palmas.y + dy;
        let opened = 0;
        for (let iy = 0; iy < 8; iy++) {
          for (let ix = -6; ix <= 6; ix++) if (walk(world, x + ix, y + iy)) opened++;
        }
        if (!best || opened > best.opened) best = { opened: opened, x: x, y: y };
      }
    }
    if (best && best.opened > 40) return best;
    return { x: palmas.x, y: Math.min(world.height - 4, palmas.y + 8), opened: 0 };
  }
  function plots(anchor) {
    const blocked = new Set();
    for (let index = 0; index < 8; index++) {
      const tx = Math.round(anchor.x + (-5.2 + index * 1.35) / 2);
      const ty = Math.round(anchor.y + 5.6 / 2);
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) blocked.add((tx + dx) + ',' + (ty + dy));
    }
    [[-4.2, 3.6], [3.4, 3.6]].forEach(([lx, lz]) => {
      const tx = Math.round(anchor.x + lx / 2);
      const ty = Math.round(anchor.y + lz / 2);
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) blocked.add((tx + dx) + ',' + (ty + dy));
    });
    return blocked;
  }
  function entrance(world) {
    const palmas = (world.waypoints || []).find((item) => item.id === 'las_palmas');
    if (!palmas) return null;
    const first = firstEntrance(world, palmas);
    if (!first) return null;
    const anchor = fincaAnchor(world, palmas);
    const blocked = plots(anchor);
    let best = null;
    for (let dy = -14; dy <= 14; dy++) {
      for (let dx = -14; dx <= 14; dx++) {
        const x = anchor.x + dx;
        const y = anchor.y + dy;
        if (blocked.has(x + ',' + y) || blocked.has(x + ',' + (y + 1))) continue;
        if (!walk(world, x, y) || !walk(world, x, y + 1)) continue;
        if (Math.max(Math.abs(x - first.x), Math.abs(y - first.y)) < 8) continue;
        const dist = Math.abs(dx) + Math.abs(dy);
        if (dist < 4 || dist > 10) continue;
        const rank = [dist, Math.abs(dy), x, y];
        if (!best || rank[0] < best[0] || (rank[0] === best[0] && (rank[1] < best[1] || (rank[1] === best[1] && rank[2] < best[2])))) best = rank;
      }
    }
    if (!best) return null;
    return { x: best[2], y: best[3], name: NAME };
  }
  function cave(groundTile) {
    const width = WIDTH;
    const height = HEIGHT;
    const ground = Array.from({ length: height }, () => Array(width).fill(groundTile));
    const collision = Array.from({ length: height }, (_, y) => Array.from({ length: width }, (_, x) => (x < 2 || y < 2 || x > width - 3 || y > height - 3 ? 1 : 0)));
    const elevation = Array.from({ length: height }, () => Array(width).fill(0));
    const nodes = [
      { id: 'salida_ladera', type: 'mine_exit', x: 24, y: 37, label: 'SALIDA', initialState: 'active', states: ['active'], sprites: { active: 'mine_exit' }, solid: true },
      { id: 'letrero_ladera', type: 'mine_sign', x: 25, y: 36, solid: false, facing: Math.PI, initialState: 'active', states: ['active'], sprites: { active: 'mine_exit' } },
      { id: 'baul_mina', type: 'mine_chest', x: 21, y: 18, solid: true, states: ['active'], initialState: 'active', sprites: { active: 'mine_exit' } },
    ];
    const layout = spots();
    Object.keys(layout).forEach((metal) => {
      layout[metal].forEach(([x, y], index) => {
        nodes.push({
          id: 'ladera_' + metal + '_' + index,
          type: 'mineral_rock',
          mineral: metal,
          pay: 'smc',
          rateSmc: RATES[metal],
          x: x,
          y: y,
          skill: 'mining',
          method: 'terrestre',
          tool: 'pico',
          solid: true,
          states: ['active', 'depleted'],
          initialState: 'active',
          sprites: { active: 'rock_' + metal, depleted: 'rock_depleted' },
          yield: { item: 'mineral_' + metal, min: 1, max: 1 },
          xp: metal === 'oro' ? 26 : metal === 'plata' ? 18 : 12,
          respawnMs: metal === 'oro' ? 32000 : 18000,
        });
      });
    });
    const rocks = [[8, 16], [30, 10], [42, 16], [14, 24], [36, 26]];
    rocks.forEach(([x, y]) => { collision[y][x] = 1; });
    nodes.forEach((node) => { if (node.type !== 'mine_sign') collision[node.y][node.x] = 1; });
    return {
      width: width,
      height: height,
      ground: ground,
      collision: collision,
      elevation: elevation,
      nodes: nodes,
      npcs: [],
      doors: [],
      animals: [],
      regions: [{ id: 'mina_ladera', name: 'Mina de La Ladera · interior', x: 0, y: 0, w: width, h: height }],
      waypoints: [{ id: 'baul', name: 'Baúl', x: 21, y: 19 }, { id: 'salida', name: 'Salida a la ladera', x: 24, y: 36 }],
      roads3d: [],
      memories: [],
      riverLayouts: [],
      bridges: [],
      parkDetails: [],
      surfaceZones: [],
      signs3d: [],
      scenery3d: [],
      waterBodies: {},
      decorations: [],
      landmarks: [],
      areas: [],
      spawn: { x: SPAWN.x, y: SPAWN.y },
      rocks: rocks,
      exitLabel: 'SALIDA',
    };
  }
  const api = {
    NAME: NAME,
    ZONE: ZONE,
    WIDTH: WIDTH,
    HEIGHT: HEIGHT,
    SPAWN: SPAWN,
    RATES: RATES,
    RECURSO: RECURSO,
    spots: spots,
    entrance: entrance,
    cave: cave,
    capacity: function () {
      const layout = spots();
      return layout.cobre.length + layout.plata.length + layout.oro.length;
    },
  };
  root.MinaLadera = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
