/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Adopción, mundos, amigos, feedback y el poste. No toca el cajón ni el viaje. */
(() => {
  'use strict';
  const POSTE = { x: 108, y: 272, place: 'parque-envigado' };
  const $ = (id) => document.getElementById(id);
  let catalog = null;
  let queued = null;
  let social = { friends: [], in: [], out: [] };
  let role = 'player';
  let placeName = 'Valle de Aburrá';
  let selected = null;
  let board = { notes: [], polls: [] };
  let applyingHome = false;

  function skip() {
    const q = new URLSearchParams(location.search);
    return q.has('autotest') || q.has('sinlogin');
  }
  function world() {
    const n = Number(sessionStorage.getItem('lifeinc.mundo') || 1);
    return n >= 1 && n <= 5 ? n : 1;
  }
  function allowsConnect() {
    if (skip()) return true;
    const worldOk = !!sessionStorage.getItem('lifeinc.mundo');
    const petOk = !!localStorage.getItem('lifeinc.mascota.v1') || localStorage.getItem('lifeinc.mascota.skip') === '1';
    return worldOk && petOk;
  }
  function queueConnect(fn) {
    queued = fn;
    openGate();
  }
  function send(obj) {
    const net = window.LiveInk && LiveInk.state && LiveInk.state.net;
    if (!net || !net.ws || net.ws.readyState !== 1) return false;
    net.ws.send(JSON.stringify(obj));
    return true;
  }
  function state() { return window.LiveInk && LiveInk.state; }
  function petLocal() {
    try { return JSON.parse(localStorage.getItem('lifeinc.mascota.v1') || 'null'); }
    catch (e) { return null; }
  }
  function withColors(pet) {
    if (!pet) return null;
    const group = catalog && catalog.pets && catalog.pets[pet.species];
    const breed = group && group.find(item => item.id === pet.breed);
    return Object.assign({}, pet, { colors: breed ? breed.colors : pet.colors });
  }
  function setPet(pet) {
    const S = state();
    if (S) S.pet = withColors(pet);
  }

  function paintCount(presence) {
    if (!presence) return;
    const total = presence.total || 0;
    const mine = (presence.worlds && presence.worlds[String(world())]) || 0;
    const bar = $('amigos-barra');
    if (bar) bar.textContent = total + ' en línea · ' + mine + ' en Mundo ' + world();
    const gear = $('cajon-amigos');
    if (gear) gear.textContent = 'Amigos · ' + total;
    const head = $('amigos-conteo');
    if (head) head.textContent = total + ' en línea · ' + mine + ' en tu mundo';
  }

  function finishGate() {
    const door = $('vida-puerta');
    if (door) door.hidden = true;
    const fn = queued;
    queued = null;
    if (fn) fn();
  }

  function openGate() {
    const door = $('vida-puerta');
    if (!door) return;
    door.hidden = false;
    const hasWorld = !!sessionStorage.getItem('lifeinc.mundo');
    $('vida-paso-mundo').hidden = hasWorld;
    $('vida-paso-mascota').hidden = !hasWorld;
    if (!hasWorld) loadWorlds();
    else paintBreeds();
  }

  async function loadCatalog() {
    if (catalog) return catalog;
    try {
      const res = await fetch('/data/vida.json', { cache: 'no-store' });
      catalog = res.ok ? await res.json() : null;
    } catch (e) { catalog = null; }
    return catalog;
  }

  async function loadWorlds() {
    const box = $('vida-mundos');
    if (!box) return;
    box.textContent = 'Contando jugadores…';
    let data = null;
    try {
      const res = await fetch('/api/mundos', { cache: 'no-store' });
      data = res.ok ? await res.json() : null;
    } catch (e) { data = null; }
    const worlds = (data && data.worlds) || [1, 2, 3, 4, 5].map(id => ({ id, name: 'Mundo ' + id, players: 0 }));
    box.replaceChildren();
    for (const item of worlds) {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = (item.name || ('Mundo ' + item.id)) + ' · ' + (item.players || 0);
      b.onclick = () => {
        sessionStorage.setItem('lifeinc.mundo', String(item.id));
        const playing = state() && state().net && state().net.ok;
        if (playing) {
          send({ t: 'mundo', id: item.id });
          $('vida-puerta').hidden = true;
          return;
        }
        const petReady = !!localStorage.getItem('lifeinc.mascota.v1') || localStorage.getItem('lifeinc.mascota.skip') === '1';
        if (petReady) { finishGate(); return; }
        $('vida-paso-mundo').hidden = true;
        $('vida-paso-mascota').hidden = false;
        paintBreeds();
      };
      box.append(b);
    }
    const note = document.createElement('p');
    note.textContent = 'Los mundos 6 a 333 están reservados y todavía no abren. En el mismo mundo y el mismo lugar se ven. En otro mundo, no.';
    box.append(note);
  }

  function paintBreeds() {
    const box = $('vida-razas');
    if (!box) return;
    box.replaceChildren();
    const pets = (catalog && catalog.pets) || {};
    for (const species of ['dog', 'cat']) {
      for (const breed of pets[species] || []) {
        const card = document.createElement('article');
        card.className = 'mascota-carta';
        const canvas = document.createElement('canvas');
        canvas.className = 'mascota-preview';
        canvas.width = 128;
        canvas.height = 128;
        canvas.dataset.pet = JSON.stringify({ species, breed: breed.id, variant: 0, colors: breed.colors });
        const title = document.createElement('strong');
        title.textContent = (species === 'dog' ? 'Perro ' : 'Gato ') + breed.name;
        const tones = document.createElement('span');
        tones.className = 'mascota-tonos';
        (breed.colors || []).forEach((color) => {
          const dot = document.createElement('i');
          dot.className = 'vida-swatch';
          dot.style.background = color;
          tones.append(dot);
        });
        const name = document.createElement('input');
        name.maxLength = 16;
        name.placeholder = 'Su nombre';
        name.setAttribute('aria-label', 'Nombre de ' + breed.name);
        const adopt = document.createElement('button');
        adopt.type = 'button';
        adopt.textContent = 'Adoptar';
        adopt.onclick = () => {
          const pet = { species, breed: breed.id, variant: 0, name: name.value.trim() || breed.name, colors: breed.colors };
          localStorage.setItem('lifeinc.mascota.v1', JSON.stringify(pet));
          localStorage.removeItem('lifeinc.mascota.skip');
          setPet(pet);
          send({ t: 'adoptar', pet });
          finishGate();
        };
        card.append(canvas, title, tones, name, adopt);
        box.append(card);
      }
    }
    if (!box.childElementCount) {
      const p = document.createElement('p');
      p.textContent = 'No se pudo cargar el catálogo. Puedes seguir y adoptar después.';
      box.append(p);
    }
  }

  function mount() {
    if ($('amigos-barra')) return;
    const bar = document.createElement('button');
    bar.id = 'amigos-barra';
    bar.type = 'button';
    bar.textContent = '0 en línea · 0 en tu mundo';
    bar.onclick = () => { $('amigos-panel').hidden = !$('amigos-panel').hidden; };
    const panel = document.createElement('section');
    panel.id = 'amigos-panel';
    panel.hidden = true;
    panel.setAttribute('aria-label', 'Amigos');
    panel.innerHTML = [
      '<header><strong id="amigos-conteo">0 en línea · 0 en tu mundo</strong><button type="button" id="amigos-cerrar">✕</button></header>',
      '<div class="fila"><input id="amigos-buscar" maxlength="16" placeholder="Buscar nick" aria-label="Buscar nick"><button type="button" id="amigos-ir">Buscar</button></div>',
      '<p id="amigos-resultado" role="status"></p>',
      '<div id="amigos-lista"></div>',
      '<div id="amigo-chat" hidden><p id="amigo-con"></p><div id="amigo-log"></div><form id="amigo-form" class="fila"><input id="amigo-texto" maxlength="160" aria-label="Mensaje privado"><button type="submit">Enviar</button></form></div>',
      '<h3 id="lugar-titulo">Lugar</h3><div id="lugar-log"></div><form id="lugar-form" class="fila"><input id="lugar-texto" maxlength="160" aria-label="Mensaje del lugar"><button type="submit">Enviar</button></form>',
      '<p class="fila"><button type="button" id="b-mandar-feedback">Mandar feedback</button><button type="button" id="b-cambiar-nick">Cambiar nick</button></p>',
      '<p class="fila"><button type="button" id="b-cambiar-mundo">Cambiar mundo</button><button type="button" id="b-adoptar-luego">Adoptar mascota</button></p>',
    ].join('');
    const door = document.createElement('section');
    door.id = 'vida-puerta';
    door.hidden = true;
    door.innerHTML = [
      '<header><strong>Antes de entrar</strong></header>',
      '<div id="vida-paso-mundo"><h2>Elige un mundo</h2><div id="vida-mundos"></div></div>',
      '<div id="vida-paso-mascota" hidden><h2>Adopta un cachorro o un gatito</h2><p>Elige uno. Escribe su nombre. Se queda en tu casa.</p><div id="vida-razas"></div><p><button type="button" id="vida-sin-mascota">Ahora no</button> <button type="button" id="vida-feedback-puerta">Mandar feedback</button></p></div>',
    ].join('');
    const feedback = document.createElement('section');
    feedback.id = 'vida-feedback';
    feedback.hidden = true;
    feedback.innerHTML = '<header><strong>Mandar feedback</strong><button type="button" id="feedback-cerrar">✕</button></header><p>Simon lo lee en el panel de administración. No es un chat público.</p><textarea id="feedback-texto" maxlength="400" placeholder="Qué te gustaría ver en el juego"></textarea><p class="fila"><button type="button" id="feedback-enviar">Enviar</button></p><p id="feedback-estado" role="status"></p>';
    const poste = document.createElement('section');
    poste.id = 'vida-poste';
    poste.hidden = true;
    poste.innerHTML = '<header><strong>Poste del Parque de Envigado</strong><button type="button" id="poste-cerrar">✕</button></header><div id="poste-lista"></div><textarea id="poste-texto" maxlength="240" placeholder="Una nota para el juego"></textarea><p class="fila"><button type="button" id="poste-enviar">Dejar nota</button></p><form id="poste-encuesta"><input id="poste-pregunta" maxlength="80" placeholder="Pregunta de la encuesta"><input id="poste-o1" maxlength="24" placeholder="Opción 1"><input id="poste-o2" maxlength="24" placeholder="Opción 2"><button type="submit">Publicar encuesta</button></form><p id="poste-estado" role="status"></p>';
    const nick = document.createElement('section');
    nick.id = 'vida-nick';
    nick.hidden = true;
    nick.innerHTML = '<header><strong>Cambiar nick</strong><button type="button" id="nick-cerrar">✕</button></header><p>Es una acción de pago. Todavía no hay cobro: el nombre no cambia.</p><input id="nick-nuevo" maxlength="16" placeholder="Nick nuevo"><p class="fila"><button type="button" id="nick-pedir">Apartar cambio</button></p><p id="nick-estado" role="status"></p>';
    document.body.append(bar, panel, door, feedback, poste, nick);
    $('amigos-cerrar').onclick = () => { panel.hidden = true; };
    $('amigos-ir').onclick = search;
    $('amigos-buscar').addEventListener('keydown', (e) => { if (e.key === 'Enter') search(); });
    $('amigo-form').onsubmit = (e) => { e.preventDefault(); whisper(); };
    $('lugar-form').onsubmit = (e) => { e.preventDefault(); sayPlace(); };
    $('b-mandar-feedback').onclick = () => { feedback.hidden = false; };
    $('vida-feedback-puerta').onclick = () => { feedback.hidden = false; };
    $('feedback-cerrar').onclick = () => { feedback.hidden = true; };
    $('feedback-enviar').onclick = sendFeedback;
    $('b-cambiar-nick').onclick = () => { nick.hidden = false; };
    $('nick-cerrar').onclick = () => { nick.hidden = true; };
    $('nick-pedir').onclick = () => send({ t: 'nick_cambio', name: $('nick-nuevo').value });
    $('b-cambiar-mundo').onclick = () => { sessionStorage.removeItem('lifeinc.mundo'); panel.hidden = true; openGate(); };
    $('b-adoptar-luego').onclick = () => { panel.hidden = true; $('vida-paso-mundo').hidden = true; $('vida-paso-mascota').hidden = false; door.hidden = false; paintBreeds(); };
    $('vida-sin-mascota').onclick = () => { localStorage.setItem('lifeinc.mascota.skip', '1'); finishGate(); };
    $('poste-cerrar').onclick = () => { poste.hidden = true; };
    $('poste-enviar').onclick = () => send({ t: 'poste_nota', text: $('poste-texto').value });
    $('poste-encuesta').onsubmit = (e) => {
      e.preventDefault();
      send({ t: 'poste_encuesta', question: $('poste-pregunta').value, options: [$('poste-o1').value, $('poste-o2').value] });
    };
    mountGear();
    new MutationObserver(mountGear).observe(document.body, { childList: true, subtree: true });
  }

  function mountGear() {
    const menu = $('hud-gear-menu');
    if (!menu || $('cajon-amigos')) return;
    const friends = document.createElement('button');
    friends.type = 'button';
    friends.id = 'cajon-amigos';
    friends.textContent = 'Amigos';
    friends.onclick = () => { $('amigos-panel').hidden = false; menu.hidden = true; };
    const feedback = document.createElement('button');
    feedback.type = 'button';
    feedback.id = 'cajon-feedback';
    feedback.textContent = 'Mandar feedback';
    feedback.onclick = () => { $('vida-feedback').hidden = false; menu.hidden = true; };
    menu.append(friends, feedback);
  }

  function line(log, m) {
    const row = document.createElement('p');
    row.textContent = (m.ts ? m.ts + ' ' : '') + (m.from || '') + ': ' + (m.text || '');
    log.append(row);
    log.scrollTop = log.scrollHeight;
  }

  function search() {
    send({ t: 'amigo_buscar', nick: $('amigos-buscar').value });
  }
  function whisper() {
    if (!selected) return;
    const input = $('amigo-texto');
    send({ t: 'chat', channel: 'privado', to: selected.nick, text: input.value });
    input.value = '';
  }
  function sayPlace() {
    const input = $('lugar-texto');
    send({ t: 'chat', channel: 'lugar', text: input.value });
    input.value = '';
  }
  function sendFeedback() {
    const text = $('feedback-texto').value;
    const nick = (window.nombrePropio && nombrePropio()) || 'Viajero';
    if (!send({ t: 'feedback', text })) {
      fetch('/api/vida/feedback', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nick, text, world: world(), place: placeName }),
      }).then(r => r.json()).then(showFeedback).catch(() => { $('feedback-estado').textContent = 'No se pudo enviar.'; });
      return;
    }
  }
  function showFeedback(result) {
    $('feedback-estado').textContent = result && result.ok ? 'Enviado. Simon puede leerlo en el panel.' : ((result && result.error) || 'No se pudo enviar.');
    if (result && result.ok) $('feedback-texto').value = '';
  }

  function paintFriends() {
    const list = $('amigos-lista');
    if (!list) return;
    list.replaceChildren();
    const add = (title, rows, action) => {
      for (const row of rows || []) {
        const b = document.createElement('button');
        b.type = 'button';
        b.textContent = title + ' ' + row.nick + (row.online ? ' · en línea' : '');
        b.onclick = () => action(row);
        list.append(b);
      }
    };
    add('Aceptar', social.in, (row) => send({ t: 'amigo_aceptar', key: row.key }));
    add('Chat', social.friends, (row) => {
      selected = row;
      $('amigo-chat').hidden = false;
      $('amigo-con').textContent = 'Con ' + row.nick;
      $('amigo-log').replaceChildren();
      send({ t: 'amigo_hilo', key: row.key });
    });
    add('Pedido', social.out, () => {});
  }

  function paintBoard() {
    const list = $('poste-lista');
    if (!list) return;
    list.replaceChildren();
    for (const note of board.notes || []) {
      const row = document.createElement('article');
      row.className = 'vida-nota';
      const who = document.createElement('p');
      who.textContent = note.nick + ': ' + note.text;
      row.append(who);
      if (note.answer) {
        const answer = document.createElement('p');
        answer.innerHTML = '<b>Simon:</b> ';
        answer.append(document.createTextNode(note.answer));
        row.append(answer);
      }
      if (role === 'simon') modButtons(row, 'note', note.id);
      list.append(row);
    }
    for (const poll of board.polls || []) {
      const row = document.createElement('article');
      row.className = 'vida-nota';
      const q = document.createElement('p');
      q.textContent = poll.question + (poll.closed ? ' · cerrada' : '');
      row.append(q);
      for (const option of poll.options || []) {
        const b = document.createElement('button');
        b.type = 'button';
        b.textContent = option.text + ' · ' + option.votes;
        b.disabled = !!poll.closed;
        b.onclick = () => send({ t: 'poste_votar', id: poll.id, option: option.id });
        row.append(b);
      }
      if (poll.answer) {
        const answer = document.createElement('p');
        answer.textContent = 'Simon: ' + poll.answer;
        row.append(answer);
      }
      if (role === 'simon') modButtons(row, 'poll', poll.id);
      list.append(row);
    }
  }
  function modButtons(row, kind, id) {
    const reply = document.createElement('button');
    reply.type = 'button';
    reply.textContent = 'Responder';
    reply.onclick = () => {
      const text = window.prompt('Respuesta de Simon');
      if (text) send({ t: 'poste_moderar', kind, id, action: 'answer', text });
    };
    const hide = document.createElement('button');
    hide.type = 'button';
    hide.textContent = 'Ocultar';
    hide.onclick = () => send({ t: 'poste_moderar', kind, id, action: 'hide' });
    row.append(reply, hide);
    if (kind === 'poll') {
      const close = document.createElement('button');
      close.type = 'button';
      close.textContent = 'Cerrar';
      close.onclick = () => send({ t: 'poste_moderar', kind, id, action: 'close' });
      row.append(close);
    }
  }

  function applyHome(layout) {
    if (!layout || !window.Casa || !Casa.apply) return;
    applyingHome = true;
    try { Casa.apply(layout); }
    finally { applyingHome = false; }
  }

  function onWelcome(m) {
    role = m.role || 'player';
    if (m.placeName) placeName = m.placeName;
    if (m.presence) paintCount(m.presence);
    if (m.social) { social = m.social; paintFriends(); }
    if (m.pet) {
      localStorage.setItem('lifeinc.mascota.v1', JSON.stringify(m.pet));
      setPet(m.pet);
    } else if (petLocal()) {
      setPet(petLocal());
      send({ t: 'adoptar', pet: petLocal() });
    }
    if (m.home) applyHome(m.home);
    else if (window.Casa && Casa.layout) send({ t: 'hogar', layout: Casa.layout });
    const title = $('lugar-titulo');
    if (title) title.textContent = 'Chat de ' + placeName;
  }

  function onNet(m) {
    if (!m || typeof m !== 'object') return false;
    if (m.t === 'welcome') { onWelcome(m); return false; }
    if (m.t === 'presence') { paintCount(m); return true; }
    if (m.t === 'pet' && m.pet) {
      if (!m.id || (state() && m.id === state().net.id)) setPet(m.pet);
      else if (state() && state().others.get(m.id)) state().others.get(m.id).pet = withColors(m.pet);
      return true;
    }
    if (m.t === 'hogar' && m.layout) { applyHome(m.layout); return true; }
    if (m.t === 'social' && m.social) { social = m.social; paintFriends(); return true; }
    if (m.t === 'amigo' && m.found) {
      $('amigos-resultado').textContent = m.found.nick + (m.found.online ? ' está en línea.' : ' tiene cuenta.');
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = 'Agregar';
      b.onclick = () => send({ t: 'amigo_pedir', key: m.found.key });
      $('amigos-resultado').append(b);
      return true;
    }
    if (m.t === 'amigo' && m.error) { $('amigos-resultado').textContent = m.error; return true; }
    if (m.t === 'chat' && m.channel === 'lugar') { line($('lugar-log'), m); return true; }
    if (m.t === 'chat' && m.channel === 'privado') {
      if (selected && (m.fromKey === selected.key || m.toKey === selected.key)) line($('amigo-log'), m);
      return true;
    }
    if (m.t === 'hilo' && Array.isArray(m.messages)) {
      const log = $('amigo-log');
      log.replaceChildren();
      for (const row of m.messages) line(log, row);
      return true;
    }
    if (m.t === 'nick_quote') {
      $('nick-estado').textContent = m.note || m.error || (m.payment_required ? 'Hace falta el pago. El nick no cambió.' : 'No se cambió.');
      return true;
    }
    if (m.t === 'feedback_result') { showFeedback(m); return true; }
    if (m.t === 'poste') {
      board = { notes: m.notes || [], polls: m.polls || [] };
      if (m.placeName) placeName = m.placeName;
      paintBoard();
      $('poste-estado').textContent = m.error || '';
      return true;
    }
    if (m.t === 'mundo' && m.presence) { paintCount(m.presence); return true; }
    if (m.t === 'vida_error') { return true; }
    return false;
  }

  function onLayout() {
    if (applyingHome || !window.Casa) return;
    send({ t: 'hogar', layout: Casa.layout });
  }

  function openPoste() {
    const S = state();
    if (!S || !S.player) return;
    const far = Math.max(Math.abs(S.player.fx - POSTE.x), Math.abs(S.player.fy - POSTE.y)) > 3;
    if (far && window.LiveInk.goTo) { LiveInk.goTo(POSTE.x, POSTE.y); return; }
    $('vida-poste').hidden = false;
    send({ t: 'poste_ver' });
  }

  window.Vida = { allowsConnect, queueConnect, world, onNet, onLayout, openPoste, petPayload: petLocal, decorate: withColors };
  loadCatalog();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
