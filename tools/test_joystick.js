/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* El joystick queda por encima de la barra y el lienzo sigue el alto vertical. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const movil = read('play/movil.js');
const css = read('play/mando.css');
const skin = read('play/movil.css');
const world = read('play/unified3d.js');
const page = read('play/index.html');

assert.ok(movil.includes('#city-joystick'));
assert.ok(css.includes('joy-flotante') || world.includes('joy-flotante'));
assert.ok(world.includes('inMoveZone'));
assert.ok(world.includes('stickPower'));
assert.ok(read('play/game.js').includes("S.keys.has('joystick')"));
assert.ok(css.includes('height: 100dvh'));
assert.ok(skin.includes('height: 100dvh'));
assert.ok(world.includes('visualViewport'));
assert.ok(world.includes('orientationchange'));
assert.ok(world.includes('status.editorApi'));
assert.ok(!world.includes('onlostpointercapture'));
assert.ok(page.includes('unified3d.js?v=joystick-v1'));
assert.ok(page.includes('id="b-acunar-pulgar"') || read('play/cajon.js').includes('b-acunar-pulgar'));
console.log('joystick vertical ok');
