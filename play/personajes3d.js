/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Personajes, oficios, fauna y mascotas en bloques. El mundo visible usa esto. */
import * as T from './three.module.js';

export const OFICIOS = ['explorador', 'comerciante', 'artesano', 'inmobiliario', 'guardian'];

const mats = new Map();
function mat(color) {
  const key = String(color || '#888').toLowerCase();
  if (!mats.has(key)) mats.set(key, new T.MeshLambertMaterial({ color: key, flatShading: true }));
  return mats.get(key);
}
const box = new T.BoxGeometry(1, 1, 1);
const geo = new Map();
function unit(kind) {
  if (!geo.has(kind)) {
    geo.set(kind, kind === 'cyl' ? new T.CylinderGeometry(1, 1, 1, 8) : kind === 'sph' ? new T.SphereGeometry(1, 8, 6) : box);
  }
  return geo.get(kind);
}
function mesh(parent, kind, color, x, y, z, sx, sy, sz) {
  const m = new T.Mesh(unit(kind), mat(color));
  m.position.set(x, y, z);
  m.scale.set(sx, sy, sz);
  m.castShadow = m.receiveShadow = true;
  parent.add(m);
  return m;
}
function pivote(parent, x, y, z) {
  const g = new T.Group();
  g.position.set(x, y, z);
  parent.add(g);
  return g;
}
function miembro(parent, x, y, z, sx, sy, sz, color) {
  const p = pivote(parent, x, y, z);
  const m = mesh(p, 'box', color, 0, -sy / 2, 0, sx, sy, sz);
  m.castShadow = true;
  return p;
}

const PIEL = '#e0b08a';
const PELO = {
  explorador: '#3a2a1c', comerciante: '#2a2118', artesano: '#1c1a18', inmobiliario: '#2c241c',
  guardian: '#3d2918', profesora: '#2a211c', capataz: '#4a3424', banquero: '#d8d2c6', vecino: '#3a2a1c',
};
const TRAJE = {
  explorador: '#6b8f71', comerciante: '#7a3030', artesano: '#4a4e55', inmobiliario: '#1e3a5f',
  guardian: '#8e2f2f', profesora: '#3d7f8c', capataz: '#ab8338', banquero: '#c4553a', vecino: '#467eb1',
};

