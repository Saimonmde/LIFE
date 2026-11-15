#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sincronizador acotado de feeds/HTML público. Uso: python3 tools/apartment_sync.py."""
import argparse
import datetime as dt
import gzip
import ipaddress
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import apartments as A

USER_AGENT = 'SimonCityApartmentIndex/1.0'
MAX_BYTES = 4 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Fetcher:
    """Dominios explícitos, HTTPS, IP pública y redirecciones revalidadas.

    Las URLs del usuario nunca entran al sincronizador. No evade 403/CAPTCHA.
    """
    def __init__(self, hosts, delay=1):
        self.hosts = hosts
        self.delay = delay
        self.last = 0
        self.robots = {}
        self.opener = urllib.request.build_opener(NoRedirect())

    def validate(self, url):
        url = A.canonical_url(url, self.hosts)
        for addr in socket.getaddrinfo(urlsplit(url).hostname, 443, type=socket.SOCK_STREAM):
            if not ipaddress.ip_address(addr[4][0]).is_global:
                raise ValueError('La fuente debe resolver a direcciones públicas')
        return url

    def request(self, url, token=None):
        for _ in range(5):
            url = self.validate(url)
            time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json,text/html,application/xml'}
            if token:
                headers['Authorization'] = 'Bearer ' + token
            parts = urlsplit(url)
            safe = urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe='/%'),
                               quote(parts.query, safe='=&%'), ''))
            req = urllib.request.Request(safe, headers=headers)
            try:
                response = self.opener.open(req, timeout=15)
            except urllib.error.HTTPError as exc:
                if exc.code in (301, 302, 303, 307, 308):
                    # Never forward a feed token to a different origin.
                    next_url = urljoin(url, exc.headers.get('Location', ''))
                    if urlsplit(next_url).netloc != urlsplit(url).netloc:
                        token = None
                    url = next_url
                    continue
                raise
            with response:
                content = response.read(MAX_BYTES + 1)
                if len(content) > MAX_BYTES:
                    raise ValueError('Documento demasiado grande')
                if content[:2] == b'\x1f\x8b':
                    import io
                    with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
                        content = gz.read(MAX_BYTES + 1)
                    if len(content) > MAX_BYTES:
                        raise ValueError('Documento comprimido demasiado grande')
                charset = response.headers.get_content_charset()
                if not charset:
                    head = content[:600].decode('ascii', 'replace')
                    meta = re.search(r'charset=["\']?([\w-]+)', head, re.I)
                    charset = meta.group(1) if meta else 'utf-8'
                return content.decode(charset, errors='replace'), url
        raise ValueError('Demasiadas redirecciones')

    def public(self, url):
        origin = 'https://' + urlsplit(url).netloc
        if origin not in self.robots:
            robots, _ = self.request(origin + '/robots.txt')
            parser = urllib.robotparser.RobotFileParser()
            parser.parse(robots.splitlines())
            self.robots[origin] = parser
        parser = self.robots[origin]
        if not parser.can_fetch(USER_AGENT, url):
            raise PermissionError('robots.txt no permite esta ruta')
        delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay('*')
        if delay:
            self.delay = max(self.delay, delay)
        return self.request(url)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.texts = []
        self.h1 = []
        self.in_h1 = False
        self.hidden = 0
        self.scripts = []
        self.recording = False
        self.buffer = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'h1':
            self.in_h1 = True
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'script' and attrs.get('type', '').lower() == 'application/ld+json':
            self.recording = True
            self.buffer = []

    def handle_data(self, data):
        if self.recording:
            self.buffer.append(data)
        if not self.hidden and data.strip():
            self.texts.append(data.strip())
            if self.in_h1:
                self.h1.append(data.strip())

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if tag == 'h1':
            self.in_h1 = False
        if tag == 'script' and self.recording:
            try:
                self.scripts.append(json.loads(''.join(self.buffer)))
            except ValueError:
                pass
            self.recording = False


