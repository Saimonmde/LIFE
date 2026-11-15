# SPDX-License-Identifier: AGPL-3.0-or-later
"""Índice de publicaciones externas. Nunca genera anuncios ni infiere disponibilidad."""
from contextlib import contextmanager
import datetime as dt
import hashlib
import json
import math
import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES = ('Medellín', 'Envigado', 'Sabaneta', 'Itagüí', 'La Estrella',
                  'Caldas', 'Bello', 'Copacabana', 'Girardota', 'Barbosa')
TTL_HOURS = 48


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value or '').lower())
                   if not unicodedata.combining(c)).strip()


def municipality(value):
    return next((m for m in MUNICIPALITIES if folded(m) == folded(value)), None)


def number(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (float, int)):
        return float(value) if math.isfinite(value) else None
    s = re.sub(r'[^\d,.]', '', str(value))
    if not s:
        return None
    # COP usa miles con punto/coma; las áreas pueden contener decimales.
    if re.fullmatch(r'\d{1,3}([.,]\d{3})+', s):
        s = s.replace('.', '').replace(',', '')
    elif ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    else:
        s = s.replace(',', '.')
    try:
        n = float(s)
        return n if math.isfinite(n) else None
    except ValueError:
        return None


def canonical_url(value, hosts=None):
    u = urlsplit(str(value or ''))
    host = (u.hostname or '').lower()
    if u.scheme != 'https' or not host or u.username or u.password or u.port not in (None, 443):
        raise ValueError('Enlace original HTTPS inválido')
    if hosts is not None and host not in hosts:
        raise ValueError('El enlace no pertenece a la fuente')
    query = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    return urlunsplit(('https', host, u.path or '/', urlencode(sorted(query)), ''))


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sources():
    path = os.environ.get('APARTMENTS_SOURCES_FILE') or ROOT / 'data/apartments/sources.json'
    rows = json.loads(Path(path).read_text())
    if len({s['id'] for s in rows}) != len(rows):
        raise ValueError('Identificadores de fuentes repetidos')
    for s in rows:
        if s.get('url_env'):
            s['url'] = os.environ.get(s['url_env'], '')
        if s.get('hosts_env'):
            s['hosts'] = [h.strip().lower() for h in os.environ.get(s['hosts_env'], '').split(',') if h.strip()]
    return sorted(rows, key=lambda s: s.get('priority', 100))


STAYS = ('dias', 'semanas', 'meses_3', 'meses_6', 'meses_12', 'mensual')
OPERATIONS = ('renta_corta', 'arriendo', 'venta')


def canonical_operation(value):
    key = folded(value).replace('_', ' ')
    return {
        'arriendo': 'arriendo', 'alquiler': 'arriendo', 'rent': 'arriendo',
        'mensual': 'arriendo', 'venta': 'venta', 'sale': 'venta', 'comprar': 'venta',
        'renta corta': 'renta_corta', 'alquiler vacacional': 'renta_corta',
        'arriendo temporal': 'renta_corta', 'vacacional': 'renta_corta',
    }.get(key)


def stay_types_for(raw, operation):
    if isinstance(raw.get('stay_types'), list):
        picked = [item for item in raw['stay_types'] if item in STAYS]
        if picked:
            return picked
    text = folded(' '.join(str(raw.get(key) or '') for key in ('title', 'stay', 'notes')))
    found = []
    if re.search(r'por dias|diario|vacacional|arriendo temporal', text):
        found.append('dias')
    if re.search(r'por semana|semanal', text):
        found.append('semanas')
    if re.search(r'3 meses', text):
        found.append('meses_3')
    if re.search(r'6 meses', text):
        found.append('meses_6')
    if re.search(r'12 meses|un ano', text):
        found.append('meses_12')
    if found:
        return found
    if operation == 'renta_corta':
        return ['dias', 'semanas']
    if operation == 'arriendo':
        return ['mensual']
    return []


def price_parts(raw, operation, price):
    day = number(raw.get('price_day') if raw.get('price_day') is not None else raw.get('price_per_day'))
    week = number(raw.get('price_week') if raw.get('price_week') is not None else raw.get('price_per_week'))
    month = number(raw.get('price_month') if raw.get('price_month') is not None else raw.get('price_per_month'))
    sale = number(raw.get('price_sale') if raw.get('price_sale') is not None else raw.get('sale_price'))
    for key, value in (('day', day), ('week', week), ('month', month), ('sale', sale)):
        if value is not None and value <= 0:
            if key == 'day':
                day = None
            elif key == 'week':
                week = None
            elif key == 'month':
                month = None
            else:
                sale = None
    if operation == 'arriendo':
        month = month or price
    elif operation == 'venta':
        sale = sale or price
    elif operation == 'renta_corta' and day is None and week is None and month is None:
        if price is not None and price < 500000:
            day = price
        else:
            month = price
    def whole(value):
        return None if value is None else int(round(value))
    return whole(day), whole(week), whole(month), whole(sale)


