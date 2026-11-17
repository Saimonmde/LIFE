/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Puma y gavilán. El bulto de la muerte lo confirma el servidor. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.Fauna = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  const GREEN = { grass: 1, grass_flowers: 1, grass_worn: 1 };
  const EXTRA = [[98, 264, 1, 1], [90, 260, 28, 22], [92, 210, 14, 10], [84, 273, 3, 2]];
  const STALK = 18, WARN = 8, BITE = 1.35, LEASH = 24, HIT = 26, PUMA_HP = 100;
  const LANZA = 34, FIST = 10, WARN_S = 1.7, BITE_EVERY = 1.15;
  const FACTS = [
    'El gavilán caminero (Rupornis magnirostris) caza insectos y lagartijas en el suelo, y también planea sobre el parque.',
    'En Antioquia se le ve en bordes de bosque y en postes. No es un animal de jaula.',
    'Las bandas claras de la cola ayudan a reconocerlo cuando da vueltas.',
    'Observar sin perseguir también enseña: el ave sigue su ronda y vos la tuya.',
  ];
  let land = null;
  let pumas = [];
  let pelts = [];
  const SPEAR_NEED = 5;
  let hawks = [];
  let drops = [];
  let remoteAt = 0;
  let dying = false;
  let lastDeath = null;
  let vistaKind = '';
  let applied = {};
  let button = null;
  let nextGrowl = 0;
  let audioCtx = null;

  function ink() { return window.LiveInk || null; }
  function world() { return ink() && ink().world; }
  function state() { return ink() && ink().state; }
  function quiet() { return /(?:^|[?&])autotest=1(?:&|$)/.test(location.search); }
  function me() {
    const S = state();
    return (S && S.me && S.me.name) || '';
  }
  function gear(id) {
    const W = world();
    const spec = W && W.items && W.items[id];
    return !!(spec && spec.category === 'tool');
  }
  function inside(x, y, boxes) {
    const ix = Math.floor(x), iy = Math.floor(y);
    for (const box of boxes) {
      if (ix >= box[0] && iy >= box[1] && ix < box[0] + box[2] && iy < box[1] + box[3]) return true;
    }
    return false;
  }
  function pad(x, y, w, h, extra) {
    return [x - extra, y - extra, w + extra * 2, h + extra * 2];
  }
  function build(W) {
    const boxes = [];
    for (const area of W.areas || []) {
      const id = String(area.id || '');
      if (id === 'plaza' || id === 'pueblo' || id.indexOf('parque_') === 0) boxes.push(pad(area.x, area.y, area.w, area.h, 2));
    }
    for (const region of W.regions || []) {
      if (region.id === 'jardin' || region.id === 'envigado') boxes.push(pad(region.x, region.y, region.w, region.h, 1));
    }
    EXTRA.forEach((box) => boxes.push(box));
    const tiles = W.tiles || {};
    const ok = [];
    for (let y = 0; y < W.height; y++) {
      const row = [];
      for (let x = 0; x < W.width; x++) {
        const blocked = W.collision && W.collision[y] && W.collision[y][x] !== 0;
        const tid = W.ground[y][x];
        const spec = tiles[tid] || tiles[String(tid)] || {};
        row.push(!blocked && !!GREEN[spec.kind] && !inside(x, y, boxes));
      }
      ok.push(row);
    }
    function allowed(x, y) {
      const ix = Math.floor(x), iy = Math.floor(y);
      return iy >= 0 && ix >= 0 && iy < ok.length && ix < ok[0].length && ok[iy][ix];
    }
    const found = [];
    const margin = 16;
    for (let y = margin; y < W.height - margin; y += 7) {
      for (let x = margin; x < W.width - margin; x += 7) if (allowed(x, y)) found.push([x, y]);
    }
    const homes = [];
    if (found.length) homes.push(found[0]);
    while (homes.length < 3 && homes.length < found.length) {
      let best = null, bestD = -1;
      for (const spot of found) {
        let dist = 1e9;
        for (const home of homes) dist = Math.min(dist, Math.hypot(spot[0] - home[0], spot[1] - home[1]));
        if (dist > bestD) { bestD = dist; best = spot; }
      }
      if (!best) break;
      homes.push(best);
    }
    return { width: W.width, height: W.height, boxes, allowed, homes, parks: (W.areas || []).filter((area) => String(area.id || '').indexOf('parque_') === 0) };
  }
  function boot() {
    const W = world();
    if (!W || !W.ground || (W.mapId && W.mapId !== 'city') || W.width < 200) return land;
    if (land && land.width === W.width) return land;
    land = build(W);
    pumas = land.homes.map((spot, i) => ({
      id: 'puma-' + (i + 1), name: 'Puma', x: spot[0], y: spot[1], fx: spot[0], fy: spot[1],
      homeX: spot[0], homeY: spot[1], dir: 'down', mode: 'wander', hp: PUMA_HP, growl: false,
      until: 0, nextHit: 0, goalX: spot[0], goalY: spot[1], goalAt: 0,
    }));
    const centers = land.parks.length ? land.parks : land.homes.map((spot) => ({ x: spot[0], y: spot[1], name: 'monte' }));
    hawks = centers.slice(0, 4).map((park, i) => ({
      id: 'gavilan-' + (i + 1),
      name: 'Gavilán caminero',
      cx: park.x + (park.w || 0) / 2,
      cy: park.y + (park.h || 0) / 2,
      radius: 5 + (i % 3),
      x: park.x + (park.w || 0) / 2,
      y: park.y + (park.h || 0) / 2,
      angle: i * 1.4,
      alt: 8,
      mode: 'circle',
      heading: 0,
      perchAt: 12 + i * 5,
      looked: 0,
    }));
    try { applied = JSON.parse(sessionStorage.getItem('lifeinc.fauna.applied') || '{}'); } catch (e) { applied = {}; }
    return land;
  }
  function remote() {
    const S = state();
    return !!(S && S.net && S.net.ok && performance.now() - remoteAt < 2500);
  }
  function rememberApplied() {
    try { sessionStorage.setItem('lifeinc.fauna.applied', JSON.stringify(applied)); } catch (e) {}
  }
  function takeFromInv(item, qty) {
    const S = state();
    if (!S || !window.quitarDelInventario) return;
    window.quitarDelInventario(item, qty);
  }
  function giveInv(item, qty) {
    const api = ink();
    if (api && api.giveItem) return api.giveItem(item, qty);
    return false;
  }
  function say(html, cls) {
    const api = ink();
    if (api && api.say) api.say(html, cls);
  }
  function note(title, text) {
    const api = ink();
    if (api && api.showNote) api.showNote(title, text);
  }
  function slide(puma, nx, ny) {
    if (!land) return;
    if (land.allowed(nx, ny)) { puma.x = nx; puma.y = ny; return; }
    if (land.allowed(nx, puma.y)) puma.x = nx;
    else if (land.allowed(puma.x, ny)) puma.y = ny;
  }
  function toward(puma, tx, ty, speed, dt) {
    const dx = tx - puma.x, dy = ty - puma.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 1e-4) return dist;
    const step = Math.min(dist, speed * dt);
    slide(puma, puma.x + dx / dist * step, puma.y + dy / dist * step);
    puma.dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up');
    return dist;
  }
  function playerAt() {
    const S = state();
    const W = world();
    if (!S || !W || (W.mapId || 'city') !== 'city') return null;
    return { x: S.player.fx, y: S.player.fy };
  }
  function stepLocal(dt, now) {
    const who = playerAt();
    const safe = who && land && inside(who.x, who.y, land.boxes);
    for (const puma of pumas) {
      puma.growl = false;
      if (puma.hp <= 0) {
        if (now >= (puma.until || 0)) {
          puma.hp = PUMA_HP;
          puma.x = puma.homeX; puma.y = puma.homeY;
          puma.mode = 'wander';
        }
        continue;
      }
      const dist = who && !safe ? Math.hypot(who.x - puma.x, who.y - puma.y) : 99;
      if (puma.mode === 'wander') {
        if (who && !safe && dist <= STALK) puma.mode = 'stalk';
        else {
          if (now >= (puma.goalAt || 0)) {
            const ang = Math.random() * Math.PI * 2;
            const rad = 3 + Math.random() * 7;
            puma.goalX = puma.homeX + Math.cos(ang) * rad;
            puma.goalY = puma.homeY + Math.sin(ang) * rad;
            puma.goalAt = now + 4;
          }
          toward(puma, puma.goalX, puma.goalY, 1.15, dt);
        }
      } else if (puma.mode === 'stalk') {
        if (!who || safe || dist > LEASH) puma.mode = 'wander';
        else if (dist <= WARN) { puma.mode = 'warn'; puma.until = now + WARN_S; puma.growl = true; }
        else toward(puma, who.x, who.y, 1.7, dt);
      } else if (puma.mode === 'warn') {
        puma.growl = true;
        if (who) puma.dir = Math.abs(who.x - puma.x) > Math.abs(who.y - puma.y) ? (who.x > puma.x ? 'right' : 'left') : (who.y > puma.y ? 'down' : 'up');
        if (now >= (puma.until || 0)) puma.mode = who && !safe && dist <= LEASH ? 'charge' : 'wander';
      } else if (puma.mode === 'charge') {
        if (!who || safe || dist > LEASH) puma.mode = 'wander';
        else {
          toward(puma, who.x, who.y, 4.4, dt);
          if (Math.hypot(who.x - puma.x, who.y - puma.y) <= BITE) { puma.mode = 'attack'; puma.nextHit = now; }
        }
      } else if (puma.mode === 'attack') {
        if (!who || safe || dist > 3.2) puma.mode = who && dist <= LEASH ? 'charge' : 'wander';
        else if (!quiet() && now >= (puma.nextHit || 0)) {
          puma.nextHit = now + BITE_EVERY;
          puma.growl = true;
          puma.streak = 0;
          puma.cue = ((puma.cue || 0) + 1) % 3;
          const api = ink();
          if (api && api.damage) api.damage(HIT, 'puma');
        }
      } else puma.mode = 'wander';
    }
  }
  function stepHawks(dt, now) {
    for (const hawk of hawks) {
      if (hawk.mode === 'perch') {
        hawk.alt = 2.5;
        hawk.x = hawk.cx;
        hawk.y = hawk.cy;
        if (now >= hawk.perchAt) { hawk.mode = 'circle'; hawk.perchAt = now + 18 + (hawk.radius % 5); }
      } else {
        hawk.angle += dt * 0.45;
        hawk.x = hawk.cx + Math.cos(hawk.angle) * hawk.radius;
        hawk.y = hawk.cy + Math.sin(hawk.angle) * hawk.radius;
        hawk.alt = 7.2 + Math.sin(now * 0.8 + hawk.angle) * 0.35;
        hawk.heading = hawk.angle + Math.PI / 2;
        if (now >= hawk.perchAt) { hawk.mode = 'perch'; hawk.perchAt = now + 6; }
      }
      hawk.fx = hawk.x;
      hawk.fy = hawk.y;
    }
  }
  function growl(now) {
    const who = playerAt();
    if (!who) return;
    const loud = pumas.some((puma) => puma.growl && Math.hypot(puma.x - who.x, puma.y - who.y) < 16);
    if (!loud || now < nextGrowl) return;
    nextGrowl = now + 1.6;
    say('El <b>puma</b> gruñe. Está por saltar.', 'aviso');
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(90, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(46, audioCtx.currentTime + 0.28);
      gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.08, audioCtx.currentTime + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.42);
      osc.connect(gain); gain.connect(audioCtx.destination);
      osc.start(); osc.stop(audioCtx.currentTime + 0.45);
    } catch (e) {}
  }
  function prompt() {
    if (!button) {
      button = document.createElement('button');
      button.type = 'button';
      button.id = 'fauna-accion';
      button.className = 'hud';
      button.style.cssText = 'position:fixed;left:50%;bottom:138px;transform:translateX(-50%);z-index:16';
      button.onclick = () => act(button.dataset.kind, button.dataset.id);
      document.body.append(button);
    }
    const who = playerAt();
    const S = state();
    if (!who || !S || quiet()) { if (button) button.hidden = true; paintDuel(null); return; }
    const skin = pelts.find((row) => row.yours !== false && Math.hypot(row.x - who.x, row.y - who.y) <= 2.4);
    if (skin) {
      button.hidden = false;
      button.dataset.kind = 'piel';
      button.dataset.id = skin.id;
      button.textContent = 'Recoger piel';
      paintDuel(null);
      return;
    }
    const foe = pumas.find((puma) => puma.hp > 0 && Math.hypot(puma.fx - who.x, puma.fy - who.y) <= 2.8 && puma.mode !== 'wander');
    paintDuel(foe);
    if (foe) {
      button.hidden = true;
      return;
    }
    const sack = drops.find((drop) => drop.owner === me() && Math.hypot(drop.x - who.x, drop.y - who.y) <= 1.8);
    if (sack) {
      button.hidden = false;
      button.dataset.kind = 'recoger';
      button.dataset.id = sack.id;
      button.textContent = 'Recoger';
      return;
    }
    const bird = hawks.find((hawk) => Math.hypot(hawk.x - who.x, hawk.y - who.y) < 5);
    if (bird) {
      button.hidden = false;
      button.dataset.kind = 'observar';
      button.dataset.id = bird.id;
      button.textContent = 'Observar';
      return;
    }
    button.hidden = true;
    paintDuel(null);
  }
  function act(kind, id) {
    if (kind === 'defender') return defend(id);
    if (kind === 'recoger') return pickup(id);
    if (kind === 'piel') return takePelt(id);
    if (kind === 'observar') return observe(id);
  }
  function ensureDuel() {
    let box = document.getElementById('puma-duelo');
    if (box) return box;
    box = document.createElement('section');
    box.id = 'puma-duelo';
    box.hidden = true;
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-label', 'Lanza de caza');
    document.body.append(box);
    return box;
  }
  function paintDuel(puma) {
    const box = ensureDuel();
    if (!puma) { box.hidden = true; box.dataset.key = ''; return; }
    const armed = !!(ink() && ink().holding && ink().holding() === 'lanza');
    const streak = puma.streak || 0;
    const cue = puma.cue || 0;
    const key = puma.id + ':' + streak + ':' + cue + ':' + (armed ? 1 : 0);
    if (box.dataset.key === key && !box.hidden) return;
    box.dataset.key = key;
    const labels = ['Izquierda', 'Centro', 'Derecha'];
    box.hidden = false;
    box.innerHTML = `<p>Puma. Lanza ${streak}/${SPEAR_NEED}. Toca el blanco marcado, sin que te alcance.</p>` +
      (armed ? '' : '<p>Equipa la lanza de caza.</p>') +
      `<div class="puma-blancos">${labels.map((label, index) => `<button type="button" data-lane="${index}" class="${index === cue ? 'is-on' : ''}">${label}</button>`).join('')}</div>`;
    box.querySelectorAll('button').forEach((button) => {
      button.onclick = () => lance(puma.id, Number(button.dataset.lane));
    });
  }
  function lance(id, lane) {
    const S = state();
    const puma = pumas.find((row) => row.id === id);
    const who = playerAt();
    const armed = !!(ink() && ink().holding && ink().holding() === 'lanza');
    if (!armed) { say('Equipa la <b>lanza de caza</b>.', 'aviso'); return; }
    if (!puma || !who || !S) return;
    if (S.net && S.net.ok && S.net.ws) {
      S.net.ws.send(JSON.stringify({ t: 'fauna_lanza', id: id, lane: lane, lanza: true }));
      return;
    }
    if ((puma.cue || 0) !== lane) {
      puma.streak = 0;
      puma.cue = (lane + 1) % 3;
      say('El golpe no dio en el blanco. La tanda vuelve a empezar.', 'aviso');
      paintDuel(puma);
      return;
    }
    puma.streak = (puma.streak || 0) + 1;
    puma.cue = ((puma.cue || 0) + 1) % 3;
    if (puma.streak >= SPEAR_NEED) {
      const x = puma.x, y = puma.y;
      puma.hp = 0;
      puma.streak = 0;
      puma.mode = 'wander';
      puma.until = performance.now() / 1000 + 120;
      puma.x = puma.homeX; puma.y = puma.homeY;
      pelts.push({ id: 'piel-' + Date.now().toString(36), owner: me() || 'local', x: x, y: y, yours: true, local: true, name: 'Piel de puma' });
      say('El puma cayó. Puedes recoger la <b>piel de puma</b>.', 'juego');
      paintDuel(null);
      return;
    }
    say('La lanza dio. Van ' + puma.streak + ' de ' + SPEAR_NEED + '.', 'juego');
    paintDuel(puma);
  }
  function takePelt(id) {
    const row = pelts.find((pelt) => pelt.id === id);
    const S = state();
    if (!row || !S) return;
    if (row.local || !(S.net && S.net.ok && S.net.ws)) {
      giveInv('piel_puma', 1);
      pelts = pelts.filter((pelt) => pelt.id !== id);
      say('Recogiste la <b>piel de puma</b>.', 'juego');
      return;
    }
    S.net.ws.send(JSON.stringify({ t: 'fauna_piel', id: id }));
  }
  function defend(id) {
    const S = state();
    const puma = pumas.find((row) => row.id === id);
    const who = playerAt();
    if (!puma || !who || !S) return;
    const armed = !!(ink() && ink().holding && ink().holding() === 'lanza');
    if (S.net && S.net.ok && S.net.ws) {
      S.net.ws.send(JSON.stringify({ t: 'fauna_golpe', id: id, lanza: armed }));
      return;
    }
    const now = performance.now() / 1000;
    if (now < (puma.swingAt || 0)) return;
    puma.swingAt = now + 0.55;
    puma.hp = Math.max(0, puma.hp - (armed ? LANZA : FIST));
    say(armed ? 'Le clavás la lanza al puma.' : 'Empujás al puma con las manos.', 'juego');
    if (puma.hp <= 0) {
      puma.mode = 'flee';
      puma.until = now + 50;
      puma.x = puma.homeX; puma.y = puma.homeY;
      say('El puma huye al monte.', 'juego');
    } else {
      puma.mode = 'warn';
      puma.until = now + 0.8;
      puma.growl = true;
    }
  }
  function observe(id) {
    const hawk = hawks.find((row) => row.id === id);
    const api = ink();
    if (!hawk || !api || !api.grant) return;
    const now = performance.now() / 1000;
    if (now < (hawk.looked || 0)) {
      say(FACTS[0], 'juego');
      return;
    }
    hawk.looked = now + 90;
    api.grant('gathering', 8);
    say(FACTS[Math.floor(hawk.angle) % FACTS.length], 'oro');
  }
  function onDown() {
    if (dying || quiet()) return;
    dying = true;
    const S = state();
    const api = ink();
    if (!S || !api) { dying = false; return; }
    const x = S.player.fx, y = S.player.fy;
    const lost = [];
    const kept = [];
    (S.inv || []).forEach((slot) => {
      if (!slot) return;
      if (gear(slot.item)) kept.push(slot);
      else lost.push({ item: slot.item, qty: slot.qty });
    });
    const token = 'caida-' + Date.now().toString(36) + '-' + Math.floor(Math.random() * 1e6).toString(36);
    lastDeath = { x: x, y: y, items: lost, token: token };
    S.inv = kept;
    if (api.paintInv) api.paintInv();
    if (api.remember) api.remember();
    S.hp = 100;
    if (S.net && S.net.ok && S.net.ws && lost.length) {
      S._faunaPending = { token: token, items: lost };
      S.net.ws.send(JSON.stringify({ t: 'fauna_morir', x: x, y: y, token: token, items: lost }));
    } else if (lost.length) {
      drops.push({ id: token, owner: me() || 'local', x: x, y: y, items: lost, label: 'Tu mochila', local: true });
    }
    if (api.respawnHome) api.respawnHome();
    S.hp = 100;
    note('Un puma', 'Te atacó un puma. Tus cosas quedaron donde caíste.');
    say('Te atacó un puma. Tus cosas quedaron donde caíste.', 'aviso');
    if (api.remember) api.remember();
    dying = false;
  }
  function confirmDrop(message) {
    const S = state();
    if (!S) return;
    const pending = S._faunaPending;
    if (!message.ok) {
      if (pending && pending.token === message.token && message.reason && message.reason.indexOf('falta') === 0) {
        pending.items.forEach((row) => giveInv(row.item, row.qty));
      }
      S._faunaPending = null;
      return;
    }
    S._faunaPending = null;
    const drop = message.drop;
    if (!drop) return;
    if (!drops.some((row) => row.id === drop.id)) drops.push(Object.assign({ label: 'Tu mochila' }, drop));
  }
  function pickup(id) {
    const drop = drops.find((row) => row.id === id);
    const S = state();
    if (!drop || !S) return;
    if (drop.owner !== me() && !drop.local) {
      say('Esa mochila no es tuya.', 'aviso');
      return;
    }
    if (drop.local) return finishPickup(drop);
    if (S.net && S.net.ok && S.net.ws) S.net.ws.send(JSON.stringify({ t: 'fauna_recoger', id: id }));
  }
  function finishPickup(drop) {
    if (!drop || applied[drop.id] === 'done') {
      drops = drops.filter((row) => !drop || row.id !== drop.id);
      return;
    }
    applied[drop.id] = 'done';
    rememberApplied();
    (drop.items || []).forEach((row) => giveInv(row.item, row.qty));
    drops = drops.filter((row) => row.id !== drop.id);
    say('Recogés tu mochila. El equipo que llevabas puesto sigue contigo.', 'juego');
    const api = ink();
    if (api && api.remember) api.remember();
  }
  function confirmPickup(message) {
    if (!message.ok) {
      say(message.reason || 'No se pudo recoger.', 'aviso');
      return;
    }
    const drop = drops.find((row) => row.id === message.id) || { id: message.id, items: message.items || [] };
    drop.items = message.items || drop.items;
    finishPickup(drop);
  }
  function reconcile(list) {
    const owner = me();
    (list || []).forEach((drop) => {
      if (!drop || drop.owner !== owner || !drop.items || applied[drop.id]) return;
      drop.items.forEach((row) => takeFromInv(row.item, row.qty));
      applied[drop.id] = 'out';
    });
    rememberApplied();
  }
  function applySnapshot(message) {
    if (state() && state().vistaLock) return;
    boot();
    remoteAt = performance.now();
    const seen = new Set();
    (message.pumas || []).forEach((row) => {
      seen.add(row.id);
      let puma = pumas.find((item) => item.id === row.id);
      if (!puma) {
        puma = Object.assign({ fx: row.x, fy: row.y, homeX: row.x, homeY: row.y, hp: PUMA_HP }, row);
        pumas.push(puma);
      } else {
        puma.x = row.x; puma.y = row.y; puma.dir = row.dir; puma.mode = row.mode;
        puma.hp = row.hp; puma.growl = !!row.growl;
        puma.streak = row.streak || 0; puma.cue = row.cue || 0; puma.need = row.need || SPEAR_NEED;
      }
    });
    if ((message.pumas || []).length) pumas = pumas.filter((puma) => seen.has(puma.id) || String(puma.id).indexOf('puma-') !== 0);
    const ids = new Set();
    (message.drops || []).forEach((row) => {
      ids.add(row.id);
      const prev = drops.find((drop) => drop.id === row.id);
      if (prev) Object.assign(prev, row);
      else drops.push(Object.assign({ label: row.owner === me() ? 'Tu mochila' : 'Mochila' }, row));
    });
    drops = drops.filter((drop) => drop.local || ids.has(drop.id));
    if (Array.isArray(message.pelts)) {
      pelts = message.pelts.map((row) => Object.assign({ name: 'Piel de puma' }, row));
    }
    reconcile(message.drops);
  }
  function tick(dt) {
    const W = world();
    if (!W || (W.mapId || 'city') !== 'city') return;
    boot();
    const now = performance.now() / 1000;
    if (state() && state().vistaLock) {
      state().night = false;
      if (vistaKind === 'gavilan') stepHawks(dt, now);
      for (const hawk of hawks) if (vistaKind === 'gavilan') hawk.alt = 2.4;
      for (const puma of pumas) { puma.fx = puma.x; puma.fy = puma.y; }
      return;
    }
    if (!remote()) stepLocal(dt, now);
    else {
      for (const puma of pumas) {
        puma.fx += (puma.x - puma.fx) * Math.min(1, dt * 6);
        puma.fy += (puma.y - puma.fy) * Math.min(1, dt * 6);
      }
    }
    if (!remote()) {
      for (const puma of pumas) { puma.fx = puma.x; puma.fy = puma.y; }
    }
    stepHawks(dt, now);
    growl(now);
    prompt();
  }
  function onNet(message) {
    if (!message || !message.t) return false;
    if (message.t === 'fauna') { applySnapshot(message); return true; }
    if (message.t === 'fauna_dano') {
      const api = ink();
      if (api && api.damage && !quiet()) api.damage(message.amount || HIT, 'puma');
      return true;
    }
    if (message.t === 'fauna_caida') { confirmDrop(message); return true; }
    if (message.t === 'fauna_recoger') { confirmPickup(message); return true; }
    if (message.t === 'fauna_lanza') {
      const puma = pumas.find((row) => row.id === message.id);
      if (puma) {
        puma.streak = message.streak || 0;
        puma.cue = message.cue || 0;
        if (message.dead) puma.hp = 0;
      }
      if (message.reason) say(message.reason, message.hit ? 'juego' : 'aviso');
      return true;
    }
    if (message.t === 'fauna_piel') {
      if (message.ok && message.item) giveInv(message.item, message.qty || 1);
      else if (message.reason) say(message.reason, 'aviso');
      return true;
    }
    if (message.t === 'fauna_golpe' && message.ok) {
      const puma = pumas.find((row) => row.hp);
      say(message.dmg >= 30 ? 'Le clavás la lanza al puma.' : 'Empujás al puma con las manos.', 'juego');
      if (message.hp <= 0) say('El puma huye al monte.', 'juego');
      return true;
    }
    return false;
  }
  function onWelcome(message) {
    if (message && message.fauna) applySnapshot(message.fauna);
  }
  function paintMinimap(ctx, point) {
    if (!ctx || !point) return;
    boot();
    const who = me();
    for (const drop of drops) {
      const at = point(drop.x, drop.y);
      ctx.fillStyle = drop.owner === who ? '#e2b23c' : '#8a6840';
      ctx.strokeStyle = '#2c1a0c';
      ctx.lineWidth = 2;
      ctx.fillRect(at[0] - 4, at[1] - 4, 8, 8);
      ctx.strokeRect(at[0] - 4, at[1] - 4, 8, 8);
    }
    for (const hawk of hawks) {
      const at = point(hawk.x, hawk.y);
      ctx.fillStyle = '#c46a32';
      ctx.beginPath();
      ctx.arc(at[0], at[1], 3, 0, 7);
      ctx.fill();
    }
    for (const puma of pumas) {
      if (puma.hp <= 0) continue;
      const at = point(puma.fx, puma.fy);
      ctx.fillStyle = puma.mode === 'attack' || puma.mode === 'charge' ? '#e23b2f' : '#a34a28';
      ctx.beginPath();
      ctx.moveTo(at[0], at[1] - 6);
      ctx.lineTo(at[0] + 5, at[1] + 4);
      ctx.lineTo(at[0] - 5, at[1] + 4);
      ctx.closePath();
      ctx.fill();
    }
  }
  function present(kind) {
    const api = ink();
    const S = state();
    const W = world();
    if (!api || !S || !W) return;
    vistaKind = kind || 'puma';
    S.vistaLock = true;
    if ((W.mapId || 'city') !== 'city' && api.exitHouse) api.exitHouse();
    land = null;
    pumas = [];
    hawks = [];
    boot();
    const place = (x, y) => { S.player.x = S.player.fx = x; S.player.y = S.player.fy = y; S.player.path = []; };
    let aim = null;
    if (kind === 'saco') {
      const spot = pumas[0] || { x: 160, y: 200 };
      place(spot.x + 1, spot.y);
      if (api.giveItem && !(S.inv || []).some((slot) => slot && slot.item === 'madera')) api.giveItem('madera', 3);
      onDown();
      S.vistaLock = true;
      if ((world().mapId || 'city') !== 'city' && api.exitHouse) api.exitHouse();
      land = null;
      boot();
      if (!drops.length && lastDeath && lastDeath.items && lastDeath.items.length) {
        drops.push({ id: lastDeath.token, owner: me() || 'local', x: lastDeath.x, y: lastDeath.y, items: lastDeath.items, label: 'Tu mochila', local: true });
      }
      const sack = drops[drops.length - 1];
      if (sack) place(sack.x + 1.4, sack.y + 0.2);
      note('Un puma', 'Te atacó un puma. Tus cosas quedaron donde caíste.');
      aim = sack;
    } else if (kind === 'gavilan') {
      const hawk = hawks[0];
      const pad = pumas[0] || { x: 80, y: 120 };
      if (hawk) {
        hawk.cx = pad.x + 5;
        hawk.cy = pad.y;
        hawk.x = hawk.cx;
        hawk.y = hawk.cy;
        hawk.mode = 'circle';
        hawk.radius = 2.2;
        hawk.alt = 2.4;
        hawk.perchAt = performance.now() / 1000 + 40;
        place(hawk.cx + 0.4, hawk.cy + 2.2);
        aim = hawk;
      }
    } else {
      const puma = pumas[0];
      if (puma) {
        puma.mode = 'warn';
        puma.growl = true;
        puma.dir = 'up';
        place(puma.x + 0.2, puma.y + 1.8);
        aim = puma;
      }
    }
    const look = () => {
      if (!window.LIVE3D || !aim) return;
      const ax = aim.x || aim.cx, ay = aim.y || aim.cy;
      window.LIVE3D.lookAt = { x: ax, y: ay - 6 };
      setTimeout(() => {
        if (!window.LIVE3D) return;
        window.LIVE3D.view = { pitch: 1.25, distance: kind === 'movil' ? 11 : 8 };
      }, 40);
    };
    look();
    setTimeout(look, 700);
    setTimeout(look, 1600);
  }
  function animals() { boot(); return { pumas: pumas, hawks: hawks, drops: drops }; }

  return {
    tick, onNet, onWelcome, onDown, paintMinimap, present, animals, boot,
    defend, observe, pickup, lance, paintDuel,
  };
});
