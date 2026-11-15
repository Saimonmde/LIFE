/* SPDX-License-Identifier: AGPL-3.0-or-later */
import { createPet, posePet, createPoste } from './estilo-jabo.js?v=mascota-r1';

const FACE = { up: Math.PI, down: 0, left: -Math.PI / 2, right: Math.PI / 2 };
const POSTE = { x: 108, y: 272 };

function waitAtHome(group, time, height) {
  const x = 2.6;
  const y = 3.4;
  group.position.set(x * 2 + 1, height(x, y), y * 2 + 1);
  group.rotation.y = FACE.down;
  const until = window.LiveInk && LiveInk.state && LiveInk.state.petGreetUntil;
  const greet = until && time < until;
  posePet(group, greet ? 'greet' : 'idle', time / 1000);
}

export function attachVida(T, ctx) {
  const pets = new Map();
  const poste = createPoste(T, ctx.material);
  poste.position.set(POSTE.x * 2 + 1, ctx.height(POSTE.x, POSTE.y), POSTE.y * 2 + 1);
  ctx.scene.add(poste);
  poste.traverse(mesh => { if (mesh.userData && mesh.userData.poste) ctx.pick.push(mesh); });

  function ensure(id, spec) {
    const key = [spec.species, spec.breed, spec.variant].join(':');
    let group = pets.get(id);
    if (!group || group.userData.key !== key) {
      if (group && group.parent) group.parent.remove(group);
      group = createPet(T, spec);
      group.userData.key = key;
      pets.set(id, group);
    }
    return group;
  }

  return {
    sync(S, _api, view, away, time) {
      const live = new Set();
      const mine = S.pet;
      const home = (S && window.LiveInk && LiveInk.world && LiveInk.world.mapId) === 'casa';
      if (home && mine && mine.species && mine.breed) {
        live.add('self');
        const group = ensure('self', mine);
        if (group.parent !== view) view.add(group);
        waitAtHome(group, time, ctx.height);
      }
      for (const [id, group] of pets) {
        if (live.has(id)) continue;
        if (group.parent) group.parent.remove(group);
        pets.delete(id);
      }
    },
  };
}
