# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
import sys
import tempfile
import unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apartments as A
import apartment_sync as SYNC
import simon_agent as AGENT
import simon_api as API
import simon_memory as MEM
import web_search as WEB

os.environ['SIMON_LIVE_SEARCH'] = '0'
SOURCE = {'id': 'fincaraiz', 'name': 'Finca Raíz', 'priority': 20, 'hosts': ['www.fincaraiz.com.co', 'example.com', 'www.espaciourbano.com', 'www.metrocuadrado.com']}


def raw(**changes):
    base = {'property_type': 'apartamento', 'operation': 'arriendo', 'price': 2500000,
            'currency': 'COP', 'municipality': 'Envigado', 'neighborhood': 'Centro',
            'area_m2': 70, 'bedrooms': 2, 'bathrooms': 2,
            'original_url': 'https://example.com/apartamento/1'}
    base.update(changes)
    return base


class SimonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MEM.Store(os.path.join(self.tmp.name, 'simon.sqlite3'), key='clave-de-prueba-simon')
        self.index = A.Index(os.path.join(self.tmp.name, 'apt.sqlite3'))
        self.secret = 'frase-unica-de-comentario-que-no-debe-leerse-en-claro'
        os.environ['SIMON_ADMIN_TOKEN'] = 'token-admin-prueba'
        os.environ.pop('BRAVE_SEARCH_API_KEY', None)
        os.environ.pop('SERPER_API_KEY', None)
        os.environ.pop('GOOGLE_API_KEY', None)
        os.environ['SIMON_LIVE_SEARCH'] = '0'

    def tearDown(self):
        self.tmp.cleanup()

    def headers(self, extra=None):
        base = {'cookie': 'simon_sujeto=abc123abc123abc123abc123abc123ab'}
        if extra:
            base.update(extra)
        return base

    def test_encryption_roundtrip_hides_plaintext(self):
        blob = MEM.encrypt({'comment': self.secret}, 'clave-de-prueba-simon')
        self.assertNotIn(self.secret, blob)
        self.assertEqual(MEM.decrypt(blob, 'clave-de-prueba-simon')['comment'], self.secret)
        with self.assertRaises(ValueError):
            MEM.decrypt(blob, 'otra-clave')

    def test_consent_gates_storage_and_delete_removes_feedback(self):
        code, data, _ = API.dispatch('POST', '/api/simon-ia/mensaje', '', self.headers(),
                                     json.dumps({'message': 'hola simon'}).encode(), self.store, self.index)
        self.assertEqual(code, 200)
        self.assertFalse(data['consent'])
        self.assertEqual(self.store._rows('message'), [])
        API.dispatch('POST', '/api/simon/consentimiento', '', self.headers(),
                     json.dumps({'accepted': True}).encode(), self.store, self.index)
        self.assertTrue(self.store.allows('abc123abc123abc123abc123abc123ab'))
        code, _, _ = API.dispatch('POST', '/api/simon/feedback', '', self.headers(), json.dumps({
            'conversation_id': 'abc12345', 'declared_opened': False, 'resolution': 'no',
            'visibility': 'privada', 'comment': self.secret,
        }).encode(), self.store, self.index)
        self.assertEqual(code, 200)
        stored = self.store.feedback()[0]
        self.assertEqual(stored['comment'], self.secret)
        import sqlite3
        with sqlite3.connect(self.store.path) as conn:
            blob = conn.execute("SELECT doc FROM simon_records WHERE kind='feedback'").fetchone()[0]
        self.assertNotIn(self.secret, blob)
        API.dispatch('DELETE', '/api/simon/datos', '', self.headers(), b'', self.store, self.index)
        self.assertEqual(self.store.feedback(), [])
        self.assertFalse(self.store.allows('abc123abc123abc123abc123abc123ab'))

    def test_public_reviews_hide_private_and_admin_sees_all(self):
        subject = 'abc123abc123abc123abc123abc123ab'
        API.dispatch('POST', '/api/simon/consentimiento', '', self.headers(),
                     json.dumps({'accepted': True}).encode(), self.store, self.index)
        self.store.remember_conversation(subject, {'id': 'a1b2c3d4e5f60718', 'urls': [], 'opened': ['https://example.com/a']})
        self.store.remember_conversation(subject, {'id': 'b2c3d4e5f6071829', 'urls': [], 'opened': []})
        for conv, visibility, resolution, rating in (
            ('a1b2c3d4e5f60718', 'publica', 'si', 5),
            ('b2c3d4e5f6071829', 'privada', 'no', 2),
        ):
            code, _, _ = API.dispatch('POST', '/api/simon/feedback', '', self.headers(), json.dumps({
                'conversation_id': conv, 'declared_opened': visibility == 'publica',
                'resolution': resolution, 'visibility': visibility, 'rating': rating,
                'comment': 'nota ' + visibility,
            }).encode(), self.store, self.index)
            self.assertEqual(code, 200)
        code, public, _ = API.dispatch('GET', '/api/simon/resenas', '', self.headers(), b'', self.store, self.index)
        self.assertEqual(code, 200)
        self.assertEqual(len(public['reviews']), 1)
        self.assertEqual(public['reviews'][0]['comment'], 'nota publica')
        self.assertNotIn('links_opened', public['reviews'][0])
        code, denied, _ = API.dispatch('GET', '/api/simon/admin/resenas', '', self.headers(), b'', self.store, self.index)
        self.assertEqual(code, 403)
        code, admin, _ = API.dispatch(
            'GET', '/api/simon/admin/resenas', '/api/simon/admin/resenas?visibility=privada&solved=no&rating=2',
            self.headers({'x-simon-admin': 'token-admin-prueba'}), b'', self.store, self.index)
        self.assertEqual(code, 200)
        self.assertEqual(len(admin['reviews']), 1)
        self.assertEqual(admin['reviews'][0]['comment'], 'nota privada')
        self.assertEqual(admin['stats']['solved_rate'], 0.5)
        self.assertEqual(admin['stats']['average_rating'], 3.5)
        self.assertEqual(admin['stats']['link_share'], 0.5)

    def test_feedback_needs_consent_unless_accepted_in_the_form(self):
        body = json.dumps({'conversation_id': 'abc12345', 'declared_opened': True, 'resolution': 'parcialmente',
                           'visibility': 'publica', 'comment': 'sirvio a medias'}).encode()
        code, _, _ = API.dispatch('POST', '/api/simon/feedback', '', self.headers(), body, self.store, self.index)
        self.assertEqual(code, 409)
        body = json.dumps({'conversation_id': 'abc12345', 'declared_opened': False, 'resolution': 'parcialmente',
                           'visibility': 'privada', 'accept_storage': True}).encode()
        code, data, _ = API.dispatch('POST', '/api/simon/feedback', '', self.headers(), body, self.store, self.index)
        self.assertEqual(code, 200)
        self.assertTrue(data['saved'])
        self.assertEqual(self.store.feedback()[0]['resolution'], 'parcialmente')
        self.assertFalse(self.store.feedback()[0]['solved'])

    def test_pace_follows_the_person_and_rejects_pressure(self):
        slow = AGENT.plan_pace({'voz': 0.8, 'pausa_ms': 500, 'adaptar': True, 'por_partes': True}, typing_ms=320)
        self.assertLessEqual(slow['voice_rate'], 0.8)
        self.assertGreaterEqual(slow['delay_ms'], 1200)
        fast = AGENT.plan_pace({'voz': 0.9, 'adaptar': True}, typing_ms=40, speech_wpm=160)
        self.assertLessEqual(fast['voice_rate'], 0.9)
        self.assertNotIn('aprovecha', AGENT._clean('Aprovecha, última oportunidad').lower())
        self.assertIn('calma', AGENT._clean('Aprovecha, última oportunidad'))

    def test_apartment_tool_returns_original_link(self):
        row = A.normalize(raw(), SOURCE)
        self.index.ingest(SOURCE, [row], {'state': 'ok'})
        data = AGENT.answer('Busco un arriendo en Envigado hasta 3 millones con 2 habitaciones',
                            agent='simon-ia', subject='abc123abc123abc123abc123abc123ab',
                            store=self.store, index=self.index, live=False)
        self.assertEqual(data['tools'][0]['name'], 'search_apartments')
        self.assertEqual(data['cards'][0]['original_url'], 'https://example.com/apartamento/1')
        self.assertNotIn('aprovecha', data['message'].lower())
        sale = A.normalize_offer(raw(operation='venta', price=250000000, original_url='https://example.com/venta/9'), SOURCE)
        self.assertEqual(sale['operation'], 'venta')
        self.assertEqual(sale['price_sale'], 250000000)
        with self.assertRaises(ValueError):
            A.normalize(raw(operation='venta'), SOURCE)

    def test_link_click_is_tracked_only_for_known_urls(self):
        self.index.ingest(SOURCE, [A.normalize(raw(), SOURCE)], {'state': 'ok'})
        code, data, _ = API.dispatch('POST', '/api/simon/mensaje', '', self.headers(),
                                     json.dumps({'message': 'arriendo en Envigado'}).encode(), self.store, self.index)
        self.assertEqual(code, 200)
        url = data['cards'][0]['original_url']
        bad, _, _ = API.dispatch('POST', '/api/simon/enlace', '', self.headers(),
                                 json.dumps({'conversation_id': data['conversation_id'], 'url': 'https://evil.example/x'}).encode(),
                                 self.store, self.index)
        self.assertEqual(bad, 400)
        ok, payload, _ = API.dispatch('POST', '/api/simon/enlace', '', self.headers(),
                                      json.dumps({'conversation_id': data['conversation_id'], 'url': url}).encode(),
                                      self.store, self.index)
        self.assertEqual(ok, 200)
        self.assertIn(url, payload['opened'])

    def test_web_fallback_cites_the_page_without_a_key(self):
        html = '<a href="https://example.com/guia">Guía del valle</a><td class="result-snippet">Datos públicos</td>'
        def transport(url, data=None, headers=None):
            return html
        found = WEB.search('clima de envigado', transport=transport)
        self.assertTrue(found['ok'])
        self.assertEqual(found['provider'], 'duckduckgo')
        self.assertEqual(found['results'][0]['url'], 'https://example.com/guia')
        self.assertIn('clave', found['notice'])

    def test_portal_parsers_extract_fields_without_photos(self):
        item = {
            'props': {'pageProps': {'fetchResult': {'searchFast': {'data': [{
                'title': 'Apartamento en Arriendo en La abadia, Envigado', 'typeID': 2,
                'link': '/apartamento-en-arriendo-en-la-abadia-envigado/1', 'showAddress': False,
                'price': {'amount': 3500000, 'hidePrice': False},
                'locations': {'city': [{'name': 'Envigado'}], 'location_main': {'name': 'La abadia'}},
                'technicalSheet': [
                    {'field': 'property_type_name', 'value': 'Apartamento'},
                    {'field': 'bedrooms', 'value': '2'}, {'field': 'bathrooms', 'value': '2'},
                    {'field': 'm2Built', 'value': '70 m2'},
                ],
                'img': 'https://cdn.example/foto.jpg', 'description': 'texto largo que no debe copiarse',
            }]}}}}}
        html = '<script id="__NEXT_DATA__" type="application/json">%s</script>' % json.dumps(item)
        rows = SYNC.fincaraiz_rows(html, 'https://www.fincaraiz.com.co/arriendo/apartamentos/envigado/antioquia')
        self.assertEqual(len(rows), 1)
        self.assertNotIn('img', rows[0])
        self.assertNotIn('description', rows[0])
        norm = A.normalize_offer(rows[0], SOURCE)
        self.assertEqual((norm['municipality'], norm['price'], norm['bedrooms']), ('Envigado', 3500000, 2))
        metro = '{"contactPhone":"1","title":"Apartamento en Arriendo, Centro, Envigado","link":"/inmueble/arriendo-apartamento-envigado-centro-2-habitaciones-1-banos/1-M1","imageLink":"https://cdn.example/a.jpg","mtipoinmueble":{"nombre":"Apartamento"},"mtiponegocio":"arriendo","mvalorarriendo":1800000,"marea":60,"mnrocuartos":2,"mnrobanos":1,"mciudad":{"nombre":"Envigado"},"mnombrecomunbarrio":"Centro"}'
        parsed = SYNC.metro_results(metro, 'https://www.metrocuadrado.com/apartamentos/arriendo/envigado/')
        self.assertEqual(parsed[0]['price'], 1800000)
        self.assertNotIn('imageLink', parsed[0])
        ficha = '<h1>Apartamento en Arriendo</h1><p>EN ARRIENDO $2.200.000</p><p>Ciudad Envigado</p><p>Sector Centro</p><p>Area total 64 M2</p><p>Alcobas familiares 2</p><p>Baños familiares 1</p>'
        detail = SYNC.ficha_rows(SYNC.Document(ficha), 'https://www.espaciourbano.com/Ficha.asp?xId=1')
        self.assertEqual(detail[0]['municipality'], 'Envigado')
        self.assertEqual(A.normalize_offer(detail[0], SOURCE)['price'], 2200000)

    def test_knowledge_and_server_route(self):
        hits = self.store.recall('qué es RentoCity y la renta corta')
        self.assertTrue(hits)
        self.assertIn('RentoCity', hits[0]['text'])
        source = (A.ROOT / 'server.py').read_text(encoding='utf-8')
        self.assertIn("path.startswith('/api/simon')", source)
        self.assertIn('sync: false', (A.ROOT / 'render.yaml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
