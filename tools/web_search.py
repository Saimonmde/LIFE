# SPDX-License-Identifier: AGPL-3.0-or-later
"""Búsqueda web configurable. La clave vive sólo en el entorno. Sin clave hay respaldo."""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

USER_AGENT = 'SimonCityWebSearch/1.0'
_CACHE = {}
_LAST = 0.0


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._href = None
        self._text = []
        self.feed('')

    def reset_feed(self, html):
        self.rows = []
        self._href = None
        self._text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href', '').startswith('http'):
            self._href = attrs['href']
            self._text = []

    def handle_data(self, data):
        if self._href and data.strip():
            self._text.append(data.strip())

    def handle_endtag(self, tag):
        if tag == 'a' and self._href:
            title = ' '.join(self._text)[:180]
            if title and 'duckduckgo.com' not in self._href:
                self.rows.append({'title': title, 'url': self._href, 'snippet': ''})
            self._href = None
            self._text = []


def _http(url, data=None, headers=None):
    global _LAST
    wait = 1.0 - (time.monotonic() - _LAST)
    if wait > 0:
        time.sleep(wait)
    _LAST = time.monotonic()
    head = {'User-Agent': USER_AGENT, 'Accept': 'application/json,text/html'}
    if headers:
        head.update(headers)
    body = data.encode() if isinstance(data, str) else data
    req = urllib.request.Request(url, data=body, headers=head)
    with urllib.request.urlopen(req, timeout=12) as response:
        return response.read(500000).decode('utf-8', 'replace')


def _cache_get(key):
    hit = _CACHE.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    return None


def _cache_put(key, value):
    _CACHE[key] = (time.time() + 1800, value)


def _brave(query, limit, transport):
    key = os.environ.get('BRAVE_SEARCH_API_KEY', '').strip()
    if not key:
        raise RuntimeError('sin clave')
    url = 'https://api.search.brave.com/res/v1/web/search?count=%d&q=%s' % (limit, urllib.parse.quote(query))
    raw = transport(url, headers={'X-Subscription-Token': key, 'Accept': 'application/json'})
    data = json.loads(raw)
    rows = []
    for item in (data.get('web') or {}).get('results') or []:
        if item.get('url'):
            rows.append({'title': item.get('title') or item['url'], 'url': item['url'],
                         'snippet': (item.get('description') or '')[:320]})
    return rows[:limit]


def _serper(query, limit, transport):
    key = os.environ.get('SERPER_API_KEY', '').strip()
    if not key:
        raise RuntimeError('sin clave')
    raw = transport('https://google.serper.dev/search', data=json.dumps({'q': query, 'num': limit}),
                    headers={'X-API-KEY': key, 'Content-Type': 'application/json'})
    data = json.loads(raw)
    return [{'title': item.get('title') or item.get('link'), 'url': item['link'],
             'snippet': (item.get('snippet') or '')[:320]}
            for item in (data.get('organic') or []) if item.get('link')][:limit]


def _google(query, limit, transport):
    key = os.environ.get('GOOGLE_API_KEY', '').strip()
    cx = os.environ.get('GOOGLE_CSE_ID', '').strip()
    if not key or not cx:
        raise RuntimeError('sin clave')
    url = 'https://www.googleapis.com/customsearch/v1?key=%s&cx=%s&num=%d&q=%s' % (
        urllib.parse.quote(key), urllib.parse.quote(cx), min(limit, 10), urllib.parse.quote(query))
    data = json.loads(transport(url))
    return [{'title': item.get('title') or item.get('link'), 'url': item['link'],
             'snippet': (item.get('snippet') or '')[:320]}
            for item in data.get('items') or [] if item.get('link')][:limit]


def _duckduckgo(query, limit, transport):
    url = 'https://lite.duckduckgo.com/lite/?q=' + urllib.parse.quote(query)
    html = transport(url)
    parser = _Links()
    parser.reset_feed(html)
    rows = []
    seen = set()
    for row in parser.rows:
        if row['url'] in seen:
            continue
        seen.add(row['url'])
        rows.append(row)
        if len(rows) >= limit:
            break
    snippets = re.findall(r'class="result-snippet"[^>]*>(.*?)</td>', html, re.S)
    for row, snippet in zip(rows, snippets):
        row['snippet'] = re.sub(r'<[^>]+>', '', snippet)
        row['snippet'] = re.sub(r'\s+', ' ', row['snippet']).strip()[:320]
    return rows


_PROVIDERS = {'brave': _brave, 'serper': _serper, 'google': _google, 'duckduckgo': _duckduckgo}


def _chain(name):
    order = {
        'brave': ('brave', 'serper', 'google', 'duckduckgo'),
        'serper': ('serper', 'brave', 'google', 'duckduckgo'),
        'google': ('google', 'brave', 'serper', 'duckduckgo'),
        'duckduckgo': ('duckduckgo',),
    }
    return order.get(name, (name, 'duckduckgo'))


def search(query, limit=5, transport=None):
    text = ' '.join(str(query or '').split())[:300]
    if not text:
        return {'ok': False, 'provider': None, 'results': [], 'notice': 'No hay una consulta para buscar.'}
    chosen = (os.environ.get('SIMON_WEB_SEARCH_PROVIDER') or 'brave').strip().lower()
    key = chosen + '|' + text + '|' + str(limit)
    cached = None if transport else _cache_get(key)
    if cached:
        return cached
    def carry(url, data=None, headers=None):
        if transport:
            return transport(url, data=data, headers=headers)
        return _http(url, data=data, headers=headers)
    notes = []
    for name in _chain(chosen):
        fn = _PROVIDERS.get(name)
        if not fn:
            continue
        try:
            rows = fn(text, limit, carry)
        except Exception as exc:
            notes.append(name + ':' + type(exc).__name__)
            continue
        if not rows:
            notes.append(name + ':vacio')
            continue
        notice = None
        if name == 'duckduckgo' and chosen != 'duckduckgo':
            notice = 'No hay clave del buscador configurado (' + chosen + '). Mostré el respaldo y cité esas páginas.'
        elif name != chosen:
            notice = 'Usé ' + name + ' porque ' + chosen + ' no respondió.'
        result = {'ok': True, 'provider': name, 'results': rows[:limit], 'notice': notice, 'query': text}
        if not transport:
            _cache_put(key, result)
        return result
    return {'ok': False, 'provider': None, 'results': [], 'query': text,
            'notice': 'No pude consultar la web. Revisa la clave del buscador en el servidor. Sigo con lo que ya tengo a mano.',
            'errors': notes}
