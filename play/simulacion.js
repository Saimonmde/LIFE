/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* SaiMonCoins (SMC), caballos, Libro Mayor y lecciones. Simulación educativa: sin valor real. */
(() => {
'use strict';
const SUBS = 100000000, MAX_SUPPLY = 21000000, MAX_SMH = 2100000000000000, INITIAL_REWARD_SMH = 50 * SUBS, HALVING_SMH = 10500000 * SUBS, TREASURY_SMH = 210000 * SUBS;
const GENESIS_PREV = '0'.repeat(64), BLOCK_SECONDS = 60;
const DOOR_TYPES = new Set(['home_door', 'mine_entrance', 'mine_exit', 'casa_exit']);

function sha256hex(msg) {
  function rotr(x, n) { return (x >>> n) | (x << (32 - n)); }
  const K = [
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
  ];
  const bytes = [];
  for (let i = 0; i < msg.length; i++) {
    const c = msg.charCodeAt(i);
    if (c < 0x80) bytes.push(c);
    else { const enc = unescape(encodeURIComponent(msg[i])); for (let j = 0; j < enc.length; j++) bytes.push(enc.charCodeAt(j)); }
  }
  const bitLen = bytes.length * 8;
  bytes.push(0x80);
  while ((bytes.length % 64) !== 56) bytes.push(0);
  for (let i = 7; i >= 0; i--) bytes.push((bitLen / Math.pow(2, i * 8)) & 0xff);
  let H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  const Wd = new Array(64);
  for (let i = 0; i < bytes.length; i += 64) {
    for (let t = 0; t < 16; t++) Wd[t] = ((bytes[i + t * 4] << 24) | (bytes[i + t * 4 + 1] << 16) | (bytes[i + t * 4 + 2] << 8) | bytes[i + t * 4 + 3]) >>> 0;
    for (let t = 16; t < 64; t++) {
      const s0 = rotr(Wd[t - 15], 7) ^ rotr(Wd[t - 15], 18) ^ (Wd[t - 15] >>> 3);
      const s1 = rotr(Wd[t - 2], 17) ^ rotr(Wd[t - 2], 19) ^ (Wd[t - 2] >>> 10);
      Wd[t] = (Wd[t - 16] + s0 + Wd[t - 7] + s1) >>> 0;
    }
    let [a, b, c, d, e, f, g, h] = H;
    for (let t = 0; t < 64; t++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const t1 = (h + S1 + ch + K[t] + Wd[t]) >>> 0;
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (S0 + maj) >>> 0;
      h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    H = H.map((x, i) => (x + [a, b, c, d, e, f, g, h][i]) >>> 0);
  }
  return H.map(x => x.toString(16).padStart(8, '0')).join('');
}
function stableStringify(x) {
  if (x === null || typeof x !== 'object') return JSON.stringify(x);
  if (Array.isArray(x)) return '[' + x.map(stableStringify).join(',') + ']';
  return '{' + Object.keys(x).sort().map(k => JSON.stringify(k) + ':' + stableStringify(x[k])).join(',') + '}';
}
function parseAmount(text) {
  let raw = String(text == null ? '' : text).trim().toLowerCase();
  if (!raw) throw new Error('monto vacío');
  let unit = 'smc';
  for (const [name, kind] of [['simonchis', 'smh'], ['simonchi', 'smh'], ['smh', 'smh'], ['smc', 'smc']]) {
    if (raw.endsWith(name)) { unit = kind; raw = raw.slice(0, -name.length).trim(); break; }
  }
  raw = raw.replace(/\s+/g, '');
  if (unit === 'smh') {
    const marks = raw.match(/[.,]/g) || [];
    const parts = raw.replace(/,/g, '.').split('.');
    if (marks.length && parts.slice(1).some(part => part.length !== 3)) throw new Error('un Simonchi no se parte');
    const grouped = raw.replace(/[.,]/g, '');
    if (!/^\d+$/.test(grouped)) throw new Error('monto ilegible');
    return Number(grouped);
  }
  if (raw.includes(',') && raw.includes('.')) raw = raw.lastIndexOf(',') > raw.lastIndexOf('.') ? raw.replace(/\./g, '').replace(',', '.') : raw.replace(/,/g, '');
  else if (raw.includes(',')) raw = raw.replace(',', '.');
  const neg = raw.startsWith('-');
  if (neg) raw = raw.slice(1);
  if (raw.startsWith('+')) raw = raw.slice(1);
  let whole = raw, frac = '';
  if (raw.includes('.')) { const bits = raw.split('.'); whole = bits[0]; frac = bits.slice(1).join(''); }
  if (whole === '') whole = '0';
  if (!/^\d+$/.test(whole) || (frac && !/^\d+$/.test(frac))) throw new Error('monto ilegible');
  if (frac.length > 8) throw new Error('como máximo 8 decimales');
  frac = frac.padEnd(8, '0');
  const smh = Number(whole) * SUBS + Number(frac || 0);
  return neg ? -smh : smh;
}
function smcToSmh(value) {
  if (typeof value === 'string') return parseAmount(value);
  if (typeof value === 'number' && Number.isInteger(value)) return value * SUBS;
  return parseAmount(String(value));
}
const subunits = (sai) => smcToSmh(sai);
function formatSmc(smh) {
  smh = Math.trunc(Number(smh) || 0);
  const neg = smh < 0;
  smh = Math.abs(smh);
  const whole = Math.floor(smh / SUBS);
  const frac = smh % SUBS;
  const grouped = whole.toLocaleString('es-CO');
  if (!frac) return (neg ? '-' : '') + grouped + ' SMC';
  return (neg ? '-' : '') + grouped + ',' + String(frac).padStart(8, '0').replace(/0+$/, '') + ' SMC';
}
function formatSmh(smh) {
  smh = Math.trunc(Number(smh) || 0);
  return (smh < 0 ? '-' : '') + Math.abs(smh).toLocaleString('es-CO') + ' SMH';
}
function formatPair(smh) { return formatSmc(smh) + ' = ' + formatSmh(smh); }
function unidadActiva() {
  try { return localStorage.getItem('lifeinc.unidad') === 'SMH' ? 'SMH' : 'SMC'; } catch (e) { return 'SMC'; }
}
function formatSai(subs) { return unidadActiva() === 'SMH' ? formatSmh(subs) : formatSmc(subs); }
function rewardSmh(minedSmh) {
  minedSmh = Math.trunc(Number(minedSmh) || 0);
  const cap = (MAX_SUPPLY - 210000) * SUBS;
  if (minedSmh >= cap) return 0;
  const era = Math.floor(minedSmh / HALVING_SMH);
  let reward = era >= 53 ? 0 : Math.floor(INITIAL_REWARD_SMH / (2 ** era));
  const remaining = cap - minedSmh;
  if (reward > remaining) reward = remaining;
  return reward;
}
function rewardSai(minedSmc) {
  const smh = rewardSmh(smcToSmh(minedSmc));
  return smh % SUBS === 0 ? smh / SUBS : smh / SUBS;
}
function ensureSmh(econ) {
  if (!econ) return econ;
  if (econ.amountUnit !== 'SMH' || econ.minedSmh == null) {
    econ.minedSmh = smcToSmh(econ.mined || 0);
    delete econ.mined;
    econ.amountUnit = 'SMH';
  }
  econ.minedSmh = Math.trunc(econ.minedSmh || 0);
  return econ;
}
function hashBlock(prev, ts, txs) {
  return sha256hex(prev + '\n' + String(ts) + '\n' + stableStringify(txs));
}
function verifyBlock(block, prev) {
  if (!block) return false;
  if (prev != null && block.prev !== prev) return false;
  return block.hash === hashBlock(block.prev, block.ts, block.txs);
}
function emptyEcon(disclaimer) {
  const txs = [{ type: 'genesis', to: 'tesoro_genesis', amountSubs: TREASURY_SMH, note: 'Reserva inicial de SaiMonCoins (no es dinero real).' }];
  const ts = 0, h = hashBlock(GENESIS_PREV, ts, txs);
  return {
    minedSmh: 0,
    amountUnit: 'SMH',
    wallets: { tesoro_genesis: TREASURY_SMH, puesto_frutas: 0 },
    blocks: [{ height: 0, ts, prev: GENESIS_PREV, hash: h, txs }],
    mempool: [],
    disclaimer: disclaimer || 'Las SaiMonCoins (SMC) son sólo una moneda del juego. No son dinero real, no se pueden retirar ni vender, no tienen valor ni canje.',
  };
}

let api = null, F = null;
const $ = (s) => document.querySelector(s);

function walletName() { return api.S.me.name || 'Viajero'; }
function walletSubs(name) { return (api.S.econ && api.S.econ.wallets && api.S.econ.wallets[name]) || 0; }
function syncButton() {
  const b = $('#b-montar');
  if (b) b.textContent = api.S.mounted ? 'Bajar' : 'Montar';
  const down = $('#b-bajar');
  if (down) down.hidden = !api.S.mounted;
  document.body.classList.toggle('mounted', !!api.S.mounted);
}
function paintHud() {
  const el = $('#sai-saldo');
  if (!el || !api.S.econ) return;
  const subs = walletSubs(walletName());
  el.textContent = formatSai(subs);
  const chip = $('#sai-chip');
  if (chip) {
    chip.title = `${formatPair(subs)} · minadas ${formatSmc(api.S.econ.minedSmh || 0)} / ${MAX_SUPPLY.toLocaleString('es-CO')} SMC · premio ${formatPair(rewardSmh(api.S.econ.minedSmh || 0))} · 1 SMC = 100.000.000 SMH · simulación, sin valor real. Pulsa para ver ${unidadActiva() === 'SMH' ? 'SMC' : 'SMH'}.`;
    if (!chip.dataset.unidad) {
      chip.dataset.unidad = '1';
      chip.addEventListener('click', () => {
        try { localStorage.setItem('lifeinc.unidad', unidadActiva() === 'SMH' ? 'SMC' : 'SMH'); } catch (e) {}
        paintHud();
        if (window.Banco) Banco.paint();
      });
    }
  }
  syncButton();
}
function ensureWallet() {
  const n = walletName();
  if (!api.S.econ.wallets[n]) api.S.econ.wallets[n] = 0;
}
function debitNamed(name, subs) {
  if (walletSubs(name) < subs) return false;
  api.S.econ.wallets[name] = walletSubs(name) - subs;
  return true;
}
function creditNamed(name, subs) { api.S.econ.wallets[name] = walletSubs(name) + subs; }
function pushTx(tx, nowTs) {
  api.S.econ.mempool.push(tx);
  sealBlocks(nowTs, false);
  api.save(); paintHud(); renderLibro();
}
function sealBlocks(nowTs, force) {
  const now = nowTs != null ? nowTs : Math.floor(Date.now() / 1000);
  if (!api.S.econ.mempool.length) return null;
  const last = api.S.econ.blocks[api.S.econ.blocks.length - 1];
  if (!force && now - (last.ts || 0) < BLOCK_SECONDS) return null;
  const txs = api.S.econ.mempool.splice(0, api.S.econ.mempool.length);
  const block = { height: last.height + 1, ts: now, prev: last.hash, txs };
  block.hash = hashBlock(block.prev, block.ts, block.txs);
  api.S.econ.blocks.push(block);
  return block;
}
function libroProgress(id) {
  const L = api.S.libro && api.S.libro.def;
  if (!L || !api.S.libro.started) return;
  const st = L.steps.find(s => s.id === id);
  if (!st || (api.S.libro.steps[st.id] || 0) >= st.count) return;
  api.S.libro.steps[st.id] = (api.S.libro.steps[st.id] || 0) + 1;
  if (L.steps.every(s => (api.S.libro.steps[s.id] || 0) >= s.count)) api.S.libro.done = true;
  api.save();
  if (api.renderQuest) api.renderQuest();
}
function localMint() {
  ensureWallet();
  ensureSmh(api.S.econ);
  const subs = rewardSmh(api.S.econ.minedSmh);
  if (subs <= 0) { api.game('Se alcanzó el tope minable de SMC.', 'aviso'); return 0; }
  api.S.econ.minedSmh += subs;
  creditNamed(walletName(), subs);
  pushTx({ type: 'mint', to: walletName(), amountSubs: subs, note: 'Emisión por bateada de oro fluvial' });
  libroProgress('lavar_oro_sai');
  api.game(`El río emite <b>${api.esc(formatPair(subs))}</b>. Es una simulación: no es dinero real.`, 'oro');
  return subs;
}
function payLocal(dest, sai, note) {
  ensureWallet();
  const subs = subunits(sai);
  if (subs <= 0) { api.game('El monto debe ser mayor que cero.', 'aviso'); return false; }
  if (!debitNamed(walletName(), subs)) { api.game('No tienes saldo suficiente en SMC.', 'aviso'); return false; }
  creditNamed(dest, subs);
  pushTx({ type: 'pay', from: walletName(), to: dest, amountSubs: subs, note: note || 'Pago' });
  libroProgress('pagar_alguien');
  api.game(`Pagas ${api.esc(formatSai(subs))} a <b>${api.esc(dest)}</b>. Sólo dentro del juego.`, 'oro');
  return true;
}
const TREASURY_SMC = 210000;
function issueLocal(amount, note, kind) {
  ensureWallet();
  ensureSmh(api.S.econ);
  const room = Math.max(0, (MAX_SUPPLY - TREASURY_SMC) * SUBS - (api.S.econ.minedSmh || 0));
  const requested = typeof amount === 'string' ? parseAmount(amount) : smcToSmh(amount);
  const subs = Math.min(requested, room);
  if (subs <= 0) { api.game('Se alcanzó el tope de 21.000.000 SMC.', 'aviso'); return 0; }
  api.S.econ.minedSmh += subs;
  creditNamed(walletName(), subs);
  pushTx({ type: kind || 'mint', to: walletName(), amountSubs: subs, note: note || 'Emisión' });
  return subs;
}
function noteLegacy(amount) {
  if (api.S.migrationAck) return;
  api.S.legacyCoins = Math.max(0, Number(amount) || 0);
}
function flushMigration() {
  if (!api || api.S.migrationAck) return;
  if (api.S.net && api.S.net.ok && api.S.net.ws) {
    api.S.net.ws.send(JSON.stringify({ t: 'migrate', amount: api.S.legacyCoins || 0 }));
    return;
  }
  if (/^https?:/.test(location.protocol)) return;
  const got = api.S.legacyCoins ? issueLocal(api.S.legacyCoins, 'Conversión 1 moneda antigua del Jardín = 1 SMC', 'migrate') : 0;
  api.S.migrationAck = true;
  api.S.coins = 0;
  api.save();
  if (got) api.game('Se convirtieron las monedas antiguas a SMC, 1 a 1.', 'oro');
}
function onWelcome() { flushMigration(); }
function localVault() {
  if (!api.S.vault) api.S.vault = { smcSubs: 0, items: {} };
  return api.S.vault;
}
function requestVault() {
  if (api.S.net.ok) api.S.net.ws.send(JSON.stringify({ t: 'vault' }));
  else if (window.Banco) Banco.paint(localVault());
}
function bankSmc(dir, amount) {
  let subs;
  try { subs = parseAmount(String(amount)); }
  catch (e) { api.game('Monto no válido. Ejemplo: 1 SMC o 12.345 SMH.', 'aviso'); return; }
  if (!(subs > 0)) return;
  if (api.S.net.ok) {
    api.S.net.ws.send(JSON.stringify({ t: dir === 'in' ? 'deposit_smc' : 'withdraw_smc', amountSmh: subs }));
    return;
  }
  const box = localVault();
  if (dir === 'in') {
    if (!debitNamed(walletName(), subs)) { api.game('No hay SMC suficientes en la billetera.', 'aviso'); return; }
    box.smh = (box.smh || box.smcSubs || 0) + subs;
    box.smcSubs = box.smh;
    pushTx({ type: 'bank', from: walletName(), to: 'deposito', amountSubs: subs, note: 'Depósito en el banquito' });
  } else {
    const have = box.smh || box.smcSubs || 0;
    if (have < subs) { api.game('El depósito no tiene tantas SMC.', 'aviso'); return; }
    box.smh = have - subs;
    box.smcSubs = box.smh;
    creditNamed(walletName(), subs);
    pushTx({ type: 'bank', from: 'deposito', to: walletName(), amountSubs: subs, note: 'Retiro del banquito' });
  }
  api.save();
  if (window.Banco) Banco.paint(box);
}
function bankItem(dir, item, qty) {
  qty = Number(qty);
  if (!item || !(qty > 0)) return;
  if (api.S.net.ok) {
    api.S.net.ws.send(JSON.stringify({ t: dir === 'in' ? 'deposit_item' : 'withdraw_item', item, qty }));
    return;
  }
  const box = localVault();
  box.items = box.items || {};
  if (dir === 'in') {
    if (!api.invRemove(item, qty)) { api.game('No llevas esa cantidad.', 'aviso'); return; }
    box.items[item] = (box.items[item] || 0) + qty;
  } else {
    if ((box.items[item] || 0) < qty) { api.game('El depósito no tiene tanto.', 'aviso'); return; }
    if (!api.invAdd(item, qty)) return;
    box.items[item] -= qty;
    if (!box.items[item]) delete box.items[item];
  }
  api.save();
  if (window.Banco) Banco.paint(box);
}
function grantTreasury(sai, note) {
  ensureWallet();
  const subs = subunits(sai);
  if (!debitNamed('tesoro_genesis', subs)) return false;
  creditNamed(walletName(), subs);
  pushTx({ type: 'grant', from: 'tesoro_genesis', to: walletName(), amountSubs: subs, note: note || 'Recompensa' });
  return true;
}
function tokenKey(name) { return 'lifeinc.sai.token.' + (name || ''); }
function walletToken(name) { try { return localStorage.getItem(tokenKey(name || walletName())) || ''; } catch (e) { return ''; } }
function saveToken(name, token) { if (!token) return; try { localStorage.setItem(tokenKey(name), token); } catch (e) {} }
function applyServer(m) {
  if (!m || !m.state) return;
  const prev = api.S.econ ? (api.S.econ.minedSmh || 0) : 0;
  const st = m.state;
  if (!api.S.econ) api.S.econ = emptyEcon(st.disclaimer);
  ensureSmh(api.S.econ);
  api.S.econ.minedSmh = st.minedSmh || 0;
  api.S.econ.disclaimer = st.disclaimer || api.S.econ.disclaimer;
  api.S.econ.ledgerResets = !!st.ledgerResets;
  api.S.econ.blockCount = st.blockCount || (st.blocks || []).length;
  api.S.econ.mempool = st.mempool || [];
  const byH = new Map((api.S.econ.blocks || []).map(b => [b.height, b]));
  for (const b of st.blocks || []) byH.set(b.height, b);
  api.S.econ.blocks = [...byH.values()].sort((a, b) => a.height - b.height);
  if (m.walletToken) saveToken(walletName(), m.walletToken);
  api.S.walletLocked = !!m.walletLocked;
  if (m.balanceSubs != null) api.S.econ.wallets[walletName()] = m.walletLocked ? 0 : m.balanceSubs;
  if ((api.S.econ.minedSmh || 0) > prev) libroProgress('lavar_oro_sai');
  paintHud(); renderLibro();
}
function blockOk(blocks, b) {
  if (!b) return false;
  if (!b.height) return b.prev === GENESIS_PREV && verifyBlock(b, GENESIS_PREV);
  const prev = blocks.find(x => x.height === b.height - 1);
  if (prev && prev.hash !== b.prev) return false;
  return verifyBlock(b, b.prev);
}
function renderLibro() {
  const el = $('#libro-cuerpo');
  if (!el || !api || !api.S.econ) return;
  const blocks = api.S.econ.blocks || [];
  const disc = (api.S.econ.disclaimer || (F && F.economy && F.economy.disclaimer) || '') + ' El libro de esta simulación se reinicia cuando el servidor se apaga o se vuelve a desplegar.';
  const oldest = blocks.length ? Math.min(...blocks.map(b => b.height)) : 0;
  const more = (api.S.econ.blockCount || blocks.length) > blocks.length;
  el.innerHTML = `<p class="aviso-legal">${api.esc(disc)} 1 SMC = 100.000.000 saimonitos.</p>
    <p>Minadas: <b>${api.esc(formatSmc(api.S.econ.minedSmh || 0))}</b> / ${MAX_SUPPLY.toLocaleString('es-CO')} SMC · Premio actual: <b>${api.esc(formatPair(rewardSmh(api.S.econ.minedSmh || 0)))}</b> · 1 SMC = 100.000.000 SMH · Mempool: ${(api.S.econ.mempool || []).length} tx · Bloque cada ~60 s</p>
    ${more ? `<button type="button" id="libro-mas">Ver bloques anteriores</button>` : ''}
    <div class="bloques">${blocks.slice().reverse().map(b => {
      const ok = blockOk(blocks, b);
      const txs = b.txs || [];
      return `<article class="bloque"><header>Bloque #${b.height} · ${ok ? 'hash válido' : 'NO COINCIDE'}</header>
        <div class="hash"><small>prev</small> ${api.esc(b.prev)}</div>
        <div class="hash"><small>hash</small> ${api.esc(b.hash)}</div>
        <ul>${txs.map(tx => `<li>${api.esc(tx.type)} ${tx.from ? api.esc(tx.from) + ' → ' : ''}${api.esc(tx.to || '')} ${formatSai(tx.amountSubs || 0)}${tx.note ? ' · ' + api.esc(tx.note) : ''}</li>`).join('')}</ul>
        <button type="button" class="ver-hash" data-h="${b.height}">Verificar hash</button></article>`;
    }).join('')}</div>`;
  const older = $('#libro-mas');
  if (older) older.onclick = () => { if (api.S.net.ok) api.S.net.ws.send(JSON.stringify({ t: 'ledger', before: oldest })); };
  el.querySelectorAll('.ver-hash').forEach(btn => btn.onclick = () => {
    const h = +btn.dataset.h;
    const b = api.S.econ.blocks.find(x => x.height === h);
    const ok = blockOk(api.S.econ.blocks, b);
    api.game(ok ? `Bloque #${h}: hash verificado (SHA-256).` : `Bloque #${h}: el hash no coincide.`, ok ? 'oro' : 'aviso');
    if (ok) libroProgress('verificar_hash');
  });
}
function toggleLibro() {
  const el = $('#w-libro');
  if (!el) return;
  el.hidden = !el.hidden;
  if (!el.hidden) { renderLibro(); libroProgress('inspeccionar_bloque'); }
}
function nearestMount() {
  let best = null, bd = 1e9;
  const p = api.S.player;
  for (const m of api.S.mounts || []) {
    if (m.ridden && m !== api.S.mounted) continue;
    const d = Math.max(Math.abs(m.x - p.x), Math.abs(m.y - p.y));
    if (d < bd) { bd = d; best = m; }
  }
  return bd <= 1 ? best : null;
}
function dismount() {
  if (!api.S.mounted) return;
  const h = api.S.mounted;
  const p = api.S.player;
  h.ridden = false;
  h.x = h.fx = p.x; h.y = h.fy = p.y;
  api.S.mounted = null;
  syncButton();
  api.game('Bajas del caballo.', 'juego');
}
function mountHorse(horse) {
  if (api.S.mounted) return dismount();
  const h = horse || nearestMount();
  if (!h || h.ridden) { api.game('Acércate a un caballo del establo (tecla M o el botón Montar).', 'aviso'); return; }
  const p = api.S.player;
  if ((api.W().mapId || 'city') !== 'city') { api.game('Los caballos esperan fuera, en el parque.', 'aviso'); return; }
  api.S.mounted = h;
  h.ridden = true;
  h.x = h.fx = p.x; h.y = h.fy = p.y;
  syncButton();
  api.game('Montas el <b>caballo</b>. Vas al doble de prisa. No puedes entrar a edificios ni al agua. M, E o el botón para bajar.', 'juego');
}
function blocksTile(W, x, y) {
  if (!api.S.mounted) return false;
  if (!W.tiles || !W.ground || !W.ground[y]) return false;
  const tile = W.tiles[W.ground[y][x]];
  const kind = tile && tile.kind;
  if (kind === 'water' || kind === 'creek') return true;
  return (W.decorations || []).some(d => d.type === 'building' && x >= d.x && x < d.x + (d.w || 1) && y >= d.y && y < d.y + (d.h || 1));
}
function buildingNode(t) {
  return t && t.kind === 'node' && DOOR_TYPES.has(t.n.def.type);
}
function study(id) {
  const lessons = F && F.skill && F.skill.lessons || [];
  const lesson = lessons.find(l => l.id === id);
  if (!lesson) return;
  api.S.studied = api.S.studied || {};
  if (api.S.studied[id]) { api.game(`Ya estudiaste «${api.esc(lesson.title)}».`, 'juego'); return; }
  api.S.studied[id] = true;
  api.addXp('blockchain', 15);
  api.game(`Lección completada: <b>${api.esc(lesson.title)}</b>. Sigue siendo una simulación, sin valor real.`, 'oro');
  api.save();
  if (api.renderSkills) api.renderSkills();
}
function skillExtraHtml() {
  const sk = F && F.skill;
  if (!sk) return '';
  const cite = sk.citation || {};
  const done = api.S.studied || {};
  const items = (sk.lessons || []).map(l => `<li class="leccion ${done[l.id] ? 'hecha' : ''}"><b>${api.esc(l.title)}</b><p>${api.esc(l.text)}</p><button type="button" class="estudiar" data-leccion="${api.esc(l.id)}">${done[l.id] ? 'Estudiada' : 'Estudiar'}</button></li>`).join('');
  return `<li class="bloque-lecciones"><span>Cita: ${api.esc(cite.title || '')} (${api.esc(String(cite.year || ''))})</span></li><ul class="lecciones">${items}</ul>`;
}
function questExtraHtml() {
  const L = api.S.libro && api.S.libro.def;
  if (!L || !api.S.libro.started) return '';
  const steps = L.steps.map(st => {
    const n = api.S.libro.steps[st.id] || 0, ok = n >= st.count;
    return `<li class="${ok ? 'hecha' : ''}" data-paso="${st.id}"><span class="caja">${ok ? '✔' : ''}</span><span>${api.esc(st.text)}</span></li>`;
  }).join('');
  const tail = api.S.libro.turnedIn ? '<li style="color:#8fe08f">★ El Libro Mayor completado</li>' : (api.S.libro.done ? '<li style="color:#ffd27a">▸ Vuelve con la Profesora de la Cadena</li>' : '');
  return `<li class="seccion">El Libro Mayor</li>${steps}${tail}`;
}
function talkProfesora() {
  const npc = (api.W().npcs || []).find(n => n.id === 'profesora_cadena');
  if (!npc) return;
  api.S.libro.started = true;
  const d = npc.dialog;
  let lines, after = null;
  if (api.S.libro.done && !api.S.libro.turnedIn) {
    lines = d.done;
    after = () => {
      api.S.libro.turnedIn = true;
      const r = (api.S.libro.def && api.S.libro.def.reward) || {};
      if (r.coins) grantTreasury(r.coins, 'Recompensa de El Libro Mayor');
      for (const [k, v] of Object.entries(r.xp || {})) api.addXp(k, v);
      api.game('¡El Libro Mayor completado! +' + (r.coins || 0) + ' SMC. No es dinero real.', 'oro');
      api.save(); api.renderAll();
    };
  } else if (api.S.libro.turnedIn) lines = d.after;
  else if (!api.S.libro.steps.lavar_oro_sai) lines = d.intro;
  else lines = d.inProgress;
  api.S.dialog = { lines, i: 0, after, who: npc };
  const aviso = $('#aviso'); if (aviso) aviso.hidden = true;
  api.showDialog();
  if (api.renderQuest) api.renderQuest();
}
function offlineCommand(text) {
  if (!text.startsWith('/')) return false;
  const parts = text.slice(1).trim().split(/\s+/);
  const cmd = (parts.shift() || '').toLowerCase();
  if (cmd === 'libro') { toggleLibro(); return true; }
  if (cmd !== 'pagar') return false;
  if (api.S.net.ok) return false;
  if (parts.length < 2) { api.sys('Uso: /pagar &lt;jugador&gt; &lt;monto&gt;  (SMC o SMH, sólo en el juego)'); return true; }
  let monto = parts.pop();
  if (/^(smc|smh|simonchis?)$/i.test(monto) && parts.length >= 2) monto = parts.pop() + ' ' + monto;
  const dest = parts.join(' ');
  let parsed = NaN;
  try { parsed = parseAmount(monto); } catch (e) { parsed = NaN; }
  if (!dest || !(parsed > 0)) { api.sys('Uso: /pagar &lt;jugador&gt; &lt;monto&gt; SMC o SMH'); return true; }
  const names = new Set(['puesto_frutas']);
  for (const o of api.S.others.values()) names.add(o.name);
  const hit = [...names].find(n => n.toLowerCase() === dest.toLowerCase());
  if (!hit) { api.sys('No encuentro a «' + api.esc(dest) + '». Prueba con un jugador conectado o puesto_frutas.'); return true; }
  payLocal(hit, monto, 'Transferencia /pagar');
  return true;
}
function onNet(m) {
  if (m.t === 'issued' && m.libro && window.LibroMadre) LibroMadre.toast(m.libro);
  if (m.t === 'economy') {
    applyServer(m);
    if (api.S.pendingBuy && m.balanceSubs != null) {
      const price = (F.stand && F.stand.priceSai) || 5;
      if (walletSubs(walletName()) + subunits(price) >= 0) {
        /* el servidor ya descontó; el mango se entrega con pay_result */
      }
    }
    return true;
  }
  if (m.t === 'smelt_result') {
    const pending = api.S.pendingSmelt;
    api.S.pendingSmelt = null;
    if (m.ok && pending && api.applySmelt) api.applySmelt(pending.id, pending.q, pending.mode, pending.result);
    else api.game(m.reason || 'La fundidora no acreditó las SMC.', 'aviso');
    return true;
  }
  if (m.t === 'migrate_result') {
    api.S.migrationAck = true;
    api.S.coins = 0;
    api.save();
    if (!m.already && m.credited) api.game(`Conversión ${m.rate}:1. Entraron ${formatPair(m.credited)}.`, 'oro');
    return true;
  }
  if (m.t === 'vault') {
    if (window.Banco) Banco.paint(m.account || { smcSubs: 0, items: {} });
    return true;
  }
  if (m.t === 'vault_item') {
    if (m.op === 'deposit') api.invRemove(m.item, m.qty);
    else api.invAdd(m.item, m.qty);
    return true;
  }
  if (m.t === 'shift') {
    if (m.paidSmh || m.paid) api.game(`Turno cumplido: ${m.amountText || formatPair(m.paidSmh || m.paid)}. ${m.note || 'No es dinero real.'}`, 'oro');
    return true;
  }
  if (m.t === 'quest_result') return true;
  if (m.t === 'playtime') {
    api.S.playtime = m.playtime || 0;
    api.S.createdAt = m.createdAt || 0;
    if (api.renderProfile) api.renderProfile();
    api.save();
    return true;
  }
  if (m.t === 'pay_result') {
    if (m.ok && api.S.pendingBuy && m.to === 'puesto_frutas') {
      api.S.pendingBuy = false;
      const sku = (F.stand && F.stand.sku) || 'mango';
      api.invAdd(sku, 1);
      api.game(`Compras 1 × <b>${api.esc(api.W().items[sku].name)}</b> por ${F.stand.priceSai} SMC.`, 'oro');
      libroProgress('pagar_alguien');
    } else if (!m.ok) api.S.pendingBuy = false;
    return true;
  }
  return false;
}
function buyStand() {
  if (api.S.mounted) { api.game('Baja del caballo para comprar.', 'aviso'); return; }
  const price = (F.stand && F.stand.priceSai) || 5;
  const sku = (F.stand && F.stand.sku) || 'mango';
  if (api.S.net.ok) {
    if (api.S.walletLocked) { api.game('Esta billetera SMC se creó en otro aparato. Puedes jugar, pero no gastar esas monedas.', 'aviso'); return; }
    api.S.pendingBuy = true;
    api.S.net.ws.send(JSON.stringify({ t: 'pay', to: 'puesto_frutas', amountSai: price, note: 'Compra en el puesto de frutas' }));
    return;
  }
  if (!payLocal('puesto_frutas', price, 'Compra en el puesto de frutas')) return;
  api.invAdd(sku, 1);
  api.game(`Compras 1 × <b>${api.esc(api.W().items[sku].name)}</b> por ${price} SMC.`);
}
function onRiverGold(nodeId) {
  if ((api.W().mapId || 'city') !== 'city') return 0;
  if (api.S.net.ok) {
    if (api.S.walletLocked) { api.game('Esta billetera SMC se creó en otro aparato. Puedes jugar, pero no emitir con ese nombre.', 'aviso'); return 0; }
    api.S.net.ws.send(JSON.stringify({ t: 'mint', node: nodeId || '' }));
    return 0;
  }
  return localMint();
}
function syncHorse() {
  const h = api.S.mounted, p = api.S.player;
  if (!h) return;
  h.x = p.x; h.y = p.y; h.fx = p.fx; h.fy = p.fy;
}
function describeMount(m) { return `Montar: <b>${api.esc(m.def.name || 'Caballo')}</b> (M o E)`; }
function hitMount(wx, wy, TS) {
  for (const m of api.S.mounts || []) {
    if (m.ridden) continue;
    const ox = (m.fx + 0.5) * TS - 28, oy = (m.fy + 1) * TS - 60;
    if (wx >= ox && wx <= ox + 70 && wy >= oy && wy <= oy + 64) return m;
  }
  return null;
}

async function installWorld(W, S) {
  const r = await fetch('../data/simulacion.json');
  if (!r.ok) throw new Error('No se pudo cargar data/simulacion.json');
  F = await r.json();
  const off = (window.Casa && window.Casa.VALLE_OFFSET) || { x: 0, y: 0 };
  if (!F._valleShifted && (off.x || off.y)) {
    const shift = (o) => { if (o && typeof o.x === 'number') { o.x += off.x; o.y += off.y; } };
    shift(F.stable); shift(F.npc); shift(F.stand);
    (F.signs || []).forEach(shift);
    (F.waypoints || []).forEach(shift);
    (F.mounts || []).forEach((m) => (m.spawn || []).forEach(shift));
    F._valleShifted = true;
  }
  Object.assign(W.sprites, F.sprites);
  const st = F.stable;
  W.decorations.push({ id: st.id, type: st.type, name: st.name, x: st.x, y: st.y, w: st.w, h: st.h, sprite: st.sprite, solid: true });
  const stand = F.stand;
  W.nodes.push({
    id: stand.id, type: 'fruit_stand', name: stand.name, x: stand.x, y: stand.y, solid: true,
    states: ['active'], initialState: 'active', sprites: { active: stand.sprite }, priceSai: stand.priceSai, sku: stand.sku,
  });
  if (W.collision[stand.y]) W.collision[stand.y][stand.x] = 1;
  W.npcs.push(F.npc);
  for (const s of F.signs) W.signs3d.push(s);
  for (const w of F.waypoints) if (!W.waypoints.some(p => p.id === w.id)) W.waypoints.push(w);
  W.skills.blockchain = F.skill;
  if (W.skills.order && !W.skills.order.includes('blockchain')) {
    const at = W.skills.order.indexOf('artesania');
    W.skills.order.splice(at < 0 ? W.skills.order.length : at, 0, 'blockchain');
  }
  W.economy = F.economy;
  W.mounts = F.mounts;
  W.questsLibroMayor = F.quest;
  const def = F.mounts[0];
  S.mounts = (def.spawn || []).map(sp => ({ def, id: sp.id, x: sp.x, y: sp.y, fx: sp.x, fy: sp.y, ridden: false }));
  S.mounted = null;
  S.econ = emptyEcon(F.economy.disclaimer);
  S.libro = { def: F.quest, started: false, steps: {}, done: false, turnedIn: false };
  S.studied = {};
  S.pendingBuy = false;
}
function bind(next) { api = next; }
function resetProgress() {
  if (!F) return;
  api.S.mounted = null;
  for (const m of api.S.mounts || []) { m.ridden = false; m.x = m.fx = m.def ? (F.mounts[0].spawn.find(s => s.id === m.id) || {}).x : m.x; }
  const spawns = (F.mounts[0] && F.mounts[0].spawn) || [];
  for (const m of api.S.mounts || []) {
    const sp = spawns.find(s => s.id === m.id);
    if (sp) { m.x = m.fx = sp.x; m.y = m.fy = sp.y; m.ridden = false; }
  }
  api.S.econ = emptyEcon(F.economy.disclaimer);
  api.S.libro = { def: F.quest, started: false, steps: {}, done: false, turnedIn: false };
  api.S.studied = {};
  api.S.pendingBuy = false;
}
function restore(d) {
  if (!d || !api) return;
  if (d.libro) Object.assign(api.S.libro, d.libro);
  if (d.studied) api.S.studied = d.studied;
  if (d.econ && d.econ.blocks && d.econ.wallets) api.S.econ = ensureSmh(d.econ);
}
function drawDialogFace(who) {
  const canvas = $('#dialogo-cara');
  if (!canvas) return;
  const d = canvas.getContext('2d');
  d.imageSmoothingEnabled = false;
  d.fillStyle = '#b9a676';
  d.fillRect(0, 0, 64, 64);
  const img = (who && who.id === 'profesora_cadena' && api.imgs._profesora) ? api.imgs._profesora : api.capataz();
  if (img) d.drawImage(img, 6, 0, 36, 36, 0, 2, 64, 64);
}
function wireLessonButtons() {
  document.querySelectorAll('.estudiar').forEach(b => b.onclick = () => study(b.dataset.leccion));
}
function autotest(ok) {
  ok(!!F && F.economy.symbol === 'SMC' && F.economy.unit === 'SaiMonCoin' && F.economy.maxSupply === 21000000 && !(F.economy.alias || []).length, 'economía SMC / SaiMonCoins / 21 millones');
  ok(rewardSai(0) === 50 && rewardSai(10500000) === 25, 'halving: 50 SMC y luego 25');
  ok(!!api.W().npcs.find(n => n.id === 'profesora_cadena' && n.name === 'Profesora de la Cadena' && !/Satoshi/i.test(n.name)), 'Profesora de la Cadena');
  ok(F.skill.lessons.length >= 8 && /Peer-to-Peer Electronic Cash System/.test(F.skill.citation.title), '8 lecciones y cita del informe por título');
  ok(F.quest.id === 'el_libro_mayor', 'misión El Libro Mayor');
  ok(/no son dinero real/i.test($('#sai-legal').textContent) && /no tienen valor/i.test($('#sai-legal').textContent) && /se reinicia/i.test($('#sai-legal').textContent), 'aviso visible: sin valor real y el libro se reinicia');
  const off = (window.Casa && window.Casa.VALLE_OFFSET) || { x: 0, y: 0 };
  ok(F.stable.y - off.y >= 62 && (F.stable.x - off.x) + F.stable.w - 1 < 234 && F.stable.x - off.x <= 234, 'establo en la plaza, fuera de la iglesia');
  ok(F.stable.x - off.x !== 226 && F.npc.x - off.x !== 227, 'establo y profesora fuera de la puerta del parque');
  const horse = api.S.mounts[0];
  ok(!!horse, 'hay un caballo en el establo');
  api.S.player.x = api.S.player.fx = horse.x;
  api.S.player.y = api.S.player.fy = horse.y + 1;
  mountHorse(horse);
  ok(!!api.S.mounted && speedMul() === 4, 'montar: velocidad ×4, el doble de la montura anterior');
  ok(!!$('#b-bajar') && $('#b-bajar').hidden === false, 'botón Bajarse del caballo visible al montar');
  if (api.update) {
    const rider = api.S.player;
    rider.path = []; rider.x = rider.fx = 220 + off.x; rider.y = rider.fy = 70 + off.y;
    for (let i = 1; i <= 16; i++) rider.path.push([220 + off.x + i, 70 + off.y]);
    api.S.keys.clear();
    api.update(0.5);
    const travelled = rider.fx - (220 + off.x);
    ok(travelled > 7.6 && travelled < 9.2, 'a caballo se recorren unas 8,4 casillas en medio segundo (' + travelled.toFixed(2) + ')');
  }
  const water = (api.W().waterBodies.rio_claro.tiles || [])[0];
  ok(blocksTile(api.W(), water[0], water[1]) || api.W().collision[water[1]][water[0]] !== 0, 'el caballo no entra al agua');
  const home = api.S.nodes.get('puerta_casa');
  if (home) {
    const before = api.W().mapId || 'city';
    api.act({ kind: 'node', n: home });
    ok((api.W().mapId || 'city') === before && !!api.S.mounted, 'a caballo no se entra a la casa');
  }
  dismount();
  ok(!api.S.mounted, 'desmontar');
  api.S.libro.started = true;
  const beforeSai = walletSubs(walletName());
  const got = localMint();
  ok(got === subunits(50) && walletSubs(walletName()) > beforeSai, 'batear oro emite 50 SMC');
  ok(payLocal('puesto_frutas', 5, 'autotest'), 'pago al puesto de frutas');
  sealBlocks(Math.floor(Date.now() / 1000) + BLOCK_SECONDS + 5, true);
  const last = api.S.econ.blocks[api.S.econ.blocks.length - 1];
  ok(last.height >= 1 && verifyBlock(last, api.S.econ.blocks[last.height - 1].hash), 'bloque encadenado y hash verificado');
  libroProgress('inspeccionar_bloque');
  libroProgress('verificar_hash');
  ok(api.S.libro.done, 'pasos de El Libro Mayor completables');
  study('p2p');
  ok(api.S.studied.p2p, 'se puede completar una lección');
  const chain = verifyBlock(api.S.econ.blocks[0], GENESIS_PREV);
  ok(chain, 'el bloque génesis verifica');
}
function speedMul() { return api.S.mounted ? ((F.mounts[0] && F.mounts[0].speed) || 2) : 1; }

window.Simulacion = {
  installWorld, bind, resetProgress, restore, paintHud, renderLibro, toggleLibro, onRiverGold, buyStand,
  mountHorse, dismount, nearestMount, blocksTile, buildingNode, speedMul, syncHorse, skillExtraHtml, questExtraHtml,
  grantTreasury, issueLocal, noteLegacy, flushMigration, onWelcome, walletSubs, localVault, requestVault, bankSmc, bankItem,
  talkProfesora, offlineCommand, onNet, drawDialogFace, wireLessonButtons, describeMount, hitMount, study, autotest,
  hashBlock, verifyBlock, emptyEcon, rewardSai, rewardSmh, formatSai, formatPair, formatSmc, formatSmh, parseAmount, walletToken, SUBS, GENESIS_PREV,
};
const legal = document.getElementById('sai-legal');
if (legal) legal.onclick = () => { const open = legal.classList.toggle('open'); legal.setAttribute('aria-expanded', open ? 'true' : 'false'); };
})();
