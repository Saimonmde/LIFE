/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Editar mundo. El servidor decide quién puede guardar; el botón sólo aparece para un administrador. */
import * as T from '../three.module.js';
import { createView } from './render.js';

const Model = window.EditorModel;
const allLayers = { terrain: true, paths: true, vegetation: true, decoration: true };
let allowed = false;
let active = false;
let env = 'public';
let version = 0;
let dirty = false;
let api = null;
let view = null;
let panel = null;
let session = Model.session();
let selection = [];
let arm = '';
let fly = false;
let preview = false;
let stroke = null;
let pending = null;
let terrainTimer = 0;
let lastTerrain = '';
const clipboard = { props: [], paths: [] };

const muestras = badge('muestras-badge', 'VERSIÓN DE MUESTRAS');
const volver = document.createElement('button');
volver.id = 'editar-mundo-volver';
volver.type = 'button';
volver.hidden = true;
volver.textContent = 'Editar mundo';
document.body.append(volver);
volver.onclick = () => setPreview(false);
const box = document.createElement('div');
box.id = 'ed-box';
box.hidden = true;
document.body.append(box);

function badge(id, text) {
  const el = document.createElement('div');
  el.id = id;
  el.textContent = text;
  el.hidden = true;
  document.body.append(el);
  return el;
}

function state() { return panel ? panel.state() : { tab: 'caminos', pathStyle: 'piedra', brush: '1', mode: 'paint', strength: 1, terrainOp: 'raise', density: 3, propType: 'palma', material: 'grass', tint: '#74875b', snap: true, scale: 1, rot: 0, layers: allLayers }; }
function note(text) { if (panel) panel.status(text); }
function bounds() {
  const world = api && api.world;
  if (!world) return null;
  return { minX: 0, minZ: 0, maxX: Math.max(0, world.width - 1), maxZ: Math.max(0, world.height - 1) };
}
function brush() { return Number(state().brush) === 5 ? 5 : Number(state().brush) === 3 ? 3 : 1; }

function adopt(pack, trust) {
  if (!pack || typeof pack !== 'object') return;
  env = pack.env === 'preview' ? 'preview' : 'public';
  document.body.classList.toggle('muestras', env === 'preview');
  muestras.hidden = env !== 'preview';
  if (trust && typeof pack.editor === 'boolean') {
    allowed = pack.editor;
    ensureMenu();
  }
  if (panel) panel.setEnv(env);
  const nextVersion = Number(pack.version) || 0;
  const changed = nextVersion !== version || !view;
  version = nextVersion;
  if (!dirty) {
    session.load(pack.current || Model.emptyCurrent());
    pending = null;
    if (panel) {
      panel.setDesigns(pack.designs || []);
      panel.setHistory(pack.history || []);
    }
    renderWorld();
  } else if (changed) {
    pending = pack;
    note('Hay una versión nueva en el servidor. Guardar puede pedir recargar.');
    if (panel) {
      panel.setDesigns(pack.designs || []);
      panel.setHistory(pack.history || []);
    }
  }
}

async function refresh() {
  try {
    const res = await fetch('/api/world-edits', { cache: 'no-store' });
    if (!res.ok) return;
    adopt(await res.json(), true);
  } catch (e) { /* el juego sigue sin la capa */ }
}

function ensureMenu() {
  const menu = document.getElementById('hud-gear-menu');
  if (!menu) return;
  let button = document.getElementById('cajon-editor');
  if (!allowed) {
    if (button) button.remove();
    return;
  }
  if (!button) {
    button = document.createElement('button');
    button.type = 'button';
    button.id = 'cajon-editor';
    button.textContent = 'Editar mundo (admin)';
    button.addEventListener('click', (event) => {
      event.stopPropagation();
      menu.hidden = true;
      const gear = document.getElementById('hud-gear');
      if (gear) gear.setAttribute('aria-expanded', 'false');
      enter();
    });
  }
  if (menu.lastElementChild !== button) menu.append(button);
}

function ensurePanel() {
  if (panel || !allowed) return;
  panel = window.EditorPanel.mount({
    action: onAction,
    change: () => renderWorld(),
    tab: () => note(state().tab === 'objetos' ? 'Toca un objeto para moverlo, girarlo o cambiar su tamaño.' : 'Listo para editar.'),
  });
  panel.setEnv(env);
}

function enter() {
  if (!allowed) return;
  ensurePanel();
  active = true;
  if (window.LIVE3D) window.LIVE3D.editMode = true;
  document.body.classList.add('modo-edicion');
  panel.show(true);
  volver.hidden = true;
  setPreview(false);
  note('Editar mundo. Guardar publica la capa para todos.');
  renderWorld();
}

function leave() {
  active = false;
  fly = false;
  arm = '';
  if (window.LIVE3D) {
    window.LIVE3D.editMode = false;
    window.LIVE3D.freeFly = false;
  }
  document.body.classList.remove('modo-edicion');
  if (panel) panel.show(false);
  volver.hidden = true;
  box.hidden = true;
  applyLayers(allLayers, true);
  if (view) view.placeGizmo(null, false);
}

