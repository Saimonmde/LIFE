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
  // Bancas de concreto del escaneo. El frente (+Z del modelo) mira al prado.
  // yaw 0 = sur, PI = norte, PI/2 = oriente, -PI/2 = occidente.
  const benches = [
    { dx: 13, dy: 9, id: 'banca_norte', yaw: Math.PI },
    { dx: 20, dy: 9, id: 'banca_oriente', yaw: Math.PI },
    { dx: 13, dy: 13, id: 'banca_sur', yaw: 0 },
    { dx: 20, dy: 13, id: 'banca_esquina', yaw: 0 },
    { dx: 9, dy: 10, id: 'banca_sendero_oeste', yaw: Math.PI },
    { dx: 31, dy: 10, id: 'banca_sendero_este', yaw: Math.PI },
    { dx: 27, dy: 12, id: 'banca_sendero_sur', yaw: 0 },
    { dx: 15, dy: 5, id: 'banca_cruce_oeste', yaw: -Math.PI / 2 },
    { dx: 18, dy: 17, id: 'banca_cruce_este', yaw: Math.PI / 2 },
    { dx: 15, dy: 21, id: 'banca_cruce_suroeste', yaw: -Math.PI / 2 },
    { dx: 36, dy: 7, id: 'banca_atrio_1', yaw: -Math.PI / 2 },
    { dx: 36, dy: 15, id: 'banca_atrio_2', yaw: -Math.PI / 2 },
  ];
  const sculptures = [
    { dx: 14, dy: 7, id: 'anillo', name: 'Anillo', note: 'Pieza abstracta de reemplazo: un anillo sobre un plinto.' },
    { dx: 19, dy: 7, id: 'columna', name: 'Columna', note: 'Pieza abstracta de reemplazo: tres bloques desplazados sobre un plinto.' },
    { dx: 15, dy: 15, id: 'ovalo', name: 'Óvalo', note: 'Pieza abstracta de reemplazo: un óvalo sobre un plinto.' },
  ];
  // Dos bancas por parque municipal, fuera de la casilla de llegada. Coordenadas absolutas.
  const municipal = [
    { x: 52, y: 362, id: 'banca_caldas_este', yaw: -Math.PI / 2 },
    { x: 49, y: 365, id: 'banca_caldas_sur', yaw: Math.PI },
    { x: 85, y: 300, id: 'banca_sabaneta_este', yaw: -Math.PI / 2 },
    { x: 82, y: 303, id: 'banca_sabaneta_sur', yaw: Math.PI },
    { x: 84, y: 352, id: 'banca_la_estrella_este', yaw: -Math.PI / 2 },
    { x: 81, y: 355, id: 'banca_la_estrella_sur', yaw: Math.PI },
    { x: 99, y: 230, id: 'banca_itagui_este', yaw: -Math.PI / 2 },
    { x: 96, y: 233, id: 'banca_itagui_sur', yaw: Math.PI },
    { x: 133, y: 196, id: 'banca_medellin_este', yaw: -Math.PI / 2 },
    { x: 130, y: 199, id: 'banca_medellin_sur', yaw: Math.PI },
    { x: 125, y: 130, id: 'banca_bello_este', yaw: -Math.PI / 2 },
    { x: 122, y: 133, id: 'banca_bello_sur', yaw: Math.PI },
    { x: 174, y: 131, id: 'banca_copacabana_este', yaw: -Math.PI / 2 },
    { x: 171, y: 134, id: 'banca_copacabana_sur', yaw: Math.PI },
    { x: 226, y: 103, id: 'banca_girardota_este', yaw: -Math.PI / 2 },
    { x: 223, y: 106, id: 'banca_girardota_sur', yaw: Math.PI },
    { x: 324, y: 50, id: 'banca_barbosa_este', yaw: -Math.PI / 2 },
    { x: 321, y: 53, id: 'banca_barbosa_sur', yaw: Math.PI },
  ];
  function tile(dx, dy) { return { x: PARK_ORIGIN.x + dx, y: PARK_ORIGIN.y + dy }; }
  function canecaTiles() { return canecas.map((c, i) => Object.assign(tile(c.dx, c.dy), { ry: c.ry, id: 'caneca_' + i, kind: 'caneca' })); }
  function skateTiles() { return skateBlocks.map(([dx, dy]) => tile(skate.dx + dx, skate.dy + dy)); }
  function benchTiles() { return benches.map(b => Object.assign(tile(b.dx, b.dy), { id: b.id, kind: 'banca', yaw: b.yaw })); }
  function sculptureTiles() { return sculptures.map(s => Object.assign(tile(s.dx, s.dy), s, { kind: 'escultura' })); }
  function municipalTiles() { return municipal.map(b => ({ x: b.x, y: b.y, id: b.id, kind: 'banca', yaw: b.yaw })); }
  function allProps() { return canecaTiles().concat(benchTiles(), sculptureTiles(), municipalTiles()); }
  function block(W) {
    if (!W || !W.collision) return;
    const spots = skateTiles().concat(allProps());
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
      const across = Math.abs(Math.sin(prop.yaw || 0)) > 0.5;
      ctx.fillStyle = '#6e6862';
      if (across) {
        ctx.fillRect(x + 18, y + 8, 28, 48);
        ctx.fillStyle = '#e7e2d6';
        ctx.fillRect(x + 22, y + 12, 20, 40);
      } else {
        ctx.fillRect(x + 8, y + 18, 48, 28);
        ctx.fillStyle = '#e7e2d6';
        ctx.fillRect(x + 12, y + 22, 40, 20);
      }
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
    PARK_ORIGIN, canecas, skate, benches, sculptures, municipal,
    canecaTiles, skateTiles, benchTiles, sculptureTiles, municipalTiles, allProps, tile, block,
    drawn2d, drawn3d, paint2d,
  };
})();
