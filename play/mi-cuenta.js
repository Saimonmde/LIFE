/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Panel Mi cuenta: el progreso vive en la cuenta, no sólo en este aparato. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);

  function vuelta() {
    const q = new URLSearchParams(location.search);
    if (location.pathname.indexOf('/movil') === 0 || q.get('movil') === '1') return '/play/?movil=1';
    return '/play/';
  }
  function texto(n) {
    const v = Math.floor(Number(n) || 0);
    return String(v);
  }
  function lista(obj, nombres) {
    const keys = Object.keys(obj || {});
    if (!keys.length) return 'Nada guardado todavía.';
    return keys.map((key) => (nombres[key] || key) + ': ' + obj[key]).join(' · ');
  }
  function inventario(rows) {
    if (!rows || !rows.length) return 'La mochila guardada está vacía.';
    return rows.map((row) => row.item + ' × ' + row.qty).join(' · ');
  }

  const panel = document.createElement('section');
  panel.id = 'mi-cuenta';
  panel.hidden = true;
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-labelledby', 'mi-cuenta-titulo');
  panel.innerHTML = [
    '<div class="mi-cuenta-panel">',
    '<header><h2 id="mi-cuenta-titulo">Mi cuenta</h2><button type="button" id="mi-cuenta-cerrar">✕ Cerrar</button></header>',
    '<p id="mi-cuenta-nick"></p>',
    '<p id="mi-cuenta-google"></p>',
    '<p id="mi-cuenta-lugar"></p>',
    '<p id="mi-cuenta-hora"></p>',
    '<p id="mi-cuenta-inv"></p>',
    '<p id="mi-cuenta-monedas"></p>',
    '<p id="mi-cuenta-finca"></p>',
    '<p id="mi-cuenta-favorito"></p>',
    '<p class="mi-cuenta-nota">Cambiar el nickname cuesta 5 Simoncoin, que se pagan al Banco Central. Simon está reservado.</p>',
    '<button type="button" id="mi-cuenta-guardar">Guardar ahora</button>',
    '<form id="mi-cuenta-clave">',
    '<label>Contraseña actual<input id="mi-cuenta-actual" type="password" autocomplete="current-password"></label>',
    '<label>Contraseña nueva<input id="mi-cuenta-nueva" type="password" autocomplete="new-password"></label>',
    '<button type="submit">Cambiar contraseña</button>',
    '</form>',
    '<button type="button" id="mi-cuenta-google-btn">Vincular con Google</button>',
    '<button type="button" id="mi-cuenta-lugar-btn">Cambiar lugar favorito</button>',
    '<button type="button" id="mi-cuenta-salir">Cerrar sesión en este dispositivo</button>',
    '<button type="button" id="mi-cuenta-salir-todos">Cerrar sesión en todos</button>',
    '<p id="mi-cuenta-estado" role="status"></p>',
    '</div>',
  ].join('');
  document.body.append(panel);

  function estado(text) {
    const el = $('mi-cuenta-estado');
    if (el) el.textContent = text || '';
  }
  function pintar(data) {
    $('mi-cuenta-nick').textContent = 'Nickname: ' + (data.nick || 'Viajero');
    $('mi-cuenta-google').textContent = 'Google: ' + (data.google ? 'sí' : 'no');
    $('mi-cuenta-lugar').textContent = 'Último lugar: ' + (data.place || 'Sin lugar guardado');
    $('mi-cuenta-hora').textContent = data.saved || 'Todavía no hay un guardado en la cuenta.';
    $('mi-cuenta-inv').textContent = 'Inventario: ' + inventario(data.inventory);
    const coins = data.coins || {};
    $('mi-cuenta-monedas').textContent = 'Simoncoin: ' + texto(coins.simoncoinSmh) + ' SMH · Simonplata: ' + texto(coins.simonplataSph) + ' SPH · Simonchis: ' + texto(coins.simonchis);
    $('mi-cuenta-finca').textContent = 'Finquita: ' + lista(data.crops, { cafe: 'Café', cacao: 'Cacao' }) + ' · Animales: ' + lista(data.animals, { gallo: 'Gallos', gallina: 'Gallinas' });
    $('mi-cuenta-favorito').textContent = 'Favorito: ' + (data.favoritePlace || 'sin lugar') + (data.favoriteWorld ? ' · Mundo ' + data.favoriteWorld : '');
    const google = $('mi-cuenta-google-btn');
    if (google) google.hidden = !!data.google;
  }
  async function abrir() {
    panel.hidden = false;
    estado('');
    const menu = $('hud-gear-menu');
    if (menu) menu.hidden = true;
    try {
      const response = await fetch('/auth/cuenta', { credentials: 'same-origin', cache: 'no-store' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Entra con tu cuenta para verla.');
      pintar(data);
    } catch (error) {
      estado(error.message);
    }
    $('mi-cuenta-cerrar').focus();
  }
  function cerrar() { panel.hidden = true; }
  async function salir(url) {
    if (window.Partida) { try { await Partida.push(); } catch (e) {} }
    const response = await fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    if (!response.ok) throw new Error('No se pudo cerrar la sesión.');
    location.replace(vuelta());
  }
  function montar() {
    const menu = $('hud-gear-menu');
    if (!menu || $('cajon-cuenta')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.id = 'cajon-cuenta';
    button.textContent = 'Mi cuenta';
    button.onclick = () => abrir();
    menu.append(button);
  }

  $('mi-cuenta-cerrar').onclick = cerrar;
  panel.addEventListener('click', (event) => { if (event.target === panel) cerrar(); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !panel.hidden) { cerrar(); event.preventDefault(); }
  });
  $('mi-cuenta-guardar').onclick = async () => {
    estado('Guardando…');
    if (window.Partida) await Partida.push();
    await abrir();
    estado('Guardado en la cuenta.');
  };
  $('mi-cuenta-clave').onsubmit = async (event) => {
    event.preventDefault();
    const current = $('mi-cuenta-actual');
    const next = $('mi-cuenta-nueva');
    estado('');
    try {
      const response = await fetch('/auth/clave', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current: current.value, password: next.value }),
      });
      const data = await response.json();
      current.value = '';
      next.value = '';
      if (!response.ok) throw new Error(data.error || 'No se cambió la contraseña.');
      estado('Contraseña cambiada.');
    } catch (error) {
      current.value = '';
      next.value = '';
      estado(error.message);
    }
  };
  $('mi-cuenta-google-btn').onclick = () => {
    location.href = '/auth/google?vuelta=' + encodeURIComponent(vuelta());
  };
  $('mi-cuenta-lugar-btn').onclick = () => {
    cerrar();
    if (window.Hogar) Hogar.openPicker((id) => {
      if (window.LiveInk && LiveInk.elegirLugar) LiveInk.elegirLugar(id, true);
    }, true);
  };
  $('mi-cuenta-salir').onclick = () => salir('/auth/salir').catch((error) => estado(error.message));
  $('mi-cuenta-salir-todos').onclick = () => salir('/auth/salir-todos').catch((error) => estado(error.message));
  montar();
  new MutationObserver(montar).observe(document.body, { childList: true, subtree: true });
  window.MiCuenta = { abrir, cerrar };
})();
