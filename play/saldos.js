/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Copia el saldo del servidor a los números que se ven. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.Saldos = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const ZERO = { simoncoin: 0, simonplata: 0, simonchis: 0 };

  function num(value) {
    const n = Number(value);
    return Number.isFinite(n) ? Math.trunc(n) : 0;
  }
  function aplicar(state, msg) {
    state = state || {};
    msg = msg || {};
    const prev = Object.assign({}, ZERO, state.saldos);
    if (msg.walletLocked) {
      state.saldos = Object.assign({}, ZERO);
      const key = state.walletKey || (state.me && state.me.name) || '';
      if (key && state.econ && state.econ.wallets) state.econ.wallets[key] = 0;
      state.plata = Object.assign({}, state.plata, { balanceSph: 0 });
      if (!state.ledger || typeof state.ledger !== 'object') state.ledger = {};
      state.ledger.balances = Object.assign({}, ZERO);
      return { simoncoin: -prev.simoncoin, simonplata: -prev.simonplata, simonchis: -prev.simonchis };
    }
    const balances = (msg.ledger && msg.ledger.balances) || {};
    const next = {
      simoncoin: msg.balanceSubs != null ? num(msg.balanceSubs) : (balances.simoncoin != null ? num(balances.simoncoin) : prev.simoncoin),
      simonplata: msg.balanceSph != null ? num(msg.balanceSph) : (balances.simonplata != null ? num(balances.simonplata) : prev.simonplata),
      simonchis: balances.simonchis != null ? num(balances.simonchis) : prev.simonchis,
    };
    state.saldos = next;
    if (!state.econ) state.econ = { wallets: {} };
    if (!state.econ.wallets) state.econ.wallets = {};
    const key = state.walletKey || (state.me && state.me.name) || '';
    if (key) state.econ.wallets[key] = next.simoncoin;
    state.plata = Object.assign({}, state.plata, { balanceSph: next.simonplata });
    if (!state.ledger || typeof state.ledger !== 'object') state.ledger = {};
    state.ledger.balances = Object.assign({}, next);
    if (msg.historial) state.historial = msg.historial;
    return {
      simoncoin: next.simoncoin - prev.simoncoin,
      simonplata: next.simonplata - prev.simonplata,
      simonchis: next.simonchis - prev.simonchis,
    };
  }
  function recibir(msg) {
    if (typeof window === 'undefined' || !window.__ELJARDIN) return null;
    const delta = aplicar(window.__ELJARDIN, msg);
    if (window.Simulacion && Simulacion.paintHud) Simulacion.paintHud();
    if (window.Cajon && Cajon.paint) Cajon.paint();
    flash(delta);
    pintar();
    return delta;
  }
  function flash(delta) {
    if (typeof document === 'undefined' || !delta) return;
    const up = delta.simoncoin > 0 || delta.simonplata > 0 || delta.simonchis > 0;
    const down = delta.simoncoin < 0 || delta.simonplata < 0 || delta.simonchis < 0;
    const cls = up ? 'saldo-mas' : (down ? 'saldo-menos' : '');
    if (!cls) return;
    for (const id of ['hud-saldos', 'sai-saldo', 'smc-pill-saldo', 'plata-saldo']) {
      const el = document.getElementById(id);
      if (!el) continue;
      el.classList.remove('saldo-mas', 'saldo-menos');
      void el.offsetWidth;
      el.classList.add(cls);
    }
  }
  function texto(base, coin) {
    const n = num(base);
    if (coin === 'simonchis') return n.toLocaleString('es-CO');
    const whole = Math.floor(Math.abs(n) / 100000000);
    const frac = Math.abs(n) % 100000000;
    const sign = n < 0 ? '-' : '';
    if (!frac) return sign + whole.toLocaleString('es-CO');
    return sign + whole.toLocaleString('es-CO') + ',' + String(frac).padStart(8, '0').replace(/0+$/, '');
  }
  function pintar() {
    const box = typeof document !== 'undefined' && document.getElementById('banco-lista');
    if (!box || !window.__ELJARDIN) return;
    const rows = __ELJARDIN.historial || [];
    box.replaceChildren();
    if (!rows.length) {
      const p = document.createElement('p');
      p.textContent = 'Todavía no hay movimientos.';
      box.appendChild(p);
      return;
    }
    for (const row of rows) {
      const p = document.createElement('p');
      const name = row.coin === 'simonplata' ? 'Simonplata' : (row.coin === 'simonchis' ? 'Simonchis' : 'Simoncoin');
      p.textContent = `${row.serial} · ${texto(row.base, row.coin)} ${name} · ${row.note || ''}`;
      box.appendChild(p);
    }
  }
  function ensure() {
    if (typeof document === 'undefined' || document.getElementById('banco-panel')) return;
    const veil = document.createElement('button');
    veil.id = 'banco-fondo';
    veil.type = 'button';
    veil.hidden = true;
    veil.setAttribute('aria-label', 'Cerrar Mi banco');
    const panel = document.createElement('section');
    panel.id = 'banco-panel';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Mi banco');
    panel.innerHTML = '<header><h2>Mi banco / Historial</h2><button type="button" class="x" id="banco-x" aria-label="Cerrar">✕</button></header><div id="banco-lista"></div>';
    document.body.append(veil, panel);
    const close = () => { panel.hidden = true; veil.hidden = true; };
    veil.onclick = close;
    document.getElementById('banco-x').onclick = close;
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !panel.hidden) { close(); e.preventDefault(); }
    });
  }
  function open() {
    ensure();
    const panel = document.getElementById('banco-panel');
    const veil = document.getElementById('banco-fondo');
    if (!panel) return;
    panel.hidden = false;
    veil.hidden = false;
    pintar();
    document.getElementById('banco-x').focus();
  }
  return { aplicar, recibir, open, pintar, texto };
});
