/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Caballo criollo procedural. Malla original, sin modelos de terceros.
   Bajo en triángulos, normales suaves sobre facetas, y un nivel lejano. */
import * as T from './three.module.js';
const CACHE = { geo: {}, mats: {}, blanket: null };
const COAT = {
  bay: { body: '#8d4f2e', bodyDeep: '#6e3b22', points: '#1a120e', blaze: '#f3eee6' },
  grey: { body: '#d4cfc7', bodyDeep: '#b7b2aa', points: '#7e7a74', blaze: '#f6f3ee' },
  black: { body: '#1b1b1e', bodyDeep: '#101012', points: '#0c0c0e', blaze: '#242428' },
};

function loft(T, stations, radial) {
  const positions = [];
  const indices = [];
  for (const station of stations) {
    for (let i = 0; i < radial; i++) {
      const angle = (i / radial) * Math.PI * 2 - Math.PI / 2;
      positions.push(Math.cos(angle) * station.rx, station.y + Math.sin(angle) * station.ry, station.z);
    }
  }
  const rings = stations.length;
  for (let s = 0; s < rings - 1; s++) {
    for (let i = 0; i < radial; i++) {
      const next = (i + 1) % radial;
      const a = s * radial + i;
      const b = s * radial + next;
      const c = (s + 1) * radial + next;
      const d = (s + 1) * radial + i;
      indices.push(a, d, c, a, c, b);
    }
  }
  const cap = (ring, outward) => {
    const center = positions.length / 3;
    const station = stations[ring];
    positions.push(0, station.y, station.z);
    const base = ring * radial;
    for (let i = 0; i < radial; i++) {
      const next = (i + 1) % radial;
      if (outward) indices.push(center, base + i, base + next);
      else indices.push(center, base + next, base + i);
    }
  };
  cap(0, false);
  cap(rings - 1, true);
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return geo;
}

function blanketTexture(T) {
  if (CACHE.blanket) return CACHE.blanket;
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 128;
  const g = canvas.getContext('2d');
  g.fillStyle = '#7a2e2a';
  g.fillRect(0, 0, 128, 128);
  g.strokeStyle = '#e2c07a';
  g.lineWidth = 3;
  for (let i = -4; i < 8; i++) {
    g.beginPath();
    g.moveTo(i * 32, 0);
    g.lineTo(i * 32 + 128, 128);
    g.stroke();
    g.beginPath();
    g.moveTo(i * 32, 128);
    g.lineTo(i * 32 + 128, 0);
    g.stroke();
  }
  g.fillStyle = '#c4893a';
  for (let y = 20; y < 128; y += 32) {
    for (let x = 20; x < 128; x += 32) {
      g.beginPath();
      g.moveTo(x, y - 7);
      g.lineTo(x + 7, y);
      g.lineTo(x, y + 7);
      g.lineTo(x - 7, y);
      g.closePath();
      g.fill();
    }
  }
  g.strokeStyle = '#f3e6c8';
  g.lineWidth = 6;
  g.strokeRect(4, 4, 120, 120);
  const tex = new T.CanvasTexture(canvas);
  tex.colorSpace = T.SRGBColorSpace;
  CACHE.blanket = tex;
  return tex;
}

function lambert(T, color, map) {
  return new T.MeshLambertMaterial({ color: color, map: map || null, flatShading: false });
}

function palette(T, coat) {
  const key = COAT[coat] ? coat : 'bay';
  if (CACHE.mats[key]) return CACHE.mats[key];
  const spec = COAT[key];
  const map = blanketTexture(T);
  const mats = {
    body: lambert(T, spec.body),
    deep: lambert(T, spec.bodyDeep),
    points: lambert(T, spec.points),
    blaze: lambert(T, spec.blaze),
    leather: lambert(T, '#6b3a24'),
    leatherDark: lambert(T, '#4a2818'),
    blanket: map ? lambert(T, '#ffffff', map) : lambert(T, '#7a2e2a'),
    fringe: lambert(T, '#e6d2a4'),
    metal: lambert(T, '#8d928f'),
    wood: lambert(T, '#6b4a2c'),
    rope: lambert(T, '#c2a36a'),
    eye: lambert(T, '#1a120e'),
    eyeWhite: lambert(T, '#f4f1ea'),
  };
  CACHE.mats[key] = mats;
  return mats;
}

