/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Galerías de las dos minas. Las vetas viejas conservan sitio y reloj. */
(function (root) {
  'use strict';
  const DATA = root.GALERIAS_DATA = {
    "palmas": {
      "width": 64,
      "height": 48,
      "spawn": [18, 27],
      "open": [[3, 3, 32, 28], [33, 13, 60, 17], [36, 5, 60, 9], [36, 21, 60, 25], [38, 5, 40, 44], [46, 5, 48, 44], [54, 5, 56, 44], [16, 29, 20, 44], [10, 40, 28, 44]],
      "fixtures": [
        {"id": "salida_mina", "type": "mine_exit", "x": 18, "y": 29},
        {"id": "letrero_salida", "type": "mine_sign", "x": 19, "y": 28, "facing": 3.1416},
        {"id": "horno_cantera", "type": "furnace", "x": 18, "y": 15},
        {"id": "baul_mina", "type": "mine_chest", "x": 15, "y": 16},
        {"id": "letrero_galeria_palmas", "type": "mine_sign", "x": 36, "y": 15, "label": "GALERÍA ESTE"}
      ],
      "rocks": [[10, 13], [26, 15], [12, 21], [22, 23], [8, 17], [28, 26], [16, 7]],
      "timbers": [[18, 22], [36, 15], [47, 7], [47, 23], [55, 15], [18, 38]],
      "veins": {
        "cobre": [[6, 6], [9, 4], [5, 12], [8, 22], [12, 8], [39, 8], [39, 20], [39, 32], [39, 40], [47, 8], [47, 32]],
        "plata": [[27, 5], [30, 10], [28, 22], [24, 9], [47, 16], [47, 24], [47, 40], [55, 12], [55, 28], [55, 40]],
        "oro": [[5, 3], [17, 3], [28, 3], [32, 17], [3, 18], [24, 27], [55, 8], [55, 20], [55, 36], [18, 42], [24, 42], [12, 42]]
      }
    },
    "ladera": {
      "width": 72,
      "height": 56,
      "spawn": [24, 35],
      "open": [[3, 3, 44, 37], [45, 15, 68, 18], [48, 6, 68, 10], [48, 28, 68, 32], [50, 6, 52, 50], [58, 6, 60, 50], [66, 6, 68, 50], [22, 37, 26, 50], [20, 46, 68, 50]],
      "fixtures": [
        {"id": "salida_ladera", "type": "mine_exit", "x": 24, "y": 37, "label": "SALIDA"},
        {"id": "letrero_ladera", "type": "mine_sign", "x": 25, "y": 36, "facing": 3.1416},
        {"id": "baul_mina", "type": "mine_chest", "x": 21, "y": 18},
        {"id": "horno_ladera", "type": "furnace", "x": 24, "y": 16},
        {"id": "letrero_galeria_ladera", "type": "mine_sign", "x": 46, "y": 16, "label": "GALERÍA ESTE"}
      ],
      "rocks": [[8, 16], [30, 10], [42, 16], [14, 24], [36, 26]],
      "timbers": [[24, 24], [46, 17], [51, 14], [59, 20], [67, 14], [24, 44]],
      "veins": {
        "cobre": [[6, 6], [11, 6], [16, 6], [6, 12], [11, 12], [16, 12], [6, 20], [11, 20], [16, 20], [6, 28], [51, 8], [51, 20], [51, 32], [51, 44], [59, 12], [59, 36]],
        "plata": [[34, 6], [40, 6], [34, 14], [40, 14], [34, 22], [40, 22], [34, 30], [40, 30], [59, 8], [59, 24], [59, 44], [67, 16], [67, 32]],
        "oro": [[22, 6], [28, 6], [22, 14], [28, 14], [22, 24], [28, 24], [22, 32], [28, 32], [18, 10], [38, 18], [24, 28], [32, 20], [67, 8], [67, 24], [67, 44], [51, 48], [40, 48], [28, 48]]
      }
    }
  };
  /* END DATA */

  function carve(plan) {
    const width = plan.width;
    const height = plan.height;
    const collision = Array.from({ length: height }, () => Array(width).fill(1));
    plan.open.forEach((rect) => {
      const x0 = Math.max(2, Math.min(rect[0], rect[2]));
      const y0 = Math.max(2, Math.min(rect[1], rect[3]));
      const x1 = Math.min(width - 3, Math.max(rect[0], rect[2]));
      const y1 = Math.min(height - 3, Math.max(rect[1], rect[3]));
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) collision[y][x] = 0;
    });
    return collision;
  }

  function walls(collision, skip) {
    const height = collision.length;
    const width = collision[0].length;
    const runs = [];
    for (let y = 2; y < height - 2; y++) {
      let start = -1;
      for (let x = 2; x < width - 2; x++) {
        const solid = collision[y][x] === 1 && !skip.has(x + ',' + y);
        let edge = false;
        if (solid) {
          edge = [[1, 0], [-1, 0], [0, 1], [0, -1]].some((step) => {
            const nx = x + step[0];
            const ny = y + step[1];
            return collision[ny] && collision[ny][nx] === 0;
          });
        }
        if (edge && start < 0) start = x;
        if (!edge && start >= 0) {
          runs.push({ x: start, y: y, w: x - start, h: 1 });
          start = -1;
        }
      }
      if (start >= 0) runs.push({ x: start, y: y, w: width - 2 - start, h: 1 });
    }
    return runs;
  }

  function spots(kind) {
    const plan = DATA[kind];
    return {
      cobre: plan.veins.cobre.map((pair) => pair.slice()),
      plata: plan.veins.plata.map((pair) => pair.slice()),
      oro: plan.veins.oro.map((pair) => pair.slice()),
    };
  }

  function cave(kind, groundTile) {
    const plan = DATA[kind];
    const width = plan.width;
    const height = plan.height;
    const collision = carve(plan);
    const ground = Array.from({ length: height }, () => Array(width).fill(groundTile || 1));
    const elevation = Array.from({ length: height }, () => Array(width).fill(0));
    const prefix = kind === 'ladera' ? 'ladera' : 'mina';
    const nodes = plan.fixtures.map((row) => ({
      id: row.id,
      type: row.type,
      x: row.x,
      y: row.y,
      label: row.label || '',
      facing: row.facing || 0,
      solid: row.type !== 'mine_sign',
      states: ['active'],
      initialState: 'active',
      sprites: { active: row.type === 'furnace' ? 'furnace' : 'mine_exit' },
    }));
    const layout = spots(kind);
    Object.keys(layout).forEach((metal) => {
      layout[metal].forEach((pair, index) => {
        const node = {
          id: prefix + '_' + metal + '_' + index,
          type: 'mineral_rock',
          mineral: metal,
          x: pair[0],
          y: pair[1],
          skill: 'mining',
          method: 'terrestre',
          tool: 'pico',
          solid: true,
          states: ['active', 'depleted'],
          initialState: 'active',
          sprites: { active: 'rock_' + metal, depleted: 'rock_depleted' },
          yield: { item: 'mineral_' + metal, min: kind === 'ladera' ? 1 : 2, max: kind === 'ladera' ? 1 : (metal === 'oro' ? 3 : 4) },
          xp: metal === 'oro' ? 26 : metal === 'plata' ? 18 : 12,
          respawnMs: metal === 'oro' ? 32000 : 18000,
        };
        if (kind === 'ladera') {
          node.pay = 'smc';
          node.rateSmc = metal === 'oro' ? 0.1 : metal === 'plata' ? 0.01 : 0.001;
        }
        nodes.push(node);
      });
    });
    const skip = new Set();
    nodes.forEach((node) => {
      if (node.type !== 'mine_sign') {
        collision[node.y][node.x] = 1;
        skip.add(node.x + ',' + node.y);
      }
    });
    plan.rocks.forEach((pair) => {
      if (collision[pair[1]] && collision[pair[1]][pair[0]] === 0) collision[pair[1]][pair[0]] = 1;
    });
    const region = kind === 'ladera'
      ? { id: 'mina_ladera', name: 'Mina de La Ladera · interior', x: 0, y: 0, w: width, h: height }
      : { id: 'mina_palmas', name: 'Mina de Las Palmas · interior', x: 0, y: 0, w: width, h: height };
    const waypoints = kind === 'ladera'
      ? [{ id: 'baul', name: 'Baúl', x: 21, y: 19 }, { id: 'horno', name: 'Horno', x: 24, y: 17 }, { id: 'salida', name: 'Salida a la ladera', x: 24, y: 36 }]
      : [{ id: 'horno', name: 'Horno central', x: 18, y: 17 }, { id: 'salida', name: 'Salida a Las Palmas', x: 18, y: 28 }];
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
      regions: [region],
      waypoints: waypoints,
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
      spawn: { x: plan.spawn[0], y: plan.spawn[1] },
      rocks: plan.rocks,
      timbers: plan.timbers,
      walls: walls(collision, skip),
      galleries: true,
      exitLabel: kind === 'ladera' ? 'SALIDA' : '',
    };
  }

  root.Galerias = { DATA: DATA, spots: spots, cave: cave, carve: carve };
})(typeof window !== 'undefined' ? window : globalThis);
