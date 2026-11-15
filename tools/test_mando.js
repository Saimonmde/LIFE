/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Barra móvil: un solo Montar, títulos que se leen y cielo de alba. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const page = read('play/index.html');
const theme = read('play/theme.css');
const mando = read('play/mando.css');
const movil = read('play/movil.js');

assert.equal(page.split('id="b-montar"').length - 1, 1);
assert.ok(page.includes('mando.css?v=joystick-v1'));
assert.ok(theme.includes('radial-gradient(1.4px 1.4px at 8% 12%'));
assert.ok(theme.includes('#e39a62 92%'));
assert.ok(theme.includes('linear-gradient(#6ea4cc'));
assert.ok(mando.includes('white-space: normal'));
assert.ok(mando.includes('text-overflow: unset'));
assert.ok(mando.includes('body.in-casa #pow-panel'));
assert.ok(mando.includes('left: 256px'));
assert.ok(mando.includes('left: 518px'));
assert.ok(mando.includes('#mando'));
assert.ok(movil.includes("id !== principal") || movil.includes('b !== principal'));
assert.ok(movil.includes("'b-montar'"));
assert.ok(movil.includes("'b-descansar'"));
assert.ok(movil.includes("'bank-dock'"));
assert.ok(movil.includes("'finca-open'"));
assert.ok(movil.includes("'b-emote'"));
assert.ok(movil.includes("'libro-open'"));
assert.ok(movil.includes("'chat-toggle'"));
assert.ok(movil.includes('max-width: 820px'));
assert.ok(mando.includes('@media (max-width: 820px)'));
console.log('mando ok');
