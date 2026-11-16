/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* La entrada solo tiene nickname, contraseña, entrar y Google. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const page = read('play/index.html');
const game = read('play/game.js');
const skin = read('play/login-entrada.css');
const cuentas = page.split('id="login-cuentas"')[1].split('id="correo-login"')[0];
assert.ok(cuentas.includes('>Nickname<'));
assert.ok(cuentas.includes('>Contraseña<'));
assert.ok(cuentas.includes('Entrar al mundo'));
assert.ok(cuentas.includes('Continuar con Google'));
assert.ok(!cuentas.includes('Crear cuenta'));
assert.ok(!cuentas.includes('Confirmar'));
assert.ok(skin.includes('#login #b-facebook'));
assert.ok(page.includes('Conectando al mundo…'));
assert.ok(page.includes('id="login-bienvenida"'));
assert.ok(game.includes("red.textContent = 'Conectando al mundo…'"));
assert.ok(game.includes("red.textContent = 'En línea'"));
assert.ok(game.includes("'Bienvenido de vuelta, '"));
assert.ok(!game.includes('Hogar.openPicker(elegirCasa)'));
assert.ok(skin.includes('#2ea84a'));
assert.ok(page.includes('login-entrada.css?v=login-limpio'));
assert.ok(read('play/vida.js').includes('const DEFAULT_WORLD = 3'));
console.log('login limpio ok');
