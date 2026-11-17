/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Hace visible la Mina de La Ladera: botón, flecha y un aviso que se cierra. */
(() => {
  'use strict';
  const KEY = 'lifeinc.ladera.aviso';

  function remembered() {
    try { return localStorage.getItem(KEY) === '1'; } catch (e) { return false; }
  }
  function remember() {
    try { localStorage.setItem(KEY, '1'); } catch (e) {}
  }
  function ir() {
    if (window.LiveInk && LiveInk.askTravel) LiveInk.askTravel('mina_ladera');
  }

  const btn = document.createElement('button');
  btn.type = 'button';
  btn.id = 'ladera-ir';
  btn.hidden = true;
  btn.innerHTML = '<span class="ladera-nueva">Nueva</span><span>Ir a la Mina de La Ladera</span>';
  btn.addEventListener('click', ir);

  const guia = document.createElement('button');
  guia.type = 'button';
  guia.id = 'ladera-guia';
  guia.hidden = true;
  guia.innerHTML = '<span id="ladera-guia-flecha" aria-hidden="true">➤</span><span id="ladera-guia-texto">La Ladera</span>';
  guia.addEventListener('click', ir);

  const aviso = document.createElement('aside');
  aviso.id = 'ladera-aviso';
  aviso.hidden = true;
  aviso.setAttribute('role', 'status');
  aviso.innerHTML = '<strong>Nueva mina</strong><p>La Mina de La Ladera está junto al cafetal. El botón de arriba te lleva.</p><div id="ladera-aviso-acciones"><button type="button" id="ladera-aviso-ir">Ir ahora</button><button type="button" id="ladera-aviso-cerrar">Ahora no</button></div>';

  document.body.append(btn, guia, aviso);
  aviso.querySelector('#ladera-aviso-ir').addEventListener('click', () => { remember(); aviso.hidden = true; ir(); });
  aviso.querySelector('#ladera-aviso-cerrar').addEventListener('click', () => { remember(); aviso.hidden = true; });

  function tick() {
    const ink = window.LiveInk;
    const started = !!(ink && ink.started);
    const world = ink && ink.world;
    const map = (world && world.mapId) || 'city';
    const inGame = document.body.classList.contains('in-game');
    const show = started && inGame && map !== 'mina2';
    btn.hidden = !show;
    const door = world && world.mineLadera;
    const player = ink && ink.state && ink.state.player;
    let far = false;
    if (show && map === 'city' && door && player) {
      const dx = door.x - player.fx;
      const dy = door.y - player.fy;
      const dist = Math.hypot(dx, dy);
      far = dist >= 8;
      const flecha = document.getElementById('ladera-guia-flecha');
      const texto = document.getElementById('ladera-guia-texto');
      if (flecha) flecha.style.transform = 'rotate(' + (Math.atan2(dy, dx) * 180 / Math.PI) + 'deg)';
      if (texto) texto.textContent = 'La Ladera · ' + Math.max(0, Math.round(dist * 2)) + ' m';
    }
    guia.hidden = !far;
    if (show && map === 'city' && !remembered()) aviso.hidden = false;
    else if (!show || remembered()) aviso.hidden = true;
  }
  setInterval(tick, 400);
  window.LaderaAviso = { ir: ir, remembered: remembered, key: KEY };
})();
