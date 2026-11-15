/* SPDX-License-Identifier: AGPL-3.0-or-later */
import { createPet, posePet, createPoste } from './estilo-jabo.js?v=guardar-r1';

const FACE = { up: Math.PI, down: 0, left: -Math.PI / 2, right: Math.PI / 2 };
const POSTE = { x: 108, y: 272 };

function openTiles() {
  const tiles = window.Casa && Casa.petWalk ? Casa.petWalk() : [];
  return tiles.length ? tiles : [[2, 3], [3, 3], [2, 4], [3, 4]];
}
function inside(tiles, x, y) {
  return tiles.some(tile => tile[0] === x && tile[1] === y);
}
function roam(group, time, height) {
  const tiles = openTiles();
  const rig = group.userData;
  if (rig.nx == null || !inside(tiles, rig.nx, rig.ny)) {
    const home = tiles[0];
    rig.tx = rig.nx = home[0];
    rig.ty = rig.ny = home[1];
    rig.depart = time;
    rig.arrive = time;
    rig.next = time + 600;
    rig.dir = 'down';
  }
  if (time >= (rig.next || 0)) {
    const near = tiles.filter(tile => Math.abs(tile[0] - rig.nx) + Math.abs(tile[1] - rig.ny) === 1);
    const pick = near.length ? near[Math.floor(Math.random() * near.length)] : [rig.nx, rig.ny];
    rig.tx = rig.nx;
    rig.ty = rig.ny;
    rig.nx = pick[0];
    rig.ny = pick[1];
    rig.depart = time;
    rig.arrive = time + 780;
    rig.next = time + 1700 + Math.random() * 1400;
    const dx = rig.nx - rig.tx;
    const dy = rig.ny - rig.ty;
    if (dx || dy) rig.dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up');
  }
  const span = Math.max(1, (rig.arrive || time) - (rig.depart || time));
  const u = Math.min(1, Math.max(0, (time - (rig.depart || time)) / span));
  const x = rig.tx + (rig.nx - rig.tx) * u;
  const y = rig.ty + (rig.ny - rig.ty) * u;
  const moving = u > 0 && u < 1 && (rig.nx !== rig.tx || rig.ny !== rig.ty);
  const greetUntil = window.LiveInk && LiveInk.state && LiveInk.state.petGreetUntil;
  const anim = greetUntil && time < greetUntil ? 'greet' : moving ? 'walk' : (Math.floor(time / 9000) % 4 === 0 ? 'lie' : 'idle');
  posePet(group, anim, time / 1000);
  group.position.set(x * 2 + 1, height(x, y), y * 2 + 1);
  group.rotation.y = FACE[rig.dir] || FACE.down;
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
        roam(group, time, ctx.height);
      }
      for (const [id, group] of pets) {
        if (live.has(id)) continue;
        if (group.parent) group.parent.remove(group);
        pets.delete(id);
      }
    },
  };
}
