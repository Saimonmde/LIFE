/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* El baúl de la mina abre en la mina y las cifras se leen en SMC. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const page = read('play/index.html');
const game = read('play/game.js');
const ui = read('play/baul.js');
const css = read('play/baul.css');
assert.ok(page.includes('id="baul-mina"'));
assert.ok(page.includes('data-cierra="baul-mina"'));
assert.ok(page.includes('id="baul-abrir"'));
assert.ok(page.includes('baul.js?v=ficha'));
assert.ok(page.includes('baul.css?v=ficha'));
assert.ok(game.includes("d.type === 'mine_chest'"));
assert.ok(game.includes('Baul.open()'));
assert.ok(game.includes("DESTINO_IDS=new Set(['mina'"));
assert.ok(game.includes("m.id === 'mina'"));
assert.ok(ui.includes("t: 'baul_mover'"));
assert.ok(ui.includes("t: 'baul_smc'"));
assert.ok(ui.includes('Guardar todo'));
assert.ok(ui.includes('Sacar todo'));
assert.ok(ui.includes('class="casillas"'));
assert.ok(ui.includes('casilla-n'));
assert.ok(ui.includes('Encima'));
assert.ok(ui.includes('Baúl'));
assert.ok(ui.includes("data-cant=\"' + b.cant"));
assert.ok(ui.includes(">1</button>") === false || ui.includes("b.texto"));
assert.ok(ui.includes('Todo'));
assert.ok(ui.includes('FICHAS'));
assert.ok(ui.includes('Mineral de cobre'));
assert.ok(ui.includes('0,001 SMC'));
assert.ok(ui.includes("here !== 'mina2'"));
assert.ok(ui.includes('bank_chest'));
assert.ok(ui.includes('Casa.ajena'));
assert.ok(ui.includes('<svg'));
assert.ok(css.includes('.casillas'));
assert.ok(css.includes('min-height: 72px') || css.includes('min-height:72px'));
assert.ok(css.includes('min-height: 48px') || css.includes('min-height:48px'));
for (const banned of ['jagex', 'osrs', 'runescape']) {
  assert.ok(!ui.toLowerCase().includes(banned), banned);
  assert.ok(!css.toLowerCase().includes(banned), banned);
}
const trade = read('play/economy-ui.js');
const tradeCss = read('play/economy.css');
assert.ok(trade.includes('id="trade-uno"'));
assert.ok(trade.includes('id="trade-x"'));
assert.ok(trade.includes('>Todo<'));
assert.ok(trade.includes('trade-ico'));
assert.ok(trade.includes('walletName'));
assert.ok(trade.includes('balanceSubs'));
assert.ok(tradeCss.includes('#coin-trade .trade-card'));
assert.ok(tradeCss.includes('aspect-ratio:1'));
for (const banned of ['SMH', 'SMP', 'SPH', 'Simonchi', 'Simonplata']) {
  assert.ok(!ui.includes(banned), banned);
  assert.ok(!css.includes(banned), banned);
}
const chest = page.slice(page.indexOf('id="baul-mina"'), page.indexOf('id="autotest"'));
for (const banned of ['SMH', 'SMP', 'SPH']) assert.ok(!chest.includes(banned), banned);