function geometries(T, low) {
  const key = low ? 'low' : 'high';
  if (CACHE.geo[key]) return CACHE.geo[key];
  const radial = low ? 6 : 8;
  const neckN = low ? 5 : 6;
  const body = [
    { z: -0.98, y: 1.12, rx: 0.11, ry: 0.11 },
    { z: -0.74, y: 1.28, rx: 0.23, ry: 0.26 },
    { z: -0.46, y: 1.36, rx: 0.27, ry: 0.30 },
    { z: -0.14, y: 1.40, rx: 0.23, ry: 0.28 },
    { z: 0.16, y: 1.42, rx: 0.21, ry: 0.28 },
    { z: 0.42, y: 1.34, rx: 0.25, ry: 0.32 },
    { z: 0.66, y: 1.22, rx: 0.23, ry: 0.32 },
    { z: 0.84, y: 1.06, rx: 0.15, ry: 0.20 },
  ];
  const neck = [];
  for (let i = 0; i < neckN; i++) {
    const t = i / (neckN - 1);
    const arch = Math.sin(t * Math.PI) * 0.04;
    neck.push({
      z: t * 0.58 + arch,
      y: t * 0.50 + Math.sin(t * Math.PI * 0.5) * 0.06,
      rx: 0.15 - t * 0.05,
      ry: 0.17 - t * 0.06,
    });
  }
  const head = [
    { z: 0.00, y: 0.02, rx: 0.10, ry: 0.12 },
    { z: 0.14, y: 0.03, rx: 0.11, ry: 0.13 },
    { z: 0.28, y: 0.00, rx: 0.09, ry: 0.10 },
    { z: 0.40, y: -0.05, rx: 0.07, ry: 0.075 },
    { z: 0.50, y: -0.09, rx: 0.055, ry: 0.055 },
  ];
  const upperH = 0.56, lowerH = 0.44;
  const geo = {
    body: loft(T, low ? body.filter((_, i) => i % 2 === 0 || i === body.length - 1) : body, radial),
    neck: loft(T, neck, low ? 5 : 7),
    head: loft(T, head, low ? 5 : 7),
    ear: new T.ConeGeometry(0.045, 0.18, 4),
    eye: new T.SphereGeometry(0.038, low ? 5 : 6, low ? 4 : 5),
    upper: new T.CylinderGeometry(low ? 0.07 : 0.085, 0.055, upperH, low ? 5 : 7),
    lower: new T.CylinderGeometry(0.042, 0.034, lowerH, low ? 5 : 6),
    hoof: new T.BoxGeometry(0.09, 0.1, 0.11),
    upperH: upperH,
    lowerH: lowerH,
  };
  CACHE.geo[key] = geo;
  return geo;
}

function add(group, geometry, material, role, x, y, z) {
  const mesh = new T.Mesh(geometry, material);
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  if (role) mesh.userData.role = role;
  group.add(mesh);
  return mesh;
}

function leg(T, geo, mats, low, side, kind) {
  const upperH = geo.upperH, lowerH = geo.lowerH;
  const hip = new T.Group();
  hip.name = kind + side;
  hip.userData.kind = kind;
  hip.userData.leg = (side < 0 ? 'l' : 'r') + (kind === 'hind' ? 'h' : 'f');
  const upper = add(hip, geo.upper, kind === 'hind' ? mats.body : mats.body, 'body', 0, -upperH / 2, 0);
  upper.userData.role = 'body';
  const knee = new T.Group();
  knee.position.y = -upperH;
  hip.add(knee);
  add(knee, geo.lower, mats.points, 'points', 0, -lowerH / 2, 0);
  const hoof = add(knee, geo.hoof, mats.points, 'points', 0, -lowerH - 0.05, 0.01);
  hoof.scale.z = 1.05;
  hip.userData.knee = knee;
  if (!low && kind === 'fore') {
    const chest = add(hip, new T.BoxGeometry(0.06, 0.16, 0.08), mats.deep, 'deep', side * -0.02, -0.08, 0.02);
    chest.rotation.z = side * 0.2;
  }
  return hip;
}

