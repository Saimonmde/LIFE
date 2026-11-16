/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Ficha de otra persona: intercambiar, seguir o agregar. No crea monedas. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  let current = null;

  const card = document.createElement('section');
  card.id = 'ficha';
  card.hidden = true;
  card.setAttribute('role', 'dialog');
  card.setAttribute('aria-labelledby', 'ficha-nombre');
  card.innerHTML = [
    '<div class="ficha-panel">',
    '<header><h2 id="ficha-nombre">Jugador</h2><button type="button" id="ficha-cerrar" aria-label="Cerrar">✕</button></header>',
    '<p id="ficha-lugar"></p>',
    '<div class="ficha-acciones">',
    '<button type="button" id="ficha-cambiar">Intercambiar</button>',
    '<button type="button" id="ficha-seguir">Seguir</button>',
    '<button type="button" id="ficha-agregar">Agregar</button>',
    '</div>',
    '<p id="ficha-nota" role="status"></p>',
    '</div>',
  ].join('');
  document.body.append(card);

  function note(text) {
    const el = $('ficha-nota');
    if (el) el.textContent = text || '';
  }
  function personOf(raw) {
    if (!raw) return null;
    const id = Number(raw.id);
    const live = window.__ELJARDIN && __ELJARDIN.others && __ELJARDIN.others.get(id);
    const row = live || raw;
    return {
      id: id,
      nick: (window.nombreAjeno ? nombreAjeno(row) : (row.nick || row.name || 'Viajero')),
      key: row.key || row.avatar_id && ('acct:' + String(row.avatar_id).replace(/^avatar_/, '')) || '',
      place: row.placeName || row.place || '',
      zone: row.zone || '',
      bot: !!row.bot,
    };
  }
  function close() {
    card.hidden = true;
    current = null;
  }
  function open(raw) {
    const person = personOf(raw);
    if (!person || !person.id || person.bot) return;
    current = person;
    $('ficha-nombre').textContent = person.nick;
    const where = person.zone === 'casa' ? 'En su casa' : (person.place ? person.place : 'En el valle');
    $('ficha-lugar').textContent = where;
    note('');
    card.hidden = false;
  }
  function send(obj) {
    const S = window.__ELJARDIN;
    const ws = S && S.net && S.net.ws;
    if (!ws || ws.readyState !== 1) throw Error('Entra al mundo para hacer eso.');
    ws.send(JSON.stringify(obj));
  }

  $('ficha-cerrar').onclick = close;
  card.addEventListener('click', (event) => { if (event.target === card) close(); });
  $('ficha-cambiar').onclick = () => {
    if (!current) return;
    if (!window.TradeUI) { note('El intercambio no está listo.'); return; }
    const id = current.id;
    close();
    TradeUI.openTrade(id);
  };
  $('ficha-seguir').onclick = () => {
    if (!current) return;
    if (!window.Seguir) { note('Seguir todavía no está listo.'); return; }
    Seguir.empezar(current);
    note('Siguiendo a ' + current.nick + '.');
  };
  $('ficha-agregar').onclick = () => {
    if (!current) return;
    if (!window.Amigos) { note('Agregar todavía no está listo.'); return; }
    Amigos.pedir(current);
    note('Pedido enviado a ' + current.nick + '.');
  };

  window.Ficha = { open, close, personOf };
})();
