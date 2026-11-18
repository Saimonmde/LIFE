/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Cambiar lo recogido por Simoncoin. La tarifa se ve antes de confirmar. */
(() => {
  'use strict';
  const TARIFA = {
    mineral_cobre: { smh: 1, cada: 10, texto: '0,001', nombre: 'Mineral de cobre' },
    mineral_plata: { smh: 1, cada: 1, texto: '0,01', nombre: 'Mineral de plata' },
    mineral_oro: { smh: 10, cada: 1, texto: '0,1', nombre: 'Mineral de oro' },
    pepita_oro: { smh: 10, cada: 1, texto: '0,1', nombre: 'Pepita de oro' },
    cafe_cereza: { smh: 1, cada: 1, texto: '0,01', nombre: 'Café' },
    cacao_baba: { smh: 1, cada: 1, texto: '0,01', nombre: 'Cacao' },
  };
  let abierto = null;

  function seCambia(item) { return !!TARIFA[item]; }
  function pago(item, qty) {
    const row = TARIFA[item];
    const n = Math.max(0, Math.floor(Number(qty) || 0));
    if (!row || n < 1) return { smh: 0, usa: 0, texto: '0 SMC' };
    const smh = Math.floor(n * row.smh / row.cada);
    const usa = Math.floor(smh * row.cada / row.smh);
    const texto = (smh / 100).toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' SMC';
    return { smh, usa, texto };
  }
  function caja() {
    let el = document.getElementById('cambiar-smc');
    if (el) return el;
    el = document.createElement('section');
    el.id = 'cambiar-smc';
    el.hidden = true;
    el.setAttribute('role', 'dialog');
    el.innerHTML = '<h2 id="cambiar-titulo">Cambiar por SMC</h2><p id="cambiar-tarifa"></p><p id="cambiar-total"></p><div class="cambiar-fila"><button type="button" id="cambiar-ok">Confirmar</button><button type="button" id="cambiar-todo">Cambiar todo</button><button type="button" id="cambiar-no">Cancelar</button></div><p id="cambiar-nota"></p>';
    document.body.append(el);
    el.querySelector('#cambiar-no').onclick = cerrar;
    el.querySelector('#cambiar-ok').onclick = () => enviar(false);
    el.querySelector('#cambiar-todo').onclick = () => enviar(true);
    return el;
  }
  function pintar() {
    if (!abierto) return;
    const el = caja();
    const row = TARIFA[abierto.item];
    const hecho = pago(abierto.item, abierto.qty);
    el.querySelector('#cambiar-titulo').textContent = 'Cambiar ' + row.nombre;
    el.querySelector('#cambiar-tarifa').textContent = 'Tarifa: ' + row.texto + ' SMC por unidad. Tienes ' + abierto.qty + '.';
    el.querySelector('#cambiar-total').textContent = hecho.smh > 0
      ? 'Vas a cambiar ' + hecho.usa + ' y recibir ' + hecho.texto + '.'
      : 'Con esa cantidad no llega a 0,01 SMC. No se quita nada.';
  }
  function abrir(item, qty) {
    if (!seCambia(item)) return;
    abierto = { item, qty: Math.max(1, Math.floor(Number(qty) || 1)) };
    const el = caja();
    el.hidden = false;
    el.querySelector('#cambiar-nota').textContent = '';
    pintar();
  }
  function cerrar() {
    const el = document.getElementById('cambiar-smc');
    if (el) el.hidden = true;
    abierto = null;
  }
  function enviar(todo) {
    if (!abierto) return;
    const S = window.LiveInk && LiveInk.state;
    const ws = S && S.net && S.net.ws;
    const nota = document.getElementById('cambiar-nota');
    if (!ws || ws.readyState !== 1) {
      if (nota) nota.textContent = 'Entra al mundo para cambiar. No se movió nada.';
      return;
    }
    ws.send(JSON.stringify({ t: 'cambiar', item: abierto.item, qty: todo ? abierto.qty : pago(abierto.item, abierto.qty).usa || abierto.qty, todo: !!todo }));
  }
  function onNet(m) {
    if (!m || m.t !== 'cambiar_result') return false;
    const nota = document.getElementById('cambiar-nota');
    if (nota) nota.textContent = m.reason || '';
    if (window.LiveInk && LiveInk.say) LiveInk.say(m.reason || '', m.ok ? 'oro' : 'aviso');
    if (m.ok && window.LiveInk && LiveInk.takeItem) LiveInk.takeItem(m.item, m.qty);
    if (m.ok && m.balanceSubs != null && window.Simulacion && Simulacion.aplicarCredito) {
      Simulacion.aplicarCredito({ walletName: (window.LiveInk.state && LiveInk.state.serverWallet) || '', balanceSubs: m.balanceSubs });
    }
    if (m.ok && window.Cajon) Cajon.paint();
    if (m.ok) cerrar();
    return true;
  }
  window.Cambiar = { seCambia, pago, abrir, onNet, TARIFA };
})();
