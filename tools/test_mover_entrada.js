/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* El caballo no puede tumbar el bucle al entrar a la casa. El login no se toca. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const game = read('play/game.js');
const page = read('play/index.html');
const login = read('play/login.css');
const skin = read('play/mover.css');
assert.ok(game.includes('const tiles=city.tiles||(window.EL_JARDIN&&EL_JARDIN.tiles)'));
assert.ok(game.includes('try { update(dt); } catch (err)'));
assert.ok(game.includes("if (window.Vida && !Vida.allowsConnect())"));
assert.ok(!login.includes('pointer-events: none'));
assert.ok(page.includes('login.css?v=login-limpio'));
assert.ok(page.includes('game.js?v=saldo-vivo'));
assert.ok(page.includes('unified3d.js?v=paso-fluido'));
assert.ok(page.includes('mover.css?v=mover-r1'));
assert.ok(skin.includes('pointer-events: none !important'));
const guest = game.slice(game.indexOf('beginAtHome();'), game.indexOf('beginAtHome();') + 80);
assert.ok(!guest.includes('startGame()'));
console.log('entrada se mueve ok');