def attach_offer(row, raw, operation):
    day, week, month, sale = price_parts(raw, operation, row['price'])
    row['operation'] = operation
    row['stay_types'] = stay_types_for(raw, operation)
    row['price_day'] = day
    row['price_week'] = week
    row['price_month'] = month
    row['price_sale'] = sale
    return row


def normalize(raw, source, checked_at=None):
    """Contrato de feed histórico: apartamento en arriendo, COP y municipio explícito."""
    if folded(raw.get('property_type')) not in ('apartamento', 'apartment'):
        raise ValueError('No es apartamento')
    if folded(raw.get('operation')) not in ('arriendo', 'alquiler', 'rent'):
        raise ValueError('No es arriendo')
    if raw.get('currency') != 'COP':
        raise ValueError('Moneda no confirmada como COP')
    city = municipality(raw.get('municipality'))
    price = number(raw.get('price'))
    if not city or price is None or price <= 0:
        raise ValueError('Faltan municipio del Valle de Aburrá o precio válido')
    url = canonical_url(raw.get('original_url'), source.get('hosts', []))
    if urlsplit(url).path == '/':
        raise ValueError('Se exige enlace a una publicación')
    now = checked_at or timestamp()
    row = {'id': hashlib.sha256((source['id'] + '|' + url).encode()).hexdigest()[:24],
           'source': source['id'], 'source_name': source['name'], 'priority': source.get('priority', 100),
           'original_url': url, 'price': int(round(price)), 'currency': 'COP',
           'municipality': city, 'neighborhood': str(raw.get('neighborhood') or '').strip()[:160] or None,
           'area_m2': number(raw.get('area_m2')), 'bedrooms': number(raw.get('bedrooms')),
           'bathrooms': number(raw.get('bathrooms')), 'address': str(raw.get('address') or '').strip()[:240] or None,
           'unit': str(raw.get('unit') or '').strip()[:80] or None,
           'title': str(raw.get('title') or 'Apartamento en arriendo')[:240],
           'published_at': raw.get('published_at'), 'checked_at': now,
           'active': raw.get('active', True) is True, 'property_type': 'apartamento', 'operation': 'arriendo'}
    for key in ('area_m2', 'bedrooms', 'bathrooms'):
        if row[key] is not None and row[key] <= 0:
            row[key] = None
        elif key != 'area_m2' and isinstance(row[key], float) and row[key] == int(row[key]):
            row[key] = int(row[key])
    return attach_offer(row, raw, 'arriendo')


def normalize_offer(raw, source, checked_at=None):
    """Arriendo, venta o renta corta. La venta sigue rechazada en normalize()."""
    operation = canonical_operation(raw.get('operation'))
    if operation in (None, 'arriendo'):
        return normalize(raw, source, checked_at)
    if folded(raw.get('property_type')) not in ('apartamento', 'apartment'):
        raise ValueError('No es apartamento')
    currency = raw.get('currency')
    if currency == '$':
        currency = 'COP'
    if currency != 'COP':
        raise ValueError('Moneda no confirmada como COP')
    city = municipality(raw.get('municipality'))
    price = number(raw.get('price'))
    if not city or price is None or price <= 0:
        raise ValueError('Faltan municipio del Valle de Aburrá o precio válido')
    url = canonical_url(raw.get('original_url'), source.get('hosts', []))
    if urlsplit(url).path == '/':
        raise ValueError('Se exige enlace a una publicación')
    now = checked_at or timestamp()
    titles = {'venta': 'Apartamento en venta', 'renta_corta': 'Apartamento en renta corta'}
    row = {'id': hashlib.sha256((source['id'] + '|' + url).encode()).hexdigest()[:24],
           'source': source['id'], 'source_name': source['name'], 'priority': source.get('priority', 100),
           'original_url': url, 'price': int(round(price)), 'currency': 'COP',
           'municipality': city, 'neighborhood': str(raw.get('neighborhood') or '').strip()[:160] or None,
           'area_m2': number(raw.get('area_m2')), 'bedrooms': number(raw.get('bedrooms')),
           'bathrooms': number(raw.get('bathrooms')), 'address': str(raw.get('address') or '').strip()[:240] or None,
           'unit': str(raw.get('unit') or '').strip()[:80] or None,
           'title': str(raw.get('title') or titles[operation])[:240],
           'published_at': raw.get('published_at'), 'checked_at': now,
           'active': raw.get('active', True) is True, 'property_type': 'apartamento', 'operation': operation}
    for key in ('area_m2', 'bedrooms', 'bathrooms'):
        if row[key] is not None and row[key] <= 0:
            row[key] = None
        elif key != 'area_m2' and isinstance(row[key], float) and row[key] == int(row[key]):
            row[key] = int(row[key])
    return attach_offer(row, raw, operation)


