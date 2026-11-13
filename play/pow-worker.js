/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Busca un nonce SHA-256 fuera del hilo de la interfaz. También corre en el teléfono. */
(function (root) {
  'use strict';
  function rotr(x, n) { return (x >>> n) | (x << (32 - n)); }
  function sha256hex(msg) {
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
  function leadingZeroBits(hex) {
    let n = 0;
    for (let i = 0; i < hex.length; i++) {
      const v = parseInt(hex[i], 16);
      if (v === 0) { n += 4; continue; }
      if (v < 2) return n + 3;
      if (v < 4) return n + 2;
      if (v < 8) return n + 1;
      return n;
    }
    return n;
  }
  root.PowHash = { sha256hex, leadingZeroBits };
  const inWorker = typeof WorkerGlobalScope !== 'undefined' && root instanceof WorkerGlobalScope;
  if (!inWorker) return;
  let stop = false;
  root.onmessage = (ev) => {
    const data = ev.data || {};
    if (data.stop) { stop = true; return; }
    stop = false;
    const payload = String(data.payload || '');
    const bits = data.bits | 0;
    let nonce = data.start | 0;
    const step = () => {
      if (stop) return;
      const end = nonce + 4096;
      for (; nonce < end; nonce++) {
        const hash = sha256hex(payload + '|' + nonce);
        if (leadingZeroBits(hash) >= bits) {
          root.postMessage({ ok: true, nonce: String(nonce), hash });
          return;
        }
      }
      root.postMessage({ progress: true, tries: nonce });
      setTimeout(step, 0);
    };
    step();
  };
})(typeof self !== 'undefined' ? self : globalThis);
if (typeof module !== 'undefined' && module.exports) module.exports = globalThis.PowHash || self.PowHash;
