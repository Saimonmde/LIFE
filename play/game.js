/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* LIFE INC · El Jardín — vista previa jugable (JS plano, sin build).
   Carga ../data/el-jardin.json (o window.EL_JARDIN) + ../graphics. Chat/presencia por WebSocket (server.py, /ws). */
(() => {
'use strict';
const BASE = '../', TS = 64;
const $ = (s) => document.querySelector(s);
const cv = $('#juego'), ctx = cv.getContext('2d');
const mm = $('#minimapa'), mctx = mm.getContext('2d');
const Q = new URLSearchParams(location.search);
const AUTOTEST = Q.has('autotest');
const VISTA = Q.get('vista') || '';

let W, tileset, imgs = {}, sheets = {}, capatazImg;
let zoom = innerWidth < 820 ? 0.85 : 1.1;
let timeOffset = 0;
const now = () => performance.now() + timeOffset;
const rnd = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
const esc = (s) => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const NOMBRES = {
  manzana: 'Manzano', pera: 'Peral', naranja: 'Naranjo', mango: 'Palo de mango', banano: 'Mata de banano', coco: 'Palma de coco',
  conejo: 'Conejo', venado: 'Venado', ave: 'Ave silvestre', cobre: 'Roca de cobre', plata: 'Roca de plata', piedra: 'Roca de piedra', pino: 'Pino',
};
const CANALES = { global: 'Mundo', proximidad: 'Cerca', clan: 'Clan', grupo: 'Grupo' };
function textoNombre(raw) {
  const text = String(raw || '').trim();
  if (!text || text.includes('@')) return 'Viajero';
  return text.slice(0, 16);
}
function pareceSimon(text) {
  const flat = String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const folded = flat.replace(/[^a-z0-9@$]/g, '').replace(/0/g, 'o').replace(/1/g, 'i').replace(/3/g, 'e').replace(/4/g, 'a').replace(/5/g, 's').replace(/7/g, 't').replace(/@/g, 'a').replace(/\$/g, 's');
  return folded === 'simon';
}
function apodoQueQueda(text) {
  const cleaned = String(text || '').normalize('NFKC').replace(/[^0-9A-Za-zÁÉÍÓÚáéíóúÑñ ]/g, '');
  return cleaned.trim().slice(0, 16);
}
function pintarApodo(input, vista) {
  if (!input || !vista) return;
  const queda = apodoQueQueda(input.value);
  vista.textContent = 'Acepta letras, números y espacios. Así quedará: ' + (queda || '(vacío)');
}
function apodoCuenta(user) {
  const wallet = String((user && user.wallet_name) || '').trim();
  const email = String((user && user.email) || '').trim().toLowerCase();
  if (!wallet || wallet.includes('@') || (email && wallet.toLowerCase() === email)) return 'Viajero';
  return wallet.slice(0, 16);
}
function nombrePropio() {
  const nick = String((S.me && S.me.nick) || '').trim();
  if (nick && !nick.includes('@')) return nick.slice(0, 16);
  if (S.sessionUser) return 'Viajero';
  return textoNombre(S.me && S.me.name);
}
function nombreAjeno(p) {
  if (!p) return 'Viajero';
  const nick = String(p.nick || '').trim();
  if (nick && !nick.includes('@')) return nick.slice(0, 16);
  if (p.avatar_id) return 'Viajero';
  return textoNombre(p.name);
}
window.nombrePropio = nombrePropio;
window.nombreAjeno = nombreAjeno;

// ---------------- estado ----------------
const S = window.__ELJARDIN = {
  me: { name: 'Viajero', nick: 'Viajero', color: 'azul', clan: '', group: '' }, sessionUser: null, houseEdit: false,
  player: { x: 0, y: 0, fx: 0, fy: 0, path: [], dir: 'down', animT: 0, busyUntil: 0, pending: null, repaths: 0 },
  nodes: new Map(), animals: [], inv: [], sel: -1, xp: {}, coins: 0, energy: 100, hp: 100, sprintLock: false, skating: false, playtime: 0, createdAt: 0, lastInput: 0,
  quest: { stage: 0, steps: {}, done: false, turnedIn: false },
  floaters: [], cam: { x: 0, y: 0 }, hover: null, dest: null, keys: new Set(), night: false, circadianIndex: null, nightOverride: null, mmZoom: 1,
  others: new Map(), net: { ws: null, ok: false, hasJoined: false, serverId: null, id: 0, ping: 0, lastSent: 0, sentKey: '' },
  chat: { tab: 'global', lines: [], unread: {} }, dialog: null, bubbles: new Map(), lastPrompt: '',
};

function load() {
  return fetch(BASE + 'data/el-jardin.json').then(r => { if (!r.ok) throw 0; return r.json(); })
    .catch(() => { if (window.EL_JARDIN) return window.EL_JARDIN; throw new Error('No se pudo cargar el-jardin.json'); });
}
const loadImg = (src) => new Promise((ok, ko) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => ko(new Error('Imagen: ' + src)); i.src = BASE + src; });

async function init() {
  W = await load();
  try {
    const bridge = await import('./bridge4sur.js?v=puente-4-sur-r1');
    bridge.install(W);
  } catch (err) { console.error(err); }
  prepareMining();
  await Simulacion.installWorld(W, S);
  Simulacion.bind({
    S, game, sys, esc, invAdd, save, addXp, renderAll, renderQuest, renderSkills, showDialog, act, update,
    W: () => W, imgs, capataz: () => capatazImg, invRemove, invCount, applySmelt, renderProfile,
  });
  const bLibro = $('#b-libro'), bLibroMovil = $('#b-libro-movil'), bMontar = $('#b-montar'), bBajar = $('#b-bajar'), bSkate = $('#b-skate'), bSkateMovil = $('#b-skate-movil');
  if (bLibro) bLibro.onclick = () => Simulacion.toggleLibro();
  if (bLibroMovil) bLibroMovil.onclick = () => Simulacion.toggleLibro();
  const toggleMount = () => { if (S.skating) S.skating = false; if (S.mounted) Simulacion.dismount(); else Simulacion.summonAndMount(); };
  if (bMontar) bMontar.onclick = toggleMount;
  const bMontarBarra = $('#b-montar-barra'); if (bMontarBarra) bMontarBarra.onclick = toggleMount;
  const pressSkate = () => toggleSkate();
  if (bSkate) bSkate.onclick = pressSkate;
  if (bSkateMovil) bSkateMovil.onclick = pressSkate;
  if (bBajar) bBajar.onclick = () => { if (S.mounted) Simulacion.dismount(); };
  tileset = await loadImg(W.tileset.image);
  sheets.default = await loadImg(W.player.image);
  for (const [c, p] of Object.entries(W.playerVariants || {})) sheets[c] = await loadImg(p);
  capatazImg = W.npcs && W.npcs[0] ? await loadImg(W.npcs[0].sheet) : null;
  const profNpc = (W.npcs || []).find(n => n.id === 'profesora_cadena');
  if (profNpc) imgs._profesora = await loadImg(profNpc.sheet);
  await Promise.all(Object.entries(W.sprites).map(async ([k, s]) => { imgs[k] = await loadImg(s.image); }));
  await Promise.all(Object.values(W.items).map(async it => { imgs['icon:' + it.id] = await loadImg(it.icon['32']); }));
  if (window.Gallos && !W.items.gallo) {
    const icon = Gallos.icon();
    W.items.gallo = { id: 'gallo', name: 'Gallo', stackable: true, maxStack: Gallos.CAP, icon: { '32': icon } };
    const pic = new Image(); pic.src = icon; imgs['icon:gallo'] = pic;
    Gallos.onTake = (bird) => {
      if (!window.Corral) return;
      const answer = Corral.catchWorld(bird || { species: 'gallo' });
      if (!answer.ok) { game(answer.reason === 'protegida' ? 'La Guacharaca no se atrapa.' : 'No se pudo atrapar.', 'aviso'); return; }
      save();
      const name = answer.animal.species === 'gallina' ? 'gallina' : 'gallo';
      game('Atrapaste un <b>' + name + '</b>. Quedó en tu corral. No se mata; el gallo sí se puede vender.', 'juego');
    };
  }
  for (const n of W.nodes) {
    if (n.type === 'animal') S.animals.push({ def: n, x: n.x, y: n.y, fx: n.x, fy: n.y, state: 'alive', until: 0, nextMove: now() + 1000 + Math.random() * 3000, frame: 0 });
    else S.nodes.set(n.id, { def: n, state: n.initialState, until: 0, crop: null });
  }
  S.quest.def = W.quests && W.quests[0];
  S.player.x = S.player.fx = W.spawn.x; S.player.y = S.player.fy = W.spawn.y; S.player.dir = W.spawn.facing || 'down';
  let prof = null; try { prof = JSON.parse(localStorage.getItem('lifeinc.perfil') || 'null'); } catch (e) {}
  if (prof) {
    if (prof.name) S.me.name = textoNombre(prof.name);
    S.me.nick = S.me.name;
    S.me.clan = prof.clan || ''; S.me.group = prof.group || '';
    if (prof.color) S.me.color = prof.color;
  }
  Casa.playerName = () => S.me.name;
  Casa.ownerKey = () => {
    const id = S.sessionUser && S.sessionUser.id;
    const mid = S.me.municipio || (S.sessionUser && S.sessionUser.municipio) || '';
    return id ? ('id:' + id + ':' + mid) : S.me.name;
  };
  Casa.enter = () => { if (S.mounted) { game('Baja del caballo para entrar a un edificio.', 'aviso'); return; } if (S.skating) S.skating = false; enterHouse(); };
  Casa.exit = () => exitHouse();
  Casa.onEdit = (on) => { S.houseEdit = on; if (on) { S.player.path = []; S.player.pending = null; S.keys.clear(); } };
  Casa.onLayout = () => { if ((W.mapId || 'city') === 'casa') applyCasaLayout(); if (window.LIVE3D && window.LIVE3D.rebuildHouse) window.LIVE3D.rebuildHouse(Casa.layout); if (window.Vida) Vida.onLayout(); };
  Casa.mount();
  Casa.load(S.me.name);
  restore();
  if(!invCount('pico'))invAdd('pico',1);
  setupMiningUI();
  drawMinimapBase(); buildColorPicker(); renderAll();
  $('#cargando').remove();
  applyCircadian(false);
  resize(); requestAnimationFrame(loop);
  if (AUTOTEST) {
    if ((W.mapId || 'city') !== 'city') switchMap('city', true);
    S.player.x = S.player.fx = W.spawn.x; S.player.y = S.player.fy = W.spawn.y;
    startGame(); autotest(); return;
  }
  if (VISTA) {
    try { localStorage.setItem('lifeinc.vuelo.v1', '1'); localStorage.setItem('lifeinc.mascota.skip', '1'); } catch (e) {}
    W.clientReady = true;
    startGame();
    const show = () => { if (window.Fauna) Fauna.present(VISTA); };
    setTimeout(show, 600);
    return;
  }
  W.clientReady = true;
  const login = $('#login');
  if (login) login.hidden = false;
  const cuentas = $('#login-cuentas');
  if (cuentas) cuentas.hidden = true;
  const red = $('#login-red');
  if (red) { red.classList.remove('en-linea'); red.textContent = 'Conectando al mundo…'; }
  if (prof && prof.name && $('#l-nombre')) { $('#l-nombre').value = textoNombre(prof.name); if (prof.color) S.me.color = prof.color; buildColorPicker(); }
  if (Q.get('auth') === 'error') $('#login-status').textContent = 'No se pudo entrar con ese proveedor. Intenta otra vez.';
  if (Q.get('auth') === 'enlace') $('#login-status').textContent = 'El enlace caducó o ya se usó. Pide otro.';
  let sessionUser = null;
  if (Q.get('auth') !== 'error') sessionUser = await leerSesion();
  if (sessionUser) {
    if (window.Hogar && Hogar.migrate) {
      try { sessionUser = await Hogar.migrate(sessionUser) || sessionUser; } catch (e) {}
    }
    continuarSesion(sessionUser);
    return;
  }
  if (cuentas) cuentas.hidden = false;
  if (red) { red.classList.add('en-linea'); red.textContent = 'En línea'; }
  fetch('/auth/providers').then(r => r.json()).then(p => {
    const g = $('#b-google');
    if (g) {
      g.hidden = !p.google;
      g.disabled = !p.google;
      const label = g.querySelector('span');
      if (label) label.textContent = 'Continuar con Google';
    }
    const reg = $('#b-registro');
    if (reg) reg.hidden = !p.registro;
    const olvide = $('#b-olvide');
    if (olvide) olvide.hidden = !p.reset;
  }).catch(() => {
    const g = $('#b-google');
    if (g) g.hidden = true;
  });
}
async function leerSesion() {
  const red = $('#login-red');
  const once = async () => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 15000);
    try {
      const response = await fetch('/auth/sesion', { signal: ctrl.signal, cache: 'no-store' });
      if (!response.ok) return { awake: true, user: null };
      const ses = await response.json();
      return { awake: true, user: ses && ses.user };
    } catch (e) {
      return { awake: false, user: null };
    } finally {
      clearTimeout(timer);
    }
  };
  let got = await once();
  if (!got.awake) {
    if (red) red.textContent = 'Despertando servidor…';
    got = await once();
  }
  return got.user || null;
}
async function leerCuerpo(response) {
  let text = '';
  try { text = await response.text(); } catch (e) { text = ''; }
  try { return JSON.parse(text || '{}'); }
  catch (e) { return { error: 'No se pudo conectar. Espera a que despierte el servidor y vuelve a intentar.' }; }
}
function buildColorPicker() {
  const box = $('#l-colores'); if (!box) return; box.innerHTML = '';
  const hex = { azul: '#2860d4', rojo: '#c82c2c', amarillo: '#ecb828', verde: '#2e9650', morado: '#7640b8' };
  for (const c of Object.keys(W.playerVariants || { azul: 1 })) {
    const b = document.createElement('button'); b.type = 'button'; b.style.background = hex[c] || '#888'; b.title = c;
    if (c === S.me.color) b.className = 'sel';
    b.onclick = () => { S.me.color = c; buildColorPicker(); }; box.appendChild(b);
  }
}
function vueltaJuego() {
  if (location.pathname.indexOf('/movil') === 0 || Q.get('movil') === '1') return '/play/?movil=1';
  return '/play/';
}
function linkCookie() {
  let token = '';
  try { token = (window.Simulacion && Simulacion.walletToken && Simulacion.walletToken($('#l-nombre').value.trim())) || ''; } catch (e) {}
  const name = ($('#l-nombre').value || '').trim();
  document.cookie = 'life_link=' + encodeURIComponent(name + '|' + token) + '; Path=/; SameSite=Lax; Max-Age=600';
  document.cookie = 'life_return=' + encodeURIComponent(vueltaJuego()) + '; Path=/; SameSite=Lax; Max-Age=600';
}
async function continuarSesion(sessionUser) {
  S.sessionUser = sessionUser;
  S.me.municipio = sessionUser.municipio || '';
  window.SaimonSession = { id: sessionUser.id, municipio: S.me.municipio };
  S.me.nick = apodoCuenta(sessionUser);
  const wallet = String(sessionUser.wallet_name || '').trim();
  if (wallet && !wallet.includes('@') && wallet.toLowerCase() !== String(sessionUser.email || '').trim().toLowerCase()) S.me.name = wallet.slice(0, 16);
  if ($('#l-nombre')) $('#l-nombre').value = S.me.nick;
  try { localStorage.setItem('lifeinc.perfil', JSON.stringify(S.me)); } catch (e) {}
  const tomar = $('#b-tomar-simon');
  if (tomar) tomar.hidden = true;
  const clave = $('#poner-clave');
  if (clave) clave.hidden = true;
  const red = $('#login-red');
  if (red) { red.classList.add('en-linea'); red.textContent = 'En línea'; }
  const hi = $('#login-bienvenida');
  const nick = apodoCuenta(sessionUser) || 'Viajero';
  if (hi) { hi.hidden = false; hi.textContent = 'Bienvenido de vuelta, ' + nick; }
  window.SaimonSession.favoritePlace = sessionUser.favoritePlace || '';
  let saved = null;
  if (window.Partida) { try { saved = await Partida.pull(); } catch (e) { saved = null; } }
  window.LIFE_PARTIDA = !!(saved && saved.saved && saved.position);
  if (!sessionUser.favoritePlace && window.Hogar) {
    document.body.classList.add('eligiendo-casa');
    Hogar.openPicker(id => elegirLugar(id, true), false);
    return;
  }
  startGame();
}
const bSimon = $('#b-tomar-simon'); if (bSimon) bSimon.onclick = async () => {
  if (bSimon.disabled) return;
  bSimon.disabled = true;
  try {
    const response = await fetch('/auth/simon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    const result = await response.json();
    if (!response.ok || !result.user) throw Error(result.error || 'No se pudo tomar el apodo.');
    continuarSesion(result.user);
    const nombre = $('#mi-nombre');
    if (nombre) nombre.textContent = 'Simon';
  } catch (error) {
    const box = $('#login-status');
    if (box) box.textContent = error.message;
  } finally { bSimon.disabled = false; }
};
function fuerzaClave(text) {
  const value = String(text || '');
  let score = 0;
  if (value.length >= 8) score += 1;
  if (value.length >= 12) score += 1;
  if (/[a-záéíóúñ]/.test(value) && /[A-ZÁÉÍÓÚÑ]/.test(value)) score += 1;
  if (/\d/.test(value)) score += 1;
  if (/[^0-9A-Za-zÁÉÍÓÚáéíóúÑñ]/.test(value)) score += 1;
  if (value.length < 8 || score < 3) return { label: 'Débil', cls: 'debil' };
  if (score < 4) return { label: 'Regular', cls: 'media' };
  return { label: 'Fuerte', cls: 'fuerte' };
}
$('#b-correo').onclick=()=>{ $('#correo-login').hidden=!$('#correo-login').hidden;$('#registro').hidden=true;$('#olvide').hidden=true; };
const bEntrar = $('#b-entrar'); if (bEntrar) bEntrar.onclick = async () => {
  if (bEntrar.disabled) return;
  const nick = $('#e-nick').value.trim();
  const password = $('#e-clave').value;
  if (!nick) { avisoLogin('Escribe un nickname de hasta 16 letras.'); return; }
  if (password.length < 8 || password.length > 1024) { avisoLogin('La contraseña necesita entre 8 y 1024 caracteres.'); return; }
  bEntrar.disabled = true;
  try {
    const response = await fetch('/auth/entrar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nick, password }) });
    const result = await leerCuerpo(response);
    $('#e-clave').value = '';
    if (!response.ok || !result.user) throw Error(result.error || 'Apodo o contraseña incorrectos.');
    location.replace(vueltaJuego());
  } catch (error) { avisoLogin(error.message || 'No se pudo conectar. Espera a que despierte el servidor y vuelve a intentar.'); }
  finally { bEntrar.disabled = false; }
};
const nickNuevo = $('#e-nick');
const lineaNueva = $('#login-nuevo');
if (nickNuevo && lineaNueva) {
  let nickTimer = 0;
  nickNuevo.addEventListener('input', () => {
    clearTimeout(nickTimer);
    const value = nickNuevo.value.trim();
    if (!value) { lineaNueva.hidden = true; return; }
    nickTimer = setTimeout(() => {
      fetch('/auth/nick', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nick: value }) })
        .then(r => r.json())
        .then(m => {
          if (nickNuevo.value.trim() !== value) return;
          lineaNueva.hidden = !m.nuevo;
        })
        .catch(() => { lineaNueva.hidden = true; });
    }, 200);
  });
}
[['p-nick', 'p-apodo-vista'], ['l-nombre', 'l-apodo-vista']].forEach(([inputId, viewId]) => {
  const input = document.getElementById(inputId);
  const vista = document.getElementById(viewId);
  if (!input || !vista) return;
  const paint = () => pintarApodo(input, vista);
  input.addEventListener('input', paint);
  paint();
});
const clave = $('#p-pass');
if (clave) clave.addEventListener('input', () => {
  const fuerza = fuerzaClave(clave.value);
  const texto = $('#p-fuerza');
  const barra = $('#p-barra');
  if (texto) texto.textContent = clave.value ? fuerza.label : 'Escribe una contraseña.';
  if (barra) barra.className = fuerza.cls;
});
const bGuardar = $('#p-guardar'); if (bGuardar) bGuardar.onclick = async () => {
  if (bGuardar.disabled) return;
  bGuardar.disabled = true;
  try {
    const response = await fetch('/auth/apodo', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nick: $('#p-nick').value.trim(), password: $('#p-pass').value, confirm: $('#p-pass2').value }) });
    const result = await response.json();
    if (!response.ok || !result.user) throw Error(result.error || 'No se pudo guardar.');
    $('#p-pass').value = '';
    $('#p-pass2').value = '';
    continuarSesion(result.user);
  } catch (error) {
    const box = $('#p-status');
    if (box) box.textContent = error.message;
  } finally { bGuardar.disabled = false; }
};
$('#b-correo-entrar').onclick=async()=>{
 const button=$('#b-correo-entrar');if(button.disabled)return;
 const email=$('#e-email').value.trim();
 const password=$('#e-password').value;
 if(!email||password.length<8){avisoLogin('Escribe el correo y una contraseña de al menos 8 caracteres.');return;}
 button.disabled=true;
 try{const response=await fetch('/auth/entrar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});const result=await leerCuerpo(response);$('#e-password').value='';
  if(!response.ok||!result.user)throw Error(result.error||'No se pudo entrar.');
  location.replace(vueltaJuego());
 }catch(error){avisoLogin(error.message||'No se pudo conectar. Espera a que despierte el servidor y vuelve a intentar.');}finally{button.disabled=false;}
};
$('#correo-login').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();$('#b-correo-entrar').click();}};
const bGoogle = $('#b-google'); if (bGoogle) bGoogle.onclick = () => { linkCookie(); location.href = '/auth/google?vuelta=' + encodeURIComponent(vueltaJuego()); };
const bFacebook = $('#b-facebook'); if (bFacebook) bFacebook.onclick = () => { linkCookie(); location.href = '/auth/facebook?vuelta=' + encodeURIComponent(vueltaJuego()); };
const bRegistro = $('#b-registro'); if (bRegistro) bRegistro.onclick = () => { $('#correo-login').hidden=true; $('#olvide').hidden=true; const box = $('#registro'); if (box) box.hidden = !box.hidden; };
const bOlvide = $('#b-olvide'); if (bOlvide) bOlvide.onclick = () => { $('#correo-login').hidden=true; $('#registro').hidden=true; const box = $('#olvide'); if (box) box.hidden = !box.hidden; if ($('#o-email') && $('#e-email')) $('#o-email').value = $('#e-email').value; };
function avisoLogin(text) { const box = $('#login-status'); if (box) box.textContent = text || ''; }
const bPedir = $('#b-pedir-codigo'); if (bPedir) bPedir.onclick = () => {
  const name = ($('#l-nombre') || {}).value.trim();
  const email = $('#r-email').value.trim();
  const password = $('#r-pass').value;
  if (!name) { avisoLogin('Escribe un apodo de hasta 16 letras.'); return; }
  if (!email) { avisoLogin('El correo no parece válido.'); return; }
  if (password.length < 8 || password.length > 1024) { avisoLogin('La contraseña necesita entre 8 y 1024 caracteres.'); return; }
  linkCookie();
  fetch('/auth/registro', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, email, password})}).then(r => leerCuerpo(r).then(m => ({ok:r.ok, m}))).then(({ok, m}) => {
    if (ok && m.user) { location.replace(vueltaJuego()); return; }
    avisoLogin(m.error || (ok ? 'Te enviamos un enlace. La cuenta no sirve hasta que lo abras.' : 'No se pudo crear la cuenta.'));
    const again = $('#b-reenviar');
    if (again && ok) again.hidden = false;
  }).catch(() => avisoLogin('No se pudo conectar. Espera a que despierte el servidor y vuelve a intentar.'));
};
const bRe = $('#b-reenviar'); if (bRe) bRe.onclick = () => {
  fetch('/auth/reenviar', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email:$('#r-email').value.trim()})}).then(r => r.json()).then(m => avisoLogin(m.error || 'Si hay un registro pendiente, enviamos otro enlace. El anterior ya no sirve.'));
};
const bReset = $('#b-olvide-enviar'); if (bReset) bReset.onclick = () => {
  fetch('/auth/olvide', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email:$('#o-email').value.trim()})}).then(r => r.json()).then(m => avisoLogin(m.error || 'Si esa cuenta existe, enviamos un enlace para la contraseña.'));
};
$('#login-form').onsubmit = (e) => { e.preventDefault(); if (bEntrar && $('#correo-login').hidden) bEntrar.click(); };
async function elegirLugar(id, remember) {
  const buttons = [...document.querySelectorAll('#hogar-lista button')];
  buttons.forEach(b => { b.disabled = true; });
  const status = document.getElementById('hogar-status');
  try {
    if (remember) {
      const response = await fetch('/auth/lugar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: id }) });
      const result = await response.json();
      if (!response.ok || !result.user) throw Error(result.error || 'No se pudo guardar el lugar.');
      S.sessionUser = result.user;
      S.me.municipio = result.user.municipio || '';
      window.SaimonSession = { id: result.user.id, municipio: S.me.municipio, favoritePlace: result.user.favoritePlace || '' };
      const spot = result.home || (window.Lugares && Lugares.get(id));
      if (!started) {
        window.LIFE_PARTIDA = false;
        window.LIFE_OVNI = spot;
        window.LIFE_WANT_INTRO = window.Hogar ? Hogar.entryMode(true) : 'ovni';
      }
      if (status && started) status.textContent = 'Favorito: ' + ((spot && spot.name) || 'ese lugar') + '. Ahí apareces al entrar.';
    }
    if (window.Hogar) Hogar.closePicker();
    document.body.classList.remove('eligiendo-casa');
    if (!started) startGame();
    else if (!remember) askTravel(id);
  } catch (error) {
    buttons.forEach(b => { b.disabled = false; });
    if (status) status.textContent = error.message;
  }
}
async function elegirCasa(id) {
  const buttons = [...document.querySelectorAll('#hogar-lista button')];
  buttons.forEach(b => { b.disabled = true; });
  const status = document.getElementById('hogar-status');
  try {
    const response = await fetch('/auth/municipio', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ municipio: id }) });
    const result = await response.json();
    if (!response.ok || !result.user) throw Error(result.error || 'No se pudo guardar tu casa.');
    S.sessionUser = result.user;
    S.me.municipio = result.user.municipio;
    window.SaimonSession = { id: result.user.id, municipio: S.me.municipio };
    const spot = result.home || (window.Hogar && Hogar.stand(id));
    window.LIFE_OVNI = spot;
    window.LIFE_WANT_INTRO = window.Hogar ? Hogar.entryMode(true) : 'ovni';
    if (window.Hogar) Hogar.closePicker();
    document.body.classList.remove('eligiendo-casa');
    startGame();
  } catch (error) {
    buttons.forEach(b => { b.disabled = false; });
    if (status) status.textContent = error.message;
  }
}
function launchRide(kind, x, y, name) {
  if (name) window.LIFE_LAND_NAME = name;
  mostrarLeyenda(name || window.LIFE_LAND_NAME || 'el valle', true);
  const go = () => {
    const view = window.LIVE3D;
    if (!view) return false;
    if (kind === 'ovni' && view.startOvni) { view.startOvni(x, y); return true; }
    if (kind === 'heli' && view.startHeli) { view.startHeli(x, y); return true; }
    if (kind === 'land' && view.startLanding) { view.startLanding(x, y, name || window.LIFE_LAND_NAME); return true; }
    return false;
  };
  const later = () => {
    if (go()) return;
    let n = 0;
    const id = setInterval(() => {
      n += 1;
      if (go()) { clearInterval(id); return; }
      if (n > 40) { clearInterval(id); ocultarLeyenda(); if (window.Tutorial) Tutorial.afterFly(); }
    }, 100);
  };
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(() => requestAnimationFrame(later));
  else later();
}
function placeAtTown(spot) {
  if (!spot) return;
  if ((W.mapId || 'city') !== 'city' && cityMap) switchMap('city');
  const p = S.player;
  p.x = p.fx = spot.x; p.y = p.fy = spot.y; p.dir = 'down';
  p.path = []; p.pending = null; p.busyUntil = 0; S.dest = null;
}
let started = false, reconnectTimer = null, reconnectDelay = 1000;
function startGame() {
  if (started) return;
  if (window.Vida && !Vida.allowsConnect()) { Vida.queueConnect(startGame); return; }
  started = true;
  document.body.classList.add('in-game'); $('#b-descansar').hidden = false; updateSkateButton(); $('#login-status').textContent = '';
  $('#login').hidden = true; S.keys.clear();
  $('#mi-nombre').textContent = nombrePropio(); drawPortrait();
  const mid = S.me.municipio || (S.sessionUser && S.sessionUser.municipio) || '';
  const home = mid && window.Hogar ? Hogar.stand(mid) : null;
  const trip = (window.Llegada ? Llegada.plan({
    autotest: AUTOTEST,
    intro: window.LIFE_WANT_INTRO,
    x: window.LIFE_OVNI && window.LIFE_OVNI.x,
    y: window.LIFE_OVNI && window.LIFE_OVNI.y,
    municipio: mid,
    hx: home && home.x,
    hy: home && home.y,
    flew: !!localStorage.getItem('lifeinc.vuelo.v1'),
  }) : { kind: 'none' });
  const ovni = !window.LIFE_PARTIDA && trip.kind === 'ovni';
  const heliSpot = !window.LIFE_PARTIDA && trip.kind === 'heli' ? { x: trip.x, y: trip.y } : null;
  let fly = false;
  if (window.LIFE_PARTIDA) {
    fly = false;
  } else if (ovni) {
    placeAtTown({ x: trip.x, y: trip.y });
    launchRide('ovni', trip.x, trip.y, (window.LIFE_OVNI && window.LIFE_OVNI.name) || 'tu parque');
  } else if (heliSpot) {
    placeAtTown(heliSpot);
    window.LIFE_WANT_INTRO = 'heli';
    window.LIFE_HELI = heliSpot;
    launchRide('heli', heliSpot.x, heliSpot.y, (home && home.name) || 'tu parque');
  } else {
    const fav = window.Lugares && S.sessionUser ? Lugares.get(S.sessionUser.favoritePlace) : null;
    if (fav && fav.kind === 'poi') {
      placeAtTown(fav);
      if (!AUTOTEST) launchRide('land', fav.x, fav.y, fav.name);
    } else {
    fly = !AUTOTEST && !Q.has('forja') && !localStorage.getItem('lifeinc.vuelo.v1');
    if (fly) {
      if ((W.mapId || 'city') === 'casa') switchMap('city');
      const stand = window.Casa.PARK_STAND;
      S.player.x = S.player.fx = stand.x; S.player.y = S.player.fy = stand.y; S.player.dir = 'up';
      window.LIFE_LAND_NAME = 'Parque de Envigado';
      window.LIFE_WANT_FLY = true;
      mostrarLeyenda('Parque de Envigado', true);
      if (window.LIVE3D && LIVE3D.startFly) LIVE3D.startFly();
    } else beginAtHome();
    }
  }
  Casa.load(S.me.name);
  if (!window.LIFE_PARTIDA && !fly && !ovni && !mid && (W.mapId || 'city') === 'casa') placeAtHouseSpawn();
  sys(`Saimon City. Valle de Aburrá, 1777. Hola, ${esc(nombrePropio())}.`);
  connect(); updateTutorial(true);
  if (!fly && !ovni && !heliSpot && window.Tutorial) Tutorial.afterFly();
  if (Q.has('forja')) showForgePreview();
}
function showForgePreview(){
  if ((W.mapId || 'city') !== 'mine') switchMap('mine');
  const n = S.nodes.get('horno_cantera'); if (!n) return;
  S.player.x = S.player.fx = n.def.x; S.player.y = S.player.fy = n.def.y + 1; S.player.path = [];
  for (const [id, qty] of [['mineral_cobre', 9], ['mineral_plata', 8], ['mineral_oro', 10]]) if (invCount(id) < qty) invAdd(id, qty - invCount(id));
  openFurnace(n);
}

