# SPDX-License-Identifier: AGPL-3.0-or-later
"""HTTP de mundos, feedback y el poste. El juego en vivo sigue por el WebSocket."""
import json

import mundos
import social


def _body(raw):
    if not raw:
        return {}
    data = json.loads(raw.decode('utf-8') if isinstance(raw, bytes) else raw)
    if not isinstance(data, dict):
        raise ValueError('Se espera un objeto JSON')
    return data


def dispatch(method, path, headers, body, ctx):
    path = (path or '').rstrip('/') or '/'
    if path != '/api/mundos' and not path.startswith('/api/vida'):
        return None
    headers = {str(k).lower(): v for k, v in (headers or {}).items()}
    state = ctx['state']
    try:
        if path == '/api/mundos' and method in ('GET', 'HEAD'):
            return 200, mundos.public_worlds(ctx['clients'].values())
        if path == '/api/vida/feedback' and method == 'POST':
            payload = _body(body)
            result = social.add_feedback(
                state, str(payload.get('nick') or 'Viajero')[:16], payload.get('text'),
                payload.get('world'), str(payload.get('place') or '')[:40],
            )
            if result.get('ok'):
                ctx['save']()
            return (200 if result.get('ok') else 400), result
        admin = headers.get('x-simon-admin', '')
        role = social.role_of(None, admin)
        if path == '/api/vida/admin/feedback' and method in ('GET', 'HEAD'):
            if not social.allows(role, 'see_feedback'):
                return 403, {'error': 'No autorizado.'}
            return 200, {'feedback': list(state.get('feedback') or [])}
        if path == '/api/vida/admin/poste' and method in ('GET', 'HEAD'):
            if not social.allows(role, 'see_feedback'):
                return 403, {'error': 'No autorizado.'}
            board = social.public_notes(state)
            board['hiddenNotes'] = [row for row in state.get('notes') or [] if row.get('hidden')]
            board['hiddenPolls'] = [row for row in state.get('polls') or [] if row.get('hidden')]
            return 200, board
        if path == '/api/vida/admin/poste' and method == 'POST':
            payload = _body(body)
            result = social.moderate(
                state, role, payload.get('kind'), payload.get('id'), payload.get('action'), payload.get('text'),
            )
            if result.get('ok'):
                ctx['save']()
            return (200 if result.get('ok') else 403), result
        return 404, {'error': 'no existe'}
    except (ValueError, json.JSONDecodeError):
        return 400, {'error': 'El JSON no se pudo leer.'}
