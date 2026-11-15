/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Mallas originales, bajas en polígonos. «Estilo Jabo» se lee aquí como hipótesis:
   chunky, tierno y de lectura isométrica, al modo Habbo. No copia modelos ajenos. */
const geos = {};
const mats = new Map();

function box(T) {
  if (!geos.box) geos.box = new T.BoxGeometry(1, 1, 1);
  return geos.box;
}
function mat(T, color) {
  const key = String(color).toLowerCase();
  if (!mats.has(key)) mats.set(key, new T.MeshLambertMaterial({ color: key, flatShading: true }));
  return mats.get(key);
}
function chunk(T, parent, color, x, y, z, sx, sy, sz) {
  const mesh = new T.Mesh(box(T), mat(T, color));
  mesh.position.set(x, y, z);
  mesh.scale.set(sx, sy, sz);
  mesh.castShadow = mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}
function blob(T, parent, color, x, y, z, sx, sy, sz) {
  if (!geos.blob) geos.blob = new T.SphereGeometry(0.5, 6, 5);
  const mesh = new T.Mesh(geos.blob, mat(T, color));
  mesh.position.set(x, y, z);
  mesh.scale.set(sx, sy, sz);
  mesh.castShadow = mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}
function pivot(T, parent, x, y, z) {
  const group = new T.Group();
  group.position.set(x, y, z);
  parent.add(group);
  return group;
}
function picks(colors, variant) {
  const list = colors && colors.length === 3 ? colors : ['#c48a52', '#f3e6c8', '#6b4a32'];
  const index = ((variant % 3) + 3) % 3;
  return { main: list[index], mark: list[(index + 1) % 3], accent: list[(index + 2) % 3] };
}

const SHAPES = {
  'dog:criollo': { body: [.72, .36, .34], leg: [.12, .28, .12], head: [.34, .30, .32], snout: [.18, .12, .16], ear: 'flop', tail: 'curve', chest: true },
  'dog:labrador': { body: [.82, .40, .38], leg: [.14, .30, .14], head: [.36, .32, .34], snout: [.24, .14, .18], ear: 'flop', tail: 'otter' },
  'dog:golden': { body: [.92, .44, .42], leg: [.14, .32, .14], head: [.40, .34, .36], snout: [.24, .14, .18], ear: 'flop', tail: 'plume', chest: true },
  'dog:pastor': { body: [.96, .36, .32], leg: [.12, .40, .12], head: [.32, .30, .38], snout: [.28, .12, .16], ear: 'point', tail: 'low', saddle: true, tanLegs: true, tanHead: true },
  'dog:bulldog': { body: [.62, .40, .48], leg: [.16, .14, .16], head: [.48, .34, .42], snout: [.30, .16, .24], ear: 'bat', tail: 'stub', stripes: true },
  'dog:beagle': { body: [.74, .34, .36], leg: [.12, .26, .12], head: [.32, .28, .32], snout: [.20, .12, .16], ear: 'long', tail: 'curve', chest: true, earDark: true, saddle: true, saddleDark: true },
  'cat:criollo': { body: [.58, .28, .28], leg: [.09, .22, .09], head: [.30, .26, .28], snout: [.12, .08, .10], ear: 'point', tail: 'whip', sit: true, chest: true },
  'cat:siames': { body: [.62, .28, .26], leg: [.09, .24, .09], head: [.28, .26, .28], snout: [.12, .08, .12], ear: 'point', tail: 'whip', sit: true, points: true },
  'cat:persa': { body: [.70, .42, .46], leg: [.12, .14, .12], head: [.48, .40, .44], snout: [.16, .12, .16], ear: 'tiny', tail: 'plume', sit: true },
  'cat:atigrado': { body: [.60, .28, .28], leg: [.09, .22, .09], head: [.30, .26, .28], snout: [.12, .08, .10], ear: 'point', tail: 'whip', sit: true, stripes: true },
  'cat:negro': { body: [.58, .28, .28], leg: [.09, .24, .09], head: [.30, .26, .28], snout: [.12, .08, .10], ear: 'point', tail: 'whip', sit: true, goldEyes: true },
  'cat:calico': { body: [.60, .28, .30], leg: [.09, .22, .09], head: [.30, .26, .28], snout: [.12, .08, .10], ear: 'point', tail: 'whip', sit: true, patches: true },
};

