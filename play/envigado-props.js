/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Bancas, canecas verdes y esculturas propias. Sin escaneo de caneca y sin marcas.
import { GLTFLoader } from './glb-loader.js?v=valle-hud-r5';

export function placeEnvigadoProps(T, scene, height) {
  const park = window.EnvigadoPark;
  if (!park || !park.allProps) return;
  const concrete = concreteMaterial(T);
  const paver = paverMaterial(T);
  park.drawn3d.length = 0;
  for (const prop of park.allProps()) {
    const g = new T.Group();
    g.position.set(prop.x * 2 + 1, height(prop.x, prop.y) + 0.04, prop.y * 2 + 1);
    g.name = prop.id;
    g.userData.parkProp = prop.id;
    if (prop.kind === 'caneca') buildCaneca(T, g, prop.ry || 0);
    else if (prop.kind === 'banca') buildBanca(T, g);
    else buildEscultura(T, g, prop.id);
    scene.add(g);
    park.drawn3d.push(prop.id);
  }
  park.model = 'original';
  buildSkate(T, scene, height, park, concrete, paver);
  buildCanopy(T, scene, height);
  buildHouses(T, scene, height);
}

function buildCaneca(T, g, ry) {
  g.rotation.y = ry;
  const body = new T.Mesh(new T.CylinderGeometry(0.46, 0.52, 1.35, 10), new T.MeshLambertMaterial({ color: '#1f7a3a', flatShading: true }));
  body.position.y = 0.72;
  const lid = new T.Mesh(new T.CylinderGeometry(0.5, 0.5, 0.16, 10), new T.MeshLambertMaterial({ color: '#145028', flatShading: true }));
  lid.position.y = 1.46;
  const rim = new T.Mesh(new T.TorusGeometry(0.18, 0.035, 6, 10), new T.MeshLambertMaterial({ color: '#9aa3a0', flatShading: true }));
  rim.position.y = 1.62;
  rim.rotation.x = Math.PI / 2;
  body.castShadow = lid.castShadow = true;
  g.add(body, lid, rim);
}

function buildBanca(T, g) {
  const wood = new T.MeshLambertMaterial({ color: '#8a5a32', flatShading: true });
  const iron = new T.MeshLambertMaterial({ color: '#3e4650', flatShading: true });
  const box = new T.BoxGeometry(1, 1, 1);
  for (const z of [-0.16, -0.02, 0.12]) {
    const slat = new T.Mesh(box, wood);
    slat.scale.set(3.3, 0.08, 0.12);
    slat.position.set(0, 0.58, z);
    slat.castShadow = true;
    g.add(slat);
  }
  for (const y of [0.82, 1.02, 1.22]) {
    const slat = new T.Mesh(box, wood);
    slat.scale.set(3.3, 0.1, 0.08);
    slat.position.set(0, y, -0.28);
    slat.castShadow = true;
    g.add(slat);
  }
  for (const x of [-1.4, 1.4]) {
    for (const z of [-0.16, 0.14]) {
      const leg = new T.Mesh(box, iron);
      leg.scale.set(0.08, 0.58, 0.08);
      leg.position.set(x, 0.29, z);
      leg.castShadow = true;
      g.add(leg);
    }
  }
}

function buildEscultura(T, g, id) {
  const stone = new T.MeshLambertMaterial({ color: '#d9d3c7', flatShading: true });
  const metal = new T.MeshLambertMaterial({ color: '#c4a15a', flatShading: true });
  const plinth = new T.Mesh(new T.BoxGeometry(1.8, 0.7, 1.8), stone);
  plinth.position.y = 0.35;
  plinth.castShadow = true;
  g.add(plinth);
  if (id === 'anillo') {
    const ring = new T.Mesh(new T.TorusGeometry(0.95, 0.22, 8, 18), metal);
    ring.position.y = 2.15;
    ring.rotation.x = Math.PI / 2.5;
    ring.castShadow = true;
    g.add(ring);
  } else if (id === 'columna') {
    [[0, 1.35, 0, 0.95], [0.35, 2.25, 0.1, 0.78], [-0.28, 3.05, -0.08, 0.62]].forEach(([x, y, z, s]) => {
      const block = new T.Mesh(new T.BoxGeometry(s, 0.85, s), metal);
      block.position.set(x, y, z);
      block.castShadow = true;
      g.add(block);
    });
  } else {
    const oval = new T.Mesh(new T.SphereGeometry(0.7, 10, 8), metal);
    oval.scale.set(1, 1.7, 0.72);
    oval.position.y = 2.15;
    oval.castShadow = true;
    g.add(oval);
  }
}

