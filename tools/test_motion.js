/* SPDX-License-Identifier: AGPL-3.0-or-later */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const Motion = createRequire(import.meta.url)('../play/motion.js');

const faster = Motion.approach(0, 4, 0.1, 8, 12);
assert(faster > 0 && faster < 4, 'acelera sin pasar el objetivo');
const slower = Motion.approach(4, 0, 0.1, 8, 12);
assert(slower < 4 && slower > 0, 'frena sin invertirse');

const spun = Motion.turn(3, -3, 0.05, 8);
assert(Math.abs(spun - 3) < 1, 'el giro toma el camino corto');

assert.equal(Motion.blend(0).idle, 1);
const walking = Motion.blend(4.2);
assert(walking.walk > 0.9 && walking.run === 0);
const running = Motion.blend(8);
assert(running.run > 0.9 && running.idle === 0);

const snap = Motion.follow(0, 0, 20, 0, 0.016);
assert.equal(snap.x, 20);
const step = Motion.follow(0, 0, 1, 0, 0.05);
assert(step.x > 0 && step.x < 1 && step.moving);

assert.equal(Motion.EMOTES.length, 8);
assert.deepEqual(Motion.EMOTES.map(e => e.id), ['wave', 'bow', 'dance', 'clap', 'laugh', 'sit', 'point', 'bacano']);
console.log('movimiento y gestos: ok');