function ear(T, parent, color, side, kind) {
  const x = side * (kind === 'bat' ? .16 : .1);
  const node = pivot(T, parent, x, kind === 'long' ? .02 : .12, 0);
  if (kind === 'point') chunk(T, node, color, 0, .1, 0, .08, .18, .05);
  else if (kind === 'bat') chunk(T, node, color, 0, .08, 0, .14, .16, .06);
  else if (kind === 'long') chunk(T, node, color, 0, -.12, .02, .08, .26, .05);
  else if (kind === 'tiny') chunk(T, node, color, 0, .06, 0, .08, .08, .05);
  else chunk(T, node, color, 0, -.02, .02, .1, .16, .05);
  return node;
}

export function createPet(T, spec) {
  const species = spec.species === 'cat' ? 'cat' : 'dog';
  const shape = SHAPES[species + ':' + spec.breed] || SHAPES['dog:criollo'];
  const paint = picks(spec.colors, spec.variant | 0);
  const root = new T.Group();
  root.name = 'mascota';
  const bob = new T.Group();
  root.add(bob);
  const [bw, bh, bd] = shape.body;
  const [lw, lh, ld] = shape.leg;
  const legColor = shape.points ? paint.accent : shape.tanLegs ? paint.accent : paint.main;
  const legs = [];
  for (const [sx, sz] of [[-.5, .32], [.5, .32], [-.5, -.32], [.5, -.32]]) {
    const hip = pivot(T, bob, sx * bw * .7, lh, sz * bd);
    chunk(T, hip, legColor, 0, -lh / 2, 0, lw, lh, ld);
    legs.push(hip);
  }
  const body = pivot(T, bob, 0, lh + bh / 2, 0);
  blob(T, body, paint.main, 0, 0, 0, bw, bh, bd);
  if (shape.chest) blob(T, body, paint.mark, 0, -.06, bd * .36, bw * .5, bh * .55, bd * .28);
  if (shape.saddle) blob(T, body, shape.saddleDark ? paint.accent : paint.main, 0, bh * .28, -.02, bw * .72, bh * .36, bd * .55);
  if (shape.stripes) {
    for (const z of [-.12, .02, .16]) chunk(T, body, paint.accent, 0, bh * .42, z, bw * .92, .05, .06);
  }
  if (shape.patches) {
    chunk(T, body, paint.mark, -.12, .04, .04, .22, .18, .2);
    chunk(T, body, paint.accent, .14, -.02, -.06, .2, .16, .18);
  }
  const [hw, hh, hd] = shape.head;
  const head = pivot(T, body, 0, bh * .55, bd * .42);
  const headColor = shape.points ? paint.mark : shape.tanHead ? paint.accent : paint.main;
  blob(T, head, headColor, 0, 0, 0, hw, hh, hd);
  if (shape.points) chunk(T, head, paint.accent, 0, -.02, hd * .2, hw * .7, hh * .55, .08);
  const [sw, sh, sd] = shape.snout;
  blob(T, head, shape.points ? paint.accent : paint.mark, 0, -.06, hd * .42, sw, sh, sd);
  chunk(T, head, '#3a2418', 0, -.08, hd * .62, sw * .28, sh * .35, .04);
  const eye = shape.goldEyes ? '#e2b84a' : '#24180f';
  chunk(T, head, eye, -.08, .04, hd * .48, .05, .05, .04);
  chunk(T, head, eye, .08, .04, hd * .48, .05, .05, .04);
  const earColor = shape.earDark || shape.points ? paint.accent : paint.main;
  const ears = [ear(T, head, earColor, -1, shape.ear), ear(T, head, earColor, 1, shape.ear)];
  const tail = pivot(T, body, 0, bh * .2, -bd * .55);
  if (shape.tail === 'stub') chunk(T, tail, shape.points ? paint.accent : paint.main, 0, .04, -.04, .1, .1, .1);
  else if (shape.tail === 'plume') chunk(T, tail, paint.main, 0, .12, -.16, .16, .22, .28);
  else if (shape.tail === 'whip') chunk(T, tail, shape.points ? paint.accent : paint.main, 0, .16, -.18, .06, .08, .32);
  else if (shape.tail === 'low') chunk(T, tail, paint.main, 0, -.02, -.2, .08, .08, .34);
  else chunk(T, tail, paint.main, 0, .14, -.14, .08, .1, .26);
  root.userData.rig = { bob, body, head, legs, tail, ears, sit: !!shape.sit, legH: lh };
  root.userData.anim = 'idle';
  posePet(root, 'idle', 0);
  return root;
}

