/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* El baúl de la mina abre en la mina y las cifras se leen en SMC.
   La ficha explica el objeto y mueve 1, 10, 100, X o todo. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const page = read('play/index.html');
const game = read('play/game.js');
const ui = read('play/baul.js');
const css = read('play/baul.css');
assert.ok(page.includes('id="baul-mina"'));
assert.ok(page.includes('data-cierra="baul-mina"'));
assert.ok(page.includes('id="baul-abrir"'));
assert.ok(page.includes('baul.js?v=ficha'));
assert.ok(page.includes('baul.css?v=ficha'));
assert.ok(game.includes("d.type === 'mine_chest'"));
assert.ok(game.includes('Baul.open()'));
assert.ok(game.includes("DESTINO_IDS=new Set(['mina'"));
assert.ok(game.includes("m.id === 'mina'"));
assert.ok(ui.includes("t: 'baul_mover'"));
assert.ok(ui.includes("t: 'baul_smc'"));
assert.ok(ui.includes('Guardar todo'));
assert.ok(ui.includes('Sacar todo'));
assert.ok(ui.includes('class="casillas"'));
assert.ok(ui.includes('casilla-n'));
assert.ok(ui.includes('Encima'));
assert.ok(ui.includes('Baúl'));
assert.ok(ui.includes('class="baul-ficha"'));
assert.ok(ui.includes("botonCantidad('1'"));
assert.ok(ui.includes("botonCantidad('10'"));
assert.ok(ui.includes("botonCantidad('100'"));
assert.ok(ui.includes("botonCantidad('x'"));
assert.ok(ui.includes("botonCantidad('all'"));
assert.ok(ui.includes('data-cant="'));
assert.ok(ui.includes('const FICHAS = {'));
assert.ok(ui.includes('Se saca picando en las minas; se funde en el horno para acuñar Simoncoins a 0,001 SMC.'));
assert.ok(ui.includes('Objeto de tu cuenta. Puedes llevarlo encima o guardarlo en el baúl.'));
assert.ok(ui.includes('<svg'));
assert.ok(css.includes('.casillas'));
assert.ok(css.includes('.baul-ficha'));
assert.ok(css.includes('.casilla.sel'));
assert.ok(css.includes('data-nombre'));
assert.ok(css.includes('hover'));
assert.ok(css.includes('min-height: 72px') || css.includes('min-height:72px'));
assert.ok(css.includes('min-height: 48px') || css.includes('min-height:48px'));
const iconBlock = ui.slice(ui.indexOf('const tabla = {'), ui.indexOf('};', ui.indexOf('const tabla = {')));
const fichaBlock = ui.slice(ui.indexOf('const FICHAS = {'), ui.indexOf('};', ui.indexOf('const FICHAS = {')));
const iconIds = [...iconBlock.matchAll(/^\s+([a-z0-9_]+):/gm)].map((m) => m[1]);
assert.ok(iconIds.includes('smc') && iconIds.includes('mineral_cobre') && iconIds.includes('madera'));
for (const id of iconIds) assert.ok(fichaBlock.includes(id + ':'), 'falta ficha de ' + id);
for (const banned of ['jagex', 'osrs', 'runescape']) {
  assert.ok(!ui.toLowerCase().includes(banned), banned);
  assert.ok(!css.toLowerCase().includes(banned), banned);
}
const trade = read('play/economy-ui.js');
const tradeCss = read('play/economy.css');
assert.ok(trade.includes('id="trade-uno"'));
assert.ok(trade.includes('id="trade-x"'));
assert.ok(trade.includes('>Todo<'));
assert.ok(trade.includes('trade-ico'));
assert.ok(trade.includes('walletName'));
assert.ok(trade.includes('balanceSubs'));
assert.ok(tradeCss.includes('#coin-trade .trade-card'));
assert.ok(tradeCss.includes('aspect-ratio:1'));
for (const banned of ['SMH', 'SMP', 'SPH', 'Simonchi', 'Simonplata']) {
  assert.ok(!ui.includes(banned), banned);
  assert.ok(!css.includes(banned), banned);
}
const chest = page.slice(page.indexOf('id="baul-mina"'), page.indexOf('id="autotest"'));
for (const banned of ['SMH', 'SMP', 'SPH']) assert.ok(!chest.includes(banned), banned);

function decode(text) {
  return String(text).replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}
