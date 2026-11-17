/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* En el celular el inventario, Botar y Acuñar se alcanzan con el pulgar. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const pulgar = read('play/pulgar.js');
const css = read('play/pulgar.css');
const cajon = read('play/cajon.js');
const cajonCss = read('play/cajon.css');
const game = read('play/game.js');
assert.ok(pulgar.includes("inv.id = 'b-inventario-movil'"));
assert.ok(pulgar.includes("inv.textContent = 'Inventario'"));
assert.ok(pulgar.includes("getElementById('w-inv')"));
assert.ok(css.includes('#b-inventario-movil'));
assert.ok(css.includes('min-height: 56px'));
assert.ok(css.includes('z-index: 50'));
assert.ok(cajon.includes('function juntoHorno'));
assert.ok(cajon.includes('mint.hidden = movil ? !juntoHorno() : false'));
assert.ok(cajonCss.includes('z-index: 50'));
assert.ok(cajonCss.includes('bottom: calc(72px + env(safe-area-inset-bottom))'));
assert.ok(game.includes('Objeto.abrir(s.item,s.qty)'));
assert.ok(game.includes("ctrl.abort(), 15000"));

assert.ok(css.includes('#w-inv:not([hidden])'));
assert.ok(css.includes('z-index: 60 !important'));
assert.ok(read('play/baul.js').includes('!(sel && sel.mano)'));
assert.ok(read('play/baul.css').includes('z-index: 140'));

const ticks = [];
const elements = {};
function nodo(id) {
  if (!elements[id]) {
    elements[id] = {
      id, hidden: true, innerHTML: '', value: '',
      addEventListener() {},
      querySelectorAll() { return []; },
      querySelector() { return null; },
    };
  }
  return elements[id];
}
const sent = [];
const sandbox = {
  console,
  setInterval(fn) { ticks.push(fn); return 0; },
  matchMedia() { return { matches: true }; },
  document: {
    getElementById(id) { return nodo(id); },
    addEventListener() {},
    documentElement: { classList: { contains: () => true } },
    body: { appendChild() {}, classList: { contains: () => true } },
    head: { append() {} },
    readyState: 'complete',
    createElement() { return { id: '', hidden: true, style: {}, setAttribute() {}, append() {}, classList: { add() {}, contains: () => false } }; },
  },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(read('play/baul.js'), sandbox);
sandbox.LiveInk = {
  world: { mapId: 'city' },
  state: {
    walletLocked: false,
    player: { x: 10, y: 10 },
    nodes: { forEach(fn) { fn({ def: { type: 'furnace', id: 'horno_cantera', x: 18, y: 15 } }); } },
    net: { ok: true, ws: { readyState: 1, send(body) { sent.push(JSON.parse(body)); } } },
  },
  goMine() { sandbox._fue = 'mina'; },
  goTo(x, y) { sandbox._fue = x + ',' + y; },
};
assert.strictEqual(sandbox.Baul.juntoHorno(), false);
sandbox.LiveInk.world.mapId = 'mine';
sandbox.LiveInk.state.player = { x: 18, y: 16 };
assert.strictEqual(sandbox.Baul.juntoHorno(), true);
sandbox.LiveInk.state.player = { x: 18, y: 18 };
assert.strictEqual(sandbox.Baul.juntoHorno(), false);
sandbox.LiveInk.world.mapId = 'mina2';
sandbox.LiveInk.state.nodes = { forEach(fn) { fn({ def: { type: 'furnace', id: 'horno_ladera', x: 24, y: 16 } }); } };
sandbox.LiveInk.state.player = { x: 24, y: 17 };
assert.strictEqual(sandbox.Baul.juntoHorno(), true);

sandbox.LiveInk.world.mapId = 'city';
sandbox.Baul.abrirFicha({ id: 'mineral_cobre', qty: 4, lado: 'encima', mano: true });
const html = elements['baul-cuerpo'].innerHTML;
assert.ok(html.includes('Mineral de cobre'), html);
assert.ok(html.includes('Botar'));
assert.ok(html.includes('data-op="soltar"'));
assert.ok(html.includes('data-cant="1"'));
assert.ok(html.includes('data-cant="10"'));
assert.ok(html.includes('>X<'));
assert.ok(html.includes('>Todo<'));
assert.ok(html.includes('data-cant="10" disabled'));
assert.ok(html.includes('Horno de Las Palmas'));
assert.ok(html.includes('Horno de La Ladera'));
assert.ok(html.includes('id="baul-ir-horno"'));
assert.ok(!html.includes('>Guardar<'));
ticks.forEach((fn) => fn());
sandbox.Baul.paint(sandbox.Baul.ultima());
assert.ok(elements['baul-cuerpo'].innerHTML.includes('id="baul-ficha"'), 'la ficha de la mano sigue abierta');
sandbox.Baul.elegir({ lado: 'encima', kind: 'item', id: 'mineral_cobre', mano: false });
ticks.forEach((fn) => fn());
sandbox.Baul.paint(sandbox.Baul.ultima());
assert.ok(!elements['baul-cuerpo'].innerHTML.includes('id="baul-ficha"'), 'sin la ficha de la mano el pulso cierra');
sandbox.Baul.abrirFicha({ id: 'mineral_cobre', qty: 4, lado: 'encima', mano: true });
assert.strictEqual(sandbox.Baul.botonesBotar(4).find((row) => row.cant === '10').off, true);
assert.strictEqual(sandbox.Baul.botonesBotar(4).find((row) => row.cant === '1').off, false);
assert.strictEqual(sandbox.Baul.botonesBotar(4).find((row) => row.cant === 'all').off, false);

vm.runInContext(read('play/objeto.js'), sandbox);
assert.strictEqual(sandbox.Objeto.botar('mineral_cobre', 10), true);
assert.strictEqual(sent.at(-1).t, 'soltar');
assert.strictEqual(sent.at(-1).item, 'mineral_cobre');
assert.strictEqual(sent.at(-1).qty, 10);
assert.strictEqual(sandbox.Objeto.botar('smc', 1), false);
const antes = sent.length;
assert.strictEqual(sandbox.Baul.enviar({ disabled: true, dataset: { op: 'soltar', cant: '10', item: 'mineral_cobre' } }), false);
assert.strictEqual(sent.length, antes);

sandbox.LiveInk.world.mapId = 'city';
sandbox.Baul.irAlHorno();
assert.strictEqual(sandbox._fue, 'mina');
sandbox.LiveInk.world.mapId = 'mina2';
sandbox.Baul.irAlHorno();
assert.strictEqual(sandbox._fue, '24,17');
console.log('inventario móvil ok');
