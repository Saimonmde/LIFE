/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* El servidor decide quién es el dueño. Este archivo sólo muestra el panel. */
(() => {
  'use strict';

  const abrir = document.createElement('button');
  abrir.type = 'button';
  abrir.id = 'dueno-smc-abrir';
  abrir.hidden = true;
  abrir.textContent = 'Editar SMC';
  document.body.append(abrir);

  const panel = document.createElement('section');
  panel.id = 'dueno-smc';
  panel.hidden = true;
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-labelledby', 'dueno-smc-titulo');
  panel.innerHTML = [
    '<div class="dueno-smc-panel">',
    '<header><h2 id="dueno-smc-titulo">Simon Coins del dueño</h2>',
    '<button type="button" id="dueno-smc-cerrar">Cerrar</button></header>',
    '<p class="dueno-aviso" id="dueno-smc-aviso">Simulación educativa. No es dinero real. Esta acuñación no es el oro del río ni el tope de juego.</p>',
    '<p id="dueno-smc-billetera"></p>',
    '<p id="dueno-smc-baul"></p>',
    '<p id="dueno-smc-total"></p>',
    '<p id="dueno-smc-cupo"></p>',
    '<label>Billetera, en SMC<input id="dueno-smc-billetera-in" inputmode="decimal" autocomplete="off"></label>',
    '<label>Baúl, en SMC<input id="dueno-smc-baul-in" inputmode="decimal" autocomplete="off"></label>',
    '<label>Acuñar, en SMC<input id="dueno-smc-mint-in" inputmode="decimal" autocomplete="off" placeholder="0"></label>',
    '<label>Motivo<input id="dueno-smc-razon" maxlength="160" autocomplete="off"></label>',
    '<div class="dueno-acciones">',
    '<button type="button" id="dueno-smc-guardar">Guardar ajuste</button>',
    '<button type="button" id="dueno-smc-mint">Acuñar</button>',
    '</div>',
    '<p id="dueno-smc-estado" role="status"></p>',
    '</div>',
  ].join('');
  document.body.append(panel);

  const $ = (id) => document.getElementById(id);

  function estado(text) {
    const el = $('dueno-smc-estado');
    if (el) el.textContent = text || '';
  }

  function pintar(data) {
    if (data.aviso) $('dueno-smc-aviso').textContent = data.aviso;
    $('dueno-smc-billetera').textContent = 'Billetera: ' + (data.billetera || '0 SMC');
    $('dueno-smc-baul').textContent = 'Baúl: ' + (data.baul || '0 SMC');
    $('dueno-smc-total').textContent = 'Total: ' + (data.total || '0 SMC');
    $('dueno-smc-cupo').textContent = 'Cabe todavía: ' + (data.cupo || '0 SMC') + ' de ' + (data.tope || '21.000.000 SMC');
    if (document.activeElement !== $('dueno-smc-billetera-in')) {
      $('dueno-smc-billetera-in').value = String(data.billetera || '').replace(' SMC', '');
    }
    if (document.activeElement !== $('dueno-smc-baul-in')) {
      $('dueno-smc-baul-in').value = String(data.baul || '').replace(' SMC', '');
    }
  }

  async function leer() {
    const response = await fetch('/auth/dueno/smc?t=' + Date.now(), { credentials: 'same-origin', cache: 'no-store' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'No se pudo leer el saldo.');
    pintar(data);
    return data;
  }

  async function enviar(body) {
    estado('Guardando…');
    const response = await fetch('/auth/dueno/smc', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'No se pudo guardar.');
    pintar(data);
    const codigo = data.codigo || (data.codigos || [])[0] || '';
    estado(codigo ? 'Quedó en el libro madre: ' + codigo : 'Listo.');
  }

  abrir.onclick = async () => {
    panel.hidden = false;
    estado('');
    try { await leer(); } catch (error) { estado(error.message); }
  };
  $('dueno-smc-cerrar').onclick = () => { panel.hidden = true; };
  $('dueno-smc-guardar').onclick = async () => {
    try {
      await enviar({
        op: 'ajustar',
        billetera: $('dueno-smc-billetera-in').value,
        baul: $('dueno-smc-baul-in').value,
        razon: $('dueno-smc-razon').value,
      });
    } catch (error) { estado(error.message); }
  };
  $('dueno-smc-mint').onclick = async () => {
    try {
      await enviar({
        op: 'acunar',
        smc: $('dueno-smc-mint-in').value,
        razon: $('dueno-smc-razon').value,
      });
      $('dueno-smc-mint-in').value = '';
    } catch (error) { estado(error.message); }
  };

  fetch('/auth/cuenta?t=' + Date.now(), { credentials: 'same-origin', cache: 'no-store' })
    .then((response) => response.ok ? response.json() : null)
    .then((data) => {
      if (data && data.role === 'owner') abrir.hidden = false;
    })
    .catch(() => {});
})();
