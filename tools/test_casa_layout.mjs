/* SPDX-License-Identifier: AGPL-3.0-or-later */
import fs from 'fs';
import vm from 'vm';

const code = fs.readFileSync(new URL('../play/casa.js', import.meta.url), 'utf8');
const sandbox = { console };
sandbox.window = sandbox;
sandbox.document = { body: { classList: { add() {}, remove() {} } } };
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const casa = sandbox.Casa;
const layout = casa.layout;
const puestos = [];
for (const item of layout.items) {
  if (!casa.canPlace(puestos, item)) {
    console.error('No cabe', item);
    process.exit(1);
  }
  puestos.push(item);
}
const tipos = new Set(layout.items.map((item) => item.type + ':' + (item.style || '')));
for (const necesario of ['bed:retazos', 'bacenilla:', 'altar:velas', 'cocina:lena', 'ventana:', 'matica:flores', 'matica:helecho', 'matica:sabila', 'matica:orquidea', 'matica:cinta', 'painting:', 'rug:']) {
  if (!tipos.has(necesario)) {
    console.error('Falta', necesario);
    process.exit(1);
  }
}
if (layout.wall !== '#e4c48a') {
  console.error('Pared', layout.wall);
  process.exit(1);
}
console.log('PLANO OK', layout.items.length);
