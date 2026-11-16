/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Un toque en el mapa marca el camino, y ese camino llega a la mina. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const game = read('play/game.js');
const map = read('play/valle-mapa.js');
const world = JSON.parse(read('data/el-jardin.json'));

assert.ok(game.includes('function setRoute'));
const places = game.slice(game.indexOf('function fillMapPlaces'), game.indexOf('function openCityMap'));
assert.ok(places.includes('setRoute(src.x, src.y, park.name)'));
assert.ok(places.includes('setRoute(x, y, park.name)'));
assert.ok(!places.includes("t: 'travel'"));
assert.ok(game.includes('S.dest.ruta && steer'));
assert.ok(game.includes('Llegaste a '));
assert.ok(game.includes('Mina · '));
assert.ok(game.includes('walkFromMinimap'));
assert.ok(game.includes('route: routeSamples()'));
assert.ok(game.includes("text:'MINA'"));
assert.ok(map.includes('opts.route'));
assert.ok(map.includes('setLineDash'));
assert.ok(read('play/unified3d.js').includes('syncRouteDots'));
assert.ok(read('play/unified3d.js').includes("minePortalSign('MINA'"));
assert.ok(!read('play/cajon.css').includes('body.mapa-limpio #mine-route'));

const palmas = world.waypoints.find((item) => item.id === 'las_palmas');
let entry = null;
for (let r = 2; r < 10 && !entry; r++) {
  for (let dx = -r; dx <= r && !entry; dx++) {
    for (let dy = -r; dy <= r && !entry; dy++) {
      const x = palmas.x + dx;
      const y = palmas.y + dy;
      if (x > 1 && y > 1 && x < world.width - 1 && y < world.height - 1 && world.collision[y][x] === 0 && world.collision[y + 1][x] === 0) entry = { x, y };
    }
  }
}
assert.ok(entry, 'hay entrada');
const walkable = (x, y) => x >= 0 && y >= 0 && x < world.width && y < world.height && world.collision[y][x] === 0;
function bfs(sx, sy, goal) {
  const key = (x, y) => y * world.width + x;
  const prev = new Map([[key(sx, sy), null]]);
  const q = [[sx, sy]];
  const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  for (let i = 0; i < q.length; i++) {
    const [x, y] = q[i];
    if (goal(x, y)) {
      const path = [];
      let k = key(x, y);
      while (k !== key(sx, sy)) {
        path.unshift([k % world.width, Math.floor(k / world.width)]);
        k = prev.get(k);
      }
      return path;
    }
    for (const [dx, dy] of dirs) {
      const nx = x + dx;
      const ny = y + dy;
      if (!walkable(nx, ny) || prev.has(key(nx, ny))) continue;
      prev.set(key(nx, ny), key(x, y));
      q.push([nx, ny]);
    }
  }
  return null;
}
const spawn = world.spawn;
const pathToMine = bfs(spawn.x, spawn.y, (x, y) => Math.max(Math.abs(x - entry.x), Math.abs(y - entry.y)) <= 1);
assert.ok(pathToMine && pathToMine.length > 1, 'el camino llega a la mina');
const home = { x: 94, y: 268 };
if (walkable(home.x, home.y)) {
  const fromHome = bfs(home.x, home.y, (x, y) => Math.max(Math.abs(x - entry.x), Math.abs(y - entry.y)) <= 1);
  assert.ok(fromHome && fromHome.length > 1, 'desde Envigado también hay camino');
}
console.log('ruta mina ok', pathToMine.length);
