/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Carga con avance, sonido opcional y estado del servidor en la portada. */
(function () {
  'use strict';
  const NativeImage = window.Image;
  let total = 0;
  let done = 0;

  function paint() {
    const bar = document.getElementById('carga-barra');
    const txt = document.getElementById('carga-txt');
    if (!bar) return;
    const pct = total ? Math.max(6, Math.min(100, Math.round(done / total * 100))) : 6;
    bar.style.width = pct + '%';
    if (txt) txt.textContent = pct >= 100 ? 'Entrando a Medellín…' : 'Cargando el valle… ' + pct + '%';
  }

  function settle(mark) {
    return function () {
      if (mark.done) return;
      mark.done = true;
      done += 1;
      paint();
    };
  }

  function track(img) {
    total += 1;
    const mark = { done: false };
    const finish = settle(mark);
    img.addEventListener('load', finish);
    img.addEventListener('error', finish);
    paint();
  }

  function ImageTracked(w, h) {
    const img = arguments.length ? new NativeImage(w, h) : new NativeImage();
    track(img);
    return img;
  }
  ImageTracked.prototype = NativeImage.prototype;
  window.Image = ImageTracked;

  const origFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    const counted = /el-jardin|simulacion\.json|\/graphics\//.test(url);
    if (!counted) return origFetch(input, init);
    total += 1;
    paint();
    const mark = { done: false };
    const finish = settle(mark);
    return origFetch(input, init).then(function (res) { finish(); return res; }, function (err) { finish(); throw err; });
  };

  const KEY = 'lifeinc.sonido.v1';
  let ctx = null;
  let nodes = null;

  function wanted() {
    try { return localStorage.getItem(KEY) === '1'; } catch (e) { return false; }
  }

  function paintSound() {
    const on = wanted();
    const label = on ? 'Sonido: encendido' : 'Sonido: apagado';
    const title = document.getElementById('b-sonido-titulo');
    const hud = document.getElementById('b-sonido');
    if (title) { title.textContent = label; title.setAttribute('aria-pressed', on ? 'true' : 'false'); }
    if (hud) {
      hud.textContent = on ? '♫' : '♪';
      hud.setAttribute('aria-pressed', on ? 'true' : 'false');
      hud.setAttribute('aria-label', label);
      hud.classList.toggle('encendido', on);
    }
  }

  function startPad() {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    if (!ctx) ctx = new AC();
    if (!nodes) {
      const master = ctx.createGain();
      master.gain.value = 0.035;
      const filter = ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.value = 680;
      filter.connect(master);
      master.connect(ctx.destination);
      [220, 277.18, 329.63].forEach(function (freq, i) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = i === 2 ? 'triangle' : 'sine';
        osc.frequency.value = freq;
        gain.gain.value = i === 0 ? 0.55 : 0.28;
        osc.connect(gain);
        gain.connect(filter);
        osc.start();
      });
      nodes = master;
    }
    if (ctx.state === 'suspended') ctx.resume();
  }

  function stopPad() {
    if (ctx && ctx.state === 'running') ctx.suspend();
  }

  function toggleSound() {
    if (wanted() && ctx && ctx.state === 'running') {
      try { localStorage.setItem(KEY, '0'); } catch (e) {}
      stopPad();
    } else {
      try { localStorage.setItem(KEY, '1'); } catch (e) {}
      startPad();
    }
    paintSound();
  }

  function bindSound() {
    ['b-sonido', 'b-sonido-titulo'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el && !el.dataset.sonido) {
        el.dataset.sonido = '1';
        el.addEventListener('click', toggleSound);
      }
    });
    paintSound();
  }

  function serverLine() {
    const el = document.getElementById('login-red');
    if (!el || !window.fetch) return;
    origFetch('/health', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (h) {
      if (!el.isConnected) return;
      if (!h || !h.ok) { el.textContent = 'Sin conexión al servidor'; return; }
      const n = Number(h.playersOnline) || 0;
      el.textContent = n ? 'Servidor en línea · ' + n + ' en el valle' : 'Servidor en línea';
    }).catch(function () {
      if (el.isConnected) el.textContent = 'Sin conexión al servidor';
    });
  }

  function boot() {
    bindSound();
    serverLine();
    paint();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
