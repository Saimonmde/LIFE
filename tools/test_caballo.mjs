/* SPDX-License-Identifier: AGPL-3.0-or-later */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import * as T from '../play/three.module.js';
import { createHorse } from '../play/caballo3d.js';

const require = createRequire(import.meta.url);
const Caballo = require('../play/caballo.js');

const root = new URL('..', import.meta.url);
const world = JSON.parse(readFileSync(new URL('../data/el-jardin.json', import.meta.url), 'utf8'));
const homes = JSON.parse(readFileSync(new URL('../data/hogares.json', import.meta.url), 'utf8'));

function open(x, y) {
  if (x < 0 || y < 0 || x >= world.width || y >= world.height) return false;
  if (world.collision[y][x] !== 0) return false;
  const kind = world.tiles[String(world.ground[y][x])].kind;
  return kind !== 'water' && kind !== 'creek';
}

assert.equal(Caballo.MOUNT_SPEED, 2.2);
assert.deepEqual(Caballo.COATS, ['bay', 'grey', 'black']);
assert.equal(Caballo.normalizeCoat('bayo'), 'bay');
assert.equal(Caballo.normalizeCoat('gris'), 'grey');
assert.equal(Caballo.normalizeCoat('negro'), 'black');
assert.equal(Caballo.normalizeCoat('pinto'), '');

const gallop = Caballo.strikes('gallop');
assert.equal(new Set(gallop).size, 4, 'el galope tiene cuatro tiempos distintos');
assert.deepEqual([...gallop].sort((a, b) => a - b), gallop);
let suspension = false;
for (let i = 0; i <= 100; i++) if (Caballo.airborneAt('gallop', i / 100)) suspension = true;
assert.equal(suspension, true, 'el galope deja las cuatro patas en el aire');
for (let i = 0; i <= 100; i++) assert.equal(Caballo.airborneAt('walk', i / 100), false);
assert.equal(Caballo.GAITS.trot.strike.lh, Caballo.GAITS.trot.strike.rf);
assert.equal(Caballo.GAITS.trot.strike.rh, Caballo.GAITS.trot.strike.lf);

const counts = new Set(homes.casas.map(house => Caballo.houseCount(house.id)));
assert.equal(counts.has(1) && counts.has(2), true, 'hay casas con un caballo y casas con dos');
const avoid = new Set(['93,267', '94,267']);
const plan = Caballo.tetherSpots(homes.casas, open, avoid);
assert.equal(plan.length, homes.casas.length);
const seen = new Set();
for (const house of plan) {
  assert.ok(house.spots.length >= 1 && house.spots.length <= 2, house.id);
  assert.equal(house.spots.length, Caballo.houseCount(house.id), house.id);
  for (const spot of house.spots) {
    const key = spot.x + ',' + spot.y;
    assert.equal(seen.has(key), false, key);
    seen.add(key);
    assert.equal(open(spot.x, spot.y), true, key);
    assert.notEqual(key, house.x + ',' + house.y, house.id);
    assert.equal(avoid.has(key), false, key);
  }
}

const S = {
  player: { x: 10, y: 10, fx: 10, fy: 10, dir: 'down', path: [[10, 11]] },
  quest: { def: { id: 'pasos' }, turnedIn: false },
  libro: { started: false, turnedIn: false },
  mounts: [],
  me: { municipio: 'envigado' },
};
const grid = (x, y) => x >= 0 && y >= 0 && x < 30 && y < 30 && !(x === 4 && y === 4);
Caballo.tick(0.4, {
  S, seconds: 1, houses: [{ id: 'envigado', name: 'Envigado', x: 12, y: 14 }],
  open: grid, route: null,
});
const horse = S.mounts.find(item => item.personal);
assert.ok(horse, 'el caballo del jugador existe');
assert.equal(horse.coat, 'bay');
assert.notEqual(horse.x + ',' + horse.y, '10,10');
assert.notEqual(horse.x + ',' + horse.y, '10,11');
horse.x = horse.fx = 10;
horse.y = horse.fy = 10;
Caballo.tick(0.2, { S, seconds: 2, houses: [{ id: 'envigado', name: 'Envigado', x: 12, y: 14 }], open: grid, route: null });
assert.notEqual(horse.x + ',' + horse.y, '10,10');
assert.notEqual(horse.x + ',' + horse.y, '10,11');
assert.equal(S.paddock.length >= 1 && S.paddock.length <= 2, true);

const bay = createHorse(T, { coat: 'bay' });
const grey = createHorse(T, { coat: 'grey' });
const black = createHorse(T, { coat: 'black' });
assert.ok(bay.detail < 3000, 'detalle ' + bay.detail);
assert.ok(bay.far < bay.detail, 'lejos ' + bay.far);
assert.equal(grey.detail, bay.detail);
black.setCoat('bay');
assert.equal(black.coat, 'bay');
bay.update({ gait: 'gallop', phase: 0.2, time: 1, tethered: false });
bay.update({ gait: 'idle', phase: 0.2, time: 2, tethered: true });
assert.equal(bay.root.children.length > 0, true);

console.log('caballo ok', bay.detail, 'cerca', bay.far, 'lejos');
