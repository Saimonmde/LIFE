/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* El baúl de la mina abre en la mina y las cifras se leen en SMC. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const page = read('play/index.html');
const game = read('play/game.js');
const ui = read('play/baul.js');
const css = read('play/baul.css');
assert.ok(page.includes('id="baul-mina"'));
assert.ok(page.includes('data-cierra="baul-mina"'));
assert.ok(page.includes('id="baul-abrir"'));
assert.ok(page.includes('baul.js?v=baul-mina'));
assert.ok(page.includes('baul.css?v=baul-mina'));
assert.ok(game.includes("d.type === 'mine_chest'"));
assert.ok(game.includes('Baul.open()'));
assert.ok(game.includes("DESTINO_IDS=new Set(['mina'"));
assert.ok(game.includes("m.id === 'mina'"));
assert.ok(ui.includes("t: 'baul_mover'"));
assert.ok(ui.includes("t: 'baul_smc'"));
assert.ok(ui.includes('Guardar todo'));
assert.ok(ui.includes('Sacar todo'));
assert.ok(css.includes('min-height: 48px') || css.includes('min-height:48px'));
for (const banned of ['SMH', 'SMP', 'SPH', 'Simonchi', 'Simonplata']) {
  assert.ok(!ui.includes(banned), banned);
  assert.ok(!css.includes(banned), banned);
}
const chest = page.slice(page.indexOf('id="baul-mina"'), page.indexOf('id="autotest"'));
for (const banned of ['SMH', 'SMP', 'SPH']) assert.ok(!chest.includes(banned), banned);
console.log('baúl de la mina ok');
