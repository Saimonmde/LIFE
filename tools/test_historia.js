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
assert.ok(page.includes('id="banco-cambiar"'));
assert.ok(page.includes('Guardar SMP'));
assert.ok(page.includes('Retirar SMP'));
assert.ok(game.includes('Acuñar SMC'));
assert.ok(game.includes('Acuñar SMP'));
assert.ok(game.includes('Faltan minerales'));
const pow = fs.readFileSync(path.join(__dirname, '..', 'play', 'pow.js'), 'utf8');
assert.ok(pow.includes('El fondo de oro se está llenando; vuelve cuando se mine más SMC'));
const theme = fs.readFileSync(path.join(__dirname, '..', 'play', 'theme.css'), 'utf8');
assert.ok(theme.includes('--glass-deep: rgba(12, 14, 20, 0.72)'));
assert.ok(theme.includes('backdrop-filter'));
assert.ok(!/Cinzel|Unifraktur|blackletter|Caroling/i.test(theme + css + page));
const smpRows = context.Historia.filas({
  blocks: [{ height: 0, ts: 0, txs: [{ type: 'genesis', to: 'tesoro_genesis', amountSubs: 50 }] }],
  mempool: [{ type: 'bank', coin: 'SMP', from: 'Ana', to: 'deposito', amountSubs: 0, amountSph: 100, note: 'Depósito de Plata en el banquito' }],
});
assert.strictEqual(smpRows[0].balanceSubs, 50);
assert.strictEqual(smpRows[1].coin, 'SMP');
assert.strictEqual(smpRows[1].amountSph, 100);
assert.strictEqual(smpRows[1].label, 'Banquito Plata');
console.log('historia y pastilla: ok');
