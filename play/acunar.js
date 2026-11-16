/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Calculadora de acuñar. El metal se queda en la mochila hasta que el servidor confirma. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const RATES = {
    simoncoin: { item: 'pepita_oro', items: ['pepita_oro', 'mineral_oro'], rate: 5, name: 'Simoncoin', metal: 'oros crudos', cap: 0.25 },
    simonplata: { item: 'mineral_plata', rate: 4, name: 'Simonplata', metal: 'plata cruda', cap: 5 },
    simonchis: { item: 'mineral_cobre', rate: 3, name: 'Simonchis', metal: 'cobre crudo', cap: 200, whole: true },
  };
  let coin = 'simoncoin';
  let pieces = 0;
  let busy = false;

  function count(id) {
    const S = window.__ELJARDIN;
    if (!S) return 0;
    const fromInv = (S.inv || []).reduce((sum, slot) => sum + (slot && slot.item === id ? Number(slot.qty) || 0 : 0), 0);
    const fromCrudo = S.crudo && S.crudo[id] != null ? Number(S.crudo[id]) || 0 : 0;
    return Math.max(fromInv, fromCrudo);
  }
  function countRow(row) {
    const ids = row.items && row.items.length ? row.items : [row.item];
    return ids.reduce((sum, id) => sum + count(id), 0);
  }
  function enMina() {
    const world = window.LiveInk && LiveInk.world;
    return !!(world && world.mapId === 'mine');
  }
  function spec() {
    const live = window.__ELJARDIN && __ELJARDIN.cupos && __ELJARDIN.cupos.coins;
    const base = RATES[coin];
    const row = live && live[coin];
    if (!row) return base;
    return {
      item: row.item || base.item,
      items: row.items || base.items || [row.item || base.item],
      rate: row.rate || base.rate,
      name: row.name || base.name,
      metal: row.metal || base.metal,
      cap: row.cap != null ? row.cap : base.cap,
      left: row.left != null ? row.left : base.cap,
      room: row.room != null ? row.room : 1e15,
      whole: !!base.whole,
    };
  }
  function quote(have, row, chosen) {
    const rate = row.rate;
    const daily = row.left != null ? row.left : row.cap;
    const world = row.room != null ? row.room : 1e15;
    const reach = have / rate;
    const ceiling = Math.min(reach, daily, world);
    let maxPieces = Math.min(have, ceiling * rate);
    if (row.whole) maxPieces = Math.floor(maxPieces / rate) * rate;
    let spend = Math.max(0, Math.min(have, chosen == null ? maxPieces : Number(chosen) || 0));
    spend = Math.min(spend, maxPieces);
    if (row.whole) spend = Math.floor(spend / rate) * rate;
    return { tienes: have, alcanzan: reach, hoy: daily, cap: row.cap, maxPieces, gastas: spend, recibes: spend / rate };
  }
  function num(n) {
    const text = Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 });
    return text;
  }
  const CORTO = { simoncoin: 'oro', simonplata: 'plata', simonchis: 'cobre' };
  function elegirMoneda() {
    const order = ['simoncoin', 'simonplata', 'simonchis'];
    const con = order.filter((id) => countRow(RATES[id]) > 0);
    if (!con.length) return 'simoncoin';
    return con.find((id) => countRow(RATES[id]) >= RATES[id].rate) || con[0];
  }
  function textoFalta(have, rate, nombre) {
    const resto = Number(have) % Number(rate);
    const falta = resto === 0 ? Number(rate) : Number(rate) - resto;
    return 'Tienes ' + num(have) + ' de ' + nombre + ', te falta ' + num(falta);
  }
  function ensure() {
    if ($('#acunar')) return;
    const veil = document.createElement('button');
    veil.id = 'acunar-fondo';
    veil.type = 'button';
    veil.hidden = true;
    veil.setAttribute('aria-label', 'Cerrar acuñar');
    const box = document.createElement('section');
    box.id = 'acunar';
    box.hidden = true;
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-label', 'Acuñar');
    box.innerHTML = [
      '<header><h2>Acuñar</h2><button type="button" class="x" id="acunar-x" aria-label="Cerrar">✕</button></header>',
      '<div class="metales" role="tablist">',
      '<button type="button" data-coin="simoncoin">Oro</button>',
      '<button type="button" data-coin="simonplata">Plata</button>',
      '<button type="button" data-coin="simonchis">Cobre</button>',
      '</div>',
      '<p id="acunar-tienes"></p>',
      '<p id="acunar-alcanzan"></p>',
      '<p id="acunar-hoy"></p>',
      '<p id="acunar-vas"></p>',
      '<input id="acunar-cantidad" type="range" min="0" value="0" step="0.05" aria-label="Cuánto metal gastar">',
      '<button type="button" class="grande" id="acunar-ok">Acuñar</button>',
      '<button type="button" class="grande" id="acunar-ir" hidden>Ir a la mina / Picar</button>',
    ].join('');
    document.body.append(veil, box);
    veil.onclick = close;
    $('#acunar-x').onclick = close;
    box.querySelectorAll('[data-coin]').forEach(button => {
      button.onclick = () => { coin = button.dataset.coin; pieces = null; paint(); };
    });
    $('#acunar-cantidad').addEventListener('input', (e) => { pieces = Number(e.target.value); paint(false); });
    $('#acunar-ok').onclick = send;
    const ir = $('#acunar-ir');
    if (ir) ir.onclick = () => { close(); if (window.LiveInk && LiveInk.goMine) LiveInk.goMine(); };
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !$('#acunar').hidden) { close(); e.preventDefault(); }
    });
  }
  function close() {
    ensure();
    $('#acunar').hidden = true;
    $('#acunar-fondo').hidden = true;
  }
  function paint(resetSlider) {
    ensure();
    const row = spec();
    const have = countRow(row);
    const aqui = enMina();
    if (resetSlider !== false && pieces == null) pieces = null;
    const q = quote(have, row, pieces);
    if (pieces == null) pieces = q.maxPieces;
    const shown = quote(have, row, pieces);
    $('#acunar-tienes').textContent = `Tienes: ${num(shown.tienes)} ${row.metal}`;
    $('#acunar-alcanzan').textContent = `Con eso alcanzan: ${num(shown.alcanzan)} ${row.name}`;
    const supply = window.__ELJARDIN && __ELJARDIN.supply;
    const copper = supply && supply.copperNote ? ' ' + supply.copperNote : '';
    $('#acunar-hoy').textContent = `Hoy puedes acuñar: ${num(shown.hoy)} de ${num(shown.cap)} ${row.name} (se reinicia a las 7:00 p. m.).${copper}`;
    const ir = $('#acunar-ir');
    const corto = CORTO[coin] || 'metal';
    const falta = shown.gastas <= 0 ? textoFalta(shown.tienes, row.rate, corto) : '';
    if (shown.tienes <= 0) {
      $('#acunar-vas').textContent = 'No tienes metal. ' + textoFalta(0, row.rate, corto) + '. Pica en la mina y vuelve al horno. No se acuñó nada.';
      if (ir) { ir.hidden = false; ir.textContent = 'Ve a picar'; }
    } else if (!aqui) {
      $('#acunar-vas').textContent = falta ? falta + ' Ve al horno de la mina.' : 'Ve al horno de la mina';
      if (ir) { ir.hidden = false; ir.textContent = 'Ve al horno de la mina'; }
    } else if (falta) {
      $('#acunar-vas').textContent = falta;
      if (ir) ir.hidden = true;
    } else {
      $('#acunar-vas').textContent = `Vas a recibir: ${num(shown.recibes)} ${row.name} y gastas: ${num(shown.gastas)} ${row.metal}`;
      if (ir) ir.hidden = true;
    }
    if (busy) $('#acunar-vas').textContent = 'Calculando prueba…';
    const slider = $('#acunar-cantidad');
    slider.max = String(shown.maxPieces);
    slider.value = String(shown.gastas);
    $('#acunar-ok').disabled = busy || !aqui || shown.gastas <= 0;
    $('#acunar').querySelectorAll('[data-coin]').forEach(button => {
      button.classList.toggle('activa', button.dataset.coin === coin);
    });
  }
  function open() {
    ensure();
    coin = elegirMoneda();
    pieces = null;
    $('#acunar').hidden = false;
    $('#acunar-fondo').hidden = false;
    paint();
    $('#acunar-x').focus();
  }
  function send() {
    const row = spec();
    const shown = quote(countRow(row), row, pieces);
    const S = window.__ELJARDIN;
    const ws = S && S.net && S.net.ws;
    if (!ws || !S.net.ok) {
      $('#acunar-vas').textContent = 'Hace falta el servidor para acuñar. El metal sigue en la mochila.';
      return;
    }
    if (!enMina()) {
      $('#acunar-vas').textContent = 'Ve al horno de la mina';
      return;
    }
    busy = true;
    if (window.Simulacion && Simulacion.expectMint && coin === 'simoncoin') {
      Simulacion.expectMint(Math.round(shown.recibes * Simulacion.SUBS));
    }
    ws.send(JSON.stringify({ t: 'acunar', coin, pieces: shown.gastas }));
    $('#acunar-vas').textContent = 'Calculando prueba…';
    $('#acunar-ok').disabled = true;
  }
  function fallo(m) {
    busy = false;
    if (window.Simulacion && Simulacion.reconcileBalance) Simulacion.reconcileBalance();
    paint();
    const box = $('#acunar-vas');
    if (box) box.textContent = (m && m.reason) || 'No se pudo acuñar.';
    const ok = $('#acunar-ok');
    if (ok && enMina()) ok.disabled = false;
  }
  function onNet(m) {
    if (!m) return false;
    if (m.t === 'pow_challenge' && m.resume && m.resume.t === 'acunar') {
      busy = true;
      const box = $('#acunar-vas');
      if (box) box.textContent = 'Calculando prueba…';
      const ok = $('#acunar-ok');
      if (ok) ok.disabled = true;
      return false;
    }
    if ((m.t === 'pow_result' || m.t === 'smelt_result') && m.ok === false && !m.needPow) {
      fallo(m);
      return false;
    }
    if (m.t === 'acunar_result' && m.pending) {
      busy = true;
      const box = $('#acunar-vas');
      if (box) box.textContent = 'Calculando prueba…';
      const ok = $('#acunar-ok');
      if (ok) ok.disabled = true;
      return true;
    }
    if (m.t !== 'acunar_result') return false;
    busy = false;
    if (m.cupos && window.__ELJARDIN) __ELJARDIN.cupos = m.cupos;
    if (m.ledger && window.__ELJARDIN) __ELJARDIN.ledger = m.ledger;
    if (m.crudo && window.ponerMetal) {
      Object.keys(m.crudo).forEach(id => window.ponerMetal(id, m.crudo[id]));
    } else if (m.ok && m.spentItems && window.quitarMetal) {
      Object.keys(m.spentItems).forEach(id => window.quitarMetal(id, m.spentItems[id]));
    }
    if (!m.ok) return fallo(m), true;
    if (m.purse && window.__ELJARDIN) __ELJARDIN.purse = m.purse;
    if (m.moneda && window.meterMonedas) window.meterMonedas(m.moneda.item, m.moneda.total || m.moneda.qty);
    if (window.Simulacion && Simulacion.aplicarCredito) Simulacion.aplicarCredito(m);
    else if (window.Simulacion && Simulacion.renderLibro) Simulacion.renderLibro();
    if (m.registro && window.LibroMadre) LibroMadre.toast(m.registro);
    if (window.Banco && Banco.paint) Banco.paint();
    if (window.Sonido) Sonido.fromMint(m);
    if (window.Cajon) Cajon.paint();
    paint();
    const box = $('#acunar-vas');
    if (box && m.reason) box.textContent = m.reason;
    return true;
  }
  window.Acunar = { open, close, paint, onNet, elegirMoneda, textoFalta };
})();
