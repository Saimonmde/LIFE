/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Dirección privada de la casa y visitas con el código CASA-XXXX. */
const q = new URLSearchParams(location.search);

let propio = null;
let conocido = false;
let listoResolucion;
const listo = new Promise((resolve) => { listoResolucion = resolve; });

function codigoUrl() {
  return String(q.get('casa') || '').trim().toUpperCase();
}
async function traerPropio() {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 4000);
    const r = await fetch('/auth/hogar', { cache: 'no-store', credentials: 'same-origin', signal: ctrl.signal });
    clearTimeout(timer);
    if (!r.ok) return null;
    const data = await r.json();
    return data && data.ok ? data : null;
  } catch (e) { return null; }
}
async function guardar(parcial) {
  try {
    const r = await fetch('/auth/hogar', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parcial || {}),
    });
    if (!r.ok) return null;
    const data = await r.json();
    if (data && data.ok) propio = data;
    return data;
  } catch (e) { return null; }
}
function aplicarRol(data) {
  if (!data || !data.role) return;
  try { localStorage.setItem('lifeinc.rol.v1', data.role); } catch (e) {}
  const me = window.LiveInk && window.LiveInk.state && window.LiveInk.state.me;
  if (me && me.name) {
    try { localStorage.setItem('lifeinc.rol.v1:' + encodeURIComponent(String(me.name).trim().toLowerCase().slice(0, 16)), data.role); } catch (e) {}
  }
}
traerPropio().then((data) => {
  propio = data;
  aplicarRol(data);
  if (data && Array.isArray(data.mascotas)) {
    const me = window.LiveInk && window.LiveInk.state && window.LiveInk.state.me;
    const nombre = String((me && me.name) || 'viajero').trim().toLowerCase().slice(0, 16) || 'viajero';
    try { localStorage.setItem('lifeinc.mascotas.v1:' + encodeURIComponent(nombre), JSON.stringify(data.mascotas)); } catch (e) {}
  }
  conocido = true;
  listoResolucion();
});

