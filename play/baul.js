/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Baúl de la mina: la misma cuenta que la casa y la Casa bancaria.
   Las cifras las manda el servidor. Aquí no se crean monedas ni objetos. */
(() => {
  'use strict';
  let last = null;
  let token = 1;
  let modo = '1';
  let montoTexto = '1';

  function esc(text) {
    return String(text == null ? '' : text).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }
  function panel() { return document.getElementById('baul-mina'); }
  function abierto() { const el = panel(); return !!(el && !el.hidden); }
  function online() {
    const S = window.LiveInk && LiveInk.state;
    const ws = S && S.net && S.net.ws;
    return !!(ws && ws.readyState === 1 && S.net.ok && !S.walletLocked);
  }
  function send(body) {
    const S = window.LiveInk && LiveInk.state;
    const ws = S && S.net && S.net.ws;
    if (!ws || ws.readyState !== 1) return false;
    ws.send(JSON.stringify(body));
    return true;
  }
  function vacio() {
    const cero = { exacto: '0 SMC', compacto: '0 SMC' };
    return {
      smc: { billetera: cero, baul: cero, total: cero, escala: 'Las cantidades se muestran en SMC.', topes: '', tope: '21.000.000 SMC' },
      filas: [],
      totales: { encima: 0, baul: 0, mineral: 0, recurso: 0 },
    };
  }
  function pedir() {
    if (!send({ t: 'baul' })) paint(last || vacio());
  }
  function open() {
    const el = panel();
    if (!el) return;
    el.hidden = false;
    const btn = document.getElementById('baul-abrir');
    if (btn) btn.hidden = true;
    pedir();
  }
  function close() {
    const el = panel();
    if (el) el.hidden = true;
  }
  function mover(op, item, qty) {
    if (!online()) return;
    const all = qty === 'all';
    if (!all && !(Number(qty) > 0)) return;
    send({ t: 'baul_mover', op: op, item: item || '', all: all, qty: all ? 'all' : qty, token: 'b' + (token++) });
  }
  function moverSmc(op, amount) {
    if (!online()) return;
    const all = amount === 'all';
    send({ t: 'baul_smc', op: op, all: all, amount: all ? 'all' : amount, token: 's' + (token++) });
  }
  function cantidadX() {
    const n = Math.floor(Number(String(montoTexto || '').replace(',', '.')) || 0);
    return n > 0 ? n : 0;
  }
  function dibujo(id) {
    const moneda = '<svg viewBox="0 0 64 64"><circle cx="32" cy="36" r="18" fill="#8a5a12"/><circle cx="32" cy="30" r="18" fill="#f0c14a" stroke="#6a4010" stroke-width="3"/><circle cx="32" cy="30" r="11" fill="none" stroke="#fff4cc" stroke-width="2"/><text x="32" y="36" text-anchor="middle" font-size="16" font-family="sans-serif" font-weight="700" fill="#5c3a08">S</text></svg>';
    const roca = (relleno, borde) => '<svg viewBox="0 0 64 64"><path d="M16 42 24 18h14l12 16 2 16H18z" fill="' + relleno + '" stroke="' + borde + '" stroke-width="3" stroke-linejoin="round"/></svg>';
    const barra = (relleno) => '<svg viewBox="0 0 64 64"><path d="M12 28h40l-6 16H18z" fill="' + relleno + '" stroke="#3a2410" stroke-width="3" stroke-linejoin="round"/></svg>';
    const saco = (relleno) => '<svg viewBox="0 0 64 64"><path d="M24 14h16l8 12v24H16V26z" fill="' + relleno + '" stroke="#3a2410" stroke-width="3" stroke-linejoin="round"/><path d="M24 14c4 6 12 6 16 0" fill="none" stroke="#3a2410" stroke-width="3"/></svg>';
    const tabla = {
      smc: moneda,
      mineral_oro: roca('#f0c14a', '#6a4010'),
      pepita_oro: roca('#ffe08a', '#6a4010'),
      mineral_plata: roca('#e4ebf2', '#4a5560'),
      mineral_cobre: roca('#d08a52', '#5a3018'),
      piedra: roca('#c2bbb0', '#4e493f'),
      mineral_piedra: roca('#c2bbb0', '#4e493f'),
      madera: '<svg viewBox="0 0 64 64"><rect x="14" y="16" width="36" height="32" rx="3" fill="#8a5a32" stroke="#4a2c14" stroke-width="3"/><path d="M22 16v32M32 16v32M42 16v32" stroke="#6a3e1c" stroke-width="2"/></svg>',
      lingote_oro: barra('#f0c14a'),
      lingote_plata: barra('#e4ebf2'),
      lingote_cobre: barra('#d08a52'),
      moneda_plata: '<svg viewBox="0 0 64 64"><circle cx="32" cy="34" r="16" fill="#9aa6b2"/><circle cx="32" cy="30" r="16" fill="#e8eef4" stroke="#5c6770" stroke-width="3"/><text x="32" y="36" text-anchor="middle" font-size="14" font-family="sans-serif" font-weight="700" fill="#3a4450">Ag</text></svg>',
      moneda_cobre: '<svg viewBox="0 0 64 64"><circle cx="32" cy="34" r="16" fill="#8a4a22"/><circle cx="32" cy="30" r="16" fill="#d08a52" stroke="#6a3014" stroke-width="3"/><text x="32" y="36" text-anchor="middle" font-size="14" font-family="sans-serif" font-weight="700" fill="#4a2410">Cu</text></svg>',
      bolsa_cafe: saco('#6f4e37'),
      bolsa_cacao: saco('#c4a574'),
    };
    return tabla[id] || saco('#6f8f55');
  }
  function cifra(texto) {
    return String(texto || '0').replace(/\s*SMC\s*$/i, '').trim() || '0';
  }
  function casilla(row) {
    const n = row.kind === 'smc' ? cifra(row.texto) : String(row.qty);
    const accion = row.lado === 'encima' ? 'Guardar' : 'Sacar';
    const nombre = row.kind === 'smc' ? 'Simoncoin' : row.name;
    return '<button type="button" class="casilla" data-lado="' + row.lado + '" data-kind="' + row.kind + '" data-item="' + esc(row.id) + '" aria-label="' + esc(accion + ' ' + nombre + ' ' + n) + '">'
      + '<span class="casilla-ico" aria-hidden="true">' + dibujo(row.id) + '</span>'
      + '<span class="casilla-n">' + esc(n) + '</span></button>';
  }
  function huecos(llenas) {
    const meta = Math.max(16, Math.ceil(llenas / 4) * 4);
    let html = '';
    for (let i = llenas; i < meta; i++) html += '<span class="casilla vacia" aria-hidden="true"></span>';
    return html;
  }
  function grupoDe(row) {
    if (row.kind === 'smc') return 'Simoncoin';
    const id = row.id || '';
    if (id.indexOf('mineral_') === 0 || id.indexOf('pepita_') === 0 || id === 'piedra') return 'Minerales';
    if (id.indexOf('lingote_') === 0) return 'Lingotes';
    if (id === 'moneda_plata' || id === 'moneda_cobre') return 'Monedas acuñadas';
    if (id === 'bolsa_cafe' || id === 'bolsa_cacao') return 'Cosechas';
    return 'Otros';
  }
  function lado(which, textoSmc, filas) {
    const celdas = [{ kind: 'smc', id: 'smc', name: 'Simoncoin', texto: textoSmc, lado: which }];
    for (const row of filas) {
      const qty = which === 'encima' ? row.encima : row.baul;
      if (qty > 0) celdas.push({ kind: 'item', id: row.id, name: row.name, qty: qty, lado: which });
    }
    const orden = ['Simoncoin', 'Minerales', 'Lingotes', 'Monedas acuñadas', 'Cosechas', 'Otros'];
    let html = '';
    orden.forEach((nombre) => {
      const grupo = celdas.filter((row) => grupoDe(row) === nombre);
      if (!grupo.length) return;
      html += '<p class="casilla-grupo">' + nombre + '</p>' + grupo.map(casilla).join('');
    });
    const titulo = which === 'encima' ? 'Encima' : 'Baúl';
    return '<section class="rejilla-lado"><h3>' + titulo + '</h3><div class="casillas">' + html + huecos(celdas.length) + '</div></section>';
  }
  function paint(view) {
    const root = document.getElementById('baul-cuerpo');
    if (!root) return;
    const data = view || vacio();
    last = data;
    const smc = data.smc || vacio().smc;
    const filas = data.filas || [];
    const totales = data.totales || {};
    const linked = online();
    const marca = (id) => (modo === id ? ' on' : '');
    root.innerHTML = ''
      + '<div class="rejilla-modo" role="group" aria-label="Cuánto mover">'
      + '<button type="button" class="baul-btn' + marca('1') + '" data-modo="1">1</button>'
      + '<button type="button" class="baul-btn' + marca('x') + '" data-modo="x">X</button>'
      + '<input id="baul-monto" inputmode="decimal" value="' + esc(montoTexto) + '" aria-label="Cantidad X" placeholder="1">'
      + '<button type="button" class="baul-btn' + marca('all') + '" data-modo="all">Todo</button>'
      + '</div>'
      + '<p class="baul-nota">Toca una casilla. 1 mueve una. X usa la cantidad. Todo guarda o saca todo. Encima se guarda en el baúl. El baúl vuelve a la mano.</p>'
      + '<div class="rejilla">'
      + lado('encima', smc.billetera && smc.billetera.exacto, filas)
      + lado('baul', smc.baul && smc.baul.exacto, filas)
      + '</div>'
      + '<p class="baul-exacto">En total ' + esc(smc.total && smc.total.exacto) + '. ' + esc(smc.escala || '') + ' Tope ' + esc(smc.tope || '') + '.</p>'
      + '<p class="baul-nota">' + esc(smc.topes || '') + '</p>'
      + '<p class="baul-nota">Encima ' + (totales.encima || 0) + ' · Baúl ' + (totales.baul || 0) + '. Guardar todo y Sacar todo no crean nada: el servidor cuenta lo que ya hay.</p>'
      + '<p class="baul-nota" id="baul-estado">' + (linked ? 'Conectado. Cada pase se guarda en la cuenta.' : 'Sin conexión. El servidor confirma cada pase.') + '</p>';
    const campo = document.getElementById('baul-monto');
    if (campo) campo.addEventListener('input', () => { montoTexto = campo.value; });
    root.querySelectorAll('[data-modo]').forEach((button) => {
      button.addEventListener('click', () => {
        modo = button.dataset.modo;
        root.querySelectorAll('[data-modo]').forEach((otro) => otro.classList.toggle('on', otro.dataset.modo === modo));
      });
    });
    root.querySelectorAll('.casilla[data-lado]').forEach((button) => {
      button.addEventListener('click', () => {
        if (!linked) return;
        const op = button.dataset.lado === 'encima' ? 'deposit' : 'withdraw';
        if (button.dataset.kind === 'smc') {
          const amount = modo === 'all' ? 'all' : (modo === 'x' ? montoTexto : '1');
          moverSmc(op, amount);
        } else {
          const qty = modo === 'all' ? 'all' : (modo === 'x' ? cantidadX() : 1);
          mover(op, button.dataset.item, qty);
        }
      });
    });
  }
  function aplicar(moved) {
    const ink = window.LiveInk;
    if (!ink || !moved) return;
    for (const row of moved) {
      const qty = Number(row.qty) || 0;
      if (qty < 1 || !row.item || row.item === 'smc') continue;
      if (row.op === 'deposit' && ink.takeItem) ink.takeItem(row.item, qty);
      if (row.op === 'withdraw' && ink.giveItem) ink.giveItem(row.item, qty);
    }
  }
  function onNet(message) {
    if (!message || message.t !== 'baul') return false;
    if (message.view) {
      paint(message.view);
      if (window.TradeUI && TradeUI.refrescar) TradeUI.refrescar();
    }
    if (message.moved) aplicar(message.moved);
    if (message.reason && window.LiveInk && LiveInk.say) LiveInk.say(message.reason, message.ok ? 'juego' : 'aviso');
    if (window.MiCuenta && MiCuenta.tocar) MiCuenta.tocar();
    return true;
  }
  function cerca() {
    const ink = window.LiveInk;
    const S = ink && ink.state;
    const world = ink && (typeof ink.world === 'function' ? ink.world() : ink.world);
    const here = (world && world.mapId) || 'city';
    if (!S || !world || (here !== 'mine' && here !== 'mina2') || !S.nodes || !S.nodes.get) return false;
    const node = S.nodes.get('baul_mina');
    if (!node || !node.def || !S.player) return false;
    return Math.max(Math.abs(S.player.x - node.def.x), Math.abs(S.player.y - node.def.y)) <= 2;
  }
  function pulso() {
    const btn = document.getElementById('baul-abrir');
    if (!btn) return;
    const show = cerca() && !abierto();
    btn.hidden = !show;
  }
  const abrir = document.getElementById('baul-abrir');
  if (abrir) abrir.addEventListener('click', open);
  setInterval(pulso, 400);
  function ultima() { return last; }
  window.Baul = { open, close, paint, pedir, onNet, abierto, cerca, ultima };
})();
