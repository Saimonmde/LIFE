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
const game = fs.readFileSync(path.join(__dirname, '..', 'play', 'game.js'), 'utf8');
const css = fs.readFileSync(path.join(__dirname, '..', 'play', 'style.css'), 'utf8');
const page = fs.readFileSync(path.join(__dirname, '..', 'play', 'index.html'), 'utf8');
assert.ok(game.includes('iconStack'), 'la pila es sólo el dibujo cuando hay más de uno');
assert.ok(game.includes('itemArt'), 'el inventario elige el dibujo');
assert.ok(css.includes('#inventario .slot .n') && css.includes('var(--sans)'), 'la cifra de la casilla usa la sans');
assert.ok(page.includes('moneda_plata.svg'), 'el panel de Plata muestra la moneda de plata');
const hudCss = fs.readFileSync(path.join(__dirname, '..', 'play', 'hud-layout.css'), 'utf8');
assert.ok(hudCss.includes('body.pantalla-limpia #hud-recursos'), 'la pantalla limpia conserva la barra');
assert.ok(hudCss.includes('span:not(#sai-chip)'), 'en limpio sólo queda el saldo SMC');
assert.ok(css.includes('#sai-chip'), 'el rediseño no quita la pastilla SMC');
assert.ok(!/pantalla-limpia #sai-chip\s*\{[^}]*display:\s*none/.test(css), 'el saldo SMC sigue visible en limpio');
for (const name of ['moneda_cobre', 'moneda_plata', 'moneda_oro', 'lingote_cobre', 'lingote_plata', 'lingote_oro']) {
  const svg = fs.readFileSync(path.join(__dirname, '..', 'graphics', 'mining', name + '.svg'), 'utf8');
  const pile = fs.readFileSync(path.join(__dirname, '..', 'graphics', 'mining', name + '_pila.svg'), 'utf8');
  assert.ok(svg.includes('linearGradient') || svg.includes('radialGradient'), name + ' con metal');
  assert.ok(svg.includes('M9.2-8.4'), name + ' lleva la S');
  assert.ok(pile.length > svg.length * 0.8, name + ' tiene variante en pila');
}
assert.strictEqual(layout.formatClock(new Date('2026-11-13T18:04:00Z'), 'America/Bogota'), 'vie 13 nov 2026 · 1:04 p. m.');
assert.strictEqual(layout.formatClock(new Date('2026-11-13T05:04:00Z'), 'America/Bogota'), 'vie 13 nov 2026 · 12:04 a. m.');
const tile = layout.minimapTile(100, 50, { x0: 10, y0: 20, span: 100 }, 200);
assert.strictEqual(tile.x, 60);
assert.strictEqual(tile.y, 45);
assert.strictEqual(layout.minimapTile(0, 0, { x0: 0, y0: 0, span: 0 }, 10), null);
const plata = { x: 276, y: 252, w: 300, h: 400 };
const clock = { x: 540, y: 62, w: 200, h: 16 };
const eye = { x: 604, y: 156, w: 72, h: 72 };
const rings = { x: 1134, y: 190, w: 134, h: 64 };
const globe = { x: 1088, y: 130, w: 44, h: 44 };
for (const box of [clock, eye, rings, globe]) assert.strictEqual(layout.rectsOverlap(box, plata), false, 'no tapa la Plata');
assert.strictEqual(layout.rectsOverlap(clock, rings), false);
assert.strictEqual(layout.rectsOverlap(eye, globe), false);
const drained = layout.staminaStep(20, false, true, false, 2);
assert.strictEqual(drained.sprint, true);
assert.ok(drained.energy < 20);
assert.strictEqual(drained.locked, true);
const locked = layout.staminaStep(0, true, true, false, 1);
assert.strictEqual(locked.sprint, false);
assert.ok(locked.energy > 0);
assert.strictEqual(locked.locked, true);
const free = layout.staminaStep(30, true, true, false, 0.1);
assert.strictEqual(free.locked, false);
assert.strictEqual(free.sprint, false);
const again = layout.staminaStep(free.energy, free.locked, true, false, 0.1);
assert.strictEqual(again.sprint, true);
assert.strictEqual(layout.applyDamage(100, 8), 92);
assert.strictEqual(layout.applyDamage(3, 10), 0);
assert.strictEqual(layout.healthStep(40, 5000, 1000, 1), 40);
assert.ok(layout.healthStep(40, 0, 1000, 1) > 40);
console.log('layout y recetas del horno: ok');
