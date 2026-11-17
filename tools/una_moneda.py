# SPDX-License-Identifier: AGPL-3.0-or-later
"""Todo el saldo pasa a Simoncoin. Las tasas las fijó Jay el 17 nov 2026, 7:43 p. m.

1 cobre = 0,001 SMC. 1 plata (SMP) = 0,01 SMC. 1 mineral de oro = 0,1 SMC.
El saldo que ya es Simoncoin no se vuelve a convertir.
La tasa vieja del código (100 SMP = 1 SMC, tools/plata.py) no se usa.
Si la suma no cabe en los 21.000.000 SMC, no se mueve ningún saldo.
"""
import hashlib
import hmac
import json
import os

import economy as eco
import plata

FLAG = 'jay-tasas-7-43'
# Jay, chat, 17 nov 2026 7:43 p. m. Bogotá.
COBRE_SMC = 1 / 1000
PLATA_SMC = 1 / 100
ORO_MINERAL_SMC = 1 / 10
PLATA_VIEJA = 100  # tools/plata.py: 100 SMP = 1 SMC. No se aplica.
ORO_MINERALES = ('pepita_oro', 'mineral_oro')
PLATA_MINERALES = ('mineral_plata',)
COBRE_MINERALES = ('mineral_cobre',)


def _millis_plata(amount):
    """Unidades de 0,001 SMC que salen de la plata guardada a 0,01 SMC por SMP.

    1 SMP = 100.000.000 unidades viejas = 10 milésimos de SMC.
    """
    amount = int(amount or 0)
    if amount <= 0:
        return 0, 0
    unidad = plata.SUBS // 10
    return amount // unidad, amount % unidad


def _millis_cobre(qty):
    """1 cobre = 1 milésimo de SMC."""
    qty = int(qty or 0)
    if qty <= 0:
        return 0, 0
    return qty, 0


def _millis_mineral(qty, each):
    """each es milésimos de SMC por pieza. El resto de pieza no existe: son enteras."""
    qty = int(qty or 0)
    return max(0, qty) * each, 0


def _floor_pair(millis, sobra_plata):
    """Baja a 0,01 SMC (10 milésimos). Devuelve SMH y la fracción SMC descartada."""
    smh = millis // 10
    resto_millis = millis % 10
    descartado = resto_millis * 0.001 + (sobra_plata / plata.SUBS) * PLATA_SMC
    return smh, descartado


def _nombre(accounts, account_id):
    for user in (accounts or {}).get('users') or []:
        if isinstance(user, dict) and user.get('id') == account_id:
            return str(user.get('wallet_name') or user.get('name') or '')
    return ''


def _sumar(bucket, name, millis, sobra=0):
    if not name:
        return
    row = bucket.setdefault(name, {'millis': 0, 'sobra': 0})
    row['millis'] += int(millis or 0)
    row['sobra'] += int(sobra or 0)


def _fuentes(econ, vault, accounts):
    """Junta plata, cobre y minerales. No incluye el SMC que ya está en la billetera."""
    bucket = {}
    box = (econ or {}).get('plata') if isinstance(econ, dict) else {}
    box = box if isinstance(box, dict) else {}
    for name, amount in (box.get('wallets') or {}).items():
        millis, sobra = _millis_plata(amount)
        _sumar(bucket, str(name), millis, sobra)
    for name, acc in ((vault or {}).get('accounts') or {}).items():
        if isinstance(acc, dict):
            millis, sobra = _millis_plata(acc.get('sph') or 0)
            _sumar(bucket, str(name), millis, sobra)
    cobre = (econ or {}).get('simonchis') if isinstance(econ, dict) else {}
    cobre = cobre if isinstance(cobre, dict) else {}
    for name, qty in (cobre.get('wallets') or {}).items():
        millis, sobra = _millis_cobre(qty)
        _sumar(bucket, str(name), millis, sobra)
    crudo = (econ or {}).get('crudo') if isinstance(econ, dict) else {}
    for account, row in (crudo or {}).items():
        if not isinstance(row, dict):
            continue
        name = _nombre(accounts, account) or str(account)
        for item, each in (
            ('pepita_oro', 100), ('mineral_oro', 100),
            ('mineral_plata', 10), ('mineral_cobre', 1),
        ):
            piezas = int(row.get(item) or 0) // 1000
            millis, sobra = _millis_mineral(piezas, each)
            _sumar(bucket, name, millis, sobra)
    purses = (vault or {}).get('purses') or {}
    for name, bag in purses.items():
        if not isinstance(bag, dict):
            continue
        for item, each in (
            ('pepita_oro', 100), ('mineral_oro', 100),
            ('mineral_plata', 10), ('mineral_cobre', 1),
        ):
            millis, sobra = _millis_mineral(bag.get(item) or 0, each)
            _sumar(bucket, str(name), millis, sobra)
    return bucket


def bug118(econ):
    """Acuñaciones de plata por debajo de 1 SMP. No se multiplican."""
    found = []
    box = (econ or {}).get('plata') if isinstance(econ, dict) else {}
    for tx in (box or {}).get('txs') or []:
        if not isinstance(tx, dict) or tx.get('type') != 'mint':
            continue
        amount = int(tx.get('amountSph') or tx.get('amount') or 0)
        if 0 < amount < plata.SUBS:
            found.append({
                'cuenta': tx.get('to') or '',
                'unidades': amount,
                'smp': amount / plata.SUBS,
                'nota': 'bug de escala; no se repara',
            })
    return found


