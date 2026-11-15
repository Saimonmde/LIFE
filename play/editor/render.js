/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Dibuja la capa de ediciones con instancias. Pocas caras, sin sombras propias. */
import * as T from '../three.module.js';

const VEGETATION = new Set(['palma', 'guayacan', 'sombra', 'arbusto', 'flores', 'pasto', 'cafe', 'cacao']);
const LAYERS = { terrain: true, paths: true, vegetation: true, decoration: true };

function hash(x, z) {
  const n = Math.sin(x * 127.1 + z * 311.7) * 43758.5453;
  return n - Math.floor(n);
}

function merge(geometries) {
  let vertices = 0;
  let indices = 0;
  geometries.forEach(geo => {
    vertices += geo.attributes.position.count;
    indices += geo.index ? geo.index.count : geo.attributes.position.count;
  });
  const position = new Float32Array(vertices * 3);
  const color = new Float32Array(vertices * 3);
  const index = new Uint32Array(indices);
  let vertex = 0;
  let offset = 0;
  geometries.forEach(geo => {
    position.set(geo.attributes.position.array, vertex * 3);
    color.set(geo.attributes.color.array, vertex * 3);
    if (geo.index) {
      for (let i = 0; i < geo.index.count; i += 1) index[offset++] = geo.index.getX(i) + vertex;
    } else {
      for (let i = 0; i < geo.attributes.position.count; i += 1) index[offset++] = vertex + i;
    }
    vertex += geo.attributes.position.count;
  });
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.BufferAttribute(position, 3));
  geo.setAttribute('color', new T.BufferAttribute(color, 3));
  geo.setIndex(new T.BufferAttribute(index, 1));
  geo.computeVertexNormals();
  return geo;
}

function paint(geo, hex) {
  const color = new T.Color(hex);
  const arr = new Float32Array(geo.attributes.position.count * 3);
  for (let i = 0; i < geo.attributes.position.count; i += 1) {
    arr[i * 3] = color.r;
    arr[i * 3 + 1] = color.g;
    arr[i * 3 + 2] = color.b;
  }
  geo.setAttribute('color', new T.BufferAttribute(arr, 3));
  return geo;
}

function partGeometry(part) {
  let geo;
  if (part.shape === 'box') geo = new T.BoxGeometry(part.w || 1, part.h || 1, part.d || 1);
  else if (part.shape === 'cylinder') geo = new T.CylinderGeometry(part.rt || 0.1, part.rb || 0.1, part.h || 1, part.seg || 5);
  else if (part.shape === 'cone') geo = new T.ConeGeometry(part.r || 0.4, part.h || 1, part.seg || 5);
  else if (part.shape === 'sphere') geo = new T.SphereGeometry(part.r || 0.3, part.seg || 6, Math.max(4, (part.seg || 6) - 1));
  else geo = new T.IcosahedronGeometry(part.r || 0.5, 0);
  if (part.rx) geo.rotateX(part.rx);
  if (part.ry) geo.rotateY(part.ry);
  if (part.rz) geo.rotateZ(part.rz);
  geo.translate(part.x || 0, part.y || 0, part.z || 0);
  return paint(geo, part.color || '#888888');
}

function buildParts(parts) {
  return merge(parts.map(partGeometry));
}

function stoneGeometry() {
  return buildParts([
    { shape: 'box', w: 0.62, h: 0.32, d: 0.46, x: -0.38, y: 0.16, z: -0.22, rz: 0.18, color: '#8d9398' },
    { shape: 'box', w: 0.5, h: 0.24, d: 0.55, x: 0.32, y: 0.12, z: 0.08, rz: -0.22, color: '#6a7076' },
    { shape: 'ico', r: 0.26, x: -0.05, y: 0.2, z: 0.38, color: '#b4b7b1' },
    { shape: 'box', w: 0.34, h: 0.2, d: 0.28, x: 0.08, y: 0.1, z: -0.42, color: '#9aa19b' },
  ]);
}

function brickTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const g = canvas.getContext('2d');
  g.fillStyle = '#6e6258';
  g.fillRect(0, 0, 256, 128);
  for (let y = 0; y < 4; y += 1) {
    for (let x = 0; x < 8; x += 1) {
      const beige = (x + y) % 3 === 0;
      const n = (x * 13 + y * 9) % 18;
      const shift = y % 2 ? 16 : 0;
      g.fillStyle = beige ? `rgb(${176 + n},${148 + n},${118 + n})` : `rgb(${150 + n},${96 + n},${72 + n})`;
      const px = ((x * 32 + shift) % 256);
      g.fillRect(px + 1, y * 32 + 1, 30, 30);
    }
  }
  const tex = new T.CanvasTexture(canvas);
  tex.colorSpace = T.SRGBColorSpace;
  tex.wrapS = tex.wrapT = T.RepeatWrapping;
  return tex;
}

function roadGeometry() {
  return buildParts([
    { shape: 'box', w: 1.96, h: 0.06, d: 1.96, y: 0.03, color: '#3a3e42' },
    { shape: 'box', w: 0.1, h: 0.02, d: 0.7, y: 0.07, z: -0.4, color: '#f0d15a' },
    { shape: 'box', w: 0.1, h: 0.02, d: 0.7, y: 0.07, z: 0.4, color: '#f0d15a' },
    { shape: 'box', w: 0.16, h: 0.12, d: 1.96, x: -0.9, y: 0.08, color: '#c8c2b4' },
    { shape: 'box', w: 0.16, h: 0.12, d: 1.96, x: 0.9, y: 0.08, color: '#d4cfc2' },
  ]);
}

function lambert(extra) {
  return new T.MeshLambertMaterial(Object.assign({ vertexColors: true }, extra || {}));
}

function instances(geo, material, items, place) {
  if (!items.length) return null;
  const mesh = new T.InstancedMesh(geo, material, items.length);
  mesh.castShadow = false;
  mesh.receiveShadow = true;
  mesh.frustumCulled = false;
  const matrix = new T.Matrix4();
  const position = new T.Vector3();
  const quaternion = new T.Quaternion();
  const scale = new T.Vector3(1, 1, 1);
  const up = new T.Vector3(0, 1, 0);
  items.forEach((item, index) => {
    const posed = place(item, index) || {};
    position.set(posed.x || 0, posed.y || 0, posed.z || 0);
    quaternion.setFromAxisAngle(up, posed.rot || 0);
    scale.set(posed.sx || 1, posed.sy || 1, posed.sz || 1);
    matrix.compose(position, quaternion, scale);
    mesh.setMatrixAt(index, matrix);
  });
  mesh.instanceMatrix.needsUpdate = true;
  mesh.userData.ids = items.map(item => item.id);
  mesh.userData.editor = true;
  return mesh;
}

function disposeMesh(mesh) {
  if (!mesh) return;
  if (mesh.parent) mesh.parent.remove(mesh);
  if (mesh.dispose) mesh.dispose();
}