let banda, direccion;
function asegurarBanda() {
  if (banda) return;
  banda = document.createElement('div');
  banda.id = 'visita-banda';
  banda.hidden = true;
  banda.innerHTML = '<p id="visita-txt"></p><button type="button" id="visita-volver">Volver a mi casa</button>';
  document.body.append(banda);
  banda.querySelector('#visita-volver').onclick = volver;
}
function volver() {
  if (window.Casa) window.Casa.quitarVisita(true);
  asegurarBanda();
  banda.hidden = true;
  const dentro = window.LiveInk && window.LiveInk.world && window.LiveInk.world.mapId === 'casa';
  if (dentro && window.Casa && window.Casa.onLayout) window.Casa.onLayout();
  else if (window.Casa && window.Casa.enter) window.Casa.enter();
}
async function entrar() {
  const codigo = codigoUrl();
  if (!codigo) return;
  if (propio && propio.codigo && propio.codigo.toUpperCase() === codigo.toUpperCase()) return;
  let data = null;
  try {
    const r = await fetch('/casa/' + encodeURIComponent(codigo), { cache: 'no-store' });
    data = await r.json();
    if (!r.ok || !data.ok) throw Error(data.error || 'No se puede visitar.');
  } catch (e) {
    asegurarBanda();
    banda.hidden = false;
    banda.querySelector('#visita-txt').textContent = (e && e.message) || 'No se puede visitar esa casa.';
    if (window.Tutorial) window.Tutorial.afterFly();
    return;
  }
  if (!window.Casa) return;
  window.Casa.ponerVisita(data);
  if (window.LiveInk && window.LiveInk.world && window.LiveInk.world.mapId !== 'casa' && window.Casa.enter) window.Casa.enter();
  asegurarBanda();
  banda.hidden = false;
  banda.querySelector('#visita-txt').textContent = 'Visitando ' + data.codigo + ' · casa de ' + (data.dueno || 'alguien') + '. Sólo puedes mirar.';
}
function asegurarDireccion() {
  if (direccion) return;
  direccion = document.createElement('section');
  direccion.id = 'casa-direccion';
  direccion.hidden = true;
  direccion.setAttribute('role', 'dialog');
  direccion.setAttribute('aria-labelledby', 'direccion-titulo');
  direccion.innerHTML = '<header id="direccion-titulo">Dirección de la casa <button type="button" id="direccion-cerrar" aria-label="Cerrar">✕</button></header><p id="direccion-codigo"></p><p id="direccion-nota"></p><div class="direccion-acciones"><button type="button" id="direccion-copiar">Copiar enlace</button><button type="button" id="direccion-nueva">Nuevo código</button><button type="button" id="direccion-visitas">Cerrar visitas</button></div><p id="direccion-estado" role="status"></p>';
  document.body.append(direccion);
  direccion.querySelector('#direccion-cerrar').onclick = () => { direccion.hidden = true; };
  direccion.querySelector('#direccion-copiar').onclick = copiar;
  direccion.querySelector('#direccion-nueva').onclick = async () => {
    const r = await fetch('/auth/hogar/codigo', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) { direccion.querySelector('#direccion-estado').textContent = data.error || 'Entra con tu cuenta para compartir la casa.'; return; }
    propio = data;
    pintarDireccion();
    direccion.querySelector('#direccion-estado').textContent = 'Listo. El enlace anterior ya no abre la casa.';
  };
  direccion.querySelector('#direccion-visitas').onclick = async () => {
    const abiertas = !(propio && propio.visitas);
    const r = await fetch('/auth/hogar/visitas', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ abiertas: !abiertas ? false : true }) });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) { direccion.querySelector('#direccion-estado').textContent = data.error || 'Entra con tu cuenta para cambiar las visitas.'; return; }
    propio = data;
    pintarDireccion();
  };
}
function pintarDireccion() {
  const codigo = propio && propio.codigo;
  direccion.querySelector('#direccion-codigo').textContent = codigo ? codigo : 'Sin código todavía';
  direccion.querySelector('#direccion-nota').textContent = codigo
    ? 'Comparte /play/?casa=' + codigo + '. Quien lo tenga puede mirar la casa, sin editar ni abrir el baúl. El campo nft queda vacío: esta versión no acuña nada.'
    : 'Entra con una cuenta para obtener una dirección y un enlace. El plano del invitado queda en este navegador.';
  const boton = direccion.querySelector('#direccion-visitas');
  boton.textContent = propio && propio.visitas === false ? 'Abrir visitas' : 'Cerrar visitas';
}
async function copiar() {
  if (!propio || !propio.codigo) {
    direccion.querySelector('#direccion-estado').textContent = 'Entra con tu cuenta para copiar el enlace.';
    return;
  }
  const url = location.origin + '/play/?casa=' + propio.codigo;
  try { await navigator.clipboard.writeText(url); direccion.querySelector('#direccion-estado').textContent = 'Enlace copiado.'; }
  catch (e) { direccion.querySelector('#direccion-estado').textContent = url; }
}
function abrirDireccion() {
  asegurarDireccion();
  direccion.hidden = false;
  pintarDireccion();
  traerPropio().then((data) => { if (data) { propio = data; pintarDireccion(); } });
}
function boton() {
  if (document.getElementById('b-direccion')) return;
  const b = document.createElement('button');
  b.id = 'b-direccion';
  b.type = 'button';
  b.textContent = 'Dirección';
  b.onclick = abrirDireccion;
  document.body.append(b);
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boton);
else boton();

window.Hogar = {
  get propio() { return propio; },
  get conocido() { return conocido; },
  listo, guardar,
};
window.Visitas = { hay: () => !!codigoUrl(), entrar, codigo: codigoUrl };
