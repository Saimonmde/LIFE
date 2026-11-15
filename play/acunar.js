/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Calculadora de acuñar. El metal se queda en la mochila hasta que el servidor confirma. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const RATES = {
    simoncoin: { item: 'pepita_oro', rate: 5, name: 'Simoncoin', metal: 'oros crudos', cap: 0.25 },
    simonplata: { item: 'mineral_plata', rate: 4, name: 'Simonplata', metal: 'plata cruda', cap: 5 },
    simonchis: { item: 'mineral_cobre', rate: 3, name: 'Simonchis', metal: 'cobre crudo', cap: 200, whole: true },
  };
  let coin = 'simoncoin';
  let pieces = 0;

  function count(id) {
    const S = window.__ELJARDIN;
    if (!S || !S.inv) return 0;
    return S.inv.reduce((sum, slot) => sum + (slot && slot.item === id ? slot.qty : 0), 0);
  }
  function spec() {
    const live = window.__ELJARDIN && __ELJARDIN.cupos && __ELJARDIN.cupos.coins;
    const base = RATES[coin];
    const row = live && live[coin];
    if (!row) return base;
    return {
      item: row.item || base.item,
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
    let maxPieces = Math.min(have, Math.floor(ceiling * rate + 1e-9));
    if (row.whole) maxPieces = Math.floor(maxPieces / rate) * rate;
    let spend = Math.max(0, Math.min(have, chosen == null ? maxPieces : chosen | 0));
    spend = Math.min(spend, maxPieces);
    if (row.whole) spend = Math.floor(spend / rate) * rate;
    return { tienes: have, alcanzan: reach, hoy: daily, cap: row.cap, maxPieces, gastas: spend, recibes: spend / rate };
  }
  function num(n) {
    const text = Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 });
    return text;
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
      '<input id="acunar-cantidad" type="range" min="0" value="0" aria-label="Cuánto metal gastar">',
      '<button type="button" class="grande" id="acunar-ok">Acuñar</button>',
    ].join('');
    document.body.append(veil, box);
    veil.onclick = close;
    $('#acunar-x').onclick = close;
    box.querySelectorAll('[data-coin]').forEach(button => {
      button.onclick = () => { coin = button.dataset.coin; pieces = null; paint(); };
    });
    $('#acunar-cantidad').addEventListener('input', (e) => { pieces = Number(e.target.value); paint(false); });
    $('#acunar-ok').onclick = send;
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
    const have = count(row.item);
    if (resetSlider !== false && pieces == null) pieces = null;
    const q = quote(have, row, pieces);
    if (pieces == null) pieces = q.maxPieces;
    const shown = quote(have, row, pieces);
    $('#acunar-tienes').textContent = `Tienes: ${num(shown.tienes)} ${row.metal}`;
    $('#acunar-alcanzan').textContent = `Con eso alcanzan: ${num(shown.alcanzan)} ${row.name}`;
    $('#acunar-hoy').textContent = `Hoy puedes acuñar: ${num(shown.hoy)} de ${num(shown.cap)} ${row.name} (se reinicia a las 7:00 p. m.)`;
    $('#acunar-vas').textContent = `Vas a recibir: ${num(shown.recibes)} ${row.name} y gastas: ${num(shown.gastas)} ${row.metal}`;
    const slider = $('#acunar-cantidad');
    slider.max = String(shown.maxPieces);
    slider.value = String(shown.gastas);
    $('#acunar-ok').disabled = shown.gastas < 1;
    $('#acunar').querySelectorAll('[data-coin]').forEach(button => {
      button.classList.toggle('activa', button.dataset.coin === coin);
    });
  }
  function open() {
    ensure();
    pieces = null;
    $('#acunar').hidden = false;
    $('#acunar-fondo').hidden = false;
    paint();
    $('#acunar-x').focus();
  }
  function send() {
    const row = spec();
    const shown = quote(count(row.item), row, pieces);
    const S = window.__ELJARDIN;
    const ws = S && S.net && S.net.ws;
    if (!ws || !S.net.ok) {
      $('#acunar-vas').textContent = 'Hace falta el servidor para acuñar. El metal sigue en la mochila.';
      return;
    }
    ws.send(JSON.stringify({ t: 'acunar', coin, pieces: shown.gastas }));
    $('#acunar-ok').disabled = true;
  }
  function onNet(m) {
    if (!m || m.t !== 'acunar_result') return false;
    if (m.cupos && window.__ELJARDIN) __ELJARDIN.cupos = m.cupos;
    if (m.ledger && window.__ELJARDIN) __ELJARDIN.ledger = m.ledger;
    if (m.ok && m.item && m.spent && window.quitarDelInventario) quitarDelInventario(m.item, m.spent);
    if (window.Cajon) Cajon.paint();
    paint();
    const box = $('#acunar-vas');
    if (box && m.reason) box.textContent = m.reason;
    return true;
  }
  window.Acunar = { open, close, paint, onNet };
})();
