/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Cafetal de Las Palmas: plantar, cosechar, talleres y libro público. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  let view = null;
  let semillaElegida = '';
  let contadores = null;
  let prevCoins = null;
  let extraFeed = [];
  let lastOp = 'ver';
  let lastExtra = {};

  function send(op, extra) {
    const S = window.LiveInk && LiveInk.state;
    const ws = S && S.net && S.net.ws;
    if (!ws || ws.readyState !== 1) {
      say('Entra al mundo para usar la finca.');
      return;
    }
    lastOp = op;
    lastExtra = extra || {};
    ws.send(JSON.stringify(Object.assign({ t: 'finca', op }, lastExtra)));
  }

  function say(text) {
    const note = $('#finca-note');
    if (note) note.textContent = text || '';
    if (text && text.indexOf('Tu mochila está llena') >= 0 && window.avisarMochilaLlena && window.LiveInk) {
      LiveInk.state.espera = {
        server: false,
        item: 'bolsa',
        qty: 1,
        done: (where) => { if (where === 'banco') send(lastOp, Object.assign({}, lastExtra, { place: 'banco' })); },
      };
      window.avisarMochilaLlena();
    }
  }

  function stageName(stage) {
    return { vacio: 'vacía', planton: 'plantón', verde: 'verde', maduro: 'maduro' }[stage] || stage;
  }

  let textos = null;
  const FASE = {
    cafe: { fruto: 'cereza_madura' },
    cacao: { fruto: 'mazorca' },
  };
  const PASO = {
    cafe: { despulpado: 'despulpado', secado: 'secado', trilla: 'trilla' },
    cacao: { fermentado: 'fermentacion_cajones', secado: 'secado' },
  };
  function esc(text) {
    return String(text == null ? '' : text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function carta(crop, etapa) {
    if (!textos || !etapa) return '';
    const row = (textos[crop] || []).find(item => item.etapa === etapa);
    if (!row) return '';
    return `<details class="finca-carta"><summary>${esc(row.titulo)}</summary><p>${esc(row.texto)}</p><p><b>Dato.</b> ${esc(row.dato)}</p><p><a href="${esc(row.fuente)}" target="_blank" rel="noopener">Fuente</a></p></details>`;
  }
  function etapaDe(crop, phase) {
    if (!phase || phase === 'vacio') return '';
    return (FASE[crop] || {})[phase] || phase;
  }

  function paintFarm() {
    const root = $('#finca-body');
    if (!root) return;
    if (!view) {
      root.innerHTML = '<p>Entra con tu cuenta. El café y el cacao están en Las Palmas.</p>';
      return;
    }
    const plots = view.plots || [];
    const list = (crop) => plots.filter(row => row.crop === crop).map(row => {
      const action = row.stage === 'vacio' ? 'Plantar' : (row.stage === 'maduro' ? 'Cosechar' : '');
      const button = action ? `<button type="button" data-op="${action === 'Plantar' ? 'plantar' : 'cosechar'}" data-plot="${row.id}">${action}</button>` : '';
      return `<div class="finca-plot"><span>${row.crop === 'cafe' ? 'Café' : 'Cacao'} · ${stageName(row.stage)}</span>${button}</div>${carta(crop, etapaDe(crop, row.phase))}`;
    }).join('');
    const goods = view.goods || {};
    const batches = view.batches || {};
    const workshop = (crop, title) => {
      const spec = (view.crops || {})[crop] || {};
      const steps = spec.steps || [];
      const ids = spec.stepIds || [];
      const batch = batches[crop];
      const lead = batch ? 'Procesar' : 'Llevar al taller';
      const buttons = `<button type="button" class="finca-llevar" data-op="procesar" data-crop="${crop}">${lead}</button>` + steps.map(label => `<button type="button" data-op="procesar" data-crop="${crop}">${label}</button>`).join('');
      const cards = ids.map(id => carta(crop, (PASO[crop] || {})[id] || id)).join('');
      const status = batch ? (batch.settled ? `Listo: ${batch.step}.` : `Trabajando: ${batch.step}.`) : 'El taller está libre.';
      return `<h3>${title}</h3><p>${status}</p><div class="finca-actions">${buttons}</div>${cards}`;
    };
    const fases = { vacio: 'Vacía', siembra: 'Siembra', crecimiento: 'Crecimiento', floracion: 'Floración', fruto: 'Fruto', cosecha: 'Cosecha' };
    const tonos = { vacio: '#8d6b45', siembra: '#d7b15a', crecimiento: '#7ea84a', floracion: '#f3e7a1', fruto: '#e07a32', cosecha: '#d64545' };
    const marcas = {
      vacio: '<circle cx="16" cy="16" r="6" fill="none" stroke="#f6e7c8" stroke-width="2"/>',
      siembra: '<circle cx="16" cy="18" r="4" fill="#f6e7c8"/>',
      crecimiento: '<path d="M16 22 V8 M16 14 l-5 4 M16 12 l5 4" fill="none" stroke="#f6e7c8" stroke-width="2"/>',
      floracion: '<circle cx="16" cy="16" r="3" fill="#f6e7c8"/><circle cx="10" cy="12" r="2" fill="#f6e7c8"/><circle cx="22" cy="12" r="2" fill="#f6e7c8"/><circle cx="11" cy="21" r="2" fill="#f6e7c8"/><circle cx="21" cy="21" r="2" fill="#f6e7c8"/>',
      fruto: '<circle cx="16" cy="16" r="6" fill="#f6e7c8"/>',
      cosecha: '<path d="M16 6 l2 6 h6 l-5 4 2 6 -5-4 -5 4 2-6 -5-4 h6z" fill="#f6e7c8"/>',
    };
    const seeds = view.seeds || {};
    const seedButtons = Object.keys(seeds).map(id => {
      const row = seeds[id];
      const on = semillaElegida === id ? ' is-on' : '';
      return `<button type="button" class="huerta-semilla${on}" data-pick="${esc(id)}">${esc(row.name)} · ${row.qty}</button>`;
    }).join('') || '<p>No tienes semillas en la mochila. Manzana, pera, naranja, mango, banano, coco, café o cacao.</p>';
    const huerta = (view.huerta || []).map(row => {
      const phase = row.phase || 'vacio';
      const pct = Math.round((Number(row.progress) || 0) * 100);
      const mark = marcas[phase] || marcas.vacio;
      const action = phase === 'vacio'
        ? `<button type="button" data-op="huerta_sembrar" data-bed="${esc(row.id)}">Sembrar</button>`
        : (row.ready ? `<button type="button" data-op="huerta_cosechar" data-bed="${esc(row.id)}">Cosechar</button>` : '');
      const title = row.name ? row.name : 'Era vacía';
      return `<div class="huerta-bed" data-phase="${esc(phase)}" data-planted="${row.plantedAt || 0}" style="--tono:${tonos[phase] || tonos.vacio}">
        <svg class="huerta-mark" viewBox="0 0 32 32" aria-hidden="true">${mark}</svg>
        <div class="huerta-copy"><b>${esc(title)}</b><span>${fases[phase] || phase}</span>
        <div class="huerta-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><span style="width:${pct}%"></span></div></div>
        ${action}</div>`;
    }).join('');
    const kilos = (crop, count) => {
      const per = Number(((view.crops || {})[crop] || {}).kgPerHarvest) || 0;
      return (Number(count) || 0) * per;
    };
    const bags = (view.bags || []).map(bag => (
      `<div class="finca-bag"><span>${bag.serial} · bulto de ${bag.kg || 0} kg · ${bag.product}</span><span>` +
      `<button type="button" data-op="vender" data-serial="${bag.serial}" data-coin="simoncoin">Vender oro</button>` +
      `<button type="button" data-op="vender" data-serial="${bag.serial}" data-coin="simonplata">Vender plata</button>` +
      `<button type="button" data-op="vender" data-serial="${bag.serial}" data-coin="simonchis">Vender cobre</button>` +
      `<button type="button" data-op="depositar" data-serial="${bag.serial}">Mi banco</button></span></div>`
    )).join('') || '<p>No tienes sacos ni cajones en la mano.</p>';
    const bank = (view.bank || []).map(bag => (
      `<div class="finca-bag"><span>${bag.serial} · bulto de ${bag.kg || 0} kg</span><button type="button" data-op="retirar" data-serial="${bag.serial}">Retirar</button></div>`
    )).join('') || '<p>El banco no guarda sacos ni cajones tuyos.</p>';
    const pay = view.buyerBalances || {};
    root.innerHTML = `
      <p class="finca-note" id="finca-note">Plantas. Esperas. Cosechas. Procesas. Vendes.</p>
      <h3>Huerta</h3>
      <p>Ocho eras vacías, aparte del café y del cacao. Elige la semilla y siembra. El color y la barra muestran la mata, de la siembra a la cosecha.</p>
      <div class="huerta-semillas">${seedButtons}</div>
      <div class="huerta-grid">${huerta || '<p>La huerta todavía no carga.</p>'}</div>
      <p>${((view.crops || {}).cafe || {}).note || ''}</p>
      <p>${((view.crops || {}).cacao || {}).note || ''}</p>
      <p>${view.ripeningNote || ''}</p>
      <p>Esos kilos cosechados se suman y no bajan. El taller no crea kilos ni monedas.</p>
      <h3>Café, junto al cacao</h3>${list('cafe') || '<p>Sin parcelas.</p>'}
      <div class="finca-actions"><button type="button" data-op="recoger" data-crop="cafe">Recoger café</button><button type="button" data-op="procesar" data-crop="cafe">Procesar café</button><button type="button" data-op="exportar" data-crop="cafe">Exportar café</button></div>
      <h3>Cacao, junto al café</h3>${list('cacao') || '<p>Sin parcelas.</p>'}
      <div class="finca-actions"><button type="button" data-op="recoger" data-crop="cacao">Recoger cacao</button><button type="button" data-op="procesar" data-crop="cacao">Procesar cacao</button><button type="button" data-op="exportar" data-crop="cacao">Exportar cacao</button></div>
      ${workshop('cafe', 'Taller de café · despulpar, secar, trillar')}
      ${workshop('cacao', 'Taller de cacao · fermentar, secar')}
      <h3>En la mano</h3>
      <p>${kilos('cafe', goods.cafe_cereza)} kg de café cereza (${goods.cafe_cereza || 0} recolecciones) · ${kilos('cacao', goods.cacao_baba)} kg de cacao en baba (${goods.cacao_baba || 0} recolecciones)</p>
      ${bags}
      <h3>Mi banco</h3>${bank}
      <h3>${view.buyerName || 'Casa de Contratación'}</h3>
      <p>Paga con monedas que ya tiene. Hoy vendiste ${view.soldToday || 0} de ${view.sellCap || 0}.</p>
      <p>Oro ${pay.simoncoinText || '0'} · Plata ${pay.simonplataText || '0'} · Cobre ${pay.simonchisText || '0'}</p>
      <button type="button" id="finca-libro">Abrir el Libro mayor</button>`;
    const note = root.querySelector('#finca-note');
    root.querySelectorAll('button[data-op], button[data-pick]').forEach(button => {
      button.onclick = () => {
        if (button.dataset.pick) {
          semillaElegida = button.dataset.pick;
          paintFarm();
          return;
        }
        const op = button.dataset.op;
        send(op, { plot: button.dataset.plot, crop: button.dataset.crop, serial: button.dataset.serial, coin: button.dataset.coin, bed: button.dataset.bed, seed: semillaElegida });
        if (note) note.textContent = 'El servidor revisa la acción.';
      };
    });
    const open = root.querySelector('#finca-libro');
    if (open) open.onclick = () => openLibro();
  }

  function paintLibro() {
    const body = $('#libro-publico-body');
    if (!body || !window.LibroPublico) return;
    const data = Object.assign({}, contadores || {}, { extraFeed });
    if (!data.finca && contadores) data.finca = contadores.finca;
    body.innerHTML = LibroPublico.render(data);
  }

  function rememberCoins(ledger) {
    if (!ledger || !ledger.coins) return;
    if (prevCoins && window.LibroPublico) {
      const lines = LibroPublico.feedFromCoins(prevCoins, ledger);
      if (lines.length) extraFeed = lines.concat(extraFeed).slice(0, 12);
    }
    prevCoins = ledger;
    contadores = Object.assign({}, contadores || {}, ledger);
    paintLibro();
  }

  function openPanel() {
    const panel = $('#finca-panel');
    if (!panel) return;
    panel.hidden = false;
    send('ver');
    paintFarm();
  }

  function openLibro() {
    const panel = $('#libro-publico');
    if (panel) panel.hidden = false;
    pull();
    paintLibro();
  }

  function open(id) {
    if (id === 'finca_libro') openLibro();
    else openPanel();
  }

  async function pull() {
    try {
      const response = await fetch('/api/contadores', { cache: 'no-store' });
      if (!response.ok) return;
      const data = await response.json();
      rememberCoins(data);
      if (data.finca) contadores = data;
      paintLibro();
    } catch (e) {}
  }

  function onNet(message) {
    if (!message || typeof message !== 'object') return false;
    if (message.t === 'finca') {
      if (message.view) view = message.view;
      if (message.error) say(message.error);
      else if (message.ok && message.view) say(message.note || 'Listo.');
      if (message.spent && window.quitarDelInventario) quitarDelInventario(message.spent.item, message.spent.qty || 1);
      if (message.gained && window.LiveInk && LiveInk.giveItem) LiveInk.giveItem(message.gained.item, message.gained.qty || 1);
      paintFarm();
      paintDock();
      if (window.LIVE3D && LIVE3D.syncFinca) LIVE3D.syncFinca(view);
      if (window.MiCuenta && MiCuenta.tocar) MiCuenta.tocar();
      return false;
    }
    if (message.t === 'libro_publico' && message.contadores) {
      contadores = message.contadores;
      rememberCoins(message.contadores);
      paintLibro();
      return false;
    }
    if (message.t === 'welcome' && message.contadores) {
      contadores = message.contadores;
      rememberCoins(message.contadores);
    }
    if ((message.t === 'economy' || message.t === 'welcome' || message.t === 'acunar_result') && message.ledger) {
      rememberCoins(message.ledger);
    }
    return false;
  }

  function mount() {
    if (document.getElementById('finca-panel')) return;
    const farm = document.createElement('button');
    farm.type = 'button';
    farm.id = 'finca-open';
    farm.textContent = 'Cafetal';
    farm.onclick = () => openPanel();
    const book = document.createElement('button');
    book.type = 'button';
    book.id = 'libro-open';
    book.textContent = 'Libro Mayor';
    book.onclick = () => openLibro();
    const panel = document.createElement('section');
    panel.id = 'finca-panel';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Cafetal de Las Palmas');
    panel.innerHTML = '<header>Las Palmas · café, cacao y huerta <button type="button" id="finca-cerrar" aria-label="Cerrar">✕</button></header><div id="finca-body"></div>';
    const libro = document.createElement('section');
    libro.id = 'libro-publico';
    libro.hidden = true;
    libro.setAttribute('role', 'dialog');
    libro.setAttribute('aria-label', 'Libro mayor');
    libro.innerHTML = '<header>Libro Mayor <button type="button" id="libro-cerrar" aria-label="Cerrar">✕</button></header><div id="libro-publico-body"></div>';
    document.body.append(farm, book, panel, libro);
    panel.querySelector('#finca-cerrar').onclick = () => { panel.hidden = true; };
    libro.querySelector('#libro-cerrar').onclick = () => { libro.hidden = true; };
    paintFarm();
    pull();
    setInterval(pull, 5000);
    setInterval(() => {
      document.querySelectorAll('.huerta-bed[data-planted]').forEach(bed => {
        const planted = Number(bed.dataset.planted || 0);
        const ripe = Number((view && view.ripeSeconds) || 0);
        if (!planted || !ripe || !view || !view.serverNow) return;
        const skew = Date.now() / 1000 - Number(view.serverNow);
        const progress = Math.max(0, Math.min(1, (Date.now() / 1000 - skew - planted) / ripe));
        const bar = bed.querySelector('.huerta-bar > span');
        const meter = bed.querySelector('.huerta-bar');
        if (bar) bar.style.width = Math.round(progress * 100) + '%';
        if (meter) meter.setAttribute('aria-valuenow', String(Math.round(progress * 100)));
      });
    }, 1000);
    setInterval(() => {
      const panel = document.getElementById('finca-panel');
      const ws = window.LiveInk && LiveInk.state && LiveInk.state.net && LiveInk.state.net.ws;
      if (!panel || panel.hidden || !ws || ws.readyState !== 1) return;
      send('ver');
    }, 4000);
    setInterval(() => {
      paintDock();
      const ws = window.LiveInk && LiveInk.state && LiveInk.state.net && LiveInk.state.net.ws;
      if (!nearFarm() || !ws || ws.readyState !== 1) return;
      send('ver');
    }, 2000);
  }

  function zone() {
    const world = window.LiveInk && LiveInk.world;
    return (world && world.mapId) || 'city';
  }

  function nearFarm() {
    const world = window.LiveInk && LiveInk.world;
    const player = window.LiveInk && LiveInk.state && LiveInk.state.player;
    if (!world || !player || zone() !== 'city') return false;
    const spot = (world.waypoints || []).find(row => row.id === 'las_palmas');
    if (!spot) return false;
    return Math.max(Math.abs(player.fx - spot.x), Math.abs(player.fy - spot.y)) <= 30;
  }

  function ensureDock() {
    let dock = document.getElementById('oficio-cerca');
    if (dock) return dock;
    dock = document.createElement('div');
    dock.id = 'oficio-cerca';
    dock.hidden = true;
    dock.setAttribute('role', 'group');
    dock.setAttribute('aria-label', 'Acciones al acercarse');
    document.body.append(dock);
    return dock;
  }

  function mataDe(id) {
    return (window.FINCA_MATAS || []).find(row => row.id === id);
  }

  function juntoA(id) {
    const row = mataDe(id);
    const player = window.LiveInk && LiveInk.state && LiveInk.state.player;
    if (!row || !player) return false;
    return Math.max(Math.abs(player.fx - row.x), Math.abs(player.fy - row.y)) <= 2.4;
  }

  function cosecharCerca(id) {
    if (!juntoA(id)) {
      say('Acércate a la mata para cosechar.');
      return;
    }
    const row = ((view && view.plots) || []).find(item => item.id === id);
    if (row && row.stage !== 'maduro') {
      say('Esta mata todavía no está madura. Cada una vuelve a crecer sola.');
      return;
    }
    send('cosechar', { plot: id });
  }

  function paintDock() {
    const dock = ensureDock();
    const buttons = [];
    if (nearFarm() && view) {
      const ripe = (view.plots || []).filter(row => row.stage === 'maduro' && juntoA(row.id));
      ripe.forEach(row => {
        const name = row.crop === 'cafe' ? 'café' : 'cacao';
        buttons.push(`<button type="button" data-op="cosechar" data-plot="${esc(row.id)}">Cosechar<small>${name}</small></button>`);
      });
      buttons.push('<button type="button" data-op="recoger" data-crop="cafe">Recoger café</button>');
      buttons.push('<button type="button" data-op="procesar" data-crop="cafe">Procesar café</button>');
      buttons.push('<button type="button" data-op="exportar" data-crop="cafe">Exportar café</button>');
      buttons.push('<button type="button" data-op="recoger" data-crop="cacao">Recoger cacao</button>');
      buttons.push('<button type="button" data-op="procesar" data-crop="cacao">Procesar cacao</button>');
      buttons.push('<button type="button" data-op="exportar" data-crop="cacao">Exportar cacao</button>');
      const goods = view.goods || {};
      const batches = view.batches || {};
      [['cafe', 'café', goods.cafe_cereza], ['cacao', 'cacao', goods.cacao_baba]].forEach(([crop, name, have]) => {
        const working = !!batches[crop];
        if (!working && !(Number(have) > 0)) return;
        const both = (Number(goods.cafe_cereza) > 0 || batches.cafe) && (Number(goods.cacao_baba) > 0 || batches.cacao);
        const label = working ? (both ? `Procesar ${name}` : 'Procesar') : (both ? `Llevar ${name} al taller` : 'Llevar al taller');
        buttons.push(`<button type="button" data-op="procesar" data-crop="${crop}">${label}</button>`);
      });
    }
    const pulgar = document.getElementById('b-acunar-pulgar');
    const acunarEnColumna = pulgar && !pulgar.hidden;
    if ((zone() === 'mine' || zone() === 'central') && !acunarEnColumna) {
      buttons.push('<button type="button" data-op="acunar">Acuñar</button>');
    }
    if (!buttons.length) {
      dock.hidden = true;
      dock.innerHTML = '';
      return;
    }
    dock.hidden = false;
    dock.innerHTML = buttons.join('');
    dock.querySelectorAll('button').forEach(button => {
      button.onclick = () => {
        if (button.dataset.op === 'acunar') {
          if (window.Acunar) Acunar.open();
          return;
        }
        send(button.dataset.op, { plot: button.dataset.plot, crop: button.dataset.crop });
      };
    });
  }

  fetch('finca-textos.json?v=cierre-r1').then(res => res.ok ? res.json() : null).then(doc => {
    if (!doc) return;
    textos = doc;
    paintFarm();
  }).catch(() => {});
  window.Finca = { onNet, open, openPanel, openLibro, pull, cosecharCerca, paintDock };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
