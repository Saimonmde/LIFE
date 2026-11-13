# SPDX-License-Identifier: AGPL-3.0-or-later
"""Estado duradero: Postgres si hay DATABASE_URL, si no los JSON de state/.

Una tabla guarda cada almacén como JSON. El primer arranque con la base vacía
copia los JSON que ya existan. Las escrituras van en una transacción.
"""
import json
import os

_CONN = None
_READY = False

NAMES = {
    'economy.json': 'economy',
    'vault.json': 'vault',
    'nft.json': 'nft',
    'players.json': 'players',
    'nft-key.json': 'nft_seed',
    'accounts.json': 'accounts',
}


def enabled():
    return bool(os.environ.get('DATABASE_URL', '').strip())


def _connect():
    global _CONN
    if _CONN is not None and not _CONN.closed:
        return _CONN
    import psycopg
    _CONN = psycopg.connect(os.environ['DATABASE_URL'].strip(), autocommit=False)
    return _CONN


def _schema(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS stores (
            name TEXT PRIMARY KEY,
            doc JSONB NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )"""
    )
    conn.commit()


def ensure():
    global _READY
    if not enabled():
        return
    conn = _connect()
    if not _READY:
        _schema(conn)
        _READY = True


def reset_connection():
    """Cierra la conexión. Lo usan las pruebas."""
    global _CONN, _READY
    if _CONN is not None and not _CONN.closed:
        _CONN.close()
    _CONN = None
    _READY = False


def _read_file(path):
    if not path or not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def _write_file(path, doc):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _import_dir(conn, directory):
    conn.execute('LOCK TABLE stores IN EXCLUSIVE MODE')
    count = conn.execute('SELECT count(*) FROM stores').fetchone()[0]
    if count:
        return
    for filename, name in NAMES.items():
        path = os.path.join(directory, filename)
        doc = _read_file(path)
        if doc is None:
            continue
        conn.execute(
            'INSERT INTO stores (name, doc) VALUES (%s, %s::jsonb) ON CONFLICT (name) DO NOTHING',
            (name, json.dumps(doc)),
        )


def load_named(name, path):
    """Devuelve el documento o None si todavía no existe."""
    if not enabled():
        return _read_file(path)
    ensure()
    conn = _connect()
    with conn.transaction():
        _import_dir(conn, os.path.dirname(path) or '.')
        row = conn.execute('SELECT doc FROM stores WHERE name = %s', (name,)).fetchone()
    if not row:
        return None
    doc = row[0]
    return doc if isinstance(doc, dict) else json.loads(doc)


def save_named(name, path, doc):
    if not enabled():
        _write_file(path, doc)
        return
    ensure()
    conn = _connect()
    with conn.transaction():
        conn.execute(
            """INSERT INTO stores (name, doc, updated_at) VALUES (%s, %s::jsonb, now())
               ON CONFLICT (name) DO UPDATE SET doc = EXCLUDED.doc, updated_at = now()""",
            (name, json.dumps(doc)),
        )
