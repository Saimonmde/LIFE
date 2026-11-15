# SPDX-License-Identifier: AGPL-3.0-or-later
"""Simon IA / Simon IO. Llama herramientas; no inventa anuncios ni apura a nadie."""
import json
import os
import re
import urllib.request
import uuid

import apartments as A
import apartment_sync as SYNC
import simon_memory as MEM
import web_search as WEB

ROOT = A.ROOT
BANNED = (
    'aprovecha', 'ultima oportunidad', 'ultimas unidades', 'se acaban', 'decidete',
    'no esperes', 'urgente', 'solo por hoy', 'corre que', 'quedan pocos',
    'oferta relampago', 'imperdible', 'apurate', 'apresurate', 'no te quedes',
)
OPS = {
    'arriendo': 'Arriendo', 'venta': 'Venta', 'renta_corta': 'Renta corta',
}
STAY_LABEL = {
    'dias': 'días', 'semanas': 'semanas', 'meses_3': '3 meses', 'meses_6': '6 meses',
    'meses_12': '12 meses', 'mensual': 'mes a mes',
}
FEEDBACK_INTRO = (
    'Cuando quieras cerramos aquí. No hay prisa ni ninguna decisión pendiente. '
    'Si te sirve, cuéntame con calma: ¿abriste algún enlace externo durante el chat? '
    '¿Encontraste una solución a lo que buscabas: sí, parcialmente o no? '
    'La valoración de 1 a 5 y el comentario son opcionales. '
    'También puedes decir si la reseña puede mostrarse en público o si prefieres dejarla privada.'
)


def system_prompt():
    path = ROOT / 'data' / 'simon' / 'sistema.md'
    return path.read_text(encoding='utf-8')


def defaults_pace():
    return {'voz': 0.92, 'pausa_ms': 800, 'por_partes': True, 'adaptar': True}


def plan_pace(settings, typing_ms=None, speech_wpm=None):
    settings = {**defaults_pace(), **(settings or {})}
    cap = min(1.15, max(0.7, float(settings.get('voz') or 0.92)))
    pause = min(4000, max(0, int(settings.get('pausa_ms') or 800)))
    parts = bool(settings.get('por_partes', True))
    rate = cap
    if settings.get('adaptar', True):
        if typing_ms is not None:
            gap = float(typing_ms)
            if gap > 220:
                rate = min(rate, 0.84)
                pause = max(pause, 1200)
            elif gap < 90:
                pause = max(400, pause)
        if speech_wpm is not None and float(speech_wpm) < 120:
            rate = min(rate, 0.82)
            pause = max(pause, 1300)
    rate = min(cap, max(0.7, rate))
    return {'voice_rate': round(rate, 2), 'delay_ms': pause, 'chunk_ms': pause if parts else 0,
            'por_partes': parts}


def _clean(text):
    folded = A.folded(text)
    if any(word in folded for word in BANNED):
        return 'Puedo seguir con calma cuando quieras. No hace falta decidir ahora.'
    return text


def chunks_of(text):
    parts = [part.strip() for part in re.split(r'(?<=[.!?])\s+', text or '') if part.strip()]
    return parts or [text or '']


