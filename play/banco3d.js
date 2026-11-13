/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Interior original de la Casa bancaria: mostrador, banquero y banquito.
export function buildBank(T) {
  const scene = new T.Scene();
  scene.background = new T.Color('#1a120c');
  scene.fog = new T.Fog('#24180f', 18, 42);
  scene.add(new T.HemisphereLight(0xf0d7a4, 0x4a3424, 0.9));
  const sun = new T.DirectionalLight(0xffe2b0, 0.7);
  sun.position.set(4, 12, 8);
  scene.add(sun);
  const pick = [];
  const mat = new Map();
  const color = (hex) => {
    if (!mat.has(hex)) mat.set(hex, new T.MeshLambertMaterial({ color: hex, flatShading: true }));
    return mat.get(hex);
  };
  const box = new T.BoxGeometry(1, 1, 1);
  function mesh(x, y, z, w, h, d, hex, id) {
    const m = new T.Mesh(box, color(hex));
    m.position.set(x, y, z);
    m.scale.set(w, h, d);
    m.castShadow = m.receiveShadow = true;
    if (id) { m.userData.id = id; pick.push(m); }
    scene.add(m);
    return m;
  }
  const floor = mesh(12, -0.08, 10, 24, 0.16, 20, '#c4a574');
  floor.userData.terrain = true;
  pick.push(floor);
  mesh(12, 1.6, 0.4, 24, 3.2, 0.4, '#6e4a2c');
  mesh(0.4, 1.6, 10, 0.4, 3.2, 20, '#6e4a2c');
  mesh(23.6, 1.6, 10, 0.4, 3.2, 20, '#6e4a2c');
  // Sin techo: la cámara del juego mira desde arriba, igual que en la casa.
  // Mostrador.
  mesh(12, 0.55, 7, 12, 1.05, 1.3, '#8a5a32', 'banquero');
  mesh(12, 1.12, 7, 12.4, 0.12, 1.5, '#e6d2a4', 'banquero');
  // Banquero detrás del mostrador.
  mesh(12, 1.7, 5.2, 0.7, 1.5, 0.45, '#c4553a', 'banquero');
  mesh(12, 2.65, 5.2, 0.42, 0.42, 0.42, '#e6c2a0', 'banquero');
  // Banquito donde se deposita.
  mesh(17, 0.28, 13, 0.7, 0.45, 0.7, '#6b4224', 'banquito');
  mesh(17, 0.55, 13, 0.85, 0.12, 0.85, '#d8b56a', 'banquito');
  // Puerta de salida.
  mesh(13, 1.3, 18.6, 1.4, 2.4, 0.2, '#3a2416', 'salida_banco');
  const lamp = new T.PointLight(0xffcc88, 18, 16, 2);
  lamp.position.set(12, 2.6, 10);
  scene.add(lamp);
  return { scene, pick };
}

export function placeBankHouse(T, scene, height) {
  const bank = window.Banco;
  if (!bank) return;
  const x = bank.DOOR.x;
  const y = bank.DOOR.y;
  const g = new T.Group();
  g.position.set((x - 2) * 2, height(x, y), (y - 2) * 2);
  const mat = (hex) => new T.MeshLambertMaterial({ color: hex, flatShading: true });
  const box = new T.BoxGeometry(1, 1, 1);
  function part(px, py, pz, w, h, d, hex) {
    const m = new T.Mesh(box, mat(hex));
    m.position.set(px, py, pz);
    m.scale.set(w, h, d);
    m.castShadow = m.receiveShadow = true;
    g.add(m);
  }
  part(5, 1.7, 3, 10, 3.4, 6, '#f3ead7');
  part(5, 3.7, 3, 10.6, 0.5, 6.6, '#8d3d32');
  part(5, 4.3, 3, 7, 1.1, 4, '#f6f1e6');
  part(5, 1.2, 6.15, 1.5, 2.2, 0.18, '#5c3a22');
  part(5, 2.6, 6.3, 2.6, 0.7, 0.08, '#1c140e');
  scene.add(g);
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 96;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1c140ee6';
  ctx.fillRect(0, 0, 512, 96);
  ctx.fillStyle = '#f0d48a';
  ctx.font = 'bold 42px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('CASA BANCARIA', 256, 62);
  const tex = new T.CanvasTexture(canvas);
  const tag = new T.Sprite(new T.SpriteMaterial({ map: tex, depthTest: false }));
  tag.position.set(x * 2 + 1, height(x, y) + 5.4, y * 2 + 1);
  tag.scale.set(8, 1.5, 1);
  scene.add(tag);
}
