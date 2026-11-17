/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Intercambio entre dos personas. El protocolo vive en tools/trades.py. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const api = () => window.LiveInk;
  const BLOCKED = new Set([
    'guacharaca', 'ortalis', 'ortal',
    'smc', 'smp', 'smh', 'sph',
    'simoncoin', 'simonplata', 'simonchis',
    'sai', 'plata', 'cobre_moneda',
    'libro', 'xp', 'wallet', 'libro_mayor',
  ]);
  const METALES = ['pepita_oro', 'mineral_oro', 'mineral_plata', 'mineral_cobre'];
  const GRUPOS = ['Simoncoin', 'Minerales', 'Lingotes', 'Monedas acuñadas', 'Cosechas', 'Otros'];
  const CONOCIDOS = {
    pepita_oro: { name: 'Pepita de oro', cat: 'Minerales', icon: 'graphics/icons/64/pepita_oro.png' },
    mineral_oro: { name: 'Oro crudo', cat: 'Minerales', icon: 'graphics/mining/mineral_oro.svg' },
    mineral_plata: { name: 'Plata cruda', cat: 'Minerales', icon: 'graphics/mining/mineral_plata.svg' },
    mineral_cobre: { name: 'Cobre crudo', cat: 'Minerales', icon: 'graphics/mining/mineral_cobre.svg' },
    lingote_oro: { name: 'Lingote de oro', cat: 'Lingotes', icon: 'graphics/mining/lingote_oro.svg' },
    lingote_plata: { name: 'Lingote de plata', cat: 'Lingotes', icon: 'graphics/mining/lingote_plata.svg' },
    lingote_cobre: { name: 'Lingote de cobre', cat: 'Lingotes', icon: 'graphics/mining/lingote_cobre.svg' },
    moneda_plata: { name: 'Moneda de plata', cat: 'Monedas acuñadas', icon: 'graphics/mining/moneda_plata.svg' },
    moneda_cobre: { name: 'Moneda de cobre', cat: 'Monedas acuñadas', icon: 'graphics/mining/moneda_cobre.svg' },
    bolsa_cafe: { name: 'Café', cat: 'Cosechas', icon: 'graphics/ui/bolsa.png' },
    bolsa_cacao: { name: 'Cacao', cat: 'Cosechas', icon: 'graphics/ui/bolsa.png' },
  };
  let session = null;
  let dirty = false;
  let pending = false;
  let returnFocus = null;
  let selected = 'simoncoin';
  let draft = { smc: '0', items: {} };
  let gridKey = '';

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
    <header><div><small>SAIMON CITY</small><h2 id="trade-title">Trueque</h2></div>
    <button id="trade-close" type="button" aria-label="Cancelar intercambio">×</button></header>
    <div class="economy-body">
      <p class="trade-notice">No se crean monedas. Los dos aceptan y después confirman.</p>
      <div class="trade-columns">
        <article id="trade-doy">
          <h3>Doy</h3>
          <p id="trade-own-status"></p>
          <div id="trade-grid"></div>
          <div class="trade-stepper">
            <button type="button" id="trade-menos" aria-label="Restar">−</button>
            <input id="trade-qty" inputmode="decimal" value="0" autocomplete="off" aria-label="Cantidad">
            <button type="button" id="trade-mas" aria-label="Sumar">+</button>
            <button type="button" id="trade-uno">1</button>
            <button type="button" id="trade-x">X</button>
            <button type="button" id="trade-max">Todo</button>
          </div>
          <p id="trade-elegido"></p>
          <button id="trade-update" type="button">Enviar oferta</button>
        </article>
        <article id="trade-recibo">
          <h3 id="trade-peer">Recibo</h3>
          <p id="trade-other-status"></p>
          <div id="trade-theirs-grid"></div>
        </article>
      </div>
      <p id="trade-review" aria-live="polite"></p>
      <div class="economy-actions">
        <button id="trade-accept" class="primary" type="button">Aceptar</button>
        <button id="trade-confirm" class="primary" type="button" hidden>Confirmar</button>
        <button id="trade-cancel" type="button">Cancelar</button>
      </div>
      <p id="trade-status" role="status" aria-live="polite"></p>
    </div>`;
  document.body.append(panel);

  function money(n) {
    return window.Simulacion && Simulacion.formatSmc ? Simulacion.formatSmc(n || 0) : (n || 0) + ' SMC';
  }
  function srcOf(path) {
    if (!path) return '';
    if (/^(?:\.\.\/|https?:|data:)/.test(path)) return path;
    return '../' + String(path).replace(/^\//, '');
  }
  function meta(id) {
    const world = api() && (api().world || (api().state && api().state.world));
    const it = world && world.items && world.items[id];
    const known = CONOCIDOS[id] || {};
    const catalog = (api()?.state?.purse?.catalog) || {};
    const icon = (it && it.icon && (it.icon['64'] || it.icon['32'])) || known.icon || '';
    return {
      name: (it && it.name) || catalog[id] || known.name || id,
      cat: known.cat || 'Otros',
      icon: srcOf(icon),
    };
  }
  function walletSmh() {
    const S = api() && api().state;
    if (!S || !window.Simulacion || !Simulacion.walletSubs) return 0;
    return Math.max(0, Number(Simulacion.walletSubs(S.me && S.me.name)) || 0);
  }
  function maxSmc() {
    const subs = window.Simulacion && Simulacion.SUBS ? Simulacion.SUBS : 100;
    return Math.round((walletSmh() / subs) * 100) / 100;
  }
  function bag() {
    const vista = window.Baul && Baul.ultima && Baul.ultima();
    if (vista && Array.isArray(vista.filas) && vista.filas.length) {
      const out = {};
      for (const row of vista.filas) {
        if (!row || BLOCKED.has(row.id)) continue;
        const n = Math.floor(Number(row.total) || 0);
        if (n > 0) out[row.id] = n;
      }
      return out;
    }
    const S = api() && api().state;
    const out = {};
    const add = (source) => {
      for (const [id, qty] of Object.entries(source || {})) {
        if (BLOCKED.has(id)) continue;
        const n = Math.floor(Number(qty) || 0);
        if (n > 0) out[id] = (out[id] || 0) + n;
      }
    };
    add(S && S.purse && S.purse.items);
    add(S && S.vault && S.vault.items);
    const crudo = {};
    for (const id of METALES) crudo[id] = S && S.crudo && S.crudo[id];
    add(crudo);
    return out;
  }
  function offerOf(raw) {
    if (!raw || typeof raw !== 'object') return { smc: Number(raw) || 0, smp: 0, cobre: 0, items: {} };
    return { smc: raw.smc || 0, smp: 0, cobre: 0, items: raw.items || {} };
  }
  function describe(offer) {
    const o = offerOf(offer);
    const bits = [];
    if (o.smc) bits.push(money(o.smc));
    for (const [id, qty] of Object.entries(o.items || {})) {
      if (qty && !BLOCKED.has(id)) bits.push(qty + ' ' + meta(id).name);
    }
    return bits.length ? bits.join(', ') : 'nada';
  }
  function readSmc(raw) {
    const text = String(raw || '0').trim();
    if (!text) return 0;
    if (!window.Simulacion || !Simulacion.parseAmount) return 0;
    if (/smh|simonchi/i.test(text)) return Simulacion.parseAmount(text);
    return Simulacion.parseAmount(/smc/i.test(text) ? text : text + ' SMC');
  }
  function smcText(smh) {
    const subs = window.Simulacion && Simulacion.SUBS ? Simulacion.SUBS : 100;
    const value = Math.round((Number(smh) || 0) / subs * 100) / 100;
    return String(value).replace('.', ',');
  }
  function readOffer() {
    const smc = readSmc(draft.smc);
    if (!Number.isSafeInteger(smc) || smc < 0) throw Error('Simoncoin no válida.');
    if (smc > walletSmh()) throw Error('No tienes tanta Simoncoin.');
    const have = bag();
    const items = {};
    for (const [id, qty] of Object.entries(draft.items)) {
      if (BLOCKED.has(id)) throw Error('Ese objeto no se intercambia.');
      const count = Math.floor(Number(qty) || 0);
      if (!Number.isSafeInteger(count) || count < 0) throw Error('Cantidad no válida.');
      if (count > (have[id] || 0)) throw Error('No tienes tanto ' + meta(id).name + '.');
      if (count) items[id] = count;
    }
    return { smc, smp: 0, cobre: 0, items };
  }
  function send(obj) {
    const S = api()?.state;
    if (!S?.net.ok || S.net.ws?.readyState !== 1) throw Error('Sin conexión. No se envió.');
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
    gridKey = '';
    if (returnFocus && returnFocus.focus) returnFocus.focus({ preventScroll: true });
  }
  function cancel() {
    if (session) {
      try { action('trade_cancel'); } catch (e) { $('#trade-status').textContent = e.message; }
    }
    close();
  }
  function word(id) {
    if (!session) return 'Esperando';
    if (session.confirmed.includes(id)) return 'Confirmó';
    if (session.accepted.includes(id)) return 'Aceptó';
    return 'Esperando';
  }
  function coinFace() {
    return '<span class="trade-ico" aria-hidden="true"><svg viewBox="0 0 64 64"><circle cx="32" cy="36" r="18" fill="#8a5a12"/><circle cx="32" cy="30" r="18" fill="#f0c14a" stroke="#6a4010" stroke-width="3"/><circle cx="32" cy="30" r="11" fill="none" stroke="#fff4cc" stroke-width="2"/><text x="32" y="36" text-anchor="middle" font-size="16" font-family="sans-serif" font-weight="700" fill="#5c3a08">S</text></svg></span>';
  }
  function card(row, pick) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'trade-card';
    button.dataset.pick = row.id;
    button.setAttribute('aria-pressed', 'false');
    const img = row.id === 'simoncoin'
      ? coinFace()
      : (row.icon ? '<img src="' + row.icon + '" alt="">' : '<span class="trade-fallback" aria-hidden="true">•</span>');
    const propia = row.id === 'simoncoin'
      ? (window.Simulacion && Simulacion.formatSmc ? Simulacion.formatSmc(walletSmh()).replace(' SMC', '') : String(row.have))
      : String(row.have);
    const have = pick ? propia : String(row.qty || row.have || propia);
    button.title = row.name + (pick ? ' · tienes ' + have : ' · ofrece ' + have);
    button.setAttribute('aria-label', row.name + ', tienes ' + have);
    button.innerHTML = img + '<b>' + row.name + '</b><em class="trade-badge"></em>';
    if (pick) button.onclick = () => { selected = row.id; paintCards(); syncStepper(); };
    return button;
  }
  function buildGrid() {
    const box = $('#trade-grid');
    const have = bag();
    const key = 'simoncoin|' + Object.keys(have).sort().map(id => id + ':' + have[id]).join(',');
    if (key === gridKey) return;
    gridKey = key;
    box.replaceChildren();
    const rows = [{ id: 'simoncoin', cat: 'Simoncoin', name: 'Simoncoin', icon: '', have: maxSmc() }];
    for (const id of Object.keys(have).sort()) {
      const info = meta(id);
      rows.push({ id, cat: info.cat, name: info.name, icon: info.icon, have: have[id] });
    }
    for (const cat of GRUPOS) {
      const group = rows.filter(row => row.cat === cat);
      if (!group.length) continue;
      const title = document.createElement('h4');
      title.textContent = cat;
      const grid = document.createElement('div');
      grid.className = 'trade-grid';
      group.forEach(row => grid.append(card(row, true)));
      box.append(title, grid);
    }
    if (!rows.some(row => row.id === selected)) selected = 'simoncoin';
  }
  function paintCards() {
    const offer = (() => { try { return readOffer(); } catch (e) { return { smc: 0, items: draft.items }; } })();
    panel.querySelectorAll('#trade-grid [data-pick]').forEach(button => {
      const id = button.dataset.pick;
      const qty = id === 'simoncoin' ? (offer.smc ? money(offer.smc).replace(' SMC', '') : '') : (draft.items[id] || '');
      button.classList.toggle('sel', id === selected);
      button.setAttribute('aria-pressed', id === selected ? 'true' : 'false');
      const badge = button.querySelector('.trade-badge');
      if (badge) badge.textContent = qty ? String(qty) : '';
    });
    const info = selected === 'simoncoin'
      ? { name: 'Simoncoin' }
      : meta(selected);
    const chosen = $('#trade-elegido');
    if (chosen) chosen.textContent = info.name;
  }
  function syncStepper() {
    const input = $('#trade-qty');
    if (!input || document.activeElement === input) return;
    const decimal = selected === 'simoncoin';
    input.step = decimal ? '0.01' : '1';
    input.inputMode = decimal ? 'decimal' : 'numeric';
    input.value = decimal ? (draft.smc || '0') : String(draft.items[selected] || 0);
  }
  function paintTheirs(offer) {
    const box = $('#trade-theirs-grid');
    if (!box) return;
    box.replaceChildren();
    const o = offerOf(offer);
    const rows = [];
    if (o.smc) {
      const corto = money(o.smc).replace(' SMC', '');
      rows.push({ id: 'simoncoin', cat: 'Simoncoin', name: 'Simoncoin', icon: '', have: corto, qty: corto });
    }
    for (const [id, qty] of Object.entries(o.items || {})) {
      if (!qty || BLOCKED.has(id)) continue;
      const info = meta(id);
      rows.push({ id, cat: info.cat, name: info.name, icon: info.icon, have: String(qty), qty: String(qty) });
    }
    if (!rows.length) {
      const p = document.createElement('p');
      p.textContent = 'Todavía no ofrece nada.';
      box.append(p);
      return;
    }
    for (const cat of GRUPOS) {
      const group = rows.filter(row => row.cat === cat);
      if (!group.length) continue;
      const title = document.createElement('h4');
      title.textContent = cat;
      const grid = document.createElement('div');
      grid.className = 'trade-grid';
      group.forEach(row => {
        const node = card(row, false);
        node.disabled = true;
        const badge = node.querySelector('.trade-badge');
        if (badge) badge.textContent = row.qty;
        grid.append(node);
      });
      box.append(title, grid);
    }
  }
  function render() {
    if (!session) return;
    const S = api().state;
    const me = S.net.id;
    const other = session.players.find(p => p.id !== me) || session.players[0];
    const review = session.accepted.length === 2;
    const locked = session.confirmed.includes(me);
    $('#trade-peer').textContent = 'Recibo · ' + (other?.name || 'otra persona');
    $('#trade-own-status').textContent = 'Tú: ' + word(me);
    $('#trade-other-status').textContent = (other?.name || 'Otra persona') + ': ' + word(other.id);
    buildGrid();
    paintCards();
    syncStepper();
    paintTheirs(session.offers[String(other.id)]);
    let mine = 'nada';
    try { mine = describe(readOffer()); } catch (e) { mine = 'revisa la cantidad'; }
    $('#trade-review').textContent = 'Das ' + mine + '. Recibes ' + describe(session.offers[String(other.id)]) + '.'
      + (review ? ' Revisa y confirma.' : '');
    $('#trade-accept').hidden = review;
    $('#trade-confirm').hidden = !review;
    $('#trade-accept').disabled = pending || dirty || locked || session.accepted.includes(me);
    $('#trade-confirm').disabled = pending || dirty || session.confirmed.includes(me);
    $('#trade-update').disabled = pending || !dirty || locked;
    $('#trade-qty').readOnly = locked;
    $('#trade-menos').disabled = locked;
    $('#trade-mas').disabled = locked;
    $('#trade-uno').disabled = locked;
    $('#trade-x').disabled = locked;
    $('#trade-max').disabled = locked;
  }
  function markDirty() {
    dirty = true;
    if (session) {
      render();
      $('#trade-status').textContent = 'Oferta sin enviar.';
    }
  }
  function setFromField() {
    const raw = $('#trade-qty').value;
    if (selected === 'simoncoin') {
      draft.smc = String(raw || '0').trim().replace('.', ',');
    } else {
      const n = Math.floor(Number(String(raw || '0').replace(',', '.')) || 0);
      const max = bag()[selected] || 0;
      const next = Math.max(0, Math.min(max, n));
      if (next) draft.items[selected] = next;
      else delete draft.items[selected];
    }
    markDirty();
  }
  function bump(dir) {
    if (selected === 'simoncoin') {
      const cur = readSmc(draft.smc || '0') / (window.Simulacion && Simulacion.SUBS ? Simulacion.SUBS : 100);
      const next = Math.max(0, Math.round((cur + dir * 0.01) * 100) / 100);
      draft.smc = String(Math.min(next, maxSmc())).replace('.', ',');
    } else {
      const max = bag()[selected] || 0;
      const next = Math.max(0, Math.min(max, Math.floor(Number(draft.items[selected] || 0)) + dir));
      if (next) draft.items[selected] = next;
      else delete draft.items[selected];
    }
    const input = $('#trade-qty');
    if (input) input.value = selected === 'simoncoin' ? draft.smc : String(draft.items[selected] || 0);
    markDirty();
  }
  function takeOffer(raw) {
    const o = offerOf(raw);
    draft = { smc: smcText(o.smc), items: Object.assign({}, o.items || {}) };
    for (const id of Object.keys(draft.items)) {
      if (BLOCKED.has(id) || !draft.items[id]) delete draft.items[id];
    }
  }
  function openTrade(peer) {
    if (!api()?.started) return;
    try {
      if (session) {
        $('#trade-status').textContent = 'Cancela el trueque actual.';
        return;
      }
      send({ t: 'baul' });
      send({ t: 'trade_start', peer: Number(peer) });
    } catch (e) {
      const status = $('#rest-status');
      if (status) status.textContent = e.message;
    }
  }
  function aplicarSaldos(box, walletName) {
    const S = api() && api().state;
    if (!S || !box) return;
    const raw = box.balanceSubs != null ? box.balanceSubs : box.smc;
    if (raw == null || !Number.isFinite(Number(raw))) return;
    const amount = Math.trunc(Number(raw));
    S.ledger = S.ledger || {};
    S.ledger.balances = Object.assign({}, S.ledger.balances || {}, { simoncoin: amount });
    if (!S.econ) S.econ = { wallets: {} };
    if (!S.econ.wallets) S.econ.wallets = {};
    const names = [];
    if (S.me && S.me.name) names.push(S.me.name);
    if (walletName && names.indexOf(walletName) < 0) names.push(walletName);
    names.forEach((name) => { S.econ.wallets[name] = amount; });
    if (window.Simulacion && Simulacion.reconcileBalance) Simulacion.reconcileBalance();
    else if (window.Simulacion && Simulacion.paintHud) Simulacion.paintHud();
    if (window.Cajon) Cajon.paint();
    if (window.Baul && Baul.pedir) Baul.pedir();
  }
  function onNet(m) {
    if (!m.t || !m.t.startsWith('trade_')) return false;
    if (m.t === 'trade_state') {
      const previous = session;
      const first = !session;
      session = m;
      pending = false;
      if (first || !dirty) takeOffer(m.offers[String(api().state.net.id)]);
      dirty = false;
      $('#trade-status').textContent = previous && previous.revision !== m.revision
        ? 'La oferta cambió. Acepta de nuevo.'
        : 'Esperando a los dos.';
      if (!panel.open) {
        returnFocus = document.activeElement;
        if (api().state.keys) api().state.keys.clear();
        if (api().state.player) api().state.player.path = [];
        panel.showModal();
      }
      render();
    } else if (m.t === 'trade_error') {
      pending = false;
      $('#trade-status').textContent = m.reason || 'No se pudo.';
      if (!session && $('#rest-status')) $('#rest-status').textContent = m.reason || '';
      render();
    } else if (m.t === 'trade_end') {
      if (session && m.id !== session.id) return true;
      close();
      if (m.ok && (m.balances || m.balanceSubs != null)) {
        aplicarSaldos({
          smc: m.balanceSubs != null ? m.balanceSubs : m.balances.smc,
          balanceSubs: m.balanceSubs != null ? m.balanceSubs : m.balances.smc,
        }, m.walletName);
      }
      const line = m.reason || (m.ok ? 'Listo.' : 'No se pudo.');
      if (typeof game === 'function') game(line, m.ok ? 'juego' : 'aviso');
      else if ($('#rest-status')) $('#rest-status').textContent = line;
      if (m.reason && m.reason.indexOf('Tu mochila está llena') >= 0 && window.avisarMochilaLlena) window.avisarMochilaLlena();
      if (window.Banco) Banco.paint();
      if (window.Cajon) Cajon.paint();
      if (window.MiCuenta && MiCuenta.tocar) MiCuenta.tocar();
    }
    return true;
  }

  panel.addEventListener('keydown', (e) => e.stopPropagation());
  $('#trade-qty').oninput = setFromField;
  $('#trade-menos').onclick = () => bump(-1);
  $('#trade-mas').onclick = () => bump(1);
  function ofrecer(mode) {
    try {
      if (selected === 'simoncoin') {
        const subs = window.Simulacion && Simulacion.SUBS ? Simulacion.SUBS : 100;
        const cur = readSmc(draft.smc || '0') / subs;
        let next = cur;
        if (mode === '1') next = Math.min(maxSmc(), Math.round((cur + 1) * 100) / 100);
        else if (mode === 'x') next = Math.min(maxSmc(), Math.max(0, readSmc($('#trade-qty').value || '0') / subs));
        else next = maxSmc();
        draft.smc = String(Math.round(next * 100) / 100).replace('.', ',');
      } else {
        const max = bag()[selected] || 0;
        let next = 0;
        if (mode === '1') next = Math.min(max, Math.floor(Number(draft.items[selected] || 0)) + 1);
        else if (mode === 'x') next = Math.min(max, Math.max(0, Math.floor(Number(String($('#trade-qty').value || '0').replace(',', '.')) || 0)));
        else next = max;
        if (next) draft.items[selected] = next;
        else delete draft.items[selected];
      }
      const input = $('#trade-qty');
      if (input) input.value = selected === 'simoncoin' ? draft.smc : String(draft.items[selected] || 0);
      action('trade_offer', { offer: readOffer() });
    } catch (e) {
      $('#trade-status').textContent = e.message;
    }
  }
  $('#trade-uno').onclick = () => ofrecer('1');
  $('#trade-x').onclick = () => ofrecer('x');
  $('#trade-max').onclick = () => ofrecer('all');
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
  function refrescar() {
    gridKey = '';
    if (session) render();
  }
  window.TradeUI = { openTrade, onNet, cancel, close, refrescar };
})();
