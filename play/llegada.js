/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Qué vuelo toca al entrar: ovni la primera vez, helicóptero después. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.Llegada = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  function finite(n) { return Number.isFinite(Number(n)); }
  function plan(opts) {
    opts = opts || {};
    if (opts.autotest) return { kind: 'none' };
    if (opts.intro === 'ovni' && finite(opts.x) && finite(opts.y)) {
      return { kind: 'ovni', x: Number(opts.x), y: Number(opts.y) };
    }
    if (opts.municipio && finite(opts.hx) && finite(opts.hy)) {
      return { kind: 'heli', x: Number(opts.hx), y: Number(opts.hy) };
    }
    if (!opts.flew) return { kind: 'fly' };
    return { kind: 'none' };
  }
  return { plan };
});
