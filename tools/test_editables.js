/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const context = { console };
context.globalThis = context;
vm.createContext(context);
function load(file) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'play', 'editor', file), 'utf8'), context, { filename: file });
}
load('editables.js');
load('model.js');
const Editables = context.Editables;
const Model = context.EditorModel;

const ids = Editables.list().map(entry => entry.id);
['palma', 'guayacan', 'sombra', 'arbusto', 'flores', 'pasto', 'cafe', 'cacao', 'roca', 'cerca', 'banca', 'farol', 'letrero', 'fuente', 'path:piedra', 'path:adoquin', 'path:carretera', 'surface', 'terrain', 'object'].forEach(id => {
  assert.ok(ids.includes(id), id);
});

Editables.register({
  id: 'farolillo',
  label: 'Farolillo',
  icon: 'farol',
  layer: 'decoration',
  params: [{ key: 'scale', type: 'number', min: 0.25, max: 4 }],
  render: () => ({ parts: [{ shape: 'sphere', r: 0.2, color: '#f3e2a4' }] }),
  serialize: (item) => ({ id: item.id, type: 'farolillo', x: item.x, y: item.y, z: item.z, scale: item.scale, rotY: item.rotY, grounded: true }),
  deserialize: (raw) => ({ id: raw.id, type: 'farolillo', x: raw.x, y: raw.y, z: raw.z, scale: raw.scale, rotY: raw.rotY, grounded: true }),
});
const raw = Editables.serialize({ id: 'l1', type: 'farolillo', x: 1, y: 2, z: 3, scale: 1.2, rotY: 30 });
const back = Editables.deserialize(raw);
assert.strictEqual(back.type, 'farolillo');
assert.strictEqual(back.scale, 1.2);
assert.deepStrictEqual(Editables.get('farolillo').render().parts[0].color, '#f3e2a4');
assert.throws(() => Editables.deserialize({ type: 'no-existe' }), /desconocido/);
assert.throws(() => Editables.register({ id: 'mal' }), /etiqueta/);

assert.strictEqual(Model.brushCells(4, 5, 1).length, 1);
assert.strictEqual(Model.brushCells(4, 5, 3).length, 9);
assert.strictEqual(Model.brushCells(4, 5, 5).length, 25);

const session = Model.session(Model.emptyCurrent());
session.commit(Model.paintPaths(session.current, Model.brushCells(2, 2, 1), 'piedra'));
session.commit(Model.paintPaths(session.current, Model.brushCells(2, 3, 1), 'adoquin'));
assert.strictEqual(session.current.paths.map(item => item.style).join(','), 'piedra,adoquin');
assert.ok(session.undo());
assert.strictEqual(session.current.paths.length, 1);
assert.ok(session.redo());
assert.strictEqual(session.current.paths.length, 2);
const round = JSON.parse(JSON.stringify(session.current));
assert.strictEqual(round.paths[0].id, '2:2');

const placed = Model.placeProps(Model.emptyCurrent(), [{ id: 'p1', type: 'banca', x: 3, y: 0, z: 4, scale: 8, rotY: 10, grounded: true }]);
assert.strictEqual(placed.props[0].scale, 4);
assert.strictEqual(placed.props[0].type, 'banca');
const flat = Model.terrainApply(Model.emptyCurrent(), [{ x: 1, z: 1 }, { x: 2, z: 1 }], 'flatten', 1, (x) => x);
assert.strictEqual(flat.terrain.find(cell => cell.x === 1).dy, 1);
const raised = Model.terrainApply(Model.emptyCurrent(), [{ x: 1, z: 1 }], 'raise', 0.5, () => 0);
assert.strictEqual(raised.terrain[0].dy, 0.5);

const page = fs.readFileSync(path.join(__dirname, '..', 'play', 'index.html'), 'utf8');
assert.ok(page.includes('editor/editables.js'));
assert.ok(page.includes('editor/editor.js'));
assert.ok(fs.readFileSync(path.join(__dirname, '..', 'server.py'), 'utf8').includes('world_edit_request'));
console.log('editables ok');