def interpret(text):
    """Lee la petición. No llama al índice."""
    folded = A.folded(text)
    if any(phrase in folded for phrase in ('terminar', 'cerrar conversacion', 'eso es todo', 'cerrar el chat')):
        return {'end': True}
    if 'borra' in folded and any(word in folded for word in ('datos', 'conversacion', 'memoria', 'reseña', 'resena')):
        return {'delete': True}
    housing = any(word in folded for word in (
        'apartamento', 'apartamentos', 'arriendo', 'alquiler', 'arrendar', 'venta', 'comprar',
        'renta corta', 'vacacional', 'inmueble', 'habitacion', 'alcoba',
    ))
    if not housing:
        return {'kind': 'general'}
    sale = any(word in folded for word in ('venta', 'comprar', 'compra'))
    short = any(word in folded for word in ('renta corta', 'por dias', 'vacacional', 'por semanas', 'arriendo temporal'))
    rent = any(word in folded for word in ('arriendo', 'alquiler', 'arrendar'))
    months = None
    for label, token in (('3', 'meses_3'), ('6', 'meses_6'), ('12', 'meses_12')):
        if re.search(r'\b' + label + r'\s+meses\b', folded):
            months = token
    if months:
        short = True
    if sale and (rent or short):
        return {'clarify': '¿Lo buscas en arriendo, en venta o en renta corta? Con una sola opción te muestro lo publicado, sin prisa.'}
    filters = {}
    cities = [city for city in A.MUNICIPALITIES if re.search(r'(?<!\w)' + re.escape(A.folded(city)) + r'(?!\w)', folded)]
    if len(cities) > 1:
        return {'clarify': 'Puedo mirar un municipio por vez. ¿Cuál de ellos te interesa?'}
    if cities:
        filters['municipality'] = cities[0]
    if sale:
        filters['operation'] = 'venta'
        filters['price_basis'] = 'sale'
    elif short:
        filters['operation'] = 'renta_corta'
        if 'por semana' in folded:
            filters['stay'] = 'semanas'
            filters['price_basis'] = 'week'
        elif months:
            filters['stay'] = months
            filters['price_basis'] = 'month'
        else:
            filters['stay'] = 'dias'
            filters['price_basis'] = 'day'
    elif rent:
        filters['operation'] = 'arriendo'
        filters['price_basis'] = 'month'
    for pattern, key in ((r'(\d+)\s*(?:habitaciones|alcobas|cuartos)', 'min_bedrooms'),
                         (r'(\d+)\s*banos', 'min_bathrooms'),
                         (r'(\d+(?:[,.]\d+)?)\s*(?:m2|metros)', 'min_area_m2')):
        found = re.search(pattern, folded)
        if found:
            filters[key] = A.number(found.group(1))
    found = re.search(r'(?:hasta|maximo|presupuesto(?: de)?|menos de|tope(?: de)?)\s*\$?\s*([\d.,]+)\s*(millones?|millon|mil)?', folded)
    if found:
        amount = A.number(found.group(1))
        unit = found.group(2) or ''
        if amount is not None:
            filters['max_price'] = int(amount * (1000000 if unit.startswith('millon') else 1000 if unit == 'mil' else 1))
    neighborhood = re.search(r'(?:barrio|sector)\s+([a-z ]+?)(?=\s+(?:hasta|con|maximo|presupuesto|de \d)|[,.;]|$)', folded)
    if neighborhood:
        filters['neighborhood'] = neighborhood.group(1).strip()
    return {'kind': 'apartments', 'filters': filters}


def search_apartments(index, filters):
    return index.search(filters)


def card_of(row):
    return {key: row.get(key) for key in (
        'operation', 'municipality', 'neighborhood', 'area_m2', 'bedrooms', 'bathrooms',
        'price', 'price_day', 'price_week', 'price_month', 'price_sale', 'stay_types',
        'source', 'source_name', 'original_url', 'checked_at', 'title', 'publications',
    )}


def _money(value):
    if value is None:
        return None
    return f'{int(value):,}'.replace(',', '.')


def _price_phrase(row):
    op = row.get('operation') or 'arriendo'
    if op == 'venta' and row.get('price_sale'):
        return _money(row['price_sale']) + ' pesos en venta'
    if row.get('price_day'):
        return _money(row['price_day']) + ' pesos por día'
    if row.get('price_week'):
        return _money(row['price_week']) + ' pesos por semana'
    if row.get('price_month'):
        return _money(row['price_month']) + ' pesos al mes'
    return _money(row.get('price')) + ' pesos'


