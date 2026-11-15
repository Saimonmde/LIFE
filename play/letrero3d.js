/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Un poste redondo y un tablero rectangular. El título es gótico; el texto largo va en la tarjeta. */
const fontReady = new FontFace('UnifrakturMaguntia', 'url(fonts/UnifrakturMaguntia.ttf)').load().then((font) => {
  document.fonts.add(font);
  return true;
}).catch(() => false);

function paintTitle(ctx, gothic) {
  ctx.clearRect(0, 0, 1024, 512);
  ctx.fillStyle = '#f6f1e6';
  ctx.fillRect(0, 0, 1024, 512);
  ctx.fillStyle = '#1c1208';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const family = gothic ? 'UnifrakturMaguntia, serif' : 'serif';
  let size = 118;
  ctx.font = size + 'px ' + family;
  while (size > 56 && ctx.measureText('Reglas de la Mina').width > 960) {
    size -= 4;
    ctx.font = size + 'px ' + family;
  }
  ctx.fillText('Reglas de la Mina', 512, 256);
}

export function board(T, x, y, z, id, facing) {
  const group = new T.Group();
  group.position.set(x, y, z);
  group.rotation.y = facing || 0;
  const wood = new T.MeshLambertMaterial({ color: '#5c3a22', flatShading: true });
  const paper = new T.MeshLambertMaterial({ color: '#f6f1e6', flatShading: true });
  const post = new T.Mesh(new T.CylinderGeometry(0.11, 0.13, 2.05, 20), wood);
  post.position.y = 1.02;
  post.userData.id = id;
  group.add(post);
  const panel = new T.Mesh(new T.BoxGeometry(1.46, 0.78, 0.06), paper);
  panel.position.set(0.34, 1.28, 0);
  panel.userData.id = id;
  group.add(panel);
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');
  paintTitle(ctx, false);
  const texture = new T.CanvasTexture(canvas);
  texture.colorSpace = T.SRGBColorSpace;
  const plate = new T.Mesh(
    new T.PlaneGeometry(1.32, 0.64),
    new T.MeshBasicMaterial({ map: texture }),
  );
  plate.position.set(0.34, 1.28, 0.04);
  plate.userData.id = id;
  group.add(plate);
  fontReady.then((ok) => {
    paintTitle(ctx, ok);
    texture.needsUpdate = true;
  });
  return group;
}
