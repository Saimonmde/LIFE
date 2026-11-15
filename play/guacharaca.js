/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Guacharaca (Ortalis). Canto original con Web Audio: no hay grabaciones. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.Guacharaca = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const NAME = 'Guacharaca';
  const LABEL = 'Especie protegida';
  const FLEE = 2.6;
  const HOME = 5;
  const HEAR = 16;
  const NEAR = 4;
  const SONG = {
    syllables: [
      { name: 'gua', at: 0.00, dur: 0.16, freq: 340, slide: 190 },
      { name: 'cha', at: 0.22, dur: 0.11, freq: 460, slide: 280 },
      { name: 'ra', at: 0.38, dur: 0.11, freq: 510, slide: 300 },
      { name: 'ca', at: 0.54, dur: 0.15, freq: 420, slide: 220 },
    ],
    phrase: 0.78,
    gap: 0.08,
    repeats: 3,
    duetDelay: 0.36,
    duetRepeats: 3,
    duetPitch: 1.14,
    thirdAt: 1.20,
    thirdRepeats: 2,
    thirdPitch: 0.86,
  };
  let zones = [];
  let birds = [];
  let nextChorus = 0;

  function singsAt(date) {
    const when = date instanceof Date ? date : new Date(date);
    if (Number.isNaN(when.getTime())) return false;
    const fmt = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/Bogota',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    });
    const parts = fmt.formatToParts(when);
    let hour = NaN;
    let minute = NaN;
    for (const part of parts) {
      if (part.type === 'hour') hour = Number(part.value);
      if (part.type === 'minute') minute = Number(part.value);
    }
    if (!Number.isFinite(hour) || !Number.isFinite(minute)) return false;
    const clock = hour * 60 + minute;
    return clock >= 4 * 60 + 30 && clock < 6 * 60;
  }

  function insideZone(list, x, y) {
    const ix = Math.floor(x);
    const iy = Math.floor(y);
    for (const zone of list || []) {
      if (ix >= zone.x && iy >= zone.y && ix < zone.x + zone.w && iy < zone.y + zone.h) return zone.kind || 'zona';
    }
    return '';
  }

  function boot(doc) {
    zones = (doc && doc.zones) || [];
    birds = [];
    const flocks = (doc && doc.flocks) || [];
    for (const flock of flocks) {
      for (const raw of flock.birds || []) {
        birds.push({
          id: raw.id,
          flock: flock.id,
          x: raw.x,
          y: raw.y,
          fx: raw.x,
          fy: raw.y,
          homeX: raw.x,
          homeY: raw.y,
          perch: !!raw.perch,
          habitat: raw.habitat || flock.habitat,
          name: NAME,
          mode: raw.perch ? 'perch' : 'walk',
          phase: (raw.x + raw.y) % 7 / 7,
          dir: 'down',
          walk: 0,
          clock: 0,
          turns: raw.x % 5,
          goalX: raw.x,
          goalY: raw.y,
          mates: (flock.birds || []).map(function (other) { return { x: other.x, y: other.y }; }),
          looked: false,
        });
      }
    }
    return birds;
  }

  function blockedItem(id) {
    return /guacharaca|ortalis/i.test(String(id || ''));
  }
  function refuse(action) {
    return { ok: false, name: NAME, label: LABEL, protected: true, action: action };
  }
  function hopTarget(bird) {
    const mates = bird.mates || [];
    for (let i = 0; i < mates.length; i++) {
      const mate = mates[(bird.turns + i) % mates.length];
      const dist = Math.hypot(mate.x - bird.fx, mate.y - bird.fy);
      if (dist > 1.2 && dist < 6) return mate;
    }
    return null;
  }
  function stepBird(bird, player, dt, list) {
    const walls = list || zones;
    const hasPlayer = player && Number.isFinite(player.x) && Number.isFinite(player.y);
    const dx = hasPlayer ? bird.fx - player.x : 0;
    const dy = hasPlayer ? bird.fy - player.y : 0;
    const dist = hasPlayer ? Math.hypot(dx, dy) : 99;
    let tx;
    let ty;
    let speed;
    bird.clock = (bird.clock || 0) + dt;
    if (hasPlayer && dist < FLEE) {
      bird.mode = 'flee';
      bird.air = 0;
      const len = dist || 1;
      tx = bird.fx + (dx / len) * 1.6;
      ty = bird.fy + (dy / len) * 1.6;
      const hx = tx - bird.homeX;
      const hy = ty - bird.homeY;
      const hd = Math.hypot(hx, hy);
      if (hd > HOME) {
        tx = bird.homeX + (hx / hd) * HOME;
        ty = bird.homeY + (hy / hd) * HOME;
      }
      speed = 3.4;
    } else if (bird.mode === 'fly' && Number.isFinite(bird.flyX)) {
      tx = bird.flyX;
      ty = bird.flyY;
      speed = 2.4;
      bird.air = 1;
      if (Math.hypot(bird.fx - tx, bird.fy - ty) < 0.25) {
        bird.mode = 'perch';
        bird.air = 0;
        bird.perch = true;
      }
    } else if (bird.mode === 'peck') {
      tx = bird.fx;
      ty = bird.fy;
      speed = 0;
      bird.air = 0;
      if (bird.clock > (bird.peckUntil || 0.6)) bird.mode = bird.perch ? 'perch' : 'walk';
    } else if (bird.clock > (bird.nextAct || 2.4)) {
      bird.clock = 0;
      bird.turns = (bird.turns || 0) + 1;
      bird.nextAct = 2.8 + (bird.turns % 3);
      const hop = hopTarget(bird);
      if (hop && bird.turns % 3 === 0) {
        bird.mode = 'fly';
        bird.flyX = hop.x;
        bird.flyY = hop.y;
        bird.air = 1;
        tx = hop.x;
        ty = hop.y;
        speed = 2.4;
      } else if (bird.turns % 2 === 0) {
        bird.mode = 'peck';
        bird.peckUntil = 0.7;
        tx = bird.fx;
        ty = bird.fy;
        speed = 0;
      } else {
        bird.mode = 'walk';
        bird.air = 0;
        const ang = (bird.turns % 8) * Math.PI / 4;
        tx = bird.homeX + Math.cos(ang) * 1.2;
        ty = bird.homeY + Math.sin(ang) * 1.2;
        if (insideZone(walls, tx, ty)) { tx = bird.homeX; ty = bird.homeY; }
        bird.goalX = tx;
        bird.goalY = ty;
        speed = 0.7;
      }
    } else if (bird.perch && bird.mode !== 'walk') {
      bird.mode = 'perch';
      tx = bird.homeX;
      ty = bird.homeY;
      speed = 1.4;
      bird.air = 0;
    } else {
      bird.mode = bird.mode === 'peck' ? 'peck' : 'walk';
      bird.walk = (bird.walk || 0) + dt;
      if (bird.goalX == null) {
        bird.goalX = bird.homeX;
        bird.goalY = bird.homeY;
      }
      tx = bird.goalX;
      ty = bird.goalY;
      speed = 0.7;
      bird.air = 0;
    }
    if (insideZone(walls, tx, ty)) {
      tx = bird.fx;
      ty = bird.fy;
    }
    const mx = tx - bird.fx;
    const my = ty - bird.fy;
    const md = Math.hypot(mx, my);
    if (md > 0.02) {
      const step = Math.min(md, speed * dt);
      const nx = bird.fx + (mx / md) * step;
      const ny = bird.fy + (my / md) * step;
      if (!insideZone(walls, nx, ny)) {
        bird.fx = nx;
        bird.fy = ny;
        bird.dir = Math.abs(mx) > Math.abs(my) ? (mx > 0 ? 'right' : 'left') : (my > 0 ? 'down' : 'up');
      }
    }
    bird.phase = (bird.phase + dt * (bird.mode === 'flee' ? 3 : 1)) % 1;
    if (insideZone(walls, bird.fx, bird.fy)) {
      bird.fx = bird.homeX;
      bird.fy = bird.homeY;
    }
    return bird;
  }

  function hearGain(dist) {
    if (dist >= HEAR) return 0;
    if (dist <= NEAR) return 1;
    return (HEAR - dist) / (HEAR - NEAR);
  }

  function squawk(ac, when, dur, freq, slide, gain) {
    const osc = ac.createOscillator();
    const count = Math.max(1, Math.floor(ac.sampleRate * dur));
    const buffer = ac.createBuffer(1, count, ac.sampleRate);
    const data = buffer.getChannelData(0);
    let hold = 0;
    for (let i = 0; i < count; i++) {
      const white = Math.random() * 2 - 1;
      hold = hold * 0.84 + white * 0.16;
      data[i] = hold;
    }
    const src = ac.createBufferSource();
    src.buffer = buffer;
    const filter = ac.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(freq, when);
    filter.Q.setValueAtTime(0.8, when);
    const amp = ac.createGain();
    const level = Math.max(0.0002, gain);
    amp.gain.setValueAtTime(0.0001, when);
    amp.gain.exponentialRampToValueAtTime(level, when + 0.012);
    amp.gain.exponentialRampToValueAtTime(0.0001, when + dur);
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(Math.max(40, freq), when);
    osc.frequency.exponentialRampToValueAtTime(Math.max(40, slide), when + dur);
    const tone = ac.createGain();
    tone.gain.value = 0.32;
    osc.connect(tone);
    tone.connect(filter);
    src.connect(filter);
    filter.connect(amp);
    amp.connect(ac.destination);
    src.start(when);
    src.stop(when + dur + 0.02);
    osc.start(when);
    osc.stop(when + dur + 0.02);
  }

  function voice(ac, start, pitch, repeats, gain) {
    for (let repeat = 0; repeat < repeats; repeat++) {
      const origin = start + repeat * (SONG.phrase + SONG.gap);
      for (const note of SONG.syllables) {
        squawk(ac, origin + note.at, note.dur, note.freq * pitch, note.slide * pitch, gain);
      }
    }
  }

  function playChorus(ac, gain) {
    const t = ac.currentTime + 0.02;
    voice(ac, t, 1, SONG.repeats, gain);
    voice(ac, t + SONG.duetDelay, SONG.duetPitch, SONG.duetRepeats, gain * 0.8);
    voice(ac, t + SONG.thirdAt, SONG.thirdPitch, SONG.thirdRepeats, gain * 0.65);
  }

  function nearest(player) {
    let best = null;
    for (const bird of birds) {
      const dist = Math.hypot(bird.fx - player.x, bird.fy - player.y);
      if (!best || dist < best.dist) best = { dist: dist, flock: bird.flock };
    }
    return best;
  }

  function tick(dt, ctx) {
    const city = !ctx || !ctx.mapId || ctx.mapId === 'city';
    const player = city && ctx ? { x: Number(ctx.x) || 0, y: Number(ctx.y) || 0 } : null;
    const far = { x: -9999, y: -9999 };
    for (const bird of birds) stepBird(bird, player || far, dt, zones);
    if (!player || typeof window === 'undefined') return birds;
    const now = Number(ctx.now) || Date.now();
    if (!singsAt(new Date(now)) || now < nextChorus) return birds;
    const sonido = window.Sonido;
    if (!sonido || !sonido.wanted || !sonido.wanted() || !sonido.live) return birds;
    const ac = sonido.live();
    if (!ac) return birds;
    const close = nearest(player);
    const gain = close ? hearGain(close.dist) * (sonido.volume ? sonido.volume() : 0) * 0.2 : 0;
    if (gain <= 0.001) return birds;
    playChorus(ac, gain);
    nextChorus = now + 28000;
    return birds;
  }

  function touch(id) {
    const bird = birds.find(function (item) { return item.id === id; });
    if (bird) bird.looked = true;
    return { ok: false, name: NAME, label: LABEL, protected: true, action: 'tocar', id: id || '' };
  }

  if (typeof window !== 'undefined' && window.GUACHARACAS) boot(window.GUACHARACAS);

  return {
    NAME: NAME,
    LABEL: LABEL,
    SONG: SONG,
    FLEE: FLEE,
    singsAt: singsAt,
    insideZone: insideZone,
    blockedItem: blockedItem,
    capture: function () { return refuse('capturar'); },
    sell: function () { return refuse('vender'); },
    keep: function () { return refuse('inventario'); },
    hunt: function () { return refuse('cazar'); },
    touch: touch,
    boot: boot,
    stepBird: stepBird,
    hearGain: hearGain,
    tick: tick,
    birds: function () { return birds; },
  };
});
