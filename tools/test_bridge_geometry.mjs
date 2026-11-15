/* SPDX-License-Identifier: AGPL-3.0-or-later */
import * as T from '../play/three.module.js';
import { buildBridge4Sur, bridgeHeight, install } from '../play/bridge4sur.js';
import fs from 'node:fs';
import assert from 'node:assert/strict';

const world = JSON.parse(fs.readFileSync(new URL('../data/el-jardin.json', import.meta.url)));
const c = install(world);
const bridge = buildBridge4Sur(T, c);
bridge.group.updateMatrixWorld(true);
const bounds = new T.Box3().setFromObject(bridge.group);
assert(!bounds.isEmpty());
assert.equal(bridge.group.userData.cables, 51);
let triangles = 0, draws = 0;
bridge.group.traverse(o => {
  if (!o.isMesh) return;
  draws++;
  triangles += (o.count ?? 1) * (o.geometry.index?.count ?? o.geometry.attributes.position.count) / 3;
  for (const v of o.geometry.attributes.position.array) assert(Number.isFinite(v));
});
assert(triangles < 10000, triangles);
assert(draws <= 8, draws);
for (let x = c.x0; x < c.x1; x++) {
  const ray = new T.Raycaster(new T.Vector3(x * 2 + 1, 100, (c.y0 + 2) * 2 + 1), new T.Vector3(0, -1, 0));
  const hit = ray.intersectObjects(bridge.meshes, false)[0];
  assert(hit, 'Every crossing tile must be clickable');
  assert(Math.abs(hit.point.y - bridgeHeight(c, x + 0.5)) < 0.001);
}
bridge.update(0, 0, true);
assert(!bridge.group.visible);
bridge.update(110, 240, true);
assert(bridge.group.visible);
bridge.update(110, 240, false);
assert(!bridge.group.visible);
assert.equal(bridgeHeight(c, c.x0), c.profile.west);
assert.equal(bridgeHeight(c, c.x1), c.profile.east);
console.log(JSON.stringify({ draws, triangles, stays: 51, walkableRaycasts: c.x1 - c.x0, geometry: 'PASS' }));
