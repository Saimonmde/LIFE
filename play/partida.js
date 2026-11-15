/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Guarda la partida en la cuenta. Las monedas y la finca no viajan en este paquete. */
(() => {
  'use strict';
  let timer = null;
  let last = '';

  function body() {
    const snap = window.LiveInk && LiveInk.partidaSnapshot ? LiveInk.partidaSnapshot() : null;
    return snap;
  }
  async function push() {
    const snap = body();
    if (!snap) return;
    const raw = JSON.stringify(snap);
    if (raw === last) return;
    const response = await fetch('/auth/partida', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: raw,
    });
    if (!response.ok) return;
    last = raw;
  }
  function touch() {
    clearTimeout(timer);
    timer = setTimeout(() => { push().catch(() => {}); }, 700);
  }
  async function pull() {
    const response = await fetch('/auth/partida', { credentials: 'same-origin', cache: 'no-store' });
    if (!response.ok) return null;
    const data = await response.json();
    const saved = data && data.partida;
    if (!saved || !saved.saved) {
      touch();
      return null;
    }
    if (window.LiveInk && LiveInk.applyPartida) LiveInk.applyPartida(saved);
    last = JSON.stringify(body() || saved);
    return saved;
  }
  window.Partida = { touch, pull, push };
})();
