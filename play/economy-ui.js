/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Intercambio entre dos personas. El protocolo vive en tools/trades.py. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const api = () => window.LiveInk;
  let session = null;
  let dirty = false;
  let pending = false;
  let returnFocus = null;

  const dock = document.createElement('button');
  dock.id = 'bank-dock';
  dock.type = 'button';
  dock.className = 'hud';
  dock.innerHTML = '<span class="coin-medallion" aria-hidden="true">S</span><span>Banco e inventario<strong id="bank-dock-balance">Ver depósito</strong></span>';
  document.body.append(dock);

  const panel = document.createElement('dialog');
  panel.id = 'coin-trade';
  panel.className = 'economy-dialog';
  panel.setAttribute('aria-labelledby', 'trade-title');
  panel.innerHTML = `
    <header><div><small>SAIMON CITY · INTERCAMBIO</small><h2 id="trade-title">Intercambiar</h2></div>
    <button id="trade-close" type="button" aria-label="Cancelar intercambio">×</button></header>
    <div class="economy-body">
      <p class="trade-notice">Pasa Simoncoin de billetera a billetera. No hay puesto, banco ni comisión, y no se crean monedas. Las dos aceptan y después confirman. Hace falta estar a 30 m, en la ciudad o en la mina, con la billetera desbloqueada. Se escribe con hasta 2 decimales. Las partes no salen en el libro público.</p>
      <ol class="trade-steps"><li id="trade-step-one">1 · Preparar oferta</li><li id="trade-step-two">2 · Revisar y confirmar</li></ol>
      <div class="trade-columns">
        <article>
          <h3>Tu oferta</h3>
          <p id="trade-available"></p>
          <label for="trade-smc">Simoncoin</label>
          <input id="trade-smc" inputmode="decimal" value="0" autocomplete="off" placeholder="1,50">
          <div id="trade-items"></div>
          <button id="trade-update" type="button">Actualizar oferta</button>
          <strong id="trade-mine">—</strong>
          <p id="trade-own-status"></p>
        </article>
        <article>
          <h3 id="trade-peer">Otra persona</h3>
          <strong id="trade-theirs">—</strong>
          <p id="trade-other-status"></p>
        </article>
      </div>
      <p id="trade-review" aria-live="polite"></p>
      <div class="economy-actions">
        <button id="trade-accept" class="primary" type="button">Aceptar oferta</button>
        <button id="trade-confirm" class="primary" type="button" hidden>Confirmar intercambio definitivo</button>
        <button id="trade-cancel" type="button">Cancelar</button>
      </div>
      <p id="trade-status" role="status" aria-live="polite"></p>
    </div>`;
  document.body.append(panel);

  function money(n) {
    return window.Simulacion && Simulacion.formatSmc ? Simulacion.formatSmc(n || 0) : (n || 0) + ' SMC';
  }
  function offerOf(raw) {
    if (!raw || typeof raw !== 'object') return { smc: Number(raw) || 0, smp: 0, cobre: 0, items: {} };
    return { smc: raw.smc || 0, smp: raw.smp || 0, cobre: raw.cobre || 0, items: raw.items || {} };
  }
  function describe(offer) {
    const o = offerOf(offer);
    const bits = [money(o.smc)];
    const names = (api()?.state?.purse?.catalog) || { bolsa_cafe: 'Bolsa de café', bolsa_cacao: 'Bolsa de cacao' };
    for (const [id, qty] of Object.entries(o.items)) {
      if (qty) bits.push(qty + ' ' + (names[id] || id));
    }
    return bits.join(' · ');
  }
  function send(obj) {
    const S = api()?.state;
    if (!S?.net.ok || S.net.ws?.readyState !== 1) throw Error('Sin conexión al servidor. No se envió la operación.');
    S.net.ws.send(JSON.stringify(obj));
  }
  function action(t, extra) {
    if (!session) return;
    send(Object.assign({ t, id: session.id, revision: session.revision }, extra || {}));
    pending = true;
    render();
  }
  function close() {
    if (panel.open) panel.close();
    session = null;
    pending = false;
    dirty = false;
    if (returnFocus && returnFocus.focus) returnFocus.focus({ preventScroll: true });
  }
  function cancel() {
    if (session) {
      try { action('trade_cancel'); } catch (e) { $('#trade-status').textContent = e.message; }
    }
    close();
  }
  function stage(id) {
    if (session.confirmed.includes(id)) return 'Confirmación final recibida';
    if (session.accepted.includes(id)) return 'Primera aceptación recibida';
    return 'Esperando aceptación';
  }
  function holdings() {
    const S = api().state;
    const smh = Simulacion.walletSubs(S.me.name);
    const bag = (S.purse && S.purse.items) || {};
    return 'Tuyo: ' + (Simulacion.formatSmc ? Simulacion.formatSmc(smh) : money(smh))
      + (Object.keys(bag).length ? '' : ' · sin bolsas en la mochila del servidor');
  }
  function renderItems() {
    const box = $('#trade-items');
    const bag = (api()?.state?.purse?.items) || {};
    const names = (api()?.state?.purse?.catalog) || { bolsa_cafe: 'Bolsa de café', bolsa_cacao: 'Bolsa de cacao' };
    const ids = Object.keys(bag);
    box.replaceChildren();
    if (!ids.length) {
      const p = document.createElement('p');
      p.textContent = 'Las bolsas de café y de cacao aparecen aquí cuando el servidor las acredita.';
      box.append(p);
      return;
    }
    for (const id of ids) {
      const label = document.createElement('label');
      label.htmlFor = 'trade-item-' + id;
      label.textContent = (names[id] || id) + ' (tienes ' + bag[id] + ')';
      const input = document.createElement('input');
      input.id = 'trade-item-' + id;
      input.dataset.item = id;
      input.inputMode = 'numeric';
      input.value = '0';
      input.autocomplete = 'off';
      input.oninput = markDirty;
      box.append(label, input);
    }
  }
  function render() {
    if (!session) return;
    const S = api().state;
    const me = S.net.id;
    const other = session.players.find(p => p.id !== me) || session.players[0];
    const review = session.accepted.length === 2;
    $('#trade-peer').textContent = other?.name || 'Otra persona';
    $('#trade-available').textContent = holdings();
    $('#trade-mine').textContent = describe(session.offers[String(me)]);
    $('#trade-theirs').textContent = describe(session.offers[String(other.id)]);
    $('#trade-own-status').textContent = stage(me);
    $('#trade-other-status').textContent = stage(other.id);
    $('#trade-step-one').classList.toggle('current', !review);
    $('#trade-step-two').classList.toggle('current', review);
    $('#trade-accept').hidden = review;
    $('#trade-confirm').hidden = !review;
    $('#trade-accept').disabled = pending || dirty || session.accepted.includes(me);
    $('#trade-confirm').disabled = pending || dirty || session.confirmed.includes(me);
    $('#trade-update').disabled = pending || !dirty;
    const locked = session.confirmed.includes(me);
    $('#trade-smc').readOnly = locked;
    $('#trade-review').textContent = 'Versión ' + session.revision + ': entregas ' + describe(session.offers[String(me)])
      + ' y recibes ' + describe(session.offers[String(other.id)]) + '. '
      + (review ? 'Revisa ambas columnas antes de confirmar.' : 'No se mueve nada hasta las dos confirmaciones.');
  }
  function markDirty() {
    dirty = true;
    if (session) {
      render();
      $('#trade-status').textContent = 'Oferta sin enviar. Actualízala antes de aceptar.';
    }
  }
  function readSmc(raw) {
    const text = String(raw || '0').trim();
    if (!text) return 0;
    if (/smh|simonchi/i.test(text)) return Simulacion.parseAmount(text);
    return Simulacion.parseAmount(/smc/i.test(text) ? text : text + ' SMC');
  }
  function readOffer() {
    const smc = readSmc($('#trade-smc').value);
    if (!Number.isSafeInteger(smc) || smc < 0) throw Error('Simoncoin no válida.');
    const smp = 0;
    const cobre = 0;
    const items = {};
    panel.querySelectorAll('[data-item]').forEach(input => {
      const qty = Number(input.value || '0');
      if (!Number.isSafeInteger(qty) || qty < 0) throw Error('Cantidad de objeto no válida.');
      if (qty) items[input.dataset.item] = qty;
    });
    return { smc, smp, cobre, items };
  }
  function openTrade(peer) {
    if (!api()?.started) return;
    try {
      if (session) {
        $('#trade-status').textContent = 'Cancela el intercambio actual antes de abrir otro.';
        return;
      }
      send({ t: 'trade_start', peer: Number(peer) });
    } catch (e) {
      const status = $('#rest-status');
      if (status) status.textContent = e.message;
    }
  }
  function fillInputs(offer) {
    const o = offerOf(offer);
    const whole = (n, unit) => {
      const subs = unit;
      if (!n) return '0';
      if (n % subs === 0) return String(n / subs);
      return String(n / subs);
    };
    $('#trade-smc').value = whole(o.smc, Simulacion.SUBS || 100);
    panel.querySelectorAll('[data-item]').forEach(input => {
      input.value = String((o.items && o.items[input.dataset.item]) || 0);
    });
  }
  function aplicarSaldos(box) {
    const S = api() && api().state;
    if (!S || !box) return;
    S.ledger = S.ledger || {};
    S.ledger.balances = Object.assign({}, S.ledger.balances || {}, {
      simoncoin: box.smc || 0,
      simonplata: box.smp || 0,
      simonchis: box.cobre || 0,
    });
    S.plata = S.plata || {};
    S.plata.balanceSph = box.smp || 0;
    if (S.econ && S.econ.wallets && S.me && S.me.name) S.econ.wallets[S.me.name] = box.smc || 0;
    if (window.Simulacion && Simulacion.paintHud) Simulacion.paintHud();
    if (window.Cajon) Cajon.paint();
  }
  function onNet(m) {
    if (!m.t || !m.t.startsWith('trade_')) return false;
    if (m.t === 'trade_state') {
      const previous = session;
      const first = !session;
      session = m;
      pending = false;
      dirty = false;
      if (first) renderItems();
      fillInputs(m.offers[String(api().state.net.id)]);
      $('#trade-status').textContent = previous && previous.revision !== m.revision
        ? 'Oferta modificada: las aceptaciones anteriores quedaron anuladas.'
        : 'Esperando a ambas personas.';
      if (!panel.open) {
        returnFocus = document.activeElement;
        api().state.keys.clear();
        api().state.player.path = [];
        panel.showModal();
      }
      render();
    } else if (m.t === 'trade_error') {
      pending = false;
      $('#trade-status').textContent = m.reason;
      if (!session && $('#rest-status')) $('#rest-status').textContent = m.reason;
      render();
    } else if (m.t === 'trade_end') {
      if (session && m.id !== session.id) return true;
      close();
      if (m.ok && m.balances) aplicarSaldos(m.balances);
      if ($('#rest-status')) $('#rest-status').textContent = m.reason || '';
      if (m.reason && typeof game === 'function') game(m.reason, m.ok ? 'juego' : 'aviso');
      if (m.reason && m.reason.indexOf('Tu mochila está llena') >= 0 && window.avisarMochilaLlena) window.avisarMochilaLlena();
      if (window.Banco) Banco.paint();
      if (window.Cajon) Cajon.paint();
    }
    return true;
  }
  panel.addEventListener('keydown', (e) => e.stopPropagation());
  $('#trade-smc').oninput = markDirty;
  $('#trade-update').onclick = () => {
    try { action('trade_offer', { offer: readOffer() }); }
    catch (e) { $('#trade-status').textContent = e.message; }
  };
  $('#trade-accept').onclick = () => action('trade_accept');
  $('#trade-confirm').onclick = () => action('trade_confirm');
  $('#trade-close').onclick = cancel;
  $('#trade-cancel').onclick = cancel;
  panel.addEventListener('cancel', (e) => { e.preventDefault(); cancel(); });
  $('#cercanos')?.addEventListener('click', (e) => {
    const button = e.target.closest('[data-trade-peer]');
    if (button) openTrade(button.dataset.tradePeer);
  });
  dock.onclick = () => { if (api()?.started && window.Banco) Banco.openPanel(); };
  window.TradeUI = { openTrade, onNet, cancel, close };
})();
