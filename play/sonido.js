/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Efectos de moneda, hechos aquí con el Web Audio API. Sin música ni archivos ajenos. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.Sonido = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const KEY = 'lifeinc.sonido.v1';
  const VOL = 'lifeinc.volumen.v1';
  const PITCH = { oro: 523.25, plata: 783.99, cobre: 392 };
  let ctx = null;
  let armed = false;

  function wanted() {
    try { return localStorage.getItem(KEY) === '1'; } catch (e) { return false; }
  }
  function volume() {
    try {
      const n = Number(localStorage.getItem(VOL));
      if (Number.isFinite(n)) return Math.max(0, Math.min(1, n));
    } catch (e) {}
    return 0.7;
  }
  function setWanted(on) {
    try { localStorage.setItem(KEY, on ? '1' : '0'); } catch (e) {}
    paint();
    if (on) ensure();
    else if (ctx && ctx.state === 'running') ctx.suspend();
  }
  function setVolume(unit) {
    const n = Math.max(0, Math.min(1, Number(unit) || 0));
    try { localStorage.setItem(VOL, String(n)); } catch (e) {}
    paint();
  }
  function isRaw(id) {
    return /^(pepita_|mineral_)/.test(String(id || ''));
  }
  function metalOf(msg) {
    if (!msg || !msg.ok) return '';
    const coin = String(msg.coin || msg.mode || '').toLowerCase();
    if (!coin || coin === 'ingot' || coin.indexOf('lingote') >= 0) return '';
    if (coin.indexOf('plata') >= 0 || coin === 'smp') return 'plata';
    if (coin.indexOf('cobre') >= 0 || coin.indexOf('chis') >= 0) return 'cobre';
    if (coin.indexOf('oro') >= 0 || coin.indexOf('simoncoin') >= 0 || coin === 'smc') return 'oro';
    return '';
  }
  function paint() {
    const on = wanted();
    const label = on ? 'Sonido: encendido' : 'Sonido: apagado';
    const title = document.getElementById('b-sonido-titulo');
    const hud = document.getElementById('b-sonido');
    const gear = document.getElementById('cajon-sonido');
    if (title) { title.textContent = label; title.setAttribute('aria-pressed', on ? 'true' : 'false'); }
    if (gear) { gear.textContent = label; gear.setAttribute('aria-pressed', on ? 'true' : 'false'); }
    if (hud) {
      hud.textContent = on ? '♫' : '♪';
      hud.setAttribute('aria-pressed', on ? 'true' : 'false');
      hud.setAttribute('aria-label', label);
      hud.classList.toggle('encendido', on);
    }
    const pct = String(Math.round(volume() * 100));
    ['sonido-volumen', 'cajon-volumen'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el && document.activeElement !== el) el.value = pct;
    });
  }
  function ensure() {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC || !wanted()) return null;
    if (!ctx) ctx = new AC();
    if (ctx.state === 'suspended') ctx.resume();
    return ctx.state === 'running' ? ctx : null;
  }
  function arm() {
    if (armed || typeof window === 'undefined') return;
    armed = true;
    const kick = function () { if (wanted()) ensure(); };
    window.addEventListener('pointerdown', kick);
    window.addEventListener('keydown', kick);
  }
  function tone(ac, freq, when, dur, gain) {
    const osc = ac.createOscillator();
    const amp = ac.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, when);
    amp.gain.setValueAtTime(0.0001, when);
    amp.gain.exponentialRampToValueAtTime(Math.max(0.0002, gain), when + 0.012);
    amp.gain.exponentialRampToValueAtTime(0.0001, when + dur);
    osc.connect(amp);
    amp.connect(ac.destination);
    osc.start(when);
    osc.stop(when + dur + 0.02);
  }
  function click(ac, when, gain) {
    const len = Math.max(1, Math.floor(ac.sampleRate * 0.025));
    const buf = ac.createBuffer(1, len, ac.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / len);
    const src = ac.createBufferSource();
    const amp = ac.createGain();
    src.buffer = buf;
    amp.gain.setValueAtTime(gain, when);
    amp.gain.exponentialRampToValueAtTime(0.0001, when + 0.03);
    src.connect(amp);
    amp.connect(ac.destination);
    src.start(when);
    src.stop(when + 0.04);
  }
  function chaChing(metal) {
    const kind = PITCH[metal] ? metal : metalOf({ ok: true, coin: metal });
    const base = PITCH[kind] || PITCH.oro;
    const ac = ensure();
    if (!ac) return false;
    const vol = volume();
    if (vol <= 0) return false;
    const t = ac.currentTime;
    click(ac, t, 0.22 * vol);
    tone(ac, base, t + 0.03, 0.16, 0.2 * vol);
    tone(ac, base * 1.498, t + 0.1, kind === 'cobre' ? 0.22 : 0.36, 0.26 * vol);
    if (kind === 'oro') tone(ac, base * 0.5, t + 0.03, 0.28, 0.1 * vol);
    return true;
  }
  function clink() {
    const ac = ensure();
    if (!ac) return false;
    const vol = volume();
    if (vol <= 0) return false;
    const t = ac.currentTime;
    const freq = 1500 + Math.random() * 1100;
    click(ac, t, 0.08 * vol);
    tone(ac, freq, t, 0.04 + Math.random() * 0.035, 0.16 * vol);
    tone(ac, freq * (1.35 + Math.random() * 0.25), t + 0.012, 0.03, 0.06 * vol);
    return true;
  }
  function fromMint(msg) {
    const kind = metalOf(msg);
    if (!kind) return false;
    return chaChing(kind);
  }
  function toggle() {
    const on = !wanted();
    setWanted(on);
    if (on) clink();
  }
  function bind() {
    if (typeof document === 'undefined') return;
    ['b-sonido', 'b-sonido-titulo', 'cajon-sonido'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el && !el.dataset.sonido) {
        el.dataset.sonido = '1';
        el.addEventListener('click', toggle);
      }
    });
    ['sonido-volumen', 'cajon-volumen'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el && !el.dataset.sonido) {
        el.dataset.sonido = '1';
        el.addEventListener('input', function () { setVolume(Number(el.value) / 100); });
      }
    });
    paint();
    arm();
  }
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
    else bind();
  }
  function blip(freq, ms) {
    if (!wanted()) return;
    const ac = ensure();
    if (!ac) return;
    const dur = Math.max(0.12, (Number(ms) || 180) / 1000);
    tone(ac, Number(freq) || 440, ac.currentTime, dur, 0.05 * volume());
  }
  if (typeof window !== 'undefined') window.LifeAudio = { enabled: wanted, tone: blip };
  return { wanted, volume, setWanted, setVolume, isRaw, metalOf, chaChing, clink, fromMint, bind, blip, PITCH };
});
