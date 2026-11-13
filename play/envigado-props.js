/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Canecas from Simón's scan, and a low-poly Zona skate modelled after his concrete ledges.
import { GLTFLoader } from './glb-loader.js?v=valle-hud-r5';

export function placeEnvigadoProps(T, scene, height) {
  const park = window.EnvigadoPark;
  if (!park) return;
  const concrete = concreteMaterial(T);
  const paver = paverMaterial(T);
  const holders = park.canecaTiles().map(spot => {
    const g = new T.Group();
    g.position.set(spot.x * 2 + 1, height(spot.x, spot.y), spot.y * 2 + 1);
    g.rotation.y = spot.ry || 0;
    g.name = 'caneca';
    const fallback = new T.Mesh(new T.CylinderGeometry(0.32, 0.36, 1, 18), new T.MeshStandardMaterial({ color: '#c5c7c4', metalness: 0.62, roughness: 0.38 }));
    fallback.position.y = 0.5;
    fallback.castShadow = fallback.receiveShadow = true;
    g.add(fallback);
    g.userData.fallback = fallback;
    scene.add(g);
    return g;
  });
  const loader = new GLTFLoader();
  park.model = 'loading';
  loader.load('../graphics/models/caneca_envigado.glb', (gltf) => {
    for (const holder of holders) {
      const copy = gltf.scene.clone(true);
      copy.traverse(o => { if (o.isMesh) { o.castShadow = o.receiveShadow = true; } });
      if (holder.userData.fallback) holder.remove(holder.userData.fallback);
      holder.add(copy);
    }
    park.model = 'glb';
  }, undefined, (err) => {
    park.model = 'fallback';
    console.warn('La caneca de Envigado usa el cilindro de respaldo.', err);
  });
  buildSkate(T, scene, height, park, concrete, paver);
  buildBenches(T, scene, height, park);
  buildSculptures(T, scene, height, park);
  buildCanopy(T, scene, height);
  buildHouses(T, scene, height);
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

function buildBenches(T, scene, height, park) {
  const wood = new T.MeshLambertMaterial({ color: '#6e4a2c', flatShading: true });
  const iron = new T.MeshLambertMaterial({ color: '#3e4650', flatShading: true });
  const box = new T.BoxGeometry(1, 1, 1);
  for (const spot of park.benchTiles()) {
    const g = new T.Group();
    g.position.set(spot.x * 2 + 1, height(spot.x, spot.y), spot.y * 2 + 1);
    g.name = spot.id;
    const seat = new T.Mesh(box, wood);
    seat.scale.set(1.5, 0.12, 0.48);
    seat.position.y = 0.48;
    const back = new T.Mesh(box, wood);
    back.scale.set(1.5, 0.42, 0.08);
    back.position.set(0, 0.78, -0.2);
    for (const x of [-0.62, 0.62]) {
      const leg = new T.Mesh(box, iron);
      leg.scale.set(0.08, 0.48, 0.4);
      leg.position.set(x, 0.24, 0);
      g.add(leg);
    }
    seat.castShadow = back.castShadow = true;
    g.add(seat, back);
    scene.add(g);
  }
}

function buildSculptures(T, scene, height, park) {
  const stone = new T.MeshLambertMaterial({ color: '#d9d3c7', flatShading: true });
  const bronze = new T.MeshStandardMaterial({ color: '#b08a4a', metalness: 0.35, roughness: 0.45 });
  for (const spot of park.sculptureTiles()) {
    const g = new T.Group();
    g.position.set(spot.x * 2 + 1, height(spot.x, spot.y), spot.y * 2 + 1);
    g.name = spot.id;
    const plinth = new T.Mesh(new T.BoxGeometry(1.5, 1.1, 1.5), stone);
    plinth.position.y = 0.55;
    plinth.castShadow = plinth.receiveShadow = true;
    g.add(plinth);
    let art;
    if (spot.id === 'anillo') {
      art = new T.Mesh(new T.TorusGeometry(0.7, 0.16, 10, 22), bronze);
      art.position.y = 2.0;
      art.rotation.x = Math.PI / 2.4;
    } else if (spot.id === 'columna') {
      art = new T.Group();
      [[0, 1.5, 0], [0.28, 2.25, 0.08], [-0.22, 2.95, -0.06]].forEach(([x, y, z], i) => {
        const block = new T.Mesh(new T.BoxGeometry(0.7 - i * 0.1, 0.7, 0.7 - i * 0.1), bronze);
        block.position.set(x, y, z);
        art.add(block);
      });
    } else {
      art = new T.Mesh(new T.SphereGeometry(0.62, 14, 12), bronze);
      art.scale.set(1, 1.45, 0.7);
      art.position.y = 2.15;
    }
    art.traverse(o => { if (o.isMesh) o.castShadow = o.receiveShadow = true; });
    g.add(art);
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