function matchCompound(el, compound) {
  const re = /#([\w-]+)|\.([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]|([A-Za-z][\w-]*)/g;
  let part = false;
  let m;
  while ((m = re.exec(compound))) {
    part = true;
    if (m[1] && el.id !== m[1]) return false;
    if (m[2] && !el.classList.contains(m[2])) return false;
    if (m[3] && (m[4] === undefined ? !el.hasAttribute(m[3]) : el.getAttribute(m[3]) !== m[4])) return false;
    if (m[5] && el.tagName !== m[5].toUpperCase()) return false;
  }
  return part;
}
function matches(el, selector) {
  const compounds = selector.trim().split(/\s+/);
  let node = el;
  for (let i = compounds.length - 1; i >= 0; i--) {
    if (i === compounds.length - 1) {
      if (!matchCompound(node, compounds[i])) return false;
    } else {
      let found = null;
      for (let anc = node.parentElement; anc; anc = anc.parentElement) {
        if (matchCompound(anc, compounds[i])) { found = anc; break; }
      }
      if (!found) return false;
      node = found;
    }
  }
  return true;
}
class ClassList {
  constructor(el) { this.el = el; }
  items() { return String(this.el.className || '').split(/\s+/).filter(Boolean); }
  contains(name) { return this.items().includes(name); }
  add(name) { if (!this.contains(name)) this.el.className = (this.items().concat(name)).join(' '); }
  remove(name) { this.el.className = this.items().filter((item) => item !== name).join(' '); }
  toggle(name, force) {
    const on = force === undefined ? !this.contains(name) : !!force;
    if (on) this.add(name); else this.remove(name);
    return on;
  }
}
class El {
  constructor(tag) {
    this.tagName = String(tag || '').toUpperCase();
    this.children = [];
    this.parentElement = null;
    this.className = '';
    this.id = '';
    this.attrs = {};
    this.listeners = {};
    this.classList = new ClassList(this);
    this.dataset = {};
    this._value = '';
  }
  get hidden() { return this.hasAttribute('hidden'); }
  set hidden(value) { if (value) this.setAttribute('hidden', ''); else this.removeAttribute('hidden'); }
  get disabled() { return this.hasAttribute('disabled'); }
  set disabled(value) { if (value) this.setAttribute('disabled', ''); else this.removeAttribute('disabled'); }
  get value() { return this._value; }
  set value(value) { this._value = String(value == null ? '' : value); }
  get textContent() {
    return this.children.map((child) => (typeof child === 'string' ? child : child.textContent)).join('');
  }
  set innerHTML(html) {
    this.children = [];
    parseInto(this, html);
  }
  append(child) {
    child.parentElement = this;
    this.children.push(child);
  }
  setAttribute(name, value) {
    this.attrs[name] = String(value);
    if (name === 'id') this.id = String(value);
    if (name === 'class') this.className = String(value);
    if (name === 'value') this._value = String(value);
    if (name.startsWith('data-')) {
      const key = name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      this.dataset[key] = String(value);
    }
  }
  getAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attrs, name) ? this.attrs[name] : null; }
  hasAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attrs, name); }
  removeAttribute(name) {
    delete this.attrs[name];
    if (name.startsWith('data-')) {
      const key = name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      delete this.dataset[key];
    }
  }
  addEventListener(type, fn) {
    (this.listeners[type] || (this.listeners[type] = [])).push(fn);
  }
  dispatchEvent(event) {
    const ev = Object.assign({ target: this, preventDefault() {}, stopPropagation() {} }, event || {});
    for (const fn of this.listeners[ev.type] || []) fn(ev);
    return ev;
  }
  click() {
    if (this.disabled) return;
    this.dispatchEvent({ type: 'click' });
  }
  closest(selector) {
    let node = this;
    while (node) {
      if (node.tagName && matches(node, selector)) return node;
      node = node.parentElement;
    }
    return null;
  }
  querySelectorAll(selector) {
    const found = [];
    const walk = (node) => {
      for (const child of node.children) {
        if (typeof child === 'string') continue;
        if (matches(child, selector)) found.push(child);
        walk(child);
      }
    };
    walk(this);
    return found;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
function parseInto(parent, html) {
  const re = /<!--[\s\S]*?-->|<(\/?)([A-Za-z][\w:-]*)([^>]*?)(\/?)>|([^<]+)/g;
  const stack = [parent];
  const voidTags = new Set(['AREA', 'BASE', 'BR', 'COL', 'EMBED', 'HR', 'IMG', 'INPUT', 'LINK', 'META', 'SOURCE', 'TRACK', 'WBR']);
  let m;
  while ((m = re.exec(html))) {
    if (m[0].startsWith('<!--')) continue;
    if (m[5] != null) {
      const text = decode(m[5]);
      if (text) stack[stack.length - 1].children.push(text);
      continue;
    }
    const close = m[1] === '/';
    const tag = m[2].toUpperCase();
    if (close) {
      if (stack.length > 1 && stack[stack.length - 1].tagName === tag) stack.pop();
      continue;
    }
    const el = new El(tag);
    const attrRe = /([:@\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?/g;
    let a;
    while ((a = attrRe.exec(m[3] || ''))) {
      const value = a[2] != null ? a[2] : (a[3] != null ? a[3] : (a[4] != null ? a[4] : ''));
      el.setAttribute(a[1], decode(value));
    }
    stack[stack.length - 1].append(el);
    if (!(m[4] === '/' || voidTags.has(tag))) stack.push(el);
  }
}

const body = new El('body');
const docListeners = [];
const documentMock = {
  body,
  getElementById(id) {
    const walk = (node) => {
      for (const child of node.children || []) {
        if (typeof child === 'string') continue;
        if (child.id === id) return child;
        const found = walk(child);
        if (found) return found;
      }
      return null;
    };
    return walk(body);
  },
  addEventListener(type, fn) { docListeners.push({ type, fn }); },
  querySelector(selector) { return body.querySelector(selector); },
  querySelectorAll(selector) { return body.querySelectorAll(selector); },
  dispatch(event) {
    const ev = Object.assign({ target: body, preventDefault() {}, stopPropagation() {} }, event);
    for (const row of docListeners) if (row.type === ev.type) row.fn(ev);
  },
};
body.innerHTML = '<section id="baul-mina" class="ventana" hidden><header><span id="baul-titulo">Baúl de la mina</span></header><div id="baul-cuerpo"></div></section><button type="button" id="baul-abrir" hidden>Abrir baúl</button>';
const sent = [];
const said = [];
global.window = global;
global.document = documentMock;
global.LiveInk = {
  state: {
    net: { ok: true, ws: { readyState: 1, send(raw) { sent.push(JSON.parse(raw)); } } },
    walletLocked: false,
  },
  say(text, tone) { said.push({ text, tone }); },
};
global.setInterval = () => 0;
vm.runInThisContext(ui, { filename: 'play/baul.js' });

function vista(extra) {
  return Object.assign({
    smc: {
      billetera: { exacto: '2,5 SMC', compacto: '2,5 SMC' },
      baul: { exacto: '0,5 SMC', compacto: '0,5 SMC' },
      total: { exacto: '3 SMC', compacto: '3 SMC' },
      escala: 'Las cantidades se muestran en SMC.',
      topes: '',
      tope: '21.000.000 SMC',
    },
    filas: [
      { id: 'mineral_cobre', name: 'Cobre', grupo: 'mineral', encima: 12, baul: 3, total: 15 },
      { id: 'madera', name: 'Madera', grupo: 'recurso', encima: 100, baul: 0, total: 100 },
    ],
    totales: { encima: 112, baul: 3, mineral: 15, recurso: 100 },
  }, extra || {});
}
function slot(lado, id) {
  return documentMock.querySelectorAll('.casilla[data-lado]').find((el) => el.dataset.lado === lado && el.dataset.item === id);
}
function cant(id) {
  const ficha = documentMock.querySelector('.baul-ficha');
  assert.ok(ficha, 'la ficha está abierta');
  return ficha.querySelector('[data-cant="' + id + '"]');
}
function fichaTexto() {
  const ficha = documentMock.querySelector('.baul-ficha');
  assert.ok(ficha, 'la ficha está abierta');
  return ficha.textContent;
}
const panel = documentMock.getElementById('baul-mina');
panel.hidden = false;
Baul.paint(vista());
const cobre = slot('encima', 'mineral_cobre');
assert.strictEqual(cobre.getAttribute('title'), 'Mineral de cobre');
assert.strictEqual(cobre.getAttribute('data-nombre'), 'Mineral de cobre');
cobre.click();
assert.ok(cobre.classList.contains('sel') || slot('encima', 'mineral_cobre').classList.contains('sel'));
assert.ok(fichaTexto().includes('Mineral de cobre'));
assert.ok(fichaTexto().includes('Se saca picando en las minas; se funde en el horno para acuñar Simoncoins a 0,001 SMC.'));
assert.ok(fichaTexto().includes('Encima'));
assert.ok(fichaTexto().includes('Baúl'));
assert.ok(fichaTexto().includes('12'));
assert.ok(fichaTexto().includes('3'));
assert.strictEqual(cant('1').disabled, false);
assert.strictEqual(cant('10').disabled, false);
assert.strictEqual(cant('100').disabled, true);
assert.strictEqual(cant('x').disabled, true);
assert.strictEqual(cant('all').disabled, false);
assert.strictEqual(cant('10').textContent, '10');
assert.ok(fichaTexto().includes('Guardar'));
cant('100').click();
assert.strictEqual(sent.length, 0);
cant('10').click();
assert.strictEqual(sent.length, 1);
assert.strictEqual(sent[0].t, 'baul_mover');
assert.strictEqual(sent[0].op, 'deposit');
assert.strictEqual(sent[0].item, 'mineral_cobre');
assert.strictEqual(sent[0].all, false);
assert.strictEqual(sent[0].qty, 10);
assert.ok(String(sent[0].token || '').startsWith('b'));
const monto = documentMock.getElementById('baul-ficha-monto');
monto.value = '13';
monto.dispatchEvent({ type: 'input' });
assert.strictEqual(cant('x').disabled, true);
cant('x').click();
assert.strictEqual(sent.length, 1);
monto.value = '1,5';
monto.dispatchEvent({ type: 'input' });
assert.strictEqual(cant('x').disabled, true, 'un objeto no acepta decimales');
monto.value = '12';
monto.dispatchEvent({ type: 'input' });
assert.strictEqual(cant('x').disabled, false);
cant('x').click();
assert.strictEqual(sent[1].qty, 12);
assert.strictEqual(sent[1].all, false);
cant('all').click();
assert.strictEqual(sent[2].qty, 'all');
assert.strictEqual(sent[2].all, true);
assert.strictEqual(sent[2].op, 'deposit');

slot('baul', 'mineral_cobre').click();
assert.ok(slot('baul', 'mineral_cobre').classList.contains('sel'));
assert.ok(fichaTexto().includes('Sacar'));
assert.strictEqual(cant('1').disabled, false);
assert.strictEqual(cant('10').disabled, true);
assert.strictEqual(cant('100').disabled, true);
cant('1').click();
assert.strictEqual(sent[3].t, 'baul_mover');
assert.strictEqual(sent[3].op, 'withdraw');
assert.strictEqual(sent[3].item, 'mineral_cobre');
assert.strictEqual(sent[3].qty, 1);
assert.strictEqual(sent[3].all, false);

slot('encima', 'madera').click();
assert.ok(fichaTexto().includes('Madera'));
assert.ok(fichaTexto().includes('Tronco cortado'));
assert.strictEqual(cant('100').disabled, false);
cant('100').click();
assert.strictEqual(sent[4].qty, 100);
assert.strictEqual(sent[4].item, 'madera');
assert.strictEqual(sent[4].op, 'deposit');

slot('encima', 'smc').click();
assert.ok(fichaTexto().includes('Simoncoin'));
assert.ok(fichaTexto().includes('La moneda de Saimon City'));
assert.ok(fichaTexto().includes('2,50 SMC'), fichaTexto());
assert.ok(fichaTexto().includes('0,50 SMC'), fichaTexto());
assert.strictEqual(cant('1').disabled, false);
assert.strictEqual(cant('10').disabled, true);
assert.strictEqual(cant('100').disabled, true);
assert.strictEqual(cant('all').disabled, false);
cant('1').click();
assert.strictEqual(sent[5].t, 'baul_smc');
assert.strictEqual(sent[5].op, 'deposit');
assert.strictEqual(sent[5].all, false);
assert.strictEqual(sent[5].amount, '1');
const campoSmc = documentMock.getElementById('baul-ficha-monto');
campoSmc.value = '2,51';
campoSmc.dispatchEvent({ type: 'input' });
assert.strictEqual(cant('x').disabled, true);
cant('x').click();
assert.strictEqual(sent.length, 6);
campoSmc.value = '2,5';
campoSmc.dispatchEvent({ type: 'input' });
assert.strictEqual(cant('x').disabled, false);
cant('x').click();
assert.strictEqual(sent[6].t, 'baul_smc');
assert.strictEqual(sent[6].amount, '2,5');
assert.strictEqual(sent[6].all, false);
assert.strictEqual(sent[6].op, 'deposit');
cant('all').click();
assert.strictEqual(sent[7].t, 'baul_smc');
assert.strictEqual(sent[7].all, true);
assert.strictEqual(sent[7].amount, 'all');

slot('baul', 'smc').click();
assert.ok(fichaTexto().includes('Sacar'));
assert.ok(fichaTexto().includes('0,50 SMC'));
assert.strictEqual(cant('1').disabled, true, '1 SMC no cabe en 0,50');
assert.strictEqual(cant('10').disabled, true);
assert.strictEqual(cant('100').disabled, true);
assert.strictEqual(cant('all').disabled, false);
const campoPoco = documentMock.getElementById('baul-ficha-monto');
campoPoco.value = '0,50';
campoPoco.dispatchEvent({ type: 'input' });
assert.strictEqual(cant('x').disabled, false);
cant('x').click();
assert.strictEqual(sent[8].t, 'baul_smc');
assert.strictEqual(sent[8].op, 'withdraw');
assert.strictEqual(sent[8].amount, '0,50');
assert.strictEqual(sent[8].all, false);
campoPoco.value = '0,501';
campoPoco.dispatchEvent({ type: 'input' });
assert.strictEqual(cant('x').disabled, true);

Baul.onNet({ t: 'baul', ok: false, reason: 'No hay esa cantidad.', view: vista() });
assert.ok(fichaTexto().includes('No hay esa cantidad.'));
assert.strictEqual(said.at(-1).text, 'No hay esa cantidad.');
assert.strictEqual(said.at(-1).tone, 'aviso');
Baul.onNet({ t: 'baul', ok: true, reason: '', view: vista() });
assert.ok(!fichaTexto().includes('No hay esa cantidad.'));

const cero = vista();
cero.smc = {
  billetera: { exacto: '0 SMC' },
  baul: { exacto: '0 SMC' },
  total: { exacto: '0 SMC' },
  escala: 'Las cantidades se muestran en SMC.',
  topes: '',
  tope: '21.000.000 SMC',
};
Baul.paint(cero);
slot('encima', 'smc').click();
assert.ok(fichaTexto().includes('0,00 SMC'));
for (const id of ['1', '10', '100', 'x', 'all']) assert.strictEqual(cant(id).disabled, true, id);

Baul.paint(vista({
  filas: [{ id: 'mango', name: 'Mango', grupo: 'recurso', encima: 2, baul: 0, total: 2 }],
}));
slot('encima', 'mango').click();
assert.ok(fichaTexto().includes('Mango'));
assert.ok(fichaTexto().includes('Objeto de tu cuenta. Puedes llevarlo encima o guardarlo en el baúl.'));
assert.strictEqual(slot('encima', 'mango').getAttribute('title'), 'Mango');

documentMock.querySelector('.baul-ficha-x').click();
assert.strictEqual(documentMock.querySelector('.baul-ficha'), null);
assert.ok(slot('encima', 'mango').classList.contains('sel'));
slot('encima', 'mango').click();
assert.ok(documentMock.querySelector('.baul-ficha'));
documentMock.dispatch({ type: 'keydown', key: 'Escape', target: body });
assert.strictEqual(documentMock.querySelector('.baul-ficha'), null);
assert.ok(slot('encima', 'mango').classList.contains('sel'));
slot('encima', 'smc').click();
assert.ok(documentMock.querySelector('.baul-ficha'));
documentMock.dispatch({ type: 'pointerdown', button: 0, target: slot('encima', 'smc') });
assert.ok(documentMock.querySelector('.baul-ficha'), 'tocar la casilla no cierra la ficha');
documentMock.dispatch({ type: 'pointerdown', button: 0, target: documentMock.querySelector('.baul-nota') });
assert.strictEqual(documentMock.querySelector('.baul-ficha'), null);

console.log('baúl de la mina ok');