const vm = require('vm');
const elements = {};
function nodo(id) {
  if (!elements[id]) {
    elements[id] = {
      id, hidden: id !== 'baul-cuerpo', innerHTML: '', value: '',
      addEventListener() {},
      querySelectorAll() { return []; },
      querySelector() { return null; },
    };
  }
  return elements[id];
}
const sandbox = {
  console,
  setInterval() { return 0; },
  document: {
    getElementById(id) { return nodo(id); },
    addEventListener() {},
    body: { appendChild() {} },
  },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(ui, sandbox);
const sent = [];
sandbox.LiveInk = {
  world() { return sandbox._map; },
  state: {
    walletLocked: false,
    player: { x: 16, y: 17 },
    nodes: { forEach(fn) { fn({ def: { type: 'mine_chest', x: 15, y: 16 } }); } },
    net: { ok: true, ws: { readyState: 1, send(body) { sent.push(JSON.parse(body)); } } },
  },
};
sandbox._map = { mapId: 'mine' };
sandbox.Casa = {
  layout: { items: [{ type: 'chest', x: 1, y: 7 }] },
  ajena() { return false; },
  playerName() { return 'Ana'; },
};
const view = {
  smc: {
    billetera: { exacto: '2,5 SMC' },
    baul: { exacto: '1,5 SMC' },
    total: { exacto: '4 SMC' },
    escala: 'Las cantidades se muestran en SMC.',
    topes: '',
    tope: '21.000.000 SMC',
  },
  filas: [{ id: 'mineral_cobre', name: 'Cobre', encima: 4, baul: 1, grupo: 'mineral' }],
  totales: { encima: 4, baul: 1 },
};
sandbox.Baul.paint(view);
sandbox.Baul.elegir({ lado: 'encima', kind: 'item', id: 'mineral_cobre' });
const cobre = elements['baul-cuerpo'].innerHTML;
assert.ok(cobre.includes('Mineral de cobre'), cobre);
assert.ok(cobre.includes('Se saca picando en las minas. Se funde en el horno para acuñar Simoncoins a 0,001 SMC.'));
assert.ok(cobre.includes('Encima: 4'));
assert.ok(cobre.includes('Baúl: 1'));
assert.ok(cobre.includes('Guardar'));
assert.ok(cobre.includes('data-cant="1">'));
assert.ok(cobre.includes('data-cant="10" disabled'));
assert.ok(cobre.includes('data-cant="100" disabled'));
assert.ok(cobre.includes('casilla sel') || cobre.includes('class="casilla sel"'));
sandbox.Baul.elegir({ lado: 'baul', kind: 'smc', id: 'smc' });
const smc = elements['baul-cuerpo'].innerHTML;
assert.ok(smc.includes('Simoncoin'));
assert.ok(smc.includes('Encima: 2,5 SMC'));
assert.ok(smc.includes('Baúl: 1,5 SMC'));
assert.ok(smc.includes('Sacar'));
assert.ok(smc.includes('data-cant="1">'));
assert.ok(smc.includes('data-cant="10" disabled'));
assert.ok(smc.includes('data-cant="100" disabled'));
const montos = sandbox.Baul.botones(4, false, '10');
assert.strictEqual(montos.find((row) => row.cant === '1').off, false);
assert.strictEqual(montos.find((row) => row.cant === '10').off, true);
assert.strictEqual(montos.find((row) => row.cant === '100').off, true);
assert.strictEqual(montos.find((row) => row.cant === 'x').off, true);
assert.strictEqual(montos.find((row) => row.cant === 'all').off, false);
const monedas = sandbox.Baul.botones(2.5, true, '1,5');
assert.strictEqual(monedas.find((row) => row.cant === '1').off, false);
assert.strictEqual(monedas.find((row) => row.cant === 'x').off, false);
assert.strictEqual(monedas.find((row) => row.cant === '10').off, true);
assert.strictEqual(sandbox.Baul.botones(2.5, true, '9').find((row) => row.cant === 'x').off, true);
sandbox.Baul.fijarMonto('1,5');
assert.strictEqual(sandbox.Baul.enviar({ disabled: false, dataset: { cant: 'x', kind: 'smc', op: 'withdraw', item: 'smc' } }), true);
assert.strictEqual(sent.at(-1).t, 'baul_smc');
assert.strictEqual(sent.at(-1).op, 'withdraw');
assert.strictEqual(sent.at(-1).amount, '1,5');
assert.strictEqual(sent.at(-1).all, false);
sandbox.Baul.enviar({ disabled: false, dataset: { cant: '10', kind: 'item', op: 'deposit', item: 'mineral_cobre' } });
assert.strictEqual(sent.at(-1).t, 'baul_mover');
assert.strictEqual(sent.at(-1).qty, 10);
assert.strictEqual(sent.at(-1).item, 'mineral_cobre');
sandbox.Baul.enviar({ disabled: false, dataset: { cant: 'all', kind: 'item', op: 'deposit', item: 'madera' } });
assert.strictEqual(sent.at(-1).qty, 'all');
assert.strictEqual(sent.at(-1).all, true);
const antes = sent.length;
assert.strictEqual(sandbox.Baul.enviar({ disabled: true, dataset: { cant: '100', kind: 'item', op: 'deposit', item: 'mineral_cobre' } }), false);
assert.strictEqual(sent.length, antes);
sandbox.Baul.onNet({ t: 'baul', ok: false, reason: 'Acércate al baúl.', view });
assert.ok(elements['baul-cuerpo'].innerHTML.includes('Acércate al baúl.'));
assert.strictEqual(sandbox.Baul.cerca(), true);
sandbox.LiveInk.state.player = { x: 1, y: 1 };
assert.strictEqual(sandbox.Baul.cerca(), false);
sandbox._map = { mapId: 'casa' };
sandbox.LiveInk.state.player = { x: 2, y: 7 };
sandbox.LiveInk.state.nodes = { forEach() {} };
assert.strictEqual(sandbox.Baul.cerca(), true);
sandbox.Casa.ajena = () => true;
assert.strictEqual(sandbox.Baul.cerca(), false);
console.log('baúl de la mina ok');
