# SPDX-License-Identifier: AGPL-3.0-or-later
"""HTTP de Simon: chat, ritmo, consentimiento, reseñas y vista previa sin fotos."""
import hmac
import json
import os
import re
from urllib.parse import parse_qs, urlsplit

import apartments as A
import apartment_sync as SYNC
import simon_agent as AGENT
import simon_memory as MEM

AGENT_CHAT = {
    '/api/simon/mensaje': 'simon-ia',
    '/api/simon-ia/mensaje': 'simon-ia',
    '/api/simon-io/mensaje': 'simon-io',
    '/api/simon/ia/mensaje': 'simon-ia',
    '/api/simon/io/mensaje': 'simon-io',
}
EPHEMERAL = {}


def notice():
    return {
        'version': MEM.NOTICE_VERSION,
        'titulo': 'Simon guarda la conversación sólo si aceptas',
        'texto': (
            'Responsable: Juan Simón Barrera Jaramillo, Saimon City / Life Inc, Medellín. '
            'Finalidad: recordar la conversación, el ritmo que prefieres y, si dejas una reseña, mejorar las respuestas. '
            'Se cifra en reposo. En tránsito el sitio público usa HTTPS. '
            'Puedes negarte, seguir hablando sin que se guarde, y borrar lo guardado cuando quieras. '
            'Correo: saimon888oficial@gmail.com. Base legal: Ley 1581 de 2012.'
        ),
    }


def _subject(headers):
    cookies = headers.get('cookie', '')
    found = re.search(r'(?:^|;\s*)simon_sujeto=([0-9a-f]{32})', cookies)
    if found:
        return found.group(1), None
    ident = os.urandom(16).hex()
    secure = '; Secure' if os.environ.get('SIMON_COOKIE_SECURE', '') == '1' else ''
    cookie = f'simon_sujeto={ident}; HttpOnly; SameSite=Lax; Path=/; Max-Age=15552000{secure}'
    return ident, cookie


def _slot(subject, conversation_id):
    return EPHEMERAL.setdefault((subject, conversation_id), {'urls': [], 'opened': []})


def remember_urls(subject, conversation_id, urls):
    slot = _slot(subject, conversation_id)
    for url in urls or []:
        if url not in slot['urls']:
            slot['urls'].append(url)


def opened_links(store, subject, conversation_id):
    links = list(_slot(subject, conversation_id)['opened'])
    row = store.conversation(subject, conversation_id) if store.allows(subject) else None
    for url in (row or {}).get('opened') or []:
        if url not in links:
            links.append(url)
    return links


def known_urls(store, subject, conversation_id, index):
    known = set(_slot(subject, conversation_id)['urls'])
    row = store.conversation(subject, conversation_id) if subject else None
    known.update((row or {}).get('urls') or [])
    return known


def track_open(store, subject, conversation_id, url):
    known = known_urls(store, subject, conversation_id, None)
    if url not in known:
        return False
    slot = _slot(subject, conversation_id)
    if url not in slot['opened']:
        slot['opened'].append(url)
    if store.allows(subject):
        row = store.conversation(subject, conversation_id) or {'id': conversation_id, 'urls': list(known), 'opened': []}
        opened = list(row.get('opened') or [])
        if url not in opened:
            opened.append(url)
        row['opened'] = opened
        row['urls'] = list(dict.fromkeys(list(row.get('urls') or []) + list(known)))
        store.remember_conversation(subject, row)
    return True


def _admin(headers):
    expected = os.environ.get('SIMON_ADMIN_TOKEN', '').strip()
    got = headers.get('x-simon-admin', '')
    if expected and len(got) == len(expected) and hmac.compare_digest(got, expected):
        return True, None
    return False, 'No autorizado.'


