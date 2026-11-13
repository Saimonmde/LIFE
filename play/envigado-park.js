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
  // Bancas y esculturas propias. No copian una obra real ni el bronce del Primer Poblado.
  const benches = [
    { dx: 13, dy: 9, id: 'banca_norte' },
    { dx: 20, dy: 9, id: 'banca_oriente' },
    { dx: 13, dy: 13, id: 'banca_sur' },
    { dx: 20, dy: 13, id: 'banca_esquina' },
  ];
  const sculptures = [
    { dx: 14, dy: 7, id: 'anillo', name: 'Anillo', note: 'Pieza abstracta de reemplazo: un anillo sobre un plinto.' },
    { dx: 19, dy: 7, id: 'columna', name: 'Columna', note: 'Pieza abstracta de reemplazo: tres bloques desplazados sobre un plinto.' },
    { dx: 15, dy: 15, id: 'ovalo', name: 'Óvalo', note: 'Pieza abstracta de reemplazo: un óvalo sobre un plinto.' },
  ];
  function tile(dx, dy) { return { x: PARK_ORIGIN.x + dx, y: PARK_ORIGIN.y + dy }; }
  function canecaTiles() { return canecas.map((c, i) => Object.assign(tile(c.dx, c.dy), { ry: c.ry, id: 'caneca_' + i, kind: 'caneca' })); }
  function skateTiles() { return skateBlocks.map(([dx, dy]) => tile(skate.dx + dx, skate.dy + dy)); }
  function benchTiles() { return benches.map(b => Object.assign(tile(b.dx, b.dy), { id: b.id, kind: 'banca', dx: 1 })); }
  function sculptureTiles() { return sculptures.map(s => Object.assign(tile(s.dx, s.dy), s, { kind: 'escultura' })); }
  function allProps() { return canecaTiles().concat(benchTiles(), sculptureTiles()); }
  function block(W) {
    if (!W || !W.collision) return;
    const spots = skateTiles().concat(allProps().flatMap(p => {
      const cells = [{ x: p.x, y: p.y }];
      if (p.dx) cells.push({ x: p.x + 1, y: p.y });
      return cells;
    }));
    for (const t of spots) {
      if (t.y >= 0 && t.y < W.height && t.x >= 0 && t.x < W.width) W.collision[t.y][t.x] = 1;
    }
  }
  const drawn2d = [];
  const drawn3d = [];
  function paint2d(ctx, prop, TS) {
    if (drawn2d[drawn2d.length - 1] !== prop.id) drawn2d.push(prop.id);
    const x = prop.x * TS, y = prop.y * TS;
    ctx.save();
    if (prop.kind === 'caneca') {
      ctx.fillStyle = '#1c6b34';
      ctx.fillRect(x + 18, y + 16, 28, 36);
      ctx.fillStyle = '#145028';
      ctx.fillRect(x + 14, y + 12, 36, 8);
      ctx.fillStyle = '#9aa3a0';
      ctx.fillRect(x + 30, y + 8, 4, 8);
    } else if (prop.kind === 'banca') {
      ctx.fillStyle = '#3e4650';
      ctx.fillRect(x + 6, y + 28, 8, 22);
      ctx.fillRect(x + 50, y + 28, 8, 22);
      ctx.fillStyle = '#8a5a32';
      ctx.fillRect(x + 4, y + 22, 92, 10);
      ctx.fillRect(x + 8, y + 8, 84, 8);
    } else if (prop.id === 'anillo') {
      ctx.strokeStyle = '#c4a15a'; ctx.lineWidth = 8;
      ctx.beginPath(); ctx.arc(x + 32, y + 28, 16, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = '#d9d3c7'; ctx.fillRect(x + 16, y + 46, 32, 10);
    } else if (prop.id === 'columna') {
      ctx.fillStyle = '#c4a15a';
      ctx.fillRect(x + 18, y + 28, 28, 16);
      ctx.fillRect(x + 22, y + 14, 22, 14);
      ctx.fillRect(x + 14, y + 2, 20, 12);
      ctx.fillStyle = '#d9d3c7'; ctx.fillRect(x + 12, y + 44, 40, 12);
    } else {
      ctx.fillStyle = '#c4a15a';
      ctx.beginPath(); ctx.ellipse(x + 32, y + 26, 14, 22, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#d9d3c7'; ctx.fillRect(x + 14, y + 48, 36, 10);
    }
    ctx.restore();
  }
  window.EnvigadoPark = {
    PARK_ORIGIN, canecas, skate, benches, sculptures,
    canecaTiles, skateTiles, benchTiles, sculptureTiles, allProps, tile, block,
    drawn2d, drawn3d, paint2d,
  };
})();