function buildCanopy(T, scene, height) {
  const world = window.LiveInk?.world;
  if (!world) return;
  const trunk = new T.MeshLambertMaterial({ color: '#6b4a2c', flatShading: true });
  const leaf = new T.MeshLambertMaterial({ color: '#2f6a32', flatShading: true });
  for (const d of world.decorations || []) {
    if (d.type !== 'canopy') continue;
    const g = new T.Group();
    g.position.set(d.x * 2 + 1, height(d.x, d.y), d.y * 2 + 1);
    const stem = new T.Mesh(new T.CylinderGeometry(0.18, 0.28, 2.2, 6), trunk);
    stem.position.y = 1.1;
    const crown = new T.Mesh(new T.IcosahedronGeometry(1.35, 0), leaf);
    crown.position.y = 2.8;
    const crown2 = new T.Mesh(new T.IcosahedronGeometry(0.9, 0), leaf);
    crown2.position.set(0.6, 3.3, 0.3);
    stem.castShadow = crown.castShadow = crown2.castShadow = true;
    g.add(stem, crown, crown2);
    scene.add(g);
  }
}

function buildHouses(T, scene, height) {
  const world = window.LiveInk?.world;
  if (!world) return;
  const wall = new T.MeshLambertMaterial({ color: '#f3ead7', flatShading: true });
  const roof = new T.MeshLambertMaterial({ color: '#a85a3a', flatShading: true });
  const box = new T.BoxGeometry(1, 1, 1);
  for (const d of world.decorations || []) {
    if (d.type !== 'casa_envigado') continue;
    const floors = d.floors || 2;
    const g = new T.Group();
    const y0 = height(d.x, d.y);
    const body = new T.Mesh(box, wall);
    body.scale.set(d.w * 2, floors * 1.35, d.h * 2);
    body.position.set((d.x + d.w / 2) * 2, y0 + floors * 0.67, (d.y + d.h / 2) * 2);
    const cap = new T.Mesh(box, roof);
    cap.scale.set(d.w * 2 + 0.4, 0.45, d.h * 2 + 0.4);
    cap.position.set(body.position.x, y0 + floors * 1.35 + 0.2, body.position.z);
    body.castShadow = cap.castShadow = true;
    g.add(body, cap);
    scene.add(g);
  }
}

function buildSkate(T, scene, height, park, concrete, paver) {
  const origin = park.tile(park.skate.dx, park.skate.dy);
  const g = new T.Group();
  g.position.set(origin.x * 2, height(origin.x, origin.y), origin.y * 2);
  g.name = 'zona-skate';
  const pad = new T.Mesh(new T.BoxGeometry(5.4, 0.05, 3.4), paver);
  pad.position.set(2.5, 0.03, 1.5);
  pad.receiveShadow = true;
  g.add(pad);
  // Three wedge ledges, 2.5 m × 0.5 m × 0.6 m, with a gap so the row can be walked around.
  wedge(T, g, concrete, 1.35, 0.35);
  wedge(T, g, concrete, 1.35, 1.45);
  wedge(T, g, concrete, 3.7, 0.35);
  wall(T, g, concrete);
  sign(T, g, 4.7, 2.15);
  scene.add(g);
}

function wedge(T, parent, material, x, z) {
  const L = 2.5, D = 0.6, H = 0.5;
  const geo = new T.BufferGeometry();
  const y0 = 0.04;
  const positions = new Float32Array([
    -L / 2, y0, -D / 2,  L / 2, y0, -D / 2,  L / 2, y0, D / 2,  -L / 2, y0, D / 2,
    -L / 2, y0 + H * 0.92, -D / 2,  L / 2, y0 + H, -D / 2,  L / 2, y0 + H * 0.42, D / 2,  -L / 2, y0 + H * 0.34, D / 2,
  ]);
  const indices = [0, 1, 5, 0, 5, 4, 1, 2, 6, 1, 6, 5, 2, 3, 7, 2, 7, 6, 3, 0, 4, 3, 4, 7, 4, 5, 6, 4, 6, 7, 0, 2, 1, 0, 3, 2];
  geo.setAttribute('position', new T.BufferAttribute(positions, 3));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  const mesh = new T.Mesh(geo, material);
  mesh.position.set(x, 0, z);
  mesh.castShadow = mesh.receiveShadow = true;
  parent.add(mesh);
}

