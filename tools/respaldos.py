# SPDX-License-Identifier: AGPL-3.0-or-later
"""Respaldos de Saimon City: etiqueta de código, fecha real y fecha de juego.

El repositorio es público. La copia de la base sale cifrada y el texto
público (etiqueta, release, manifiesto) sólo lleva fechas y conteos.
"""
import argparse
import base64
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, unquote, urlsplit
from zoneinfo import ZoneInfo

import reloj

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, 'state')
BOGOTA = ZoneInfo('America/Bogota')
REPO_DEFECTO = 'Saimonmde/LIFE'
MAGIC = b'LIFEBAK1'
SALT = b'saimon-city-respaldo-v1'
PERMITIDOS = {'logico.json', 'juego.dump', 'manifiesto.json'}
STORE_FILES = {
    'economy.json': 'economy',
    'vault.json': 'vault',
    'nft.json': 'nft',
    'players.json': 'players',
    'nft-key.json': 'nft_seed',
    'accounts.json': 'accounts',
    'libro-madre.json': 'libro_madre',
}
ESQUEMA = {
    'stores': {
        'columnas': [
            {'name': 'name', 'tipo': 'text'},
            {'name': 'doc', 'tipo': 'jsonb'},
            {'name': 'updated_at', 'tipo': 'timestamptz'},
        ],
        'primaria': ['name'],
    },
    'libro_ids': {
        'columnas': [{'name': 'id', 'tipo': 'text'}],
        'primaria': ['id'],
    },
    'simon_records': {
        'columnas': [
            {'name': 'id', 'tipo': 'text'},
            {'name': 'kind', 'tipo': 'text'},
            {'name': 'subject', 'tipo': 'text'},
            {'name': 'doc', 'tipo': 'text'},
        ],
        'primaria': ['id'],
    },
    'apartment_listings': {
        'columnas': [
            {'name': 'id', 'tipo': 'text'},
            {'name': 'doc', 'tipo': 'text'},
        ],
        'primaria': ['id'],
    },
    'apartment_source_status': {
        'columnas': [
            {'name': 'id', 'tipo': 'text'},
            {'name': 'doc', 'tipo': 'text'},
        ],
        'primaria': ['id'],
    },
}
TIPOS = {
    'text': 'text',
    'character varying': 'text',
    'jsonb': 'jsonb',
    'json': 'jsonb',
    'integer': 'integer',
    'bigint': 'bigint',
    'smallint': 'smallint',
    'boolean': 'boolean',
    'timestamp with time zone': 'timestamptz',
    'timestamp without time zone': 'timestamp',
    'numeric': 'numeric',
    'bytea': 'bytea',
    'double precision': 'double precision',
    'real': 'real',
    'date': 'date',
}
AUSENTE = [
    'Casas y muebles: cada jugador los guarda en su navegador (lifeinc.casa.v1), no en el servidor.',
    'Mascotas: el juego todavía no guarda mascotas de los jugadores.',
]
_IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_PR_MERGE = re.compile(r'Merge pull request #(\d+)', re.I)
_PR_SQUASH = re.compile(r'\(#(\d+)\)\s*$', re.M)
_SKIP = '[sin-respaldo]'
_FORCE = '[respaldo]'


def ocultar(texto):
    """Quita contraseñas, tokens y correos de un texto que puede imprimirse."""
    texto = str(texto or '')
    texto = re.sub(r'x-access-token:[^@\s]+', 'x-access-token:[oculto]', texto)
    texto = re.sub(r'github_pat_[A-Za-z0-9_]+', '[token]', texto)
    texto = re.sub(r'gh[pousr]_[A-Za-z0-9_]+', '[token]', texto)
    texto = re.sub(r'https://[^/\s:]+:[^/\s@]+@', 'https://[oculto]@', texto)
    texto = re.sub(r'(?i)postgres(?:ql)?://\S+', '[url]', texto)
    texto = re.sub(r'(?i)\bbearer\s+\S+', 'bearer [oculto]', texto)
    texto = re.sub(r'(?i)\b[\w.+-]+@[\w.-]+\.\w+\b', '[correo]', texto)
    texto = re.sub(
        r'(?i)(password|passwd|secret|token|api[_-]?key|frase|passphrase)\s*[:=]\s*\S+',
        r'\1=[oculto]',
        texto,
    )
    texto = re.sub(r'\b[0-9a-fA-F]{32,}\b', '[hex]', texto)
    return texto


def _si(valor):
    return str(valor or '').strip().lower() in ('1', 'true', 'si', 'sí', 'yes')


def _git(repo, *args, entrada=None):
    cmd = [
        'git', '-c', 'user.name=Saimon City',
        '-c', 'user.email=respaldos@users.noreply.github.com',
        *args,
    ]
    proc = subprocess.run(cmd, cwd=repo, input=entrada, capture_output=True)
    if proc.returncode != 0:
        detalle = ocultar((proc.stderr or b'').decode('utf-8', 'replace')).strip()
        raise RuntimeError(detalle or 'git falló')
    return proc.stdout


def _ejecutar(cmd, cwd=None, env=None, timeout=180):
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        detalle = ocultar((proc.stderr or b'').decode('utf-8', 'replace')).strip()
        raise RuntimeError(detalle or (cmd[0] + ' falló'))
    return proc.stdout


def reloj_real(now):
    return datetime.fromtimestamp(float(now), BOGOTA)


def momento_juego(now, epoch):
    """Fecha de juego con el mismo reloj que el servidor."""
    info = reloj.describe(now, epoch)
    elapsed = max(0.0, float(now) - float(epoch))
    fecha = reloj.START + timedelta(seconds=elapsed * 86400.0 / reloj.REAL_SECONDS_PER_DAY)
    info['anio'] = fecha.year
    return info


def ancla(logico, env=None):
    """Misma prioridad que el servidor: variable, época guardada, despliegue."""
    saved = None
    economy = _documento(logico, 'economy')
    if isinstance(economy, dict):
        saved = economy.get('relojEpoch')
    if env is None:
        env = os.environ.get('GAME_CLOCK_EPOCH')
    return reloj.resolve_epoch(saved, env)


def etiquetar(now, epoch, sha, resumen, linea_base=False):
    real = reloj_real(now)
    juego = momento_juego(now, epoch)
    corto = (sha or 'manual')[:7]
    return {
        'etiqueta': real.strftime('respaldo-%Y%m%d-%H%M-') + corto,
        'fecha_real': real.strftime('%Y-%m-%d %H:%M'),
        'zona': 'America/Bogota',
        'fecha_juego': juego['fecha'],
        'anio_juego': juego['anio'],
        'hora_juego': juego['hora'],
        'commit': sha or '',
        'linea_base': bool(linea_base),
        'resumen': resumen,
        'epoch': int(epoch),
    }


def mensaje_etiqueta(info):
    lineas = [
        'Respaldo %s · %s' % (info['fecha_real'], info['fecha_juego']),
        '',
        'fecha_real: %s' % info['fecha_real'],
        'zona: America/Bogota',
        'fecha_juego: %s' % info['fecha_juego'],
        'anio_juego: %s' % info['anio_juego'],
        'hora_juego: %s' % info['hora_juego'],
        'commit: %s' % info['commit'],
        'linea_base: %s' % ('si' if info.get('linea_base') else 'no'),
        'resumen: %s' % info.get('resumen', ''),
    ]
    return '\n'.join(lineas) + '\n'