function setPreview(on) {
  preview = !!on;
  if (panel) panel.preview(preview);
  volver.hidden = !preview;
}

function attach() {
  if (api || !window.LIVE3D || !window.LIVE3D.editorApi) return;
  api = window.LIVE3D.editorApi;
  view = createView();
  api.scene.add(view.root);
  api.scene.add(view.gizmo);
  api.scene.add(view.ring);
  window.LIVE3D.onEditPointer = onPointer;
  window.LIVE3D.onEditFrame = onFrame;
  renderWorld();
}

function hookNet() {
  const net = window.LiveInk && LiveInk.state && LiveInk.state.net;
  const ws = net && net.ws;
  if (!ws || ws.__edits) return;
  ws.__edits = true;
  ws.addEventListener('message', (event) => {
    let message;
    try { message = JSON.parse(event.data); } catch (e) { return; }
    if (!message) return;
    if (message.t === 'welcome' && message.worldEdits) adopt(message.worldEdits, true);
    if (message.t === 'world_edits' && message.worldEdits) adopt(message.worldEdits, false);
    if (message.t === 'world_edit_result') {
      if (message.code === 403) note('El servidor rechazó la edición.');
      else if (message.worldEdits) adopt(message.worldEdits, true);
    }
  });
}

function overlayMap() {
  const map = new Map();
  (session.current.terrain || []).forEach(cell => map.set(cell.x + ',' + cell.z, cell.dy));
  return map;
}

function renderWorld() {
  if (!view || !api) return;
  const layers = active && panel ? state().layers : allLayers;
  if (api.setElevationOverlay) {
    const map = overlayMap();
    api.setElevationOverlay((x, z) => map.get(x + ',' + z) || 0);
  }
  const key = view.rebuild(session.current, api.height, layers);
  applyLayers(layers, false);
  if (key !== lastTerrain) {
    const first = lastTerrain === '';
    lastTerrain = key;
    if (!(first && key === '[]')) {
      clearTimeout(terrainTimer);
      terrainTimer = setTimeout(() => { if (api.rebuildTerrain) api.rebuildTerrain(); applyLayers(active && panel ? state().layers : allLayers, false); }, 80);
    }
  }
  placeSelection();
  if (panel && active) panel.setList(listRows());
}

function applyLayers(layers, forceShow) {
  const show = forceShow ? allLayers : layers;
  if (view) view.setLayers(show);
  if (!api) return;
  api.scene.traverse(obj => {
    if (obj.userData && obj.userData.terrain) obj.visible = !!show.terrain;
  });
}

function listRows() {
  return (session.current.props || []).slice(-24).reverse().map(prop => ({
    kind: 'prop', id: prop.id, label: prop.type + ' · ' + Math.round(prop.x) + ',' + Math.round(prop.z),
  }));
}

function aim(event) {
  api.pointer.set((event.clientX / innerWidth) * 2 - 1, 1 - (event.clientY / innerHeight) * 2);
  api.ray.setFromCamera(api.pointer, api.camera);
}

function tileAt(event) {
  aim(event);
  const terrains = [];
  api.scene.traverse(obj => { if (obj.userData && obj.userData.terrain) terrains.push(obj); });
  const hit = terrains.length ? api.ray.intersectObjects(terrains, false)[0] : null;
  if (hit) return { x: Math.floor(hit.point.x / 2), z: Math.floor(hit.point.z / 2), point: hit.point.clone() };
  const origin = api.ray.ray.origin;
  const dir = api.ray.ray.direction;
  for (let t = 2; t < 600; t += 1.5) {
    const x = origin.x + dir.x * t;
    const y = origin.y + dir.y * t;
    const z = origin.z + dir.z * t;
    const tx = x / 2;
    const tz = z / 2;
    if (y <= api.height(tx, tz) + 0.5) return { x: Math.floor(tx), z: Math.floor(tz), point: new T.Vector3(x, y, z) };
  }
  return null;
}

function pick(event) {
  aim(event);
  if (view && view.gizmo.visible) {
    const gizmoHit = api.ray.intersectObjects(view.gizmo.children, false)[0];
    if (gizmoHit) return { gizmo: gizmoHit.object.userData.axis, point: gizmoHit.point.clone() };
  }
  const editors = [];
  view.root.traverse(obj => { if (obj.isMesh) editors.push(obj); });
  const editorHit = editors.length ? api.ray.intersectObjects(editors, false)[0] : null;
  if (editorHit && editorHit.instanceId != null && editorHit.object.userData.ids) {
    return { kind: editorHit.object.userData.kind, id: editorHit.object.userData.ids[editorHit.instanceId], point: editorHit.point.clone() };
  }
  const world = [];
  api.scene.traverse(obj => {
    if (!obj.isMesh || !obj.userData || obj.userData.editor || obj.userData.terrain) return;
    world.push(obj);
  });
  const worldHit = world.length ? api.ray.intersectObjects(world, false)[0] : null;
  if (worldHit) {
    let node = worldHit.object;
    let found = null;
    while (node) {
      if (node.userData && node.userData.actor) { found = null; break; }
      if (node.userData && node.userData.id) found = node;
      node = node.parent;
    }
    if (found) return { kind: 'object', id: found.userData.id, mesh: found, point: worldHit.point.clone() };
  }
  return null;
}