class Index:
    """SQLite local; Postgres dedicado si existe DATABASE_URL. No usa stores del juego."""
    def __init__(self, path=None):
        self.pg = bool(os.environ.get('DATABASE_URL')) and path is None
        self.path = str(path or os.environ.get('APARTMENTS_DB_PATH') or ROOT / 'state/apartments.sqlite3')
        if not self.pg:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS apartment_listings (id TEXT PRIMARY KEY, doc TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS apartment_source_status (id TEXT PRIMARY KEY, doc TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        if self.pg:
            import psycopg
            connection = psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10)
        else:
            connection = sqlite3.connect(self.path, timeout=20)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _upsert(self, c, table, ident, doc):
        marker = '%s' if self.pg else '?'
        c.execute(f'INSERT INTO {table}(id,doc) VALUES ({marker},{marker}) '
                  'ON CONFLICT(id) DO UPDATE SET doc=excluded.doc', (ident, json.dumps(doc, ensure_ascii=False)))

    def ingest(self, source, rows, report):
        with self.connect() as c:
            for row in rows:
                self._upsert(c, 'apartment_listings', row['id'], row)
            self._upsert(c, 'apartment_source_status', source['id'], report)
        # Una pasada parcial nunca elimina anuncios no visitados. Caducan por checked_at.

    def has_url(self, url):
        try:
            canon = canonical_url(url)
        except ValueError:
            return False
        with self.connect() as conn:
            rows = [json.loads(doc) for (doc,) in conn.execute('SELECT doc FROM apartment_listings')]
        for row in rows:
            if row.get('original_url') == canon:
                return True
            for pub in row.get('publications') or []:
                if pub.get('original_url') == canon:
                    return True
        return False

    def status(self):
        with self.connect() as c:
            reports = {i: json.loads(d) for i, d in c.execute('SELECT id,doc FROM apartment_source_status')}
        return [{'id': s['id'], 'name': s['name'], 'priority': s.get('priority'),
                 **reports.get(s['id'], {'state': 'not_synced', 'note': s.get('note')})} for s in sources()]

    def search(self, filters):
        allowed = {'municipality', 'neighborhood', 'min_price', 'max_price', 'min_area_m2',
                   'min_bedrooms', 'min_bathrooms', 'limit', 'offset', 'operation', 'stay', 'price_basis'}
        if set(filters) - allowed:
            raise ValueError('Filtros no soportados: ' + ', '.join(sorted(set(filters) - allowed)))
        city = filters.get('municipality')
        if city and not municipality(city):
            raise ValueError('Municipio no reconocido')
        city = municipality(city) if city else None
        budget = number(filters.get('max_price'))
        beds = number(filters.get('min_bedrooms'))
        baths = number(filters.get('min_bathrooms'))
        area = number(filters.get('min_area_m2'))
        low = number(filters.get('min_price'))
        for key in ('max_price', 'min_price', 'min_bedrooms', 'min_bathrooms', 'min_area_m2'):
            if filters.get(key) not in (None, '') and (number(filters[key]) is None or number(filters[key]) < 0):
                raise ValueError('Filtro numérico inválido: ' + key)
        operation = filters.get('operation') or None
        stay = filters.get('stay') or None
        basis = filters.get('price_basis') or None
        if operation and operation not in OPERATIONS:
            raise ValueError('Operación no reconocida')
        if stay and stay not in STAYS:
            raise ValueError('Tipo de estancia no reconocido')
        if basis and basis not in ('day', 'week', 'month', 'sale'):
            raise ValueError('Base de precio no reconocida')
        limit = min(50, max(1, int(filters.get('limit') or 20)))
        offset = min(10000, max(0, int(filters.get('offset') or 0)))
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=TTL_HOURS)
        with self.connect() as c:
            rows = [json.loads(d) for (d,) in c.execute('SELECT doc FROM apartment_listings')]
        selected = []
        for r in rows:
            checked = dt.datetime.fromisoformat(r['checked_at'])
            if not r['active'] or checked < cutoff:
                continue
            if city and r['municipality'] != city:
                continue
            if operation and r.get('operation', 'arriendo') != operation:
                continue
            if stay and stay not in (r.get('stay_types') or []):
                continue
            if filters.get('neighborhood') and folded(filters['neighborhood']) not in folded(r['neighborhood']):
                continue
            amount = r['price']
            if basis:
                amount = {'day': r.get('price_day'), 'week': r.get('price_week'),
                          'month': r.get('price_month'), 'sale': r.get('price_sale')}[basis]
                if amount is None:
                    continue
            if budget is not None and amount > budget or low is not None and amount < low:
                continue
            if any(n is not None and (r[k] is None or r[k] < n) for k, n in
                   (('bedrooms', beds), ('bathrooms', baths), ('area_m2', area))):
                continue
            selected.append(r)
        grouped = deduplicate(selected)
        grouped.sort(key=lambda r: (r['price'], r['priority'], r['id']))
        return {'results': grouped[offset:offset + limit], 'total': len(grouped), 'offset': offset,
                'municipalities': MUNICIPALITIES, 'sources': self.status(), 'max_age_hours': TTL_HOURS,
                'notice': 'Publicaciones observadas; confirma disponibilidad y precio con el anunciante.'}