def parsear_mensaje(texto):
    datos = {}
    for linea in (texto or '').splitlines():
        if ':' not in linea:
            continue
        clave, valor = linea.split(':', 1)
        clave = clave.strip()
        if clave in (
            'fecha_real', 'zona', 'fecha_juego', 'anio_juego', 'hora_juego',
            'commit', 'linea_base', 'resumen',
        ):
            datos[clave] = valor.strip()
    if 'anio_juego' in datos:
        try:
            datos['anio_juego'] = int(datos['anio_juego'])
        except ValueError:
            datos['anio_juego'] = None
    datos['linea_base'] = datos.get('linea_base') == 'si'
    return datos


def etiquetas_de(pr):
    nombres = []
    for etiqueta in pr.get('labels') or []:
        if isinstance(etiqueta, dict):
            nombres.append((etiqueta.get('name') or '').strip().lower())
        else:
            nombres.append(str(etiqueta).strip().lower())
    return nombres


def numeros_pr(commits):
    encontrados = []
    for commit in commits or []:
        mensaje = commit.get('message') or ''
        encontrados.extend(_PR_MERGE.findall(mensaje))
        encontrados.extend(_PR_SQUASH.findall(mensaje))
    vistos = []
    for numero in encontrados:
        if numero not in vistos:
            vistos.append(numero)
    return vistos


def _linea_con_marca(texto, marca):
    """La marca cuenta en el título o al inicio de una línea, no citada en un párrafo."""
    for linea in (texto or '').splitlines():
        limpia = linea.strip().lower()
        if limpia.startswith(marca):
            return True
    return False


def es_importante(commits, prs, manual=False):
    """Un pull request fusionado cuenta. [sin-respaldo] lo salta. [respaldo] lo pide."""
    if manual:
        return True
    etiquetas = []
    opt_out = False
    opt_in = False
    for commit in commits or []:
        mensaje = commit.get('message') or ''
        opt_out = opt_out or _linea_con_marca(mensaje, _SKIP)
        opt_in = opt_in or _linea_con_marca(mensaje, _FORCE)
    for pr in prs or []:
        titulo = pr.get('title') or ''
        opt_out = opt_out or _linea_con_marca(titulo, _SKIP)
        opt_in = opt_in or _linea_con_marca(titulo, _FORCE)
        etiquetas.extend(etiquetas_de(pr))
    if opt_out or 'sin-respaldo' in etiquetas:
        return False
    if opt_in or 'respaldo' in etiquetas:
        return True
    if prs or numeros_pr(commits):
        return True
    return False


def redactar(texto):
    return ocultar(texto)


def limpiar_texto(texto):
    texto = texto or ''
    texto = re.sub(r'<!--.*?-->', ' ', texto, flags=re.S)
    texto = re.sub(r'```.*?```', ' ', texto, flags=re.S)
    texto = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', texto)
    texto = re.sub(r'\[[^\]]*\]\([^)]*\)', ' ', texto)
    texto = redactar(texto)
    return re.sub(r'\s+', ' ', texto).strip()


def _primera_frase(texto, limite=180):
    texto = limpiar_texto(texto)
    if not texto:
        return ''
    frase = re.split(r'(?<=[.!?])\s+', texto)[0]
    if len(frase) > limite:
        frase = frase[:limite - 1].rstrip() + '…'
    return frase


def _titulo_pr(pr):
    titulo = limpiar_texto(pr.get('title') or '')
    return re.sub(r'(?i)^merge pull request #\d+\b.*', '', titulo).strip()


def resumen(prs, commits=None, manual='', limite=500):
    """Una frase en español a partir de los títulos y los cuerpos."""
    escrito = limpiar_texto(manual)
    if escrito:
        return escrito[:limite]
    partes = []
    for pr in prs or []:
        titulo = _titulo_pr(pr).rstrip('.')
        cuerpo = _primera_frase(pr.get('body') or '')
        if titulo and cuerpo and cuerpo.lower() not in titulo.lower():
            partes.append('%s. %s' % (titulo, cuerpo))
        elif titulo:
            partes.append(titulo)
        elif cuerpo:
            partes.append(cuerpo)
    if not partes:
        for commit in commits or []:
            lineas = [ln.strip() for ln in (commit.get('message') or '').splitlines() if ln.strip()]
            if not lineas:
                continue
            sujeto = limpiar_texto(lineas[0])
            sujeto = re.sub(r'(?i)^merge pull request #\d+\b.*', '', sujeto).strip()
            if not sujeto and len(lineas) > 1:
                sujeto = limpiar_texto(lineas[-1])
            if sujeto:
                partes.append(sujeto.rstrip('.'))
                break
    if not partes:
        texto = 'Actualización de main sin una descripción.'
    elif len(partes) == 1:
        texto = 'Incluye: %s.' % partes[0].rstrip('.')
    else:
        texto = 'Entran %d cambios. Incluye: %s.' % (len(partes), '; '.join(parte.rstrip('.') for parte in partes))
    texto = re.sub(r'\s+', ' ', texto).strip()
    if len(texto) > limite:
        texto = texto[:limite - 1].rstrip() + '…'
    return texto


def titulo_release(info):
    prefijo = 'Línea base · ' if info.get('linea_base') else ''
    corto = info.get('resumen') or ''
    if len(corto) > 80:
        corto = corto[:77].rstrip() + '...'
    titulo = '%s%s Bogotá · año %s · %s' % (prefijo, info['fecha_real'], info['anio_juego'], corto)
    return titulo[:240]


def notas_release(info, repo=REPO_DEFECTO):
    cuentas = info.get('cuentas') or {}
    if info.get('datos') == 'incluidos' and info.get('almacen') == 'privado':
        donde = (
            'La copia de la base está cifrada en el almacén privado (`%s`). '
            'No se adjuntó a este release: el repositorio es público.'
        ) % (info.get('objeto') or 'saimon-city')
    elif info.get('datos') == 'incluidos':
        donde = (
            'La copia de la base va adjunta y cifrada (`%s`). '
            'Se puede descargar, y sólo se abre con la frase BACKUP_PASSPHRASE.'
        ) % (info.get('archivo') or 'saimon-datos.lifebak')
    else:
        donde = 'Esta vez no hay copia de la base. %s' % (info.get('motivo_datos') or '')
    lineas = [
        'Respaldo de Saimon City.',
        '',
        'Fecha real: %s (America/Bogota).' % info['fecha_real'],
        'Fecha de juego: %s, a las %s. Año %s.' % (
            info['fecha_juego'], info['hora_juego'], info['anio_juego'],
        ),
        'Commit: `%s`.' % info.get('commit', ''),
        '',
        info.get('resumen') or '',
        '',
        'Jugadores: %s. Billeteras: %s. Bloques de monedas: %s. Registros del libro: %s. Cuentas: %s. Opiniones: %s. Notas: %s. Anuncios: %s.' % (
            cuentas.get('jugadores', 0), cuentas.get('billeteras', 0),
            cuentas.get('bloques_monedas', 0), cuentas.get('registros_libro', 0),
            cuentas.get('cuentas', 0), cuentas.get('opiniones', 0),
            cuentas.get('notas', 0), cuentas.get('anuncios', 0),
        ),
        'Semilla de certificados: %s. Clave de Simón: %s.' % (
            info.get('semilla_certificados', 'ausente'), info.get('clave_simon', 'ausente'),
        ),
        donde.strip(),
        '',
        'Casas y muebles no están en el servidor: viven en el navegador de cada jugador. El juego todavía no guarda mascotas.',
        '',
        'Para mirar esta versión sin tocar el juego en vivo:',
        'https://github.com/%s/blob/main/BACKUPS.md' % repo,
        '',
        'python3 tools/respaldos.py listar',
        'python3 tools/respaldos.py codigo --etiqueta %s' % info.get('etiqueta', ''),
        'python3 tools/respaldos.py restaurar --etiqueta %s' % info.get('etiqueta', ''),
    ]
    return '\n'.join(lineas) + '\n'


