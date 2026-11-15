# SPDX-License-Identifier: AGPL-3.0-or-later
"""Memoria de Simon: cifrada en reposo, con consentimiento y borrado (Ley 1581 de 2012)."""
from contextlib import contextmanager
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTICE_VERSION = '2026-11-15'
SALT = b'simon-city-memoria-v1'
_DERIVED = {}


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value or '').lower())
                   if not unicodedata.combining(c))


def tokens(value):
    return set(re.findall(r'[a-z0-9]{4,}', folded(value)))


def resolve_key(explicit=None):
    if explicit:
        return str(explicit)
    env = os.environ.get('SIMON_DATA_KEY', '').strip()
    if env:
        return env
    path = ROOT / 'state' / 'simon-data.key'
    if path.is_file():
        return path.read_text(encoding='utf-8').strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    path.write_text(key, encoding='utf-8')
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


def key_is_configured():
    return bool(os.environ.get('SIMON_DATA_KEY', '').strip())


def _keys(secret):
    cached = _DERIVED.get(secret)
    if cached:
        return cached
    raw = hashlib.scrypt(str(secret).encode(), salt=SALT, n=2 ** 14, r=8, p=1, dklen=64)
    _DERIVED[secret] = (raw[:32], raw[32:])
    return _DERIVED[secret]


def _stream(key, nonce, length):
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hmac.new(key, nonce + counter.to_bytes(4, 'big'), hashlib.sha256).digest())
        counter += 1
    return bytes(out[:length])


def encrypt(obj, secret):
    data = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode()
    nonce = secrets.token_bytes(16)
    enc_key, mac_key = _keys(secret)
    cipher = bytes(a ^ b for a, b in zip(data, _stream(enc_key, nonce, len(data))))
    mac = hmac.new(mac_key, nonce + cipher, hashlib.sha256).digest()
    return base64.b64encode(b'\x01' + nonce + mac + cipher).decode()


