/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Aceleración, giro y el seguimiento de otros jugadores. Sin asignar objetos en el bucle. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Motion = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const EMOTES = [
    { id: 'wave', name: 'Saludar' },
    { id: 'bow', name: 'Reverencia' },
    { id: 'dance', name: 'Bailar' },
    { id: 'clap', name: 'Aplauso' },
    { id: 'laugh', name: 'Reír' },
    { id: 'sit', name: 'Sentarse' },
    { id: 'point', name: 'Señalar' },
    { id: 'bacano', name: '¡Bacano!' },
  ];

  function approach(current, target, dt, accel, brake) {
    const cur = Number(current) || 0;
    const goal = Number(target) || 0;
    const rate = goal > cur ? accel : brake;
    const k = 1 - Math.exp(-Math.max(0, dt) * rate);
    return cur + (goal - cur) * k;
  }

  function turn(current, target, dt, rate) {
    let delta = (Number(target) || 0) - (Number(current) || 0);
    const pi = Math.PI;
    while (delta > pi) delta -= pi * 2;
    while (delta < -pi) delta += pi * 2;
    const k = 1 - Math.exp(-Math.max(0, dt) * rate);
    return (Number(current) || 0) + delta * k;
  }

  function blend(speed, walk, run) {
    const pace = walk || 4.2;
    const sprint = run || 7.3;
    const s = Math.max(0, Number(speed) || 0);
    if (s < 0.2) return { idle: 1, walk: 0, run: 0 };
    if (s <= pace) {
      const w = s / pace;
      return { idle: 1 - w, walk: w, run: 0 };
    }
    const r = Math.min(1, (s - pace) / Math.max(0.01, sprint - pace));
    return { idle: 0, walk: 1 - r, run: r };
  }

  function follow(x, y, tx, ty, dt, snap) {
    const dx = tx - x;
    const dy = ty - y;
    const dist = Math.hypot(dx, dy);
    const limit = snap || 8;
    if (!Number.isFinite(dist) || dist > limit) return { x: tx, y: ty, speed: 0, moving: false };
    const k = 1 - Math.exp(-Math.max(0, dt) * 8);
    return {
      x: x + dx * k,
      y: y + dy * k,
      speed: dist * 8,
      moving: dist > 0.03,
    };
  }

  return { EMOTES, approach, turn, blend, follow };
});
