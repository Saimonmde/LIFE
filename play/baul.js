/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Baúl de la mina: la misma cuenta que la casa y la Casa bancaria.
   Las cifras las manda el servidor. Aquí no se crean monedas ni objetos.
   Cada casilla abre una ficha. Guardar y Sacar usan los mensajes que ya existían. */
(() => {
  'use strict';
  let last = null;
  let token = 1;
  let montoTexto = '';
  let seleccion = null;
  let fichaAbierta = false;
  let aviso = '';

  /* Un solo mapa: nombre y para qué sirve cada objeto que el baúl dibuja. */
  const FICHAS = {
    smc: {
      name: 'Simoncoin',
      desc: 'La moneda de Saimon City. Encima está en la billetera y en el baúl está guardada. Moverla no crea ni gasta monedas.',
    },
    mineral_oro: {
      name: 'Mineral de oro',
      desc: 'Se saca picando en las minas. Se funde en el horno para acuñar Simoncoins a 0,1 SMC cada uno.',
    },
    pepita_oro: {
      name: 'Pepita de oro',
      desc: 'Oro del río, lavado con la batea. Se funde en el horno para acuñar Simoncoins a 0,1 SMC cada uno.',
    },
    mineral_plata: {
      name: 'Mineral de plata',
      desc: 'Se saca picando en las minas. Se funde en el horno para acuñar Simoncoins a 0,01 SMC cada uno.',
    },
    mineral_cobre: {
      name: 'Mineral de cobre',
      desc: 'Se saca picando en las minas; se funde en el horno para acuñar Simoncoins a 0,001 SMC.',
    },
    piedra: {
      name: 'Piedra',
      desc: 'Roca suelta. Sirve de material y se guarda en el baúl para no llenar lo que llevas encima.',
    },
    mineral_piedra: {
      name: 'Mineral de piedra',
      desc: 'Piedra de la mina. Sirve de material y se guarda en el baúl para no llenar lo que llevas encima.',
    },
    madera: {
      name: 'Madera',
      desc: 'Tronco cortado. Sirve de material y se guarda en el baúl para no llenar lo que llevas encima.',
    },
    lingote_oro: {
      name: 'Lingote de oro',
      desc: 'Barra de oro fundida en el Banco Central. No es Simoncoin; se guarda en el baúl.',
    },
    lingote_plata: {
      name: 'Lingote de plata',
      desc: 'Barra de plata fundida en el Banco Central. No es Simoncoin; se guarda en el baúl.',
    },
    lingote_cobre: {
      name: 'Lingote de cobre',
      desc: 'Barra de cobre fundida en el Banco Central. No es Simoncoin; se guarda en el baúl.',
    },
    bolsa_cafe: {
      name: 'Bolsa de café',
      desc: 'Cosecha de la finca. El baúl la mueve entre la mochila y el banco sin copiarla.',
    },
    bolsa_cacao: {
      name: 'Bolsa de cacao',
      desc: 'Cosecha de la finca. El baúl la mueve entre la mochila y el banco sin copiarla.',
    },
  };

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
    fichaAbierta = false;
  }
  function mover(op, item, qty) {
    if (!online()) return false;
    const all = qty === 'all';
    if (!all && !(Number(qty) > 0)) return false;
    return send({ t: 'baul_mover', op: op, item: item || '', all: all, qty: all ? 'all' : qty, token: 'b' + (token++) });
  }
  function moverSmc(op, amount) {
    if (!online()) return false;
    const all = amount === 'all';
    return send({ t: 'baul_smc', op: op, all: all, amount: all ? 'all' : amount, token: 's' + (token++) });
  }
  function infoDe(id, nombre) {
    if (FICHAS[id]) return FICHAS[id];
    const name = String(nombre || id || 'Objeto').trim() || 'Objeto';
    return { name: name, desc: 'Objeto de tu cuenta. Puedes llevarlo encima o guardarlo en el baúl.' };
  }
  function leerCentavos(texto, servidor) {
    let raw = String(texto == null ? '' : texto).replace(/\s*smc\s*$/i, '').trim().replace(/\s/g, '');
    if (!raw || raw === '-') return null;
    let neg = false;
    if (raw[0] === '-') { neg = true; raw = raw.slice(1); }
    const commas = (raw.match(/,/g) || []).length;
    const dots = (raw.match(/\./g) || []).length;
    let whole = raw;
    let frac = '';
    if (commas && dots) {
      if (raw.lastIndexOf(',') > raw.lastIndexOf('.')) {
        whole = raw.replace(/\./g, '').split(',')[0];
        frac = raw.split(',').pop() || '';
      } else {
        whole = raw.replace(/,/g, '').split('.')[0];
        frac = raw.split('.').pop() || '';
      }
    } else if (commas) {
      const parts = raw.split(',');
      if (commas > 1 && parts.slice(1).every((p) => p.length === 3)) whole = parts.join('');
      else if (commas === 1) { whole = parts[0] || '0'; frac = parts[1]; }
      else return null;
    } else if (dots > 1) {
      const parts = raw.split('.');
      if (!parts.slice(1).every((p) => p.length === 3)) return null;
      whole = parts.join('');
    } else if (dots === 1) {
      const parts = raw.split('.');
      if (servidor && parts[1].length === 3) whole = parts.join('');
      else { whole = parts[0] || '0'; frac = parts[1]; }
    }
    if (!/^\d+$/.test(whole || '0')) return null;
    if (frac && !/^\d+$/.test(frac)) return null;
    if (frac.length > 2) return null;
    const cents = Number(whole || '0') * 100 + Number((frac + '00').slice(0, 2));
    if (!Number.isFinite(cents)) return null;
    return neg ? -cents : cents;
  }
  function textoSmc(cents) {
    cents = Math.round(Number(cents) || 0);
    const neg = cents < 0;
    const v = Math.abs(cents);
    const frac = String(v % 100).padStart(2, '0');
    const whole = String(Math.floor(v / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return (neg ? '-' : '') + whole + ',' + frac + ' SMC';
  }
  function pedidoEntero(texto) {
    const raw = String(texto || '').trim();
    if (!/^\d+$/.test(raw)) return null;
    const n = Number(raw);
    if (!Number.isFinite(n) || n < 1) return null;
    return n;
  }
  function pedidoDe(cant, smc) {
    if (cant === 'all') return 'all';
    if (cant === 'x') return smc ? leerCentavos(montoTexto, false) : pedidoEntero(montoTexto);
    const n = Number(cant);
    if (!(n > 0)) return null;
    return smc ? n * 100 : n;
  }
  function cabe(pedido, disponible) {
    if (pedido === 'all') return disponible >= 1;
    return pedido != null && pedido > 0 && pedido <= disponible;
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
      bolsa_cafe: saco('#6f4e37'),
      bolsa_cacao: saco('#c4a574'),
    };
    return tabla[id] || saco('#6f8f55');
  }
  function cifra(texto) {
    return String(texto || '0').replace(/\s*SMC\s*$/i, '').trim() || '0';
  }
  function celdasDe(which, textoSmcLado, filas) {
    const celdas = [{ kind: 'smc', id: 'smc', name: 'Simoncoin', texto: textoSmcLado, lado: which }];
    for (const row of filas || []) {
      const qty = which === 'encima' ? row.encima : row.baul;
      if (qty > 0) celdas.push({ kind: 'item', id: row.id, name: row.name, qty: qty, lado: which });
    }
    return celdas;
  }
  function casilla(row) {
    const info = infoDe(row.id, row.name);
    const n = row.kind === 'smc' ? cifra(row.texto) : String(row.qty);
    const donde = row.lado === 'encima' ? 'encima' : 'en el baúl';
    const sel = seleccion && seleccion.lado === row.lado && seleccion.id === row.id;
    return '<button type="button" class="casilla' + (sel ? ' sel' : '') + '" data-lado="' + row.lado + '" data-kind="' + row.kind + '" data-item="' + esc(row.id) + '" data-nombre="' + esc(info.name) + '" title="' + esc(info.name) + '" aria-selected="' + (sel ? 'true' : 'false') + '" aria-label="' + esc(info.name + ', ' + n + ' ' + donde) + '">'
      + '<span class="casilla-ico" aria-hidden="true">' + dibujo(row.id) + '</span>'
      + '<span class="casilla-n">' + esc(n) + '</span></button>';
  }
  function huecos(llenas) {
    const meta = Math.max(16, Math.ceil(llenas / 4) * 4);
    let html = '';
    for (let i = llenas; i < meta; i++) html += '<span class="casilla vacia" aria-hidden="true"></span>';
    return html;
  }
  function lado(which, textoSmcLado, filas) {
    const celdas = celdasDe(which, textoSmcLado, filas);
    const titulo = which === 'encima' ? 'Encima' : 'Baúl';
    return '<section class="rejilla-lado"><h3>' + titulo + '</h3><div class="casillas">' + celdas.map(casilla).join('') + huecos(celdas.length) + '</div></section>';
  }
  function celdaActual(data) {
    if (!seleccion) return null;
    const smc = data.smc || {};
    const texto = seleccion.lado === 'encima' ? (smc.billetera && smc.billetera.exacto) : (smc.baul && smc.baul.exacto);
    const celdas = celdasDe(seleccion.lado, texto, data.filas);
    return celdas.find((row) => row.id === seleccion.id) || null;
  }
  function montos(data, celda) {
    if (celda.kind === 'smc') {
      const smc = data.smc || {};
      const encima = leerCentavos(smc.billetera && smc.billetera.exacto, true) || 0;
      const enBaul = leerCentavos(smc.baul && smc.baul.exacto, true) || 0;
      return {
        encima: textoSmc(encima),
        baul: textoSmc(enBaul),
        disponible: celda.lado === 'encima' ? encima : enBaul,
        smc: true,
      };
    }
    const fila = (data.filas || []).find((row) => row && row.id === celda.id) || {};
    const encima = Math.max(0, Number(fila.encima) || 0);
    const enBaul = Math.max(0, Number(fila.baul) || 0);
    const propio = Math.max(0, Number(celda.qty) || 0);
    return {
      encima: String(encima),
      baul: String(enBaul),
      disponible: celda.lado === 'encima' ? (fila.encima == null ? propio : encima) : (fila.baul == null ? propio : enBaul),
      smc: false,
    };
  }
  function botonCantidad(cant, verbo, activo, visible) {
    return '<button type="button" class="baul-btn" data-cant="' + cant + '" aria-label="' + esc(verbo + ' ' + visible) + '"' + (activo ? '' : ' disabled') + '>' + esc(visible) + '</button>';
  }
  function fichaHtml(data, celda) {
    const info = infoDe(celda.id, celda.name);
    const n = montos(data, celda);
    const verbo = celda.lado === 'encima' ? 'Guardar' : 'Sacar';
    const pedidoX = pedidoDe('x', n.smc);
    const xActivo = cabe(pedidoX, n.disponible);
    return '<article class="baul-ficha" role="dialog" aria-modal="true" aria-labelledby="baul-ficha-nombre">'
      + '<button type="button" class="baul-ficha-x" aria-label="Cerrar">✕</button>'
      + '<div class="baul-ficha-cuerpo">'
      + '<div class="baul-ficha-ico" aria-hidden="true">' + dibujo(celda.id) + '</div>'
      + '<h3 id="baul-ficha-nombre">' + esc(info.name) + '</h3>'
      + '<p class="baul-ficha-desc">' + esc(info.desc) + '</p>'
      + '<p class="baul-ficha-cant"><span class="' + (celda.lado === 'encima' ? 'aqui' : '') + '">Encima <b>' + esc(n.encima) + '</b></span><span class="' + (celda.lado === 'baul' ? 'aqui' : '') + '">Baúl <b>' + esc(n.baul) + '</b></span></p>'
      + '<p class="baul-ficha-error" role="status">' + esc(aviso) + '</p>'
      + '<div class="baul-ficha-mover" role="group" aria-label="' + verbo + '">'
      + '<span class="baul-ficha-op">' + verbo + '</span>'
      + botonCantidad('1', verbo, cabe(pedidoDe('1', n.smc), n.disponible), '1')
      + botonCantidad('10', verbo, cabe(pedidoDe('10', n.smc), n.disponible), '10')
      + botonCantidad('100', verbo, cabe(pedidoDe('100', n.smc), n.disponible), '100')
      + '<input id="baul-ficha-monto" inputmode="decimal" autocomplete="off" aria-label="Cantidad X" placeholder="Cantidad" value="' + esc(montoTexto) + '">'
      + botonCantidad('x', verbo, xActivo, 'X')
      + botonCantidad('all', verbo, cabe('all', n.disponible), 'Todo')
      + '</div>'
      + '</div></article>';
  }
  function paint(view) {
    const root = document.getElementById('baul-cuerpo');
    if (!root) return;
    const data = view || vacio();
    last = data;
    const celda = celdaActual(data);
    if (!celda) { seleccion = null; fichaAbierta = false; }
    const el = panel();
    if (el) el.classList.toggle('con-ficha', !!(celda && fichaAbierta));
    const smc = data.smc || vacio().smc;
    const filas = data.filas || [];
    const totales = data.totales || {};
    const linked = online();
    root.innerHTML = ''
      + '<p class="baul-nota">Toca una casilla para ver qué es. En la ficha, Guardar pasa de Encima al baúl y Sacar lo devuelve a la mano.</p>'
      + '<div class="rejilla">'
      + lado('encima', smc.billetera && smc.billetera.exacto, filas)
      + lado('baul', smc.baul && smc.baul.exacto, filas)
      + '</div>'
      + (celda && fichaAbierta ? fichaHtml(data, celda) : '')
      + '<p class="baul-exacto">En total ' + esc(smc.total && smc.total.exacto) + '. ' + esc(smc.escala || '') + ' Tope ' + esc(smc.tope || '') + '.</p>'
      + '<p class="baul-nota">' + esc(smc.topes || '') + '</p>'
      + '<p class="baul-nota">Encima ' + (totales.encima || 0) + ' · Baúl ' + (totales.baul || 0) + '. Guardar todo y Sacar todo no crean nada: el servidor cuenta lo que ya hay.</p>'
      + '<p class="baul-nota" id="baul-estado">' + (linked ? 'Conectado. Cada pase se guarda en la cuenta.' : 'Sin conexión. El servidor confirma cada pase.') + '</p>';
    root.querySelectorAll('.casilla[data-lado]').forEach((button) => {
      button.addEventListener('click', () => {
        seleccion = { lado: button.dataset.lado, id: button.dataset.item };
        fichaAbierta = true;
        aviso = '';
        paint(last);
      });
    });
    const cerrar = root.querySelector('.baul-ficha-x');
    if (cerrar) cerrar.addEventListener('click', () => cerrarFicha());
    const campo = document.getElementById('baul-ficha-monto');
    const viva = celda && fichaAbierta ? celda : null;
    if (campo && viva) {
      campo.addEventListener('input', () => {
        montoTexto = campo.value;
        const x = root.querySelector('[data-cant="x"]');
        if (x) x.disabled = !cabe(pedidoDe('x', viva.kind === 'smc'), montos(last, viva).disponible);
      });
    }
    root.querySelectorAll('[data-cant]').forEach((button) => {
      button.addEventListener('click', () => {
        if (button.disabled || !viva) return;
        const actual = document.getElementById('baul-ficha-monto');
        if (actual) montoTexto = actual.value;
        const n = montos(last, viva);
        if (!cabe(pedidoDe(button.dataset.cant, n.smc), n.disponible)) return;
        if (!online()) {
          aviso = 'Sin conexión. El servidor confirma cada pase.';
          paint(last);
          return;
        }
        aviso = '';
        const op = viva.lado === 'encima' ? 'deposit' : 'withdraw';
        let ok = false;
        if (n.smc) {
          const amount = button.dataset.cant === 'all' ? 'all' : (button.dataset.cant === 'x' ? String(montoTexto || '').trim() : String(button.dataset.cant));
          ok = moverSmc(op, amount);
        } else {
          const qty = button.dataset.cant === 'all' ? 'all' : (button.dataset.cant === 'x' ? pedidoEntero(montoTexto) : Number(button.dataset.cant));
          ok = mover(op, viva.id, qty);
        }
        if (!ok) {
          aviso = 'Sin conexión. El servidor confirma cada pase.';
          paint(last);
        }
      });
    });
  }
  function cerrarFicha() {
    if (!fichaAbierta) return;
    fichaAbierta = false;
    aviso = '';
    paint(last || vacio());
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
    if (message.reason && !message.ok) aviso = String(message.reason);
    else if (message.ok) aviso = '';
    if (message.view) {
      paint(message.view);
      if (window.TradeUI && TradeUI.refrescar) TradeUI.refrescar();
    }
    if (message.moved) aplicar(message.moved);
    if (message.reason && window.LiveInk && LiveInk.say) LiveInk.say(message.reason, message.ok ? 'juego' : 'aviso');
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
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !fichaAbierta || !abierto()) return;
    cerrarFicha();
    event.preventDefault();
    event.stopPropagation();
  }, true);
  document.addEventListener('pointerdown', (event) => {
    if (!fichaAbierta || !abierto()) return;
    if (event.button && event.button !== 0) return;
    const objetivo = event.target;
    if (!objetivo || !objetivo.closest) return;
    if (objetivo.closest('.baul-ficha')) return;
    if (objetivo.closest('.casilla[data-lado]')) return;
    cerrarFicha();
  }, true);
  const abrir = document.getElementById('baul-abrir');
  if (abrir) abrir.addEventListener('click', open);
  setInterval(pulso, 400);
  function ultima() { return last; }
  window.Baul = { open, close, paint, pedir, onNet, abierto, cerca, ultima };
})();