function sombrero(head, color, ala) {
  mesh(head, 'cyl', color, 0, 0.34, 0, 0.28, 0.16, 0.28);
  mesh(head, 'cyl', color, 0, 0.24, 0, ala, 0.05, ala);
}
function extras(torso, head, brazos, kind, tint) {
  const traje = TRAJE[kind] || tint || '#467eb1';
  if (kind === 'explorador') {
    sombrero(head, '#6b4a2a', 0.62);
    mesh(torso, 'box', '#c4a574', 0, 0.35, 0.02, 0.78, 0.55, 0.4);
    mesh(torso, 'box', '#5a3b24', 0.32, 0.15, 0.22, 0.22, 0.28, 0.16);
    mesh(brazos.der, 'box', '#6b4228', 0, -0.55, 0.12, 0.08, 0.42, 0.08);
  } else if (kind === 'comerciante') {
    sombrero(head, '#e6c878', 0.58);
    mesh(torso, 'box', '#f3efe4', 0, 0.42, 0.04, 0.5, 0.35, 0.28);
    mesh(torso, 'box', traje, 0, 0.22, 0.06, 0.72, 0.42, 0.34);
    mesh(torso, 'box', '#e2b23c', -0.22, 0.12, 0.24, 0.16, 0.16, 0.1);
  } else if (kind === 'artesano') {
    mesh(torso, 'box', '#6b3e2a', 0, 0.28, 0.08, 0.7, 0.62, 0.28);
    mesh(brazos.der, 'box', '#9aa3a8', 0.12, -0.42, 0.1, 0.28, 0.12, 0.12);
    mesh(brazos.der, 'box', '#5a3b24', 0, -0.62, 0.08, 0.08, 0.36, 0.08);
    mesh(head, 'box', '#2a211c', 0, 0.02, 0.22, 0.28, 0.06, 0.06);
  } else if (kind === 'inmobiliario') {
    mesh(torso, 'box', '#f7f3ea', 0, 0.48, 0.05, 0.42, 0.28, 0.26);
    mesh(torso, 'box', '#e2b23c', 0, 0.42, 0.16, 0.08, 0.28, 0.04);
    mesh(brazos.izq, 'box', '#f4efe2', 0, -0.35, 0.12, 0.22, 0.28, 0.04);
    mesh(torso, 'box', '#e2b23c', 0.22, 0.2, 0.22, 0.08, 0.08, 0.04);
  } else if (kind === 'guardian') {
    sombrero(head, '#3d2918', 0.55);
    mesh(torso, 'box', '#f3e6c0', 0, 0.38, 0.05, 0.62, 0.12, 0.36);
    mesh(torso, 'box', '#1c1a18', 0.28, 0.05, 0.2, 0.22, 0.18, 0.12);
    mesh(brazos.izq, 'box', '#e2b23c', 0, -0.48, 0.1, 0.1, 0.16, 0.1);
  } else if (kind === 'profesora') {
    mesh(head, 'box', PELO.profesora, 0, 0.32, -0.04, 0.28, 0.22, 0.28);
    mesh(torso, 'box', traje, 0, 0.05, 0, 0.7, 0.85, 0.4);
    mesh(brazos.izq, 'box', '#f4efe2', 0.08, -0.32, 0.12, 0.22, 0.06, 0.16);
    mesh(brazos.izq, 'box', '#6d2d32', 0.08, -0.4, 0.12, 0.2, 0.05, 0.14);
  } else if (kind === 'capataz') {
    sombrero(head, '#c4a574', 0.66);
    mesh(torso, 'box', '#5a3b24', 0, 0.32, 0.06, 0.68, 0.4, 0.3);
    mesh(head, 'box', '#4a3424', 0, -0.02, 0.22, 0.22, 0.06, 0.06);
  } else if (kind === 'banquero') {
    mesh(head, 'box', '#20242a', -0.12, 0.08, 0.22, 0.16, 0.05, 0.04);
    mesh(head, 'box', '#20242a', 0.12, 0.08, 0.22, 0.16, 0.05, 0.04);
    mesh(torso, 'box', '#f7f3ea', 0, 0.45, 0.05, 0.46, 0.28, 0.26);
    mesh(torso, 'box', '#e2b23c', 0, 0.38, 0.16, 0.08, 0.22, 0.04);
  } else {
    mesh(torso, 'box', tint || traje, 0, 0.32, 0.04, 0.62, 0.28, 0.32);
  }
  if (OFICIOS.includes(kind) && tint) mesh(torso, 'box', tint, 0, 0.08, 0.2, 0.55, 0.08, 0.06);
}

export function crear(spec) {
  const kind = spec && spec.kind || 'explorador';
  const tint = spec && spec.tint || TRAJE[kind] || '#467eb1';
  const traje = kind === 'vecino' ? tint : (TRAJE[kind] || tint);
  const root = new T.Group();
  const bob = new T.Group();
  root.add(bob);
  const legL = miembro(bob, -0.16, 0.72, 0, 0.2, 0.7, 0.22, '#3d2918');
  const legR = miembro(bob, 0.16, 0.72, 0, 0.2, 0.7, 0.22, '#3d2918');
  const torso = pivote(bob, 0, 0.72, 0);
  mesh(torso, 'box', traje, 0, 0.4, 0, 0.62, 0.78, 0.38);
  const armL = miembro(torso, -0.42, 0.7, 0, 0.16, 0.62, 0.16, PIEL);
  const armR = miembro(torso, 0.42, 0.7, 0, 0.16, 0.62, 0.16, PIEL);
  mesh(armL, 'box', traje, 0, -0.18, 0, 0.2, 0.28, 0.2);
  mesh(armR, 'box', traje, 0, -0.18, 0, 0.2, 0.28, 0.2);
  const head = pivote(torso, 0, 0.86, 0);
  mesh(head, 'box', PIEL, 0, 0.2, 0, 0.42, 0.4, 0.4);
  mesh(head, 'box', PELO[kind] || '#3a2a1c', 0, 0.38, 0, 0.46, 0.14, 0.46);
  extras(torso, head, { izq: armL, der: armR }, kind, tint);
  root.userData.parts = { bob, legL, legR, armL, armR, head };
  root.userData.kind = kind;
  root.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });
  return root;
}

