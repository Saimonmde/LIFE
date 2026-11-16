/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Skate Park La 4 Sur. Las rampas están en metros, medidas del escaneo, con arte original.
window.SKATE_4_SUR = {
  id: 'skate_4_sur',
  name: 'Skate Park La 4 Sur',
  osm: {
    node: 11683484732,
    way: null,
    name: 'Skate Park La 4 Sur',
    lat: 6.2041874,
    lon: -75.5802401,
    leisure: 'pitch',
    sport: 'skateboard',
    surface: 'concrete',
    covered: 'yes',
    areaPublished_m2: 1771,
    license: '© OpenStreetMap contributors, ODbL',
    attribution: '© OpenStreetMap contributors, ODbL',
    note: 'OSM no trae un polígono: el parque es sólo el nodo 11683484732. El área de 1771 m² es la cifra publicada, no un contorno medido. El rectángulo jugable de 28×20 m es una estimación, no una medida de OpenStreetMap.',
  },
  scale: { playMetersPerTile: 2, valleyTilesPerKm: 7.2, valleyMetersPerTile: 138.89 },
  placement: {
    x: 92, y: 210, w: 14, h: 10,
    meters: [28, 20],
    metersAreEstimate: true,
    targetTile: [107, 239],
    reason: 'A 7.2 casillas por km el nodo 11683484732 cae junto al río, entre Itagüí y Envigado, donde el piso plano mide unos 14 m. La pista jugable de 28×20 m es una estimación: OSM no tiene el polígono. Queda en el pasto plano al norte de Itagüí, y el camino del valle llega a pie desde el Parque de Envigado.',
  },
  speed: 1.9,
  // Origen en el centro de la pista (casilla 99, 215). x sigue el eje largo del escaneo. +z mira hacia el puente.
  ramps: [
    { id: 'landing', kind: 'funbox', x: -0.86, z: 2.78, w: 5.73, d: 4.76, h: 0.58, wall: '-z' },
    { id: 'funbox_largo', kind: 'funbox', x: 6.69, z: 4.19, w: 9.37, d: 1.95, h: 0.52, coping: 'long' },
    { id: 'riel_verde', kind: 'rail', x: 3.72, z: -2.34, length: 5.1, h: 0.47, color: 'green' },
    { id: 'borde_sur', kind: 'rail', x: -9.75, z: -0.81, length: 2.9, h: 0.36, yaw: 0.34 },
  ],
  polycam: {
    captureId: '99FE1721-02A4-44A9-B82A-887ECEA51C9A',
    url: 'https://poly.cam/capture/99FE1721-02A4-44A9-B82A-887ECEA51C9A',
    date: '2026-11-13',
    type: 'LiDAR',
    usedAsTexture: false,
    author: 'Jay (Saimon888)',
    note: 'El AABB del escaneo mide 10.33×25.46 m y la malla cubre unos 68 m². Sólo cubre una parte del parque. Las fotos del escaneo no entran al juego.',
  },
};