function onPointer(phase, event) {
  if (!active || !api) return false;
  if (event.target && event.target.closest && event.target.closest('#editor-panel, #editar-mundo-volver, #hud-gear, #hud-gear-menu')) return false;
  if (fly && phase !== 'up') return false;
  if ((event.altKey || event.button === 2) && phase !== 'up') return false;
  if (phase === 'down') { begin(event); return !fly; }
  if (phase === 'move' && stroke) { move(event); return !fly; }
  if (phase === 'up') { finish(event); return true; }
  return false;
}

function begin(event) {
  const tool = armedTool();
  if (api.indoors && api.indoors() && (tool === 'paint' || tool === 'erase')) {
    note('Sal al valle para editar el mapa.');
    return;
  }
  const hit = pick(event);
  const tile = tileAt(event);
  stroke = { tool, pointer: event.pointerId, sx: event.clientX, sy: event.clientY, base: Model.clone(session.current), tile, hit, cells: [], props: [], moved: false };
  if (tool === 'box') { box.hidden = false; box.style.left = event.clientX + 'px'; box.style.top = event.clientY + 'px'; box.style.width = '0px'; box.style.height = '0px'; return; }
  if (hit && hit.gizmo) { stroke.tool = 'gizmo'; stroke.axis = hit.gizmo; session.begin(); return; }
  if (tool === 'pick') { eyedrop(hit, tile); stroke = null; return; }
  if (tool === 'select' || tool === 'move') {
    if (hit && hit.id) select(hit, event.shiftKey);
    else if (!event.shiftKey) selection = [];
    placeSelection();
    if (tool === 'move' && selection.length) session.begin();
    return;
  }
  if (tool === 'paint' || tool === 'erase') {
    session.begin();
    stamp(tile);
  }
}

function move(event) {
  if (!stroke) return;
  if (stroke.tool === 'box') {
    const x = Math.min(stroke.sx, event.clientX);
    const y = Math.min(stroke.sy, event.clientY);
    box.style.left = x + 'px';
    box.style.top = y + 'px';
    box.style.width = Math.abs(event.clientX - stroke.sx) + 'px';
    box.style.height = Math.abs(event.clientY - stroke.sy) + 'px';
    return;
  }
  const tile = tileAt(event);
  if (stroke.tool === 'gizmo') { dragGizmo(event); return; }
  if (stroke.tool === 'move') { dragGround(tile); return; }
  if (stroke.tool === 'paint' || stroke.tool === 'erase') stamp(tile);
}

function finish(event) {
  if (stroke && stroke.tool === 'box') selectBox(event);
  if (stroke && session) session.end();
  if (stroke && (stroke.tool === 'paint' || stroke.tool === 'erase' || stroke.tool === 'move' || stroke.tool === 'gizmo')) dirty = dirty || true;
  stroke = null;
  box.hidden = true;
  renderWorld();
  placeSelection();
}

function armedTool() {
  if (arm === 'pick' || arm === 'box') return arm;
  const tab = state().tab;
  if (tab === 'objetos' || tab === 'disenos') return state().mode === 'erase' ? 'erase' : 'select';
  if (state().mode === 'move') return 'move';
  if (state().mode === 'erase') return 'erase';
  return 'paint';
}

function select(hit, add) {
  const item = { kind: hit.kind === 'surface' ? 'surface' : hit.kind, id: String(hit.id) };
  if (!add) selection = [item];
  else if (!selection.some(row => row.kind === item.kind && row.id === item.id)) selection.push(item);
  if (hit.kind === 'object' && hit.mesh && !hit.mesh.userData.editBase) {
    hit.mesh.userData.editBase = {
      x: hit.mesh.position.x, y: hit.mesh.position.y, z: hit.mesh.position.z,
      sx: hit.mesh.scale.x, sy: hit.mesh.scale.y, sz: hit.mesh.scale.z, ry: hit.mesh.rotation.y,
    };
  }
  syncSelectionLabel();
}

function objectDraft(mesh) {
  if (!mesh.userData.editBase) {
    mesh.userData.editBase = {
      x: mesh.position.x, y: mesh.position.y, z: mesh.position.z,
      sx: mesh.scale.x, sy: mesh.scale.y, sz: mesh.scale.z,
      ry: mesh.rotation.y,
    };
  }
  const base = mesh.userData.editBase;
  return {
    id: mesh.userData.id,
    x: Math.round(base.x * 1000) / 1000,
    y: Math.round(base.y * 1000) / 1000,
    z: Math.round(base.z * 1000) / 1000,
    scale: 1,
    rotY: Math.round((base.ry * 180 / Math.PI) % 360),
    deleted: false,
  };
}

