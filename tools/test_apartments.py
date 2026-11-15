# SPDX-License-Identifier: AGPL-3.0-or-later
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apartments as A
import apartment_api as API
import apartment_sync as S

SOURCE = {'id': 'test', 'name': 'Agencia externa', 'priority': 10, 'hosts': ['example.com'], 'kind': 'feed', 'url': 'https://example.com/feed'}


def raw(**changes):
    return {'property_type': 'apartamento', 'operation': 'arriendo', 'price': '$2.500.000',
            'currency': 'COP', 'municipality': 'Itagui', 'neighborhood': 'Santa María',
            'area_m2': '65,5', 'bedrooms': 3, 'bathrooms': 2,
            'original_url': 'https://example.com/apartamento/123?utm_source=test', **changes}


class ApartmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, 'index.sqlite3')
        self.index = A.Index(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, values, source=SOURCE, date=None):
        row = A.normalize(values, source, date)
        self.index.ingest(source, [row], {'state': 'ok'})
        return row

    def test_all_ten_municipalities_and_normalization(self):
        for i, city in enumerate(A.MUNICIPALITIES):
            self.add(raw(municipality=A.folded(city), original_url=f'https://example.com/p/{i}'))
            result = self.index.search({'municipality': city})
            self.assertEqual(result['total'], 1)
            self.assertEqual(result['results'][0]['municipality'], city)
        row = self.index.search({'municipality': 'itagui'})['results'][0]
        self.assertEqual(row['price'], 2500000)
        self.assertEqual(row['area_m2'], 65.5)
        self.assertEqual(row['original_url'], 'https://example.com/p/3')

    def test_reject_unusable_wrong_region_sale_currency_link(self):
        for change in ({'currency': 'USD'}, {'municipality': 'Bogotá'}, {'price': 'consultar'},
                       {'operation': 'venta'}, {'property_type': 'casa'}, {'price': float('nan')},
                       {'original_url': 'javascript:alert(1)'}, {'original_url': 'https://evil.example/p/1'}):
            with self.assertRaises(ValueError):
                A.normalize(raw(**change), SOURCE)

    def test_filter_does_not_treat_unknown_attributes_as_match(self):
        self.add(raw())
        self.add(raw(original_url='https://example.com/p/2', bedrooms=None, price=1500000))
        self.assertEqual(self.index.search({'min_bedrooms': 2})['total'], 1)
        self.assertEqual(self.index.search({'max_price': 2000000})['total'], 1)
        self.assertEqual(self.index.search({'neighborhood': 'santa maria'})['total'], 2)
        self.assertEqual(self.index.search({'min_area_m2': 70})['total'], 0)
        for f in ({'max_price': 'error'}, {'municipality': 'Cali'}, {'limit': 'inf'}, {'parking': True}):
            with self.assertRaises(ValueError):
                self.index.search(f)

    def test_persists_upserts_and_expires(self):
        self.add(raw())
        self.add(raw(price=2800000))
        self.assertEqual(A.Index(self.db).search({})['total'], 1)
        self.assertEqual(self.index.search({})['results'][0]['price'], 2800000)
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=49)).isoformat()
        self.add(raw(), date=old)
        self.assertEqual(self.index.search({})['total'], 0)
        self.add(raw(active=False))
        self.assertEqual(self.index.search({})['total'], 0)

    def test_dedup_preserves_sources_and_different_units(self):
        values = raw(address='Carrera 50 # 10-20', unit='301')
        self.add(values)
        second = {**SOURCE, 'id': 'rentocity', 'name': 'Rentocity', 'priority': 0}
        self.add({**values, 'price': 2600000, 'original_url': 'https://example.com/p/456'}, second)
        result = self.index.search({})
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['results'][0]['publications']), 2)
        self.assertEqual(result['results'][0]['source'], 'rentocity')
        self.add({**values, 'unit': '302', 'original_url': 'https://example.com/p/789'})
        self.assertEqual(self.index.search({})['total'], 2)

    def test_similar_anonymous_units_are_not_merged(self):
        self.add(raw())
        self.add(raw(original_url='https://example.com/p/another'))
        self.assertEqual(self.index.search({})['total'], 2)

    def test_agents_return_real_index_links_and_parse_budget(self):
        self.add(raw())
        for agent in ('simon-ia', 'simon-io'):
            code, data = API.dispatch('POST', f'/api/{agent}/apartamentos', '', json.dumps({
                'message': 'Encuéntrame un apartamento en Itagüí hasta 2,5 millones con 3 habitaciones y 2 baños'
            }).encode(), self.index)
            self.assertEqual(code, 200)
            self.assertEqual(data['total'], 1)
            self.assertEqual(data['applied_filters']['max_price'], 2500000)
            self.assertEqual(data['results'][0]['original_url'], 'https://example.com/apartamento/123')
        self.assertEqual(A.parse_request('en Medellín máximo 800 mil')['max_price'], 800000)
        self.assertEqual(A.parse_request('en Bello hasta $1.500.000')['max_price'], 1500000)

    def test_agent_does_not_invent_empty_or_unsupported_matches(self):
        data = A.agent_search(self.index, 'simon-ia', 'en Caldas')
        self.assertEqual(data['total'], 0)
        self.assertIn('No encontré', data['message'])
        for text in ('en Bello y Sabaneta', 'apartamento con parqueadero', 'apartamento para comprar'):
            with self.assertRaises(ValueError):
                A.parse_request(text)
        self.assertEqual(API.dispatch('POST', '/api/simon-ia/apartamentos', '', b'[]', self.index)[0], 400)
        self.assertEqual(API.dispatch('POST', '/api/simon-ia/apartamentos', '', b'bad', self.index)[0], 400)
        self.assertEqual(API.dispatch('GET', '/api/apartamentos/no-existe', '', index=self.index)[0], 404)
        self.assertEqual(API.dispatch('GET', '/api/simon-ia/apartamentos', '', index=self.index)[0], 405)

    def test_jsonld_cannot_mix_a_house_or_sale_into_apartment(self):
        obj = {'@type': 'Apartment', 'name': 'Apartamento en arriendo en Itagüí',
               'url': '/apartamento/12', 'address': {'addressLocality': 'Itagüí'},
               'offers': {'price': '2500000', 'priceCurrency': 'COP'},
               'floorSize': {'value': 65, 'unitCode': 'MTK'}, 'numberOfBedrooms': 3}
        html = '<script type="application/ld+json">' + json.dumps({'@graph': [obj, {**obj, 'name': 'Casa en venta', 'url': '/casa/12'}]}) + '</script>'
        rows = list(S.structured_rows(S.Document(html), 'https://example.com/'))
        self.assertEqual(len(rows), 1)
        self.assertEqual(A.normalize(rows[0], SOURCE)['area_m2'], 65)
        self.assertIsNone(A.normalize(rows[0], SOURCE)['bathrooms'])

    def test_metro_visible_detail_extracts_public_facts(self):
        from pathlib import Path
        html = (A.ROOT / 'tests/fixtures/apartments/metrocuadrado-visible.html').read_text()
        url = 'https://www.metrocuadrado.com/inmueble/arriendo-apartamento-itagui-viviendas-del-sur-3-habitaciones-2-banos-1-garajes/23074-M6771804'
        values = S.metrocuadrado_detail(S.Document(html), url)
        self.assertEqual(len(values), 1)
        source = next(s for s in A.sources() if s['id'] == 'metrocuadrado')
        row = A.normalize(values[0], source)
        self.assertEqual((row['municipality'], row['price'], row['area_m2'], row['bedrooms'], row['bathrooms']),
                         ('Itagüí', 3000000, 75, 3, 2))
        self.assertEqual(S.metrocuadrado_detail(S.Document(html), 'https://www.metrocuadrado.com/'), [])

    def test_feed_pagination_failure_does_not_remove_previous_data(self):
        self.add(raw())
        class Fetch:
            hosts = ['example.com']
            def request(self, url, token=None):
                if 'page=2' in url:
                    raise TimeoutError()
                return json.dumps({'listings': [raw(original_url='https://example.com/p/new')], 'next': '?page=2'}), url
        report = S.sync_source(SOURCE, self.index, Fetch(), 3)
        self.assertEqual(report['state'], 'partial')
        self.assertEqual(report['accepted'], 1)
        self.assertEqual(self.index.search({})['total'], 2)

    def test_missing_feed_is_honest_configuration_status(self):
        report = S.sync_source({**SOURCE, 'url': ''}, self.index)
        self.assertEqual(report['state'], 'configuration_required')
        self.assertEqual(self.index.search({})['total'], 0)

    def test_server_http_get_head_and_both_agent_posts(self):
        import ast
        import asyncio
        import types
        import urllib.parse
        tree = ast.parse((A.ROOT / 'server.py').read_text())
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'handle')
        module = ast.Module(body=[function], type_ignores=[])
        namespace = {'asyncio': asyncio, 'urllib': __import__('urllib'), 'json': json,
                     'APARTMENT_API': types.SimpleNamespace(AGENT_PATHS=API.AGENT_PATHS,
                         dispatch=lambda method, path, target, body: API.dispatch(method, path, target, body, self.index))}
        exec(compile(module, 'server.py', 'exec'), namespace)
        self.add(raw())
        class Writer:
            data = b''
            def write(self, data): self.data += data
            async def drain(self): pass
            def close(self): pass
        async def request(method, path, payload=None):
            reader = asyncio.StreamReader()
            body = json.dumps(payload).encode() if payload else b''
            reader.feed_data((f'{method} {path} HTTP/1.1\r\nContent-Length: {len(body)}\r\n\r\n').encode() + body)
            reader.feed_eof()
            writer = Writer()
            await namespace['handle'](reader, writer)
            return writer.data
        for agent in ('simon-ia', 'simon-io'):
            response = asyncio.run(request('POST', f'/api/{agent}/apartamentos', {'message': 'en Itagüí hasta 3 millones'}))
            header, body = response.split(b'\r\n\r\n', 1)
            self.assertIn(b'200 OK', header)
            self.assertEqual(json.loads(body)['total'], 1)
        response = asyncio.run(request('GET', '/api/apartamentos?municipality=Itagui'))
        self.assertEqual(json.loads(response.split(b'\r\n\r\n')[1])['total'], 1)
        response = asyncio.run(request('HEAD', '/api/apartamentos'))
        self.assertTrue(response.endswith(b'\r\n\r\n'))

    def test_ssrf_private_address_and_redirect_domain_are_rejected(self):
        f = S.Fetcher(['example.com'], delay=0)
        with patch.object(S.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaises(ValueError):
                f.validate('https://example.com/a')
        with self.assertRaises(ValueError):
            f.validate('https://unconfigured.example/a')
        with self.assertRaises(ValueError):
            f.validate('http://example.com/a')


if __name__ == '__main__':
    unittest.main()