def preview(econ, vault=None, accounts=None):
    econ = econ if isinstance(econ, dict) else {}
    filas = []
    credit = 0
    descartado = 0.0
    for name, row in sorted(_fuentes(econ, vault, accounts).items()):
        smh, pierde = _floor_pair(row['millis'], row['sobra'])
        exacto = row['millis'] * 0.001 + (row['sobra'] / plata.SUBS) * PLATA_SMC
        filas.append({
            'cuenta': name,
            'smh': smh,
            'smc': smh / eco.SMH_PER_SMC,
            'exacto': exacto,
            'descartado': pierde,
        })
        credit += smh
        descartado += pierde
    room = eco.issuance_room(econ)
    return {
        'ok': credit <= room,
        'tasas': {
            'plata': '1 SMP = 0,01 SMC',
            'cobre': '1 cobre = 0,001 SMC',
            'oroMineral': '1 mineral de oro = 0,1 SMC',
            'oroMoneda': 'el saldo SMC no se reconvierte',
        },
        'creditoSmh': credit,
        'creditoSmc': credit / eco.SMH_PER_SMC,
        'descartadoSmc': descartado,
        'cupoSmc': room / eco.SMH_PER_SMC,
        'topeSmc': eco.MAX_SUPPLY,
        'filas': filas,
        'bug118': bug118(econ),
        'tasaViejaNoUsada': '100 SMP = 1 SMC en tools/plata.py',
    }


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


def _backup(econ, vault, folder):
    os.makedirs(folder, exist_ok=True)
    key_path = os.path.join(folder, 'una-moneda.key')
    blob_path = os.path.join(folder, 'una-moneda-respaldo.bin')
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
    snap = {
        'plata': (econ or {}).get('plata'),
        'simonchis': (econ or {}).get('simonchis'),
        'crudo': (econ or {}).get('crudo'),
        'wallets': (econ or {}).get('wallets'),
        'minedSmh': (econ or {}).get('minedSmh'),
        'purses': (vault or {}).get('purses'),
        'deposito': (vault or {}).get('accounts'),
    }
    raw = json.dumps(snap, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')
    with open(blob_path, 'wb') as handle:
        handle.write(_seal(key, raw))
    return blob_path


def _vaciar(econ, vault):
    box = econ.get('plata')
    if isinstance(box, dict):
        for name in list((box.get('wallets') or {}).keys()):
            box['wallets'][name] = 0
    cobre = econ.get('simonchis')
    if isinstance(cobre, dict):
        for name in list((cobre.get('wallets') or {}).keys()):
            cobre['wallets'][name] = 0
    for row in (econ.get('crudo') or {}).values():
        if not isinstance(row, dict):
            continue
        for item in ORO_MINERALES + PLATA_MINERALES + COBRE_MINERALES:
            if item in row:
                row[item] = 0
    for bag in ((vault or {}).get('purses') or {}).values():
        if not isinstance(bag, dict):
            continue
        for item in ORO_MINERALES + PLATA_MINERALES + COBRE_MINERALES:
            bag.pop(item, None)
    for acc in ((vault or {}).get('accounts') or {}).values():
        if isinstance(acc, dict):
            acc['sph'] = 0


def aplicar(econ, vault=None, accounts=None, folder=None, now=None):
    if not isinstance(econ, dict):
        return {'ok': False, 'estado': 'vacio'}
    meta = econ.setdefault('meta', {})
    hecho = meta.get('unaMoneda')
    if isinstance(hecho, dict) and hecho.get('id') == FLAG:
        return {'ok': True, 'estado': 'ya', 'id': FLAG}
    plan = preview(econ, vault, accounts)
    if folder:
        _backup(econ, vault, folder)
        path = os.path.join(folder, 'una-moneda-informe.json')
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump({
                'ok': plan['ok'],
                'creditoSmc': plan['creditoSmc'],
                'descartadoSmc': plan['descartadoSmc'],
                'cupoSmc': plan['cupoSmc'],
                'bug118': plan['bug118'],
                'filas': plan['filas'],
            }, handle, ensure_ascii=False, indent=2)
    if not plan['ok']:
        return {'ok': False, 'estado': 'bloqueada', 'plan': plan, 'changed': False}
    for row in plan['filas']:
        if row['smh'] <= 0:
            continue
        granted = eco.issue(
            econ, row['cuenta'], row['smh'],
            'Conversión a Simoncoin (plata 0,01, cobre 0,001, mineral de oro 0,1)',
            'conversion', now=now,
        )
        if granted != row['smh']:
            raise RuntimeError('el tope se movió durante la conversión')
    _vaciar(econ, vault)
    meta['unaMoneda'] = {
        'id': FLAG,
        'estado': 'hecha',
        'creditoSmc': plan['creditoSmc'],
        'descartadoSmc': plan['descartadoSmc'],
        'bug118': len(plan['bug118']),
    }
    return {'ok': True, 'estado': 'hecha', 'plan': plan, 'changed': True}
