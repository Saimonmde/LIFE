/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Canecas from Simón's scan, and a low-poly Zona skate modelled after his concrete ledges.
import { GLTFLoader } from './glb-loader.js?v=envigado-r1';

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
