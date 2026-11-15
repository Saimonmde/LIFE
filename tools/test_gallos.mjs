import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const Gallos = require('../play/gallo.js');

assert.equal(Gallos.crowsReal(new Date('2026-11-15T09:59:00Z')), false, '4:59 calla');
assert.equal(Gallos.crowsReal(new Date('2026-11-15T10:00:00Z')), true, '5:00 canta');
assert.equal(Gallos.crowsReal(new Date('2026-11-15T10:59:00Z')), true, '5:59 canta');
assert.equal(Gallos.crowsReal(new Date('2026-11-15T11:00:00Z')), false, '6:00 calla');
assert.equal(Gallos.gameDay(1_700_000_000, 1_700_000_000), 1);
assert.equal(Gallos.gameDay(1_700_000_000 + 20 * 60, 1_700_000_000), 2);
assert.equal(Gallos.notice(2), 'Amaneció: día 2');
assert.equal(Gallos.sellable('gallo'), true);
assert.equal(Gallos.sellable('guacharaca'), false);
assert.equal(Gallos.SONG.strong.map(note => note.name).join('-'), 'qui-qui-riqui');

const bird = {
  fx: 10, fy: 10, homeX: 10, homeY: 10, mode: 'idle', phase: 0, clock: 0, turns: 1, goalX: 10, goalY: 10,
};
for (let i = 0; i < 40; i++) Gallos.stepBird(bird, 0.3);
assert.ok(Math.hypot(bird.fx - 10, bird.fy - 10) <= 1.7, 'se queda en el patio');
assert.ok(bird.mode === 'peck' || bird.mode === 'walk' || bird.mode === 'idle');
console.log('gallos ok');
