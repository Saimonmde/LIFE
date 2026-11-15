/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Panel de administración. Español, vidrio oscuro y línea de oro, sin tapar el minimapa ni el chat. */
(function (root) {
  'use strict';
  const TABS = [
    ['caminos', 'Caminos', icon('path')],
    ['objetos', 'Objetos', icon('box')],
    ['terreno', 'Terreno', icon('mountain')],
    ['vegetacion', 'Vegetación', icon('tree')],
    ['superficies', 'Superficies', icon('paint')],
    ['disenos', 'Diseños', icon('stack')],
  ];
  const PROPS = [
    ['palma', 'Palma'], ['guayacan', 'Guayacán'], ['sombra', 'Sombra'], ['arbusto', 'Arbusto'],
    ['flores', 'Flores'], ['pasto', 'Pasto'], ['cafe', 'Cafeto'], ['cacao', 'Cacao'],
    ['roca', 'Roca'], ['cerca', 'Cerca'], ['banca', 'Banca'], ['farol', 'Farola'],
    ['letrero', 'Letrero'], ['fuente', 'Fuente'],
  ];
  const MATERIALS = [
    ['grass', 'Pasto'], ['dirt', 'Tierra'], ['sand', 'Arena'], ['stone', 'Piedra'],
    ['brick', 'Ladrillo'], ['asphalt', 'Asfalto'], ['water', 'Orilla de agua'],
  ];
  const PALETTES = {
    valle: ['#74875b', '#c4ac87', '#baa47a', '#8d7355', '#357f8b'],
    pueblo: ['#c4784e', '#a85a3a', '#e2cda0', '#6b4a2c', '#d9d3c7'],
    piedra: ['#9aa0a2', '#7c8286', '#b5b7b2', '#5c6158', '#d9d3c7'],
  };

  function icon(name) {
    const paths = {
      path: 'M4 16c4-8 12-8 16 0',
      box: 'M4 8l8-4 8 4-8 4-8-4zm0 0v8l8 4 8-4V8',
      mountain: 'M3 18l6-9 4 5 3-4 5 8H3z',
      tree: 'M12 20V10M12 13l-4 3M12 11l4 3M8 8c0-3 8-3 8 0 2 0 3 3 0 4H8c-3-1-2-4 0-4z',
      paint: 'M6 16c0 2 2 3 3 3h1v-2H9c-.5 0-1-.5-1-1s.5-1 1-1h6c2 0 3-2 3-4 0-4-3-6-8-6S4 7 4 11c0 2 .5 3 2 5z',
      stack: 'M4 8l8-3 8 3-8 3-8-3zm0 4l8 3 8-3M4 16l8 3 8-3',
    };
    return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + (paths[name] || paths.box) + '"/></svg>';
  }

  function mount(hooks) {
    const aside = document.createElement('aside');
    aside.id = 'editor-panel';
    aside.hidden = true;
    aside.dataset.tab = 'caminos';
    aside.setAttribute('aria-label', 'Editar mundo');
    const state = {
      tab: 'caminos', pathStyle: 'piedra', brush: '1', mode: 'paint', strength: 1,
      terrainOp: 'raise', density: 3, propType: 'palma', material: 'grass', tint: '#74875b',
      snap: true, scale: 1, rot: 0,
      layers: { terrain: true, paths: true, vegetation: true, decoration: true },
    };
    let silent = false;
    aside.innerHTML = [
      '<header class="ed-head"><strong>Editar mundo</strong>',
      '<button type="button" data-act="collapse" id="ed-colapsar" aria-expanded="true">Ocultar</button>',
      '<button type="button" data-act="save">Guardar</button>',
      '<button type="button" data-act="exit">Salir</button></header>',
      '<p id="ed-status" role="status">Los cambios se publican al guardar.</p>',
      '<nav class="ed-tabs">' + TABS.map(([id, label, svg]) => '<button type="button" data-tab="' + id + '">' + svg + '<span>' + label + '</span></button>').join('') + '</nav>',
      '<div class="ed-scroll">',
      section('caminos', [
        '<div class="ed-row">',
        choice('pathStyle', 'piedra', 'Camino de piedra'),
        choice('pathStyle', 'adoquin', 'Adoquín'),
        choice('pathStyle', 'carretera', 'Carretera'),
        '</div>',
        modes(),
        brushes(),
      ].join('')),
      section('objetos', [
        '<p id="ed-sel">Nada seleccionado. Toca un objeto del mapa.</p>',
        '<label>Escala <input id="ed-scale" type="range" min="0.25" max="4" step="0.05" value="1"></label>',
        '<label>Giro libre <input id="ed-rot" type="range" min="0" max="360" step="1" value="0"><span id="ed-rot-n">0°</span></label>',
        '<div class="ed-row">',
        '<button type="button" data-act="rot" data-delta="-15">−15°</button>',
        '<button type="button" data-act="rot" data-delta="15">+15°</button>',
        '<button type="button" data-act="duplicate">Duplicar</button>',
        '<button type="button" data-act="delete">Borrar</button>',
        '</div>',
        '<p class="ed-note">Arrastra el objeto o las flechas. Las flechas del teclado lo empujan. Imantar lo deja en la cuadrícula.</p>',
        '<div id="ed-list"></div>',
      ].join('')),
      section('terreno', [
        '<div class="ed-row">',
        choice('terrainOp', 'raise', 'Subir'),
        choice('terrainOp', 'lower', 'Bajar'),
        choice('terrainOp', 'flatten', 'Aplanar'),
        choice('terrainOp', 'smooth', 'Suavizar'),
        '</div>',
        brushes(),
        '<label>Fuerza <input id="ed-strength" type="range" min="0.25" max="2" step="0.25" value="1"></label>',
        modes(),
      ].join('')),
      section('vegetacion', [
        '<div class="ed-grid" id="ed-props">' + PROPS.map(([id, label]) => '<button type="button" data-prop="' + id + '">' + label + '</button>').join('') + '</div>',
        '<label>Densidad del pincel <input id="ed-density" type="range" min="1" max="8" step="1" value="3"></label>',
        brushes(),
        modes(),
      ].join('')),
      section('superficies', [
        '<div class="ed-row">' + MATERIALS.map(([id, label]) => choice('material', id, label)).join('') + '</div>',
        '<label>Tinte <input id="ed-tint" type="color" value="#74875b"></label>',
        '<div class="ed-swatches" id="ed-swatches"></div>',
        brushes(),
        modes(),
      ].join('')),
      section('disenos', [
        '<label>Nombre <input id="ed-design-name" maxlength="40" placeholder="Plaza norte"></label>',
        '<div class="ed-row">',
        '<button type="button" data-act="save-design">Guardar diseño</button>',
        '<button type="button" data-act="export-current">Exportar JSON</button>',
        '</div>',
        '<div id="ed-designs"></div>',
        '<div class="ed-row"><button type="button" id="ed-elegir">Elegir archivo</button><span id="ed-file-name">Ningún archivo</span></div>',
        '<input id="ed-import" type="file" accept="application/json" hidden>',
        '<label>Confirmación <input id="ed-confirm" maxlength="16" placeholder="PROMOVER" autocomplete="off"></label>',
        '<div class="ed-row">',
        '<button type="button" data-act="import">Importar</button>',
        '<button type="button" data-act="revert">Volver al mapa base</button>',
        '</div>',
        '<div id="ed-preview-tools">',
        '<button type="button" data-act="seed">Sembrar muestra</button>',
        '<button type="button" data-act="reset">Restablecer muestras</button>',
        '</div>',
        '<h3>Historial</h3><div id="ed-history"></div>',
      ].join('')),
      '<div class="ed-tools">',
      '<button type="button" data-act="undo">Deshacer</button>',
      '<button type="button" data-act="redo">Rehacer</button>',
      '<button type="button" data-act="eyedropper">Cuentagotas</button>',
      '<button type="button" data-act="box">Caja</button>',
      '<button type="button" data-act="copy">Copiar</button>',
      '<button type="button" data-act="paste">Pegar</button>',
      '<button type="button" data-act="preview">Vista previa</button>',
      '<button type="button" data-act="fly">Volar</button>',
      '<label class="ed-check"><input id="ed-snap" type="checkbox" checked> Imantar</label>',
      '</div>',
      '<div class="ed-layers">',
      layer('terrain', 'Relieve'), layer('paths', 'Caminos'), layer('vegetation', 'Vegetación'), layer('decoration', 'Decoración'),
      '</div>',
      '</div>',
    ].join('');
    document.body.append(aside);
    paintSwatches();
    markActive();

    aside.addEventListener('click', (e) => {
      const tab = e.target.closest('[data-tab]');
      if (tab) {
        state.tab = tab.dataset.tab;
        aside.dataset.tab = state.tab;
        markActive();
        emit('tab');
        return;
      }
      const choiceBtn = e.target.closest('[data-choice]');
      if (choiceBtn) {
        state[choiceBtn.dataset.choice] = choiceBtn.dataset.value;
        markActive();
        emit('change');
        return;
      }
      const prop = e.target.closest('[data-prop]');
      if (prop) {
        state.propType = prop.dataset.prop;
        state.tab = 'vegetacion';
        markActive();
        emit('change');
        return;
      }
      const act = e.target.closest('[data-act]');
      if (act) {
        hooks.action(act.dataset.act, Object.assign(readExtra(), {
          id: act.dataset.id || '',
          version: act.dataset.version ? Number(act.dataset.version) : null,
          delta: act.dataset.delta ? Number(act.dataset.delta) : null,
        }));
        return;
      }
      const row = e.target.closest('#ed-list [data-id]');
      if (row) hooks.action('select-row', { kind: row.dataset.kind, id: row.dataset.id });
    });
    aside.addEventListener('input', (e) => {
      if (silent) return;
      if (e.target.id === 'ed-scale') { state.scale = Number(e.target.value); hooks.action('scale', { value: state.scale, live: true }); }
      else if (e.target.id === 'ed-rot') { state.rot = Number(e.target.value); aside.querySelector('#ed-rot-n').textContent = state.rot + '°'; hooks.action('rot-set', { value: state.rot, live: true }); }
      else if (e.target.id === 'ed-strength') state.strength = Number(e.target.value);
      else if (e.target.id === 'ed-density') state.density = Number(e.target.value);
      else if (e.target.id === 'ed-tint') { state.tint = e.target.value; emit('change'); }
      else if (e.target.id === 'ed-snap') state.snap = e.target.checked;
      else if (e.target.dataset.layer) { state.layers[e.target.dataset.layer] = e.target.checked; hooks.action('layers', state.layers); }
    });
    aside.querySelector('#ed-elegir').onclick = () => aside.querySelector('#ed-import').click();
    aside.addEventListener('change', (e) => {
      if (e.target.id === 'ed-scale') hooks.action('scale', { value: state.scale, live: false });
      if (e.target.id === 'ed-rot') hooks.action('rot-set', { value: state.rot, live: false });
      if (e.target.id === 'ed-import') {
        const file = e.target.files && e.target.files[0];
        aside.querySelector('#ed-file-name').textContent = file ? file.name : 'Ningún archivo';
        hooks.action('file', { file: file });
      }
    });

    function emit(name) { if (!silent && hooks[name]) hooks[name](state); }
    function readExtra() {
      return {
        name: (aside.querySelector('#ed-design-name').value || '').trim(),
        confirm: (aside.querySelector('#ed-confirm').value || '').trim(),
      };
    }
    function markActive() {
      aside.querySelectorAll('[data-tab]').forEach(btn => btn.classList.toggle('on', btn.dataset.tab === state.tab));
      aside.querySelectorAll('[data-choice]').forEach(btn => btn.classList.toggle('on', state[btn.dataset.choice] === btn.dataset.value));
      aside.querySelectorAll('[data-prop]').forEach(btn => btn.classList.toggle('on', btn.dataset.prop === state.propType));
    }
    function paintSwatches() {
      const box = aside.querySelector('#ed-swatches');
      Object.entries(PALETTES).forEach(([name, colors]) => {
        const row = document.createElement('div');
        row.className = 'ed-palette';
        colors.forEach(color => {
          const b = document.createElement('button');
          b.type = 'button';
          b.style.background = color;
          b.title = name;
          b.onclick = () => { state.tint = color; aside.querySelector('#ed-tint').value = color; emit('change'); };
          row.append(b);
        });
        box.append(row);
      });
    }
    return {
      el: aside,
      state: () => state,
      show(on) { aside.hidden = !on; },
      preview(on) { aside.classList.toggle('ed-preview', !!on); },
      status(text) { aside.querySelector('#ed-status').textContent = text; },
      setSelection(label, scale, rot) {
        aside.querySelector('#ed-sel').textContent = label;
        silent = true;
        if (scale != null) { state.scale = scale; aside.querySelector('#ed-scale').value = String(scale); }
        if (rot != null) { state.rot = rot; aside.querySelector('#ed-rot').value = String(rot); aside.querySelector('#ed-rot-n').textContent = rot + '°'; }
        silent = false;
      },
      setList(rows) {
        aside.querySelector('#ed-list').innerHTML = rows.map(row => '<button type="button" data-kind="' + row.kind + '" data-id="' + escapeAttr(row.id) + '">' + escapeText(row.label) + '</button>').join('');
      },
      setDesigns(rows) {
        aside.querySelector('#ed-designs').innerHTML = (rows || []).map(row => '<article><b>' + escapeText(row.name) + '</b><span>' + escapeText(row.fromEnv || '') + '</span><button type="button" data-act="apply-design" data-id="' + escapeAttr(row.id) + '">Aplicar</button><button type="button" data-act="duplicate-design" data-id="' + escapeAttr(row.id) + '">Duplicar</button><button type="button" data-act="export-design" data-id="' + escapeAttr(row.id) + '">Exportar</button></article>').join('') || '<p class="ed-note">Todavía no hay diseños.</p>';
      },
      setHistory(rows) {
        aside.querySelector('#ed-history').innerHTML = (rows || []).slice().reverse().map(row => '<button type="button" data-act="rollback" data-version="' + row.version + '">v' + row.version + ' · ' + escapeText(row.op || '') + '</button>').join('') || '<p class="ed-note">Sin versiones anteriores.</p>';
      },
      setEnv(env) { aside.classList.toggle('ed-preview-env', env === 'preview'); },
      confirm() { return (aside.querySelector('#ed-confirm').value || '').trim(); },
      designName() { return (aside.querySelector('#ed-design-name').value || '').trim(); },
    };
  }

  function section(id, html) { return '<section data-for="' + id + '">' + html + '</section>'; }
  function choice(key, value, label) { return '<button type="button" data-choice="' + key + '" data-value="' + value + '">' + label + '</button>'; }
  function modes() {
    return '<div class="ed-row">' + choice('mode', 'paint', 'Pintar') + choice('mode', 'move', 'Mover') + choice('mode', 'erase', 'Borrar') + '</div>';
  }
  function brushes() {
    return '<div class="ed-row ed-brush">' + choice('brush', '1', '1') + choice('brush', '3', '3') + choice('brush', '5', '5') + '</div>';
  }
  function layer(id, label) {
    return '<label class="ed-check"><input type="checkbox" data-layer="' + id + '" checked>' + label + '</label>';
  }
  function escapeText(text) { return String(text || '').replace(/[&<>]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch])); }
  function escapeAttr(text) { return escapeText(text).replace(/"/g, '&quot;'); }

  root.EditorPanel = { mount: mount };
})(typeof globalThis !== 'undefined' ? globalThis : this);
