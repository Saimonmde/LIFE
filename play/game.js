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
const CANALES = { global: 'Global', proximidad: 'Proximidad', clan: 'Clan', grupo: 'Grupo' };

// ---------------- estado ----------------
const S = window.__ELJARDIN = {
  me: { name: 'Viajero', color: 'azul', clan: '', group: '' }, houseEdit: false,
  player: { x: 0, y: 0, fx: 0, fy: 0, path: [], dir: 'down', animT: 0, busyUntil: 0, pending: null, repaths: 0 },
  nodes: new Map(), animals: [], inv: [], sel: -1, xp: {}, coins: 0, energy: 100,
  quest: { stage: 0, steps: {}, done: false, turnedIn: false },
  floaters: [], cam: { x: 0, y: 0 }, hover: null, dest: null, keys: new Set(), night: false, circadianIndex: null, nightOverride: null, mmZoom: 1,
  others: new Map(), net: { ws: null, ok: false, hasJoined: false, serverId: null, id: 0, ping: 0, lastSent: 0, sentKey: '' },
  chat: { tab: 'proximidad', lines: [], unread: {} }, dialog: null, bubbles: new Map(), lastPrompt: '',
};

function load() {
  return fetch(BASE + 'data/el-jardin.json').then(r => { if (!r.ok) throw 0; return r.json(); })
    .catch(() => { if (window.EL_JARDIN) return window.EL_JARDIN; throw new Error('No se pudo cargar el-jardin.json'); });
}
const loadImg = (src) => new Promise((ok, ko) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => ko(new Error('Imagen: ' + src)); i.src = BASE + src; });