export function posePet(group, anim, time) {
  const rig = group && group.userData.rig;
  if (!rig) return;
  group.userData.anim = anim;
  const t = Number(time) || 0;
  const sit = rig.sit && anim === 'idle';
  rig.bob.position.y = 0;
  rig.body.rotation.x = 0;
  rig.head.rotation.x = Math.sin(t * 1.6) * .04;
  rig.head.rotation.z = 0;
  rig.tail.rotation.y = Math.sin(t * 3) * (anim === 'lie' ? .15 : .45);
  rig.tail.rotation.x = 0;
  for (const ear of rig.ears) ear.rotation.z = Math.sin(t * 2 + 1) * .08;
  if (anim === 'walk') {
    const step = Math.sin(t * 8);
    rig.legs[0].rotation.x = step * .7;
    rig.legs[1].rotation.x = -step * .7;
    rig.legs[2].rotation.x = -step * .7;
    rig.legs[3].rotation.x = step * .7;
    rig.bob.position.y = Math.abs(step) * .04;
    rig.body.rotation.x = .08;
  } else if (anim === 'lie') {
    rig.bob.position.y = -rig.legH * .72;
    rig.body.rotation.x = .15;
    rig.head.rotation.x = .35;
    for (const leg of rig.legs) leg.rotation.x = 1.25;
    rig.tail.rotation.x = .3;
  } else if (anim === 'greet') {
    const feline = !!rig.sit;
    const wag = Math.sin(t * (feline ? 7 : 16));
    rig.tail.rotation.y = wag * (feline ? .55 : 1.05);
    rig.head.rotation.x = feline ? -.2 + Math.sin(t * 9) * .18 : Math.sin(t * 10) * .08;
    rig.head.rotation.z = feline ? Math.sin(t * 7) * .18 : 0;
    rig.bob.position.y = Math.abs(Math.sin(t * 8)) * .04;
    if (feline) {
      rig.bob.position.y -= rig.legH * .35;
      rig.legs[2].rotation.x = 1.35;
      rig.legs[3].rotation.x = 1.35;
    }
  } else if (sit) {
    rig.bob.position.y = -rig.legH * .35;
    rig.legs[0].rotation.x = .15;
    rig.legs[1].rotation.x = .15;
    rig.legs[2].rotation.x = 1.35;
    rig.legs[3].rotation.x = 1.35;
    rig.head.rotation.x = -.08;
  } else {
    for (const leg of rig.legs) leg.rotation.x = 0;
    rig.bob.position.y = Math.sin(t * 2) * .015;
  }
}

function add(T, part, color, x, y, z, sx, sy, sz) {
  part(box(T), color, x, y, z, sx, sy, sz);
}

