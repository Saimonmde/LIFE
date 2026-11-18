/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Filomancia: el encendedor y la madera prenden una fogata. El nivel maestro lanza fuegos artificiales. */
(function () {
  const RANGOS = [[1, 'Hacer fuego'], [2, 'Mantener la llama'], [3, 'Brasas'], [4, 'Chispa alta'], [5, 'Fuegos artificiales']];
  const MAESTRO = 5;
  const fuegos = new Map();
  const mallas = new Map();
  const vistos = new Set();
  let cielo = null;
  let chispas = [];
  let pendiente = '';

  function nivel(xp) {
    return Math.floor(Math.sqrt(Math.max(0, xp) / 25)) + 1;
  }
  function rango(xp) {
    let nombre = RANGOS[0][1];
    const actual = nivel(xp);
    for (const par of RANGOS) if (actual >= par[0]) nombre = par[1];
    return nombre;
  }
  function estado() { return window.LiveInk && LiveInk.state; }
  function xp() { const s = estado(); return s && s.xp ? (s.xp.filomancia || 0) : 0; }
  function tiene(id) {
    const s = estado();
    if (!s || !s.inv) return 0;
    return s.inv.reduce((n, slot) => n + (slot && slot.item === id ? (slot.qty || 1) : 0), 0);
  }

  function montar() {
    const s = estado();
    const mundo = window.LiveInk && LiveInk.world;
    if (!s || !mundo) return;
    if (!mundo.items.encendedor) {
      mundo.items.encendedor = {
        id: 'encendedor', name: 'Encendedor', category: 'tool', stackable: false, maxStack: 1,
        icon: { 16: 'graphics/icons/encendedor.svg', 32: 'graphics/icons/encendedor.svg', 64: 'graphics/icons/encendedor.svg' },
      };
    }
    mundo.skills.filomancia = {
      name: 'Filomancia', verb: 'Hacer fuego',
      learn: 'Empieza por hacer fuego: junta el encendedor con madera cortada. Luego vienen mantener la llama, las brasas y la chispa alta. El nivel maestro lanza fuegos artificiales.',
    };
    if (mundo.skills.order && mundo.skills.order.indexOf('filomancia') < 0) mundo.skills.order.push('filomancia');
    if (!tiene('encendedor') && LiveInk.giveItem) LiveInk.giveItem('encendedor', 1);
    if (window.Objeto && !Objeto.abrir.__filo) {
      const abrir = Objeto.abrir;
      const envuelto = function (item, qty) { const r = abrir.call(Objeto, item, qty); ponerBoton(item); return r; };
      envuelto.__filo = true;
      Objeto.abrir = envuelto;
    }
    requestAnimationFrame(dibujar);
  }

  function ponerBoton(item) {
    const caja = document.querySelector('#objeto .objeto-acciones');
    if (!caja) return;
    let boton = document.getElementById('objeto-fuego');
    const pareja = item === 'encendedor' ? 'madera' : (item === 'madera' ? 'encendedor' : '');
    if (!pareja || !tiene(pareja)) { if (boton) boton.hidden = true; return; }
    if (!boton) {
      boton = document.createElement('button');
      boton.type = 'button';
      boton.id = 'objeto-fuego';
      boton.textContent = 'Prender fogata';
      caja.append(boton);
      boton.onclick = () => prender();
    }
    boton.hidden = false;
  }

  function atar(slot, item) {
    if (item !== 'encendedor' && item !== 'madera') return;
    slot.draggable = true;
    slot.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('application/x-lifeinc-fuego', item);
      e.dataTransfer.setData('text/plain', item);
    });
    slot.addEventListener('dragover', (e) => {
      if (e.dataTransfer.types && [...e.dataTransfer.types].indexOf('application/x-lifeinc-fuego') >= 0) e.preventDefault();
    });
    slot.addEventListener('drop', (e) => {
      const otro = e.dataTransfer.getData('application/x-lifeinc-fuego');
      if ((item === 'encendedor' && otro === 'madera') || (item === 'madera' && otro === 'encendedor')) {
        e.preventDefault();
        prender();
      }
    });
  }

  function decir(texto, tono) {
    if (window.LiveInk && LiveInk.say) LiveInk.say(texto, tono || 'aviso');
  }

  function prender() {
    if (!tiene('encendedor')) { decir('Te falta el encendedor.'); return; }
    if (!tiene('madera')) { decir('Te falta madera cortada.'); return; }
    if (LiveInk.takeItem) LiveInk.takeItem('madera', 1);
    const s = estado();
    const local = { id: 'local-' + Date.now(), tipo: 'fogata', x: s.player.fx, y: s.player.fy, zone: (LiveInk.world.mapId || 'city'), hasta: Date.now() / 1000 + 60 };
    pendiente = local.id;
    recibir(local);
    if (LiveInk.grant) LiveInk.grant('filomancia', 8);
    decir('Prendes una fogata. Dura un minuto.', 'juego');
    if (window.flotar) window.flotar(s.player.x, s.player.y, '+ Filomancia');
    enviar('fogata');
    if (window.Objeto && Objeto.cerrar) Objeto.cerrar();
  }

  function lanzar() {
    if (!tiene('encendedor')) { decir('Te falta el encendedor.'); return; }
    if (nivel(xp()) < MAESTRO) { decir('Los fuegos artificiales son el nivel maestro de Filomancia.'); return; }
    const s = estado();
    recibir({ id: 'local-fuegos-' + Date.now(), tipo: 'fuegos', x: s.player.fx, y: s.player.fy, zone: (LiveInk.world.mapId || 'city'), hasta: Date.now() / 1000 + 8 });
    if (LiveInk.grant) LiveInk.grant('filomancia', 12);
    decir('Lanzas fuegos artificiales.', 'oro');
    enviar('fuegos', xp());
  }

  function enviar(tipo, puntos) {
    const s = estado();
    if (!s || !s.net || !s.net.ok || !s.net.ws) return;
    s.net.ws.send(JSON.stringify({ t: 'filomancia', tipo, xp: puntos || 0 }));
  }

  function onNet(m) {
    if (!m || m.t !== 'filomancia') return false;
    if (m.ok === false && m.error) {
      if (m.tipo === 'fogata' && pendiente && LiveInk.giveItem) LiveInk.giveItem('madera', 1);
      if (pendiente) quitar(pendiente);
      pendiente = '';
      decir(m.error);
      return true;
    }
    if (m.fuego && m.fuego.tipo === 'fogata') pendiente = '';
    for (const fuego of m.fuegos || []) recibir(fuego);
    if (m.fuego) recibir(m.fuego);
    return true;
  }

  function quitar(id) {
    const grupo = mallas.get(id);
    if (grupo && grupo.parent) grupo.parent.remove(grupo);
    mallas.delete(id);
    fuegos.delete(id);
  }
  function recibir(fuego) {
    if (!fuego || !fuego.id) return;
    if (String(fuego.id).indexOf('local-') !== 0 && fuego.tipo === 'fogata') {
      for (const id of [...fuegos.keys()]) if (String(id).indexOf('local-') === 0) quitar(id);
    }
    fuegos.set(fuego.id, fuego);
    if (fuego.tipo === 'fuegos' && !vistos.has(fuego.id)) {
      vistos.add(fuego.id);
      estallar();
    }
  }

  function fase(fuego) {
    const queda = fuego.hasta - Date.now() / 1000;
    if (queda <= 0) return 'apagada';
    if (queda <= 8) return 'brasas';
    return 'llama';
  }

  function malla(fuego) {
    const api = window.LIVE3D && LIVE3D.editorApi;
    if (!api || !api.T || !api.scene) return null;
    let grupo = mallas.get(fuego.id);
    if (grupo) return grupo;
    const T = api.T;
    grupo = new T.Group();
    const tronco = new T.Mesh(new T.BoxGeometry(0.95, 0.16, 0.24), new T.MeshStandardMaterial({ color: '#6b3a1c' }));
    tronco.rotation.y = 0.5;
    tronco.position.y = 0.12;
    const tronco2 = tronco.clone();
    tronco2.rotation.y = -0.6;
    grupo.add(tronco, tronco2);
    const llama = new T.Mesh(new T.ConeGeometry(0.26, 0.72, 7), new T.MeshBasicMaterial({ color: '#ffb15a' }));
    llama.position.y = 0.55;
    llama.name = 'llama';
    grupo.add(llama);
    const luz = new T.PointLight(0xff8a3a, 6, 14);
    luz.position.y = 0.6;
    grupo.add(luz);
    const y = api.height ? api.height(fuego.x, fuego.y) : 0;
    grupo.position.set(fuego.x * 2 + 1.8, y, fuego.y * 2 + 1.6);
    api.scene.add(grupo);
    mallas.set(fuego.id, grupo);
    return grupo;
  }

  function dibujar() {
    const ahora = Date.now() / 1000;
    for (const [id, fuego] of [...fuegos]) {
      if (fuego.hasta <= ahora || fuego.tipo !== 'fogata') {
        if (fuego.hasta <= ahora) quitar(id);
        continue;
      }
      const grupo = malla(fuego);
      if (!grupo) continue;
      const llama = grupo.getObjectByName('llama');
      const brasas = fase(fuego) === 'brasas';
      const pulso = 0.85 + Math.sin(ahora * (brasas ? 6 : 10)) * (brasas ? 0.08 : 0.15);
      if (llama) {
        llama.scale.set(brasas ? 0.45 : 1, pulso * (brasas ? 0.35 : 1), brasas ? 0.45 : 1);
        llama.material.color.set(brasas ? '#c4512a' : '#ffb15a');
      }
    }
    const capa = document.getElementById('fuegos-cielo');
    if (capa) {
      const ctx = capa.getContext('2d');
      if (capa.width !== innerWidth) { capa.width = innerWidth; capa.height = innerHeight; }
      ctx.clearRect(0, 0, capa.width, capa.height);
      chispas = chispas.filter((p) => {
        p.v += 0.08;
        p.y += p.v;
        p.x += p.vx;
        p.vida -= 1;
        ctx.globalAlpha = Math.max(0, p.vida / 40);
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.vida > 24 ? (p.r || 4) : 2, 0, Math.PI * 2);
        ctx.fill();
        return p.vida > 0 && p.y < capa.height + 20;
      });
      ctx.globalAlpha = 1;
    }
    const boton = document.getElementById('pirotecnia');
    if (boton) boton.hidden = !(document.body.classList.contains('in-game') && tiene('encendedor') && nivel(xp()) >= MAESTRO);
    requestAnimationFrame(dibujar);
  }

  function estallar() {
    const capa = cielo || document.getElementById('fuegos-cielo');
    if (!capa) return;
    const colores = ['#ffd56a', '#ff7a4a', '#fff4d2', '#7ed0ff', '#ff4d6a'];
    for (const parte of [0, 1]) {
      const cx = innerWidth * (0.32 + parte * 0.28);
      const cy = innerHeight * (0.16 + parte * 0.08);
      for (let i = 0; i < 64; i++) {
        const ang = (Math.PI * 2 * i) / 64;
        chispas.push({ x: cx, y: cy, vx: Math.cos(ang) * (2.2 + Math.random() * 1.4), v: Math.sin(ang) * 2.2 - 0.4, vida: 48, r: 3 + (i % 4), color: colores[i % colores.length] });
      }
    }
  }

  function asegurar() {
    if (document.getElementById('fuegos-cielo')) return;
    cielo = document.createElement('canvas');
    cielo.id = 'fuegos-cielo';
    document.body.append(cielo);
    const boton = document.createElement('button');
    boton.id = 'pirotecnia';
    boton.type = 'button';
    boton.hidden = true;
    boton.textContent = 'Fuegos artificiales';
    boton.onclick = lanzar;
    document.body.append(boton);
  }

  asegurar();
  window.Filomancia = { montar, atar, onNet, prender, lanzar, nivel, rango };
})();