async function init() {
  W = await load();
  if(W.homeLocation){Object.assign(Casa.PARK_DOOR,W.homeLocation.door);Object.assign(Casa.PARK_STAND,W.homeLocation.stand);}
  installHorse();
  prepareMining();
  tileset = await loadImg(W.tileset.image);
  sheets.default = await loadImg(W.player.image);
  for (const [c, p] of Object.entries(W.playerVariants || {})) sheets[c] = await loadImg(p);
  capatazImg = W.npcs && W.npcs[0] ? await loadImg(W.npcs[0].sheet) : null;
  await Promise.all(Object.entries(W.sprites).map(async ([k, s]) => { imgs[k] = await loadImg(s.image); }));
  await Promise.all(Object.values(W.items).map(async it => { imgs['icon:' + it.id] = await loadImg(it.icon['32']); }));
  for (const n of W.nodes) {
    if (n.type === 'animal') S.animals.push({ def: n, x: n.x, y: n.y, fx: n.x, fy: n.y, state: 'alive', until: 0, nextMove: now() + 1000 + Math.random() * 3000, frame: 0 });
    else S.nodes.set(n.id, { def: n, state: n.initialState, until: 0, crop: null });
  }
  S.quest.def = W.quests && W.quests[0];
  S.player.x = S.player.fx = W.spawn.x; S.player.y = S.player.fy = W.spawn.y; S.player.dir = W.spawn.facing || 'down';
  let prof = null; try { prof = JSON.parse(localStorage.getItem('lifeinc.perfil') || 'null'); } catch (e) {}
  if (prof) {
    if (prof.name) S.me.name = String(prof.name).slice(0, 16);
    S.me.clan = prof.clan || ''; S.me.group = prof.group || '';
    if (prof.color) S.me.color = prof.color;
  }
  Casa.playerName = () => S.me.name;
  Casa.enter = () => enterHouse();
  Casa.exit = () => exitHouse();
  Casa.onEdit = (on) => { S.houseEdit = on; if (on) { S.player.path = []; S.player.pending = null; S.keys.clear(); } };
  Casa.onLayout = () => { if ((W.mapId || 'city') === 'casa') applyCasaLayout(); if (window.LIVE3D && window.LIVE3D.rebuildHouse) window.LIVE3D.rebuildHouse(Casa.layout); };
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
  beginAtHome();
  if (Q.has('sinlogin') || Q.has('sinayuda')) { if (Q.get('nombre')) S.me.name = Q.get('nombre'); beginAtHome(); W.clientReady = true; startGame(); return; }
  W.clientReady = true;
  if (prof && prof.name) { $('#l-nombre').value = prof.name; if (prof.color) S.me.color = prof.color; buildColorPicker(); }
  $('#login').hidden = false; $('#l-nombre').focus();
}
function buildColorPicker() {
  const box = $('#l-colores'); box.innerHTML = '';
  const hex = { azul: '#2860d4', rojo: '#c82c2c', amarillo: '#ecb828', verde: '#2e9650', morado: '#7640b8' };
  for (const c of Object.keys(W.playerVariants || { azul: 1 })) {
    const b = document.createElement('button'); b.type = 'button'; b.style.background = hex[c] || '#888'; b.title = c;
    if (c === S.me.color) b.className = 'sel';
    b.onclick = () => { S.me.color = c; buildColorPicker(); }; box.appendChild(b);
  }
}
$('#login-form').onsubmit = (e) => {
  e.preventDefault();
  S.me.name = $('#l-nombre').value.trim().slice(0, 16) || 'Viajero';
  S.me.clan = S.me.clan || ''; S.me.group = S.me.group || '';
  localStorage.setItem('lifeinc.perfil', JSON.stringify(S.me));
  $('#login').hidden = true; startGame();
};
let started = false, reconnectTimer = null;
function startGame() {
  if (started) return; started = true;
  document.body.classList.add('in-game'); $('#b-descansar').hidden = false; $('#login-status').textContent = '';
  $('#login').hidden = true; S.keys.clear();
  $('#mi-nombre').textContent = S.me.name; drawPortrait();
  beginAtHome();
  Casa.load(S.me.name);
  if ((W.mapId || 'city') === 'casa') placeAtHouseSpawn();
  sys(`Bienvenido a Medellín, ${esc(S.me.name)}.`);
  connect(); updateTutorial(true);
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
$('#b-descansar').onclick=rest;
addEventListener('pagehide',()=>{ if(started) save(); });

const MAP_FIELDS=['width','height','ground','collision','elevation','nodes','npcs','doors','animals','regions','waypoints','roads3d','memories','riverLayouts','bridges','parkDetails','surfaceZones','signs3d','scenery3d','waterBodies','decorations','landmarks','areas','spawn'];
let cityMap=null,caveMap=null,casaMap=null,cityNodes=null,caveNodes=null,casaNodes=null,cityAnimals=null,cityReturn=null;
function installHorse(){
 const stand=W.homeLocation?.stand||Casa.PARK_STAND;
 S.horse={x:stand.x+3,y:stand.y,mounted:false,gallop:false};
 const controls=document.createElement('div');controls.id='horse-controls';
 controls.innerHTML='<button id="horse-mount" type="button">Montar caballo</button><button id="horse-gait" type="button" hidden>Paso</button>';
 document.body.append(controls);
 function sync(){const h=S.horse;$('#horse-mount').textContent=h.mounted?'Desmontar':'Montar caballo';$('#horse-gait').hidden=!h.mounted;$('#horse-gait').textContent=h.gallop?'Galope':'Paso';$('#horse-gait').setAttribute('aria-pressed',String(h.gallop));}
 $('#horse-mount').onclick=()=>{if(!started)return;const h=S.horse;if(h.mounted){h.mounted=false;h.x=S.player.x;h.y=S.player.y;sync();return;}if(W.mapId!=='city'){game('El caballo te espera afuera de la casa.');return;}if(cheb(S.player.x,S.player.y,h.x,h.y)>2){game('Acércate al caballo junto a la casa para montar.');goTo(h.x,h.y);return;}h.mounted=true;sync();game('Montaste el caballo. Usa el joystick o toca el suelo; elige paso o galope.');};
 $('#horse-gait').onclick=()=>{S.horse.gallop=!S.horse.gallop;sync();};
}
function prepareCave(){
 const palmas=W.waypoints.find(p=>p.id==='las_palmas');let entry=null;
 for(let r=2;r<10&&!entry;r++)for(let dx=-r;dx<=r&&!entry;dx++)for(let dy=-r;dy<=r&&!entry;dy++){const x=palmas.x+dx,y=palmas.y+dy;if(x>1&&y>1&&x<W.width-1&&y<W.height-1&&W.collision[y][x]===0&&W.collision[y+1][x]===0&&!W.nodes.some(n=>n.x===x&&n.y===y))entry={x,y};}
 if(!entry)throw Error('No hay acceso a la mina en Las Palmas');
 W.nodes.push({id:'entrada_mina_palmas',type:'mine_entrance',...entry,initialState:'active',states:['active'],sprites:{active:'mine_portal'},solid:true});
 W.waypoints.push({id:'cantera',name:'Mina de Las Palmas · entrada',x:entry.x,y:entry.y+1});
 W.sprites.mine_portal={...W.sprites.rock_piedra};W.sprites.mine_exit={...W.sprites.rock_piedra};
 cityMap=Object.fromEntries(MAP_FIELDS.map(k=>[k,W[k]]));
 const width=36,height=32,ground=Array.from({length:height},()=>Array(width).fill(W.ground[palmas.y][palmas.x])),collision=Array.from({length:height},(_,y)=>Array.from({length:width},(_,x)=>x<2||y<2||x>33||y>29?1:0)),elevation=Array.from({length:height},()=>Array(width).fill(0));
 const nodes=[{id:'salida_mina',type:'mine_exit',x:18,y:29,initialState:'active',states:['active'],sprites:{active:'mine_exit'},solid:true},{id:'horno_cantera',type:'furnace',x:18,y:15,solid:true,states:['active'],initialState:'active',sprites:{active:'furnace'}}];
 const layout={cobre:[[6,6],[9,4],[5,12],[8,22],[12,8]],plata:[[27,5],[30,10],[28,22],[24,9]],oro:[[5,3],[17,3],[28,3],[32,17],[3,18],[24,27]]};
 for(const [metal,coords] of Object.entries(layout))coords.forEach(([x,y],i)=>nodes.push({id:'mina_'+metal+'_'+i,type:'mineral_rock',mineral:metal,x,y,skill:'mining',method:'terrestre',tool:'pico',solid:true,states:['active','depleted'],initialState:'active',sprites:{active:'rock_'+metal,depleted:'rock_depleted'},yield:{item:'mineral_'+metal,min:2,max:metal==='oro'?3:4},xp:metal==='oro'?26:metal==='plata'?18:12,respawnMs:metal==='oro'?32000:18000}));
 const rocks=[[10,13],[26,15],[12,21],[22,23],[8,17],[28,26],[16,7]];for(const [x,y] of rocks){collision[y][x]=1;}
 for(const n of nodes)collision[n.y][n.x]=1;
 caveMap={width,height,ground,collision,elevation,nodes,npcs:[],doors:[],animals:[],regions:[{id:'mina_palmas',name:'Mina de Las Palmas · interior',x:0,y:0,w:width,h:height}],waypoints:[{id:'horno',name:'Horno central',x:18,y:17},{id:'salida',name:'Salida a Las Palmas',x:18,y:28}],roads3d:[],memories:[],riverLayouts:[],bridges:[],parkDetails:[],surfaceZones:[],signs3d:[],scenery3d:[],waterBodies:{},decorations:[],landmarks:[],areas:[],spawn:{x:18,y:27},rocks};
 W.caveDefinition=caveMap;W.cityDefinition=cityMap;W.mineEntrance=entry;
 const home=window.Casa.PARK_DOOR;
 W.collision[home.y][home.x]=1;
 W.nodes.push({id:'puerta_casa',type:'home_door',x:home.x,y:home.y,initialState:'active',states:['active'],sprites:{active:'home_door'},solid:true});
 W.sprites.home_door={...W.sprites.rock_piedra};
 W.signs3d=W.signs3d||[];
 W.signs3d.push({text:'TU CASA · PARQUE DE ENVIGADO',x:home.x+2,y:home.y-1});
 W.homeDoor={x:home.x,y:home.y,standX:window.Casa.PARK_STAND.x,standY:window.Casa.PARK_STAND.y};
}
function applyCasaLayout(){
 if((W.mapId||'city')!=='casa')return;
 const map=Casa.buildMap(Casa.layout);
 W.collision=map.collision; W.ground=map.ground; casaMap=map;
 const p=S.player;
 if(!walkable(p.x,p.y)){p.x=p.fx=Casa.SPAWN.x;p.y=p.fy=Casa.SPAWN.y;p.path=[];}
 drawMinimapBase();
}
function enterHouse(){
 if((W.mapId||'city')==='mine'){game('Sal de la mina antes de volver a casa.','aviso');return;}
 if((W.mapId||'city')==='casa'){game('Ya estás en tu casa.');return;}
 Casa.load(S.me.name);
 S.portalUntil=now()+800;
 switchMap('casa');
}
function exitHouse(){
 if((W.mapId||'city')!=='casa')return;
 S.portalUntil=now()+900;
 if(window.LIVE3D)window.LIVE3D.lookAt={x:239,y:229};
 switchMap('city');
}
function switchMap(id,restored=false){
 if(!cityMap)return;
 if(S.horse?.mounted&&id!=='city'){S.horse.mounted=false;S.horse.x=S.player.x;S.horse.y=S.player.y;$('#horse-mount').textContent='Montar caballo';$('#horse-gait').hidden=true;}
 const prev=W.mapId||'city';
 if(id===prev)return;
 if(prev==='mine')caveNodes=S.nodes;
 if(prev==='casa')casaNodes=S.nodes;
 if(prev==='city'){cityNodes=S.nodes;cityAnimals=S.animals;if(!restored)cityReturn={x:S.player.x,y:S.player.y};}
 if(id==='mine'){Object.assign(W,caveMap);W.mapId='mine';if(!caveNodes)caveNodes=new Map(W.nodes.map(n=>[n.id,{def:n,state:n.initialState,until:0,crop:null}]));S.nodes=caveNodes;S.animals=[];}
 else if(id==='casa'){casaMap=Casa.buildMap(Casa.layout);Object.assign(W,casaMap);W.mapId='casa';casaNodes=new Map(W.nodes.map(n=>[n.id,{def:n,state:n.initialState,until:0,crop:null}]));S.nodes=casaNodes;S.animals=[];}
 else {Object.assign(W,cityMap);W.mapId='city';S.nodes=cityNodes;S.animals=cityAnimals;id='city';}
 const p=S.player;
 let xy;
 if(id==='mine')xy=caveMap.spawn;
 else if(id==='casa')xy={x:Casa.SPAWN.x,y:Casa.SPAWN.y};
 else if(prev==='mine')xy=cityReturn||{x:W.mineEntrance.x,y:W.mineEntrance.y+1};
 else if(prev==='casa')xy={x:Casa.PARK_STAND.x,y:Casa.PARK_STAND.y};
 else xy={x:p.x,y:p.y};
 p.x=p.fx=xy.x;p.y=p.fy=xy.y;if(id==='casa')p.dir=Casa.SPAWN.dir;
 p.path=[];p.pending=null;p.busyUntil=0;S.dest=null;S.keys.clear();S.sel=-1;
 for(const key of ['furnace-panel','world-routes','memories','city-map','aviso','objetivo']){const el=document.getElementById(key);if(el)el.hidden=true;}
 closeForgeChat();pendingFurnaceDrop=null;if(oreDrag||touchOre)endOreDrag();
 S.hover=null;S.floaters=[];S.bubbles.clear();
 document.body.classList.toggle('in-mine',id==='mine');
 document.body.classList.toggle('in-casa',id==='casa');
 document.body.dataset.zone=id;
 if(id!=='casa'&&window.Casa)Casa.setEditing(false);
 const zoneLabel=id==='casa'?'Tu casa · Medellín':id==='mine'?'Mina de Las Palmas · interior':null;
 if(zoneLabel){$('#zona-nombre').textContent=zoneLabel;}
 drawMinimapBase();
 if(!restored){
  save();
  if(id==='mine')game('Entras a la mina de Las Palmas. Toca una veta para usar tu pica; el horno está en el centro.');
  else if(id==='city'&&prev==='mine')game('Sales de la mina y vuelves a Las Palmas.');
  else if(id==='casa')game('Entras a tu casa en Medellín. La puerta sale al Parque de Envigado.');
  else if(id==='city'&&prev==='casa')game('Sales al <b>Parque de Envigado</b>. El botón Casa te devuelve a tu casa.');
 }
 if(S.net.ok)sendMove(true);
}

// ---------------- cantera y fundición ----------------
function prepareMining(){
 W.items.pico.name='Pica de minería';NOMBRES.oro='Roca de oro';
 for(const metal of ['cobre','plata','oro']){
  const raw='mineral_'+metal,ingot='lingote_'+metal;
  if(!W.items[raw])W.items[raw]={...W.items.mineral_cobre,id:raw,name:'Mineral de oro sin refinar'};
  W.items[raw].name='Mineral de '+metal+' sin refinar';
  W.items[raw].icon={'16':'graphics/mining/'+raw+'.svg','32':'graphics/mining/'+raw+'.svg','64':'graphics/mining/'+raw+'.svg'};
  W.items[ingot]={id:ingot,name:'Lingote de '+metal,category:'ingot',stackable:true,maxStack:999,icon:{'16':'graphics/mining/'+ingot+'.svg','32':'graphics/mining/'+ingot+'.svg','64':'graphics/mining/'+ingot+'.svg'}};
 }
 W.skills.mining.learn='Usa la pica sobre vetas de cobre, plata y oro. Cada extracción da experiencia y los minerales se apilan en la mochila.';
 W.skills.mining.methods.terrestre.minerals=['piedra','cobre','plata','oro'];
 W.skills.smelting={name:'Fundición',verb:'Fundir minerales',learn:'Transforma mineral sin refinar en lingotes o acuña monedas en el horno de la cantera.'};
 if(W.skills.order&&!W.skills.order.includes('smelting'))W.skills.order.push('smelting');
 W.sprites.rock_oro={...W.sprites.rock_cobre};W.sprites.furnace={...W.sprites.rock_piedra};
 const taken=new Set([...W.nodes,...W.npcs,...W.doors].map(n=>`${n.x},${n.y}`));
 function spot(cx,cy){for(let r=0;r<16;r++)for(let dy=-r;dy<=r;dy++)for(let dx=-r;dx<=r;dx++){if(Math.max(Math.abs(dx),Math.abs(dy))!==r)continue;const x=cx+dx,y=cy+dy;if(x<1||y<1||x>=W.width-1||y>=W.height-1||W.collision[y][x]!==0||taken.has(`${x},${y}`))continue;if(![[1,0],[-1,0],[0,1],[0,-1]].some(([a,b])=>W.collision[y+b][x+a]===0))continue;taken.add(`${x},${y}`);return {x,y};}throw Error('No se encontró espacio para la cantera');}
 prepareCave();
}
let furnaceNode=null;
function setupMiningUI(){
 const panel=document.createElement('section');panel.id='furnace-panel';panel.className='ventana';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Horno de fundición');panel.innerHTML='<header>Horno de la cantera <button id="furnace-close" aria-label="Cerrar horno">×</button></header><div class="forge-content"><p>Selecciona mineral en tu mochila y toca el horno. Cada lote produce un lingote o su valor en monedas.</p><label>Mineral<select id="forge-ore"></select></label><div id="forge-stock"></div><label>Lotes <input id="forge-batches" type="number" min="1" step="1" value="1"></label><div class="forge-presets"><button id="forge-one">1 lote</button><button id="forge-all">Máximo</button></div><p id="forge-preview" aria-live="polite"></p><div class="forge-actions"><button id="forge-ingot">Crear lingotes</button><button id="forge-coins">Acuñar monedas</button></div><p id="forge-result" role="status"></p></div>';document.body.append(panel);
 for(const [id,r] of Object.entries(MiningRules.recipes)){const o=document.createElement('option');o.value=id;o.textContent=W.items[id].name;$('#forge-ore').append(o);}
 $('#furnace-close').onclick=()=>panel.hidden=true;
 $('#forge-ore').onchange=$('#forge-batches').oninput=renderForge;
 $('#forge-one').onclick=()=>{$('#forge-batches').value=1;renderForge();};$('#forge-all').onclick=()=>{const id=$('#forge-ore').value;$('#forge-batches').value=Math.max(1,Math.floor(invCount(id)/MiningRules.recipes[id].ore));renderForge();};
 $('#forge-ingot').onclick=()=>smelt('ingot');$('#forge-coins').onclick=()=>smelt('coins');
 const intro=document.createElement('p');intro.className='bag-note';intro.textContent='60 casillas · pilas de 999 · arrastra mineral al horno';$('#inventario').before(intro);
 const modes=document.createElement('div');modes.id='bag-modes';modes.innerHTML='<button id="bag-summary" type="button">Resumen 4×6</button><button id="bag-full" type="button">Completo</button>';$('#w-inv header').append(modes);$('#bag-summary').onclick=()=>setBagMode('summary');$('#bag-full').onclick=()=>setBagMode('full');
 const pages=document.createElement('nav');pages.id='bag-pages';pages.setAttribute('aria-label','Páginas del inventario resumido');pages.innerHTML='<button type="button" id="bag-prev" aria-label="Página anterior del inventario">‹</button><span id="bag-page-label"></span><button type="button" id="bag-next" aria-label="Página siguiente del inventario">›</button>';$('#inventario').after(pages);$('#bag-prev').onclick=()=>{bagPage=Math.max(0,bagPage-1);renderInv();};$('#bag-next').onclick=()=>{bagPage=Math.min(Math.ceil(SLOTS/24)-1,bagPage+1);renderInv();};
 setupBagForge();updateBagMode();renderInv();
 const guide=document.createElement('button');guide.id='mine-route';guide.textContent='⛏ Cantera y horno';guide.className='hud';guide.onclick=()=>{if(W.mapId==='casa'){game('Sal de tu casa para ir a la mina.','aviso');return;}if(started&&W.mapId!=='mine'){const e=S.nodes.get('entrada_mina_palmas');if(e)return approach({kind:'node',n:e});}const d=W.waypoints.find(w=>w.id===(W.mapId==='mine'?'horno':'cantera'));if(started&&d)goTo(d.x,d.y);};document.body.append(guide);
 const enter=document.createElement('button');enter.id='mine-enter';enter.className='hud';enter.type='button';enter.hidden=true;enter.textContent='⛏ Entrar a la mina';enter.onclick=()=>{const e=S.nodes.get('entrada_mina_palmas');if(started&&W.mapId!=='mine'&&e)approach({kind:'node',n:e});};document.body.append(enter);
 const exit=document.createElement('button');exit.id='mine-exit-route';exit.className='hud';exit.textContent='↗ Salir a Las Palmas';exit.onclick=()=>{if(started&&W.mapId==='mine')approach({kind:'node',n:S.nodes.get('salida_mina')});};document.body.append(exit);
}
function openFurnace(n){furnaceNode=n;if(pendingFurnaceDrop?.nodeId===n.def.id){const item=pendingFurnaceDrop.item;pendingFurnaceDrop=null;openForgeChat(item);return;}closeForgeChat();const id=selected();if(MiningRules.recipes[id])$('#forge-ore').value=id;$('#forge-result').textContent='';$('#furnace-panel').hidden=false;renderForge();}
function renderForge(){if(!$('#forge-ore'))return;const id=$('#forge-ore').value,r=MiningRules.recipes[id],q=Number($('#forge-batches').value),max=Math.floor(invCount(id)/r.ore),valid=Number.isSafeInteger(q)&&q>0&&q<=max;
 $('#forge-stock').textContent=`En mochila: ${invCount(id)} · ${r.ore} minerales por lote · disponibles: ${max} lotes`;
 $('#forge-batches').max=Math.max(1,max);$('#forge-preview').textContent=valid?`${q*r.ore} minerales → ${q} lingote${q===1?'':'s'} de ${r.metal} O ${q*r.coins} monedas. El sobrante queda en la mochila.`:`Reúne al menos ${r.ore} minerales y elige una cantidad disponible.`;
 $('#forge-ingot').disabled=$('#forge-coins').disabled=!valid;
}
async function smelt(mode){if(!started||!furnaceNode)return;const d=furnaceNode.def;if(cheb(S.player.x,S.player.y,d.x,d.y)>1){$('#forge-result').textContent='Acércate al horno para fundir.';return;}
 const id=$('#forge-ore').value,q=Number($('#forge-batches').value),result=MiningRules.smelt(S.inv,W.items,id,q,mode,SLOTS);if(result.error){$('#forge-result').textContent=result.error;return;}
 if(S.forgePending)return;S.forgePending=true;
 try{await economyAction({action:'forge',item:id,batches:q,mode});}catch(error){$('#forge-result').textContent=error.message;return;}finally{S.forgePending=false;}
 const previous={inv:S.inv,coins:S.coins,xp:{...S.xp},sel:S.sel};S.inv=result.inv;S.xp.smelting=(S.xp.smelting||0)+result.xp;S.sel=-1;
 if(!save()){$('#forge-result').textContent='El servidor confirmó la operación, pero no se pudo guardar el inventario local. Conserva esta sesión abierta.';return;}
 S.forgeUntil=now()+1500;renderAll();renderForge();const message=$('#forge-result').textContent=mode==='coins'?`Acuñaste ${result.coins} monedas. +${result.xp} XP de Fundición.`:`Creaste ${q} lingote${q===1?'':'s'} de ${MiningRules.recipes[id].metal}. +${result.xp} XP de Fundición.`;return message;
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
function beginOreDrag(item,x,y){if(!started||!MiningRules.recipes[item]||!invCount(item))return false;oreDrag={item};window.LiveInk.draggedMineral=item;document.body.classList.add('dragging-ore');const ghost=$('#ore-drag-ghost');ghost.textContent=W.items[item].name+' · suelta sobre el horno';ghost.hidden=false;moveOreDrag(x,y);return true;}
function moveOreDrag(x,y){if(!oreDrag)return;const ghost=$('#ore-drag-ghost');ghost.style.left=Math.max(8,Math.min(innerWidth-220,x+14))+'px';ghost.style.top=Math.max(8,y-42)+'px';const id=window.LiveInk.furnaceAtScreen?.(x,y);window.LiveInk.oreDropHovered=!!id;ghost.classList.toggle('valid-drop',!!id);}
function endOreDrag(){oreDrag=null;touchOre=null;window.LiveInk.draggedMineral=null;window.LiveInk.oreDropHovered=false;document.body.classList.remove('dragging-ore');const ghost=document.getElementById('ore-drag-ghost');if(ghost)ghost.hidden=true;suppressOreClickUntil=now()+350;}
function dropOre(x,y){if(!oreDrag)return false;const item=oreDrag.item,id=window.LiveInk.furnaceAtScreen?.(x,y);endOreDrag();if(!id)return false;return requestFurnaceDrop(item,id);}
function requestFurnaceDrop(item,nodeId){const n=S.nodes.get(nodeId);if(!started||n?.def.type!=='furnace'||!MiningRules.recipes[item]||!invCount(item))return false;pendingFurnaceDrop={item,nodeId};selectItem(item);approach({kind:'node',n});return true;}
function wireMineralDrag(slot,item){if(!MiningRules.recipes[item])return;slot.draggable=true;slot.classList.add('draggable-ore');slot.setAttribute('aria-description','Arrastra este mineral al horno para elegir lingotes o monedas.');
 slot.ondragstart=e=>{if(!beginOreDrag(item,e.clientX,e.clientY)){e.preventDefault();return;}e.dataTransfer.effectAllowed='copy';e.dataTransfer.setData('application/x-lifeinc-ore',item);e.dataTransfer.setData('text/plain',item);};slot.ondragend=endOreDrag;
 slot.onpointerdown=e=>{if(e.pointerType==='mouse'||!started)return;touchOre={item,id:e.pointerId,x:e.clientX,y:e.clientY,slot};slot.setPointerCapture(e.pointerId);};
 slot.onpointermove=e=>{if(!touchOre||touchOre.id!==e.pointerId)return;if(!oreDrag&&Math.hypot(e.clientX-touchOre.x,e.clientY-touchOre.y)>8)beginOreDrag(item,e.clientX,e.clientY);if(oreDrag){e.preventDefault();moveOreDrag(e.clientX,e.clientY);}};
 slot.onpointerup=e=>{if(!touchOre||touchOre.id!==e.pointerId)return;if(oreDrag){e.preventDefault();dropOre(e.clientX,e.clientY);}else touchOre=null;};slot.onpointercancel=()=>{if(touchOre)endOreDrag();};slot.onlostpointercapture=()=>{if(touchOre)endOreDrag();};
}
function setupBagForge(){
 const ghost=document.createElement('div');ghost.id='ore-drag-ghost';ghost.hidden=true;document.body.append(ghost);
 document.addEventListener('dragover',e=>{if(!oreDrag)return;e.preventDefault();e.dataTransfer.dropEffect=window.LiveInk.furnaceAtScreen?.(e.clientX,e.clientY)?'copy':'none';moveOreDrag(e.clientX,e.clientY);});
 document.addEventListener('drop',e=>{if(!oreDrag)return;e.preventDefault();dropOre(e.clientX,e.clientY);});addEventListener('blur',()=>{if(oreDrag||touchOre)endOreDrag();});
 const card=document.createElement('section');card.id='forge-chat-card';card.hidden=true;card.setAttribute('aria-label','Elegir fundición en el chat');card.innerHTML='<header><b id="forge-chat-title">Horno</b><button type="button" id="forge-chat-cancel" aria-label="Cancelar fundición en chat">×</button></header><p>¿Quieres hacer lingotes o monedas?</p><div id="forge-chat-stock"></div><label>Lotes <input id="forge-chat-batches" type="number" min="1" step="1" value="1"></label><button type="button" id="forge-chat-max">Máximo</button><p id="forge-chat-preview"></p><div class="forge-chat-actions"><button type="button" id="forge-chat-ingot">Hacer lingotes</button><button type="button" id="forge-chat-coins">Hacer monedas</button></div><p id="forge-chat-result" role="status"></p>';
 $('#chat-form').before(card);$('#forge-chat-cancel').onclick=closeForgeChat;$('#forge-chat-batches').oninput=renderForgeChat;
 $('#forge-chat-max').onclick=()=>{if(!chatForgeItem)return;$('#forge-chat-batches').value=Math.max(1,Math.floor(invCount(chatForgeItem)/MiningRules.recipes[chatForgeItem].ore));renderForgeChat();};
 for(const [id,mode] of [['forge-chat-ingot','ingot'],['forge-chat-coins','coins']])$('#'+id).onclick=async()=>{if(!chatForgeItem)return;$('#forge-ore').value=chatForgeItem;$('#forge-batches').value=$('#forge-chat-batches').value;const message=await smelt(mode);$('#forge-chat-result').textContent=message||$('#forge-result').textContent;renderForgeChat();if(message)game(esc(message));};
}
function closeForgeChat(){chatForgeItem=null;const card=document.getElementById('forge-chat-card');if(card)card.hidden=true;$('#hud-chat').classList.remove('forge-chat-open');}
function openForgeChat(item){chatForgeItem=item;$('#furnace-panel').hidden=true;$('#forge-chat-card').hidden=false;$('#hud-chat').classList.add('forge-chat-open');$('#forge-chat-batches').value=1;$('#forge-chat-result').textContent='';renderForgeChat();game(`Horno: trajiste <b>${esc(W.items[item].name)}</b>. ¿Quieres hacer lingotes o monedas?`);window.ChatUI?.setOpen(true);}
function renderForgeChat(){if(!chatForgeItem)return;const r=MiningRules.recipes[chatForgeItem],have=invCount(chatForgeItem),q=Number($('#forge-chat-batches').value),max=Math.floor(have/r.ore),valid=Number.isSafeInteger(q)&&q>0&&q<=max;
 $('#forge-chat-title').textContent='Horno · '+r.name;$('#forge-chat-stock').textContent=`Tienes ${have} minerales · ${r.ore} por lote`;
 $('#forge-chat-batches').max=Math.max(1,max);$('#forge-chat-preview').textContent=valid?`${q*r.ore} minerales → ${q} lingote${q===1?'':'s'} o ${q*r.coins} monedas. Conservas ${have-q*r.ore} minerales.`:`Necesitas al menos ${r.ore} minerales para un lote.`;
 $('#forge-chat-ingot').disabled=$('#forge-chat-coins').disabled=!valid;
}

// ---------------- inventario / xp / monedas ----------------
const SLOTS = 60;
function invCount(id) { return S.inv.filter(s => s && s.item === id).reduce((a, s) => a + s.qty, 0); }
function invAdd(id,qty){const next=MiningRules.add(S.inv,W.items,id,qty,SLOTS);if(!next){game('Tu mochila está llena. Libera una casilla.','aviso');return false;}S.inv=next;save();renderInv();return true;}
function invRemove(id,qty){const next=MiningRules.remove(S.inv,id,qty);if(!next)return false;S.inv=next;if(!S.inv[S.sel])S.sel=-1;save();renderInv();return true;}
const selected = () => S.sel >= 0 && S.inv[S.sel] ? S.inv[S.sel].item : null;
function selectItem(id) { const i = S.inv.findIndex(s => s && s.item === id); if (i >= 0) { S.sel = i; renderInv(); } return i >= 0; }
const level = (xp) => Math.floor(Math.sqrt(xp / 25)) + 1;
const skillIds = () => (W.skills.order || Object.keys(W.skills).filter(k => W.skills[k] && W.skills[k].name));
function addXp(skill, n) {
  if (!W.skills[skill]) return;
  const before = level(S.xp[skill] || 0); S.xp[skill] = (S.xp[skill] || 0) + n; save(); renderSkills(); renderProfile();
  if (level(S.xp[skill]) > before) game(`¡Subiste a nivel ${level(S.xp[skill])} de ${W.skills[skill].name}!`, 'oro');
}
function totalLevel() { return skillIds().filter(k => !W.skills[k].stub).reduce((a, k) => a + level(S.xp[k] || 0), 0) - (skillIds().filter(k => !W.skills[k].stub).length - 1); }
function save() { try { localStorage.setItem('lifeinc.eljardin.v3', JSON.stringify({ inv: S.inv, xp: S.xp, coins: S.coins, legacyCoins:S.legacyCoins||0, energy: S.energy, mapId:W.mapId||'city', cityReturn, resourceState:Object.fromEntries([...(caveNodes||[])].filter(([,n])=>n.state==='depleted').map(([id,n])=>[id,Date.now()+Math.max(0,n.until-now())])), mapRevision: W.expansion?.revision || 0, position: {x:S.player.x,y:S.player.y,dir:S.player.dir}, quest: { stage: S.quest.stage, steps: S.quest.steps, done: S.quest.done, turnedIn: S.quest.turnedIn } })); return true; } catch (e) { return false; } }
function restore() {
  let d = null; try { d = JSON.parse(localStorage.getItem('lifeinc.eljardin.v3')); } catch (e) {}
  if (d && Array.isArray(d.inv) && d.inv.every(s => !s || W.items[s.item])) { S.inv = d.inv; S.xp = d.xp || {}; S.legacyCoins=d.legacyCoins||d.coins||0;S.coins=0; Object.assign(S.quest, d.quest || {});
    if (Number.isFinite(d.energy)) S.energy = Math.max(0, Math.min(100, d.energy));
    if(d.cityReturn)cityReturn=d.cityReturn;
    // Inventory, skills and quests carry over. The saved map and coordinates never decide where a session starts.
    if(d.resourceState){if(!caveNodes)caveNodes=new Map(caveMap.nodes.map(n=>[n.id,{def:n,state:n.initialState,until:0,crop:null}]));for(const [id,until] of Object.entries(d.resourceState)){const n=caveNodes.get(id);if(n&&until>Date.now()){n.state='depleted';n.until=now()+until-Date.now();}}}
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
  S.inv = []; S.xp = {}; S.coins = W.startingCoins || 0; S.quest.stage = 0; S.quest.steps = {}; S.quest.done = false; S.quest.turnedIn = false;
  for (const s of W.starterInventory) invAdd(s.item, s.qty);
}
function renderAll() { renderInv(); renderSkills(); renderProfile(); renderQuest(); }
function renderInv() {
  const el = $('#inventario'); el.innerHTML = '';
  const first=bagMode==='summary'?bagPage*BAG_PAGE_SIZE:0,limit=bagMode==='summary'?first+BAG_PAGE_SIZE:SLOTS;
  for (let i = first; i < limit; i++) {
    const s = i<SLOTS?S.inv[i]:null; const d = document.createElement('div');
    if(s)d.setAttribute('role','button'); d.tabIndex=s?0:-1;
    d.className = 'slot' + (s ? '' : ' vacio') + (i === S.sel ? ' sel' : '');
    if (s) { const it = W.items[s.item]; d.title = it.name; d.setAttribute('aria-label',it.name+' × '+s.qty); d.innerHTML = `<img src="${BASE + it.icon['32']}" alt="">` + (it.stackable ? `<span class="n">${s.qty}</span>` : ''); d.innerHTML += `<small class="item-name">${esc(it.name)}</small>`;wireMineralDrag(d,s.item);d.onclick = () => { if(now()<suppressOreClickUntil)return;S.sel = S.sel === i ? -1 : i;if(MiningRules.recipes[selected()]&&$('#forge-ore')){$('#forge-ore').value=selected();renderForge();}renderInv(); };d.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();d.click();}}; }
    el.appendChild(d);
  }
  updateBagMode();
  const sel = selected(); $('#seleccion').innerHTML = 'Seleccionado: ' + (sel ? `<b>${W.items[sel].name}</b>` : '—');
  const hb = $('#hotbar'); hb.innerHTML = '';
  for (let i = 0; i < 10; i++) {
    const s = S.inv[i]; const d = document.createElement('div'); d.className = 'hs' + (i === S.sel ? ' sel' : '');
    d.innerHTML = `<span class="k">${(i + 1) % 10}</span>` + (s ? `<img src="${BASE + W.items[s.item].icon['32']}" alt=""><span class="n">${W.items[s.item].stackable ? s.qty : ''}</span>` : '');
    if (s) d.title = W.items[s.item].name;
    d.onclick = () => { if (S.inv[i]) { S.sel = S.sel === i ? -1 : i; renderInv(); } };
    hb.appendChild(d);
  }
  $('#bolsa').textContent = `${S.inv.filter(Boolean).length}/${SLOTS}`; $('#monedas').textContent = S.coins.toLocaleString('es-CO');
}
function renderSkills() {
  const el = $('#habilidades'); el.innerHTML = '';
  for (const k of skillIds()) {
    const sk = W.skills[k]; if (!sk || !sk.name) continue;
    const xp = S.xp[k] || 0, lv = level(xp), lo = 25 * (lv - 1) ** 2, hi = 25 * lv ** 2;
    el.insertAdjacentHTML('beforeend', `<li title="${esc(sk.learn || '')}"><span>${sk.name}${sk.stub ? ' <small style="color:#a59a82">(próximamente)</small>' : ''}</span><span>Nv ${lv} · ${xp} xp</span></li><div class="b"><i style="width:${Math.round(100 * (xp - lo) / (hi - lo))}%"></i></div>`);
  }
}
function renderProfile() {
  $('#mi-nivel').textContent = `Nv. ${totalLevel()}`;
  $('#bar-energia').style.width = S.energy + '%'; $('#txt-energia').textContent = `${Math.round(S.energy)} / 100`;
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
        game(`Primeros Pasos: <b>${esc(st.text)}</b> ✔`, 'oro');
        for (const g of (st.onComplete && st.onComplete.giveItems) || []) if (!invCount(g.item)) { invAdd(g.item, g.qty); game(`Recibes: <b>${W.items[g.item].name}</b>.`, 'juego'); }
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
      const r = S.quest.def.reward; S.quest.turnedIn = true; S.legacyCoins=(S.legacyCoins||0)+(r.coins||0);
      for (const [k, v] of Object.entries(r.xp || {})) addXp(k, v);
      game(`¡Primeros Pasos completado! +${r.coins} puntos de misión (fuera de la moneda del servidor).`, 'oro'); save(); renderAll(); updateTutorial();
    };
  } else if (S.quest.turnedIn) lines = d.after; else lines = d.inProgress;
  S.dialog = { lines, i: 0, after }; $('#aviso').hidden = true; showDialog();
}
function showDialog() { const D = S.dialog; $('#dialogo').hidden = false; $('#dialogo-txt').textContent = D.lines[D.i]; $('.quien').textContent = W.npcs[0].name; }
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
    global: '(Global) Visible para todos los jugadores conectados',
    proximidad: `(Proximidad) Solo visible para jugadores cercanos (≤ 30 m) · ${inRange} en rango`,
    clan: S.me.clan ? `(Clan) Visible para tu clan: ${esc(S.me.clan)}` : '(Clan) Sin clan · escribe /clan nombre',
    grupo: S.me.group ? `(Grupo) Visible para tu grupo: ${esc(S.me.group)}` : '(Grupo) No estás en un grupo · escribe /grupo nombre',
  };
  $('#chat-nota').innerHTML = (S.net.ok ? '' : '⚠ Sin servidor de chat (ejecuta python3 server.py) · ') + notas[S.chat.tab];
}
function renderTabs() { document.querySelectorAll('.pestanas button[data-canal]').forEach(b => { const c = b.dataset.canal; b.classList.toggle('activa', c === S.chat.tab); b.innerHTML = CANALES[c] + (S.chat.unread[c] ? '<span class="nuevo"></span>' : ''); }); }
document.querySelectorAll('.pestanas button[data-canal]').forEach(b => b.onclick = () => { S.chat.tab = b.dataset.canal; S.chat.unread[S.chat.tab] = false; renderTabs(); renderChat(); });
$('#chat-min').onclick = () => window.ChatUI.setOpen(false);
$('#chat-form').onsubmit = (e) => {
  e.preventDefault(); const inp = $('#chat-input'); const text = inp.value.trim(); inp.value = ''; inp.blur(); if (!text) return;
  if (S.net.ok) S.net.ws.send(JSON.stringify({ t: 'chat', channel: S.chat.tab, text }));
  else { addLine(S.chat.tab, chatLine({ channel: S.chat.tab, from: S.me.name, text, ts: hhmm() }, true)); bubble(0, text); }
};
const hhmm = () => new Date().toTimeString().slice(0, 5);
const NAME_COL = ['#7fd0ff', '#ff9ad5', '#ffd27a', '#9df59a', '#c9a6ff', '#ffb070'];
function chatLine(m, mine) {
  const col = mine ? '#9df59a' : NAME_COL[(m.fromId || 0) % NAME_COL.length];
  return `<span class="t">[${esc(m.ts)}]</span> <span class="n" style="color:${col}">${esc(m.from)}:</span> ${esc(m.text)}`;
}
function bubble(id, text) { S.bubbles.set(id, { text: text.length > 60 ? text.slice(0, 58) + '…' : text, until: now() + 6000 }); }

