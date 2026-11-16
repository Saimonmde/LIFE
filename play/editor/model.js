/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Estado local del editor: pincel, deshacer y la forma que el servidor vuelve a leer. */
(function (root) {
  'use strict';
  const STYLES = ['piedra', 'adoquin', 'carretera'];
  const MATERIALS = ['grass', 'dirt', 'sand', 'stone', 'brick', 'asphalt', 'water'];
  const SCALE_MIN = 0.25;
  const SCALE_MAX = 4;

  function clone(value) { return JSON.parse(JSON.stringify(value)); }

  function emptyCurrent() {
    return { paths: [], objects: [], props: [], terrain: [], surfaces: [] };
  }

  function newId(prefix) {
    return String(prefix || 'v') + Math.random().toString(36).slice(2, 8);
  }

  function clamp(value, lo, hi) { return Math.max(lo, Math.min(hi, value)); }

  function brushCells(x, z, size, bounds) {
    const n = size === 5 ? 5 : size === 3 ? 3 : 1;
    const radius = (n - 1) / 2;
    const cells = [];
    for (let dz = -radius; dz <= radius; dz += 1) {
      for (let dx = -radius; dx <= radius; dx += 1) {
        const cx = (x | 0) + dx;
        const cz = (z | 0) + dz;
        if (bounds && (cx < bounds.minX || cz < bounds.minZ || cx > bounds.maxX || cz > bounds.maxZ)) continue;
        if (cx < 0 || cz < 0 || cx > 4096 || cz > 4096) continue;
        cells.push({ x: cx, z: cz });
      }
    }
    return cells;
  }

  function key(x, z) { return x + ':' + z; }

  function paintPaths(current, cells, style) {
    if (STYLES.indexOf(style) < 0) throw new Error('estilo de camino desconocido');
    const next = clone(current);
    const map = new Map(next.paths.map(item => [key(item.x, item.z), item]));
    cells.forEach(cell => {
      map.set(key(cell.x, cell.z), { id: key(cell.x, cell.z), style: style, x: cell.x | 0, z: cell.z | 0 });
    });
    next.paths = [...map.values()];
    return next;
  }

  function erasePaths(current, cells) {
    const drop = new Set(cells.map(cell => key(cell.x, cell.z)));
    const next = clone(current);
    next.paths = next.paths.filter(item => !drop.has(key(item.x, item.z)));
    return next;
  }

  function movePaths(current, cells, dx, dz) {
    const drop = new Set(cells.map(cell => key(cell.x, cell.z)));
    const moving = current.paths.filter(item => drop.has(key(item.x, item.z)));
    const next = clone(current);
    next.paths = next.paths.filter(item => !drop.has(key(item.x, item.z)));
    const map = new Map(next.paths.map(item => [key(item.x, item.z), item]));
    moving.forEach(item => {
      const x = item.x + (dx | 0);
      const z = item.z + (dz | 0);
      if (x < 0 || z < 0 || x > 4096 || z > 4096) return;
      map.set(key(x, z), { id: key(x, z), style: item.style, x: x, z: z });
    });
    next.paths = [...map.values()];
    return next;
  }

  function paintSurfaces(current, cells, material, tint) {
    if (MATERIALS.indexOf(material) < 0) throw new Error('material desconocido');
    const color = /^#[0-9a-fA-F]{6}$/.test(tint || '') ? tint.toLowerCase() : '#74875b';
    const next = clone(current);
    const map = new Map(next.surfaces.map(item => [key(item.x, item.z), item]));
    cells.forEach(cell => {
      map.set(key(cell.x, cell.z), { id: key(cell.x, cell.z), x: cell.x | 0, z: cell.z | 0, material: material, tint: color });
    });
    next.surfaces = [...map.values()];
    return next;
  }

  function eraseSurfaces(current, cells) {
    const drop = new Set(cells.map(cell => key(cell.x, cell.z)));
    const next = clone(current);
    next.surfaces = next.surfaces.filter(item => !drop.has(key(item.x, item.z)));
    return next;
  }

  function placeProps(current, props) {
    const next = clone(current);
    props.forEach(prop => {
      const saved = root.Editables.serialize(prop);
      const back = root.Editables.deserialize(saved);
      if (!back.id) back.id = newId('v');
      next.props.push(back);
    });
    return next;
  }

  function updateProps(current, ids, patch) {
    const want = new Set(ids);
    const next = clone(current);
    next.props = next.props.map(prop => {
      if (!want.has(prop.id)) return prop;
      const merged = Object.assign({}, prop, patch);
      if (patch.scale != null) merged.scale = clamp(Number(patch.scale) || 1, SCALE_MIN, SCALE_MAX);
      if (patch.rotY != null) merged.rotY = ((Number(patch.rotY) || 0) % 360 + 360) % 360;
      return root.Editables.deserialize(root.Editables.serialize(merged));
    });
    return next;
  }

  function removeProps(current, ids) {
    const want = new Set(ids);
    const next = clone(current);
    next.props = next.props.filter(prop => !want.has(prop.id));
    return next;
  }

  function moveProps(current, ids, dx, dy, dz) {
    const want = new Set(ids);
    const next = clone(current);
    next.props = next.props.map(prop => {
      if (!want.has(prop.id)) return prop;
      return Object.assign({}, prop, {
        x: Math.round((prop.x + dx) * 1000) / 1000,
        y: Math.round((prop.y + dy) * 1000) / 1000,
        z: Math.round((prop.z + dz) * 1000) / 1000,
        grounded: dy !== 0 ? false : prop.grounded,
      });
    });
    return next;
  }

  function upsertObjects(current, items) {
    const next = clone(current);
    items.forEach(item => {
      const saved = root.Editables.deserialize(root.Editables.serialize(Object.assign({ type: 'object' }, item)));
      const index = next.objects.findIndex(obj => obj.id === saved.id);
      const row = {
        id: saved.id, x: saved.x, y: saved.y, z: saved.z,
        scale: saved.scale, rotY: saved.rotY, deleted: !!item.deleted,
      };
      if (index >= 0) next.objects[index] = row;
      else next.objects.push(row);
    });
    return next;
  }

  function terrainApply(current, cells, mode, strength, baseAt) {
    const next = clone(current);
    const map = new Map(next.terrain.map(item => [key(item.x, item.z), item.dy]));
    const total = (x, z) => (baseAt ? Number(baseAt(x, z)) || 0 : 0) + (map.get(key(x, z)) || 0);
    const list = cells.map(cell => ({ x: cell.x | 0, z: cell.z | 0 }));
    const power = clamp(Number(strength) || 1, 0.1, 4);
    if (mode === 'erase') {
      list.forEach(cell => map.delete(key(cell.x, cell.z)));
    } else if (mode === 'flatten' && list.length) {
      const center = list[Math.floor(list.length / 2)];
      const target = total(center.x, center.z);
      list.forEach(cell => {
        const base = baseAt ? Number(baseAt(cell.x, cell.z)) || 0 : 0;
        map.set(key(cell.x, cell.z), clamp(target - base, -12, 12));
      });
    } else if (mode === 'smooth') {
      const updates = list.map(cell => {
        let sum = 0;
        let count = 0;
        for (let dz = -1; dz <= 1; dz += 1) {
          for (let dx = -1; dx <= 1; dx += 1) {
            sum += total(cell.x + dx, cell.z + dz);
            count += 1;
          }
        }
        const base = baseAt ? Number(baseAt(cell.x, cell.z)) || 0 : 0;
        const blended = total(cell.x, cell.z) * (1 - Math.min(1, power)) + (sum / count) * Math.min(1, power);
        return [cell, clamp(blended - base, -12, 12)];
      });
      updates.forEach(([cell, dy]) => map.set(key(cell.x, cell.z), dy));
    } else {
      const dir = mode === 'lower' ? -1 : 1;
      list.forEach(cell => {
        map.set(key(cell.x, cell.z), clamp((map.get(key(cell.x, cell.z)) || 0) + dir * power, -12, 12));
      });
    }
    next.terrain = [...map.entries()].filter(([, dy]) => Math.abs(dy) >= 0.001).map(([id, dy]) => {
      const parts = id.split(':');
      return { x: Number(parts[0]), z: Number(parts[1]), dy: Math.round(dy * 1000) / 1000 };
    });
    return next;
  }

  function scatter(cx, cz, brush, density, type, rng) {
    const random = rng || Math.random;
    const count = clamp(density | 0, 1, 8);
    const reach = Math.max(0.2, ((brush === 5 ? 5 : brush === 3 ? 3 : 1) - 1) / 2);
    const props = [];
    for (let i = 0; i < count; i += 1) {
      const angle = random() * Math.PI * 2;
      const radius = count === 1 ? 0 : random() * reach;
      const x = cx + Math.cos(angle) * radius;
      const z = cz + Math.sin(angle) * radius;
      props.push({
        id: newId('v'),
        type: type,
        x: Math.round((x * 2 + 1) * 1000) / 1000,
        y: 0,
        z: Math.round((z * 2 + 1) * 1000) / 1000,
        scale: Math.round((0.85 + random() * 0.35) * 1000) / 1000,
        rotY: Math.round(random() * 360),
        grounded: true,
      });
    }
    return props;
  }

  function session(current) {
    let present = clone(current || emptyCurrent());
    const past = [];
    const future = [];
    let mark = null;
    return {
      get current() { return present; },
      begin() { if (!mark) mark = clone(present); },
      preview(next) { present = next; },
      end() {
        if (!mark) return false;
        const changed = JSON.stringify(mark) !== JSON.stringify(present);
        if (changed) {
          past.push(mark);
          if (past.length > 50) past.shift();
          future.length = 0;
        }
        mark = null;
        return changed;
      },
      cancel() { if (mark) present = mark; mark = null; },
      commit(next) { this.begin(); this.preview(next); return this.end(); },
      undo() {
        if (!past.length) return false;
        future.push(clone(present));
        present = past.pop();
        return true;
      },
      redo() {
        if (!future.length) return false;
        past.push(clone(present));
        present = future.pop();
        return true;
      },
      canUndo() { return past.length > 0; },
      canRedo() { return future.length > 0; },
      load(next) {
        present = clone(next || emptyCurrent());
        past.length = 0;
        future.length = 0;
        mark = null;
      },
    };
  }

  root.EditorModel = {
    STYLES, MATERIALS, SCALE_MIN, SCALE_MAX,
    clone, emptyCurrent, newId, brushCells,
    paintPaths, erasePaths, movePaths,
    paintSurfaces, eraseSurfaces,
    placeProps, updateProps, removeProps, moveProps, upsertObjects,
    terrainApply, scatter, session,
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
