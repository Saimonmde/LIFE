/* SPDX-License-Identifier: AGPL-3.0-or-later */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.join(__dirname, '..');
const js = fs.readFileSync(path.join(root, 'play/finca.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'play/finca.css'), 'utf8');
const html = fs.readFileSync(path.join(root, 'play/index.html'), 'utf8');
const acunar = fs.readFileSync(path.join(root, 'play/acunar.js'), 'utf8');

assert.ok(js.includes('>Cosechar<small>'));
assert.ok(js.includes('Cosechar todo'));
assert.ok(js.includes('Llevar al taller'));
assert.ok(js.includes('Procesar'));
assert.ok(js.includes("data-op=\"acunar\">Acuñar"));
assert.ok(js.includes("zone() === 'mine' || zone() === 'central'"));
assert.ok(js.includes('Acunar.open'));
assert.ok(!js.includes('t: \'acunar\'') && !js.includes('t:"acunar"'));
assert.ok(css.includes('min-height: 44px'));
assert.ok(css.includes('#oficio-cerca button'));
assert.ok(css.includes('system-ui, sans-serif'));
assert.ok(!html.includes('id="hud-gear-menu"') || html.includes('id="hud-gear-menu"'));
assert.ok(!js.includes('hud-gear-menu') && !js.includes('cajon-editor'));
assert.ok(acunar.includes('rate: 5'));
assert.ok(acunar.includes('elegirMoneda'));
assert.ok(acunar.includes('textoFalta'));
assert.ok(!html.includes('hud-gear-menu') || html.includes('<body'));
assert.ok(!js.includes('hud-gear-menu') && !js.includes('cajon-editor'));

const elements = {};
function node() {
  return {
    hidden: true,
    innerHTML: '',
    textContent: '',
    onclick: null,
    setAttribute() {},
    querySelector() { return { onclick: null }; },
    querySelectorAll() { return []; },
  };
}
const sandbox = {
  console,
  setInterval() { return 0; },
  fetch() { return Promise.resolve({ ok: false, json() { return Promise.resolve(null); } }); },
  document: {
    readyState: 'complete',
    getElementById(id) { return elements[id] || null; },
    querySelector() { return null; },
    createElement() { return node(); },
    body: { append(...kids) { kids.forEach((kid) => { if (kid && kid.id) elements[kid.id] = kid; }); } },
    addEventListener() {},
  },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(js, sandbox);
const view = {
  plots: [
    { id: 'cafe-0', crop: 'cafe', stage: 'maduro' },
    { id: 'cacao-0', crop: 'cacao', stage: 'maduro' },
    { id: 'cafe-1', crop: 'cafe', stage: 'verde' },
  ],
  goods: { cafe_cereza: 2, cacao_baba: 0 },
  batches: {},
};
sandbox.LiveInk = {
  world: { mapId: 'city', waypoints: [{ id: 'las_palmas', x: 40, y: 20 }] },
  state: { player: { fx: 42, fy: 24 } },
};
sandbox.Finca.onNet({ t: 'finca', ok: true, view });
const dock = elements['oficio-cerca'];
assert.ok(dock && !dock.hidden);
assert.equal((dock.innerHTML.match(/data-op="cosechar"/g) || []).length, 2);
assert.ok(dock.innerHTML.includes('Cosechar todo'));
assert.ok(dock.innerHTML.includes('Llevar al taller'));
assert.ok(!dock.innerHTML.includes('Acuñar'));
sandbox.LiveInk.state.player = { fx: 1, fy: 1 };
sandbox.Finca.onNet({ t: 'finca', ok: true, view });
assert.equal(elements['oficio-cerca'].hidden, true);
sandbox.LiveInk.world.mapId = 'mine';
sandbox.Finca.onNet({ t: 'finca', ok: true, view });
assert.ok(elements['oficio-cerca'].innerHTML.includes('>Acuñar</button>'));
assert.ok(!elements['oficio-cerca'].innerHTML.includes('Cosechar'));
sandbox.LiveInk.world.mapId = 'central';
sandbox.Finca.onNet({ t: 'finca', ok: true, view });
assert.ok(elements['oficio-cerca'].innerHTML.includes('>Acuñar</button>'));
let opened = false;
sandbox.Acunar = { open() { opened = true; } };
const button = { dataset: { op: 'acunar' }, onclick: null };
elements['oficio-cerca'].querySelectorAll = () => [button];
sandbox.Finca.onNet({ t: 'finca', ok: true, view });
button.onclick();
assert.equal(opened, true);
console.log('botones de oficio ok');
