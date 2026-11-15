/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Instructivo visible. Las teclas son las del juego, no unas inventadas. */
(() => {
  'use strict';
  const html = [
    '<header><strong>Cómo se juega</strong><button type="button" id="instructivo-cerrar" aria-label="Cerrar">✕</button></header>',
    '<p class="inst-lead">Este texto sale la primera vez. Lo podés saltar. Si lo necesitás después, tocá <b>?</b> o buscalo en la rueda <b>⚙</b>.</p>',
    '<section class="inst-card inst-wide" id="inst-web">',
    '<h2>En la computadora</h2>',
    '<p class="inst-aqui" hidden>Estás aquí.</p>',
    '<p>Para caminar en <span>/play/</span>, usá <kbd>W</kbd> <kbd>A</kbd> <kbd>S</kbd> <kbd>D</kbd> o las flechas. La flecha hacia arriba avanza hacia el fondo de la pantalla. También podés hacer clic en el suelo.</p>',
    '<p>Abajo a la izquierda hay un palito redondo: arrastralo y también camina.</p>',
    '<p>Para mirar, arrastrá el mouse. <kbd>Shift</kbd> y las flechas giran o inclinan. <kbd>Z</kbd> y arriba acerca. <kbd>Z</kbd> y abajo aleja.</p>',
    '<p>Para usar algo, hacé clic en la puerta, el árbol, la roca o la persona. Si está lejos, caminás hasta allá.</p>',
    '</section>',
    '<section class="inst-card inst-wide" id="inst-movil">',
    '<h2>En el celular</h2>',
    '<p class="inst-aqui" hidden>Estás aquí.</p>',
    '<p>En <span>/movil/</span>, arrastrá el joystick, el palito redondo de abajo a la izquierda. O tocá el suelo para caminar hasta ese punto.</p>',
    '<p>🏃 En el celular no hay un botón de correr. Con teclado, mantené <kbd>X</kbd> y una tecla de caminar. A caballo no se corre con <kbd>X</kbd>.</p>',
    '<p>Arrastrá un dedo para girar la vista. Pellizcá para acercar o alejar. Tocá la puerta, el árbol, la roca o la persona.</p>',
    '<p>El botón <b>Chat</b> abre el chat. El botón <b>☰ Menú</b> muestra las herramientas. <b>Amigos</b> está bajo la rueda o dentro de <b>⚙</b>.</p>',
    '</section>',
    '<section class="inst-card inst-wide">',
    '<h2>Salir con calma</h2>',
    '<p>🏠 Tocá <b>Descansar</b> para guardar y volver a la entrada. Tu mascota te espera en casa.</p>',
    '<p>🚪 <b>Salir al Parque</b> te deja en el Parque de Envigado. La puerta de la casa hace lo mismo. El botón <b>Casa</b> te devuelve.</p>',
    '<p>👋 Si entraste con cuenta, <b>Cerrar sesión</b> está en <b>⚙</b> y dentro de la casa. Cierra la sesión y no borra la cuenta. Pregunta antes de salir.</p>',
    '<p>Para montar, usá <kbd>M</kbd> o <kbd>E</kbd>, o el botón <b>Montar</b>. A caballo no se entra a la casa.</p>',
    '</section>',
    '<section class="inst-card inst-wide" id="inst-monedas">',
    '<h2>Tus primeras monedas</h2>',
    '<p>No son dinero real. No se venden ni se canjean por plata de verdad. Los números del día los dice el letrero de la mina.</p>',
    '</section>',
    '<section class="inst-card inst-wide">',
    '<h2>Café y cacao</h2>',
    '<p>Plantas en una parcela.</p>',
    '<p>Cosechas cuando está maduro.</p>',
    '<p>En el taller procesas el fruto.</p>',
    '<p>Vendes el bulto si la casa tiene monedas.</p>',
    '<p>El café está junto al cacao. Veinte minutos reales son un día de juego.</p>',
    '<p>Diez cosechas de café son 940 kg de cereza y dan dos sacos de 70 kg de excelso. Diez de cacao son 900 kg en baba y llenan dos cajones, 150 kg secos cada uno. Los kilos cosechados no bajan.</p>',
    '<p>El Libro mayor muestra los kilos y los sacos. No dice quién.</p>',
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
  function paintMonedas(board) {
    const box = document.getElementById('inst-monedas');
    if (!box || !board || !Array.isArray(board.lines) || !board.lines.length) return;
    const title = box.querySelector('h2');
    box.replaceChildren();
    if (title) box.append(title);
    const note = document.createElement('p');
    note.textContent = 'No son dinero real. No se venden ni se canjean por plata de verdad.';
    box.append(note);
    board.lines.forEach((line) => {
      const p = document.createElement('p');
      p.textContent = line;
      box.append(p);
    });
    const more = document.createElement('p');
    more.textContent = 'La tecla L abre el Libro Mayor.';
    box.append(more);
  }
  function loadMonedas() {
    fetch('/reglas-mina', { cache: 'no-store', credentials: 'same-origin' })
      .then((r) => r.json())
      .then(paintMonedas)
      .catch(() => {});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => { mount(); loadMonedas(); });
  else { mount(); loadMonedas(); }
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
