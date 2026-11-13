# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path
from collections import deque
root=Path(__file__).resolve().parents[1]
w=json.loads((root/'data/el-jardin.json').read_text())
assert len(w['municipalities'])==10
assert len({m['name'] for m in w['municipalities']})==10
assert all(len(w[k])==w['height'] and all(len(row)==w['width'] for row in w[k]) for k in ['ground','collision','elevation'])
start=(w['homeLocation']['stand']['x'],w['homeLocation']['stand']['y']);seen={start};q=deque([start])
while q:
 x,y=q.popleft()
 for a,b in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
  if 0<=a<w['width'] and 0<=b<w['height'] and not w['collision'][b][a] and (a,b) not in seen:seen.add((a,b));q.append((a,b))
for m in w['municipalities']:
 p=m['park'];assert (p['x'],p['y']) in seen,m['name']
assert json.loads((root/'data/el-jardin.js').read_text().removeprefix('window.EL_JARDIN=').strip().removesuffix(';'))==w
print('PASS: diez municipios, dimensiones válidas, diez parques conectados con la casa y datos JS/JSON idénticos.')
