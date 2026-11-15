/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const llegada = require('../play/llegada.js');

const first = llegada.plan({ intro: 'ovni', x: 94, y: 267, municipio: 'envigado', hx: 94, hy: 267, flew: false });
assert.strictEqual(first.kind, 'ovni');
assert.strictEqual(first.x, 94);
const later = llegada.plan({ intro: '', municipio: 'envigado', hx: 94, hy: 267, flew: true });
assert.strictEqual(later.kind, 'heli');
const fresh = llegada.plan({ flew: false });
assert.strictEqual(fresh.kind, 'fly');
const seen = llegada.plan({ flew: true });
assert.strictEqual(seen.kind, 'none');
const test = llegada.plan({ autotest: true, intro: 'ovni', x: 1, y: 2 });
assert.strictEqual(test.kind, 'none');
console.log('llegada: ok');
