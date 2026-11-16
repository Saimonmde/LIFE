/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Barra de cinco botones, cambio sin acuñar y nivel a la vista. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const page = read('play/index.html');
const bar = read('play/pulgar.js');
const css = read('play/pulgar.css');
const game = read('play/game.js');
const quote = require('../play/cambio-simple.js').quote;
for (const label of ['Inventario', 'Intercambio', 'Niveles', 'Mapa', 'Menú']) {
  assert.ok(bar.includes(label), label);
}
assert.ok(css.includes('min-height: 48px'));
assert.ok(css.includes('min-width: 48px'));
assert.ok(css.includes('#hoja-cerrar'));
assert.ok(css.includes('z-index: 48'));
assert.ok(css.includes('#shell-b-descansar'));
assert.ok(css.includes('bottom: calc(280px + env(safe-area-inset-bottom))'));
assert.ok(css.includes('position: fixed !important'));
assert.ok(bar.includes('Confirmar'));
assert.ok(bar.includes('cambio-vista'));
assert.ok(!bar.includes('hud-gear-menu') || bar.includes("id === 'hud-gear-menu'") || bar.includes("'hud-gear-menu'"));
assert.ok(!read('play/pulgar.js').includes('cajon-editor'));
assert.ok(game.includes('Nivel ${lv} de'));
assert.ok(game.includes('no se abre una herramienta nueva'));
assert.ok(page.includes('pulgar.css?v=chat-mundo'));
assert.ok(page.includes('pulgar.js?v=chat-mundo'));
assert.ok(bar.includes('Cuenta'));
assert.ok(read('play/mi-cuenta.js').includes('Mi cuenta'));
assert.ok(read('play/mi-cuenta.js').includes('id = \'cajon-cuenta\''));
const shown = quote('simonplata', 'simoncoin', 250, 250, 5 * 100000000, 0);
assert.strictEqual(shown.das, 200);
assert.strictEqual(shown.recibes, 2);
assert.ok(shown.texto.startsWith('Das 200 Simonplata. Recibes 2 Simoncoin'));
const blocked = quote('simoncoin', 'simonplata', 1, 1, 1e15, 1e15);
assert.strictEqual(blocked.ok, false);
console.log('barra vertical ok');
