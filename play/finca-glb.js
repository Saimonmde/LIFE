/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Carga un GLB sólo si el mapa lo nombra y no estamos en el celular. Si falla, queda el dibujo plano.
import { GLTFLoader } from './glb-loader.js?v=fases-r1';

const loader = new GLTFLoader();
const cache = new Map();

export function placeModel(parent, choice, onFlat) {
  if (!choice || choice.kind !== 'glb' || !choice.url) {
    if (onFlat) onFlat(choice && choice.url || choice && choice.flat || '');
    return;
  }
  const hit = cache.get(choice.url);
  if (hit) {
    parent.add(hit.clone ? hit.clone() : hit);
    return;
  }
  loader.load(choice.url, (gltf) => {
    const scene = gltf.scene || gltf;
    cache.set(choice.url, scene);
    parent.add(scene);
  }, undefined, () => {
    if (onFlat) onFlat(choice.flat || '');
  });
}
