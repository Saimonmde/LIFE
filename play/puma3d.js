/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Puma concolor, malla original con color por vértice. Sin textura de foto. */
import * as T from './three.module.js';

const TAU = Math.PI * 2;

function hex(value) {
  const color = new T.Color(value);
  return [color.r, color.g, color.b];
}

function pushBox(positions, colors, w, h, d, x, y, z, faceColors) {
  const hw = w / 2, hh = h / 2, hd = d / 2;
  const corners = [
    [-hw, -hh, -hd], [hw, -hh, -hd], [hw, hh, -hd], [-hw, hh, -hd],
    [-hw, -hh, hd], [hw, -hh, hd], [hw, hh, hd], [-hw, hh, hd],
  ];
  const faces = [
    [0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7],
    [1, 5, 6, 2], [3, 2, 6, 7], [4, 5, 1, 0],
  ];
  for (let f = 0; f < faces.length; f++) {
    const ids = faces[f];
    const color = faceColors[f] || faceColors[0];
    const quad = ids.map((id) => corners[id]);
    const tris = [0, 1, 2, 0, 2, 3];
    for (const index of tris) {
      const p = quad[index];
      positions.push(p[0] + x, p[1] + y, p[2] + z);
      colors.push(color[0], color[1], color[2]);
    }
  }
}

function tones(base, belly, dark) {
  const top = hex(belly);
  const mid = hex(base);
  const low = hex(dark);
  return [mid, mid, low, mid, top, low];
}

