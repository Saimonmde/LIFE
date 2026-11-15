/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.join(__dirname, '..');
const acunarSrc = fs.readFileSync(path.join(root, 'play/acunar.js'), 'utf8');
const game = fs.readFileSync(path.join(root, 'play/game.js'), 'utf8');
const html = fs.readFileSync(path.join(root, 'play/index.html'), 'utf8');

const sandbox = { console, document: { querySelector() { return null; }, addEventListener() {} } };
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(acunarSrc, sandbox);
sandbox.window.__ELJARDIN = { inv: [{ item: 'mineral_cobre', qty: 2 }] };
assert.strictEqual(sandbox.Acunar.elegirMoneda(), 'simonchis');
assert.strictEqual(sandbox.Acunar.textoFalta(2, 3, 'cobre'), 'Tienes 2 de cobre, te falta 1');
sandbox.window.__ELJARDIN = { inv: [{ item: 'pepita_oro', qty: 5 }] };
assert.strictEqual(sandbox.Acunar.elegirMoneda(), 'simoncoin');
sandbox.window.__ELJARDIN = { inv: [] };
assert.strictEqual(sandbox.Acunar.elegirMoneda(), 'simoncoin');

const fn = game.match(/function apodoQueQueda\(text\) \{[\s\S]*?\n\}/);
assert.ok(fn, 'falta apodoQueQueda');
vm.runInContext(fn[0] + '\nthis.queda = apodoQueQueda;', sandbox);
assert.strictEqual(sandbox.queda('raimundo_prueba'), 'raimundoprueba');
assert.strictEqual(sandbox.queda('Ana María'), 'Ana María');
assert.ok(html.includes('id="p-apodo-vista"'));
assert.ok(html.includes('id="l-apodo-vista"'));
assert.ok(game.includes('Así quedará'));
console.log('acunar y apodo ok');
