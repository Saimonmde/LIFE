/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const saldos = require('../play/saldos.js');

const state = {
  me: { name: 'Minero' },
  econ: { wallets: { Minero: 0 } },
  saldos: { simoncoin: 0, simonplata: 0, simonchis: 0 },
};
const delta = saldos.aplicar(state, {
  t: 'acunar_result',
  ledger: { balances: { simoncoin: 16000000, simonplata: 0, simonchis: 2 } },
  historial: [{ serial: 'SCH-00000001', coin: 'simonchis', base: 2, note: 'Acuñación' }],
});
assert.strictEqual(state.econ.wallets.Minero, 16000000, 'el número de Simoncoin sale de cero');
assert.strictEqual(state.saldos.simonchis, 2, 'Simonchis deja de quedar en cero');
assert.strictEqual(state.plata.balanceSph, 0);
assert.strictEqual(delta.simoncoin, 16000000);
assert.strictEqual(delta.simonchis, 2);
assert.strictEqual(state.historial[0].serial, 'SCH-00000001');
assert.strictEqual(saldos.texto(16000000, 'simoncoin'), '0,16');
assert.strictEqual(saldos.texto(2, 'simonchis'), '2');
console.log('saldos del cliente: ok');
