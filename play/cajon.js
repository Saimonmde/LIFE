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
    const subs = window.Simulacion ? Simulacion.SUBS : 100000000;
    const compact = (base, whole) => {
      const value = Number(base) || 0;
      if (window.Simulacion && Simulacion.formatCompact) return Simulacion.formatCompact(whole ? value : value / subs);
      return grupo(whole ? value : value / subs);
    };
    return {
      simoncoin: compact(simoncoin, false),
      simonplata: compact(simonplata, false),
      simonchis: compact(simonchis, true),
      exactSimoncoin: window.Simulacion && Simulacion.formatPair ? Simulacion.formatPair(simoncoin) : grupo(simoncoin) + ' SMH',
      exactSimonplata: window.Simulacion && Simulacion.formatPlataPair ? Simulacion.formatPlataPair(simonplata) : grupo(simonplata) + ' SPH',
      exactSimonchis: grupo(simonchis) + ' Simonchis',
    };
  }
  function paint() {
    const nick = $('#hud-nick');
    if (nick) nick.textContent = window.nombrePropio ? nombrePropio() : 'Viajero';
    const clock = $('#reloj-ahora');
    if (clock && clockLabel) clock.textContent = clockLabel;
    const money = balances();
    const line = $('#hud-saldos');
    if (line) {
      line.textContent = `Simoncoin ${money.simoncoin} SMC · Simonplata ${money.simonplata} SMP · Simonchis ${money.simonchis}`;
      line.title = [money.exactSimoncoin, money.exactSimonplata, money.exactSimonchis].filter(Boolean).join(' · ');
    }
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
        if (window.Simulacion && Simulacion.reflejarMonedas) Simulacion.reflejarMonedas();
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
      '<h3>En corto</h3>',
      '<ol>',
      '<li>🏙 Saimon City. Valle de Aburrá. Año 1777.</li>',
      '<li>⛏ Ve a la mina. Pica el metal.</li>',
      '<li>🪙 En el horno, Acuñar guarda las monedas en tu inventario.</li>',
      '<li>🏠 Descansar / Ir a casa. Tu mascota te espera.</li>',
      '</ol>',
      '<p>5 oros crudos hacen 1 Simoncoin. 4 platas, 1 Simonplata. 3 cobres, 1 Simonchis. El tope del día se reinicia a las 7:00 p. m.</p>',
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
      '<button type="button" id="cajon-finca">Cafetal de Las Palmas</button>',
      '<button type="button" id="cajon-chat">Chat del mundo</button>',
      '<button type="button" id="cajon-gente">Jugadores en línea</button>',
      '<button type="button" id="cajon-libro">Libro Mayor</button>',
      '<button type="button" id="cajon-madre">Libro madre</button>',
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
    const madre = $('#cajon-madre');
    if (madre) madre.onclick = () => { closeDrawer(); if (window.LibroMadre) LibroMadre.open(); };
    const chatBtn = $('#cajon-chat');
    if (chatBtn) chatBtn.onclick = () => { closeDrawer(); if (window.ChatUI) ChatUI.setOpen(true, true); };
    const genteBtn = $('#cajon-gente');
    if (genteBtn) genteBtn.onclick = () => {
      closeDrawer();
      const list = document.getElementById('mundo-lista');
      const tab = document.getElementById('mundo-tab');
      if (list) list.hidden = false;
      if (tab) tab.setAttribute('aria-expanded', 'true');
    };
    $('#cajon-plata').onclick = () => showPiece('plata-panel');
    $('#cajon-herramientas').onclick = () => showPiece('world-tools');
    $('#cajon-barra').onclick = () => showPiece('hotbar');
    $('#cajon-simon').onclick = () => { location.href = '/play/simon.html'; };
    $('#cajon-ajustes').onclick = () => { const start = $('#hud-edit-start'); if (start) start.click(); };
    if (window.Sonido) Sonido.bind();
    const openFinca = $('#cajon-finca'); if (openFinca) openFinca.onclick = () => { if (window.Finca) Finca.openPanel(); closeDrawer(); };
    const openLibro = $('#cajon-libro'); if (openLibro) openLibro.onclick = () => { if (window.Finca) Finca.openLibro(); closeDrawer(); };
    let startX = 0;
    menu.addEventListener('pointerdown', (e) => { startX = e.clientX; });
    menu.addEventListener('pointerup', (e) => { if (e.clientX - startX > 70) closeDrawer(); });
    try { paint(); } catch (e) { console.error(e); }
    try { paintPlaces(); } catch (e) { console.error(e); }
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
    if (document.getElementById('b-acunar-pulgar')) return;
    const mint = document.createElement('button');
    mint.type = 'button';
    mint.id = 'b-acunar-pulgar';
    mint.textContent = 'Acuñar';
    mint.title = 'Acuñar o cambiar monedas';
    mint.onclick = () => { if (window.Acunar) Acunar.open(); };
    document.body.append(mint);
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
  window.Cajon = { paint, clockText: () => clockLabel, rememberClock, pullClock };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