def objects(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from objects(v)
    elif isinstance(value, list):
        for v in value:
            yield from objects(v)


def scalar(value):
    return value.get('value') if isinstance(value, dict) else value


def structured_rows(document, page_url):
    """Schema.org Apartment / RealEstateListing. No mezcla datos de tarjetas distintas."""
    for script in document.scripts:
        for obj in objects(script):
            typ = obj.get('@type', [])
            types = [typ] if isinstance(typ, str) else typ
            if not set(types or []) & {'Apartment', 'RealEstateListing', 'Product', 'Residence'}:
                continue
            entity = obj.get('mainEntity') or obj.get('itemOffered') or obj
            if not isinstance(entity, dict):
                continue
            offer = obj.get('offers') or entity.get('offers') or {}
            if isinstance(offer, list):
                offer = offer[0] if offer else {}
            if not isinstance(offer, dict):
                continue
            title = obj.get('name') or entity.get('name') or ''
            url = obj.get('url') or entity.get('url') or offer.get('url') or page_url
            if not isinstance(url, str):
                continue
            context = A.folded(str(title) + ' ' + url)
            if not re.search(r'apartament|apartment', context):
                continue
            # La operación tiene que estar escrita; no se infiere del precio.
            rent = re.search(r'arriendo|alquiler|\brent\b', context) or 'LeaseOut' in str(offer.get('businessFunction', ''))
            sale = re.search(r'\bventa\b|\bsale\b', context) or 'Sell' in str(offer.get('businessFunction', ''))
            if not rent and not sale:
                continue
            operation = 'venta' if sale and not rent else 'arriendo'
            address = entity.get('address') or obj.get('address') or {}
            if not isinstance(address, dict):
                continue
            floor = entity.get('floorSize') or {}
            if isinstance(floor, dict) and floor.get('unitCode') not in (None, 'MTK', 'm2'):
                floor = None
            spec = offer.get('priceSpecification') or {}
            available = str(offer.get('availability', ''))
            yield {'title': title, 'property_type': 'apartamento', 'operation': operation,
                   'currency': offer.get('priceCurrency') or spec.get('priceCurrency'),
                   'price': offer.get('price') or spec.get('price'),
                   'municipality': address.get('addressLocality'),
                   'neighborhood': address.get('neighborhood'),
                   'address': address.get('streetAddress'), 'unit': entity.get('unitNumber'),
                   'area_m2': scalar(floor), 'bedrooms': scalar(entity.get('numberOfBedrooms')),
                   'bathrooms': scalar(entity.get('numberOfBathroomsTotal')),
                   'published_at': obj.get('datePosted') or obj.get('datePublished'),
                   'original_url': urljoin(page_url, url),
                   'active': not any(x in available for x in ('SoldOut', 'OutOfStock', 'Discontinued'))}



def metrocuadrado_detail(document, page_url):
    """Respaldo para la ficha visible de Metro Cuadrado cuando falta JSON-LD.

    Exige ruta de apartamento en arriendo, H1 y precio cerca del encabezado.
    Las cifras de habitaciones/baños salen de los segmentos explícitos de URL.
    """
    path = A.folded(urlsplit(page_url).path)
    if not path.startswith('/inmueble/arriendo-apartamento-'):
        return []
    title = ' '.join(document.h1)
    if 'apartamento' not in A.folded(title) or 'arriendo' not in A.folded(title):
        return []
    text = ' '.join(document.texts)
    start = text.find(title)
    if start < 0:
        return []
    header = text[start:start + 1500]
    price = re.search(r'\$\s*([\d.,]+)', header)
    cities = [m for m in A.MUNICIPALITIES if re.search(r'(?<![a-z])' + re.escape(A.folded(m).replace(' ', '-')) + r'(?![a-z])', path)]
    if not price or len(cities) != 1:
        return []
    area = re.search(r'area\s+construida\s*([\d.,]+)\s*m', A.folded(header))
    beds = re.search(r'-(\d+)-habitaciones', path)
    baths = re.search(r'-(\d+)-banos', path)
    return [{'title': title, 'property_type': 'apartamento', 'operation': 'arriendo',
             'price': price[1], 'currency': 'COP', 'municipality': cities[0],
             'neighborhood': title.partition(',')[2].strip() or None,
             'area_m2': area[1] if area else None, 'bedrooms': beds[1] if beds else None,
             'bathrooms': baths[1] if baths else None, 'original_url': page_url}]


def _sheet(item):
    rows = item.get('technicalSheet') or []
    if isinstance(rows, dict):
        return {str(k): v for k, v in rows.items()}
    found = {}
    for row in rows:
        if isinstance(row, dict) and row.get('field'):
            found[str(row['field'])] = row.get('value')
    return found


def _json_script(html, script_id):
    match = re.search(r'<script id="%s"[^>]*>(.*?)</script>' % re.escape(script_id), html, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except ValueError:
        return None


def fincaraiz_rows(html, page_url):
    """Listados en __NEXT_DATA__. No copia fotos ni la descripción larga."""
    data = _json_script(html, '__NEXT_DATA__')
    if not data:
        return []
    try:
        items = data['props']['pageProps']['fetchResult']['searchFast']['data']
    except (KeyError, TypeError):
        return []
    if not isinstance(items, list):
        return []
    path = A.folded(urlsplit(page_url).path)
    if 'temporal' in path or 'vacacional' in path:
        operation = 'renta_corta'
    elif path.startswith('/venta/') or '/venta/' in path:
        operation = 'venta'
    else:
        operation = 'arriendo'
    rows = []
    for item in items:
        if not isinstance(item, dict) or item.get('price', {}).get('hidePrice'):
            continue
        sheet = _sheet(item)
        kind = A.folded(sheet.get('property_type_name') or item.get('title'))
        if 'apartament' not in kind and item.get('typeID') != 2:
            continue
        link = item.get('link')
        if not isinstance(link, str):
            continue
        locations = item.get('locations') or {}
        city = None
        cities = locations.get('city') or []
        if cities and isinstance(cities[0], dict):
            city = cities[0].get('name')
        neighborhood = None
        main = locations.get('location_main') or {}
        if isinstance(main, dict):
            neighborhood = main.get('name')
        amount = (item.get('price') or {}).get('amount')
        address = item.get('address') if item.get('showAddress') else None
        unit = None
        if isinstance(address, str):
            found = re.search(r'\b(?:int|apto|apartamento|unidad)\s*([0-9a-z-]{1,8})', address, re.I)
            unit = found.group(1) if found else None
        rows.append({
            'title': item.get('title'), 'property_type': 'apartamento', 'operation': operation,
            'currency': 'COP', 'price': amount, 'municipality': city, 'neighborhood': neighborhood,
            'address': address, 'unit': unit,
            'area_m2': sheet.get('m2Built') or sheet.get('m2apto'),
            'bedrooms': sheet.get('bedrooms'), 'bathrooms': sheet.get('bathrooms'),
            'original_url': urljoin(page_url, link),
        })
    return rows


def _unescape_jsonish(html):
    text = html.replace('\\/', '/').replace('\\"', '"')
    return re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text)


def metro_results(html, page_url):
    """Tarjetas embebidas de la búsqueda Next de Metro Cuadrado. Sin fotos ni teléfonos."""
    if 'metrocuadrado.com' not in urlsplit(page_url).netloc:
        return []
    plain = _unescape_jsonish(html)
    rows = []
    seen = set()
    for match in re.finditer(r'"link"\s*:\s*"(/inmueble/[^"]+)"', plain):
        start = plain.rfind('{"contactPhone"', 0, match.start())
        if start < 0:
            start = plain.rfind('{', max(0, match.start() - 4000), match.start())
        if start < 0:
            continue
        depth = 0
        end = None
        for index, char in enumerate(plain[start:start + 12000], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if not end:
            continue
        try:
            obj = json.loads(plain[start:end])
        except ValueError:
            continue
        link = obj.get('link')
        if not isinstance(link, str) or link in seen:
            continue
        tipo = obj.get('mtipoinmueble')
        kind = A.folded(tipo.get('nombre')) if isinstance(tipo, dict) else ''
        if kind and kind != 'apartamento':
            continue
        if 'apartamento' not in A.folded(obj.get('title')) and kind != 'apartamento':
            continue
        seen.add(link)
        business = A.folded(obj.get('mtiponegocio'))
        operation = 'venta' if business == 'venta' else 'arriendo'
        price = obj.get('mvalorventa') if operation == 'venta' else obj.get('mvalorarriendo')
        if price in (None, '', 0) and operation == 'arriendo':
            price = obj.get('mvalorventa')
            operation = 'venta' if price else operation
        city = obj.get('mciudad')
        city_name = city.get('nombre') if isinstance(city, dict) else obj.get('cityName')
        rows.append({
            'title': obj.get('title'), 'property_type': 'apartamento', 'operation': operation,
            'currency': 'COP', 'price': price, 'municipality': city_name,
            'neighborhood': obj.get('mnombrecomunbarrio') or obj.get('mbarrio'),
            'area_m2': obj.get('marea') or obj.get('mareac'),
            'bedrooms': obj.get('mnrocuartos'), 'bathrooms': obj.get('mnrobanos'),
            'original_url': urljoin('https://www.metrocuadrado.com/', link),
        })
    return rows


def _plain_text(document):
    return ' '.join(document.texts)


def tidy_url(url):
    """La ficha usa xId numérico. Un espacio o un + al final no es otro anuncio."""
    match = re.search(r'(https://[^?\s]+)\?xId=(\d+)', str(url or ''), re.I)
    if match:
        return match.group(1) + '?xId=' + match.group(2)
    return url


def ficha_rows(document, page_url):
    page_url = tidy_url(page_url)
    """Ficha.asp?xId= de Espacio Urbano y Panorama. El enlace es la ficha, no la foto."""
    if 'ficha.asp' not in page_url.lower():
        return []
    text = _plain_text(document)
    folded = A.folded(text + ' ' + ' '.join(document.h1))
    if 'apartament' not in folded:
        return []
    if 'arriendo' in folded and 'venta' not in folded.split('arriendo')[0]:
        operation = 'arriendo'
    elif re.search(r'\bventa\b', folded) and 'arriendo' not in folded:
        operation = 'venta'
    elif 'arriendo' in folded:
        operation = 'arriendo'
    else:
        return []
    if re.search(r'por dias|vacacional', folded):
        operation = 'renta_corta'
    price = re.search(r'\$\s*([\d.,]+)', text)
    if not price:
        return []
    city = None
    if 'ciudad' in folded:
        after = folded.split('ciudad', 1)[1].strip()
        for candidate in sorted(A.MUNICIPALITIES, key=len, reverse=True):
            if after.startswith(A.folded(candidate)):
                city = candidate
                break
    if not city:
        found = [m for m in A.MUNICIPALITIES if re.search(r'(?<![a-z])' + re.escape(A.folded(m)) + r'(?![a-z])', folded)]
        city = found[0] if len(found) == 1 else None
    if not city:
        return []
    area = re.search(r'area total\s*([\d.,]+)\s*m', folded)
    beds = re.search(r'alcobas familiares\s*(\d+)', folded)
    baths = re.search(r'banos familiares\s*(\d+)', folded)
    sector = re.search(r'[Ss]ector\s+([A-Za-zÁÉÍÓÚáéíóúñÑ0-9 ]{2,40}?)(?=\s+[Ee]strato|\s+[ÁAáa]rea|\s+[Aa]lcobas|$)', text)
    return [{
        'title': ' '.join(document.h1) or 'Apartamento',
        'property_type': 'apartamento', 'operation': operation, 'currency': 'COP',
        'price': price.group(1), 'municipality': city,
        'neighborhood': sector.group(1).strip() if sector else None,
        'area_m2': area.group(1) if area else None,
        'bedrooms': beds.group(1) if beds else None,
        'bathrooms': baths.group(1) if baths else None,
        'original_url': page_url,
    }]


def visible_listing(document, page_url):
    """Ficha cuya ruta ya dice apartamento, arriendo o venta. Sin copiar el texto largo."""
    path = A.folded(urlsplit(page_url).path)
    if not re.search(r'apartamento-(venta|arriendo|alquiler)|/inmueble/', path):
        return []
    folded = A.folded(_plain_text(document) + ' ' + path)
    if 'apartament' not in folded:
        return []
    if 'venta' in path and 'arriendo' not in path and 'alquiler' not in path:
        operation = 'venta'
    elif 'arriendo' in path or 'alquiler' in path:
        operation = 'arriendo'
    elif re.search(r'\bventa\b', folded) and 'arriendo' not in folded:
        operation = 'venta'
    else:
        operation = 'arriendo'
    price = re.search(r'\$\s*([\d.,]+)', _plain_text(document))
    if not price:
        return []
    cities = [m for m in A.MUNICIPALITIES if re.search(r'(?<![a-z])' + re.escape(A.folded(m)) + r'(?![a-z])', folded)]
    if len(cities) != 1:
        return []
    beds = re.search(r'(\d+)\s*(?:alcobas|habitaciones)', folded)
    baths = re.search(r'(\d+)\s*banos', folded)
    area = re.search(r'(\d+(?:[,.]\d+)?)\s*(?:m2|mts)', folded)
    return [{
        'title': ' '.join(document.h1) or 'Apartamento',
        'property_type': 'apartamento', 'operation': operation, 'currency': 'COP',
        'price': price.group(1), 'municipality': cities[0],
        'bedrooms': beds.group(1) if beds else None,
        'bathrooms': baths.group(1) if baths else None,
        'area_m2': area.group(1) if area else None,
        'original_url': page_url,
    }]


def sync_source(source, index, fetcher=None, max_pages=40):
    report = {'state': 'error', 'checked_at': A.timestamp(), 'pages': 0, 'accepted': 0, 'rejected': 0, 'errors': []}
    rows = {}
    fetcher = fetcher or Fetcher(source.get('hosts', []))
    try:
        if source['kind'] == 'feed':
            if not source.get('url') or not source.get('hosts'):
                report.update(state='configuration_required', note=source.get('note') or 'Configura URL y dominios del feed')
                index.ingest(source, [], report)
                return report
            feed_host = urlsplit(source['url']).hostname
            # API y publicaciones pueden estar en dominios distintos, ambos configurados por operador.
            fetcher.hosts = list(set(fetcher.hosts + [feed_host]))
            pending = [source['url']]
        else:
            pending = list(source.get('seeds', []))
        seen = set()
        while pending and report['pages'] < max_pages:
            url = pending.pop(0)
            if url in seen:
                continue
            seen.add(url)
            report['pages'] += 1
            try:
                if source['kind'] == 'feed':
                    body, final = fetcher.request(url, os.environ.get(source['token_env']) if source.get('token_env') else None)
                    data = json.loads(body)
                    raw_rows = data if isinstance(data, list) else data['listings']
                    if not isinstance(raw_rows, list):
                        raise ValueError('listings debe ser una lista')
                    next_page = data.get('next') if isinstance(data, dict) else None
                    if next_page:
                        next_url = urljoin(final, next_page)
                        if urlsplit(next_url).netloc != urlsplit(source['url']).netloc:
                            raise ValueError('Paginación fuera del feed')
                        pending.append(next_url)
                else:
                    body, final = fetcher.public(url)
                    doc = Document(body)
                    raw_rows = list(structured_rows(doc, final))
                    raw_rows.extend(fincaraiz_rows(body, final))
                    raw_rows.extend(metro_results(body, final))
                    raw_rows.extend(ficha_rows(doc, final))
                    raw_rows.extend(visible_listing(doc, final))
                    if not raw_rows and source['id'] == 'metrocuadrado':
                        raw_rows = metrocuadrado_detail(doc, final)
                    list_parsed = bool(raw_rows) and source['id'] in ('fincaraiz', 'metrocuadrado')
                    for link in doc.links:
                        candidate = urljoin(final, link)
                        try:
                            candidate = A.canonical_url(candidate, source['hosts'])
                        except ValueError:
                            continue
                        candidate = tidy_url(candidate)
                        is_detail = re.search(source['detail_pattern'], candidate)
                        is_page = re.search(r'[?&](page|pagina)=\d+', candidate) or re.search(r'/pagina\d+$', candidate)
                        if list_parsed and not is_page:
                            continue
                        if (is_detail or is_page) and candidate not in seen and candidate not in pending:
                            pending.append(candidate)
                for raw in raw_rows:
                    try:
                        row = A.normalize_offer(raw, source)
                        rows[row['id']] = row
                    except (ValueError, TypeError, AttributeError):
                        report['rejected'] += 1
            except Exception as exc:
                # No URLs/tokens en logs públicos. Las fallas se distinguen del inventario vacío.
                report['errors'].append({'page': report['pages'], 'type': type(exc).__name__,
                                         'http_status': getattr(exc, 'code', None)})
        report['accepted'] = len(rows)
        report['truncated'] = bool(pending)
        report['state'] = ('partial' if report['errors'] else 'ok') if rows else 'no_supported_data'
        if report['errors'] and not rows:
            report['state'] = 'error'
        if not rows and not report['errors']:
            report['note'] = 'No se extrajeron anuncios estructurados compatibles; requiere adaptar el conector o un feed. No prueba ausencia de oferta.'
    except Exception as exc:
        report['errors'].append({'type': type(exc).__name__})
    index.ingest(source, list(rows.values()), report)
    return report


CITY_SLUG = {
    'Medellín': 'medellin', 'Envigado': 'envigado', 'Sabaneta': 'sabaneta', 'Itagüí': 'itagui',
    'La Estrella': 'la-estrella', 'Caldas': 'caldas', 'Bello': 'bello', 'Copacabana': 'copacabana',
    'Girardota': 'girardota', 'Barbosa': 'barbosa',
}
LIVE_ORDER = ('rentocity', 'fincaraiz', 'metrocuadrado', 'espaciourbano', 'panorama',
              'survivienda', 'arrendamientos-sur', 'ayura', 'delnorte')


def relevant_seeds(source, municipality, operation):
    seeds = list(source.get('seeds') or [])
    slug = CITY_SLUG.get(municipality or '', '')
    narrowed = []
    for url in seeds:
        folded = A.folded(url)
        portal = source['id'] in ('fincaraiz', 'metrocuadrado')
        if portal and slug and slug not in folded:
            continue
        if portal and operation == 'venta' and 'venta' not in folded:
            continue
        if portal and operation == 'arriendo' and 'venta' in folded and 'arriendo' not in folded:
            continue
        if portal and operation == 'renta_corta' and not any(token in folded for token in ('temporal', 'vacacional')):
            continue
        narrowed.append(url)
    if narrowed:
        return narrowed[:1]
    if not portal_only(source) and operation != 'renta_corta':
        return seeds[:1]
    return []


def portal_only(source):
    return source['id'] in ('fincaraiz', 'metrocuadrado')


def fresh_enough(index, filters):
    try:
        found = index.search(dict(filters, limit=5))
    except (ValueError, TypeError):
        return False
    if not found['results']:
        return False
    newest = max(dt.datetime.fromisoformat(row['checked_at']) for row in found['results'])
    return newest >= dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=12)


def refresh_for_query(index, filters, max_pages=3):
    """Lectura acotada de semillas propias. No acepta URLs del usuario."""
    if os.environ.get('SIMON_LIVE_SEARCH', '1') == '0':
        return {'skipped': True, 'reason': 'desactivado'}
    query = {k: v for k, v in filters.items() if k in ('municipality', 'operation', 'stay')}
    if fresh_enough(index, query):
        return {'skipped': True, 'reason': 'indice_reciente'}
    reports = []
    budget = max_pages
    order = {sid: i for i, sid in enumerate(LIVE_ORDER)}
    selected = sorted(A.sources(), key=lambda s: order.get(s['id'], 50))
    for source in selected:
        if budget <= 0:
            break
        if source['kind'] == 'feed' and not source.get('url'):
            continue
        seeds = relevant_seeds(source, filters.get('municipality'), filters.get('operation'))
        if not seeds and source['kind'] != 'feed':
            continue
        scoped = dict(source)
        if seeds:
            scoped['seeds'] = seeds
        report = sync_source(scoped, index, max_pages=1 if source['id'] in ('fincaraiz', 'metrocuadrado') else min(3, budget))
        reports.append({'source': source['id'], 'state': report.get('state'), 'accepted': report.get('accepted', 0)})
        budget -= max(1, report.get('pages') or 1)
        try:
            if index.search(dict(query, limit=5))['total'] >= 5:
                break
        except (ValueError, TypeError):
            pass
    return {'skipped': False, 'reports': reports}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', help='Identificador de fuente; por defecto todas')
    p.add_argument('--max-pages', type=int, default=40)
    args = p.parse_args()
    if not 1 <= args.max_pages <= 500:
        p.error('--max-pages debe estar entre 1 y 500')
    selected = [s for s in A.sources() if not args.source or s['id'] == args.source]
    if not selected:
        p.error('Fuente desconocida')
    index = A.Index()
    for source in selected:
        print(json.dumps({'source': source['id'], **sync_source(source, index, max_pages=args.max_pages)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
