/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Seguir a otra persona: posición, estado, rastro y caminar detrás. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  let target = null;
  let trail = [];
  let auto = false;
  let lastWalk = 0;

  const chip = document.createElement('section');
  chip.id = 'seguir-chip';
  chip.hidden = true;
  chip.innerHTML = [
    '<p id="seguir-texto"></p>',
    '<label><input id="seguir-auto" type="checkbox"> Caminar detrás</label>',
    '<button type="button" id="seguir-dejar">Dejar de seguir</button>',
  ].join('');
  document.body.append(chip);

  function send(obj) {
    const S = window.__ELJARDIN;
    const ws = S && S.net && S.net.ws;
    if (!ws || ws.readyState !== 1) return;
    ws.send(JSON.stringify(obj));
  }
  function meters(other) {
    const S = window.__ELJARDIN;
    if (!S || !other) return 0;
    const tile = (S.world && S.world.render && S.world.render.metersPerTile) || 2;
    return Math.round(Math.hypot((other.fx || other.x || 0) - S.player.fx, (other.fy || other.y || 0) - S.player.fy) * tile);
  }
  function estado(other) {
    if (!other) return 'quieto';
    if (other.zone === 'casa' || other.pace === 'casa') return 'en casa';
    if (other.pace === 'caballo' || other.mounted) return 'a caballo';
    if (other.pace === 'corriendo') return 'corriendo';
    if (other.pace === 'caminando' || other.moving) return 'caminando';
    return 'quieto';
  }
  function paint() {
    if (!target) { chip.hidden = true; return; }
    const S = window.__ELJARDIN;
    const other = S && S.others && S.others.get(target.id);
    const where = other || target;
    chip.hidden = false;
    $('seguir-texto').textContent = target.nick + ' · ' + estado(where) + ' · ' + meters(where) + ' m';
    $('seguir-auto').checked = auto;
  }
  function empezar(person) {
    if (!person || !person.id) return;
    target = { id: Number(person.id), nick: person.nick || 'Viajero', key: person.key || '' };
    trail = [];
    auto = false;
    send({ t: 'seguir', id: target.id });
    paint();
  }
  function soltar() {
    if (!target) return;
    send({ t: 'dejar_seguir', id: target.id });
    target = null;
    trail = [];
    auto = false;
    paint();
  }
  function paso(other) {
    if (!target || !other || other.id !== target.id) return;
    const x = Number(other.fx != null ? other.fx : other.x);
    const y = Number(other.fy != null ? other.fy : other.y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    const last = trail[trail.length - 1];
    if (!last || Math.hypot(last[0] - x, last[1] - y) > 0.35) {
      trail.push([x, y]);
      if (trail.length > 24) trail.shift();
    }
    paint();
  }
  function vista() {
    if (!target) return null;
    const S = window.__ELJARDIN;
    const other = S && S.others && S.others.get(target.id);
    if (!other) return { x: null, y: null, trail: trail.slice(), name: target.nick, state: 'en casa', meters: 0 };
    return {
      x: other.fx, y: other.fy, trail: trail.slice(),
      name: target.nick, state: estado(other), meters: meters(other),
    };
  }
  function tick() {
    if (!target || !auto) return;
    const S = window.__ELJARDIN;
    if (!S || !S.net || !S.net.ok) return;
    if (S.keys && S.keys.has('joystick')) { soltar(); return; }
    const other = S.others && S.others.get(target.id);
    if (!other || other.zone === 'casa') return;
    const now = performance.now();
    if (now - lastWalk < 700) return;
    const far = Math.hypot(other.fx - S.player.fx, other.fy - S.player.fy);
    if (far < 2.2) return;
    lastWalk = now;
    if (window.LiveInk && LiveInk.setRoute) LiveInk.setRoute(other.fx, other.fy, target.nick);
  }
  function dibujar(ctx, point) {
    const view = vista();
    if (!view || view.x == null || !ctx || !point) return;
    ctx.save();
    ctx.setLineDash([2, 4]);
    ctx.strokeStyle = '#7fd0ff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    view.trail.forEach((pt, index) => {
      const [x, y] = point(pt[0], pt[1]);
      if (index) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    });
    ctx.stroke();
    ctx.restore();
    const [x, y] = point(view.x, view.y);
    ctx.fillStyle = '#7fd0ff';
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#f4fbff';
    ctx.font = '700 11px system-ui, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(view.name + ' · ' + view.state, x + 7, y);
  }
  $('seguir-dejar').onclick = soltar;
  $('seguir-auto').onchange = () => { auto = $('seguir-auto').checked; };
  setInterval(tick, 400);
  window.Seguir = { empezar, soltar, paso, vista, dibujar, paint };
})();
