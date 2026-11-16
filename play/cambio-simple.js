/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Vista previa del cambio. No mueve monedas: el servidor decide. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof root !== 'undefined') root.CambioSimple = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const SUBS = 100;
  const PLATA_SUBS = 100000000;
  const SMP_POR_SMC = 100;
  const MINERAL_SMH = 1;
  const MINERALES = { mineral_cobre: 'cobre', mineral_plata: 'plata', mineral_oro: 'oro' };

  function texto(das, nombreDas, recibes, nombreRecibes, extra) {
    return ('Das ' + das + ' ' + nombreDas + '. Recibes ' + recibes + ' ' + nombreRecibes + '.' + (extra ? ' ' + extra : '')).trim();
  }
  function smc(smh) {
    const whole = Math.floor(smh / SUBS);
    const frac = smh % SUBS;
    if (!frac) return String(whole);
    return (whole + ',' + String(frac).padStart(2, '0')).replace(/0+$/, '');
  }
  function no(line) {
    return { ok: false, das: 0, recibes: 0, maximo: 0, texto: line };
  }
  function quote(give, receive, qty, have, fondoSmh, puestoSmh) {
    qty = Math.floor(Number(qty) || 0);
    have = Math.floor(Number(have) || 0);
    fondoSmh = Math.floor(Number(fondoSmh) || 0);
    puestoSmh = Math.floor(Number(puestoSmh) || 0);
    if (give === receive) return no('Elige dos cosas distintas.');
    if (receive !== 'simoncoin') return no('Eso crearía monedas o metal nuevo. Aquí solo se mueve lo que ya existe.');
    if (give === 'simonplata') {
      const haveSmp = Math.max(0, Math.floor(have / PLATA_SUBS));
      const fondo = Math.max(0, Math.floor(fondoSmh / SUBS));
      const maximo = Math.max(0, Math.min(Math.floor(haveSmp / SMP_POR_SMC), fondo));
      const usado = Math.max(0, Math.min(Math.floor(Math.max(0, qty) / SMP_POR_SMC), maximo));
      return {
        ok: usado > 0,
        das: usado * SMP_POR_SMC,
        recibes: usado,
        maximo: maximo * SMP_POR_SMC,
        texto: texto(usado * SMP_POR_SMC, 'Simonplata', usado, 'Simoncoin', 'El oro sale de monedas que ya existían.'),
      };
    }
    if (Object.prototype.hasOwnProperty.call(MINERALES, give)) {
      const cabe = Math.max(0, Math.floor(puestoSmh / MINERAL_SMH));
      const maximo = Math.max(0, Math.min(have, cabe));
      const usado = Math.max(0, Math.min(Math.max(0, qty), maximo));
      const smh = usado * MINERAL_SMH;
      return {
        ok: usado > 0,
        das: usado,
        recibes: smh / SUBS,
        maximo: maximo,
        texto: texto(usado, 'de ' + MINERALES[give], smc(smh), 'Simoncoin', 'El puesto paga con monedas que ya tenía.'),
      };
    }
    return no('Eso no se puede cambiar.');
  }
  return { quote: quote, SUBS: SUBS, MINERALES: MINERALES };
});
