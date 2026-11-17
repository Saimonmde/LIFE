/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const game = fs.readFileSync(path.join(__dirname, '../play/game.js'), 'utf8');
const fish = game.slice(game.indexOf("d.type === 'fishing_spot'"), game.indexOf("d.type === 'nodo_oro_fluvial'"));
assert.ok(fish.includes("t: 'pescar'"), 'en línea la red le pregunta al servidor');
assert.ok(fish.includes('rollTable'), 'sin servidor la red sigue pescando en local');
const gold = game.slice(game.indexOf("d.type === 'nodo_oro_fluvial'"), game.indexOf("d.type === 'mine_chest'"));
assert.ok(gold.includes('onRiverGold'), 'la batea pide la acuñación del río');
assert.ok(gold.includes("kind: 'lavar'"), 'la pepita sigue pasando por el servidor');
const finca = fs.readFileSync(path.join(__dirname, '../play/finca.js'), 'utf8');
assert.ok(finca.includes('huerta-bed') && finca.includes('huerta_sembrar') && finca.includes('huerta-bar'));
const fauna = fs.readFileSync(path.join(__dirname, '../play/fauna.js'), 'utf8');
assert.ok(fauna.includes('fauna_lanza') && fauna.includes('piel_puma') && fauna.includes('puma-duelo'));
console.log('oficios rio ok');
