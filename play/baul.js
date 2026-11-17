/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Baúl de la mina: la misma cuenta que la casa y la Casa bancaria.
   Las cifras las manda el servidor. Aquí no se crean monedas ni objetos. */
(() => {
  'use strict';
  const SWATCH = {
    mineral_oro: 'sw-oro', pepita_oro: 'sw-oro', mineral_plata: 'sw-plata',
    mineral_cobre: 'sw-cobre', piedra: 'sw-piedra', mineral_piedra: 'sw-piedra',
    madera: 'sw-madera', bolsa_cafe: 'sw-cafe', bolsa_cacao: 'sw-cacao',
  };

  let last = null;
  let token = 1;

  function esc(text) {
    return String(text == null ? '' : text).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }
  function panel() { return document.getElementById('baul-mina'); }
  function abierto() { const el = panel(); return !!(el && !el.hidden); }
  function online() {
    const S = window.LiveInk && LiveInk.state;
    const ws = S && S.net && S.net.ws;
    return !!(ws && ws.readyState === 1 && S.net.ok && !S.walletLocked);
  }
  function send(body) {
    const S = window.LiveInk && LiveInk.state;
    const ws = S && S.net && S.net.ws;
    if (!ws || ws.readyState !== 1) return false;
    ws.send(JSON.stringify(body));
    return true;
  }
  function vacio() {
    const cero = { exacto: '0 SMC', compacto: '0 SMC' };
    return {
      smc: { billetera: cero, baul: cero, total: cero, escala: 'Las cantidades se muestran en SMC.', topes: '', tope: '21.000.000 SMC' },
      filas: [],
      totales: { encima: 0, baul: 0, mineral: 0, recurso: 0 },
    };
  }
  function pedir() {
    if (!send({ t: 'baul' })) paint(last || vacio());
  }
  function open() {
    const el = panel();
    if (!el) return;
    el.hidden = false;
    const btn = document.getElementById('baul-abrir');
    if (btn) btn.hidden = true;
    pedir();
  }
  function close() {
    const el = panel();
    if (el) el.hidden = true;
  }
  function mover(op, item, all) {
    if (!online()) return;
    send({ t: 'baul_mover', op: op, item: item || '', all: !!all, qty: all ? 'all' : 1, token: 'b' + (token++) });
  }
  function moverSmc(op, all) {
    if (!online()) return;
    const field = document.getElementById('baul-monto');
    const amount = all ? 'all' : (field && field.value) || '';
    send({ t: 'baul_smc', op: op, all: !!all, amount: amount, token: 's' + (token++) });
  }
  function fila(row) {
    const sw = SWATCH[row.id] || 'sw-otro';
    const buttons = [
      ['deposit', false, 'Guardar'],
      ['deposit', true, 'Guardar todo'],
      ['withdraw', false, 'Sacar'],
      ['withdraw', true, 'Sacar todo'],
    ].map(([op, all, label]) => {
      const off = (op === 'deposit' ? row.encima : row.baul) < 1;
      return `<button type="button" class="baul-btn${all ? ' sec' : ''}" data-op="${op}" data-item="${esc(row.id)}" data-all="${all ? '1' : ''}" ${off ? 'disabled' : ''}>${label}</button>`;
    }).join('');
    return `<div class="baul-fila">
      <div class="baul-nombre"><span class="baul-swatch ${sw}" aria-hidden="true"></span><span>${esc(row.name)}</span></div>
      <div class="baul-nums">Encima ${row.encima}<br>Baúl ${row.baul}<br>Total ${row.total}</div>
      <div class="baul-acciones">${buttons}</div>
    </div>`;
  }
  function grupo(title, rows) {
    const body = rows.length ? rows.map(fila).join('') : '<p class="baul-nota">Nada en esta cuenta.</p>';
    const total = rows.reduce((sum, row) => sum + (row.total || 0), 0);
    return `<section class="baul-grupo"><h3>${esc(title)} · ${total}</h3>${body}</section>`;
  }
  function paint(view) {
    const root = document.getElementById('baul-cuerpo');
    if (!root) return;
    const data = view || vacio();
    last = data;
    const smc = data.smc || vacio().smc;
    const filas = data.filas || [];
    const minerales = filas.filter((row) => row.grupo === 'mineral');
    const recursos = filas.filter((row) => row.grupo !== 'mineral');
    const totales = data.totales || {};
    const linked = online();
    root.innerHTML = `
      <section class="baul-moneda">
        <h3>Simoncoin</h3>
        <div class="baul-total">${esc(smc.total && smc.total.compacto)}</div>
        <p class="baul-exacto">${esc(smc.total && smc.total.exacto)}</p>
        <div class="baul-lados">
          <p class="baul-lado"><b>En la billetera</b>${esc(smc.billetera && smc.billetera.exacto)}</p>
          <p class="baul-lado"><b>En el baúl</b>${esc(smc.baul && smc.baul.exacto)}</p>
        </div>
        <p class="baul-nota">${esc(smc.escala || '')} Tope ${esc(smc.tope || '')}.</p>
        <p class="baul-nota">${esc(smc.topes || '')}</p>
        <div class="baul-acciones">
          <input id="baul-monto" inputmode="decimal" value="1" aria-label="Cantidad de SMC" placeholder="1">
          <button type="button" class="baul-btn" data-smc="deposit" ${linked ? '' : 'disabled'}>Guardar</button>
          <button type="button" class="baul-btn sec" data-smc="withdraw" ${linked ? '' : 'disabled'}>Sacar</button>
          <button type="button" class="baul-btn" data-smc="deposit" data-all="1" ${linked ? '' : 'disabled'}>Guardar todo</button>
          <button type="button" class="baul-btn sec" data-smc="withdraw" data-all="1" ${linked ? '' : 'disabled'}>Sacar todo</button>
        </div>
      </section>
      <div class="baul-listas">${grupo('Minerales', minerales)}${grupo('Recursos', recursos)}</div>
      <p class="baul-nota">Encima ${totales.encima || 0} · Baúl ${totales.baul || 0}. Guardar o sacar no crea nada: el servidor cuenta lo que ya hay.</p>
      <p class="baul-nota" id="baul-estado">${linked ? 'Conectado. Cada pase se guarda en la cuenta.' : 'Sin conexión. El servidor confirma cada pase.'}</p>`;
    root.querySelectorAll('[data-op]').forEach((button) => {
      button.addEventListener('click', () => mover(button.dataset.op, button.dataset.item, button.dataset.all === '1'));
    });
    root.querySelectorAll('[data-smc]').forEach((button) => {
      button.addEventListener('click', () => moverSmc(button.dataset.smc, button.dataset.all === '1'));
    });
  }
  function aplicar(moved) {
    const ink = window.LiveInk;
    if (!ink || !moved) return;
    for (const row of moved) {
      const qty = Number(row.qty) || 0;
      if (qty < 1 || !row.item || row.item === 'smc') continue;
      if (row.op === 'deposit' && ink.takeItem) ink.takeItem(row.item, qty);
      if (row.op === 'withdraw' && ink.giveItem) ink.giveItem(row.item, qty);
    }
  }
  function onNet(message) {
    if (!message || message.t !== 'baul') return false;
    if (message.view) paint(message.view);
    if (message.moved) aplicar(message.moved);
    if (message.reason && window.LiveInk && LiveInk.say) LiveInk.say(message.reason, message.ok ? 'juego' : 'aviso');
    return true;
  }
  function cerca() {
    const ink = window.LiveInk;
    const S = ink && ink.state;
    const world = ink && ink.world && ink.world();
    if (!S || !world || (world.mapId || 'city') !== 'mine' || !S.nodes || !S.nodes.get) return false;
    const node = S.nodes.get('baul_mina');
    if (!node || !node.def || !S.player) return false;
    return Math.max(Math.abs(S.player.x - node.def.x), Math.abs(S.player.y - node.def.y)) <= 2;
  }
  function pulso() {
    const btn = document.getElementById('baul-abrir');
    if (!btn) return;
    const show = cerca() && !abierto();
    btn.hidden = !show;
  }
  const abrir = document.getElementById('baul-abrir');
  if (abrir) abrir.addEventListener('click', open);
  setInterval(pulso, 400);
  window.Baul = { open, close, paint, pedir, onNet, abierto, cerca };
})();