function mane(T, mats, low) {
  const group = new T.Group();
  const count = low ? 3 : 7;
  const locks = [];
  for (let i = 0; i < count; i++) {
    const t = i / (count - 1 || 1);
    const lock = new T.Group();
    const length = 0.16 + t * 0.22;
    const mesh = add(lock, new T.BoxGeometry(0.05, length, 0.07), mats.points, 'points', 0.04, -length / 2, 0);
    mesh.rotation.z = -0.35;
    lock.position.set(0.02, 0.16 + t * 0.34, 0.06 + t * 0.42);
    group.add(lock);
    locks.push(lock);
  }
  group.userData.locks = locks;
  return group;
}

function tail(T, mats, low) {
  const root = new T.Group();
  const lengths = low ? [0.34, 0.4] : [0.22, 0.26, 0.28, 0.3];
  const segments = [];
  let parent = root;
  lengths.forEach((len, i) => {
    const seg = new T.Group();
    const wide = Math.max(0.035, 0.09 - i * 0.015);
    add(seg, new T.BoxGeometry(wide, len, wide * 0.7), mats.points, 'points', 0, -len * 0.5, -0.02);
    if (i > 0) seg.position.y = -lengths[i - 1];
    parent.add(seg);
    segments.push(seg);
    parent = seg;
  });
  root.userData.segments = segments;
  return root;
}

function tack(T, mats, low) {
  const group = new T.Group();
  const blanket = add(group, new T.BoxGeometry(0.62, 0.06, 0.78), mats.blanket, 'blanket', 0, 1.56, 0.02);
  blanket.rotation.x = -0.04;
  add(group, new T.BoxGeometry(0.36, 0.1, 0.42), mats.leather, 'leather', 0, 1.64, 0.02);
  add(group, new T.BoxGeometry(0.28, 0.1, 0.12), mats.leatherDark, 'leatherDark', 0, 1.68, 0.24);
  add(group, new T.BoxGeometry(0.34, 0.12, 0.1), mats.leatherDark, 'leatherDark', 0, 1.7, -0.18);
  if (!low) {
    for (const side of [-1, 1]) {
      add(group, new T.BoxGeometry(0.03, 0.55, 0.04), mats.leather, 'leather', side * 0.2, 1.28, 0.05);
      const iron = add(group, new T.TorusGeometry(0.06, 0.012, 4, 8), mats.metal, 'metal', side * 0.24, 0.98, 0.08);
      iron.rotation.y = Math.PI / 2;
    }
    for (let i = 0; i < 7; i++) {
      const z = -0.32 + i * 0.1;
      add(group, new T.BoxGeometry(0.03, 0.12, 0.04), mats.fringe, 'fringe', -0.3, 1.46, z);
      add(group, new T.BoxGeometry(0.03, 0.12, 0.04), mats.fringe, 'fringe', 0.3, 1.46, z);
    }
    add(group, new T.BoxGeometry(0.5, 0.04, 0.08), mats.leatherDark, 'leatherDark', 0, 1.05, 0.2);
  }
  return group;
}

function bridle(T, mats) {
  const group = new T.Group();
  add(group, new T.BoxGeometry(0.22, 0.025, 0.025), mats.leather, 'leather', 0, 0.06, 0.16);
  add(group, new T.BoxGeometry(0.025, 0.12, 0.025), mats.leather, 'leather', -0.09, -0.02, 0.2);
  add(group, new T.BoxGeometry(0.025, 0.12, 0.025), mats.leather, 'leather', 0.09, -0.02, 0.2);
  add(group, new T.BoxGeometry(0.12, 0.02, 0.02), mats.metal, 'metal', 0, -0.1, 0.48);
  return group;
}