function rest() {
  if (!started) return;
  if (!save()) { $('#rest-status').textContent = 'No se pudo guardar. Libera espacio y vuelve a intentar.'; return; }
  closeForgeChat();pendingFurnaceDrop=null;if(oreDrag||touchOre)endOreDrag();
  started = false; clearTimeout(reconnectTimer);
  S.keys.clear(); S.player.path=[]; S.player.pending=null; S.player.busyUntil=0;
  S.player.fx=S.player.x; S.player.fy=S.player.y; S.dest=null; S.dialog=null;
  const ws=S.net.ws; S.net.ws=null; S.net.ok=false;
  if (ws) { ws.onopen=ws.onmessage=ws.onclose=ws.onerror=null; ws.close(1000,'Descansar'); }
  S.others.clear(); S.bubbles.clear(); S.floaters=[]; renderNearby();
  $('#ping').classList.remove('ok'); $('#ping span').textContent='sin conexión';
  for (const id of ['ayuda','w-inv','w-hab','p-misiones','p-cercanos','dialogo','aviso','objetivo','tooltip','world-routes','memories','city-map','furnace-panel']) { const el=document.getElementById(id); if(el) el.hidden=true; }
  window.ChatUI?.setOpen(false); document.activeElement?.blur();
  Casa.setEditing(false);
  document.body.classList.remove('in-game'); $('#b-descansar').hidden=true;
  $('#rest-status').textContent=''; $('#login-status').textContent='Progreso guardado. Puedes volver a entrar.';
  $('#login').hidden=false; $('#login-form button[type=submit]').focus();
}
$('#b-descansar').onclick=irACasaAstral;
addEventListener('pagehide',()=>{ if(started) save(); });

const MAP_FIELDS=['width','height','ground','collision','elevation','nodes','npcs','doors','animals','regions','waypoints','roads3d','memories','riverLayouts','bridges','parkDetails','surfaceZones','signs3d','scenery3d','waterBodies','decorations','landmarks','areas','spawn','bridge4Sur'];
let cityMap=null,caveMap=null,casaMap=null,cityNodes=null,caveNodes=null,casaNodes=null,cityAnimals=null,cityReturn=null;
function prepareCave(){
 const palmas=W.waypoints.find(p=>p.id==='las_palmas');let entry=null;
 for(let r=2;r<10&&!entry;r++)for(let dx=-r;dx<=r&&!entry;dx++)for(let dy=-r;dy<=r&&!entry;dy++){const x=palmas.x+dx,y=palmas.y+dy;if(x>1&&y>1&&x<W.width-1&&y<W.height-1&&W.collision[y][x]===0&&W.collision[y+1][x]===0&&!W.nodes.some(n=>n.x===x&&n.y===y))entry={x,y};}
 if(!entry)throw Error('No hay acceso a la mina en Las Palmas');
 W.nodes.push({id:'entrada_mina_palmas',type:'mine_entrance',...entry,initialState:'active',states:['active'],sprites:{active:'mine_portal'},solid:true});
 const signHere=(x,y)=>x>1&&y>1&&x<W.width-1&&y<W.height-1&&W.collision[y]&&W.collision[y][x]===0;
 const sign=signHere(entry.x+1,entry.y+1)?{x:entry.x+1,y:entry.y+1}:signHere(entry.x-1,entry.y+1)?{x:entry.x-1,y:entry.y+1}:{x:entry.x+1,y:entry.y};
 W.nodes.push({id:'letrero_palmas',type:'mine_sign',x:sign.x,y:sign.y,solid:false,facing:0,initialState:'active',states:['active'],sprites:{active:'mine_portal'}});
 W.waypoints.push({id:'cantera',name:'Mina de Las Palmas · entrada',x:entry.x,y:entry.y+1});
 W.sprites.mine_portal={...W.sprites.rock_piedra};W.sprites.mine_exit={...W.sprites.rock_piedra};
 cityMap=Object.fromEntries(MAP_FIELDS.map(k=>[k,W[k]]));
 const width=36,height=32,ground=Array.from({length:height},()=>Array(width).fill(W.ground[palmas.y][palmas.x])),collision=Array.from({length:height},(_,y)=>Array.from({length:width},(_,x)=>x<2||y<2||x>33||y>29?1:0)),elevation=Array.from({length:height},()=>Array(width).fill(0));
 const nodes=[{id:'salida_mina',type:'mine_exit',x:18,y:29,initialState:'active',states:['active'],sprites:{active:'mine_exit'},solid:true},{id:'letrero_salida',type:'mine_sign',x:19,y:28,solid:false,facing:Math.PI,initialState:'active',states:['active'],sprites:{active:'mine_exit'}},{id:'horno_cantera',type:'furnace',x:18,y:15,solid:true,states:['active'],initialState:'active',sprites:{active:'furnace'}},{id:'baul_mina',type:'mine_chest',x:15,y:16,solid:true,states:['active'],initialState:'active',sprites:{active:'mine_exit'}}];
 const layout={cobre:[[6,6],[9,4],[5,12],[8,22],[12,8]],plata:[[27,5],[30,10],[28,22],[24,9]],oro:[[5,3],[17,3],[28,3],[32,17],[3,18],[24,27]]};
 for(const [metal,coords] of Object.entries(layout))coords.forEach(([x,y],i)=>nodes.push({id:'mina_'+metal+'_'+i,type:'mineral_rock',mineral:metal,x,y,skill:'mining',method:'terrestre',tool:'pico',solid:true,states:['active','depleted'],initialState:'active',sprites:{active:'rock_'+metal,depleted:'rock_depleted'},yield:{item:'mineral_'+metal,min:2,max:metal==='oro'?3:4},xp:metal==='oro'?26:metal==='plata'?18:12,respawnMs:metal==='oro'?32000:18000}));
 const rocks=[[10,13],[26,15],[12,21],[22,23],[8,17],[28,26],[16,7]];for(const [x,y] of rocks){collision[y][x]=1;}
 for(const n of nodes)if(n.type!=='mine_sign')collision[n.y][n.x]=1;
 caveMap={width,height,ground,collision,elevation,nodes,npcs:[],doors:[],animals:[],regions:[{id:'mina_palmas',name:'Mina de Las Palmas · interior',x:0,y:0,w:width,h:height}],waypoints:[{id:'horno',name:'Horno central',x:18,y:17},{id:'salida',name:'Salida a Las Palmas',x:18,y:28}],roads3d:[],memories:[],riverLayouts:[],bridges:[],parkDetails:[],surfaceZones:[],signs3d:[],scenery3d:[],waterBodies:{},decorations:[],landmarks:[],areas:[],spawn:{x:18,y:27},rocks};
 W.caveDefinition=caveMap;W.cityDefinition=cityMap;W.mineEntrance=entry;
 const home=window.Casa.PARK_DOOR;
 W.collision[home.y][home.x]=1;
 W.nodes.push({id:'puerta_casa',type:'home_door',x:home.x,y:home.y,initialState:'active',states:['active'],sprites:{active:'home_door'},solid:true});
 W.sprites.home_door={...W.sprites.rock_piedra};
 W.signs3d=W.signs3d||[];
 W.signs3d.push({text:'TU CASA · PARQUE DE ENVIGADO',x:home.x+2,y:home.y-1});
 W.signs3d.push({text:'MINA',x:entry.x+2,y:entry.y});
 const mineFrom=[W.spawn,window.Casa.PARK_STAND].filter(spot=>spot&&Number.isFinite(spot.x));
 const seenSigns=new Set();
 const openTile=(x,y)=>x>0&&y>0&&x<W.width-1&&y<W.height-1&&W.collision[y]&&W.collision[y][x]===0;
 for(const from of mineFrom){
  const key=(x,y)=>y*W.width+x;
  const prev=new Map([[key(from.x,from.y),null]]);
  const queue=[[from.x,from.y]];
  let found=null;
  for(let i=0;i<queue.length&&i<90000;i++){
   const [x,y]=queue[i];
   if(Math.max(Math.abs(x-entry.x),Math.abs(y-entry.y))<=1){found=key(x,y);break;}
   for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){
    const nx=x+dx,ny=y+dy;
    if(!openTile(nx,ny)||prev.has(key(nx,ny)))continue;
    prev.set(key(nx,ny),key(x,y));
    queue.push([nx,ny]);
   }
  }
  if(found==null)continue;
  const trail=[];
  let k=found;
  while(k!==key(from.x,from.y)){trail.unshift([k%W.width,Math.floor(k/W.width)]);k=prev.get(k);}
  for(let i=16;i<trail.length-8;i+=28){
   const [sx,sy]=trail[i];
   const id=sx+','+sy;
   if(seenSigns.has(id))continue;
   seenSigns.add(id);
   W.signs3d.push({text:'MINA',x:sx,y:sy});
   if(seenSigns.size>=7)break;
  }
 }
 if (cityMap) cityMap.signs3d = W.signs3d;
 W._destinos=null;
 destinosLocales();
 W.homeDoor={x:home.x,y:home.y,standX:window.Casa.PARK_STAND.x,standY:window.Casa.PARK_STAND.y};
 if (window.EnvigadoPark) EnvigadoPark.block(W);
 if (window.Banco) Banco.stamp(W);
 if (window.Central) Central.stamp(W);
}
function applyCasaLayout(){
 if((W.mapId||'city')!=='casa')return;
 const map=Casa.buildMap(Casa.layout);
 W.collision=map.collision; W.ground=map.ground; casaMap=map;
 const p=S.player;
 if(!walkable(p.x,p.y)){p.x=p.fx=Casa.SPAWN.x;p.y=p.fy=Casa.SPAWN.y;p.path=[];}
 drawMinimapBase();
}
function greetPet(){
 S.petGreetUntil = performance.now() + 2200;
 const pet = S.pet;
 if (pet && pet.species === 'cat') game(pet.name ? '<b>' + esc(pet.name) + '</b> maúlla.' : 'Tu gato maúlla.');
 else if (pet && pet.species === 'dog') game(pet.name ? '<b>' + esc(pet.name) + '</b> mueve la cola.' : 'Tu perro mueve la cola.');
}
function enterHouse(){
 if((W.mapId||'city')==='mine'){game('Sal de la mina antes de volver a casa.','aviso');return;}
 if((W.mapId||'city')==='casa'){greetPet();return;}
 Casa.load(S.me.name);
 S.portalUntil=now()+800;
 switchMap('casa');
}
function irACasa(){
 if (S.mounted && window.Simulacion) Simulacion.dismount();
 if ((W.mapId||'city')==='casa') { greetPet(); return; }
 Casa.load(S.me.name);
 S.portalUntil=now()+800;
 switchMap('casa');
}
let astralTimer = 0;
function finishAstral(){
 clearTimeout(astralTimer);
 astralTimer = 0;
 const veil = document.getElementById('astral');
 if (veil) veil.hidden = true;
 if ((W.mapId || 'city') !== 'casa') irACasa();
 rest();
}
function irACasaAstral(){
 if (!started) return;
 if (S.mounted && window.Simulacion) Simulacion.dismount();
 const veil = document.getElementById('astral');
 const caption = veil && veil.querySelector('p');
 if (caption) caption.textContent = 'Aterrizando en tu casa';
 if (!veil) { if ((W.mapId || 'city') !== 'casa') irACasa(); rest(); return; }
 veil.hidden = false;
 clearTimeout(astralTimer);
 astralTimer = setTimeout(finishAstral, 1500);
}
function mostrarLeyenda(name, intro){
 const el = document.getElementById('viaje-leyenda');
 const pasos = document.getElementById('viaje-pasos');
 const titulo = name || 'el valle';
 if (el) { el.hidden = false; el.textContent = 'Aterrizando en ' + titulo; }
 if (pasos) pasos.hidden = !intro;
 const skip = document.getElementById('ovni-saltar');
 if (skip) skip.hidden = false;
}
function ocultarLeyenda(){
 const el = document.getElementById('viaje-leyenda');
 const pasos = document.getElementById('viaje-pasos');
 if (el) el.hidden = true;
 if (pasos) pasos.hidden = true;
 const skip = document.getElementById('ovni-saltar');
 if (skip) skip.hidden = true;
}
window.mostrarLeyenda = mostrarLeyenda;
window.ocultarLeyenda = ocultarLeyenda;
const astralVeil = document.getElementById('astral');
if (astralVeil) {
  astralVeil.addEventListener('click', (event) => {
    if (event.target.id === 'astral' || event.target.id === 'astral-saltar') finishAstral();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && astralTimer) { event.preventDefault(); finishAstral(); }
  });
}
function exitHouse(){
 if((W.mapId||'city')!=='casa')return;
 S.portalUntil=now()+900;
 if(window.LIVE3D){const off=window.Casa.VALLE_OFFSET||{x:0,y:0};window.LIVE3D.lookAt={x:239+off.x,y:69+off.y};}
 switchMap('city');
}
function switchMap(id,restored=false){
 if(!cityMap)return;
 const prev=W.mapId||'city';
 if(id==='central' && !(window.LiveInk && LiveInk.state && LiveInk.state.canMintIngots)){
  game('El Banco Central es un recinto del personal. Esta cuenta no entra.','aviso');
  if(prev!=='central') return;
  id='city';
 }
 if(id===prev)return;
 if(prev==='mine')caveNodes=S.nodes;
 if(prev==='casa')casaNodes=S.nodes;
 if(prev==='city'){cityNodes=S.nodes;cityAnimals=S.animals;if(!restored)cityReturn={x:S.player.x,y:S.player.y};}
 if(id==='mine'){Object.assign(W,caveMap);W.mapId='mine';if(!caveNodes)caveNodes=new Map(W.nodes.map(n=>[n.id,{def:n,state:n.initialState,until:0,crop:null}]));S.nodes=caveNodes;S.animals=[];}
 else if(id==='casa'){casaMap=Casa.buildMap(Casa.layout);Object.assign(W,casaMap);W.mapId='casa';casaNodes=new Map(W.nodes.map(n=>[n.id,{def:n,state:n.initialState,until:0,crop:null}]));S.nodes=casaNodes;S.animals=[];}
 else if(id==='banco'){const bancoMap=Banco.buildMap();Object.assign(W,bancoMap);W.mapId='banco';S.nodes=new Map(W.nodes.map(n=>[n.id,{def:n,state:n.initialState,until:0,crop:null}]));S.animals=[];}
 else if(id==='central'){const centralMap=Central.buildMap();Object.assign(W,centralMap);W.mapId='central';S.nodes=new Map(W.nodes.map(n=>[n.id,{def:n,state:n.initialState,until:0,crop:null}]));S.animals=[];}
 else {Object.assign(W,cityMap);W.mapId='city';S.nodes=cityNodes;S.animals=cityAnimals;id='city';}
 const p=S.player;
 let xy;
 if(id==='mine')xy=caveMap.spawn;
 else if(id==='casa')xy={x:Casa.SPAWN.x,y:Casa.SPAWN.y};
 else if(id==='banco')xy={x:Banco.SPAWN.x,y:Banco.SPAWN.y};
 else if(id==='central')xy={x:Central.SPAWN.x,y:Central.SPAWN.y};
 else if(prev==='mine')xy=cityReturn||{x:W.mineEntrance.x,y:W.mineEntrance.y+1};
 else if(prev==='casa'){const mid=S.me.municipio;const home=window.Hogar&&mid&&mid!=='envigado'?Hogar.stand(mid):null;xy=home?{x:home.x,y:home.y}:{x:Casa.PARK_STAND.x,y:Casa.PARK_STAND.y};}
 else if(prev==='banco')xy={x:Banco.OUTSIDE.x,y:Banco.OUTSIDE.y};
 else if(prev==='central')xy={x:Central.OUTSIDE.x,y:Central.OUTSIDE.y};
 else xy={x:p.x,y:p.y};
 p.x=p.fx=xy.x;p.y=p.fy=xy.y;if(id==='casa')p.dir=Casa.SPAWN.dir;if(id==='banco')p.dir=Banco.SPAWN.dir;if(id==='central')p.dir=Central.SPAWN.dir;
 p.path=[];p.pending=null;p.busyUntil=0;S.dest=null;S.keys.clear();S.sel=-1;
 for(const key of ['furnace-panel','world-routes','memories','city-map','aviso','objetivo']){const el=document.getElementById(key);if(el)el.hidden=true;}
 closeForgeChat();pendingFurnaceDrop=null;if(oreDrag||touchOre)endOreDrag();
 S.hover=null;S.floaters=[];S.bubbles.clear();
 document.body.classList.toggle('in-mine',id==='mine');
 document.body.classList.toggle('in-casa',id==='casa');
 document.body.classList.toggle('in-banco',id==='banco');
 document.body.classList.toggle('in-central',id==='central');
 document.body.dataset.zone=id;
 if(id!=='casa'&&window.Casa)Casa.setEditing(false);
 const mundo=window.Vida?Vida.world():3;
 const zoneLabel=id==='casa'?'Tu casa · Medellín':id==='mine'?('Mina de Las Palmas · Mundo '+mundo):id==='banco'?'Casa bancaria':id==='central'?'Banco Central':null;
 if(zoneLabel){$('#zona-nombre').textContent=zoneLabel;}
 drawMinimapBase();
 if(!restored){
  save();
  if(id==='mine')game('Pica el metal. En el horno, Acuñar lo guarda como monedas en tu inventario. Estás en el Mundo '+(window.Vida?Vida.world():3)+'. Aquí se ven y pueden hablar quienes estén en este mismo mundo.');
  else if(id==='city'&&prev==='mine')game('Sales de la mina y vuelves a Las Palmas.');
  else if(id==='casa'){ greetPet(); game('Estás en casa. Tu mascota te espera.'); }
  else if(id==='city'&&prev==='casa')game('Sales al <b>Parque de Envigado</b>. El botón Casa te devuelve a tu casa.');
  else if(id==='banco')game('Entras a la Casa bancaria. El mostrador atiende el banquero. El banquito guarda SMC y objetos: no se pierden si caes.');
  else if(id==='city'&&prev==='banco')game('Sales de la Casa bancaria, junto al Parque de Envigado.');
  else if(id==='central')game('Entras al Banco Central.');
  else if(id==='city'&&prev==='central')game('Sales del Banco Central.');
 }
 S.others.clear();
 renderNearby();
 if(S.net.ok){sendMove(true); if(S.net.ws){S.net.ws.send(JSON.stringify({t:'cerca'})); S.net.ws.send(JSON.stringify({t:'nodos'}));}}
}

// ---------------- cantera y fundición ----------------
function prepareMining(){
 W.items.pico.name='Pica de minería';NOMBRES.oro='Roca de oro';
 for(const metal of ['cobre','plata','oro']){
  const raw='mineral_'+metal,ingot='lingote_'+metal;
  if(!W.items[raw])W.items[raw]={...W.items.mineral_cobre,id:raw,name:'Mineral de oro sin refinar'};
  W.items[raw].name='Mineral de '+metal+' sin refinar';
  W.items[raw].icon={'16':'graphics/mining/'+raw+'.svg','32':'graphics/mining/'+raw+'.svg','64':'graphics/mining/'+raw+'.svg'};
  const bar={ '16':'graphics/mining/'+ingot+'.svg','32':'graphics/mining/'+ingot+'.svg','64':'graphics/mining/'+ingot+'.svg' };
  const pile={ '16':'graphics/mining/'+ingot+'_pila.svg','32':'graphics/mining/'+ingot+'_pila.svg','64':'graphics/mining/'+ingot+'_pila.svg' };
  W.items[ingot]={id:ingot,name:'Lingote de '+metal,category:'ingot',stackable:true,maxStack:999,icon:bar,iconStack:pile};
  const coin='moneda_'+metal;
  const face={ '16':'graphics/mining/'+coin+'.svg','32':'graphics/mining/'+coin+'.svg','64':'graphics/mining/'+coin+'.svg' };
  const coins={ '16':'graphics/mining/'+coin+'_pila.svg','32':'graphics/mining/'+coin+'_pila.svg','64':'graphics/mining/'+coin+'_pila.svg' };
  W.items[coin]={id:coin,name:'Moneda de '+metal,category:'coin',stackable:true,maxStack:999,icon:face,iconStack:coins};
 }
 W.skills.mining.learn='Usa la pica sobre vetas de cobre, plata y oro. Cada extracción da experiencia y los minerales se apilan en la mochila.';
 W.skills.mining.methods.terrestre.minerals=['piedra','cobre','plata','oro'];
 W.skills.smelting={name:'Fundición',verb:'Fundir minerales',learn:'En el horno, Acuñar cambia el mineral por Simoncoin. El libro mayor acredita el saldo.'};
 if(W.skills.order&&!W.skills.order.includes('smelting'))W.skills.order.push('smelting');
 W.skills.skate={name:'Patinaje',verb:'Patinar',learn:'En el Skate Park de la 4 Sur se recoge la patineta. Sobre la pista, patinar da experiencia. Todavía no hay trucos.'};
 if(W.skills.order&&!W.skills.order.includes('skate'))W.skills.order.push('skate');
 const icon={ '16':'graphics/icons/skate_icon.svg','32':'graphics/icons/skate_icon.svg','64':'graphics/icons/skate_icon.svg' };
 W.items.patineta={id:'patineta',name:'Patineta',category:'ride',stackable:false,maxStack:1,icon};
 const park=window.SKATE_4_SUR&&window.SKATE_4_SUR.placement;
 if(park)for(let y=park.y;y<park.y+park.h;y++)for(let x=park.x;x<park.x+park.w;x++){if(W.tiles[String(W.ground[y][x])].kind==='water')continue;W.ground[y][x]=104;W.collision[y][x]=0;}
 W.sprites.rock_oro={...W.sprites.rock_cobre};W.sprites.furnace={...W.sprites.rock_piedra};
 const taken=new Set([...W.nodes,...W.npcs,...W.doors].map(n=>`${n.x},${n.y}`));
 function spot(cx,cy){for(let r=0;r<16;r++)for(let dy=-r;dy<=r;dy++)for(let dx=-r;dx<=r;dx++){if(Math.max(Math.abs(dx),Math.abs(dy))!==r)continue;const x=cx+dx,y=cy+dy;if(x<1||y<1||x>=W.width-1||y>=W.height-1||W.collision[y][x]!==0||taken.has(`${x},${y}`))continue;if(![[1,0],[-1,0],[0,1],[0,-1]].some(([a,b])=>W.collision[y+b][x+a]===0))continue;taken.add(`${x},${y}`);return {x,y};}throw Error('No se encontró espacio para la cantera');}
 prepareCave();
}
let furnaceNode=null;
function setupMiningUI(){
 const panel=document.createElement('section');panel.id='furnace-panel';panel.className='ventana';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Horno de fundición');panel.innerHTML='<header>Horno de la cantera <button id="furnace-close" aria-label="Cerrar horno">×</button></header><div class="forge-content"><p>El horno acuña sólo Simoncoin. No se puede pasar de 21.000.000.</p><ul id="forge-recipes"></ul><div id="forge-pair" class="forge-outputs"></div><label>Mineral<select id="forge-ore"></select></label><div id="forge-stock"></div><label>Lotes <input id="forge-batches" type="number" min="1" step="1" value="1"></label><div class="forge-presets"><button id="forge-one" type="button">1 lote</button><button id="forge-all" type="button">Máximo</button></div><p id="forge-preview" aria-live="polite"></p><div id="forge-progress" hidden><div id="forge-progress-bar"></div><p id="forge-progress-label">Fundiendo…</p></div><div class="forge-actions"><button id="forge-coin" type="button">Acuñar monedas</button><button id="forge-coins" class="forge-mint" type="button"><img src="../graphics/mining/moneda_oro.svg?v=vidrio-r1" alt=""> Acuñar SMC</button></div><p id="forge-result" role="status"></p><p id="forge-made"></p></div>';document.body.append(panel);
 for(const [id,r] of Object.entries(MiningRules.recipes)){const o=document.createElement('option');o.value=id;o.textContent=W.items[id].name;$('#forge-ore').append(o);}
 $('#furnace-close').onclick=()=>panel.hidden=true;
 $('#forge-ore').onchange=$('#forge-batches').oninput=renderForge;
 $('#forge-one').onclick=()=>{$('#forge-batches').value=1;renderForge();};$('#forge-all').onclick=()=>{const id=$('#forge-ore').value;$('#forge-batches').value=Math.max(1,Math.floor(invCount(id)/MiningRules.recipes[id].ore));renderForge();};
 $('#forge-coin').onclick=()=>smelt('coin');$('#forge-coins').onclick=()=>smelt($('#forge-coins').dataset.mode||'coins');
 const why=document.createElement('p');why.id='forge-mint-why';why.setAttribute('role','status');panel.querySelector('.forge-actions').before(why);
 for(const [id,r] of Object.entries(MiningRules.recipes)){if(id==='pepita_oro')continue;const li=document.createElement('li');li.className='forge-recipe';li.innerHTML=`${itemImg(W.items[id],1,'ore-art')}${itemImg(W.items[r.coinItem],r.coinQty,'ore-art')}<span>${esc(r.name)}: ${r.ore} minerales. El horno paga Simoncoin.</span>`;$('#forge-recipes').append(li);}
 const intro=document.createElement('p');intro.className='bag-note';intro.textContent='60 casillas · pilas de 999 · arrastra mineral al horno';$('#inventario').before(intro);
 const modes=document.createElement('div');modes.id='bag-modes';modes.innerHTML='<button id="bag-summary" type="button">Resumen 4×6</button><button id="bag-full" type="button">Completo</button>';$('#w-inv header').append(modes);$('#bag-summary').onclick=()=>setBagMode('summary');$('#bag-full').onclick=()=>setBagMode('full');
 const pages=document.createElement('nav');pages.id='bag-pages';pages.setAttribute('aria-label','Páginas del inventario resumido');pages.innerHTML='<button type="button" id="bag-prev" aria-label="Página anterior del inventario">‹</button><span id="bag-page-label"></span><button type="button" id="bag-next" aria-label="Página siguiente del inventario">›</button>';$('#inventario').after(pages);$('#bag-prev').onclick=()=>{bagPage=Math.max(0,bagPage-1);renderInv();};$('#bag-next').onclick=()=>{bagPage=Math.min(Math.ceil(SLOTS/24)-1,bagPage+1);renderInv();};
 setupBagForge();updateBagMode();renderInv();
 const guide=document.createElement('button');guide.id='mine-route';guide.textContent='Ir a la mina';guide.className='hud';guide.onclick=()=>irALaMina();document.body.append(guide);
 const chip=document.createElement('button');chip.id='mina-brujula';chip.type='button';chip.hidden=true;chip.innerHTML='<span id="mina-flecha" aria-hidden="true">➤</span><span id="mina-texto">Mina</span>';chip.onclick=()=>irALaMina();document.body.append(chip);
 const enter=document.createElement('button');enter.id='mine-enter';enter.className='hud';enter.type='button';enter.hidden=true;enter.textContent='⛏ Entrar a la mina';enter.onclick=()=>{const e=S.nodes.get('entrada_mina_palmas');if(started&&W.mapId!=='mine'&&e)approach({kind:'node',n:e});};document.body.append(enter);
 const exit=document.createElement('button');exit.id='mine-exit-route';exit.className='hud';exit.textContent='↗ Salir a Las Palmas';exit.onclick=()=>{if(started&&W.mapId==='mine')approach({kind:'node',n:S.nodes.get('salida_mina')});};document.body.append(exit);
 const jay=document.createElement('button');jay.id='mina-mundo-jay';jay.type='button';jay.className='hud';jay.textContent='Ir al mundo de Jay';jay.onclick=()=>{if(!S.net.ok||!S.net.ws){game('Entra al mundo para cambiar de sala.','aviso');return;}const aqui=window.Vida?Vida.world():3;if(aqui===5){game('Ya estás en el Mundo 5, el de Jay.','juego');return;}try{sessionStorage.setItem('lifeinc.mundo','5');}catch(e){}S.net.ws.send(JSON.stringify({t:'mundo',id:5}));game('Vas al Mundo 5, el de Jay. En la mina se ven quienes estén en ese mismo mundo.','juego');};document.body.append(jay);
}
function openFurnace(n){furnaceNode=n;if(pendingFurnaceDrop?.nodeId===n.def.id){pendingFurnaceDrop=null;}closeForgeChat();if(window.Acunar){Acunar.open();return;}const id=selected();if(MiningRules.recipes[id])$('#forge-ore').value=id;$('#forge-result').textContent='';$('#furnace-panel').hidden=false;renderForge();}
let forgeTimer=0;
function forgeWait(){return matchMedia('(prefers-reduced-motion: reduce)').matches?160:1100;}
function showForgeProgress(){const box=$('#forge-progress');if(!box)return;box.hidden=false;$('#forge-progress-label').textContent='Acuñando Simoncoin…';$('#forge-progress-bar').innerHTML='<i></i>';}
function hideForgeProgress(){const box=$('#forge-progress');if(box)box.hidden=true;}
function forgeBagLine(){const parts=[];for(const id of ['moneda_cobre','moneda_plata','moneda_oro']){const n=invCount(id);if(n&&W.items[id])parts.push(n+' × '+W.items[id].name);}return parts.length?'En la mochila: '+parts.join(', ')+'.':'En la mochila todavía no hay monedas acuñadas.';}
function renderForge(){if(!$('#forge-ore'))return;const id=$('#forge-ore').value,r=MiningRules.recipes[id],q=Number($('#forge-batches').value),max=Math.floor(invCount(id)/r.ore),valid=Number.isSafeInteger(q)&&q>0&&q<=max;
 const coinQty=q*(r.coinQty||0),coinName=W.items[r.coinItem]?W.items[r.coinItem].name:'monedas';
 $('#forge-stock').textContent=`En mochila: ${invCount(id)} · ${r.ore} minerales por lote · disponibles: ${max} lotes`;
 $('#forge-batches').max=Math.max(1,max); $('#forge-preview').innerHTML=valid?`${itemImg(W.items[id],q,'ore-art')} ${q*r.ore} minerales → ${itemImg(W.items[r.coinItem],coinQty,'ore-art')} ${coinQty} ${esc(coinName)}. El horno pide la prueba y el servidor guarda Simoncoin.`:`Reúne al menos ${r.ore} minerales y elige una cantidad disponible.`;
 const pair=$('#forge-pair'); if(pair) pair.innerHTML=`<figure>${itemImg(W.items[r.coinItem],Math.max(1,coinQty))}<figcaption>${Math.max(0,coinQty)} ${esc(coinName)}</figcaption></figure>`;
 const busy=!!forgeTimer;const blocked=!valid||busy;
 $('#forge-coin').disabled=blocked;
 const mint=$('#forge-coins');
 const coinBtn=$('#forge-coin'); if(coinBtn) coinBtn.hidden=true;
 const metal=r.metal;
 const mintMode=metal==='plata'?'simonplata':metal==='cobre'?'simonchis':'simoncoin';
 const mintLabels={simoncoin:'Acuñar Simoncoin',simonplata:'Acuñar Simoncoin',simonchis:'Acuñar Simoncoin'};
 const mintName='Simoncoin';
 mint.dataset.mode=mintMode;
 mint.classList.toggle('forge-mint',true);
 mint.disabled=blocked;
 mint.innerHTML=`<img src="../graphics/mining/moneda_${metal}.svg?v=vidrio-r1" alt=""> ${mintLabels[mintMode]}`;
 const why=$('#forge-mint-why');
 if(why){
   if(busy)why.textContent='El horno está trabajando.';
   else if(!valid){
     const have=invCount(id);
     why.textContent=`Faltan minerales de ${r.name.toLowerCase()}. Hacen falta ${r.ore} y tienes ${have}.`;
   }else why.textContent=`Acuñar ${mintName} gasta el mineral y guarda las monedas en el servidor. Si ya se llegó al máximo, no se crea ni una más.`;
 }
 if($('#forge-made'))$('#forge-made').textContent=forgeBagLine();
}
function applySmelt(id,q,mode,result){
 const previous={inv:S.inv,xp:{...S.xp},sel:S.sel};
 S.inv=result.inv;S.xp.smelting=(S.xp.smelting||0)+result.xp;S.sel=-1;
 if(!save()){Object.assign(S,previous);return false;}
 S.forgeUntil=now()+1500;renderAll();renderForge();
 const r=MiningRules.recipes[id];
 const made=`${mintNameOf(mode)} en tu saldo`;
 const message=`Listo: entró ${made}. +${result.xp} XP de Fundición.`;
 const box=$('#forge-result'); if(box) box.textContent=message;
 return message;
}
function mintNameOf(){return 'Simoncoin';}
function netMintMode(mode){if(mode==='ingot')return '';if(mode==='simonplata'||mode==='simonchis'||mode==='simoncoin')return mode;if(mode==='coins')return 'simoncoin';return '';}
function finishForge(id,q,mode,result){
 forgeTimer=0;hideForgeProgress();
 const netMode=netMintMode(mode);
 if(netMode && !S.net.ok){$('#forge-result').textContent='Hace falta el servidor para acuñar. El mineral sigue en la mochila.';renderForge();return;}
 if(netMode && S.net.ok){S.pendingSmelt={id,q,mode:netMode,result};S.net.ws.send(JSON.stringify({t:'smelt',ore:id,batches:q,mode:netMode}));$('#forge-result').textContent='El horno pide la prueba antes de acuñar…';renderForge();return;}
 const message=applySmelt(id,q,mode,result);
 const chat=$('#forge-chat-result'); if(chat&&chatForgeItem) chat.textContent=message||'';
 if(message)game(esc(message));
}
function smelt(mode){if(mode==='ingot'||!started||!furnaceNode||forgeTimer)return;const d=furnaceNode.def;if(cheb(S.player.x,S.player.y,d.x,d.y)>1){$('#forge-result').textContent='Acércate al horno para fundir.';return;}
 const id=$('#forge-ore').value,q=Number($('#forge-batches').value),result=MiningRules.smelt(S.inv,W.items,id,q,'coins',SLOTS);if(result.error){$('#forge-result').textContent=result.error;return;}
 showForgeProgress(mode);renderForge();
 $('#forge-result').textContent=$('#forge-progress-label').textContent;
 const chat=$('#forge-chat-result'); if(chat) chat.textContent=$('#forge-progress-label').textContent;
 forgeTimer=setTimeout(()=>finishForge(id,q,mode,result),forgeWait());
}

