/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const map = require('../play/assets/cafe-cacao/map.js');

const dir = path.join(__dirname, '../play/assets/cafe-cacao');
const needed = ['cafe', 'cacao', 'bag', 'kg', 'oro', 'plata', 'cobre', 'ingot', 'workshopCafe', 'workshopCacao', 'plotCafePlanton', 'plotCafeVerde', 'plotCafeMaduro', 'plotCacaoPlanton', 'plotCacaoVerde', 'plotCacaoMaduro'];
for (const key of needed) {
  assert.ok(map.icons[key], 'falta el icono ' + key);
  const file = path.join(dir, map.icons[key]);
  assert.ok(fs.existsSync(file), map.icons[key]);
}
assert.ok(map.colors.leaf && map.colors.cherry && map.colors.pod);
assert.strictEqual(map.credit, 'Sara');
assert.deepStrictEqual(map.stand, {
  workshopCafe: 'taller_cafe_lite.png',
  workshopCacao: 'taller_cacao_lite.png',
  kg: 'kg_cosechados.svg',
});
for (const file of Object.values(map.sheets)) {
  assert.ok(fs.existsSync(path.join(dir, file)), file);
}
for (const crop of ['cafe', 'cacao']) {
  assert.strictEqual(map.stageIcons[crop].length, 5);
  for (const row of map.stageIcons[crop]) {
    const file = path.join(dir, row.file);
    assert.ok(fs.existsSync(file), row.file);
    assert.ok(fs.statSync(file).size < 80000, row.file);
    assert.ok(fs.existsSync(path.join(dir, row.live)), row.live);
  }
}
assert.ok(fs.existsSync(path.join(dir, map.manifest)));
for (const file of Object.values(map.icons)) {
  const bytes = fs.statSync(path.join(dir, file)).size;
  assert.ok(bytes < 80000, file + ' pesa demasiado para el celular: ' + bytes);
}
const code = fs.readFileSync(path.join(__dirname, '../play/libro-publico.js'), 'utf8');
assert.ok(code.includes('CAFE_CACAO_ART'));
assert.ok(!code.includes('<svg'));
console.log('cafe cacao art ok');
