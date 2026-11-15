/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Tutorial corto, se puede saltar y se recuerda. */
(() => {
  'use strict';
  const KEY = 'lifeinc.instructivo.v1';
  function root() { return document.getElementById('instructivo') || document.getElementById('tutorial'); }
  function open() {
    const el = root();
    if (!el) return;
    el.hidden = false;
  }
  function close(remember) {
    const el = root();
    if (el) el.hidden = true;
    if (remember) {
      try { localStorage.setItem(KEY, '1'); } catch {}
    }
  }
  function afterFly() {
    if (window.Intro && Intro.blocking()) return;
    if (/autotest=1/.test(location.search)) return;
    try { if (localStorage.getItem(KEY)) return; } catch {}
    open();
  }
  document.addEventListener('click', (event) => {
    const t = event.target;
    if (!(t instanceof Element)) return;
    if (t.id === 'tutorial-cerrar' || t.id === 'tutorial-saltar' || t.id === 'instructivo-cerrar' || t.id === 'instructivo-saltar') close(true);
    if (t.id === 'b-tutorial' || t.id === 'cajon-instructivo' || t.id === 'b-ayuda-izq') open();
  });
  window.Tutorial = { open, close, afterFly };
})();
