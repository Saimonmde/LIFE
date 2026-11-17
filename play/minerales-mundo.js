/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Vetas nuevas por mundo y arena de oro en el Río Medellín.
   El oro sigue siendo pepita de río. Estas rocas no acuñan otra moneda. */
(function (root) {
  'use strict';
  const data = root.MINERALES_DATA;
  if (!data) return;

  function goldNode(spec) {
    return {
      id: spec.id, type: 'nodo_oro_fluvial', waterBody: spec.water, x: spec.x, y: spec.y,
      skill: 'mining', method: 'fluvial', tool: 'batea', solid: true,
      states: ['active', 'depleted'], initialState: 'active',
      sprites: { active: 'spot_oro', depleted: 'spot_oro_lavado' },
      successChance: 0.75, yield: { item: 'pepita_oro', min: 1, max: 1 }, xp: 25, respawnMs: 30000,
    };
  }
  function rockNode(world, spec) {
    return {
      id: spec.id, type: 'mineral_rock', mineral: spec.item, nombre: spec.name, mundo: world,
      x: spec.x, y: spec.y, skill: 'mining', method: 'terrestre', tool: 'pico', solid: true,
      states: ['active', 'depleted'], initialState: 'active',
      sprites: { active: 'rock_piedra', depleted: 'rock_depleted' },
      yield: { item: spec.item, min: 1, max: 1 }, xp: 12, respawnMs: 18000,
    };
  }
  function stand(world, x, y) {
    const steps = [[0, 1], [1, 0], [-1, 0], [0, -1], [1, 1], [-1, 1], [1, -1], [-1, -1]];
    for (const [dx, dy] of steps) {
      const nx = x + dx;
      const ny = y + dy;
      if (ny > 1 && nx > 1 && world.collision[ny] && world.collision[ny][nx] === 0) return { x: nx, y: ny };
    }
    return { x: x, y: y + 1 };
  }
  function install(world) {
    if (!world || world._mineralesMundo) return;
    const have = new Set((world.nodes || []).map((node) => node.id));
    data.gold.forEach((spec) => {
      if (have.has(spec.id)) return;
      world.nodes.push(goldNode(spec));
    });
    data.worlds.forEach((row) => {
      row.rocks.forEach((spec) => {
        if (have.has(spec.id)) return;
        const node = rockNode(row.id, spec);
        const feet = stand(world, node.x, node.y);
        node.stand = feet;
        if (world.collision[node.y]) world.collision[node.y][node.x] = 1;
        world.nodes.push(node);
        const icon = {
          16: 'graphics/mining/' + spec.item + '.svg',
          32: 'graphics/mining/' + spec.item + '.svg',
          64: 'graphics/mining/' + spec.item + '.svg',
        };
        world.items[spec.item] = {
          id: spec.item, name: spec.name, category: 'mineral', stackable: true, maxStack: 999, icon: icon,
        };
      });
    });
    world._mineralesMundo = true;
  }
  function worlds() {
    return data.worlds.map((row) => ({
      id: row.id,
      names: row.rocks.map((rock) => rock.name),
      rocks: row.rocks.map((rock) => ({ id: rock.id, x: rock.x, y: rock.y, name: rock.name, item: rock.item })),
    }));
  }
  function worldOf(id) {
    return worlds().find((row) => row.id === Number(id)) || null;
  }
  root.MineralesMundo = { install: install, worlds: worlds, worldOf: worldOf, data: data };
})(typeof window !== 'undefined' ? window : globalThis);