def _json_body(body):
    if not body:
        return {}
    payload = json.loads(body.decode('utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('Se espera un objeto JSON')
    return payload


def _excerpt(html):
    text = re.sub(r'(?is)<script[\s\S]*?</script>', ' ', html)
    text = re.sub(r'(?is)<style[\s\S]*?</style>', ' ', text)
    text = re.sub(r'(?is)<img\b[^>]*>', ' ', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:700]


def preview(url, index):
    host = urlsplit(url).hostname
    fetcher = SYNC.Fetcher([host], delay=0)
    try:
        body, final = fetcher.public(url)
    except Exception as exc:
        return {'ok': False, 'notice': 'No pude leer una vista previa. El enlace original sigue disponible.',
                'reason': type(exc).__name__}
    return {'ok': True, 'url': final, 'excerpt': _excerpt(body),
            'notice': 'Vista en texto. No se copian fotos.'}


def _feedback_payload(store, subject, payload):
    conversation_id = str(payload.get('conversation_id') or '')
    if not re.fullmatch(r'[0-9a-f]{8,64}', conversation_id):
        raise ValueError('Falta la conversación')
    resolution = payload.get('resolution')
    if resolution not in ('si', 'parcialmente', 'no'):
        raise ValueError('La solución se responde con sí, parcialmente o no')
    visibility = payload.get('visibility')
    if visibility not in ('publica', 'privada'):
        raise ValueError('Indica si la reseña es pública o privada')
    rating = payload.get('rating', None)
    if rating in ('', None):
        rating = None
    else:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError('La valoración va de 1 a 5, o puedes omitirla')
    comment = str(payload.get('comment') or '').strip()[:800]
    declared = payload.get('declared_opened')
    if declared not in (True, False):
        raise ValueError('Cuéntame si abriste un enlace: sí o no')
    links = opened_links(store, subject, conversation_id)
    record = {
        'conversation_id': conversation_id,
        'created_at': A.timestamp(),
        'links_opened': links,
        'declared_opened': declared,
        'opened_link': bool(links) or declared,
        'resolution': resolution,
        'solved': resolution == 'si',
        'rating': rating,
        'comment': comment,
        'visibility': visibility,
    }
    store.save_feedback(subject, record)
    if resolution == 'si':
        hosts = []
        for link in links:
            host = urlsplit(link).hostname
            if host and host not in hosts:
                hosts.append(host)
        text = 'Caso marcado como resuelto.'
        if hosts:
            text += ' Se abrieron enlaces de: ' + ', '.join(hosts) + '.'
        if visibility == 'publica' and comment:
            text += ' Comentario público: ' + comment
        store.save_case(subject, {'title': 'Caso resuelto', 'text': text, 'tags': ['caso', 'resuelto', 'apartamento']})
    return record


def dispatch(method, path, target, headers, body=b'', store=None, index=None):
    path = path.rstrip('/') or '/'
    if not (path.startswith('/api/simon') or path in AGENT_CHAT):
        return None
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    subject, cookie = _subject(headers)
    extra = {'Set-Cookie': cookie} if cookie else {}
    store = store or MEM.Store()
    index = index or A.Index()
    try:
        if method not in ('GET', 'HEAD', 'POST', 'DELETE'):
            return 405, {'error': 'Método no permitido'}, extra
        if path in AGENT_CHAT:
            if method != 'POST':
                return 405, {'error': 'Método no permitido'}, extra
            payload = _json_body(body)
            settings = payload.get('settings') if isinstance(payload.get('settings'), dict) else None
            result = AGENT.answer(
                payload.get('message', ''), agent=AGENT_CHAT[path], subject=subject, store=store, index=index,
                settings=settings, typing_ms=payload.get('typing_ms'), speech_wpm=payload.get('speech_wpm'),
                conversation_id=payload.get('conversation_id') or None,
            )
            remember_urls(subject, result['conversation_id'], result.get('urls'))
            result['privacy'] = notice()
            return 200, result, extra
        if path == '/api/simon/consentimiento' and method == 'GET':
            current = store.consent(subject)
            return 200, {'notice': notice(), 'accepted': bool(current), 'consent': current}, extra
        if path == '/api/simon/consentimiento' and method == 'POST':
            payload = _json_body(body)
            if not isinstance(payload.get('accepted'), bool):
                raise ValueError('accepted debe ser verdadero o falso')
            store.set_consent(subject, payload['accepted'], A.timestamp())
            if payload['accepted'] is False:
                store.delete_subject(subject)
                store.set_consent(subject, False, A.timestamp())
            return 200, {'accepted': payload['accepted'], 'notice': notice()}, extra
        if path == '/api/simon/datos' and method == 'DELETE':
            removed = store.delete_subject(subject)
            return 200, {'deleted': removed, 'message': 'Listo. Borré lo que Simon tenía de esta sesión.'}, extra
        if path == '/api/simon/ritmo' and method == 'GET':
            saved = store.pace(subject) if store.allows(subject) else None
            return 200, {'settings': saved or AGENT.defaults_pace(), 'stored': bool(saved)}, extra
        if path == '/api/simon/ritmo' and method == 'POST':
            payload = _json_body(body)
            voz = float(payload.get('voz', 0.92))
            pausa = int(payload.get('pausa_ms', 800))
            if not 0.7 <= voz <= 1.15 or not 0 <= pausa <= 4000:
                raise ValueError('La voz va de 0.7 a 1.15 y la pausa de 0 a 4000 ms')
            settings = {'voz': round(voz, 2), 'pausa_ms': pausa,
                        'por_partes': bool(payload.get('por_partes', True)),
                        'adaptar': bool(payload.get('adaptar', True))}
            stored = False
            if store.allows(subject):
                store.set_pace(subject, settings)
                stored = True
            return 200, {'settings': settings, 'stored': stored, 'pace': AGENT.plan_pace(settings)}, extra
        if path == '/api/simon/enlace' and method == 'POST':
            payload = _json_body(body)
            url = str(payload.get('url') or '')
            conversation_id = str(payload.get('conversation_id') or '')
            if not track_open(store, subject, conversation_id, url):
                return 400, {'error': 'Ese enlace no salió de esta conversación'}, extra
            return 200, {'ok': True, 'opened': opened_links(store, subject, conversation_id)}, extra
        if path == '/api/simon/feedback' and method == 'POST':
            payload = _json_body(body)
            if payload.get('accept_storage') is True:
                store.set_consent(subject, True, A.timestamp())
            if not store.allows(subject):
                return 409, {'error': 'Para guardar la reseña hace falta tu consentimiento. Puedes enviarla otra vez marcando que aceptas, o no guardarla.',
                             'notice': notice()}, extra
            record = _feedback_payload(store, subject, payload)
            public = {k: record[k] for k in ('created_at', 'resolution', 'rating', 'visibility')}
            return 200, {'saved': True, 'review': public,
                         'message': 'Gracias. Quedó guardada. Si prefieres que no esté, puedes borrar tus datos.'}, extra
        if path == '/api/simon/resenas' and method in ('GET', 'HEAD'):
            rows = [MEM.public_review(row) for row in store.feedback() if row.get('visibility') == 'publica']
            rows.sort(key=lambda row: row.get('created_at') or '', reverse=True)
            return 200, {'reviews': rows}, extra
        if path == '/api/simon/admin/resenas' and method in ('GET', 'HEAD'):
            ok, why = _admin(headers)
            if not ok:
                return 403, {'error': why}, extra
            query = {k: v[-1] for k, v in parse_qs(urlsplit(target).query).items()}
            rows = MEM.filter_feedback(store.feedback(), query)
            rows.sort(key=lambda row: row.get('created_at') or '', reverse=True)
            safe = []
            for row in rows:
                safe.append({key: row.get(key) for key in (
                    'conversation_id', 'created_at', 'links_opened', 'declared_opened', 'opened_link',
                    'resolution', 'solved', 'rating', 'comment', 'visibility',
                )})
            return 200, {'reviews': safe, 'stats': MEM.stats(store.feedback(), store.conversations()),
                         'filters': query}, extra
        if path == '/api/simon/vista' and method in ('GET', 'HEAD'):
            query = {k: v[-1] for k, v in parse_qs(urlsplit(target).query).items()}
            url = query.get('url') or ''
            conversation_id = query.get('conversation_id') or ''
            allowed = url in known_urls(store, subject, conversation_id, index) or index.has_url(url)
            if not allowed:
                return 403, {'error': 'Sólo puedo previsualizar un enlace que Simon acaba de mostrar.'}, extra
            return 200, preview(url, index), extra
        if path == '/api/simon/aviso' and method in ('GET', 'HEAD'):
            return 200, notice(), extra
        return 404, {'error': 'Ruta desconocida'}, extra
    except (ValueError, TypeError, OverflowError, UnicodeError) as exc:
        return 400, {'error': str(exc)}, extra
    except Exception:
        return 503, {'error': 'Simon no pudo completar eso. Intenta de nuevo en un momento.'}, extra
