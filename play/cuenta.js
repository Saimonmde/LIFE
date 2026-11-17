/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Eliminar mi cuenta y cerrar sesión, dentro del menú ⚙. */
(() => {
  'use strict';
  const perfil = document.getElementById('hud-perfil');
  if (!perfil) return;

  let usuario = null;

  const aviso = document.createElement('p');
  aviso.id = 'cuenta-aviso';
  aviso.hidden = true;
  aviso.setAttribute('role', 'status');

  const fondo = document.createElement('div');
  fondo.id = 'eliminar-fondo';
  fondo.hidden = true;
  const dialog = document.createElement('section');
  dialog.id = 'eliminar-dialogo';
  dialog.className = 'ventana';
  dialog.hidden = true;
  dialog.setAttribute('role', 'dialog');
  dialog.setAttribute('aria-modal', 'true');
  dialog.setAttribute('aria-labelledby', 'eliminar-titulo');
  dialog.innerHTML = [
    '<header id="eliminar-titulo">Eliminar mi cuenta <button type="button" class="x" id="eliminar-x" aria-label="Cerrar">✕</button></header>',
    '<div class="cuerpo">',
    '<p>Se borra tu correo, el vínculo con Google o Facebook, tu nickname, tus sesiones y los datos de tu perfil y de tu casa. El libro conserva el movimiento, pero con un identificador anónimo en lugar de tu nombre.</p>',
    '<p>Tu Simoncoin, en la billetera y en el depósito, vuelve al fondo. Esta acción no se puede deshacer.</p>',
    '<label for="eliminar-confirma">Escribe tu nickname o la palabra ELIMINAR<input id="eliminar-confirma" autocomplete="off" spellcheck="false"></label>',
    '<p id="eliminar-error" role="status"></p>',
    '<div id="eliminar-botones"><button type="button" id="eliminar-cancelar">Cancelar</button><button type="button" id="eliminar-confirmar" disabled>Eliminar mi cuenta</button></div>',
    '</div>',
  ].join('');
  document.body.append(fondo, dialog);

  const input = dialog.querySelector('#eliminar-confirma');
  const error = dialog.querySelector('#eliminar-error');
  const confirmar = dialog.querySelector('#eliminar-confirmar');
  const cancelar = dialog.querySelector('#eliminar-cancelar');

  function clave(text) {
    return String(text || '').normalize('NFKC').trim().replace(/\s+/g, ' ').toLocaleLowerCase('es');
  }
  function vuelta() {
    const q = new URLSearchParams(location.search);
    if (location.pathname.indexOf('/movil') === 0 || q.get('movil') === '1') return '/play/?movil=1';
    return '/play/';
  }
  function coincide() {
    const text = input.value.trim();
    if (text === 'ELIMINAR') return true;
    const key = clave(text);
    if (!key || !usuario) return false;
    return key === clave(usuario.name) || key === clave(usuario.wallet_name);
  }
  function boton(id, text) {
    let el = document.getElementById(id);
    if (el) return el;
    el = document.createElement('button');
    el.type = 'button';
    el.id = id;
    el.textContent = text;
    el.hidden = true;
    return el;
  }
  function montar() {
    const menu = document.getElementById('hud-gear-menu');
    if (!menu) return false;
    const salir = boton('b-cerrar-sesion', 'Cerrar sesión');
    const borrar = boton('b-eliminar-cuenta', 'Eliminar mi cuenta');
    if (salir.parentElement !== menu) menu.append(salir, borrar, aviso);
    if (!salir.dataset.listo) {
      salir.dataset.listo = '1';
      salir.onclick = pedirSalida;
      borrar.onclick = abrir;
    }
    return true;
  }
  function sync() {
    montar();
    const on = !!(usuario && document.body.classList.contains('in-game'));
    for (const id of ['b-cerrar-sesion', 'b-eliminar-cuenta']) {
      const el = document.getElementById(id);
      if (el) el.hidden = !on;
    }
    if (!on) aviso.hidden = true;
  }
  function abrir() {
    input.value = '';
    error.textContent = '';
    confirmar.disabled = true;
    fondo.hidden = false;
    dialog.hidden = false;
    cancelar.focus();
  }
  function cerrar() {
    fondo.hidden = true;
    dialog.hidden = true;
    error.textContent = '';
  }
  function limpiarLocal() {
    const nick = String((usuario && (usuario.wallet_name || usuario.name)) || '');
    const casa = 'lifeinc.casa.v1:' + encodeURIComponent(nick.trim().toLowerCase().slice(0, 16) || 'viajero');
    const token = 'lifeinc.sai.token.' + nick;
    try {
      localStorage.removeItem('lifeinc.perfil');
      localStorage.removeItem('lifeinc.eljardin.v3');
      localStorage.removeItem(casa);
      localStorage.removeItem(token);
    } catch (e) {}
  }

  const salida = document.createElement('section');
  salida.id = 'cerrar-sesion';
  salida.hidden = true;
  salida.setAttribute('role', 'dialog');
  salida.setAttribute('aria-label', 'Cerrar sesión');
  salida.innerHTML = '<h2>¿Cerrar sesión?</h2><p>Vuelves a la pantalla de entrada. Tu casa y tu mascota siguen en la cuenta.</p><p class="fila"><button type="button" id="cerrar-sesion-no">No</button><button type="button" id="cerrar-sesion-si">Sí, salir</button></p>';
  document.body.append(salida);
  const casaBtn = document.createElement('button');
  casaBtn.type = 'button';
  casaBtn.id = 'b-cerrar-casa';
  casaBtn.textContent = 'Cerrar sesión';
  casaBtn.onclick = pedirSalida;
  document.body.append(casaBtn);
  salida.querySelector('#cerrar-sesion-no').onclick = () => { salida.hidden = true; };
  salida.querySelector('#cerrar-sesion-si').onclick = () => { salida.hidden = true; cerrarSesion(); };
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !salida.hidden) salida.hidden = true;
  });
  function pedirSalida() {
    salida.hidden = false;
    salida.querySelector('#cerrar-sesion-no').focus();
  }

  async function cerrarSesion() {
    const button = document.getElementById('b-cerrar-sesion');
    if (!button || button.disabled) return;
    button.disabled = true;
    aviso.hidden = true;
    try {
      const response = await fetch('/auth/salir', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: '{}',
      });
      if (!response.ok) throw new Error('no');
      location.replace(vuelta());
    } catch (e) {
      button.disabled = false;
      aviso.hidden = false;
      aviso.textContent = 'No se pudo cerrar la sesión.';
    }
  }
  cancelar.onclick = cerrar;
  dialog.querySelector('#eliminar-x').onclick = cerrar;
  fondo.onclick = cerrar;
  input.addEventListener('input', () => {
    confirmar.disabled = !coincide();
    error.textContent = '';
  });
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !confirmar.disabled) {
      event.preventDefault();
      confirmar.click();
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !dialog.hidden) cerrar();
  });
  confirmar.onclick = async () => {
    if (!coincide() || confirmar.disabled) return;
    confirmar.disabled = true;
    error.textContent = '';
    try {
      const response = await fetch('/auth/delete-account', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: input.value.trim() }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        error.textContent = data.error || 'No se pudo eliminar la cuenta.';
        confirmar.disabled = !coincide();
        return;
      }
      limpiarLocal();
      location.replace(vuelta());
    } catch (e) {
      error.textContent = 'No se pudo eliminar la cuenta. No se cambió nada.';
      confirmar.disabled = !coincide();
    }
  };

  async function sesion() {
    try {
      const response = await fetch('/auth/sesion', { cache: 'no-store', credentials: 'same-origin' });
      const data = response.ok ? await response.json() : null;
      usuario = data && data.user;
    } catch (e) {
      usuario = null;
    }
    sync();
  }

  new MutationObserver(sync).observe(document.body, { attributes: true, attributeFilter: ['class'] });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', sesion);
  else sesion();
  window.Cuenta = { pedirSalida };
})();
