/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Skate Park La 4 Sur. Las rampas están en metros para poder reemplazarlas con el escaneo.
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
    license: 'OpenStreetMap, ODbL',
    note: 'OSM no trae un polígono: el parque es el nodo 11683484732. El área de 1771 m² es la cifra publicada, no un contorno medido en el mapa.',
  },
  scale: { playMetersPerTile: 2, valleyTilesPerKm: 7.2, valleyMetersPerTile: 138.89 },
  placement: {
    x: 92, y: 210, w: 14, h: 10,
    meters: [28, 20],
    targetTile: [107, 239],
    reason: 'A 7.2 casillas por km el nodo cae junto al río, entre Itagüí y Envigado, donde el piso plano mide unos 14 m. La pista jugable queda en el pasto plano de al lado, al norte de Itagüí, y el camino del valle llega a pie desde el Parque de Envigado.',
  },
  speed: 1.9,
  ramps: [
    { id: 'quarter_norte', kind: 'quarter', x: 0, z: -6.2, length: 8, radius: 1.45, yaw: 0 },
    { id: 'quarter_sur', kind: 'quarter', x: 0, z: 6.2, length: 8, radius: 1.45, yaw: 3.1416 },
    { id: 'funbox', kind: 'funbox', x: 5.2, z: 0, w: 3.4, d: 3.2, h: 0.55 },
    { id: 'riel', kind: 'rail', x: -5.4, z: 0, length: 6.2, h: 0.42 },
    { id: 'borde', kind: 'ledge', x: 1.2, z: 3.2, w: 3.6, d: 0.46, h: 0.32 },
  ],
};
