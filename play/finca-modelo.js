/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Elige el dibujo de una etapa. El manifiesto de Sara es la lista de archivos.
   planted es siembra y grown es cosecha. growing, flowering y fruiting
   son las claves que ella sugirió: aquí son crecimiento, floración y fruto.
   En el celular se pide el GLB lejano, y se carga después. Si falla, queda el 2D. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.FincaModelo = api;
})(typeof window !== 'undefined' ? window : this, function () {
  const PHASES = ['siembra', 'crecimiento', 'floracion', 'fruto', 'cosecha'];
  const LOD_DISTANCE = 18;

  function slot(art, group, crop, id) {
    const models = (art && art.models) || {};
    const table = (models[group] || {})[crop] || {};
    return table[id] || null;
  }

  function visualFor(art, request) {
    const ask = request || {};
    const base = (art && art.base) || 'assets/cafe-cacao/';
    const item = slot(art, ask.group, ask.crop, ask.id);
    if (!item) return { kind: 'flat', url: '', lod: '' };
    const flat = item.flat ? base + item.flat : '';
    const mobile = !!(ask.mobile || ask.flat);
    const farFile = item.lod || item.glb || '';
    if (mobile) {
      if (!farFile) return { kind: 'flat', url: flat, lod: '' };
      return { kind: 'glb', url: base + farFile, lod: 'far', flat: flat, lazy: true };
    }
    if (!item.glb) return { kind: 'flat', url: flat, lod: '' };
    const limit = Number(item.lodDistance || ask.lodDistance || LOD_DISTANCE);
    if (Number(ask.distance) > limit && item.lod) {
      return { kind: 'glb', url: base + item.lod, lod: 'far', flat: flat, lazy: false };
    }
    return { kind: 'glb', url: base + item.glb, lod: 'near', flat: flat, lazy: false };
  }

  // El servidor real habla en español. Las claves en inglés son las que
  // Sara anotó como suggestedState, no un segundo reloj.
  const SERVER_STAGE = {
    empty: '', vacio: '',
    planted: 'siembra', planton: 'siembra', siembra: 'siembra',
    growing: 'crecimiento', verde: 'crecimiento', crecimiento: 'crecimiento',
    flowering: 'floracion', floracion: 'floracion',
    fruiting: 'fruto', fruto: 'fruto',
    grown: 'cosecha', maduro: 'cosecha', cosecha: 'cosecha',
  };

  const LIVE_FLAT = {
    '../sprites/plot_cafe_siembra.png': 'cafe_siembra_64.png',
    '../sprites/plot_cafe_crecimiento.png': 'cafe_crecimiento_64.png',
    '../sprites/plot_cafe_cosecha.png': 'cafe_cosecha_64.png',
    '../sprites/plot_cacao_siembra.png': 'cacao_siembra_64.png',
    '../sprites/plot_cacao_crecimiento.png': 'cacao_crecimiento_64.png',
    '../sprites/plot_cacao_cosecha.png': 'cacao_cosecha_64.png',
    '../talleres/taller_cafe.png': 'taller_cafe_lite.png',
    '../talleres/taller_cacao.png': 'taller_cacao_lite.png',
    '../cultivos/bulto_cafe.png': 'bulto_cafe_64.png',
  };

  function artBase(art) {
    return (art && art.base) || 'assets/cafe-cacao/';
  }

  function saraRoot(art) {
    return artBase(art) + ((art && art.sara) || 'sara/');
  }

  function resolveFlat(art, raw) {
    if (!raw) return '';
    const live = LIVE_FLAT[raw];
    if (live) return artBase(art) + live;
    return saraRoot(art) + raw;
  }

  function choiceFromManifest(manifest, request) {
    const ask = request || {};
    const key = String(ask.id || ask.stage || '').trim().toLowerCase();
    const stage = Object.prototype.hasOwnProperty.call(SERVER_STAGE, key) ? SERVER_STAGE[key] : '';
    const art = ask.art;
    if (!stage) return { kind: 'flat', url: '', lod: '', flat: '' };
    const row = manifest && manifest.crops && manifest.crops[ask.crop] && manifest.crops[ask.crop][stage];
    if (!row || !row.near || !row.far) return { kind: 'flat', url: '', lod: '', flat: '' };
    const flat = resolveFlat(art, row.fallback2d);
    const root = saraRoot(art);
    const mobile = !!(ask.mobile || ask.flat);
    const limit = Number(ask.lodDistance || LOD_DISTANCE);
    const scale = Number(row.scale || 1);
    if (mobile || Number(ask.distance) > limit) {
      return { kind: 'glb', url: root + row.far, lod: 'far', flat: flat, lazy: mobile, scale: scale };
    }
    return { kind: 'glb', url: root + row.near, lod: 'near', flat: flat, lazy: false, scale: scale };
  }

  function stationFromManifest(manifest, request) {
    const ask = request || {};
    const row = manifest && manifest.stations && manifest.stations[ask.crop] && manifest.stations[ask.crop][ask.id];
    if (!row || !row.glb) return { kind: 'flat', url: '', lod: '', flat: '' };
    const art = ask.art;
    const flat = resolveFlat(art, row.fallback2d);
    const mobile = !!(ask.mobile || ask.flat);
    return {
      kind: 'glb',
      url: saraRoot(art) + row.glb,
      lod: mobile ? 'far' : 'near',
      flat: flat,
      lazy: mobile,
      scale: Number(row.scale || 1),
    };
  }

  return { PHASES, LOD_DISTANCE, SERVER_STAGE, visualFor, choiceFromManifest, stationFromManifest, resolveFlat };
});
