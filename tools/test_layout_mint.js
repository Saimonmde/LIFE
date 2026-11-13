/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

function load(file) {
  const context = { console };
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', file), 'utf8'), context, { filename: file });
  return context;
}

const layout = load('play/hud-layout-core.js').HudLayoutCore;
const rules = load('play/mining-rules.js').MiningRules;

assert.strictEqual(layout.storageKey(false, false), 'lifeinc.hud.layout.desktop.horizontal');
assert.strictEqual(layout.storageKey(false, true), 'lifeinc.hud.layout.desktop.vertical');
assert.strictEqual(layout.storageKey(true, false), 'lifeinc.hud.layout.movil.horizontal');
assert.strictEqual(layout.storageKey(true, true), 'lifeinc.hud.layout.movil.vertical');
assert.notStrictEqual(layout.storageKey(false, false), layout.storageKey(true, true));

const memory = new Map();
const store = {
  getItem: (k) => memory.has(k) ? memory.get(k) : null,
  setItem: (k, v) => memory.set(k, String(v)),
  removeItem: (k) => memory.delete(k),
};
const desktop = { 'hud-mapa': { x: 20, y: 30, scale: 1.2, minimized: false } };
const phone = { 'hotbar': { x: 8, y: 400, scale: 0.8, minimized: true, closed: false } };
layout.saveLayout(store, layout.storageKey(false, false), desktop);
layout.saveLayout(store, layout.storageKey(true, true), phone);
const back = layout.loadLayout(store, layout.storageKey(false, false));
assert.strictEqual(back['hud-mapa'].x, 20);
assert.strictEqual(back['hud-mapa'].scale, 1.2);
assert.strictEqual(layout.loadLayout(store, layout.storageKey(true, true))['hotbar'].minimized, true);
assert.strictEqual(Object.keys(layout.loadLayout(store, layout.storageKey(true, false))).length, 0);
assert.strictEqual(Object.keys(layout.unpack('no-es-json')).length, 0);
assert.deepStrictEqual(JSON.parse(JSON.stringify(layout.clampBox(-40, 900, 100, 40, 390, 800, 8))), { x: 8, y: 752 });
assert.strictEqual(layout.stepScale(1, 1), 1.1);
assert.strictEqual(layout.stepScale(1.8, 1), 1.8);
assert.strictEqual(layout.stepScale(0.55, -1), 0.55);
assert.ok(layout.fitScale(1.5, 900, 100, 400, 800, 8) < 1.5);

const ids = ['mineral_cobre', 'mineral_plata', 'mineral_oro', 'pepita_oro', 'lingote_cobre', 'lingote_plata', 'lingote_oro', 'moneda_cobre', 'moneda_plata', 'moneda_oro'];
const items = {};
for (const id of ids) items[id] = { id, stackable: true, maxStack: 999 };
let inv = Array(60).fill(null);
inv = rules.add(inv, items, 'mineral_oro', 10, 60);
inv = rules.add(inv, items, 'mineral_cobre', 6, 60);
const coins = rules.smelt(inv, items, 'mineral_oro', 2, 'coin', 60);
assert.strictEqual(coins.coins, 0);
assert.strictEqual(coins.item, 'moneda_oro');
assert.strictEqual(coins.qty, 4);
assert.strictEqual(rules.count(coins.inv, 'moneda_oro'), 4);
assert.strictEqual(rules.count(coins.inv, 'mineral_oro'), 0);
assert.strictEqual(rules.count(coins.inv, 'lingote_oro'), 0);
const ingots = rules.smelt(inv, items, 'mineral_cobre', 2, 'ingot', 60);
assert.strictEqual(ingots.coins, 0);
assert.strictEqual(ingots.item, 'lingote_cobre');
assert.strictEqual(ingots.qty, 2);
assert.strictEqual(rules.count(ingots.inv, 'lingote_cobre'), 2);
assert.strictEqual(rules.count(ingots.inv, 'moneda_cobre'), 0);
const ledger = rules.smelt(inv, items, 'mineral_oro', 1, 'coins', 60);
assert.strictEqual(ledger.coins, 30);
assert.strictEqual(rules.count(ledger.inv, 'moneda_oro'), 0);
assert.strictEqual(rules.count(ledger.inv, 'mineral_oro'), 5);
assert.ok(rules.smelt(inv, items, 'mineral_plata', 1, 'coin', 60).error);
assert.strictEqual(rules.recipes.mineral_plata.coinQty, 3);
assert.strictEqual(rules.recipes.mineral_cobre.ore, 3);
assert.strictEqual(rules.recipes.pepita_oro.coinItem, 'moneda_oro');
console.log('layout y recetas del horno: ok');
