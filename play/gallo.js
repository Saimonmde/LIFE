/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Gallo. Canto original con Web Audio: no hay grabaciones. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.Gallos = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const ITEM = 'gallo';
  const NAME = 'Gallo';
  const CAP = 8;
  const HEAR = 18;
  const NEAR = 4;
  const DAY_SECONDS = 20 * 60;
  const SONG = {
    strong: [
      { name: 'qui', at: 0.00, dur: 0.09, freq: 640, slide: 700 },
      { name: 'qui', at: 0.12, dur: 0.09, freq: 860, slide: 920 },
      { name: 'riqui', at: 0.24, dur: 0.62, freq: 1180, slide: 460 },
    ],
    strongGap: 0.98,
    strongRepeats: 2,
    short: [
      { name: 'qui', at: 0.00, dur: 0.08, freq: 700, slide: 760 },
      { name: 'qui', at: 0.10, dur: 0.08, freq: 900, slide: 980 },
      { name: 'riqui', at: 0.20, dur: 0.42, freq: 1100, slide: 520 },
    ],
  };
  let birds = [];
  let realSung = false;
  let lastDay = 0;
  let nextShort = 0;

  function crowsReal(date) {
    const when = date instanceof Date ? date : new Date(date);
    if (Number.isNaN(when.getTime())) return false;
    const fmt = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/Bogota', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    });
    let hour = NaN;
    let minute = NaN;
    for (const part of fmt.formatToParts(when)) {
      if (part.type === 'hour') hour = Number(part.value);
      if (part.type === 'minute') minute = Number(part.value);
    }
    if (!Number.isFinite(hour) || !Number.isFinite(minute)) return false;
    const clock = hour * 60 + minute;
    return clock >= 5 * 60 && clock < 6 * 60;
  }

  function gameDay(nowSec, epoch) {
    const elapsed = Math.max(0, Number(nowSec) - Number(epoch));
    if (!Number.isFinite(elapsed)) return 1;
    return Math.floor(elapsed / DAY_SECONDS) + 1;
  }

  function notice(day) {
    const number = Math.max(1, Number(day) || 1);
    return 'Amaneció: día ' + number;
  }

  function sellable(item) {
    return String(item || '') === ITEM;
  }

  function boot(doc) {
    birds = [];
    const list = (doc && doc.roosters) || [];
    for (const raw of list) {
      birds.push({
        id: raw.id,
        x: raw.x,
        y: raw.y,
        fx: raw.x,
        fy: raw.y,
        homeX: raw.x,
        homeY: raw.y,
        where: raw.where || 'patio',
        species: raw.species || 'gallo',
        loose: !!raw.loose,
        mode: 'idle',
        phase: (raw.x + raw.y) % 5 / 5,
        dir: 'down',
        clock: 0,
        turns: raw.x % 6,
        goalX: raw.x,
        goalY: raw.y,
      });
    }
    return birds;
  }

  function stepBird(bird, dt) {
    bird.clock = (bird.clock || 0) + dt;
    if (bird.mode === 'peck') {
      if (bird.clock > 0.55) bird.mode = 'walk';
      bird.phase = (bird.phase + dt) % 1;
      return bird;
    }
    if (bird.clock > 3.2) {
      bird.clock = 0;
      bird.turns = (bird.turns || 0) + 1;
      if (bird.turns % 2 === 0) {
        bird.mode = 'peck';
        return bird;
      }
      const ang = (bird.turns % 8) * Math.PI / 4;
      bird.goalX = bird.homeX + Math.cos(ang) * 1.1;
      bird.goalY = bird.homeY + Math.sin(ang) * 1.1;
      bird.mode = 'walk';
    }
    const mx = (bird.goalX == null ? bird.homeX : bird.goalX) - bird.fx;
    const my = (bird.goalY == null ? bird.homeY : bird.goalY) - bird.fy;
    const md = Math.hypot(mx, my);
    if (md > 0.08) {
      const step = Math.min(md, 0.55 * dt);
      const nx = bird.fx + (mx / md) * step;
      const ny = bird.fy + (my / md) * step;
      if (Math.hypot(nx - bird.homeX, ny - bird.homeY) <= 1.6) {
        bird.fx = nx;
        bird.fy = ny;
        bird.dir = Math.abs(mx) > Math.abs(my) ? (mx > 0 ? 'right' : 'left') : (my > 0 ? 'down' : 'up');
        bird.mode = 'walk';
      }
    } else if (bird.mode !== 'peck') bird.mode = 'idle';
    bird.phase = (bird.phase + dt) % 1;
    return bird;
  }

  function hearGain(dist) {
    if (dist >= HEAR) return 0;
    if (dist <= NEAR) return 1;
    return (HEAR - dist) / (HEAR - NEAR);
  }

    function nearestLoose(player, caught) {
      const skip = caught || [];
      let best = null;
      for (const bird of birds) {
        if (!bird.loose || skip.indexOf(bird.id) >= 0) continue;
        const dist = Math.hypot(bird.fx - player.x, bird.fy - player.y);
        if (dist > 2.4) continue;
        if (!best || dist < best.dist) best = { dist: dist, id: bird.id, species: bird.species || 'gallo' };
      }
      return best;
    }
    function nearest(player) {
    let best = null;
    for (const bird of birds) {
      const dist = Math.hypot(bird.fx - player.x, bird.fy - player.y);
      if (!best || dist < best.dist) best = { dist: dist, id: bird.id };
    }
    return best;
  }

  function squawk(ac, when, dur, freq, slide, gain) {
    const osc = ac.createOscillator();
    const count = Math.max(1, Math.floor(ac.sampleRate * dur));
    const buffer = ac.createBuffer(1, count, ac.sampleRate);
    const data = buffer.getChannelData(0);
    let hold = 0;
    for (let i = 0; i < count; i++) {
      hold = hold * 0.62 + (Math.random() * 2 - 1) * 0.38;
      data[i] = hold;
    }
    const src = ac.createBufferSource();
    src.buffer = buffer;
    const filter = ac.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(Math.max(80, freq), when);
    filter.Q.setValueAtTime(1.4, when);
    const amp = ac.createGain();
    const level = Math.max(0.0002, gain);
    amp.gain.setValueAtTime(0.0001, when);
    amp.gain.exponentialRampToValueAtTime(level, when + 0.015);
    amp.gain.exponentialRampToValueAtTime(0.0001, when + dur);
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(Math.max(80, freq), when);
    osc.frequency.exponentialRampToValueAtTime(Math.max(80, slide), when + Math.max(0.05, dur * 0.85));
    const tone = ac.createGain();
    tone.gain.value = 0.55;
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

  function phrase(ac, start, notes, gain) {
    for (const note of notes) squawk(ac, start + note.at, note.dur, note.freq, note.slide, gain);
  }

  function play(kind, gain) {
    const sonido = typeof window !== 'undefined' ? window.Sonido : null;
    if (!sonido || !sonido.wanted || !sonido.wanted() || !sonido.live) return false;
    const ac = sonido.live();
    if (!ac || gain <= 0.001) return false;
    const vol = (sonido.volume ? sonido.volume() : 0.7) * gain * (kind === 'strong' ? 0.28 : 0.16);
    const t = ac.currentTime + 0.02;
    if (kind === 'strong') {
      for (let i = 0; i < SONG.strongRepeats; i++) phrase(ac, t + i * SONG.strongGap, SONG.strong, vol);
    } else phrase(ac, t, SONG.short, vol);
    return true;
  }

  function showNotice(text) {
    if (typeof document === 'undefined') return;
    let el = document.getElementById('gallo-amanecer');
    if (!el) {
      el = document.createElement('div');
      el.id = 'gallo-amanecer';
      el.setAttribute('role', 'status');
      document.body.append(el);
      const style = document.createElement('style');
      style.textContent = '#gallo-amanecer{position:fixed;left:50%;bottom:max(88px,env(safe-area-inset-bottom));transform:translateX(-50%);background:#241c14e6;color:#f6e2bd;border:1px solid #ad8951;border-radius:999px;padding:6px 12px;font:13px system-ui;z-index:18;pointer-events:none}#gallo-amanecer[hidden]{display:none}';
      document.head.append(style);
    }
    el.hidden = false;
    el.textContent = text;
    clearTimeout(el._hide);
    el._hide = setTimeout(function () { el.hidden = true; }, 7000);
  }

  function onGameDawn(reloj, nowMs) {
    const nowSec = (Number(nowMs) || Date.now()) / 1000;
    const epoch = reloj && Number(reloj.epoch);
    const day = epoch ? gameDay(nowSec, epoch) : 1;
    if (day === lastDay) return day;
    lastDay = day;
    showNotice(notice(day));
    const now = Number(nowMs) || Date.now();
    if (now >= nextShort) {
      let gain = 0.35;
      if (typeof window !== 'undefined' && window.LiveInk && window.LiveInk.state && window.LiveInk.state.player) {
        const map = window.LiveInk.world && window.LiveInk.world.mapId;
        if (map && map !== 'city') gain = 0;
        else {
          const player = window.LiveInk.state.player;
          const close = nearest({ x: player.fx, y: player.fy });
          gain = close ? hearGain(close.dist) : 0;
        }
      }
      if (gain > 0) play('short', gain);
      nextShort = now + 20000;
    }
    return day;
  }

  function tick(dt, ctx) {
    const city = !ctx || !ctx.mapId || ctx.mapId === 'city';
    for (const bird of birds) stepBird(bird, dt);
    if (!city || typeof window === 'undefined') return birds;
    const now = Number(ctx.now) || Date.now();
    const player = { x: Number(ctx.x) || 0, y: Number(ctx.y) || 0 };
    const close = nearest(player);
    const gain = close ? hearGain(close.dist) : 0;
    if (crowsReal(new Date(now))) {
      if (!realSung && gain > 0) {
        if (play('strong', gain)) realSung = true;
      }
    } else realSung = false;
    return birds;
  }

  function touch(id) {
    const given = id && typeof id === 'object' ? id : null;
    const bird = given || birds.find(function (item) { return item.id === id; });
    if (bird && bird.looked !== undefined) bird.looked = true;
    if (typeof onTake === 'function') onTake(bird || { id: id, species: 'gallo' });
    return { ok: true, item: ITEM, name: NAME, id: (bird && bird.id) || id || '' };
  }

  function icon() {
    const canvas = typeof document !== 'undefined' ? document.createElement('canvas') : null;
    if (!canvas) return '';
    canvas.width = canvas.height = 32;
    const g = canvas.getContext('2d');
    g.fillStyle = '#c47a32';
    g.fillRect(6, 12, 16, 12);
    g.fillStyle = '#d12626';
    g.fillRect(18, 6, 4, 6);
    g.fillStyle = '#e2b13a';
    g.fillRect(22, 14, 6, 3);
    g.fillStyle = '#2a3a28';
    g.fillRect(2, 10, 6, 8);
    return canvas.toDataURL('image/png');
  }

  let onTake = null;
  if (typeof window !== 'undefined' && window.GALLOS) boot(window.GALLOS);

  return {
    ITEM: ITEM,
    NAME: NAME,
    CAP: CAP,
    SONG: SONG,
    crowsReal: crowsReal,
    gameDay: gameDay,
    notice: notice,
    sellable: sellable,
    killable: function () { return false; },
    nearestLoose: nearestLoose,
    boot: boot,
    stepBird: stepBird,
    hearGain: hearGain,
    onGameDawn: onGameDawn,
    tick: tick,
    touch: touch,
    icon: icon,
    birds: function () { return birds; },
    set onTake(fn) { onTake = fn; },
    get onTake() { return onTake; },
  };
});
