/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Baúl: la misma cuenta en la casa, el Banco Central, la Casa bancaria y las minas.
   Las cifras las manda el servidor. Aquí no se crean monedas ni objetos. */
(() => {
  'use strict';
  let last = null;
  let token = 1;
  let montoTexto = '1';
  let sel = null;
  let aviso = '';

  const FICHAS = {
    smc: {
      nombre: 'Simoncoin',
      texto: 'Moneda del valle. Se guarda en el baúl o se lleva encima. Moverla no acuña ni crea monedas.',
    },
    mineral_oro: {
      nombre: 'Mineral de oro',
      texto: 'Se saca picando vetas de oro en las minas. Se funde en el horno para acuñar Simoncoins a 0,1 SMC.',
    },
    pepita_oro: {
      nombre: 'Pepita de oro',
      texto: 'Se lava en la arena de oro del río. Se funde en el horno para acuñar Simoncoins.',
    },
    mineral_plata: {
      nombre: 'Mineral de plata',
      texto: 'Se saca picando vetas de plata en las minas. Se funde en el horno para acuñar Simoncoins a 0,01 SMC. Cuatro piezas hacen una moneda de plata, que se guarda en el inventario.',
    },
    mineral_cobre: {
      nombre: 'Mineral de cobre',
      texto: 'Se saca picando en las minas. Se funde en el horno para acuñar Simoncoins a 0,001 SMC. Tres piezas hacen una moneda de cobre, que se guarda en el inventario.',
    },
    moneda_plata: {
      nombre: 'Moneda de plata',
      texto: 'Moneda de plata acuñada. Se guarda, se cambia o se suelta. No es Simoncoin.',
    },
    moneda_cobre: {
      nombre: 'Moneda de cobre',
      texto: 'Moneda de cobre acuñada. Se guarda, se cambia o se suelta. No es Simoncoin.',
    },
    piedra: {
      nombre: 'Piedra',
      texto: 'Se pica de las rocas claras. Sirve para construir y para los oficios. No se acuña.',
    },
    mineral_piedra: {
      nombre: 'Piedra',
      texto: 'Se pica de las rocas claras. Sirve para construir y para los oficios. No se acuña.',
    },
    madera: {
      nombre: 'Madera',
      texto: 'Se tala de los pinos. Sirve para construir y para los oficios.',
    },
    lingote_oro: {
      nombre: 'Lingote de oro',
      texto: 'Barra de oro ya fundida. Se guarda en el baúl. No es una moneda.',
    },
    lingote_plata: {
      nombre: 'Lingote de plata',
      texto: 'Barra de plata ya fundida. Se guarda en el baúl. No es una moneda.',
    },
    lingote_cobre: {
      nombre: 'Lingote de cobre',
      texto: 'Barra de cobre ya fundida. Se guarda en el baúl. No es una moneda.',
    },
    bolsa_cafe: {
      nombre: 'Café',
      texto: 'Bulto de la finca. Se guarda con la cosecha, sin copiarlo a otro depósito.',
    },
    bolsa_cacao: {
      nombre: 'Cacao',
      texto: 'Bulto de la finca. Se guarda con la cosecha, sin copiarlo a otro depósito.',
    },
    carne: { nombre: 'Carne', texto: 'Se obtiene al cazar. Se guarda en el baúl o se lleva encima.' },
    piel: { nombre: 'Piel', texto: 'Se obtiene al cazar. Se guarda en el baúl o se lleva encima.' },
    pluma: { nombre: 'Pluma', texto: 'Se obtiene al cazar. Se guarda en el baúl o se lleva encima.' },
    mango: { nombre: 'Mango', texto: 'Fruta del valle. Se recoge de los árboles y se puede guardar en el baúl.' },
    banano: { nombre: 'Banano', texto: 'Fruta del valle. Se recoge de los árboles y se puede guardar en el baúl.' },
    coco: { nombre: 'Coco', texto: 'Fruta del valle. Se recoge de los árboles y se puede guardar en el baúl.' },
    manzana: { nombre: 'Manzana', texto: 'Fruta del valle. Se recoge de los árboles y se puede guardar en el baúl.' },
    pera: { nombre: 'Pera', texto: 'Fruta del valle. Se recoge de los árboles y se puede guardar en el baúl.' },
    naranja: { nombre: 'Naranja', texto: 'Fruta del valle. Se recoge de los árboles y se puede guardar en el baúl.' },
    trucha: { nombre: 'Trucha', texto: 'Pez del río. Se pesca con la red y se puede guardar en el baúl.' },
    bocachico: { nombre: 'Bocachico', texto: 'Pez del río. Se pesca con la red y se puede guardar en el baúl.' },
    mojarra: { nombre: 'Mojarra', texto: 'Pez del río. Se pesca con la red y se puede guardar en el baúl.' },
  };

  function fichaDe(id, nombre) {
    if (FICHAS[id]) return FICHAS[id];
    return {
      nombre: nombre || 'Objeto',
      texto: 'Objeto del valle. Se guarda en el baúl o se lleva encima.',
    };
  }

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
    const titulo = document.getElementById('baul-titulo');
    if (titulo) titulo.textContent = 'Baúl';
    el.hidden = false;
    const btn = document.getElementById('baul-abrir');
    if (btn) btn.hidden = true;
    pedir();
  }
  function cerrarFicha() {
    sel = null;
    paint(last || vacio());
  }
  function close() {
    sel = null;
    const el = panel();
    if (el) el.hidden = true;
    const ficha = document.getElementById('baul-ficha');
    if (ficha && ficha.parentNode) ficha.parentNode.removeChild(ficha);
  }
  function mensaje(op, kind, item, cant) {
    if (kind === 'smc') {
      const all = cant === 'all';
      return { t: 'baul_smc', op: op, all: all, amount: all ? 'all' : String(cant) };
    }
    const all = cant === 'all';
    return { t: 'baul_mover', op: op, item: item || '', all: all, qty: all ? 'all' : cant };
  }
  function mover(op, item, qty) {
    if (!online()) return;
    const all = qty === 'all';
    if (!all && !(Number(qty) > 0)) return;
    const body = mensaje(op, 'item', item, all ? 'all' : qty);
    body.token = 'b' + (token++);
    send(body);
  }
  function moverSmc(op, amount) {
    if (!online()) return;
    const all = amount === 'all';
    const body = mensaje(op, 'smc', 'smc', all ? 'all' : amount);
    body.token = 's' + (token++);
    send(body);
  }
  function centimos(texto) {
    let raw = String(texto || '').replace(/\s*SMC\s*$/i, '').trim();
    if (!raw) return 0;
    if (raw.indexOf(',') >= 0 && raw.indexOf('.') >= 0) {
      if (raw.lastIndexOf(',') > raw.lastIndexOf('.')) raw = raw.replace(/\./g, '').replace(',', '.');
      else raw = raw.replace(/,/g, '');
    } else if (raw.indexOf(',') >= 0) raw = raw.replace(',', '.');
    const n = Number(raw);
    if (!isFinite(n) || n < 0) return 0;
    return Math.round(n * 100);
  }
  function smcNumero(texto) {
    return centimos(texto) / 100;
  }
  function entero(texto) {
    const raw = String(texto || '').trim().replace(',', '.');
    if (!/^\d+$/.test(raw)) return 0;
    const n = Number(raw);
    return n > 0 ? n : 0;
  }
  function seSuelta(id) {
    return ['smc', 'simoncoin', 'moneda_oro', 'sai'].indexOf(id) < 0;
  }
  function botonesBotar(have) {
    const pedido = entero(montoTexto);
    return [
      { cant: '1', texto: '1', off: !(have >= 1) },
      { cant: '10', texto: '10', off: !(have >= 10) },
      { cant: 'x', texto: 'X', off: !(pedido >= 1 && pedido <= have) },
      { cant: 'all', texto: 'Todo', off: !(have >= 1) },
    ];
  }
  function juntoHorno() {
    const ink = window.LiveInk;
    const S = ink && ink.state;
    const world = ink && (typeof ink.world === 'function' ? ink.world() : ink.world);
    const here = (world && world.mapId) || 'city';
    if (!S || !S.player || !S.nodes || (here !== 'mine' && here !== 'mina2')) return false;
    let near = false;
    S.nodes.forEach((node) => {
      const d = node && node.def;
      if (!d || d.type !== 'furnace') return;
      if (Math.max(Math.abs(S.player.x - d.x), Math.abs(S.player.y - d.y)) <= 1) near = true;
    });
    return near;
  }
  function irAlHorno() {
    const ink = window.LiveInk;
    if (!ink) return false;
    const world = typeof ink.world === 'function' ? ink.world() : ink.world;
    const here = (world && world.mapId) || 'city';
    const S = ink.state;
    cerrarFicha();
    if ((here === 'mine' || here === 'mina2') && S && S.nodes && ink.goTo) {
      let furnace = null;
      S.nodes.forEach((node) => { if (node.def && node.def.type === 'furnace') furnace = node; });
      if (furnace) { ink.goTo(furnace.def.x, furnace.def.y + 1); return true; }
    }
    if (ink.goMine) { ink.goMine(); return true; }
    if (ink.askTravel) { ink.askTravel('mina'); return true; }
    return false;
  }
  function botones(disponible, moneda, textoX) {
    const have = Number(disponible) || 0;
    function cabe(n) {
      if (!(n > 0)) return false;
      if (moneda) return Math.round(n * 100) <= Math.round(have * 100);
      return n <= have;
    }
    const pedido = moneda ? smcNumero(textoX) : entero(textoX);
    return [
      { cant: '1', texto: '1', off: !cabe(1) },
      { cant: '10', texto: '10', off: !cabe(10) },
      { cant: '100', texto: '100', off: !cabe(100) },
      { cant: 'x', texto: 'X', off: !cabe(pedido) },
      { cant: 'all', texto: 'Todo', off: !(have > 0) },
    ];
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
    const info = fichaDe(row.id, row.name);
    const nombre = info.nombre;
    const on = sel && sel.lado === row.lado && sel.id === row.id;
    return '<button type="button" class="casilla' + (on ? ' sel' : '') + '" data-lado="' + row.lado + '" data-kind="' + row.kind + '" data-item="' + esc(row.id) + '" data-nombre="' + esc(nombre) + '" aria-pressed="' + (on ? 'true' : 'false') + '" aria-label="' + esc(nombre + ' ' + n) + '">'
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
  function carta(data) {
    if (!sel) return '';
    const smc = data.smc || vacio().smc;
    const filas = data.filas || [];
    const encimaSmc = (smc.billetera && smc.billetera.exacto) || '0 SMC';
    const baulSmc = (smc.baul && smc.baul.exacto) || '0 SMC';
    let encima = 0;
    let enBaul = 0;
    let nombreSrv = '';
    if (sel.kind === 'smc') {
      encima = smcNumero(encimaSmc);
      enBaul = smcNumero(baulSmc);
    } else {
      const row = filas.filter((item) => item.id === sel.id)[0];
      encima = row ? Number(row.encima) || 0 : 0;
      enBaul = row ? Number(row.baul) || 0 : 0;
      nombreSrv = row ? row.name : '';
    }
    if (!encima && sel.mano && sel.qty) encima = Number(sel.qty) || 0;
    const info = fichaDe(sel.id, nombreSrv || sel.nombre);
    const have = sel.lado === 'encima' ? encima : enBaul;
    const moneda = sel.kind === 'smc';
    const enCofre = !sel.mano || cerca();
    const op = sel.lado === 'encima' ? 'deposit' : 'withdraw';
    const verbo = sel.lado === 'encima' ? 'Guardar' : 'Sacar';
    const nums = botones(have, moneda, montoTexto);
    const botonesHtml = nums.map((b) => '<button type="button" class="baul-btn" data-op="' + op + '" data-kind="' + sel.kind + '" data-item="' + esc(sel.id) + '" data-cant="' + b.cant + '"' + (b.off ? ' disabled' : '') + '>' + b.texto + '</button>').join('');
    const encimaTxt = moneda ? encimaSmc : String(encima);
    const baulTxt = moneda ? baulSmc : String(enBaul);
    const llevar = encima > 0 && seSuelta(sel.id);
    const botarNums = botonesBotar(encima);
    const botarHtml = llevar ? ('<p class="baul-verbo">Botar</p><div class="baul-montos baul-botar">' + botarNums.map((b) => '<button type="button" class="baul-btn" data-op="soltar" data-kind="item" data-item="' + esc(sel.id) + '" data-cant="' + b.cant + '"' + (b.off ? ' disabled' : '') + '>' + b.texto + '</button>').join('') + '</div>') : '';
    const canje = (sel.id === 'moneda_plata' || sel.id === 'moneda_cobre') ? '<button type="button" class="baul-btn" id="baul-canje" data-op="canjear" data-item="' + esc(sel.id) + '">Canjear por Simoncoin</button>' : '';
    const esMineral = sel.id === 'mineral_oro' || sel.id === 'mineral_plata' || sel.id === 'mineral_cobre' || sel.id === 'pepita_oro';
    const horno = esMineral && !juntoHorno()
      ? '<p class="baul-horno">Se acuña en el Horno de Las Palmas o en el Horno de La Ladera.</p><button type="button" class="baul-btn" id="baul-ir-horno">Ir al horno</button>'
      : '';
    const pase = enCofre
      ? '<p class="baul-verbo">' + verbo + '</p><div class="baul-montos">' + botonesHtml + '<input id="baul-monto" inputmode="decimal" value="' + esc(montoTexto) + '" aria-label="Cantidad X" placeholder="1"></div>'
      : '<div class="baul-montos"><input id="baul-monto" inputmode="decimal" value="' + esc(montoTexto) + '" aria-label="Cantidad X" placeholder="1"></div>';
    return '<div id="baul-ficha" class="baul-ficha"><div class="baul-carta" role="dialog" aria-labelledby="baul-ficha-nombre">'
      + '<button type="button" class="x" id="baul-ficha-x" aria-label="Cerrar">✕</button>'
      + '<div class="ficha-ico" aria-hidden="true">' + dibujo(sel.id) + '</div>'
      + '<h3 id="baul-ficha-nombre">' + esc(info.nombre) + '</h3>'
      + '<p class="baul-desc">' + esc(info.texto) + '</p>'
      + '<p class="baul-cantidades">Encima: ' + esc(encimaTxt) + ' · Baúl: ' + esc(baulTxt) + '</p>'
      + pase
      + botarHtml
      + canje
      + horno
      + (aviso ? '<p class="baul-aviso" role="alert">' + esc(aviso) + '</p>' : '')
      + '</div></div>';
  }
  function sacarFicha() {
    const ficha = document.getElementById('baul-ficha');
    if (ficha && document.body && ficha.parentNode !== document.body) document.body.appendChild(ficha);
  }
  function paint(view) {
    const root = document.getElementById('baul-cuerpo');
    if (!root) return;
    const vieja = document.getElementById('baul-ficha');
    if (vieja && vieja.parentNode) vieja.parentNode.removeChild(vieja);
    const data = view || vacio();
    last = data;
    const smc = data.smc || vacio().smc;
    const filas = data.filas || [];
    const totales = data.totales || {};
    const linked = online();
    root.innerHTML = ''
      + '<p class="baul-nota">Toca una casilla para ver qué es. Encima se guarda en el baúl. El baúl vuelve a la mano.</p>'
      + '<div class="rejilla">'
      + lado('encima', smc.billetera && smc.billetera.exacto, filas)
      + lado('baul', smc.baul && smc.baul.exacto, filas)
      + '</div>'
      + '<p class="baul-exacto">En total ' + esc(smc.total && smc.total.exacto) + '. ' + esc(smc.escala || '') + ' Tope ' + esc(smc.tope || '') + '.</p>'
      + '<p class="baul-nota">' + esc(smc.topes || '') + '</p>'
      + '<p class="baul-nota">Encima ' + (totales.encima || 0) + ' · Baúl ' + (totales.baul || 0) + '. Guardar todo y Sacar todo no crean nada: el servidor cuenta lo que ya hay.</p>'
      + '<p class="baul-nota" id="baul-estado">' + (aviso ? esc(aviso) : (linked ? 'Conectado. Cada pase se guarda en la cuenta.' : 'Sin conexión. El servidor confirma cada pase.')) + '</p>'
      + carta(data);
    const ficha = document.getElementById('baul-ficha');
    const campo = document.getElementById('baul-monto');
    if (campo) campo.addEventListener('input', () => {
      montoTexto = campo.value;
      if (!sel || !ficha) return;
      const smc = (last && last.smc) || vacio().smc;
      const filas = (last && last.filas) || [];
      const moneda = sel.kind === 'smc';
      let have = 0;
      if (moneda) {
        const texto = sel.lado === 'encima' ? (smc.billetera && smc.billetera.exacto) : (smc.baul && smc.baul.exacto);
        have = smcNumero(texto);
      } else {
        const row = filas.filter((item) => item.id === sel.id)[0];
        have = row ? Number(sel.lado === 'encima' ? row.encima : row.baul) || 0 : 0;
      }
      const nums = botones(have, moneda, montoTexto);
      ficha.querySelectorAll('.baul-montos:not(.baul-botar) [data-cant]').forEach((button) => {
        const row = nums.filter((item) => item.cant === button.dataset.cant)[0];
        if (row) button.disabled = !!row.off;
      });
      const filaMano = filas.filter((item) => item.id === sel.id)[0];
      const sueltos = botonesBotar((filaMano && Number(filaMano.encima)) || (sel.mano && sel.qty) || 0);
      ficha.querySelectorAll('.baul-botar [data-cant]').forEach((button) => {
        const row = sueltos.filter((item) => item.cant === button.dataset.cant)[0];
        if (row) button.disabled = !!row.off;
      });
    });
    root.querySelectorAll('.casilla[data-lado]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        sel = { lado: button.dataset.lado, kind: button.dataset.kind, id: button.dataset.item, mano: false };
        aviso = '';
        paint(last);
      });
    });
    const cerrar = document.getElementById('baul-ficha-x');
    if (cerrar) cerrar.addEventListener('click', (event) => { event.stopPropagation(); cerrarFicha(); });
    const fondo = document.getElementById('baul-ficha');
    if (fondo) fondo.addEventListener('click', (event) => { if (event.target === fondo) cerrarFicha(); });
    const ir = document.getElementById('baul-ir-horno');
    if (ir) ir.addEventListener('click', (event) => { event.stopPropagation(); irAlHorno(); });
    const canje = document.getElementById('baul-canje');
    if (canje) canje.addEventListener('click', (event) => {
      event.stopPropagation();
      const qty = entero(montoTexto) || 1;
      if (window.Objeto && Objeto.canjear) Objeto.canjear(canje.dataset.item, qty);
    });
    sacarFicha();
    const montos = (ficha || root).querySelectorAll('.baul-montos [data-cant]');
    montos.forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        enviar(button);
      });
    });
  }
  function abrirFicha(opts) {
    opts = opts || {};
    sel = {
      lado: opts.lado || 'encima',
      kind: opts.id === 'smc' ? 'smc' : 'item',
      id: opts.id,
      mano: opts.mano !== false,
      qty: Number(opts.qty) || 0,
      nombre: opts.nombre || '',
    };
    aviso = '';
    const el = panel();
    const cerrado = !el || el.hidden;
    paint(last || vacio());
    if (cerrado && el) el.hidden = true;
  }
  function enviar(button) {
    if (!button || button.disabled) return false;
    const cant = button.dataset.cant;
    if (button.dataset.op === 'soltar') {
      const have = sel && sel.mano && sel.qty ? Number(sel.qty) : 0;
      const fila = (last && last.filas || []).filter((item) => item.id === button.dataset.item)[0];
      const encima = fila ? Number(fila.encima) || 0 : have;
      const qty = cant === 'all' ? encima : (cant === 'x' ? entero(montoTexto) : Number(cant));
      if (!(qty >= 1) || !window.Objeto || !Objeto.botar) return false;
      return !!Objeto.botar(button.dataset.item, qty);
    }
    if (!online()) return false;
    if (button.dataset.kind === 'smc') {
      const amount = cant === 'all' ? 'all' : (cant === 'x' ? montoTexto : cant);
      moverSmc(button.dataset.op, amount);
    } else {
      const qty = cant === 'all' ? 'all' : (cant === 'x' ? entero(montoTexto) : Number(cant));
      mover(button.dataset.op, button.dataset.item, qty);
    }
    return true;
  }
  function fijarMonto(valor) { montoTexto = String(valor == null ? '' : valor); }
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
    if (message.reason && !message.ok) aviso = message.reason;
    else if (message.ok) aviso = '';
    if (message.view) {
      paint(message.view);
      if (window.TradeUI && TradeUI.refrescar) TradeUI.refrescar();
    } else if (aviso) paint(last || vacio());
    if (message.moved) aplicar(message.moved);
    if (message.reason && window.LiveInk && LiveInk.say) LiveInk.say(message.reason, message.ok ? 'juego' : 'aviso');
    return true;
  }
  function mundo() {
    const ink = window.LiveInk;
    const world = ink && (typeof ink.world === 'function' ? ink.world() : ink.world);
    return { ink: ink, world: world, here: (world && world.mapId) || 'city', S: ink && ink.state };
  }
  function cerca() {
    const ctx = mundo();
    const S = ctx.S;
    const here = ctx.here;
    if (!S || !ctx.world || !S.player) return false;
    if (here !== 'mine' && here !== 'mina2' && here !== 'casa' && here !== 'banco' && here !== 'central') return false;
    if (here === 'casa' && window.Casa && typeof Casa.ajena === 'function' && Casa.ajena()) return false;
    const px = S.player.x;
    const py = S.player.y;
    const spots = [];
    if (S.nodes && S.nodes.forEach) {
      S.nodes.forEach((node) => {
        const d = node && node.def;
        if (!d) return;
        if (d.type === 'mine_chest' || d.type === 'bank_chest' || d.type === 'banquito') spots.push(d);
      });
    }
    if (here === 'casa' && window.Casa && Casa.layout && Casa.layout.items) {
      for (const item of Casa.layout.items) if (item && item.type === 'chest') spots.push(item);
    }
    return spots.some((d) => Math.max(Math.abs(px - d.x), Math.abs(py - d.y)) <= 2);
  }
  function pulso() {
    const btn = document.getElementById('baul-abrir');
    if (!btn) return;
    const show = cerca() && !abierto();
    btn.hidden = !show;
    if (!abierto() && !(sel && sel.mano)) close();
  }
  const abrir = document.getElementById('baul-abrir');
  if (abrir) abrir.addEventListener('click', open);
  function fichaSuelta() { return !!(sel && sel.mano && !abierto()); }
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !sel || (!abierto() && !fichaSuelta())) return;
    event.preventDefault();
    cerrarFicha();
  });
  document.addEventListener('pointerdown', (event) => {
    if (!sel || (!abierto() && !fichaSuelta())) return;
    const t = event.target;
    if (!t || !t.closest) return;
    if (t.closest('#baul-ficha, .baul-carta, .casilla, #baul-abrir, #baul-mina header')) return;
    cerrarFicha();
  });
  setInterval(pulso, 400);
  function ultima() { return last; }
  function elegir(row) { sel = row; aviso = ''; paint(last || vacio()); }
  window.Baul = { open, close, paint, pedir, onNet, abierto, cerca, ultima, elegir, abrirFicha, fichaDe, FICHAS, botones, botonesBotar, mensaje, centimos, enviar, fijarMonto, juntoHorno, irAlHorno, seSuelta };
})();