export function furnish(T, part, type, variant) {
  const draw = (color, x, y, z, sx, sy, sz) => add(T, part, color, x, y, z, sx, sy, sz);
  if (type === 'bed' && variant === 'colonial') {
    draw('#6e4a2e', 0, .28, 0, 1.7, .32, .9);
    draw('#f3efe4', 0, .48, .04, 1.55, .16, .72);
    draw('#8d3d3a', .15, .58, .02, .9, .08, .7);
    draw('#6e4a2e', -.8, .55, 0, .08, .5, .9);
    return true;
  }
  if (type === 'bed' && variant === 'nogal') {
    draw('#3e2918', 0, .3, 0, 1.7, .34, .92);
    draw('#d7e2d2', 0, .5, 0, 1.5, .14, .7);
    draw('#2f6a4a', .2, .6, 0, .85, .08, .68);
    draw('#3e2918', -.82, .62, 0, .1, .7, .92);
    return true;
  }
  if (type === 'bed' && variant === 'hamaca') {
    draw('#6e4a2e', -.7, .55, 0, .1, 1.1, .1);
    draw('#6e4a2e', .7, .55, 0, .1, 1.1, .1);
    draw('#e7d7a8', 0, .42, 0, 1.2, .08, .55);
    draw('#c45c38', 0, .36, 0, 1.05, .06, .4);
    return true;
  }
  if (type === 'altar') {
    const stone = variant === 'piedra';
    const gold = variant === 'dorado';
    const wood = stone ? '#8d8478' : '#6e4a2e';
    draw(wood, 0, .42, 0, .7, .8, .5);
    draw(gold ? '#e2b23c' : '#f7f1e4', 0, .84, 0, .78, .06, .56);
    draw('#f3e2b0', -.16, 1.05, 0, .06, .32, .06);
    draw('#f3e2b0', .16, 1.05, 0, .06, .32, .06);
    draw('#ffd27a', -.16, 1.26, 0, .05, .08, .05);
    draw('#ffd27a', .16, 1.26, 0, .05, .08, .05);
    return true;
  }
  if (type === 'plant' && variant) {
    const pot = variant === 'blanca' ? '#f4f1ea' : variant === 'colgante' ? '#c47a4a' : '#a86448';
    if (variant === 'colgante') {
      draw('#6e4a2e', 0, 1.15, 0, .08, 1.3, .08);
      draw('#6e4a2e', 0, 1.75, .15, .08, .08, .4);
      draw(pot, 0, 1.35, .28, .28, .22, .28);
      draw('#3e6a38', 0, 1.55, .28, .32, .24, .32);
    } else {
      draw(pot, 0, .22, 0, .34, .36, .34);
      draw('#3e6a38', 0, .55, 0, .4, .36, .4);
      draw('#6f8f45', .12, .78, .06, .22, .24, .22);
    }
    return true;
  }
  if (type === 'stove' && variant === 'fogon') {
    draw('#a86448', 0, .4, 0, .7, .75, .6);
    draw('#2a211c', 0, .42, .24, .36, .32, .08);
    draw('#ff9a3c', 0, .42, .16, .2, .16, .08);
    return true;
  }
  if (type === 'stove' && variant === 'lena') {
    draw('#6e4a2e', -.1, .12, 0, .55, .14, .18);
    draw('#8a5a32', .08, .22, .04, .5, .12, .16);
    draw('#5a3b24', 0, .34, -.02, .46, .12, .16);
    draw('#c47a4a', 0, .52, 0, .28, .22, .28);
    draw('#6e4a2e', 0, .66, 0, .3, .06, .3);
    return true;
  }
  if (type === 'stove' && variant === 'mesa') {
    draw('#efe2c4', 0, .42, 0, .9, .7, .5);
    draw('#d7c4a4', 0, .8, 0, .96, .08, .56);
    draw('#8fb8c9', -.2, .95, 0, .28, .16, .28);
    draw('#f3efe4', .22, 1.05, -.1, .2, .28, .16);
    return true;
  }
  return false;
}

export function createPoste(T, material) {
  const group = new T.Group();
  const wood = material('#6e4a2e');
  const post = new T.Mesh(box(T), wood);
  post.position.set(0, .85, 0);
  post.scale.set(.18, 1.7, .18);
  post.castShadow = true;
  group.add(post);
  const board = new T.Mesh(box(T), material('#f3e6c8'));
  board.position.set(0, 1.45, .12);
  board.scale.set(.9, .7, .08);
  board.castShadow = true;
  group.add(board);
  const ink = document.createElement('canvas');
  ink.width = 256;
  ink.height = 160;
  const ctx = ink.getContext('2d');
  ctx.fillStyle = '#3a2412';
  ctx.fillRect(0, 0, 256, 160);
  ctx.fillStyle = '#fff1c9';
  ctx.font = 'bold 42px Georgia, serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('NOTAS', 128, 58);
  ctx.font = '24px Georgia, serif';
  ctx.fillText('del parque', 128, 108);
  const tex = new T.CanvasTexture(ink);
  if ('colorSpace' in tex && T.SRGBColorSpace) tex.colorSpace = T.SRGBColorSpace;
  const label = new T.Mesh(new T.PlaneGeometry(.78, .5), new T.MeshBasicMaterial({ map: tex }));
  label.position.set(0, 1.45, .17);
  group.add(label);
  const hit = new T.Mesh(box(T), new T.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
  hit.position.set(0, 1.1, 0);
  hit.scale.set(1.1, 2.2, .6);
  hit.userData.poste = 'envigado';
  group.add(hit);
  return group;
}