function buildRig(T, mats, low) {
  const geo = geometries(T, low);
  const rig = new T.Group();
  add(rig, geo.body, mats.body, 'body', 0, 0, 0);
  const neck = new T.Group();
  neck.position.set(0, 1.40, 0.28);
  rig.add(neck);
  add(neck, geo.neck, mats.body, 'body', 0, 0, 0);
  const maneGroup = mane(T, mats, low);
  neck.add(maneGroup);
  const head = new T.Group();
  const poll = low ? { z: 0.5, y: 0.46 } : { z: 0.58, y: 0.56 };
  head.position.set(0, poll.y, poll.z);
  neck.add(head);
  add(head, geo.head, mats.body, 'body', 0, 0, 0);
  const blaze = add(head, new T.BoxGeometry(0.045, 0.16, 0.08), mats.blaze, 'blaze', 0, -0.01, 0.3);
  blaze.rotation.x = 0.5;
  for (const side of [-1, 1]) {
    const ear = add(head, geo.ear, mats.body, 'body', side * 0.06, 0.12, 0.04);
    ear.rotation.z = side * -0.35;
    ear.rotation.x = -0.2;
    const eye = add(head, geo.eye, mats.eye, 'eye', side * 0.09, 0.02, 0.18);
    if (!low) add(head, new T.SphereGeometry(0.012, 4, 3), mats.eyeWhite, 'eyeWhite', side * 0.1, 0.03, 0.2);
  }
  if (!low) {
    add(head, new T.BoxGeometry(0.04, 0.03, 0.04), mats.points, 'points', -0.025, -0.1, 0.5);
    add(head, new T.BoxGeometry(0.04, 0.03, 0.04), mats.points, 'points', 0.025, -0.1, 0.5);
    head.add(bridle(T, mats));
  }
  const tailGroup = tail(T, mats, low);
  tailGroup.position.set(0, 1.22, -0.92);
  rig.add(tailGroup);
  const legs = {};
  for (const side of [-1, 1]) {
    const fore = leg(T, geo, mats, low, side, 'fore');
    fore.position.set(side * 0.18, geo.upperH + geo.lowerH + 0.1, 0.5);
    rig.add(fore);
    legs[(side < 0 ? 'l' : 'r') + 'f'] = fore;
    const hind = leg(T, geo, mats, low, side, 'hind');
    hind.position.set(side * 0.18, geo.upperH + geo.lowerH + 0.1, -0.58);
    rig.add(hind);
    legs[(side < 0 ? 'l' : 'r') + 'h'] = hind;
  }
  rig.add(tack(T, mats, low));
  rig.userData.bones = { neck: neck, head: head, mane: maneGroup, tail: tailGroup, legs: legs, blaze: blaze };
  return rig;
}

function hitch(T, mats) {
  const group = new T.Group();
  group.position.set(-0.72, 0, 0.05);
  add(group, new T.CylinderGeometry(0.045, 0.055, 1.15, 6), mats.wood, 'wood', 0, 0.58, 0);
  add(group, new T.BoxGeometry(0.28, 0.06, 0.08), mats.wood, 'wood', 0, 1.12, 0);
  const rope = add(group, new T.CylinderGeometry(0.012, 0.012, 1, 5), mats.rope, 'rope', 0.35, 0.55, 0.35);
  rope.scale.y = 0.95;
  rope.rotation.z = 0.7;
  rope.rotation.x = -0.4;
  return group;
}

export function countTriangles(object) {
  let count = 0;
  object.traverse(mesh => {
    if (!mesh.isMesh || !mesh.geometry) return;
    const geo = mesh.geometry;
    count += geo.index ? geo.index.count / 3 : geo.attributes.position.count / 3;
  });
  return count;
}

function paint(root, mats, coat) {
  root.traverse(mesh => {
    if (!mesh.isMesh) return;
    const role = mesh.userData.role;
    if (role && mats[role]) mesh.material = mats[role];
    if (role === 'blaze') mesh.visible = coat !== 'black';
  });
}

