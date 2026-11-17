/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* LIFE INC · modo móvil. El candado de gestos es de /movil/.
   La barra de acciones también entra en una ventana de 390×844, para que
   Gestos, Cafetal, Libro, Chat, Descansar y el banco no tapen los letreros. */
(() => {
  const q = new URLSearchParams(location.search);
  const root = document.documentElement;
  const estrecho = () => root.classList.contains('movil') || matchMedia('(max-width: 820px)').matches;
  if (q.get('movil') === '1') {
    root.classList.add('movil');
    const vp = document.querySelector('meta[name=viewport]');
    if (vp) vp.content = 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover';
    for (const t of ['gesturestart', 'gesturechange', 'gestureend']) document.addEventListener(t, e => e.preventDefault(), { passive: false });
    let lastTap = 0;
    document.addEventListener('touchend', e => { const n = Date.now(); if (n - lastTap < 300 && !e.target.closest('input,textarea')) e.preventDefault(); lastTap = n; }, { passive: false });
    document.addEventListener('touchmove', e => { if (e.touches.length > 1 || !e.target.closest('.ventana,#w-inv,#baul-mina,#mi-cuenta,#hud-accesos,#pulgar,#hud-chat,#chat-log,#ayuda,#memories,#camera-panel,#furnace-panel,#city-map,.panel,.hud-pieza,.hud-shell,#hud-gear-menu,#hud-edit-bar,#mando,#city-joystick')) e.preventDefault(); }, { passive: false });
  }
  const ORDEN = ['bank-dock', 'b-montar', 'touch-extra', 'b-emote', 'finca-open', 'libro-open', 'chat-toggle', 'b-bajar', 'b-cerrar-casa', 'b-salir-parque', 'b-editar-casa'];
  const casa = new Map();
  function barra() {
    let box = document.getElementById('mando');
    if (!estrecho()) {
      casa.forEach((parent, id) => {
        const el = document.getElementById(id);
        if (el && parent && parent.isConnected && box && el.parentElement === box) parent.append(el);
      });
      if (box) box.hidden = true;
      return;
    }
    if (!box) {
      box = document.createElement('div');
      box.id = 'mando';
      box.setAttribute('aria-label', 'Acciones');
      document.body.append(box);
    }
    box.hidden = false;
    ORDEN.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (!casa.has(id)) casa.set(id, el.parentElement);
      if (el.parentElement !== box) box.append(el);
    });
    const principal = document.getElementById('b-montar');
    document.querySelectorAll('button').forEach((b) => {
      if (b !== principal && /^\s*Montar\s*$/.test(b.textContent || '')) b.hidden = true;
    });
  }
  addEventListener('resize', barra);
  addEventListener('DOMContentLoaded', () => {
    if (q.get('movil') === '1' && !document.getElementById('movil-menu')) {
      const b = document.createElement('button');
      b.id = 'movil-menu'; b.className = 'hud'; b.type = 'button';
      b.textContent = '☰ Menú'; b.setAttribute('aria-expanded', 'false');
      b.onclick = () => { const on = root.classList.toggle('movil-menu-abierto'); b.setAttribute('aria-expanded', String(on)); b.textContent = on ? '✕ Menú' : '☰ Menú'; };
      document.body.append(b);
    }
    barra();
    new MutationObserver(barra).observe(document.body, { childList: true, subtree: true });
  });
})();
