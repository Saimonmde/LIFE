# SPDX-License-Identifier: AGPL-3.0-or-later
"""Repara las acuñaciones de plata del #118. Una sola vez.

El #118 anotó la plata en la escala del oro (100) y no en platicas
(100.000.000). Cada unidad guardada debía valer un millón de platicas.
Jay fijó 1 plata = 0,01 SMC. La diferencia se redondea hacia abajo a
2 decimales y se acredita en Simoncoin. Si no cabe en 21.000.000, no
se mueve nada.
"""
import hashlib
import hmac
import json
import os

import economy as eco
import una_moneda as una

FLAG = 'jay-plata-118'
NOTA = 'Reparación de la plata del #118: 1 plata = 0,01 SMC'


def _smh(unidades):
    """Enteros de 0,01 SMC. 100 unidades erróneas = 1 SMP = 0,01 SMC."""
    return int(unidades or 0) // 100


def plan(econ):
    """Dry run. No escribe saldos."""
    grupos = {}
    mints = una.bug118(econ)
    for row in mints:
        name = str(row.get('cuenta') or '').strip()
        if not name:
            continue
        grupos[name] = grupos.get(name, 0) + int(row.get('unidades') or 0)
    cuentas = []
    total = 0
    for name in sorted(grupos):
        smh = _smh(grupos[name])
        if smh <= 0:
            continue
        cuentas.append({
            'cuenta': name,
            'unidades': grupos[name],
            'smh': smh,
            'smc': smh / eco.SMH_PER_SMC,
        })
        total += smh
    room = eco.issuance_room(econ if isinstance(econ, dict) else {})
    return {
        'ok': total <= room,
        'cuentas': cuentas,
        'mints': len(mints),
        'totalSmh': total,
        'totalSmc': total / eco.SMH_PER_SMC,
        'cupoSmh': room,
        'cupoSmc': room / eco.SMH_PER_SMC,
        'tasa': '1 plata = 0,01 SMC',
        'escala': 'cada unidad del #118 vale 1.000.000 platicas',
    }


def _ya(econ):
    meta = (econ or {}).get('meta') if isinstance(econ, dict) else None
    hecho = (meta or {}).get('plata118')
    return isinstance(hecho, dict) and hecho.get('id') == FLAG


def _seal(key, raw):
    nonce = os.urandom(16)
    stream = b''
    counter = 0
    while len(stream) < len(raw):
        stream += hmac.new(key, nonce + counter.to_bytes(4, 'big'), hashlib.sha256).digest()
        counter += 1
    body = bytes(a ^ b for a, b in zip(raw, stream))
    mac = hmac.new(key, nonce + body, hashlib.sha256).digest()
    return nonce + mac + body


def _respaldo(econ, folder):
    os.makedirs(folder, exist_ok=True)
    key_path = os.path.join(folder, 'plata-118.key')
    blob_path = os.path.join(folder, 'plata-118-respaldo.bin')
    if os.path.exists(blob_path):
        return blob_path
    key = os.urandom(32)
    if os.path.exists(key_path):
        key = open(key_path, 'rb').read()
    else:
        with open(key_path, 'wb') as handle:
            handle.write(key)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
    raw = json.dumps({
        'wallets': (econ or {}).get('wallets'),
        'minedSmh': (econ or {}).get('minedSmh'),
        'plataTxs': ((econ or {}).get('plata') or {}).get('txs'),
    }, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')
    with open(blob_path, 'wb') as handle:
        handle.write(_seal(key, raw))
    return blob_path


def _informe(folder, body):
    path = os.path.join(folder, 'plata-118-informe.json')
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(body, handle, ensure_ascii=False, indent=2)
    return path


def aplicar(econ, folder=None, now=None, techo_smh=None):
    """Acredita la diferencia. Idempotente. Si no cabe, el saldo queda igual."""
    if not isinstance(econ, dict):
        return {'ok': False, 'estado': 'vacio', 'changed': False}
    if _ya(econ):
        return {'ok': True, 'estado': 'ya', 'id': FLAG, 'changed': False}
    preview = plan(econ)
    if techo_smh is not None and preview['totalSmh'] > int(techo_smh):
        preview = dict(preview)
        preview['ok'] = False
        preview['motivo'] = 'no cabe en el libro público'
    if folder:
        _respaldo(econ, folder)
        _informe(folder, {'fase': 'dry-run', 'estado': 'cabe' if preview['ok'] else 'bloqueada', **preview})
    if not preview['ok']:
        return {'ok': False, 'estado': 'bloqueada', 'changed': False, 'plan': preview}
    for row in preview['cuentas']:
        granted = eco.issue(econ, row['cuenta'], row['smh'], NOTA, 'reparacion', now=now)
        if granted != row['smh']:
            raise RuntimeError('el tope se movió durante la reparación')
    econ.setdefault('meta', {})['plata118'] = {
        'id': FLAG,
        'estado': 'hecha',
        'totalSmc': preview['totalSmc'],
        'cuentas': len(preview['cuentas']),
    }
    return {'ok': True, 'estado': 'hecha', 'changed': True, 'plan': preview}
