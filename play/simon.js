// SPDX-License-Identifier: AGPL-3.0-or-later
const $ = id => document.getElementById(id);
const money = n => new Intl.NumberFormat('es-CO', {style: 'currency', currency: 'COP', maximumFractionDigits: 0}).format(n);
let conversation = null;
let consent = false;
let gaps = [];
let lastKey = 0;
let voiceRate = 0.92;
let speaking = null;

function settings() {
  return {
    voz: Number($('voz').value),
    pausa_ms: Number($('pausa').value),
    por_partes: $('partes').checked,
    adaptar: $('adaptar').checked,
  };
}
function bubble(cls, text) {
  const el = document.createElement('div');
  el.className = 'burbuja ' + cls;
  el.textContent = text;
  $('log').append(el);
  $('log').scrollTop = $('log').scrollHeight;
  return el;
}
const whole = value => (value == null || value === '') ? '—' : (Number(value) % 1 === 0 ? String(Math.round(Number(value))) : String(value));
function priceBits(card) {
  const bits = [];
  if (card.price_day) bits.push(money(card.price_day) + ' / día');
  if (card.price_week) bits.push(money(card.price_week) + ' / semana');
  if (card.price_month) bits.push(money(card.price_month) + ' / mes');
  if (card.price_sale) bits.push(money(card.price_sale) + ' en venta');
  if (!bits.length && card.price) bits.push(money(card.price));
  return bits.join(' · ');
}
function addCard(card) {
  const el = document.createElement('article');
  el.className = 'card';
  const title = document.createElement('h3');
  const op = {arriendo: 'Arriendo', renta_corta: 'Renta corta', venta: 'Venta'}[card.operation] || 'Publicación';
  title.textContent = `${op} · ${card.municipality || ''}${card.neighborhood ? ' · ' + card.neighborhood : ''}`;
  const price = document.createElement('p');
  price.innerHTML = '<b></b>';
  price.querySelector('b').textContent = priceBits(card);
  const meta = document.createElement('p');
  meta.textContent = `${whole(card.area_m2)} m² · ${whole(card.bedrooms)} hab. · ${whole(card.bathrooms)} baños · ${card.source_name || ''}`;
    const actions = document.createElement('div');
    actions.className = 'acciones';
    el.append(title, price, meta, actions);
    const url = card.original_url;
  if (url && url.startsWith('https://')) {
    const a = document.createElement('a');
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = 'Abrir ficha original';
    a.addEventListener('click', () => {
      if (!conversation) return;
      fetch('/api/simon/enlace', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({conversation_id: conversation, url}), keepalive: true});
    });
    const preview = document.createElement('button');
    preview.type = 'button';
    preview.textContent = 'Vista previa';
    const box = document.createElement('div');
    preview.addEventListener('click', async () => {
      box.textContent = 'Leyendo una vista en texto…';
      const res = await fetch('/api/simon/vista?' + new URLSearchParams({url, conversation_id: conversation || ''}));
      const data = await res.json();
      box.replaceChildren();
      const p = document.createElement('p');
      p.className = 'excerpt';
      p.textContent = data.excerpt || data.notice || data.error || 'Sin vista previa.';
      box.append(p);
      const frame = document.createElement('iframe');
      frame.className = 'vista';
      frame.sandbox = 'allow-popups allow-popups-to-escape-sandbox';
      frame.referrerPolicy = 'no-referrer';
      frame.title = 'Vista de la ficha original';
      frame.src = url;
      box.append(frame);
    });
    actions.append(a, preview);
    el.append(box);
  }
  $('log').append(el);
}
function addCitations(rows) {
  for (const row of rows || []) {
    const el = document.createElement('article');
    el.className = 'card';
    const h = document.createElement('h3');
    h.textContent = row.title || row.url;
    const p = document.createElement('p');
    p.textContent = row.snippet || '';
    const a = document.createElement('a');
    a.href = row.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = 'Abrir fuente';
    a.addEventListener('click', () => {
      if (!conversation) return;
      fetch('/api/simon/enlace', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({conversation_id: conversation, url: row.url}), keepalive: true});
    });
    el.append(h, p, a);
    $('log').append(el);
  }
}
async function say(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = 'es-CO';
  utter.rate = voiceRate;
  window.speechSynthesis.speak(utter);
}
async function reveal(data) {
  const host = bubble('simon', '');
  const parts = data.pace && data.pace.por_partes ? (data.chunks || [data.message]) : [data.message];
  const wait = data.pace ? data.pace.chunk_ms : 0;
  voiceRate = data.pace ? data.pace.voice_rate : voiceRate;
  if (wait) await new Promise(r => setTimeout(r, Math.min(wait, 1500)));
  for (let i = 0; i < parts.length; i++) {
    host.textContent = parts.slice(0, i + 1).join(' ');
    if (wait && i < parts.length - 1) await new Promise(r => setTimeout(r, Math.min(wait, 1200)));
  }
  for (const card of data.cards || []) addCard(card);
  addCitations(data.citations);
  if (data.feedback) {
    $('feedback').hidden = false;
    $('feedback-texto').textContent = data.message;
    $('aceptar-fila').hidden = !!data.consent;
  }
}
async function send(message, extra = {}) {
  const average = gaps.length ? gaps.reduce((a, b) => a + b, 0) / gaps.length : null;
  const body = {message, conversation_id: conversation, settings: settings(), typing_ms: average, ...extra};
  if (speaking) body.speech_wpm = speaking;
  const path = $('agente').value === 'simon-io' ? '/api/simon-io/mensaje' : '/api/simon-ia/mensaje';
  const res = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Simon no pudo responder');
  conversation = data.conversation_id;
  consent = !!data.consent;
  if (data.pace) $('voz').value = data.pace.voice_rate;
  await reveal(data);
}
$('texto').addEventListener('keydown', () => {
  const now = performance.now();
  if (lastKey) gaps.push(Math.min(2000, now - lastKey));
  if (gaps.length > 12) gaps.shift();
  lastKey = now;
});
$('enviar').addEventListener('submit', async e => {
  e.preventDefault();
  const text = $('texto').value.trim();
  if (!text) return;
  $('texto').value = '';
  bubble('user', text);
  try { await send(text); } catch (err) { bubble('simon', err.message); }
});
$('cerrar').addEventListener('click', async () => {
  bubble('user', 'Quiero cerrar la conversación.');
  try { await send('Quiero terminar la conversación.'); } catch (err) { bubble('simon', err.message); }
});
$('oir').addEventListener('click', () => {
  const last = [...document.querySelectorAll('.simon')].pop();
  if (last) say(last.textContent);
});
$('guardar-ritmo').addEventListener('click', async () => {
  const res = await fetch('/api/simon/ritmo', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(settings())});
  const data = await res.json();
  bubble('simon', data.stored ? 'Guardé el ritmo en el servidor.' : 'Dejé el ritmo en esta pantalla. Si aceptas el aviso, también puedo recordarlo.');
});
for (let n = 1; n <= 5; n++) {
  const b = document.createElement('button');
  b.type = 'button';
  b.textContent = String(n);
  b.addEventListener('click', () => { $('stars').dataset.value = String(n); [...$('stars').children].forEach(ch => ch.disabled = false); b.setAttribute('aria-pressed', 'true'); });
  $('stars').append(b);
}
$('feedback-form').addEventListener('submit', async e => {
  e.preventDefault();
  const form = new FormData(e.currentTarget);
  const body = {
    conversation_id: conversation,
    declared_opened: form.get('declared_opened') === 'si',
    resolution: form.get('resolution'),
    visibility: form.get('visibility'),
    comment: $('comentario').value,
    rating: $('stars').dataset.value ? Number($('stars').dataset.value) : null,
    accept_storage: $('aceptar').checked || consent,
  };
  const res = await fetch('/api/simon/feedback', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  const data = await res.json();
  $('feedback-estado').textContent = data.message || data.error || 'Listo.';
});
try {
  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (Rec) {
    const rec = new Rec();
    rec.lang = 'es-CO';
    rec.onresult = ev => {
      const said = ev.results[ev.results.length - 1][0].transcript || '';
      const words = said.trim().split(/\s+/).filter(Boolean).length;
      if (words) speaking = Math.max(40, Math.min(220, words * 8));
    };
  }
} catch (err) { /* el ritmo de voz es opcional */ }
const aviso = await fetch('/api/simon/aviso').then(r => r.json());
$('aviso').innerHTML = `<p><b>${aviso.titulo}</b></p><p></p><p><button type="button" id="si">Acepto guardar</button> <button type="button" id="no">Seguir sin guardar</button> <a href="/privacidad">Política de privacidad</a></p>`;
$('aviso').querySelector('p:nth-child(2)').textContent = aviso.texto;
$('si').addEventListener('click', async () => {
  await fetch('/api/simon/consentimiento', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({accepted: true})});
  consent = true;
  $('aviso').querySelector('b').textContent = 'Gracias. La conversación se guarda cifrada y puedes borrarla cuando quieras.';
});
$('no').addEventListener('click', async () => {
  await fetch('/api/simon/consentimiento', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({accepted: false})});
  consent = false;
  $('aviso').querySelector('b').textContent = 'De acuerdo. Puedes hablar y no guardaré la conversación.';
});
bubble('simon', 'Hola, soy Simon. Cuéntame con calma qué buscas. Si es un apartamento, dime el municipio y si es arriendo, renta corta o venta.');