// ---------------- red (WebSocket) ----------------
const economyPending=new Map();
function economyAction(action){
 if(!S.net.ok)return Promise.reject(new Error('Conéctate al servidor para registrar minería y fundición.'));
 sendMove(true);const request=crypto.randomUUID();
 return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{economyPending.delete(request);reject(new Error('No se confirmó la operación. Revisa el libro mayor antes de repetir.'));},15000);economyPending.set(request,{resolve,reject,timer});S.net.ws.send(JSON.stringify({t:'economy',request,...action}));});
}
function receiveEconomy(m){
 if(m.token)localStorage.setItem('saimon.wallet.token',m.token);
 if(m.wallet){S.wallet=m.wallet;S.coins=m.wallet.balance;renderAll();renderLedger();}
 const pending=economyPending.get(m.request);if(pending){clearTimeout(pending.timer);economyPending.delete(m.request);if(m.error)pending.reject(new Error(m.error));else pending.resolve(m.result);}
}
function renderLedger(){
 if(!document.getElementById('ledger-panel')){const panel=document.createElement('section');panel.id='ledger-panel';panel.className='ventana';panel.hidden=true;panel.innerHTML='<header>Libro mayor <button id="ledger-close" type="button">×</button></header><div id="ledger-content"></div>';document.body.append(panel);$('#ledger-close').onclick=()=>panel.hidden=true;const b=document.createElement('button');b.id='ledger-open';b.type='button';b.textContent='Libro mayor';document.getElementById('horse-controls').append(b);b.onclick=()=>panel.hidden=!panel.hidden;}
 const w=S.wallet;if(!w)return;
 const box=$('#ledger-content');box.replaceChildren();const text=document.createElement('p');text.textContent=`Economía de prueba · Emisión fija: ${w.supply.toLocaleString('es-CO')}. Tesorería: ${w.treasury.toLocaleString('es-CO')}. En circulación: ${w.circulating.toLocaleString('es-CO')}. Tu saldo: ${w.balance.toLocaleString('es-CO')}.`;box.append(text);const help=document.createElement('p');help.textContent='La fundición transfiere monedas de la tesorería. Tus monedas antiguas de demostración no se convierten automáticamente. Libro del servidor, sin blockchain.';box.append(help);for(const tx of w.journal){const row=document.createElement('p');row.textContent=`${new Date(tx.at*1000).toLocaleString('es-CO')} · +${tx.amount} · ${tx.reason}`;box.append(row);}
}
function connect() {
  if (!started) return;
  clearTimeout(reconnectTimer);
  if (!/^https?:/.test(location.protocol)) { renderChat(); return; }
  let ws; try { ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws'); } catch (e) { return; }
  S.net.ws = ws;
  addEventListener('pagehide', () => { try { ws.close(); } catch (e) {} }, { once: true });
  ws.onopen = () => { if(!started || S.net.ws!==ws) {ws.close();return;} if(!S.net.hasJoined) beginAtHome(); const atHome = W.mapId==='casa'; ws.send(JSON.stringify({ t: 'hello', walletToken: localStorage.getItem('saimon.wallet.token'), name: S.me.name, color: S.me.color, clan: S.me.clan || '', group: S.me.group || '', level: totalLevel(), zone: atHome ? 'casa' : 'city', resume: atHome ? null : (S.net.hasJoined ? (W.mapId==='mine'?cityReturn:{x:S.player.fx,y:S.player.fy}) : null) })); };
  ws.onmessage = (ev) => {
    if (!started || S.net.ws!==ws) return;
    const m = JSON.parse(ev.data);
    if(m.t==='economy'){receiveEconomy(m);return;}
    if (m.t === 'welcome') {
      S.net.ok = true; S.net.id = m.id; S.me.name = m.you.name; $('#mi-nombre').textContent = S.me.name;
      S.net.serverId = m.serverId || null;
      if (!S.net.hasJoined && W.mapId==='casa') placeAtHouseSpawn();
      S.net.hasJoined=true; S.others.clear();
      for (const p of m.players) addOther(p);
      renderNearby();
      $('#ping').classList.add('ok'); sys('Conectado al mundo compartido de LifeIn.'); renderChat(); sendMove(true);
    } else if (m.t === 'join') addOther(m.player);
    else if (m.t === 'player') { const o = S.others.get(m.player.id); if (o) Object.assign(o, { name: m.player.name, clan: m.player.clan, group: m.player.group }); if (m.player.id === S.net.id) { S.me.clan = m.player.clan; S.me.group = m.player.group; renderChat(); } }
    else if (m.t === 'leave') { S.others.delete(m.id); renderNearby(); }
    else if (m.t === 'move') { const o = S.others.get(m.id); if (o) { o.x = m.x; o.y = m.y; o.dir = m.dir; o.moving = m.moving; o.level = m.level; o.lastMove = now(); } }
    else if (m.t === 'chat') {
      const mine = m.fromId === S.net.id;
      addLine(m.channel, chatLine(m, mine));
      if (mine || m.channel === 'proximidad' || m.channel === 'global') bubble(mine ? 0 : m.fromId, m.text);
    }
    else if (m.t === 'system') sys(esc(m.text));
    else if (m.t === 'pong') { S.net.ping = Math.round(performance.now() - m.c); $('#ping span').textContent = S.net.ping + ' ms'; }
  };
  ws.onclose = () => {
    if (S.net.ws!==ws) return;
    if (S.net.ok) sys('Se perdió la conexión con el chat. Reintentando…');
    S.net.ok = false; S.others.clear(); $('#ping').classList.remove('ok'); $('#ping span').textContent = 'sin conexión'; renderChat();
    if(started) reconnectTimer=setTimeout(connect, 4000);
  };
}
function addOther(p) { if(p.id===S.net.id||p.zone==='casa'||p.zone==='mine')return; S.others.set(p.id, { ...p, fx: p.x, fy: p.y, lastMove: now() }); renderChat(); renderNearby(); }
function sendMove(force) {
  if(W.mapId==='mine'){if(S.net.ok&&(force||performance.now()-S.net.lastSent>120)){S.net.lastSent=performance.now();S.net.ws.send(JSON.stringify({t:'move',zone:'mine',x:S.player.fx,y:S.player.fy}));}return;}
  if (!S.net.ok) return;
  if(W.mapId==='casa'){
    if(!force && S.net.sentZone==='casa')return;
    S.net.sentZone='casa'; S.net.sentKey=''; S.net.lastSent=performance.now();
    S.net.ws.send(JSON.stringify({ t:'move', zone:'casa', level: totalLevel() }));
    return;
  }
  const p = S.player, key = `${p.fx.toFixed(2)},${p.fy.toFixed(2)},${p.dir},${!!p.path.length}`;
  if (!force && (key === S.net.sentKey || performance.now() - S.net.lastSent < 120)) return;
  S.net.sentKey = key; S.net.sentZone='city'; S.net.lastSent = performance.now();
  S.net.ws.send(JSON.stringify({ t: 'move', zone:'city', x: p.fx, y: p.fy, dir: p.dir, moving: !!p.path.length, level: totalLevel() }));
}
setInterval(() => { if (S.net.ok) S.net.ws.send(JSON.stringify({ t: 'ping', c: performance.now() })); }, 3000);
const dist = (o) => Math.hypot(o.fx - S.player.fx, o.fy - S.player.fy);
function renderNearby() {
  const el = $('#cercanos'), list = [...S.others.values()].filter(o => !o.bot).sort((a, b) => dist(a) - dist(b));
  $('#n-cercanos').textContent = list.length;
  el.innerHTML = list.length ? list.slice(0, 10).map(o => { const m = Math.round(dist(o) * (W.render.metersPerTile || 2)); return `<li class="${m > 30 ? 'lejos' : ''}"><span class="pt"></span><span>${esc(o.name)}</span><span class="m">${m} m</span></li>`; }).join('')
    : `<li class="vacio">${S.net.ok ? 'Nadie más conectado' : 'Sin conexión al servidor'}</li>`;
}

// ---------------- mapa / colisión ----------------
const inside = (x, y) => x >= 0 && y >= 0 && x < W.width && y < W.height;
const walkable = (x, y) => inside(x, y) && W.collision[y][x] === 0;
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
  if (t.kind === 'animal') return { x: t.a.x, y: t.a.y };
  if (t.kind === 'npc' || t.kind === 'door') return { x: t.d.x, y: t.d.y };
  return { x: t.n.def.x, y: t.n.def.y };
}
function describe(t) {
  if (t.kind === 'animal') return `Cazar: <b>${NOMBRES[t.a.def.species]}</b>`;
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
    case 'mineral_rock': return n.state === 'active' ? `Picar: <b>${NOMBRES[d.mineral]}</b>` : 'Roca agotada';
  }
  return '';
}
function spriteKeyFor(n) { const d = n.def; return d.type === 'farm_plot' && n.state === 'grown' ? d.sprites.grown[n.crop] : d.sprites[n.state]; }
function hitTest(wx, wy) {
  const cand = [];
  for (const a of S.animals) {
    if (a.state !== 'alive') continue;
    const s = W.sprites[a.def.sprites.alive[0]]; const ox = a.fx * TS + 32 - s.anchorX, oy = (a.fy + 1) * TS - s.anchorY;
    if (wx >= ox - 8 && wx <= ox + s.w + 8 && wy >= oy - 8 && wy <= oy + s.h + 8) cand.push({ kind: 'animal', a, sort: (a.fy + 1) * TS + 1000 });
  }
  for (const npc of W.npcs || []) { const ox = npc.x * TS + 8, oy = (npc.y + 1) * TS - 92; if (wx >= ox && wx <= ox + 48 && wy >= oy && wy <= oy + 88) cand.push({ kind: 'npc', d: npc, sort: (npc.y + 1) * TS + 900 }); }
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
}
function followRoad(id) {
  const road=(W.roads3d||[]).find(r=>r.id===id);if(!road||!started)return;
  const p=S.player;let x=p.x,y=p.y,path=[];
  for(const point of road.points){const part=bfs(x,y,(a,b)=>a===point.x&&b===point.y);if(!part)return;path.push(...part);x=point.x;y=point.y;}
  p.path=path;p.pending=null;S.dest={x,y,t:now()};
}
function approach(t) {
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
function give(item, qty, tx, ty) { if (invAdd(item, qty)) { floatText(tx, ty, `+${qty} ${W.items[item].name}`); questProgress('collect', item, qty); } }
function floatText(tx, ty, text, color = '#fff7b0') { S.floaters.push({ x: tx * TS + 32, y: ty * TS, text, color, t0: now() }); }
function tired() { S.energy = Math.max(0, S.energy - 2); renderProfile(); }

async function act(t) {
  const p = S.player; const tt = targetTile(t); face(tt.x, tt.y);
  if(S.forgePending||S.minePending)return;
  if (t.kind === 'npc') return talkCapataz();
  if (t.kind === 'door') { S.quest.doorOpened = true; game('Tocas la puerta… ¡el capataz sale a recibirte!', 'juego'); updateTutorial(); return talkCapataz(); }
  if (now() < p.busyUntil) return;
  p.busyUntil = now() + 450;
  if (t.kind === 'animal') return hunt(t.a);
  const n = t.n, d = n.def; const secs = () => Math.max(1, Math.ceil((n.until - now()) / 1000));
  if(d.type==='mine_entrance')return switchMap('mine');
  if(d.type==='mine_exit')return switchMap('city');
  if(d.type==='home_door')return enterHouse();
  if(d.type==='casa_exit')return exitHouse();
  if(d.type==='furnace')return openFurnace(n);
  if (d.type === 'fruit_tree') {
    if (n.state !== 'full') return game(`El ${NOMBRES[d.species].toLowerCase()} no tiene frutas. Vuelven en ${secs()} s.`, 'aviso');
    const q = rnd(d.yield.min, d.yield.max); give(d.yield.item, q, d.x, d.y); game(`Recoges ${q} × <b>${W.items[d.yield.item].name}</b>.`);
    if (d.bonus && Math.random() < d.bonus.chance) { give(d.bonus.item, 1, d.x, d.y - 0.4); game(`¡Encontraste una <b>${W.items[d.bonus.item].name.toLowerCase()}</b>!`); }
    addXp('gathering', d.xp); n.state = 'picked'; n.until = now() + d.respawnMs; tired();
  } else if (d.type === 'wood_tree') {
    if (!needTool(d.tool)) return;
    if (n.state !== 'standing') return game(`Sólo queda el tocón. El pino vuelve a crecer en ${secs()} s.`, 'aviso');
    const q = rnd(d.yield.min, d.yield.max); give('madera', q, d.x, d.y); game(`Talas el pino y obtienes ${q} × <b>madera</b>.`);
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
      const q = rnd(d.harvest.fruitMin, d.harvest.fruitMax); give(n.crop, q, d.x, d.y); game(`Cosechas ${q} × <b>${W.items[n.crop].name}</b>.`);
      if (Math.random() < d.harvest.seedChance) give(n.crop + '_seed', 1, d.x, d.y - 0.4);
      addXp('planting', d.xp.harvest); n.state = 'empty'; n.crop = null;
    }
  } else if (d.type === 'fishing_spot') {
    if (!needTool(d.tool)) return;
    if (n.state !== 'active') return game(`Aquí no hay peces ahora. Vuelven en ${secs()} s.`, 'aviso');
    const fish = rollTable(d.yield.table); give(fish, d.yield.qty, d.x, d.y); game(`Lanzas la red y atrapas: <b>${W.items[fish].name}</b>.`);
    addXp('fishing', d.xp); n.state = 'depleted'; n.until = now() + d.respawnMs; tired();
  } else if (d.type === 'nodo_oro_fluvial') {
    if (!needTool(d.tool)) return;
    if (n.state !== 'active') return game(`Ya lavaste esta arena. El río trae más oro en ${secs()} s.`, 'aviso');
    if (Math.random() > d.successChance) { floatText(d.x, d.y, 'Sólo arena…', '#e8d9b0'); return game('Mueves la batea en la corriente… sólo arena. Intenta otra vez.', 'aviso'); }
    give(d.yield.item, 1, d.x, d.y); game('¡Brilla en la batea! Una <b>pepita de oro</b> del río.', 'oro');
    addXp('mining', d.xp); n.state = 'depleted'; n.until = now() + d.respawnMs; tired();
  } else if (d.type === 'mineral_rock') {
    if (!needTool(d.tool)) return;
    if (n.state !== 'active') return game(`La roca está agotada. Vuelve en ${secs()} s.`, 'aviso');
    let q;if(W.mapId==='mine'){if(!MiningRules.add(S.inv,W.items,d.yield.item,2,SLOTS)){game('Libera espacio antes de picar.');return;}if(S.minePending)return;S.minePending=true;try{const receipt=await economyAction({action:'mine',node:d.id});q=receipt.qty;}catch(error){game(esc(error.message));return;}finally{S.minePending=false;}}else q=rnd(d.yield.min,d.yield.max);if(!invAdd(d.yield.item,q)){game('El servidor guardó el mineral verificado. Libera espacio antes de seguir picando.');return;}floatText(d.x,d.y,`+${q} ${W.items[d.yield.item].name}`);questProgress('collect',d.yield.item,q);S.player.miningUntil=now()+800; game(`Picas la roca y obtienes ${q} × <b>${W.items[d.yield.item].name.toLowerCase()}</b>.`);
    addXp('mining', d.xp); n.state = 'depleted'; n.until = now() + d.respawnMs; tired();save();
  }
}
function hunt(a) {
  const d = a.def; if (!needTool(d.tool)) return; if (a.state !== 'alive') return;
  for (const y of d.yield) if (Math.random() < y.chance) give(y.item, rnd(y.min, y.max), a.x, a.y - (y.item === 'carne' ? 0 : 0.4));
  game(`Cazas un <b>${NOMBRES[d.species].toLowerCase()}</b> con la lanza.`); addXp('hunting', d.xp); a.state = 'hunted'; a.until = now() + d.respawnMs; tired();
}

