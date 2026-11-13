/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Filas del libro mayor para cuando el servidor no mandó la historia ya armada. */
(function (root) {
  'use strict';
  const LABELS = {
    mint: ['minado', 'Minado'],
    mina: ['minado', 'Minado'],
    migrate: ['minado', 'Minado'],
    exchange: ['cambio', 'Cambio plata→oro'],
    fusion: ['fusion', 'Fusión'],
    genesis: ['reserva', 'Reserva'],
    pool: ['fondo', 'Al fondo'],
    grant: ['otro', 'Misión'],
    pay: ['otro', 'Pago'],
    bank: ['otro', 'Banquito'],
  };

  function labelOf(kind) {
    return LABELS[kind] || ['otro', 'Movimiento'];
  }

  function filas(state) {
    const econ = state || {};
    const events = [];
    (econ.blocks || []).forEach(block => {
      const ts = block.ts || 0;
      const height = block.height || 0;
      (block.txs || []).forEach((tx, index) => events.push([ts, height, index, tx]));
    });
    (econ.mempool || []).forEach((tx, index) => events.push([tx.ts || 0, 1e9, index, tx]));
    const seenExchange = new Map();
    const seenPool = new Map();
    function take(map, key) {
      const left = map.get(key) || 0;
      if (!left) return false;
      map.set(key, left - 1);
      return true;
    }
    events.forEach(([, , , tx]) => {
      const amount = Math.trunc(tx.amountSubs || 0);
      if (tx.type === 'exchange') {
        const key = (tx.to || '') + '\0' + amount;
        seenExchange.set(key, (seenExchange.get(key) || 0) + 1);
      } else if (tx.type === 'pool') {
        const key = (tx.from || '') + '\0' + amount;
        seenPool.set(key, (seenPool.get(key) || 0) + 1);
      }
    });
    const notes = (econ.plata && econ.plata.txs) || econ.plataMoves || [];
    notes.forEach((tx, index) => {
      if (tx.type === 'exchange') {
        const amount = Math.trunc(tx.gotSmh || 0);
        if (take(seenExchange, (tx.name || '') + '\0' + amount)) return;
        events.push([tx.t || 0, 1e8, index, {
          type: 'exchange', from: 'fondo_cambio', to: tx.name || '', amountSubs: amount, note: 'Cambio de plata por oro',
        }]);
      } else if (tx.type === 'pool') {
        const amount = Math.trunc(tx.amountSmh || 0);
        if (take(seenPool, (tx.from || '') + '\0' + amount)) return;
        events.push([tx.t || 0, 1e8, index, {
          type: 'pool', from: tx.from || '', to: 'fondo_cambio', amountSubs: amount, note: 'Un quinto al fondo de cambio',
        }]);
      }
    });
    events.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
    const balances = {};
    const plataBalances = {};
    const rows = [];
    events.forEach(([ts, , , tx]) => {
      const amount = Math.trunc(tx.amountSubs || 0);
      const sph = Math.trunc(tx.amountSph || 0);
      if (tx.coin === 'SMP' && sph > 0) {
        const origin = tx.from || '';
        const dest = tx.to || '';
        if (origin) plataBalances[origin] = (plataBalances[origin] || 0) - sph;
        if (dest) plataBalances[dest] = (plataBalances[dest] || 0) + sph;
        const account = dest || origin;
        rows.push({
          ts: ts || 0,
          type: 'otro',
          label: 'Banquito Plata',
          amountSubs: 0,
          amountSph: sph,
          coin: 'SMP',
          account: origin && dest ? origin + ' → ' + dest : account,
          balanceSubs: 0,
          balanceSph: plataBalances[account] || 0,
          note: tx.note || '',
        });
        return;
      }
      if (!amount) return;
      const pair = labelOf(tx.type);
      const origin = tx.from || '';
      const dest = tx.to || '';
      if (origin) balances[origin] = (balances[origin] || 0) - amount;
      if (dest) balances[dest] = (balances[dest] || 0) + amount;
      const account = dest || origin;
      rows.push({
        ts: ts || 0,
        type: pair[0],
        label: pair[1],
        amountSubs: amount,
        account: origin && dest ? origin + ' → ' + dest : account,
        balanceSubs: balances[account] || 0,
        note: tx.note || '',
      });
    });
    return rows;
  }

  root.Historia = { filas: filas };
})(typeof window !== 'undefined' ? window : globalThis);
