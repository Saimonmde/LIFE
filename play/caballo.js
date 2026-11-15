/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Caballo criollo: velocidad, pelaje, caballos de la casa y el que sigue en las misiones.
   La malla vive en caballo3d.js. Aquí no hay geometría. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.Caballo = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // Una sola constante: a caballo se va 2,2 veces más rápido que caminando.
  const MOUNT_SPEED = 2.2;
  // El jinete se sienta a esta altura sobre el suelo del mundo (unidades Three.js).
  const SEAT = 1.05;
  const COATS = ['bay', 'grey', 'black'];
  const ALIASES = { bayo: 'bay', gris: 'grey', negro: 'black' };
  const LEGS = ['lh', 'rh', 'lf', 'rf'];
  // Galope transversal de cuatro tiempos: posterior izquierdo, posterior derecho,
  // anterior izquierdo, anterior derecho, y un instante con las cuatro patas en el aire.
  const GAITS = {
    idle: { strike: { lh: 0, lf: 0.5, rh: 0.25, rf: 0.75 }, stance: 1 },
    walk: { strike: { lh: 0, lf: 0.25, rh: 0.5, rf: 0.75 }, stance: 0.62 },
    trot: { strike: { lh: 0, rf: 0, rh: 0.5, lf: 0.5 }, stance: 0.42 },
    gallop: { strike: { lh: 0, rh: 0.22, lf: 0.48, rf: 0.70 }, stance: 0.18 },
  };
  const RATE = { idle: 0.45, walk: 1.05, trot: 1.7, gallop: 2.35 };
  const STORAGE = 'lifeinc.caballo.v1';

  let coat = 'bay';

  function normalizeCoat(value) {
    const key = ALIASES[String(value || '').trim().toLowerCase()] || String(value || '').trim().toLowerCase();
    return COATS.indexOf(key) >= 0 ? key : '';
  }
  function houseCount(id) {
    let hash = 0;
    const text = String(id || '');
    for (let i = 0; i < text.length; i++) hash = (hash * 33 + text.charCodeAt(i)) >>> 0;
    return 1 + (hash % 2);
  }
  function faceToward(spot, stand) {
    const dx = stand.x - spot.x, dy = stand.y - spot.y;
    if (Math.abs(dx) > Math.abs(dy)) return dx > 0 ? 'right' : 'left';
    return dy > 0 ? 'down' : 'up';
  }
  function tetherSpots(houses, open, avoid) {
    const blocked = avoid || new Set();
    const plan = [];
    const order = [[0, 1], [0, -1], [-1, 0], [1, 0], [-1, 1], [1, 1], [-1, -1], [1, -1], [0, 2], [0, -2], [-2, 0], [2, 0], [-2, 1], [2, 1], [-1, 2], [1, 2]];
    for (const house of houses || []) {
      const want = houseCount(house.id);
      const spots = [];
      const used = new Set();
      for (const [dx, dy] of order) {
        if (spots.length >= want) break;
        const x = house.x + dx, y = house.y + dy;
        const key = x + ',' + y;
        if (used.has(key) || blocked.has(key) || (x === house.x && y === house.y)) continue;
        if (open && !open(x, y)) continue;
        used.add(key);
        spots.push({ x: x, y: y, dir: faceToward({ x: x, y: y }, house) });
      }
      plan.push({ id: house.id, name: house.name, x: house.x, y: house.y, spots: spots });
    }
    return plan;
  }
  function onMission(S) {
    if (!S) return false;
    const quest = S.quest;
    if (quest && quest.def && !quest.turnedIn) return true;
    const libro = S.libro;
    return !!(libro && libro.started && !libro.turnedIn);
  }
  function grounded(gait, leg, phase) {
    const spec = GAITS[gait] || GAITS.idle;
    if (gait === 'idle') return true;
    const t = (phase - spec.strike[leg] + 1) % 1;
    return t < spec.stance;
  }
  function legPose(gait, phase, leg) {
    const spec = GAITS[gait] || GAITS.idle;
    if (!gait || gait === 'idle') {
      const wobble = Math.sin((phase || 0) * Math.PI * 2 + leg.charCodeAt(0)) * 0.02;
      return { swing: wobble, lift: 0, knee: leg.charAt(0) === 'h' ? 0.25 : 0.12, grounded: true };
    }
    const t = (phase - spec.strike[leg] + 1) % 1;
    if (t < spec.stance) {
      const u = t / spec.stance;
      return { swing: 0.5 - u, lift: 0, knee: leg.charAt(0) === 'h' ? 0.22 : 0.1, grounded: true };
    }
    const u = (t - spec.stance) / (1 - spec.stance);
    const lift = Math.sin(u * Math.PI);
    return {
      swing: -0.5 + u,
      lift: lift,
      knee: (leg.charAt(0) === 'h' ? 0.25 : 0.12) + lift * (leg.charAt(0) === 'f' ? 1.15 : 0.95),
      grounded: false,
    };
  }
  function strikes(gait) {
    const spec = GAITS[gait];
    return spec ? LEGS.map(leg => spec.strike[leg]) : [];
  }
  function airborneAt(gait, phase) {
    return LEGS.every(leg => !grounded(gait, leg, phase));
  }

  function readLocal() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE) || 'null');
      const next = saved && normalizeCoat(saved.coat);
      if (next) coat = next;
    } catch (e) { /* el pelaje de la cuenta manda si el navegador no guarda */ }
  }
  function writeLocal() {
    try { localStorage.setItem(STORAGE, JSON.stringify({ coat: coat })); } catch (e) { /* privado */ }
  }
  function applyCoat(value) {
    const next = normalizeCoat(value) || 'bay';
    coat = next;
    const horse = personal();
    if (horse) horse.coat = next;
    paintPicker();
    return next;
  }
  function personal() {
    const S = root.LiveInk && root.LiveInk.state;
    return S && S.mounts && S.mounts.find(m => m.personal);
  }
  function paintPicker() {
    const box = document.getElementById('caballo-pelaje');
    if (!box) return;
    box.querySelectorAll('button').forEach(button => button.classList.toggle('sel', button.dataset.coat === coat));
  }
  function mountPicker() {
    if (typeof document === 'undefined' || document.getElementById('caballo-pelaje')) return;
    const anchor = document.getElementById('cajon-llamar');
    if (!anchor) return;
    const box = document.createElement('div');
    box.id = 'caballo-pelaje';
    const label = document.createElement('span');
    label.textContent = 'Pelaje';
    box.append(label);
    for (const [id, name] of [['bay', 'Bayo'], ['grey', 'Gris'], ['black', 'Negro']]) {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.coat = id;
      button.textContent = name;
      button.onclick = () => chooseCoat(id);
      box.append(button);
    }
    anchor.insertAdjacentElement('afterend', box);
    paintPicker();
  }
  async function pullCoat() {
    if (typeof fetch === 'undefined') return;
    try {
      const response = await fetch('/auth/caballo', { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) return;
      const data = await response.json();
      const next = data.caballo && normalizeCoat(data.caballo.coat);
      if (!next) return;
      applyCoat(next);
      writeLocal();
    } catch (e) { /* sin sesión se queda el pelaje de este aparato */ }
  }
  async function chooseCoat(value) {
    const next = applyCoat(value);
    writeLocal();
    if (typeof fetch === 'undefined') return next;
    try {
      await fetch('/auth/caballo', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ coat: next }),
      });
    } catch (e) { /* se reintenta al volver a elegir */ }
    return next;
  }

  function ensurePaddock(S, houses, open, avoid) {
    if (S.paddock) return S.paddock;
    const plan = tetherSpots(houses, open, avoid);
    const paddock = [];
    for (const house of plan) {
      house.spots.forEach((spot, index) => {
        const variant = index === 0 ? 'bay' : (houseCount(house.id + '-b') === 2 ? 'grey' : 'black');
        paddock.push({
          id: 'casa-' + house.id + '-' + index,
          house: house.id,
          decor: true,
          x: spot.x, y: spot.y, fx: spot.x, fy: spot.y,
          dir: spot.dir,
          tethered: true,
          gait: 'idle',
          phase: (index * 0.41) % 1,
          coat: variant,
          hidden: false,
        });
      });
    }
    S.paddock = paddock;
    return paddock;
  }
  function homeSpot(S, houses) {
    const id = S.me && S.me.municipio;
    if (!id || !S.paddock) return null;
    return S.paddock.find(horse => horse.house === id && horse.id.endsWith('-0')) || null;
  }
  function ensurePersonal(S, spot) {
    S.mounts = S.mounts || [];
    let horse = S.mounts.find(m => m.personal);
    if (!horse) {
      const x = spot ? spot.x : S.player.x;
      const y = spot ? spot.y : S.player.y;
      horse = {
        id: 'caballo-personal', personal: true,
        def: { id: 'caballo', name: 'Caballo' },
        x: x, y: y, fx: x, fy: y, ridden: false,
        coat: coat, gait: 'idle', phase: 0.2, tethered: true,
        dir: spot ? spot.dir : 'down', called: false, path: null, goal: null, planAt: 0,
      };
      S.mounts.push(horse);
    }
    horse.coat = coat;
    return horse;
  }
  function hideHomeDuplicate(S) {
    const id = S.me && S.me.municipio;
    const mine = (S.mounts || []).find(m => m.personal);
    for (const horse of S.paddock || []) {
      const slot = id && horse.house === id && horse.id.endsWith('-0');
      horse.hidden = !!(slot && mine);
    }
  }
  function forbidden(S) {
    const tiles = new Set();
    const player = S.player;
    tiles.add(Math.round(player.fx) + ',' + Math.round(player.fy));
    const next = player.path && player.path[0];
    if (next) tiles.add(next[0] + ',' + next[1]);
    return tiles;
  }
  function stepToward(horse, tx, ty, dt, speed, open, banned) {
    let dx = tx - horse.fx, dy = ty - horse.fy;
    const dist = Math.hypot(dx, dy);
    if (dist < 0.05) {
      horse.fx = tx; horse.fy = ty; horse.x = Math.round(tx); horse.y = Math.round(ty);
      return false;
    }
    const step = Math.min(dist, speed * dt);
    const tryMove = (nx, ny) => {
      const tileX = Math.round(nx), tileY = Math.round(ny);
      if (banned && banned.has(tileX + ',' + tileY)) return false;
      if (open && !open(tileX, tileY) && (tileX !== horse.x || tileY !== horse.y)) return false;
      horse.fx = nx; horse.fy = ny; horse.x = tileX; horse.y = tileY;
      if (Math.abs(dx) > 0.04 || Math.abs(dy) > 0.04) {
        horse.dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up');
      }
      return true;
    };
    if (tryMove(horse.fx + dx / dist * step, horse.fy + dy / dist * step)) return true;
    if (Math.abs(dx) >= Math.abs(dy) && tryMove(horse.fx + Math.sign(dx) * step, horse.fy)) return true;
    if (tryMove(horse.fx, horse.fy + Math.sign(dy) * step)) return true;
    return false;
  }
  function shoveOff(horse, S, open) {
    const banned = forbidden(S);
    const key = horse.x + ',' + horse.y;
    if (!banned.has(key)) return;
    const options = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, 1], [1, -1], [-1, -1]];
    for (const [dx, dy] of options) {
      const x = horse.x + dx, y = horse.y + dy;
      if (banned.has(x + ',' + y)) continue;
      if (open && !open(x, y)) continue;
      horse.x = horse.fx = x; horse.y = horse.fy = y;
      return;
    }
  }
  function steer(horse, tx, ty, dt, speed, ctx, now) {
    const open = ctx.open;
    const dist = Math.hypot(tx - horse.fx, ty - horse.fy);
    const end = horse.path && horse.path[horse.path.length - 1];
    const stale = !end || Math.hypot(end[0] - tx, end[1] - ty) > 5;
    if (dist > 6 && stale && ctx.route && now - (horse.planAt || 0) > 0.6) {
      const path = ctx.route(Math.round(horse.fx), Math.round(horse.fy), Math.round(tx), Math.round(ty));
      horse.path = path ? path.slice() : [];
      horse.goal = [tx, ty];
      horse.planAt = now;
    } else if (dist <= 6) {
      horse.path = null;
    }
    let nx = tx, ny = ty;
    if (horse.path && horse.path.length) {
      while (horse.path.length && Math.hypot(horse.path[0][0] - horse.fx, horse.path[0][1] - horse.fy) < 0.4) horse.path.shift();
      if (horse.path[0]) { nx = horse.path[0][0]; ny = horse.path[0][1]; }
    }
    const moving = stepToward(horse, nx, ny, dt, speed, open, forbidden(ctx.S));
    shoveOff(horse, ctx.S, open);
    if (!moving || dist < 0.35) horse.gait = 'idle';
    else if (dist > 8) horse.gait = 'gallop';
    else horse.gait = dist > 3.2 ? 'trot' : 'walk';
    horse.tethered = false;
  }
  function behind(player) {
    const back = { up: [0, 2], down: [0, -2], left: [2, 0], right: [-2, 0] }[player.dir] || [0, -2];
    return [player.fx + back[0], player.fy + back[1]];
  }
  function tick(dt, ctx) {
    const S = ctx && ctx.S;
    if (!S || !S.player) return;
    const houses = ctx.houses || (root.HOGARES && root.HOGARES.casas) || [];
    const avoid = ctx.avoid || new Set();
    ensurePaddock(S, houses, ctx.open, avoid);
    const spot = (S.paddock || []).find(horse => S.me && horse.house === S.me.municipio && horse.id.endsWith('-0'));
    const horse = ensurePersonal(S, spot);
    hideHomeDuplicate(S);
    const now = typeof ctx.now === 'function' ? ctx.now() / 1000 : (ctx.seconds || 0);
    const city = !ctx.W || (ctx.W.mapId || 'city') === 'city';
    if (S.mounted === horse) {
      horse.gait = (S.player.path && S.player.path.length) ? 'gallop' : 'idle';
      horse.tethered = false;
      horse.called = false;
      horse.dir = S.player.dir;
      horse.phase = (horse.phase + dt * (RATE[horse.gait] || 1)) % 1;
    } else if (city && onMission(S)) {
      horse.called = false;
      const goal = behind(S.player);
      const far = Math.hypot(horse.fx - S.player.fx, horse.fy - S.player.fy);
      const speed = far > 8 ? 4.2 * 2 : 4.2 * 1.25;
      steer(horse, goal[0], goal[1], dt, speed, ctx, now);
      horse.phase = (horse.phase + dt * (RATE[horse.gait] || 1)) % 1;
    } else if (city && !horse.called && spot) {
      const home = Math.hypot(horse.fx - spot.x, horse.fy - spot.y) > 0.4;
      if (home) steer(horse, spot.x, spot.y, dt, 4.2 * 1.15, ctx, now);
      else {
        horse.fx = spot.x; horse.fy = spot.y; horse.x = spot.x; horse.y = spot.y;
        horse.gait = 'idle'; horse.tethered = true; horse.dir = spot.dir; horse.path = null;
      }
      horse.phase = (horse.phase + dt * (RATE[horse.gait] || 0.45)) % 1;
    } else {
      horse.gait = 'idle';
      horse.tethered = false;
      horse.phase = (horse.phase + dt * RATE.idle) % 1;
    }
    for (const decor of S.paddock || []) {
      if (decor.hidden) continue;
      decor.gait = 'idle';
      decor.tethered = true;
      decor.phase = (decor.phase + dt * RATE.idle) % 1;
    }
  }
  function noteSummon(horse) {
    if (!horse) return;
    horse.called = true;
    horse.tethered = false;
    horse.path = null;
    horse.gait = 'idle';
  }
  function boot() {
    if (typeof document === 'undefined') return;
    readLocal();
    const style = document.createElement('style');
    style.textContent = '#caballo-pelaje{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0 12px}#caballo-pelaje span{font:600 13px system-ui;color:#f1d69d}#caballo-pelaje button{background:#3a2c1c;color:#f6e2bd;border:1px solid #b39153;border-radius:5px;padding:6px 10px;font:13px system-ui;cursor:pointer}#caballo-pelaje button.sel{outline:2px solid #e2b23c;background:#5a4128}';
    document.head.append(style);
    const tryMount = () => mountPicker();
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', tryMount);
    else tryMount();
    if (document.getElementById('login') || document.getElementById('hud-gear')) setInterval(tryMount, 1500);
    pullCoat();
  }
  if (typeof document !== 'undefined') boot();

  return {
    MOUNT_SPEED: MOUNT_SPEED, SEAT: SEAT, COATS: COATS, GAITS: GAITS, LEGS: LEGS,
    normalizeCoat: normalizeCoat, houseCount: houseCount, tetherSpots: tetherSpots,
    onMission: onMission, legPose: legPose, grounded: grounded, strikes: strikes, airborneAt: airborneAt,
    tick: tick, noteSummon: noteSummon, chooseCoat: chooseCoat, applyCoat: applyCoat,
    get coat() { return coat; },
  };
});
