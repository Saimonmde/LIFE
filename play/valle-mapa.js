/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Mapa del valle a partir de coordenadas reales, en el estilo bajo del juego. */
(() => {
  'use strict';
  const FONT = '600 13px system-ui, "Segoe UI", sans-serif';

  function geo() { return window.VALLE_GEO; }

  function fit(canvas, view) {
    const data = geo();
    const b = data.bounds;
    const pad = 28;
    const zoom = (view && view.zoom) || 1;
    const availW = Math.max(40, canvas.width - pad * 2);
    const availH = Math.max(40, canvas.height - pad * 2);
    const aspect = ((b.lonE - b.lonW) * Math.cos(6.25 * Math.PI / 180)) / (b.latN - b.latS);
    let w = availW * zoom;
    let h = w / aspect;
    if (h > availH * zoom) { h = availH * zoom; w = h * aspect; }
    return {
      left: (canvas.width - w) / 2 + ((view && view.panX) || 0),
      top: (canvas.height - h) / 2 + ((view && view.panY) || 0),
      w: w, h: h, bounds: b,
    };
  }

  function xy(frame, lat, lon) {
    const b = frame.bounds;
    const x = (lon - b.lonW) / (b.lonE - b.lonW);
    const y = (b.latN - lat) / (b.latN - b.latS);
    return [frame.left + x * frame.w, frame.top + y * frame.h];
  }

  function latlonOfTile(x, y, world) {
    const b = geo().bounds;
    const lon = b.lonW + (x / Math.max(1, world.width - 1)) * (b.lonE - b.lonW);
    const lat = b.latN - (y / Math.max(1, world.height - 1)) * (b.latN - b.latS);
    return [lat, lon];
  }

  function playerLatLon(px, py, world) {
    const homes = (window.HOGARES && window.HOGARES.casas) || [];
    for (const home of homes) {
      if (Math.max(Math.abs(px - home.x), Math.abs(py - home.y)) <= 14) {
        const town = geo().municipios.find(item => item.id === home.id);
        if (town) return [town.lat, town.lon];
      }
    }
    return latlonOfTile(px, py, world);
  }

  function house(ctx, x, y, s) {
    ctx.fillStyle = '#8d5a42';
    ctx.beginPath();
    ctx.moveTo(x, y - s * 0.2);
    ctx.lineTo(x - s, y + s * 0.35);
    ctx.lineTo(x + s, y + s * 0.35);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = '#f7f1e4';
    ctx.fillRect(x - s * 0.62, y + s * 0.28, s * 1.24, s * 0.85);
    ctx.fillStyle = '#6b4228';
    ctx.fillRect(x - s * 0.16, y + s * 0.62, s * 0.32, s * 0.5);
  }

  function draw(ctx, canvas, view, opts) {
    const data = geo();
    if (!data) return null;
    const frame = fit(canvas, view);
    const world = opts.world;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#24362c';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const grid = data.grid;
    const cw = frame.w / grid.cols;
    const ch = frame.h / grid.rows;
    let lo = 1e9, hi = 0;
    for (const row of grid.elev) for (const v of row) { if (v < lo) lo = v; if (v > hi) hi = v; }
    const span = hi - lo || 1;
    for (let j = 0; j < grid.rows; j++) {
      for (let i = 0; i < grid.cols; i++) {
        const t = (grid.elev[j][i] - lo) / span;
        ctx.fillStyle = t < 0.16 ? '#e7c892' : t < 0.34 ? '#8aaf62' : t < 0.58 ? '#4f7a45' : '#3d4e3c';
        ctx.fillRect(frame.left + i * cw, frame.top + j * ch, cw + 0.8, ch + 0.8);
      }
    }
    ctx.beginPath();
    data.river.forEach(([lat, lon], index) => {
      const [x, y] = xy(frame, lat, lon);
      if (index) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    });
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#1f6f86';
    ctx.lineWidth = Math.max(5, frame.w * 0.014);
    ctx.stroke();
    ctx.strokeStyle = '#d5f4fb';
    ctx.lineWidth = Math.max(1.6, frame.w * 0.004);
    ctx.stroke();
    ctx.font = FONT;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    const placed = [];
    const overlaps = (a, b) => !(a.x + a.w + 4 < b.x || b.x + b.w + 4 < a.x || a.y + a.h + 3 < b.y || b.y + b.h + 3 < a.y);
    for (const park of data.parques) {
      const [x, y] = xy(frame, park.lat, park.lon);
      const w = ctx.measureText(park.name).width + 8;
      let ly = y - 8;
      let guard = 0;
      while (guard++ < 6 && placed.some(box => overlaps(box, { x: x + 6, y: ly, w: w, h: 14 }))) ly += 14;
      placed.push({ x: x + 6, y: ly, w: w, h: 14 });
      ctx.fillStyle = '#2f6a32';
      ctx.fillRect(x - 3, y - 3, 6, 6);
      ctx.fillStyle = '#f4fff0';
      ctx.fillText(park.name, x + 8, ly + 7);
    }
    for (const town of data.municipios) {
      const [x, y] = xy(frame, town.lat, town.lon);
      house(ctx, x, y, 7);
      const label = town.name;
      const w = ctx.measureText(label).width + 10;
      let ly = y - 16;
      let guard = 0;
      while (guard++ < 8 && placed.some(box => overlaps(box, { x: x + 12, y: ly, w: w, h: 16 }))) ly += 16;
      placed.push({ x: x + 12, y: ly, w: w, h: 16 });
      ctx.fillStyle = 'rgba(20, 24, 18, 0.82)';
      ctx.fillRect(x + 12, ly, w, 16);
      ctx.fillStyle = '#fff6e4';
      ctx.fillText(label, x + 16, ly + 8);
    }
    ctx.fillStyle = '#f7e8bb';
    ctx.font = '700 16px system-ui, "Segoe UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('N', canvas.width / 2, 16);
    ctx.fillText('S', canvas.width / 2, canvas.height - 10);
    ctx.fillText('OC', 18, canvas.height / 2);
    ctx.fillText('OR', canvas.width - 18, canvas.height / 2);
    if (opts.player && world) {
      const [lat, lon] = playerLatLon(opts.player.x, opts.player.y, world);
      const [x, y] = xy(frame, lat, lon);
      ctx.save();
      ctx.translate(x, y);
      ctx.beginPath();
      for (let i = 0; i < 10; i++) {
        const a = -Math.PI / 2 + i * Math.PI / 5;
        const rr = i % 2 ? 4 : 9;
        ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
      }
      ctx.closePath();
      ctx.fillStyle = '#ffdf29';
      ctx.strokeStyle = '#33230c';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fill();
      ctx.restore();
    }
    ctx.font = '12px system-ui, "Segoe UI", sans-serif';
    ctx.fillStyle = 'rgba(255,255,255,0.78)';
    ctx.textAlign = 'left';
    ctx.fillText('Río Medellín · © OpenStreetMap · Relieve NASA SRTM', 10, canvas.height - 8);
    return frame;
  }

  function hit(canvas, view, px, py, world) {
    const frame = fit(canvas, view);
    const marks = [];
    const ctx = canvas.getContext('2d');
    ctx.font = FONT;
    for (const town of geo().municipios) {
      const [x, y] = xy(frame, town.lat, town.lon);
      const w = ctx.measureText(town.name).width + 22;
      if (px >= x - 12 && px <= x + 12 + w && py >= y - 18 && py <= y + 14) {
        return { id: town.id, tx: 0, ty: 0, pt: { x: px, y: py }, frame: frame };
      }
      marks.push(town);
    }
    const b = frame.bounds;
    const u = (px - frame.left) / frame.w;
    const v = (py - frame.top) / frame.h;
    if (u < 0 || v < 0 || u > 1 || v > 1) return null;
    const lon = b.lonW + u * (b.lonE - b.lonW);
    const lat = b.latN - v * (b.latN - b.latS);
    const tx = Math.floor(u * (world.width - 1));
    const ty = Math.floor(v * (world.height - 1));
    return { tx: tx, ty: ty, pt: { x: px, y: py }, frame: frame, lat: lat, lon: lon };
  }

  window.ValleMapa = { draw: draw, hit: hit, fit: fit };
})();
