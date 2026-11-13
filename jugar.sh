#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# LIFE INC · El Jardín — vista previa jugable + chat multijugador (puerto 8765)
# Uso: ./jugar.sh            (con 3 jugadores de demostración "(bot)")
#      ./jugar.sh --sin-bots (sin bots)    ./jugar.sh --port 9000 (otro puerto)
cd "$(dirname "$0")" || exit 1
exec python3 server.py --port 8765 "$@"
