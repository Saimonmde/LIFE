/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Relieve amplio del Valle de Aburrá y la vista 3D del mapa.
// Viajar reutiliza LiveInk.askTravel (el diálogo y el teletransporte del servidor).
const TRAVEL = new Set(['barbosa','girardota','copacabana','bello','medellin','itagui','envigado','sabaneta','la_estrella','caldas','parque_bolivar','las_palmas']);
const STEP = 4;
const PITCH_MIN = 10 * Math.PI / 180;
const PITCH_MAX = Math.PI / 2;

function clampYaw(v) { return ((v % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2); }

function linear(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255].map(v => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
}

const KIND_COLOR = {
  grass: linear('#6e8a52'), grass_flowers: linear('#759455'), grass_worn: linear('#7d8a48'),
  path: linear('#c4ac87'), cobble: linear('#c08a68'), pavement: linear('#b4b8b4'),
  creek: linear('#5e9aa0'), bridge: linear('#9a7350'), water: linear('#2f7f8e'),
  cliff: linear('#6e6e62'), shore: linear('#c2ad82'), mountain: linear('#6d8a5c'),
  rocky: linear('#8e8c78'), asphalt: linear('#4a5154'),
};

export function createValleyView(T, opts) {
  const { W, scene, corner, terrainKind, chunkMeshes, chunkSize, renderer, camera, narrow, height } = opts;
  const elev = W.elevation;
  const mapW = W.width;
  const mapH = W.height;
  function cityHeight(x, y) {
    if (!elev || !elev.length || !elev[0]) return 0;
    const ix = Math.max(0, Math.min(elev[0].length - 1, Math.floor(x)));
    const iy = Math.max(0, Math.min(elev.length - 1, Math.floor(y)));
    return elev[iy][ix] || 0;
  }
  function lift(x, y) {
    return (W.mapId || 'city') === 'city' ? height(x, y) : cityHeight(x, y);
  }
  const cols = Math.ceil(mapW / STEP);
  const rows = Math.ceil(mapH / STEP);
  const positions = [];
  const colors = [];
  const quads = [];
  const sample = (i, j) => {
    const x = Math.max(0, Math.min(mapW - 1, Math.min(mapW, i * STEP)));
    const y = Math.max(0, Math.min(mapH - 1, Math.min(mapH, j * STEP)));
    return { x, y, h: corner(x, y) };
  };
  for (let j = 0; j <= rows; j++) {
    for (let i = 0; i <= cols; i++) {
      const p = sample(i, j);
      const wx = Math.min(mapW, i * STEP) * 2;
      const wz = Math.min(mapH, j * STEP) * 2;
      positions.push(wx, p.h, wz);
      const kind = terrainKind(p.x, p.y);
      const base = KIND_COLOR[kind] || KIND_COLOR.grass;
      const lift = kind === 'water' || kind === 'creek' ? 0.9 : 0.78 + Math.min(0.4, Math.max(0, p.h) / 90);
      colors.push(base[0] * lift, base[1] * lift, base[2] * lift);
    }
  }
  for (let j = 0; j < rows; j++) {
    for (let i = 0; i < cols; i++) {
      const tx = Math.min(mapW - 1, i * STEP);
      const ty = Math.min(mapH - 1, j * STEP);
      quads.push({ key: Math.floor(tx / chunkSize) + ',' + Math.floor(ty / chunkSize), i, j });
    }
  }
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
  geo.setAttribute('color', new T.Float32BufferAttribute(colors, 3));
  const stride = cols + 1;
  const full = [];
  for (const q of quads) {
    const a = q.j * stride + q.i;
    const b = (q.j + 1) * stride + q.i;
    const c = (q.j + 1) * stride + q.i + 1;
    const d = q.j * stride + q.i + 1;
    full.push(a, b, c, a, c, d);
  }
  geo.setIndex(full);
  geo.computeVertexNormals();
  const relief = new T.Mesh(geo, new T.MeshLambertMaterial({ vertexColors: true, flatShading: true }));
  relief.frustumCulled = true;
  relief.receiveShadow = false;
  relief.castShadow = false;
  scene.add(relief);

  const beacon = new T.Group();
  const gem = new T.Mesh(new T.OctahedronGeometry(1.6), new T.MeshBasicMaterial({ color: '#ffdf29' }));
  gem.position.y = 14;
  const pole = new T.Mesh(new T.CylinderGeometry(0.12, 0.12, 14, 6), new T.MeshBasicMaterial({ color: '#ffdf29' }));
  pole.position.y = 7;
  beacon.add(pole, gem);
  beacon.visible = false;
  scene.add(beacon);

  const focus = new T.Vector3(mapW, 16, mapH);
  const posedTarget = new T.Vector3();
  const projected = new T.Vector3();
  let open = false;
  let flyT = null;
  let here = { x: mapW / 2, y: mapH / 2 };
  let player = { x: 0, y: 0 };
  let mapYaw = 0;
  let mapPitch = 1.02;
  let mapDist = 900;
  let maskKey = '';
  let pointers = new Map();
  let sized = '';
  let pinch = 0;
  let down = null;
  let dragged = false;
  const labelEls = new Map();
  let flyLayer = null;

  function fitDist() {
    const aspect = Math.max(0.4, camera.aspect || 1);
    const vFov = camera.fov * Math.PI / 180;
    const hFov = 2 * Math.atan(Math.tan(vFov / 2) * aspect);
    const spanX = mapW * 2;
    const spanZ = mapH * 2;
    return Math.max((spanZ / 2) / Math.tan(vFov / 2), (spanX / 2) / Math.tan(hFov / 2)) * 1.05;
  }
  function clampDist(v) { return Math.max(36, Math.min(fitDist() * 1.45, v)); }

  function applyMask(overview) {
    const keys = overview ? null : new Set(chunkMeshes.keys());
    const sig = overview ? 'all' : [...keys].sort().join('|');
    if (sig === maskKey) return;
    maskKey = sig;
    const index = [];
    for (const q of quads) {
      if (keys && keys.has(q.key)) continue;
      const a = q.j * stride + q.i;
      const b = (q.j + 1) * stride + q.i;
      const c = (q.j + 1) * stride + q.i + 1;
      const d = q.j * stride + q.i + 1;
      index.push(a, b, c, a, c, d);
    }
    geo.setIndex(index);
  }

  function overviewOn() { return open || (flyT != null && flyT < 0.84); }

  function labels() {
    return (W.mapLabels || []).filter(item => item && item.name != null && Number.isFinite(item.x) && Number.isFinite(item.y));
  }
  function worldPoint(label) {
    const x = (label.x + 0.5) * 2;
    const z = (label.y + 0.5) * 2;
    const y = lift(label.x, label.y) + (label.kind === 'poi' ? 16 : 26);
    return [x, y, z];
  }
  function screenNudge(label, width) {
    const dist = camera.position.distanceTo(focus) || 1;
    const zoom = Math.min(1.2, Math.max(0.35, dist / fitDist()));
    const k = (width / 800) * zoom;
    return [(label.dx || 0) * k, (label.dy || 0) * k];
  }
  function travelId(label) {
    if (!label.id) return null;
    if (label.kind === 'municipio' || TRAVEL.has(label.id)) return TRAVEL.has(label.id) ? label.id : null;
    return null;
  }

  function placeHtml(layer, width, heightPx, clickable) {
    if (!layer) return;
    const seen = new Set();
    const placed = [];
    const marks = labels();
    for (const label of marks) {
      const id = label.id || label.name;
      seen.add(id);
      let el = labelEls.get(layer.id + ':' + id);
      if (!el || el.parentElement !== layer) {
        const go = clickable && travelId(label);
        el = document.createElement(go ? 'button' : 'span');
        if (go) {
          el.type = 'button';
          el.className = label.kind === 'poi' ? 'poi' : 'muni';
          el.onclick = (event) => { event.stopPropagation(); window.LiveInk?.askTravel?.(go); };
        } else el.className = label.kind === 'poi' ? 'poi quiet' : 'quiet';
        el.textContent = label.name;
        layer.append(el);
        labelEls.set(layer.id + ':' + id, el);
      }
      const [x, y, z] = worldPoint(label);
      projected.set(x, y, z).project(camera);
      const visible = projected.z > -1 && projected.z < 1 && Math.abs(projected.x) < 1.2 && Math.abs(projected.y) < 1.2;
      el.hidden = !visible;
      if (!visible) continue;
      const [nx, ny] = screenNudge(label, width);
      const w = label.name.length * 7.2 + 16;
      const h = label.kind === 'poi' ? 18 : 22;
      let left = (projected.x + 1) * width / 2 + nx - w / 2;
      let top = (1 - projected.y) * heightPx / 2 + ny;
      let guard = 0;
      const hits = (a, b) => !(a.x + a.w + 4 <= b.x || b.x + b.w + 4 <= a.x || a.y + a.h + 3 <= b.y || b.y + b.h + 3 <= a.y);
      while (guard++ < 28 && placed.some(b => hits({ x: left, y: top, w, h }, b))) {
        top += 8;
        if (guard % 5 === 0) left += guard % 10 === 0 ? -14 : 14;
      }
      placed.push({ x: left, y: top, w, h });
      el.style.left = (left + w / 2) + 'px';
      el.style.top = top + 'px';
    }
    const compass = [
      ['N', mapW, 28, 6],
      ['S', mapW, 22, mapH * 2 - 6],
      ['OR', mapW * 2 - 8, 22, mapH],
      ['OC', 8, 22, mapH],
    ];
    for (const [name, x, y, z] of compass) {
      seen.add('c:' + name);
      let el = labelEls.get(layer.id + ':c:' + name);
      if (!el || el.parentElement !== layer) {
        el = document.createElement('span');
        el.className = 'rosa';
        el.textContent = name;
        layer.append(el);
        labelEls.set(layer.id + ':c:' + name, el);
      }
      projected.set(x, y, z).project(camera);
      const visible = projected.z > -1 && projected.z < 1;
      el.hidden = !visible;
      if (!visible) continue;
      el.style.left = ((projected.x + 1) * width / 2) + 'px';
      el.style.top = ((1 - projected.y) * heightPx / 2) + 'px';
    }
    let you = labelEls.get(layer.id + ':tu');
    if (!you || you.parentElement !== layer) {
      you = document.createElement('span');
      you.className = 'tu';
      you.textContent = '★ Tú';
      layer.append(you);
      labelEls.set(layer.id + ':tu', you);
    }
    projected.set(here.x * 2 + 1, lift(here.x, here.y) + 18, here.y * 2 + 1).project(camera);
    const youVisible = projected.z > -1 && projected.z < 1;
    you.hidden = !youVisible;
    if (youVisible) {
      you.style.left = ((projected.x + 1) * width / 2) + 'px';
      you.style.top = ((1 - projected.y) * heightPx / 2) + 'px';
    }
    seen.add('tu');
    for (const [key, el] of labelEls) {
      if (!key.startsWith(layer.id + ':')) continue;
      const id = key.slice(layer.id.length + 1);
      if (!seen.has(id) && !id.startsWith('c:')) { el.remove(); labelEls.delete(key); }
    }
  }

  function ensureFlyLayer() {
    if (flyLayer) return flyLayer;
    flyLayer = document.createElement('div');
    flyLayer.id = 'valley-fly-labels';
    document.body.append(flyLayer);
    return flyLayer;
  }
  function clearLayer(layer) {
    if (!layer) return;
    layer.replaceChildren();
    for (const key of [...labelEls.keys()]) if (key.startsWith(layer.id + ':')) labelEls.delete(key);
  }

  function buildChips() {
    const row = document.getElementById('city-map-muni');
    if (!row) return;
    row.replaceChildren();
    for (const label of labels()) {
      const id = travelId(label);
      if (!id) continue;
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = label.name;
      b.onclick = (event) => { event.stopPropagation(); window.LiveInk?.askTravel?.(id); };
      row.append(b);
    }
  }
  function wireZoom() {
    const box = document.getElementById('city-map-zoom');
    if (!box || box.childElementCount) return;
    for (const [id, text, dir] of [['city-map-in', '+', -1], ['city-map-out', '−', 1]]) {
      const b = document.createElement('button');
      b.type = 'button';
      b.id = id;
      b.textContent = text;
      b.setAttribute('aria-label', dir < 0 ? 'Acercar' : 'Alejar');
      b.onclick = (event) => { event.stopPropagation(); mapDist = clampDist(mapDist * (dir < 0 ? 0.82 : 1.22)); };
      box.append(b);
    }
  }

  function resize() {
    const stage = document.getElementById('city-map-stage');
    if (!open || !stage) return;
    const w = Math.max(2, stage.clientWidth);
    const h = Math.max(2, stage.clientHeight);
    const key = w + 'x' + h;
    if (key === sized) return;
    sized = key;
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, narrow() ? 1 : 1.5));
    renderer.setSize(w, h, true);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  function openMap() {
    const stage = document.getElementById('city-map-stage');
    const canvas = renderer.domElement;
    if (!stage || !canvas) return false;
    open = true;
    canvas.classList.add('valley-map-canvas');
    canvas.style.position = 'absolute';
    canvas.style.inset = 'auto';
    canvas.style.left = '0';
    canvas.style.top = '0';
    canvas.style.zIndex = '1';
    canvas.style.touchAction = 'none';
    stage.append(canvas);
    mapYaw = 0;
    mapPitch = 1.02;
    mapDist = fitDist();
    buildChips();
    wireZoom();
    resize();
    return true;
  }
  function closeMap() {
    if (!open && renderer.domElement.parentElement === document.body) return;
    open = false;
    sized = '';
    const canvas = renderer.domElement;
    canvas.classList.remove('valley-map-canvas');
    canvas.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;touch-action:none;z-index:0';
    document.body.insertBefore(canvas, document.body.firstChild);
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, narrow() ? 1.25 : 2));
    renderer.setSize(innerWidth, innerHeight, false);
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    const row = document.getElementById('city-map-muni');
    if (row) row.replaceChildren();
    clearLayer(document.getElementById('city-map-labels'));
    pointers.clear();
    pinch = 0;
    dragged = false;
  }

  function pose() {
    if (open) {
      posedTarget.copy(focus);
      return { target: posedTarget, yaw: mapYaw, pitch: mapPitch, distance: mapDist };
    }
    if (flyT == null) return null;
    const t = flyT;
    const u = t < 0.62 ? 0 : (t - 0.62) / 0.38;
    const e = u * u * (3 - 2 * u);
    const px = player.x * 2 + 1;
    const pz = player.y * 2 + 1;
    const py = lift(player.x, player.y) + 1;
    posedTarget.set(focus.x * (1 - e) + px * e, focus.y * (1 - e) + py * e, focus.z * (1 - e) + pz * e);
    const yaw = (-0.4 + Math.sin(t * Math.PI) * 0.28) * (1 - e) + 0.12 * e;
    const pitch = 1.0 * (1 - e) + 1.08 * e;
    const distance = fitDist() * (1 - e) + 24 * e;
    return { target: posedTarget, yaw, pitch, distance };
  }

  function atmosphere() {
    if (open || flyT != null) return { fogNear: 1800, fogFar: 5600, cameraFar: 6800 };
    if (narrow()) return { fogNear: 90, fogFar: 460, cameraFar: 1400 };
    return { fogNear: 160, fogFar: 920, cameraFar: 2400 };
  }

  function sync(px, py) {
    player = { x: px, y: py };
    const city = (W.mapId || 'city') === 'city';
    if (city) here = { x: px, y: py };
    else if (window.Casa?.PARK_DOOR) here = { x: Casa.PARK_DOOR.x, y: Casa.PARK_DOOR.y };
    const show = overviewOn();
    for (const holder of chunkMeshes.values()) holder.visible = !show;
    applyMask(show);
    beacon.visible = show;
    beacon.position.set(here.x * 2 + 1, lift(here.x, here.y), here.y * 2 + 1);
    if (open) {
      resize();
      const stage = document.getElementById('city-map-stage');
      const layer = document.getElementById('city-map-labels');
      if (stage && layer) placeHtml(layer, stage.clientWidth, stage.clientHeight, true);
      if (flyLayer) flyLayer.hidden = true;
      const loc = document.getElementById('city-map-location');
      if (loc) loc.textContent = city
        ? `Tu posición: ${px.toFixed(1)}, ${py.toFixed(1)} · ★ Tú`
        : 'Estás en un interior. El mapa muestra el valle; viajar sale afuera.';
    } else if (flyT != null && flyT < 0.8) {
      const layer = ensureFlyLayer();
      layer.hidden = false;
      placeHtml(layer, innerWidth, innerHeight, false);
    } else if (flyLayer) {
      flyLayer.hidden = true;
    }
  }

  function pointerDown(e) {
    renderer.domElement.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, [e.clientX, e.clientY]);
    down = [e.clientX, e.clientY];
    dragged = false;
    pinch = 0;
  }
  function pointerMove(e) {
    if (!pointers.has(e.pointerId)) return;
    const prev = pointers.get(e.pointerId);
    pointers.set(e.pointerId, [e.clientX, e.clientY]);
    if (pointers.size > 1) {
      const [a, b] = [...pointers.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (pinch) mapDist = clampDist(mapDist * pinch / d);
      pinch = d;
      dragged = true;
      return;
    }
    if (down && Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 6) dragged = true;
    if (dragged && prev) {
      mapYaw = clampYaw(mapYaw - (e.clientX - prev[0]) * 0.008);
      mapPitch = Math.max(PITCH_MIN, Math.min(PITCH_MAX, mapPitch + (e.clientY - prev[1]) * 0.005));
    }
  }
  function pointerUp(e) { pointers.delete(e.pointerId); if (pointers.size < 2) pinch = 0; }
  function wheel(e) {
    e.preventDefault();
    mapDist = clampDist(mapDist * (e.deltaY > 0 ? 1.08 : 0.92));
  }

  return {
    isOpen: () => open,
    open: openMap,
    close: closeMap,
    setFly(t) { flyT = t; },
    pose,
    atmosphere,
    sync,
    resize,
    pointerDown,
    pointerMove,
    pointerUp,
    wheel,
    fitDistance: fitDist,
  };
}