// ---------------- entrada ----------------
const screenToWorld = (sx, sy) => ({ x: sx / zoom + S.cam.x, y: sy / zoom + S.cam.y });
cv.addEventListener('pointerdown', (e) => {
  if (!W || !started) return; $('#ayuda').hidden = true; if (S.dialog) return advanceDialog();
  const w = screenToWorld(e.clientX, e.clientY); const t = hitTest(w.x, w.y);
  if (t) { S.player.repaths = 0; approach(t); return; }
  const tx = Math.floor(w.x / TS), ty = Math.floor(w.y / TS);
  if (walkable(tx, ty)) goTo(tx, ty); else game('No se puede caminar ahí.', 'aviso');
});
function openCityMap() {
  if (!started) return;
  S.keys.clear(); $('#city-map').hidden=false; $('#hud-mapa').setAttribute('aria-expanded','true');
  drawCityMap(); $('#city-map-close').focus();
}
function closeCityMap() { $('#city-map').hidden=true; $('#hud-mapa').setAttribute('aria-expanded','false'); $('#hud-mapa').focus(); }
$('#hud-mapa').addEventListener('click',openCityMap);
$('#hud-mapa').addEventListener('keydown',e=>{if(e.target===$('#hud-mapa') && ['Enter',' '].includes(e.key)){e.preventDefault();openCityMap();}});
$('#city-map-close').onclick=closeCityMap;
$('#city-map').addEventListener('click',e=>{if(e.target===$('#city-map'))closeCityMap();});
function nearestWalkable(tx, ty) { for (let r = 0; r < 4; r++) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) if (walkable(tx + dx, ty + dy)) return [tx + dx, ty + dy]; return null; }
$('#mm-zoom').onclick = (e) => { e.stopPropagation(); S.mmZoom = S.mmZoom === 1 ? 2 : 1; $('#mm-zoom').textContent = S.mmZoom === 1 ? '+' : '−'; };
cv.addEventListener('pointermove', (e) => {
  if (!W) return; const w = screenToWorld(e.clientX, e.clientY); const t = hitTest(w.x, w.y); S.hover = t; const tip = $('#tooltip');
  if (t) { tip.hidden = false; tip.innerHTML = describe(t); tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY + 12) + 'px'; } else tip.hidden = true;
});
cv.addEventListener('pointerleave', () => { $('#tooltip').hidden = true; S.hover = null; });
const typing = () => document.activeElement && ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName);
addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !$('#hud-chat').hidden) { window.ChatUI.setOpen(false); e.preventDefault(); return; }
  if (e.key==='Escape' && !$('#city-map').hidden) { closeCityMap(); e.preventDefault(); return; }
  if (typing()) { if (e.key === 'Escape') document.activeElement.blur(); return; }
  if (!started) return;
  const k = e.key.toLowerCase();
  if (e.key === 'Enter' && started) { window.ChatUI.setOpen(true, true); e.preventDefault(); return; }
  if (S.dialog && (k === ' ' || k === 'enter')) return advanceDialog();
  if (['w','a','s','d','arrowup','arrowdown','arrowleft','arrowright','x'].includes(k)) { S.keys.add(k); e.preventDefault(); }
  if (/^[0-9]$/.test(k)) { const i = (+k + 9) % 10; if (S.inv[i]) { S.sel = i; renderInv(); } }
  if (k === '+' || k === '=') zoom = Math.min(2.5, zoom + 0.15);
  if (k === '-') zoom = Math.max(0.5, zoom - 0.15);
  if (k === 'h') $('#ayuda').hidden = !$('#ayuda').hidden;
  if (k === 'i') toggle('#w-inv'); if (k === 'k') toggle('#w-hab'); if (k === 'q') toggle('#p-misiones'); if (k === 'n') toggleNight();
  if (k === 'escape') { $('#ayuda').hidden = true; $('#w-inv').hidden = true; $('#w-hab').hidden = true; }
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
      if (announce && started) game(S.night ? 'Anochece en El Jardín.' : 'Amanece en El Jardín.', 'juego');
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
$('#btn-cerrar-ayuda').onclick = () => { $('#ayuda').hidden = true; };
$('#btn-reiniciar').onclick = () => { localStorage.removeItem('lifeinc.eljardin.v3'); location.reload(); };
function resize() { const r = devicePixelRatio || 1; cv.width = innerWidth * r; cv.height = innerHeight * r; }
addEventListener('resize', resize);

