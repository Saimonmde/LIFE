/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Ir al Mundo 1, 2, 3, 4 o 5. Pide confirmación y usa el cambio de mundo que ya existe. */
(() => {
  'use strict';
  let pending = 0;

  function rows() {
    const api = window.MineralesMundo;
    if (api && api.worlds) return api.worlds();
    return [1, 2, 3, 4, 5].map((id) => ({ id: id, names: [], rocks: [] }));
  }
  function send(id) {
    const net = window.LiveInk && LiveInk.state && LiveInk.state.net;
    try { sessionStorage.setItem('lifeinc.mundo', String(id)); } catch (e) {}
    if (!net || !net.ws || net.ws.readyState !== 1) return false;
    net.ws.send(JSON.stringify({ t: 'mundo', id: id }));
    return true;
  }
  function walk(id) {
    const row = rows().find((item) => item.id === id);
    const rock = row && row.rocks && row.rocks[0];
    const W = window.LiveInk && LiveInk.world;
    if (!rock || !W || (W.mapId || 'city') !== 'city' || !window.LiveInk.goTo) return;
    const node = window.LiveInk.state && LiveInk.state.nodes && LiveInk.state.nodes.get(rock.id);
    const feet = node && node.def && node.def.stand;
    if (feet) LiveInk.goTo(feet.x, feet.y);
    else LiveInk.goTo(rock.x, rock.y + 1);
  }
  function say(id) {
    const row = rows().find((item) => item.id === id);
    const names = row && row.names && row.names.length ? row.names.join(' y ') : 'sus minerales';
    const text = 'Mundo ' + id + '. Aquí se mina ' + names + '. El oro sigue en el río.';
    if (window.LiveInk && LiveInk.say) LiveInk.say(text, 'juego');
  }
  function go(id) {
    pending = 0;
    const box = document.getElementById('viaje-mundo');
    if (box) box.hidden = true;
    send(id);
    walk(id);
    say(id);
  }
  function paintList(list) {
    list.replaceChildren();
    rows().forEach((row) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = 'Ir al Mundo ' + row.id;
      const hint = document.createElement('small');
      hint.textContent = row.names.length ? ' · ' + row.names.join(' y ') : '';
      b.append(hint);
      b.onclick = () => ask(row.id);
      list.append(b);
    });
  }
  function ask(id) {
    pending = Number(id);
    const box = ensure();
    box.hidden = false;
    const list = document.getElementById('viaje-mundo-lista');
    const q = document.getElementById('viaje-mundo-pregunta');
    if (list) list.hidden = true;
    if (q) {
      q.hidden = false;
      const row = rows().find((item) => item.id === pending);
      const names = row && row.names.length ? row.names.join(' y ') : 'minerales nuevos';
      const lead = document.getElementById('viaje-mundo-texto');
      if (lead) lead.textContent = 'Mundo ' + pending + '. Vas a minar ' + names + '. El oro del río sigue igual, hasta 50 SMC al día.';
    }
  }
  function showList() {
    pending = 0;
    const box = ensure();
    box.hidden = false;
    const list = document.getElementById('viaje-mundo-lista');
    const q = document.getElementById('viaje-mundo-pregunta');
    if (q) q.hidden = true;
    if (list) { list.hidden = false; paintList(list); }
  }
  function ensure() {
    let box = document.getElementById('viaje-mundo');
    if (box) return box;
    const open = document.createElement('button');
    open.id = 'viaje-mundo-abrir';
    open.type = 'button';
    open.textContent = 'Ir a un mundo';
    open.onclick = () => showList();
    box = document.createElement('section');
    box.id = 'viaje-mundo';
    box.hidden = true;
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-label', 'Ir a un mundo');
    box.innerHTML = [
      '<header><strong>Mundos</strong><button type="button" id="viaje-mundo-cerrar" aria-label="Cerrar">✕</button></header>',
      '<div id="viaje-mundo-lista"></div>',
      '<div id="viaje-mundo-pregunta" hidden>',
      '<p id="viaje-mundo-texto"></p>',
      '<p>¿Seguro que deseas ir a este mundo?</p>',
      '<div class="fila"><button type="button" id="viaje-mundo-si">Sí</button><button type="button" id="viaje-mundo-no">No</button></div>',
      '</div>',
    ].join('');
    document.body.append(open, box);
    box.querySelector('#viaje-mundo-cerrar').onclick = () => { box.hidden = true; };
    box.querySelector('#viaje-mundo-no').onclick = () => showList();
    box.querySelector('#viaje-mundo-si').onclick = () => { if (pending) go(pending); };
    return box;
  }
  function boot() {
    ensure();
  }
  window.ViajeMundo = { ask: ask, open: showList, go: go };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
