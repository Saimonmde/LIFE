/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Elige el dibujo de una etapa. En el celular, o si Sara todavía no dejó el GLB, queda el plano de 64 px.
   Cuando el mapa trae glb, el cercano usa ese archivo y el lejano usa lod. */
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
    if (mobile || !item.glb) return { kind: 'flat', url: flat, lod: '' };
    const limit = Number(item.lodDistance || ask.lodDistance || LOD_DISTANCE);
    if (Number(ask.distance) > limit && item.lod) {
      return { kind: 'glb', url: base + item.lod, lod: 'far', flat: flat };
    }
    return { kind: 'glb', url: base + item.glb, lod: 'near', flat: flat };
  }

  return { PHASES, LOD_DISTANCE, visualFor };
});
