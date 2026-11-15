/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Primer ingreso: el espíritu baja a la casa, toma el cuerpo y deja una guía corta.
   El viaje astral reutiliza el mismo espíritu. El invitado lo recuerda en este aparato;
   la cuenta, en el servidor. */
(() => {
  'use strict';
  const KEY = 'lifeinc.intro.v1';
  const OLD = 'lifeinc.vuelo.v1';
  const STEPS = [
    { id: 'mover', text: 'Muévete con WASD o las flechas.', mobile: 'Mueve el joystick para caminar.', target: '#city-joystick' },
    { id: 'camara', text: 'Gira la vista arrastrando. Acerca con + o la rueda.', mobile: 'Arrastra para girar. Pellizca o toca + para el zoom.', target: '#zoom-in' },
    { id: 'salir', text: 'Sal de la casa: toca la puerta o Salir al Parque.', mobile: 'Sal de la casa: toca la puerta o Salir al Parque.', target: '#b-salir-parque' },
    { id: 'lugares', text: 'Abre el globo o el minimapa para ir a otro lugar.', mobile: 'Abre el globo o el minimapa para ir a otro lugar.', target: '#b-globo' },
    { id: 'viajes', text: 'Viaje astral vuela como espíritu. A caballo sigue el camino.', mobile: 'Viaje astral vuela. A caballo sigue el camino. Están a la derecha.', target: '#b-viaje-astral' },
  ];
  const q = () => new URLSearchParams(location.search);
  let gate = 'off';
  let cine = null;
  let flight = null;
  let guide = null;
  let replay = false;
  let shot = '';
  let raf = 0;
  let focusEl = null;

  function mobile() { return document.documentElement.classList.contains('movil') || innerWidth < 820; }
  function seenLocal() {
    try { return localStorage.getItem(KEY) === '1' || localStorage.getItem(OLD) === '1'; } catch (e) { return false; }
  }
  function player() {
    const p = window.LiveInk && LiveInk.state && LiveInk.state.player;
    if (p) return { x: p.fx, y: p.fy };
    const stand = window.Casa && Casa.PARK_STAND;
    return stand ? { x: stand.x, y: stand.y } : { x: 94, y: 267 };
  }
  function zone() {
    const w = window.LiveInk && LiveInk.world;
    return (w && w.mapId) || 'city';
  }
  function ease(t) { return t * t * (3 - 2 * t); }
  function tone(freq, ms) {
    const audio = window.LifeAudio;
    if (!audio || !audio.enabled || !audio.enabled()) return;
    audio.tone(freq, ms);
  }
  function setLock(on) {
    document.body.classList.toggle('intro-cine', !!on);
    if (window.LiveInk && LiveInk.setIntroLock) LiveInk.setIntroLock(!!on);
  }
  function $(id) { return document.getElementById(id); }

  function stars() {
    const el = $('astral-estrellas');
    if (!el || el.dataset.listo) return;
    const narrow = mobile();
    const n = narrow ? 36 : 56;
    const layers = [];
    for (let i = 0; i < n; i++) {
      const x = (i * 97) % 100;
      const y = (i * 53) % 62;
      const r = i % 9 === 0 ? 2.4 : i % 3 === 0 ? 1.7 : 1.15;
      const tone = i % 8 === 0 ? '#fff4d2' : '#fff';
      layers.push('radial-gradient(circle ' + r + 'px at ' + x + '% ' + y + '%, ' + tone + ' 0 68%, transparent 74%)');
    }
    el.style.backgroundImage = layers.join(',');
    el.style.backgroundRepeat = 'no-repeat';
    el.style.backgroundSize = 'auto';
    el.style.boxShadow = 'none';
    el.dataset.listo = '1';
  }

  function clearFocus() {
    if (focusEl) { focusEl.classList.remove('guia-foco'); focusEl = null; }
    const arrow = $('guia-flecha');
    if (arrow) arrow.hidden = true;
    document.body.classList.remove('guia-camara');
  }
  function clearVisual() {
    cine = null;
    flight = null;
    guide = null;
    clearFocus();
    setLock(false);
    const sky = $('astral-cielo');
    if (sky) { sky.classList.remove('visto'); sky.hidden = true; }
    const fig = $('astral-espiritu');
    if (fig) fig.hidden = true;
    const pulso = $('astral-pulso');
    if (pulso) pulso.classList.remove('late');
    const skip = $('astral-saltar');
    if (skip) skip.hidden = true;
    const box = $('guia');
    if (box) box.hidden = true;
    if (window.LIVE3D) LIVE3D.spirit = null;
    document.body.dataset.intro = '';
  }

  function remember() {
    if (shot) return;
    try { localStorage.setItem(KEY, '1'); localStorage.setItem(OLD, '1'); } catch (e) {}
    document.dispatchEvent(new CustomEvent('life-intro-done'));
  }
  function release() {
    gate = 'off';
    if (window.LiveInk && LiveInk.refreshTutorial) LiveInk.refreshTutorial();
  }
  function finish() {
    clearVisual();
    remember();
    release();
  }
  function abort() {
    clearVisual();
    gate = 'off';
  }

  function loop() {
    tick(performance.now());
    raf = requestAnimationFrame(loop);
  }
  function ensureLoop() { if (!raf) raf = requestAnimationFrame(loop); }

  function cineSpirit(t, narrow) {
    const p = player();
    const high = narrow ? 9 : 13;
    let lift = high, alpha = 0.72, pulse = 0.12, hide = true, pitch = 1.15, dist = narrow ? 16 : 22;
    if (t >= 0.22 && t < 0.75) {
      const e = ease((t - 0.22) / 0.53);
      lift = high * (1 - e) + 0.25 * e;
      pulse = 0;
      pitch = 1.15 * (1 - e) + 0.72 * e;
      dist = (narrow ? 16 : 22) * (1 - e) + (narrow ? 13 : 15) * e;
    } else if (t >= 0.75) {
      const u = (t - 0.75) / 0.25;
      lift = 0.25 * (1 - u);
      alpha = 0.7 * (1 - u);
      pulse = Math.sin(Math.min(1, u) * Math.PI);
      hide = false;
      pitch = 0.72;
      dist = narrow ? 13 : 15;
    }
    return {
      x: p.x, y: p.y, lift, alpha, pulse, hideBody: hide,
      cam: { yaw: Math.PI - 0.28, pitch, distance: dist, x: p.x, y: p.y, lift: Math.min(lift, 3) },
    };
  }
  function paintCine(t) {
    stars();
    const sky = $('astral-cielo');
    const fig = $('astral-espiritu');
    const pulso = $('astral-pulso');
    const skip = $('astral-saltar');
    if (sky) {
      sky.hidden = false;
      const fade = t < 0.18 ? 1 : t < 0.7 ? 1 - (t - 0.18) / 0.52 : 0;
      sky.style.opacity = String(Math.max(0, fade));
      sky.classList.toggle('visto', fade > 0.04);
    }
    const gl = window.LIVE3D && LIVE3D.frames > 2 && t > 0.4;
    if (fig) {
      fig.hidden = !!gl;
      const y = t < 0.22 ? 16 : t < 0.75 ? 16 + ((t - 0.22) / 0.53) * 40 : 58;
      fig.style.top = y + '%';
      fig.style.opacity = String(t < 0.8 ? 0.95 : Math.max(0, 1 - (t - 0.8) / 0.2));
    }
    if (pulso) pulso.classList.toggle('late', t >= 0.78 && t < 0.98);
    if (skip) skip.hidden = false;
    if (t > 0.04 && cine && !cine.s1) { cine.s1 = 1; tone(196, 880); }
    if (t > 0.32 && cine && cine.s1 < 2) { cine.s1 = 2; tone(247, 640); }
    if (t > 0.8 && cine && cine.s1 < 3) { cine.s1 = 3; tone(392, 420); }
    document.body.dataset.intro = t < 0.22 ? 'cielo' : t < 0.75 ? 'descenso' : 'posesion';
  }
  function startCine(hold) {
    gate = 'cine';
    guide = null;
    const box = $('guia');
    if (box) box.hidden = true;
    setLock(true);
    const narrow = mobile();
    cine = { t0: performance.now(), dur: narrow ? 6500 : 8500, hold: hold, s1: 0 };
    ensureLoop();
  }
  function endCine() {
    cine = null;
    setLock(false);
    const sky = $('astral-cielo');
    if (sky) { sky.classList.remove('visto'); sky.style.opacity = '0'; sky.hidden = true; }
    const fig = $('astral-espiritu');
    if (fig) fig.hidden = true;
    if (window.LIVE3D) {
      LIVE3D.spirit = null;
      LIVE3D.view = { yaw: Math.PI - 0.28, pitch: 0.72, distance: mobile() ? 13 : 15 };
    }
    if (shot && shot !== 'full') return;
    startGuide(0, false);
  }

  function flightSpirit(t, narrow) {
    const e = ease(t);
    const x = flight.from.x + (flight.to.x - flight.from.x) * e;
    const y = flight.from.y + (flight.to.y - flight.from.y) * e;
    const dist = Math.hypot(flight.to.x - flight.from.x, flight.to.y - flight.from.y);
    const arc = Math.sin(Math.min(1, t) * Math.PI) * Math.min(narrow ? 14 : 26, 8 + dist * 0.05);
    const land = t > 0.86;
    return {
      x, y, lift: land ? arc * (1 - (t - 0.86) / 0.14) : arc,
      alpha: land ? 0.7 * (1 - (t - 0.86) / 0.14) : 0.7,
      pulse: land ? Math.sin((t - 0.86) / 0.14 * Math.PI) : 0.08,
      hideBody: !land,
      cam: { yaw: 0.45 + t * 0.5, pitch: narrow ? 0.9 : 0.82, distance: (narrow ? 16 : 22) + arc * 0.35, x, y, lift: Math.min(arc, 6) },
    };
  }
  function startFlight(from, to, done, hold) {
    const narrow = mobile();
    const dist = Math.hypot(to.x - from.x, to.y - from.y);
    flight = { from, to, t0: performance.now(), dur: Math.max(1500, Math.min(narrow ? 2800 : 4200, dist * 26)), done, hold, snd: 0 };
    if (window.LiveInk && LiveInk.setIntroLock) LiveInk.setIntroLock(true);
    tone(220, 500);
    ensureLoop();
    document.body.dataset.intro = 'astral';
  }
  function endFlight() {
    const done = flight && flight.done;
    flight = null;
    if (window.LIVE3D) LIVE3D.spirit = null;
    if (window.LiveInk && LiveInk.setIntroLock) LiveInk.setIntroLock(false);
    tone(349, 280);
    if (done) done();
  }

  function placeArrow() {
    const arrow = $('guia-flecha');
    if (!guide || !arrow) return;
    const step = STEPS[guide.i];
    const el = document.querySelector(step.target);
    if (!el || el.offsetParent === null && getComputedStyle(el).display === 'none') {
      arrow.hidden = true;
      return;
    }
    if (focusEl !== el) {
      if (focusEl) focusEl.classList.remove('guia-foco');
      el.classList.add('guia-foco');
      focusEl = el;
    }
    const r = el.getBoundingClientRect();
    arrow.hidden = false;
    arrow.style.left = (r.left + r.width / 2) + 'px';
    arrow.style.top = (r.top + r.height / 2) + 'px';
  }
  function showStep() {
    const box = $('guia');
    const txt = $('guia-txt');
    const step = STEPS[guide.i];
    if (!box || !step) return;
    box.hidden = false;
    if (txt) txt.textContent = mobile() ? step.mobile : step.text;
    document.body.classList.toggle('guia-camara', step.id === 'camara');
    document.body.dataset.intro = 'guia-' + step.id;
    const skip = $('astral-saltar');
    if (skip) skip.hidden = true;
    if (step.id === 'camara' && window.LIVE3D && LIVE3D.camera) guide.cam = Object.assign({}, LIVE3D.camera);
    if (step.id === 'mover') guide.origin = player();
    placeArrow();
  }
  function startGuide(index, hold) {
    gate = 'guide';
    setLock(false);
    guide = { i: index, hold: !!hold, origin: player(), cam: window.LIVE3D && LIVE3D.camera ? Object.assign({}, LIVE3D.camera) : null, sawMap: false, sawViaje: false };
    showStep();
    ensureLoop();
  }
  function nextStep() {
    if (!guide) return;
    if (guide.i >= STEPS.length - 1) { finish(); return; }
    guide.i += 1;
    showStep();
  }
  function checkGuide() {
    if (!guide || guide.hold) return;
    const id = STEPS[guide.i].id;
    const p = player();
    if (id === 'mover' && guide.origin && Math.max(Math.abs(p.x - guide.origin.x), Math.abs(p.y - guide.origin.y)) >= 1) nextStep();
    else if (id === 'camara' && guide.cam && window.LIVE3D && LIVE3D.camera) {
      const c = LIVE3D.camera;
      if (Math.abs(c.distance - guide.cam.distance) > 1.2 || Math.abs(c.yaw - guide.cam.yaw) > 0.08 || Math.abs(c.pitch - guide.cam.pitch) > 0.06) nextStep();
    } else if (id === 'salir' && zone() !== 'casa') nextStep();
    else if (id === 'lugares' && guide.sawMap) nextStep();
    else if (id === 'viajes' && guide.sawViaje) nextStep();
  }

  function tick() {
    const narrow = mobile();
    if (cine) {
      let t = Math.min(1, (performance.now() - cine.t0) / cine.dur);
      if (cine.hold != null) t = cine.hold;
      paintCine(t);
      if (window.LIVE3D) LIVE3D.spirit = cineSpirit(t, narrow);
      if (cine.hold == null && t >= 1) endCine();
    } else if (flight) {
      let t = Math.min(1, (performance.now() - flight.t0) / flight.dur);
      if (flight.hold != null) t = flight.hold;
      if (window.LIVE3D) LIVE3D.spirit = flightSpirit(t, narrow);
      document.body.dataset.intro = 'astral';
      const fig = $('astral-espiritu');
      const gl = window.LIVE3D && LIVE3D.frames > 2;
      if (fig) {
        fig.hidden = !!(gl && flight.hold == null);
        fig.style.left = (16 + t * 58) + '%';
        fig.style.top = (46 - Math.sin(Math.min(1, t) * Math.PI) * 24) + '%';
      }
      if (flight.hold == null && t >= 1) endFlight();
    } else if (window.LIVE3D && LIVE3D.spirit && !guide) LIVE3D.spirit = null;
    if (guide) { checkGuide(); placeArrow(); }
  }

  function begin(mode) {
    shot = mode === 'full' ? '' : mode;
    replay = false;
    if (mode === 'full') { shot = ''; startCine(null); return; }
    if (mode === 'cielo') return startCine(0.12);
    if (mode === 'descenso') return startCine(0.48);
    if (mode === 'posesion') return startCine(0.86);
    const idx = STEPS.findIndex(s => s.id === mode);
    if (idx >= 0) { setLock(false); startGuide(idx, true); return; }
    if (mode === 'astral') {
      setTimeout(() => {
        if (zone() === 'casa' && window.LiveInk && LiveInk.exitHouse) LiveInk.exitHouse();
        const from = player();
        startFlight(from, { x: 130, y: 196 }, () => {}, 0.45);
        document.body.dataset.intro = 'astral';
      }, 600);
      return;
    }
    if (mode === 'caballo') {
      setTimeout(() => {
        if (zone() === 'casa' && window.LiveInk && LiveInk.exitHouse) LiveInk.exitHouse();
        if (window.Simulacion && Simulacion.summonAndMount) Simulacion.summonAndMount();
        if (window.LiveInk && LiveInk.openTravelMenu) LiveInk.openTravelMenu('caballo');
        document.body.dataset.intro = 'caballo';
      }, 700);
    }
  }

  function consider() {
    const query = q();
    if (query.has('autotest') || query.has('forja')) { gate = 'off'; return; }
    const forced = query.get('intro');
    if (forced) { gate = 'cine'; begin(forced); return; }
    gate = 'wait';
    const local = seenLocal();
    fetch('/auth/sesion', { cache: 'no-store' }).then(r => r.ok ? r.json() : {}).then(data => {
      if (gate === 'off' && !replay) return;
      const user = data && data.user;
      if (user && user.introSeen) { release(); return; }
      if (user && !user.introSeen) { begin('full'); return; }
      if (local) { release(); return; }
      begin('full');
    }).catch(() => {
      if (local) release();
      else begin('full');
    });
  }

  function playArrival(msg) {
    const from = zone() === 'city' ? player() : { x: (window.Casa && Casa.PARK_STAND && Casa.PARK_STAND.x) || 94, y: (window.Casa && Casa.PARK_STAND && Casa.PARK_STAND.y) || 267 };
    startFlight(from, { x: msg.x, y: msg.y }, () => {
      if (window.LiveInk && LiveInk.finishAstral) LiveInk.finishAstral(msg);
      if (guide) guide.sawViaje = true;
    }, null);
  }

  document.addEventListener('click', (event) => {
    const t = event.target;
    if (!(t instanceof Element)) return;
    if (t.id === 'astral-saltar' || t.id === 'guia-saltar') { finish(); return; }
    if (t.id === 'b-globo' || t.id === 'minimapa' || t.closest('#hud-mapa')) { if (guide) guide.sawMap = true; }
    if (t.id === 'b-viaje-astral' || t.id === 'b-viaje-caballo' || t.closest('#viaje-menu')) { if (guide) guide.sawViaje = true; }
  });
  document.addEventListener('life-viaje', () => { if (guide) guide.sawViaje = true; });

  window.Intro = {
    consider, replay() { replay = true; shot = ''; if (window.LiveInk && LiveInk.goHomeForIntro) LiveInk.goHomeForIntro(); begin('full'); },
    abort, blocking() { return gate === 'wait' || gate === 'cine' || gate === 'guide' || gate === 'play'; },
    holdPlace() { return !!(flight || (shot === 'astral' || shot === 'caballo')); },
    playArrival, fly: startFlight,
  };
})();