def compose_apartments(result, filters, loosened):
    total = result.get('total') or 0
    city = filters.get('municipality') or 'el Valle de Aburrá'
    names = {
        'arriendo': 'arriendo' if total == 1 else 'arriendos',
        'venta': 'venta' if total == 1 else 'ventas',
        'renta_corta': 'renta corta' if total == 1 else 'rentas cortas',
    }
    op = names.get(filters.get('operation') or '', 'publicaciones')
    if not total:
        return (
            f'No encontré publicaciones recientes de {op} en {city} dentro del índice. '
            'Eso no quiere decir que no existan: alguna fuente puede estar sin configurar o haber cambiado su página. '
            'Si quieres, miro otro municipio o otro tipo de oferta. No hace falta decidir nada ahora.'
        )
    lines = [f'Encontré {total} {op} en {city}, con lo que está publicado ahora. Puedes abrir la ficha original cuando quieras.']
    if loosened:
        lines.append('Ningún anuncio leído declara ese plazo. Te muestro lo publicado y el contrato se confirma con quien anuncia. No asumo que acepten renta corta.')
    for row in result['results'][:3]:
        place = row['municipality'] + ((' · ' + row['neighborhood']) if row.get('neighborhood') else '')
        facts = [place, _price_phrase(row)]
        if row.get('bedrooms') is not None:
            beds = int(row['bedrooms'])
            facts.append(f"{beds} habitación" if beds == 1 else f"{beds} habitaciones")
        if row.get('area_m2') is not None:
            area = row['area_m2']
            if float(area) == int(float(area)):
                area = int(float(area))
            facts.append(f"{area} m²")
        lines.append(' · '.join(facts) + f". Fuente: {row.get('source_name')}.")
    if total > 3:
        lines.append('Hay más fichas en las tarjetas, cada una con su enlace.')
    return ' '.join(lines)


def compose_general(text, knowledge, web):
    parts = []
    if knowledge:
        parts.append(knowledge[0].get('text') or '')
        parts.append('Esto sale de la base de Saimon City y RentoCity.')
    if web and web.get('results'):
        first = web['results'][0]
        parts.append(f"También encontré «{first.get('title')}». Dejo el enlace para que lo abras si quieres.")
        if web.get('notice'):
            parts.append(web['notice'])
    elif web and web.get('notice') and not knowledge:
        parts.append(web['notice'])
    if not parts:
        parts.append('Puedo buscarlo en la web o en los apartamentos del Valle. Dime el municipio y si es arriendo, venta o renta corta, con la calma que necesites.')
    return ' '.join(parts)


