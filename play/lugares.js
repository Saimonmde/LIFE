/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Lugares para empezar. Los nombres y las casillas salen del valle que ya existe. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.Lugares = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  function catalog(homes, world) {
    const source = homes || (typeof window !== 'undefined' ? window.HOGARES : null) || { casas: [] };
    const map = world || (typeof window !== 'undefined' ? window.EL_JARDIN : null) || {};
    const points = {};
    const labels = {};
    (map.waypoints || []).forEach(item => { if (item && item.id) points[item.id] = item; });
    (map.mapLabels || []).forEach(item => { if (item && item.id) labels[item.id] = item; });
    const found = [];
    (source.casas || []).forEach(casa => {
      const mark = points[casa.id] || {};
      let name = mark.name || casa.name;
      let x = Number(mark.x != null ? mark.x : casa.x);
      let y = Number(mark.y != null ? mark.y : casa.y);
      if (casa.id === 'envigado') {
        name = 'Parque de Envigado';
        x = Number(casa.x);
        y = Number(casa.y);
      }
      found.push({ id: casa.id, name: name, x: x, y: y, kind: 'parque', municipio: casa.id });
    });
    const park = labels.parque_bolivar;
    if (park) found.push({ id: 'parque_bolivar', name: park.name || 'Parque de Bolívar', x: Number(park.x), y: Number(park.y), kind: 'poi', municipio: 'medellin' });
    const palms = points.las_palmas;
    if (palms) found.push({ id: 'las_palmas', name: 'Las Palmas', x: Number(palms.x), y: Number(palms.y), kind: 'poi', municipio: '' });
    return found;
  }

  function get(id, homes, world) {
    const key = String(id || '').toLowerCase();
    return catalog(homes, world).find(item => item.id === key) || null;
  }

  return { catalog: catalog, get: get };
});