function poseRig(rig, gait, phase, time) {
  const bones = rig.userData.bones;
  if (!bones) return;
  const api = globalThis.Caballo;
  const pose = (leg) => (api && api.legPose ? api.legPose(gait, phase, leg) : { swing: 0, lift: 0, knee: 0.15 });
  let lift = 0;
  for (const [name, hip] of Object.entries(bones.legs)) {
    const leg = pose(name);
    const hind = name === 'lh' || name === 'rh';
    hip.rotation.x = -leg.swing * 0.85;
    hip.userData.knee.rotation.x = (hind ? -1 : 1) * leg.knee * 0.75;
    lift += leg.lift;
  }
  const idle = gait === 'idle';
  bones.neck.rotation.x = idle ? -0.12 + Math.sin(time * 1.25) * 0.05 : gait === 'gallop' ? -0.38 + Math.sin(phase * Math.PI * 2) * 0.08 : -0.18;
  bones.head.rotation.x = idle ? Math.sin(time * 1.25 + 0.6) * 0.1 : gait === 'gallop' ? -0.12 : 0.02;
  bones.head.rotation.y = idle ? Math.sin(time * 0.7) * 0.12 : 0;
  const segments = bones.tail.userData.segments || [];
  segments.forEach((seg, i) => {
    const swish = Math.sin(time * (idle ? 1.4 : 2.2) + i * 0.5);
    seg.rotation.y = swish * (gait === 'gallop' ? 0.28 : 0.2);
    seg.rotation.x = -0.25 - i * 0.06 + (gait === 'gallop' ? -0.25 : 0);
  });
  for (const lock of bones.mane.userData.locks || []) {
    lock.rotation.z = Math.sin(time * 2.1 + lock.position.z) * (gait === 'gallop' ? 0.18 : 0.05);
  }
  const bob = idle ? Math.sin(time * 1.7) * 0.012 : gait === 'gallop' ? Math.sin(phase * Math.PI * 2) * 0.035 + lift * 0.012 : Math.sin(phase * Math.PI * 2) * 0.015;
  rig.position.y = bob;
  rig.scale.y = idle ? 1 + Math.sin(time * 1.7) * 0.012 : 1;
  rig.rotation.x = gait === 'gallop' ? Math.sin(phase * Math.PI * 2) * 0.05 : 0;
}

export function createHorse(T, options) {
  const coat = COAT[options && options.coat] ? options.coat : 'bay';
  const mats = palette(T, coat);
  const root = new T.Group();
  root.name = 'caballo';
  const high = buildRig(T, mats, false);
  const low = buildRig(T, mats, true);
  const lod = new T.LOD();
  lod.addLevel(high, 0);
  lod.addLevel(low, 48);
  root.add(lod);
  const post = hitch(T, mats);
  root.add(post);
  paint(root, mats, coat);
  const horse = {
    root: root,
    coat: coat,
    detail: countTriangles(high) + countTriangles(post),
    far: countTriangles(low) + countTriangles(post),
    setCoat(next) {
      const key = COAT[next] ? next : 'bay';
      horse.coat = key;
      paint(root, palette(T, key), key);
    },
    update(state) {
      const time = state && state.time || 0;
      const gait = state && state.gait || 'idle';
      const rate = gait === 'gallop' ? 2.35 : gait === 'trot' ? 1.7 : gait === 'walk' ? 1.05 : 0.45;
      const phase = state && state.phase != null ? state.phase : (time * rate) % 1;
      poseRig(high, gait, phase, time);
      poseRig(low, gait, phase, time);
      post.visible = !!(state && state.tethered);
    },
  };
  horse.update({ gait: 'idle', phase: 0.2, time: 0, tethered: false });
  return horse;
}

export function poseRider(group, mounted) {
  if (!group) return;
  const limbs = [];
  group.children.forEach(child => {
    if (child.userData && (child.userData.limb === 'leg' || child.userData.limb === 'arm')) limbs.push(child);
  });
  for (const limb of limbs) {
    if (!limb.userData.rest) limb.userData.rest = { x: limb.position.x, y: limb.position.y, z: limb.position.z };
    const rest = limb.userData.rest;
    const side = rest.x < 0 ? -1 : 1;
    if (!mounted) {
      limb.position.set(rest.x, rest.y, rest.z);
      limb.rotation.set(0, 0, 0);
      continue;
    }
    if (limb.userData.limb === 'leg') {
      limb.position.set(rest.x + side * 0.06, rest.y + 0.05, rest.z + 0.2);
      limb.rotation.set(1.2, 0, side * -0.35);
    } else {
      limb.position.set(rest.x * 0.62, rest.y - 0.02, rest.z + 0.26);
      limb.rotation.set(1.0, side * 0.15, side * -0.2);
    }
  }
}