function stamp(tile) {
  if (!tile || !stroke) return;
  const ui = state();
  const cells = Model.brushCells(tile.x, tile.z, brush(), bounds());
  if (ui.tab === 'caminos') {
    stroke.cells.push(...cells);
    const unique = dedupe(stroke.cells);
    session.preview(stroke.tool === 'erase' ? Model.erasePaths(stroke.base, unique) : Model.paintPaths(stroke.base, unique, ui.pathStyle));
  } else if (ui.tab === 'superficies') {
    stroke.cells.push(...cells);
    const unique = dedupe(stroke.cells);
    session.preview(stroke.tool === 'erase' ? Model.eraseSurfaces(stroke.base, unique) : Model.paintSurfaces(stroke.base, unique, ui.material, ui.tint));
  } else if (ui.tab === 'terreno') {
    stroke.cells.push(...cells);
    const mode = stroke.tool === 'erase' ? 'erase' : ui.terrainOp;
    session.preview(Model.terrainApply(stroke.base, dedupe(stroke.cells), mode, ui.strength, (x, z) => api.corner(x, z) - (overlayMap().get(x + ',' + z) || 0)));
  } else if (ui.tab === 'vegetacion') {
    const mark = tile.x + ':' + tile.z;
    if (stroke.mark === mark) return;
    stroke.mark = mark;
    if (stroke.tool === 'erase') {
      const reach = brush();
      const drop = (stroke.base.props || []).filter(prop => Math.hypot((prop.x - 1) / 2 - tile.x, (prop.z - 1) / 2 - tile.z) <= reach).map(prop => prop.id);
      session.preview(Model.removeProps(session.current, drop));
      stroke.base = Model.clone(session.current);
    } else if (ui.density <= 1) {
      stroke.props.push(Model.scatter(tile.x, tile.z, 1, 1, ui.propType)[0]);
      session.preview(Model.placeProps(stroke.base, stroke.props));
    } else {
      stroke.props.push(...Model.scatter(tile.x, tile.z, brush(), ui.density, ui.propType));
      session.preview(Model.placeProps(stroke.base, stroke.props));
    }
  }
  dirty = true;
  renderWorld();
}

function dedupe(cells) {
  const map = new Map();
  cells.forEach(cell => map.set(cell.x + ':' + cell.z, { x: cell.x | 0, z: cell.z | 0 }));
  return [...map.values()];
}

function dragGround(tile) {
  if (!tile || !stroke || !stroke.tile) return;
  const dx = tile.point.x - stroke.tile.point.x;
  const dz = tile.point.z - stroke.tile.point.z;
  if (!dx && !dz) return;
  nudgeSelection(dx, 0, dz, false, true);
  stroke.moved = true;
}

function dragGizmo(event) {
  if (!stroke || !selection.length) return;
  const axis = stroke.axis;
  if (axis === 'scale') {
    const scale = Math.max(0.25, Math.min(4, state().scale + event.movementX * 0.01));
    applyScale(scale, true);
    return;
  }
  const origin = gizmoPoint() || new T.Vector3();
  const dir = new T.Vector3(axis === 'x' ? 1 : 0, axis === 'y' ? 1 : 0, axis === 'z' ? 1 : 0);
  const a = origin.clone().project(api.camera);
  const b = origin.clone().add(dir).project(api.camera);
  const sx = (b.x - a.x) * innerWidth / 2;
  const sy = (a.y - b.y) * innerHeight / 2;
  const len2 = sx * sx + sy * sy || 1;
  const delta = (event.movementX * sx + event.movementY * sy) / len2;
  const step = state().snap ? Math.round(delta) : delta;
  nudgeSelection(axis === 'x' ? step : 0, axis === 'y' ? step : 0, axis === 'z' ? step : 0, false);
}

