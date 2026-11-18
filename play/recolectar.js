/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Botón grande al acercarse a una mata madura o a una roca. */
(() => {
  'use strict';
  const CERCA = 2.4;

  function jugador() {
    return window.LiveInk && LiveInk.state && LiveInk.state.player;
  }
  function cerca(x, y) {
    const p = jugador();
    if (!p) return false;
    return Math.max(Math.abs(p.fx - x), Math.abs(p.fy - y)) <= CERCA;
  }
  function boton() {
    let el = document.getElementById('recolectar');
    if (el) return el;
    el = document.createElement('button');
    el.type = 'button';
    el.id = 'recolectar';
    el.hidden = true;
    document.body.append(el);
    return el;
  }
  function guia() {
    if (localStorage.getItem('lifeinc.guia-smc')) return;
    if (document.getElementById('guia-smc')) return;
    const box = document.createElement('section');
    box.id = 'guia-smc';
    box.setAttribute('role', 'dialog');
    box.innerHTML = '<h2>Tus primeras monedas</h2><ol><li>Acércate y toca <b>Recoger</b> o <b>Minar</b>.</li><li>Abre <b>Inventario</b>.</li><li>Toca el objeto y <b>Cambiar por SMC</b>.</li></ol><button type="button" id="guia-smc-ok">Entendido</button>';
    document.body.append(box);
    document.getElementById('guia-smc-ok').onclick = () => {
      try { localStorage.setItem('lifeinc.guia-smc', '1'); } catch (e) {}
      box.remove();
    };
  }
  function pintar() {
    const el = boton();
    const p = jugador();
    if (!p || !document.body.classList.contains('in-game')) { el.hidden = true; return; }
    let accion = null;
    const plots = window.Finca && Finca.vista ? Finca.vista() : [];
    for (const mata of window.FINCA_MATAS || []) {
      const row = plots.find(item => item.id === mata.id);
      if (!row || row.stage !== 'maduro' || !cerca(mata.x, mata.y)) continue;
      const nombre = mata.crop === 'cafe' ? 'café' : 'cacao';
      accion = { texto: 'Recoger', sub: nombre, run: () => window.Finca && Finca.cosecharCerca(mata.id) };
      break;
    }
    const nodes = window.LiveInk.state && LiveInk.state.nodes;
    if (!accion && nodes && nodes.forEach) {
      nodes.forEach((node) => {
        if (accion) return;
        const d = node.def;
        if (!d || node.state !== 'active') return;
        if (d.type !== 'mineral_rock' && d.type !== 'nodo_oro_fluvial') return;
        if (!cerca(d.x, d.y)) return;
        const nombre = d.type === 'nodo_oro_fluvial' ? 'oro del río' : (d.mineral === 'oro' ? 'mineral de oro' : d.mineral === 'plata' ? 'mineral de plata' : 'mineral de cobre');
        accion = {
          texto: 'Minar',
          sub: nombre,
          run: () => window.LiveInk && LiveInk.interact && LiveInk.interact(d.id),
        };
      });
    }
    if (!accion) { el.hidden = true; el.onclick = null; return; }
    el.hidden = false;
    el.innerHTML = accion.texto + '<small>' + accion.sub + '</small>';
    el.onclick = accion.run;
  }
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'e' && event.key !== 'E') return;
    const tag = event.target && event.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    const el = document.getElementById('recolectar');
    if (!el || el.hidden) return;
    event.preventDefault();
    el.click();
  });
  window.Recolectar = { pintar, guia };
  setInterval(pintar, 300);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', guia);
  else setTimeout(guia, 1200);
})();