def decrypt(blob, secret):
    raw = base64.b64decode(blob)
    if len(raw) < 1 + 16 + 32 or raw[0] != 1:
        raise ValueError('Cifrado ilegible')
    nonce, mac, cipher = raw[1:17], raw[17:49], raw[49:]
    enc_key, mac_key = _keys(secret)
    expected = hmac.new(mac_key, nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError('El contenido no se puede abrir')
    plain = bytes(a ^ b for a, b in zip(cipher, _stream(enc_key, nonce, len(cipher))))
    return json.loads(plain.decode())


def seed_documents():
    path = ROOT / 'data' / 'simon' / 'conocimiento.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    docs = list(data.get('documentos') or [])
    for item in data.get('pendientes') or []:
        docs.append({'id': item['id'], 'title': 'Pendiente', 'tags': ['pendiente', 'tarea'], 'text': item['text'],
                     'kind': 'pendiente'})
    return docs


class Store:
    def __init__(self, path=None, key=None):
        self.key = resolve_key(key)
        self.pg = bool(os.environ.get('DATABASE_URL')) and path is None
        self.path = str(path or os.environ.get('SIMON_DB_PATH') or ROOT / 'state' / 'simon.sqlite3')
        if not self.pg:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute(
                'CREATE TABLE IF NOT EXISTS simon_records ('
                'id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject TEXT, doc TEXT NOT NULL)'
            )

    @contextmanager
    def connect(self):
        if self.pg:
            import psycopg
            connection = psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10)
        else:
            connection = sqlite3.connect(self.path, timeout=20)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _marker(self):
        return '%s' if self.pg else '?'

    def put(self, kind, subject, payload):
        ident = str(payload.get('id') or secrets.token_hex(12))
        payload = dict(payload)
        payload['id'] = ident
        blob = encrypt(payload, self.key)
        m = self._marker()
        with self.connect() as conn:
            conn.execute(
                f'INSERT INTO simon_records(id,kind,subject,doc) VALUES ({m},{m},{m},{m}) '
                'ON CONFLICT(id) DO UPDATE SET kind=excluded.kind, subject=excluded.subject, doc=excluded.doc',
                (ident, kind, subject, blob),
            )
        return ident

    def _rows(self, kind=None, subject=None):
        clauses, args = [], []
        m = self._marker()
        if kind:
            clauses.append(f'kind={m}')
            args.append(kind)
        if subject is not None:
            clauses.append(f'subject={m}')
            args.append(subject)
        sql = 'SELECT id, kind, subject, doc FROM simon_records'
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        with self.connect() as conn:
            found = conn.execute(sql, args).fetchall()
        rows = []
        for ident, row_kind, row_subject, blob in found:
            try:
                doc = decrypt(blob, self.key)
            except (ValueError, json.JSONDecodeError):
                continue
            doc['id'] = doc.get('id') or ident
            doc['kind'] = row_kind
            doc['subject'] = row_subject
            rows.append(doc)
        return rows

    def delete_subject(self, subject):
        m = self._marker()
        with self.connect() as conn:
            before = conn.execute(f'SELECT count(*) FROM simon_records WHERE subject={m}', (subject,)).fetchone()[0]
            conn.execute(f'DELETE FROM simon_records WHERE subject={m}', (subject,))
        return int(before)

    def set_consent(self, subject, accepted, at):
        return self.put('consent', subject, {
            'id': 'consent-' + subject, 'accepted': bool(accepted), 'at': at,
            'version': NOTICE_VERSION, 'subject': subject,
        })

    def consent(self, subject):
        rows = [row for row in self._rows('consent', subject) if row.get('accepted')]
        return rows[-1] if rows else None

    def allows(self, subject):
        return self.consent(subject) is not None

    def remember_conversation(self, subject, payload):
        payload = dict(payload)
        payload['id'] = payload.get('id') or secrets.token_hex(8)
        return self.put('conversation', subject, payload)

    def conversation(self, subject, conversation_id):
        for row in self._rows('conversation', subject):
            if row.get('id') == conversation_id or row.get('conversation_id') == conversation_id:
                return row
        return None

    def conversations(self):
        return self._rows('conversation')

    def save_feedback(self, subject, payload):
        payload = dict(payload)
        payload['id'] = 'fb-' + payload['conversation_id']
        return self.put('feedback', subject, payload)

    def feedback(self):
        return self._rows('feedback')

    def save_case(self, subject, payload):
        payload = dict(payload)
        payload.setdefault('id', 'case-' + secrets.token_hex(6))
        return self.put('case', subject, payload)

    def cases(self, subject):
        return self._rows('case', subject)

    def set_pace(self, subject, payload):
        payload = dict(payload)
        payload['id'] = 'pace-' + subject
        return self.put('pace', subject, payload)

    def pace(self, subject):
        rows = self._rows('pace', subject)
        return rows[-1] if rows else None

    def recall(self, text, subject=None, limit=3):
        want = tokens(text)
        docs = seed_documents()
        if subject and self.allows(subject):
            docs.extend(self.cases(subject))
        scored = []
        for doc in docs:
            blob = ' '.join([doc.get('title') or '', doc.get('text') or '', ' '.join(doc.get('tags') or [])])
            have = tokens(blob)
            if not want or not have:
                continue
            score = len(want & have) / float(len(want))
            if score >= 0.34:
                scored.append((score, doc))
        scored.sort(key=lambda item: (-item[0], item[1].get('id') or ''))
        return [doc for _, doc in scored[:limit]]


def public_review(row):
    return {
        'created_at': row.get('created_at'),
        'resolution': row.get('resolution'),
        'rating': row.get('rating'),
        'comment': row.get('comment') or '',
        'visibility': 'publica',
    }


def filter_feedback(rows, filters):
    filters = filters or {}
    selected = []
    for row in rows:
        if filters.get('visibility') and row.get('visibility') != filters['visibility']:
            continue
        solved = filters.get('solved') or ''
        if solved in ('si', 'no', 'parcialmente') and row.get('resolution') != solved:
            continue
        if solved == 'resuelto' and row.get('resolution') != 'si':
            continue
        if solved == 'no_resuelto' and row.get('resolution') == 'si':
            continue
        if filters.get('rating') not in (None, ''):
            if row.get('rating') != int(filters['rating']):
                continue
        start = filters.get('desde') or ''
        end = filters.get('hasta') or ''
        stamp = row.get('created_at') or ''
        if start and stamp < start:
            continue
        if end and stamp[:10] > end:
            continue
        selected.append(row)
    return selected


def stats(feedback_rows, conversations):
    total = len(feedback_rows)
    solved = sum(1 for row in feedback_rows if row.get('resolution') == 'si')
    ratings = [row['rating'] for row in feedback_rows if isinstance(row.get('rating'), int)]
    chats = len(conversations)
    opened = sum(1 for row in conversations if row.get('opened'))
    return {
        'reviews': total,
        'solved_rate': (solved / total) if total else None,
        'average_rating': (sum(ratings) / len(ratings)) if ratings else None,
        'rated': len(ratings),
        'chats': chats,
        'chats_with_link': opened,
        'link_share': (opened / chats) if chats else None,
    }