def _keys(frase):
    raw = hashlib.scrypt(frase.encode('utf-8'), salt=SALT, n=2 ** 14, r=8, p=1, dklen=64)
    return raw[:32], raw[32:]


def _stream(key, nonce, length):
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hmac.new(key, nonce + counter.to_bytes(4, 'big'), hashlib.sha256).digest())
        counter += 1
    return bytes(out[:length])


def frase_actual(explicita=None):
    frase = explicita if explicita is not None else os.environ.get('BACKUP_PASSPHRASE', '')
    frase = str(frase or '')
    if len(frase) < 8:
        raise ValueError('BACKUP_PASSPHRASE necesita al menos 8 caracteres y no va en el repositorio.')
    return frase


def cifrar(data, frase):
    frase = frase_actual(frase)
    data = bytes(data)
    nonce = secrets.token_bytes(16)
    enc_key, mac_key = _keys(frase)
    cipher = bytes(a ^ b for a, b in zip(data, _stream(enc_key, nonce, len(data))))
    mac = hmac.new(mac_key, nonce + cipher, hashlib.sha256).digest()
    return MAGIC + nonce + mac + cipher


def descifrar(blob, frase):
    frase = frase_actual(frase)
    raw = bytes(blob)
    if len(raw) < len(MAGIC) + 16 + 32 or not raw.startswith(MAGIC):
        raise ValueError('El archivo no es un respaldo de Saimon City.')
    nonce = raw[len(MAGIC):len(MAGIC) + 16]
    mac = raw[len(MAGIC) + 16:len(MAGIC) + 48]
    cipher = raw[len(MAGIC) + 48:]
    enc_key, mac_key = _keys(frase)
    expected = hmac.new(mac_key, nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError('La frase no abre este respaldo.')
    return bytes(a ^ b for a, b in zip(cipher, _stream(enc_key, nonce, len(cipher))))


def _agregar(tar, nombre, data):
    info = tarfile.TarInfo(nombre)
    info.size = len(data)
    info.mtime = 0
    tar.addfile(info, io.BytesIO(data))


def empaquetar(logico, dump=None, manifiesto=None):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        _agregar(tar, 'logico.json', json.dumps(logico, ensure_ascii=False).encode('utf-8'))
        if dump:
            _agregar(tar, 'juego.dump', dump)
        if manifiesto is not None:
            _agregar(tar, 'manifiesto.json', json.dumps(manifiesto, ensure_ascii=False).encode('utf-8'))
    return buf.getvalue()


def abrir_paquete(data):
    salida = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        for miembro in tar.getmembers():
            nombre = os.path.basename(miembro.name)
            if nombre not in PERMITIDOS or not miembro.isfile():
                continue
            extraido = tar.extractfile(miembro)
            if extraido is None:
                continue
            salida[nombre] = extraido.read()
    if 'logico.json' not in salida:
        raise ValueError('El respaldo no trae los datos.')
    logico = json.loads(salida['logico.json'].decode('utf-8'))
    return logico, salida.get('juego.dump'), salida.get('manifiesto.json')


def _jsonable(valor):
    if isinstance(valor, dict):
        if set(valor) == {'$b64'} and isinstance(valor.get('$b64'), str):
            return valor
        return {str(k): _jsonable(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_jsonable(v) for v in valor]
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, (bytes, bytearray, memoryview)):
        return {'$b64': base64.b64encode(bytes(valor)).decode('ascii')}
    if isinstance(valor, (str, int, float, bool)) or valor is None:
        return valor
    return str(valor)


def _leer_json(path):
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _nombre_seguro(nombre):
    base = os.path.basename(nombre or '')
    return base == nombre and bool(base) and '..' not in base and _IDENT.match(os.path.splitext(base)[0] or '')


def _tabla(filas, esquema=None):
    caja = {'filas': filas}
    if esquema:
        caja['columnas'] = esquema['columnas']
        caja['primaria'] = esquema['primaria']
    return caja


def _documento(logico, nombre):
    tablas = (logico or {}).get('tablas') or {}
    filas = (tablas.get('stores') or {}).get('filas') or []
    for fila in filas:
        if isinstance(fila, dict) and fila.get('name') == nombre:
            doc = fila.get('doc')
            return doc if isinstance(doc, dict) else None
    return None


def cuentas_publicas(logico):
    """Conteos. Ningún nombre, correo, saldo ni secreto."""
    tablas = (logico or {}).get('tablas') or {}
    economy = _documento(logico, 'economy') or {}
    players = _documento(logico, 'players') or {}
    libro = _documento(logico, 'libro_madre') or {}
    vault = _documento(logico, 'vault') or {}
    accounts = _documento(logico, 'accounts') or {}
    semilla = _documento(logico, 'nft_seed') or {}
    simon = (tablas.get('simon_records') or {}).get('filas') or []
    anuncios = (tablas.get('apartment_listings') or {}).get('filas') or []
    notas = [fila for fila in simon if fila.get('kind') in ('conversation', 'case')]
    opiniones = [fila for fila in simon if fila.get('kind') == 'feedback']
    ausente = list(AUSENTE)
    if 'simon_records' not in tablas:
        ausente.append('Notas y opiniones: esta copia no tiene la tabla simon_records.')
    return {
        'cuentas': {
            'jugadores': len(players.get('players') or {}) if isinstance(players, dict) else 0,
            'billeteras': len(economy.get('wallets') or {}) if isinstance(economy, dict) else 0,
            'bloques_monedas': len(economy.get('blocks') or []) if isinstance(economy, dict) else 0,
            'registros_libro': len(libro.get('blocks') or []) if isinstance(libro, dict) else 0,
            'cuentas': len(accounts.get('users') or []) if isinstance(accounts, dict) else 0,
            'opiniones': len(opiniones),
            'notas': len(notas),
            'deposito': len(vault.get('accounts') or {}) if isinstance(vault, dict) else 0,
            'anuncios': len(anuncios),
        },
        'semilla_certificados': 'incluida' if semilla.get('seed') else 'ausente',
        'clave_simon': 'incluida' if (logico or {}).get('claves', {}).get('SIMON_DATA_KEY') else 'ausente',
        'ausente': ausente,
        'tablas': sorted(tablas),
    }


def _clave_simon(state_dir=None, usar_archivo=False):
    env = os.environ.get('SIMON_DATA_KEY', '').strip()
    if env:
        return env
    if usar_archivo and state_dir:
        path = os.path.join(state_dir, 'simon-data.key')
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as handle:
                return handle.read().strip()
    return ''


def _leer_sqlite(path, sql):
    if not os.path.isfile(path):
        return []
    uri = 'file:%s?mode=ro' % path
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(fila) for fila in conn.execute(sql)]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def exportar_archivos(state_dir):
    tablas = {}
    stores = []
    for filename, nombre in STORE_FILES.items():
        doc = _leer_json(os.path.join(state_dir, filename))
        if isinstance(doc, dict):
            stores.append({'name': nombre, 'doc': doc, 'updated_at': None})
    if stores:
        tablas['stores'] = _tabla(stores, ESQUEMA['stores'])
    ids = _leer_json(os.path.join(state_dir, 'libro-ids.json')) or {}
    if isinstance(ids, dict) and ids.get('ids'):
        tablas['libro_ids'] = _tabla(
            [{'id': str(item)} for item in ids['ids'] if item],
            ESQUEMA['libro_ids'],
        )
    simon = _leer_sqlite(
        os.path.join(state_dir, 'simon.sqlite3'),
        'SELECT id, kind, subject, doc FROM simon_records',
    )
    if simon or os.path.isfile(os.path.join(state_dir, 'simon.sqlite3')):
        tablas['simon_records'] = _tabla(simon, ESQUEMA['simon_records'])
    for tabla, archivo in (
        ('apartment_listings', 'apartments.sqlite3'),
        ('apartment_source_status', 'apartments.sqlite3'),
    ):
        filas = _leer_sqlite(os.path.join(state_dir, archivo), 'SELECT id, doc FROM %s' % tabla)
        if filas:
            tablas[tabla] = _tabla(filas, ESQUEMA[tabla])
    sqlite_bytes = {}
    for nombre in os.listdir(state_dir):
        if nombre.endswith('.sqlite3') and _nombre_seguro(nombre):
            with open(os.path.join(state_dir, nombre), 'rb') as handle:
                sqlite_bytes[nombre] = base64.b64encode(handle.read()).decode('ascii')
    extras = {}
    for nombre in os.listdir(state_dir):
        if not nombre.endswith('.json') or nombre in STORE_FILES or nombre == 'libro-ids.json':
            continue
        if not _nombre_seguro(nombre):
            continue
        doc = _leer_json(os.path.join(state_dir, nombre))
        if doc is not None:
            extras[nombre] = doc
    clave = _clave_simon(state_dir, usar_archivo=True)
    return {
        'origen': 'archivos',
        'tablas': tablas,
        'sqlite': sqlite_bytes,
        'extras': extras,
        'claves': {'SIMON_DATA_KEY': clave} if clave else {},
        'pg_dump': None,
        'error': '',
    }


