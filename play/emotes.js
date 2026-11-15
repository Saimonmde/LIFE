/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Rueda de gestos. Con la rueda abierta, las teclas 1–8 los lanzan. */
(() => {
  'use strict';
  const list = (window.Motion && Motion.EMOTES) || [];
  let open = false;
  const button = document.createElement('button');
  button.id = 'b-emote';
  button.type = 'button';
  button.textContent = 'Gestos';
  button.setAttribute('aria-expanded', 'false');
  button.setAttribute('aria-controls', 'emote-wheel');
  const wheel = document.createElement('div');
  wheel.id = 'emote-wheel';
  wheel.hidden = true;
  wheel.setAttribute('role', 'menu');
  wheel.setAttribute('aria-label', 'Gestos');
  list.forEach((emote, index) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.dataset.emote = String(index + 1);
    item.textContent = (index + 1) + ' ' + emote.name;
    item.onclick = () => play(index + 1);
    wheel.append(item);
  });
  document.body.append(button, wheel);

  function setOpen(next) {
    open = !!next;
    wheel.hidden = !open;
    button.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function play(n) {
    const emote = list[n - 1];
    const S = window.LiveInk && LiveInk.state;
    if (!emote || !S || !window.LiveInk.started) return;
    S.player.emote = emote.id;
    S.player.emoteUntil = performance.now() + (emote.id === 'sit' ? 4200 : 2600);
    const ws = S.net && S.net.ws;
    if (S.net && S.net.ok && ws && ws.readyState === 1) {
      ws.send(JSON.stringify({ t: 'emote', emote: emote.id }));
    }
    setOpen(false);
  }
  button.onclick = () => setOpen(!open);
  addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && open) { setOpen(false); e.preventDefault(); }
  });
  window.Emotes = { play, isOpen: () => open, setOpen, list };
})();
