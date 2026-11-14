/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Eliminar mi cuenta y cerrar sesión, en el perfil. */
(() => {
  'use strict';
  const perfil = document.getElementById('hud-perfil');
  if (!perfil) return;

  let usuario = null;

  const bar = document.createElement('div');
  bar.id = 'cuenta-barra';
  bar.hidden = true;
  bar.innerHTML = '<p id="cuenta-nombre"></p><p id="cuenta-correo"></p><div id="cuenta-acciones"><button type="button" id="b-cerrar-sesion">Cerrar sesión</button><button type="button" id="b-eliminar-cuenta">Eliminar mi cuenta</button></div>';
  perfil.appendChild(bar);

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
    '<p>Tu SMC, en la billetera y en el depósito, vuelve al fondo de cambio. Tu SMP se quema: no hay una reserva de Plata, y el total emitido no cambia. Esta acción no se puede deshacer.</p>',
    '<label for="eliminar-confirma">Escribe tu nickname o la palabra ELIMINAR<input id="eliminar-confirma" autocomplete="off" spellcheck="false"></label>',
    '<p id="eliminar-error" role="status"></p>',
    '<div id="eliminar-botones"><button type="button" id="eliminar-cancelar">Cancelar</button><button type="button" id="eliminar-confirmar" disabled>Eliminar mi cuenta</button></div>',
    '</div>',
  ].join('');
  document.body.append(fondo, dialog);

  const nombre = bar.querySelector('#cuenta-nombre');
  const correo = bar.querySelector('#cuenta-correo');
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
  function pintar() {
    if (!usuario) return;
    const nick = usuario.name || usuario.wallet_name || '';
    nombre.textContent = 'Nickname: ' + nick;
    correo.textContent = usuario.email ? 'Cuenta: ' + usuario.email : 'Cuenta iniciada';
  }
  function colocar() {
    if (bar.hidden) return;
    if (bar.parentElement !== document.body) document.body.appendChild(bar);
    bar.classList.add('cuenta-flotante');
    const rect = perfil.getBoundingClientRect();
    const margin = 8;
    const width = Math.min(280, window.innerWidth - margin * 2);
    const left = Math.max(margin, Math.min(rect.left, window.innerWidth - margin - width));
    let top = rect.bottom + 8;
    const alto = bar.offsetHeight || 168;
    if (top + alto > window.innerHeight - margin) top = Math.max(margin, window.innerHeight - margin - alto);
    bar.style.left = left + 'px';
    bar.style.top = top + 'px';
    bar.style.width = width + 'px';
  }
  function sync() {
    const on = !!(usuario && document.body.classList.contains('in-game'));
    bar.hidden = !on;
    if (on) {
      pintar();
      colocar();
    }
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

  bar.querySelector('#b-cerrar-sesion').onclick = async () => {
    const button = bar.querySelector('#b-cerrar-sesion');
    button.disabled = true;
    try {
      const response = await fetch('/auth/salir', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: '{}',
      });
      if (!response.ok) throw new Error('no');
      location.replace(vuelta());
    } catch (e) {
      button.disabled = false;
      correo.textContent = 'No se pudo cerrar la sesión.';
    }
  };
  bar.querySelector('#b-eliminar-cuenta').onclick = abrir;
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
  addEventListener('resize', colocar);
  setInterval(colocar, 500);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', sesion);
  else sesion();
})();
