/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* El texto del letrero llega del servidor. Aquí no hay topes escritos a mano. */
(() => {
  'use strict';
  let data = null;
  let timer = 0;

  function cantidad(number) {
    const value = Number(number);
    if (!Number.isFinite(value)) return '';
    if (Math.abs(value - Math.round(value)) < 1e-6) {
      return Math.round(value).toLocaleString('es-CO');
    }
    const [whole, frac] = value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '').split('.');
    return Number(whole).toLocaleString('es-CO') + (frac ? ',' + frac : '');
  }

  function hoyLocal() {
    const cupos = window.LiveInk && LiveInk.state && LiveInk.state.cupos;
    const coins = cupos && cupos.coins;
    if (!coins) return [];
    return ['simoncoin', 'simonplata', 'simonchis'].map((id) => {
      const row = coins[id];
      if (!row || row.left == null) return '';
      return 'Hoy te quedan ' + cantidad(row.left) + ' ' + row.name + '.';
    }).filter(Boolean);
  }

  function clockText() {
    if (!data || !data.resetAt) return '';
    const left = Math.max(0, data.resetAt * 1000 - Date.now());
    const total = Math.floor(left / 1000);
    const h = Math.floor(total / 3600);
    const m = Math.floor(total / 60) % 60;
    const s = total % 60;
    const pad = (n) => (n < 10 ? '0' + n : String(n));
    const when = data.reset ? ' (' + data.reset + ')' : '';
    return 'Falta ' + h + ':' + pad(m) + ':' + pad(s) + ' para el próximo reinicio' + when + '.';
  }

  function fill(id, lines) {
    const box = document.getElementById(id);
    if (!box) return;
    box.replaceChildren();
    lines.forEach((line) => {
      const p = document.createElement('p');
      p.textContent = line;
      box.append(p);
    });
  }

  function fillMonedas() {
    const box = document.getElementById('letrero-monedas');
    if (!box) return;
    box.replaceChildren();
    const supply = (data && data.supply) || {};
    [
      ['simoncoin', 'Simoncoin es la moneda de oro. Sólo habrá ', supply.simoncoin],
      ['simonplata', 'Simonplata es la moneda de plata. Sólo habrá ', supply.simonplata],
      ['simonchis', 'Simonchis son las monedas de cobre. Existirán ', supply.simonchis],
    ].forEach(([id, lead, max]) => {
      if (max == null) return;
      const p = document.createElement('p');
      const img = document.createElement('img');
      img.alt = '';
      img.src = 'assets/sara-cartel/' + id + '.svg';
      const span = document.createElement('span');
      span.textContent = lead + cantidad(max) + '. Nadie puede crear más ni copiarlas.';
      p.append(img, span);
      box.append(p);
    });
  }

  function fillMinar() {
    const list = document.getElementById('letrero-minar');
    if (!list) return;
    const rates = (data && data.rates) || {};
    const lines = [
      'Entrá con tu apodo.',
      'Viajá a la Mina de Las Palmas, o caminá hasta allá.',
      'Picá una veta con la pica. El mineral cae en la mochila.',
      'Acercate al horno del centro.',
      'Elegí oro, plata o cobre y acuñá, sin pasar del tope del día.',
    ];
    if (rates.simoncoin && rates.simonplata && rates.simonchis) {
      lines.push(
        cantidad(rates.simoncoin) + ' oros crudos hacen 1 Simoncoin, ' +
        cantidad(rates.simonplata) + ' platas crudas hacen 1 Simonplata y ' +
        cantidad(rates.simonchis) + ' cobres crudos hacen 1 Simonchis.'
      );
    }
    list.replaceChildren();
    lines.forEach((line) => {
      const li = document.createElement('li');
      li.textContent = line;
      list.append(li);
    });
  }

  function paint() {
    fillMonedas();
    fill('letrero-texto', (data && data.lines) || []);
    fill('letrero-hoy', (data && data.hoy && data.hoy.length) ? data.hoy : hoyLocal());
    fill('letrero-pasos', ((data && data.steps) || []).map((step) => step.text).filter(Boolean));
    fillMinar();
    const clock = document.getElementById('letrero-cuenta');
    if (clock) clock.textContent = clockText();
    if (data && data.resetAt && data.resetAt * 1000 - Date.now() <= 0) load();
  }

  function ensure() {
    let panel = document.getElementById('letrero-mina');
    if (panel) return panel;
    panel = document.createElement('section');
    panel.id = 'letrero-mina';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Reglas de la mina');
    panel.innerHTML = '<header><strong>Reglas de la Mina</strong><button type="button" id="letrero-cerrar" aria-label="Cerrar">✕</button></header><p id="letrero-cuenta"></p><h3>Cómo funcionan</h3><div id="letrero-monedas"></div><div id="letrero-texto"></div><h3>Hoy</h3><div id="letrero-hoy"></div><h3>Cómo minar y acuñar</h3><ol id="letrero-minar"></ol><h3>Recompensas</h3><div id="letrero-pasos"></div><p id="letrero-aviso">Si el mundo ya llegó al máximo de una moneda, el horno se detiene. No sale ni una de más.</p>';
    document.body.append(panel);
    panel.querySelector('#letrero-cerrar').onclick = () => close();
    return panel;
  }

  function close() {
    const panel = document.getElementById('letrero-mina');
    if (panel) panel.hidden = true;
    clearInterval(timer);
    timer = 0;
  }

  function open() {
    const panel = ensure();
    panel.hidden = false;
    paint();
    clearInterval(timer);
    timer = setInterval(paint, 1000);
    load();
  }

  function setNear() {}

  function load() {
    fetch('/reglas-mina', { cache: 'no-store', credentials: 'same-origin' }).then((r) => r.json()).then((body) => {
      data = body;
      paint();
    }).catch(() => {});
  }

  window.Letrero = { open, setNear, paint, load, close };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
