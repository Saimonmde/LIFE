/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Poste cilíndrico y panel rectangular, con la cara que dibujó Sara.
   El título del cartel es UnifrakturMaguntia. El instructivo largo va en la tarjeta. */
const fontReady = new FontFace('UnifrakturMaguntia', 'url(fonts/UnifrakturMaguntia.ttf)').load().then((font) => {
  document.fonts.add(font);
  return true;
}).catch(() => false);

function paintTitle(ctx, gothic) {
  ctx.clearRect(0, 0, 1024, 512);
  ctx.fillStyle = '#efe6cf';
  ctx.fillRect(0, 0, 1024, 512);
  ctx.strokeStyle = '#e2b23c';
  ctx.lineWidth = 10;
  ctx.strokeRect(24, 24, 976, 464);
  ctx.fillStyle = '#1c1208';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const family = gothic ? 'UnifrakturMaguntia, serif' : 'serif';
  let size = 92;
  ctx.font = size + 'px ' + family;
  while (size > 48 && ctx.measureText('Reglas de la Mina').width > 900) {
    size -= 4;
    ctx.font = size + 'px ' + family;
  }
  ctx.fillText('Reglas de la Mina', 512, 210);
  ctx.strokeStyle = '#e2b23c';
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.moveTo(280, 280);
  ctx.lineTo(744, 280);
  ctx.stroke();
  ctx.font = '36px Inter, system-ui, sans-serif';
  ctx.fillText('Toca el cartel para leer', 512, 350);
  ctx.fillText('cómo minar y acuñar', 512, 400);
}

export function board(T, x, y, z, id, facing) {
  const group = new T.Group();
  group.position.set(x, y, z);
  group.rotation.y = facing || 0;
  const wood = new T.MeshLambertMaterial({ color: '#6b4a2c', flatShading: true });
  const metal = new T.MeshLambertMaterial({ color: '#8a9098', flatShading: true });
  const dirt = new T.MeshLambertMaterial({ color: '#3d2814', flatShading: true });
  const post = new T.Mesh(new T.CylinderGeometry(0.07, 0.085, 1.45, 20), wood);
  post.position.y = 0.78;
  post.userData.id = id;
  group.add(post);
  [0.42, 0.86, 1.28].forEach((height) => {
    const band = new T.Mesh(new T.CylinderGeometry(0.095, 0.095, 0.07, 8), metal);
    band.position.y = height;
    band.userData.id = id;
    group.add(band);
  });
  const base = new T.Mesh(new T.BoxGeometry(0.46, 0.07, 0.46), wood);
  base.position.y = 0.06;
  base.userData.id = id;
  group.add(base);
  const mound = new T.Mesh(new T.CylinderGeometry(0.36, 0.42, 0.05, 16), dirt);
  mound.position.y = 0.02;
  group.add(mound);
  const frame = new T.Mesh(new T.BoxGeometry(1.7, 1.38, 0.08), wood);
  frame.position.y = 1.92;
  frame.userData.id = id;
  group.add(frame);
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');
  paintTitle(ctx, false);
  const painted = new T.CanvasTexture(canvas);
  painted.colorSpace = T.SRGBColorSpace;
  const face = new T.Mesh(
    new T.PlaneGeometry(1.52, 1.22),
    new T.MeshBasicMaterial({ map: painted }),
  );
  face.position.set(0, 1.92, 0.05);
  face.userData.id = id;
  group.add(face);
  fontReady.then((ok) => {
    paintTitle(ctx, ok);
    painted.needsUpdate = true;
  });
  const loader = new T.TextureLoader();
  loader.load('assets/sara-cartel/panel-cara.png', (tex) => {
    tex.colorSpace = T.SRGBColorSpace;
    face.material.map = tex;
    face.material.needsUpdate = true;
  });
  return group;
}
