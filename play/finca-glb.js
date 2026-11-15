/* SPDX-License-Identifier: AGPL-3.0-or-later */
// Carga un GLB sólo si el mapa lo nombra y no estamos en el celular. Si falla, queda el dibujo plano.
import { GLTFLoader } from './glb-loader.js?v=sara3d-r1';

const loader = new GLTFLoader();
const cache = new Map();

function loadScene(url) {
  if (!cache.has(url)) {
    cache.set(url, new Promise((ok, ko) => {
      loader.load(url, (gltf) => ok(gltf.scene || gltf), undefined, ko);
    }));
  }
  return cache.get(url);
}

export function placeModel(parent, choice, onFlat, onReady) {
  if (onFlat && typeof onFlat === 'object') {
    onReady = onFlat.onReady;
    onFlat = onFlat.onFlat;
  }
  if (!choice || choice.kind !== 'glb' || !choice.url) {
    if (onFlat) onFlat(choice && (choice.flat || choice.url) || '');
    return;
  }
  const start = () => {
    loadScene(choice.url).then((scene) => {
      const copy = scene.clone(true);
      const scale = Number(choice.scale || 1);
      if (scale !== 1) copy.scale.set(scale, scale, scale);
      parent.add(copy);
      if (onReady) onReady(copy);
    }).catch(() => {
      if (onFlat) onFlat(choice.flat || '');
    });
  };
  if (choice.lazy) {
    if (onFlat) onFlat(choice.flat || '');
    if (typeof requestIdleCallback === 'function') requestIdleCallback(start, { timeout: 1500 });
    else setTimeout(start, 500);
    return;
  }
  start();
}
