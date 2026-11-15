/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Cajón de la rueda, reloj de 1777 y las tres monedas. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  let clockLabel = '';

  function grupo(n) {
    const value = Number(n);
    if (!Number.isFinite(value)) return '0';
    return value.toLocaleString('es-CO', { maximumFractionDigits: 8 });
  }
  function coinText(base, subs) {
    if (window.Simulacion && subs === Simulacion.SUBS && Simulacion.formatSai) {
      return Simulacion.formatSai(base).replace(/\s*SMC$/, '').replace(/\s*SMP$/, '');
    }
    return grupo(base);
  }
  function rows() {
    const ledger = (window.__ELJARDIN && __ELJARDIN.ledger) || {};
    const list = ledger.coins || [
      { id: 'simoncoin', name: 'Simoncoin', minted: 0, max: 21000000 },
      { id: 'simonplata', name: 'Simonplata', minted: 0, max: 84000000 },
      { id: 'simonchis', name: 'Simonchis', minted: 0, max: 333000000 },
    ];
    return list.slice(0, 3);
  }
  function rawBalances() {
    /* Simon Coins (oro) = Simoncoin en SMH. Simon Plata (plata) = Simonplata en SPH.
       Simonchis (cobre) es la moneda entera de cobre, no el SMH del oro. */
    const S = window.__ELJARDIN || {};
    const ledger = S.ledger && S.ledger.balances;
    const name = window.nombrePropio ? nombrePropio() : '';
    let simoncoin = ledger ? ledger.simoncoin : 0;
    let simonplata = ledger ? ledger.simonplata : 0;
    let simonchis = ledger ? ledger.simonchis : 0;
    if (!ledger && S.econ && S.econ.wallets && name) {
      simoncoin = S.econ.wallets[name] || 0;
      simonplata = (S.plata && S.plata.balanceSph) || 0;
      simonchis = (S.ledger && S.ledger.balances && S.ledger.balances.simonchis) || 0;
    }
    return { simoncoin: simoncoin || 0, simonplata: simonplata || 0, simonchis: simonchis || 0 };
  }
  function labeled() {
    const raw = rawBalances();
    const sim = window.Simulacion;
    return {
      oro: sim && sim.formatSai ? sim.formatSai(raw.simoncoin) : grupo(raw.simoncoin),
      plata: sim && sim.formatPlata ? sim.formatPlata(raw.simonplata) : grupo(raw.simonplata),
      cobre: grupo(raw.simonchis),
    };
  }
  function balances() {
    const raw = rawBalances();
    return {
      simoncoin: coinText(raw.simoncoin, window.Simulacion ? Simulacion.SUBS : 100000000),
      simonplata: window.Simulacion && Simulacion.formatPlata ? Simulacion.formatPlata(raw.simonplata).replace(/\s*SMP$/, '') : grupo(raw.simonplata),
      simonchis: grupo(raw.simonchis),
    };
  }
  function putText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }
  function paint() {
    const nick = $('#hud-nick');
    if (nick) nick.textContent = window.nombrePropio ? nombrePropio() : 'Viajero';
    const clock = $('#reloj-ahora');
    if (clock && clockLabel) clock.textContent = clockLabel;
    const money = balances();
    const shown = labeled();
    const line = $('#hud-saldos');
    if (line) line.textContent = `Simoncoin ${shown.oro} · Simonplata ${shown.plata} · Simonchis ${shown.cobre}`;
    putText('barra-oro', shown.oro);
    putText('barra-plata', shown.plata);
    putText('barra-cobre', shown.cobre);
    putText('libro-saldo-oro', shown.oro);
    putText('libro-saldo-plata', shown.plata);
    putText('libro-saldo-cobre', shown.cobre);
    const box = $('#cajon-monedas');
    if (!box) return;
    box.replaceChildren();
    for (const row of rows()) {
      const p = document.createElement('p');
      p.className = 'cajon-moneda';
      const minted = grupo(row.minted);
      const max = grupo(row.max);
      p.innerHTML = `<span><b>${row.name}</b><br>Tuyo: ${money[row.id] || '0'}</span><span>Acuñadas ${minted}<br>de ${max}</span>`;
      box.appendChild(p);
    }
  }
  function rememberClock(data) {
    if (!data || !data.label) return;
    clockLabel = data.label;
    if (window.__ELJARDIN) __ELJARDIN.reloj = data;
    paint();
  }
  async function pullClock() {
    try {
      const response = await fetch('/api/reloj', { cache: 'no-store' });
      if (!response.ok) return;
      rememberClock(await response.json());
    } catch (e) {}
    try {
      const response = await fetch('/api/contadores', { cache: 'no-store' });
      if (!response.ok) return;
      const ledger = await response.json();
      if (window.__ELJARDIN) {
        const prev = __ELJARDIN.ledger && __ELJARDIN.ledger.balances;
        __ELJARDIN.ledger = Object.assign({}, ledger, prev ? { balances: prev } : {});
      }
      paint();
    } catch (e) {}
  }
  function lugares() {
    const world = window.LiveInk && LiveInk.world;
    const list = [{ id: 'casa', name: 'Casa' }, { id: 'mina', name: 'Mina de Las Palmas', mine: true }];
    if (window.Casa && Casa.PARK_STAND) list.push({ id: 'parque', name: 'Parque de Envigado', x: Casa.PARK_STAND.x, y: Casa.PARK_STAND.y });
    if (window.EnvigadoPark && EnvigadoPark.skateTiles) {
      const tile = EnvigadoPark.skateTiles()[0];
      if (tile) list.push({ id: 'skate', name: 'Zona skate', x: tile.x, y: tile.y });
    }
    const seen = new Set(list.map(item => item.id));
    for (const point of (world && world.waypoints) || []) {
      if (!point || seen.has(point.id) || point.x == null) continue;
      seen.add(point.id);
      list.push({ id: point.id, name: point.name || point.id, x: point.x, y: point.y });
    }
    return list;
  }
  function paintPlaces() {
    const box = $('#cajon-lugares');
    if (!box) return;
    box.replaceChildren();
    for (const place of lugares()) {
      const row = document.createElement('p');
      row.className = 'cajon-lugar';
      const name = document.createElement('b');
      name.textContent = place.name;
      const go = document.createElement('button');
      go.type = 'button';
      go.textContent = place.mine ? 'Ir a la mina / Picar' : 'Ir a caballo';
      go.onclick = () => {
        if (place.mine && window.LiveInk && LiveInk.goMine) LiveInk.goMine();
        else if (window.LiveInk && LiveInk.rideHorseTo) LiveInk.rideHorseTo(place);
        closeDrawer();
      };
      row.append(name, go);
      box.appendChild(row);
    }
  }
  function closeDrawer() {
    const menu = $('#hud-gear-menu');
    const gear = $('#hud-gear');
    if (menu) menu.hidden = true;
    if (gear) gear.setAttribute('aria-expanded', 'false');
  }
  function showPiece(id) {
    const el = document.getElementById(id);
    const host = $('#cajon-panel');
    if (!el || !host) return;
    host.appendChild(el);
    el.hidden = false;
    el.classList.add('en-cajon');
    el.classList.remove('hud-cerrado');
  }
  function fillDrawer() {
    const menu = $('#hud-gear-menu');
    if (!menu || menu.dataset.cajon) return;
    menu.dataset.cajon = '1';
    const block = document.createElement('div');
    block.innerHTML = [
      '<h2>Menú</h2>',
      '<section id="cajon-monedas" aria-label="Las tres monedas"></section>',
      '<section class="cajon-guia" id="guia-monedas">',
      '<h3>Cómo funcionan</h3>',
      '<p><b>Simoncoin</b> es la moneda de oro. Sólo existirán 21.000.000. Nadie puede crear más, cambiar ese número ni copiar una.</p>',
      '<p><b>Simonplata</b> es la moneda de plata. Sólo existirán 84.000.000. Nadie puede crear más, cambiar ese número ni copiar una.</p>',
      '<p><b>Simonchis</b> son las monedas de cobre. Existirán 333.000.000.</p>',
      '<p>El libro de arriba dice cuántas van y cuántas pueden existir. Tu número es el de la izquierda.</p>',
      '<h3>Cómo minar y acuñar</h3>',
      '<ol>',
      '<li>Entra con tu cuenta.</li>',
      '<li>Abre Viajar y elige la mina, o camina hasta Las Palmas.</li>',
      '<li>Entra a la mina y pica una veta con la pica. El mineral cae en la mochila.</li>',
      '<li>Acércate al horno del centro.</li>',
      '<li>Elige el mineral: oro, plata o cobre.</li>',
      '<li>Picar y lavar sólo guarda metal en la mochila. Eso no crea monedas.</li>',
      '<li>En el horno, Acuñar cambia el metal por monedas: 5 oros crudos hacen 1 Simoncoin, 4 platas crudas hacen 1 Simonplata y 3 cobres crudos hacen 1 Simonchis.</li>',
      '<li>Hoy puedes acuñar hasta el tope del día. Se reinicia a las 7:00 p. m. (hora de Bogotá).</li>',
      '</ol>',
      '<p>Si el número ya llegó al máximo, el horno se detiene. No aparece ni una moneda de más.</p>',
      '</section>',
      '<h3>Viajar</h3><div id="cajon-lugares"></div>',
      '<h3>Caballo</h3><p>Tu caballo te lleva solo por el camino. También puedes llamarlo a la puerta.</p>',
      '<button type="button" id="cajon-llamar">Llamar a mi caballo</button>',
      '<h3>Sonido</h3>',
      '<button type="button" id="cajon-sonido" aria-pressed="false">Sonido: apagado</button>',
      '<label class="sonido-vol">Volumen <input id="cajon-volumen" type="range" min="0" max="100" value="70" aria-label="Volumen"></label>',
      '<h3>Atajos</h3>',
      '<button type="button" id="cajon-perfil">Perfil</button>',
      '<button type="button" id="cajon-minar">Acuñar monedas</button>',
      '<button type="button" id="cajon-plata">Simonplata</button>',
      '<button type="button" id="cajon-herramientas">Herramientas</button>',
      '<button type="button" id="cajon-barra">Barra rápida</button>',
      '<button type="button" id="cajon-simon">Simon</button>',
      '<button type="button" id="cajon-ajustes">Ajustes de la pantalla</button>',
      '<div id="cajon-panel"></div>',
    ].join('');
    const closer = document.createElement('button');
    closer.type = 'button';
    closer.id = 'cajon-cerrar';
    closer.textContent = '✕';
    closer.setAttribute('aria-label', 'Cerrar menú');
    closer.onclick = (e) => { e.stopPropagation(); closeDrawer(); };
    block.prepend(closer);
    menu.prepend(block);
    if (!document.getElementById('cajon-fondo')) {
      const veil = document.createElement('button');
      veil.type = 'button';
      veil.id = 'cajon-fondo';
      veil.hidden = true;
      veil.setAttribute('aria-label', 'Cerrar menú');
      veil.onclick = () => closeDrawer();
      document.body.append(veil);
      new MutationObserver(() => { veil.hidden = menu.hidden; }).observe(menu, { attributes: true, attributeFilter: ['hidden'] });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !menu.hidden) { closeDrawer(); e.preventDefault(); }
      });
    }
    $('#cajon-llamar').onclick = () => { if (window.LiveInk) LiveInk.summonPersonalHorse(); closeDrawer(); };
    $('#cajon-perfil').onclick = () => showPiece('hud-perfil');
    $('#cajon-minar').onclick = () => { closeDrawer(); if (window.Acunar) Acunar.open(); };
    $('#cajon-plata').onclick = () => showPiece('plata-panel');
    $('#cajon-herramientas').onclick = () => showPiece('world-tools');
    $('#cajon-barra').onclick = () => showPiece('hotbar');
    $('#cajon-simon').onclick = () => { location.href = '/play/simon.html'; };
    $('#cajon-ajustes').onclick = () => { const start = $('#hud-edit-start'); if (start) start.click(); };
    if (window.Sonido) Sonido.bind();
    let startX = 0;
    menu.addEventListener('pointerdown', (e) => { startX = e.clientX; });
    menu.addEventListener('pointerup', (e) => { if (e.clientX - startX > 70) closeDrawer(); });
    try { paint(); } catch (e) { console.error(e); }
    try { paintPlaces(); } catch (e) { console.error(e); }
    const oro = $('#barra-oro-btn');
    const plata = $('#barra-plata-btn');
    function flip(storage, mark) {
      try {
        const now = localStorage.getItem(storage);
        localStorage.setItem(storage, now === mark ? '' : mark);
      } catch (e) {}
      if (window.Simulacion && Simulacion.paintHud) Simulacion.paintHud();
      else paint();
    }
    if (oro && !oro.dataset.unidad) {
      oro.dataset.unidad = '1';
      oro.addEventListener('click', () => flip('lifeinc.unidad', 'SMH'));
    }
    if (plata && !plata.dataset.unidad) {
      plata.dataset.unidad = '1';
      plata.addEventListener('click', () => flip('lifeinc.unidad.plata', 'SPH'));
    }
  }
  function mountPicar() {
    if (document.getElementById('b-picar')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.id = 'b-picar';
    button.textContent = 'Picar';
    button.title = 'Ir a la mina y picar';
    button.onclick = () => { if (window.LiveInk && LiveInk.goMine) LiveInk.goMine(); };
    document.body.append(button);
  }
  function boot() {
    mountPicar();
    document.body.classList.add('mapa-limpio');
    pullClock();
    fillDrawer();
    const gear = $('#hud-gear');
    if (gear && !gear.dataset.cajon) {
      gear.dataset.cajon = '1';
      gear.addEventListener('click', () => { paint(); paintPlaces(); });
    }
    pullClock();
    setInterval(pullClock, 20000);
    setInterval(paint, 1500);
  }
  window.Cajon = { paint, labeled, balances, clockText: () => clockLabel, rememberClock, pullClock };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
