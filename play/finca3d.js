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
  function iconPlane(name, x, y, z, id) {
    const url = iconUrl(name);
    const plate = new T.Mesh(new T.PlaneGeometry(0.95, 0.95), new T.MeshBasicMaterial({ color: tone('wall'), transparent: true }));
    plate.position.set(x, y, z);
    if (id) { plate.userData.id = id; pick.push(plate); }
    g.add(plate);
    if (url) new T.TextureLoader().load(url, (tex) => { tex.colorSpace = T.SRGBColorSpace; plate.material = new T.MeshBasicMaterial({ map: tex, transparent: true }); });
    return plate;
  }
  function coffeeBush(x, z, ripe) {
    mesh(trunk, tone('trunk'), x, 0.35, z, 0.08, 0.7, 0.08);
    mesh(ball, tone('leaf'), x, 0.85, z, 0.42, 0.32, 0.42);
    mesh(ball, tone('leafLite'), x + 0.16, 0.7, z + 0.08, 0.28, 0.22, 0.28);
    if (!ripe) return;
    for (let i = 0; i < 4; i++) {
      const a = i * 1.6;
      mesh(ball, i % 2 ? tone('cherry') : tone('cherryDark'), x + Math.sin(a) * 0.22, 0.75 + (i % 2) * 0.12, z + Math.cos(a) * 0.22, 0.07, 0.07, 0.07);
    }
  }
  function cacaoTree(x, z, ripe) {
    mesh(trunk, tone('trunkDark'), x, 1.1, z, 0.1, 2.2, 0.1);
    mesh(ball, tone('leafDeep'), x, 2.15, z, 0.7, 0.45, 0.7);
    mesh(ball, tone('leaf'), x + 0.2, 1.9, z - 0.1, 0.4, 0.3, 0.4);
    if (!ripe) return;
    for (let i = 0; i < 3; i++) {
      const pod = mesh(ball, i % 2 ? tone('pod') : tone('podRipe'), x + (i - 1) * 0.18, 0.7 + i * 0.28, z + 0.16, 0.1, 0.18, 0.1);
      pod.rotation.z = (i - 1) * 0.4;
    }
  }
  function shade(x, z) {
    mesh(trunk, tone('trunkDark'), x, 2.2, z, 0.16, 4.4, 0.16);
    mesh(ball, tone('shade'), x, 4.3, z, 1.5, 0.7, 1.5);
    mesh(ball, tone('shadeDeep'), x + 0.4, 4.0, z + 0.2, 0.9, 0.5, 0.9);
  }
  mesh(box, tone('soil'), 0, 0.02, 2, 18, 0.04, 14);
  for (let row = 0; row < 4; row++) {
    for (let col = 0; col < 5; col++) coffeeBush(-6.2 + col * 0.85, -2.2 + row * 0.9, true);
  }
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) cacaoTree(2.2 + col * 1.5, -1.8 + row * 1.5, true);
  }
  shade(-7.2, -3.2);
  shade(-3.2, -3.4);
  shade(6.2, -3.2);
  function workshop(x, z, id, kind) {
    mesh(box, tone('wall'), x, 1.1, z, 3.2, 2.2, 2.4, id);
    mesh(box, tone('roof'), x, 2.35, z, 3.6, 0.28, 2.8, id);
    mesh(box, tone('trunkDark'), x, 0.15, z + 1.7, 3.4, 0.12, 1.6, id);
    if (kind === 'cafe') {
      mesh(trunk, tone('tank'), x - 1.3, 0.55, z + 1.7, 0.45, 0.7, 0.45, id);
      mesh(box, tone('patio'), x + 0.2, 0.35, z + 1.8, 1.4, 0.12, 0.8, id);
      mesh(box, tone('roaster'), x + 1.2, 0.7, z + 1.5, 0.7, 0.9, 0.7, id);
      mesh(trunk, tone('trunk'), x + 1.2, 1.5, z + 1.5, 0.12, 0.8, 0.12, id);
      mesh(ball, tone('ember'), x + 1.2, 0.55, z + 1.85, 0.16, 0.12, 0.08, id);
      sign('TALLER DE CAFÉ', x, 2.9, z + 1.3, id);
      iconPlane('workshopCafe', x, 1.5, z + 1.25, id);
    } else {
      for (const dx of [-0.7, 0.15, 1]) mesh(box, tone('box'), x + dx, 0.4, z + 1.7, 0.7, 0.45, 0.7, id);
      mesh(box, tone('pulp'), x - 0.7, 0.68, z + 1.7, 0.5, 0.12, 0.5, id);
      mesh(box, tone('dry'), x + 0.4, 0.32, z + 2.3, 1.8, 0.08, 0.7, id);
      sign('TALLER DE CACAO', x, 2.9, z + 1.3, id);
      iconPlane('workshopCacao', x, 1.5, z + 1.25, id);
    }
  }
  workshop(-4.2, 3.6, 'finca_cafe', 'cafe');
  workshop(3.4, 3.6, 'finca_cacao', 'cacao');
  sign('LIBRO MAYOR', -0.2, 1.4, 5.4, 'finca_libro');
  const beds = [];
  for (let i = 0; i < 8; i++) {
    const crop = i < 4 ? 'cafe' : 'cacao';
    const x = -5.2 + i * 1.35;
    const bed = mesh(box, tone('plotEmpty'), x, 0.08, 5.6, 1.1, 0.1, 0.8, 'finca_las_palmas');
    beds.push({ mesh: bed, crop, index: i % 4 });
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
    }
  }
  return { group: g, sync };
}
