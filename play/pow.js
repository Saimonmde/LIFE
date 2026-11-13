/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Paneles de minado. La prueba corre en un Worker para no frenar el juego ni el teléfono. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  let worker = null;
  let busy = false;
  let busyCoin = '';
  let plataView = null;
  const money = (subs) => {
    if (window.Simulacion && Simulacion.formatPair) return Simulacion.formatPair(subs || 0);
    return String(subs || 0);
  };
  const plataMoney = (sph) => {
    if (window.Simulacion && Simulacion.formatPlataPair) return Simulacion.formatPlataPair(sph || 0);
    return String(sph || 0);
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
    if (status && !(busy && busyCoin !== 'SMP')) {
      const bits = view.bits != null ? `Dificultad ${view.bits} bits. ` : '';
      const premio = view.eraRewardSubs != null ? `Premio de la era: ${money(view.eraRewardSubs)}. ` : '';
      const siguiente = view.nextSubs != null && !view.guest ? `La próxima prueba paga como máximo ${money(view.nextSubs)}.` : '';
      status.textContent = `${bits}${premio}${siguiente}`.trim();
    }
    const owed = $('#pow-cobrar');
    if (owed) owed.hidden = !(view.owedSubs > 0);
  }
  function paintPlata(view) {
    if (view) plataView = view;
    view = view || plataView;
    const panel = $('#plata-panel');
    if (!panel || !view) return;
    if (window.Simulacion && Simulacion.rememberPlata) Simulacion.rememberPlata(view);
    const status = $('#plata-status');
    const cap = $('#plata-cap');
    const left = $('#plata-left');
    const hint = $('#plata-hint');
    const tasa = $('#plata-tasa');
    const fondo = $('#plata-fondo');
    const xcap = $('#plata-xcap');
    const meter = $('#plata-meter');
    const bar = $('#plata-meter-bar');
    if (hint && view.hint) hint.textContent = view.hint;
    if (tasa) tasa.textContent = `${view.rateText || '100 SMP = 1 SMC'}. ${view.shareText || 'La Plata se quema y el SMC sale del fondo ya emitido.'}`;
    if (view.guest) {
      if (cap) cap.textContent = `Cuenta nueva, tope de hoy: ${plataMoney(view.dailyCapSph)}.`;
      if (left) left.textContent = 'Invitado: puedes jugar y recoger objetos, no Plata.';
      if (xcap) xcap.textContent = 'Puedes cambiar hoy: nada, hace falta una cuenta.';
    } else {
      if (cap) cap.textContent = `Tope de hoy: ${plataMoney(view.dailyCapSph)}.`;
      if (left) left.textContent = `Te quedan: ${plataMoney(view.remainingSph)}.`;
      if (xcap) xcap.textContent = `Puedes cambiar hoy: ${money(view.exchangeLeftSmh)}.`;
    }
    if (fondo) fondo.textContent = `Fondo: ${money(view.poolSmh)}. De ahí sale el SMC. Hoy no se crea oro.`;
    const max = Number(view.dailyCapSph) || 0;
    const earned = Number(view.earnedSph) || 0;
    const pct = max > 0 ? Math.max(0, Math.min(100, Math.round((earned / max) * 100))) : 0;
    if (bar) bar.style.width = pct + '%';
    if (meter) meter.setAttribute('aria-valuenow', String(pct));
    if (status && !(busy && busyCoin === 'SMP')) {
      const bits = view.bits != null ? `Dificultad ${view.bits} bits. ` : '';
      const premio = view.eraRewardSph != null ? `Premio de la era: ${plataMoney(view.eraRewardSph)}. ` : '';
      const siguiente = view.nextSph != null && !view.guest ? `La próxima prueba paga como máximo ${plataMoney(view.nextSph)}.` : '';
      status.textContent = `${bits}${premio}${siguiente}`.trim();
    }
    preview();
  }
  function preview() {
    const box = $('#cambio-preview');
    const input = $('#cambio-monto');
    if (!box || !input || !window.Simulacion || !Simulacion.parsePlata) return;
    let sph = 0;
    try { sph = Simulacion.parsePlata(input.value); } catch (e) { sph = 0; }
    const nominal = Math.floor((Number(sph) || 0) / 100);
    const left = plataView && plataView.exchangeLeftSmh != null ? Number(plataView.exchangeLeftSmh) : nominal;
    const capped = Math.max(0, Math.min(nominal, left));
    if (nominal <= 0) box.textContent = 'Hacen falta 100 platicas (SPH) por cada Simonchi (SMH).';
    else if (capped < nominal) box.textContent = `A 100 SMP = 1 SMC serían ${money(nominal)}. Hoy el fondo te deja ${money(capped)}. La Plata se quema.`;
    else box.textContent = `Entregas ${plataMoney(nominal * 100)}. Recibes ${money(nominal)}. La Plata se quema.`;
  }
  function setBusy(text, coin) {
    busy = true;
    busyCoin = coin || '';
    const status = coin === 'SMP' ? $('#plata-status') : $('#pow-status');
    const panel = coin === 'SMP' ? $('#plata-panel') : $('#pow-panel');
    if (panel) panel.hidden = false;
    if (status) status.textContent = text;
  }
  function stop() {
    if (worker) {
      try { worker.postMessage({ stop: true }); worker.terminate(); } catch (e) {}
      worker = null;
    }
    busy = false;
    busyCoin = '';
  }
  function solve(challenge, resume) {
    const coin = challenge.coin === 'SMP' ? 'SMP' : 'SMC';
    stop();
    setBusy(`Prueba de ${coin === 'SMP' ? 'Plata' : 'SMC'} en curso. Dificultad ${challenge.bits} bits.`, coin);
    let w;
    try { w = new Worker('pow-worker.js'); }
    catch (e) {
      busy = false;
      const status = coin === 'SMP' ? $('#plata-status') : $('#pow-status');
      if (status) status.textContent = 'Este navegador no pudo abrir la prueba. Entra desde el servidor.';
      return;
    }
    worker = w;
    w.onmessage = (ev) => {
      const data = ev.data || {};
      if (data.progress) {
        const status = coin === 'SMP' ? $('#plata-status') : $('#pow-status');
        if (status) status.textContent = `Prueba de ${coin === 'SMP' ? 'Plata' : 'SMC'} en curso: ${Number(data.tries).toLocaleString('es-CO')} intentos.`;
        return;
      }
      if (!data.ok) return;
      stop();
      const status = coin === 'SMP' ? $('#plata-status') : $('#pow-status');
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
  function sendExchange(max) {
    const ws = window.Simulacion && Simulacion.net && Simulacion.net();
    const box = $('#cambio-result');
    if (!ws) {
      if (box) box.textContent = 'No hay conexión para cambiar.';
      return;
    }
    if (max) {
      ws.send(JSON.stringify({ t: 'exchange_plata', max: true }));
      return;
    }
    let sph = 0;
    try { sph = Simulacion.parsePlata(($('#cambio-monto') || {}).value || ''); }
    catch (e) { sph = 0; }
    ws.send(JSON.stringify({ t: 'exchange_plata', sph: sph }));
  }
  function observe(m) {
    if (!m) return false;
    if (m.supply) {
      if (window.Simulacion && Simulacion.rememberSupply) Simulacion.rememberSupply(m.supply);
      paint(m.supply);
    }
    if (m.plata) paintPlata(m.plata);
    if (m.t === 'pow_challenge' && m.challenge) {
      solve(m.challenge, m.resume || {});
      return true;
    }
    if (m.t === 'pow_result' || m.t === 'plata_result') {
      stop();
      const status = m.coin === 'SMP' || m.t === 'plata_result' ? $('#plata-status') : $('#pow-status');
      if (status) status.textContent = m.reason || (m.ok ? 'Prueba aceptada.' : 'La prueba no sirvió.');
      if (m.supply) paint(m.supply);
      if (m.plata) paintPlata(m.plata);
      return true;
    }
    if (m.t === 'exchange_result') {
      const box = $('#cambio-result');
      if (box) box.textContent = m.reason || (m.ok ? 'Cambio hecho.' : 'No se pudo cambiar.');
      if (m.plata) paintPlata(m.plata);
      return true;
    }
    if (m.t === 'issued' || (m.t === 'quest_result' && m.ok && m.amountSmh)) {
      stop();
      const status = m.coin === 'SMP' ? $('#plata-status') : $('#pow-status');
      if (status && m.amountText) status.textContent = `Entraron ${m.amountText}.`;
    }
    return false;
  }
  function boot() {
    const button = $('#pow-cobrar');
    if (button) button.onclick = () => {
      const ws = window.Simulacion && Simulacion.net && Simulacion.net();
      if (!ws) return;
      ws.send(JSON.stringify({ t: 'quest', id: 'primeros_pasos' }));
    };
    const mine = $('#pow-plata');
    if (mine) mine.onclick = () => {
      const ws = window.Simulacion && Simulacion.net && Simulacion.net();
      if (!ws) return;
      ws.send(JSON.stringify({ t: 'mint_plata' }));
    };
    const change = $('#pow-cambiar');
    if (change) change.onclick = () => sendExchange(false);
    const all = $('#pow-cambiar-max');
    if (all) all.onclick = () => sendExchange(true);
    const input = $('#cambio-monto');
    if (input) input.addEventListener('input', preview);
    paint(null);
    preview();
  }
  window.PowMint = { observe, paint, paintPlata, boot };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