def _pg_env(url):
    partes = urlsplit(url)
    env = os.environ.copy()
    env['PGHOST'] = partes.hostname or ''
    env['PGPORT'] = str(partes.port or 5432)
    env['PGUSER'] = unquote(partes.username or '')
    env['PGPASSWORD'] = unquote(partes.password or '')
    env['PGDATABASE'] = unquote((partes.path or '/').lstrip('/'))
    env['PGCONNECT_TIMEOUT'] = '10'
    consulta = dict(parse_qsl(partes.query))
    if consulta.get('sslmode'):
        env['PGSSLMODE'] = consulta['sslmode']
    elif consulta.get('ssl', '').lower() == 'true':
        env['PGSSLMODE'] = 'require'
    return env


def _volcar_pg(url, destino):
    if not _which('pg_dump'):
        return None
    env = _pg_env(url)
    _ejecutar(
        ['pg_dump', '--format=custom', '--no-owner', '--no-acl', '--file', destino],
        env=env,
        timeout=180,
    )
    with open(destino, 'rb') as handle:
        return handle.read()


def _which(nombre):
    for carpeta in os.environ.get('PATH', '').split(os.pathsep):
        candidato = os.path.join(carpeta, nombre)
        if os.path.isfile(candidato) and os.access(candidato, os.X_OK):
            return candidato
    return ''


def _columnas_pg(conn, tabla):
    filas = conn.execute(
        """SELECT column_name, data_type
           FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = %s
           ORDER BY ordinal_position""",
        (tabla,),
    ).fetchall()
    columnas = [{'name': nombre, 'tipo': TIPOS.get((tipo or '').lower(), 'text')} for nombre, tipo in filas]
    primaria = [
        fila[0] for fila in conn.execute(
            """SELECT kcu.column_name
               FROM information_schema.table_constraints tc
               JOIN information_schema.key_column_usage kcu
                 ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
               WHERE tc.table_schema = 'public' AND tc.table_name = %s
                 AND tc.constraint_type = 'PRIMARY KEY'
               ORDER BY kcu.ordinal_position""",
            (tabla,),
        ).fetchall()
    ]
    return columnas, primaria


def exportar_postgres(url):
    import psycopg
    logico = {
        'origen': 'postgres',
        'tablas': {},
        'sqlite': {},
        'extras': {},
        'claves': {},
        'pg_dump': None,
        'error': '',
    }
    conn = psycopg.connect(url, connect_timeout=10, autocommit=False)
    try:
        conn.execute("SET statement_timeout = '60s'")
        conn.execute("SET lock_timeout = '5s'")
        conn.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        tablas = [
            fila[0] for fila in conn.execute(
                """SELECT table_name FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                   ORDER BY table_name"""
            ).fetchall()
        ]
        for tabla in tablas:
            if not _IDENT.match(tabla):
                continue
            columnas, primaria = _columnas_pg(conn, tabla)
            nombres = [col['name'] for col in columnas if _IDENT.match(col['name'])]
            if not nombres:
                continue
            quoted = ', '.join('"%s"' % nombre for nombre in nombres)
            crudas = conn.execute('SELECT %s FROM "%s"' % (quoted, tabla)).fetchall()
            filas = []
            for cruda in crudas:
                filas.append({nombre: _jsonable(valor) for nombre, valor in zip(nombres, cruda)})
            logico['tablas'][tabla] = {'filas': filas, 'columnas': columnas, 'primaria': primaria}
        conn.rollback()
    finally:
        conn.close()
    clave = _clave_simon()
    if clave:
        logico['claves'] = {'SIMON_DATA_KEY': clave}
    try:
        fd, ruta = tempfile.mkstemp(prefix='saimon-', suffix='.dump')
        os.close(fd)
        try:
            logico['pg_dump'] = _volcar_pg(url, ruta)
        finally:
            if os.path.isfile(ruta):
                os.remove(ruta)
    except Exception as exc:
        logico['error'] = 'pg_dump no pudo correr: %s' % ocultar(exc)
    return logico


def exportar(state_dir=None, url=None):
    if url is None:
        url = os.environ.get('DATABASE_URL', '').strip()
    else:
        url = str(url or '').strip()
    if url:
        try:
            return exportar_postgres(url)
        except Exception as exc:
            return {
                'origen': 'postgres',
                'tablas': {},
                'sqlite': {},
                'extras': {},
                'claves': {},
                'pg_dump': None,
                'error': 'No se pudo leer la base: %s' % type(exc).__name__,
            }
    carpeta = STATE_DIR if state_dir is None else state_dir
    if not carpeta or not os.path.isdir(carpeta):
        return {
            'origen': 'vacio',
            'tablas': {},
            'sqlite': {},
            'extras': {},
            'claves': {},
            'pg_dump': None,
            'error': 'No hay DATABASE_URL ni carpeta state/.',
        }
    return exportar_archivos(carpeta)


def manifiesto_publico(info, logico, datos, motivo, archivo=None, almacen='omitido', objeto=None, sha256=None):
    publico = cuentas_publicas(logico)
    return {
        'etiqueta': info['etiqueta'],
        'fecha_real': info['fecha_real'],
        'zona': 'America/Bogota',
        'fecha_juego': info['fecha_juego'],
        'anio_juego': info['anio_juego'],
        'hora_juego': info['hora_juego'],
        'commit': info['commit'],
        'linea_base': bool(info.get('linea_base')),
        'resumen': info.get('resumen') or '',
        'epoch': info.get('epoch'),
        'cifrado': 'lifebak1' if datos == 'incluidos' else '',
        'datos': datos,
        'motivo_datos': motivo,
        'archivo': archivo,
        'almacen': almacen,
        'objeto': objeto,
        'sha256': sha256,
        'cuentas': publico['cuentas'],
        'semilla_certificados': publico['semilla_certificados'],
        'clave_simon': publico['clave_simon'],
        'ausente': publico['ausente'],
        'tablas': publico['tablas'],
    }


