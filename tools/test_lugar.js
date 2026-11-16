const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Lugares = require('../play/lugares.js');

const root = path.join(__dirname, '..');
const homes = JSON.parse(fs.readFileSync(path.join(root, 'data', 'hogares.json'), 'utf8'));
const world = JSON.parse(fs.readFileSync(path.join(root, 'data', 'el-jardin.json'), 'utf8'));
const park = Lugares.get('envigado', homes, world);
assert.equal(park.name, 'Parque de Envigado');
assert.equal(park.x, 94);
assert.equal(park.y, 267);
assert.equal(Lugares.get('las_palmas', homes, world).name, 'Las Palmas');
assert.equal(Lugares.get('parque_bolivar', homes, world).name, 'Parque de Bolívar');
assert.equal(Lugares.get('paris', homes, world), null);

const page = fs.readFileSync(path.join(root, 'play', 'index.html'), 'utf8');
const hogar = fs.readFileSync(path.join(root, 'play', 'hogar.js'), 'utf8');
const game = fs.readFileSync(path.join(root, 'play', 'game.js'), 'utf8');
assert.ok(page.includes('¿Dónde quieres empezar?'));
assert.ok(page.includes('lugares.js?v=lugar-r1'));
assert.ok(!page.includes('id="cajon-lugar"'));
assert.ok(hogar.includes("button.id = 'cajon-lugar'"));
assert.ok(hogar.includes('menu.append(button)'));
assert.ok(!hogar.includes('cajon-editor'));
assert.ok(game.includes('favoritePlace'));
assert.ok(!game.includes('Hogar.openPicker(elegirCasa)'));
console.log('lugar ok');
