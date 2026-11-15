/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Guacharaca low-poly. Malla original de cajas: cuerpo café oliva, cabeza gris, garganta roja, cola larga. */
import * as T from './three.module.js';

const CACHE = { geo: new Map(), mat: new Map() };
const COLOR = {
  body: '#6e6240',
  olive: '#5c6a38',
  tail: '#4d5830',
  head: '#8d9390',
  throat: '#c44536',
  beak: '#3c342c',
  leg: '#6a4e38',
  wing: '#5a6236',
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
  return geo('b' + w + 'x' + h + 'x' + d, () => new T.BoxGeometry(w, h, d));
}
function part(root, w, h, d, x, y, z, color) {
  const mesh = new T.Mesh(box(w, h, d), mat(color));
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  root.add(mesh);
  return mesh;
}

export function createGuacharaca() {
  const root = new T.Group();
  const body = part(root, 0.34, 0.26, 0.5, 0, 0.34, 0.02, COLOR.body);
  part(root, 0.22, 0.12, 0.28, 0, 0.28, 0.1, COLOR.olive);
  const tail = [
    part(root, 0.06, 0.04, 0.62, -0.08, 0.4, -0.48, COLOR.tail),
    part(root, 0.05, 0.035, 0.74, 0, 0.42, -0.54, COLOR.olive),
    part(root, 0.06, 0.04, 0.58, 0.08, 0.4, -0.46, COLOR.tail),
  ];
  part(root, 0.2, 0.18, 0.2, 0, 0.5, 0.28, COLOR.head);
  part(root, 0.08, 0.06, 0.14, 0, 0.46, 0.4, COLOR.beak);
  const throat = part(root, 0.1, 0.08, 0.08, 0, 0.4, 0.3, COLOR.throat);
  const wingL = part(root, 0.05, 0.16, 0.28, -0.18, 0.36, 0, COLOR.wing);
  const wingR = part(root, 0.05, 0.16, 0.28, 0.18, 0.36, 0, COLOR.wing);
  const legL = part(root, 0.04, 0.22, 0.04, -0.07, 0.12, 0.06, COLOR.leg);
  const legR = part(root, 0.04, 0.22, 0.04, 0.07, 0.12, 0.06, COLOR.leg);
  const facing = { up: Math.PI, down: 0, left: -Math.PI / 2, right: Math.PI / 2 };
  function pose(bird, time) {
    const mode = bird.mode || (bird.perch ? 'perch' : 'walk');
    root.rotation.y = facing[bird.dir] || 0;
    const flap = Math.sin((bird.phase || 0) * Math.PI * 2);
    body.position.y = 0.34 + (mode === 'walk' ? Math.abs(flap) * 0.03 : 0);
    wingL.rotation.z = mode === 'flee' ? -0.9 : mode === 'walk' ? flap * 0.25 : 0.15;
    wingR.rotation.z = mode === 'flee' ? 0.9 : mode === 'walk' ? -flap * 0.25 : -0.15;
    const tucked = mode === 'perch';
    legL.scale.y = tucked ? 0.25 : 1;
    legR.scale.y = tucked ? 0.25 : 1;
    legL.rotation.x = tucked ? 0 : flap * 0.6;
    legR.rotation.x = tucked ? 0 : -flap * 0.6;
    for (const feather of tail) feather.rotation.x = mode === 'flee' ? -0.35 : mode === 'perch' ? 0.45 : 0.1;
    throat.scale.y = 1 + Math.sin(time * 6 + (bird.phase || 0)) * 0.08;
  }
  return { root, pose };
}