function meshFrom(positions, colors) {
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
  geo.setAttribute('color', new T.Float32BufferAttribute(colors, 3));
  geo.computeVertexNormals();
  const material = new T.MeshLambertMaterial({ vertexColors: true });
  const mesh = new T.Mesh(geo, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

export function createPuma() {
  const root = new T.Group();
  const bodyP = [], bodyC = [];
  const coat = tones('#c47a3a', '#f3d7a8', '#6a3818');
  const spine = tones('#8a4e22', '#e7c49a', '#3e2414');
  pushBox(bodyP, bodyC, 0.46, 0.38, 1.15, 0, 0.62, 0.02, coat);
  pushBox(bodyP, bodyC, 0.28, 0.12, 0.72, 0, 0.84, -0.02, spine);
  pushBox(bodyP, bodyC, 0.4, 0.16, 0.7, 0, 0.46, 0.04, tones('#f0d2a4', '#f7e6c8', '#b88858'));
  const chest = new T.Group();
  chest.add(meshFrom(bodyP, bodyC));
  const hipP = [], hipC = [];
  pushBox(hipP, hipC, 0.34, 0.28, 0.36, 0, 0.58, -0.48, coat);
  chest.add(meshFrom(hipP, hipC));
  root.add(chest);

  const head = new T.Group();
  const headP = [], headC = [];
  pushBox(headP, headC, 0.32, 0.28, 0.36, 0, 0, 0, coat);
  pushBox(headP, headC, 0.18, 0.12, 0.16, 0, -0.02, 0.24, tones('#f4efe6', '#fff8ee', '#d9cbb8'));
  pushBox(headP, headC, 0.08, 0.06, 0.08, 0, 0.02, 0.32, tones('#2a211c', '#3a3028', '#1a120e'));
  pushBox(headP, headC, 0.1, 0.08, 0.06, -0.1, 0.04, 0.16, tones('#1c140f', '#2a2018', '#120e0c'));
  pushBox(headP, headC, 0.1, 0.08, 0.06, 0.1, 0.04, 0.16, tones('#1c140f', '#2a2018', '#120e0c'));
  head.add(meshFrom(headP, headC));
  const earGeo = [], earCol = [];
  pushBox(earGeo, earCol, 0.08, 0.12, 0.04, -0.1, 0.2, -0.02, tones('#2a211c', '#c47a3a', '#1a120e'));
  pushBox(earGeo, earCol, 0.08, 0.12, 0.04, 0.1, 0.2, -0.02, tones('#2a211c', '#c47a3a', '#1a120e'));
  head.add(meshFrom(earGeo, earCol));
  const eye = new T.Mesh(new T.BoxGeometry(0.05, 0.04, 0.02), new T.MeshLambertMaterial({ color: '#e2b23c', emissive: '#6a4a12', emissiveIntensity: 0.35 }));
  eye.castShadow = false;
  const eyeL = eye.clone();
  eye.position.set(-0.07, 0.04, 0.18);
  eyeL.position.set(0.07, 0.04, 0.18);
  head.add(eye, eyeL);
  head.position.set(0, 0.78, 0.62);
  root.add(head);

  const tail = new T.Group();
  const tailP = [], tailC = [];
  pushBox(tailP, tailC, 0.1, 0.1, 0.55, 0, 0, -0.28, tones('#a86428', '#e7c49a', '#5a3014'));
  pushBox(tailP, tailC, 0.12, 0.12, 0.16, 0, 0.02, -0.58, tones('#1a120e', '#2c241c', '#0e0c0a'));
  tail.add(meshFrom(tailP, tailC));
  tail.position.set(0, 0.7, -0.55);
  root.add(tail);

  const legs = [];
  const paws = [[-0.16, 0.22, 0.32], [0.16, 0.22, 0.32], [-0.16, 0.22, -0.32], [0.16, 0.22, -0.32]];
  for (const [x, y, z] of paws) {
    const legP = [], legC = [];
    pushBox(legP, legC, 0.12, 0.36, 0.12, 0, 0.12, 0, tones('#8a4e22', '#c47a3a', '#3e2414'));
    pushBox(legP, legC, 0.14, 0.06, 0.16, 0, -0.02, 0.02, tones('#2a211c', '#3a3028', '#1a120e'));
    const leg = new T.Group();
    leg.add(meshFrom(legP, legC));
    leg.position.set(x, y, z);
    root.add(leg);
    legs.push(leg);
  }

  const blob = new T.Mesh(
    new T.CircleGeometry(0.72, 14),
    new T.MeshBasicMaterial({ color: '#1a140c', transparent: true, opacity: 0.28, depthWrite: false })
  );
  blob.rotation.x = -Math.PI / 2;
  blob.position.y = 0.04;
  blob.castShadow = false;
  root.add(blob);

  const mark = new T.Mesh(
    new T.BoxGeometry(0.16, 0.28, 0.06),
    new T.MeshBasicMaterial({ color: '#e23b2f' })
  );
  mark.position.set(0, 1.35, 0.2);
  mark.visible = false;
  root.add(mark);

  root.scale.set(1.7, 1.7, 1.7);
  function pose(animal, time) {
    const mode = animal.mode || 'wander';
    const moving = mode === 'wander' || mode === 'stalk' || mode === 'charge';
    const pace = mode === 'charge' ? 11 : mode === 'stalk' ? 4.2 : 3;
    const swing = moving ? Math.sin((time || 0) * pace) : 0;
    const crouch = mode === 'warn' || mode === 'stalk' ? 0.12 : mode === 'charge' ? 0.06 : 0;
    chest.position.y = -crouch;
    chest.rotation.x = mode === 'charge' ? 0.18 : mode === 'warn' ? -0.08 : 0;
    head.position.y = 0.78 - crouch;
    head.rotation.x = mode === 'warn' ? -0.25 : mode === 'attack' ? 0.35 : 0.05;
    head.rotation.z = mode === 'warn' ? Math.sin((time || 0) * 18) * 0.08 : 0;
    tail.rotation.x = -0.5 + Math.sin((time || 0) * 2.2) * 0.18;
    tail.rotation.z = Math.sin((time || 0) * 1.6) * 0.35;
    legs.forEach((leg, i) => {
      leg.rotation.x = swing * (i % 2 ? 0.55 : -0.55);
    });
    mark.visible = !!(animal.growl || mode === 'warn' || mode === 'charge');
    mark.position.y = 1.28 + Math.sin((time || 0) * 8) * 0.06;
    const face = { up: Math.PI, down: 0, left: -Math.PI / 2, right: Math.PI / 2 };
    root.rotation.y = face[animal.dir] || 0;
  }
  return { root, pose };
}

export const PUMA_TURN = TAU;
