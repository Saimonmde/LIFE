#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verifica la cadena de certificados SMC. Sólo biblioteca estándar.

Uso: python3 tools/verify_nft.py [state/nft.json]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nft


def main(argv):
    path = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'state', 'nft.json')
    if not os.path.isfile(path):
        print('No hay certificados en', path)
        return 1
    with open(path, encoding='utf-8') as handle:
        chain = json.load(handle)
    ok, message = nft.verify_chain(chain)
    print(('OK ' if ok else 'FALLO ') + message)
    pubkey = chain.get('pubkey') or ''
    print('Clave pública:', pubkey)
    print('Tope de la simulación: 21.000.000 SMC entre todos los certificados y la reserva.')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
