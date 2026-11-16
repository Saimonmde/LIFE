/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Pedir amistad. El servidor guarda el pedido en la cuenta. */
(() => {
  'use strict';
  function send(obj) {
    const S = window.__ELJARDIN;
    const ws = S && S.net && S.net.ws;
    if (!ws || ws.readyState !== 1) return false;
    ws.send(JSON.stringify(obj));
    return true;
  }
  function pedir(person) {
    if (!person || !person.key || String(person.key).indexOf('acct:') !== 0) {
      return 'Esa persona no tiene cuenta. No se envió el pedido.';
    }
    if (!send({ t: 'amigo_pedir', key: person.key })) return 'Entra al mundo para agregar.';
    return 'Pedido enviado a ' + (person.nick || 'esa persona') + '.';
  }
  window.Amigos = { pedir };
})();
