/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Interior colonial y la puerta de la casa junto al Parque de Envigado.
   Geometría original: muros de cal, vigas, teja, fogón de barro y patio. */
export function buildHouse(T) {
  const scene = new T.Scene();
  scene.background = new T.Color('#b7cabb');
  scene.fog = new T.Fog('#b7cabb', 26, 62);
  scene.add(new T.HemisphereLight(0xfff3e2, 0x6d5844, 1.25));
  const sun = new T.DirectionalLight(0xffe2bc, 1.15);
  sun.position.set(-10, 22, 8);
  scene.add(sun);
  const pick = [];
  const shared = new Map();
  const geo = (key, build) => { if (!shared.has(key)) shared.set(key, build()); return shared.get(key); };
  const boxG = () => geo('box', () => new T.BoxGeometry(1, 1, 1));
  const cyl = () => geo('cyl', () => new T.CylinderGeometry(1, 1, 1, 12));
  const sph = () => geo('sph', () => new T.SphereGeometry(1, 14, 10));
  const matCache = new Map();
  function mat(color, map) {
    const key = color + (map ? ':map' : '');
    if (!map && matCache.has(key)) return matCache.get(key);
    const m = new T.MeshLambertMaterial({ color, map: map || null, flatShading: true });
    if (!map) matCache.set(key, m);
    return m;
  }
  function tex(w, h, draw) {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    draw(c.getContext('2d'), w, h);
    const t = new T.CanvasTexture(c);
    t.colorSpace = T.SRGBColorSpace; t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 4;
    return t;
  }
  const plaster = tex(128, 128, (g) => {
    g.fillStyle = '#f7f3ea'; g.fillRect(0, 0, 128, 128);
    for (let i = 0; i < 900; i++) { const v = (i * 37) % 40; g.fillStyle = `rgba(90,70,40,${v / 900})`; g.fillRect((i * 17) % 128, (i * 29) % 128, 2, 2); }
  });
  const tileTex = tex(128, 128, (g) => {
    g.fillStyle = '#e7e0d4'; g.fillRect(0, 0, 128, 128);
    for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) {
      const shade = 236 - ((x * 3 + y * 5) % 5) * 8;
      g.fillStyle = `rgb(${shade},${shade - 8},${shade - 16})`;
      g.fillRect(x * 32 + 2, y * 32 + 2, 28, 28);
    }
  });
  const rugTex = tex(128, 128, (g) => {
    g.fillStyle = '#7d2e2a'; g.fillRect(0, 0, 128, 128);
    for (let y = 0; y < 128; y += 8) { g.fillStyle = y % 16 ? '#e6d2a2' : '#8c3d32'; g.fillRect(0, y, 128, 4); }
    g.strokeStyle = '#f3e6c4'; g.lineWidth = 6; g.strokeRect(6, 6, 116, 116);
  });
  const paintTex = tex(256, 160, (g) => {
    const sky = g.createLinearGradient(0, 0, 0, 160);
    sky.addColorStop(0, '#8eb8c9'); sky.addColorStop(0.55, '#e7d7b0'); sky.addColorStop(1, '#6e8f52');
    g.fillStyle = sky; g.fillRect(0, 0, 256, 160);
    g.fillStyle = '#6d8a48'; g.beginPath(); g.moveTo(0, 110); g.lineTo(40, 70); g.lineTo(90, 108); g.lineTo(150, 62); g.lineTo(210, 112); g.lineTo(256, 80); g.lineTo(256, 160); g.lineTo(0, 160); g.fill();
    g.fillStyle = '#f4efe4'; g.fillRect(108, 88, 36, 28);
    g.fillStyle = '#a86448'; g.beginPath(); g.moveTo(100, 90); g.lineTo(126, 70); g.lineTo(152, 90); g.fill();
    g.fillStyle = '#5c4632'; g.fillRect(122, 100, 8, 16);
    g.fillStyle = '#2f6a34'; g.beginPath(); g.arc(48, 100, 16, 0, 7); g.arc(200, 104, 18, 0, 7); g.fill();
  });
  const shell = new T.Group(); const furn = new T.Group();
  const doorHovers = [];
  scene.add(shell, furn);
  const owned = new Set();
  function clearGroup(group) {
    for (const child of [...group.children]) {
      group.remove(child);
      child.traverse(o => {
        if (owned.has(o)) owned.delete(o);
        if (o.userData && o.userData.ownMat && o.material) {
          if (o.material.map && o.userData.ownMap) o.material.map.dispose();
          o.material.dispose();
        }
      });
    }
  }
  function add(group, mesh) { group.add(mesh); owned.add(mesh); return mesh; }
  function part(group, geometry, color, x, y, z, sx, sy, sz, map) {
    const mesh = new T.Mesh(geometry, mat(color, map));
    mesh.position.set(x, y, z); mesh.scale.set(sx, sy, sz);
    mesh.castShadow = mesh.receiveShadow = true;
    if (map) mesh.userData.ownMat = true;
    return add(group, mesh);
  }
  function sign(text, w, h, fill) {
    return tex(w, h, (g, W, H) => {
      g.fillStyle = fill; g.fillRect(0, 0, W, H);
      g.strokeStyle = '#e2b23c'; g.lineWidth = 8; g.strokeRect(6, 6, W - 12, H - 12);
      g.fillStyle = '#fff1c9'; g.font = 'bold 42px Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(text, W / 2, H / 2);
    });
  }

  function rebuild(layout) {
    clearGroup(shell); clearGroup(furn); pick.length = 0; doorHovers.length = 0;
    const L = layout || window.Casa.layout;
    const wall = L.wall || '#f4f0e6';
    const floorTint = L.floor || '#c45c38';
    const wood = '#6b4228', dark = '#3d2918', clay = '#a86448';
    const floorMat = mat('#ffffff', tileTex); floorMat.color.set(floorTint); floorMat.userData = { own: true };
    const wallMat = mat('#ffffff', plaster); wallMat.color.set(wall);
    function slab(x, z, w, d, tint) {
      const m = new T.Mesh(boxG(), tint === 'patio' ? mat('#7d8f58') : floorMat);
      m.position.set(x, 0.06, z); m.scale.set(w, 0.12, d); m.receiveShadow = true; m.userData.terrain = true;
      add(shell, m); pick.push(m); return m;
    }
    // Sala: baldosas 1..8. Patio y zaguán al costado.
    slab(10, 10, 16, 16);
    slab(19, 9, 2, 6);
    slab(23, 10, 6, 12, 'patio');
    function wallBox(x, y, z, w, h, d) {
      const m = new T.Mesh(boxG(), wallMat);
      m.position.set(x, y, z); m.scale.set(w, h, d); m.castShadow = m.receiveShadow = true;
      return add(shell, m);
    }
    const H = 4.3;
    wallBox(10, H / 2, 1.75, 16.6, H, 0.5);
    wallBox(1.75, H / 2, 10, 0.5, H, 16.6);
    wallBox(4.7, H / 2, 18.35, 5.4, H, 0.55);
    wallBox(14.3, H / 2, 18.35, 7.4, H, 0.55);
    wallBox(18.25, H / 2, 4.2, 0.5, H, 4.2);
    wallBox(18.25, H / 2, 15.2, 0.5, H, 5.6);
    wallBox(23, H / 2, 3.75, 6.4, H, 0.45);
    wallBox(23, H / 2, 16.25, 6.4, H, 0.45);
    wallBox(26.25, H / 2, 10, 0.45, H, 12.6);
    // Zócalo, vigas y alero de teja sin tapar la vista.
    for (const z of [2.1, 17.9]) part(shell, boxG(), wood, 10, 0.18, z, 16.2, 0.28, 0.28);
    for (const x of [2.1, 17.9]) part(shell, boxG(), wood, x, 0.18, 10, 0.28, 0.28, 15.6);
    for (const z of [5, 9]) part(shell, boxG(), dark, 10, 4.15, z, 15.4, 0.22, 0.28);
    part(shell, boxG(), dark, 6, 4.15, 10, 0.22, 0.22, 15);
    part(shell, boxG(), '#a86448', 10, 4.45, 1.45, 16.8, 0.18, 0.7);
    // Ventana con postigos de madera.
    const winZ = 9;
    part(shell, boxG(), wood, 1.78, 2.35, winZ, 0.18, 1.7, 1.5);
    for (const side of [-1, 1]) {
      const shutter = part(shell, boxG(), '#7a5132', 1.15, 2.35, winZ + side * 0.85, 0.12, 1.45, 0.7);
      shutter.rotation.y = side * 0.7;
    }
    part(shell, boxG(), '#9ec4cf', 1.7, 2.35, winZ, 0.08, 1.2, 1.05);
    // Hornacina y cruz de madera (geometría propia, no un icono copiado).
    part(shell, boxG(), '#e7e1d4', 9, 2.7, 2.05, 1.5, 2.1, 0.28);
    part(shell, boxG(), dark, 9, 2.55, 1.82, 0.12, 1.35, 0.1);
    part(shell, boxG(), dark, 9, 2.85, 1.82, 0.7, 0.1, 0.1);
    // Puerta colonial grande, de cara al interior, con marco claro y farol.
    const door = new T.Group();
    door.position.set(9, 0, 17.85);
    const jamb = '#f7f1e4', leaf = '#5a3018', brass = '#e2b23c';
    const piece = (x, y, z, w, h, d, c) => part(door, boxG(), c, x, y, z, w, h, d);
    piece(0, 2.15, 0.05, 3.5, 4.5, 0.42, jamb);
    piece(-1.55, 2.05, -0.22, 0.28, 4.15, 0.34, dark);
    piece(1.55, 2.05, -0.22, 0.28, 4.15, 0.34, dark);
    piece(0, 4.15, -0.22, 3.4, 0.32, 0.34, dark);
    piece(0, 0.18, -0.16, 2.7, 0.16, 0.4, '#6b5340');
    piece(0, 2.05, -0.28, 2.55, 3.7, 0.16, leaf);
    for (const py of [1.15, 2.15, 3.15]) piece(0, py, -0.38, 2.15, 0.08, 0.06, brass);
    for (const px of [-0.55, 0.55]) piece(px, 2.1, -0.38, 0.08, 3.15, 0.06, brass);
    part(door, cyl(), brass, 0.72, 1.85, -0.46, 0.11, 0.11, 0.08);
    for (const x of [-1.15, 1.15]) {
      piece(x, 3.15, -0.55, 0.12, 0.7, 0.12, dark);
      part(door, boxG(), '#ffe7a8', x, 2.72, -0.55, 0.28, 0.36, 0.28);
      const lamp = new T.PointLight(0xffc56a, 14, 8, 2);
      lamp.position.set(x, 2.7, -0.7); door.add(lamp);
    }
    const glowMat = new T.MeshBasicMaterial({ color: '#ffd56a', transparent: true, opacity: 0.45, depthWrite: false });
    const glow = new T.Mesh(new T.RingGeometry(1.15, 1.7, 28), glowMat);
    glow.rotation.x = -Math.PI / 2; glow.position.set(0, 0.08, -0.9); door.add(glow);
    const outlineMat = new T.MeshBasicMaterial({ color: '#ffe08a', transparent: true, opacity: 0.95, depthWrite: false });
    const outline = new T.Mesh(boxG(), outlineMat);
    outline.position.set(0, 2.15, -0.5); outline.scale.set(3.85, 4.7, 0.08); outline.visible = false;
    door.add(outline); doorHovers.push(outline);
    const label = new T.Sprite(new T.SpriteMaterial({ map: sign('Salir · Parque de Envigado', 1024, 180, '#3a2412'), depthTest: false, transparent: true }));
    label.position.set(0, 2.35, -0.55); label.scale.set(3.35, 0.58, 1); label.renderOrder = 8; door.add(label);
    const hit = new T.Mesh(boxG(), new T.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
    hit.position.set(0, 2.4, -0.2); hit.scale.set(4.2, 5.4, 1.2); door.add(hit);
    door.traverse(m => { if (m.isMesh) { m.userData.exitDoor = true; m.userData.id = 'puerta_salida'; pick.push(m); } });
    shell.add(door);
    // Jardín fijo del patio: macetas en las esquinas, además de las plantas editables.
    for (const [x, z] of [[20.6, 4.7], [25.2, 15.2]]) {
      part(shell, cyl(), clay, x, 0.28, z, 0.38, 0.4, 0.38);
      part(shell, sph(), '#3f6b3a', x, 0.85, z, 0.45, 0.55, 0.45);
    }
    const warm = new T.PointLight(0xffc27a, 18, 16, 2); warm.position.set(9, 2.4, 9); scene.add(warm);
    if (shell.userData.warm) scene.remove(shell.userData.warm);
    shell.userData.warm = warm;

    const anchor = new Map();
    for (const item of L.items) {
      const g = new T.Group();
      const s = window.Casa.cellsOf(item);
      if (!s.length) continue;
      let minX = 99, minY = 99, maxX = -1, maxY = -1;
      for (const [x, y] of s) { minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y); }
      g.position.set((minX + maxX + 1), 0, (minY + maxY + 1));
      g.rotation.y = -(((item.rot % 4) + 4) % 4) * Math.PI / 2;
      g.userData.casaItem = item.id;
      buildItem(g, item.type);
      g.traverse(m => { if (m.isMesh) { m.userData.casaItem = item.id; m.castShadow = true; m.receiveShadow = true; pick.push(m); } });
      furn.add(g);
      if (item.id === window.Casa.selected) {
        const ring = new T.Mesh(new T.RingGeometry(0.9, 1.15, 24), new T.MeshBasicMaterial({ color: '#ffd56a', side: T.DoubleSide }));
        ring.rotation.x = -Math.PI / 2; ring.position.y = 0.08; g.add(ring);
      }
      anchor.set(item.id, g);
    }
    furn.userData.anchor = anchor;
  }
  function buildItem(g, type) {
    const P = (geometry, color, x, y, z, sx, sy, sz) => part(g, geometry, color, x, y, z, sx, sy, sz);
    const wood = '#6e4a2e', linen = '#f3efe4', clay = '#a86448';
    if (type === 'bed') {
      P(boxG(), wood, 0, 0.28, 0, 3.3, 0.35, 1.55);
      P(boxG(), linen, 0, 0.52, 0.05, 3.05, 0.22, 1.25);
      P(boxG(), '#d9c7a2', -1.15, 0.68, 0.05, 0.7, 0.16, 1.0);
      P(boxG(), '#8d3d3a', 0.45, 0.66, 0.02, 1.5, 0.1, 1.2);
      P(boxG(), wood, -1.55, 0.7, 0, 0.12, 0.7, 1.55);
    } else if (type === 'table') {
      P(boxG(), wood, 0, 0.78, 0, 3.1, 0.12, 1.45);
      for (const x of [-1.3, 1.3]) for (const z of [-0.55, 0.55]) P(boxG(), '#5a3b24', x, 0.38, z, 0.12, 0.72, 0.12);
    } else if (type === 'chair') {
      P(boxG(), wood, 0, 0.48, 0, 0.7, 0.1, 0.7);
      P(boxG(), wood, 0, 0.85, -0.3, 0.7, 0.7, 0.1);
      for (const x of [-0.26, 0.26]) for (const z of [-0.26, 0.26]) P(boxG(), '#5a3b24', x, 0.22, z, 0.08, 0.42, 0.08);
    } else if (type === 'chest') {
      P(boxG(), '#6a4328', 0, 0.38, 0, 1.15, 0.62, 0.7);
      P(boxG(), '#8a5d34', 0, 0.72, 0, 1.2, 0.16, 0.76);
      P(boxG(), '#c2b48a', 0, 0.45, 0.36, 0.7, 0.08, 0.06);
    } else if (type === 'stove') {
      P(boxG(), clay, 0, 0.45, 0, 1.35, 0.85, 1.15);
      P(boxG(), '#2a211c', 0, 0.55, 0.42, 0.7, 0.45, 0.12);
      P(boxG(), '#ff9a3c', 0, 0.55, 0.32, 0.4, 0.22, 0.12);
      const fire = new T.PointLight(0xff8a32, 8, 6, 2); fire.position.set(0, 0.8, 0.3); g.add(fire);
    } else if (type === 'pots') {
      P(cyl(), clay, -0.28, 0.22, 0, 0.22, 0.32, 0.22);
      P(sph(), '#8d4d34', -0.28, 0.42, 0, 0.2, 0.12, 0.2);
      P(cyl(), '#c48a58', 0.28, 0.16, 0.1, 0.16, 0.24, 0.16);
      P(cyl(), '#6d5340', 0.05, 0.28, -0.22, 0.12, 0.2, 0.12);
    } else if (type === 'plant') {
      P(cyl(), clay, 0, 0.22, 0, 0.32, 0.36, 0.32);
      P(sph(), '#3e6a38', 0, 0.7, 0, 0.42, 0.5, 0.42);
      P(sph(), '#6f8f45', 0.2, 0.95, 0.1, 0.22, 0.28, 0.22);
    } else if (type === 'rug') {
      const m = part(g, boxG(), '#ffffff', 0, 0.04, 0, 3.6, 0.05, 3.6, rugTex);
      m.userData.ownMat = true;
    } else if (type === 'candle') {
      P(cyl(), '#f3e2b0', 0, 0.28, 0, 0.1, 0.45, 0.1);
      P(boxG(), '#5a3b24', 0, 0.05, 0, 0.28, 0.08, 0.28);
      P(sph(), '#ffd27a', 0, 0.58, 0, 0.08, 0.14, 0.08);
      const glow = new T.PointLight(0xffc56a, 6, 5, 2); glow.position.set(0, 0.7, 0); g.add(glow);
    } else if (type === 'painting') {
      P(boxG(), wood, 0, 1.15, 0, 1.35, 1.7, 0.1);
      const canvas = part(g, new T.PlaneGeometry(1.1, 1.35), '#ffffff', 0, 1.2, 0.07, 1, 1, 1, paintTex);
      canvas.userData.ownMat = true;
    } else if (type === 'shelf') {
      P(boxG(), wood, 0, 0.35, 0, 1.3, 0.1, 0.4);
      P(boxG(), wood, 0, 0.85, 0, 1.3, 0.1, 0.4);
      for (const x of [-0.55, 0.55]) P(boxG(), '#5a3b24', x, 0.6, 0, 0.08, 1.2, 0.36);
      for (const x of [-0.35, 0.05, 0.4]) P(cyl(), x < 0 ? clay : '#d8c39a', x, 0.55, 0, 0.1, 0.22, 0.1);
    }
  }
  rebuild(window.Casa.layout);
  return { scene, pick, rebuild, setDoorHover(on) { for (const m of doorHovers) m.visible = !!on; } };
}

