/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Libro mayor público: totales, iconos y frases sin nombres. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.LibroPublico = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this), function () {
  'use strict';

  function formatEs(n) {
    const value = Number(n);
    if (!Number.isFinite(value)) return '0';
    const negative = value < 0;
    const fixed = Math.abs(value).toFixed(8).replace(/0+$/, '').replace(/\.$/, '');
    const parts = fixed.split('.');
    const whole = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    const text = parts[1] ? whole + ',' + parts[1] : whole;
    return negative ? '-' + text : text;
  }

  function coinLine(delta, name) {
    return 'Se acuñaron ' + formatEs(delta) + ' ' + name;
  }

  function feedFromCoins(prev, next) {
    const lines = [];
    const before = {};
    for (const row of (prev && prev.coins) || []) before[row.id] = Number(row.minted) || 0;
    for (const row of (next && next.coins) || []) {
      const was = before[row.id] || 0;
      const now = Number(row.minted) || 0;
      if (now > was) lines.push(coinLine(now - was, row.name || row.id || 'moneda'));
    }
    return lines;
  }

  function ingotRows(ledger) {
    const map = { oro: 0, plata: 0, cobre: 0 };
    if (!ledger || typeof ledger !== 'object') return map;
    let source = null;
    if (ledger.ingots && typeof ledger.ingots === 'object') source = ledger.ingots;
    else if (ledger.lingotes && typeof ledger.lingotes === 'object') source = ledger.lingotes;
    else if (ledger.foundry && typeof ledger.foundry === 'object') source = ledger.foundry;
    if (!source) return map;
    for (const [key, value] of Object.entries(source)) {
      const name = String(key).toLowerCase();
      const count = Number(value) || 0;
      if (name.includes('oro') || name.includes('gold')) map.oro += count;
      else if (name.includes('plata') || name.includes('silver')) map.plata += count;
      else if (name.includes('cobre') || name.includes('copper')) map.cobre += count;
    }
    return map;
  }

  function esc(text) {
    return String(text == null ? '' : text)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function artMap() {
    if (typeof window !== 'undefined' && window.CAFE_CACAO_ART) return window.CAFE_CACAO_ART;
    return null;
  }

  function icon(kind) {
    const map = artMap();
    const file = map && map.icons && map.icons[kind];
    if (!file) return '';
    const base = map.base || 'assets/cafe-cacao/';
    const rev = map.rev ? ('?v=' + map.rev) : '';
    const src = base + file + rev;
    return `<img class="libro-ico-img" src="${esc(src)}" alt="">`;
  }

  function stageRow(crop) {
    const map = artMap();
    const rows = map && map.stageIcons && map.stageIcons[crop];
    if (!rows || !rows.length) return '';
    const base = map.base || 'assets/cafe-cacao/';
    return `<div class="libro-etapas">${rows.map((row) => {
      const src = base + row.file;
      const live = row.live ? base + row.live : '';
      const backup = live ? ` onerror="this.onerror=null;this.src='${esc(live)}'"` : '';
      return `<img src="${esc(src)}" alt="${esc(row.label || '')}"${backup}>`;
    }).join('')}</div>`;
  }

  function bar(minted, max) {
    const top = Number(max) || 0;
    const now = Number(minted) || 0;
    const pct = top > 0 ? Math.max(0, Math.min(100, now / top * 100)) : 0;
    return `<div class="libro-bar" role="meter" aria-valuemin="0" aria-valuemax="${esc(top)}" aria-valuenow="${esc(now)}"><span style="width:${pct}%"></span></div>`;
  }

  function render(data) {
    data = data || {};
    const finca = data.finca || {};
    const kg = finca.harvestedKg || {};
    const bags = finca.processedBags || {};
    const crops = [
      ['cafe', 'Café', kg.cafe || 0, bags.cafe || 0],
      ['cacao', 'Cacao', kg.cacao || 0, bags.cacao || 0],
    ];
    const cropHtml = crops.map(([id, name, kilos, count]) => {
      const spec = (finca.crops || {})[id] || {};
      const fresh = spec.freshName ? ` de ${esc(spec.freshName)}` : '';
      const unit = spec.unitCount ? esc(spec.unitCount) : 'bultos procesados';
      return `<article class="libro-crop"><div class="libro-ico">${icon(id)}${icon('kg')}${icon('bag')}</div>` +
        `<h3>${name}</h3>${stageRow(id)}<p><b>${esc(formatEs(kilos))} kg</b> cosechados${fresh}</p><p><b>${esc(formatEs(count))}</b> ${unit}</p></article>`;
    }).join('');
    const coins = [
      ['simoncoin', 'oro', 'Simoncoin', 'Oro', 21000000],
    ];
    const byId = {};
    for (const row of data.coins || []) byId[row.id] = row;
    const blurbs = {
      simoncoin: 'Simoncoin: 21.000.000 y no más. Hasta 2 decimales.',
    };
    const coinHtml = coins.map(([id, kind, name, metal, fallback]) => {
      const row = byId[id] || {};
      const max = row.max != null ? row.max : fallback;
      const minted = row.minted || 0;
      const total = id === 'simoncoin' ? `<p>SMC minadas en total: <b>${esc(formatEs(minted))}</b> de ${esc(formatEs(max))}.</p>` : '';
      return `<article class="libro-coin"><div class="libro-ico">${icon(kind)}</div><h3>${name}</h3><p>${esc(blurbs[id])}</p><p>Van <b>${esc(formatEs(minted))}</b> de ${esc(formatEs(max))}</p>${total}${bar(minted, max)}</article>`;
    }).join('');
    const ingots = ingotRows(data);
    const ingotHtml = `<section class="libro-ingots"><div class="libro-ico">${icon('ingot')}</div><h3>Lingotes</h3><p>Los cuenta el Banco Central. Acá sólo se leen. Este libro no los crea.</p><ul><li>Oro <b>${esc(formatEs(ingots.oro))}</b></li><li>Plata <b>${esc(formatEs(ingots.plata))}</b></li><li>Cobre <b>${esc(formatEs(ingots.cobre))}</b></li></ul></section>`;
    const feed = [].concat(finca.feed || [], data.extraFeed || []).slice(0, 12);
    const feedHtml = feed.length ? feed.map(line => `<li>${esc(line)}</li>`).join('') : '<li>Todavía no hay movimientos. El libro te lo dice con calma.</li>';
    return `<div class="libro-publico-cuerpo">` +
      `<p class="libro-lead">Este libro es la memoria de las monedas del juego. Acá ves lo que se acuñó. Es una simulación. Las monedas no son dinero real. No se retiran ni se canjean por plata de verdad. El libro público no dice quién.</p>` +
      `<div class="libro-grid">${cropHtml}</div>` +
      `<div class="libro-grid">${coinHtml}</div>` +
      ingotHtml +
      `<section class="libro-feed"><h3>En vivo</h3><ul>${feedHtml}</ul></section>` +
      `</div>`;
  }

  return { formatEs, coinLine, feedFromCoins, ingotRows, render, icon };
});