export function createView() {
  const root = new T.Group();
  root.name = 'world-edits';
  const paths = new T.Group();
  paths.name = 'paths';
  const vegetation = new T.Group();
  vegetation.name = 'vegetation';
  const decoration = new T.Group();
  decoration.name = 'decoration';
  const surfaces = new T.Group();
  surfaces.name = 'surfaces';
  root.add(paths, vegetation, decoration, surfaces);

  const cache = new Map();
  function cached(id, build) {
    if (!cache.has(id)) {
      const geo = build();
      geo.userData.keep = true;
      cache.set(id, geo);
    }
    return cache.get(id);
  }
  const brick = brickTexture();
  const brickMat = new T.MeshLambertMaterial({ map: brick, color: '#ffffff' });
  const solid = lambert();
  const tintMat = new T.MeshLambertMaterial({ color: '#ffffff' });
  const waterMat = new T.MeshLambertMaterial({ color: '#ffffff', transparent: true, opacity: 0.72, depthWrite: false });

  const ring = new T.Mesh(
    new T.RingGeometry(0.7, 0.86, 24),
    new T.MeshBasicMaterial({ color: '#e2b23c', side: T.DoubleSide, depthTest: false, transparent: true, opacity: 0.95 }),
  );
  ring.rotation.x = -Math.PI / 2;
  ring.visible = false;
  ring.renderOrder = 3;
  const gizmo = new T.Group();
  gizmo.visible = false;
  gizmo.renderOrder = 4;
  [['x', '#e05a4f', 1, 0, 0], ['y', '#7dce6a', 0, 1, 0], ['z', '#6aa7e8', 0, 0, 1]].forEach(([axis, color, x, y, z]) => {
    const shaft = new T.Mesh(new T.BoxGeometry(0.08, 0.08, 0.08), new T.MeshBasicMaterial({ color, depthTest: false }));
    shaft.scale.set(x ? 14 : 1, y ? 14 : 1, z ? 14 : 1);
    shaft.position.set(x * 0.7, y * 0.7, z * 0.7);
    shaft.userData.axis = axis;
    shaft.userData.editor = true;
    gizmo.add(shaft);
  });
  const handle = new T.Mesh(new T.BoxGeometry(0.22, 0.22, 0.22), new T.MeshBasicMaterial({ color: '#f0d48a', depthTest: false }));
  handle.position.set(0.2, 0.9, 0.2);
  handle.userData.axis = 'scale';
  handle.userData.editor = true;
  gizmo.add(handle);

  let terrainKey = '';

  function clearGroup(group) {
    [...group.children].forEach(disposeMesh);
  }

  function tileY(height, x, z, lift) {
    try { return height(x, z) + lift; } catch (e) { return lift; }
  }

  function propY(height, prop) {
    if (!prop.grounded) return prop.y;
    return tileY(height, (prop.x - 1) / 2, (prop.z - 1) / 2, 0);
  }

  function roadRot(item, set) {
    const horizontal = set.has((item.x - 1) + ':' + item.z) || set.has((item.x + 1) + ':' + item.z);
    const vertical = set.has(item.x + ':' + (item.z - 1)) || set.has(item.x + ':' + (item.z + 1));
    if (horizontal && !vertical) return Math.PI / 2;
    return 0;
  }

  function rebuild(current, height, layers) {
    const show = Object.assign({}, LAYERS, layers || {});
    paths.visible = !!show.paths;
    vegetation.visible = !!show.vegetation;
    decoration.visible = !!show.decoration;
    surfaces.visible = true;
    clearGroup(paths);
    clearGroup(vegetation);
    clearGroup(decoration);
    clearGroup(surfaces);
    const doc = current || { paths: [], props: [], surfaces: [] };
    const byStyle = { piedra: [], adoquin: [], carretera: [] };
    (doc.paths || []).forEach(item => { if (byStyle[item.style]) byStyle[item.style].push(item); });
    const roadSet = new Set(byStyle.carretera.map(item => item.x + ':' + item.z));
    const stone = instances(cached('stone', stoneGeometry), solid, byStyle.piedra, item => {
      const h = hash(item.x, item.z);
      return {
        x: item.x * 2 + 1, y: tileY(height, item.x, item.z, 0.02), z: item.z * 2 + 1,
        rot: h * Math.PI, sx: 0.82 + h * 0.35, sz: 0.78 + hash(item.z, item.x) * 0.4, sy: 0.75 + hash(item.x, item.z) * 0.5,
      };
    });
    if (stone) { stone.userData.kind = 'path'; stone.userData.layer = 'paths'; paths.add(stone); }
    const paverGeo = cached('paver', () => {
      const geo = new T.PlaneGeometry(1.94, 1.94);
      geo.rotateX(-Math.PI / 2);
      return geo;
    });
    const paver = instances(paverGeo, brickMat, byStyle.adoquin, item => ({
      x: item.x * 2 + 1, y: tileY(height, item.x, item.z, 0.045), z: item.z * 2 + 1,
      rot: ((item.x + item.z) % 2) * Math.PI,
    }));
    if (paver) { paver.userData.kind = 'path'; paver.userData.layer = 'paths'; paths.add(paver); }
    const road = instances(cached('road', roadGeometry), solid, byStyle.carretera, item => ({
      x: item.x * 2 + 1, y: tileY(height, item.x, item.z, 0.02), z: item.z * 2 + 1,
      rot: roadRot(item, roadSet),
    }));
    if (road) { road.userData.kind = 'path'; road.userData.layer = 'paths'; paths.add(road); }

    const propsByType = new Map();
    (doc.props || []).forEach(prop => {
      if (!propsByType.has(prop.type)) propsByType.set(prop.type, []);
      propsByType.get(prop.type).push(prop);
    });
    propsByType.forEach((list, type) => {
      const entry = window.Editables && Editables.get(type);
      if (!entry) return;
      const desc = entry.render();
      if (!desc || !desc.parts) return;
      const geo = cached('prop:' + type, () => buildParts(desc.parts));
      const mesh = instances(geo, solid, list, prop => ({
        x: prop.x, y: propY(height, prop), z: prop.z,
        rot: (prop.rotY || 0) * Math.PI / 180,
        sx: prop.scale || 1, sy: prop.scale || 1, sz: prop.scale || 1,
      }));
      if (!mesh) return;
      mesh.userData.kind = 'prop';
      mesh.userData.layer = VEGETATION.has(type) ? 'vegetation' : 'decoration';
      (VEGETATION.has(type) ? vegetation : decoration).add(mesh);
    });

    const byMat = new Map();
    (doc.surfaces || []).forEach(item => {
      if (!byMat.has(item.material)) byMat.set(item.material, []);
      byMat.get(item.material).push(item);
    });
    const plane = cached('surface', () => {
      const geo = new T.PlaneGeometry(1.98, 1.98);
      geo.rotateX(-Math.PI / 2);
      return geo;
    });
    byMat.forEach((list, material) => {
      const mat = material === 'water' ? waterMat : tintMat;
      const mesh = instances(plane, mat, list, item => ({
        x: item.x * 2 + 1, y: tileY(height, item.x, item.z, material === 'water' ? 0.08 : 0.05), z: item.z * 2 + 1,
      }));
      if (!mesh) return;
      const colors = new Float32Array(list.length * 3);
      list.forEach((item, index) => {
        const color = new T.Color(item.tint || '#ffffff');
        colors[index * 3] = color.r;
        colors[index * 3 + 1] = color.g;
        colors[index * 3 + 2] = color.b;
      });
      mesh.instanceColor = new T.InstancedBufferAttribute(colors, 3);
      mesh.userData.kind = 'surface';
      mesh.userData.layer = 'surfaces';
      surfaces.add(mesh);
    });
    terrainKey = JSON.stringify(doc.terrain || []);
    return terrainKey;
  }

  function placeGizmo(point, visible) {
    gizmo.visible = !!visible && !!point;
    ring.visible = gizmo.visible;
    if (!point) return;
    gizmo.position.set(point.x, point.y, point.z);
    ring.position.set(point.x, point.y + 0.08, point.z);
  }

  function setLayers(layers) {
    const show = Object.assign({}, LAYERS, layers || {});
    paths.visible = !!show.paths;
    vegetation.visible = !!show.vegetation;
    decoration.visible = !!show.decoration;
    surfaces.visible = true;
    return show;
  }

  return { root, gizmo, ring, rebuild, placeGizmo, setLayers, terrainKey: () => terrainKey };
}
