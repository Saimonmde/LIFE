/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Reloj de Bogotá y cuenta hasta el reinicio del minado.
   La hora de corte llega del servidor (resetAt). Aquí no se inventa otra. */
(() => {
  'use strict';
  let resetAt = 0;
  let serverBase = 0;
  let clientBase = 0;
  let seenServer = 0;
  let asked = 0;

  function pad(n) {
    n = Math.max(0, Math.floor(n));
    return (n < 10 ? '0' : '') + n;
  }
  function clock(total) {
    const sec = Math.max(0, Math.floor(total));
    return pad(Math.floor(sec / 3600)) + ':' + pad(Math.floor(sec / 60) % 60) + ':' + pad(sec % 60);
  }
  function state() {
    return (window.LiveInk && LiveInk.state) || window.__ELJARDIN || null;
  }
  function world() {
    return (window.LiveInk && LiveInk.world) || null;
  }
  function sync(nowMs, serverSec) {
    if (!serverSec) return;
    serverBase = serverSec * 1000;
    clientBase = nowMs;
  }
  function serverNow() {
    const S = state();
    const reloj = S && S.reloj;
    const stamp = reloj && Number(reloj.serverNow);
    if (stamp && stamp !== seenServer) {
      seenServer = stamp;
      sync(Date.now(), stamp);
    }
    if (!serverBase) return Date.now();
    return serverBase + (Date.now() - clientBase);
  }
  function takeReset(value) {
    const next = Number(value);
    if (next > 0) resetAt = next;
  }
  function pull() {
    const S = state();
    if (S && S.cupos && S.cupos.resetAt) takeReset(S.cupos.resetAt);
    if (resetAt && Date.now() - asked < 60000) return;
    asked = Date.now();
    fetch('/reglas-mina', { cache: 'no-store', credentials: 'same-origin' }).then((r) => r.json()).then((body) => {
      takeReset(body && body.resetAt);
      if (body && body.serverNow) sync(Date.now(), Number(body.serverNow));
    }).catch(() => {});
  }
  function hora(ms) {
    try {
      return new Intl.DateTimeFormat('es-CO', {
        timeZone: 'America/Bogota', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
      }).format(new Date(ms));
    } catch (e) {
      const bogota = new Date(ms - 5 * 3600 * 1000);
      return pad(bogota.getUTCHours()) + ':' + pad(bogota.getUTCMinutes()) + ':' + pad(bogota.getUTCSeconds());
    }
  }
  function nearMineOrGold(S, W) {
    if (!S || !S.player || !S.nodes) return false;
    for (const n of S.nodes.values()) {
      if (!n.def) continue;
      const gold = n.def.type === 'nodo_oro_fluvial';
      const own = n.def.type === 'mineral_rock' && n.def.mundo;
      if (!gold && !own) continue;
      const dist = Math.max(Math.abs(S.player.x - n.def.x), Math.abs(S.player.y - n.def.y));
      if (dist <= (gold ? 4 : 3)) return true;
    }
    if (W && (W.mapId || 'city') === 'city') {
      for (const id of ['entrada_mina_palmas', 'entrada_mina_ladera']) {
        const door = S.nodes.get(id);
        if (!door) continue;
        const dist = Math.max(Math.abs(S.player.x - door.def.x), Math.abs(S.player.y - door.def.y));
        if (dist <= 5) return true;
      }
    }
    return false;
  }
  function capHit(S) {
    if (!S) return false;
    const supply = S.supply || {};
    if (supply.remainingSubs != null && Number(supply.remainingSubs) <= 0 && !supply.guest) return true;
    const coins = S.cupos && S.cupos.coins;
    if (!coins) return false;
    const gold = coins.simoncoin;
    const copper = coins.simonchis;
    if (gold && gold.left != null && Number(gold.left) <= 0) return true;
    if (copper && copper.left != null && Number(copper.left) <= 0) return true;
    return false;
  }
  function showNow() {
    const S = state();
    const W = world();
    if (!S || !W || !document.body.classList.contains('in-game')) return false;
    const map = W.mapId || 'city';
    if (map === 'mine' || map === 'mina2') return true;
    if (capHit(S)) return true;
    return nearMineOrGold(S, W);
  }
  function veinLeft() {
    const S = state();
    const tick = window.LiveInk && LiveInk.now ? LiveInk.now() : 0;
    if (!S || !S.nodes || !tick) return 0;
    let best = 0;
    for (const n of S.nodes.values()) {
      const kind = n.def && n.def.type;
      if (kind !== 'mineral_rock' && kind !== 'nodo_oro_fluvial') continue;
      if (!n.until || n.until <= tick) continue;
      const left = (n.until - tick) / 1000;
      if (left > 0 && (!best || left < best)) best = left;
    }
    return best;
  }
  function ensure() {
    let box = document.getElementById('reloj-mina');
    if (box) return box;
    box = document.createElement('aside');
    box.id = 'reloj-mina';
    box.hidden = true;
    box.setAttribute('aria-live', 'polite');
    box.innerHTML = '<p id="reloj-mina-hora"></p><p id="reloj-mina-dia"></p><p id="reloj-mina-veta" hidden></p>';
    document.body.append(box);
    return box;
  }
  function paint() {
    const box = ensure();
    const visible = showNow();
    box.hidden = !visible;
    if (!visible) return;
    pull();
    const nowMs = serverNow();
    const horaEl = document.getElementById('reloj-mina-hora');
    const diaEl = document.getElementById('reloj-mina-dia');
    const vetaEl = document.getElementById('reloj-mina-veta');
    if (horaEl) horaEl.textContent = 'Ahora ' + hora(nowMs);
    if (diaEl) {
      if (resetAt) {
        const left = Math.max(0, resetAt * 1000 - nowMs) / 1000;
        diaEl.textContent = 'Minado se restablece en ' + clock(left);
        if (left <= 0) { resetAt = 0; asked = 0; pull(); }
      } else {
        diaEl.textContent = 'Consultando la hora de restablecimiento…';
      }
    }
    const vein = veinLeft();
    if (vetaEl) {
      vetaEl.hidden = !(vein > 0);
      if (vein > 0) vetaEl.textContent = 'La veta vuelve en ' + clock(vein);
    }
  }
  function boot() {
    ensure();
    pull();
    setInterval(paint, 1000);
    paint();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
