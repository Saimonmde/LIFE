/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Libro madre: acuñaciones únicas. Simulación educativa, sin valor real. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  let toastTimer = 0;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function panel() { return $('#w-libro-madre'); }
  function open(focusId) {
    const el = panel();
    if (!el) return;
    el.hidden = false;
    if (window.Paneles) Paneles.scan();
    load(focusId);
  }
  function card(block) {
    const id = block.id || '';
    const ok = block.verificado !== false;
    const who = block.miner || block.owner || block.from || '—';
    const where = block.location || '—';
    const amount = block.amountText || ((block.amountSmh || 0) + ' SMH');
    const hash = block.hash || '';
    return `<article class="madre-card" data-id="${esc(id)}">
      <header><span class="codigo">${esc(id)}</span> <span class="ok">${ok ? '✓ verificado' : '✗ no verifica'}</span></header>
      <div>${esc(who)} · ${esc(where)}</div>
      <div class="smc">${esc(amount)}</div>
      <div class="hash codigo-largo">${esc(hash)}</div>
      <button type="button" data-ver="${esc(id)}">Ver registro</button>
    </article>`;
  }
  async function load(focusId) {
    const body = $('#libro-madre-cuerpo');
    if (!body) return;
    body.innerHTML = '<p class="madre-aviso">Cargando el libro madre…</p>';
    let page = null;
    try {
      const res = await fetch('/api/libro?limite=12');
      if (res.ok) page = await res.json();
    } catch (e) { page = null; }
    if (!page) {
      body.innerHTML = '<p class="madre-aviso">El libro madre vive en el servidor. Ábrelo desde la partida en línea. Es una simulación: las SMC no son dinero real.</p>';
      return;
    }
    const blocks = page.blocks || [];
    body.innerHTML = `<p class="madre-aviso">${esc(page.disclaimer || '')}</p>
      <p>Altura ${page.height || 0} · emitidas <span class="smc">${esc(String(page.supply))}</span> · tope <span class="smc">${Number(page.maxSupply || 0).toLocaleString('es-CO')} SMC</span>. <span class="smc">1 SMC = 100.000.000 SMH</span>.</p>
      <button type="button" id="madre-verificar">Verificar la cadena</button>
      <p id="madre-estado" role="status"></p>
      ${blocks.map(card).join('') || '<p>Todavía no hay acuñaciones.</p>'}`;
    const check = $('#madre-verificar');
    if (check) check.onclick = async () => {
      const estado = $('#madre-estado');
      try {
        const res = await fetch('/api/libro/verificar');
        const data = await res.json();
        if (estado) estado.textContent = data.ok ? `Cadena válida. ${data.mensaje}` : `La cadena no verifica: ${data.mensaje}`;
      } catch (e) {
        if (estado) estado.textContent = 'No se pudo verificar.';
      }
    };
    body.querySelectorAll('[data-ver]').forEach((btn) => {
      btn.onclick = () => { window.open('/api/libro/' + encodeURIComponent(btn.dataset.ver), '_blank', 'noopener'); };
    });
    if (focusId) {
      const found = body.querySelector(`[data-id="${CSS.escape(focusId)}"]`);
      if (found) { found.classList.add('brilla'); found.scrollIntoView({ block: 'nearest' }); }
    }
  }
  function toast(record) {
    const el = $('#libro-toast');
    if (!el || !record || !record.id) return;
    el.hidden = false;
    el.innerHTML = `<strong>Acuñaste <span class="codigo">${esc(record.id)}</span></strong><span><span class="smc">${esc(record.amountText || ((record.amountSmh || 0) + ' SMH'))}</span>. Simulación, sin valor real.</span><button type="button">Ver el registro</button>`;
    el.querySelector('button').onclick = () => open(record.id);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, 8000);
  }
  function wire() {
    const desk = $('#b-libro-madre');
    const mob = $('#b-libro-madre-movil');
    if (desk) desk.onclick = () => open();
    if (mob) mob.onclick = () => open();
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && panel()) panel().hidden = true;
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
  window.LibroMadre = { open, toast };
})();