def deduplicate(rows):
    """Sólo fusiona coincidencias fuertes: dirección y unidad explícitas + atributos.

    No agrupa por precio/barrio/área: puede haber varios apartamentos idénticos.
    Conserva todas las publicaciones y sus precios/fechas.
    """
    groups = {}
    for r in sorted(rows, key=lambda x: (x['priority'], x['id'])):
        key = ('url', r['original_url'])
        if r['address'] and r['unit'] and all(r[k] is not None for k in ('area_m2', 'bedrooms', 'bathrooms')):
            key = ('unit', folded(r['municipality']), re.sub(r'\W', '', folded(r['address'])),
                   folded(r['unit']), r['area_m2'], r['bedrooms'], r['bathrooms'])
        pub = {k: r[k] for k in ('source', 'source_name', 'original_url', 'price', 'checked_at', 'published_at')}
        if key in groups:
            groups[key]['publications'].append(pub)
        else:
            groups[key] = {**r, 'publications': [pub]}
    return list(groups.values())


def parse_request(text):
    """Intenciones comunes; no ignora restricciones que no pueda interpretar."""
    text = folded(text)
    cities = [m for m in MUNICIPALITIES if re.search(r'(?<!\w)' + re.escape(folded(m)) + r'(?!\w)', text)]
    if len(cities) > 1:
        raise ValueError('Indica un municipio por búsqueda o usa el filtro de todos los municipios.')
    filters = {'municipality': cities[0]} if cities else {}
    for pattern, key in ((r'(\d+)\s*(?:habitaciones|alcobas|cuartos)', 'min_bedrooms'),
                         (r'(\d+)\s*banos', 'min_bathrooms'), (r'(\d+(?:[,.]\d+)?)\s*(?:m2|m²|metros)', 'min_area_m2')):
        found = re.search(pattern, text)
        if found:
            filters[key] = number(found[1])
    found = re.search(r'(?:hasta|maximo|presupuesto(?: de)?|menos de|tope(?: de)?)\s*\$?\s*([\d.,]+)\s*(millones?|millon|mil)?', text)
    if found:
        amount = number(found[1])
        unit = found[2] or ''
        if amount is not None:
            filters['max_price'] = int(amount * (1000000 if unit.startswith('millon') else 1000 if unit == 'mil' else 1))
    neighborhood = re.search(r'(?:barrio|sector)\s+([a-z ]+?)(?=\s+(?:hasta|con|maximo|presupuesto|de \d)|[,.;]|$)', text)
    if neighborhood:
        filters['neighborhood'] = neighborhood[1].strip()
    # Venta y comodidades requieren otros filtros; no devolver coincidencias engañosas.
    unsupported = [term for term in ('comprar', 'venta', 'amoblado', 'parqueadero', 'mascotas', 'balcon', 'ascensor') if term in text]
    if unsupported:
        raise ValueError('Usa los filtros disponibles (municipio, barrio, precio, área, habitaciones y baños). Aún no puedo filtrar: ' + ', '.join(unsupported))
    return filters


def agent_search(index, agent, text, filters=None):
    if agent not in ('simon-ia', 'simon-io'):
        raise ValueError('Agente desconocido')
    if not isinstance(text, str) or len(text) > 2000:
        raise ValueError('Petición inválida')
    parsed = parse_request(text)
    parsed.update(filters or {})
    result = index.search(parsed)
    result.update({'agent': agent, 'applied_filters': parsed, 'tool': 'search_apartments',
                   'message': f"Encontré {result['total']} apartamentos publicados." if result['total'] else
                   'No encontré publicaciones recientes que cumplan los filtros en el índice. Revisa el estado de las fuentes; esto no demuestra que no existan apartamentos.'})
    return result
