/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* El texto del letrero llega del servidor. Aquí no hay topes escritos a mano. */
(() => {
  'use strict';
  let data = null;
  let pinned = false;

  function cantidad(number) {
    const value = Number(number);
    if (!Number.isFinite(value)) return '';
    if (Math.abs(value - Math.round(value)) < 1e-6) {
      return Math.round(value).toLocaleString('es-CO');
    }
    const [whole, frac] = value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '').split('.');
    return Number(whole).toLocaleString('es-CO') + (frac ? ',' + frac : '');
  }

  function hoy() {
    const cupos = window.LiveInk && LiveInk.state && LiveInk.state.cupos;
    const coins = cupos && cupos.coins;
    if (!coins) return [];
    return ['simoncoin', 'simonplata', 'simonchis'].map((id) => {
      const row = coins[id];
      if (!row || row.left == null) return '';
      return 'Hoy te quedan ' + cantidad(row.left) + ' ' + row.name + '.';
    }).filter(Boolean);
  }

  function paint() {
    const box = document.getElementById('letrero-texto');
    if (!box) return;
    const lines = ((data && data.lines) || []).concat(hoy());
    box.replaceChildren();
    lines.forEach((line) => {
      const p = document.createElement('p');
      p.textContent = line;
      box.append(p);
    });
  }

  function ensure() {
    let panel = document.getElementById('letrero-mina');
    if (panel) return panel;
    panel = document.createElement('section');
    panel.id = 'letrero-mina';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Reglas de la mina');
    panel.innerHTML = '<header><strong>Reglas de la mina</strong><button type="button" id="letrero-cerrar" aria-label="Cerrar">✕</button></header><div id="letrero-texto"></div>';
    document.body.append(panel);
    panel.querySelector('#letrero-cerrar').onclick = () => { pinned = false; panel.hidden = true; };
    return panel;
  }

  function open() {
    const panel = ensure();
    panel.hidden = false;
    pinned = true;
    paint();
  }

  function setNear(near) {
    const panel = ensure();
    if (near) {
      panel.hidden = false;
      paint();
      return;
    }
    if (!pinned) panel.hidden = true;
  }

  function load() {
    fetch('/reglas-mina', { cache: 'no-store' }).then((r) => r.json()).then((body) => {
      data = body;
      paint();
    }).catch(() => {});
  }

  window.Letrero = { open, setNear, paint, load };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
