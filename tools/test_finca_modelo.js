/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const modelo = require('../play/finca-modelo.js');
const map = require('../play/assets/cafe-cacao/map.js');

const flat = modelo.visualFor(map, { group: 'plant', crop: 'cafe', id: 'siembra', distance: 4 });
assert.strictEqual(flat.kind, 'flat');
assert.ok(flat.url.endsWith('cafe_siembra_64.png'));

const phone = modelo.visualFor(map, { group: 'plant', crop: 'cacao', id: 'cosecha', mobile: true, distance: 2 });
assert.strictEqual(phone.kind, 'flat');
assert.ok(phone.url.endsWith('cacao_cosecha_64.png'));

const withGlb = JSON.parse(JSON.stringify(map));
withGlb.models.plant.cafe.fruto.glb = 'cafe_fruto.glb';
withGlb.models.plant.cafe.fruto.lod = 'cafe_fruto_lejano.glb';
const near = modelo.visualFor(withGlb, { group: 'plant', crop: 'cafe', id: 'fruto', distance: 6 });
assert.strictEqual(near.kind, 'glb');
assert.strictEqual(near.lod, 'near');
assert.ok(near.url.endsWith('cafe_fruto.glb'));
const far = modelo.visualFor(withGlb, { group: 'plant', crop: 'cafe', id: 'fruto', distance: 40 });
assert.strictEqual(far.lod, 'far');
assert.ok(far.url.endsWith('cafe_fruto_lejano.glb'));
const hand = modelo.visualFor(withGlb, { group: 'plant', crop: 'cafe', id: 'fruto', distance: 4, mobile: true });
assert.strictEqual(hand.kind, 'flat');

assert.deepStrictEqual(modelo.PHASES, ['siembra', 'crecimiento', 'floracion', 'fruto', 'cosecha']);
console.log('finca modelo ok');
