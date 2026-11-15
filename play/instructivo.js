/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Instructivo visible. Las teclas son las del juego, no unas inventadas. */
(() => {
  'use strict';
  const html = [
    '<header><strong>Cómo se juega</strong><button type="button" id="instructivo-cerrar" aria-label="Cerrar">✕</button></header>',
    '<p class="inst-lead">Sale una vez al empezar. Puedes saltarlo. El botón <b>?</b> lo abre cuando quieras. También está en el engranaje.</p>',
    '<div class="inst-cols">',
    '<section class="inst-card" id="inst-web">',
    '<h2>En la computadora <span>/play/</span></h2>',
    '<p class="inst-aqui" hidden>Estás aquí.</p>',
    '<h3>Caminar</h3>',
    '<p><kbd>W</kbd> <kbd>A</kbd> <kbd>S</kbd> <kbd>D</kbd> o las flechas. Siguen la cámara: <kbd>↑</kbd> avanza hacia el fondo de la pantalla.</p>',
    '<p>Clic en el suelo: caminas hasta ese punto. El palito redondo de abajo a la izquierda también camina si lo arrastras.</p>',
    '<h3>Correr</h3>',
    '<p>Mantén <kbd>X</kbd> y una tecla de caminar. Vas el doble de rápido y gastas energía. Si la energía llega a cero, hay que recuperar un poco para volver a correr. A caballo no se corre con <kbd>X</kbd>.</p>',
    '<h3>Mirar</h3>',
    '<p>Arrastra con el mouse para girar la vista. <kbd>Shift</kbd> + <kbd>←</kbd> <kbd>→</kbd> gira. <kbd>Shift</kbd> + <kbd>↑</kbd> <kbd>↓</kbd> inclina. <kbd>Z</kbd> + <kbd>↑</kbd> acerca y <kbd>Z</kbd> + <kbd>↓</kbd> aleja. <kbd>+</kbd> y <kbd>−</kbd> también cambian el zoom.</p>',
    '<h3>Tocar cosas</h3>',
    '<p>Clic en una puerta, un árbol, una roca o una persona. Si está lejos, caminas hasta allí y la acción ocurre sola. Caminar hasta la puerta de tu casa sale al parque.</p>',
    '<h3>Chat y amigos</h3>',
    '<p>El botón <b>Chat</b>, o <kbd>Enter</kbd>, abre el chat. <kbd>Esc</kbd> lo cierra. Las pestañas son Global, Proximidad, Clan y Grupo. Global se oye en tu mundo. Proximidad, a unos 30 metros y en tu mundo.</p>',
    '<p>La barrita bajo el engranaje es Amigos. También está el botón <b>Amigos</b> dentro de <b>⚙</b>. Ahí buscas un nick, charlas en privado y ves el chat del lugar donde estás.</p>',
    '</section>',
    '<section class="inst-card" id="inst-movil">',
    '<h2>En el celular <span>/movil/</span></h2>',
    '<p class="inst-aqui" hidden>Estás aquí.</p>',
    '<h3>Caminar</h3>',
    '<p>Arrastra el joystick, el palito redondo de abajo a la izquierda. O toca el suelo: caminas hasta ahí.</p>',
    '<h3>Correr</h3>',
    '<p>En la pantalla táctil no hay un botón de correr. Se camina. Correr es con teclado: mantén <kbd>X</kbd> y una dirección.</p>',
    '<h3>Mirar</h3>',
    '<p>Arrastra un dedo para girar la vista. Pellizca para acercar o alejar.</p>',
    '<h3>Tocar cosas</h3>',
    '<p>Toca la puerta, el árbol, la roca o la persona. Si está lejos, el personaje va hasta allí. Tocar la puerta de tu casa sale al parque.</p>',
    '<h3>Chat y amigos</h3>',
    '<p>El botón <b>Chat</b> abre el chat. El botón <b>☰ Menú</b> muestra las herramientas del mundo.</p>',
    '<p>Amigos es la barrita bajo el engranaje, o <b>Amigos</b> dentro de <b>⚙</b>. Ahí está el chat privado y el chat del lugar.</p>',
    '</section>',
    '</div>',
    '<section class="inst-card inst-wide">',
    '<h2>Salir con calma</h2>',
    '<p><b>Descansar</b> guarda la partida, cierra la conexión y vuelve a la pantalla de entrada. El aviso dice que el progreso quedó guardado.</p>',
    '<p>Si entraste con una cuenta: <b>⚙</b> y <b>Cerrar sesión</b>. Eso cierra la sesión y recarga el juego. No borra la cuenta.</p>',
    '<p>Cerrar la pestaña también intenta guardar. Descansar es la salida segura.</p>',
    '</section>',
    '<section class="inst-card inst-wide">',
    '<h2>Empezar a explorar</h2>',
    '<ol>',
    '<li>Entras en tu casa.</li>',
    '<li>La puerta, o el botón <b>Salir al Parque</b>, te deja en el Parque de Envigado. El botón <b>Casa</b> te devuelve.</li>',
    '<li>El globo del minimapa abre el mapa del valle. Elige un municipio y confirma para viajar. Tocar el minimapa camina hasta ese punto, sin viajar.</li>',
    '<li>En <b>⚙</b>, <b>Viajar</b> y <b>Ir a caballo</b> te monta y te lleva a ese lugar por el camino.</li>',
    '<li>Al entrar elegiste un mundo, del 1 al 5. Para cambiarlo: <b>Amigos</b> y <b>Cambiar mundo</b>. Solo ves a quien está en tu mundo y en el mismo lugar.</li>',
    '</ol>',
    '<p>Montar: <kbd>M</kbd> o <kbd>E</kbd>, o el botón <b>Montar</b>. <b>Bajarse del caballo</b> aparece mientras vas montado. A caballo no se entra a la casa.</p>',
    '</section>',
    '<p class="inst-actions"><button type="button" id="instructivo-saltar">Entendido</button></p>',
  ].join('');

  function mount() {
    if (document.getElementById('instructivo')) return;
    const panel = document.createElement('section');
    panel.id = 'instructivo';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Cómo se juega');
    panel.innerHTML = html;
    document.body.append(panel);
    if (!document.getElementById('b-ayuda-izq')) {
      const help = document.createElement('button');
      help.type = 'button';
      help.id = 'b-ayuda-izq';
      help.textContent = '?';
      help.setAttribute('aria-label', 'Cómo se juega');
      help.title = 'Cómo se juega';
      document.body.append(help);
    }
    const web = document.documentElement.classList.contains('movil');
    const mark = panel.querySelector(web ? '#inst-movil .inst-aqui' : '#inst-web .inst-aqui');
    if (mark) mark.hidden = false;
    const menu = document.getElementById('hud-gear-menu');
    if (menu && !document.getElementById('cajon-instructivo')) {
      const button = document.createElement('button');
      button.type = 'button';
      button.id = 'cajon-instructivo';
      button.textContent = '? Cómo se juega';
      menu.append(button);
    }
    if (document.body.classList.contains('vista-instructivo')) {
      panel.hidden = false;
      document.querySelector('#inst-web .inst-aqui').hidden = false;
      document.querySelector('#inst-movil .inst-aqui').hidden = true;
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
  new MutationObserver(() => {
    const menu = document.getElementById('hud-gear-menu');
    if (menu && !document.getElementById('cajon-instructivo') && document.getElementById('instructivo')) {
      const button = document.createElement('button');
      button.type = 'button';
      button.id = 'cajon-instructivo';
      button.textContent = '? Cómo se juega';
      menu.append(button);
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
