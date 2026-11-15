/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Cafetal y cacaotal de Las Palmas, con los dos talleres. Geometría original.
export function attachFinca(T, parent, opt) {
  opt = opt || {};
  const pack = (typeof window !== 'undefined' && window.CAFE_CACAO_ART) || { icons: {}, colors: {}, base: 'assets/cafe-cacao/' };
  const tone = (name, fallback) => (pack.colors && pack.colors[name]) || fallback;
  const iconUrl = (name) => {
    const file = pack.icons && pack.icons[name];
    return file ? (pack.base || 'assets/cafe-cacao/') + file : '';
  };
  const g = new T.Group();
  g.position.set(opt.x || 0, opt.y || 0, opt.z || 0);
  const materials = new Map();
  const mat = (color) => {
    if (!materials.has(color)) materials.set(color, new T.MeshLambertMaterial({ color, flatShading: true }));
    return materials.get(color);
  };
  const box = new T.BoxGeometry(1, 1, 1);
  const ball = new T.IcosahedronGeometry(1, 1);
  const trunk = new T.CylinderGeometry(1, 1, 1, 6);
  const pick = opt.pick || [];
  function mesh(geo, color, x, y, z, sx, sy, sz, id) {
    const m = new T.Mesh(geo, mat(color));
    m.position.set(x, y, z);
    m.scale.set(sx, sy, sz);
    m.castShadow = true;
    m.receiveShadow = true;
    if (id) { m.userData.id = id; pick.push(m); }
    g.add(m);
    return m;
  }
  function sign(text, x, y, z, id) {
    const c = document.createElement('canvas');
    c.width = 512; c.height = 128;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#3a2414';
    ctx.fillRect(0, 0, 512, 128);
    ctx.strokeStyle = '#e2b23c';
    ctx.lineWidth = 8;
    ctx.strokeRect(8, 8, 496, 112);
    ctx.fillStyle = '#ffe7b0';
    ctx.font = 'bold 42px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 256, 64);
    const tex = new T.CanvasTexture(c);
    tex.colorSpace = T.SRGBColorSpace;
    const plate = new T.Mesh(new T.PlaneGeometry(3.2, 0.8), new T.MeshBasicMaterial({ map: tex }));
    plate.position.set(x, y, z);
    if (id) { plate.userData.id = id; pick.push(plate); }
    g.add(plate);
    mesh(box, tone('signPost'), x, y - 0.7, z, 0.12, 1.2, 0.12, id);
  }
  const texCache = new Map();
  function texture(name) {
    const url = iconUrl(name);
    if (!url) return null;
    if (!texCache.has(url)) {
      const tex = new T.TextureLoader().load(url);
      tex.colorSpace = T.SRGBColorSpace;
      texCache.set(url, tex);
    }
    return texCache.get(url);
  }
  function billboard(name, x, y, z, w, h, id) {
    const plate = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ map: texture(name), transparent: true, side: T.DoubleSide, depthWrite: false }));
    plate.position.set(x, y, z);
    if (id) { plate.userData.id = id; pick.push(plate); }
    g.add(plate);
    return plate;
  }
  function shade(x, z) {
    mesh(trunk, tone('trunkDark'), x, 2.2, z, 0.16, 4.4, 0.16);
    mesh(ball, tone('shade'), x, 4.3, z, 1.5, 0.7, 1.5);
    mesh(ball, tone('shadeDeep'), x + 0.4, 4.0, z + 0.2, 0.9, 0.5, 0.9);
  }
  mesh(box, tone('soil'), 0, 0.02, 2, 18, 0.04, 14);
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 5; col++) billboard('plotCafeMaduro', -6.2 + col * 1.05, 0.85, -2.2 + row * 1.15, 0.9, 1.35);
  }
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) billboard('plotCacaoMaduro', 2.1 + col * 1.45, 1.05, -1.6 + row * 1.45, 1.05, 1.55);
  }
  shade(-7.2, -3.2);
  shade(6.4, -3.2);
  function workshop(x, z, id, kind) {
    mesh(box, tone('soil'), x, 0.04, z, 3.6, 0.08, 2.2, id);
    const art = kind === 'cafe' ? 'workshopCafe' : 'workshopCacao';
    billboard(art, x, 1.15, z + 0.2, 3.4, 1.9, id);
    sign(kind === 'cafe' ? 'TALLER DE CAFÉ' : 'TALLER DE CACAO', x, 2.45, z + 0.3, id);
  }
  workshop(-4.2, 3.6, 'finca_cafe', 'cafe');
  workshop(3.4, 3.6, 'finca_cacao', 'cacao');
  sign('LIBRO MAYOR', -0.2, 1.4, 5.4, 'finca_libro');
  const beds = [];
  for (let i = 0; i < 8; i++) {
    const crop = i < 4 ? 'cafe' : 'cacao';
    const x = -5.2 + i * 1.35;
    const bed = mesh(box, tone('plotEmpty'), x, 0.08, 5.6, 1.1, 0.1, 0.8, 'finca_las_palmas');
    const sprite = billboard(crop === 'cafe' ? 'plotCafePlanton' : 'plotCacaoPlanton', x, 0.7, 5.6, 0.7, 1.05, 'finca_las_palmas');
    sprite.visible = false;
    beds.push({ mesh: bed, sprite, crop, index: i % 4 });
  }
  if (opt.lamp) {
    const sun = new T.PointLight(0xffe0b0, 40, 28, 2);
    sun.position.set(0, 6, 2);
    g.add(sun);
    const sky = new T.Mesh(new T.CircleGeometry(9, 20), new T.MeshBasicMaterial({ color: '#9ec4c8', side: T.DoubleSide }));
    sky.rotation.x = Math.PI / 2;
    sky.position.set(0, 7.2, 2);
    g.add(sky);
  }
  parent.add(g);
  function sync(view) {
    const plots = (view && view.plots) || [];
    const cafe = plots.filter(row => row.crop === 'cafe');
    const cacao = plots.filter(row => row.crop === 'cacao');
    for (const bed of beds) {
      const row = (bed.crop === 'cafe' ? cafe : cacao)[bed.index];
      const stage = row ? row.stage : 'vacio';
      const color = stage === 'maduro'
        ? (bed.crop === 'cafe' ? tone('cherry') : tone('pod'))
        : stage === 'verde' ? tone('green')
          : stage === 'planton' ? tone('seedling')
            : tone('plotEmpty');
      bed.mesh.material = mat(color);
      const art = stage === 'maduro' ? (bed.crop === 'cafe' ? 'plotCafeMaduro' : 'plotCacaoMaduro')
        : stage === 'verde' ? (bed.crop === 'cafe' ? 'plotCafeVerde' : 'plotCacaoVerde')
          : stage === 'planton' ? (bed.crop === 'cafe' ? 'plotCafePlanton' : 'plotCacaoPlanton')
            : '';
      bed.sprite.visible = !!art;
      if (art) bed.sprite.material.map = texture(art);
    }
  }
  return { group: g, sync };
}
