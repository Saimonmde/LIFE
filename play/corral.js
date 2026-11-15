/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Corral del jugador: gallos y gallinas. La guacharaca no entra. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.Corral = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const SPECIES = {
    gallo: ['dorado', 'negro', 'blanco', 'rojo'],
    gallina: ['blanca', 'pinta', 'negra', 'dorada'],
  };
  const CAP = 8;
  let data = { v: 1, animals: [], caught: [] };

  function catchable(species) {
    return Object.prototype.hasOwnProperty.call(SPECIES, String(species || ''));
  }
  function sellable(species) {
    return catchable(species);
  }
  function killable() {
    return false;
  }
  function bounds(house, place) {
    if (place === 'finca') return { place: 'finca', x: 148, y: 209, w: 4, h: 3 };
    const x = house && Number.isFinite(house.x) ? house.x + 2 : 0;
    const y = house && Number.isFinite(house.y) ? house.y + 1 : 0;
    return { place: 'patio', x: x, y: y, w: 4, h: 3 };
  }
  function apply(raw) {
    const animals = [];
    const seen = {};
    const rows = raw && raw.animals || [];
    for (const row of rows) {
      if (!row || animals.length >= CAP || !catchable(row.species)) continue;
      let id = String(row.id || '');
      if (!id || seen[id]) id = row.species + '-' + (animals.length + 1);
      seen[id] = true;
      const colors = SPECIES[row.species];
      animals.push({
        id: id,
        species: row.species,
        color: colors.indexOf(row.color) >= 0 ? row.color : colors[0],
        place: row.place === 'finca' ? 'finca' : 'patio',
        fx: Number(row.fx) || 0,
        fy: Number(row.fy) || 0,
        goalX: Number(row.goalX) || 0,
        goalY: Number(row.goalY) || 0,
        mode: 'walk',
      });
    }
    const caught = [];
    for (const item of (raw && raw.caught) || []) {
      const id = String(item || '');
      if (id && caught.indexOf(id) < 0 && caught.length < 40) caught.push(id);
    }
    data = { v: 1, animals: animals, caught: caught };
    return data;
  }
  function snapshot() {
    return {
      v: 1,
      animals: data.animals.map(function (animal) {
        return { id: animal.id, species: animal.species, color: animal.color, place: animal.place };
      }),
      caught: data.caught.slice(),
    };
  }
  function catchWorld(bird) {
    const species = bird && (bird.species || 'gallo');
    if (!catchable(species)) return { ok: false, meat: 0, reason: 'protegida' };
    if (bird && bird.id && data.caught.indexOf(bird.id) >= 0) return { ok: false, meat: 0, reason: 'ya' };
    if (data.animals.length >= CAP) return { ok: false, meat: 0, reason: 'lleno' };
    const colors = SPECIES[species];
    const animal = {
      id: species + '-' + (data.animals.length + 1),
      species: species,
      color: colors[(bird && bird.x || data.animals.length) % colors.length],
      place: 'patio',
      fx: 0, fy: 0, goalX: 0, goalY: 0, mode: 'walk',
    };
    data.animals.push(animal);
    if (bird && bird.id) data.caught.push(bird.id);
    return { ok: true, meat: 0, animal: animal };
  }
  function kill() {
    return { ok: false, meat: 0, reason: 'no se puede matar' };
  }
  function takeOut(id) {
    const next = [];
    let found = null;
    for (const animal of data.animals) {
      if (!found && animal.id === id) found = animal;
      else next.push(animal);
    }
    if (!found) return null;
    data.animals = next;
    return found;
  }
  function step(animal, box, dt) {
    if (!animal.goalX) {
      animal.goalX = box.x + 0.6 + ((animal.id.length) % Math.max(1, box.w - 1));
      animal.goalY = box.y + 0.6;
    }
    const dx = animal.goalX - (animal.fx || box.x + 0.5);
    const dy = animal.goalY - (animal.fy || box.y + 0.5);
    const dist = Math.hypot(dx, dy);
    if (dist < 0.2) {
      animal.goalX = box.x + 0.4 + ((animal.turns = (animal.turns || 0) + 1) % Math.max(1, box.w - 1));
      animal.goalY = box.y + 0.4 + (animal.turns % Math.max(1, box.h - 1));
      animal.mode = animal.turns % 3 === 0 ? 'peck' : 'walk';
    } else {
      const hop = Math.min(dist, 0.55 * dt);
      animal.fx = (animal.fx || box.x + 0.5) + dx / dist * hop;
      animal.fy = (animal.fy || box.y + 0.5) + dy / dist * hop;
      animal.mode = 'walk';
    }
    const loX = box.x + 0.15;
    const hiX = box.x + box.w - 0.15;
    const loY = box.y + 0.15;
    const hiY = box.y + box.h - 0.15;
    animal.fx = Math.min(hiX, Math.max(loX, animal.fx));
    animal.fy = Math.min(hiY, Math.max(loY, animal.fy));
    return animal;
  }
  function tick(dt, house) {
    for (const animal of data.animals) step(animal, bounds(house, animal.place), dt);
    return data.animals;
  }
  return {
    SPECIES: SPECIES,
    CAP: CAP,
    catchable: catchable,
    sellable: sellable,
    killable: killable,
    bounds: bounds,
    apply: apply,
    snapshot: snapshot,
    catchWorld: catchWorld,
    kill: kill,
    takeOut: takeOut,
    step: step,
    tick: tick,
    animals: function () { return data.animals; },
    caught: function () { return data.caught; },
  };
});