// Inventory modes and local furnace conversation. No chat message is sent to other players.
const BAG_PAGE_SIZE=24;
let bagMode='summary',bagPage=0,oreDrag=null,touchOre=null,suppressOreClickUntil=0,pendingFurnaceDrop=null,chatForgeItem=null;
try{if(localStorage.getItem('lifeinc.bag.mode')==='full')bagMode='full';}catch{}
function setBagMode(mode){bagMode=mode;bagPage=0;try{localStorage.setItem('lifeinc.bag.mode',mode);}catch{}renderInv();}
function updateBagMode(){const bag=$('#w-inv');bag.classList.toggle('bag-summary',bagMode==='summary');bag.classList.remove('compact-bag');
 for(const [id,mode] of [['bag-summary','summary'],['bag-full','full']]){const b=document.getElementById(id);if(b)b.setAttribute('aria-pressed',String(bagMode===mode));}
 const pager=document.getElementById('bag-pages');if(pager){pager.hidden=bagMode!=='summary';$('#bag-page-label').textContent=`${bagPage*24+1}–${Math.min(SLOTS,(bagPage+1)*24)} de ${SLOTS}`;$('#bag-prev').disabled=bagPage===0;$('#bag-next').disabled=(bagPage+1)*24>=SLOTS;}
}
function beginOreDrag(item,x,y){if(!started||!MiningRules.recipes[item]||!invCount(item))return false;oreDrag={item};window.LiveInk.draggedMineral=item;document.body.classList.add('dragging-ore');const ghost=$('#ore-drag-ghost');ghost.innerHTML=itemImg(W.items[item],invCount(item),'ore-art')+`<span>${esc(W.items[item].name)} · suelta sobre el horno</span>`;ghost.hidden=false;moveOreDrag(x,y);return true;}
function moveOreDrag(x,y){if(!oreDrag)return;const ghost=$('#ore-drag-ghost');ghost.style.left=Math.max(8,Math.min(innerWidth-220,x+14))+'px';ghost.style.top=Math.max(8,y-42)+'px';const id=window.LiveInk.furnaceAtScreen?.(x,y);window.LiveInk.oreDropHovered=!!id;ghost.classList.toggle('valid-drop',!!id);}
function endOreDrag(){oreDrag=null;touchOre=null;window.LiveInk.draggedMineral=null;window.LiveInk.oreDropHovered=false;document.body.classList.remove('dragging-ore');const ghost=document.getElementById('ore-drag-ghost');if(ghost)ghost.hidden=true;suppressOreClickUntil=now()+350;}
function dropOre(x,y){if(!oreDrag)return false;const item=oreDrag.item,id=window.LiveInk.furnaceAtScreen?.(x,y);endOreDrag();if(!id)return false;return requestFurnaceDrop(item,id);}
function requestFurnaceDrop(item,nodeId){const n=S.nodes.get(nodeId);if(!started||n?.def.type!=='furnace'||!MiningRules.recipes[item]||!invCount(item))return false;pendingFurnaceDrop={item,nodeId};selectItem(item);approach({kind:'node',n});return true;}
function wireMineralDrag(slot,item){if(!MiningRules.recipes[item])return;slot.draggable=true;slot.classList.add('draggable-ore');slot.setAttribute('aria-description','Arrastra este mineral al horno para acuñar.');
 slot.ondragstart=e=>{if(!beginOreDrag(item,e.clientX,e.clientY)){e.preventDefault();return;}e.dataTransfer.effectAllowed='copy';e.dataTransfer.setData('application/x-lifeinc-ore',item);e.dataTransfer.setData('text/plain',item);};slot.ondragend=endOreDrag;
 slot.onpointerdown=e=>{if(e.pointerType==='mouse'||!started)return;touchOre={item,id:e.pointerId,x:e.clientX,y:e.clientY,slot};slot.setPointerCapture(e.pointerId);};
 slot.onpointermove=e=>{if(!touchOre||touchOre.id!==e.pointerId)return;if(!oreDrag&&Math.hypot(e.clientX-touchOre.x,e.clientY-touchOre.y)>8)beginOreDrag(item,e.clientX,e.clientY);if(oreDrag){e.preventDefault();moveOreDrag(e.clientX,e.clientY);}};
 slot.onpointerup=e=>{if(!touchOre||touchOre.id!==e.pointerId)return;if(oreDrag){e.preventDefault();dropOre(e.clientX,e.clientY);}else touchOre=null;};slot.onpointercancel=()=>{if(touchOre)endOreDrag();};slot.onlostpointercapture=()=>{if(touchOre)endOreDrag();};
}
function setupBagForge(){
 const ghost=document.createElement('div');ghost.id='ore-drag-ghost';ghost.hidden=true;document.body.append(ghost);
 document.addEventListener('dragover',e=>{if(!oreDrag)return;e.preventDefault();e.dataTransfer.dropEffect=window.LiveInk.furnaceAtScreen?.(e.clientX,e.clientY)?'copy':'none';moveOreDrag(e.clientX,e.clientY);});
 document.addEventListener('drop',e=>{if(!oreDrag)return;e.preventDefault();dropOre(e.clientX,e.clientY);});addEventListener('blur',()=>{if(oreDrag||touchOre)endOreDrag();});
 const card=document.createElement('section');card.id='forge-chat-card';card.hidden=true;card.setAttribute('aria-label','Elegir fundición en el chat');card.innerHTML='<header><b id="forge-chat-title">Horno</b><button type="button" id="forge-chat-cancel" aria-label="Cancelar fundición en chat">×</button></header><p>Puedes acuñar Simoncoin.</p><div id="forge-chat-stock"></div><label>Lotes <input id="forge-chat-batches" type="number" min="1" step="1" value="1"></label><button type="button" id="forge-chat-max">Máximo</button><p id="forge-chat-preview"></p><div class="forge-chat-actions"><button type="button" id="forge-chat-coin">Acuñar monedas</button><button type="button" id="forge-chat-coins" class="forge-mint"><img src="../graphics/mining/moneda_oro.svg?v=vidrio-r1" alt=""> Acuñar Simoncoin</button></div><p id="forge-chat-result" role="status"></p>';
 $('#chat-form').before(card);$('#forge-chat-cancel').onclick=closeForgeChat;$('#forge-chat-batches').oninput=renderForgeChat;
 $('#forge-chat-max').onclick=()=>{if(!chatForgeItem)return;$('#forge-chat-batches').value=Math.max(1,Math.floor(invCount(chatForgeItem)/MiningRules.recipes[chatForgeItem].ore));renderForgeChat();};
 for(const [id,mode] of [['forge-chat-coin','coin'],['forge-chat-coins','coins']])$('#'+id).onclick=()=>{if(!chatForgeItem||mode==='coin')return;const metal=MiningRules.recipes[chatForgeItem].metal;const use=metal==='plata'?'simonplata':metal==='cobre'?'simonchis':'simoncoin';$('#forge-ore').value=chatForgeItem;$('#forge-batches').value=$('#forge-chat-batches').value;smelt(use);renderForgeChat();};const chatCoin=document.getElementById('forge-chat-coin');if(chatCoin)chatCoin.hidden=true;
}
function closeForgeChat(){chatForgeItem=null;const card=document.getElementById('forge-chat-card');if(card)card.hidden=true;$('#hud-chat').classList.remove('forge-chat-open');}
function openForgeChat(item){chatForgeItem=item;$('#furnace-panel').hidden=true;$('#forge-chat-card').hidden=false;$('#hud-chat').classList.add('forge-chat-open');$('#forge-chat-batches').value=1;$('#forge-chat-result').textContent='';renderForgeChat();game(`Horno: trajiste <b>${esc(W.items[item].name)}</b>. Puedes acuñar Simoncoin.`);window.ChatUI?.setOpen(true);}
function renderForgeChat(){if(!chatForgeItem)return;const r=MiningRules.recipes[chatForgeItem],have=invCount(chatForgeItem),q=Number($('#forge-chat-batches').value),max=Math.floor(have/r.ore),valid=Number.isSafeInteger(q)&&q>0&&q<=max;
 $('#forge-chat-title').textContent='Horno · '+r.name;$('#forge-chat-stock').textContent=`Tienes ${have} minerales · ${r.ore} por lote`;
 $('#forge-chat-batches').max=Math.max(1,max); $('#forge-chat-preview').innerHTML=valid?`${itemImg(W.items[chatForgeItem],q,'ore-art')}${itemImg(W.items[r.coinItem],q*r.coinQty,'ore-art')} ${q*r.ore} minerales → ${q*r.coinQty} monedas de ${esc(r.metal)}. Conservas ${have-q*r.ore} minerales.`:`Necesitas al menos ${r.ore} minerales para un lote.`;
 $('#forge-chat-coin').disabled=$('#forge-chat-coins').disabled=!valid||!!forgeTimer;
}

