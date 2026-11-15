/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Vista previa de cada mascota. Mallas propias, sin modelos de terceros. */
import * as T from './three.module.js';
import { createPet, posePet } from './estilo-jabo.js?v=mascota-r1';

const renderer = new T.WebGLRenderer({ alpha: true, antialias: false });
renderer.setSize(128, 128);
renderer.setClearColor(0x000000, 0);
const scene = new T.Scene();
const camera = new T.PerspectiveCamera(30, 1, 0.1, 20);
camera.position.set(1.7, 1.05, 2.15);
camera.lookAt(0, 0.38, 0);
scene.add(new T.HemisphereLight(0xfff6e4, 0x6a5340, 1.25));
const sun = new T.DirectionalLight(0xfff1c4, 0.85);
sun.position.set(2, 3, 2);
scene.add(sun);
const cache = new Map();

function petFor(spec) {
  const key = [spec.species, spec.breed, spec.variant].join(':');
  let group = cache.get(key);
  if (!group) {
    group = createPet(T, spec);
    cache.set(key, group);
  }
  return group;
}

function frame(time) {
  requestAnimationFrame(frame);
  const cards = document.querySelectorAll('canvas.mascota-preview');
  if (!cards.length) return;
  cards.forEach((canvas) => {
    let spec = null;
    try { spec = JSON.parse(canvas.dataset.pet || ''); } catch (e) { spec = null; }
    if (!spec) return;
    const group = petFor(spec);
    scene.add(group);
    group.rotation.y = time / 1400;
    posePet(group, 'idle', time / 1000);
    renderer.render(scene, camera);
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(renderer.domElement, 0, 0, canvas.width, canvas.height);
    scene.remove(group);
  });
}
requestAnimationFrame(frame);
