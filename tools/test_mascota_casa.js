const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const read = (name) => fs.readFileSync(path.join(root, name), 'utf8');
const pets = read('play/estilo-jabo.js');
for (const id of ['dog:criollo', 'dog:labrador', 'dog:golden', 'dog:pastor', 'dog:bulldog', 'dog:beagle', 'cat:criollo', 'cat:siames', 'cat:persa', 'cat:atigrado', 'cat:negro', 'cat:calico']) {
  assert.ok(pets.includes("'" + id + "'"), id);
}
assert.ok(pets.includes("anim === 'greet'"));
assert.ok(!pets.includes('gltf') && !pets.includes('.glb'));
const vida = read('play/vida.js');
assert.ok(vida.includes('Ahora no'));
assert.ok(vida.includes('Su nombre'));
assert.ok(vida.includes('mascota-preview'));
const home = read('play/vida3d.js');
assert.ok(home.includes('waitAtHome'));
assert.ok(!home.includes('leader.fx'));
const guide = read('play/instructivo.js');
for (const line of ['Valle de Aburrá', '1777', 'Pica el metal', 'tu inventario', 'Tu mascota te espera', 'Descansar', 'Cerrar sesión']) {
  assert.ok(guide.includes(line), line);
}
const game = read('play/game.js');
assert.ok(!game.includes("canClaimSimon ? 'Simon'"));
assert.ok(game.includes('pareceSimon'));
assert.ok(game.includes('irACasaAstral'));
assert.ok(game.includes('1500'));
assert.ok(!game.includes("createOscillator"));
const page = read('play/index.html');
assert.ok(page.includes('Descansar / Ir a casa'));
assert.ok(page.includes('id="astral"'));
console.log('mascota y casa ok');
