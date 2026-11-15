/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Lectura breve. Texto de la Reina-Valera 1909, en dominio público. */
(() => {
  'use strict';
  const VERSOS = [
    { cita: 'Salmo 23, 1-4', texto: 'Jehová es mi pastor; nada me faltará. En lugares de delicados pastos me hará yacer: junto á aguas de reposo me pastoreará. Confortará mi alma; guiaráme por sendas de justicia por amor de su nombre. Aunque ande en valle de sombra de muerte, no temeré mal alguno; porque tú estarás conmigo: tu vara y tu cayado me infundirán aliento.' },
    { cita: 'Salmo 121, 1-2', texto: 'Alzaré mis ojos á los montes, de donde vendrá mi socorro. Mi socorro viene de Jehová, que hizo los cielos y la tierra.' },
    { cita: 'Juan 3, 16', texto: 'Porque de tal manera amó Dios al mundo, que ha dado á su Hijo unigénito, para que todo aquel que en él cree, no se pierda, mas tenga vida eterna.' },
    { cita: 'Mateo 11, 28', texto: 'Venid á mí todos los que estáis trabajados y cargados, que yo os haré descansar.' },
    { cita: 'Filipenses 4, 6-7', texto: 'Por nada estéis afanosos; sino sean conocidas vuestras peticiones delante de Dios en toda oración y ruego, con hacimiento de gracias. Y la paz de Dios, que sobrepuja todo entendimiento, guardará vuestros corazones y vuestros pensamientos en Cristo Jesús.' },
  ];
  let abierta = false;
  let indice = 0;
  let panel;

  function pintar() {
    const verso = VERSOS[indice];
    panel.querySelector('#biblia-cita').textContent = verso.cita;
    panel.querySelector('#biblia-texto').textContent = verso.texto;
    panel.querySelector('#biblia-n').textContent = (indice + 1) + ' / ' + VERSOS.length;
  }
  function asegurar() {
    if (panel) return;
    panel = document.createElement('section');
    panel.id = 'biblia';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-labelledby', 'biblia-titulo');
    panel.innerHTML = '<header id="biblia-titulo">Biblia <button type="button" id="biblia-cerrar" aria-label="Cerrar">✕</button></header><p class="biblia-nota">Reina-Valera 1909 · dominio público. Una lectura corta, no una edición completa.</p><p id="biblia-cita"></p><p id="biblia-texto"></p><div class="biblia-nav"><button type="button" id="biblia-antes">Anterior</button><span id="biblia-n"></span><button type="button" id="biblia-sigue">Siguiente</button></div>';
    document.body.append(panel);
    panel.querySelector('#biblia-cerrar').onclick = cerrar;
    panel.querySelector('#biblia-antes').onclick = () => { indice = (indice + VERSOS.length - 1) % VERSOS.length; pintar(); };
    panel.querySelector('#biblia-sigue').onclick = () => { indice = (indice + 1) % VERSOS.length; pintar(); };
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && abierta) cerrar(); });
  }
  function abrir() {
    asegurar();
    abierta = true;
    panel.hidden = false;
    pintar();
    panel.querySelector('#biblia-cerrar').focus();
  }
  function cerrar() {
    abierta = false;
    if (panel) panel.hidden = true;
  }
  window.Biblia = { abrir, cerrar, abierta: () => abierta, versos: VERSOS };
})();
