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
        import asyncio
        import server
        self.add(raw())
        original = server.APARTMENT_API.dispatch
        def fake(method, path, target, body=b'', index=None):
            return original(method, path, target, body, self.index)
        server.APARTMENT_API.dispatch = fake
        class Writer:
            data = b''
            def write(self, data): self.data += data
            async def drain(self): pass
            def close(self): pass
            def get_extra_info(self, name): return None
        async def request(method, path, payload=None):
            reader = asyncio.StreamReader()
            body = json.dumps(payload).encode() if payload else b''
            reader.feed_data((f'{method} {path} HTTP/1.1\r\nContent-Length: {len(body)}\r\n\r\n').encode() + body)
            reader.feed_eof()
            writer = Writer()
            await server.handle(reader, writer)
            return writer.data
        try:
            for agent in ('simon-ia', 'simon-io'):
                response = asyncio.run(request('POST', f'/api/{agent}/apartamentos', {'message': 'en Itagüí hasta 3 millones'}))
                header, body = response.split(b'\r\n\r\n', 1)
                self.assertIn(b'200 OK', header)
                self.assertIn(b'X-Content-Type-Options: nosniff', header)
                self.assertEqual(json.loads(body)['total'], 1)
            response = asyncio.run(request('GET', '/api/apartamentos?municipality=Itagui'))
            self.assertEqual(json.loads(response.split(b'\r\n\r\n')[1])['total'], 1)
            response = asyncio.run(request('HEAD', '/api/apartamentos'))
            self.assertTrue(response.endswith(b'\r\n\r\n'))
        finally:
            server.APARTMENT_API.dispatch = original

    def test_client_ip_follows_the_socket_until_render_and_cloudflare(self):
        import server
        class Writer:
            def __init__(self, host):
                self.host = host
            def get_extra_info(self, name):
                return (self.host, 9) if name == 'peername' else None
        forged = {'x-forwarded-for': '1.1.1.1', 'cf-connecting-ip': '8.8.8.8'}
        with patch.dict(os.environ, {'RENDER': ''}):
            self.assertEqual(server.client_ip(forged, Writer('203.0.113.9')), '203.0.113.9')
        chain = {
            'x-forwarded-for': '9.9.9.9, 8.8.8.8, 104.16.1.1, 198.51.100.8',
            'cf-connecting-ip': '8.8.8.8',
        }
        with patch.dict(os.environ, {'RENDER': 'true'}):
            self.assertEqual(server.client_ip(chain, Writer('10.0.0.4')), '8.8.8.8')
            planted = {
                'x-forwarded-for': '104.16.1.1, 8.8.8.8, 203.0.113.4, 198.51.100.7',
                'cf-connecting-ip': '1.1.1.1',
            }
            self.assertEqual(server.client_ip(planted, Writer('10.0.0.4')), '198.51.100.7')

    def test_listing_routes_rate_limit_ignores_a_forged_forwarded_for(self):
        import asyncio
        import server
        import seguridad as seg
        calls = {'n': 0}
        def fake(method, path, target, body=b'', index=None):
            calls['n'] += 1
            return 200, {'total': 0, 'results': []}
        original = server.APARTMENT_API.dispatch
        server.APARTMENT_API.dispatch = fake
        seg.CUBO.clear()

        class Writer:
            def __init__(self, host):
                self.data = b''
                self.host = host
            def write(self, data):
                self.data += data
            async def drain(self):
                pass
            def close(self):
                pass
            def get_extra_info(self, name):
                return (self.host, 9) if name == 'peername' else None

        async def once(i, peer='203.0.113.50', origin=''):
            reader = asyncio.StreamReader()
            # El primer X-Forwarded-For cambia en cada intento. Antes eso abría un cubo nuevo.
            header = f'X-Forwarded-For: 198.51.100.{i % 200}\r\n'
            if origin:
                header += f'Origin: {origin}\r\n'
            reader.feed_data((f'GET /api/apartamentos?offset={i} HTTP/1.1\r\n{header}\r\n').encode())
            reader.feed_eof()
            writer = Writer(peer)
            await server.handle(reader, writer)
            return writer.data

        async def burst():
            seen = []
            for i in range(seg.LISTADOS_TOPE + 1):
                seen.append(await once(i))
            other = await once(0, peer='198.51.100.20')
            blocked = await once(0, origin='https://rentocity.com.co')
            return seen, other, blocked

        try:
            with patch.dict(os.environ, {'RENDER': ''}):
                seen, other, blocked = asyncio.run(burst())
        finally:
            server.APARTMENT_API.dispatch = original
            seg.CUBO.clear()
        self.assertEqual(calls['n'], seg.LISTADOS_TOPE + 1)
        for response in seen[:-1]:
            self.assertIn(b'200 OK', response.split(b'\r\n', 1)[0])
        self.assertIn(b'429', blocked.split(b'\r\n', 1)[0])
        self.assertIn(b'Demasiados intentos', blocked)
        self.assertIn(b'Access-Control-Allow-Origin: https://rentocity.com.co', blocked)
        self.assertIn(b'200 OK', other.split(b'\r\n', 1)[0])
        self.assertIn(b'429', seen[-1].split(b'\r\n', 1)[0])

    def test_ssrf_private_address_and_redirect_domain_are_rejected(self):
        f = S.Fetcher(['example.com'], delay=0)
        with patch.object(S.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaises(ValueError):
                f.validate('https://example.com/a')
        with self.assertRaises(ValueError):
            f.validate('https://unconfigured.example/a')
        with self.assertRaises(ValueError):
            f.validate('http://example.com/a')

    def test_public_cards_need_a_real_price_and_one_city(self):
        panda = (
            '<a href="https://pandainmobiliaria.inmo.co/apartamento-alquiler-loma-los-mesa-envigado/9639365" class="t8-title">'
            'APARTAMENTO PARA ARRIENDO EN ENVIGADO- LOMA LOS MESA</a>'
            '<span class="dt1">3</span> <span class="dt2 t8-title"> Habitaciones</span>'
            '<span class="dt1">4</span> <span class="dt2 t8-title"> Baños</span>'
            '<span class="dt1">291</span> <span class="dt2 t8-title"> Área m<sup>2</sup></span>'
            '<p class=" text-truncate">$20.000.000 <small>COP</small></p>'
        )
        rows = S.panda_rows(panda, 'https://pandainmobiliaria.inmo.co/s/apartamento/alquileres')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['municipality'], 'Envigado')
        self.assertEqual(rows[0]['operation'], 'arriendo')
        self.assertEqual(A.number(rows[0]['price']), 20000000)
        self.assertEqual(S.panda_rows(panda.replace('$20.000.000', 'consultar'), 'https://pandainmobiliaria.inmo.co/s/apartamento/alquileres'), [])
        sur = (
            '<div class="property_item"><a href="/inmueble/4684-apartamento-arriendo-sabaneta-sabaneta-3-alcobas-2-banos">Apartamento - 4684</a>'
            '<span>120 m<sup>2</sup></span><span>3 Alcobas</span><span>2.0 Baños</span>'
            '<h4>Sabaneta, Sabaneta</h4><p class="pull-md-left"> $4,300,000 </p></div>'
        )
        got = S.sur_rows(sur, 'https://www.survivienda.com/Paginas/')
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]['municipality'], 'Sabaneta')
        self.assertEqual(got[0]['bedrooms'], '3')
        pages = S.following_pages('https://www.fincaraiz.com.co/venta/apartamentos/barbosa/antioquia', 3)
        self.assertEqual(pages, [
            'https://www.fincaraiz.com.co/venta/apartamentos/barbosa/antioquia/pagina2',
            'https://www.fincaraiz.com.co/venta/apartamentos/barbosa/antioquia/pagina3',
        ])
        self.assertEqual(S.following_pages(pages[0], 3), [])
        metro = S.following_pages('https://www.metrocuadrado.com/apartamentos/venta/caldas/', 3)
        self.assertTrue(metro[0].endswith('/apartamentos/venta/caldas/2'))
        ids = {s['id']: s for s in A.sources()}
        self.assertEqual(ids['rentocity']['kind'], 'feed')
        self.assertEqual(ids['arrendamientos-valle-aburra']['kind'], 'feed')
        self.assertTrue(any('venta/apartamentos/la-estrella' in url for url in ids['fincaraiz']['seeds']))
        self.assertTrue(any('venta/barbosa' in url for url in ids['metrocuadrado']['seeds']))
        self.assertEqual(API.cors_headers('https://rentocity.com.co')[0], 'Access-Control-Allow-Origin: https://rentocity.com.co')
        self.assertEqual(API.cors_headers('https://www.rentocity.com.co')[0].split(': ')[1], 'https://www.rentocity.com.co')
        self.assertEqual(API.cors_headers('https://otro.example'), [])
        self.assertNotIn('Allow-Credentials', ' '.join(API.cors_headers('https://rentocity.com.co')))


if __name__ == '__main__':
    unittest.main()
