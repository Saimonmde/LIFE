/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Gallo low-poly. Malla original: cresta roja, cuerpo en capas y cola oscura. */
import * as T from './three.module.js';

const CACHE = { geo: new Map(), mat: new Map() };
const COLOR = {
  body: '#c47a32',
  deep: '#8d4e22',
  wing: '#e0b15a',
  tail: '#243028',
  tailGold: '#c9a15a',
  comb: '#d12626',
  wattle: '#c41e1e',
  beak: '#e2b13a',
  leg: '#e6c36a',
};

function geo(key, build) {
  if (!CACHE.geo.has(key)) CACHE.geo.set(key, build());
  return CACHE.geo.get(key);
}
function mat(hex) {
  if (!CACHE.mat.has(hex)) CACHE.mat.set(hex, new T.MeshLambertMaterial({ color: hex, flatShading: true }));
  return CACHE.mat.get(hex);
}
function box(w, h, d) {
  return geo('g' + w + 'x' + h + 'x' + d, () => new T.BoxGeometry(w, h, d));
}
function part(root, w, h, d, x, y, z, color) {
  const mesh = new T.Mesh(box(w, h, d), mat(color));
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  root.add(mesh);
  return mesh;
}

export function createGallo() {
  const root = new T.Group();
  const body = part(root, 0.42, 0.36, 0.58, 0, 0.48, 0.02, COLOR.body);
  part(root, 0.34, 0.12, 0.4, 0, 0.62, 0.02, COLOR.wing);
  part(root, 0.28, 0.1, 0.22, 0, 0.36, 0.12, COLOR.deep);
  const tail = [
    part(root, 0.06, 0.42, 0.08, -0.08, 0.78, -0.22, COLOR.tail),
    part(root, 0.05, 0.5, 0.07, 0, 0.86, -0.26, COLOR.tailGold),
    part(root, 0.06, 0.4, 0.08, 0.08, 0.76, -0.2, COLOR.tail),
  ];
  const neck = part(root, 0.14, 0.22, 0.14, 0, 0.7, 0.22, COLOR.deep);
  const head = part(root, 0.2, 0.16, 0.2, 0, 0.86, 0.3, COLOR.body);
  const comb = [
    part(root, 0.05, 0.1, 0.05, -0.04, 0.98, 0.28, COLOR.comb),
    part(root, 0.05, 0.14, 0.05, 0.01, 1.02, 0.3, COLOR.comb),
    part(root, 0.05, 0.09, 0.05, 0.06, 0.96, 0.32, COLOR.comb),
  ];
  part(root, 0.1, 0.05, 0.14, 0, 0.82, 0.42, COLOR.beak);
  const wattle = part(root, 0.06, 0.1, 0.04, 0, 0.74, 0.38, COLOR.wattle);
  const legL = part(root, 0.045, 0.28, 0.045, -0.08, 0.16, 0.06, COLOR.leg);
  const legR = part(root, 0.045, 0.28, 0.045, 0.08, 0.16, 0.06, COLOR.leg);
  const facing = { up: Math.PI, down: 0, left: -Math.PI / 2, right: Math.PI / 2 };
  function pose(bird, time) {
    const mode = bird.mode || 'idle';
    root.rotation.y = facing[bird.dir] || 0;
    const flap = Math.sin((bird.phase || 0) * Math.PI * 2);
    body.position.y = 0.48 + (mode === 'walk' ? Math.abs(flap) * 0.03 : 0);
    legL.rotation.x = mode === 'walk' ? flap * 0.7 : 0;
    legR.rotation.x = mode === 'walk' ? -flap * 0.7 : 0;
    head.rotation.x = mode === 'peck' ? 0.85 : 0;
    neck.rotation.x = mode === 'peck' ? 0.4 : 0;
    head.position.y = mode === 'peck' ? 0.7 : 0.86;
    head.position.z = mode === 'peck' ? 0.4 : 0.3;
    for (const tooth of comb) tooth.position.y += 0;
    for (const feather of tail) feather.rotation.x = mode === 'peck' ? 0.2 : -0.35 + Math.sin((time || 0) * 2) * 0.04;
    wattle.scale.y = 1 + Math.sin((time || 0) * 5) * 0.06;
  }
  return { root, pose };
}
