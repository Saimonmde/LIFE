/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
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
const html = fs.readFileSync(path.join(__dirname, '../play/index.html'), 'utf8');
const tag = html.match(/src="(finca-modelo\.js[^"]*)"/);
assert.ok(tag, 'falta finca-modelo.js en la página');
assert.ok(fs.existsSync(path.join(__dirname, '../play', tag[1].split('?')[0])));
const scene = fs.readFileSync(path.join(__dirname, '../play/finca3d.js'), 'utf8');
assert.ok(scene.includes('plotCafePlanton') && scene.includes('plotCafeVerde') && scene.includes('plotCafeMaduro'));
assert.ok(scene.includes('Sprite'));
assert.ok(scene.includes('opt.height'));
assert.ok(scene.includes('v2/'));
console.log('finca modelo ok');
