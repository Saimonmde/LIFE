/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Parque de Envigado props. Move PARK_ORIGIN and every caneca and the skate cluster move with the block. */
(() => {
  'use strict';
  // Sara's origin (214, 52) plus the same VALLE_OFFSET as PARK_DOOR.
  const off = (window.Casa && window.Casa.VALLE_OFFSET) || { x: 0, y: 0 };
  const PARK_ORIGIN = { x: 214 + off.x, y: 52 + off.y };
  const canecas = [
    { dx: 18, dy: 8, ry: 0.4 },
    { dx: 15, dy: 11, ry: 1.7 },
    { dx: 22, dy: 18, ry: 2.6 },
  ];
  const skate = { dx: 3, dy: 18 };
  const skateBlocks = [[0, 0], [1, 0], [0, 1], [1, 1], [2, 0], [2, 1]];
  function tile(dx, dy) { return { x: PARK_ORIGIN.x + dx, y: PARK_ORIGIN.y + dy }; }
  function canecaTiles() { return canecas.map(c => Object.assign(tile(c.dx, c.dy), { ry: c.ry })); }
  function skateTiles() { return skateBlocks.map(([dx, dy]) => tile(skate.dx + dx, skate.dy + dy)); }
  function block(W) {
    if (!W || !W.collision) return;
    for (const t of canecaTiles().concat(skateTiles())) {
      if (t.y >= 0 && t.y < W.height && t.x >= 0 && t.x < W.width) W.collision[t.y][t.x] = 1;
    }
  }
  window.EnvigadoPark = { PARK_ORIGIN, canecas, skate, canecaTiles, skateTiles, tile, block };
})();
