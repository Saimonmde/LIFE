/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const context = { console };
context.globalThis = context;
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'play', 'historia.js'), 'utf8'), context, { filename: 'historia.js' });
const rows = context.Historia.filas({
  blocks: [{
    height: 0, ts: 0, txs: [{ type: 'genesis', to: 'tesoro_genesis', amountSubs: 210000 }],
  }, {
    height: 1, ts: 1700000000, txs: [
      { type: 'mint', to: 'Ana', amountSubs: 1000 },
      { type: 'fusion', from: 'Ana', to: 'Simon', amountSubs: 1000, note: 'Fusión inicial a la cuenta del fundador' },
    ],
  }],
  plata: { txs: [{ type: 'exchange', name: 'Ana', gotSmh: 50, spentSph: 5000, t: 1700000005 }] },
});
assert.strictEqual(rows.map(row => row.type).join(','), 'reserva,minado,fusion,cambio');
assert.strictEqual(rows[1].balanceSubs, 1000);
assert.strictEqual(rows[2].account, 'Ana → Simon');
assert.strictEqual(rows[2].balanceSubs, 1000);
assert.strictEqual(rows[2].note, 'Fusión inicial a la cuenta del fundador');
assert.strictEqual(rows[3].label, 'Cambio plata→oro');
const page = fs.readFileSync(path.join(__dirname, '..', 'play', 'index.html'), 'utf8');
const css = fs.readFileSync(path.join(__dirname, '..', 'play', 'style.css'), 'utf8');
const game = fs.readFileSync(path.join(__dirname, '..', 'play', 'game.js'), 'utf8');
assert.ok(page.includes('id="smc-pill"'));
assert.ok(css.includes('#smc-pill'));
assert.ok(css.includes('body.pantalla-limpia #smc-pill'));
assert.ok(game.includes('¿Teletransportarte a '));
assert.ok(game.includes('askMapSpot'));
assert.ok(page.includes('>Confirmar<'));
assert.ok(page.includes('>Ir aquí<'));
console.log('historia y pastilla: ok');