// ---------------- inventario / xp / monedas ----------------
const SLOTS = 60;
function invCount(id) { return S.inv.filter(s => s && s.item === id).reduce((a, s) => a + s.qty, 0); }
function avisarMochilaLlena() {
  let box = document.getElementById('mochila-llena');
  if (!box) {
    box = document.createElement('section');
    box.id = 'mochila-llena';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-label', 'Mochila llena');
    box.innerHTML = '<h2>Tu mochila está llena</h2><p>No se guardó nada en la mochila. El objeto sigue donde estaba.</p><p class="fila"><button type="button" id="mochila-banco">Guardar en el banco</button><button type="button" id="mochila-soltar">Soltar</button><button type="button" id="mochila-vender">Vender</button></p>';
    document.body.append(box);
    box.querySelector('#mochila-banco').onclick = () => elegirMochila('banco');
    box.querySelector('#mochila-soltar').onclick = () => elegirMochila('soltar');
    box.querySelector('#mochila-vender').onclick = () => elegirMochila('vender');
  }
  box.hidden = false;
}
function elegirMochila(op) {
  const box = document.getElementById('mochila-llena');
  if (box) box.hidden = true;
  const espera = S.espera;
  S.espera = null;
  if (S.net && S.net.ok && espera && espera.server) {
    S.net.ws.send(JSON.stringify({ t: 'mochila_op', op }));
    return;
  }
  if (!espera) return;
  if (op === 'soltar') { game('Lo dejaste donde estaba.', 'aviso'); return; }
  if (op === 'banco') {
    S.vault = S.vault || { smcSubs: 0, items: {} };
    S.vault.items = S.vault.items || {};
    S.vault.items[espera.item] = (S.vault.items[espera.item] || 0) + espera.qty;
    save();
    if (espera.done) espera.done('banco');
    game('Quedó en el banco. La mochila no cambió.', 'juego');
    return;
  }
  game('Hace falta el servidor para vender. No se perdió nada.', 'aviso');
}
window.avisarMochilaLlena = avisarMochilaLlena;
function invAdd(id,qty){if(window.Guacharaca&&Guacharaca.blockedItem(id)){game('La <b>Guacharaca</b> es fauna protegida. No se caza, no se captura y no se vende.','aviso');return false;}const next=MiningRules.add(S.inv,W.items,id,qty,SLOTS);if(!next){avisarMochilaLlena();return false;}S.inv=next;save();renderInv();return true;}
function invRemove(id,qty){const next=MiningRules.remove(S.inv,id,qty);if(!next)return false;S.inv=next;if(!S.inv[S.sel])S.sel=-1;save();renderInv();if(window.Acunar)Acunar.paint();return true;}
window.quitarDelInventario = invRemove;
window.meterMonedas = (item, qty) => { const have = invCount(item); if (qty > have) invAdd(item, qty - have); };
const selected = () => S.sel >= 0 && S.inv[S.sel] ? S.inv[S.sel].item : null;
function selectItem(id) { const i = S.inv.findIndex(s => s && s.item === id); if (i >= 0) { S.sel = i; renderInv(); } return i >= 0; }
const level = (xp) => Math.floor(Math.sqrt(xp / 25)) + 1;
const skillIds = () => (W.skills.order || Object.keys(W.skills).filter(k => W.skills[k] && W.skills[k].name));
function inSkatePark(x, y) {
  const box = window.SKATE_4_SUR && window.SKATE_4_SUR.placement;
  return !!(box && x >= box.x && x < box.x + box.w && y >= box.y && y < box.y + box.h);
}
function updateSkateButton() {
  const label = !invCount('patineta') ? 'Tomar tabla' : (S.skating ? 'A pie' : 'Patinar');
  for (const id of ['b-skate', 'b-skate-movil']) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.hidden = false;
    el.setAttribute('aria-label', label);
    if (!el.querySelector('img')) el.textContent = label;
  }
}
function toggleSkate() {
  if (!started) return;
  if (S.mounted) { game('Baja del caballo para patinar.', 'aviso'); return; }
  if (!invCount('patineta')) {
    if (!inSkatePark(S.player.x, S.player.y)) {
      game('La patineta está en el Skate Park de la 4 Sur, al norte por el camino del valle.', 'aviso');
      return;
    }
    if (!invAdd('patineta', 1)) return;
    game('Recoges una patineta en el Skate Park de la 4 Sur.', 'juego');
    S.skating = true;
  } else S.skating = !S.skating;
  updateSkateButton();
}
function skateTick(dt) {
  if (S.mounted) S.skating = false;
  if (!S.skating || !invCount('patineta')) { S.skating = false; return; }
  S.skateAcc = (S.skateAcc || 0) + dt;
  if (S.skateAcc < 2) return;
  S.skateAcc = 0;
  if (inSkatePark(S.player.x, S.player.y)) addXp('skate', 4);
}
function addXp(skill, n) {
  if (!W.skills[skill]) return;
  const before = level(S.xp[skill] || 0); S.xp[skill] = (S.xp[skill] || 0) + n; save(); renderSkills(); renderProfile();
  if (level(S.xp[skill]) > before) game(`¡Subiste a nivel ${level(S.xp[skill])} de ${W.skills[skill].name}!`, 'oro');
}
function totalLevel() { return skillIds().filter(k => !W.skills[k].stub).reduce((a, k) => a + level(S.xp[k] || 0), 0) - (skillIds().filter(k => !W.skills[k].stub).length - 1); }
function partidaSnapshot() {
  const hud = {};
  if (window.HudLayoutCore) {
    for (const mobile of [false, true]) for (const portrait of [false, true]) {
      const key = HudLayoutCore.storageKey(mobile, portrait);
      try { hud[key] = HudLayoutCore.loadLayout(localStorage, key); } catch (e) {}
    }
  }
  try { hud.pantallaLimpia = localStorage.getItem('lifeinc.pantalla.v1') === '1'; } catch (e) {}
  const libro = S.libro ? { started: !!S.libro.started, done: !!S.libro.done, turnedIn: !!S.libro.turnedIn, steps: S.libro.steps || {} } : {};
  return {
    inv: S.inv, xp: S.xp,
    quest: { stage: S.quest.stage, steps: S.quest.steps, done: S.quest.done, turnedIn: S.quest.turnedIn },
    libro, studied: S.studied || {}, hp: S.hp, energy: S.energy,
    position: { mapId: W.mapId || 'city', x: S.player.x, y: S.player.y, dir: S.player.dir },
    hud, layout: window.Casa ? Casa.layout : null, pet: S.pet || null,
    corral: window.Corral ? Corral.snapshot() : null,
    coat: window.Caballo ? Caballo.coat : '',
    horse: (() => {
      const mount = (S.mounts || []).find(item => item.personal);
      if (!mount) return { coat: window.Caballo ? Caballo.coat : '' };
      return { x: mount.fx, y: mount.fy, dir: mount.dir || 'down', coat: mount.coat || (window.Caballo ? Caballo.coat : '') };
    })(),
  };
}
function applyPartida(doc) {
  if (!doc) return;
  if (Array.isArray(doc.inv)) {
    const next = doc.inv.filter(slot => slot && W.items[slot.item]);
    if (next.length) S.inv = next;
  }
  if (doc.xp && typeof doc.xp === 'object') S.xp = doc.xp;
  if (doc.quest) Object.assign(S.quest, doc.quest);
  if (doc.libro && S.libro) Object.assign(S.libro, { started: !!doc.libro.started, done: !!doc.libro.done, turnedIn: !!doc.libro.turnedIn, steps: doc.libro.steps || {} });
  if (doc.studied && typeof doc.studied === 'object') S.studied = doc.studied;
  if (Number.isFinite(doc.hp)) S.hp = Math.max(0, Math.min(100, doc.hp));
  if (Number.isFinite(doc.energy)) { S.energy = Math.max(0, Math.min(100, doc.energy)); if (S.energy <= 0) S.sprintLock = true; }
  if (doc.pet && window.Vida && Vida.decorate) { S.pet = Vida.decorate(doc.pet); try { localStorage.setItem('lifeinc.mascota.v1', JSON.stringify(doc.pet)); } catch (e) {} }
  else if (doc.pet) S.pet = doc.pet;
  if (doc.layout && window.Casa && Casa.apply) Casa.apply(doc.layout);
  if (doc.corral && window.Corral) Corral.apply(doc.corral);
  if (doc.coat && window.Caballo && Caballo.applyCoat) Caballo.applyCoat(doc.coat);
  if (doc.horse && Number.isFinite(Number(doc.horse.x)) && Number.isFinite(Number(doc.horse.y))) {
    const mount = ensurePersonalHorse();
    mount.x = mount.fx = Number(doc.horse.x);
    mount.y = mount.fy = Number(doc.horse.y);
    if (doc.horse.dir) mount.dir = doc.horse.dir;
    mount.ridden = false;
    mount.called = false;
    if (doc.horse.coat && window.Caballo && Caballo.applyCoat) Caballo.applyCoat(doc.horse.coat);
  }
  if (doc.hud && window.HudLayout && HudLayout.applySaved) HudLayout.applySaved(doc.hud);
  const pos = doc.position;
  if (pos && ['city', 'casa', 'mine', 'banco', 'central'].includes(pos.mapId)) {
    if ((W.mapId || 'city') !== pos.mapId) { try { switchMap(pos.mapId); } catch (e) {} }
    const tx = Math.floor(pos.x), ty = Math.floor(pos.y);
    if (pos.mapId === 'casa' || walkable(tx, ty)) {
      S.player.x = S.player.fx = pos.x; S.player.y = S.player.fy = pos.y;
      if (pos.dir) S.player.dir = pos.dir;
      S.player.path = [];
    }
  }
  renderAll();
}
function save() { try { localStorage.setItem('lifeinc.eljardin.v3', JSON.stringify({ inv: S.inv, xp: S.xp, coins: S.coins, legacyCoins: S.legacyCoins || 0, migrationAck: !!S.migrationAck, vault: S.vault || { smcSubs: 0, items: {} }, playtime: S.playtime || 0, createdAt: S.createdAt || 0, energy: S.energy, hp: S.hp, mapId:W.mapId||'city', cityReturn, resourceState:Object.fromEntries([...(caveNodes||[])].filter(([,n])=>n.state==='depleted').map(([id,n])=>[id,Date.now()+Math.max(0,n.until-now())])), mapRevision: W.expansion?.revision || 0, position: {x:S.player.x,y:S.player.y,dir:S.player.dir}, quest: { stage: S.quest.stage, steps: S.quest.steps, done: S.quest.done, turnedIn: S.quest.turnedIn }, libro: S.libro, studied: S.studied, econ: S.econ })); if (window.Partida) Partida.touch(); return true; } catch (e) { return false; } }
function restore() {
  let d = null; try { d = JSON.parse(localStorage.getItem('lifeinc.eljardin.v3')); } catch (e) {}
  if (d && Array.isArray(d.inv) && d.inv.every(s => !s || W.items[s.item])) { S.inv = d.inv; S.xp = d.xp || {}; S.coins = d.coins || 0; S.legacyCoins = d.legacyCoins || d.coins || 0; S.migrationAck = !!d.migrationAck; S.vault = d.vault || { smcSubs: 0, items: {} }; S.playtime = d.playtime || 0; S.createdAt = d.createdAt || 0; Object.assign(S.quest, d.quest || {});
    if (Number.isFinite(d.energy)) S.energy = Math.max(0, Math.min(100, d.energy));
    if (Number.isFinite(d.hp)) S.hp = Math.max(0, Math.min(100, d.hp));
    if (S.energy <= 0) S.sprintLock = true;
    if(d.cityReturn)cityReturn=d.cityReturn;
    // Inventory, skills and quests carry over. The saved map and coordinates never decide where a session starts.
    if(d.resourceState){if(!caveNodes)caveNodes=new Map(caveMap.nodes.map(n=>[n.id,{def:n,state:n.initialState,until:0,crop:null}]));for(const [id,until] of Object.entries(d.resourceState)){const n=caveNodes.get(id);if(n&&until>Date.now()){n.state='depleted';n.until=now()+until-Date.now();}}}
    if (window.Simulacion) { Simulacion.restore(d); Simulacion.noteLegacy(S.legacyCoins); }
  }
  else fresh();
}
function placeAtHouseSpawn() {
  const p = S.player;
  p.x = p.fx = Casa.SPAWN.x; p.y = p.fy = Casa.SPAWN.y; p.dir = Casa.SPAWN.dir || 'down';
  p.path = []; p.pending = null; p.busyUntil = 0; S.dest = null;
}
function beginAtHome() {
  if (AUTOTEST) return;
  if ((W.mapId || 'city') !== 'casa') switchMap('casa');
  placeAtHouseSpawn();
}
function fresh() {
  S.inv = []; S.xp = {}; S.coins = W.startingCoins || 0; S.legacyCoins = S.coins; S.migrationAck = false; S.vault = { smcSubs: 0, items: {} }; S.quest.stage = 0; S.quest.steps = {}; S.quest.done = false; S.quest.turnedIn = false;
  for (const s of W.starterInventory) invAdd(s.item, s.qty);
  if (window.Simulacion) { Simulacion.resetProgress(); Simulacion.noteLegacy(S.legacyCoins); Simulacion.flushMigration(); }
}
function renderAll() { renderInv(); renderSkills(); renderProfile(); renderQuest(); }
const ART = 'iconos-r2';
function itemArt(it, qty) {
  if (!it || !it.icon) return '';
  const set = qty > 1 && it.iconStack ? it.iconStack : it.icon;
  return BASE + (set['64'] || set['32']) + '?v=' + ART;
}
function itemImg(it, qty, cls) {
  if (!it) return '';
  return `<img class="${cls || 'item-art'}" src="${itemArt(it, qty)}" alt="">`;
}
function showItemTip(it, qty, ev) {
  const tip = $('#tooltip'); if (!tip || !it) return;
  tip.hidden = false; tip.classList.add('tip-item');
  tip.innerHTML = `${itemImg(it, qty, 'tip-art')}<b>${esc(it.name)}</b><span class="tip-qty">× ${qty}</span>`;
  tip.style.left = Math.min(innerWidth - 148, (ev.clientX || 0) + 14) + 'px';
  tip.style.top = Math.max(8, (ev.clientY || 0) - 96) + 'px';
}
function hideItemTip() {
  const tip = $('#tooltip'); if (!tip || !tip.classList.contains('tip-item')) return;
  tip.classList.remove('tip-item'); tip.hidden = true; tip.innerHTML = '';
}
function renderInv() {
  const el = $('#inventario'); el.innerHTML = '';
  const first=bagMode==='summary'?bagPage*BAG_PAGE_SIZE:0,limit=bagMode==='summary'?first+BAG_PAGE_SIZE:SLOTS;
  for (let i = first; i < limit; i++) {
    const s = i<SLOTS?S.inv[i]:null; const d = document.createElement('div');
    if(s)d.setAttribute('role','button'); d.tabIndex=s?0:-1;
    d.className = 'slot' + (s ? '' : ' vacio') + (i === S.sel ? ' sel' : '');
    if (s) { const it = W.items[s.item]; d.title = it.name; d.setAttribute('aria-label',it.name+' × '+s.qty); d.innerHTML = itemImg(it, s.qty) + (it.stackable ? `<span class="n">${s.qty}</span>` : '') + `<small class="item-name">${esc(it.name)}</small>`; wireMineralDrag(d,s.item); d.onpointerenter=e=>showItemTip(it,s.qty,e); d.onpointerleave=hideItemTip; d.onclick = () => { if(now()<suppressOreClickUntil)return;S.sel = S.sel === i ? -1 : i;if(MiningRules.recipes[selected()]&&$('#forge-ore')){$('#forge-ore').value=selected();renderForge();}renderInv(); };d.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();d.click();}}; }
    el.appendChild(d);
  }
  updateBagMode();
  const sel = selected(); const held = sel ? S.inv[S.sel] : null;
  $('#seleccion').innerHTML = 'Seleccionado: ' + (sel ? itemImg(W.items[sel], held.qty, 'sel-art') + `<b>${esc(W.items[sel].name)}</b>` : '—');
  const hb = $('#hotbar'); hb.querySelectorAll('.hs').forEach(n => n.remove());
  for (let i = 0; i < 10; i++) {
    const s = S.inv[i]; const d = document.createElement('div'); d.className = 'hs' + (i === S.sel ? ' sel' : '');
    d.innerHTML = `<span class="k">${(i + 1) % 10}</span>` + (s ? itemImg(W.items[s.item], s.qty) + `<span class="n">${W.items[s.item].stackable ? s.qty : ''}</span>` : '');
    if (s) { d.title = W.items[s.item].name; d.onpointerenter=e=>showItemTip(W.items[s.item], s.qty, e); d.onpointerleave=hideItemTip; }
    d.onclick = () => { if (S.inv[i]) { S.sel = S.sel === i ? -1 : i; renderInv(); } };
    hb.appendChild(d);
  }
  $('#bolsa').textContent = `${S.inv.filter(Boolean).length}/${SLOTS}`; if ($('#monedas')) $('#monedas').textContent = '0';
  if (window.Simulacion) Simulacion.paintHud();
}
function renderSkills() {
  const el = $('#habilidades'); el.innerHTML = '';
  const skill = 'mining';
  const sk = W.skills[skill] || { name: 'Minería', learn: '' };
  const xp = S.xp[skill] || 0;
  const lv = level(xp);
  const hi = 25 * lv * lv;
  const falta = Math.max(0, hi - xp);
  el.insertAdjacentHTML('beforeend', `<li class="nivel-resumen"><b>Nivel ${lv} de ${esc(sk.name)}</b><span class="nivel-barra" aria-hidden="true"><i style="width:${Math.round(100 * (xp - 25 * (lv - 1) ** 2) / Math.max(1, hi - 25 * (lv - 1) ** 2))}%"></i></span><span>Te faltan ${falta} de experiencia para el nivel ${lv + 1}. En ese nivel no se abre una herramienta nueva: sigues practicando. ${esc(sk.learn || '')}</span></li>`);
  for (const k of skillIds()) {
    const sk = W.skills[k]; if (!sk || !sk.name) continue;
    const xp = S.xp[k] || 0, lv = level(xp), lo = 25 * (lv - 1) ** 2, hi = 25 * lv ** 2;
    el.insertAdjacentHTML('beforeend', `<li title="${esc(sk.learn || '')}"><span>${sk.name}${sk.stub ? ' <small style="color:#a59a82">(próximamente)</small>' : ''}</span><span>Nv ${lv} · ${xp} xp</span></li><div class="b"><i style="width:${Math.round(100 * (xp - lo) / (hi - lo))}%"></i></div>`);
  }
  if (window.Simulacion) { el.insertAdjacentHTML('beforeend', Simulacion.skillExtraHtml()); Simulacion.wireLessonButtons(); }
}
function formatPlay(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h} h ${m} min`;
  return `${m} min`;
}
function formatSince(ts) {
  if (!ts) return '—';
  const d = new Date(ts * 1000);
  const months = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
}
function renderProfile() {
  $('#mi-nivel').textContent = `Nv. ${totalLevel()}`;
  const tiempo = $('#tiempo-jugado'), desde = $('#jugador-desde');
  if (tiempo) { tiempo.textContent = `Tiempo jugado: ${formatPlay(S.playtime)}`; tiempo.title = 'Lo cuenta el servidor. En Render vuelve a cero al redeploy.'; }
  if (desde) desde.textContent = `Jugador desde: ${formatSince(S.createdAt)}`;
  const energia = $('#bar-energia'); if (energia) energia.style.width = S.energy + '%';
  const txtEn = $('#txt-energia'); if (txtEn) txtEn.textContent = `${Math.round(S.energy)} / 100`;
  paintRings();
}
function paintRings() {
  const hp = Math.max(0, Math.min(100, Number.isFinite(S.hp) ? S.hp : 100));
  const en = Math.max(0, Math.min(100, Number.isFinite(S.energy) ? S.energy : 100));
  const vida = $('#bar-vida'); if (vida) vida.style.width = hp + '%';
  const txtHp = $('#txt-vida'); if (txtHp) txtHp.textContent = Math.round(hp) + ' / 100';
  const pct = $('#vida-pct'); if (pct) pct.textContent = Math.round(hp) + '%';
  const meter = $('#anillo-vida'); if (meter) meter.setAttribute('aria-valuenow', String(Math.round(hp)));
  const c = 2 * Math.PI * 26;
  const arco = $('#vida-arco');
  const eArco = $('#energia-arco');
  if (arco) { arco.style.strokeDasharray = c + ' ' + c; arco.style.strokeDashoffset = String(c * (1 - hp / 100)); }
  if (eArco) { eArco.style.strokeDasharray = c + ' ' + c; eArco.style.strokeDashoffset = String(c * (1 - en / 100)); }
  const box = $('#anillo-energia'); if (box) box.classList.toggle('sin-aliento', !!S.sprintLock);
}
function damagePlayer(amount, cause) {
  if (!started) return S.hp ?? 100;
  const before = Number.isFinite(S.hp) ? S.hp : 100;
  const next = window.HudLayoutCore ? HudLayoutCore.applyDamage(before, amount) : Math.max(0, before - Math.max(0, Number(amount) || 0));
  S.hp = next;
  S.hurtUntil = now() + 2200;
  if (before > 0 && next < before) floatText(S.player.x, S.player.y, '-' + Math.round(before - next), '#ffb0a4');
  if (before > 0 && next <= 0) {
    if (cause === 'puma' && window.Fauna) Fauna.onDown();
    else game('Te quedaste sin vida. Recuperas al respirar.', 'aviso');
  }
  paintRings();
  return S.hp;
}
function drawPortrait() {
  const c = $('#retrato').getContext('2d'), sh = sheets[S.me.color] || sheets.default; c.imageSmoothingEnabled = false;
  c.fillStyle = '#3b5a2c'; c.fillRect(0, 0, 56, 56); c.drawImage(sh, 6, 0, 36, 36, 0, 2, 56, 56);
  const d = $('#dialogo-cara').getContext('2d'); d.imageSmoothingEnabled = false; d.fillStyle = '#b9a676'; d.fillRect(0, 0, 64, 64);
  if (capatazImg) d.drawImage(capatazImg, 6, 0, 36, 36, 0, 2, 64, 64);
}

// ---------------- Primeros Pasos ----------------
function stepDone(st) { return (S.quest.steps[st.id] || 0) >= st.count; }
function stepActive(st) { return !(st.requires || []).some(id => !stepDone(S.quest.def.steps.find(s => s.id === id))); }
function questProgress(type, item, qty) {
  const q = S.quest.def; if (!q || S.quest.turnedIn) return;
  for (const st of q.steps) {
    if (stepDone(st) || !stepActive(st)) continue;
    if ((type === 'collect' && st.type === 'collect' && st.item === item) || (type === 'talk' && st.type === 'talk' && st.target === item)) {
      S.quest.steps[st.id] = Math.min(st.count, (S.quest.steps[st.id] || 0) + qty);
      if (stepDone(st)) {
        const gifts = (st.onComplete && st.onComplete.giveItems) || [];
        const given = [];
        let full = false;
        for (const g of gifts) {
          if (invCount(g.item)) continue;
          if (!invAdd(g.item, g.qty)) { full = true; break; }
          given.push(g);
        }
        if (full) {
          for (const g of given) invRemove(g.item, g.qty);
          S.quest.steps[st.id] = Math.max(0, (S.quest.steps[st.id] || 0) - qty);
          break;
        }
        game(`Primeros Pasos: <b>${esc(st.text)}</b> ✔`, 'oro');
        for (const g of given) game(`Recibes: <b>${W.items[g.item].name}</b>.`, 'juego');
      }
    }
  }
  S.quest.done = q.steps.every(stepDone); save(); renderQuest(); updateTutorial();
}
function renderQuest() {
  const q = S.quest.def; if (!q) return;
  const el = $('#misiones'); el.innerHTML = '';
  for (const st of q.steps) {
    const n = S.quest.steps[st.id] || 0, ok = n >= st.count;
    el.insertAdjacentHTML('beforeend', `<li class="${ok ? 'hecha' : ''}" data-paso="${st.id}"><span class="caja">${ok ? '✔' : ''}</span><span>${esc(st.text)}</span>${st.count > 1 ? `<span class="prog">(${n}/${st.count})</span>` : ''}</li>`);
  }
  if (S.quest.done && !S.quest.turnedIn) el.insertAdjacentHTML('beforeend', '<li style="color:#ffd27a">▸ Vuelve con el capataz</li>');
  if (S.quest.turnedIn) el.insertAdjacentHTML('beforeend', '<li style="color:#8fe08f">★ ¡Completado!</li>');
  if (window.Simulacion) el.insertAdjacentHTML('beforeend', Simulacion.questExtraHtml());
}
function currentStage() {
  const t = S.quest.def && S.quest.def.tutorial; if (!t) return null;
  return t.stages[Math.min(S.quest.stage, t.stages.length - 1)];
}
function stageComplete(st) {
  const c = st.completeWhen; if (!c) return false; const p = S.player;
  if (c.type === 'reach') return Math.max(Math.abs(p.x - c.x), Math.abs(p.y - c.y)) <= c.radius;
  if (c.type === 'door') return !!S.quest.doorOpened;
  if (c.type === 'step') return stepDone(S.quest.def.steps.find(s => s.id === c.step));
  if (c.type === 'questDone') return S.quest.turnedIn;
  return false;
}
function updateTutorial(force) {
  if(W.mapId==='mine'||W.mapId==='casa')return;
  const t = S.quest.def && S.quest.def.tutorial; if (!t || !started) return;
  let changed = force;
  // si el paso "hablar" ya está hecho, salta las etapas previas (p. ej. hablaron directo con el capataz)
  if (stepDone(S.quest.def.steps[0])) { const i = t.stages.findIndex(s => s.id === 'madera'); if (S.quest.stage < i) { S.quest.stage = i; changed = true; } }
  while (S.quest.stage < t.stages.length - 1 && stageComplete(t.stages[S.quest.stage])) { S.quest.stage++; changed = true; }
  if (!changed) return;
  save();
  const st = currentStage();
  $('#objetivo').hidden = !st; if (!st) return;
  $('#objetivo-txt').textContent = st.box; const ob = $('#objetivo'); ob.classList.remove('parpadeo'); void ob.offsetWidth; ob.classList.add('parpadeo');
  if (st.prompt && !S.dialog) { $('#aviso').hidden = false; $('#aviso-titulo').textContent = st.prompt.title; $('#aviso-txt').textContent = st.prompt.text; }
  else $('#aviso').hidden = true;
  if (st.id === 'libre') setTimeout(() => { if (currentStage() && currentStage().id === 'libre') $('#objetivo').hidden = true; }, 15000);
}
function arrowTarget() {
  if(W.mapId==='mine'||W.mapId==='casa')return null;
  const st = currentStage(); if (!st || !st.arrow) return null; const a = st.arrow;
  if (a.kind === 'tile') return { x: a.x, y: a.y, h: 0 };
  if (a.kind === 'door') { const d = W.doors.find(d => d.id === a.id); return d && { x: d.x, y: d.y, h: 40 }; }
  if (a.kind === 'npc') { const n = W.npcs.find(n => n.id === a.id); return n && { x: n.x, y: n.y, h: 92 }; }
  if (a.kind === 'nearest') {
    let best = null, bd = 1e9; const p = S.player;
    for (const n of S.nodes.values()) {
      if (n.def.type !== a.nodeType || (a.mineral && n.def.mineral !== a.mineral) || (a.state && n.state !== a.state)) continue;
      const d = Math.hypot(n.def.x - p.x, n.def.y - p.y); if (d < bd) { bd = d; best = n.def; }
    }
    return best && { x: best.x, y: best.y, h: a.nodeType === 'wood_tree' ? 140 : 60 };
  }
  return null;
}

// ---------------- diálogo del capataz ----------------
function talkCapataz() {
  const npc = W.npcs[0], d = npc.dialog; let lines, after = null;
  if (!stepDone(S.quest.def.steps[0])) { lines = d.intro; after = () => questProgress('talk', 'capataz', 1); }
  else if (S.quest.done && !S.quest.turnedIn) {
    lines = d.done; after = () => {
      const r = S.quest.def.reward; S.quest.turnedIn = true;
      for (const [k, v] of Object.entries(r.xp || {})) addXp(k, v);
      if (S.net.ok) S.net.ws.send(JSON.stringify({ t: 'quest', id: 'primeros_pasos' }));
      else if (window.Simulacion) Simulacion.grantTreasury(r.coins || 0, 'Primeros Pasos');
      game(S.net.ok
        ? '¡Primeros Pasos completado! El tesoro paga sólo hasta el tope de hoy. El resto queda en la reserva.'
        : `¡Primeros Pasos completado! +${r.coins} SMC del tesoro de misiones.`, 'oro'); save(); renderAll(); updateTutorial();
    };
  } else if (S.quest.turnedIn) lines = d.after; else lines = d.inProgress;
  S.dialog = { lines, i: 0, after }; $('#aviso').hidden = true; showDialog();
}
function showDialog() { const D = S.dialog; $('#dialogo').hidden = false; $('#dialogo-txt').textContent = D.lines[D.i]; $('.quien').textContent = (D.who && D.who.name) || W.npcs[0].name; if (window.Simulacion) Simulacion.drawDialogFace(D.who); }
function advanceDialog() {
  const D = S.dialog; if (!D) return; D.i++;
  if (D.i >= D.lines.length) { S.dialog = null; $('#dialogo').hidden = true; if (D.after) D.after(); updateTutorial(true); return; }
  showDialog();
}
$('#dialogo').onclick = advanceDialog;

// ---------------- chat ----------------
function addLine(channel, html) {
  S.chat.lines.push({ channel, html }); if (S.chat.lines.length > 300) S.chat.lines.shift();
  if (channel !== 'juego' && channel !== 'sys' && channel !== S.chat.tab) { S.chat.unread[channel] = true; renderTabs(); }
  window.ChatUI?.received(channel);
  renderChat();
}
const sys = (html) => addLine('sys', `<span class="sys">${html}</span>`);
function game(html, cls = 'juego') { addLine('juego', `<span class="${cls}">${html}</span>`); }
function renderChat() {
  const el = $('#chat-log'), atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 30;
  el.innerHTML = S.chat.lines.filter(l => l.channel === S.chat.tab || l.channel === 'juego' || l.channel === 'sys').slice(-80).map(l => `<div class="l">${l.html}</div>`).join('');
  if (atBottom) el.scrollTop = el.scrollHeight;
  const inRange = [...S.others.values()].filter(o => dist(o) * 2 <= 30).length;
  const notas = {
    global: '(Mundo) Lo leen todos los que están en tu mundo, cerca o lejos.',
    proximidad: `(Cerca) Sólo a ≤ 30 m en tu mundo · ${inRange} en rango`,
    clan: S.me.clan ? `(Clan) Visible para tu clan: ${esc(S.me.clan)}` : '(Clan) Sin clan · escribe /clan nombre',
    grupo: S.me.group ? `(Grupo) Visible para tu grupo: ${esc(S.me.group)}` : '(Grupo) No estás en un grupo · escribe /grupo nombre',
  };
  $('#chat-nota').innerHTML = (S.net.ok ? '' : '⚠ Sin servidor de chat (ejecuta python3 server.py) · ') + notas[S.chat.tab];
}
function renderTabs() { document.querySelectorAll('.pestanas button[data-canal]').forEach(b => { const c = b.dataset.canal; b.classList.toggle('activa', c === S.chat.tab); b.innerHTML = CANALES[c] + (S.chat.unread[c] ? '<span class="nuevo"></span>' : ''); }); }
document.querySelectorAll('.pestanas button[data-canal]').forEach(b => b.onclick = () => { S.chat.tab = b.dataset.canal; S.chat.unread[S.chat.tab] = false; renderTabs(); renderChat(); });
$('#chat-min').onclick = () => window.ChatUI.setOpen(false);
const chatGente = $('#chat-gente-btn');
if (chatGente) chatGente.onclick = () => {
  const list = document.getElementById('mundo-lista');
  const tab = document.getElementById('mundo-tab');
  if (!list) return;
  list.hidden = false;
  if (tab) tab.setAttribute('aria-expanded', 'true');
};
const chatInvitar = $('#chat-invitar');
if (chatInvitar) chatInvitar.onclick = () => {
  const list = document.getElementById('mundo-lista');
  if (list) list.hidden = false;
  const invite = document.getElementById('mundo-invitar');
  if (invite) invite.click();
};
$('#chat-form').onsubmit = (e) => {
  e.preventDefault(); const inp = $('#chat-input'); const text = inp.value.trim(); inp.value = ''; inp.blur(); if (!text) return;
  if (window.Simulacion && Simulacion.offlineCommand(text)) return;
  if (S.net.ok) S.net.ws.send(JSON.stringify({ t: 'chat', channel: S.chat.tab, text }));
  else { addLine(S.chat.tab, chatLine({ channel: S.chat.tab, from: nombrePropio(), text, ts: hhmm() }, true)); bubble(0, text); }
};
const hhmm = () => new Date().toTimeString().slice(0, 5);
const NAME_COL = ['#7fd0ff', '#ff9ad5', '#ffd27a', '#9df59a', '#c9a6ff', '#ffb070'];
function chatLine(m, mine) {
  const col = mine ? '#9df59a' : NAME_COL[(m.fromId || 0) % NAME_COL.length];
  const who = mine ? nombrePropio() : textoNombre(m.from);
  return `<span class="t">[${esc(m.ts)}]</span> <span class="n" style="color:${col}">${esc(who)}:</span> ${esc(m.text)}`;
}
function bubble(id, text) { S.bubbles.set(id, { text: text.length > 60 ? text.slice(0, 58) + '…' : text, until: now() + 6000 }); }

// ---------------- red (WebSocket) ----------------
(function watchBuild() {
  const meta = document.querySelector('meta[name="life-revision"]');
  const mine = (meta && meta.content || '').trim();
  let busy = false;
  async function check() {
    if (busy) return;
    try {
      const res = await fetch('/session.json?t=' + Date.now(), { cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      const stalePage = mine && data.revision && data.revision !== mine;
      const otherRoom = S.net.serverId && data.serverId && data.serverId !== S.net.serverId;
      if (stalePage || otherRoom) { busy = true; location.reload(); }
    } catch (e) {}
  }
  setInterval(check, 15000);
  check();
})();
function scheduleReconnect() {
  if (!started) return;
  const wait = reconnectDelay;
  reconnectDelay = Math.min(15000, Math.round(reconnectDelay * 1.7));
  reconnectTimer = setTimeout(connect, wait);
}
function connect() {
  if (!started) return;
  clearTimeout(reconnectTimer);
  if (!/^https?:/.test(location.protocol)) { renderChat(); return; }
  let ws; try { ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws'); } catch (e) { scheduleReconnect(); return; }
  const rawSend = ws.send.bind(ws);
  ws.send = (data) => { if (ws.readyState !== 1) return; try { rawSend(data); } catch (e) { S.net.ok = false; } };
  S.net.ws = ws;
  S.net.seen = 0;
  addEventListener('pagehide', () => { try { ws.close(); } catch (e) {} }, { once: true });
  ws.onopen = () => { if(!started || S.net.ws!==ws) {ws.close();return;} reconnectDelay = 1000; S.net.seen = performance.now(); const zone = W.mapId==='casa'?'casa':W.mapId==='mine'?'mine':W.mapId==='banco'?'banco':W.mapId==='central'&&S.canMintIngots?'central':'city'; ws.send(JSON.stringify({ t: 'hello', name: S.me.name, color: S.me.color, clan: S.me.clan || '', group: S.me.group || '', level: totalLevel(), zone, world: window.Vida ? Vida.world() : 3, pet: window.Vida ? Vida.petPayload() : null, walletToken: window.Simulacion ? Simulacion.walletToken(S.me.name) : '', resume: zone==='city' && (S.net.hasJoined || window.LIFE_PARTIDA) ? {x:S.player.fx,y:S.player.fy} : (W.mapId==='mine'?cityReturn:null) })); };
  ws.onmessage = (ev) => {
    if (!started || S.net.ws!==ws) return;
    S.net.seen = performance.now();
    let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
    if (!m || typeof m !== 'object') return;
    if (m.t === 'veta' && m.ok === false) { if (S.metalOptimistic) { invRemove(S.metalOptimistic.item, S.metalOptimistic.qty); S.metalOptimistic = null; } S.espera = null; nota(m.reason || 'Esa veta está ocupada.'); return; }
    if (m.t === 'nodos' && Array.isArray(m.nodes)) { m.nodes.forEach(row => aplicarNodo(row, false)); return; }
    if (m.t === 'nodo') { aplicarNodo(m, !!m.back); return; }
    if (m.t === 'recoger' && m.ok && S.espera && S.espera.done) { const done = S.espera.done; S.espera = null; done('mochila'); return; }
    if (m.t === 'mochila_llena') { if (S.metalOptimistic) { invRemove(S.metalOptimistic.item, S.metalOptimistic.qty); S.metalOptimistic = null; } if (S.espera) S.espera.server = true; avisarMochilaLlena(); game(m.reason || 'Tu mochila está llena', 'aviso'); if (window.Simulacion && Simulacion.reconcileBalance) Simulacion.reconcileBalance(); return; }
    if (m.t === 'mochila_op') {
      if (!m.ok) { game(m.reason || 'No se perdió nada.', 'aviso'); if (S.espera) avisarMochilaLlena(); return; }
      const done = S.espera && S.espera.done;
      S.espera = null;
      if (m.op === 'soltar') { game(m.reason || 'Lo dejaste donde estaba.', 'aviso'); return; }
      if (done) done(m.op);
      game(m.reason || 'Listo.', 'juego');
      return;
    }
    if (m.t === 'cambio_result') {
      if (m.purse) S.purse = m.purse;
      if (m.ok && m.give && window.quitarDelInventario) quitarDelInventario(m.give, m.das || 1);
      game(m.reason || (m.ok ? 'Listo.' : 'No se movió nada.'), m.ok ? 'juego' : 'aviso');
      if (window.Pulgar && Pulgar.pintarCambio) Pulgar.pintarCambio();
      return;
    }
    if (m.t === 'central_result' && !m.ok) {
      S.canMintIngots = false;
      if ((W.mapId || 'city') === 'central') switchMap('city');
      else game(m.reason || 'El Banco Central es un recinto del personal. Esta cuenta no entra.', 'aviso');
      return;
    }
    if (window.Central && Central.onNet(m)) return;
    if (window.Finca) Finca.onNet(m);
    if (window.Fauna && Fauna.onNet(m)) return;
    if (window.Vida && Vida.onNet(m)) return;
    if (m.t === 'welcome') {
      S.net.ok = true; S.net.id = m.id; S.me.name = m.you.name; S.me.nick = m.you.nick ? textoNombre(m.you.nick) : (S.sessionUser ? 'Viajero' : textoNombre(m.you.name)); $('#mi-nombre').textContent = nombrePropio();
      S.net.serverId = m.serverId || null;
      if (!S.net.hasJoined && W.mapId==='casa' && !window.LIFE_PARTIDA) placeAtHouseSpawn();
      S.net.hasJoined=true; S.others.clear();
      for (const p of m.players || []) addOther(p);
      if (Array.isArray(m.nodos)) m.nodos.forEach(row => aplicarNodo(row, false));
      renderNearby();
      $('#ping').classList.add('ok'); sys('Conectado al mundo compartido de LifeIn.'); renderChat(); sendMove(true); if (m.reloj) S.reloj = m.reloj; if (m.ledger) S.ledger = m.ledger; if (m.purse) S.purse = m.purse; if (window.Simulacion && Simulacion.aplicarCredito) Simulacion.aplicarCredito(m); S.canMintIngots = !!m.canMintIngots; if ((W.mapId || 'city') === 'central' && !S.canMintIngots) switchMap('city'); if (window.Cajon) Cajon.paint(); if (window.Simulacion) Simulacion.onWelcome(); if (window.Fauna) Fauna.onWelcome(m); migrarMetal();
    } else if (m.t === 'crudo') {
      S.crudo = Object.assign({}, S.crudo || {}, m.crudo || {});
      if (m.item != null && m.total != null) S.crudo[m.item] = m.total;
      S.metalOptimistic = null;
      if (m.crudo) Object.keys(m.crudo).forEach(id => ponerMetal(id, m.crudo[id]));
      else if (m.item != null) ponerMetal(m.item, m.total);
      if (window.Simulacion && Simulacion.reconcileBalance) Simulacion.reconcileBalance();
      if (m.migrado) { try { localStorage.setItem('lifeinc.crudo.migrado', '1'); } catch (e) {} }
    } else if (m.t === 'join' && m.player) addOther(m.player);
    else if (m.t === 'cerca' && Array.isArray(m.players)) { S.others.clear(); m.players.forEach(addOther); renderNearby(); }
    else if (m.t === 'player') { const o = S.others.get(m.player.id); if (o) Object.assign(o, { name: m.player.name, nick: m.player.nick, clan: m.player.clan, group: m.player.group }); if (m.player.id === S.net.id) { S.me.clan = m.player.clan; S.me.group = m.player.group; if (m.player.nick) S.me.nick = textoNombre(m.player.nick); renderChat(); } }
    else if (m.t === 'leave') { S.others.delete(m.id); renderNearby(); }
    else if (m.t === 'move') applyMove(m);
    else if (m.t === 'gesto') { const o = S.others.get(m.id); if (o && (m.zone || o.zone) === (W.mapId || 'city')) { if (m.kind === 'picar' || m.kind === 'sostener') { o.miningUntil = now() + 800; o.emote = 'point'; o.emoteUntil = now() + 700; } else floatText(m.x, m.y, '·', '#ffe14d'); } }
    else if (m.t === 'seguir_aviso') { game(esc(m.text || ((m.from || 'Alguien') + ' te está siguiendo')), 'juego'); }
    else if (m.t === 'seguir_result' && m.ok === false) { game(esc(m.reason || 'No se puede seguir.'), 'aviso'); }
    else if (m.t === 'move_correct') { if (S.vistaLock) return; const rider = S.player; const far = Math.hypot((m.x || 0) - rider.fx, (m.y || 0) - rider.fy); if (!(S.dest && S.dest.ruta && rider.path && rider.path.length && far <= 2.5)) { rider.x = rider.fx = m.x; rider.y = rider.fy = m.y; rider.path = []; S.dest = null; S.rideAuto = false; } }
    else if (m.t === 'travel_result') { if (!m.ok) game(esc(m.reason || 'No se puede viajar ahí.'), 'aviso'); else flyTo(m.x, m.y, m.name || 'ese lugar'); }
    else if (m.t === 'chat') {
      const mine = m.fromId === S.net.id;
      addLine(m.channel, chatLine(m, mine));
      if (mine || m.channel === 'proximidad' || m.channel === 'global') bubble(mine ? 0 : m.fromId, m.text);
    }
    else if (m.t === 'emote') { const who = m.id === S.net.id ? S.player : S.others.get(m.id); if (who) { who.emote = m.emote; who.emoteUntil = now() + (m.emote === 'sit' ? 4200 : 2600); } }
    else if (window.TradeUI && TradeUI.onNet(m)) { /* intercambio entre dos personas */ }
    else if (m.t === 'system') sys(esc(m.text));
    else if (window.Acunar && Acunar.onNet(m)) { /* acuñar */ }
    else if (window.Simulacion && Simulacion.onNet(m)) { /* SMC o resultado de pago */ }
    else if (m.t === 'pong') { S.net.ping = Math.round(performance.now() - m.c); $('#ping span').textContent = S.net.ping + ' ms'; }
  };
  ws.onerror = () => { try { ws.close(); } catch (e) {} };
  ws.onclose = () => {
    if (S.net.ws!==ws) return;
    if (S.net.ok) sys('Se perdió la conexión. Reintentando…');
    S.net.ok = false; S.others.clear(); $('#ping').classList.remove('ok'); $('#ping span').textContent = 'reconectando'; renderChat();
    scheduleReconnect();
  };
}
function addOther(p) { if(p.id===S.net.id)return; if((p.zone||'city')!==(W.mapId||'city'))return; if(p.pet&&window.Vida&&Vida.decorate)p.pet=Vida.decorate(p.pet); S.others.set(p.id, { ...p, fx: p.x, fy: p.y, lastMove: now() }); renderChat(); renderNearby(); }
function applyMove(m) {
  if (!m || m.id === S.net.id) return;
  const zone = m.zone || 'city';
  let o = S.others.get(m.id);
  if (zone !== (W.mapId || 'city')) { if (o) { S.others.delete(m.id); renderNearby(); } return; }
  if (!o) addOther({ id: m.id, name: m.name || 'Viajero', nick: m.nick || '', color: m.color || 'azul', x: m.x, y: m.y, dir: m.dir, moving: !!m.moving, level: m.level || 1, zone });
  o = S.others.get(m.id);
  if (!o) return;
  o.x = m.x; o.y = m.y; o.dir = m.dir || o.dir; o.moving = !!m.moving; o.level = m.level || o.level; o.pace = m.pace || ''; o.zone = zone; o.lastMove = now();
  if (window.Seguir) Seguir.paso(o);
}
function aplicarNodo(row, back) {
  if (!row || !S.nodes) return;
  const until = Number(row.until) * 1000;
  const n = S.nodes.get(row.id);
  if (!n) return;
  if (until > now()) {
    n.state = (n.def.states || []).includes('depleted') ? 'depleted' : n.state;
    n.until = until;
    return;
  }
  if (n.until) {
    n.state = n.def.initialState || 'active';
    n.until = 0;
    if (back && Math.hypot((n.def.x || 0) - S.player.fx, (n.def.y || 0) - S.player.fy) < 18) nota('Volvió la veta');
  }
}
function nota(text) {
  const box = document.getElementById('toasts');
  if (!box) return;
  const line = document.createElement('p');
  line.textContent = String(text || '').slice(0, 80);
  box.append(line);
  while (box.children.length > 4) box.firstChild.remove();
  setTimeout(() => { if (line.parentNode) line.remove(); }, 2400);
}
function sendGesto(kind, x, y) {
  window.sendGesto = sendGesto;
  if (!S.net.ok || !S.net.ws) return;
  const mark = performance.now();
  if (mark - (S.net.gestoAt || 0) < 80) return;
  S.net.gestoAt = mark;
  S.net.ws.send(JSON.stringify({ t: 'gesto', kind, x: x == null ? S.player.fx : x, y: y == null ? S.player.fy : y, dir: S.player.dir }));
}
function sendMove(force) {
  if (S.vistaLock || !S.net.ok) return;
  if (W.mapId==='mine') {
    const p = S.player;
    const key = `mine:${p.fx.toFixed(2)},${p.fy.toFixed(2)},${p.dir},${!!p.path.length}`;
    if (!force && (key === S.net.sentKey || performance.now() - S.net.lastSent < 120)) return;
    S.net.sentKey = key; S._zoneSent = 'mine'; S.net.lastSent = performance.now();
    S.net.ws.send(JSON.stringify({ t:'move', zone:'mine', x:p.fx, y:p.fy, dir:p.dir, moving:!!p.path.length, level: totalLevel() }));
    return;
  }
  if (W.mapId==='banco' || W.mapId==='central' || W.mapId==='casa') {
    const zone = W.mapId;
    if (!force && S._zoneSent === zone) return;
    S._zoneSent = zone;
    S.net.ws.send(JSON.stringify({ t:'move', zone, level: totalLevel() }));
    return;
  }
  S._zoneSent = 'city';
  const p = S.player, key = `${p.fx.toFixed(2)},${p.fy.toFixed(2)},${p.dir},${!!p.path.length}`;
  if (!force && (key === S.net.sentKey || performance.now() - S.net.lastSent < 120)) return;
  S.net.sentKey = key; S.net.sentZone='city'; S.net.lastSent = performance.now();
  S.net.ws.send(JSON.stringify({ t: 'move', zone:'city', x: p.fx, y: p.fy, dir: p.dir, moving: !!p.path.length, level: totalLevel(), pace: S.pace || 'quieto' }));
}
setInterval(() => {
  const ws = S.net.ws;
  if (!started || !ws || ws.readyState !== 1) return;
  if (S.net.seen && performance.now() - S.net.seen > 12000) { try { ws.close(); } catch (e) {} return; }
  ws.send(JSON.stringify({ t: 'ping', c: performance.now() }));
}, 3000);
addEventListener('pointerdown', (e) => {
  S.lastInput = now();
  const typingNow = document.activeElement && ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName);
  if (typingNow && !(e.target && e.target.closest && e.target.closest('input,textarea,select,label'))) document.activeElement.blur();
}, true);
addEventListener('keydown', () => { S.lastInput = now(); }, true);
setInterval(() => {
  if (!started || !S.net.ok) return;
  const active = now() - (S.lastInput || 0) < 60000;
  S.net.ws.send(JSON.stringify({ t: 'heartbeat', active }));
}, 30000);
const dist = (o) => Math.hypot(o.fx - S.player.fx, o.fy - S.player.fy);
function renderNearby() {
  const el = $('#cercanos'), list = [...S.others.values()].filter(o => !o.bot).sort((a, b) => dist(a) - dist(b));
  $('#n-cercanos').textContent = list.length;
  el.innerHTML = list.length ? list.slice(0, 10).map(o => { const m = Math.round(dist(o) * (W.render.metersPerTile || 2)); return `<li class="${m > 30 ? 'lejos' : ''}"><span class="pt"></span><button type="button" data-trade-peer="${o.id}">${esc(nombreAjeno(o))} · Comerciar</button><span class="m">${m} m</span></li>`; }).join('')
    : `<li class="vacio">${S.net.ok ? 'Nadie más conectado' : 'Sin conexión al servidor'}</li>`;
}

// ---------------- mapa / colisión ----------------
const inside = (x, y) => x >= 0 && y >= 0 && x < W.width && y < W.height;
function walkable(x, y) {
  if (!inside(x, y) || W.collision[y][x] !== 0) return false;
  if (window.Simulacion && Simulacion.blocksTile(W, x, y)) return false;
  return true;
}
function bfs(sx, sy, isGoal) {
  const key = (x, y) => y * W.width + x; const prev = new Map([[key(sx, sy), null]]); const q = [[sx, sy]];
  const dirs = [[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
  for (let qi = 0; qi < q.length; qi++) {
    const [x, y] = q[qi];
    if (isGoal(x, y)) { const path = []; let k = key(x, y); while (k !== key(sx, sy)) { path.unshift([k % W.width, Math.floor(k / W.width)]); k = prev.get(k); } return path; }
    for (const [dx, dy] of dirs) {
      const nx = x + dx, ny = y + dy; if (!walkable(nx, ny) || prev.has(key(nx, ny))) continue;
      if (dx && dy && (!walkable(x + dx, y) || !walkable(x, y + dy))) continue;
      prev.set(key(nx, ny), key(x, y)); q.push([nx, ny]);
    }
  }
  return null;
}
const cheb = (ax, ay, bx, by) => Math.max(Math.abs(ax - bx), Math.abs(ay - by));

// ---------------- objetivos clicables ----------------
function targetTile(t) {
  if (t.kind === 'peer') { const o = S.others.get(t.id); return { x: o?.fx ?? S.player.fx, y: o?.fy ?? S.player.fy }; }
  if (t.kind === 'animal') return { x: t.a.x, y: t.a.y };
  if (t.kind === 'mount') return { x: t.m.x, y: t.m.y };
  if (t.kind === 'npc' || t.kind === 'door') return { x: t.d.x, y: t.d.y };
  return { x: t.n.def.x, y: t.n.def.y };
}
function describe(t) {
  if (t.kind === 'peer') return 'Intercambiar con <b>' + esc(nombreAjeno(S.others.get(t.id) || {})) + '</b>';
  if (t.kind === 'animal') return `Cazar: <b>${NOMBRES[t.a.def.species]}</b>`;
  if (t.kind === 'mount') return Simulacion.describeMount(t.m);
  if (t.kind === 'npc') return `Hablar con: <b>${esc(t.d.name)}</b>`;
  if (t.kind === 'door') return 'Tocar la <b>puerta</b> de la Casa del Capataz';
  const n = t.n, d = n.def;
  if(d.type==='furnace')return 'Usar horno de fundición';if(d.type==='mine_entrance')return 'Entrar a la mina de Las Palmas';if(d.type==='mine_exit')return 'Salir hacia Las Palmas';if(d.type==='home_door')return 'Entrar a <b>tu casa</b>';if(d.type==='casa_exit')return 'Salir al <b>Parque de Envigado</b>';
  switch (d.type) {
    case 'fruit_tree': return n.state === 'full' ? `Recoger: <b>${NOMBRES[d.species]}</b> (con frutas)` : `<b>${NOMBRES[d.species]}</b> (sin frutas)`;
    case 'wood_tree': return n.state === 'standing' ? 'Talar: <b>Pino</b> (madera)' : 'Tocón de pino (vuelve a crecer)';
    case 'farm_plot': return n.state === 'empty' ? 'Sembrar en <b>parcela vacía</b>' : n.state === 'planted' ? `Parcela sembrada: <b>${W.items[n.crop].name}</b>` : `Cosechar: <b>${W.items[n.crop].name}</b>`;
    case 'fishing_spot': return n.state === 'active' ? `Pescar con red: <b>${d.waterBody === 'rio_claro' ? 'Río Claro' : 'Estanque'}</b>` : 'Agua tranquila';
    case 'nodo_oro_fluvial': return n.state === 'active' ? 'Lavar arena: <b>oro fluvial en el río</b> (batea)' : 'Arena lavada';
    case 'fruit_stand': return `Comprar un <b>mango</b> por <span class="smc">${d.priceSai || 5} SMC</span> (simulación)`;
    case 'mineral_rock': return n.state === 'active' ? `Picar: <b>${NOMBRES[d.mineral]}</b>` : 'Roca agotada';
  }
  return '';
}
function spriteKeyFor(n) { const d = n.def; return d.type === 'farm_plot' && n.state === 'grown' ? d.sprites.grown[n.crop] : d.sprites[n.state]; }
function hitTest(wx, wy) {
  const cand = [];
  if ((W.mapId || 'city') === 'city') {
    for (const o of S.others.values()) {
      if (o.bot) continue;
      const ox = o.fx * TS + 32, oy = (o.fy + 1) * TS;
      if (Math.abs(wx - ox) < 28 && wy > oy - 88 && wy < oy) cand.push({ kind: 'peer', id: o.id, sort: oy + 1100 });
    }
  }
  for (const a of S.animals) {
    if (a.state !== 'alive') continue;
    const s = W.sprites[a.def.sprites.alive[0]]; const ox = a.fx * TS + 32 - s.anchorX, oy = (a.fy + 1) * TS - s.anchorY;
    if (wx >= ox - 8 && wx <= ox + s.w + 8 && wy >= oy - 8 && wy <= oy + s.h + 8) cand.push({ kind: 'animal', a, sort: (a.fy + 1) * TS + 1000 });
  }
  for (const npc of W.npcs || []) { const ox = npc.x * TS + 8, oy = (npc.y + 1) * TS - 92; if (wx >= ox && wx <= ox + 48 && wy >= oy && wy <= oy + 88) cand.push({ kind: 'npc', d: npc, sort: (npc.y + 1) * TS + 900 }); }
  if (window.Simulacion) { const m = Simulacion.hitMount(wx, wy, TS); if (m) cand.push({ kind: 'mount', m, sort: (m.fy + 1) * TS + 860 }); }
  for (const dr of W.doors || []) if (wx >= dr.x * TS + 8 && wx < dr.x * TS + 56 && wy >= dr.y * TS - 20 && wy < (dr.y + 1) * TS) cand.push({ kind: 'door', d: dr, sort: (dr.y + 1) * TS + 800 });
  for (const n of S.nodes.values()) {
    const d = n.def; const s = W.sprites[spriteKeyFor(n)];
    let hit = wx >= d.x * TS && wx < (d.x + 1) * TS && wy >= d.y * TS && wy < (d.y + 1) * TS;
    if (!hit && s && (d.type === 'fruit_tree' || d.type === 'wood_tree')) {
      const ox = d.x * TS + 32 - s.anchorX, oy = (d.y + 1) * TS - s.anchorY;
      hit = wx >= ox + s.w * 0.15 && wx <= ox + s.w * 0.85 && wy >= oy + s.h * 0.05 && wy <= oy + s.h;
    }
    if (hit) cand.push({ kind: 'node', n, sort: (d.y + 1) * TS });
  }
  cand.sort((a, b) => b.sort - a.sort);
  return cand[0] || null;
}

// ---------------- acciones ----------------
function goTo(tx, ty) {
  const p = S.player; const path = bfs(p.x, p.y, (x, y) => x === tx && y === ty);
  if (!path) { game('No puedes llegar ahí.', 'aviso'); return; }
  p.path = path; p.pending = null; S.dest = { x: tx, y: ty, t: now() };
  sendGesto('toque', tx, ty);
}
function setRoute(tx, ty, name) {
  if (!started) { game('Entra al mundo para caminar hasta ahí.', 'aviso'); return false; }
  if ((W.mapId || 'city') !== 'city') { game('Sal al valle para caminar hasta ahí.', 'aviso'); return false; }
  const spot = nearestWalkable(Math.floor(tx), Math.floor(ty), 14);
  if (!spot) { game('No se puede caminar ahí.', 'aviso'); return false; }
  const p = S.player;
  const path = bfs(Math.floor(p.x), Math.floor(p.y), (x, y) => x === spot[0] && y === spot[1]);
  if (!path) { game('No hay camino hasta ahí.', 'aviso'); return false; }
  p.path = path; p.pending = null; S.rideAuto = false;
  S.dest = { x: spot[0], y: spot[1], name: name || 'ese lugar', ruta: true, t: now() };
  return true;
}
function routeSamples() {
  if (!S.dest || !S.dest.ruta) return null;
  const pts = [[S.player.fx, S.player.fy]];
  const path = S.player.path || [];
  const step = Math.max(1, Math.ceil(path.length / 80));
  for (let i = 0; i < path.length; i += step) pts.push(path[i]);
  const last = path[path.length - 1];
  if (last) pts.push(last);
  return { pts: pts, name: S.dest.name, x: S.dest.x, y: S.dest.y };
}
function followRoad(id) {
  const road=(W.roads3d||[]).find(r=>r.id===id);if(!road||!started)return;
  const p=S.player;let x=p.x,y=p.y,path=[];
  for(const point of road.points){const part=bfs(x,y,(a,b)=>a===point.x&&b===point.y);if(!part)return;path.push(...part);x=point.x;y=point.y;}
  p.path=path;p.pending=null;S.dest={x,y,t:now()};
}
function approach(t) {
  if (t.kind === 'peer') { if (window.Ficha) Ficha.open(S.others.get(t.id) || { id: t.id }); else window.TradeUI?.openTrade(t.id); return; }
  const p = S.player; const tt = targetTile(t);
  const goal = t.kind === 'door' ? ((x, y) => x === t.d.approach.x && y === t.d.approach.y) : ((x, y) => cheb(x, y, tt.x, tt.y) === 1);
  if (goal(p.x, p.y) && !p.path.length) { p.pending = null; S.dest = null; act(t); return; }
  const path = bfs(p.x, p.y, goal);
  if (!path) { game('No hay forma de acercarse.', 'aviso'); return; }
  p.path = path; p.pending = t; S.dest = { ...tt, t: now() };
}
function needTool(tool) {
  if (!invCount(tool)) { game(`Necesitas <b>${W.items[tool].name}</b> para esto.` + (tool === 'hacha' ? ' Habla con el capataz.' : ''), 'aviso'); return false; }
  if (selected() !== tool) { selectItem(tool); game(`Equipas: <b>${W.items[tool].name}</b>.`); }
  return true;
}
function face(tx, ty) { const p = S.player, dx = tx - p.x, dy = ty - p.y; p.dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up'); }
function rollTable(table) { const tot = table.reduce((a, r) => a + r.weight, 0); let r = Math.random() * tot; for (const e of table) { if ((r -= e.weight) < 0) return e.item; } return table[0].item; }
function ponerMetal(id, qty) {
  qty = Math.round((Number(qty) || 0) * 1000) / 1000;
  S.inv = (S.inv || []).filter(slot => !slot || slot.item !== id);
  if (qty > 0) {
    const hole = S.inv.findIndex(slot => !slot);
    const slot = { item: id, qty };
    if (hole >= 0) S.inv[hole] = slot;
    else S.inv.push(slot);
  }
  save(); renderInv();
}
function quitarMetal(id, qty) {
  let left = Math.round((Number(qty) || 0) * 1000);
  if (left <= 0) return;
  for (const slot of S.inv || []) {
    if (!slot || slot.item !== id) continue;
    const have = Math.round((Number(slot.qty) || 0) * 1000);
    const take = Math.min(have, left);
    slot.qty = (have - take) / 1000;
    left -= take;
  }
  S.inv = S.inv.filter(slot => slot && slot.qty > 0.0005);
  save(); renderInv();
}
window.ponerMetal = ponerMetal;
window.quitarMetal = quitarMetal;
function migrarMetal() {
  try { if (localStorage.getItem('lifeinc.crudo.migrado')) return; } catch (e) { return; }
  const counts = {};
  for (const id of ['pepita_oro', 'mineral_oro', 'mineral_plata', 'mineral_cobre']) counts[id] = invCount(id);
  if (S.net && S.net.ok) S.net.ws.send(JSON.stringify({ t: 'metal_migrar', counts }));
}
function tintinear(item) { if (window.Sonido && Sonido.isRaw(item)) Sonido.clink(); }
function give(item, qty, tx, ty) { if (!invAdd(item, qty)) return false; tintinear(item); floatText(tx, ty, `+${qty} ${W.items[item].name}`); questProgress('collect', item, qty); return true; }
function floatText(tx, ty, text, color = '#fff7b0') { S.floaters.push({ x: tx * TS + 32, y: ty * TS, text: String(text || '').slice(0, 42), color, t0: now() }); if (S.floaters.length > 4) S.floaters.splice(0, S.floaters.length - 4); }
function tired() { S.energy = Math.max(0, S.energy - 2); renderProfile(); }

function act(t) {
  if (t.kind === 'peer') { if (window.Ficha) Ficha.open(S.others.get(t.id) || { id: t.id }); else window.TradeUI?.openTrade(t.id); return; }
  const p = S.player; const tt = targetTile(t); face(tt.x, tt.y);
  if (t.kind === 'mount') { if (S.skating) S.skating = false; return Simulacion.mountHorse(t.m); }
  if (t.kind === 'npc') return t.d.id === 'profesora_cadena' ? Simulacion.talkProfesora() : talkCapataz();
  if (t.kind === 'door') { S.quest.doorOpened = true; game('Tocas la puerta… ¡el capataz sale a recibirte!', 'juego'); updateTutorial(); return talkCapataz(); }
  if (now() < p.busyUntil) return;
  p.busyUntil = now() + 450;
  if (t.kind === 'animal') return hunt(t.a);
  const n = t.n, d = n.def; const secs = () => Math.max(1, Math.ceil((n.until - now()) / 1000));
  if (S.mounted && (d.type === 'mine_entrance' || d.type === 'mine_exit' || d.type === 'home_door' || d.type === 'bank_door' || d.type === 'central_door')) return game('Baja del caballo para entrar a un edificio.', 'aviso');
  if(d.type==='mine_sign'){ if(window.Letrero) Letrero.open(); return; }
  if(d.type==='mine_entrance')return switchMap('mine');
  if(d.type==='mine_exit')return switchMap('city');
  if(d.type==='home_door')return enterHouse();
  if(d.type==='casa_exit')return exitHouse();
  if(d.type==='bank_door')return switchMap('banco');
  if(d.type==='bank_exit')return switchMap('city');
  if(d.type==='central_door')return switchMap('central');
  if(d.type==='central_exit')return switchMap('city');
  if(d.type==='central_vault'){ if(window.Central && Central.allowed()) Central.open(); return; }
  if(d.type==='banquito'||d.type==='banker'){ if(window.Banco) Banco.openPanel(); return game(d.type==='banker'?'El banquero abre el banquito. Lo que dejes aquí no se pierde si caes.':'El banquito es el mismo depósito que el baúl de tu casa.','juego'); }
  if(d.type==='fruit_stand')return Simulacion.buyStand();
  if(d.type==='furnace')return openFurnace(n);
  if (d.type === 'fruit_tree') {
    if (n.state !== 'full') return game(`El ${NOMBRES[d.species].toLowerCase()} no tiene frutas. Vuelven en ${secs()} s.`, 'aviso');
    const q = rnd(d.yield.min, d.yield.max); if (!give(d.yield.item, q, d.x, d.y)) return; game(`Recoges ${q} × <b>${W.items[d.yield.item].name}</b>.`);
    if (d.bonus && Math.random() < d.bonus.chance) { give(d.bonus.item, 1, d.x, d.y - 0.4); game(`¡Encontraste una <b>${W.items[d.bonus.item].name.toLowerCase()}</b>!`); }
    addXp('gathering', d.xp); n.state = 'picked'; n.until = now() + d.respawnMs; tired();
  } else if (d.type === 'wood_tree') {
    if (!needTool(d.tool)) return;
    if (n.state !== 'standing') return game(`Sólo queda el tocón. El pino vuelve a crecer en ${secs()} s.`, 'aviso');
    const q = rnd(d.yield.min, d.yield.max); if (!give('madera', q, d.x, d.y)) return; game(`Talas el pino y obtienes ${q} × <b>madera</b>.`);
    addXp('woodcutting', d.xp); n.state = 'stump'; n.until = now() + d.respawnMs; tired();
  } else if (d.type === 'farm_plot') {
    if (n.state === 'empty') {
      let seed = selected(); if (!seed || !d.accepts.includes(seed)) {
        const any = S.inv.find(s => s && d.accepts.includes(s.item));
        if (!any) return game('No tienes semillas. Consíguelas recogiendo fruta o cosechando.', 'aviso');
        seed = any.item; selectItem(seed); game(`Usas: <b>${W.items[seed].name}</b> (elige otra en la barra si prefieres).`);
      }
      invRemove(seed, 1); n.crop = W.items[seed].grows; n.state = 'planted'; n.until = now() + d.growMs;
      addXp('planting', d.xp.plant); floatText(d.x, d.y, 'Sembrado'); game(`Siembras <b>${W.items[seed].name.toLowerCase()}</b>. Lista en ${Math.round(d.growMs / 1000)} s.`);
    } else if (n.state === 'planted') game(`La planta de ${W.items[n.crop].name.toLowerCase()} está creciendo… faltan ${secs()} s.`, 'aviso');
    else {
      const q = rnd(d.harvest.fruitMin, d.harvest.fruitMax); if (!give(n.crop, q, d.x, d.y)) return; game(`Cosechas ${q} × <b>${W.items[n.crop].name}</b>.`);
      if (Math.random() < d.harvest.seedChance) give(n.crop + '_seed', 1, d.x, d.y - 0.4);
      addXp('planting', d.xp.harvest); n.state = 'empty'; n.crop = null;
    }
  } else if (d.type === 'fishing_spot') {
    if (!needTool(d.tool)) return;
    if (n.state !== 'active') return game(`Aquí no hay peces ahora. Vuelven en ${secs()} s.`, 'aviso');
    const fish = rollTable(d.yield.table); if (!give(fish, d.yield.qty, d.x, d.y)) return; game(`Lanzas la red y atrapas: <b>${W.items[fish].name}</b>.`);
    addXp('fishing', d.xp); n.state = 'depleted'; n.until = now() + d.respawnMs; tired();
  } else if (d.type === 'nodo_oro_fluvial') {
    if (!needTool(d.tool)) return;
    if (n.state !== 'active') return game(`Ya lavaste esta arena. El río trae más oro en ${secs()} s.`, 'aviso');
    if (Math.random() > d.successChance) { floatText(d.x, d.y, 'Sólo arena…', '#e8d9b0'); return game('Mueves la batea en la corriente… sólo arena. Intenta otra vez.', 'aviso'); }
    if (S.net && S.net.ok) {
      const item = d.yield.item;
      S.metalOptimistic = invAdd(item, 1) ? { item, qty: 1 } : null;
      S.espera = { server: true, item, qty: 1, done: (where) => { const pending = S.metalOptimistic; S.metalOptimistic = null; if (where === 'mochila') { if (!(pending && pending.item === item)) { if (!invAdd(item, 1)) return; } nota('+1 Pepita de oro'); } else if (pending && pending.item === item) invRemove(item, 1); addXp('mining', d.xp); n.state = 'depleted'; n.until = now() + d.respawnMs; tired(); } };
      sendGesto('picar', d.x, d.y);
      S.net.ws.send(JSON.stringify({ t: 'recoger', item, qty: 1, kind: 'lavar', spot: d.id }));
      return;
    }
    if (!give(d.yield.item, 1, d.x, d.y)) { S.espera = { item: d.yield.item, qty: 1, done: () => { n.state = 'depleted'; n.until = now() + d.respawnMs; tired(); } }; return; }
    game('Una <b>pepita de oro</b> quedó en la mochila. Las monedas se acuñan en el horno.', 'oro');
    addXp('mining', d.xp); n.state = 'depleted'; n.until = now() + d.respawnMs; tired();
  } else if (d.type === 'mine_chest') {
    if (window.Banco) Banco.openPanel();
    nota('Tu depósito: casa, banco y este baúl');
    return;
  } else if (d.type === 'mineral_rock') {
    if (!needTool(d.tool)) return;
    if (n.state !== 'active') return game(`La roca está agotada. Vuelve en ${secs()} s.`, 'aviso');
    const q = rnd(d.yield.min, d.yield.max);
    const guardar = (where) => { if (where === 'mochila' && !invAdd(d.yield.item, q)) return; tintinear(d.yield.item); floatText(d.x, d.y, `+${q} ${W.items[d.yield.item].name}`); nota('+' + q + ' ' + W.items[d.yield.item].name); questProgress('collect', d.yield.item, q); S.player.miningUntil = now() + 800; addXp('mining', d.xp); n.state = 'depleted'; n.until = now() + d.respawnMs; tired(); save(); };
    if (S.net && S.net.ok) {
      S.metalOptimistic = invAdd(d.yield.item, q) ? { item: d.yield.item, qty: q } : null;
      S.espera = { server: true, item: d.yield.item, qty: q, done: (where) => {
        const pending = S.metalOptimistic;
        S.metalOptimistic = null;
        if (where === 'mochila' && pending && pending.item === d.yield.item) {
          tintinear(d.yield.item); floatText(d.x, d.y, `+${q} ${W.items[d.yield.item].name}`); nota('+' + q + ' ' + W.items[d.yield.item].name); questProgress('collect', d.yield.item, q); S.player.miningUntil = now() + 800; addXp('mining', d.xp); n.state = 'depleted'; n.until = now() + d.respawnMs; tired(); save();
          return;
        }
        if (pending && pending.item === d.yield.item) invRemove(pending.item, pending.qty);
        guardar(where);
      } };
      sendGesto('picar', d.x, d.y);
      S.net.ws.send(JSON.stringify({ t: 'recoger', item: d.yield.item, qty: q, kind: 'ore', spot: d.id }));
      return;
    }
    if (!invAdd(d.yield.item, q)) { S.espera = { item: d.yield.item, qty: q, done: (where) => { if (where === 'banco') guardar('banco'); } }; return; }
    tintinear(d.yield.item); floatText(d.x, d.y, `+${q} ${W.items[d.yield.item].name}`); nota('+' + q + ' ' + W.items[d.yield.item].name); questProgress('collect', d.yield.item, q); S.player.miningUntil = now() + 800;
    addXp('mining', d.xp); n.state = 'depleted'; n.until = now() + d.respawnMs; tired(); save();
  }
}
function hunt(a) {
  const d = a.def;
  if (d.protected || d.species === 'guacharaca' || (window.Guacharaca && Guacharaca.blockedItem(d.species))) {
    game('La <b>Guacharaca</b> es fauna protegida. No se caza, no se captura y no se vende.', 'aviso');
    return;
  }
  if (d.species === 'gallo' || d.species === 'gallina' || (window.Gallos && Gallos.killable && Gallos.killable(d.species))) {
    game('No se mata. Se puede atrapar y, si es gallo, vender.', 'aviso');
    return;
  }
  if (!needTool(d.tool)) return; if (a.state !== 'alive') return;
  const got = [];
  for (const y of d.yield) if (Math.random() < y.chance) got.push([y.item, rnd(y.min, y.max)]);
  const antes = S.inv.map(slot => slot ? { ...slot } : null);
  if (got.some(([item, qty]) => !give(item, qty, a.x, a.y - (item === 'carne' ? 0 : 0.4)))) {
    S.inv = antes; save(); renderInv(); return;
  }
  game(`Cazas un <b>${NOMBRES[d.species].toLowerCase()}</b> con la lanza.`); addXp('hunting', d.xp); a.state = 'hunted'; a.until = now() + d.respawnMs; tired();
}

// ---------------- entrada ----------------
const screenToWorld = (sx, sy) => ({ x: sx / zoom + S.cam.x, y: sy / zoom + S.cam.y });
let sostenerTimer = 0;
cv.addEventListener('pointerdown', (e) => {
  if (!W || !started) return; $('#ayuda').hidden = true; if (S.dialog) return advanceDialog();
  const w = screenToWorld(e.clientX, e.clientY); const t = hitTest(w.x, w.y);
  clearTimeout(sostenerTimer);
  sostenerTimer = setTimeout(() => sendGesto('sostener', w.x / TS, w.y / TS), 420);
  const soltar = () => { clearTimeout(sostenerTimer); cv.removeEventListener('pointerup', soltar); cv.removeEventListener('pointercancel', soltar); };
  cv.addEventListener('pointerup', soltar); cv.addEventListener('pointercancel', soltar);
  if (t) { S.player.repaths = 0; approach(t); return; }
  const tx = Math.floor(w.x / TS), ty = Math.floor(w.y / TS);
  if (walkable(tx, ty)) goTo(tx, ty); else game('No se puede caminar ahí.', 'aviso');
});
const cityView = { zoom: 1, panX: 0, panY: 0 };
let mapPin = null;
function setMapPin(tx, ty) {
  if (!W || !Number.isFinite(tx) || !Number.isFinite(ty)) return;
  const x = Math.max(0, Math.min(W.width - 1, Math.floor(tx)));
  const y = Math.max(0, Math.min(W.height - 1, Math.floor(ty)));
  mapPin = { x, y };
  const bar = $('#city-map-go'); if (bar) bar.hidden = false;
  const label = $('#city-map-go-label'); if (label) label.textContent = 'Destino marcado';
  if (window.LIVE3D && LIVE3D.setMapPin) LIVE3D.setMapPin(mapPin);
  if (!$('#city-map').hidden && !window.LIVE3D?.mapOpen) drawCityMap();
}
function clearMapPin() {
  mapPin = null;
  const bar = $('#city-map-go'); if (bar) bar.hidden = true;
  if (window.LIVE3D && LIVE3D.setMapPin) LIVE3D.setMapPin(null);
  if ($('#city-map') && !$('#city-map').hidden && !window.LIVE3D?.mapOpen) drawCityMap();
}
function travelIdForPark(park) {
  const id = park && park.id;
  if (id === 'parque_envigado') return 'envigado';
  if (id === 'parque_sabaneta') return 'sabaneta';
  if (id === 'parque_itagui') return 'itagui';
  if (id === 'parque_bello') return 'bello';
  return TRAVEL_IDS.has(id) ? id : '';
}
function fillMapPlaces() {
  const row = $('#city-map-muni');
  if (!row || !window.VALLE_GEO) return;
  row.replaceChildren();
  const mina = document.createElement('button');
  mina.type = 'button';
  mina.textContent = 'Ir a la mina';
  mina.onclick = (ev) => { ev.stopPropagation(); irALaMina(); };
  row.append(mina);
  for (const park of VALLE_GEO.parques || []) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = park.name;
    b.onclick = (ev) => {
      ev.stopPropagation();
      if (!started) {
        const where = $('#city-map-location');
        if (where) where.textContent = 'Entra al mundo para caminar a ' + park.name + '.';
        return;
      }
      closeCityMap();
      const id = travelIdForPark(park);
      const src = id && ((W.waypoints || []).find(item => item.id === id) || (W.mapLabels || []).find(item => item.id === id));
      if (id) { viajarA(id); return; }
      if (src) { setRoute(src.x, src.y, park.name); return; }
      const box = VALLE_GEO.bounds;
      const x = (park.lon - box.lonW) / (box.lonE - box.lonW) * (W.width - 1);
      const y = (box.latN - park.lat) / (box.latN - box.latS) * (W.height - 1);
      setRoute(x, y, park.name);
    };
    row.append(b);
  }
  for (const spot of destinosVisibles()) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = spot.name + ' · ' + spot.recurso;
    b.onclick = (ev) => {
      ev.stopPropagation();
      if (!started) {
        const where = $('#city-map-location');
        if (where) where.textContent = 'Entra al mundo para ir a ' + spot.name + '.';
        return;
      }
      viajarA(spot.id);
    };
    row.append(b);
  }
}
function openCityMap() {
  if (S && S.keys) S.keys.clear();
  cityView.zoom = 1; cityView.panX = 0; cityView.panY = 0;
  mapPin = null;
  const bar = $('#city-map-go'); if (bar) bar.hidden = true;
  const canvas = $('#city-map-canvas');
  if (canvas) canvas.hidden = false;
  $('#city-map').hidden=false;
  const globe = $('#b-globo'); if (globe) globe.setAttribute('aria-expanded','true');
  fillMapPlaces();
  try { drawCityMap(); } catch (err) {}
  const close = $('#city-map-close'); if (close) close.focus();
}
function closeCityMap() {
  if (window.LIVE3D && LIVE3D.closeValleyMap) LIVE3D.closeValleyMap();
  const canvas = $('#city-map-canvas'); if (canvas) canvas.hidden = false;
  $('#city-map').hidden=true;
  const globe = $('#b-globo'); if (globe) { globe.setAttribute('aria-expanded','false'); globe.focus(); }
  closeTravelAsk();
  clearMapPin();
}
const TRAVEL_IDS=new Set(['barbosa','girardota','copacabana','bello','medellin','itagui','envigado','sabaneta','la_estrella','caldas','parque_bolivar','las_palmas']);
const DESTINO_IDS=new Set(['mina','cantera','rio_claro','finca','cafetal','madera','banco','skate','parque_envigado','casa']);
const SAFE_KINDS=new Set(['cobble','path','grass','grass_worn','grass_flowers','bridge','asphalt','pavement']);
const SKATE_BLOCK=new Set(['84,273','85,273','84,274','85,274','86,273','86,274']);
function tileKindAt(x,y){return inside(x,y)?W.tiles[W.ground[y][x]].kind:'';}
function tileSafe(x,y,blocked){if(!inside(x,y)||W.collision[y][x]!==0)return false;if(blocked&&blocked.has(x+','+y))return false;const kind=tileKindAt(x,y);return kind!=='water'&&SAFE_KINDS.has(kind);}
function tileBeside(x,y,radius,blocked){for(let ring=0;ring<=radius;ring++)for(let dy=-ring;dy<=ring;dy++)for(let dx=-ring;dx<=ring;dx++)if(Math.max(Math.abs(dx),Math.abs(dy))===ring&&tileSafe(x+dx,y+dy,blocked))return [x+dx,y+dy];return null;}
function destinosLocales(){
 if(!W)return [];
 if(W._destinos)return W._destinos;
 const nodes=W.nodes||[];
 const block=list=>new Set(list.map(n=>n.x+','+n.y));
 const list=[];
 const push=(id,name,x,y,recurso,mark,color,corto)=>{if(x==null||y==null)return;list.push({id,name,x,y,recurso,mark,color,corto:corto||name});};
 const river=new Set((((W.waterBodies||{}).rio_claro||{}).tiles||[]).map(t=>t[0]+','+t[1]));
 const gold=nodes.filter(n=>n.type==='nodo_oro_fluvial'&&river.has(n.x+','+n.y));
 if(gold.length){const spot=tileBeside(gold[0].x,gold[0].y,3,block(gold));if(spot)push('rio_claro','Río Claro',spot[0],spot[1],'oro (río, batea)','Au','#e2b23c','oro · batea');}
 const ores=nodes.filter(n=>n.type==='mineral_rock'&&(n.mineral==='cobre'||n.mineral==='plata'));
 if(ores.length){const spot=tileBeside(ores[0].x,ores[0].y,2,block(ores));if(spot)push('cantera','Cantera',spot[0],spot[1],'plata, cobre (pico)','Ag','#c46a3a','plata/cobre');}
 const pines=nodes.filter(n=>n.type==='wood_tree');
 if(pines.length){const spot=tileBeside(pines[0].x,pines[0].y,2,block(pines));if(spot)push('madera','Pinos',spot[0],spot[1],'madera','Md','#2f6a32','madera');}
 const palmas=(W.waypoints||[]).find(p=>p.id==='las_palmas');
 if(palmas){const spot=tileBeside(palmas.x,palmas.y,4,null);if(spot)push('finca','Cafetal',spot[0],spot[1],'café, cacao','Cf','#6f8f55','café, cacao');}
 const mina=(W.waypoints||[]).find(p=>p.id==='cantera');
 if(mina)push('mina','Mina de Las Palmas',mina.x,mina.y,'plata, cobre (pico)','Pk','#d7c4a3','mina · pico');
 else if(W.mineEntrance)push('mina','Mina de Las Palmas',W.mineEntrance.x,W.mineEntrance.y+1,'plata, cobre (pico)','Pk','#d7c4a3','mina · pico');
 if(window.Banco){const spot=tileBeside(Banco.OUTSIDE.x,Banco.OUTSIDE.y,1,null);if(spot)push('banco','Banco Envigado',spot[0],spot[1],'casa bancaria','Bn','#f3ead7','banco');}
 if(window.EnvigadoPark&&EnvigadoPark.skateTiles){const tile=EnvigadoPark.skateTiles()[0];if(tile){const spot=tileBeside(tile.x,tile.y,2,SKATE_BLOCK);if(spot)push('skate','Skate',spot[0],spot[1],'skate','Sk','#9ecbff','skate');}}
 const park=(W.waypoints||[]).find(p=>p.id==='envigado');
 if(park){const spot=nearestSafe(park.x,park.y);if(spot)push('parque_envigado','Parque de Envigado',spot[0],spot[1],'parque','Pq','#7dcea0','parque');}
 W._destinos=list;
 window.SaimonDestinos=list;
 return list;
}
function destinosVisibles(){
 const list=destinosLocales().slice();
 const home=(window.Hogar&&S.me&&Hogar.stand(S.me.municipio))||(window.Casa&&{x:Casa.PARK_STAND.x,y:Casa.PARK_STAND.y});
 if(home){const spot=tileBeside(home.x,home.y,1,null);if(spot)list.push({id:'casa',name:'Tu casa',x:spot[0],y:spot[1],recurso:'hogar',mark:'Ca',color:'#f7f1e4',corto:'casa'});}
 return list;
}
window.destinosVisibles = destinosVisibles;
function puntoDe(id){
 const key=id==='cafetal'?'finca':id;
 const extra=destinosVisibles().find(s=>s.id===key);
 if(extra)return extra;
 const wp=(W.waypoints||[]).find(item=>item.id===id)||(W.mapLabels||[]).find(item=>item.id===id);
 if(!wp)return null;
 const spot=nearestSafe(wp.x,wp.y);
 if(!spot)return null;
 return {id,name:wp.name||travelName(id),x:spot[0],y:spot[1],recurso:''};
}
function destinoCerca(tx,ty){
 let best=null,bestD=3;
 for(const spot of destinosVisibles()){
  const d=Math.max(Math.abs(spot.x-tx),Math.abs(spot.y-ty));
  if(d<bestD){best=spot;bestD=d;}
 }
 for(const label of W.mapLabels||[]){
  if(!TRAVEL_IDS.has(label.id))continue;
  const d=Math.max(Math.abs(label.x-tx),Math.abs(label.y-ty));
  if(d<bestD){best={id:label.id,name:label.name,x:label.x,y:label.y,recurso:''};bestD=d;}
 }
 return best;
}
let viajeEn=0;
let mmHits=[];
let travelPick=null;
function travelName(id){const label=(W.mapLabels||[]).find(item=>item.id===id);return label?label.name:id;}
function closeTravelAsk(){const box=$('#viaje-dialogo'); if(box) box.hidden=true; travelPick=null;}
function openTravelAsk(pick, name){
  travelPick=pick;
  const box=$('#viaje-dialogo');
  $('#viaje-pregunta').textContent='¿Teletransportarte a '+name+'?';
  const yes=$('#viaje-si'); if(yes) yes.textContent='Confirmar';
  const no=$('#viaje-no'); if(no) no.textContent='Cancelar';
  box.hidden=false;
  if(yes) yes.focus();
}
function viajarA(id){
  if(!started) return;
  if(!TRAVEL_IDS.has(id)&&!DESTINO_IDS.has(id)){ game('No se puede teletransportar ahí.', 'aviso'); return; }
  const ahora=performance.now();
  if(ahora<viajeEn){ game('Espera un momento para volver a viajar.', 'aviso'); return; }
  viajeEn=ahora+2500;
  closeTravelAsk();
  closeCityMap();
  if(S.net.ok&&S.net.ws&&S.net.ws.readyState===1){ S.net.ws.send(JSON.stringify({t:'travel', id})); return; }
  const spot=puntoDe(id);
  if(!spot){ game('No se puede teletransportar ahí.', 'aviso'); return; }
  aterrizar(spot.x, spot.y, spot.name);
}
function askTravel(id){
  if(!started||(!TRAVEL_IDS.has(id)&&!DESTINO_IDS.has(id))) return;
  viajarA(id);
}
function askMapSpot(x, y){
  if(!started) return;
  const near=destinoCerca(Math.floor(x), Math.floor(y));
  if(near){ viajarA(near.id); return; }
  setMapPin(x, y);
  game('Ese punto no es un destino. Pulsa Ir aquí para caminar.', 'aviso');
}
function canvasPoint(canvas,event){
  const rect=canvas.getBoundingClientRect();
  return {x:(event.clientX-rect.left)*(canvas.width/rect.width), y:(event.clientY-rect.top)*(canvas.height/rect.height)};
}
function labelHit(px,py,toPixel,unit){
  const cityScale=MAP_REF/Math.max(W.width,W.height);
  const k=unit/cityScale;
  const labels=[...(W.mapLabels||[])].filter(item=>TRAVEL_IDS.has(item.id)).sort((a,b)=>(a.kind==='municipio'?0:1)-(b.kind==='municipio'?0:1));
  for(const label of labels){
    const [ax,ay]=toPixel(label.x,label.y);
    const box=mapLabelBox(label,k);
    const x=ax+(label.dx||0)*k-box.w/2, y=ay+(label.dy||0)*k;
    const onLabel=px>=x&&px<=x+box.w&&py>=y&&py<=y+box.h;
    const onMark=Math.hypot(px-ax,py-ay)<=Math.max(8,10*k);
    if(onLabel||onMark) return label.id;
  }
  return null;
}
function placeOnCity(x,y){
  const prev=W.mapId||'city';
  if(prev!=='city'&&cityMap){
    if(prev==='mine') caveNodes=S.nodes;
    if(prev==='casa') casaNodes=S.nodes;
    if(prev==='city'){cityNodes=S.nodes;cityAnimals=S.animals;}
    Object.assign(W,cityMap); W.mapId='city'; S.nodes=cityNodes; S.animals=cityAnimals;
    document.body.classList.remove('in-mine','in-casa','in-banco','in-central');
    document.body.dataset.zone='city';
    if(window.Casa) Casa.setEditing(false);
    drawMinimapBase();
  }
  const p=S.player;
  p.x=p.fx=x; p.y=p.fy=y; p.path=[]; p.pending=null; p.busyUntil=0; S.dest=null; S.keys.clear();
  if(window.Simulacion&&Simulacion.syncHorse) Simulacion.syncHorse();
  save();
  if(S.net.ok&&S.net.ws) S.net.ws.send(JSON.stringify({t:'move', zone:'city', x, y, dir:p.dir, moving:false, level:totalLevel()}));
}
function aterrizar(x,y,name){
  const veil=$('#viaje-vuelo');
  if(veil) veil.classList.remove('activo');
  placeOnCity(x,y);
  closeCityMap();
  const titulo=name||'el valle';
  mostrarLeyenda(titulo, false);
  if(window.LIVE3D&&LIVE3D.startLanding) LIVE3D.startLanding(x,y,titulo);
}
function flyTo(x,y,name){ aterrizar(x,y,name); }
function nearestSafe(tx,ty){
  const kindAt=(x,y)=>W.tiles[W.ground[y][x]].kind;
  const open=(x,y)=>inside(x,y)&&W.collision[y][x]===0&&kindAt(x,y)!=='water';
  const good=(x,y)=>open(x,y)&&['cobble','path','grass','grass_worn','grass_flowers','bridge','asphalt','pavement'].includes(kindAt(x,y));
  if(good(tx,ty)) return [tx,ty];
  for(let r=1;r<=16;r++) for(let dy=-r;dy<=r;dy++) for(let dx=-r;dx<=r;dx++) if(Math.max(Math.abs(dx),Math.abs(dy))===r&&good(tx+dx,ty+dy)) return [tx+dx,ty+dy];
  if(open(tx,ty)) return [tx,ty];
  for(let r=1;r<=16;r++) for(let dy=-r;dy<=r;dy++) for(let dx=-r;dx<=r;dx++) if(Math.max(Math.abs(dx),Math.abs(dy))===r&&open(tx+dx,ty+dy)) return [tx+dx,ty+dy];
  return null;
}
function confirmTravel(){
  const id=travelPick; if(!id) return;
  if(typeof id==='object'){ closeTravelAsk(); game('Ese punto no es un destino. Pulsa Ir aquí para caminar.', 'aviso'); return; }
  viajarA(id);
}
$('#viaje-si').onclick=confirmTravel;
$('#viaje-no').onclick=closeTravelAsk;
function nearestWalkable(tx, ty, radius) {
  const limit = radius == null ? 6 : radius;
  for (let r = 0; r <= limit; r++) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) if (Math.max(Math.abs(dx), Math.abs(dy)) === r && walkable(tx + dx, ty + dy)) return [tx + dx, ty + dy];
  return null;
}
function walkFromMinimap(px, py) {
  if (!started || !W) return;
  const cx = mm.width / 2, cy = mm.height / 2;
  if (Math.hypot(px - cx, py - cy) > mm.width / 2 - 1) return;
  const v = mmView();
  const tile = window.HudLayoutCore && HudLayoutCore.minimapTile ? HudLayoutCore.minimapTile(px, py, v, mm.width) : { x: Math.floor(v.x0 + px / (mm.width / v.span)), y: Math.floor(v.y0 + py / (mm.width / v.span)) };
  if (!tile) return;
  const spot = nearestWalkable(tile.x, tile.y, 8);
  if (!spot) { game('No se puede caminar ahí.', 'aviso'); return; }
  setRoute(spot[0], spot[1], 'ese punto');
}
function walkToMarked() {
  if (!mapPin || !started) return;
  if ((W.mapId || 'city') !== 'city') { game('Sal al valle para caminar hasta esa marca. También puedes ir al parque de un municipio.', 'aviso'); return; }
  const spot = nearestWalkable(mapPin.x, mapPin.y, 14);
  if (!spot) { game('No se puede caminar ahí.', 'aviso'); return; }
  closeCityMap();
  goTo(spot[0], spot[1]);
}
function zoomCity(dir) {
  if (!W) return;
  const prev = cityView.zoom || 1;
  const next = Math.max(1, Math.min(6, Math.round(prev * (dir < 0 ? 1.25 : 0.8) * 100) / 100));
  if (next === prev) return;
  const k = next / prev;
  cityView.zoom = next;
  cityView.panX *= k;
  cityView.panY *= k;
  drawCityMap();
}
function zoomMap(dir) {
  if (window.LIVE3D && LIVE3D.mapOpen && typeof LIVE3D.zoomMap === 'function') { LIVE3D.zoomMap(dir); return; }
  zoomCity(dir);
}
mm.addEventListener('click', (e) => {
  e.stopPropagation();
  const rect = mm.getBoundingClientRect();
  const px = (e.clientX - rect.left) * (mm.width / rect.width);
  const py = (e.clientY - rect.top) * (mm.height / rect.height);
  let best = null, bestD = 14;
  for (const hit of mmHits) {
    const d = Math.hypot(px - hit.x, py - hit.y);
    if (d < bestD) { best = hit; bestD = d; }
  }
  if (best) { viajarA(best.id); return; }
  walkFromMinimap(px, py);
});
const mapSurface = $('#city-map-view');
const mapPointers = new Map();
let mapPinch = 0, mapDrag = null;
function mapEventTile(e) {
  const canvas = $('#city-map-canvas');
  const rect = canvas.getBoundingClientRect();
  if (e.clientX < rect.left || e.clientY < rect.top || e.clientX > rect.right || e.clientY > rect.bottom) return null;
  const pt = canvasPoint(canvas, e);
  if (window.ValleMapa && window.VALLE_GEO) return ValleMapa.hit(canvas, cityView, pt.x, pt.y, W);
  const frame = cityFrame();
  const tx = Math.floor((pt.x - frame.left) / frame.scale);
  const ty = Math.floor((pt.y - frame.top) / frame.scale);
  if (tx < 0 || ty < 0 || tx >= W.width || ty >= W.height) return null;
  return { tx, ty, pt, frame };
}
if (mapSurface) {
  mapSurface.addEventListener('pointerdown', (e) => {
    if ($('#city-map').hidden || (window.LIVE3D && LIVE3D.mapOpen)) return;
    if (e.target.closest('button, a, input')) return;
    mapSurface.setPointerCapture(e.pointerId);
    mapPointers.set(e.pointerId, [e.clientX, e.clientY]);
    mapDrag = { x: e.clientX, y: e.clientY, panX: cityView.panX, panY: cityView.panY, moved: false };
    mapPinch = 0;
  });
  mapSurface.addEventListener('pointermove', (e) => {
    if (!mapPointers.has(e.pointerId) || (window.LIVE3D && LIVE3D.mapOpen)) return;
    mapPointers.set(e.pointerId, [e.clientX, e.clientY]);
    if (mapPointers.size > 1) {
      const pts = [...mapPointers.values()];
      const d = Math.hypot(pts[0][0] - pts[1][0], pts[0][1] - pts[1][1]);
      if (mapPinch && d > 0) {
        const prev = cityView.zoom;
        cityView.zoom = Math.max(1, Math.min(6, prev * d / mapPinch));
        const k = cityView.zoom / prev;
        cityView.panX *= k;
        cityView.panY *= k;
      }
      mapPinch = d;
      if (mapDrag) mapDrag.moved = true;
      drawCityMap();
      return;
    }
    if (!mapDrag) return;
    const dx = e.clientX - mapDrag.x, dy = e.clientY - mapDrag.y;
    if (Math.hypot(dx, dy) > 6) mapDrag.moved = true;
    if (!mapDrag.moved) return;
    const canvas = $('#city-map-canvas');
    const rect = canvas.getBoundingClientRect();
    cityView.panX = mapDrag.panX + dx * (canvas.width / rect.width);
    cityView.panY = mapDrag.panY + dy * (canvas.height / rect.height);
    drawCityMap();
  });
  const endMapPointer = (e) => {
    const moved = mapDrag && mapDrag.moved;
    mapPointers.delete(e.pointerId);
    if (mapPointers.size < 2) mapPinch = 0;
    if (mapPointers.size > 0) return;
    mapDrag = null;
    if (moved || $('#city-map').hidden || (window.LIVE3D && LIVE3D.mapOpen) || !started) return;
    const hit = mapEventTile(e);
    if (!hit) return;
    const placeId = hit.id || (hit.frame && hit.frame.scale != null ? labelHit(hit.pt.x, hit.pt.y, (x, y) => [hit.frame.left + (x + .5) * hit.frame.scale, hit.frame.top + (y + .5) * hit.frame.scale], hit.frame.scale) : null);
    if (placeId && (TRAVEL_IDS.has(placeId) || DESTINO_IDS.has(placeId))) { viajarA(placeId); return; }
    const near = destinoCerca(hit.tx, hit.ty);
    if (near) { viajarA(near.id); return; }
    closeCityMap();
    setRoute(hit.tx, hit.ty, 'ese punto');
  };
  mapSurface.addEventListener('pointerup', endMapPointer);
  mapSurface.addEventListener('pointercancel', (e) => { mapPointers.delete(e.pointerId); if (mapPointers.size === 0) { mapDrag = null; mapPinch = 0; } });
  mapSurface.addEventListener('wheel', (e) => {
    if ($('#city-map').hidden || (window.LIVE3D && LIVE3D.mapOpen)) return;
    e.preventDefault();
    zoomCity(e.deltaY > 0 ? 1 : -1);
  }, { passive: false });
}
$('#city-map-close').onclick=closeCityMap;
$('#city-map').addEventListener('click',e=>{if(e.target===$('#city-map'))closeCityMap();});
(function () {
  const head = document.querySelector('#city-map .city-map-panel header');
  if (!head) return;
  let y0 = 0;
  head.addEventListener('pointerdown', (e) => { y0 = e.clientY; });
  head.addEventListener('pointerup', (e) => { if (e.clientY - y0 > 48) closeCityMap(); });
})();
const globeBtn = $('#b-globo'); if (globeBtn) globeBtn.onclick = (e) => { e.stopPropagation(); openCityMap(); };
const zoomIn = $('#city-map-in'); if (zoomIn) zoomIn.onclick = (e) => { e.stopPropagation(); zoomMap(-1); };
const zoomOut = $('#city-map-out'); if (zoomOut) zoomOut.onclick = (e) => { e.stopPropagation(); zoomMap(1); };
const walkBtn = $('#city-map-walk'); if (walkBtn) walkBtn.onclick = (e) => { e.stopPropagation(); walkToMarked(); };
const clearBtn = $('#city-map-clear'); if (clearBtn) clearBtn.onclick = (e) => { e.stopPropagation(); clearMapPin(); };
$('#mm-zoom').onclick = (e) => { e.stopPropagation(); S.mmZoom = S.mmZoom === 1 ? 2 : 1; $('#mm-zoom').textContent = S.mmZoom === 1 ? '+' : '−'; };
cv.addEventListener('pointermove', (e) => {
  if (!W) return; const w = screenToWorld(e.clientX, e.clientY); const t = hitTest(w.x, w.y); S.hover = t; const tip = $('#tooltip');
  if (t) { tip.classList.remove('tip-item'); tip.hidden = false; tip.innerHTML = describe(t); tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY + 12) + 'px'; } else if (!tip.classList.contains('tip-item')) tip.hidden = true;
});
cv.addEventListener('pointerleave', () => { $('#tooltip').hidden = true; S.hover = null; });
const typing = () => document.activeElement && ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName);
addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !$('#hud-chat').hidden) { window.ChatUI.setOpen(false); e.preventDefault(); return; }
  if (e.key==='Escape' && $('#viaje-dialogo') && !$('#viaje-dialogo').hidden) { closeTravelAsk(); e.preventDefault(); return; }
  if (e.key==='Escape' && !$('#city-map').hidden) { closeCityMap(); e.preventDefault(); return; }
  if (typing()) { if (e.key === 'Escape') document.activeElement.blur(); return; }
  if (!started) return;
  const k = e.key.toLowerCase();
  if (e.key === 'Enter' && started) { window.ChatUI.setOpen(true, true); e.preventDefault(); return; }
  if (S.dialog && (k === ' ' || k === 'enter')) return advanceDialog();
  if (['w','a','s','d','arrowup','arrowdown','arrowleft','arrowright','x'].includes(k)) { S.keys.add(k); e.preventDefault(); }
  if (/^[1-8]$/.test(k) && window.Emotes && Emotes.isOpen()) { Emotes.play(Number(k)); e.preventDefault(); return; }
  if (/^[0-9]$/.test(k)) { const i = (+k + 9) % 10; if (S.inv[i]) { S.sel = i; renderInv(); } }
  if (k === '+' || k === '=') zoom = Math.min(2.5, zoom + 0.15);
  if (k === '-') zoom = Math.max(0.5, zoom - 0.15);
  if (k === 'h') $('#ayuda').hidden = !$('#ayuda').hidden;
  if (k === 'i') toggle('#w-inv'); if (k === 'k') toggle('#w-hab'); if (k === 'q') toggle('#p-misiones'); if (k === 'n') toggleNight();
  if (k === 'l' && window.Simulacion) Simulacion.toggleLibro();
  if ((k === 'm' || k === 'e') && window.Simulacion) { if (S.skating) S.skating = false; if (S.mounted) Simulacion.dismount(); else Simulacion.summonAndMount(); }
  if (k === 'g') toggleSkate();
  if (k === 'escape') { $('#ayuda').hidden = true; $('#w-inv').hidden = true; $('#w-hab').hidden = true; const libro = $('#w-libro'); if (libro) libro.hidden = true; }
});
addEventListener('keyup', (e) => S.keys.delete(e.key.toLowerCase()));
addEventListener('wheel', (e) => { if (e.target === cv) zoom = Math.max(0.5, Math.min(2.5, zoom - Math.sign(e.deltaY) * 0.1)); }, { passive: true });
function toggle(sel) { const el = $(sel); el.hidden = !el.hidden; }
function circadianState(atMs) {
  const c = W.circadian;
  if (!c || c.enabled === false) return null;
  const dur = (c.phaseDurationMinutes || 10) * 60 * 1000;
  const epoch = c.epochMs || 0;
  const phases = c.phases || ['day', 'night'];
  const t = Math.max(0, (atMs == null ? Date.now() : atMs) - epoch);
  const index = Math.floor(t / dur) % phases.length;
  return { name: phases[index], index, remainingMs: dur - (t % dur), durationMs: dur };
}
function isNightPhase(name) { return name === 'night' || name === 'noche'; }
function updateNightIcon() {
  const ico = $('#ico-noche'); if (ico) ico.src = BASE + 'graphics/ui/' + (S.night ? 'sol' : 'luna') + '.png';
  const btn = $('#b-noche');
  if (btn) {
    const st = circadianState();
    if (st) {
      const mins = Math.max(1, Math.ceil(st.remainingMs / 60000));
      const ahora = S.night ? 'Noche' : 'Día';
      btn.title = ahora + ' · cambia en ' + mins + ' min (N previsualiza)';
    } else btn.title = 'Día / noche (N)';
    }
}
function applyCircadian(announce) {
  const st = circadianState();
  if (!st) return st;
  if (S.circadianIndex !== st.index) {
    S.circadianIndex = st.index;
    S.nightOverride = null;
    const night = isNightPhase(st.name);
    if (S.night !== night) {
      S.night = night;
      if (announce && started) {
        if (!S.night && window.Gallos) Gallos.onGameDawn(S.reloj);
        else game(S.night ? 'Anochece en El Jardín.' : 'Amanece en El Jardín.', 'juego');
      }
    }
  } else if (S.nightOverride == null) {
    S.night = isNightPhase(st.name);
  }
  updateNightIcon();
  return st;
}
function toggleNight() {
  S.nightOverride = !S.night;
  S.night = S.nightOverride;
  updateNightIcon();
}
$('#b-inv').onclick = () => toggle('#w-inv'); $('#b-hab').onclick = () => toggle('#w-hab'); $('#b-mis').onclick = () => toggle('#p-misiones');
$('#b-soc').onclick = () => toggle('#p-cercanos'); $('#b-noche').onclick = toggleNight; $('#b-ayuda').onclick = () => toggle('#ayuda');
document.querySelectorAll('[data-cierra]').forEach(b => b.onclick = () => { $('#' + b.dataset.cierra).hidden = true; });
const cerrarAyuda = () => { $('#ayuda').hidden = true; };
const btnAyuda = $('#btn-cerrar-ayuda'); if (btnAyuda) btnAyuda.onclick = cerrarAyuda;
const btnJugar = $('#btn-jugar'); if (btnJugar) btnJugar.onclick = cerrarAyuda;
$('#btn-reiniciar').onclick = () => { localStorage.removeItem('lifeinc.eljardin.v3'); location.reload(); };
function resize() { const r = devicePixelRatio || 1; cv.width = innerWidth * r; cv.height = innerHeight * r; }
addEventListener('resize', resize);

// ---------------- simulación ----------------
const SPEED = 4.2;
let last = performance.now();
function portalAt(x, y) {
  const ids = W.mapId==='mine' ? ['salida_mina'] : W.mapId==='casa' ? ['puerta_salida'] : W.mapId==='banco' ? ['salida_banco'] : W.mapId==='central' ? ['salida_central'] : ['entrada_mina_palmas', 'puerta_casa', 'puerta_banco', 'puerta_central'];
  for (const id of ids) { const n = S.nodes.get(id); if (n && n.def.x===x && n.def.y===y) return n; }
  return null;
}
function updateMinePrompt() {
  const b = document.getElementById('mine-enter'), e = W.mineEntrance;
  const chip = document.getElementById('mina-brujula');
  const outdoors = !!(started && e && (W.mapId || 'city') === 'city');
  if (chip) {
    if (chip.hidden === outdoors) chip.hidden = !outdoors;
    if (outdoors) {
      const dx = e.x - S.player.fx, dy = e.y - S.player.fy;
      const label = 'Mina · ' + Math.max(0, Math.round(Math.hypot(dx, dy) * 2)) + ' m';
      const text = document.getElementById('mina-texto');
      if (text && text.textContent !== label) text.textContent = label;
      const arrow = document.getElementById('mina-flecha');
      if (arrow) arrow.style.transform = 'rotate(' + (Math.atan2(dy, dx) * 180 / Math.PI) + 'deg)';
    }
  }
  if (!b || !e) return;
  const near = started && W.mapId !== 'mine' && cheb(S.player.x, S.player.y, e.x, e.y) <= 5;
  if (b.hidden === near) b.hidden = !near;
}
function updateSign() {
  if (!window.Letrero) return;
  let near = false;
  for (const n of S.nodes.values()) {
    if (n.def && n.def.type === 'mine_sign' && cheb(S.player.x, S.player.y, n.def.x, n.def.y) <= 2) near = true;
  }
  Letrero.setNear(started && near);
}
function update(dt) {
  updateMinePrompt();
  updateSign();
  if (!started) return;
  const p = S.player, t = now();
  const steer = ['w','a','s','d','arrowup','arrowdown','arrowleft','arrowright'].some(k => S.keys.has(k)) || S.keys.has('joystick');
  if (S.dest && S.dest.ruta && steer) { p.path = []; S.dest = null; S.rideAuto = false; }
  const running = S.keys.has('x') && ['w','a','s','d','arrowup','arrowdown','arrowleft','arrowright'].some(k => S.keys.has(k));
  const sprinting = running && !S.mounted && !S.sprintLock && S.energy > 0;
  S.pace = S.mounted ? 'caballo' : (sprinting ? 'corriendo' : ((S.player.path && S.player.path.length) ? 'caminando' : 'quieto'));
  if (S.houseEdit) { p.path = []; S.dest = null; }
  else if (S.rideAuto && S.mounted && S.keys.size && !S.dialog) { p.path = []; S.dest = null; S.rideAuto = false; }
  else if (!p.path.length && S.keys.size && !S.dialog) {
    let dx = 0, dy = 0; const K = S.keys;
    if (K.has('w') || K.has('arrowup')) dy = -1; if (K.has('s') || K.has('arrowdown')) dy = 1;
    if (K.has('a') || K.has('arrowleft')) dx = -1; if (K.has('d') || K.has('arrowright')) dx = 1;
    if (window.LiveInk?.keyboardDirection) [dx, dy] = window.LiveInk.keyboardDirection(dx, dy);
    let nx = p.x + dx, ny = p.y + dy;
    if (dx && dy && (!walkable(p.x + dx, p.y) || !walkable(p.x, p.y + dy))) { if (walkable(p.x + dx, p.y)) ny = p.y; else if (walkable(p.x, p.y + dy)) nx = p.x; }
    const portal = (dx || dy) && (portalAt(p.x + dx, p.y + dy) || portalAt(p.x + dx, p.y) || portalAt(p.x, p.y + dy));
    if (portal && now() > (S.portalUntil || 0)) {
      if (S.mounted && ['home_door', 'mine_entrance', 'mine_exit', 'bank_door'].includes(portal.def.type)) { game('Baja del caballo para entrar a un edificio.', 'aviso'); S.portalUntil = now() + 900; return; }
      S.portalUntil = now() + 1500; S.keys.clear(); act({ kind: 'node', n: portal }); return;
    }
    if ((dx || dy) && walkable(nx, ny)) { p.path = [[nx, ny]]; p.pending = null; S.dest = null; }
    else if (dx || dy) p.dir = dx > 0 ? 'right' : dx < 0 ? 'left' : dy > 0 ? 'down' : 'up';
  }
  const joy = S.keys.has('joystick');
  const power = joy && window.LiveInk && LiveInk.stickPower ? Math.max(0.28, LiveInk.stickPower()) : 1;
  const cruise = SPEED * (joy ? power : 1) * (S.mounted ? Simulacion.speedMul() : (S.skating ? 1.9 : (sprinting ? 1.75 : 1)));
  if (p.emote === 'sit' && t < (p.emoteUntil || 0)) p.path = [];
  const want = p.path.length ? cruise * (p.path.length <= 1 ? 0.62 : 1) : 0;
  p.speed = window.Motion ? Motion.approach(p.speed || 0, want, dt, sprinting ? 10 : 6.5, 12) : want;
  if (p.path.length) {
    let budget = Math.max(p.speed || 0, want > 0 && (p.speed || 0) < 0.35 ? 0.35 : 0) * dt;
    let guard = 0;
    while (p.path.length && budget > 1e-4 && guard++ < 40) {
      const [nx, ny] = p.path[0]; const ddx = nx - p.fx, ddy = ny - p.fy, d = Math.hypot(ddx, ddy);
      if (Math.abs(ddx) > 0.01 || Math.abs(ddy) > 0.01) p.dir = Math.abs(ddx) > Math.abs(ddy) ? (ddx > 0 ? 'right' : 'left') : (ddy > 0 ? 'down' : 'up');
      if (d > budget) { p.fx += ddx / d * budget; p.fy += ddy / d * budget; budget = 0; break; }
      budget -= d;
      p.fx = nx; p.fy = ny; p.x = nx; p.y = ny; p.path.shift(); updateTutorial();
      if (!p.path.length) {
        if (S.dest && S.dest.ruta && cheb(p.x, p.y, S.dest.x, S.dest.y) <= 1) game('Llegaste a ' + esc(S.dest.name || 'ese lugar') + '.', 'juego');
        S.dest = null;
        if (p.pending) {
          const tg = p.pending; p.pending = null; const tt = targetTile(tg);
          if (tg.kind === 'door' ? (p.x === tg.d.approach.x && p.y === tg.d.approach.y) : cheb(p.x, p.y, tt.x, tt.y) <= 1) act(tg);
          else if (tg.kind === 'animal' && tg.a.state === 'alive' && p.repaths++ < 4) approach(tg);
          else if (tg.kind === 'animal') game('El animal se alejó.', 'aviso');
          budget = 0;
        } else if ((S.mounted || S.skating || S.keys.has('joystick')) && budget > 1e-4 && !S.dialog && !S.houseEdit) {
          let mx = 0, my = 0; const K = S.keys;
          if (K.has('w') || K.has('arrowup')) my = -1; if (K.has('s') || K.has('arrowdown')) my = 1;
          if (K.has('a') || K.has('arrowleft')) mx = -1; if (K.has('d') || K.has('arrowright')) mx = 1;
          if (window.LiveInk?.keyboardDirection) [mx, my] = window.LiveInk.keyboardDirection(mx, my);
          let tx = p.x + mx, ty = p.y + my;
          if (mx && my && (!walkable(p.x + mx, p.y) || !walkable(p.x, p.y + my))) { if (walkable(p.x + mx, p.y)) ty = p.y; else if (walkable(p.x, p.y + my)) tx = p.x; }
          if ((mx || my) && walkable(tx, ty)) p.path = [[tx, ty]];
          else budget = 0;
        }
      }
    }
    p.animT += dt * (1 + (p.speed || 0) / SPEED);
  } else p.animT += dt * 0.2;
  if (window.Simulacion) Simulacion.syncHorse();
  skateTick(dt);
  updateSkateButton();
  if (window.Caballo) Caballo.tick(dt, horseContext());
  if (window.Guacharaca) Guacharaca.tick(dt, { mapId: W.mapId || 'city', x: S.player.fx, y: S.player.fy, now: Date.now() });
  if (window.Gallos) Gallos.tick(dt, { mapId: W.mapId || 'city', x: S.player.fx, y: S.player.fy, now: Date.now() });
  if (window.Fauna) Fauna.tick(dt);
  if (window.Corral) {
    const casa = (window.HOGARES && HOGARES.casas || []).find(item => item.id === (S.me && S.me.municipio));
    Corral.tick(dt, casa || null);
    paintAtrapar();
  }
  if(W.mapId==='casa' && !S.houseEdit && p.x===Casa.DOOR.x && p.y===Casa.DOOR.y && !p.path.length && now()>(S.portalUntil||0)) { S.portalUntil=now()+900; exitHouse(); }
  if(W.mapId==='banco' && p.x===6 && p.y===9 && !p.path.length && now()>(S.portalUntil||0)) { S.portalUntil=now()+900; switchMap('city'); }
  if(W.mapId==='central' && p.x===6 && p.y===9 && !p.path.length && now()>(S.portalUntil||0)) { S.portalUntil=now()+900; switchMap('city'); }
  sendMove(false);
  for (const n of S.nodes.values()) {
    if (!n.until || t < n.until) continue;
    const d = n.def; n.until = 0;
    if (d.type === 'farm_plot' && n.state === 'planted') { n.state = 'grown'; floatText(d.x, d.y, '¡Lista para cosechar!', '#c8f59a'); }
    else if (d.type !== 'farm_plot') n.state = d.initialState;
  }
  for (const a of S.animals) {
    if (a.state === 'hunted') { if (t >= a.until) { a.state = 'alive'; a.x = a.fx = a.def.x; a.y = a.fy = a.def.y; } continue; }
    if (Math.abs(a.fx - a.x) > 0.01 || Math.abs(a.fy - a.y) > 0.01) {
      const ddx = a.x - a.fx, ddy = a.y - a.fy, d = Math.hypot(ddx, ddy), st = 2.2 * dt;
      if (d <= st) { a.fx = a.x; a.fy = a.y; } else { a.fx += ddx / d * st; a.fy += ddy / d * st; }
      a.frame = Math.floor(t / 150) % 2;
    } else if (t > a.nextMove) {
      a.frame = 0; a.nextMove = t + 1800 + Math.random() * 3500;
      const [dx, dy] = [[1,0],[-1,0],[0,1],[0,-1]][rnd(0, 3)]; const nx = a.x + dx, ny = a.y + dy;
      const busy = S.animals.some(o => o !== a && o.state === 'alive' && o.x === nx && o.y === ny) || (nx === p.x && ny === p.y);
      const kind = inside(nx, ny) && W.tiles[W.ground[ny][nx]].kind;
      if (walkable(nx, ny) && !busy && cheb(nx, ny, a.def.x, a.def.y) <= a.def.wanderRadius && kind !== 'path' && kind !== 'cobble') { a.x = nx; a.y = ny; }
    }
  }
  for (const o of S.others.values()) {
    const step = window.Motion ? Motion.follow(o.fx, o.fy, o.x, o.y, dt) : { x: o.x, y: o.y, speed: 0, moving: false };
    o.fx = step.x; o.fy = step.y; o.speed = step.speed;
    o.walking = step.moving || (o.moving && t - o.lastMove < 300);
    if (o.walking) o.animT = (o.animT || 0) + dt * (o.pace === 'corriendo' ? 1.6 : 1);
    else if (o.moving && t - o.lastMove > 1500) o.moving = false;
  }
  if (S.animals.some(a => a.state === 'alive' && cheb(a.x, p.x, a.y, p.y) <= 1) && t > (S.biteUntil || 0)) {
    S.biteUntil = t + 1500;
    damagePlayer(8);
  }
  if (window.HudLayoutCore) {
    const stepped = HudLayoutCore.staminaStep(S.energy, S.sprintLock, sprinting, p.path.length > 0, dt);
    S.energy = stepped.energy;
    S.sprintLock = stepped.locked;
    S.hp = HudLayoutCore.healthStep(S.hp, S.hurtUntil || 0, t, dt);
  }
  paintRings();
  S.floaters = S.floaters.filter(f => t - f.t0 < 1400);
  for (const [k, b] of S.bubbles) if (t > b.until) S.bubbles.delete(k);
}

// ---------------- dibujo ----------------
function drawSpriteAt(key, wx, wy) { const s = W.sprites[key], im = imgs[key]; if (s && im) ctx.drawImage(im, Math.round(wx - s.anchorX), Math.round(wy - s.anchorY)); }
const drawSprite = (key, tx, ty) => drawSpriteAt(key, tx * TS + 32, (ty + 1) * TS);
function frameKey(d, t) { return d.frames ? d.frames[Math.floor(t / (d.frameMs || 200)) % d.frames.length] : d.sprite; }
function bar(x, y, frac, col) { ctx.fillStyle = 'rgba(20,12,4,.75)'; ctx.fillRect(x - 20, y, 40, 6); ctx.fillStyle = col; ctx.fillRect(x - 19, y + 1, Math.max(0, 38 * frac), 4); }
function drawHorseAt(fx, fy, dir, walking) {
  const key = walking && Math.floor(now() / 160) % 2 ? 'caballo_1' : 'caballo_0';
  const im = imgs[key], sp = W.sprites[key];
  if (!im || !sp) return;
  const dx = Math.round((fx + 0.5) * TS - sp.anchorX), dy = Math.round((fy + 1) * TS - sp.anchorY);
  if (dir === 'left') { ctx.save(); ctx.translate(dx + sp.w, dy); ctx.scale(-1, 1); ctx.drawImage(im, 0, 0); ctx.restore(); }
  else ctx.drawImage(im, dx, dy);
}
function drawChar(sheet, fx, fy, dir, walking, animT, frameRow) {
  const P = W.player, row = P.rows[dir] ?? 0; const fr = walking ? P.walkFrames[Math.floor(animT * 8) % P.walkFrames.length] : P.idleFrame;
  ctx.drawImage(sheet, fr * P.frameW, row * P.frameH, P.frameW, P.frameH, Math.round(fx * TS + 32 - P.anchorX), Math.round((fy + 1) * TS - P.anchorY), P.frameW, P.frameH);
}
function nameplate(x, y, lines) {
  ctx.textAlign = 'center'; let yy = y;
  for (const [txt, col, size] of lines) { ctx.font = `bold ${size || 12}px Pixelify, sans-serif`; ctx.fillStyle = '#000'; ctx.fillText(txt, x + 1, yy + 1); ctx.fillStyle = col; ctx.fillText(txt, x, yy); yy += (size || 12) + 1; }
}
function speech(x, y, text) {
  ctx.font = '13px Pixelify, sans-serif'; const words = text.split(' '); const lines = []; let cur = '';
  for (const w of words) { const t = cur ? cur + ' ' + w : w; if (ctx.measureText(t).width > 170 && cur) { lines.push(cur); cur = w; } else cur = t; } lines.push(cur);
  const wdt = Math.max(...lines.map(l => ctx.measureText(l).width)) + 14, h = lines.length * 15 + 8, bx = x - wdt / 2, by = y - h - 10;
  ctx.fillStyle = 'rgba(20,14,8,.88)'; ctx.strokeStyle = '#b48a46'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.roundRect ? ctx.roundRect(bx, by, wdt, h, 6) : ctx.rect(bx, by, wdt, h); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(x - 6, by + h); ctx.lineTo(x, by + h + 8); ctx.lineTo(x + 6, by + h); ctx.fill();
  ctx.fillStyle = '#fff1c9'; ctx.textAlign = 'center'; lines.forEach((l, i) => ctx.fillText(l, x, by + 17 + i * 15));
}
function yellowArrow(wx, wy, t) {
  const bob = Math.sin(t / 180) * 6, on = Math.floor(t / 350) % 2 === 0;
  ctx.save(); ctx.translate(wx, wy - 18 + bob); ctx.globalAlpha = on ? 1 : 0.55;
  ctx.fillStyle = '#ffe14d'; ctx.strokeStyle = '#3a2600'; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.moveTo(-9, -30); ctx.lineTo(9, -30); ctx.lineTo(9, -12); ctx.lineTo(18, -12); ctx.lineTo(0, 6); ctx.lineTo(-18, -12); ctx.lineTo(-9, -12); ctx.closePath(); ctx.fill(); ctx.stroke();
  ctx.restore();
}
function draw() {
  const r = devicePixelRatio || 1, vw = cv.width / r / zoom, vh = cv.height / r / zoom, p = S.player, t = now();
  const mapW = W.width * TS, mapH = W.height * TS;
  S.cam.x = vw > mapW ? (mapW - vw) / 2 : Math.max(0, Math.min(mapW - vw, (p.fx + 0.5) * TS - vw / 2));
  S.cam.y = vh > mapH ? (mapH - vh) / 2 : Math.max(0, Math.min(mapH - vh, (p.fy + 0.5) * TS - vh / 2));
  ctx.setTransform(r * zoom, 0, 0, r * zoom, -S.cam.x * r * zoom, -S.cam.y * r * zoom);
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = '#0f170b'; ctx.fillRect(S.cam.x - 64, S.cam.y - 64, vw + 128, vh + 128);
  const x0 = Math.max(0, Math.floor(S.cam.x / TS)), y0 = Math.max(0, Math.floor(S.cam.y / TS));
  const x1 = Math.min(W.width - 1, Math.ceil((S.cam.x + vw) / TS)), y1 = Math.min(W.height - 1, Math.ceil((S.cam.y + vh) / TS));
  const cols = W.tileset.columns;
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const id = W.ground[y][x]; ctx.drawImage(tileset, (id % cols) * TS, Math.floor(id / cols) * TS, TS, TS, x * TS, y * TS, TS + 0.5, TS + 0.5);
    if (W.elevation && W.mapId !== 'casa' && W.mapId !== 'mine') {
      const h = W.elevation[y][x], west = W.elevation[y][Math.max(0, x - 1)], north = W.elevation[Math.max(0, y - 1)][x];
      const shade = Math.max(-0.42, Math.min(0.32, (west - h) * 0.08 + (north - h) * 0.05));
      if (shade) { ctx.fillStyle = shade > 0 ? `rgba(255,244,214,${shade})` : `rgba(16,26,14,${-shade})`; ctx.fillRect(x * TS, y * TS, TS, TS); }
      if (Math.floor(h / 8) !== Math.floor(west / 8)) { ctx.fillStyle = 'rgba(42,32,18,.38)'; ctx.fillRect(x * TS, y * TS, 3, TS); }
    }
  }
  const list = [];
  for (const n of S.nodes.values()) {
    const d = n.def;
    if (d.type === 'fishing_spot' || d.type === 'nodo_oro_fluvial') {
      const bob = n.state === 'active' ? Math.sin(t / 400 + d.x) * 1.5 : 0; drawSprite(spriteKeyFor(n), d.x, d.y + bob / TS);
      if (n.until) bar(d.x * TS + 32, d.y * TS + 4, 1 - (n.until - t) / d.respawnMs, '#7fc8ff');
    } else list.push({ y: (d.y + 1) * TS, x: d.x, draw: () => {
      drawSprite(spriteKeyFor(n), d.x, d.y);
      if (n.until) { const total = d.type === 'farm_plot' ? d.growMs : d.respawnMs; bar(d.x * TS + 32, (d.y + 1) * TS - (d.type === 'farm_plot' ? 98 : 20), 1 - (n.until - t) / total, d.type === 'farm_plot' ? '#8ccf4a' : '#ffd27a'); }
    } });
  }
  for (const dc of W.decorations) {
    const w = dc.w || 1, h = dc.h || 1;
    list.push({ y: (dc.y + h) * TS + (dc.sortOffset || 0), x: dc.x, draw: () => drawSpriteAt(frameKey(dc, t), (dc.x + w / 2) * TS, (dc.y + h) * TS) });
  }
  if ((W.mapId || 'city') === 'city' && window.EnvigadoPark && EnvigadoPark.allProps) {
    EnvigadoPark.drawn2d.length = 0;
    for (const prop of EnvigadoPark.allProps()) list.push({ y: (prop.y + 1) * TS, x: prop.x, draw: () => EnvigadoPark.paint2d(ctx, prop, TS) });
  }
  for (const a of S.animals) if (a.state === 'alive') list.push({ y: (a.fy + 1) * TS + 1, x: a.fx, draw: () => drawSprite(a.def.sprites.alive[a.frame], a.fx, a.fy) });
  for (const npc of W.npcs || []) list.push({ y: (npc.y + 1) * TS + 2, x: npc.x, draw: () => {
    const sheet = npc.id === 'profesora_cadena' && imgs._profesora ? imgs._profesora : capatazImg;
    if (sheet) drawChar(sheet, npc.x, npc.y, npc.facing || 'down', false, 0);
    const cx = npc.x * TS + 32, top = (npc.y + 1) * TS - 96;
    nameplate(cx, top - 4, [[npc.name, npc.id === 'profesora_cadena' ? '#9fd8e6' : '#ffe14d', 13]]);
    if (npc.id === 'capataz' && !S.quest.turnedIn && (!stepDone(S.quest.def.steps[0]) || S.quest.done)) { ctx.font = 'bold 26px Pixelify, sans-serif'; ctx.fillStyle = '#000'; ctx.fillText(S.quest.done ? '?' : '!', cx + 2, top - 18 + Math.sin(t / 200) * 2); ctx.fillStyle = '#ffd400'; ctx.fillText(S.quest.done ? '?' : '!', cx, top - 20 + Math.sin(t / 200) * 2); }
  } });
  for (const m of S.mounts || []) if (!m.ridden) list.push({ y: (m.fy + 1) * TS + 2, x: m.fx, draw: () => drawHorseAt(m.fx, m.fy, 'right', false) });
  for (const o of S.others.values()) list.push({ y: (o.fy + 1) * TS + 2, x: o.fx, draw: () => {
    drawChar(sheets[o.color] || sheets.default, o.fx, o.fy, o.dir || 'down', o.walking, t / 1000);
    const cx = o.fx * TS + 32, top = (o.fy + 1) * TS - 96;
    nameplate(cx, top - 20, [[nombreAjeno(o), '#ffffff', 12], ...(o.clan ? [[`<${o.clan}>`, '#ffd27a', 11]] : []), [`Nv. ${o.level || 1}`, '#b8e0ff', 11]]);
  } });
  list.push({ y: (p.fy + 1) * TS + 3, x: p.fx, draw: () => {
    ctx.strokeStyle = 'rgba(120,255,120,.75)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.ellipse(p.fx * TS + 32, (p.fy + 1) * TS - 12, 20, 8, 0, 0, Math.PI * 2); ctx.stroke();
    if (S.mounted) drawHorseAt(p.fx, p.fy, p.dir, !!p.path.length);
    if (S.skating) { ctx.fillStyle = '#e4d2ad'; ctx.fillRect(p.fx * TS + 18, (p.fy + 1) * TS - 18, 28, 10); ctx.fillStyle = '#2c3136'; ctx.fillRect(p.fx * TS + 20, (p.fy + 1) * TS - 16, 4, 4); ctx.fillRect(p.fx * TS + 40, (p.fy + 1) * TS - 16, 4, 4); }
    drawChar(sheets[S.me.color] || sheets.default, p.fx, S.mounted ? p.fy - 0.35 : p.fy, p.dir, !!p.path.length, p.animT);
    const sel = selected(); if (sel && W.items[sel].category === 'tool' && imgs['icon:' + sel]) ctx.drawImage(imgs['icon:' + sel], Math.round(p.fx * TS + 40), Math.round((p.fy + 1) * TS - 56), 24, 24);
    const cx = p.fx * TS + 32, top = (p.fy + 1) * TS - 96;
    nameplate(cx, top - 20, [[nombrePropio(), '#9df59a', 12], ...(S.me.clan ? [[`<${S.me.clan}>`, '#ffd27a', 11]] : []), [`Nv. ${totalLevel()}`, '#b8e0ff', 11]]);
  } });
  if (S.dest) { // marca de clic amarilla
    const k = Math.min(1, (t - (S.dest.t || 0)) / 300), dx = S.dest.x * TS + 32, dy = S.dest.y * TS + 32, s = 10 - k * 3;
    ctx.strokeStyle = '#ffe14d'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(dx - s, dy - s); ctx.lineTo(dx + s, dy + s); ctx.moveTo(dx + s, dy - s); ctx.lineTo(dx - s, dy + s); ctx.stroke();
  }
  if (S.hover) {
    const tt = targetTile(S.hover), hx = S.hover.kind === 'animal' ? S.hover.a.fx : tt.x, hy = S.hover.kind === 'animal' ? S.hover.a.fy : tt.y;
    ctx.strokeStyle = 'rgba(255,225,77,.9)'; ctx.lineWidth = 2; ctx.setLineDash([6, 4]); ctx.strokeRect(hx * TS + 2, hy * TS + 2, TS - 4, TS - 4); ctx.setLineDash([]);
  }
  list.sort((a, b) => a.y - b.y || a.x - b.x).forEach(o => o.draw());
  // globos de chat
  for (const [id, b] of S.bubbles) {
    const o = id === 0 || id === S.net.id ? { fx: p.fx, fy: p.fy } : S.others.get(id); if (!o) continue;
    speech(o.fx * TS + 32, (o.fy + 1) * TS - 130, b.text);
  }
  const at = arrowTarget(); if (at && !S.dialog) yellowArrow(at.x * TS + 32, at.y * TS + 32 - at.h, t);
  ctx.font = 'bold 14px Pixelify, sans-serif'; ctx.textAlign = 'center';
  S.floaters.forEach((f, i) => { const k = (t - f.t0) / 1400, y = f.y - 20 - k * 28 - i * 16; ctx.globalAlpha = Math.max(0, 1 - k * k); ctx.fillStyle = '#000'; ctx.fillText(f.text, f.x + 1, y + 1); ctx.fillStyle = f.color; ctx.fillText(f.text, f.x, y); });
  ctx.globalAlpha = 1;
  if (S.night) drawNight(t);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  if (!S.night) { const g = ctx.createRadialGradient(cv.width / 2, cv.height / 2, cv.height * 0.35, cv.width / 2, cv.height / 2, cv.height * 0.9); g.addColorStop(0, 'rgba(255,220,150,0.04)'); g.addColorStop(1, 'rgba(30,20,0,0.28)'); ctx.fillStyle = g; ctx.fillRect(0, 0, cv.width, cv.height); }
  if (at && !S.dialog) edgeArrow(at, t);
  drawMinimap(at);
}
function edgeArrow(at, t) {   // si el objetivo está fuera de pantalla, flecha amarilla en el borde apuntando hacia él
  const r = devicePixelRatio || 1, W2 = cv.width / r, H2 = cv.height / r;
  const sx = ((at.x * TS + 32) - S.cam.x) * zoom, sy = ((at.y * TS + 32 - at.h) - S.cam.y) * zoom;
  if (sx > 40 && sy > 40 && sx < W2 - 40 && sy < H2 - 40) return;
  const cx = W2 / 2, cy = H2 / 2, ang = Math.atan2(sy - cy, sx - cx);
  const k = Math.min((W2 / 2 - 60) / Math.abs(Math.cos(ang) || 1e-6), (H2 / 2 - 90) / Math.abs(Math.sin(ang) || 1e-6));
  const px = cx + Math.cos(ang) * k, py = cy + Math.sin(ang) * k, on = Math.floor(t / 350) % 2 === 0;
  ctx.save(); ctx.setTransform(r, 0, 0, r, 0, 0); ctx.translate(px, py); ctx.rotate(ang); ctx.globalAlpha = on ? 1 : 0.55;
  ctx.fillStyle = '#ffe14d'; ctx.strokeStyle = '#3a2600'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(22, 0); ctx.lineTo(-4, -20); ctx.lineTo(-4, -8); ctx.lineTo(-24, -8); ctx.lineTo(-24, 8); ctx.lineTo(-4, 8); ctx.lineTo(-4, 20); ctx.closePath(); ctx.fill(); ctx.stroke();
  ctx.restore();
}
let nightCv;
function drawNight(t) {
  const r = devicePixelRatio || 1;
  if (!nightCv || nightCv.width !== cv.width || nightCv.height !== cv.height) { nightCv = document.createElement('canvas'); nightCv.width = cv.width; nightCv.height = cv.height; }
  const n = nightCv.getContext('2d'); n.setTransform(1, 0, 0, 1, 0, 0); n.globalCompositeOperation = 'source-over';
  n.clearRect(0, 0, nightCv.width, nightCv.height); n.fillStyle = 'rgba(8,14,44,0.66)'; n.fillRect(0, 0, nightCv.width, nightCv.height);
  n.setTransform(r * zoom, 0, 0, r * zoom, -S.cam.x * r * zoom, -S.cam.y * r * zoom); n.globalCompositeOperation = 'destination-out';
  const lights = [];
  for (const d of W.decorations) {
    if (d.light) lights.push([(d.x + 0.5) * TS, (d.y + 1) * TS - 78, d.light.radius * (0.95 + 0.05 * Math.sin(t / 90 + d.x))]);
    for (const [lx, ly] of d.lights || []) lights.push([(d.x + (d.w || 1) * lx) * TS, (d.y + (d.h || 1) * ly) * TS - 40, 80]);
  }
  lights.push([(S.player.fx + 0.5) * TS, (S.player.fy + 0.5) * TS, 120]);
  for (const [x, y, rad] of lights) { const g = n.createRadialGradient(x, y, 0, x, y, rad); g.addColorStop(0, 'rgba(0,0,0,0.95)'); g.addColorStop(1, 'rgba(0,0,0,0)'); n.fillStyle = g; n.beginPath(); n.arc(x, y, rad, 0, Math.PI * 2); n.fill(); }
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(nightCv, 0, 0);
  ctx.setTransform(r * zoom, 0, 0, r * zoom, -S.cam.x * r * zoom, -S.cam.y * r * zoom); ctx.globalCompositeOperation = 'lighter';
  for (const [x, y, rad] of lights.slice(0, -1)) { const g = ctx.createRadialGradient(x, y, 0, x, y, rad * 0.7); g.addColorStop(0, 'rgba(255,150,50,0.28)'); g.addColorStop(1, 'rgba(255,120,30,0)'); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, rad * 0.7, 0, Math.PI * 2); ctx.fill(); }
  ctx.globalCompositeOperation = 'source-over';
}
let mmBase;
function drawMinimapBase() {
  const k = 4; mmBase = document.createElement('canvas'); mmBase.width = W.width * k; mmBase.height = W.height * k; const c = mmBase.getContext('2d');
  const col = { mountain:'#5a7554',rocky:'#83836d',asphalt:'#444b50',pavement:'#b8b4a3', grass: '#5f9a3a', grass_flowers: '#6aa443', grass_worn: '#7f9a48', path: '#c09058', water: '#2ab0c0', bridge: '#8a5a2b', cobble: '#a8a090' };
  for (let y = 0; y < W.height; y++) for (let x = 0; x < W.width; x++) {
    if (W.mapId==='casa') { const kind=window.Casa.floor.get(x+','+y); c.fillStyle=!kind?'#f4f0e6':kind==='patio'?'#6f8f55':kind==='door'?'#6b4228':'#c4623c'; c.fillRect(x*k,y*k,k,k); continue; }
    const kind=W.tiles[W.ground[y][x]].kind; c.fillStyle = W.mapId==='mine'?(W.collision[y][x]?'#35291e':'#80603d'):(col[kind] || '#5f9a3a'); if(kind==='mountain'&&W.mapId!=='mine'){const v=Math.round(70+W.elevation[y][x]*1.6);c.fillStyle=`rgb(${v},${Math.min(154,v+26)},${Math.max(58,v-12)})`;}  c.fillRect(x * k, y * k, k, k);
    if(W.elevation&&W.mapId!=='casa'&&W.mapId!=='mine'){const h=W.elevation[y][x],west=W.elevation[y][Math.max(0,x-1)],north=W.elevation[Math.max(0,y-1)][x];const s=Math.max(-.5,Math.min(.28,(west-h)*.07+(north-h)*.05));if(s){c.fillStyle=s>0?`rgba(255,255,255,${s})`:`rgba(0,0,0,${-s})`;c.fillRect(x*k,y*k,k,k);}if(Math.floor(h/8)!==Math.floor(west/8)){c.fillStyle='rgba(28,22,12,.7)';c.fillRect(x*k,y*k,1,k);}}
  }
  if (W.mapId==='casa' && window.Casa) { for (const it of Casa.layout.items) { const s=Casa.cellsOf(it); c.fillStyle=Casa.CATALOG[it.type].solid?'#6b4228':'#e6c27a'; for (const [x,y] of s) c.fillRect(x*k+1,y*k+1,k-2,k-2); } }
  for (const z of W.surfaceZones || []) { c.fillStyle = '#aab0b1'; c.fillRect(z.x*k,z.y*k,z.w*k,z.h*k); }
  for (const d of W.decorations) {
    const colr = { building: '#8a3b2a', waterfall: '#6e6258', fountain: '#9fe0ea', fence: '#7a5a34', tree_roble: '#2f6a2a', bush: '#3d7a34', stall: '#c83c30', mine_entrance: '#4a4038', boulder: '#8a8478' }[d.type];
    if (!colr) continue; c.fillStyle = colr;
    if (d.type === 'waterfall') { c.fillRect(d.x * k, d.y * k, (d.w || 1) * k, 3 * k); c.fillStyle = '#e8fbff'; c.fillRect(31 * k, d.y * k, 3 * k, (d.h || 1) * k); }
    else c.fillRect(d.x * k, d.y * k, (d.w || 1) * k, (d.h || 1) * k);
  }
  const landmarkColor={santa_gertrudis:'#f5f3ec',santa_ana:'#f0eadc',torre_unica:'#f7f4ee',capilla:'#f6f1e4',torres_bajas:'#c4a48a',catedral:'#c98962',nave_larga:'#e7e1d4',fronton:'#e6d3a8',aguja:'#efe6d6'};
  for (const d of W.landmarks || []) { c.fillStyle = landmarkColor[d.kind] || '#a88a68'; c.fillRect(d.x*k,d.y*k,d.w*k,d.h*k); }
  const nc = { fruit_tree: '#2e6b2a', wood_tree: '#1f4d2a', farm_plot: '#6b4a26', mineral_rock: '#b0aaa0', fishing_spot: '#e8fbff', nodo_oro_fluvial: '#ffd400' };
  for (const n of W.nodes) if (nc[n.type]) { c.fillStyle = nc[n.type]; c.fillRect(n.x * k + 1, n.y * k + 1, k - 1, k - 1); }
  if ((W.mapId||'city')==='city' && window.EnvigadoPark) {
    for (const t of EnvigadoPark.canecaTiles()) { c.fillStyle = '#d9dde0'; c.fillRect(t.x*k+1, t.y*k+1, k-2, k-2); }
    for (const t of EnvigadoPark.benchTiles()) { c.fillStyle = '#6e4a2c'; c.fillRect(t.x*k, t.y*k+1, k, k-2); }
    for (const t of EnvigadoPark.sculptureTiles()) { c.fillStyle = '#e6d3a2'; c.fillRect(t.x*k+1, t.y*k, k-2, k); }
  }
  if ((W.mapId||'city')==='city' && window.Banco) {
    c.fillStyle = '#f3ead7';
    for (const [x, y] of Banco.SOLIDS) c.fillRect(x*k, y*k, k, k);
  }
  if ((W.mapId||'city')==='city' && window.Central) {
    c.fillStyle = '#14382c';
    for (const [x, y] of Central.SOLIDS) c.fillRect(x*k, y*k, k, k);
  }
  if (W.mapId==='central' && W.floor) {
    for (let y = 0; y < W.height; y++) for (let x = 0; x < W.width; x++) {
      const kind = W.floor.get(x+','+y);
      c.fillStyle = kind==='vault' ? '#e2b23c' : kind==='door' ? '#f6e7a8' : kind==='wall' ? '#0c241c' : '#14382c';
      c.fillRect(x*k, y*k, k, k);
    }
  }
  if (W.mapId==='banco' && W.floor) {
    for (let y = 0; y < W.height; y++) for (let x = 0; x < W.width; x++) {
      const kind = W.floor.get(x+','+y);
      c.fillStyle = kind==='counter' ? '#8a5a32' : kind==='door' ? '#3a2416' : kind==='wall' ? '#6e4a2c' : '#c4a574';
      c.fillRect(x*k, y*k, k, k);
    }
  }
}
function mmView() {
  const span = Math.min(W.width,W.height)/(S.mmZoom===1?2:4);
  return {span,x0:Math.max(0,Math.min(W.width-span,S.player.fx+.5-span/2)),y0:Math.max(0,Math.min(W.height-span,S.player.fy+.5-span/2))};
}
function playerStar(c,x,y,r=6) {
  c.save(); c.translate(x,y); c.beginPath();
  for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rr=i%2?r*.45:r;c.lineTo(Math.cos(a)*rr,Math.sin(a)*rr);}
  c.closePath();c.fillStyle='#ffdf29';c.strokeStyle='#33230c';c.lineWidth=2;c.stroke();c.fill();c.restore();
}
function drawMinimap(at) {
  const v=mmView(),size=mm.width,K=size/v.span,k=4;
  mmHits=[];
  mctx.clearRect(0,0,size,size);mctx.save();mctx.beginPath();mctx.arc(size/2,size/2,size/2,0,Math.PI*2);mctx.clip();
  mctx.fillStyle='#233827';mctx.fillRect(0,0,size,size);mctx.drawImage(mmBase,v.x0*k,v.y0*k,v.span*k,v.span*k,0,0,size,size);
  const point=(x,y)=>[(x+.5-v.x0)*K,(y+.5-v.y0)*K];
  for(const o of S.others.values()){const [x,y]=point(o.fx,o.fy);mctx.fillStyle='#eef4ea';mctx.beginPath();mctx.arc(x,y,2,0,7);mctx.fill();}
  if(at){const [x,y]=point(at.x,at.y);mctx.strokeStyle='#f8bd54';mctx.lineWidth=2;mctx.strokeRect(x-4,y-4,8,8);}
  if((W.mapId||'city')==='city'&&W.mineEntrance){let [x,y]=point(W.mineEntrance.x,W.mineEntrance.y);const cx=size/2,cy=size/2,dd=Math.hypot(x-cx,y-cy),lim=size/2-9;if(dd>lim){x=cx+(x-cx)/dd*lim;y=cy+(y-cy)/dd*lim;}const pulse=5+Math.sin(performance.now()/260)*1.5;mctx.fillStyle='rgba(255,196,60,.35)';mctx.beginPath();mctx.arc(x,y,pulse+4,0,7);mctx.fill();mctx.fillStyle='#ffc93c';mctx.strokeStyle='#2c1a0c';mctx.lineWidth=2;mctx.beginPath();mctx.arc(x,y,5,0,7);mctx.fill();mctx.stroke();mctx.fillStyle='#2c1a0c';mctx.fillRect(x-1,y-3,2,6);}
  if((W.mapId||'city')==='city'&&W.homeDoor){let [x,y]=point(W.homeDoor.x,W.homeDoor.y);const cx=size/2,cy=size/2,dd=Math.hypot(x-cx,y-cy),lim=size/2-9;if(dd>lim){x=cx+(x-cx)/dd*lim;y=cy+(y-cy)/dd*lim;}mctx.fillStyle='#7dcea0';mctx.strokeStyle='#1c3324';mctx.lineWidth=2;mctx.fillRect(x-4,y-5,8,7);mctx.strokeRect(x-4,y-5,8,7);mctx.beginPath();mctx.moveTo(x-5,y-4);mctx.lineTo(x,y-8);mctx.lineTo(x+5,y-4);mctx.closePath();mctx.fill();mctx.stroke();}
  if((W.mapId||'city')==='city'){
    drawMapLabels(mctx,(x,y)=>point(x,y), K, {x:size/2,y:size/2,r:size/2-6});
    const cx=size/2, cy=size/2, lim=size/2-12;
    for(const spot of destinosVisibles()){
      let [x,y]=point(spot.x,spot.y);
      const dd=Math.hypot(x-cx,y-cy);
      if(dd>lim){x=cx+(x-cx)/dd*lim;y=cy+(y-cy)/dd*lim;}
      mctx.fillStyle='#1c140c';
      mctx.beginPath();mctx.arc(x,y,8,0,7);mctx.fill();
      mctx.fillStyle=spot.color||'#f4e2a8';
      mctx.font='700 9px Inter, "Segoe UI", Arial, sans-serif';
      mctx.textAlign='center';mctx.textBaseline='middle';
      mctx.fillText(spot.mark||'•',x,y+0.5);
      mmHits.push({id:spot.id,x,y});
    }
  }
  const route = routeSamples();
  if (route && route.pts.length > 1) {
    mctx.save(); mctx.setLineDash([3, 5]); mctx.strokeStyle = '#ffe14d'; mctx.lineWidth = 2; mctx.beginPath();
    route.pts.forEach((pt, i) => { const [x, y] = point(pt[0], pt[1]); if (i) mctx.lineTo(x, y); else mctx.moveTo(x, y); });
    mctx.stroke(); mctx.restore();
    const [dx, dy] = point(route.x, route.y);
    mctx.fillStyle = '#ff8a3d'; mctx.beginPath(); mctx.arc(dx, dy, 5, 0, 7); mctx.fill();
    mctx.fillStyle = '#fff6df'; mctx.font = '700 11px system-ui, sans-serif'; mctx.textAlign = 'left'; mctx.fillText(route.name || 'Destino', dx + 7, dy);
  }
  if (S.dest) {
    let [x, y] = point(S.dest.x, S.dest.y);
    const cx = size / 2, cy = size / 2, dd = Math.hypot(x - cx, y - cy), lim = size / 2 - 10;
    if (dd > lim) { x = cx + (x - cx) / dd * lim; y = cy + (y - cy) / dd * lim; }
    mctx.strokeStyle = '#ffe14d'; mctx.lineWidth = 2;
    mctx.beginPath(); mctx.arc(x, y, 6, 0, Math.PI * 2); mctx.stroke();
    mctx.beginPath(); mctx.moveTo(x - 8, y); mctx.lineTo(x + 8, y); mctx.moveTo(x, y - 8); mctx.lineTo(x, y + 8); mctx.stroke();
  }
  if (window.Seguir) Seguir.dibujar(mctx, point);
  if (window.Fauna) Fauna.paintMinimap(mctx, point);
  playerStar(mctx,...point(S.player.fx,S.player.fy),7);mctx.restore();
  if(!$('#city-map').hidden && !window.LIVE3D?.mapOpen) drawCityMap();
}
const MAP_CHAR_W=7.4, MAP_PAD_X=6, MAP_REF=(800-84);
function mapLabelBox(label, unit){
  const kind=label.kind||'municipio';
  const w=(label.name.length*MAP_CHAR_W+MAP_PAD_X*2)*unit;
  const h=(kind==='municipio'?22:18)*unit;
  return {w,h};
}
function drawMapLabels(c, toPixel, unit, clip){
  const labels=[...(W.mapLabels||[])].sort((a,b)=>(a.kind==='municipio'?1:0)-(b.kind==='municipio'?1:0));
  const cityScale=MAP_REF/Math.max(W.width,W.height);
  const k=unit/cityScale;
  for(const label of labels){
    const [px,py]=toPixel(label.x,label.y);
    const box=mapLabelBox(label, k);
    const x=px+(label.dx||0)*k-box.w/2, y=py+(label.dy||0)*k;
    if(clip){
      const cx=clip.x, cy=clip.y, r=clip.r-2;
      const inside=[[x,y],[x+box.w,y],[x,y+box.h],[x+box.w,y+box.h]].every(([qx,qy])=>Math.hypot(qx-cx,qy-cy)<=r);
      if(!inside) continue;
    }
    c.fillStyle=label.kind==='poi'?'#2c1a0ce8':'#14251ee8';
    c.fillRect(x,y,box.w,box.h);
    c.fillStyle=label.kind==='poi'?'#ffd66b':'#fff1c9';
    c.font='600 '+(12*k)+'px Inter, "Segoe UI", Arial, sans-serif';
    c.textAlign='center'; c.textBaseline='middle';
    c.fillText(label.name, x+box.w/2, y+box.h/2);
    if(label.kind!=='poi'){c.fillStyle='#f4e2a8';c.fillRect(px-2,py-2,4,4);}
  }
}
function cityFrame() {
  const canvas = $('#city-map-canvas');
  const size = canvas.width;
  const pad = 42;
  const base = (size - pad * 2) / Math.max(W.width, W.height);
  const scale = base * (cityView.zoom || 1);
  const width = W.width * scale;
  const height = W.height * scale;
  return { canvas, size, scale, width, height, left: (size - width) / 2 + cityView.panX, top: (size - height) / 2 + cityView.panY };
}
function drawCityMap() {
  const canvas = $('#city-map-canvas');
  if (window.ValleMapa && window.VALLE_GEO && canvas) {
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ValleMapa.draw(ctx, canvas, cityView, { world: W, player: { x: S.player.fx, y: S.player.fy }, mine: W.mineEntrance || null, route: routeSamples(), follow: window.Seguir ? Seguir.vista() : null, recursos: destinosVisibles() });
    const home = window.Hogar && S.me.municipio && Hogar.casa(S.me.municipio);
    $('#city-map-location').textContent = home ? ('Tu casa · ' + home.name + ' · ★ Tú') : ('Tu posición: ' + S.player.fx.toFixed(1) + ', ' + S.player.fy.toFixed(1) + ' · ★ Tú');
    return;
  }
  const frame = cityFrame();
  const c = canvas.getContext('2d'), size = frame.size, scale = frame.scale, left = frame.left, top = frame.top, width = frame.width, height = frame.height;
  c.clearRect(0,0,size,size);c.fillStyle='#182820';c.fillRect(0,0,size,size);
  c.imageSmoothingEnabled=false;c.drawImage(mmBase,left,top,width,height);
  c.strokeStyle='#a8a17c';c.lineWidth=1;c.strokeRect(left,top,width,height);
  c.fillStyle='#f7e8bb';c.textAlign='center';c.textBaseline='middle';c.font='600 22px Inter, "Segoe UI", Arial, sans-serif';
  c.fillText('N',size/2,top-21);c.fillText('S',size/2,top+height+23);c.fillText('OC',left-22,size/2);c.fillText('OR',left+width+23,size/2);
  for(const o of S.others.values()){c.fillStyle='#eef4ea';c.beginPath();c.arc(left+(o.fx+.5)*scale,top+(o.fy+.5)*scale,2,0,7);c.fill();}
  if((W.mapId||'city')==='city'&&W.mineEntrance){const x=left+(W.mineEntrance.x+.5)*scale,y=top+(W.mineEntrance.y+.5)*scale;c.fillStyle='#ffc93c';c.strokeStyle='#2c1a0c';c.lineWidth=2;c.beginPath();c.arc(x,y,7,0,7);c.fill();c.stroke();}
  if((W.mapId||'city')==='city'&&W.homeDoor){const x=left+(W.homeDoor.x+.5)*scale,y=top+(W.homeDoor.y+.5)*scale;c.fillStyle='#7dcea0';c.strokeStyle='#1c3324';c.lineWidth=2;c.fillRect(x-6,y-6,12,10);c.strokeRect(x-6,y-6,12,10);c.beginPath();c.moveTo(x-8,y-5);c.lineTo(x,y-14);c.lineTo(x+8,y-5);c.closePath();c.fill();c.stroke();}
  drawMapLabels(c,(x,y)=>[left+(x+.5)*scale, top+(y+.5)*scale], scale);
  if (mapPin) {
    const x = left + (mapPin.x + .5) * scale, y = top + (mapPin.y + .5) * scale;
    c.strokeStyle = '#ff8a3d'; c.lineWidth = 3;
    c.beginPath(); c.arc(x, y, 8, 0, Math.PI * 2); c.stroke();
    c.beginPath(); c.moveTo(x, y - 14); c.lineTo(x, y + 14); c.moveTo(x - 14, y); c.lineTo(x + 14, y); c.stroke();
  }
  playerStar(c,left+(S.player.fx+.5)*scale,top+(S.player.fy+.5)*scale,8);
  $('#city-map-location').textContent=`Tu posición: ${S.player.fx.toFixed(1)}, ${S.player.fy.toFixed(1)} · ★ Tú`;
}
let lastUi = 0, lastMap = 0, lastMapKey = '';
function loop(ts) {
  const dt = Math.min(0.05, (ts - last) / 1000); last = ts;
  try { update(dt); } catch (err) { /* un fallo del caballo no puede congelar el paso */ }
  let peerKey = ''; for (const o of S.others.values()) peerKey += '|' + o.id + ':' + Math.round(o.fx) + ',' + Math.round(o.fy);
  const mapKey = Math.floor(S.player.fx) + ',' + Math.floor(S.player.fy) + ':' + (S.dest && S.dest.ruta ? S.dest.x + ',' + S.dest.y + ':' + (S.player.path ? S.player.path.length : 0) : '') + peerKey;
  if (mapKey !== lastMapKey || ts - lastMap > 250) { lastMapKey = mapKey; lastMap = ts; drawMinimap(arrowTarget()); }
  if (ts - lastUi > 500) { lastUi = ts; applyCircadian(true); renderNearby(); renderProfile(); if (S.chat.tab === 'proximidad') renderChatNote(); }
  requestAnimationFrame(loop);
}
function renderChatNote() { const n = $('#chat-nota'); const before = n.innerHTML; renderChat(); if (n.innerHTML === before) return; }

function paintAtrapar() {
  let button = document.getElementById('atrapar-ave');
  if (!button) {
    button = document.createElement('button');
    button.id = 'atrapar-ave';
    button.type = 'button';
    button.className = 'hud';
    button.textContent = 'Atrapar';
    button.style.cssText = 'position:fixed;left:50%;bottom:138px;transform:translateX(-50%);z-index:16';
    button.onclick = () => {
      const bird = (window.Gallos ? Gallos.birds() : []).find(item => item.id === button.dataset.id);
      if (bird && window.Gallos) Gallos.touch(bird);
    };
    document.body.append(button);
    const vender = document.createElement('button');
    vender.id = 'vender-gallo';
    vender.type = 'button';
    vender.className = 'hud';
    vender.textContent = 'Vender gallo';
    vender.style.cssText = 'position:fixed;left:50%;bottom:96px;transform:translateX(-50%);z-index:16';
    vender.onclick = () => {
      const animal = (Corral.animals() || []).find(item => item.species === 'gallo');
      if (!animal) { game('No hay un gallo en tu corral.', 'aviso'); return; }
      Corral.takeOut(animal.id);
      if (invAdd('gallo', 1)) game('El gallo salió del corral. Ya se puede vender o cambiar. No se mata.', 'juego');
      save();
    };
    document.body.append(vender);
  }
  const city = (W.mapId || 'city') === 'city';
  const loose = city && window.Gallos ? Gallos.nearestLoose(S.player, Corral.caught()) : null;
  button.hidden = !loose;
  if (loose) button.dataset.id = loose.id;
  const vender = document.getElementById('vender-gallo');
  if (vender) vender.hidden = !(city && (Corral.animals() || []).some(item => item.species === 'gallo'));
}
function horseContext(){
 const avoid=new Set();
 if(window.Casa){avoid.add(Casa.PARK_DOOR.x+','+Casa.PARK_DOOR.y);avoid.add(Casa.PARK_STAND.x+','+Casa.PARK_STAND.y);}
 const city=cityMap||W;
 return {S:S,W:W,seconds:now()/1000,houses:(window.HOGARES&&HOGARES.casas)||[],avoid:avoid,
  open(x,y){if(x<0||y<0||x>=city.width||y>=city.height||!city.collision[y]||city.collision[y][x]!==0)return false;const tiles=city.tiles||(window.EL_JARDIN&&EL_JARDIN.tiles);const row=city.ground&&city.ground[y];if(!tiles||!row)return true;const kind=tiles[row[x]]&&tiles[row[x]].kind;return kind!=='water'&&kind!=='creek';},
  route(x,y,tx,ty){if((W.mapId||'city')!=='city')return null;return bfs(x,y,(a,b)=>a===tx&&b===ty);}};
}
function ensurePersonalHorse(){
 S.mounts=S.mounts||[];
 let horse=S.mounts.find(m=>m.personal);
 if(!horse){
  const def=(W.mounts&&W.mounts[0])||{id:'caballo',name:'Caballo',speed:4};
  horse={def,id:'caballo-personal',personal:true,x:S.player.x,y:S.player.y,fx:S.player.fx,fy:S.player.fy,ridden:false,coat:(window.Caballo&&Caballo.coat)||'bay',gait:'idle',phase:0,tethered:false,called:false};
  S.mounts.push(horse);
 }
 if(window.Caballo)horse.coat=Caballo.coat;
 return horse;
}
function entranceSpot(){
 const map=W.mapId||'city';
 let door=null;
 for(const n of S.nodes.values()){
  const t=n.def&&n.def.type;
  if(map==='casa'&&t==='casa_exit')door=n.def;
  else if(map==='mine'&&t==='mine_exit')door=n.def;
  else if(map==='banco'&&t==='bank_door')door=n.def;
  else if(map==='city'&&t==='home_door')door=n.def;
 }
 if(door)return nearestSafe(door.x,door.y)||nearestWalkable(door.x,door.y,4);
 if(map==='city'&&window.Casa)return nearestSafe(Casa.PARK_STAND.x,Casa.PARK_STAND.y);
 return nearestSafe(Math.floor(S.player.x),Math.floor(S.player.y));
}
function summonPersonalHorse(){
 if(!started)return;
 const spot=entranceSpot();
 if(!spot){game('No hay sitio junto a la entrada.','aviso');return;}
 const horse=ensurePersonalHorse();
 if(S.mounted===horse&&window.Simulacion)Simulacion.dismount();
 horse.ridden=false;horse.x=horse.fx=spot[0];horse.y=horse.fy=spot[1];
 if(window.Caballo)Caballo.noteSummon(horse);else horse.called=true;
 game('Tu caballo apareció junto a la entrada.','juego');
}
function mountAndGo(x,y,after){
 const spot=nearestSafe(x,y);if(!spot){game('No hay un camino hasta ahí.','aviso');return;}
 if((W.mapId||'city')!=='city'){game('El caballo sólo camina por el valle.','aviso');return;}
 const horse=ensurePersonalHorse();
 horse.x=horse.fx=S.player.x;horse.y=horse.fy=S.player.y;
 if(window.Simulacion){
  if(S.mounted&&S.mounted!==horse)Simulacion.dismount();
  if(!S.mounted)Simulacion.mountHorse(horse, true);
 }
 S.rideAuto=true;
 goTo(spot[0],spot[1]);
 game('El caballo sigue el camino. WASD, las flechas o el joystick lo desvían.','juego');
 if(after){
  const watch=setInterval(()=>{if(!S.player.path.length&&cheb(S.player.x,S.player.y,spot[0],spot[1])<=1){clearInterval(watch);after();}},500);
  setTimeout(()=>clearInterval(watch),180000);
 }
}
function rideHorseTo(place){
 if(!started||!place)return;
 if(place.id==='casa'){
  if((W.mapId||'city')==='mine'){game('Sal de la mina para volver a casa.','aviso');return;}
  if((W.mapId||'city')==='banco'||(W.mapId||'city')==='central')switchMap('city');
  if((W.mapId||'city')==='casa'){game('Ya estás en casa.','juego');return;}
  mountAndGo(Casa.PARK_STAND.x,Casa.PARK_STAND.y,()=>{if(S.mounted&&window.Simulacion)Simulacion.dismount();enterHouse();});
  return;
 }
 if((W.mapId||'city')==='casa')exitHouse();
 else if((W.mapId||'city')!=='city')switchMap('city');
 mountAndGo(place.x,place.y);
}
function irALaMina() {
  if (!started) {
    const where = $('#city-map-location');
    if (where) where.textContent = 'Entra al mundo para ir a la mina.';
    return;
  }
  closeCityMap();
  if ((W.mapId || 'city') === 'mine') { game('Ya estás en la mina. Toca una veta con la pica.', 'juego'); return; }
  if ((W.mapId || 'city') === 'casa') exitHouse();
  if ((W.mapId || 'city') !== 'city') switchMap('city');
  const e = W.mineEntrance;
  if (S.mounted && e) { mountAndGo(e.x, e.y + 1); return; }
  if (S.net.ok && S.net.ws) { S.net.ws.send(JSON.stringify({ t: 'ir_mina' })); return; }
  if (e) placeAtTown({ x: e.x, y: e.y + 1 });
  game('Llegaste a la entrada de la mina.', 'juego');
}
function goMine(){
 if(!started)return;
 if((W.mapId||'city')==='casa')exitHouse();
 if((W.mapId||'city')==='mine'){const n=S.nodes.get('horno_cantera');if(n)goTo(n.def.x,n.def.y+1);game('Estás en la mina. Toca una veta con la pica.');return;}
 const e=S.nodes.get('entrada_mina_palmas');
 if(!e){game('No encuentro la entrada de la mina.','aviso');return;}
 if((W.mapId||'city')!=='city')switchMap('city');
 approach({kind:'node',n:e});
 game('Vamos a la mina de Las Palmas. Al llegar, entra y pica una veta.');
}
window.LiveInk = { get cityNodes(){return cityNodes||S.nodes;},get cityAnimals(){return cityAnimals||S.animals;},get world(){return W;}, state:S, walkable, goTo, setRoute, followRoad, approach, advanceDialog, enterHouse, exitHouse, enterMine(){ if((W.mapId||'city')!=='mine') switchMap('mine'); }, askTravel, summonPersonalHorse, ensurePersonalHorse, rideHorseTo, goMine, damage: damagePlayer, markMap(x, y){ askMapSpot(x, y); }, partidaSnapshot, applyPartida,
 respawnHome: beginAtHome, paintInv: renderInv, remember: save, say: game, grant: addXp, giveItem: invAdd, holding: selected,
 showNote(title, text){ const box=$('#aviso'); if(!box)return; box.hidden=false; $('#aviso-titulo').textContent=title; $('#aviso-txt').textContent=text; },
 click(x,y){if(!started)return; if(S.dialog)return advanceDialog(); const t=hitTest(x*TS+32,(y+1)*TS-8); if(t)approach(t);else if(walkable(Math.floor(x),Math.floor(y)))goTo(Math.floor(x),Math.floor(y));},
 enterBank(){ if(started) switchMap('banco'); },
 interact(id){if(id==='finca_cafe'||id==='finca_cacao'||id==='finca_las_palmas'||id==='finca_libro'){if(window.Finca)Finca.open(id);return;}if(id==='puerta_salida'&&started&&(W.mapId||'city')==='casa'){exitHouse();return;}const mnt=(S.mounts||[]).find(m=>m.id===id);if(mnt&&started){if(S.mounted)Simulacion.dismount();else approach({kind:'mount',m:mnt});return;}const n=S.nodes.get(id);const a=S.animals.find(a=>a.def.id===id);const d=W.doors.find(d=>d.id===id);const npc=W.npcs.find(n=>n.id===id);const t=n?{kind:'node',n}:a?{kind:'animal',a}:d?{kind:'door',d}:npc?{kind:'npc',d:npc}:null;if(t&&started)approach(t);},
 spriteKeyFor, frameKey, now, get started(){return started;} };
// ---------------- prueba automática (?autotest) ----------------
function autotest() {
  const out = []; const ok = (c, m) => out.push((c ? 'OK ' : 'FALLO ') + m);
  Math.random = (() => { let s = 7; return () => (s = (s * 16807) % 2147483647) / 2147483647 * 0.5; })();
  localStorage.removeItem('lifeinc.eljardin.v3'); fresh(); S.quest.doorOpened = false; renderAll();
  const p = S.player; p.x = p.fx = W.spawn.x; p.y = p.fy = W.spawn.y; updateTutorial(true);
  const nextTo = (x, y) => { const path = bfs(W.spawn.x, W.spawn.y, (a, b) => cheb(a, b, x, y) === 1); if (!path) return false; const [ax, ay] = path.length ? path[path.length - 1] : [W.spawn.x, W.spawn.y]; p.x = p.fx = ax; p.y = p.fy = ay; p.path = []; p.busyUntil = 0; return true; };
  const node = id => S.nodes.get(id);
  const tabs = [...document.querySelectorAll('.pestanas button[data-canal]')].map(b => b.textContent.trim());
  ok(JSON.stringify(tabs) === JSON.stringify(['Global', 'Proximidad', 'Clan', 'Grupo']), 'pestañas de chat exactas: ' + tabs.join('/'));
  const circ = W.circadian;
  ok(!!circ && circ.enabled !== false && circ.phaseDurationMinutes === 10 && circ.sync === 'unix', 'ciclo circadiano: 10 min, reloj Unix');
  ok(Array.isArray(circ.phases) && circ.phases.length === 2 && circ.phases.includes('day') && circ.phases.includes('night'), 'fases day/night');
  const st = applyCircadian(false);
  ok(!!st && S.night === isNightPhase(st.name), 'la fase visible sigue el reloj compartido');

  ok(!/Comercio/.test(document.body.innerText), 'sin pestaña Comercio');
  ok(document.querySelector('.marca span').textContent === 'LIFE INC' && $('#zona-nombre').textContent === 'El Jardín', 'marca LIFE INC y zona El Jardín');
  const tut = S.quest.def.tutorial.stages;
  ok(currentStage().id === 'seguir_camino' && /Sigue el camino/.test($('#objetivo-txt').textContent), 'tutorial 1: sigue el camino (caja visible)');
  ok(W.tiles[W.ground[W.spawn.y][W.spawn.x]].kind === 'path', 'spawn sobre camino de tierra');
  ok(!!arrowTarget(), 'flecha amarilla con objetivo');
  const R = tut[0].completeWhen; ok(!!bfs(p.x, p.y, (x, y) => x === R.x && y === R.y), 'camino al pueblo alcanzable');
  p.x = p.fx = R.x; p.y = p.fy = R.y; updateTutorial(); ok(currentStage().id === 'entrar_puerta' && !$('#aviso').hidden, 'tutorial 2: “Continuemos” + entra por la puerta');
  const door = W.doors[0]; ok(!!bfs(R.x, R.y, (x, y) => x === door.approach.x && y === door.approach.y), 'puerta alcanzable');
  p.x = p.fx = door.approach.x; p.y = p.fy = door.approach.y; act({ kind: 'door', d: door });
  ok(!!S.dialog && /bienvenida/i.test($('#dialogo-txt').textContent) && /Toca aquí para continuar/.test($('#dialogo').textContent), 'capataz da la bienvenida (toca para continuar)');
  while (S.dialog) advanceDialog();
  ok(stepDone(S.quest.def.steps[0]) && invCount('hacha') === 1, 'paso 1 completo y recibes el hacha');
  ok(currentStage().id === 'madera', 'tutorial: ahora la madera');
  ok(/Recolecta 10 de madera/.test($('#misiones').textContent) && /\(0\/10\)/.test($('#misiones').textContent), 'panel muestra Recolecta 10 de madera (0/10)');
  let guard = 0;
  while (invCount('madera') < 10 && guard++ < 40) {
    const n = [...S.nodes.values()].find(n => n.def.type === 'wood_tree' && n.state === 'standing');
    if (!n) { timeOffset += 21000; update(0.016); continue; }
    nextTo(n.def.x, n.def.y); act({ kind: 'node', n });
  }
  ok(stepDone(S.quest.def.steps[1]) && /\(10\/10\)/.test($('#misiones').textContent) && $('#misiones li[data-paso="recolectar_madera"] .caja').textContent === '✔', 'madera 10/10 con ✔ en vivo');
  updateTutorial(); ok(currentStage().id === 'piedra', 'tutorial: ahora la piedra');
  guard = 0;
  while (invCount('piedra') < 5 && guard++ < 40) {
    const n = [...S.nodes.values()].find(n => n.def.type === 'mineral_rock' && n.def.mineral === 'piedra' && n.state === 'active');
    if (!n) { timeOffset += 16000; update(0.016); continue; }
    nextTo(n.def.x, n.def.y); act({ kind: 'node', n });
  }
  ok(stepDone(S.quest.def.steps[2]) && /\(5\/5\)/.test($('#misiones').textContent), 'piedra 5/5');
  ok(S.quest.done && currentStage().id === 'entregar', 'volver con el capataz');
  const sai0 = window.Simulacion ? Simulacion.walletSubs(S.me.name) : 0; const cap = W.npcs[0]; nextTo(cap.x, cap.y); act({ kind: 'npc', d: cap }); while (S.dialog) advanceDialog();
  ok(S.quest.turnedIn && window.Simulacion && Simulacion.walletSubs(S.me.name) >= sai0 + Simulacion.SUBS * 250 && currentStage().id === 'libre', 'Primeros Pasos entrega 250 SMC');
  for (const sp of ['manzana', 'pera', 'naranja', 'mango', 'banano', 'coco']) { const n = node(`arbol_${sp}_1`); nextTo(n.def.x, n.def.y); const b = invCount(sp); act({ kind: 'node', n }); ok(invCount(sp) > b && n.state === 'picked', `recoger ${sp}`); }
  const pl = node('parcela_1'); nextTo(pl.def.x, pl.def.y); selectItem('mango_seed'); act({ kind: 'node', n: pl }); ok(pl.state === 'planted', 'sembrar');
  timeOffset += pl.def.growMs + 100; update(0.016); ok(pl.state === 'grown', 'crece'); p.busyUntil = 0; const mb = invCount('mango'); act({ kind: 'node', n: pl }); ok(invCount('mango') > mb, 'cosechar');
  for (const id of ['pesca_rio_1', 'pesca_estanque_1']) { const n = node(id); ok(nextTo(n.def.x, n.def.y), 'alcanzable ' + id); const f = ['trucha', 'bocachico', 'mojarra'].reduce((a, k) => a + invCount(k), 0); act({ kind: 'node', n }); ok(['trucha', 'bocachico', 'mojarra'].reduce((a, k) => a + invCount(k), 0) === f + 1 && selected() === 'red_pesca', 'pescar con red: ' + id); }
  const g = node('oro_fluvial_1'); ok(nextTo(g.def.x, g.def.y), 'alcanzable oro'); act({ kind: 'node', n: g }); ok(invCount('pepita_oro') === 1 && selected() === 'batea', 'oro fluvial con batea');
  ok(W.nodes.filter(n => n.type === 'nodo_oro_fluvial').every(n => W.waterBodies.rio_claro.tiles.some(([x, y]) => x === n.x && y === n.y)), 'todo el oro está en el río');
  for (const id of ['roca_cobre_1', 'roca_plata_1']) { const n = node(id); ok(nextTo(n.def.x, n.def.y), 'alcanzable ' + id); act({ kind: 'node', n }); ok(invCount(n.def.yield.item) >= 1 && selected() === 'pico', 'picar ' + id); }
  for (const sp of ['conejo', 'venado', 'ave']) { const a = S.animals.find(a => a.def.species === sp); ok(nextTo(a.x, a.y), 'alcanzable ' + sp); act({ kind: 'animal', a }); ok(a.state === 'hunted' && selected() === 'lanza', 'cazar ' + sp); }
  const unreach = W.nodes.filter(n => !bfs(W.spawn.x, W.spawn.y, (a, b) => cheb(a, b, n.x, n.y) === 1)); ok(!unreach.length, 'todos los nodos alcanzables' + (unreach.length ? ': ' + unreach.map(n => n.id).join(',') : ''));
  ok(['astrologia', 'combate', 'religion', 'artesania'].every(k => W.skills[k] && W.skills[k].stub) && /Astrología/.test($('#habilidades').textContent), 'habilidades educativas (stubs) en el panel');
  for (const m of W.memories) ok(!!bfs(W.spawn.x,W.spawn.y,(x,y)=>x===m.x&&y===m.y),'memoria y región alcanzable: '+m.id);
  const off=window.Casa.VALLE_OFFSET||{x:0,y:0};
  ok(W.valle && W.valle.municipios && W.valle.municipios.length===10,'diez municipios del Valle de Aburrá');
  ok(W.width===W.valle.width && W.height===W.valle.height,'tamaño del valle');
  ok(W.elevation && W.valle.relief && W.valle.relief.max>W.valle.relief.min+20,'relieve con diferencia de altura');
  const south=W.waypoints.find(w=>w.id==='caldas'), north=W.waypoints.find(w=>w.id==='barbosa'), estrella=W.waypoints.find(w=>w.id==='la_estrella');
  ok(!!south && !!north && south.y>north.y,'Caldas al sur y Barbosa al norte');
  ok(!!bfs(south.x,south.y,(x,y)=>x===north.x&&y===north.y),'a caballo se puede ir de Caldas a Barbosa');
  ok(!!bfs(estrella.x,estrella.y,(x,y)=>x===north.x&&y===north.y),'a caballo se puede ir de La Estrella a Barbosa');
  for(const id of W.valle.municipios){const park=W.waypoints.find(w=>w.id===id);ok(!!park && !!bfs(south.x,south.y,(x,y)=>x===park.x&&y===park.y),'parque en el camino: '+id);}
  ok(!walkable(214+off.x,44+off.y) && walkable(214+off.x,68+off.y) && W.tiles[W.ground[44+off.y][214+off.x]].kind==='water' && W.tiles[W.ground[68+off.y][214+off.x]].kind==='bridge','quebrada bloqueada y puente caminable');
  p.x = p.fx = W.spawn.x; p.y = p.fy = W.spawn.y;
  if (window.Simulacion) Simulacion.autotest(ok);
  const fails = out.filter(l => l.startsWith('FALLO')).length;
  const el = $('#autotest'); el.hidden = false; el.textContent = (fails ? 'AUTOTEST FALLÓ' : 'AUTOTEST OK') + ` (${out.length} comprobaciones)\n` + out.join('\n');
  document.title = fails ? 'AUTOTEST FALLÓ' : 'AUTOTEST OK';
}

S.dbg = { updateTutorial, talkCapataz, advanceDialog, act, toggleNight };
init().catch(err => { const c = $('#cargando'); if (c) c.textContent = 'Error: ' + err.message + ' — abre esta página con el servidor (ver README).'; console.error(err); });
})();
