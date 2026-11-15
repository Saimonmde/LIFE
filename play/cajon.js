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
  function balances() {
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
    return {
      simoncoin: coinText(simoncoin, window.Simulacion ? Simulacion.SUBS : 100000000),
      simonplata: window.Simulacion && Simulacion.formatPlata ? Simulacion.formatPlata(simonplata).replace(/\s*SMP$/, '') : grupo(simonplata),
      simonchis: grupo(simonchis),
    };
  }
  function paint() {
    const nick = $('#hud-nick');
    if (nick) nick.textContent = window.nombrePropio ? nombrePropio() : 'Viajero';
    const clock = $('#reloj-ahora');
    if (clock && clockLabel) clock.textContent = clockLabel;
    const money = balances();
    const line = $('#hud-saldos');
    if (line) line.textContent = `Simoncoin ${money.simoncoin} · Simonplata ${money.simonplata} · Simonchis ${money.simonchis}`;
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
    const list = [{ id: 'casa', name: 'Casa' }];
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
      go.textContent = 'Ir a caballo';
      go.onclick = () => {
        if (window.LiveInk && LiveInk.rideHorseTo) LiveInk.rideHorseTo(place);
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
    menu.prepend(block);
    $('#cajon-llamar').onclick = () => { if (window.LiveInk) LiveInk.summonPersonalHorse(); closeDrawer(); };
    $('#cajon-perfil').onclick = () => showPiece('hud-perfil');
    $('#cajon-minar').onclick = () => { closeDrawer(); if (window.Acunar) Acunar.open(); };
    $('#cajon-plata').onclick = () => showPiece('plata-panel');
    $('#cajon-herramientas').onclick = () => showPiece('world-tools');
    $('#cajon-barra').onclick = () => showPiece('hotbar');
    $('#cajon-simon').onclick = () => { location.href = '/play/simon.html'; };
    $('#cajon-ajustes').onclick = () => { const start = $('#hud-edit-start'); if (start) start.click(); };
    let startX = 0;
    menu.addEventListener('pointerdown', (e) => { startX = e.clientX; });
    menu.addEventListener('pointerup', (e) => { if (e.clientX - startX > 70) closeDrawer(); });
    try { paint(); } catch (e) { console.error(e); }
    try { paintPlaces(); } catch (e) { console.error(e); }
  }
  function boot() {
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
  window.Cajon = { paint, clockText: () => clockLabel, rememberClock, pullClock };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
