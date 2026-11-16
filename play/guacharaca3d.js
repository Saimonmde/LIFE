/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Guacharaca: gallina delgada, cola larga, café oliva, cabeza gris y garganta roja.
   Malla original. El escudo verde es fauna protegida. */
import * as T from './three.module.js';

const CACHE = { geo: new Map(), mat: new Map(), leaf: null };
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
function leafMark(Tlib) {
  if (!CACHE.leaf && typeof document !== 'undefined') {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 64;
    const g = canvas.getContext('2d');
    g.fillStyle = '#1e6b38';
    g.beginPath();
    g.arc(32, 32, 28, 0, Math.PI * 2);
    g.fill();
    g.strokeStyle = '#d9f5c8';
    g.lineWidth = 3;
    g.stroke();
    g.fillStyle = '#d9f5c8';
    g.beginPath();
    g.ellipse(32, 30, 9, 16, -0.5, 0, Math.PI * 2);
    g.fill();
    g.strokeStyle = '#1e6b38';
    g.beginPath();
    g.moveTo(28, 40);
    g.lineTo(36, 20);
    g.stroke();
    const tex = new Tlib.CanvasTexture(canvas);
    tex.colorSpace = Tlib.SRGBColorSpace;
    CACHE.leaf = tex;
  }
  return CACHE.leaf;
}

export function createGuacharaca() {
  const root = new T.Group();
  const body = part(root, 0.46, 0.34, 0.62, 0, 0.4, 0.02, COLOR.body);
  part(root, 0.3, 0.16, 0.28, 0, 0.32, 0.16, COLOR.olive);
  const tail = [
    part(root, 0.07, 0.045, 0.78, -0.1, 0.48, -0.58, COLOR.tail),
    part(root, 0.06, 0.04, 0.92, 0, 0.52, -0.66, COLOR.olive),
    part(root, 0.07, 0.045, 0.74, 0.1, 0.48, -0.56, COLOR.tail),
  ];
  const neck = part(root, 0.12, 0.16, 0.12, 0, 0.58, 0.24, COLOR.body);
  const head = part(root, 0.22, 0.2, 0.22, 0, 0.72, 0.32, COLOR.head);
  part(root, 0.1, 0.06, 0.16, 0, 0.66, 0.46, COLOR.beak);
  const throat = part(root, 0.12, 0.1, 0.08, 0, 0.58, 0.38, COLOR.throat);
  const wingL = part(root, 0.06, 0.2, 0.34, -0.24, 0.42, 0, COLOR.wing);
  const wingR = part(root, 0.06, 0.2, 0.34, 0.24, 0.42, 0, COLOR.wing);
  const legL = part(root, 0.045, 0.26, 0.045, -0.09, 0.14, 0.08, COLOR.leg);
  const legR = part(root, 0.045, 0.26, 0.045, 0.09, 0.14, 0.08, COLOR.leg);
  part(root, 0.12, 0.03, 0.08, -0.09, 0.02, 0.1, COLOR.leg);
  part(root, 0.12, 0.03, 0.08, 0.09, 0.02, 0.1, COLOR.leg);
  const mark = leafMark(T);
  let badge = null;
  if (mark) {
    badge = new T.Sprite(new T.SpriteMaterial({ map: mark, transparent: true, depthWrite: false }));
    badge.position.set(0, 1.15, 0);
    badge.scale.set(0.42, 0.42, 1);
    root.add(badge);
  }
  const facing = { up: Math.PI, down: 0, left: -Math.PI / 2, right: Math.PI / 2 };
  function pose(bird, time) {
    const mode = bird.mode || (bird.perch ? 'perch' : 'walk');
    root.rotation.y = facing[bird.dir] || 0;
    const flap = Math.sin((bird.phase || 0) * Math.PI * 2);
    body.position.y = 0.4 + (mode === 'walk' ? Math.abs(flap) * 0.03 : 0);
    const flying = mode === 'fly' || mode === 'flee';
    wingL.rotation.z = flying ? -1.15 : mode === 'walk' ? flap * 0.3 : 0.2;
    wingR.rotation.z = flying ? 1.15 : mode === 'walk' ? -flap * 0.3 : -0.2;
    const tucked = mode === 'perch';
    legL.scale.y = tucked || flying ? 0.35 : 1;
    legR.scale.y = tucked || flying ? 0.35 : 1;
    legL.rotation.x = tucked || flying ? 0.4 : flap * 0.7;
    legR.rotation.x = tucked || flying ? 0.4 : -flap * 0.7;
    for (const feather of tail) feather.rotation.x = flying ? -0.45 : mode === 'perch' ? 0.5 : 0.12;
    head.rotation.x = mode === 'peck' ? 0.9 : 0;
    neck.rotation.x = mode === 'peck' ? 0.45 : 0;
    head.position.z = mode === 'peck' ? 0.4 : 0.32;
    head.position.y = mode === 'peck' ? 0.52 : 0.72;
    throat.scale.y = 1 + Math.sin((time || 0) * 6 + (bird.phase || 0)) * 0.08;
    if (badge) badge.position.y = mode === 'peck' ? 0.95 : 1.15;
  }
  return { root, pose };
}