function nudgeSelection(dx, dy, dz, fromKeys, absolute) {
  const ui = state();
  const snap = !!ui.snap;
  const props = selection.filter(item => item.kind === 'prop').map(item => item.id);
  const objects = selection.filter(item => item.kind === 'object');
  const paths = selection.filter(item => item.kind === 'path');
  let next = absolute && stroke && stroke.base ? Model.clone(stroke.base) : session.current;
  if (props.length) {
    let mx = dx;
    let my = dy;
    let mz = dz;
    if (fromKeys) {
      const step = snap ? 1 : 0.25;
      mx *= step; my *= step; mz *= step;
    }
    next = Model.moveProps(next, props, mx, my, mz);
    if (snap && !fromKeys) {
      next = Model.updateProps(next, props, {});
      next.props = next.props.map(prop => props.includes(prop.id) ? Object.assign({}, prop, { x: Math.round(prop.x), z: Math.round(prop.z) }) : prop);
    }
  }
  if (paths.length) {
    const stepX = fromKeys ? (dx > 0 ? 1 : dx < 0 ? -1 : 0) : Math.round(dx / 2);
    const stepZ = fromKeys ? (dz > 0 ? 1 : dz < 0 ? -1 : 0) : Math.round(dz / 2);
    if (stepX || stepZ) {
      next = Model.movePaths(next, paths.map(item => {
        const [x, z] = item.id.split(':').map(Number);
        return { x, z };
      }), stepX, stepZ);
      selection = selection.map(item => {
        if (item.kind !== 'path') return item;
        const [x, z] = item.id.split(':').map(Number);
        return { kind: 'path', id: (x + stepX) + ':' + (z + stepZ) };
      });
    }
  }
  objects.forEach(item => {
    const mesh = findObject(item.id);
    const current = next.objects.find(obj => obj.id === item.id) || (mesh ? objectDraft(mesh) : null);
    if (!current) return;
    const step = fromKeys ? (snap ? 1 : 0.25) : 1;
    const nx = current.x + dx * (fromKeys ? step : 1);
    const ny = current.y + dy * (fromKeys ? step : 1);
    const nz = current.z + dz * (fromKeys ? step : 1);
    next = Model.upsertObjects(next, [Object.assign({}, current, {
      x: snap ? Math.round(nx) : Math.round(nx * 1000) / 1000,
      y: Math.round(ny * 1000) / 1000,
      z: snap ? Math.round(nz) : Math.round(nz * 1000) / 1000,
    })]);
  });
  if (stroke) session.preview(next);
  else session.commit(next);
  dirty = true;
  renderWorld();
}

function applyScale(scale, live) {
  const value = Math.max(0.25, Math.min(4, Number(scale) || 1));
  const props = selection.filter(item => item.kind === 'prop').map(item => item.id);
  const objects = selection.filter(item => item.kind === 'object');
  let next = session.current;
  if (props.length) next = Model.updateProps(next, props, { scale: value });
  objects.forEach(item => {
    const mesh = findObject(item.id);
    const current = next.objects.find(obj => obj.id === item.id) || (mesh ? objectDraft(mesh) : null);
    if (current) next = Model.upsertObjects(next, [Object.assign({}, current, { scale: value })]);
  });
  if (live) {
    session.begin();
    session.preview(next);
  } else session.commit(next);
  dirty = true;
  if (panel) panel.setSelection(selectionLabel(), value, null);
  renderWorld();
}

function applyRot(rot, live) {
  const value = ((Number(rot) || 0) % 360 + 360) % 360;
  const props = selection.filter(item => item.kind === 'prop').map(item => item.id);
  let next = session.current;
  if (props.length) next = Model.updateProps(next, props, { rotY: value });
  selection.filter(item => item.kind === 'object').forEach(item => {
    const mesh = findObject(item.id);
    const current = next.objects.find(obj => obj.id === item.id) || (mesh ? objectDraft(mesh) : null);
    if (current) next = Model.upsertObjects(next, [Object.assign({}, current, { rotY: value })]);
  });
  if (live) { session.begin(); session.preview(next); }
  else session.commit(next);
  dirty = true;
  if (panel) panel.setSelection(selectionLabel(), null, Math.round(value));
  renderWorld();
}

function rotateBy(delta) {
  const base = selectedRot();
  const snapped = Math.round((base + delta) / 15) * 15;
  applyRot(snapped, false);
}

function selectedRot() {
  const prop = selectedProp();
  if (prop) return prop.rotY || 0;
  const obj = selectedObject();
  return obj ? obj.rotY || 0 : state().rot;
}

function selectedProp() {
  const hit = selection.find(item => item.kind === 'prop');
  return hit && session.current.props.find(prop => prop.id === hit.id);
}
function selectedObject() {
  const hit = selection.find(item => item.kind === 'object');
  return hit && session.current.objects.find(obj => obj.id === hit.id);
}

function selectionLabel() {
  if (!selection.length) return 'Nada seleccionado. Toca un objeto del mapa.';
  if (selection.length > 1) return selection.length + ' elementos seleccionados.';
  const item = selection[0];
  return item.kind + ' · ' + item.id;
}

function syncSelectionLabel() {
  const prop = selectedProp();
  const obj = selectedObject();
  const scale = prop ? prop.scale : obj ? obj.scale : 1;
  const rot = prop ? prop.rotY : obj ? obj.rotY : 0;
  if (panel) panel.setSelection(selectionLabel(), Math.round(scale * 100) / 100, Math.round(rot));
}

function findObject(id) {
  let found = null;
  api.scene.traverse(obj => {
    if (found || !obj.userData || obj.userData.id !== id || obj.userData.actor) return;
    if (obj.parent && obj.parent.userData && obj.parent.userData.id === id) return;
    found = obj;
  });
  return found;
}

function gizmoPoint() {
  const prop = selectedProp();
  if (prop) return new T.Vector3(prop.x, api.height((prop.x - 1) / 2, (prop.z - 1) / 2), prop.z);
  const obj = selectedObject();
  if (obj) return new T.Vector3(obj.x, obj.y, obj.z);
  const path = selection.find(item => item.kind === 'path');
  if (path) {
    const [x, z] = path.id.split(':').map(Number);
    return new T.Vector3(x * 2 + 1, api.height(x, z), z * 2 + 1);
  }
  return null;
}

