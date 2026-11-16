/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Bulto de la mochila caída. Malla original y un letrero flotante. */
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
    const color = faceColors[f] || faceColors[0];
    const quad = faces[f].map((id) => corners[id]);
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

function labelTexture(text) {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 128;
  const g = canvas.getContext('2d');
  g.fillStyle = '#2c1a0ce6';
  g.fillRect(0, 0, 512, 128);
  g.strokeStyle = '#e2b23c';
  g.lineWidth = 8;
  g.strokeRect(6, 6, 500, 116);
  g.font = '700 64px sans-serif';
  g.fillStyle = '#fff1c9';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText(text || 'Tu mochila', 256, 68);
  const tex = new T.CanvasTexture(canvas);
  tex.colorSpace = T.SRGBColorSpace;
  return tex;
}

export function createSaco(text) {
  const root = new T.Group();
  const positions = [], colors = [];
  pushBox(positions, colors, 0.62, 0.42, 0.46, 0, 0.28, 0, tones('#c4a574', '#e6d3a8', '#8a6840'));
  pushBox(positions, colors, 0.5, 0.16, 0.36, 0, 0.5, 0, tones('#d7c09a', '#f0e2c4', '#a88858'));
  pushBox(positions, colors, 0.08, 0.22, 0.08, -0.12, 0.62, 0, tones('#6b4224', '#8a5a32', '#3e2614'));
  pushBox(positions, colors, 0.08, 0.22, 0.08, 0.12, 0.62, 0, tones('#6b4224', '#8a5a32', '#3e2614'));
  pushBox(positions, colors, 0.34, 0.06, 0.08, 0, 0.7, 0, tones('#6b4224', '#a06a3c', '#3e2614'));
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
  geo.setAttribute('color', new T.Float32BufferAttribute(colors, 3));
  geo.computeVertexNormals();
  const sack = new T.Mesh(geo, new T.MeshLambertMaterial({ vertexColors: true }));
  sack.castShadow = true;
  sack.receiveShadow = true;
  root.add(sack);
  const blob = new T.Mesh(
    new T.CircleGeometry(0.42, 12),
    new T.MeshBasicMaterial({ color: '#1a140c', transparent: true, opacity: 0.3, depthWrite: false })
  );
  blob.rotation.x = -Math.PI / 2;
  blob.position.y = 0.03;
  root.add(blob);
  const sprite = new T.Sprite(new T.SpriteMaterial({ map: labelTexture(text), transparent: true, depthTest: false }));
  sprite.position.set(0, 1.15, 0);
  sprite.scale.set(1.8, 0.45, 1);
  root.add(sprite);
  root.scale.set(1.45, 1.45, 1.45);
  function retitle(next) {
    sprite.material.map = labelTexture(next);
    sprite.material.needsUpdate = true;
  }
  return { root, retitle };
}