// ---------------- simulación ----------------
const SPEED = 4.2;
let last = performance.now();
function portalAt(x, y) {
  const ids = W.mapId==='mine' ? ['salida_mina'] : W.mapId==='casa' ? ['puerta_salida'] : ['entrada_mina_palmas', 'puerta_casa'];
  for (const id of ids) { const n = S.nodes.get(id); if (n && n.def.x===x && n.def.y===y) return n; }
  return null;
}
function updateMinePrompt() { const b = document.getElementById('mine-enter'), e = W.mineEntrance; if (!b || !e) return; const near = started && W.mapId !== 'mine' && cheb(S.player.x, S.player.y, e.x, e.y) <= 5; if (b.hidden === near) b.hidden = !near; }
function update(dt) {
  updateMinePrompt();
  if (!started) return;
  const p = S.player, t = now();
  const running = S.keys.has('x') && ['w','a','s','d','arrowup','arrowdown','arrowleft','arrowright'].some(k => S.keys.has(k));
  if (S.houseEdit) { p.path = []; S.dest = null; }
  else if (!p.path.length && S.keys.size && !S.dialog) {
    let dx = 0, dy = 0; const K = S.keys;
    if (K.has('w') || K.has('arrowup')) dy = -1; if (K.has('s') || K.has('arrowdown')) dy = 1;
    if (K.has('a') || K.has('arrowleft')) dx = -1; if (K.has('d') || K.has('arrowright')) dx = 1;
    if (window.LiveInk?.keyboardDirection) [dx, dy] = window.LiveInk.keyboardDirection(dx, dy);
    let nx = p.x + dx, ny = p.y + dy;
    if (dx && dy && (!walkable(p.x + dx, p.y) || !walkable(p.x, p.y + dy))) { if (walkable(p.x + dx, p.y)) ny = p.y; else if (walkable(p.x, p.y + dy)) nx = p.x; }
    const portal = (dx || dy) && (portalAt(p.x + dx, p.y + dy) || portalAt(p.x + dx, p.y) || portalAt(p.x, p.y + dy));
    if (portal && now() > (S.portalUntil || 0)) { S.portalUntil = now() + 1500; S.keys.clear(); act({ kind: 'node', n: portal }); return; }
    if ((dx || dy) && walkable(nx, ny)) { p.path = [[nx, ny]]; p.pending = null; S.dest = null; }
    else if (dx || dy) p.dir = dx > 0 ? 'right' : dx < 0 ? 'left' : dy > 0 ? 'down' : 'up';
  }
  if (p.path.length) {
    const [nx, ny] = p.path[0]; const ddx = nx - p.fx, ddy = ny - p.fy, d = Math.hypot(ddx, ddy);
    if (Math.abs(ddx) > 0.01 || Math.abs(ddy) > 0.01) p.dir = Math.abs(ddx) > Math.abs(ddy) ? (ddx > 0 ? 'right' : 'left') : (ddy > 0 ? 'down' : 'up');
    const step = SPEED * (S.horse?.mounted ? (S.horse.gallop ? 3.4 : 2) : (running ? 2 : 1)) * dt;
    if (d <= step) {
      p.fx = nx; p.fy = ny; p.x = nx; p.y = ny; p.path.shift(); updateTutorial();
      if (!p.path.length) {
        S.dest = null;
        if (p.pending) {
          const tg = p.pending; p.pending = null; const tt = targetTile(tg);
          if (tg.kind === 'door' ? (p.x === tg.d.approach.x && p.y === tg.d.approach.y) : cheb(p.x, p.y, tt.x, tt.y) <= 1) act(tg);
          else if (tg.kind === 'animal' && tg.a.state === 'alive' && p.repaths++ < 4) approach(tg);
          else if (tg.kind === 'animal') game('El animal se alejó.', 'aviso');
        }
      }
    } else { p.fx += ddx / d * step; p.fy += ddy / d * step; }
    p.animT += dt * (running ? 2 : 1);
  } else p.animT = 0;
  if(W.mapId==='casa' && !S.houseEdit && p.x===Casa.DOOR.x && p.y===Casa.DOOR.y && !p.path.length && now()>(S.portalUntil||0)) { S.portalUntil=now()+900; exitHouse(); }
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
  for (const o of S.others.values()) {   // interpolación de otros jugadores
    const ddx = o.x - o.fx, ddy = o.y - o.fy, d = Math.hypot(ddx, ddy);
    if (d > 6) { o.fx = o.x; o.fy = o.y; } else if (d > 0.01) { const st = Math.max(SPEED * dt, d * 0.2); if (d <= st) { o.fx = o.x; o.fy = o.y; } else { o.fx += ddx / d * st; o.fy += ddy / d * st; } }
    o.walking = d > 0.02 || (o.moving && t - o.lastMove < 300);
  }
  if (S.energy < 100) { S.energy = Math.min(100, S.energy + dt * 0.8); }
  S.floaters = S.floaters.filter(f => t - f.t0 < 1400);
  for (const [k, b] of S.bubbles) if (t > b.until) S.bubbles.delete(k);
}

