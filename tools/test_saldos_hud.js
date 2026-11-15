/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Inventario redondo y saldos visibles. No toca la emisión. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const page = read('play/index.html');
const css = read('play/saldos.css');
const theme = read('play/theme.css');
const style = read('play/style.css');
const game = read('play/game.js');
const sim = read('play/simulacion.js');
const cajon = read('play/cajon.js');
const layout = read('play/hud-layout.js');
const economy = read('tools/economy.py');
const cobre = read('tools/cobre.py');
const plata = read('tools/plata.py');

assert.ok(page.includes('href="saldos.css'));
assert.ok(page.includes('id="barra-monedas"'));
assert.ok(page.includes('id="barra-oro"'));
assert.ok(page.includes('id="barra-plata"'));
assert.ok(page.includes('id="barra-cobre"'));
assert.ok(page.includes('moneda_cobre.svg'));
assert.ok(!/Unifraktur|blackletter|Caroling/i.test(theme + style + page));
assert.ok(css.includes('UnifrakturMaguntia'));
assert.ok(css.includes('.libro-saldos'));
assert.ok(css.includes('#barra-monedas'));
assert.ok(css.includes('border-radius: 50%'));
assert.ok(css.includes('border-radius: 30px'));
assert.ok(fs.existsSync(path.join(root, 'play/fonts/UnifrakturMaguntia-Book.ttf')));
assert.ok(game.includes('class="gema"'));
assert.ok(sim.includes('id="libro-saldo-oro"'));
assert.ok(sim.includes('Simon Coins'));
assert.ok(sim.includes('Simonchis es el cobre'));
assert.ok(sim.includes('if (m.ledger) api.S.ledger = m.ledger'));
assert.ok(sim.includes('Cajon.paint()'));
assert.ok(cajon.includes('function labeled'));
assert.ok(cajon.includes('barra-cobre'));
assert.ok(cajon.includes('libro-saldo-cobre'));
assert.ok(layout.includes("['barra-monedas', 'Monedas', 'hud']"));
assert.ok(economy.includes('SUBS = 100_000_000'));
assert.ok(economy.includes("BASE_NAME = 'Simonchi'"));
assert.ok(cobre.includes('MAX_SUPPLY = 333_000_000'));
assert.ok(plata.includes('MAX_SUPPLY'));
console.log('saldos hud: ok');
