import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const Corral = require('../play/corral.js');

const refused = Corral.catchWorld({ id: 'gua-1', species: 'guacharaca' });
assert.equal(refused.ok, false);
assert.equal(refused.meat, 0);
assert.equal(Corral.animals().length, 0);

const caught = Corral.catchWorld({ id: 'gallo-finca-3', species: 'gallo', x: 2 });
assert.equal(caught.ok, true);
assert.equal(caught.meat, 0);
assert.equal(caught.animal.species, 'gallo');
const killed = Corral.kill();
assert.equal(killed.ok, false);
assert.equal(killed.meat, 0);
assert.equal(Corral.animals().length, 1);
assert.equal(Corral.sellable('gallo'), true);
assert.equal(Corral.catchable('guacharaca'), false);

const box = Corral.bounds({ x: 10, y: 10 }, 'patio');
const animal = { id: 'g1', fx: box.x + 0.5, fy: box.y + 0.5, goalX: box.x + 30, goalY: box.y - 10, turns: 0 };
for (let i = 0; i < 30; i++) Corral.step(animal, box, 0.4);
assert.ok(animal.fx >= box.x && animal.fx < box.x + box.w);
assert.ok(animal.fy >= box.y && animal.fy < box.y + box.h);
console.log('corral ok');
