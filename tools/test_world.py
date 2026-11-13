# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check the current valley, not coordinates from a superseded map."""
import json
from pathlib import Path
from collections import deque
root=Path(__file__).resolve().parents[1]
w=json.loads((root/'data/el-jardin.json').read_text())
offset=json.loads((root/'data/valle-offset.json').read_text())
expected={'barbosa','girardota','copacabana','bello','medellin','envigado','itagui','sabaneta','la_estrella','caldas'}
assert set(w['valle']['municipios'])==expected
assert all(len(w[k])==w['height'] and all(len(row)==w['width'] for row in w[k]) for k in ['ground','collision','elevation'])
start=(227+offset['x'],64+offset['y']);seen={start};q=deque([start])
assert not w['collision'][start[1]][start[0]]
while q:
 x,y=q.popleft()
 for a,b in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
  if 0<=a<w['width'] and 0<=b<w['height'] and not w['collision'][b][a] and (a,b) not in seen:seen.add((a,b));q.append((a,b))
for ident in expected:
 p=next(p for p in w['waypoints'] if p['id']==ident);assert (p['x'],p['y']) in seen,ident
assert json.loads((root/'data/el-jardin.js').read_text().removeprefix('window.EL_JARDIN=').strip().removesuffix(';'))==w
print('PASS: salida de casa conectada a los diez parques; dimensiones y JS/JSON coherentes.')
