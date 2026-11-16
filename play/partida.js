/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Guarda la partida en la cuenta (el id de la sesión). Si no hay red, queda
   en este aparato y se manda otra vez al reconectar, sin sumar lo ya guardado. */
(() => {
  'use strict';
  const EVERY = 20000;
  let timer = null;
  let last = '';
  let accountId = '';
  let busy = false;

  function key() {
    return 'lifeinc.guardado.v1:' + (accountId || 'local');
  }
  function body() {
    const snap = window.LiveInk && LiveInk.partidaSnapshot ? LiveInk.partidaSnapshot() : null;
    if (!snap) return null;
    snap.rev = Date.now();
    return snap;
  }
  function localSave(raw) {
    try { localStorage.setItem(key(), raw); } catch (e) {}
  }
  function localRead() {
    try { return localStorage.getItem(key()); } catch (e) { return null; }
  }
  function mark(text) {
    let el = document.getElementById('guardado-estado');
    if (!el && document.body) {
      el = document.createElement('div');
      el.id = 'guardado-estado';
      el.setAttribute('role', 'status');
      document.body.append(el);
      const style = document.createElement('style');
      style.textContent = '#guardado-estado{position:fixed;top:8px;left:50%;transform:translateX(-50%);z-index:30;background:#1c3324e6;color:#d7f5c8;border:1px solid #7dcea0;border-radius:999px;padding:3px 8px;font:12px system-ui;pointer-events:none}#guardado-estado[hidden]{display:none}';
      document.head.append(style);
    }
    if (!el) return;
    el.hidden = false;
    el.textContent = text;
    clearTimeout(el._hide);
    if (text === 'Guardado ✓') el._hide = setTimeout(() => { el.hidden = true; }, 2500);
  }
  function noteAccount(saved) {
    if (saved && saved.accountId) accountId = String(saved.accountId);
  }
  async function push(raw) {
    const snap = raw || JSON.stringify(body() || {});
    if (!snap || snap === '{}' || snap === last) return false;
    localSave(snap);
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      mark('Sin red');
      return false;
    }
    let response;
    try {
      response = await fetch('/auth/partida', {
        method: 'POST', credentials: 'same-origin', keepalive: true,
        headers: { 'Content-Type': 'application/json' },
        body: snap,
      });
    } catch (e) {
      mark('Sin red');
      return false;
    }
    if (!response.ok) { mark('Sin red'); return false; }
    let data = null;
    try { data = await response.json(); } catch (e) { data = null; }
    noteAccount(data && data.partida);
    last = snap;
    mark('Guardado ✓');
    return true;
  }
  function touch() {
    clearTimeout(timer);
    timer = setTimeout(() => { push().catch(() => {}); }, 700);
  }
  async function pull() {
    let response;
    try {
      response = await fetch('/auth/partida', { credentials: 'same-origin', cache: 'no-store' });
    } catch (e) {
      return null;
    }
    if (!response.ok) return null;
    const data = await response.json();
    const saved = data && data.partida;
    noteAccount(saved);
    const pending = localRead();
    if (pending && pending !== last) await push(pending);
    if (!saved || !saved.saved) {
      touch();
      return saved || null;
    }
    if (window.LiveInk && LiveInk.applyPartida) LiveInk.applyPartida(saved);
    last = JSON.stringify(body() || saved);
    return saved;
  }
  function flush() {
    const snap = body();
    if (!snap) return;
    const raw = JSON.stringify(snap);
    localSave(raw);
    if (raw === last) return;
    push(raw).catch(() => {});
  }
  setInterval(() => { if (!busy) { busy = true; push().finally(() => { busy = false; }); } }, EVERY);
  if (typeof window !== 'undefined') {
    window.addEventListener('pagehide', flush);
    window.addEventListener('online', () => { push(localRead()).catch(() => {}); });
  }
  window.Partida = { touch, pull, push, flush };
})();