function placeSelection() {
  if (!view) return;
  const point = active ? gizmoPoint() : null;
  view.placeGizmo(point, !!point);
  syncSelectionLabel();
}

function eyedrop(hit, tile) {
  arm = '';
  if (hit && hit.kind === 'path') {
    const path = session.current.paths.find(item => item.id === hit.id);
    if (path && panel) panel.state().pathStyle = path.style;
  } else if (hit && hit.kind === 'prop') {
    const prop = session.current.props.find(item => item.id === hit.id);
    if (prop && panel) panel.state().propType = prop.type;
  } else if (hit && hit.kind === 'surface') {
    const surface = session.current.surfaces.find(item => item.id === hit.id);
    if (surface && panel) { panel.state().material = surface.material; panel.state().tint = surface.tint; }
  } else if (tile) {
    const path = session.current.paths.find(item => item.x === tile.x && item.z === tile.z);
    if (path && panel) panel.state().pathStyle = path.style;
  }
  note('Cuentagotas listo.');
}

function selectBox(event) {
  const x0 = Math.min(stroke.sx, event.clientX);
  const y0 = Math.min(stroke.sy, event.clientY);
  const x1 = Math.max(stroke.sx, event.clientX);
  const y1 = Math.max(stroke.sy, event.clientY);
  const next = [];
  (session.current.props || []).forEach(prop => {
    const y = api.height((prop.x - 1) / 2, (prop.z - 1) / 2);
    const screen = project(prop.x, y, prop.z);
    if (screen && screen.x >= x0 && screen.x <= x1 && screen.y >= y0 && screen.y <= y1) next.push({ kind: 'prop', id: prop.id });
  });
  (session.current.paths || []).forEach(path => {
    const screen = project(path.x * 2 + 1, api.height(path.x, path.z), path.z * 2 + 1);
    if (screen && screen.x >= x0 && screen.x <= x1 && screen.y >= y0 && screen.y <= y1) next.push({ kind: 'path', id: path.id });
  });
  selection = next;
  arm = '';
  note(next.length ? next.length + ' en la caja.' : 'La caja no tocó elementos.');
}

function project(x, y, z) {
  const vector = new T.Vector3(x, y, z).project(api.camera);
  if (vector.z < -1 || vector.z > 1) return null;
  return { x: (vector.x + 1) * innerWidth / 2, y: (1 - vector.y) * innerHeight / 2 };
}

function onFrame() {
  if (!api) return;
  (session.current.objects || []).forEach(item => {
    const mesh = findObject(item.id);
    if (!mesh) return;
    if (!mesh.userData.editBase) {
      mesh.userData.editBase = { x: mesh.position.x, y: mesh.position.y, z: mesh.position.z, sx: mesh.scale.x, sy: mesh.scale.y, sz: mesh.scale.z, ry: mesh.rotation.y };
    }
    const base = mesh.userData.editBase;
    const show = !active || !panel || state().layers.decoration;
    mesh.visible = !item.deleted && !!show;
    mesh.position.set(item.x, item.y, item.z);
    mesh.scale.set(base.sx * item.scale, base.sy * item.scale, base.sz * item.scale);
    mesh.rotation.y = item.rotY * Math.PI / 180;
  });
}

function removeSelection() {
  const props = selection.filter(item => item.kind === 'prop').map(item => item.id);
  let next = Model.removeProps(session.current, props);
  const paths = selection.filter(item => item.kind === 'path').map(item => {
    const [x, z] = item.id.split(':').map(Number);
    return { x, z };
  });
  if (paths.length) next = Model.erasePaths(next, paths);
  selection.filter(item => item.kind === 'object').forEach(item => {
    const mesh = findObject(item.id);
    const current = next.objects.find(obj => obj.id === item.id) || (mesh ? objectDraft(mesh) : { id: item.id, x: 0, y: 0, z: 0, scale: 1, rotY: 0, deleted: false });
    next = Model.upsertObjects(next, [Object.assign({}, current, { deleted: true })]);
  });
  session.commit(next);
  selection = [];
  dirty = true;
  renderWorld();
}

function duplicateSelection() {
  const copies = selection.map(item => selectedProp() && item.kind === 'prop' ? session.current.props.find(prop => prop.id === item.id) : null).filter(Boolean).map(prop => Object.assign({}, prop, {
    id: Model.newId('v'), x: prop.x + 2, z: prop.z + 2,
  }));
  if (!copies.length) { note('Sólo se duplican los elementos colocados.'); return; }
  session.commit(Model.placeProps(session.current, copies));
  selection = copies.map(prop => ({ kind: 'prop', id: prop.id }));
  dirty = true;
  renderWorld();
}

