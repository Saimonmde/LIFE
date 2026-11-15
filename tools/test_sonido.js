/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const sonido = require('../play/sonido.js');

assert.strictEqual(sonido.metalOf({ ok: true, coin: 'simoncoin' }), 'oro');
assert.strictEqual(sonido.metalOf({ ok: true, coin: 'simonplata' }), 'plata');
assert.strictEqual(sonido.metalOf({ ok: true, mode: 'simonchis' }), 'cobre');
assert.strictEqual(sonido.metalOf({ ok: true, coin: 'SMP' }), 'plata');
assert.strictEqual(sonido.metalOf({ ok: false, coin: 'simoncoin' }), '');
assert.strictEqual(sonido.metalOf({ ok: true, mode: 'ingot' }), '');
assert.strictEqual(sonido.isRaw('pepita_oro'), true);
assert.strictEqual(sonido.isRaw('mineral_plata'), true);
assert.strictEqual(sonido.isRaw('madera'), false);
assert.ok(sonido.PITCH.oro < sonido.PITCH.plata);
assert.ok(sonido.PITCH.cobre < sonido.PITCH.oro);
const shell = fs.readFileSync(path.join(__dirname, '../play/shell.js'), 'utf8');
assert.ok(!/createOscillator/.test(shell), 'la portada no deja un tono continuo');
assert.ok(!/277\.18/.test(shell));
console.log('sonido: ok');
