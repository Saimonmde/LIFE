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
assert.ok(page.includes('unified3d.js?v=en-vivo'));
assert.ok(world.includes('phoneGfx()?1.5:2'));
assert.ok(world.includes('shadowMap.enabled=!phoneGfx()'));
assert.ok(!world.includes('Math.round(camera.position'));
assert.ok(world.includes('box.w>box.h'));
assert.ok(world.includes('stickMag<0.02'));
assert.ok(world.includes('stickMag>0.02'));
assert.ok(world.includes('Math.min(box.w,box.h)<=520'));
assert.ok(read('play/pulgar.css').includes('orientation: landscape'));
assert.ok(read('play/pulgar.css').includes('safe-area-inset-left'));
assert.ok(page.includes('id="b-acunar-pulgar"') || read('play/cajon.js').includes('b-acunar-pulgar'));
console.log('joystick vertical ok');