export function buildHomeMarker(T, scene, pick, height, material) {
  const door = window.Casa.PARK_DOOR;
  const y = height(door.x, door.y);
  const g = new T.Group();
  g.position.set(door.x * 2 + 1, y, door.y * 2 + 1);
  g.rotation.y = Math.PI / 2;
  scene.add(g);
  const mat = (c) => material(c);
  function box(w, h, d, x, py, z, color) {
    const m = new T.Mesh(new T.BoxGeometry(w, h, d), mat(color));
    m.position.set(x, py, z); m.castShadow = m.receiveShadow = true; m.userData.id = 'puerta_casa';
    g.add(m); pick.push(m); return m;
  }
  box(3.4, 3.2, 2.4, 0, 1.6, -0.4, '#f4f0e6');
  box(3.8, 0.16, 2.8, 0, 3.25, -0.4, '#a86448');
  box(0.2, 1.1, 3.1, -1.5, 3.7, -0.4, '#a86448');
  box(0.2, 1.1, 3.1, 1.5, 3.7, -0.4, '#a86448');
  box(3.2, 0.16, 0.2, 0, 4.15, -0.4, '#8d5438');
  box(1.15, 2.15, 0.12, 0, 1.2, 0.82, '#6b4228');
  box(1.5, 0.16, 0.16, 0, 2.35, 0.9, '#3d2918');
  box(0.35, 0.5, 0.08, -1.15, 2.15, 0.9, '#7a5132');
  box(0.55, 0.7, 0.08, 1.15, 2.15, 0.9, '#9ec4cf');
  const c = document.createElement('canvas'); c.width = 512; c.height = 128;
  const x = c.getContext('2d');
  x.fillStyle = '#3a2412'; x.fillRect(0, 0, 512, 128);
  x.strokeStyle = '#e2b23c'; x.lineWidth = 8; x.strokeRect(6, 6, 500, 116);
  x.fillStyle = '#fff1c9'; x.font = 'bold 54px Georgia, serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText('CASA', 256, 64);
  const tex = new T.CanvasTexture(c); tex.colorSpace = T.SRGBColorSpace;
  const board = new T.Mesh(new T.PlaneGeometry(2.4, 0.6), new T.MeshBasicMaterial({ map: tex }));
  board.position.set(0, 3.55, 0.95); board.userData.id = 'puerta_casa'; g.add(board); pick.push(board);
  const tag = new T.Sprite(new T.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  tag.position.set(0, 5.1, 0); tag.scale.set(3.2, 0.8, 1); tag.userData.id = 'puerta_casa'; g.add(tag); pick.push(tag);
  return g;
}