// ---------------- dibujo ----------------
function drawSpriteAt(key, wx, wy) { const s = W.sprites[key], im = imgs[key]; if (s && im) ctx.drawImage(im, Math.round(wx - s.anchorX), Math.round(wy - s.anchorY)); }
const drawSprite = (key, tx, ty) => drawSpriteAt(key, tx * TS + 32, (ty + 1) * TS);
function frameKey(d, t) { return d.frames ? d.frames[Math.floor(t / (d.frameMs || 200)) % d.frames.length] : d.sprite; }
function bar(x, y, frac, col) { ctx.fillStyle = 'rgba(20,12,4,.75)'; ctx.fillRect(x - 20, y, 40, 6); ctx.fillStyle = col; ctx.fillRect(x - 19, y + 1, Math.max(0, 38 * frac), 4); }
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
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const id = W.ground[y][x]; ctx.drawImage(tileset, (id % cols) * TS, Math.floor(id / cols) * TS, TS, TS, x * TS, y * TS, TS + 0.5, TS + 0.5); }
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
  for (const a of S.animals) if (a.state === 'alive') list.push({ y: (a.fy + 1) * TS + 1, x: a.fx, draw: () => drawSprite(a.def.sprites.alive[a.frame], a.fx, a.fy) });
  for (const npc of W.npcs || []) list.push({ y: (npc.y + 1) * TS + 2, x: npc.x, draw: () => {
    if (capatazImg) drawChar(capatazImg, npc.x, npc.y, npc.facing, false, 0);
    const cx = npc.x * TS + 32, top = (npc.y + 1) * TS - 96;
    nameplate(cx, top - 4, [[npc.name, '#ffe14d', 13]]);
    if (!S.quest.turnedIn && (!stepDone(S.quest.def.steps[0]) || S.quest.done)) { ctx.font = 'bold 26px Pixelify, sans-serif'; ctx.fillStyle = '#000'; ctx.fillText(S.quest.done ? '?' : '!', cx + 2, top - 18 + Math.sin(t / 200) * 2); ctx.fillStyle = '#ffd400'; ctx.fillText(S.quest.done ? '?' : '!', cx, top - 20 + Math.sin(t / 200) * 2); }
  } });
  for (const o of S.others.values()) list.push({ y: (o.fy + 1) * TS + 2, x: o.fx, draw: () => {
    drawChar(sheets[o.color] || sheets.default, o.fx, o.fy, o.dir || 'down', o.walking, t / 1000);
    const cx = o.fx * TS + 32, top = (o.fy + 1) * TS - 96;
    nameplate(cx, top - 20, [[o.name, '#ffffff', 12], ...(o.clan ? [[`<${o.clan}>`, '#ffd27a', 11]] : []), [`Nv. ${o.level || 1}`, '#b8e0ff', 11]]);
  } });
  list.push({ y: (p.fy + 1) * TS + 3, x: p.fx, draw: () => {
    ctx.strokeStyle = 'rgba(120,255,120,.75)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.ellipse(p.fx * TS + 32, (p.fy + 1) * TS - 12, 20, 8, 0, 0, Math.PI * 2); ctx.stroke();
    drawChar(sheets[S.me.color] || sheets.default, p.fx, p.fy, p.dir, !!p.path.length, p.animT);
    const sel = selected(); if (sel && W.items[sel].category === 'tool' && imgs['icon:' + sel]) ctx.drawImage(imgs['icon:' + sel], Math.round(p.fx * TS + 40), Math.round((p.fy + 1) * TS - 56), 24, 24);
    const cx = p.fx * TS + 32, top = (p.fy + 1) * TS - 96;
    nameplate(cx, top - 20, [[S.me.name, '#9df59a', 12], ...(S.me.clan ? [[`<${S.me.clan}>`, '#ffd27a', 11]] : []), [`Nv. ${totalLevel()}`, '#b8e0ff', 11]]);
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
  for (const f of S.floaters) { const k = (t - f.t0) / 1400, y = f.y - 20 - k * 36; ctx.globalAlpha = 1 - k * k; ctx.fillStyle = '#000'; ctx.fillText(f.text, f.x + 1, y + 1); ctx.fillStyle = f.color; ctx.fillText(f.text, f.x, y); }
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
  }
  if (W.mapId==='casa' && window.Casa) { for (const it of Casa.layout.items) { const s=Casa.cellsOf(it); c.fillStyle=Casa.CATALOG[it.type].solid?'#6b4228':'#e6c27a'; for (const [x,y] of s) c.fillRect(x*k+1,y*k+1,k-2,k-2); } }
  for (const z of W.surfaceZones || []) { c.fillStyle = '#aab0b1'; c.fillRect(z.x*k,z.y*k,z.w*k,z.h*k); }
  for (const d of W.decorations) {
    const colr = { building: '#8a3b2a', waterfall: '#6e6258', fountain: '#9fe0ea', fence: '#7a5a34', tree_roble: '#2f6a2a', bush: '#3d7a34', stall: '#c83c30', mine_entrance: '#4a4038', boulder: '#8a8478' }[d.type];
    if (!colr) continue; c.fillStyle = colr;
    if (d.type === 'waterfall') { c.fillRect(d.x * k, d.y * k, (d.w || 1) * k, 3 * k); c.fillStyle = '#e8fbff'; c.fillRect(31 * k, d.y * k, 3 * k, (d.h || 1) * k); }
    else c.fillRect(d.x * k, d.y * k, (d.w || 1) * k, (d.h || 1) * k);
  }
  for (const d of W.landmarks || []) { c.fillStyle = d.kind === 'santa_gertrudis' ? '#f5f3ec' : '#a88a68'; c.fillRect(d.x*k,d.y*k,d.w*k,d.h*k); }
  const nc = { fruit_tree: '#2e6b2a', wood_tree: '#1f4d2a', farm_plot: '#6b4a26', mineral_rock: '#b0aaa0', fishing_spot: '#e8fbff', nodo_oro_fluvial: '#ffd400' };
  for (const n of W.nodes) if (nc[n.type]) { c.fillStyle = nc[n.type]; c.fillRect(n.x * k + 1, n.y * k + 1, k - 1, k - 1); }
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
  mctx.clearRect(0,0,size,size);mctx.save();mctx.beginPath();mctx.arc(size/2,size/2,size/2,0,Math.PI*2);mctx.clip();
  mctx.fillStyle='#233827';mctx.fillRect(0,0,size,size);mctx.drawImage(mmBase,v.x0*k,v.y0*k,v.span*k,v.span*k,0,0,size,size);
  const point=(x,y)=>[(x+.5-v.x0)*K,(y+.5-v.y0)*K];
  for(const o of S.others.values()){const [x,y]=point(o.fx,o.fy);mctx.fillStyle='#eef4ea';mctx.beginPath();mctx.arc(x,y,2,0,7);mctx.fill();}
  if(at){const [x,y]=point(at.x,at.y);mctx.strokeStyle='#f8bd54';mctx.lineWidth=2;mctx.strokeRect(x-4,y-4,8,8);}
  if((W.mapId||'city')==='city'&&W.mineEntrance){let [x,y]=point(W.mineEntrance.x,W.mineEntrance.y);const cx=size/2,cy=size/2,dd=Math.hypot(x-cx,y-cy),lim=size/2-9;if(dd>lim){x=cx+(x-cx)/dd*lim;y=cy+(y-cy)/dd*lim;}const pulse=5+Math.sin(performance.now()/260)*1.5;mctx.fillStyle='rgba(255,196,60,.35)';mctx.beginPath();mctx.arc(x,y,pulse+4,0,7);mctx.fill();mctx.fillStyle='#ffc93c';mctx.strokeStyle='#2c1a0c';mctx.lineWidth=2;mctx.beginPath();mctx.arc(x,y,5,0,7);mctx.fill();mctx.stroke();mctx.fillStyle='#2c1a0c';mctx.fillRect(x-1,y-3,2,6);}
  if((W.mapId||'city')==='city'&&W.homeDoor){let [x,y]=point(W.homeDoor.x,W.homeDoor.y);const cx=size/2,cy=size/2,dd=Math.hypot(x-cx,y-cy),lim=size/2-9;if(dd>lim){x=cx+(x-cx)/dd*lim;y=cy+(y-cy)/dd*lim;}mctx.fillStyle='#7dcea0';mctx.strokeStyle='#1c3324';mctx.lineWidth=2;mctx.fillRect(x-4,y-5,8,7);mctx.strokeRect(x-4,y-5,8,7);mctx.beginPath();mctx.moveTo(x-5,y-4);mctx.lineTo(x,y-8);mctx.lineTo(x+5,y-4);mctx.closePath();mctx.fill();mctx.stroke();}
  playerStar(mctx,...point(S.player.fx,S.player.fy),7);mctx.restore();
  if(!$('#city-map').hidden) drawCityMap();
}
function drawCityMap() {
  const canvas=$('#city-map-canvas'),c=canvas.getContext('2d'),size=canvas.width,pad=42,scale=(size-pad*2)/Math.max(W.width,W.height);
  const width=W.width*scale,height=W.height*scale,left=(size-width)/2,top=(size-height)/2;
  c.clearRect(0,0,size,size);c.fillStyle='#182820';c.fillRect(0,0,size,size);
  c.imageSmoothingEnabled=false;c.drawImage(mmBase,left,top,width,height);
  c.strokeStyle='#a8a17c';c.lineWidth=1;c.strokeRect(left,top,width,height);
  c.fillStyle='#f7e8bb';c.textAlign='center';c.textBaseline='middle';c.font='bold 22px sans-serif';
  c.fillText('N',size/2,top-21);c.fillText('S',size/2,top+height+23);c.fillText('OC',left-22,size/2);c.fillText('OR',left+width+23,size/2);
  for(const label of W.mapLabels||[]){const x=left+(label.x+.5)*scale,y=top+(label.y+.5)*scale;c.font='bold 12px sans-serif';const name=label.name.replace('Parque de ','').replace(' · mirador','');const textWidth=c.measureText(name).width;c.fillStyle='#14251ee8';c.fillRect(x-textWidth/2-5,y+8,textWidth+10,20);c.fillStyle='#fff1c9';c.fillText(name,x,y+18);}
  for(const o of S.others.values()){c.fillStyle='#eef4ea';c.beginPath();c.arc(left+(o.fx+.5)*scale,top+(o.fy+.5)*scale,2,0,7);c.fill();}
  if((W.mapId||'city')==='city'&&W.mineEntrance){const x=left+(W.mineEntrance.x+.5)*scale,y=top+(W.mineEntrance.y+.5)*scale;c.fillStyle='#ffc93c';c.strokeStyle='#2c1a0c';c.lineWidth=2;c.beginPath();c.arc(x,y,7,0,7);c.fill();c.stroke();c.font='bold 12px sans-serif';const t='⛏ Mina';const tw=c.measureText(t).width;c.fillStyle='#2c1a0ce8';c.fillRect(x-tw/2-5,y+10,tw+10,20);c.fillStyle='#ffd66b';c.fillText(t,x,y+20);}
  if((W.mapId||'city')==='city'&&W.homeDoor){const x=left+(W.homeDoor.x+.5)*scale,y=top+(W.homeDoor.y+.5)*scale;c.fillStyle='#7dcea0';c.strokeStyle='#1c3324';c.lineWidth=2;c.fillRect(x-6,y-6,12,10);c.strokeRect(x-6,y-6,12,10);c.beginPath();c.moveTo(x-8,y-5);c.lineTo(x,y-14);c.lineTo(x+8,y-5);c.closePath();c.fill();c.stroke();c.font='bold 12px sans-serif';const t='Casa';const tw=c.measureText(t).width;c.fillStyle='#1c3324e8';c.fillRect(x-tw/2-5,y+8,tw+10,18);c.fillStyle='#d8ffe8';c.fillText(t,x,y+17);}
  playerStar(c,left+(S.player.fx+.5)*scale,top+(S.player.fy+.5)*scale,8);
  $('#city-map-location').textContent=`Tu posición: ${S.player.fx.toFixed(1)}, ${S.player.fy.toFixed(1)} · ★ Tú`;
}
let lastUi = 0;
function loop(ts) {
  const dt = Math.min(0.05, (ts - last) / 1000); last = ts;
  update(dt); drawMinimap(arrowTarget());
  if (ts - lastUi > 500) { lastUi = ts; applyCircadian(true); renderNearby(); renderProfile(); if (S.chat.tab === 'proximidad') renderChatNote(); }
  requestAnimationFrame(loop);
}
function renderChatNote() { const n = $('#chat-nota'); const before = n.innerHTML; renderChat(); if (n.innerHTML === before) return; }

window.LiveInk = { get cityNodes(){return cityNodes||S.nodes;},get cityAnimals(){return cityAnimals||S.animals;},get world(){return W;}, state:S, walkable, goTo, followRoad, approach, advanceDialog, enterHouse, exitHouse,
 click(x,y){if(!started)return; if(S.dialog)return advanceDialog(); const t=hitTest(x*TS+32,(y+1)*TS-8); if(t)approach(t);else if(walkable(Math.floor(x),Math.floor(y)))goTo(Math.floor(x),Math.floor(y));},
 interact(id){if(id==='puerta_salida'&&started&&(W.mapId||'city')==='casa'){exitHouse();return;}const n=S.nodes.get(id);const a=S.animals.find(a=>a.def.id===id);const d=W.doors.find(d=>d.id===id);const npc=W.npcs.find(n=>n.id===id);const t=n?{kind:'node',n}:a?{kind:'animal',a}:d?{kind:'door',d}:npc?{kind:'npc',d:npc}:null;if(t&&started)approach(t);},
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
  const coins0 = S.coins; const cap = W.npcs[0]; nextTo(cap.x, cap.y); act({ kind: 'npc', d: cap }); while (S.dialog) advanceDialog();
  ok(S.quest.turnedIn && S.coins > coins0 && currentStage().id === 'libre', 'Primeros Pasos entregado (+monedas)');
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
  ok(W.width===80 && W.height===64,'mundo compartido 80x64');
  ok(!walkable(49,20)&&walkable(49,30),'río bloqueado y puente caminable');
  p.x = p.fx = W.spawn.x; p.y = p.fy = W.spawn.y;
  const fails = out.filter(l => l.startsWith('FALLO')).length;
  const el = $('#autotest'); el.hidden = false; el.textContent = (fails ? 'AUTOTEST FALLÓ' : 'AUTOTEST OK') + ` (${out.length} comprobaciones)\n` + out.join('\n');
  document.title = fails ? 'AUTOTEST FALLÓ' : 'AUTOTEST OK';
}

S.dbg = { updateTutorial, talkCapataz, advanceDialog, act, toggleNight };
init().catch(err => { const c = $('#cargando'); if (c) c.textContent = 'Error: ' + err.message + ' — abre esta página con el servidor (ver README).'; console.error(err); });
})();
