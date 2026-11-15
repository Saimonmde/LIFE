const assert = require('assert');
const fs = require('fs');
const path = require('path');
require('../play/mining-rules.js');
const rules = globalThis.MiningRules;

const items = {
  piedra: { name: 'Piedra', stack: 99 },
  mineral_oro: { name: 'Mineral de oro', stack: 1e15 },
  pepita_oro: { name: 'Pepita de oro', stack: 1e15 },
  bolsa_cafe: { name: 'Bolsa de café', stack: 20 },
};
const full = Array.from({ length: 60 }, (_, i) => ({ item: 'piedra', qty: 1, uid: 's' + i }));
assert.strictEqual(rules.add(full, items, 'mineral_oro', 2, 60), null);
assert.strictEqual(rules.add(full, items, 'pepita_oro', 1, 60), null);
assert.strictEqual(rules.add(full, items, 'bolsa_cafe', 1, 60), null);
const withOre = full.slice();
withOre[0] = { item: 'mineral_oro', qty: 3 };
const stacked = rules.add(withOre, items, 'mineral_oro', 2, 60);
assert.strictEqual(stacked[0].qty, 5);

const game = fs.readFileSync(path.join(__dirname, '../play/game.js'), 'utf8');
const river = game.slice(game.indexOf("d.type === 'nodo_oro_fluvial'"), game.indexOf("d.type === 'mineral_rock'"));
assert.ok(river.indexOf('if (!give(') < river.indexOf("t: 'lavar'"), 'el río no avisa al servidor si la mochila está llena');
assert.ok(game.includes('Tu mochila está llena'));
assert.ok(game.includes('Dejarlo donde está'));
assert.ok(game.includes('Abrir la mochila'));
const rock = game.slice(game.indexOf("d.type === 'mineral_rock'"), game.indexOf('function hunt'));
assert.ok(rock.includes('if(!invAdd(d.yield.item,q))return'));
console.log('mochila llena ok');
