/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Reconstrucción original en código del Gilberto Echeverri Mejía.
   No es la captura de Polycam. El servidor aplica la misma huella en tools/bridge4sur.py. */
const X0 = 82, X1 = 138, Y0 = 238, Y1 = 242;

export function bridgeHeight(c, x) {
  const p = c.profile;
  if (x < c.x0 + p.rampTiles) return p.west + (p.deck - p.west) * (x - c.x0) / p.rampTiles;
  if (x > c.x1 - p.rampTiles) return p.east + (p.deck - p.east) * (c.x1 - x) / p.rampTiles;
  return p.deck;
}
export function onBridge(c, x, y) {
  return !!c && x >= c.x0 && x < c.x1 && y >= c.y0 && y < c.y1;
}

export function install(w) {
  if (!w || w.bridge4Sur) return w && w.bridge4Sur;
  const nodes = w.nodes || [];
  if (nodes.some(n => n.x >= X0 - 1 && n.x <= X1 + 1 && n.y >= Y0 - 1 && n.y <= Y1)) return null;
  const west = w.elevation[240][X0 - 1];
  const east = w.elevation[240][X1];
  const deck = Math.max(west, east) + 2;
  const asphalt = Number(Object.keys(w.tiles).find(k => w.tiles[k].kind === 'asphalt'));
  const heightAt = x => {
    if (x < X0 + 15) return west + (deck - west) * (x - X0) / 15;
    if (x > X1 - 15) return east + (deck - east) * (X1 - x) / 15;
    return deck;
  };
  for (let x = X0; x < X1; x++) {
    for (let y = Y0; y < Y1; y++) {
      w.ground[y][x] = asphalt;
      w.collision[y][x] = 0;
      w.elevation[y][x] = Math.round(heightAt(x + 0.5) * 10000) / 10000;
    }
    if (x > X0 && x < X1 - 1) {
      w.collision[Y0 - 1][x] = 1;
      w.collision[Y1][x] = 1;
    }
  }
  for (const x of [104, 115]) w.collision[Y0 + 1][x] = 1;
  const river = (((w.waterBodies || {}).rio_medellin || {}).tiles) || [];
  const water = [];
  for (const cell of river) {
    const cx = Array.isArray(cell) ? cell[0] : cell.x;
    const cy = Array.isArray(cell) ? cell[1] : cell.y;
    if (cx >= X0 && cx < X1 && cy >= Y0 && cy < Y1) water.push([cx, cy]);
  }
  const cfg = {
    id: 'puente_4_sur',
    name: 'Puente de la 4 Sur · Gilberto Echeverri Mejía',
    kind: 'procedural-reconstruction',
    surveyed: false,
    x0: X0, x1: X1, y0: Y0, y1: Y1,
    nominalMeters: { length: 560, width: 40.5, pylon: 47, pylonSpacing: 108, stayedSpan: 213 },
    renderUnitsPerNominalMeter: 0.2,
    rendererUnitsPerTile: 2,
    profile: { west, east, deck, rampTiles: 15 },
    pylonTiles: [104, 115],
    waterCells: water,
    scan: {
      status: 'not-loaded',
      url: 'https://poly.cam/capture/0B952B36-D202-4FC6-A4F9-8FAE632DABD8',
      segments: [],
      transform: { translation: [220, deck, 480], rotationY: 0, scale: 1 },
    },
    note: 'Proporciones nominales. No es un escaneo ni una medición.',
  };
  w.waypoints = w.waypoints || [];
  w.signs3d = w.signs3d || [];
  if (!w.waypoints.some(p => p.id === 'puente_4_sur')) {
    w.waypoints.push({ id: 'puente_4_sur', name: 'Puente de la 4 Sur · acceso El Poblado', x: X1 - 1, y: Y0 + 2 });
  }
  if (!w.waypoints.some(p => p.id === 'puente_4_sur_guayabal')) {
    w.waypoints.push({ id: 'puente_4_sur_guayabal', name: 'Puente de la 4 Sur · acceso Guayabal', x: X0, y: Y0 + 2 });
  }
  if (!w.signs3d.some(s => s.text === 'PUENTE 4 SUR · RECREACIÓN')) {
    w.signs3d.push({ text: 'PUENTE 4 SUR · RECREACIÓN', x: X1 + 1, y: Y0 + 2 });
  }
  w.bridge4Sur = cfg;
  return cfg;
}

