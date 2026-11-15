# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fechas, importancia, cifrado y que el texto público no lleve datos privados."""
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reloj
import respaldos

FRASE = 'frase-de-prueba-larga'
SEMILLA = 'ab' * 32
CORREO = 'ana.secreta@example.com'
JUGADOR = 'JugadorSecretoZz'
CLAVE_SIMON = 'clave-simon-de-prueba-zzzz'
URL = 'postgresql://life:clave-super-secreta@db.interno:5432/life'


class RelojPublicoTests(unittest.TestCase):
    def test_fecha_de_bogota_y_fecha_de_juego(self):
        now = 1_700_000_000
        epoch = 1_700_000_000
        info = respaldos.etiquetar(now, epoch, '218e52a8f7a2', 'Incluye: prueba.', False)
        real = datetime.fromtimestamp(now, ZoneInfo('America/Bogota'))
        self.assertEqual(info['fecha_real'], real.strftime('%Y-%m-%d %H:%M'))
        self.assertEqual(info['zona'], 'America/Bogota')
        self.assertTrue(info['etiqueta'].startswith(real.strftime('respaldo-%Y%m%d-%H%M-')))
        self.assertEqual(info['fecha_juego'], '1 de enero de 1777')
        self.assertEqual(info['anio_juego'], 1777)
        self.assertEqual(info['hora_juego'], '00:00')
        siguiente = respaldos.etiquetar(now + 20 * 60, epoch, '218e52a8f7a2', 'x', False)
        self.assertEqual(siguiente['fecha_juego'], '2 de enero de 1777')
        self.assertEqual(siguiente['anio_juego'], 1777)

    def test_la_ancla_sigue_al_servidor(self):
        logico = {'tablas': {'stores': {'filas': [
            {'name': 'economy', 'doc': {'relojEpoch': 1_700_000_000}},
        ]}}}
        self.assertEqual(respaldos.ancla(logico, env=''), 1_700_000_000)
        self.assertEqual(respaldos.ancla(logico, env='1800000000'), 1800000000)
        self.assertEqual(respaldos.ancla({'tablas': {}}, env=''), reloj.DEPLOY_EPOCH)


class ImportanciaTests(unittest.TestCase):
    def test_un_pull_request_fusionado_cuenta_y_se_puede_saltar(self):
        fusion = [{
            'id': 'abc',
            'message': 'Merge pull request #30 from Saimonmde/cursor/login\n\nEl acceso ya no entra como invitado.',
        }]
        squash = [{'id': 'def', 'message': 'Deja el servidor listo para otra red. (#26)'}]
        self.assertTrue(respaldos.es_importante(fusion, [], manual=False))
        self.assertTrue(respaldos.es_importante(squash, [], manual=False))
        self.assertFalse(respaldos.es_importante(
            [{'message': 'Ajusta un comentario del mapa.'}], [], manual=False,
        ))
        self.assertTrue(respaldos.es_importante(
            [{'message': '[respaldo] anoto el mapa a mano'}], [], manual=False,
        ))
        self.assertFalse(respaldos.es_importante(
            [{'message': 'Merge pull request #9 from a/b\n\n[sin-respaldo] sólo un typo'}],
            [],
            manual=False,
        ))
        self.assertFalse(respaldos.es_importante(
            fusion,
            [{'title': 'El acceso', 'body': '', 'labels': ['sin-respaldo']}],
            manual=False,
        ))
        self.assertTrue(respaldos.es_importante(
            [{'message': '[sin-respaldo] no'}], [], manual=True,
        ))

    def test_el_commit_de_la_fusion_cuenta_aunque_la_lista_traiga_solo_la_rama(self):
        evento = {
            'commits': [{
                'id': '0d4f779',
                'message': 'Archiva cada fusión importante con la fecha de Bogotá.',
            }],
            'head_commit': {
                'id': '7385ee8',
                'message': 'Merge pull request #34 from Saimonmde/cursor/respaldos-saimon-c375\n\nArchiva cada fusión importante con fecha real, fecha de juego y copia cifrada',
            },
        }
        commits = respaldos.commits_del_evento(evento, [])
        self.assertTrue(respaldos.es_importante(commits, [], manual=False))
        self.assertEqual(respaldos.numeros_pr(commits), ['34'])
        self.assertTrue(respaldos.es_importante(
            [{'message': 'Merge pull request #34 from a/b\n\nArchiva los respaldos'}],
            [{'title': 'Archiva los respaldos', 'body': 'Escribe [sin-respaldo] en el título para saltarlo.', 'labels': []}],
            False,
        ))

    def test_el_resumen_sale_en_espanol_y_sin_secretos(self):
        prs = [{
            'title': 'Abre la casa colonial',
            'body': 'Cada jugador guarda sus muebles.\n\nCorreo ' + CORREO + '\n' + URL + '\n' + SEMILLA,
            'labels': [],
        }, {
            'title': 'Suma el libro madre',
            'body': 'El libro anota cada acuñación.',
            'labels': [],
        }]
        texto = respaldos.resumen(prs)
        self.assertTrue(texto.startswith('Entran 2 cambios. Incluye:'))
        self.assertIn('Abre la casa colonial', texto)
        self.assertIn('Suma el libro madre', texto)
        self.assertNotIn(CORREO, texto)
        self.assertNotIn('clave-super-secreta', texto)
        self.assertNotIn(SEMILLA, texto)
        self.assertNotIn('postgresql://', texto)


