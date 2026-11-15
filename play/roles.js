/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Oficio del jugador: se elige antes de la entrada y se puede cambiar después. */
import { foto, OFICIOS, rostro } from './personajes3d.js?v=hogar-r1';

const LISTA = [
  { id: 'explorador', nombre: 'Explorador', linea: 'Recorre el valle con ruana corta, morral y sombrero de camino.' },
  { id: 'comerciante', nombre: 'Comerciante', linea: 'Lleva la plaza en el chaleco y las monedas en el bolsillo.' },
  { id: 'artesano', nombre: 'Artesano / Herrero', linea: 'Delantal de cuero y martillo: convierte el metal en oficio.' },
  { id: 'inmobiliario', nombre: 'Agente inmobiliario', linea: 'De RentoCity: carpeta, llaves y traje para mostrar casas.' },
  { id: 'guardian', nombre: 'Guardián / Vecino', linea: 'Ruana antioqueña y farol: cuida la cuadra y da la bienvenida.' },
];

function nombre() {
  const me = window.LiveInk && window.LiveInk.state && window.LiveInk.state.me;
  const crudo = (me && me.name) || 'viajero';
  return String(crudo).trim().toLowerCase().slice(0, 16) || 'viajero';
}
function clave() { return 'lifeinc.rol.v1:' + encodeURIComponent(nombre()); }
function guardarLocal(id) {
  try {
    localStorage.setItem(clave(), id);
    localStorage.setItem('lifeinc.rol.v1', id);
  } catch (e) {}
}
function leerLocal() {
  try {
    const propio = localStorage.getItem(clave());
    const general = localStorage.getItem('lifeinc.rol.v1');
    const id = OFICIOS.includes(propio) ? propio : general;
    return OFICIOS.includes(id) ? id : '';
  } catch (e) { return ''; }
}

let panel, elegido = '', alTerminar = null, fotos = null;

function ficha(rol) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'oficio-ficha';
  b.dataset.oficio = rol.id;
  b.setAttribute('aria-pressed', 'false');
  const img = document.createElement('img');
  img.alt = rol.nombre;
  img.width = 180;
  img.height = 220;
  const titulo = document.createElement('b');
  titulo.textContent = rol.nombre;
  const linea = document.createElement('span');
  linea.textContent = rol.linea;
  b.append(img, titulo, linea);
  b.onclick = () => marcar(rol.id);
  return b;
}
function marcar(id) {
  elegido = id;
  for (const b of panel.querySelectorAll('.oficio-ficha')) {
    const on = b.dataset.oficio === id;
    b.classList.toggle('armada', on);
    b.setAttribute('aria-pressed', String(on));
  }
  const rol = LISTA.find(r => r.id === id);
  panel.querySelector('#oficio-linea').textContent = rol ? rol.linea : '';
  panel.querySelector('#oficio-entrar').disabled = !rol;
}
function pintarFotos() {
  if (fotos) return;
  fotos = {};
  for (const rol of LISTA) {
    try { fotos[rol.id] = foto(rol.id); } catch (e) { fotos[rol.id] = ''; }
    const img = panel.querySelector('[data-oficio="' + rol.id + '"] img');
    if (img && fotos[rol.id]) img.src = fotos[rol.id];
  }
}
function asegurar() {
  if (panel) return;
  panel = document.createElement('section');
  panel.id = 'oficio-panel';
  panel.hidden = true;
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-modal', 'true');
  panel.setAttribute('aria-labelledby', 'oficio-titulo');
  panel.innerHTML = '<div class="oficio-caja"><h2 id="oficio-titulo">Elige tu oficio</h2><p>Antes de entrar a Medellín, elige cómo te verán. Puedes cambiarlo después.</p><div id="oficio-lista"></div><p id="oficio-linea"></p><div class="oficio-acciones"><button type="button" id="oficio-entrar" disabled>Entrar con este oficio</button><button type="button" id="oficio-cerrar" hidden>Cancelar</button></div></div>';
  document.body.append(panel);
  const lista = panel.querySelector('#oficio-lista');
  for (const rol of LISTA) lista.append(ficha(rol));
  panel.querySelector('#oficio-entrar').onclick = confirmar;
  panel.querySelector('#oficio-cerrar').onclick = () => { panel.hidden = true; alTerminar = null; };
}
function confirmar() {
  if (!OFICIOS.includes(elegido)) return;
  guardarLocal(elegido);
  panel.hidden = true;
  if (window.Hogar) window.Hogar.guardar({ role: elegido });
  const retrato = document.getElementById('retrato');
  if (retrato) rostro(retrato, { kind: elegido });
  const etiqueta = document.getElementById('mi-oficio');
  if (etiqueta) etiqueta.textContent = (LISTA.find(r => r.id === elegido) || {}).nombre || '';
  const sigue = alTerminar;
  alTerminar = null;
  if (sigue) sigue();
}
function pedir(sigue, obligatorio) {
  asegurar();
  alTerminar = sigue || null;
  panel.hidden = false;
  panel.querySelector('#oficio-cerrar').hidden = !!obligatorio;
  pintarFotos();
  const ya = actual();
  if (ya) marcar(ya);
  else panel.querySelector('#oficio-linea').textContent = 'Toca un oficio para verlo.';
}
function actual() {
  const servidor = window.Hogar && window.Hogar.propio && window.Hogar.propio.role;
  if (OFICIOS.includes(servidor)) return servidor;
  return leerLocal();
}
function frena() {
  const q = new URLSearchParams(location.search);
  if (q.has('autotest') || q.has('sinlogin') || q.has('sinayuda') || q.has('forja')) return false;
  return !actual();
}
function boton(padre, id) {
  if (!padre || document.getElementById(id)) return;
  const b = document.createElement('button');
  b.type = 'button';
  b.id = id;
  b.textContent = 'Cambiar oficio';
  b.onclick = () => pedir(null, false);
  padre.append(b);
}
function montar() {
  const q = new URLSearchParams(location.search);
  if (OFICIOS.includes(q.get('oficio'))) guardarLocal(q.get('oficio'));
  const perfil = document.getElementById('hud-perfil');
  if (perfil && !document.getElementById('mi-oficio')) {
    const p = document.createElement('div');
    p.id = 'mi-oficio';
    const datos = perfil.querySelector('.datos');
    if (datos) datos.append(p);
  }
  boton(document.getElementById('cuenta-acciones'), 'b-oficio');
  boton(perfil, 'b-oficio-perfil');
  const id = actual();
  const etiqueta = document.getElementById('mi-oficio');
  if (etiqueta && id) etiqueta.textContent = (LISTA.find(r => r.id === id) || {}).nombre || '';
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', montar);
else montar();
setTimeout(montar, 600);

window.Roles = { actual, frena, pedir, lista: LISTA, OFICIOS };
