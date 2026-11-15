/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const libro = require('../play/libro-publico.js');

assert.strictEqual(libro.coinLine(0.25, 'Simoncoin'), 'Se acuñaron 0,25 Simoncoin');
assert.deepStrictEqual(
  libro.feedFromCoins(
    { coins: [{ id: 'simoncoin', name: 'Simoncoin', minted: 0 }] },
    { coins: [{ id: 'simoncoin', name: 'Simoncoin', minted: 0.25 }] },
  ),
  ['Se acuñaron 0,25 Simoncoin'],
);

const html = libro.render({
  coins: [
    { id: 'simoncoin', name: 'Simoncoin', minted: 3, max: 21000000 },
    { id: 'simonplata', name: 'Simonplata', minted: 0, max: 84000000 },
    { id: 'simonchis', name: 'Simonchis', minted: 0, max: 333000000 },
  ],
  foundry: { lingote_oro: 2, lingote_plata: 0, lingote_cobre: 1 },
  historia: [{ account: 'CuentaAnaPrivada', note: 'no debe verse' }],
  balances: { simoncoin: 99 },
  finca: {
    harvestedKg: { cafe: 4, cacao: 6 },
    processedBags: { cafe: 2, cacao: 0 },
    feed: ['Se procesó 1 bulto de café'],
  },
});
assert.ok(html.includes('Este libro es la memoria de las monedas del juego.'));
assert.ok(html.includes('no son dinero real'));
assert.ok(html.includes('21.000.000 y no más'));
assert.ok(html.includes('El libro público no dice quién.'));
assert.ok(html.includes('Se procesó 1 bulto de café'));
assert.ok(html.includes('bultos procesados'));

const weighed = libro.render({
  coins: [],
  finca: {
    harvestedKg: { cafe: 940, cacao: 900 },
    processedBags: { cafe: 2, cacao: 2 },
    crops: {
      cafe: { freshName: 'café cereza', unitCount: 'sacos de 70 kg de excelso' },
      cacao: { freshName: 'cacao en baba', unitCount: 'cajones de 150 kg secos' },
    },
    feed: [],
  },
});
assert.ok(weighed.includes('sacos de 70 kg de excelso'));
assert.ok(weighed.includes('cajones de 150 kg secos'));
assert.ok(weighed.includes('café cereza'));
assert.ok(!html.includes('CuentaAnaPrivada'));
assert.ok(html.includes('Lingotes'));
assert.ok(html.includes('>2<'));
assert.ok(!html.includes('CuentaAnaPrivada'));
assert.ok(!html.includes('no debe verse'));
assert.ok(!html.includes('counterparty'));

const bare = libro.render({
  coins: [],
  finca: { harvestedKg: { cafe: 0, cacao: 1 }, processedBags: { cafe: 0, cacao: 0 }, feed: [] },
});
assert.ok(bare.includes('El libro te lo dice con calma.'));
assert.ok(!bare.includes('Lingotes'));
assert.strictEqual(libro.ingotRows({}), null);
assert.deepStrictEqual(libro.ingotRows({ foundry: { lingote_oro: 2 } }), { oro: 2, plata: 0, cobre: 0 });
console.log('libro publico ok');
