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

  let onChoose = null;
  function openPicker(choose) {
    const root = document.getElementById('hogar');
    const list = document.getElementById('hogar-lista');
    if (!root || !list) return;
    onChoose = choose;
    list.replaceChildren();
    for (const id of ORDEN) {
      const item = byId[id];
      if (!item) continue;
      const b = document.createElement('button');
      b.type = 'button';
      b.dataset.municipio = id;
      b.innerHTML = HOUSE + '<span><b>' + item.name + '</b><small>Tu casa</small></span>';
      b.onclick = () => { if (onChoose) onChoose(id); };
      list.append(b);
    }
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

  window.Hogar = { ORDEN, entryMode, casa, stand, current, openPicker, closePicker, readLocal, migrate };
})();