export function animar(grupo, t, moving) {
  const p = grupo && grupo.userData.parts;
  if (!p) return;
  const swing = moving ? Math.sin(t * 8) : Math.sin(t * 2) * 0.12;
  const amp = moving ? 0.85 : 1;
  p.legL.rotation.x = swing * amp;
  p.legR.rotation.x = -swing * amp;
  p.armL.rotation.x = -swing * (moving ? 0.7 : 0.4);
  p.armR.rotation.x = swing * (moving ? 0.7 : 0.4);
  p.bob.position.y = moving ? Math.abs(Math.sin(t * 8)) * 0.07 : Math.sin(t * 2) * 0.025;
  if (p.head) p.head.rotation.y = moving ? 0 : Math.sin(t * 1.3) * 0.08;
}

export function oficio(id) {
  const estado = window.LiveInk && window.LiveInk.state;
  if (id === 'self') return (window.Roles && window.Roles.actual()) || 'explorador';
  if (id === 'profesora_cadena') return 'profesora';
  if (id === 'capataz') return 'capataz';
  if (String(id).startsWith('peer')) {
    const raw = String(id).slice(4);
    const otro = estado && estado.others && (estado.others.get(Number(raw)) || estado.others.get(raw));
    return otro && OFICIOS.includes(otro.oficio) ? otro.oficio : 'vecino';
  }
  return 'vecino';
}
export function tinte(id, color) {
  if (id === 'self' || String(id).startsWith('peer')) return color || '#376fc2';
  return '#376fc2';
}

function cuadrupedo(g, cuerpo, detalle) {
  const bob = new T.Group();
  g.add(bob);
  mesh(bob, 'box', cuerpo, 0, 0.42, 0, detalle.largo, 0.32, 0.28);
  mesh(bob, 'box', cuerpo, detalle.largo * 0.38, 0.62, 0, 0.28, 0.24, 0.22);
  const patas = [];
  for (const [x, z] of [[-0.18, 0.1], [0.18, 0.1], [-0.18, -0.1], [0.16, -0.1]]) {
    patas.push(miembro(bob, x, 0.32, z, 0.08, 0.28, 0.08, detalle.pata || cuerpo));
  }
  if (detalle.orejas) {
    mesh(bob, 'box', cuerpo, detalle.largo * 0.42, 0.82, -0.06, 0.06, 0.16, 0.05);
    mesh(bob, 'box', cuerpo, detalle.largo * 0.42, 0.82, 0.06, 0.06, 0.16, 0.05);
  }
  if (detalle.cola) mesh(bob, 'box', detalle.cola, -detalle.largo * 0.4, 0.5, 0, 0.22, 0.06, 0.06);
  g.userData.menear = (t, moving) => {
    const s = moving ? Math.sin(t / 140) : Math.sin(t / 500) * 0.2;
    patas[0].rotation.x = s; patas[1].rotation.x = -s; patas[2].rotation.x = -s; patas[3].rotation.x = s;
    bob.position.y = moving ? Math.abs(Math.sin(t / 140)) * 0.04 : 0;
  };
}

export function fauna(g, key) {
  const k = key || '';
  if (k.includes('ave')) {
    const bob = new T.Group();
    g.add(bob);
    mesh(bob, 'box', '#d5b071', 0, 0.45, 0, 0.28, 0.22, 0.36);
    mesh(bob, 'box', '#c49a58', 0.22, 0.55, 0, 0.16, 0.14, 0.14);
    mesh(bob, 'box', '#f3efe4', 0.32, 0.52, 0, 0.08, 0.05, 0.05);
    const alaL = miembro(bob, 0, 0.5, -0.16, 0.2, 0.05, 0.12, '#b8884e');
    const alaR = miembro(bob, 0, 0.5, 0.16, 0.2, 0.05, 0.12, '#b8884e');
    g.userData.menear = (t) => { const s = Math.sin(t / 180) * 0.4; alaL.rotation.z = s; alaR.rotation.z = -s; bob.position.y = Math.sin(t / 280) * 0.05; };
    return;
  }
  cuadrupedo(g, k.includes('conejo') ? '#d7c4a8' : '#8a6244', { largo: k.includes('conejo') ? 0.55 : 0.9, orejas: k.includes('conejo'), cola: k.includes('venado') ? '#f3efe4' : '' });
}

