// SPDX-License-Identifier: AGPL-3.0-or-later
const $ = id => document.getElementById(id);
const money = n => new Intl.NumberFormat('es-CO', {style: 'currency', currency: 'COP', maximumFractionDigits: 0}).format(n);
const states = {not_synced: 'Sin sincronizar', configuration_required: 'Falta configurar', error: 'Error de acceso', no_supported_data: 'Requiere adaptar conector', partial: 'Actualización parcial', ok: 'Actualizado'};
const ops = {arriendo: 'Arriendo', renta_corta: 'Renta corta', venta: 'Venta'};
const whole = value => (value == null || value === '') ? '—' : (Number(value) % 1 === 0 ? String(Math.round(Number(value))) : String(value));
const stays = {dias: 'días', semanas: 'semanas', meses_3: '3 meses', meses_6: '6 meses', meses_12: '12 meses', mensual: 'mes a mes'};
let next = null, loading = false;
const node = (tag, text, cls) => { const el = document.createElement(tag); if (text) el.textContent = text; if (cls) el.className = cls; return el; };
function showSources(sources) {
  $('sources').replaceChildren(...sources.map(s => node('li', `${s.name} · ${states[s.state] || s.state}${s.checked_at ? ' · ' + new Date(s.checked_at).toLocaleString('es-CO') : ''}${s.accepted !== undefined ? ' · ' + s.accepted + ' anuncios en la última pasada' : ''}${s.note ? ' · ' + s.note : ''}`, s.state === 'ok' ? '' : 'bad')));
}
function priceLine(r) {
  const bits = [];
  if (r.price_day) bits.push(money(r.price_day) + ' / día');
  if (r.price_week) bits.push(money(r.price_week) + ' / semana');
  if (r.price_month) bits.push(money(r.price_month) + ' / mes');
  if (r.price_sale) bits.push(money(r.price_sale) + ' en venta');
  if (!bits.length) bits.push(money(r.price) + ((r.operation === 'venta') ? ' en venta' : ' / mes'));
  return bits.join(' · ');
}
function render(data, append = false) {
  const rows = data.results || data.cards || [];
  if (!append) $('results').replaceChildren();
  $('result-title').textContent = `${data.total ?? rows.length} apartamentos en el índice`;
  $('message').textContent = data.message || data.notice || '';
  const labels = {municipality: 'Municipio', max_price: 'Máximo COP', min_bedrooms: 'Habitaciones mínimas', min_bathrooms: 'Baños mínimos', min_area_m2: 'Área mínima m²', neighborhood: 'Barrio', operation: 'Operación', stay: 'Estancia'};
  if (data.applied_filters) $('filters').textContent = 'Filtros aplicados: ' + (Object.entries(data.applied_filters).filter(([k, v]) => labels[k] && v !== '').map(([k, v]) => `${labels[k]}: ${v}`).join(' · ') || 'Sin restricciones adicionales');
  for (const r of rows) {
    const card = node('article', '', 'card');
    card.append(
      node('h3', `${ops[r.operation] || 'Publicación'} · ${r.municipality}${r.neighborhood ? ' · ' + r.neighborhood : ''}`),
      node('p', priceLine(r), 'price'),
      node('p', `${whole(r.area_m2)} m² · ${whole(r.bedrooms)} habitaciones · ${whole(r.bathrooms)} baños`),
      node('p', (r.stay_types || []).map(s => stays[s] || s).join(', '), 'date'),
    );
    for (const p of r.publications || [{source_name: r.source_name, price: r.price, original_url: r.original_url, checked_at: r.checked_at}]) {
      if (!p.original_url) continue;
      const url = new URL(p.original_url);
      if (url.protocol !== 'https:') continue;
      const a = node('a', `${p.source_name || r.source_name} · abrir ficha`);
      a.href = url.href; a.target = '_blank'; a.rel = 'noopener noreferrer';
      card.append(a);
      if (p.checked_at) card.append(node('p', 'Observado: ' + new Date(p.checked_at).toLocaleString('es-CO'), 'date'));
    }
    $('results').append(card);
  }
  if (data.sources) showSources(data.sources);
  $('more').hidden = data.total == null || data.offset + rows.length >= data.total;
}
async function run(url, options = {}, append = false) {
  if (loading) return;
  loading = true;
  document.querySelectorAll('button').forEach(b => b.disabled = true);
  $('message').textContent = 'Consultando publicaciones…';
  try {
    const res = await fetch(url, options);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'No se pudo consultar');
    render(data, append);
    if (next) next.offset = (data.offset || 0) + (data.results || []).length;
  } catch (e) {
    $('message').textContent = e.message;
    $('more').hidden = true;
    if (!append) { $('results').replaceChildren(); $('result-title').textContent = 'Consulta sin completar'; }
  } finally {
    loading = false;
    document.querySelectorAll('button').forEach(b => b.disabled = false);
  }
}
$('search').addEventListener('submit', e => {
  e.preventDefault();
  const filters = Object.fromEntries([...new FormData(e.currentTarget)].filter(([, v]) => v !== ''));
  next = {type: 'search', filters, offset: 0};
  run('/api/apartamentos?' + new URLSearchParams(filters));
});
$('agent').addEventListener('submit', e => {
  e.preventDefault();
  const values = Object.fromEntries(new FormData(e.currentTarget));
  next = {type: 'agent', ...values, offset: 0};
  run(`/api/${values.agent}/apartamentos`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: values.message})});
});
$('more').addEventListener('click', () => {
  if (!next) return;
  if (next.type === 'agent') run(`/api/${next.agent}/apartamentos`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: next.message, filters: {offset: next.offset}})}, true);
  else run('/api/apartamentos?' + new URLSearchParams({...next.filters, offset: next.offset}), {}, true);
});
try {
  const res = await fetch('/api/apartamentos/fuentes');
  if (!res.ok) throw new Error('No se pudo leer el estado de las fuentes');
  const data = await res.json();
  for (const m of data.municipalities) { const option = node('option', m); option.value = m; $('municipality').append(option); }
  showSources(data.sources);
} catch (e) { $('message').textContent = e.message; }
