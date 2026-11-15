/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Instructivo visible. Las teclas son las del juego, no unas inventadas. */
(() => {
  'use strict';
  const html = [
    '<header><strong>Cómo se juega</strong><button type="button" id="instructivo-cerrar" aria-label="Cerrar">✕</button></header>',
    '<p class="inst-lead">Una idea por línea. El botón <b>?</b> abre esto otra vez.</p>',
    '<section class="inst-card inst-wide" id="inst-web">',
    '<h2>El juego</h2>',
    '<p class="inst-aqui" hidden>Estás aquí.</p>',
    '<p>🏙 Saimon City. Valle de Aburrá. El año es 1777.</p>',
    '<p>⛏ Ve a la mina. Pica el metal.</p>',
    '<p>🪙 En el horno, Acuñar guarda las monedas en tu inventario. Así armas tu reserva.</p>',
    '<p>🏠 <b>Descansar</b> / Ir a casa. Tu mascota te espera.</p>',
    '</section>',
    '<section class="inst-card inst-wide" id="inst-movil">',
    '<h2>Cómo moverte</h2>',
    '<p class="inst-aqui" hidden>Estás aquí.</p>',
    '<p>🖥 En <span>/play/</span>: clic en el suelo, o <kbd>W</kbd> <kbd>A</kbd> <kbd>S</kbd> <kbd>D</kbd>.</p>',
    '<p>📱 En <span>/movil/</span>: arrastra el joystick.</p>',
    '<p>🏃 En el celular no hay un botón de correr. Con teclado, mantén <kbd>X</kbd> y camina.</p>',
    '<p>🚪 <b>Salir al Parque</b> te deja fuera. La puerta de la casa hace lo mismo.</p>',
    '<p>👋 <b>Cerrar sesión</b> está en ⚙ y dentro de la casa. Pregunta antes de salir.</p>',
    '</section>',
    '<section class="inst-card inst-wide">',
    '<h2>Café y cacao</h2>',
    '<p>Plantas en una parcela.</p>',
    '<p>Cosechas cuando está maduro.</p>',
    '<p>En el taller procesas el fruto.</p>',
    '<p>Vendes el bulto si la casa tiene monedas.</p>',
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
