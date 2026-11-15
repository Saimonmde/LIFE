/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const map = require('../play/assets/cafe-cacao/map.js');

const dir = path.join(__dirname, '../play/assets/cafe-cacao');
const needed = ['cafe', 'cacao', 'bag', 'oro', 'plata', 'cobre', 'ingot', 'workshopCafe', 'workshopCacao', 'shade', 'cherry', 'pod', 'libro', 'patio'];
for (const key of needed) {
  assert.ok(map.icons[key], 'falta el icono ' + key);
  const file = path.join(dir, map.icons[key]);
  assert.ok(fs.existsSync(file), map.icons[key]);
}
assert.ok(map.colors.leaf && map.colors.cherry && map.colors.pod);
const code = fs.readFileSync(path.join(__dirname, '../play/libro-publico.js'), 'utf8');
assert.ok(code.includes('CAFE_CACAO_ART'));
assert.ok(!code.includes('<svg'));
console.log('cafe cacao art ok');