function copySelection() {
  clipboard.props = selection.map(item => session.current.props.find(prop => prop.id === item.id)).filter(Boolean).map(prop => Object.assign({}, prop));
  clipboard.paths = selection.filter(item => item.kind === 'path').map(item => session.current.paths.find(path => path.id === item.id)).filter(Boolean).map(path => Object.assign({}, path));
  note('Copiado.');
}

function pasteSelection() {
  const props = clipboard.props.map(prop => Object.assign({}, prop, { id: Model.newId('v'), x: prop.x + 2, z: prop.z + 2 }));
  let next = props.length ? Model.placeProps(session.current, props) : session.current;
  if (clipboard.paths.length) {
    const cells = clipboard.paths.map(path => ({ x: path.x + 1, z: path.z }));
    next = cells.reduce((doc, cell, index) => Model.paintPaths(doc, [cell], clipboard.paths[index].style), next);
  }
  session.commit(next);
  dirty = true;
  renderWorld();
}

async function post(message) {
  const res = await fetch('/api/world-edits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(Object.assign({ baseVersion: version }, message)),
  });
  let data = {};
  try { data = await res.json(); } catch (e) { data = {}; }
  if (res.status === 403 || data.code === 403) {
    note('Sólo un administrador puede guardar.');
    return data;
  }
  if (res.status === 409 || data.code === 409) {
    note('El mundo cambió. Trae la versión del servidor y vuelve a intentar.');
    pending = data.worldEdits || pending;
    return data;
  }
  if (!res.ok || data.ok === false) {
    note(data.error || 'No se pudo guardar.');
    return data;
  }
  dirty = false;
  if (data.worldEdits) adopt(data.worldEdits, true);
  return data;
}

async function save() {
  if (!allowed) return;
  note('Guardando…');
  const data = await post({ op: 'replace', current: session.current });
  if (data && data.ok) note('Guardado. Versión ' + version + '.');
}

function pullServer() {
  if (!pending) return;
  dirty = false;
  adopt(pending, true);
  note('Trajiste la versión del servidor.');
}

async function onAction(name, extra) {
  extra = extra || {};
  if (name === 'collapse') {
    if (!panel) return;
    const folded = panel.el.classList.toggle('ed-colapsado');
    const toggle = panel.el.querySelector('#ed-colapsar');
    if (toggle) {
      toggle.textContent = folded ? 'Mostrar' : 'Ocultar';
      toggle.setAttribute('aria-expanded', folded ? 'false' : 'true');
    }
    return;
  }
  if (name === 'save' || name === 'exit') { if (name === 'save') save(); else leave(); return; }
  if (name === 'undo') { if (session.undo()) { dirty = true; renderWorld(); } return; }
  if (name === 'redo') { if (session.redo()) { dirty = true; renderWorld(); } return; }
  if (name === 'eyedropper') { arm = arm === 'pick' ? '' : 'pick'; note(arm ? 'Toca un elemento para copiar su estilo.' : 'Cuentagotas guardado.'); return; }
  if (name === 'box') { arm = arm === 'box' ? '' : 'box'; note(arm ? 'Arrastra un rectángulo.' : 'Caja guardada.'); return; }
  if (name === 'copy') { copySelection(); return; }
  if (name === 'paste') { pasteSelection(); return; }
  if (name === 'preview') { setPreview(!preview); return; }
  if (name === 'fly') { toggleFly(); return; }
  if (name === 'delete') { removeSelection(); return; }
  if (name === 'duplicate') { duplicateSelection(); return; }
  if (name === 'rot') { rotateBy(extra.delta || 0); return; }
  if (name === 'rot-set') { applyRot(extra.value, !!extra.live); return; }
  if (name === 'scale') { applyScale(extra.value, !!extra.live); return; }
  if (name === 'layers') { renderWorld(); return; }
  if (name === 'select-row') { selection = [{ kind: extra.kind, id: extra.id }]; placeSelection(); return; }
  if (name === 'save-design') {
    const data = await post({ op: 'save_design', name: extra.name || panel.designName() || 'Diseño', snapshot: session.current });
    if (data && data.ok) note('Diseño guardado.');
    return;
  }
  if (name === 'apply-design') { await post({ op: 'apply_design', id: extra.id }); note('Diseño aplicado.'); return; }
  if (name === 'duplicate-design') { await post({ op: 'duplicate_design', id: extra.id }); return; }
  if (name === 'export-design' || name === 'export-current') {
    if (name === 'export-current') {
      download({ kind: 'life-world-design', schema: 1, name: panel.designName() || 'capa', fromEnv: env, snapshot: session.current });
      return;
    }
    const data = await post({ op: 'export_design', id: extra.id });
    if (data && data.package) download(data.package);
    return;
  }
  if (name === 'file') {
    const file = extra.file;
    if (!file) return;
    const text = await file.text();
    try { pendingFile = JSON.parse(text); } catch (e) { note('Ese JSON no se pudo leer.'); return; }
    note('Archivo listo. Escribe PROMOVER y pulsa Importar.');
    return;
  }
  if (name === 'import') {
    if (!pendingFile) { note('Primero elige un archivo.'); return; }
    const data = await post({ op: 'import_design', confirm: extra.confirm, package: pendingFile, apply: true });
    if (data && data.ok) { pendingFile = null; note('Diseño importado al mundo ' + env + '.'); }
    return;
  }
  if (name === 'revert') {
    const data = await post({ op: 'revert', confirm: extra.confirm });
    if (data && data.ok) note('La capa volvió al mapa base. El mapa original no se tocó.');
    return;
  }
  if (name === 'rollback') {
    const data = await post({ op: 'rollback', version: extra.version });
    if (data && data.ok) note('Versión restaurada.');
    return;
  }
  if (name === 'seed') {
    const here = api ? api.playerTile() : { x: 10, y: 10 };
    const data = await post({ op: 'seed_preview', anchor: { x: Math.round(here.x), z: Math.round(here.y) } });
    if (data && data.ok) note('Muestra sembrada junto a ti.');
    return;
  }
  if (name === 'reset') {
    if (extra.confirm !== 'RESTABLECER') { note('Escribe RESTABLECER para vaciar las muestras.'); return; }
    const data = await post({ op: 'reset_preview', confirm: extra.confirm });
    if (data && data.ok) note('Muestras vaciadas.');
    return;
  }
}

