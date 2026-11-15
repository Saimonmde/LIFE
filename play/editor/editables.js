/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Registro de tipos editables. Una entrada declara id, etiqueta, icono, parámetros y cómo se ve y se guarda. */
(function (root) {
  'use strict';
  const registry = new Map();

  function register(entry) {
    if (!entry || typeof entry.id !== 'string' || !entry.id) throw new Error('El editable necesita id.');
    if (typeof entry.label !== 'string' || !entry.label) throw new Error('El editable necesita etiqueta.');
    if (typeof entry.icon !== 'string') throw new Error('El editable necesita icono.');
    if (!Array.isArray(entry.params)) throw new Error('El editable necesita parámetros.');
    if (typeof entry.render !== 'function') throw new Error('El editable necesita render.');
    if (typeof entry.serialize !== 'function' || typeof entry.deserialize !== 'function') {
      throw new Error('El editable necesita serialize y deserialize.');
    }
    registry.set(entry.id, entry);
    return entry;
  }

  function get(id) { return registry.get(id) || null; }
  function list(layer) {
    const all = [...registry.values()];
    return layer ? all.filter(entry => entry.layer === layer) : all;
  }
  function clear() { registry.clear(); }

  function serialize(item) {
    const entry = get(item && item.type);
    if (!entry) throw new Error('tipo desconocido: ' + (item && item.type));
    return entry.serialize(item);
  }

  function deserialize(raw) {
    const entry = get(raw && raw.type);
    if (!entry) throw new Error('tipo desconocido: ' + (raw && raw.type));
    return entry.deserialize(raw);
  }

  function propEntry(spec) {
    return register({
      id: spec.id,
      label: spec.label,
      icon: spec.icon,
      layer: spec.layer,
      params: [
        { key: 'scale', type: 'number', min: 0.25, max: 4, step: 0.05 },
        { key: 'rotY', type: 'number', min: 0, max: 360, step: 1 },
      ],
      render: function () { return { parts: spec.parts }; },
      serialize: function (item) {
        return {
          id: String(item.id || ''),
          type: spec.id,
          x: Number(item.x) || 0,
          y: Number(item.y) || 0,
          z: Number(item.z) || 0,
          scale: Number(item.scale) || 1,
          rotY: Number(item.rotY) || 0,
          grounded: item.grounded !== false,
        };
      },
      deserialize: function (raw) {
        return {
          id: String(raw.id || ''),
          type: spec.id,
          x: Number(raw.x) || 0,
          y: Number(raw.y) || 0,
          z: Number(raw.z) || 0,
          scale: Math.max(0.25, Math.min(4, Number(raw.scale) || 1)),
          rotY: ((Number(raw.rotY) || 0) % 360 + 360) % 360,
          grounded: raw.grounded !== false,
        };
      },
    });
  }

  propEntry({
    id: 'palma', label: 'Palma', icon: 'palma', layer: 'vegetation',
    parts: [
      { shape: 'cylinder', rt: 0.07, rb: 0.12, h: 2.6, y: 1.3, seg: 5, color: '#8d6844' },
      { shape: 'box', w: 1.5, h: 0.06, d: 0.22, x: 0.45, y: 2.55, rz: -0.5, color: '#1e6a38' },
      { shape: 'box', w: 1.5, h: 0.06, d: 0.22, x: -0.45, y: 2.55, rz: 0.5, color: '#217543' },
      { shape: 'box', w: 0.22, h: 0.06, d: 1.5, z: 0.45, y: 2.5, rx: 0.5, color: '#176033' },
      { shape: 'box', w: 0.22, h: 0.06, d: 1.5, z: -0.4, y: 2.45, rx: -0.45, color: '#25864a' },
      { shape: 'sphere', r: 0.16, y: 2.35, seg: 6, color: '#d8b15a' },
    ],
  });
  propEntry({
    id: 'guayacan', label: 'Guayacán', icon: 'flor', layer: 'vegetation',
    parts: [
      { shape: 'cylinder', rt: 0.1, rb: 0.16, h: 1.7, y: 0.85, seg: 5, color: '#6b4a2c' },
      { shape: 'ico', r: 0.85, y: 2.15, color: '#2f6a32' },
      { shape: 'ico', r: 0.62, y: 2.45, x: 0.28, color: '#e2c14a' },
      { shape: 'ico', r: 0.4, y: 2.7, x: -0.2, color: '#f0d36a' },
    ],
  });
  propEntry({
    id: 'sombra', label: 'Árbol de sombra', icon: 'arbol', layer: 'vegetation',
    parts: [
      { shape: 'cylinder', rt: 0.12, rb: 0.2, h: 1.8, y: 0.9, seg: 5, color: '#5c4030' },
      { shape: 'ico', r: 1.25, y: 2.35, color: '#2a6238' },
      { shape: 'ico', r: 0.8, y: 2.9, x: 0.35, color: '#347846' },
    ],
  });
  propEntry({
    id: 'arbusto', label: 'Arbusto', icon: 'arbusto', layer: 'vegetation',
    parts: [
      { shape: 'ico', r: 0.48, y: 0.42, color: '#2f6b34' },
      { shape: 'ico', r: 0.32, y: 0.62, x: 0.22, color: '#3d7d40' },
    ],
  });
  propEntry({
    id: 'flores', label: 'Flores', icon: 'flor', layer: 'vegetation',
    parts: [
      { shape: 'cylinder', rt: 0.03, rb: 0.04, h: 0.35, y: 0.18, seg: 4, color: '#3e6a32' },
      { shape: 'sphere', r: 0.12, y: 0.42, x: 0.08, seg: 6, color: '#e07098' },
      { shape: 'sphere', r: 0.1, y: 0.4, x: -0.1, seg: 6, color: '#f0d36a' },
      { shape: 'sphere', r: 0.09, y: 0.48, seg: 6, color: '#f4f0e4' },
    ],
  });
  propEntry({
    id: 'pasto', label: 'Mata de pasto', icon: 'pasto', layer: 'vegetation',
    parts: [
      { shape: 'box', w: 0.06, h: 0.38, d: 0.06, y: 0.19, rz: 0.2, color: '#6a8a3e' },
      { shape: 'box', w: 0.05, h: 0.32, d: 0.05, x: 0.1, y: 0.16, rz: -0.3, color: '#7ea04a' },
      { shape: 'box', w: 0.05, h: 0.28, d: 0.05, x: -0.08, y: 0.14, rz: 0.15, color: '#5e7c38' },
    ],
  });
  propEntry({
    id: 'cafe', label: 'Cafeto', icon: 'cafe', layer: 'vegetation',
    parts: [
      { shape: 'cylinder', rt: 0.05, rb: 0.08, h: 0.9, y: 0.45, seg: 5, color: '#6a4a30' },
      { shape: 'ico', r: 0.42, y: 1.05, color: '#1f6a32' },
      { shape: 'sphere', r: 0.07, y: 0.95, x: 0.18, seg: 5, color: '#b4332a' },
      { shape: 'sphere', r: 0.06, y: 1.15, x: -0.12, z: 0.1, seg: 5, color: '#9a2e28' },
    ],
  });
  propEntry({
    id: 'cacao', label: 'Cacao', icon: 'cacao', layer: 'vegetation',
    parts: [
      { shape: 'cylinder', rt: 0.06, rb: 0.1, h: 1.1, y: 0.55, seg: 5, color: '#5c4030' },
      { shape: 'ico', r: 0.5, y: 1.25, color: '#245c30' },
      { shape: 'sphere', r: 0.1, y: 0.7, x: 0.12, seg: 5, color: '#e0a040' },
      { shape: 'sphere', r: 0.09, y: 0.62, x: -0.1, seg: 5, color: '#c4842c' },
    ],
  });
  propEntry({
    id: 'roca', label: 'Roca', icon: 'roca', layer: 'decoration',
    parts: [
      { shape: 'ico', r: 0.42, y: 0.28, color: '#8e8a80' },
      { shape: 'box', w: 0.36, h: 0.22, d: 0.28, x: 0.18, y: 0.16, color: '#6e6a62' },
    ],
  });
  propEntry({
    id: 'cerca', label: 'Cerca', icon: 'cerca', layer: 'decoration',
    parts: [
      { shape: 'box', w: 0.08, h: 0.7, d: 0.08, x: -0.7, y: 0.35, color: '#6e4a2c' },
      { shape: 'box', w: 0.08, h: 0.7, d: 0.08, x: 0.7, y: 0.35, color: '#6e4a2c' },
      { shape: 'box', w: 1.5, h: 0.08, d: 0.06, y: 0.48, color: '#8a6240' },
      { shape: 'box', w: 1.5, h: 0.08, d: 0.06, y: 0.24, color: '#7a5638' },
    ],
  });
  propEntry({
    id: 'banca', label: 'Banca', icon: 'banca', layer: 'decoration',
    parts: [
      { shape: 'box', w: 1.2, h: 0.08, d: 0.42, y: 0.42, color: '#6e4a2c' },
      { shape: 'box', w: 1.2, h: 0.42, d: 0.08, y: 0.66, z: -0.18, color: '#7d5634' },
      { shape: 'box', w: 0.08, h: 0.4, d: 0.08, x: -0.5, y: 0.2, z: 0.14, color: '#3e4650' },
      { shape: 'box', w: 0.08, h: 0.4, d: 0.08, x: 0.5, y: 0.2, z: 0.14, color: '#3e4650' },
      { shape: 'box', w: 0.08, h: 0.4, d: 0.08, x: -0.5, y: 0.2, z: -0.14, color: '#3e4650' },
      { shape: 'box', w: 0.08, h: 0.4, d: 0.08, x: 0.5, y: 0.2, z: -0.14, color: '#3e4650' },
    ],
  });
  propEntry({
    id: 'farol', label: 'Farola', icon: 'farol', layer: 'decoration',
    parts: [
      { shape: 'cylinder', rt: 0.05, rb: 0.07, h: 2.1, y: 1.05, seg: 6, color: '#3e4650' },
      { shape: 'box', w: 0.28, h: 0.34, d: 0.28, y: 2.2, color: '#f3e2a4' },
      { shape: 'box', w: 0.34, h: 0.06, d: 0.34, y: 2.4, color: '#2c3238' },
    ],
  });
  propEntry({
    id: 'letrero', label: 'Letrero', icon: 'letrero', layer: 'decoration',
    parts: [
      { shape: 'cylinder', rt: 0.05, rb: 0.06, h: 1.5, y: 0.75, seg: 5, color: '#5c4030' },
      { shape: 'box', w: 0.9, h: 0.42, d: 0.06, y: 1.45, color: '#3a2412' },
      { shape: 'box', w: 0.78, h: 0.28, d: 0.02, y: 1.45, z: 0.04, color: '#e2b23c' },
    ],
  });
  propEntry({
    id: 'fuente', label: 'Fuente', icon: 'fuente', layer: 'decoration',
    parts: [
      { shape: 'cylinder', rt: 0.7, rb: 0.75, h: 0.28, y: 0.2, seg: 8, color: '#d9d3c7' },
      { shape: 'cylinder', rt: 0.5, rb: 0.5, h: 0.12, y: 0.32, seg: 8, color: '#6aa4b0' },
      { shape: 'cylinder', rt: 0.08, rb: 0.1, h: 0.55, y: 0.55, seg: 5, color: '#c8c2b6' },
    ],
  });

  function pathEntry(id, label, icon) {
    return register({
      id: id,
      label: label,
      icon: icon,
      layer: 'path',
      params: [{ key: 'style', type: 'enum', options: ['piedra', 'adoquin', 'carretera'] }],
      render: function () { return { kind: 'path', style: id.replace('path:', '') }; },
      serialize: function (item) {
        return { id: item.x + ':' + item.z, type: id, style: id.replace('path:', ''), x: item.x | 0, z: item.z | 0 };
      },
      deserialize: function (raw) {
        return { id: (raw.x | 0) + ':' + (raw.z | 0), type: id, style: id.replace('path:', ''), x: raw.x | 0, z: raw.z | 0 };
      },
    });
  }
  pathEntry('path:piedra', 'Camino de piedra', 'piedra');
  pathEntry('path:adoquin', 'Adoquín', 'adoquin');
  pathEntry('path:carretera', 'Carretera', 'carretera');

  register({
    id: 'surface',
    label: 'Superficie',
    icon: 'superficie',
    layer: 'surface',
    params: [
      { key: 'material', type: 'enum', options: ['grass', 'dirt', 'sand', 'stone', 'brick', 'asphalt', 'water'] },
      { key: 'tint', type: 'color' },
    ],
    render: function (item) { return { kind: 'surface', material: item && item.material, tint: item && item.tint }; },
    serialize: function (item) {
      return { id: item.x + ':' + item.z, type: 'surface', x: item.x | 0, z: item.z | 0, material: item.material, tint: item.tint };
    },
    deserialize: function (raw) {
      return { id: (raw.x | 0) + ':' + (raw.z | 0), type: 'surface', x: raw.x | 0, z: raw.z | 0, material: raw.material, tint: raw.tint || '#74875b' };
    },
  });

  register({
    id: 'terrain',
    label: 'Terreno',
    icon: 'terreno',
    layer: 'terrain',
    params: [
      { key: 'dy', type: 'number', min: -12, max: 12, step: 0.25 },
    ],
    render: function (item) { return { kind: 'terrain', dy: item && item.dy }; },
    serialize: function (item) { return { type: 'terrain', x: item.x | 0, z: item.z | 0, dy: Number(item.dy) || 0 }; },
    deserialize: function (raw) { return { type: 'terrain', x: raw.x | 0, z: raw.z | 0, dy: Number(raw.dy) || 0 }; },
  });

  register({
    id: 'object',
    label: 'Objeto del mapa',
    icon: 'objeto',
    layer: 'object',
    params: [
      { key: 'scale', type: 'number', min: 0.25, max: 4, step: 0.05 },
      { key: 'rotY', type: 'number', min: 0, max: 360, step: 15 },
    ],
    render: function () { return { kind: 'object' }; },
    serialize: function (item) {
      return {
        id: String(item.id || ''), type: 'object',
        x: Number(item.x) || 0, y: Number(item.y) || 0, z: Number(item.z) || 0,
        scale: Number(item.scale) || 1, rotY: Number(item.rotY) || 0, deleted: !!item.deleted,
      };
    },
    deserialize: function (raw) {
      const item = {
        id: String(raw.id || ''), type: 'object',
        x: Number(raw.x) || 0, y: Number(raw.y) || 0, z: Number(raw.z) || 0,
        scale: Math.max(0.25, Math.min(4, Number(raw.scale) || 1)),
        rotY: ((Number(raw.rotY) || 0) % 360 + 360) % 360,
        deleted: !!raw.deleted,
      };
      if (!item.id) throw new Error('El objeto necesita id.');
      return item;
    },
  });

  root.Editables = { register, get, list, clear, serialize, deserialize };
})(typeof globalThis !== 'undefined' ? globalThis : this);