def _identificar(nombre):
    if not _IDENT.match(nombre or ''):
        raise ValueError('Nombre no permitido')
    return nombre


def misma_base(una, otra):
    if not una or not otra:
        return False
    a, b = urlsplit(una.strip()), urlsplit(otra.strip())
    puerto_a = a.port or 5432
    puerto_b = b.port or 5432
    return (
        (a.hostname or '').lower(),
        puerto_a,
        unquote((a.path or '').rstrip('/')).lower(),
    ) == (
        (b.hostname or '').lower(),
        puerto_b,
        unquote((b.path or '').rstrip('/')).lower(),
    )


def destino_peligroso(destino, repo=ROOT):
    real = os.path.realpath(destino)
    state = os.path.realpath(os.path.join(repo, 'state'))
    return real == state


def _escribir(path, data, texto=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    modo = 'w' if texto else 'wb'
    with open(path, modo, encoding='utf-8' if texto else None) as handle:
        handle.write(data)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def restaurar_directorio(logico, destino):
    if os.path.isdir(destino) and os.listdir(destino):
        raise RuntimeError('La carpeta de destino ya tiene archivos. Elige otra.')
    os.makedirs(destino, exist_ok=True)
    tablas = logico.get('tablas') or {}
    stores = (tablas.get('stores') or {}).get('filas') or []
    por_nombre = {fila.get('name'): fila.get('doc') for fila in stores if isinstance(fila, dict)}
    inversos = {nombre: archivo for archivo, nombre in STORE_FILES.items()}
    for nombre, doc in por_nombre.items():
        archivo = inversos.get(nombre)
        if not archivo or not isinstance(doc, dict):
            continue
        _escribir(os.path.join(destino, archivo), json.dumps(doc, ensure_ascii=False, indent=1), texto=True)
    ids = [fila.get('id') for fila in (tablas.get('libro_ids') or {}).get('filas') or [] if fila.get('id')]
    if ids:
        _escribir(
            os.path.join(destino, 'libro-ids.json'),
            json.dumps({'ids': sorted(set(ids))}, ensure_ascii=False),
            texto=True,
        )
    for nombre, doc in (logico.get('extras') or {}).items():
        if _nombre_seguro(nombre) and nombre.endswith('.json'):
            _escribir(os.path.join(destino, nombre), json.dumps(doc, ensure_ascii=False, indent=1), texto=True)
    sqlite_bytes = logico.get('sqlite') or {}
    if sqlite_bytes:
        for nombre, encoded in sqlite_bytes.items():
            if not (nombre.endswith('.sqlite3') and _nombre_seguro(nombre)):
                continue
            _escribir(os.path.join(destino, nombre), base64.b64decode(encoded))
    else:
        _restaurar_sqlite(
            os.path.join(destino, 'simon.sqlite3'),
            'simon_records',
            'CREATE TABLE IF NOT EXISTS simon_records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject TEXT, doc TEXT NOT NULL)',
            'INSERT INTO simon_records (id, kind, subject, doc) VALUES (?, ?, ?, ?)',
            [
                (fila.get('id'), fila.get('kind'), fila.get('subject'), fila.get('doc'))
                for fila in (tablas.get('simon_records') or {}).get('filas') or []
                if fila.get('id')
            ],
        )
        listings = (tablas.get('apartment_listings') or {}).get('filas') or []
        status = (tablas.get('apartment_source_status') or {}).get('filas') or []
        if listings or status:
            path = os.path.join(destino, 'apartments.sqlite3')
            conn = sqlite3.connect(path)
            try:
                conn.execute('CREATE TABLE IF NOT EXISTS apartment_listings (id TEXT PRIMARY KEY, doc TEXT NOT NULL)')
                conn.execute('CREATE TABLE IF NOT EXISTS apartment_source_status (id TEXT PRIMARY KEY, doc TEXT NOT NULL)')
                conn.executemany(
                    'INSERT INTO apartment_listings (id, doc) VALUES (?, ?)',
                    [(fila.get('id'), fila.get('doc')) for fila in listings if fila.get('id')],
                )
                conn.executemany(
                    'INSERT INTO apartment_source_status (id, doc) VALUES (?, ?)',
                    [(fila.get('id'), fila.get('doc')) for fila in status if fila.get('id')],
                )
                conn.commit()
            finally:
                conn.close()
            os.chmod(path, 0o600)
    clave = (logico.get('claves') or {}).get('SIMON_DATA_KEY')
    if clave:
        _escribir(os.path.join(destino, 'simon-data.key'), clave, texto=True)


def _restaurar_sqlite(path, _tabla_nombre, create, insert, filas):
    if not filas and not os.path.isfile(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(create)
        if filas:
            conn.executemany(insert, filas)
        conn.commit()
    finally:
        conn.close()
    os.chmod(path, 0o600)


def _valor_pg(tipo, valor):
    if isinstance(valor, dict) and set(valor) == {'$b64'}:
        return base64.b64decode(valor['$b64'])
    if tipo == 'jsonb' and not isinstance(valor, str):
        from psycopg.types.json import Json
        return Json(valor)
    return valor


def restaurar_postgres(url, logico, dump, reemplazar=False):
    if dump and _which('pg_restore'):
        _restaurar_pg_dump(url, dump, reemplazar)
        return 'pg_restore'
    import psycopg
    conn = psycopg.connect(url, connect_timeout=10, autocommit=False)
    try:
        with conn.transaction():
            for tabla, caja in (logico.get('tablas') or {}).items():
                _identificar(tabla)
                columnas = [col for col in (caja.get('columnas') or []) if _IDENT.match(col.get('name') or '')]
                if not columnas:
                    continue
                tipos = {col['name']: col.get('tipo') or 'text' for col in columnas}
                existe = conn.execute(
                    """SELECT 1 FROM information_schema.tables
                       WHERE table_schema = 'public' AND table_name = %s""",
                    (tabla,),
                ).fetchone()
                if not existe:
                    primaria = [col for col in (caja.get('primaria') or []) if _IDENT.match(col)]
                    defs = ['"%s" %s' % (col['name'], col.get('tipo') or 'text') for col in columnas]
                    if primaria:
                        defs.append('PRIMARY KEY (%s)' % ', '.join('"%s"' % col for col in primaria))
                    conn.execute('CREATE TABLE "%s" (%s)' % (tabla, ', '.join(defs)))
                else:
                    cuantos = conn.execute('SELECT count(*) FROM "%s"' % tabla).fetchone()[0]
                    if cuantos and not reemplazar:
                        raise RuntimeError(
                            'La tabla %s ya tiene filas. Usa otra base vacía, o --reemplazar si esa copia es tuya.'
                            % tabla
                        )
                    if cuantos and reemplazar:
                        conn.execute('DELETE FROM "%s"' % tabla)
                nombres = [col['name'] for col in columnas]
                quoted = ', '.join('"%s"' % nombre for nombre in nombres)
                marks = ', '.join(['%s'] * len(nombres))
                sql = 'INSERT INTO "%s" (%s) VALUES (%s)' % (tabla, quoted, marks)
                for fila in caja.get('filas') or []:
                    try:
                        conn.execute(sql, [_valor_pg(tipos[nombre], fila.get(nombre)) for nombre in nombres])
                    except Exception as exc:
                        raise RuntimeError(
                            'No se pudo escribir la tabla %s (%s).' % (tabla, type(exc).__name__)
                        ) from None
        return 'logico'
    finally:
        conn.close()


def _restaurar_pg_dump(url, dump, reemplazar):
    fd, ruta = tempfile.mkstemp(prefix='saimon-', suffix='.dump')
    os.close(fd)
    try:
        with open(ruta, 'wb') as handle:
            handle.write(dump)
        cmd = ['pg_restore', '--no-owner', '--no-acl', '--exit-on-error']
        if reemplazar:
            cmd.extend(['--clean', '--if-exists'])
        cmd.append(ruta)
        _ejecutar(cmd, env=_pg_env(url), timeout=180)
    finally:
        os.remove(ruta)


def comprobar_destino(database_url='', destino='', produccion=False, repo=ROOT):
    produccion_url = os.environ.get('DATABASE_URL', '').strip()
    if database_url and misma_base(database_url, produccion_url) and not produccion:
        raise RuntimeError(
            'Esa URL es la base de producción. Elige otra base, o pasa --produccion si de verdad quieres reemplazar la ciudad en vivo.'
        )
    if destino and destino_peligroso(destino, repo) and not produccion:
        raise RuntimeError(
            'Esa carpeta es state/ del juego en vivo. Elige restauracion/<etiqueta> u otra carpeta.'
        )


def restaurar(archivo, destino, frase, database_url='', produccion=False, reemplazar=False, repo=ROOT):
    comprobar_destino(database_url, destino, produccion, repo)
    with open(archivo, 'rb') as handle:
        claro = descifrar(handle.read(), frase)
    logico, dump, _manifiesto = abrir_paquete(claro)
    hecho = []
    if destino:
        restaurar_directorio(logico, destino)
        hecho.append(destino)
    if database_url:
        via = restaurar_postgres(database_url, logico, dump, reemplazar)
        hecho.append(via)
    if not hecho:
        raise RuntimeError('Indica una carpeta con --destino o una base con --database-url.')
    return hecho


def listar(repo='.'):
    raw = _git(
        repo, 'tag', '-l', 'respaldo-*', '--sort=-creatordate',
        '--format=%(refname:short)%00%(contents)%00',
    ).decode('utf-8', 'replace')
    partes = raw.split('\0')
    filas = []
    indice = 0
    while indice + 1 < len(partes):
        nombre = partes[indice].strip()
        mensaje = partes[indice + 1]
        indice += 2
        if not nombre.startswith('respaldo-'):
            continue
        datos = parsear_mensaje(mensaje)
        datos['etiqueta'] = nombre
        filas.append(datos)
    filas.sort(key=lambda fila: (fila.get('fecha_real') or '', fila.get('etiqueta') or ''), reverse=True)
    return filas


def formato_lista(filas):
    if not filas:
        return 'Todavía no hay respaldos. Cuando se fusione un pull request en main, aparecerá aquí.\n'
    lineas = []
    for fila in filas:
        anio = fila.get('anio_juego')
        anio_txt = ('año %s' % anio) if anio else 'año ?'
        marca = ' · línea base' if fila.get('linea_base') else ''
        lineas.append(
            '%s (Bogotá) · %s · %s · %s%s' % (
                fila.get('fecha_real') or 'sin fecha',
                anio_txt,
                fila.get('fecha_juego') or 'sin fecha de juego',
                fila.get('etiqueta') or '',
                marca,
            )
        )
        if fila.get('resumen'):
            lineas.append('    %s' % fila['resumen'])
    return '\n'.join(lineas) + '\n'


def preparar_codigo(etiqueta, carpeta, repo='.'):
    if os.path.exists(carpeta):
        raise RuntimeError('Ya existe %s. No la borro.' % carpeta)
    os.makedirs(os.path.dirname(os.path.abspath(carpeta)) or '.', exist_ok=True)
    try:
        _git(repo, 'fetch', 'origin', 'tag', etiqueta, '--no-tags')
    except RuntimeError:
        pass
    _git(repo, 'worktree', 'add', '--detach', carpeta, etiqueta)
    return carpeta


def _commits_git(repo, antes, despues):
    if not antes or not despues or str(antes).startswith('0000000'):
        return []
    try:
        raw = _git(repo, 'log', '--format=COMMIT %H%n%s%n%b%nENDCOMMIT', '%s..%s' % (antes, despues))
    except RuntimeError:
        return []
    commits = []
    for bloque in raw.decode('utf-8', 'replace').split('ENDCOMMIT'):
        bloque = bloque.strip()
        if not bloque.startswith('COMMIT '):
            continue
        lineas = bloque.splitlines()
        sha = lineas[0][len('COMMIT '):].strip()
        sujeto = lineas[1] if len(lineas) > 1 else ''
        cuerpo = '\n'.join(lineas[2:]).strip()
        mensaje = sujeto + ('\n\n' + cuerpo if cuerpo else '')
        commits.append({'id': sha, 'message': mensaje.strip()})
    return commits


def commits_del_evento(evento, desde_git):
    """Incluye el commit de la fusión aunque el push sólo liste los commits de la rama."""
    commits = list(desde_git or [])
    if not commits:
        for commit in (evento or {}).get('commits') or []:
            commits.append({'id': commit.get('id') or '', 'message': commit.get('message') or ''})
    cabeza = (evento or {}).get('head_commit') or {}
    mensaje = cabeza.get('message') or ''
    identificador = cabeza.get('id') or ''
    if mensaje and not any(c.get('id') == identificador and identificador for c in commits):
        if not any(c.get('message') == mensaje for c in commits):
            commits.insert(0, {'id': identificador, 'message': mensaje})
    return commits


def _titulo_desde_commit(commit, numero):
    mensaje = commit.get('message') or ''
    if re.search(r'\(#%s\)\s*$' % re.escape(numero), mensaje, re.M):
        return (mensaje.splitlines() or [''])[0]
    if re.search(r'Merge pull request #%s\b' % re.escape(numero), mensaje):
        lineas = [ln.strip() for ln in mensaje.splitlines() if ln.strip()]
        if len(lineas) > 1:
            return lineas[-1]
    return ''


def pulls_del_commit(repo_slug, sha):
    """El pull request fusionado, aunque el mensaje del push no lo diga."""
    if not sha or not repo_slug:
        return []
    try:
        raw = _ejecutar([
            'gh', 'api', 'repos/%s/commits/%s/pulls' % (repo_slug, sha),
            '-H', 'Accept: application/vnd.github+json',
        ])
        data = json.loads(raw.decode('utf-8'))
    except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        return []
    prs = []
    for pr in data if isinstance(data, list) else []:
        prs.append({
            'number': pr.get('number'),
            'title': pr.get('title') or '',
            'body': pr.get('body') or '',
            'labels': etiquetas_de(pr),
        })
    return prs


def obtener_prs(numeros, commits):
    prs = []
    for numero in numeros:
        try:
            raw = _ejecutar(['gh', 'pr', 'view', str(numero), '--json', 'title,body,labels,number'])
            pr = json.loads(raw.decode('utf-8'))
            pr['labels'] = etiquetas_de(pr)
            prs.append(pr)
        except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired):
            titulo = ''
            for commit in commits or []:
                titulo = _titulo_desde_commit(commit, str(numero))
                if titulo:
                    break
            prs.append({'number': int(numero), 'title': titulo, 'body': '', 'labels': []})
    return prs


def etiquetas_del_commit(repo, sha):
    raw = _git(repo, 'tag', '-l', 'respaldo-*', '--points-at', sha).decode('utf-8', 'replace')
    return [linea.strip() for linea in raw.splitlines() if linea.strip()]


def _sha_head(repo):
    return _git(repo, 'rev-parse', 'HEAD').decode().strip()


def _subir_privado(ruta, nombre):
    bucket = os.environ.get('BACKUP_S3_BUCKET', '').strip()
    key_id = os.environ.get('BACKUP_S3_ACCESS_KEY_ID', '').strip()
    secret = os.environ.get('BACKUP_S3_SECRET_ACCESS_KEY', '').strip()
    if not bucket:
        return None
    if not key_id or not secret:
        raise RuntimeError(
            'BACKUP_S3_BUCKET está puesto, pero faltan BACKUP_S3_ACCESS_KEY_ID y BACKUP_S3_SECRET_ACCESS_KEY.'
        )
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError('Falta boto3 para el almacén privado. pip install boto3') from exc
    endpoint = os.environ.get('BACKUP_S3_ENDPOINT', '').strip() or None
    if endpoint:
        region = os.environ.get('BACKUP_S3_REGION', '').strip() or 'auto'
    else:
        region = os.environ.get('BACKUP_S3_REGION', '').strip() or 'us-east-1'
    cliente = boto3.client(
        's3',
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
    )
    clave = 'saimon-city/' + nombre
    cliente.upload_file(ruta, bucket, clave)
    return clave


def _bajar_privado(objeto, destino):
    bucket = os.environ.get('BACKUP_S3_BUCKET', '').strip()
    key_id = os.environ.get('BACKUP_S3_ACCESS_KEY_ID', '').strip()
    secret = os.environ.get('BACKUP_S3_SECRET_ACCESS_KEY', '').strip()
    if not (bucket and key_id and secret):
        raise RuntimeError('Ese respaldo está en el almacén privado y aquí faltan las claves S3.')
    import boto3
    endpoint = os.environ.get('BACKUP_S3_ENDPOINT', '').strip() or None
    region = os.environ.get('BACKUP_S3_REGION', '').strip() or ('auto' if endpoint else 'us-east-1')
    cliente = boto3.client(
        's3',
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
    )
    cliente.download_file(bucket, objeto, destino)
    return destino


def _release_existe(nombre):
    proc = subprocess.run(['gh', 'release', 'view', nombre, '--json', 'tagName'], capture_output=True)
    return proc.returncode == 0


def _crear_release(nombre, titulo, notas, archivos, repo):
    fd, path = tempfile.mkstemp(prefix='notas-respaldo-', suffix='.md')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(notas)
        cmd = ['gh', 'release', 'create', nombre, '--title', titulo, '--notes-file', path, *archivos]
        _ejecutar(cmd, cwd=repo)
    finally:
        if os.path.isfile(path):
            os.remove(path)


def _subir_asset(nombre, archivo, repo):
    _ejecutar(['gh', 'release', 'upload', nombre, archivo, '--clobber'], cwd=repo)


def _empujar_etiqueta(repo, nombre):
    proc = subprocess.run(
        ['git', 'push', 'origin', 'refs/tags/' + nombre],
        cwd=repo, capture_output=True,
    )
    if proc.returncode == 0:
        return
    detalle = ocultar((proc.stderr or b'').decode('utf-8', 'replace'))
    bajo = detalle.lower()
    if 'already exists' in bajo or 'ya existe' in bajo or 'up-to-date' in bajo or 'todo actualizado' in bajo:
        return
    raise RuntimeError(detalle.strip() or 'git push falló')


def _preparar_cifrado(info, logico):
    if isinstance(logico, dict):
        dump = logico.pop('pg_dump', None)
    else:
        dump = None
    motivo = (logico or {}).get('error') or ''
    hay_datos = bool((logico or {}).get('tablas')) or bool(dump)
    if not hay_datos:
        manifiesto = manifiesto_publico(info, logico or {}, 'omitidos', motivo or 'No había datos que copiar.')
        return manifiesto, None, None
    try:
        frase = frase_actual()
    except ValueError:
        manifiesto = manifiesto_publico(
            info, logico, 'omitidos',
            'Falta BACKUP_PASSPHRASE. No subo la base en claro porque el repositorio es público.',
        )
        return manifiesto, None, None
    previo = manifiesto_publico(info, logico, 'incluidos', '', almacen='release')
    paquete = empaquetar(logico, dump, previo)
    cifrado = cifrar(paquete, frase)
    digest = hashlib.sha256(cifrado).hexdigest()
    archivo = 'saimon-datos-%s.lifebak' % info['etiqueta']
    manifiesto = manifiesto_publico(
        info, logico, 'incluidos', '', archivo=archivo, almacen='release', sha256=digest,
    )
    return manifiesto, cifrado, archivo


def _leer_evento(path):
    if not path or not os.path.isfile(path):
        return {}
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def publicar(repo='.', sha='', manual=False, linea_base=False, solo_datos=False, resumen_manual='',
             evento_path='', evento_nombre='', empujar=None, etiqueta_existente=''):
    if empujar is None:
        empujar = os.environ.get('GITHUB_ACTIONS') == 'true'
    evento_nombre = evento_nombre or os.environ.get('GITHUB_EVENT_NAME', '')
    evento_path = evento_path or os.environ.get('GITHUB_EVENT_PATH', '')
    if evento_nombre == 'workflow_dispatch':
        manual = True
    linea_base = linea_base or _si(os.environ.get('LINEA_BASE'))
    solo_datos = solo_datos or _si(os.environ.get('SOLO_DATOS'))
    resumen_manual = resumen_manual or os.environ.get('RESUMEN_MANUAL', '')
    etiqueta_existente = etiqueta_existente or os.environ.get('ETIQUETA', '')
    if str(resumen_manual or '').strip().lower() in ('', 'null', 'none'):
        resumen_manual = ''
    if str(etiqueta_existente or '').strip().lower() in ('', 'null', 'none'):
        etiqueta_existente = ''
    if not manual and not solo_datos and evento_nombre not in ('push', 'workflow_dispatch'):
        raise RuntimeError('Nada que publicar. En GitHub esto corre al fusionar en main, o con --linea-base.')
    evento = _leer_evento(evento_path)
    sha = (sha or evento.get('after') or evento.get('head_commit', {}).get('id') or '').strip()
    if not sha or sha.startswith('0000000'):
        sha = _sha_head(repo)
    repo_slug = os.environ.get('GITHUB_REPOSITORY', '').strip() or REPO_DEFECTO
    commits = commits_del_evento(evento, _commits_git(repo, evento.get('before'), evento.get('after')))
    numeros = numeros_pr(commits)
    prs = []
    if not solo_datos:
        prs = pulls_del_commit(repo_slug, sha)
        if not prs and numeros:
            prs = obtener_prs(numeros, commits)
    if not solo_datos and not es_importante(commits, prs, manual=manual or linea_base):
        print('Este push no pide respaldo: no es un pull request fusionado ni lleva [respaldo].')
        return 0
    previas = etiquetas_del_commit(repo, sha)
    if etiqueta_existente:
        nombre = etiqueta_existente
    elif previas:
        nombre = previas[0]
    else:
        nombre = ''
    if solo_datos and not nombre:
        raise RuntimeError('No hay una etiqueta de respaldo en ese commit. Publícala primero.')
    logico = exportar()
    epoch = ancla(logico)
    texto = resumen(prs, commits, resumen_manual)
    if linea_base and not texto.lower().startswith('línea base'):
        texto = 'Línea base de Saimon City. ' + texto
    info = etiquetar(time.time(), epoch, sha, texto, linea_base=linea_base)
    if nombre:
        info['etiqueta'] = nombre
    else:
        nombre = info['etiqueta']
    manifiesto, cifrado, archivo = _preparar_cifrado(info, logico)
    info.update({
        'datos': manifiesto['datos'],
        'motivo_datos': manifiesto['motivo_datos'],
        'archivo': manifiesto.get('archivo'),
        'almacen': manifiesto.get('almacen'),
        'objeto': manifiesto.get('objeto'),
        'cuentas': manifiesto['cuentas'],
        'semilla_certificados': manifiesto['semilla_certificados'],
        'clave_simon': manifiesto['clave_simon'],
    })
    temporal = tempfile.mkdtemp(prefix='respaldo-')
    try:
        ruta_manifiesto = os.path.join(temporal, 'manifiesto.json')
        with open(ruta_manifiesto, 'w', encoding='utf-8') as handle:
            json.dump(manifiesto, handle, ensure_ascii=False, indent=1)
        archivos = [ruta_manifiesto]
        ruta_cifrado = None
        if cifrado is not None:
            ruta_cifrado = os.path.join(temporal, archivo)
            with open(ruta_cifrado, 'wb') as handle:
                handle.write(cifrado)
            try:
                objeto = _subir_privado(ruta_cifrado, archivo)
            except Exception as exc:
                objeto = None
                manifiesto['motivo_datos'] = 'El almacén privado falló (%s). El cifrado queda en el release.' % type(exc).__name__
                info['motivo_datos'] = manifiesto['motivo_datos']
            if objeto:
                manifiesto['almacen'] = 'privado'
                manifiesto['objeto'] = objeto
                info['almacen'] = 'privado'
                info['objeto'] = objeto
                with open(ruta_manifiesto, 'w', encoding='utf-8') as handle:
                    json.dump(manifiesto, handle, ensure_ascii=False, indent=1)
            else:
                archivos.append(ruta_cifrado)
        notas = notas_release(info, repo_slug)
        titulo = titulo_release(info)
        if nombre not in previas and not etiqueta_existente:
            _git(repo, 'tag', '-a', nombre, sha, '-F', '-', entrada=mensaje_etiqueta(info).encode('utf-8'))
        if not empujar:
            print('Etiqueta local %s. Para publicarla en GitHub hace falta --empujar.' % nombre)
            return 0
        _empujar_etiqueta(repo, nombre)
        if not _release_existe(nombre):
            _crear_release(nombre, titulo, notas, archivos, repo)
        elif ruta_cifrado and manifiesto.get('almacen') != 'privado':
            _subir_asset(nombre, ruta_cifrado, repo)
            _subir_asset(nombre, ruta_manifiesto, repo)
        elif solo_datos or ruta_cifrado:
            _subir_asset(nombre, ruta_manifiesto, repo)
        print('Respaldo %s · %s · %s' % (nombre, info['fecha_real'], info['fecha_juego']))
        return 0
    finally:
        for nombre_archivo in os.listdir(temporal):
            os.remove(os.path.join(temporal, nombre_archivo))
        os.rmdir(temporal)


def _descargar(etiqueta, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    manifiesto = os.path.join(carpeta, 'manifiesto.json')
    try:
        _ejecutar([
            'gh', 'release', 'download', etiqueta, '--pattern', 'manifiesto.json',
            '--dir', carpeta, '--clobber',
        ])
    except RuntimeError:
        pass
    datos = {}
    if os.path.isfile(manifiesto):
        datos = _leer_json(manifiesto) or {}
    if datos.get('almacen') == 'privado' and datos.get('objeto'):
        destino = os.path.join(carpeta, datos.get('archivo') or 'saimon-datos.lifebak')
        return _bajar_privado(datos['objeto'], destino)
    _ejecutar([
        'gh', 'release', 'download', etiqueta, '--pattern', '*.lifebak',
        '--dir', carpeta, '--clobber',
    ])
    encontrados = [
        os.path.join(carpeta, nombre) for nombre in os.listdir(carpeta) if nombre.endswith('.lifebak')
    ]
    if not encontrados:
        raise RuntimeError(
            'Esa etiqueta no tiene copia de la base. Revisa BACKUP_PASSPHRASE y DATABASE_URL, y vuelve a correr el workflow con «solo datos».'
        )
    return encontrados[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description='Respaldos de Saimon City.')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_listar = sub.add_parser('listar', help='Muestra los respaldos por fecha real y año de juego.')
    p_listar.add_argument('--repo', default='.')

    p_publicar = sub.add_parser('publicar', help='Crea la etiqueta y el release. Lo usa GitHub Actions.')
    p_publicar.add_argument('--repo', default='.')
    p_publicar.add_argument('--sha', default='')
    p_publicar.add_argument('--evento', default='')
    p_publicar.add_argument('--evento-nombre', default='')
    p_publicar.add_argument('--linea-base', action='store_true')
    p_publicar.add_argument('--solo-datos', action='store_true')
    p_publicar.add_argument('--resumen', default='')
    p_publicar.add_argument('--etiqueta', default='')
    p_publicar.add_argument('--empujar', action='store_true')

    p_codigo = sub.add_parser('codigo', help='Deja esa versión en una carpeta nueva, sin mover main.')
    p_codigo.add_argument('--etiqueta', required=True)
    p_codigo.add_argument('--carpeta', default='')
    p_codigo.add_argument('--repo', default='.')

    p_restaurar = sub.add_parser('restaurar', help='Abre una copia de los datos en otra carpeta o en otra base.')
    p_restaurar.add_argument('--etiqueta', default='')
    p_restaurar.add_argument('--archivo', default='')
    p_restaurar.add_argument('--destino', default='')
    p_restaurar.add_argument('--database-url', default='')
    p_restaurar.add_argument('--produccion', action='store_true')
    p_restaurar.add_argument('--reemplazar', action='store_true')
    p_restaurar.add_argument('--repo', default='.')

    args = parser.parse_args(argv)
    try:
        if args.cmd == 'listar':
            sys.stdout.write(formato_lista(listar(args.repo)))
            return 0
        if args.cmd == 'publicar':
            return publicar(
                repo=args.repo,
                sha=args.sha,
                manual=args.linea_base or args.solo_datos,
                linea_base=args.linea_base,
                solo_datos=args.solo_datos,
                resumen_manual=args.resumen,
                evento_path=args.evento,
                evento_nombre=args.evento_nombre,
                empujar=True if args.empujar or os.environ.get('GITHUB_ACTIONS') == 'true' else False,
                etiqueta_existente=args.etiqueta,
            )
        if args.cmd == 'codigo':
            carpeta = args.carpeta or os.path.join('restauracion', args.etiqueta)
            preparar_codigo(args.etiqueta, carpeta, args.repo)
            print('Código en %s. main no se movió.' % carpeta)
            print('Para jugar esa copia: cd %s && python3 server.py --host 127.0.0.1 --port 8766' % carpeta)
            return 0
        archivo = args.archivo
        if not archivo:
            if not args.etiqueta:
                raise RuntimeError('Indica --archivo o --etiqueta.')
            archivo = _descargar(args.etiqueta, tempfile.mkdtemp(prefix='bajar-respaldo-'))
        destino = args.destino
        if not destino and not args.database_url:
            if not args.etiqueta:
                raise RuntimeError('Indica --destino, --database-url o --etiqueta.')
            destino = os.path.join('restauracion', args.etiqueta, 'state')
        frase = frase_actual()
        hecho = restaurar(
            archivo, destino, frase,
            database_url=args.database_url,
            produccion=args.produccion,
            reemplazar=args.reemplazar,
            repo=args.repo if args.repo != '.' else ROOT,
        )
        print('Datos restaurados: %s' % ', '.join(hecho))
        print('La ciudad en https://lifein.onrender.com no se tocó.')
        return 0
    except (RuntimeError, ValueError) as exc:
        print(ocultar(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