export function caballo(g) {
  const bob = new T.Group();
  g.add(bob);
  mesh(bob, 'box', '#8a5a32', 0, 0.85, 0, 1.15, 0.55, 0.42);
  mesh(bob, 'box', '#a56b3c', 0.72, 1.15, 0, 0.42, 0.32, 0.28);
  mesh(bob, 'box', '#c48a52', 0.98, 1.28, 0, 0.28, 0.22, 0.2);
  mesh(bob, 'box', '#3a2416', 0.95, 1.42, -0.08, 0.06, 0.12, 0.04);
  mesh(bob, 'box', '#3a2416', 0.95, 1.42, 0.08, 0.06, 0.12, 0.04);
  mesh(bob, 'box', '#6b2e22', 0.05, 1.05, 0, 0.45, 0.08, 0.36);
  mesh(bob, 'box', '#3a2416', -0.62, 0.95, 0, 0.12, 0.28, 0.08);
  const patas = [];
  for (const [x, z] of [[-0.32, 0.14], [0.28, 0.14], [-0.32, -0.14], [0.28, -0.14]]) patas.push(miembro(bob, x, 0.62, z, 0.12, 0.58, 0.12, '#6b4224'));
  g.userData.menear = (t, moving) => {
    const s = moving ? Math.sin(t / 120) : Math.sin(t / 700) * 0.08;
    patas[0].rotation.x = s; patas[1].rotation.x = -s; patas[2].rotation.x = -s; patas[3].rotation.x = s;
    bob.position.y = moving ? Math.abs(Math.sin(t / 120)) * 0.05 : 0;
  };
  g.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });
}

const PELOS = {
  gato: { naranja: '#e08a3c', negro: '#2a2424', blanco: '#f4efe4', gris: '#8d8a86', tricolor: '#c46a3a' },
  perro: { cafe: '#8a5a32', negro: '#2c2826', blanco: '#f7f3ea', dorado: '#e2b23c', manchado: '#d9c7a2' },
};

export function mascota(pet) {
  const especie = pet && pet.especie === 'perro' ? 'perro' : 'gato';
  const color = (PELOS[especie] && PELOS[especie][pet.color]) || PELOS[especie].naranja || '#e08a3c';
  const g = new T.Group();
  const bob = new T.Group();
  g.add(bob);
  const largo = especie === 'perro' ? 0.7 : 0.55;
  mesh(bob, 'box', color, 0, 0.32, 0, largo, 0.28, 0.26);
  mesh(bob, 'box', color, largo * 0.4, 0.5, 0, 0.26, 0.22, 0.22);
  if (especie === 'gato') {
    mesh(bob, 'box', color, largo * 0.48, 0.68, -0.06, 0.05, 0.14, 0.04);
    mesh(bob, 'box', color, largo * 0.48, 0.68, 0.06, 0.05, 0.14, 0.04);
    mesh(bob, 'box', color, -largo * 0.45, 0.4, 0, 0.28, 0.05, 0.05);
  } else {
    mesh(bob, 'box', '#3d2918', largo * 0.55, 0.48, 0, 0.1, 0.06, 0.08);
    mesh(bob, 'box', color, -largo * 0.42, 0.42, 0.12, 0.08, 0.16, 0.05);
  }
  if (pet && pet.color === 'tricolor') mesh(bob, 'box', '#f4efe4', 0.05, 0.4, 0.12, 0.16, 0.1, 0.04);
  if (pet && pet.color === 'manchado') mesh(bob, 'box', '#3d2918', -0.05, 0.42, 0.12, 0.16, 0.1, 0.04);
  const patas = [];
  for (const [x, z] of [[-0.12, 0.08], [0.12, 0.08], [-0.12, -0.08], [0.12, -0.08]]) patas.push(miembro(bob, x, 0.24, z, 0.07, 0.22, 0.07, color));
  const nombre = new T.CanvasTexture(rotulo(pet && pet.nombre || ''));
  nombre.colorSpace = T.SRGBColorSpace;
  const sprite = new T.Sprite(new T.SpriteMaterial({ map: nombre, transparent: true, depthTest: false }));
  sprite.position.set(0, 1.05, 0);
  sprite.scale.set(1.1, 0.32, 1);
  g.add(sprite);
  g.userData.pose = (t, modo) => {
    const sit = modo === 'sit';
    const s = sit ? 0 : Math.sin(t / 140);
    patas[0].rotation.x = sit ? 1.1 : s;
    patas[1].rotation.x = sit ? 1.1 : -s;
    patas[2].rotation.x = sit ? -0.4 : -s;
    patas[3].rotation.x = sit ? -0.4 : s;
    bob.position.y = sit ? -0.06 : Math.abs(s) * 0.04;
    bob.rotation.x = sit ? 0.15 : 0;
  };
  return g;
}
function rotulo(texto) {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 64;
  const g = c.getContext('2d');
  g.clearRect(0, 0, 256, 64);
  g.font = 'bold 28px sans-serif';
  g.textAlign = 'center';
  g.fillStyle = '#2c1a0c';
  g.fillText(String(texto || '').slice(0, 16), 128, 42);
  g.fillStyle = '#fff6df';
  g.fillText(String(texto || '').slice(0, 16), 126, 40);
  return c;
}

