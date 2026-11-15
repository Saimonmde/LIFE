/* SPDX-License-Identifier: AGPL-3.0-or-later */
import { createPet, posePet, createPoste } from './estilo-jabo.js?v=vida-r1';

const FACE = { up: Math.PI, down: 0, left: -Math.PI / 2, right: Math.PI / 2 };
const POSTE = { x: 108, y: 272 };

function follow(group, leader, home, time, height) {
  const back = { up: [0, 1], down: [0, -1], left: [1, 0], right: [-1, 0] }[leader.dir] || [0, 1];
  const goalX = home ? 3.2 : leader.fx + back[0] * 1.15;
  const goalY = home ? 5.4 : leader.fy + back[1] * 1.15;
  if (group.userData.fx == null) {
    group.userData.fx = goalX;
    group.userData.fy = goalY;
  }
  group.userData.fx += (goalX - group.userData.fx) * .12;
  group.userData.fy += (goalY - group.userData.fy) * .12;
  const dist = Math.hypot(goalX - group.userData.fx, goalY - group.userData.fy);
  const moving = dist > .08 || !!leader.moving;
  posePet(group, moving ? 'walk' : home ? 'lie' : 'idle', time / 1000);
  const x = group.userData.fx;
  const y = group.userData.fy;
  group.position.set(x * 2 + 1, height(x, y), y * 2 + 1);
  group.rotation.y = FACE[leader.dir] || 0;
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
      if (mine && mine.species && mine.breed) {
        live.add('self');
        const group = ensure('self', mine);
        if (group.parent !== view) view.add(group);
        follow(group, S.player, home, time, ctx.height);
      }
      if (!away) {
        for (const [id, other] of S.others || []) {
          if (!other.pet || !other.pet.species) continue;
          const pid = 'p' + id;
          live.add(pid);
          const group = ensure(pid, other.pet);
          if (group.parent !== ctx.scene) ctx.scene.add(group);
          follow(group, { fx: other.fx, fy: other.fy, dir: other.dir, moving: !!other.moving }, false, time, ctx.height);
        }
      }
      for (const [id, group] of pets) {
        if (live.has(id)) continue;
        if (group.parent) group.parent.remove(group);
        pets.delete(id);
      }
    },
  };
}
