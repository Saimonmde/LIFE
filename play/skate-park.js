/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Pista de la 4 Sur: un solo mesh, colores de vértice, sin fotos.
import * as T from './three.module.js';

// Concreto cálido con más contraste, coping de metal y un verde propio. Sin fotos del escaneo.
const TOP = [0.96, 0.86, 0.72];
const SIDE = [0.40, 0.30, 0.22];
const UNDER = [0.18, 0.13, 0.10];
const SHADOW = [0.12, 0.09, 0.07];
const STRIPE = [0.16, 0.12, 0.09];
const SLAB = [0.78, 0.68, 0.56];
const SLAB_DARK = [0.48, 0.40, 0.32];
const WALL = [0.28, 0.21, 0.16];
const MARK = [0.93, 0.70, 0.18];
const COPING = [0.94, 0.96, 0.98];
const COPING_MID = [0.38, 0.42, 0.46];
const GREEN = [0.10, 0.46, 0.20];
const GREEN_HI = [0.62, 0.90, 0.38];
const GREEN_DARK = [0.04, 0.20, 0.08];

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
  box(pos, col, -mw / 2, mw / 2, 0, 0.08, -mh / 2, mh / 2, SLAB, SLAB_DARK);
  quad(pos, col, [-mw / 2 + 1.2, 0.09, -0.35], [mw / 2 - 1.2, 0.09, -0.35], [mw / 2 - 1.2, 0.09, 0.35], [-mw / 2 + 1.2, 0.09, 0.35], STRIPE);
  for (const ramp of cfg.ramps) {
    if (ramp.kind === 'quarter') quarter(pos, col, ramp);
    else if (ramp.kind === 'funbox') funbox(pos, col, ramp);
    else if (ramp.kind === 'rail') rail(pos, col, ramp);
    else if (ramp.kind === 'ledge') box(pos, col, ramp.x - ramp.w / 2, ramp.x + ramp.w / 2, 0.08, 0.08 + ramp.h, ramp.z - ramp.d / 2, ramp.z + ramp.d / 2, TOP, SIDE);
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
    quad(pos, col, a0, a1, b1, b0, i === segs - 1 ? COPING : TOP);
    quad(pos, col, a0, b0, [b0[0], 0, b0[2]], [a0[0], 0, a0[2]], UNDER);
    quad(pos, col, a1, [a1[0], 0, a1[2]], [b1[0], 0, b1[2]], b1, SIDE);
  }
}

