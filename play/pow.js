/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Panel de minado. La prueba corre en un Worker para no frenar el juego ni el teléfono. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  let worker = null;
  let busy = false;
  const money = (subs) => {
    if (window.Simulacion && Simulacion.formatPair) return Simulacion.formatPair(subs || 0);
    return String(subs || 0);
  };
  function paint(view) {
    const panel = $('#pow-panel');
    if (!panel) return;
    const status = $('#pow-status');
    const cap = $('#pow-cap');
    const left = $('#pow-left');
    const hint = $('#pow-hint');
    if (!view) {
      if (status && !busy) status.textContent = 'Sin prueba en curso.';
      return;
    }
    if (hint && view.hint) hint.textContent = view.hint;
    if (view.guest) {
      if (cap) cap.textContent = `Cuenta nueva, tope de hoy: ${money(view.dailyCapSubs)}.`;
      if (left) left.textContent = 'Invitado: puedes jugar y recoger objetos, no SMC.';
    } else {
      if (cap) cap.textContent = `Tope de hoy: ${money(view.dailyCapSubs)}.`;
      if (left) left.textContent = `Te quedan: ${money(view.remainingSubs)}.`;
      if (view.owedSubs > 0 && left) left.textContent += ` Misión en reserva: ${money(view.owedSubs)}.`;
    }
    if (status && !busy) {
      const bits = view.bits != null ? `Dificultad ${view.bits} bits. ` : '';
      const premio = view.eraRewardSubs != null ? `Premio de la era: ${money(view.eraRewardSubs)}. ` : '';
      const siguiente = view.nextSubs != null && !view.guest ? `La próxima prueba paga como máximo ${money(view.nextSubs)}.` : '';
      status.textContent = `${bits}${premio}${siguiente}`.trim();
    }
    const owed = $('#pow-cobrar');
    if (owed) owed.hidden = !(view.owedSubs > 0);
  }
  function setBusy(text) {
    busy = true;
    const status = $('#pow-status');
    const panel = $('#pow-panel');
    if (panel) panel.hidden = false;
    if (status) status.textContent = text;
  }
  function stop() {
    if (worker) {
      try { worker.postMessage({ stop: true }); worker.terminate(); } catch (e) {}
      worker = null;
    }
    busy = false;
  }
  function solve(challenge, resume) {
    stop();
    setBusy(`Prueba de trabajo en curso. Dificultad ${challenge.bits} bits.`);
    let w;
    try { w = new Worker('pow-worker.js'); }
    catch (e) {
      busy = false;
      const status = $('#pow-status');
      if (status) status.textContent = 'Este navegador no pudo abrir la prueba. Entra desde el servidor.';
      return;
    }
    worker = w;
    w.onmessage = (ev) => {
      const data = ev.data || {};
      if (data.progress) {
        const status = $('#pow-status');
        if (status) status.textContent = `Prueba de trabajo en curso: ${Number(data.tries).toLocaleString('es-CO')} intentos.`;
        return;
      }
      if (!data.ok) return;
      stop();
      const status = $('#pow-status');
      if (status) status.textContent = 'Prueba encontrada. El servidor la está comprobando.';
      const ws = window.Simulacion && Simulacion.net && Simulacion.net();
      if (!ws) {
        if (status) status.textContent = 'No hay conexión para entregar la prueba.';
        return;
      }
      const proof = Object.assign({}, challenge, { nonce: String(data.nonce) });
      ws.send(JSON.stringify(Object.assign({}, resume || {}, { proof })));
    };
    w.postMessage({ payload: challenge.payload, bits: challenge.bits, start: 0 });
  }
  function observe(m) {
    if (!m) return false;
    if (m.supply) {
      if (window.Simulacion && Simulacion.rememberSupply) Simulacion.rememberSupply(m.supply);
      paint(m.supply);
    }
    if (m.t === 'pow_challenge' && m.challenge) {
      solve(m.challenge, m.resume || {});
      return true;
    }
    if (m.t === 'pow_result') {
      stop();
      const status = $('#pow-status');
      if (status) status.textContent = m.reason || (m.ok ? 'Prueba aceptada.' : 'La prueba no sirvió.');
      paint(m.supply);
      return true;
    }
    if (m.t === 'issued' || (m.t === 'quest_result' && m.ok && m.amountSmh)) {
      stop();
      const status = $('#pow-status');
      if (status && m.amountText) status.textContent = `Entraron ${m.amountText}.`;
    }
    return false;
  }
  function boot() {
    const panel = $('#pow-panel');
    if (!panel) return;
    const button = $('#pow-cobrar');
    if (button) button.onclick = () => {
      const ws = window.Simulacion && Simulacion.net && Simulacion.net();
      if (!ws) return;
      ws.send(JSON.stringify({ t: 'quest', id: 'primeros_pasos' }));
    };
    paint(null);
  }
  window.PowMint = { observe, paint, boot };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
