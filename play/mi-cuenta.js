/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Panel Mi cuenta: el progreso vive en la cuenta, no sólo en este aparato. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);

  function vuelta() {
    const q = new URLSearchParams(location.search);
    if (location.pathname.indexOf('/movil') === 0 || q.get('movil') === '1') return '/play/?movil=1';
    return '/play/';
  }
  function texto(n) {
    const v = Math.floor(Number(n) || 0);
    return String(v);
  }
  function lista(obj, nombres) {
    const keys = Object.keys(obj || {});
    if (!keys.length) return 'Nada guardado todavía.';
    return keys.map((key) => (nombres[key] || key) + ': ' + obj[key]).join(' · ');
  }
  function inventario(rows) {
    if (!rows || !rows.length) return 'La mochila guardada está vacía.';
    return rows.map((row) => row.item + ' × ' + row.qty).join(' · ');
  }

  const panel = document.createElement('section');
  panel.id = 'mi-cuenta';
  panel.hidden = true;
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-labelledby', 'mi-cuenta-titulo');
  panel.innerHTML = [
    '<div class="mi-cuenta-panel">',
    '<header><h2 id="mi-cuenta-titulo">Mi cuenta</h2><button type="button" id="mi-cuenta-cerrar">✕ Cerrar</button></header>',
    '<p id="mi-cuenta-nick"></p>',
    '<p id="mi-cuenta-google"></p>',
    '<p id="mi-cuenta-lugar"></p>',
    '<p id="mi-cuenta-hora"></p>',
    '<p id="mi-cuenta-inv"></p>',
    '<p id="mi-cuenta-monedas"></p>',
    '<p id="mi-cuenta-finca"></p>',
    '<p id="mi-cuenta-favorito"></p>',
    '<p class="mi-cuenta-nota">Cambiar el nickname cuesta 5 Simoncoin, que se pagan al Banco Central. Simon está reservado.</p>',
    '<label class="mi-cuenta-seguir"><input id="mi-cuenta-seguir" type="checkbox" checked> Pueden seguirme</label>',
    '<h3>Amigos</h3><div id="mi-cuenta-amigos"></div>',
    '<h3>Pedidos</h3><div id="mi-cuenta-pedidos"></div>',
    '<button type="button" id="mi-cuenta-guardar">Guardar ahora</button>',
    '<form id="mi-cuenta-clave">',
    '<label>Contraseña actual<input id="mi-cuenta-actual" type="password" autocomplete="current-password"></label>',
    '<label>Contraseña nueva<input id="mi-cuenta-nueva" type="password" autocomplete="new-password"></label>',
    '<button type="submit">Cambiar contraseña</button>',
    '</form>',
    '<button type="button" id="mi-cuenta-google-btn">Vincular con Google</button>',
    '<button type="button" id="mi-cuenta-lugar-btn">Cambiar lugar favorito</button>',
    '<button type="button" id="mi-cuenta-salir">Cerrar sesión en este dispositivo</button>',
    '<button type="button" id="mi-cuenta-salir-todos">Cerrar sesión en todos</button>',
    '<p id="mi-cuenta-estado" role="status"></p>',
    '</div>',
  ].join('');
  document.body.append(panel);

  function estado(text) {
    const el = $('mi-cuenta-estado');
    if (el) el.textContent = text || '';
  }
  function pintar(data) {
    $('mi-cuenta-nick').textContent = 'Nickname: ' + (data.nick || 'Viajero');
    $('mi-cuenta-google').textContent = 'Google: ' + (data.google ? 'sí' : 'no');
    $('mi-cuenta-lugar').textContent = 'Último lugar: ' + (data.place || 'Sin lugar guardado');
    $('mi-cuenta-hora').textContent = data.saved || 'Todavía no hay un guardado en la cuenta.';
    $('mi-cuenta-inv').textContent = 'Inventario: ' + inventario(data.inventory);
    const coins = data.coins || {};
    const subs = window.Simulacion ? Simulacion.SUBS : 100;
    const plataSubs = window.Simulacion && Simulacion.PLATA_SUBS ? Simulacion.PLATA_SUBS : 100000000;
    const compact = (base, whole) => {
      const value = Number(base) || 0;
      if (window.Simulacion && Simulacion.formatCompact) return Simulacion.formatCompact(whole ? value : value / subs);
      return texto(whole ? value : value / subs);
    };
    const plataN = (Number(coins.simonplataSph) || 0) / plataSubs;
    const plataTxt = window.Simulacion && Simulacion.formatCompact ? Simulacion.formatCompact(plataN) : texto(plataN);
    const total = coins.totalSmh != null ? coins.totalSmh : coins.simoncoinSmh;
    const line = $('mi-cuenta-monedas');
    line.textContent = 'Simoncoin: ' + compact(total, false) + ' SMC · Simonplata: ' + plataTxt + ' SMP · Simonchis: ' + compact(coins.simonchis, true);
    const exactSmc = window.Simulacion && Simulacion.formatPair ? Simulacion.formatPair(total || 0) : (texto(total) + ' SMH');
    const exactSmp = window.Simulacion && Simulacion.formatPlataPair ? Simulacion.formatPlataPair(coins.simonplataSph || 0) : (texto(coins.simonplataSph) + ' SPH');
    line.title = exactSmc + ' · ' + exactSmp + ' · ' + texto(coins.simonchis) + ' Simonchis';
    $('mi-cuenta-finca').textContent = 'Finquita: ' + lista(data.crops, { cafe: 'Café', cacao: 'Cacao' }) + ' · Animales: ' + lista(data.animals, { gallo: 'Gallos', gallina: 'Gallinas' });
    $('mi-cuenta-favorito').textContent = 'Favorito: ' + (data.favoritePlace || 'sin lugar') + (data.favoriteWorld ? ' · Mundo ' + data.favoriteWorld : '');
    const google = $('mi-cuenta-google-btn');
    if (google) google.hidden = !!data.google;
    const seguir = $('mi-cuenta-seguir');
    if (seguir) seguir.checked = data.followable !== false;
    pintarGente('mi-cuenta-amigos', data.amigos, false);
    pintarGente('mi-cuenta-pedidos', data.pedidos, true);
    pintarStaff(data);
    marcar(data.role);
  }
  function marcar(role) {
    let badge = $('staff-badge');
    if (role !== 'staff') {
      if (badge) badge.hidden = true;
      return;
    }
    if (!badge) {
      badge = document.createElement('span');
      badge.id = 'staff-badge';
      badge.textContent = 'Staff';
      document.body.append(badge);
    }
    badge.hidden = false;
  }
  function staffEstado(text) {
    const el = $('staff-estado');
    if (el) el.textContent = text || '';
  }
  async function staffPost(body) {
    const response = await fetch('/auth/staff', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo.');
    return data;
  }
  function filaStaff(person, quitar) {
    const line = document.createElement('p');
    line.className = 'staff-fila';
    const text = document.createElement('span');
    text.textContent = (person.nick || 'Viajero') + (person.email ? ' · ' + person.email : '') + (person.role === 'owner' ? ' · dueño' : '');
    line.append(text);
    if (person.role === 'owner') return line;
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = quitar ? 'Quitar staff' : (person.role === 'staff' ? 'Quitar staff' : 'Dar staff');
    button.onclick = async () => {
      staffEstado('');
      try {
        const data = await staffPost({ id: person.id, grant: person.role !== 'staff' });
        pintarLista(data.staff || []);
        const box = $('staff-resultados');
        if (box) box.replaceChildren();
        staffEstado(person.role === 'staff' ? 'Ya no es staff.' : 'Ahora es staff.');
      } catch (error) {
        staffEstado(error.message);
      }
    };
    line.append(button);
    return line;
  }
  function pintarLista(rows) {
    const box = $('staff-lista');
    if (!box) return;
    box.replaceChildren();
    if (!rows || !rows.length) {
      const empty = document.createElement('p');
      empty.textContent = 'Todavía no hay staff.';
      box.append(empty);
      return;
    }
    rows.forEach((person) => box.append(filaStaff(person, true)));
  }
  function pintarAuditoria(rows) {
    const box = $('staff-audit');
    if (!box) return;
    box.replaceChildren();
    (rows || []).slice().reverse().forEach((row) => {
      const line = document.createElement('p');
      const when = row.at ? new Date(row.at * 1000).toLocaleString('es-CO', { timeZone: 'America/Bogota', dateStyle: 'short', timeStyle: 'short' }) : '';
      line.textContent = [when, row.nick || row.account, row.action, row.target].filter(Boolean).join(' · ');
      box.append(line);
    });
  }
  async function buscarStaff() {
    staffEstado('');
    try {
      const data = await staffPost({ q: $('staff-buscar').value });
      const box = $('staff-resultados');
      box.replaceChildren();
      if (!data.results || !data.results.length) {
        const empty = document.createElement('p');
        empty.textContent = 'No hay una cuenta con ese nick o correo.';
        box.append(empty);
      } else {
        data.results.forEach((person) => box.append(filaStaff(person, false)));
      }
      pintarLista(data.staff || []);
      pintarAuditoria(data.audit || []);
    } catch (error) {
      staffEstado(error.message);
    }
  }
  function pintarStaff(data) {
    let box = $('mi-cuenta-staff');
    if (!data || data.role !== 'owner') {
      if (box) box.hidden = true;
      return;
    }
    if (!box) {
      box = document.createElement('section');
      box.id = 'mi-cuenta-staff';
      box.innerHTML = [
        '<h3>Personal</h3>',
        '<p>Sólo el dueño da o quita staff. Entran con su cuenta. Moderan y editan el mundo. No nombran personal, no cambian al dueño y no acuñan monedas.</p>',
        '<label>Buscar nick o correo<input id="staff-buscar" maxlength="80" placeholder="nick o correo" autocomplete="off"></label>',
        '<button type="button" id="staff-ir">Buscar</button>',
        '<div id="staff-resultados"></div>',
        '<h3>Staff ahora</h3>',
        '<div id="staff-lista"></div>',
        '<h3>Registro</h3>',
        '<div id="staff-audit"></div>',
        '<p id="staff-estado" role="status"></p>',
      ].join('');
      $('mi-cuenta-estado').before(box);
      $('staff-ir').onclick = buscarStaff;
      $('staff-buscar').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') { event.preventDefault(); buscarStaff(); }
      });
    }
    box.hidden = false;
    pintarLista(data.staff || []);
    pintarAuditoria(data.audit || []);
  }
  function pintarGente(id, rows, pedido) {
    const box = $(id);
    if (!box) return;
    box.replaceChildren();
    if (!rows || !rows.length) {
      const empty = document.createElement('p');
      empty.textContent = pedido ? 'No hay pedidos.' : 'Todavía no hay amigos.';
      box.append(empty);
      return;
    }
    rows.forEach((row) => {
      const line = document.createElement('p');
      line.textContent = (row.nick || 'Viajero') + (row.online ? ' · en línea' : ' · fuera de línea');
      if (row.online && window.Vida && Vida.presence) {
        const live = (Vida.presence().players || []).find((item) => item.key === row.key);
        if (live) {
          const go = document.createElement('button');
          go.type = 'button';
          go.textContent = 'Ir con él';
          go.onclick = () => {
            const S = window.__ELJARDIN;
            if (S && S.net && S.net.ws) S.net.ws.send(JSON.stringify({ t: 'ir_con', id: live.id }));
          };
          const follow = document.createElement('button');
          follow.type = 'button';
          follow.textContent = 'Seguir';
          follow.onclick = () => { if (window.Seguir) Seguir.empezar(live); };
          line.append(' ', go, ' ', follow);
        }
      }
      if (pedido) {
        const yes = document.createElement('button');
        yes.type = 'button';
        yes.textContent = 'Aceptar';
        yes.onclick = () => {
          const S = window.__ELJARDIN;
          if (S && S.net && S.net.ws) S.net.ws.send(JSON.stringify({ t: 'amigo_aceptar', key: row.key }));
        };
        const no = document.createElement('button');
        no.type = 'button';
        no.textContent = 'Rechazar';
        no.onclick = () => {
          const S = window.__ELJARDIN;
          if (S && S.net && S.net.ws) S.net.ws.send(JSON.stringify({ t: 'amigo_rechazar', key: row.key }));
        };
        line.append(' ', yes, ' ', no);
      }
      box.append(line);
    });
  }
  async function abrir() {
    panel.hidden = false;
    estado('');
    const menu = $('hud-gear-menu');
    if (menu) menu.hidden = true;
    try {
      const response = await fetch('/auth/cuenta', { credentials: 'same-origin', cache: 'no-store' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Entra con tu cuenta para verla.');
      pintar(data);
    } catch (error) {
      estado(error.message);
    }
    $('mi-cuenta-cerrar').focus();
  }
  function cerrar() { panel.hidden = true; }
  async function salir(url) {
    if (window.Partida) { try { await Partida.push(); } catch (e) {} }
    const response = await fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    if (!response.ok) throw new Error('No se pudo cerrar la sesión.');
    location.replace(vuelta());
  }
  function montar() {
    const menu = $('hud-gear-menu');
    if (!menu || $('cajon-cuenta')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.id = 'cajon-cuenta';
    button.textContent = 'Mi cuenta';
    button.onclick = () => abrir();
    menu.append(button);
  }

  $('mi-cuenta-cerrar').onclick = cerrar;
  panel.addEventListener('click', (event) => { if (event.target === panel) cerrar(); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !panel.hidden) { cerrar(); event.preventDefault(); }
  });
  $('mi-cuenta-guardar').onclick = async () => {
    estado('Guardando…');
    if (window.Partida) await Partida.push();
    await abrir();
    estado('Guardado en la cuenta.');
  };
  $('mi-cuenta-clave').onsubmit = async (event) => {
    event.preventDefault();
    const current = $('mi-cuenta-actual');
    const next = $('mi-cuenta-nueva');
    estado('');
    try {
      const response = await fetch('/auth/clave', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current: current.value, password: next.value }),
      });
      const data = await response.json();
      current.value = '';
      next.value = '';
      if (!response.ok) throw new Error(data.error || 'No se cambió la contraseña.');
      estado('Contraseña cambiada.');
    } catch (error) {
      current.value = '';
      next.value = '';
      estado(error.message);
    }
  };
  $('mi-cuenta-google-btn').onclick = () => {
    location.href = '/auth/google?vuelta=' + encodeURIComponent(vuelta());
  };
  $('mi-cuenta-seguir').onchange = async () => {
    const on = $('mi-cuenta-seguir').checked;
    estado('');
    try {
      const response = await fetch('/auth/seguir', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ on: on }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'No se guardó.');
      estado(on ? 'Otras personas pueden seguirte.' : 'Nadie puede seguirte.');
    } catch (error) {
      estado(error.message);
    }
  };
  $('mi-cuenta-lugar-btn').onclick = () => {
    cerrar();
    if (window.Hogar) Hogar.openPicker((id) => {
      if (window.LiveInk && LiveInk.elegirLugar) LiveInk.elegirLugar(id, true);
    }, true);
  };
  $('mi-cuenta-salir').onclick = () => salir('/auth/salir').catch((error) => estado(error.message));
  $('mi-cuenta-salir-todos').onclick = () => salir('/auth/salir-todos').catch((error) => estado(error.message));
  montar();
  new MutationObserver(montar).observe(document.body, { childList: true, subtree: true });
  window.MiCuenta = { abrir, cerrar, marcar };
})();
