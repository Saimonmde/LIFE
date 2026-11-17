/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Cinco botones grandes abajo. Una hoja a la vez. */
(() => {
  'use strict';
  const estrecho = () => matchMedia('(max-width: 820px)').matches || document.documentElement.classList.contains('movil');
  const HOJAS = ['w-inv', 'w-hab', 'city-map', 'hoja-cambio', 'hud-gear-menu', 'w-libro', 'furnace-panel', 'mi-cuenta'];
  let cantidad = 1;

  function $(id) { return document.getElementById(id); }
  function cerrar() {
    HOJAS.forEach((id) => { const el = $(id); if (el) el.hidden = true; });
    document.querySelectorAll('#pulgar button').forEach((b) => b.setAttribute('aria-pressed', 'false'));
  }
  function abrir(id, boton) {
    const el = $(id);
    const ya = el && !el.hidden;
    cerrar();
    if (!el || ya) return;
    el.hidden = false;
    if (boton) boton.setAttribute('aria-pressed', 'true');
    if (id === 'hoja-cambio') pintarCambio();
  }
  function tengo(id) {
    const S = window.LiveInk && LiveInk.state;
    if (!S) return 0;
    if (id === 'simonplata') return Math.floor(Number(S.plata && S.plata.balanceSph) || 0);
    const purse = S.purse && S.purse.items;
    if (purse && purse[id] != null) return Math.floor(Number(purse[id]) || 0);
    return (S.inv || []).reduce((sum, slot) => sum + (slot && slot.item === id ? slot.qty : 0), 0);
  }
  function fondo() {
    const S = window.LiveInk && LiveInk.state;
    const box = S && S.plata;
    return Math.floor(Number(box && (box.poolSmh || box.smcPoolSmh) || 0) || 0);
  }
  function puesto() {
    const S = window.LiveInk && LiveInk.state;
    return Math.floor(Number(S && S.puestoSmh) || 0);
  }
  function pintarCambio() {
    const vista = $('cambio-vista');
    const dar = ($('cambio-doy') || {}).value;
    const recibir = ($('cambio-recibo') || {}).value;
    const quoted = window.CambioSimple ? CambioSimple.quote(dar, recibir, cantidad, tengo(dar), fondo(), puesto()) : { ok: false, texto: 'Entra al mundo para cambiar.', maximo: 0 };
    if (vista) vista.textContent = quoted.texto;
    const ok = $('cambio-ok');
    if (ok) ok.disabled = !quoted.ok;
    const n = $('cambio-n');
    if (n) n.textContent = String(quoted.das || cantidad);
  }
  function confirmar() {
    const dar = $('cambio-doy').value;
    const recibir = $('cambio-recibo').value;
    const net = window.LiveInk && LiveInk.state && LiveInk.state.net;
    if (!net || !net.ws || net.ws.readyState !== 1) {
      const vista = $('cambio-vista');
      if (vista) vista.textContent = 'Entra al mundo para cambiar. No se movió nada.';
      return;
    }
    const msg = dar === 'simonplata'
      ? { t: 'cambio_simple', give: dar, receive: recibir, qty: cantidad }
      : { t: 'cambio_simple', give: dar, receive: recibir, qty: cantidad };
    net.ws.send(JSON.stringify(msg));
  }
  function mount() {
    if ($('pulgar') || !estrecho()) return;
    const bar = document.createElement('nav');
    bar.id = 'pulgar';
    bar.setAttribute('aria-label', 'Acciones principales');
    const items = [
      ['inv', 'Inventario', () => { const b = $('b-inv'); if (b) b.click(); }],
      ['cam', 'Intercambio', () => abrir('hoja-cambio', bar.querySelector('[data-pulgar="cam"]'))],
      ['niv', 'Niveles', () => { const b = $('b-hab'); if (b) b.click(); }],
      ['mapa', 'Mapa', () => { const b = $('b-globo'); if (b) b.click(); }],
      ['chat', 'Chat', () => { if (window.ChatUI) ChatUI.setOpen(true, true); }],
      ['menu', 'Menú', () => { const b = $('hud-gear'); if (b) b.click(); }],
      ['cuenta', 'Cuenta', () => { if (window.MiCuenta) MiCuenta.abrir(); }],
    ];
    items.forEach(([id, label, fn]) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.dataset.pulgar = id;
      b.textContent = label;
      b.setAttribute('aria-pressed', 'false');
      b.onclick = fn;
      bar.append(b);
    });
    const hoja = document.createElement('section');
    hoja.id = 'hoja-cambio';
    hoja.hidden = true;
    hoja.setAttribute('aria-label', 'Intercambio');
    hoja.innerHTML = [
      '<header><strong>Intercambio</strong><button type="button" id="hoja-cerrar" aria-label="Cerrar">✕</button></header>',
      '<label>Doy<select id="cambio-doy"><option value="mineral_cobre">Cobre</option><option value="mineral_plata">Plata</option><option value="mineral_oro">Oro</option></select></label>',
      '<label>Recibo<select id="cambio-recibo"><option value="simoncoin">Simoncoin</option></select></label>',
      '<div id="cambio-pasos"><button type="button" id="cambio-menos" aria-label="Menos">−</button><b id="cambio-n">1</b><button type="button" id="cambio-mas" aria-label="Más">+</button><button type="button" id="cambio-max">Máximo</button></div>',
      '<p id="cambio-vista">Das 0. Recibes 0.</p>',
      '<button type="button" id="cambio-ok">Confirmar</button>',
    ].join('');
    document.body.append(bar, hoja);
    if (!document.getElementById('b-inventario-movil')) {
      const inv = document.createElement('button');
      inv.type = 'button';
      inv.id = 'b-inventario-movil';
      inv.textContent = 'Inventario';
      inv.setAttribute('aria-label', 'Abrir inventario');
      inv.onclick = () => {
        const panel = document.getElementById('w-inv');
        const boton = document.getElementById('b-inv');
        if (boton) boton.click();
        else if (panel) panel.hidden = !panel.hidden;
        if (window.LiveInk && LiveInk.paintInv) LiveInk.paintInv();
      };
      document.body.append(inv);
    }
    $('hoja-cerrar').onclick = cerrar;
    $('cambio-doy').onchange = pintarCambio;
    $('cambio-recibo').onchange = pintarCambio;
    $('cambio-menos').onclick = () => { cantidad = Math.max(1, cantidad - ( $('cambio-doy').value === 'simonplata' ? 100 : 1)); pintarCambio(); };
    $('cambio-mas').onclick = () => { cantidad += $('cambio-doy').value === 'simonplata' ? 100 : 1; pintarCambio(); };
    $('cambio-max').onclick = () => {
      const quoted = CambioSimple.quote($('cambio-doy').value, $('cambio-recibo').value, 1e15, tengo($('cambio-doy').value), fondo(), puesto());
      cantidad = Math.max(1, quoted.maximo || 1);
      pintarCambio();
    };
    $('cambio-ok').onclick = confirmar;
    pintarCambio();
  }
  const COLUMNA = ['b-acunar-pulgar', 'b-picar', 'b-inventario-movil', 'mine-route', 'mine-enter', 'viaje-mundo-abrir', 'ladera-ir', 'mine-exit-route', 'mina-mundo-jay'];
  const HUECO = 8;
  const INICIO = 72;
  function portraitMovil() {
    return estrecho() && matchMedia('(orientation: portrait)').matches;
  }
  function sePisan(a, b) {
    if (!a || !b) return false;
    return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
  }
  function puestosDe(alturas, inicio, hueco) {
    const out = [];
    let cursor = inicio == null ? INICIO : inicio;
    const gap = hueco == null ? HUECO : hueco;
    for (let i = 0; i < alturas.length; i++) {
      const alto = Number(alturas[i]) || 0;
      if (!(alto > 0)) { out.push(null); continue; }
      out.push({ desde: cursor, hasta: cursor + alto, alto: alto });
      cursor += alto + gap;
    }
    return out;
  }
  function rectsDe(puestos, ancho, vista, borde) {
    const right = vista.w - borde;
    return puestos.map((p) => {
      if (!p) return null;
      return { left: right - ancho, right: right, top: vista.h - p.hasta, bottom: vista.h - p.desde };
    });
  }
  function visible(el) {
    if (!el || el.hidden) return false;
    const estilo = getComputedStyle(el);
    return estilo.display !== 'none' && estilo.visibility !== 'hidden';
  }
  function limpiar(el) {
    if (!el || !el.classList.contains('columna-pulgar')) return;
    el.classList.remove('columna-pulgar');
    el.style.removeProperty('--columna-desde');
  }
  function apilar() {
    const els = COLUMNA.map((id) => $(id));
    if (!portraitMovil()) {
      els.forEach(limpiar);
      return [];
    }
    const vivos = els.map((el) => !!(el && visible(el)));
    els.forEach((el, i) => {
      if (!el) return;
      if (vivos[i]) el.classList.add('columna-pulgar');
      else limpiar(el);
    });
    const alturas = els.map((el, i) => vivos[i] ? Math.ceil(el.getBoundingClientRect().height) : 0);
    const puestos = puestosDe(alturas);
    puestos.forEach((p, i) => {
      if (!p || !els[i]) return;
      els[i].style.setProperty('--columna-desde', 'calc(' + p.desde + 'px + env(safe-area-inset-bottom))');
    });
    return puestos;
  }
  window.Pulgar = { pintarCambio: pintarCambio, cerrar: cerrar, apilar: apilar, puestosDe: puestosDe, rectsDe: rectsDe, sePisan: sePisan, COLUMNA: COLUMNA, HUECO: HUECO, INICIO: INICIO };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
  addEventListener('resize', () => { if (!$('pulgar')) mount(); apilar(); });
  setInterval(apilar, 400);
})();