class CifradoYPrivacidadTests(unittest.TestCase):
    def setUp(self):
        self._frase = os.environ.get('BACKUP_PASSPHRASE')
        self._simon = os.environ.get('SIMON_DATA_KEY')
        self._db = os.environ.get('DATABASE_URL')
        os.environ.pop('DATABASE_URL', None)
        os.environ['BACKUP_PASSPHRASE'] = FRASE
        os.environ['SIMON_DATA_KEY'] = ''
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        self._volver('BACKUP_PASSPHRASE', self._frase)
        self._volver('SIMON_DATA_KEY', self._simon)
        self._volver('DATABASE_URL', self._db)

    def _volver(self, clave, valor):
        if valor is None:
            os.environ.pop(clave, None)
        else:
            os.environ[clave] = valor

    def _estado(self):
        economia = {
            'relojEpoch': 1_700_000_000,
            'wallets': {JUGADOR: 5, 'tesoro_genesis': 1},
            'blocks': [{'height': 0, 'txs': [{'note': 'reserva'}]}],
        }
        with open(os.path.join(self.dir, 'economy.json'), 'w', encoding='utf-8') as handle:
            json.dump(economia, handle)
        with open(os.path.join(self.dir, 'players.json'), 'w', encoding='utf-8') as handle:
            json.dump({'players': {JUGADOR: {'playtime': 10}}}, handle)
        with open(os.path.join(self.dir, 'accounts.json'), 'w', encoding='utf-8') as handle:
            json.dump({'users': [{'email': CORREO, 'name': JUGADOR}], 'sessions': {}}, handle)
        with open(os.path.join(self.dir, 'nft-key.json'), 'w', encoding='utf-8') as handle:
            json.dump({'seed': SEMILLA}, handle)
        with open(os.path.join(self.dir, 'simon-data.key'), 'w', encoding='utf-8') as handle:
            handle.write(CLAVE_SIMON)
        conn = sqlite3.connect(os.path.join(self.dir, 'simon.sqlite3'))
        conn.execute(
            'CREATE TABLE simon_records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject TEXT, doc TEXT NOT NULL)'
        )
        conn.execute(
            'INSERT INTO simon_records VALUES (?, ?, ?, ?)',
            ('fb-1', 'feedback', JUGADOR, 'nota privada ' + CORREO),
        )
        conn.execute(
            'INSERT INTO simon_records VALUES (?, ?, ?, ?)',
            ('c-1', 'conversation', JUGADOR, 'una nota de Simón'),
        )
        conn.commit()
        conn.close()

    def test_cifrado_roundtrip_y_frase_mala(self):
        original = os.urandom(100_000)
        cerrado = respaldos.cifrar(original, FRASE)
        self.assertEqual(respaldos.descifrar(cerrado, FRASE), original)
        with self.assertRaises(ValueError) as ctx:
            respaldos.descifrar(cerrado, 'otra-frase-distinta')
        self.assertNotIn(original[:20], str(ctx.exception).encode())

    def test_la_copia_publica_no_lleva_datos_privados_y_la_restauracion_si(self):
        self._estado()
        logico = respaldos.exportar_archivos(self.dir)
        logico['pg_dump'] = b'PGDMP-falso'
        info = respaldos.etiquetar(1_700_000_000, 1_700_000_000, '218e52a', 'Incluye: prueba.', True)
        manifiesto, blob, _archivo = respaldos._preparar_cifrado(info, logico)
        publico = json.dumps(manifiesto, ensure_ascii=False)
        for secreto in (SEMILLA, CORREO, JUGADOR, CLAVE_SIMON, 'clave-super-secreta', 'PGDMP'):
            self.assertNotIn(secreto, publico)
        self.assertEqual(manifiesto['cuentas']['jugadores'], 1)
        self.assertEqual(manifiesto['cuentas']['opiniones'], 1)
        self.assertEqual(manifiesto['cuentas']['notas'], 1)
        self.assertEqual(manifiesto['cuentas']['bloques_monedas'], 1)
        self.assertEqual(manifiesto['semilla_certificados'], 'incluida')
        self.assertEqual(manifiesto['clave_simon'], 'incluida')
        self.assertTrue(any('navegador' in linea for linea in manifiesto['ausente']))
        self.assertTrue(any('mascotas' in linea for linea in manifiesto['ausente']))
        notas = respaldos.notas_release(dict(info, **{
            'datos': manifiesto['datos'],
            'motivo_datos': manifiesto['motivo_datos'],
            'archivo': manifiesto['archivo'],
            'almacen': manifiesto['almacen'],
            'cuentas': manifiesto['cuentas'],
            'semilla_certificados': manifiesto['semilla_certificados'],
            'clave_simon': manifiesto['clave_simon'],
        }))
        for secreto in (SEMILLA, CORREO, JUGADOR, CLAVE_SIMON):
            self.assertNotIn(secreto, notas)
        self.assertIn('1777', notas)
        self.assertIn('America/Bogota', notas)
        claro = respaldos.descifrar(blob, FRASE)
        abierto, dump, _interno = respaldos.abrir_paquete(claro)
        self.assertEqual(dump, b'PGDMP-falso')
        destino = os.path.join(self.dir, 'restaurado')
        respaldos.restaurar_directorio(abierto, destino)
        with open(os.path.join(destino, 'accounts.json'), encoding='utf-8') as handle:
            self.assertIn(CORREO, handle.read())
        with open(os.path.join(destino, 'economy.json'), encoding='utf-8') as handle:
            self.assertIn(JUGADOR, handle.read())
        with open(os.path.join(destino, 'nft-key.json'), encoding='utf-8') as handle:
            self.assertEqual(json.load(handle)['seed'], SEMILLA)
        with open(os.path.join(destino, 'simon-data.key'), encoding='utf-8') as handle:
            self.assertEqual(handle.read(), CLAVE_SIMON)
        self.assertEqual(os.stat(os.path.join(destino, 'simon-data.key')).st_mode & 0o777, 0o600)
        conn = sqlite3.connect(os.path.join(destino, 'simon.sqlite3'))
        fila = conn.execute("SELECT doc FROM simon_records WHERE kind='feedback'").fetchone()
        conn.close()
        self.assertIn(CORREO, fila[0])

    def test_sin_frase_no_hay_archivo_publico_con_datos(self):
        self._estado()
        os.environ.pop('BACKUP_PASSPHRASE', None)
        logico = respaldos.exportar_archivos(self.dir)
        info = respaldos.etiquetar(1_700_000_000, 1_700_000_000, '218e52a', 'Incluye: prueba.', False)
        manifiesto, blob, _archivo = respaldos._preparar_cifrado(info, logico)
        self.assertIsNone(blob)
        self.assertEqual(manifiesto['datos'], 'omitidos')
        publico = json.dumps(manifiesto)
        self.assertNotIn(SEMILLA, publico)
        self.assertNotIn(CORREO, publico)
        self.assertIn('BACKUP_PASSPHRASE', manifiesto['motivo_datos'])

    def test_un_miembro_malicioso_del_tar_no_se_escribe_fuera(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:gz') as tar:
            fuera = b'secreto-fuera'
            info = tarfile.TarInfo('../secreto-fuera.txt')
            info.size = len(fuera)
            tar.addfile(info, io.BytesIO(fuera))
            adentro = json.dumps({'tablas': {}, 'claves': {}}).encode()
            info = tarfile.TarInfo('logico.json')
            info.size = len(adentro)
            tar.addfile(info, io.BytesIO(adentro))
        ruta = os.path.join(self.dir, 'malo.lifebak')
        with open(ruta, 'wb') as handle:
            handle.write(respaldos.cifrar(buf.getvalue(), FRASE))
        destino = os.path.join(self.dir, 'copia')
        respaldos.restaurar(ruta, destino, FRASE, repo=self.dir)
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.dir), 'secreto-fuera.txt')))
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'secreto-fuera.txt')))

    def test_no_pisa_la_base_ni_el_state_de_produccion(self):
        os.environ['DATABASE_URL'] = 'postgresql://life:clave-una-xyz@db.example.com:5432/ciudad'
        with self.assertRaises(RuntimeError) as misma:
            respaldos.comprobar_destino('postgres://life:clave-otra-xyz@db.example.com/ciudad')
        self.assertNotIn('clave-una-xyz', str(misma.exception))
        self.assertNotIn('clave-otra-xyz', str(misma.exception))
        respaldos.comprobar_destino('postgresql://life:clave-otra-xyz@db.example.com:5432/ciudad_copia')
        with self.assertRaises(RuntimeError):
            respaldos.comprobar_destino(destino=os.path.join(respaldos.ROOT, 'state'))
        respaldos.comprobar_destino(destino=os.path.join(respaldos.ROOT, 'state'), produccion=True)

    def test_ocultar_tokens(self):
        sucio = 'https://x-access-token:ghs_abc123def@github.com/Saimonmde/LIFE ' + URL
        limpio = respaldos.ocultar(sucio)
        self.assertNotIn('ghs_', limpio)
        self.assertNotIn('clave-super-secreta', limpio)
        self.assertNotIn('postgresql://', limpio)


class ListarYCodigoTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        subprocess.check_call(['git', 'init', '-b', 'main'], cwd=self.dir, stdout=subprocess.DEVNULL)
        with open(os.path.join(self.dir, 'hola.txt'), 'w', encoding='utf-8') as handle:
            handle.write('hola\n')
        subprocess.check_call(['git', 'add', 'hola.txt'], cwd=self.dir)
        subprocess.check_call(
            ['git', '-c', 'user.email=t@example.com', '-c', 'user.name=t', 'commit', '-m', 'inicio'],
            cwd=self.dir, stdout=subprocess.DEVNULL,
        )
        self.sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.dir, text=True).strip()

    def tearDown(self):
        copia = os.path.join(self.dir, 'copia')
        if os.path.isdir(copia):
            subprocess.call(['git', 'worktree', 'remove', '--force', copia], cwd=self.dir)
        shutil.rmtree(self.dir, ignore_errors=True)

    def _etiquetar(self, nombre, info):
        respaldos._git(
            self.dir, 'tag', '-a', nombre, self.sha, '-F', '-',
            entrada=respaldos.mensaje_etiqueta(info).encode('utf-8'),
        )

    def test_lista_por_fecha_real_y_anio_de_juego(self):
        self._etiquetar('respaldo-20200102-0304-aaaaaaa', {
            'fecha_real': '2020-01-02 03:04',
            'fecha_juego': '1 de enero de 1777',
            'anio_juego': 1777,
            'hora_juego': '00:00',
            'commit': self.sha,
            'linea_base': True,
            'resumen': 'Línea base vieja.',
        })
        self._etiquetar('respaldo-20241115-1200-bbbbbbb', {
            'fecha_real': '2024-11-15 12:00',
            'fecha_juego': '3 de marzo de 1842',
            'anio_juego': 1842,
            'hora_juego': '08:15',
            'commit': self.sha,
            'linea_base': False,
            'resumen': 'Incluye: el mapa.',
        })
        filas = respaldos.listar(self.dir)
        self.assertEqual([fila['etiqueta'] for fila in filas], [
            'respaldo-20241115-1200-bbbbbbb',
            'respaldo-20200102-0304-aaaaaaa',
        ])
        self.assertEqual(filas[0]['anio_juego'], 1842)
        self.assertEqual(filas[1]['anio_juego'], 1777)
        self.assertTrue(filas[1]['linea_base'])
        texto = respaldos.formato_lista(filas)
        self.assertIn('año 1842', texto)
        self.assertIn('año 1777', texto)
        self.assertLess(texto.index('2024-11-15'), texto.index('2020-01-02'))

    def test_el_codigo_queda_en_otra_carpeta(self):
        nombre = 'respaldo-20241115-1200-bbbbbbb'
        self._etiquetar(nombre, {
            'fecha_real': '2024-11-15 12:00',
            'fecha_juego': '3 de marzo de 1842',
            'anio_juego': 1842,
            'hora_juego': '08:15',
            'commit': self.sha,
            'linea_base': False,
            'resumen': 'Incluye: el mapa.',
        })
        carpeta = os.path.join(self.dir, 'copia')
        respaldos.preparar_codigo(nombre, carpeta, self.dir)
        self.assertTrue(os.path.isfile(os.path.join(carpeta, 'hola.txt')))
        rama = subprocess.check_output(['git', 'branch', '--show-current'], cwd=self.dir, text=True).strip()
        self.assertEqual(rama, 'main')


if __name__ == '__main__':
    unittest.main()
