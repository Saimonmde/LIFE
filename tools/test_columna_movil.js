/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* La columna derecha del celular no superpone Picar, las rutas, Inventario ni Acuñar. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const js = read('play/pulgar.js');
const css = read('play/pulgar.css');
for (const id of ['b-acunar-pulgar', 'b-picar', 'b-inventario-movil', 'mine-route', 'viaje-mundo-abrir', 'ladera-ir']) {
  assert.ok(js.includes("'" + id + "'"), id);
  assert.ok(css.includes('#' + id + '.columna-pulgar'), id);
}
assert.ok(css.includes('max-width: 156px !important'));
assert.ok(css.includes('bottom: var(--columna-desde, 72px) !important'));
assert.ok(read('play/cajon.js').includes('Pulgar.apilar'));
assert.ok(read('play/finca.js').includes('acunarEnColumna'));

const sandbox = {
  console,
  setInterval() { return 0; },
  addEventListener() {},
  matchMedia() { return { matches: false }; },
  document: {
    readyState: 'complete',
    documentElement: { classList: { contains: () => false } },
    getElementById(id) { return id === 'pulgar' ? { id: 'pulgar' } : null; },
    body: { append() {}, classList: { contains: () => false } },
  },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(js, sandbox);
const Pulgar = sandbox.Pulgar;

function sinCruce(alturas, vista) {
  const puestos = Pulgar.puestosDe(alturas);
  const rects = Pulgar.rectsDe(puestos, 156, vista, 8);
  const vivos = rects.filter(Boolean);
  for (let i = 0; i < vivos.length; i++) {
    assert.ok(vivos[i].top >= 0, 'cabe arriba ' + JSON.stringify(vivos[i]));
    assert.ok(vivos[i].bottom <= vista.h, 'cabe abajo');
    assert.ok(vivos[i].left >= 148, 'no tapa el joystick ' + vivos[i].left);
    for (let j = i + 1; j < vivos.length; j++) {
      assert.strictEqual(Pulgar.sePisan(vivos[i], vivos[j]), false, JSON.stringify([vivos[i], vivos[j]]));
    }
  }
  let anterior = null;
  puestos.forEach((p) => {
    if (!p) return;
    if (anterior) assert.strictEqual(p.desde, anterior.hasta + Pulgar.HUECO);
    anterior = p;
  });
}

const enMina = [56, 56, 56, 56, 0, 48, 80, 56, 56];
const afuera = [0, 56, 56, 56, 56, 48, 80, 0, 0];
sinCruce(enMina, { w: 390, h: 844 });
sinCruce(enMina, { w: 360, h: 740 });
sinCruce(afuera, { w: 390, h: 844 });
sinCruce(afuera, { w: 360, h: 740 });
const hueco = Pulgar.puestosDe([56, 0, 56]);
assert.strictEqual(hueco[1], null);
assert.strictEqual(hueco[2].desde, hueco[0].hasta + 8);
console.log('columna móvil ok');
