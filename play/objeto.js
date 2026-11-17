/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Ficha del objeto: dejar presionado, clic sostenido o clic derecho.
   Examinar dice para qué sirve. Soltar lo saca ya y lo deja aparecer a los 10 segundos. */
(() => {
  'use strict';
  const GRUPOS = ['Simoncoin', 'Minerales', 'Lingotes', 'Monedas acuñadas', 'Cosechas', 'Otros'];
  const COSECHA = ['bolsa_cafe', 'bolsa_cacao', 'mango', 'banano', 'coco', 'manzana', 'pera', 'naranja', 'trucha', 'bocachico', 'mojarra'];
  let drops = [];
  let abierto = null;
  let token = 1;

  function grupo(id) {
    if (id === 'smc' || id === 'simoncoin' || id === 'moneda_oro') return 'Simoncoin';
    if (id.indexOf('mineral_') === 0 || id.indexOf('pepita_') === 0 || id === 'piedra') return 'Minerales';
    if (id.indexOf('lingote_') === 0) return 'Lingotes';
    if (id === 'moneda_plata' || id === 'moneda_cobre') return 'Monedas acuñadas';
    if (COSECHA.indexOf(id) >= 0) return 'Cosechas';
    return 'Otros';
  }
  function texto(id) {
    const fila = {
      mineral_oro: 'Oro crudo. En el horno se vuelve Simoncoin y esa acuñación sí entra al libro mayor.',
      pepita_oro: 'Pepita de oro. El horno la cuenta como oro crudo para acuñar Simoncoin.',
      mineral_plata: 'Plata cruda. Cuatro piezas hacen una moneda de plata, que se guarda en el inventario.',
      mineral_cobre: 'Cobre crudo. Tres piezas hacen una moneda de cobre, que se guarda en el inventario.',
      moneda_plata: 'Moneda de plata acuñada. Se guarda, se cambia o se suelta. No es Simoncoin.',
      moneda_cobre: 'Moneda de cobre acuñada. Se guarda, se cambia o se suelta. No es Simoncoin.',
      moneda_oro: 'Es la cara del Simoncoin. No se suelta: se cambia con otra persona.',
      lingote_plata: 'Lingote de plata. En el horno equivale a una moneda de plata.',
      lingote_cobre: 'Lingote de cobre. En el horno equivale a una moneda de cobre.',
      lingote_oro: 'Lingote de oro. Lo guarda el Banco Central. No es Simoncoin suelto.',
      bolsa_cafe: 'Café de la finca. Se lleva al taller y también se puede cambiar.',
      bolsa_cacao: 'Cacao de la finca. Se lleva al taller y también se puede cambiar.',
    };
    return fila[id] || 'Objeto del inventario. Se puede guardar en el baúl o dejar en el piso.';
  }
  function seSuelta(id) {
    return ['smc', 'simoncoin', 'moneda_oro', 'sai'].indexOf(id) < 0;
  }
  function caja() {
    let el = document.getElementById('objeto-ficha');
    if (el) return el;
    el = document.createElement('section');
    el.id = 'objeto-ficha';
    el.hidden = true;
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-label', 'Ficha del objeto');
    el.innerHTML = '<header><b id="objeto-nombre"></b><button type="button" id="objeto-cerrar" aria-label="Cerrar ficha">×</button></header><div class="objeto-cuerpo"><span id="objeto-ico"></span><p id="objeto-cant"></p><p id="objeto-grupo"></p><p id="objeto-uso" hidden></p><div class="objeto-soltar"><button type="button" id="objeto-menos" aria-label="Menos">−</button><input id="objeto-qty" inputmode="numeric" value="1" aria-label="Cantidad a soltar"><button type="button" id="objeto-mas" aria-label="Más">+</button></div><div class="objeto-acciones"><button type="button" id="objeto-examinar">Examinar</button><button type="button" id="objeto-soltar">Soltar</button><button type="button" id="objeto-canje" hidden>Canjear por Simoncoin</button></div><p id="objeto-nota"></p></div>';
    document.body.append(el);
    el.querySelector('#objeto-cerrar').onclick = cerrar;
    el.querySelector('#objeto-examinar').onclick = () => {
      const uso = el.querySelector('#objeto-uso');
      uso.hidden = false;
      uso.textContent = texto(abierto && abierto.item);
    };
    el.querySelector('#objeto-soltar').onclick = soltar;
    el.querySelector('#objeto-canje').onclick = canjear;
    el.querySelector('#objeto-menos').onclick = () => paso(-1);
    el.querySelector('#objeto-mas').onclick = () => paso(1);
    return el;
  }
  function paso(delta) {
    const input = document.getElementById('objeto-qty');
    const max = (abierto && abierto.qty) || 1;
    const next = Math.max(1, Math.min(max, (Number(input.value) || 1) + delta));
    input.value = String(next);
  }
  function abrir(item, qty) {
    const world = window.LiveInk && LiveInk.world;
    const items = world && world.items;
    const it = items && items[item];
    abierto = { item, qty: Number(qty) || 1 };
    const el = caja();
    el.hidden = false;
    el.querySelector('#objeto-nombre').textContent = (it && it.name) || item;
    el.querySelector('#objeto-cant').textContent = 'Cantidad: ' + abierto.qty;
    el.querySelector('#objeto-grupo').textContent = grupo(item);
    el.querySelector('#objeto-uso').hidden = true;
    el.querySelector('#objeto-nota').textContent = '';
    const ico = el.querySelector('#objeto-ico');
    ico.innerHTML = '';
    if (it && it.icon) {
      const img = document.createElement('img');
      img.alt = '';
      img.src = '../' + (it.icon['64'] || it.icon['32']);
      ico.append(img);
    }
    const input = el.querySelector('#objeto-qty');
    input.value = '1';
    input.max = String(abierto.qty);
    const puede = seSuelta(item);
    el.querySelector('#objeto-soltar').hidden = !puede;
    el.querySelector('.objeto-soltar').hidden = !puede;
    const canje = el.querySelector('#objeto-canje');
    canje.hidden = item !== 'moneda_plata' && item !== 'moneda_cobre';
    if (!puede) el.querySelector('#objeto-nota').textContent = 'El Simoncoin no se suelta. Se cambia con otra persona.';
  }
  function cerrar() {
    const el = document.getElementById('objeto-ficha');
    if (el) el.hidden = true;
    abierto = null;
  }
  function enviar(body) {
    const S = window.LiveInk && LiveInk.state;
    const ws = S && S.net && S.net.ws;
    if (!ws || ws.readyState !== 1) {
      const nota = document.getElementById('objeto-nota');
      if (nota) nota.textContent = 'Entra al mundo para soltar o recoger.';
      return false;
    }
    ws.send(JSON.stringify(body));
    return true;
  }
  function soltar() {
    if (!abierto || !seSuelta(abierto.item)) return;
    const qty = Math.max(1, Math.min(abierto.qty, Number(document.getElementById('objeto-qty').value) || 1));
    enviar({ t: 'soltar', item: abierto.item, qty, token: 's' + (token++) });
  }
  function canjear() {
    if (!abierto) return;
    const qty = Math.max(1, Math.min(abierto.qty, Number(document.getElementById('objeto-qty').value) || 1));
    enviar({ t: 'canjear', item: abierto.item, qty });
  }
  function alzar(id) {
    enviar({ t: 'alzar', id });
  }
  function atar(el, item, qty) {
    if (!el || !item || el.dataset.ficha) return;
    el.dataset.ficha = '1';
    let timer = 0;
    const prevDown = el.onpointerdown;
    const prevUp = el.onpointerup;
    el.onpointerdown = (e) => {
      if (e.button === 2) return;
      clearTimeout(timer);
      timer = setTimeout(() => {
        timer = 0;
        if (window.LiveInk && LiveInk.state) window.__fichaHold = Date.now() + 700;
        abrir(item, qty);
      }, 450);
      if (prevDown) prevDown.call(el, e);
    };
    el.onpointerup = (e) => {
      clearTimeout(timer);
      timer = 0;
      if (prevUp) prevUp.call(el, e);
    };
    el.addEventListener('pointermove', (e) => {
      if (e.movementX || e.movementY) clearTimeout(timer);
    });
    el.addEventListener('pointercancel', () => clearTimeout(timer));
    el.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      abrir(item, qty);
    });
  }
  function onNet(m) {
    if (!m) return false;
    if (m.t === 'piso') {
      drops = m.drops || [];
      return true;
    }
    if (m.t === 'soltar_result') {
      const nota = document.getElementById('objeto-nota');
      if (nota) nota.textContent = m.reason || '';
      if (m.ok && !m.dup && abierto && window.LiveInk) {
        if (m.donde === 'crudo' && window.quitarMetal) window.quitarMetal(abierto.item, Number(document.getElementById('objeto-qty').value) || 1);
        else if (LiveInk.takeItem && m.donde !== 'baul') LiveInk.takeItem(abierto.item, Number(document.getElementById('objeto-qty').value) || 1);
      }
      if (window.LiveInk && LiveInk.say) LiveInk.say(m.reason || '', m.ok ? 'juego' : 'aviso');
      return true;
    }
    if (m.t === 'alzar_result') {
      if (m.ok && window.LiveInk && LiveInk.giveItem) LiveInk.giveItem(m.item, m.qty);
      if (window.LiveInk && LiveInk.say) LiveInk.say(m.reason || '', m.ok ? 'juego' : 'aviso');
      return true;
    }
    if (m.t === 'canjear_result') {
      const nota = document.getElementById('objeto-nota');
      if (nota) nota.textContent = m.reason || '';
      if (m.ok && abierto && window.LiveInk && LiveInk.takeItem) LiveInk.takeItem(m.item, m.qty);
      if (window.LiveInk && LiveInk.say) LiveInk.say(m.reason || '', m.ok ? 'juego' : 'aviso');
      return true;
    }
    return false;
  }
  function piso() {
    const ahora = Date.now() / 1000;
    return drops.map((row) => Object.assign({}, row, { espera: ahora < Number(row.aparece || 0) }));
  }
  function barra() {
    const inv = document.getElementById('inventario');
    if (!inv || document.getElementById('bag-grupos')) return;
    const bar = document.createElement('div');
    bar.id = 'bag-grupos';
    bar.setAttribute('role', 'tablist');
    bar.setAttribute('aria-label', 'Categorías del inventario');
    bar.innerHTML = GRUPOS.map((nombre) => '<button type="button" data-grupo="' + nombre + '">' + nombre + '</button>').join('');
    inv.before(bar);
    bar.addEventListener('click', (e) => {
      const button = e.target.closest('button');
      if (!button) return;
      const ya = button.classList.contains('on');
      bar.querySelectorAll('button').forEach((otro) => otro.classList.remove('on'));
      window.__bagGrupo = ya ? '' : button.dataset.grupo;
      if (!ya) button.classList.add('on');
      if (window.LiveInk && LiveInk.paintInv) LiveInk.paintInv();
    });
  }
  const estilo = document.createElement('style');
  estilo.textContent = '#objeto-ficha{position:fixed;z-index:40;left:50%;top:50%;transform:translate(-50%,-50%);width:min(380px,94vw);background:#211a15f8;color:#eee0c7;border:1px solid #b48346;border-radius:14px;font:15px/1.4 "Avenir Next","Segoe UI",system-ui,sans-serif}#objeto-ficha header{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;background:#52351f;border-radius:14px 14px 0 0}#objeto-ficha header button{background:transparent;color:#ffe7bb;border:0;font-size:22px}#objeto-ficha .objeto-cuerpo{padding:14px}#objeto-ficha img{width:72px;height:72px}#objeto-grupo{color:#e2b23c;font-weight:700}#objeto-ficha .objeto-soltar,#objeto-ficha .objeto-acciones{display:flex;gap:8px;margin-top:8px}#objeto-ficha button,#objeto-ficha input{min-height:44px;border-radius:10px;border:1px solid #aa814b;background:#6b4825;color:#ffe7bb;font:700 15px system-ui}#objeto-ficha input{width:72px;text-align:center;background:#33271d}#bag-grupos{display:flex;gap:6px;overflow:auto;padding:6px 8px}#bag-grupos button{flex:0 0 auto;min-height:36px;border-radius:999px;border:1px solid #aa814b;background:#3a2a1c;color:#ffe7bb;font:600 12px system-ui}#bag-grupos button.on{background:#e2b23c;color:#2a1c10}#inventario .slot.fuera{opacity:.25}';
  document.head.append(estilo);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', barra);
  else barra();
  window.Objeto = { abrir, cerrar, atar, onNet, piso, alzar, grupo, texto };
})();
