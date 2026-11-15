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
  function ground(localX, localZ) {
    if (typeof opt.height !== 'function') return 0;
    const worldX = (opt.x || 0) + localX;
    const worldZ = (opt.z || 0) + localZ;
    return opt.height(worldX / 2, worldZ / 2) - (opt.y || 0);
  }
  function plantSprite(name, x, z, h, id) {
    const baseY = ground(x, z);
    const sprite = new T.Sprite(new T.SpriteMaterial({ map: texture(name), transparent: true, depthWrite: false }));
    sprite.position.set(x, baseY + h / 2, z);
    sprite.scale.set(h * 0.72, h, 1);
    sprite.userData.h = h;
    if (id) { sprite.userData.id = id; pick.push(sprite); }
    g.add(sprite);
    return sprite;
  }
  function standUrl(key) {
    const file = pack.stand && pack.stand[key];
    if (!file) return '';
    return (pack.base || 'assets/cafe-cacao/') + (pack.v2 || 'v2/') + file;
  }
  function tryStand(key, x, z, h, id) {
    const url = standUrl(key);
    if (!url) return null;
    const material = new T.SpriteMaterial({ transparent: true, depthWrite: false });
    const sprite = new T.Sprite(material);
    const baseY = ground(x, z);
    sprite.position.set(x, baseY + h / 2, z);
    sprite.scale.set(h * 0.7, h, 1);
    sprite.visible = false;
    if (id) { sprite.userData.id = id; pick.push(sprite); }
    g.add(sprite);
    new T.TextureLoader().load(url, (loaded) => {
      const image = loaded.image || {};
      const width = image.width || 0;
      const height = image.height || 0;
      if (!width || !height || width > height) return;
      loaded.colorSpace = T.SRGBColorSpace;
      material.map = loaded;
      material.needsUpdate = true;
      sprite.scale.set(h * (width / height), h, 1);
      sprite.visible = true;
    });
    return sprite;
  }
  function shade(x, z) {
    const y0 = ground(x, z);
    mesh(trunk, tone('trunkDark'), x, y0 + 2.2, z, 0.16, 4.4, 0.16);
    mesh(ball, tone('shade'), x, y0 + 4.3, z, 1.5, 0.7, 1.5);
    mesh(ball, tone('shadeDeep'), x + 0.4, y0 + 4.0, z + 0.2, 0.9, 0.5, 0.9);
  }
  const cafeStages = ['plotCafePlanton', 'plotCafeVerde', 'plotCafeMaduro'];
  const cacaoStages = ['plotCacaoPlanton', 'plotCacaoVerde', 'plotCacaoMaduro'];
  const heights = [1.2, 1.5, 1.8];
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 5; col++) {
      const x = -6.2 + col * 1.05;
      const z = -2.2 + row * 1.15;
      const step = (row + col) % 3;
      const y0 = ground(x, z);
      mesh(box, tone('soil'), x, y0 + 0.04, z, 0.9, 0.06, 0.7);
      plantSprite(cafeStages[step], x, z, heights[step]);
    }
  }
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) {
      const x = 2.1 + col * 1.45;
      const z = -1.6 + row * 1.45;
      const step = (row + col) % 3;
      const y0 = ground(x, z);
      mesh(box, tone('soil'), x, y0 + 0.04, z, 1.05, 0.06, 0.8);
      plantSprite(cacaoStages[step], x, z, heights[step]);
    }
  }
  shade(-7.2, -3.2);
  shade(6.4, -3.2);
  function label(text, x, z, id) {
    const y0 = ground(x, z);
    mesh(box, tone('signPost'), x, y0 + 1.7, z, 0.12, 3.2, 0.12, id);
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
    const plate = new T.Sprite(new T.SpriteMaterial({ map: tex, depthTest: false }));
    plate.position.set(x, y0 + 3.5, z);
    plate.scale.set(2.8, 0.7, 1);
    if (id) { plate.userData.id = id; pick.push(plate); }
    g.add(plate);
  }
  function workshop(x, z, id, kind) {
    const y0 = ground(x, z);
    mesh(box, tone('patio'), x, y0 + 0.05, z, 2.2, 0.08, 1.8, id);
    mesh(box, tone('wall'), x, y0 + 0.95, z, 1.5, 1.5, 1.15, id);
    mesh(box, tone('roof'), x, y0 + 1.82, z, 1.85, 0.26, 1.45, id);
    tryStand(kind === 'cafe' ? 'workshopCafe' : 'workshopCacao', x, z + 0.15, 2.2, id);
    label(kind === 'cafe' ? 'TALLER DE CAFÉ' : 'TALLER DE CACAO', x, z + 0.2, id);
  }
  workshop(-4.2, 3.6, 'finca_cafe', 'cafe');
  workshop(3.4, 3.6, 'finca_cacao', 'cacao');
  label('LIBRO MAYOR', -0.2, 5.4, 'finca_libro');
  const beds = [];
  for (let i = 0; i < 8; i++) {
    const crop = i < 4 ? 'cafe' : 'cacao';
    const x = -5.2 + i * 1.35;
    const z = 5.6;
    const y0 = ground(x, z);
    const bed = mesh(box, tone('plotEmpty'), x, y0 + 0.08, z, 1.1, 0.1, 0.8, 'finca_las_palmas');
    const sprite = plantSprite(crop === 'cafe' ? 'plotCafePlanton' : 'plotCacaoPlanton', x, z, 1.2, 'finca_las_palmas');
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
      if (art) {
        const h = stage === 'maduro' ? 1.8 : stage === 'verde' ? 1.5 : 1.2;
        bed.sprite.material.map = texture(art);
        bed.sprite.scale.set(h * 0.72, h, 1);
        bed.sprite.position.y = ground(bed.sprite.position.x, bed.sprite.position.z) + h / 2;
      }
    }
  }
  return { group: g, sync };
}