function shadow(pos, col, x0, x1, z0, z1) {
  quad(pos, col, [x0, 0.085, z1], [x1, 0.085, z1], [x1, 0.085, z0], [x0, 0.085, z0], SHADOW);
}
function yawBox(pos, col, x0, x1, y0, y1, z0, z1, top, side, yaw, at) {
  const p = (x, y, z) => spin([x, y, z], yaw || 0, at);
  quad(pos, col, p(x0, y1, z1), p(x1, y1, z1), p(x1, y1, z0), p(x0, y1, z0), top);
  quad(pos, col, p(x0, y0, z0), p(x1, y0, z0), p(x1, y0, z1), p(x0, y0, z1), side);
  quad(pos, col, p(x0, y0, z1), p(x0, y1, z1), p(x0, y1, z0), p(x0, y0, z0), side);
  quad(pos, col, p(x1, y0, z0), p(x1, y1, z0), p(x1, y1, z1), p(x1, y0, z1), side);
  quad(pos, col, p(x0, y0, z0), p(x0, y1, z0), p(x1, y1, z0), p(x1, y0, z0), side);
  quad(pos, col, p(x0, y0, z1), p(x1, y0, z1), p(x1, y1, z1), p(x0, y1, z1), side);
}
function funbox(pos, col, ramp) {
  const x0 = ramp.x - ramp.w / 2, x1 = ramp.x + ramp.w / 2;
  const z0 = ramp.z - ramp.d / 2, z1 = ramp.z + ramp.d / 2;
  const top = 0.08 + ramp.h;
  shadow(pos, col, x0 - 0.18, x1 + 0.18, z0 - 0.18, z1 + 0.18);
  if (ramp.wall === '-z') {
    const lip = Math.min(1.15, ramp.d * 0.26);
    const zk = z1 - lip;
    box(pos, col, x0, x1, 0.08, top, z0, zk, TOP, SIDE);
    quad(pos, col, [x0, top, zk], [x1, top, zk], [x1, 0.08, z1], [x0, 0.08, z1], TOP);
    tri(pos, col, [x0, top, zk], [x0, 0.08, zk], [x0, 0.08, z1], UNDER);
    tri(pos, col, [x1, 0.08, zk], [x1, top, zk], [x1, 0.08, z1], UNDER);
    const mid = (z0 + zk) / 2;
    quad(pos, col, [x0 + 0.35, 0.22, z0 - 0.01], [x1 - 0.35, 0.22, z0 - 0.01], [x1 - 0.35, top - 0.12, z0 - 0.01], [x0 + 0.35, top - 0.12, z0 - 0.01], WALL);
    quad(pos, col, [ramp.x - 0.55, 0.34, z0 - 0.02], [ramp.x + 0.55, 0.34, z0 - 0.02], [ramp.x + 0.16, top - 0.22, z0 - 0.02], [ramp.x - 0.16, top - 0.22, z0 - 0.02], MARK);
    quad(pos, col, [x0 + 0.2, top + 0.012, mid - 0.18], [x1 - 0.2, top + 0.012, mid - 0.18], [x1 - 0.2, top + 0.012, mid + 0.18], [x0 + 0.2, top + 0.012, mid + 0.18], STRIPE);
    return;
  }
  if (ramp.coping === 'long') {
    const nose = Math.min(0.7, ramp.w * 0.08);
    box(pos, col, x0 + nose, x1 - nose, 0.08, top, z0, z1, TOP, SIDE);
    quad(pos, col, [x0, 0.08, z0], [x0 + nose, top, z0], [x0 + nose, top, z1], [x0, 0.08, z1], SIDE);
    quad(pos, col, [x1 - nose, top, z0], [x1, 0.08, z0], [x1, 0.08, z1], [x1 - nose, top, z1], SIDE);
    const railY = top + 0.02, thick = 0.07;
    box(pos, col, x0 + nose, x1 - nose, railY, railY + thick, z0 - 0.02, z0 + 0.08, COPING, COPING_MID);
    box(pos, col, x0 + nose, x1 - nose, railY, railY + thick, z1 - 0.08, z1 + 0.02, COPING, COPING_MID);
    return;
  }
  box(pos, col, x0 + 0.7, x1 - 0.7, 0.08, top, z0, z1, TOP, SIDE);
  quad(pos, col, [x0, 0.08, z0], [x0 + 0.7, top, z0], [x0 + 0.7, top, z1], [x0, 0.08, z1], SIDE);
  quad(pos, col, [x1 - 0.7, top, z0], [x1, 0.08, z0], [x1, 0.08, z1], [x1 - 0.7, top, z1], SIDE);
}

function rail(pos, col, ramp) {
  const green = ramp.color === 'green';
  const topC = green ? GREEN_HI : COPING;
  const sideC = green ? GREEN : COPING_MID;
  const postC = green ? GREEN_DARK : UNDER;
  const y = 0.08 + ramp.h, half = ramp.length / 2;
  const yaw = ramp.yaw || 0;
  const at = [ramp.x, 0, ramp.z];
  shadow(pos, col, ramp.x - half - 0.12, ramp.x + half + 0.12, ramp.z - 0.16, ramp.z + 0.16);
  yawBox(pos, col, ramp.x - half, ramp.x + half, y, y + 0.07, ramp.z - 0.045, ramp.z + 0.045, topC, sideC, yaw, at);
  for (const x of [ramp.x - half + 0.22, ramp.x + half - 0.22]) {
    yawBox(pos, col, x - 0.045, x + 0.045, 0.08, y, ramp.z - 0.04, ramp.z + 0.04, sideC, postC, yaw, at);
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
  const mesh = new T.Mesh(geo, new T.MeshLambertMaterial({ vertexColors: true, flatShading: true }));
  const { x, y, w, h } = cfg.placement;
  mesh.position.set((x + w / 2) * 2, height(x + w / 2, y + h / 2), (y + h / 2) * 2);
  mesh.castShadow = mesh.receiveShadow = true;
  mesh.name = 'skate-4-sur';
  scene.add(mesh);
  cfg.triangles = built.triangles;
  return built.triangles;
}
