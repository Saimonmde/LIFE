/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Tres arreglos chicos: cielo del vuelo, paneles de la casa y un solo saldo SMC. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const page = read('play/index.html');
const css = read('play/style.css');
const theme = read('play/theme.css');
const view = read('play/unified3d.js');
const valley = read('play/valle-vista.js');

assert.ok(page.includes('id="intro-cielo"'));
assert.ok(theme.includes('#intro-cielo'));
assert.ok(theme.includes('linear-gradient(#6ea4cc'));
assert.ok(theme.includes('#intro-cielo.noche'));
assert.ok(view.includes("getElementById('intro-cielo')"));
assert.ok(view.includes('setClearAlpha(0)'));
assert.ok(view.includes('alpha:true'));
assert.ok(valley.includes('narrow()'));
assert.ok(valley.includes('Math.max(4, Math.min(width - w - 4, left))'));

assert.ok(css.includes('#smc-pill, body.pantalla-limpia #smc-pill'));
assert.ok(css.includes('display: none !important'));
assert.ok(theme.includes('html.movil #smc-pill'));
assert.ok(theme.includes('body.pantalla-limpia #hud-recursos > #sai-chip') || read('play/style.css').includes('body.pantalla-limpia #hud-recursos > #sai-chip'));

assert.ok(theme.includes('body.in-game.in-casa #b-cerrar-casa'));
assert.ok(theme.includes('body.in-casa #b-salir-parque'));
assert.ok(theme.includes('body.in-casa #b-editar-casa'));
assert.ok(theme.includes('+ 336px'));
assert.ok(theme.includes('+ 388px'));
assert.ok(theme.includes('+ 440px'));
assert.ok(css.includes('body.in-casa #world-tools{top:120px'));

console.log('cielo, casa y saldo: ok');
