/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Pista de la 4 Sur: un solo mesh, colores de vértice, sin fotos.
import * as T from './three.module.js';

const PAD = [0.86, 0.83, 0.76];
const PAD_DARK = [0.62, 0.60, 0.56];
const CONCRETE = [0.78, 0.74, 0.68];
const SHADE = [0.42, 0.40, 0.38];
const RAIL = [0.22, 0.24, 0.27];

function tri(pos, col, a, b, c, color) {
  pos.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]);
  for (let i = 0; i < 3; i++) col.push(color[0], color[1], color[2]);
}
function quad(pos, col, a, b, c, d, color) {
  tri(pos, col, a, b, c, color);
  tri(pos, col, a, c, d, color);
}
function box(pos, col, x0, x1, y0, y1, z0, z1, top, side) {
  quad(pos, col, [x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0], top);
  quad(pos, col, [x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1], side);
  quad(pos, col, [x0, y0, z1], [x0, y1, z1], [x0, y1, z0], [x0, y0, z0], side);
  quad(pos, col, [x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1], side);
  quad(pos, col, [x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [x1, y0, z0], side);
  quad(pos, col, [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1], side);
}
function spin(p, yaw, at) {
  const c = Math.cos(yaw), s = Math.sin(yaw);
  const x = p[0] - at[0], z = p[2] - at[2];
  return [at[0] + x * c - z * s, p[1], at[2] + x * s + z * c];
}

export function skateArrays(cfg) {
  const pos = [], col = [];
  const [mw, mh] = cfg.placement.meters;
  box(pos, col, -mw / 2, mw / 2, 0, 0.08, -mh / 2, mh / 2, PAD, PAD_DARK);
  quad(pos, col, [-mw / 2 + 1.2, 0.09, -0.35], [mw / 2 - 1.2, 0.09, -0.35], [mw / 2 - 1.2, 0.09, 0.35], [-mw / 2 + 1.2, 0.09, 0.35], SHADE);
  for (const ramp of cfg.ramps) {
    if (ramp.kind === 'quarter') quarter(pos, col, ramp);
    else if (ramp.kind === 'funbox') funbox(pos, col, ramp);
    else if (ramp.kind === 'rail') rail(pos, col, ramp);
    else if (ramp.kind === 'ledge') box(pos, col, ramp.x - ramp.w / 2, ramp.x + ramp.w / 2, 0.08, 0.08 + ramp.h, ramp.z - ramp.d / 2, ramp.z + ramp.d / 2, CONCRETE, SHADE);
  }
  return { positions: pos, colors: col, triangles: pos.length / 9 };
}

function quarter(pos, col, ramp) {
  const segs = 5, r = ramp.radius, half = ramp.length / 2;
  const at = [ramp.x, 0, ramp.z];
  const ring = (i) => {
    const t = (i / segs) * Math.PI / 2;
    const z = -r * (1 - Math.cos(t));
    const y = r * Math.sin(t);
    return [spin([-half, y, z], ramp.yaw || 0, [0, 0, 0]), spin([half, y, z], ramp.yaw || 0, [0, 0, 0])];
  };
  for (let i = 0; i < segs; i++) {
    const [a0, a1] = ring(i).map(p => [p[0] + at[0], p[1], p[2] + at[2]]);
    const [b0, b1] = ring(i + 1).map(p => [p[0] + at[0], p[1], p[2] + at[2]]);
    quad(pos, col, a0, a1, b1, b0, i % 2 ? CONCRETE : PAD);
    quad(pos, col, a0, b0, [b0[0], 0, b0[2]], [a0[0], 0, a0[2]], SHADE);
    quad(pos, col, a1, [a1[0], 0, a1[2]], [b1[0], 0, b1[2]], b1, SHADE);
  }
}

function funbox(pos, col, ramp) {
  const x0 = ramp.x - ramp.w / 2, x1 = ramp.x + ramp.w / 2;
  const z0 = ramp.z - ramp.d / 2, z1 = ramp.z + ramp.d / 2;
  const top = 0.08 + ramp.h;
  box(pos, col, x0 + 0.7, x1 - 0.7, 0.08, top, z0, z1, CONCRETE, SHADE);
  quad(pos, col, [x0, 0.08, z0], [x0 + 0.7, top, z0], [x0 + 0.7, top, z1], [x0, 0.08, z1], PAD);
  quad(pos, col, [x1 - 0.7, top, z0], [x1, 0.08, z0], [x1, 0.08, z1], [x1 - 0.7, top, z1], PAD);
}

function rail(pos, col, ramp) {
  const y = 0.08 + ramp.h, half = ramp.length / 2;
  box(pos, col, ramp.x - half, ramp.x + half, y, y + 0.06, ramp.z - 0.04, ramp.z + 0.04, RAIL, RAIL);
  for (const x of [ramp.x - half + 0.3, ramp.x + half - 0.3]) {
    box(pos, col, x - 0.04, x + 0.04, 0.08, y, ramp.z - 0.04, ramp.z + 0.04, RAIL, SHADE);
  }
}

export function placeSkatePark(scene, height) {
  const cfg = window.SKATE_4_SUR;
  if (!cfg) return 0;
  const built = skateArrays(cfg);
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.Float32BufferAttribute(built.positions, 3));
  geo.setAttribute('color', new T.Float32BufferAttribute(built.colors, 3));
  geo.computeVertexNormals();
  const mesh = new T.Mesh(geo, new T.MeshLambertMaterial({ vertexColors: true }));
  const { x, y, w, h } = cfg.placement;
  mesh.position.set((x + w / 2) * 2, height(x + w / 2, y + h / 2), (y + h / 2) * 2);
  mesh.castShadow = mesh.receiveShadow = true;
  mesh.name = 'skate-4-sur';
  scene.add(mesh);
  cfg.triangles = built.triangles;
  return built.triangles;
}