def _phrase(fallback, payload, allowed_urls):
    key = os.environ.get('SIMON_LLM_API_KEY', '').strip()
    if not key:
        return fallback
    base = (os.environ.get('SIMON_LLM_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')
    model = os.environ.get('SIMON_LLM_MODEL') or 'gpt-4o-mini'
    body = json.dumps({
        'model': model,
        'temperature': 0.2,
        'messages': [
            {'role': 'system', 'content': system_prompt()},
            {'role': 'user', 'content': 'Redacta una respuesta breve en español, sin prisa, usando sólo este JSON:\n' + json.dumps(payload, ensure_ascii=False)[:8000]},
        ],
    }).encode()
    req = urllib.request.Request(base + '/chat/completions', data=body, headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read(200000).decode())
        text = data['choices'][0]['message']['content']
    except Exception:
        return fallback
    for url in re.findall(r'https://[^\s)]+', text or ''):
        if url.rstrip('.,') not in allowed_urls:
            return fallback
    return _clean(text)


def answer(text, agent='simon-ia', subject=None, store=None, index=None, settings=None,
           typing_ms=None, speech_wpm=None, conversation_id=None, live=None):
    if agent not in ('simon-ia', 'simon-io'):
        raise ValueError('Agente desconocido')
    if not isinstance(text, str) or not text.strip() or len(text) > 2000:
        raise ValueError('Petición inválida')
    store = store or MEM.Store()
    index = index or A.Index()
    saved = store.pace(subject) if subject else None
    merged = defaults_pace()
    if saved:
        merged.update({key: saved[key] for key in ('voz', 'pausa_ms', 'por_partes', 'adaptar') if key in saved})
    if settings:
        merged.update({key: settings[key] for key in ('voz', 'pausa_ms', 'por_partes', 'adaptar') if key in settings})
    pace = plan_pace(merged, typing_ms, speech_wpm)
    if subject and store.allows(subject) and settings:
        store.set_pace(subject, merged)
    conversation_id = conversation_id or uuid.uuid4().hex
    consented = bool(subject and store.allows(subject))
    intent = interpret(text)
    tools = []
    cards = []
    citations = []
    urls = []
    notice = None
    if intent.get('end'):
        message = FEEDBACK_INTRO
        feedback = True
    elif intent.get('delete'):
        removed = store.delete_subject(subject) if subject else 0
        message = f'Borré {removed} registros de esta conversación en el servidor. Si el navegador guardó algo, también puedes limpiar los datos del sitio.'
        feedback = False
        consented = False
    elif intent.get('clarify'):
        message = intent['clarify']
        feedback = False
    elif intent.get('kind') == 'apartments':
        filters = dict(intent.get('filters') or {})
        if live is None:
            live = os.environ.get('SIMON_LIVE_SEARCH', '1') != '0'
        refresh = SYNC.refresh_for_query(index, filters) if live else {'skipped': True}
        tools.append({'name': 'search_apartments', 'filters': filters, 'refresh': refresh})
        loosened = False
        result = search_apartments(index, filters)
        if result.get('total') == 0 and (filters.get('stay') or filters.get('price_basis') in ('day', 'week')):
            loose = dict(filters)
            loose.pop('stay', None)
            loose.pop('price_basis', None)
            result = search_apartments(index, loose)
            loosened = True
            tools.append({'name': 'search_apartments', 'filters': loose, 'note': 'sin estancia estricta'})
        cards = [card_of(row) for row in result.get('results') or []]
        for card in cards:
            if card.get('original_url'):
                urls.append(card['original_url'])
        message = compose_apartments(result, filters, loosened)
        notice = result.get('notice')
        allowed = set(urls)
        message = _phrase(message, {'filters': filters, 'results': cards, 'notice': notice}, allowed)
        feedback = False
    else:
        knowledge = store.recall(text, subject if consented else None)
        tools.append({'name': 'recall_knowledge', 'hits': [doc.get('id') for doc in knowledge]})
        internal = any(word in A.folded(text) for word in ('rentocity', 'simon', 'pendiente', 'life inc', 'saimon'))
        web = {'results': [], 'notice': None}
        if not internal or not knowledge:
            web = WEB.search(text)
            tools.append({'name': 'web_search', 'provider': web.get('provider'), 'ok': web.get('ok')})
            for row in web.get('results') or []:
                citations.append(row)
                if row.get('url'):
                    urls.append(row['url'])
        message = compose_general(text, knowledge, web)
        message = _phrase(message, {'knowledge': knowledge, 'web': citations}, set(urls))
        feedback = False
    message = _clean(message)
    if consented and subject and not intent.get('delete'):
        prior = store.conversation(subject, conversation_id) or {'id': conversation_id, 'urls': [], 'opened': []}
        known = list(dict.fromkeys(list(prior.get('urls') or []) + urls))
        store.remember_conversation(subject, {
            'id': conversation_id, 'agent': agent, 'urls': known, 'opened': prior.get('opened') or [],
        })
        store.put('message', subject, {
            'id': 'msg-' + uuid.uuid4().hex, 'conversation_id': conversation_id,
            'role': 'user', 'text': text,
        })
        store.put('message', subject, {
            'id': 'msg-' + uuid.uuid4().hex, 'conversation_id': conversation_id,
            'role': 'simon', 'text': message, 'urls': urls,
        })
    return {
        'agent': agent, 'message': message, 'chunks': chunks_of(message), 'pace': pace,
        'cards': cards, 'citations': citations, 'tools': tools, 'conversation_id': conversation_id,
        'consent': consented, 'feedback': feedback, 'notice': notice, 'urls': urls,
        'memory_key_configured': MEM.key_is_configured(),
    }
