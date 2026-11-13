#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Relieve simplificado del Valle de Aburrá a partir de SRTM (dominio público).

Descarga el mosaico de 1 segundo de arco N06W076 (NASA SRTM GL1, dominio público)
desde el espejo público de teselas de elevación y guarda una rejilla reducida en
data/relieve-aburra.json. Ese archivo es el que usa tools/valle_aburra.py.

Fuente y atribución (también en el JSON, en CREDITOS-RECURSOS.md y en el manifiesto):
  NASA Shuttle Radar Topography Mission (SRTM) Global 1 arc-second.
  Dominio público (Gobierno de Estados Unidos).
  Descarga usada: elevation-tiles-prod, tesela skadi N06W076 (en esta latitud el
  mosaico reproduce SRTM). No se incrustan fotos ni el HGT completo en el repositorio.

Uso:
  python3 tools/relieve_aburra.py
  python3 tools/relieve_aburra.py --refresh
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'relieve-aburra.json'
CACHE = Path('/tmp/dem/N06W076.hgt.gz')
URL = 'https://elevation-tiles-prod.s3.amazonaws.com/skadi/N06/N06W076.hgt.gz'

# Tesela SRTM: lat 6°–7° N, lon 76°–75° W. El valle cabe entero.
TILE_LAT = 6
TILE_LON = -76
SAMPLES = 3601

# Recorte del valle, de sur a norte y de occidente a oriente.
LAT_S, LAT_N = 6.02, 6.50
LON_W, LON_E = -75.72, -75.28
ROWS, COLS = 170, 150

ATTRIBUTION = {
    'title': 'NASA SRTM GL1 (Shuttle Radar Topography Mission), 1 arc-second',
    'license': 'Public domain (U.S. Government work)',
    'url': 'https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1',
    'mirror': URL,
    'tile': 'N06W076',
    'note': (
        'En esta latitud la tesela skadi N06W076 reproduce SRTM. '
        'La rejilla del juego es un remuestreo simplificado y una escala vertical propia; '
        'no es el modelo original ni un mapa oficial.'
    ),
}


def download(refresh=False):
    if CACHE.exists() and CACHE.stat().st_size > 1_000_000 and not refresh:
        return CACHE
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={'User-Agent': 'SaimonCity-valle/1.0'})
    with urllib.request.urlopen(req, timeout=120) as response, CACHE.open('wb') as handle:
        handle.write(response.read())
    return CACHE


def load_hgt(path):
    raw = gzip.open(path, 'rb').read()
    expect = SAMPLES * SAMPLES * 2
    if len(raw) != expect:
        raise SystemExit(f'HGT inesperado: {len(raw)} bytes, se esperaban {expect}')
    return raw


def sample(raw, lat, lon):
    """Altura en metros. Fila 0 de la tesela es el borde norte."""
    if not (TILE_LAT <= lat <= TILE_LAT + 1 and TILE_LON <= lon <= TILE_LON + 1):
        return None
    row = (TILE_LAT + 1 - lat) * (SAMPLES - 1)
    col = (lon - TILE_LON) * (SAMPLES - 1)
    r0 = int(math.floor(row))
    c0 = int(math.floor(col))
    r0 = max(0, min(SAMPLES - 2, r0))
    c0 = max(0, min(SAMPLES - 2, c0))
    fr, fc = row - r0, col - c0

    def at(r, c):
        i = (r * SAMPLES + c) * 2
        v = int.from_bytes(raw[i:i + 2], 'big', signed=True)
        return None if v <= -32000 else v

    corners = [at(r0, c0), at(r0, c0 + 1), at(r0 + 1, c0), at(r0 + 1, c0 + 1)]
    if any(v is None for v in corners):
        known = [v for v in corners if v is not None]
        return known[0] if known else None
    a, b, c, d = corners
    return (a * (1 - fc) + b * fc) * (1 - fr) + (c * (1 - fc) + d * fc) * fr


def build_grid(raw):
    grid = []
    vals = []
    for r in range(ROWS):
        lat = LAT_N - (LAT_N - LAT_S) * (r / (ROWS - 1))
        row = []
        for c in range(COLS):
            lon = LON_W + (LON_E - LON_W) * (c / (COLS - 1))
            h = sample(raw, lat, lon)
            if h is None:
                h = row[-1] if row else 1500
            h = int(round(h))
            row.append(h)
            vals.append(h)
        grid.append(row)
    return grid, min(vals), max(vals)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    raw = load_hgt(download(args.refresh))
    grid, lo, hi = build_grid(raw)
    doc = {
        'id': 'relieve-aburra',
        'attribution': ATTRIBUTION,
        'latN': LAT_N,
        'latS': LAT_S,
        'lonW': LON_W,
        'lonE': LON_E,
        'rows': ROWS,
        'cols': COLS,
        'vertical': 'metros sobre el nivel del mar, enteros, remuestreo bilineal',
        'min': lo,
        'max': hi,
        'elev': grid,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'{OUT.relative_to(ROOT)} {ROWS}×{COLS} {lo}–{hi} m')


if __name__ == '__main__':
    main()