function wall(T, parent, concrete) {
  const body = new T.Mesh(new T.BoxGeometry(3.2, 0.48, 0.28), concrete);
  body.position.set(1.5, 0.28, 2.55);
  body.castShadow = body.receiveShadow = true;
  parent.add(body);
  const metal = new T.MeshStandardMaterial({ color: '#8d9398', metalness: 0.7, roughness: 0.35 });
  for (let i = 0; i < 5; i++) {
    const post = new T.Mesh(new T.BoxGeometry(0.045, 0.62, 0.045), metal);
    post.position.set(0.15 + i * 0.75, 0.78, 2.55);
    post.castShadow = true;
    parent.add(post);
  }
  for (const y of [0.68, 0.98]) {
    const rail = new T.Mesh(new T.BoxGeometry(3.15, 0.035, 0.035), metal);
    rail.position.set(1.5, y, 2.55);
    rail.castShadow = true;
    parent.add(rail);
  }
}

function sign(T, parent, x, z) {
  const post = new T.Mesh(new T.BoxGeometry(0.08, 1.15, 0.08), new T.MeshStandardMaterial({ color: '#5c6560', metalness: 0.4, roughness: 0.45 }));
  post.position.set(x, 0.6, z);
  post.castShadow = true;
  parent.add(post);
  const c = document.createElement('canvas');
  c.width = 512; c.height = 128;
  const g = c.getContext('2d');
  g.fillStyle = '#2f3b34'; g.fillRect(0, 0, 512, 128);
  g.strokeStyle = '#d7c48a'; g.lineWidth = 8; g.strokeRect(6, 6, 500, 116);
  g.fillStyle = '#f4ead0'; g.font = 'bold 54px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText('Zona skate', 256, 64);
  const tex = new T.CanvasTexture(c);
  tex.colorSpace = T.SRGBColorSpace;
  const face = new T.MeshStandardMaterial({ map: tex, color: '#ffffff' });
  const edge = new T.MeshStandardMaterial({ color: '#2f3b34' });
  const board = new T.Mesh(new T.BoxGeometry(1.5, 0.38, 0.06), [edge, edge, edge, edge, face, face]);
  board.position.set(x, 1.15, z);
  board.castShadow = true;
  parent.add(board);
}

function concreteMaterial(T) {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  g.fillStyle = '#c5c3bc'; g.fillRect(0, 0, 128, 128);
  for (let i = 0; i < 700; i++) {
    const v = 150 + ((i * 37) % 50);
    g.fillStyle = `rgba(${v},${v - 2},${v - 6},0.35)`;
    g.fillRect((i * 17) % 128, (i * 29) % 128, 2, 2);
  }
  const tex = new T.CanvasTexture(c);
  tex.colorSpace = T.SRGBColorSpace;
  tex.wrapS = tex.wrapT = T.RepeatWrapping;
  return new T.MeshStandardMaterial({ map: tex, color: '#ffffff', roughness: 0.92, metalness: 0.02 });
}

function paverMaterial(T) {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 128;
  const g = c.getContext('2d');
  for (let y = 0; y < 4; y++) for (let x = 0; x < 8; x++) {
    const beige = (x + y) % 3 === 0;
    const n = (x * 13 + y * 9) % 18;
    g.fillStyle = beige ? `rgb(${176 + n},${164 + n},${140 + n})` : `rgb(${132 + n},${134 + n},${136 + n})`;
    g.fillRect(x * 32 + 1, y * 32 + 1, 30, 30);
  }
  const tex = new T.CanvasTexture(c);
  tex.colorSpace = T.SRGBColorSpace;
  tex.wrapS = tex.wrapT = T.RepeatWrapping;
  return new T.MeshStandardMaterial({ map: tex, color: '#ffffff', roughness: 0.95 });
}
