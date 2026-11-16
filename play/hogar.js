/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Elige el municipio. Tu casa queda ahí. El ovni sólo corre en esa primera elección. */
(() => {
  'use strict';
  const data = window.HOGARES || { orden: [], casas: [] };
  const byId = Object.fromEntries((data.casas || []).map(item => [item.id, item]));
  const ORDEN = data.orden || [];
  const HOUSE = '<svg class="casa-ico" viewBox="0 0 32 32" aria-hidden="true"><path d="M5 15 L16 5 L27 15 V27 H5 Z" fill="#f4efe2"/><path d="M3 16 L16 3 L29 16" fill="#8d5a42"/><path d="M7 16 L16 8 L25 16 V27 H7 Z" fill="#f7f1e4"/><rect x="13.5" y="18" width="5" height="9" fill="#6b4228"/></svg>';

  function entryMode(justPicked) { return justPicked ? 'ovni' : 'heli'; }
  function casa(id) { return byId[String(id || '').toLowerCase()] || null; }
  function stand(id) {
    const item = casa(id);
    return item ? { x: item.x, y: item.y, name: item.name, id: item.id } : null;
  }
  function current() {
    return (window.SaimonSession && window.SaimonSession.municipio) || '';
  }

  function thumb(place) {
    const canvas = document.createElement('canvas');
    canvas.width = 72;
    canvas.height = 48;
    canvas.className = 'lugar-mini';
    const pen = canvas.getContext('2d');
    if (!pen) return canvas;
    pen.fillStyle = '#8ec4ea';
    pen.fillRect(0, 0, 72, 20);
    pen.fillStyle = place.id === 'las_palmas' ? '#2f6a34' : '#7eaa55';
    pen.fillRect(0, 20, 72, 28);
    pen.fillStyle = '#6b3e24';
    if (place.kind === 'poi' && place.id === 'las_palmas') {
      pen.fillRect(34, 18, 4, 22);
      pen.beginPath();
      pen.arc(36, 18, 10, 0, Math.PI * 2);
      pen.fill();
    } else {
      pen.beginPath();
      pen.moveTo(18, 30);
      pen.lineTo(36, 16);
      pen.lineTo(54, 30);
      pen.fill();
      pen.fillStyle = '#f7f1e4';
      pen.fillRect(24, 30, 24, 14);
    }
    return canvas;
  }

  let onChoose = null;
  function mountMenu() {
    const menu = document.getElementById('hud-gear-menu');
    if (!menu || document.getElementById('cajon-lugar')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.id = 'cajon-lugar';
    button.textContent = 'Dónde empezar';
    button.onclick = () => {
      menu.hidden = true;
      openPicker((id, remember) => {
        if (window.LiveInk && LiveInk.elegirLugar) LiveInk.elegirLugar(id, remember);
      }, true);
    };
    menu.append(button);
  }
  function openPicker(choose, inGame) {
    const root = document.getElementById('hogar');
    const list = document.getElementById('hogar-lista');
    if (!root || !list) return;
    onChoose = choose;
    const places = window.Lugares ? Lugares.catalog() : ORDEN.map(id => byId[id]).filter(Boolean);
    const fav = (window.SaimonSession && window.SaimonSession.favoritePlace) || '';
    list.replaceChildren();
    for (const item of places) {
      if (!item) continue;
      const row = document.createElement('div');
      row.className = 'lugar-fila';
      const b = document.createElement('button');
      b.type = 'button';
      b.dataset.municipio = item.id;
      b.append(thumb(item));
      const label = document.createElement('span');
      const star = item.id === fav ? '⭐ ' : '';
      label.innerHTML = '<b>' + star + item.name + '</b><small>' + (inGame ? 'Esta vez' : 'Empezar aquí') + '</small>';
      b.append(label);
      b.onclick = () => { if (onChoose) onChoose(item.id, !inGame); };
      row.append(b);
      if (inGame) {
        const mark = document.createElement('button');
        mark.type = 'button';
        mark.className = 'lugar-estrella';
        mark.textContent = 'Favorito';
        mark.setAttribute('aria-label', 'Marcar ' + item.name + ' como favorito');
        mark.onclick = () => { if (onChoose) onChoose(item.id, true); };
        row.append(mark);
      }
      list.append(row);
    }
    const close = document.getElementById('hogar-cerrar');
    if (close) close.hidden = !inGame;
    root.hidden = false;
    const first = list.querySelector('button');
    if (first) first.focus();
  }
  function closePicker() {
    const root = document.getElementById('hogar');
    if (root) root.hidden = true;
    onChoose = null;
  }

  function readLocal() {
    let layout = null;
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!key || key.indexOf('lifeinc.casa.v1:') !== 0) continue;
        const parsed = JSON.parse(localStorage.getItem(key) || 'null');
        if (parsed && Array.isArray(parsed.items)) { layout = parsed; break; }
      }
    } catch (e) { layout = null; }
    let items = [];
    try {
      const bag = JSON.parse(localStorage.getItem('lifeinc.eljardin.v3') || 'null');
      const box = bag && bag.vault && bag.vault.items;
      if (Array.isArray(box)) items = box;
      else if (box && typeof box === 'object') items = Object.keys(box).map(item => ({ item: item, qty: box[item] }));
    } catch (e) { items = []; }
    let pet = null;
    try { pet = JSON.parse(localStorage.getItem('lifeinc.mascota.v1') || 'null'); } catch (e) { pet = null; }
    return { layout: layout, items: items, pet: pet };
  }

  async function migrate(user) {
    if (!user || (user.casa && user.casa.migrated)) return user;
    const local = readLocal();
    const response = await fetch('/auth/casa', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ migrate: true, layout: local.layout, items: local.items, pet: local.pet }),
    });
    const result = await response.json();
    if (!response.ok || !result.user) return user;
    if (result.casa && result.casa.layout && window.Casa && Casa.apply) Casa.apply(result.casa.layout);
    return result.user;
  }

  const closer = document.getElementById('hogar-cerrar');
  if (closer) closer.onclick = () => closePicker();
  mountMenu();
  new MutationObserver(mountMenu).observe(document.body, { childList: true, subtree: true });

  window.Hogar = { ORDEN, entryMode, casa, stand, current, openPicker, closePicker, readLocal, migrate, mountMenu };
})();
