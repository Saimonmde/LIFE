/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Gavilán caminero (Rupornis magnirostris). Malla original, alas que baten. */
import * as T from './three.module.js';

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
    for (const index of [0, 1, 2, 0, 2, 3]) {
      const p = quad[index];
      positions.push(p[0] + x, p[1] + y, p[2] + z);
      colors.push(color[0], color[1], color[2]);
    }
  }
}

function tones(base, light, dark) {
  return [hex(base), hex(base), hex(dark), hex(base), hex(light), hex(dark)];
}

function meshFrom(positions, colors) {
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
  geo.setAttribute('color', new T.Float32BufferAttribute(colors, 3));
  geo.computeVertexNormals();
  const mesh = new T.Mesh(geo, new T.MeshLambertMaterial({ vertexColors: true }));
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function wing() {
  const positions = [], colors = [];
  pushBox(positions, colors, 0.7, 0.05, 0.28, 0.36, 0, 0, tones('#7a4a28', '#a86840', '#4a2c16'));
  pushBox(positions, colors, 0.28, 0.04, 0.18, 0.78, 0, 0.02, tones('#5c3a22', '#8a5430', '#3a2414'));
  pushBox(positions, colors, 0.5, 0.03, 0.16, 0.3, -0.03, 0, tones('#e6d2a8', '#f3e6c8', '#b89870'));
  return meshFrom(positions, colors);
}

export function createGavilan() {
  const root = new T.Group();
  const bodyP = [], bodyC = [];
  pushBox(bodyP, bodyC, 0.22, 0.18, 0.42, 0, 0, 0.02, tones('#7a4a28', '#c4a574', '#4a2c16'));
  pushBox(bodyP, bodyC, 0.16, 0.08, 0.28, 0, -0.08, 0.04, tones('#e6d2a8', '#f4e7cc', '#b89870'));
  root.add(meshFrom(bodyP, bodyC));

  const head = new T.Group();
  const headP = [], headC = [];
  pushBox(headP, headC, 0.14, 0.12, 0.16, 0, 0, 0, tones('#6e5438', '#cbb89a', '#3e2c1c'));
  pushBox(headP, headC, 0.06, 0.04, 0.1, 0, -0.02, 0.12, tones('#e2b23c', '#f0d48a', '#a88420'));
  pushBox(headP, headC, 0.08, 0.03, 0.04, 0, 0.02, 0.08, tones('#2a241c', '#4a4038', '#1a140e'));
  head.add(meshFrom(headP, headC));
  head.position.set(0, 0.08, 0.24);
  root.add(head);

  const tail = new T.Group();
  const tailP = [], tailC = [];
  pushBox(tailP, tailC, 0.16, 0.03, 0.28, 0, 0, -0.16, tones('#a34a28', '#c46a32', '#6a3018'));
  pushBox(tailP, tailC, 0.12, 0.02, 0.08, 0, 0, -0.32, tones('#f0e2c0', '#fff6e4', '#c4b090'));
  tail.add(meshFrom(tailP, tailC));
  tail.position.set(0, 0.02, -0.18);
  root.add(tail);

  const wingL = new T.Group();
  const left = wing();
  left.scale.x = -1;
  wingL.add(left);
  wingL.position.set(-0.08, 0.06, 0);
  root.add(wingL);
  const wingR = new T.Group();
  wingR.add(wing());
  wingR.position.set(0.08, 0.06, 0);
  root.add(wingR);

  const blob = new T.Mesh(
    new T.CircleGeometry(0.35, 10),
    new T.MeshBasicMaterial({ color: '#1a140c', transparent: true, opacity: 0.18, depthWrite: false })
  );
  blob.rotation.x = -Math.PI / 2;
  blob.position.y = -0.9;
  root.add(blob);

  root.scale.set(2.4, 2.4, 2.4);
  function pose(bird, time) {
    const flying = bird.mode !== 'perch';
    const flap = flying ? Math.sin((time || 0) * (bird.mode === 'circle' ? 7 : 4)) : 0.15;
    wingL.rotation.z = 0.35 + flap * 0.55;
    wingR.rotation.z = -0.35 - flap * 0.55;
    tail.rotation.x = flying ? -0.15 : 0.05;
    root.rotation.z = flying ? Math.sin((time || 0) * 2) * 0.05 : 0;
    const face = bird.heading || 0;
    root.rotation.y = face;
  }
  return { root, pose };
}
