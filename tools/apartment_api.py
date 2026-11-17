# SPDX-License-Identifier: AGPL-3.0-or-later
"""Rutas sin efectos de escritura. La sincronización es un comando privado del operador."""
import json
from urllib.parse import parse_qs, urlsplit
import apartments as A

AGENT_PATHS = {'/api/simon-ia/apartamentos': 'simon-ia', '/api/simon-io/apartamentos': 'simon-io'}


def dispatch(method, path, target, body=b'', index=None):
    if not (path.startswith('/api/apartamentos') or path in AGENT_PATHS):
        return None
    try:
        if method not in ('GET', 'HEAD', 'POST'):
            return 405, {'error': 'Método no permitido'}
        if path not in ('/api/apartamentos', '/api/apartamentos/fuentes', *AGENT_PATHS):
            return 404, {'error': 'Ruta desconocida'}
        if path in AGENT_PATHS and method != 'POST' or path not in AGENT_PATHS and method == 'POST':
            return 405, {'error': 'Método no permitido'}
        if method == 'POST':
            payload = json.loads(body.decode('utf-8'))
            if not isinstance(payload, dict) or not isinstance(payload.get('filters', {}), dict):
                raise ValueError('Se espera un objeto JSON y filters como objeto')
        else:
            payload = {k: v[-1] for k, v in parse_qs(urlsplit(target).query).items()}
        index = index or A.Index()
        if path == '/api/apartamentos/fuentes':
            return 200, {'sources': index.status(), 'municipalities': A.MUNICIPALITIES}
        if path in AGENT_PATHS:
            return 200, A.agent_search(index, AGENT_PATHS[path], payload.get('message', ''), payload.get('filters'))
        return 200, index.search(payload)
    except (ValueError, TypeError, OverflowError, UnicodeError):
        return 400, {'error': 'No se pudo leer la petición.'}
    except Exception:
        return 503, {'error': 'El índice no está disponible. Intenta más tarde.'}
