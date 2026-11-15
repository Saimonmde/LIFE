/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Marco de madera y tablero de piedra. El texto largo va en la tarjeta, no en la malla. */
export function board(T, x, y, z, id, facing) {
  const group = new T.Group();
  group.position.set(x, y, z);
  group.rotation.y = facing || 0;
  const mat = new Map();
  const color = (hex) => {
    if (!mat.has(hex)) mat.set(hex, new T.MeshLambertMaterial({ color: hex, flatShading: true }));
    return mat.get(hex);
  };
  const box = new T.BoxGeometry(1, 1, 1);
  function part(px, py, pz, w, h, d, hex) {
    const mesh = new T.Mesh(box, color(hex));
    mesh.position.set(px, py, pz);
    mesh.scale.set(w, h, d);
    mesh.castShadow = mesh.receiveShadow = true;
    mesh.userData.id = id;
    group.add(mesh);
    return mesh;
  }
  part(-0.72, 0.85, 0, 0.12, 1.7, 0.12, '#5c3a22');
  part(0.72, 0.85, 0, 0.12, 1.7, 0.12, '#5c3a22');
  part(0, 1.7, 0, 1.7, 0.12, 0.14, '#6e4a2c');
  part(0, 0.95, 0, 1.56, 1.15, 0.08, '#d7c4a2');
  part(0, 0.95, 0.05, 1.28, 0.9, 0.04, '#f6f1e6');
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#f6f1e6';
  ctx.fillRect(0, 0, 512, 256);
  ctx.fillStyle = '#1c1208';
  ctx.font = '700 54px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('REGLAS', 256, 110);
  ctx.font = '600 28px sans-serif';
  ctx.fillText('Toca para leer', 256, 168);
  const texture = new T.CanvasTexture(canvas);
  texture.colorSpace = T.SRGBColorSpace;
  const plate = new T.Mesh(
    new T.PlaneGeometry(1.2, 0.72),
    new T.MeshBasicMaterial({ map: texture }),
  );
  plate.position.set(0, 0.95, 0.08);
  plate.userData.id = id;
  group.add(plate);
  return group;
}