let pendingFile = null;

function download(pack) {
  const blob = new Blob([JSON.stringify(pack, null, 1)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = (pack.name || 'diseno') + '.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

function toggleFly() {
  fly = !fly;
  if (!window.LIVE3D) return;
  window.LIVE3D.freeFly = fly;
  if (fly) {
    const here = api.playerTile();
    window.LIVE3D.freeFlyAt = new T.Vector3(here.x * 2 + 1, api.height(here.x, here.y) + 14, here.y * 2 + 1);
    note('Vuelo libre. WASD mueve, Q y E suben y bajan, Alt gira.');
  } else note('Cámara de juego.');
}

function flyStep(key, shift) {
  const at = window.LIVE3D && window.LIVE3D.freeFlyAt;
  if (!at) return;
  const yaw = (window.LIVE3D.camera && window.LIVE3D.camera.yaw) || 0;
  const step = shift ? 6 : 2.5;
  const sin = Math.sin(yaw);
  const cos = Math.cos(yaw);
  if (key === 'w' || key === 'arrowup') { at.x -= sin * step; at.z -= cos * step; }
  if (key === 's' || key === 'arrowdown') { at.x += sin * step; at.z += cos * step; }
  if (key === 'd' || key === 'arrowright') { at.x += cos * step; at.z -= sin * step; }
  if (key === 'a' || key === 'arrowleft') { at.x -= cos * step; at.z += sin * step; }
  if (key === 'q') at.y += step;
  if (key === 'e') at.y -= step;
}

addEventListener('keydown', (event) => {
  if (!active) return;
  const typing = document.activeElement && ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName);
  if (typing) return;
  const key = event.key.toLowerCase();
  if ((event.ctrlKey || event.metaKey) && key === 'z') { event.preventDefault(); event.stopImmediatePropagation(); if (session[event.shiftKey ? 'redo' : 'undo']()) { dirty = true; renderWorld(); } return; }
  if ((event.ctrlKey || event.metaKey) && key === 'y') { event.preventDefault(); event.stopImmediatePropagation(); if (session.redo()) { dirty = true; renderWorld(); } return; }
  if ((event.ctrlKey || event.metaKey) && key === 'c') { event.preventDefault(); event.stopImmediatePropagation(); copySelection(); return; }
  if ((event.ctrlKey || event.metaKey) && key === 'v') { event.preventDefault(); event.stopImmediatePropagation(); pasteSelection(); return; }
  if (key === 'escape') { event.preventDefault(); event.stopImmediatePropagation(); if (preview) setPreview(false); else if (fly) toggleFly(); else selection = []; placeSelection(); return; }
  if (key === 'delete' || key === 'backspace') { event.preventDefault(); event.stopImmediatePropagation(); removeSelection(); return; }
  if (fly && ['w', 'a', 's', 'd', 'q', 'e', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) {
    event.preventDefault(); event.stopImmediatePropagation(); flyStep(key, event.shiftKey); return;
  }
  if (['arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key) && selection.length && !event.shiftKey) {
    event.preventDefault(); event.stopImmediatePropagation();
    const dx = key === 'arrowright' ? 1 : key === 'arrowleft' ? -1 : 0;
    const dz = key === 'arrowdown' ? 1 : key === 'arrowup' ? -1 : 0;
    session.begin();
    nudgeSelection(dx, 0, dz, true);
    session.end();
  }
}, true);

new MutationObserver(() => ensureMenu()).observe(document.body, { childList: true, subtree: true });
refresh();
setInterval(() => { attach(); hookNet(); ensureMenu(); }, 400);

window.WorldEditor = {
  enter, leave, save, pullServer,
  get allowed() { return allowed; },
  get active() { return active; },
  get version() { return version; },
};
