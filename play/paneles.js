/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* El arrastre de paneles pasó a hud-layout.js y sólo ocurre en modo edición. */
(() => {
  'use strict';
  function scan() { if (window.HudLayout) window.HudLayout.scan(); }
  window.Paneles = { scan };
})();