let retratoGl, retratoEscena, retratoCam, retratoFig, retratoClave = '';
export function rostro(canvas, spec) {
  if (!canvas || !canvas.getContext) return false;
  try {
    if (!retratoGl) {
      retratoGl = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
      retratoGl.setSize(128, 128);
      retratoEscena = new T.Scene();
      retratoEscena.add(new T.HemisphereLight(0xfff3e0, 0x6a5438, 1.6));
      const sol = new T.DirectionalLight(0xfff6e8, 1.1);
      sol.position.set(2, 4, 3);
      retratoEscena.add(sol);
      retratoCam = new T.PerspectiveCamera(32, 1, 0.1, 20);
      retratoCam.position.set(1.1, 1.7, 2.6);
      retratoCam.lookAt(0, 1.15, 0);
    }
    const clave = (spec && spec.kind || 'explorador') + '|' + (spec && spec.tint || '');
    if (clave !== retratoClave) {
      if (retratoFig) retratoEscena.remove(retratoFig);
      retratoFig = crear(spec || { kind: 'explorador' });
      retratoEscena.add(retratoFig);
      retratoClave = clave;
    }
    animar(retratoFig, performance.now() / 1000, false);
    retratoGl.render(retratoEscena, retratoCam);
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(retratoGl.domElement, 0, 0, canvas.width, canvas.height);
    return true;
  } catch (e) { return false; }
}

export function foto(kind) {
  const renderer = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setSize(180, 220);
  const scene = new T.Scene();
  scene.add(new T.HemisphereLight(0xfff4e0, 0x6a5438, 1.5));
  const sol = new T.DirectionalLight(0xffffff, 1);
  sol.position.set(2, 4, 3);
  scene.add(sol);
  const fig = crear({ kind });
  animar(fig, 0.4, false);
  scene.add(fig);
  const cam = new T.PerspectiveCamera(32, 180 / 220, 0.1, 20);
  cam.position.set(1.5, 1.45, 3.1);
  cam.lookAt(0, 0.95, 0);
  renderer.render(scene, cam);
  const url = renderer.domElement.toDataURL('image/png');
  renderer.dispose();
  return url;
}

function engancharCara() {
  const sim = window.Simulacion;
  if (!sim || sim._rostro3d || typeof sim.drawDialogFace !== 'function') return;
  const prev = sim.drawDialogFace;
  sim.drawDialogFace = (who) => {
    const canvas = document.getElementById('dialogo-cara');
    const kind = who && who.id === 'profesora_cadena' ? 'profesora' : who && who.id === 'banquero' ? 'banquero' : 'capataz';
    if (canvas && rostro(canvas, { kind })) return;
    prev(who);
  };
  sim._rostro3d = true;
}
engancharCara();
setTimeout(engancharCara, 400);
window.Personajes = { crear, animar, oficio, tinte, fauna, caballo, mascota, rostro, foto, OFICIOS };
