import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const Guacharaca = require('../play/guacharaca.js');

function at(iso) {
  return Guacharaca.singsAt(new Date(iso));
}

assert.equal(at('2026-11-15T09:29:00Z'), false, '4:29 en Bogotá calla');
assert.equal(at('2026-11-15T09:30:00Z'), true, '4:30 en Bogotá canta');
assert.equal(at('2026-11-15T10:00:00Z'), true, '5:00 en Bogotá canta');
assert.equal(at('2026-11-15T10:59:00Z'), true, '5:59 en Bogotá canta');
assert.equal(at('2026-11-15T11:00:00Z'), false, '6:00 en Bogotá calla');
assert.equal(at('2026-11-15T17:00:00Z'), false, 'mediodía calla');
assert.equal(at('2026-11-15T08:00:00Z'), false, '3:00 calla');

const zones = [
  { x: 8, y: 0, w: 4, h: 4, kind: 'casa' },
  { x: 0, y: 8, w: 3, h: 3, kind: 'corral' },
];
const bird = {
  id: 'b', x: 6, y: 1, fx: 6, fy: 1, homeX: 6, homeY: 1,
  perch: false, mode: 'walk', phase: 0, dir: 'down', walk: 0, turns: 0, goalX: 6, goalY: 1,
};
const player = { x: 4, y: 1 };
for (let i = 0; i < 50; i++) Guacharaca.stepBird(bird, player, 0.2, zones);
assert.equal(Guacharaca.insideZone(zones, bird.fx, bird.fy), '', 'no entra a la casa al huir');
assert.ok(bird.fx < 8, 'se queda antes del umbral');

const walker = {
  id: 'c', x: 2, y: 2, fx: 2, fy: 2, homeX: 2, homeY: 2,
  perch: false, mode: 'walk', phase: 0.2, dir: 'down', walk: -100, turns: 1, goalX: 1, goalY: 9,
};
for (let i = 0; i < 40; i++) Guacharaca.stepBird(walker, { x: 20, y: 20 }, 0.3, zones);
assert.equal(Guacharaca.insideZone(zones, walker.fx, walker.fy), '', 'el paseo no cruza el corral');

assert.equal(Guacharaca.hearGain(2), 1);
assert.equal(Guacharaca.hearGain(16), 0);
assert.ok(Guacharaca.hearGain(10) < 1 && Guacharaca.hearGain(10) > 0);
assert.deepEqual(Guacharaca.SONG.syllables.map(note => note.name), ['gua', 'cha', 'ra', 'ca']);
assert.equal(Guacharaca.NAME, 'Guacharaca');
assert.equal(Guacharaca.LABEL, 'Especie protegida');
for (const call of [Guacharaca.capture, Guacharaca.sell, Guacharaca.keep, Guacharaca.hunt]) {
  const answer = call();
  assert.equal(answer.ok, false);
  assert.equal(answer.protected, true);
  assert.equal(answer.name, 'Guacharaca');
}
assert.equal(Guacharaca.blockedItem('guacharaca'), true);
assert.equal(Guacharaca.blockedItem('carne'), false);
const touched = Guacharaca.touch('nadie');
assert.equal(touched.ok, false);
assert.equal(touched.label, 'Especie protegida');

const loner = {
  id: 'solo', fx: 10, fy: 10, homeX: 10, homeY: 10, perch: false,
  mode: 'walk', phase: 0, dir: 'down', walk: 0, clock: 0, turns: 1,
  goalX: 10, goalY: 10, mates: [{ x: 14, y: 10 }],
};
for (let i = 0; i < 30; i++) Guacharaca.stepBird(loner, { x: 0, y: 10 }, 0.2, []);
assert.ok(loner.fx > 7, 'no sigue al jugador');

const pecker = {
  id: 'pico', fx: 10, fy: 10, homeX: 10, homeY: 10, perch: false,
  mode: 'walk', phase: 0, clock: 5, nextAct: 0, turns: 1, mates: [], goalX: 10, goalY: 10,
};
Guacharaca.stepBird(pecker, { x: 40, y: 40 }, 0.1, []);
assert.equal(pecker.mode, 'peck');

const flyer = {
  id: 'vuelo', fx: 10, fy: 10, homeX: 10, homeY: 10, perch: false,
  mode: 'walk', phase: 0, clock: 5, nextAct: 0, turns: 2,
  mates: [{ x: 14, y: 10 }], goalX: 10, goalY: 10,
};
Guacharaca.stepBird(flyer, { x: 40, y: 40 }, 0.1, []);
assert.equal(flyer.mode, 'fly');
assert.ok(flyer.fx >= 10, 'el vuelo corto no va hacia el jugador');
console.log('guacharaca ok');
