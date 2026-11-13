/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* LIFE INC · modo móvil. Sólo se activa con /movil/ o /play/?movil=1; en escritorio no hace nada. */
(() => {
  const q = new URLSearchParams(location.search);
  if (q.get('movil') !== '1') return;
  const root = document.documentElement;
  root.classList.add('movil');
  const vp = document.querySelector('meta[name=viewport]');
  if (vp) vp.content = 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover';
  // Sin zoom de página (iOS ignora user-scalable) ni desplazamiento: los gestos son del juego.
  for (const t of ['gesturestart', 'gesturechange', 'gestureend']) document.addEventListener(t, e => e.preventDefault(), { passive: false });
  let lastTap = 0;
  document.addEventListener('touchend', e => { const n = Date.now(); if (n - lastTap < 300 && !e.target.closest('input,textarea')) e.preventDefault(); lastTap = n; }, { passive: false });
  document.addEventListener('touchmove', e => { if (e.touches.length > 1 || !e.target.closest('.ventana,#hud-chat,#chat-log,#ayuda,#memories,#camera-panel,#furnace-panel,#city-map,.panel')) e.preventDefault(); }, { passive: false });
  // Botón "Menú" que muestra/oculta las herramientas del mundo (Memorias, Cámara, Recorrer…).
  addEventListener('DOMContentLoaded', () => {
    const b = document.createElement('button');
    b.id = 'movil-menu'; b.className = 'hud'; b.type = 'button';
    b.textContent = '☰ Menú'; b.setAttribute('aria-expanded', 'false');
    b.onclick = () => { const on = root.classList.toggle('movil-menu-abierto'); b.setAttribute('aria-expanded', String(on)); b.textContent = on ? '✕ Menú' : '☰ Menú'; };
    document.body.append(b);
  });
})();