export function buildBridge4Sur(T, c) {
  const group = new T.Group();
  group.name = '4 Sur · reconstrucción proporcional';
  group.userData.scanLoaded = false;
  if (!c) return { group, update() {}, meshes: [] };
  const meshes = [];
  const positions = [];
  const z0 = c.y0 * 2, z1 = c.y1 * 2;
  function tri(a, b, d) { positions.push(...a, ...b, ...d); }
  for (let i = 0; i < c.x1 - c.x0; i++) {
    const x = c.x0 + i, a = x * 2, b = (x + 1) * 2;
    const ha = bridgeHeight(c, x), hb = bridgeHeight(c, x + 1);
    tri([a, ha, z0], [a, ha, z1], [b, hb, z1]);
    tri([a, ha, z0], [b, hb, z1], [b, hb, z0]);
  }
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
  geo.computeVertexNormals();
  const deck = new T.Mesh(geo, new T.MeshLambertMaterial({ color: '#515c5e', side: T.DoubleSide }));
  deck.receiveShadow = true;
  deck.userData.terrain = true;
  group.add(deck);
  meshes.push(deck);
  const boxGeometry = new T.BoxGeometry(1, 1, 1);
  function boxes(rows, color) {
    if (!rows.length) return null;
    const mesh = new T.InstancedMesh(boxGeometry, new T.MeshLambertMaterial({ color }), rows.length);
    const dummy = new T.Object3D();
    rows.forEach(([x, y, z, w, h, d, angle = 0], i) => {
      dummy.position.set(x, y, z);
      dummy.scale.set(w, h, d);
      dummy.rotation.set(0, 0, angle);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    });
    mesh.instanceMatrix.needsUpdate = true;
    mesh.receiveShadow = true;
    group.add(mesh);
    return mesh;
  }
  const kerbs = [], rails = [], marks = [], posts = [], supports = [];
  for (let x = c.x0 + 0.5; x < c.x1; x++) {
    const h = bridgeHeight(c, x), worldX = x * 2;
    for (const z of [z0 + 0.55, z1 - 0.55]) kerbs.push([worldX, h + 0.08, z, 2, 0.16, 1.1]);
    for (const z of [z0 + 0.08, z1 - 0.08]) {
      rails.push([worldX, h + 0.85, z, 2, 0.1, 0.12]);
      if (Math.round(x - 0.5) % 2 === 0) posts.push([worldX, h + 0.45, z, 0.1, 0.9, 0.1]);
    }
    if (Math.round(x - 0.5) % 3 === 0) {
      for (let lane = 1; lane < 8; lane++) {
        const z = z0 + 1.15 + lane * (z1 - z0 - 2.3) / 8;
        marks.push([worldX, h + 0.012, z, 0.8, 0.02, 0.04]);
      }
    }
    if (Math.round(x - 0.5) % 7 === 0) supports.push([worldX, h / 2, (z0 + z1) / 2, 0.6, Math.max(0.2, h - 0.15), 1.5]);
  }
  boxes((c.waterCells || []).map(([x, y]) => [x * 2 + 1, -0.39, y * 2 + 1, 2, 0.08, 2]), '#357f8b');
  boxes(kerbs, '#aab3ad');
  boxes(rails.concat(posts), '#dae2dc');
  boxes(marks, '#f3df9d');
  boxes(supports, '#828e8b');
  const pylons = [];
  for (const x of c.pylonTiles) {
    const h = bridgeHeight(c, x);
    const top = h + c.nominalMeters.pylon * c.renderUnitsPerNominalMeter;
    pylons.push([x * 2 + 1, (h + top) / 2, z0 + 3, 0.55, top - h, 0.65]);
    pylons.push([x * 2 + 1, top - 0.5, (z0 + z1) / 2, 0.75, 0.45, z1 - z0 - 1.2]);
  }
  boxes(pylons, '#e7e6d8');
  const cables = [];
  for (const [plane, n] of [[z0 + 0.3, 18], [z1 - 0.3, 17], [(z0 + z1) / 2, 16]]) {
    for (let i = 0; i < n; i++) {
      const tx = c.pylonTiles[i % 2];
      const top = bridgeHeight(c, tx) + c.nominalMeters.pylon * c.renderUnitsPerNominalMeter - 0.6;
      const end = c.x0 + 18 + (i / (n - 1)) * (c.x1 - c.x0 - 36);
      cables.push([[tx * 2 + 1, top, plane], [end * 2, bridgeHeight(c, end) + 0.15, plane]]);
    }
  }
  const cableMesh = new T.InstancedMesh(new T.CylinderGeometry(0.025, 0.025, 1, 5), new T.MeshLambertMaterial({ color: '#e9e3c8' }), cables.length);
  const dummy = new T.Object3D();
  const up = new T.Vector3(0, 1, 0);
  cables.forEach(([a, b], i) => {
    const A = new T.Vector3(...a), B = new T.Vector3(...b);
    const delta = B.clone().sub(A);
    dummy.position.copy(A).add(B).multiplyScalar(0.5);
    dummy.quaternion.setFromUnitVectors(up, delta.clone().normalize());
    dummy.scale.set(1, delta.length(), 1);
    dummy.updateMatrix();
    cableMesh.setMatrixAt(i, dummy.matrix);
  });
  cableMesh.instanceMatrix.needsUpdate = true;
  group.add(cableMesh);
  group.userData.nominalMeters = c.nominalMeters;
  group.userData.cables = cables.length;
  group.userData.segments = ['west-approach', 'stayed-span', 'east-approach'];
  function update(x, y, city) {
    const cx = (c.x0 + c.x1) / 2, cy = (c.y0 + c.y1) / 2;
    group.visible = !!city && Math.hypot(x - cx, y - cy) < 115;
  }
  return { group, meshes, update };
}
