/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Interior del Banco Central: bóveda verde, distinta de la Casa bancaria.
export function buildCentral(T) {
  const scene = new T.Scene();
  scene.background = new T.Color('#1c4a3c');
  scene.fog = new T.Fog('#1c4a3c', 22, 48);
  scene.add(new T.HemisphereLight(0xf4fff8, 0x2f8f72, 1.2));
  const sun = new T.DirectionalLight(0xfff1c4, 1.15);
  sun.position.set(-4, 10, 6);
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
  const floor = mesh(12, -0.08, 10, 24, 0.16, 20, '#2f8f72');
  floor.userData.terrain = true;
  pick.push(floor);
  mesh(12, 1.6, 0.4, 24, 3.2, 0.4, '#0c241c');
  mesh(0.4, 1.6, 10, 0.4, 3.2, 20, '#0c241c');
  mesh(23.6, 1.6, 10, 0.4, 3.2, 20, '#0c241c');
  mesh(12, 0.7, 6.2, 8, 1.3, 1.4, '#1d4a3a', 'boveda');
  mesh(12, 1.5, 6.2, 3.2, 0.35, 0.3, '#e2b23c', 'boveda');
  mesh(12, 2.15, 5.4, 1.1, 0.7, 0.35, '#f6e7a8', 'boveda');
  mesh(13, 1.3, 18.6, 1.4, 2.4, 0.2, '#e2b23c', 'salida_central');
  const lamp = new T.PointLight(0xfff1c4, 40, 22, 2);
  lamp.position.set(12, 2.8, 8);
  scene.add(lamp);
  return { scene, pick };
}

export function placeCentralHouse(T, scene, height) {
  const bank = window.Central;
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
  part(5, 1.8, 3, 9, 3.6, 6, '#14382c');
  part(5, 3.8, 3, 9.4, 0.45, 6.4, '#0c241c');
  part(5, 4.4, 3, 4.2, 1.2, 2.4, '#e2b23c');
  part(5, 1.2, 6.15, 1.6, 2.2, 0.2, '#f6e7a8');
  scene.add(g);
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 96;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#06241ce6';
  ctx.fillRect(0, 0, 512, 96);
  ctx.fillStyle = '#f6e7a8';
  ctx.font = 'bold 42px sans-serif';
  ctx.fillText('BANCO CENTRAL', 36, 62);
  const texture = new T.CanvasTexture(canvas);
  const sign = new T.Mesh(new T.PlaneGeometry(4.2, 0.8), new T.MeshBasicMaterial({ map: texture, transparent: true }));
  sign.position.set(5, 3.1, 6.35);
  g.add(sign);
}
