/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Gaticos y perritos. Siguen al jugador, se sientan y viven en la casa. */
import { mascota as crearMascota } from './personajes3d.js?v=hogar-r1';

const PELOS = {
  gato: [['naranja', 'Naranja'], ['negro', 'Negro'], ['blanco', 'Blanco'], ['gris', 'Gris'], ['tricolor', 'Tricolor']],
  perro: [['cafe', 'Café'], ['negro', 'Negro'], ['blanco', 'Blanco'], ['dorado', 'Dorado'], ['manchado', 'Manchado']],
};
const MAX = 3;
const mallas = new Map();
let panel;

function clave() {
  const me = window.LiveInk && window.LiveInk.state && window.LiveInk.state.me;
  const nombre = String((me && me.name) || 'viajero').trim().toLowerCase().slice(0, 16) || 'viajero';
  return 'lifeinc.mascotas.v1:' + encodeURIComponent(nombre);
}
function leer() {
  try {
    const raw = JSON.parse(localStorage.getItem(clave()) || '[]');
    return Array.isArray(raw) ? raw.slice(0, MAX) : [];
  } catch (e) { return []; }
}
function guardar(lista) {
  try { localStorage.setItem(clave(), JSON.stringify(lista)); } catch (e) {}
  if (window.Hogar) window.Hogar.guardar({ mascotas: lista });
}
function propias() {
  const servidor = window.Hogar && window.Hogar.propio && window.Hogar.propio.mascotas;
  if (Array.isArray(servidor) && servidor.length) return servidor;
  return leer();
}
function activas(zona) {
  if (zona === 'casa' && window.Casa && window.Casa.visita) return window.Casa.visita.mascotas || [];
  return propias();
}
function adoptar(especie, color, nombre) {
  const lista = leer().slice();
  if (lista.length >= MAX) return;
  lista.push({
    id: especie + '-' + Math.random().toString(36).slice(2, 7),
    especie, color,
    nombre: String(nombre || '').trim().slice(0, 16) || (especie === 'gato' ? 'Michi' : 'Firulais'),
  });
  guardar(lista);
  pintar();
}
function quitar(id) {
  guardar(leer().filter(p => p.id !== id));
  pintar();
}
function pintar() {
  if (!panel) return;
  const lista = panel.querySelector('#mascotas-lista');
  lista.replaceChildren();
  for (const pet of leer()) {
    const fila = document.createElement('p');
    fila.textContent = pet.nombre + ' · ' + (pet.especie === 'perro' ? 'perrito' : 'gatico') + ' ' + pet.color;
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = 'Dejar en adopción';
    b.onclick = () => quitar(pet.id);
    fila.append(b);
    lista.append(fila);
  }
  panel.querySelector('#mascotas-cupo').textContent = leer().length + ' de ' + MAX;
}
function asegurar() {
  if (panel) return;
  panel = document.createElement('section');
  panel.id = 'mascotas';
  panel.hidden = true;
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-labelledby', 'mascotas-titulo');
  panel.innerHTML = '<header id="mascotas-titulo">Mascotas <button type="button" id="mascotas-cerrar" aria-label="Cerrar">✕</button></header><p>Hasta tres gaticos o perritos. Te siguen por el valle y se quedan en la casa. <span id="mascotas-cupo"></span></p><label>Nombre <input id="mascotas-nombre" maxlength="16" placeholder="Michi"></label><div id="mascotas-opciones"></div><div id="mascotas-lista"></div>';
  document.body.append(panel);
  const opciones = panel.querySelector('#mascotas-opciones');
  for (const [especie, colores] of Object.entries(PELOS)) {
    for (const [color, etiqueta] of colores) {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = (especie === 'gato' ? 'Gato ' : 'Perro ') + etiqueta;
      b.onclick = () => adoptar(especie, color, panel.querySelector('#mascotas-nombre').value);
      opciones.append(b);
    }
  }
  panel.querySelector('#mascotas-cerrar').onclick = () => { panel.hidden = true; };
}
function abrir() { asegurar(); panel.hidden = false; pintar(); }
function boton() {
  if (document.getElementById('b-mascotas')) return;
  const b = document.createElement('button');
  b.id = 'b-mascotas';
  b.type = 'button';
  b.textContent = 'Mascotas';
  b.onclick = abrir;
  document.body.append(b);
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boton);
else boton();

function tick(escena, jugador, zona, time, height) {
  const lista = activas(zona);
  const vivas = new Set(lista.map(p => p.id));
  for (const [id, g] of mallas) {
    if (!vivas.has(id)) { (g.parent || escena).remove(g); mallas.delete(id); }
  }
  const indoors = zona === 'casa' || zona === 'mine' || zona === 'banco';
  lista.forEach((pet, i) => {
    let g = mallas.get(pet.id);
    const firma = pet.especie + '|' + pet.color + '|' + pet.nombre;
    if (!g || g.userData.firma !== firma) {
      if (g) (g.parent || escena).remove(g);
      g = crearMascota(pet);
      g.userData.firma = firma;
      mallas.set(pet.id, g);
    }
    if (g.parent !== escena) escena.add(g);
    g.visible = zona !== 'mine' && zona !== 'banco';
    const dir = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }[jugador.dir] || [0, 1];
    let x, z, modo = 'idle';
    if (zona === 'casa') {
      const lugares = [[7, 7], [9, 7], [11, 9]];
      const sitio = lugares[i] || lugares[0];
      x = sitio[0]; z = sitio[1];
      modo = 'sit';
    } else if (!indoors) {
      const detras = 1.35 + i * 0.75;
      x = jugador.fx * 2 + 1 - dir[0] * detras + dir[1] * ((i - 1) * 0.35);
      z = jugador.fy * 2 + 1 - dir[1] * detras - dir[0] * ((i - 1) * 0.35);
    } else {
      g.visible = false;
      return;
    }
    const y = zona === 'casa' ? 0 : (height ? height(x / 2, z / 2) : 0);
    const dx = x - g.position.x, dz = z - g.position.z;
    const lejos = Math.hypot(dx, dz);
    if (lejos > 0.04 && modo !== 'sit') modo = 'walk';
    g.position.x += dx * (zona === 'casa' ? 1 : 0.18);
    g.position.z += dz * (zona === 'casa' ? 1 : 0.18);
    g.position.y = y;
    if (modo === 'sit' || lejos < 0.2) {
      g.position.x = zona === 'casa' ? x : g.position.x;
      g.position.z = zona === 'casa' ? z : g.position.z;
      if (lejos < 0.25) modo = 'sit';
    }
    if (Math.abs(dx) + Math.abs(dz) > 0.05) g.rotation.y = Math.atan2(dx, dz);
    if (g.userData.pose) g.userData.pose(time, modo === 'walk' ? 'walk' : 'sit');
  });
}

window.Mascotas = { abrir, leer, tick, PELOS };
