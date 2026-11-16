# SPDX-License-Identifier: AGPL-3.0-or-later
"""Genera El Jardín completo: teselas, sprites, iconos, JSON del mapa y vistas previas.
Uso: cd /workspace/Live-Ink/El-Jardin/tools && python3 build.py
Todo el arte es original y se pinta por código (sin assets externos)."""
import json, math, os, random
from PIL import Image
import tiles as TL
import objects as O
import village as V

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
G = os.path.join(ROOT, 'graphics')
W = H = 40
TS = 64
rnd = random.Random(2026)

# ---------------- terreno ----------------
T = [['G'] * W for _ in range(H)]
BODY = [[None] * W for _ in range(H)]
# Río Claro (norte -> sur, al este)
for y in range(H):
    cx = 31 + round(1.6 * math.sin(y / 5.5))
    for x in range(cx - 1, cx + 2):
        T[y][x] = 'W'; BODY[y][x] = 'rio_claro'
# Estanque de los Patos (suroeste)
for y in range(H):
    for x in range(W):
        if ((x - 6) / 3.7) ** 2 + ((y - 33) / 2.7) ** 2 <= 1:
            T[y][x] = 'W'; BODY[y][x] = 'estanque'

def seg(a, b):
    (x0, y0), (x1, y1) = a, b
    if x0 == x1:
        for y in range(min(y0, y1), max(y0, y1) + 1): yield x0, y
    else:
        for x in range(min(x0, x1), max(x0, x1) + 1): yield x, y0
def poly(pts):
    for a, b in zip(pts, pts[1:]):
        for x, y in seg(a, b):
            T[y][x] = 'B' if T[y][x] == 'W' else 'P'

# Acantilado con cascada (norte del río): casillas 'K' = roca, no caminables
CLIFF = (26, 0, 12, 4)   # x, y, w, h
for y in range(CLIFF[1], CLIFF[1] + CLIFF[3]):
    for x in range(CLIFF[0], CLIFF[0] + CLIFF[2]):
        T[y][x] = 'K'; BODY[y][x] = None
poly([(0,21),(5,21),(5,19),(12,19),(12,20),(14,20)])                   # camino oeste -> plaza
poly([(24,20),(26,20),(26,19),(39,19)])                                # plaza -> puente -> este
poly([(15,24),(15,26),(10,26),(10,30),(9,30)])                         # a la arboleda tropical / estanque
poly([(20,24),(20,25)])                                                # puerta del huerto
poly([(5,19),(5,7),(7,7)])                                             # a la cantera
PLAZA = (14, 16, 11, 8)  # plaza empedrada del pueblo
for y in range(PLAZA[1], PLAZA[1] + PLAZA[3]):
    for x in range(PLAZA[0], PLAZA[0] + PLAZA[2]): T[y][x] = 'C'
SPAWN = (10, 28)   # en el camino de tierra, en el prado junto al estanque (inicio del tutorial)

# ---------------- objetos ----------------
nodes, decos = [], []
occupied = {}
def occ(x, y, what, ok='G'):
    assert T[y][x] in ok, f"{what} en ({x},{y}) no es césped: {T[y][x]}"
    assert (x, y) not in occupied, f"{what} choca con {occupied[(x, y)]}"
    assert max(abs(x - SPAWN[0]), abs(y - SPAWN[1])) > 1, f"{what} bloquea el spawn"
    occupied[(x, y)] = what

FRUIT_TREES = {
    'manzana': [(2,11),(7,13),(3,17)], 'pera': [(9,11),(3,14),(10,16)], 'naranja': [(7,16),(11,13),(8,18)],
    'mango': [(13,29),(20,32),(23,31)], 'banano': [(17,31),(12,33),(21,35)], 'coco': [(10,35),(17,34),(24,33)],
}
TROPICAL = {'mango', 'banano', 'coco'}
for sp, pts in FRUIT_TREES.items():
    for i, (x, y) in enumerate(pts, 1):
        nid = f'arbol_{sp}_{i}'; occ(x, y, nid)
        nodes.append({
            'id': nid, 'type': 'fruit_tree', 'species': sp, 'grove': 'tropical' if sp in TROPICAL else 'templada',
            'x': x, 'y': y, 'skill': 'gathering', 'item': sp, 'solid': True,
            'states': ['full', 'picked'], 'initialState': 'full',
            'sprites': {'full': f'tree_{sp}_full', 'picked': f'tree_{sp}_picked'},
            'yield': {'item': sp, 'min': 1, 'max': 3}, 'bonus': {'item': f'{sp}_seed', 'chance': 0.25},
            'xp': 10, 'respawnMs': 25000,
        })
SEEDS = [f'{s}_seed' for s in FRUIT_TREES]
for i, (x, y) in enumerate([(17,26),(18,26),(19,26),(21,26),(22,26),(23,26),(17,28),(18,28),(19,28),(21,28),(22,28),(23,28)], 1):
    nid = f'parcela_{i}'; occ(x, y, nid)
    nodes.append({
        'id': nid, 'type': 'farm_plot', 'x': x, 'y': y, 'skill': 'planting', 'solid': True,
        'states': ['empty', 'planted', 'grown'], 'initialState': 'empty', 'accepts': SEEDS, 'growMs': 15000,
        'sprites': {'empty': 'plot_empty', 'planted': 'plot_planted', 'grown': {s: f'plot_grown_{s}' for s in FRUIT_TREES}},
        'harvest': {'fruitMin': 2, 'fruitMax': 3, 'seedChance': 0.6}, 'xp': {'plant': 8, 'harvest': 12},
    })
for kind, pts, resp in (('cobre', [(2,4),(4,2),(9,2),(3,8)], 18000), ('plata', [(7,4),(11,5),(9,8)], 25000)):
    for i, (x, y) in enumerate(pts, 1):
        nid = f'roca_{kind}_{i}'; occ(x, y, nid)
        nodes.append({
            'id': nid, 'type': 'mineral_rock', 'mineral': kind, 'x': x, 'y': y, 'skill': 'mining', 'method': 'terrestre',
            'tool': 'pico', 'solid': True, 'states': ['active', 'depleted'], 'initialState': 'active',
            'sprites': {'active': f'rock_{kind}', 'depleted': 'rock_depleted'},
            'yield': {'item': f'mineral_{kind}', 'min': 1, 'max': 1}, 'xp': 12 if kind == 'cobre' else 18, 'respawnMs': resp,
        })

def bank_tile(y, side):
    """casilla de río en la orilla (oeste u este) de la fila y"""
    xs = [x for x in range(W) if BODY[y][x] == 'rio_claro' and T[y][x] == 'W']
    return (min(xs) if side == 'w' else max(xs)), y
def is_shore(x, y):
    return any(0 <= x+dx < W and 0 <= y+dy < H and T[y+dy][x+dx] in 'GP' for dx in (-1,0,1) for dy in (-1,0,1))
water_used = set()
def water_node(nid, x, y, body):
    assert T[y][x] == 'W' and BODY[y][x] == body and is_shore(x, y) and (x, y) not in water_used, nid
    water_used.add((x, y))
for i, (y, side) in enumerate([(7,'w'),(24,'w'),(34,'e')], 1):
    x, y = bank_tile(y, side); nid = f'pesca_rio_{i}'; water_node(nid, x, y, 'rio_claro')
    nodes.append({'id': nid, 'type': 'fishing_spot', 'waterBody': 'rio_claro', 'x': x, 'y': y, 'skill': 'fishing',
                  'tool': 'red_pesca', 'solid': True, 'states': ['active', 'depleted'], 'initialState': 'active',
                  'sprites': {'active': 'spot_pesca', 'depleted': 'spot_pesca_calma'},
                  'yield': {'table': [{'item': 'trucha', 'weight': 65}, {'item': 'bocachico', 'weight': 35}], 'qty': 1},
                  'xp': 12, 'respawnMs': 15000})
for i, (x, y) in enumerate([(8,31),(3,34)], 1):
    nid = f'pesca_estanque_{i}'; water_node(nid, x, y, 'estanque')
    nodes.append({'id': nid, 'type': 'fishing_spot', 'waterBody': 'estanque', 'x': x, 'y': y, 'skill': 'fishing',
                  'tool': 'red_pesca', 'solid': True, 'states': ['active', 'depleted'], 'initialState': 'active',
                  'sprites': {'active': 'spot_pesca', 'depleted': 'spot_pesca_calma'},
                  'yield': {'table': [{'item': 'mojarra', 'weight': 100}], 'qty': 1}, 'xp': 10, 'respawnMs': 15000})
for i, (y, side) in enumerate([(10,'e'),(13,'w'),(28,'e'),(37,'w')], 1):
    x, y = bank_tile(y, side); nid = f'oro_fluvial_{i}'; water_node(nid, x, y, 'rio_claro')
    nodes.append({'id': nid, 'type': 'nodo_oro_fluvial', 'waterBody': 'rio_claro', 'x': x, 'y': y, 'skill': 'mining',
                  'method': 'fluvial', 'tool': 'batea', 'solid': True, 'states': ['active', 'depleted'], 'initialState': 'active',
                  'sprites': {'active': 'spot_oro', 'depleted': 'spot_oro_lavado'}, 'successChance': 0.75,
                  'yield': {'item': 'pepita_oro', 'min': 1, 'max': 1}, 'xp': 25, 'respawnMs': 30000})
# Primeros Pasos: pinos para talar (madera, con hacha) y rocas de piedra (piedra, con pico)
for i, (x, y) in enumerate([(13,9),(15,7),(17,10),(12,6),(18,6),(20,9)], 1):
    nid = f'pino_{i}'; occ(x, y, nid)
    nodes.append({'id': nid, 'type': 'wood_tree', 'species': 'pino', 'x': x, 'y': y, 'skill': 'woodcutting', 'tool': 'hacha',
                  'solid': True, 'states': ['standing', 'stump'], 'initialState': 'standing',
                  'sprites': {'standing': 'tree_pino', 'stump': 'tree_pino_stump'},
                  'yield': {'item': 'madera', 'min': 2, 'max': 3}, 'xp': 12, 'respawnMs': 20000})
for i, (x, y) in enumerate([(23,6),(25,8),(22,10),(26,5)], 1):
    nid = f'roca_piedra_{i}'; occ(x, y, nid)
    nodes.append({'id': nid, 'type': 'mineral_rock', 'mineral': 'piedra', 'x': x, 'y': y, 'skill': 'mining', 'method': 'terrestre',
                  'tool': 'pico', 'solid': True, 'states': ['active', 'depleted'], 'initialState': 'active',
                  'sprites': {'active': 'rock_piedra', 'depleted': 'rock_piedra_depleted'},
                  'yield': {'item': 'piedra', 'min': 1, 'max': 2}, 'xp': 8, 'respawnMs': 15000})
ANIMALS = {'conejo': [(26,12),(12,23),(27,25),(28,15)], 'venado': [(36,11),(36,28)], 'ave': [(27,29),(8,24),(36,36)]}
AN_YIELD = {
    'conejo': [{'item': 'carne', 'min': 1, 'max': 1, 'chance': 1}, {'item': 'piel', 'min': 1, 'max': 1, 'chance': 0.5}],
    'venado': [{'item': 'carne', 'min': 2, 'max': 3, 'chance': 1}, {'item': 'piel', 'min': 1, 'max': 1, 'chance': 1}],
    'ave': [{'item': 'pluma', 'min': 1, 'max': 3, 'chance': 1}, {'item': 'carne', 'min': 1, 'max': 1, 'chance': 0.6}],
}
for sp, pts in ANIMALS.items():
    for i, (x, y) in enumerate(pts, 1):
        assert T[y][x] in 'G' and (x, y) not in occupied
        nodes.append({'id': f'{sp}_{i}', 'type': 'animal', 'species': sp, 'x': x, 'y': y, 'wanderRadius': 2,
                      'skill': 'hunting', 'tool': 'lanza', 'solid': False, 'states': ['alive', 'hunted'], 'initialState': 'alive',
                      'sprites': {'alive': [f'animal_{sp}_0', f'animal_{sp}_1']}, 'yield': AN_YIELD[sp],
                      'xp': {'conejo': 10, 'venado': 30, 'ave': 8}[sp], 'respawnMs': 25000})

# decoración: pueblo (v3), letrero, robles, arbustos
def place(did, dtype, x, y, w, h, sprite, solid=True, ok='GC', **kw):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if solid: occ(xx, yy, did, ok)
    d = {'id': did, 'type': dtype, 'x': x, 'y': y, 'sprite': sprite, 'solid': solid}
    if w != 1 or h != 1: d['w'] = w; d['h'] = h
    d.update(kw); decos.append(d); return d
place('letrero_el_jardin', 'sign', 25, 21, 1, 1, 'sign_el_jardin', text='El Jardín')
place('cascada', 'waterfall', *CLIFF, 'cascada_0', ok='K', frames=['cascada_0', 'cascada_1', 'cascada_2'], frameMs=160)
place('casa_capataz', 'building', 14, 13, 3, 3, 'casa_capataz', name='Casa del Capataz', lights=[[0.15, 0.69], [0.70, 0.69], [0.5, 1.0]])
place('casa_piedra', 'building', 18, 13, 3, 3, 'casa_piedra', name='Casa de piedra', lights=[[0.16, 0.76], [0.66, 0.76], [0.48, 0.40]])
place('puesto_mercado', 'stall', 22, 15, 2, 1, 'puesto', name='Puesto del mercado')
place('fuente', 'fountain', 19, 18, 2, 2, 'fuente_0', frames=['fuente_0', 'fuente_1'], frameMs=220, name='Fuente de la plaza')
for i, (x, y) in enumerate([(14,17),(24,17),(14,23),(24,23),(19,24),(21,24)], 1):
    place(f'antorcha_{i}', 'torch', x, y, 1, 1, 'antorcha_0', frames=['antorcha_0', 'antorcha_1'], frameMs=180, light={'radius': 150, 'color': '#ffb050'})
place('fogata', 'campfire', 22, 21, 1, 1, 'fogata_0', frames=['fogata_0', 'fogata_1', 'fogata_2'], frameMs=140,
      light={'radius': 210, 'color': '#ff9a40'}, name='Fogata de la plaza')
place('entrada_mina', 'mine_entrance', 5, 0, 2, 2, 'entrada_mina', name='Entrada de la mina')
for x in range(16, 25):
    for y in (25, 29):
        if (x, y) == (20, 25): continue
        place(f'valla_{x}_{y}', 'fence', x, y, 1, 1, 'valla_h')
for y in range(26, 29):
    for x in (16, 24): place(f'valla_{x}_{y}', 'fence', x, y, 1, 1, 'valla_v')
for y in range(H):
    for x in range(W):
        if T[y][x] == 'B': decos.append({'id': f'baranda_{x}_{y}', 'type': 'bridge_rail', 'x': x, 'y': y, 'sprite': 'baranda', 'solid': False, 'sortOffset': 40})
NPCS = [{'id': 'capataz', 'name': 'Capataz', 'x': 17, 'y': 17, 'facing': 'down', 'solid': True, 'sheet': 'graphics/characters/capataz.png',
         'questGiver': 'primeros_pasos',
         'dialog': {
            'intro': ['¡Hola! Veo que acabas de llegar a El Jardín. Te doy la bienvenida a LIFE INC: mi trabajo es recibir a quienes llegan.',
                      'Aquí se aprende haciendo: pescar, minar, cultivar, trabajar la madera… oficios de la vida real que dominarás practicándolos.',
                      'Empecemos por lo básico. Necesito materiales para reparar la plaza.',
                      'Toma esta hacha. Tala los pinos al norte de las casas y tráeme 10 de madera.',
                      'Luego, con tu pico, extrae 5 de piedra de las rocas claras junto a los pinos. ¡Manos a la obra!'],
            'inProgress': ['¿Cómo vas? Necesito 10 de madera de los pinos y 5 de piedra de las rocas claras. Las herramientas están en tu barra.'],
            'done': ['¡Buen trabajo! Con esto arreglamos la plaza. Toma estas monedas: te las ganaste practicando.',
                     'Ahora el mundo es tuyo: recoge fruta, siembra en el Huerto, pesca con la red en el Río Claro, caza con la lanza…',
                     '…y si buscas fortuna, lava arena con la batea en el río: el oro sólo sale del agua. Cobre y plata están en la cantera del noroeste.'],
            'after': ['El Jardín es tuyo, compañero. Si encuentras oro en el río, invita a tus amigos.'],
         }}]
for n in NPCS: occ(n['x'], n['y'], n['id'], 'GC')
def far_from_nodes(x, y, d=1):
    return all(max(abs(x - a), abs(y - b)) > d for (a, b) in occupied) and all(max(abs(x - a), abs(y - b)) > d for (a, b) in water_used)
def free_grass(x, y):
    if not (0 <= x < W and 0 <= y < H) or T[y][x] != 'G' or (x, y) in occupied: return False
    if any(0 <= x+dx < W and 0 <= y+dy < H and T[y+dy][x+dx] in 'PBCK' for dx in (-1,0,1) for dy in (-1,0,1)): return False
    if max(abs(x - SPAWN[0]), abs(y - SPAWN[1])) <= 3: return False
    for sp, pts in ANIMALS.items():
        if any(max(abs(x - a), abs(y - b)) <= 2 for a, b in pts): return False
    if 13 <= x <= 25 and 12 <= y <= 30: return False      # pueblo y huerto despejados
    return far_from_nodes(x, y)
robles = [(0,0),(13,1),(16,0),(20,2),(24,1),(27,4),(36,2),(38,6),(35,23),(38,32),(28,38),(0,25),(1,38),(26,13),(13,22)]
k = 0
for (x, y) in robles + [(29,9),(35,16),(28,31),(35,25)]:
    if free_grass(x, y):
        k += 1; occ(x, y, 'roble')
        if (x, y) in [(29,9),(35,16),(28,31),(35,25)]: decos.append({'id': f'roca_{k}', 'type': 'boulder', 'x': x, 'y': y, 'sprite': 'roca_deco', 'solid': True})
        else: decos.append({'id': f'roble_{k}', 'type': 'tree_roble', 'x': x, 'y': y, 'sprite': 'tree_roble', 'solid': True})
k = 0       # rocas musgosas en la orilla del río y del estanque (v3.1, sólo decoración)
for y in range(H):
    for x in range(W):
        if k >= 14 or (x * 7 + y * 13) % 5: continue
        if not free_grass(x, y): continue
        if not any(0 <= x+dx < W and 0 <= y+dy < H and T[y+dy][x+dx] == 'W' for dx in (-1,0,1) for dy in (-1,0,1)): continue
        k += 1; occ(x, y, 'roca_orilla')
        decos.append({'id': f'roca_orilla_{k}', 'type': 'boulder', 'x': x, 'y': y, 'sprite': f'roca_orilla_{k % 2}', 'solid': True})
k = 0
tries = 0
while k < 26 and tries < 5000:
    tries += 1
    x, y = rnd.randrange(W), rnd.randrange(H)
    if free_grass(x, y):
        k += 1; v = rnd.randrange(2); occ(x, y, 'arbusto')
        decos.append({'id': f'arbusto_{k}', 'type': 'bush', 'x': x, 'y': y, 'sprite': f'bush_{v}', 'solid': True})

# ---------------- suelo / autotile (47 combinaciones "blob" de 8 vecinos) ----------------
tile_list, tile_index = [], {}
def reg(key, kind, walkable, img_fn):
    if key not in tile_index:
        tile_index[key] = len(tile_list)
        tile_list.append({'key': key, 'kind': kind, 'walkable': walkable, 'img': TL.to64(img_fn())})
    return tile_index[key]
for i in range(4): reg(f'grass_{i}', 'grass', True, lambda i=i: TL.grass_half(i))
for i in range(2): reg(f'grass_flores_{i}', 'grass_flowers', True, lambda i=i: TL.grass_half(i, flowers=3 + i))
for i in range(4): reg(f'grass_gastado_{i}', 'grass_worn', True, lambda i=i: TL.grass_half(i, worn=True))
ORDER = ('N','E','S','W','NE','SE','SW','NW')
DIRS = {'N': (0,-1), 'E': (1,0), 'S': (0,1), 'W': (-1,0), 'NE': (1,-1), 'SE': (1,1), 'SW': (-1,1), 'NW': (-1,-1)}
def normalize(m):
    for q, a, b in (('NE','N','E'),('SE','S','E'),('SW','S','W'),('NW','N','W')):
        if not (m[a] and m[b]): m[q] = False
    return m
def mask(x, y, group):
    m = {}
    for k_, (dx, dy) in DIRS.items():
        nx, ny = x + dx, y + dy
        m[k_] = (T[ny][nx] in group) if (0 <= nx < W and 0 <= ny < H) else (T[y][x] in group)  # fuera del mapa: continúa
    return normalize(m)
def mkey(m): return ''.join('1' if m[k_] else '0' for k_ in ORDER)
# juego completo de 47 variantes para camino y agua (para editores futuros), aunque el mapa no use todas
ALL47 = sorted({mkey(normalize(dict(zip(ORDER, [(b >> i) & 1 == 1 for i in range(8)])))) for b in range(256)})
assert len(ALL47) == 47
def m_from(key): return {k_: key[i] == '1' for i, k_ in enumerate(ORDER)}
for key in ALL47: reg('path_' + key, 'path', True, lambda key=key: TL.path_half(m_from(key)))
for key in ALL47: reg('water_' + key, 'water', False, lambda key=key: TL.water_half(m_from(key)))
for key in ALL47: reg('cobble_' + key, 'cobble', True, lambda key=key: TL.cobble_half(m_from(key)))
ground = [[0] * W for _ in range(H)]
for y in range(H):
    for x in range(W):
        t = T[y][x]
        if t == 'G':
            near_spawn = max(abs(x - SPAWN[0]), abs(y - SPAWN[1])) <= 4
            worn_zone = (1 <= x <= 12 and 1 <= y <= 9 and rnd.random() < 0.6) or (16 <= x <= 24 and 25 <= y <= 29 and rnd.random() < 0.7) or (13 <= x <= 25 and 12 <= y <= 15 and rnd.random() < 0.4)
            r = rnd.random()
            if worn_zone: key = f'grass_gastado_{rnd.randrange(4)}'
            elif r < (0.30 if near_spawn else 0.08): key = f'grass_flores_{rnd.randrange(2)}'
            else: key = f'grass_{rnd.choice([0,0,1,1,2,3])}'
            ground[y][x] = tile_index[key]
        elif t == 'K':
            ground[y][x] = tile_index['grass_0']
        elif t == 'C':
            ground[y][x] = tile_index['cobble_' + mkey(mask(x, y, 'C'))]
        elif t == 'P':
            ground[y][x] = tile_index['path_' + mkey(mask(x, y, 'PBC'))]
        elif t == 'W':
            ground[y][x] = tile_index['water_' + mkey(mask(x, y, 'WBK'))]
        elif t == 'B':
            m = mask(x, y, 'WBK'); key = 'bridge_' + mkey(m)
            ground[y][x] = reg(key, 'bridge', True, lambda m=m: TL.bridge_half(m))

COLS = 16
rows = (len(tile_list) + COLS - 1) // COLS
atlas = Image.new('RGBA', (COLS * TS, rows * TS), (0, 0, 0, 0))
os.makedirs(os.path.join(G, 'tiles'), exist_ok=True)
for i, t in enumerate(tile_list):
    atlas.paste(t['img'], ((i % COLS) * TS, (i // COLS) * TS))
    t['img'].save(os.path.join(G, 'tiles', f"{i:03d}_{t['key']}.png"))
atlas.save(os.path.join(G, 'tileset.png'))

# ---------------- sprites ----------------
SPR = {}
def save_sprite(key, img, ax, ay, folder='objects'):
    path = f'graphics/{folder}/{key}.png'
    os.makedirs(os.path.join(ROOT, 'graphics', folder), exist_ok=True)
    img.save(os.path.join(ROOT, path))
    SPR[key] = {'image': path, 'w': img.width, 'h': img.height, 'anchorX': ax, 'anchorY': ay}
for sp in list(FRUIT_TREES) + ['roble']:
    for st, fr in (('full', True), ('picked', False)):
        if sp == 'roble' and st == 'picked': continue
        im = O.make_tree(sp, fr)
        key = f'tree_{sp}' if sp == 'roble' else f'tree_{sp}_{st}'
        save_sprite(key, im, im.width // 2, im.height - 4)
save_sprite('plot_empty', O.plot('empty'), 32, 94)
save_sprite('plot_planted', O.plot('planted'), 32, 94)
for s in FRUIT_TREES: save_sprite(f'plot_grown_{s}', O.plot('grown', s), 32, 94)
save_sprite('rock_cobre', O.rock('cobre'), 32, 60); save_sprite('rock_plata', O.rock('plata'), 32, 60)
save_sprite('rock_depleted', O.rock('cobre', True), 32, 60)
save_sprite('rock_piedra', O.rock('piedra'), 32, 60); save_sprite('rock_piedra_depleted', O.rock('piedra', True), 32, 60)
_p = O.make_tree('pino', True); save_sprite('tree_pino', _p, _p.width // 2, _p.height - 4)
_p = O.make_tree('pino', False); save_sprite('tree_pino_stump', _p, _p.width // 2, _p.height - 4)
save_sprite('spot_pesca', O.water_spot('pesca', True), 32, 64); save_sprite('spot_pesca_calma', O.water_spot('pesca', False), 32, 64)
save_sprite('spot_oro', O.water_spot('oro', True), 32, 64); save_sprite('spot_oro_lavado', O.water_spot('oro', False), 32, 64)
AN_ANCH = {'conejo': (20, 48), 'venado': (32, 76), 'ave': (18, 48)}
for sp in ANIMALS:
    for f in range(2):
        im = O.animal(sp, f); save_sprite(f'animal_{sp}_{f}', im, *AN_ANCH[sp], folder='characters')
save_sprite('bush_0', O.bush(0), 32, 62); save_sprite('bush_1', O.bush(1), 32, 62)
save_sprite('sign_el_jardin', O.sign(), 48, 80)
sheet = O.player_sheet(); sheet.save(os.path.join(G, 'characters', 'player.png'))
V.capataz_sheet().save(os.path.join(G, 'characters', 'capataz.png'))
VARIANTS = {}
for c in V.PLAYER_COLORS:
    V.player_variant(c).save(os.path.join(G, 'characters', f'player_{c}.png')); VARIANTS[c] = f'graphics/characters/player_{c}.png'
cas = [V.cascada(f) for f in range(3)]
for f, im in enumerate(cas): save_sprite(f'cascada_{f}', im, im.width // 2, 256)
for k in ('capataz', 'piedra'):
    im = V.casa3q(k); save_sprite('casa_' + k, im, 96, im.height - 4)   # ancla: centro de la fachada sobre la columna central
for k, fn in (('puesto', V.puesto), ('entrada_mina', V.entrada_mina)):
    im = fn(); save_sprite(k, im, im.width // 2, im.height - 4)
for f in range(2):
    im = V.fuente(f); save_sprite(f'fuente_{f}', im, im.width // 2, im.height - 6)
    im = V.antorcha(f); save_sprite(f'antorcha_{f}', im, im.width // 2, im.height - 8)
save_sprite('valla_h', V.valla('h'), 32, 64); save_sprite('valla_v', V.valla('v'), 32, 64)
save_sprite('baranda', V.baranda(), 32, 64)
rd = O.rock('cobre', True); save_sprite('roca_deco', rd, 32, 60)
for f in range(3):
    im = V.fogata(f); save_sprite(f'fogata_{f}', im, im.width // 2, im.height - 6)
for v in range(2):
    im = V.roca_orilla(v); save_sprite(f'roca_orilla_{v}', im, im.width // 2, im.height - 6)
PLAYER = {'image': 'graphics/characters/player.png', 'frameW': 48, 'frameH': 80, 'anchorX': 24, 'anchorY': 92,
          'rows': {'down': 0, 'left': 1, 'right': 2, 'up': 3}, 'walkFrames': [1, 0, 2, 0], 'idleFrame': 0}

# ---------------- ítems ----------------
ITEMS = {}
def item(iid, name, cat, **kw):
    for s, im in O.icon_sizes(iid).items():
        os.makedirs(os.path.join(G, 'icons', str(s)), exist_ok=True)
        im.save(os.path.join(G, 'icons', str(s), f'{iid}.png'))
    ITEMS[iid] = {'id': iid, 'name': name, 'category': cat, 'stackable': cat != 'tool', 'maxStack': 999 if cat != 'tool' else 1,
                  'icon': {str(s): f'graphics/icons/{s}/{iid}.png' for s in (16, 32, 64)}, **kw}
NAMES = {'manzana': 'Manzana', 'pera': 'Pera', 'naranja': 'Naranja', 'mango': 'Mango', 'banano': 'Banano', 'coco': 'Coco'}
for f, n in NAMES.items():
    item(f, n, 'fruit', origin='tropical' if f in TROPICAL else 'templada', edible=True)
for f, n in NAMES.items():
    item(f'{f}_seed', f'Semilla de {n.lower()}', 'seed', grows=f)
item('trucha', 'Trucha', 'fish', edible=True); item('bocachico', 'Bocachico', 'fish', edible=True); item('mojarra', 'Mojarra', 'fish', edible=True)
item('carne', 'Carne cruda', 'hunt'); item('piel', 'Piel', 'hunt'); item('pluma', 'Pluma', 'hunt')
item('madera', 'Madera', 'material'); item('piedra', 'Piedra', 'material')
item('mineral_cobre', 'Mineral de cobre', 'mineral'); item('mineral_plata', 'Mineral de plata', 'mineral')
item('pepita_oro', 'Pepita de oro (fluvial)', 'mineral', note='Sólo se obtiene lavando arena en el río con la batea.')
item('red_pesca', 'Red de pesca', 'tool', usedFor='fishing', usedOn=['fishing_spot'],
     craft={'requires': [{'item': 'piel', 'qty': 0}, {'item': 'pluma', 'qty': 0}], 'note': 'Receta pendiente (stub): por ahora es objeto inicial.'})
item('lanza', 'Lanza de caza', 'tool', usedFor='hunting', usedOn=['animal'],
     craft={'requires': [{'item': 'mineral_cobre', 'qty': 0}], 'note': 'Receta pendiente (stub): por ahora es objeto inicial.'})
item('pico', 'Pico', 'tool', usedFor='mining', usedOn=['mineral_rock'],
     craft={'requires': [{'item': 'mineral_cobre', 'qty': 0}], 'note': 'Receta pendiente (stub).'})
item('hacha', 'Hacha', 'tool', usedFor='woodcutting', usedOn=['wood_tree'], givenBy='capataz',
     craft={'requires': [{'item': 'madera', 'qty': 0}, {'item': 'piedra', 'qty': 0}], 'note': 'La entrega el capataz en Primeros Pasos. Receta pendiente (stub).'})
item('batea', 'Batea de madera', 'tool', usedFor='mining', usedOn=['nodo_oro_fluvial'],
     craft={'requires': [], 'note': 'Receta pendiente (stub). Se usa sólo en el río.'})

world = {
    'id': 'el-jardin', 'name': 'El Jardín', 'version': 3, 'orientation': 'orthogonal',
    'compat': {'minReaderVersion': 2, 'note': 'v3 sólo AGREGA campos (npcs, quests, decoraciones con w/h, frames, luces, plaza, cascada). Un lector v2 sigue funcionando.'},
    'brand': {'name': 'LIFE INC', 'zoneTitle': 'El Jardín', 'kind': 'educativo', 'pitch': 'Mundo abierto en línea donde se aprenden oficios y saberes de la vida real practicándolos.'},
    'render': {'projection': 'orthogonal', 'camera': 'top-down 3/4 (sprites altos con ancla en el pie)', 'metersPerTile': 2},
    'tileSize': TS, 'width': W, 'height': H,
    'tileset': {'image': 'graphics/tileset.png', 'columns': COLS, 'tileSize': TS, 'count': len(tile_list)},
    'tiles': {str(i): {'key': t['key'], 'kind': t['kind'], 'walkable': t['walkable']} for i, t in enumerate(tile_list)},
    'ground': ground,
    'collision': None,
    'waterBodies': {
        'rio_claro': {'name': 'Río Claro', 'kind': 'river', 'tiles': [[x, y] for y in range(H) for x in range(W) if BODY[y][x] == 'rio_claro']},
        'estanque': {'name': 'Estanque', 'kind': 'pond', 'tiles': [[x, y] for y in range(H) for x in range(W) if BODY[y][x] == 'estanque']},
    },
    'spawn': {'x': SPAWN[0], 'y': SPAWN[1], 'facing': 'down'},
    'areas': [
        {'id': 'plaza', 'name': 'Plaza del pueblo', 'x': PLAZA[0], 'y': PLAZA[1], 'w': PLAZA[2], 'h': PLAZA[3]},
        {'id': 'pueblo', 'name': 'Pueblo de El Jardín', 'x': 13, 'y': 12, 'w': 13, 'h': 13},
        {'id': 'huerto', 'name': 'El Huerto', 'x': 16, 'y': 25, 'w': 9, 'h': 5},
        {'id': 'cascada', 'name': 'Cascada del Río Claro', 'x': CLIFF[0], 'y': CLIFF[1], 'w': CLIFF[2], 'h': CLIFF[3] + 1},
        {'id': 'arboleda_templada', 'name': 'Arboleda templada', 'x': 1, 'y': 10, 'w': 12, 'h': 9},
        {'id': 'arboleda_tropical', 'name': 'Arboleda tropical', 'x': 9, 'y': 27, 'w': 17, 'h': 11},
        {'id': 'pinar', 'name': 'Pinar y pedregal (Primeros Pasos)', 'x': 11, 'y': 4, 'w': 16, 'h': 8},
        {'id': 'cantera', 'name': 'Cantera (cobre y plata)', 'x': 1, 'y': 1, 'w': 12, 'h': 9},
        {'id': 'rio', 'name': 'Río Claro (pesca y oro fluvial)', 'x': 28, 'y': 0, 'w': 7, 'h': 40},
        {'id': 'estanque', 'name': 'Estanque', 'x': 2, 'y': 30, 'w': 8, 'h': 6},
    ],
    'sprites': SPR, 'player': PLAYER, 'playerVariants': VARIANTS,
    'npcs': NPCS,
    'doors': [{'id': 'puerta_capataz', 'building': 'casa_capataz', 'x': 15, 'y': 15, 'approach': {'x': 15, 'y': 16}, 'action': 'talk', 'target': 'capataz',
               'note': 'Puerta interactuable (casilla sólida del edificio). Al tocarla el capataz sale a recibir al jugador; aún no hay interiores.'}],
    'quests': [{
        'id': 'primeros_pasos', 'name': 'Primeros Pasos', 'giver': 'capataz', 'autoStart': True, 'order': 'requires',
        'steps': [
            {'id': 'hablar_capataz', 'text': 'Habla con el capataz', 'type': 'talk', 'target': 'capataz', 'count': 1,
             'onComplete': {'giveItems': [{'item': 'hacha', 'qty': 1}]}},
            {'id': 'recolectar_madera', 'text': 'Recolecta 10 de madera', 'type': 'collect', 'item': 'madera', 'count': 10,
             'requires': ['hablar_capataz'], 'hint': 'Tala los pinos al norte de las casas con el hacha.', 'nodes': ['pino_1', 'pino_2', 'pino_3', 'pino_4', 'pino_5', 'pino_6']},
            {'id': 'extraer_piedra', 'text': 'Extrae 5 de piedra', 'type': 'collect', 'item': 'piedra', 'count': 5,
             'requires': ['hablar_capataz'], 'hint': 'Usa el pico en las rocas claras junto a los pinos.', 'nodes': ['roca_piedra_1', 'roca_piedra_2', 'roca_piedra_3', 'roca_piedra_4']},
        ],
        'turnIn': 'capataz',
        'tutorial': {
            'note': 'Flujo guiado del cliente. Cada etapa muestra una caja de objetivo, opcionalmente un aviso grande y una flecha amarilla intermitente sobre el objetivo; el minimapa marca el destino.',
            'stages': [
                {'id': 'seguir_camino', 'box': 'Sigue el camino al occidente: el capataz de Primeros Pasos está en el Parque de El Poblado.\nToca el suelo o el minimapa para moverte.',
                 'arrow': {'kind': 'tile', 'x': 15, 'y': 20}, 'completeWhen': {'type': 'reach', 'x': 15, 'y': 20, 'radius': 1}},
                {'id': 'entrar_puerta', 'prompt': {'title': 'Continuemos', 'text': 'Es hora de conocer al capataz. Para continuar, toca la puerta de su casa: la señala una flecha amarilla intermitente.'},
                 'box': 'Entra por la puerta cercana para continuar.\nEsta caja te recordará lo que debes hacer en los próximos pasos.',
                 'arrow': {'kind': 'door', 'id': 'puerta_capataz'}, 'completeWhen': {'type': 'door', 'id': 'puerta_capataz'}},
                {'id': 'hablar_capataz', 'box': 'Habla con el capataz.', 'arrow': {'kind': 'npc', 'id': 'capataz'}, 'completeWhen': {'type': 'step', 'step': 'hablar_capataz'}},
                {'id': 'madera', 'box': 'Tala los pinos al norte de las casas con tu hacha.\nRecolecta 10 de madera.', 'arrow': {'kind': 'nearest', 'nodeType': 'wood_tree', 'state': 'standing'},
                 'completeWhen': {'type': 'step', 'step': 'recolectar_madera'}},
                {'id': 'piedra', 'box': 'Usa el pico en las rocas claras junto a los pinos.\nExtrae 5 de piedra.', 'arrow': {'kind': 'nearest', 'nodeType': 'mineral_rock', 'mineral': 'piedra', 'state': 'active'},
                 'completeWhen': {'type': 'step', 'step': 'extraer_piedra'}},
                {'id': 'entregar', 'box': 'Vuelve con el capataz en la plaza para entregar los materiales.', 'arrow': {'kind': 'npc', 'id': 'capataz'}, 'completeWhen': {'type': 'questDone'}},
                {'id': 'libre', 'box': '¡Primeros Pasos completados! Explora El Jardín: fruta, huerto, pesca, caza, cobre, plata y oro del río.', 'arrow': None, 'completeWhen': None},
            ],
        },
        'reward': {'coins': 250, 'xp': {'woodcutting': 40, 'mining': 40}},
    }],
    'chat': {'channels': ['Global', 'Proximidad', 'Clan', 'Grupo'], 'proximityMeters': 30, 'metersPerTile': 2, 'server': 'ws://<host>:8765/ws'},
    'startingCoins': 100,
    'nodes': nodes, 'decorations': decos, 'items': ITEMS,
    'skills': {
        'gathering': {'name': 'Recolección', 'verb': 'Recoger fruta', 'nodeTypes': ['fruit_tree'], 'learn': 'Reconocer frutas maduras y cosecharlas sin dañar el árbol.'},
        'woodcutting': {'name': 'Tala', 'verb': 'Talar', 'nodeTypes': ['wood_tree'], 'tool': 'hacha', 'learn': 'Cortar madera con seguridad y dejar que el bosque se recupere.'},
        'astrologia': {'name': 'Astrología', 'stub': True, 'learn': 'Observar el cielo nocturno: constelaciones, fases de la luna y calendarios.'},
        'combate': {'name': 'Combate', 'stub': True, 'learn': 'Defensa personal y disciplina: postura, distancia y respeto por el rival.'},
        'religion': {'name': 'Religión', 'stub': True, 'learn': 'Conocer tradiciones, rituales y festividades de distintas culturas.'},
        'artesania': {'name': 'Artesanía', 'stub': True, 'learn': 'Transformar madera, piedra, fibras y metales en objetos útiles.'},
        'planting': {'name': 'Siembra', 'verb': 'Sembrar', 'nodeTypes': ['farm_plot'], 'learn': 'Sembrar semillas, esperar su crecimiento y cosechar a tiempo.'},
        'fishing': {'name': 'Pesca', 'verb': 'Pescar con red', 'nodeTypes': ['fishing_spot'], 'tool': 'red_pesca', 'learn': 'Leer el agua y usar la red para pescar en ríos y estanques.'},
        'hunting': {'name': 'Caza', 'verb': 'Cazar con lanza', 'nodeTypes': ['animal'], 'tool': 'lanza', 'learn': 'Rastrear animales y aprovechar carne, piel y plumas.'},
        'mining': {'name': 'Minería', 'verb': 'Picar roca / lavar oro', 'learn': 'Extraer piedra y metales; el oro aluvial se lava con batea en el río.', 'nodeTypes': ['mineral_rock', 'nodo_oro_fluvial'],
                   'methods': {'terrestre': {'tool': 'pico', 'minerals': ['piedra', 'cobre', 'plata']}, 'fluvial': {'tool': 'batea', 'minerals': ['oro'], 'onlyOn': 'rio_claro'}}},
        'xpCurve': 'level = floor(sqrt(xp / 25)) + 1  (stub)',
        'order': ['gathering', 'planting', 'woodcutting', 'mining', 'fishing', 'hunting', 'artesania', 'astrologia', 'combate', 'religion'],
    },
    'starterInventory': [{'item': 'red_pesca', 'qty': 1}, {'item': 'lanza', 'qty': 1}, {'item': 'pico', 'qty': 1}, {'item': 'batea', 'qty': 1}]
                        + [{'item': s, 'qty': 2} for s in SEEDS],
    'interaction': {'range': 'chebyshev', 'distance': 1, 'note': 'El jugador debe estar en una casilla caminable vecina (8 direcciones) del nodo.'},
}
solid = {(n['x'], n['y']) for n in nodes if n.get('solid')} | {(n['x'], n['y']) for n in NPCS}
for d in decos:
    if d.get('solid'):
        for yy in range(d['y'], d['y'] + d.get('h', 1)):
            for xx in range(d['x'], d['x'] + d.get('w', 1)): solid.add((xx, yy))
world['collision'] = [[0 if (tile_list[ground[y][x]]['walkable'] and (x, y) not in solid) else 1 for x in range(W)] for y in range(H)]

# ================= v4: datos 3D (aditivos) =================
import materials as MAT
os.makedirs(os.path.join(G, 'materials'), exist_ok=True)
MATS = {}
for k, im in MAT.build_all().items():
    im.save(os.path.join(G, 'materials', f'{k}.png'))
    MATS[k] = {'texture': f'graphics/materials/{k}.png', 'size': 64, 'repeatMeters': 2}
def tile_png(key):
    i = tile_index[key]; return f'graphics/tiles/{i:03d}_{key}.png'
for k, key in (('cesped', 'grass_0'), ('camino_tierra', 'path_11111111'), ('agua_turquesa', 'water_11111111'),
               ('empedrado', 'cobble_11111111'), ('puente_tablas', [t['key'] for t in tile_list if t['kind'] == 'bridge'][0])):
    MATS[k] = {'texture': tile_png(key), 'size': 64, 'repeatMeters': 2, 'fromTile': key}
MATS['agua_turquesa'].update({'color': '#2aa8b8', 'opacity': 0.82, 'animated': True})

# elevación en METROS (altura de la superficie del terreno en el centro de cada casilla; 1 casilla = 2 m de lado)
def smooth_noise(x, y):
    return 0.18 * math.sin(x * 0.55 + 1.3) * math.cos(y * 0.47 + 0.4) + 0.12 * math.sin((x + y) * 0.31)
WATER_LEVEL = {'rio_claro': -0.5, 'estanque': -0.4}
BED = {'rio_claro': -1.4, 'estanque': -1.1}
CLIFF_TOP = 7.0
elev = [[0.0] * W for _ in range(H)]
for y in range(H):
    for x in range(W):
        t = T[y][x]
        if t == 'W': e = BED[BODY[y][x]]
        elif t == 'K': e = CLIFF_TOP
        elif t == 'B': e = 0.3
        elif t == 'C': e = 0.15
        elif t == 'P': e = 0.0
        else: e = max(0.0, 0.2 + smooth_noise(x, y))
        if t in 'GP':
            if x <= 12 and y <= 9: e += 0.6 * min(1.0, (10 - y) / 3) * min(1.0, (13 - x) / 3)       # cantera elevada
            if 11 <= x <= 26 and 4 <= y <= 11: e += 0.3                                             # pinar
            if y <= 4 and (x in (24, 25, 38, 39)): e = max(e, CLIFF_TOP * (0.55 if x in (25, 38) else 0.35) * (1 - y / 6))  # hombros del acantilado
        elev[y][x] = round(e, 2)
FALL_X = [x for x in range(W) if BODY[CLIFF[1] + CLIFF[3]][x] == 'rio_claro']
world['version'] = 4
world['circadian'] = {
    'enabled': True,
    'phaseDurationMinutes': 10,
    'phases': ['day', 'night'],
    'epochMs': 0,
    'sync': 'unix',
    'note': 'Ciclo compartido. index = floor((nowMs - epochMs) / (phaseDurationMinutes * 60000)) % phases.length. Cada fase dura 10 minutos (día ↔ noche). Todas las clientes usan el reloj Unix para coincidir.',
}
world['compat'] = {'minReaderVersion': 2, 'note': 'v4 sólo AGREGA datos 3D opcionales (elevation, waterBodies[].waterLevel/bedLevel, render3d, materials3d, volumes3d, decorations[].d3). Un lector v3 (o v2) que los ignore sigue funcionando igual.'}
world['elevation'] = elev
for b, lvl in WATER_LEVEL.items():
    world['waterBodies'][b]['waterLevel'] = lvl; world['waterBodies'][b]['bedLevel'] = BED[b]
world['render3d'] = {
    'units': 'meters', 'metersPerTile': 2, 'upAxis': 'y',
    'gridToWorld': 'worldX = (x + 0.5) * 2 ; worldZ = (y + 0.5) * 2 ; worldY = elevation[y][x]  (x = columna, y = fila; norte = -Z)',
    'pixelsPerMeter': 32, 'note': 'Los sprites 2D (64 px = 1 casilla = 2 m) sirven como billboards: altura en metros = h_px / 32.',
    'camera': {'mode': 'orbit', 'defaultPitchDeg': 50, 'defaultYawDeg': 0, 'defaultDistance': 28, 'minDistance': 8, 'maxDistance': 70,
               'minPitchDeg': 25, 'maxPitchDeg': 80, 'rotate': True, 'target': 'player'},
    'waterfall': {'decoration': 'cascada', 'columns': FALL_X, 'lipRow': CLIFF[1] + CLIFF[3] - 1, 'topElevation': CLIFF_TOP,
                  'bottomElevation': WATER_LEVEL['rio_claro'], 'material': 'agua_turquesa', 'foamRow': CLIFF[1] + CLIFF[3]},
    'cliff': {'x': CLIFF[0], 'y': CLIFF[1], 'w': CLIFF[2], 'h': CLIFF[3], 'topElevation': CLIFF_TOP, 'material': 'roca_acantilado'},
    'lighting': {'sun': {'azimuthDeg': 135, 'elevationDeg': 50, 'color': '#fff1d0'}, 'night': {'ambient': '#2a3560', 'torchColor': '#ffb050'}},
}
world['materials3d'] = MATS
world['terrainMaterials'] = {'grass': 'cesped', 'grass_flowers': 'cesped', 'grass_worn': 'cesped', 'path': 'camino_tierra',
                             'water': 'agua_turquesa', 'cobble': 'empedrado', 'bridge': 'puente_tablas', 'cliff': 'roca_acantilado', 'shore': 'arena_orilla'}
world['volumes3d'] = {
    'note': 'Volumen por tipo. shape = primitiva sugerida; height en metros; billboard = usar el sprite 2D de pie mirando a la cámara.',
    'decorationTypes': {
        'building': {'shape': 'house_gable', 'wallHeight': 4.0, 'roofHeight': 3.2, 'ridge': 'x', 'eaveOverhang': 0.4},
        'stall': {'shape': 'stall', 'height': 2.6, 'materials': {'frame': 'madera_tablas', 'awning': 'toldo_rayas'}},
        'fountain': {'shape': 'fountain', 'height': 2.4, 'basinHeight': 0.6, 'radius': 1.8, 'materials': {'stone': 'piedra_fuente', 'water': 'agua_turquesa'}},
        'torch': {'shape': 'pole', 'height': 2.2, 'billboard': True},
        'campfire': {'shape': 'campfire', 'height': 0.8, 'billboard': True},
        'waterfall': {'shape': 'cliff', 'height': CLIFF_TOP, 'materials': {'rock': 'roca_acantilado', 'water': 'agua_turquesa'}},
        'mine_entrance': {'shape': 'mine', 'height': 3.0, 'materials': {'rock': 'roca_acantilado', 'frame': 'madera_tablas'}},
        'fence': {'shape': 'fence', 'height': 1.1, 'materials': {'wood': 'madera_tablas'}},
        'bridge_rail': {'shape': 'rail', 'height': 1.0, 'materials': {'wood': 'madera_tablas'}},
        'tree_roble': {'shape': 'tree', 'height': 6.0, 'billboard': True},
        'bush': {'shape': 'bush', 'height': 1.0, 'billboard': True},
        'boulder': {'shape': 'rock', 'height': 1.2, 'materials': {'rock': 'roca_acantilado'}},
        'sign': {'shape': 'sign', 'height': 1.6, 'billboard': True},
    },
    'nodeTypes': {
        'fruit_tree': {'shape': 'tree', 'height': 5.0, 'billboard': True, 'perSpecies': {'coco': 7.0, 'banano': 4.5}},
        'wood_tree': {'shape': 'tree', 'height': 8.0, 'billboard': True, 'states': {'stump': 0.6}},
        'farm_plot': {'shape': 'plot', 'height': 0.3, 'billboard': True},
        'mineral_rock': {'shape': 'rock', 'height': 1.0, 'billboard': True},
        'fishing_spot': {'shape': 'water_decal', 'height': 0.0, 'onWaterLevel': True},
        'nodo_oro_fluvial': {'shape': 'water_decal', 'height': 0.0, 'onWaterLevel': True},
        'animal': {'shape': 'billboard', 'perSpecies': {'conejo': 0.5, 'venado': 1.6, 'ave': 0.5}},
    },
    'characters': {'player': {'height': 1.8, 'billboard': True}, 'npc': {'height': 1.8, 'billboard': True}},
}
for d in decos:
    if d['id'] == 'casa_capataz':
        d['d3'] = {'wallHeight': 4.0, 'roofHeight': 3.2, 'materials': {'walls': 'muro_yeso_vigas', 'base': 'zocalo_piedra', 'roof': 'techo_tejas_rojas', 'trim': 'madera_tablas'},
                   'door': {'door': 'puerta_capataz', 'face': 'south'}, 'chimney': {'fx': 0.65, 'height': 1.4}}
    elif d['id'] == 'casa_piedra':
        d['d3'] = {'wallHeight': 4.2, 'roofHeight': 3.4, 'materials': {'walls': 'muro_piedra_clara', 'base': 'zocalo_piedra', 'roof': 'techo_pizarra_azul', 'trim': 'madera_tablas'},
                   'door': {'face': 'south', 'fx': 0.5}, 'dormer': True, 'chimney': {'fx': 0.2, 'height': 1.4}}
os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
with open(os.path.join(ROOT, 'data', 'el-jardin.json'), 'w', encoding='utf-8') as f:
    json.dump(world, f, ensure_ascii=False, indent=1)
# copia JS para abrir el preview incluso sin servidor (file://)
with open(os.path.join(ROOT, 'data', 'el-jardin.js'), 'w', encoding='utf-8') as f:
    f.write('window.EL_JARDIN = ' + json.dumps(world, ensure_ascii=False) + ';\n')

# ---------------- vistas previas ----------------
def render(world, showcase=True, player=True):
    img = Image.new('RGBA', (W * TS, H * TS))
    for y in range(H):
        for x in range(W):
            img.paste(tile_list[ground[y][x]]['img'], (x * TS, y * TS))
    cache = {}
    def sp(key):
        if key not in cache: cache[key] = Image.open(os.path.join(ROOT, SPR[key]['image'])).convert('RGBA')
        return cache[key], SPR[key]
    over, objs = [], []
    crops = list(FRUIT_TREES)
    for n in nodes:
        t = n['type']
        if t in ('fishing_spot', 'nodo_oro_fluvial'): over.append((n['x'], n['y'], n['sprites']['active']))
        elif t == 'fruit_tree': objs.append((n['x'], n['y'], n['sprites']['full'] if not (showcase and n['id'].endswith('_3')) else n['sprites']['picked']))
        elif t == 'farm_plot':
            i = int(n['id'].split('_')[1])
            key = 'plot_empty'
            if showcase:
                key = ['plot_empty', 'plot_planted', None, None, 'plot_planted', None, None, 'plot_empty', None, 'plot_planted', None, 'plot_empty'][i - 1] or f"plot_grown_{crops[(i) % 6]}"
            objs.append((n['x'], n['y'], key))
        elif t == 'mineral_rock': objs.append((n['x'], n['y'], n['sprites']['active']))
        elif t == 'wood_tree': objs.append((n['x'], n['y'], n['sprites']['stump'] if (showcase and n['id'] == 'pino_3') else n['sprites']['standing']))
        elif t == 'animal': objs.append((n['x'], n['y'], n['sprites']['alive'][0]))
    for d in decos: objs.append((d['x'], d['y'], d['sprite'], d.get('w', 1), d.get('h', 1), d.get('sortOffset', 0)))
    for n in NPCS: objs.append((n['x'], n['y'], '__capataz'))
    for (x, y, k) in over:
        im, s = sp(k); img.alpha_composite(im, (x * TS + 32 - s['anchorX'], (y + 1) * TS - s['anchorY']))
    if player:
        objs.append((SPAWN[0], SPAWN[1], '__player'))
    objs = [o if len(o) == 6 else (*o, 1, 1, 0) for o in objs]
    cap = Image.open(os.path.join(G, 'characters', 'capataz.png')).convert('RGBA')
    for (x, y, k, w, h, so) in sorted(objs, key=lambda o: ((o[1] + o[4]) * TS + o[5], o[0])):
        if k in ('__player', '__capataz'):
            fr = (sheet if k == '__player' else cap).crop((0, 0, 48, 80)); img.alpha_composite(fr, (x * TS + 32 - 24, (y + 1) * TS - 92 + 0))
            continue
        im, s = sp(k)
        px_, py_ = int((x + w / 2) * TS - s['anchorX']), (y + h) * TS - s['anchorY']
        if px_ < 0 or py_ < 0:
            cut = im.crop((max(0, -px_), max(0, -py_), im.width, im.height)); img.alpha_composite(cut, (max(0, px_), max(0, py_)))
        else:
            img.alpha_composite(im, (px_, py_))
    return img
def night(img):
    """versión nocturna: oscurece y suma luz cálida de antorchas y ventanas"""
    from PIL import ImageChops, ImageDraw, ImageFilter
    base = img.convert('RGB')
    dark = Image.new('RGB', base.size, (60, 70, 130))
    out = ImageChops.multiply(base, dark)
    light = Image.new('L', base.size, 0); dr = ImageDraw.Draw(light)
    for d in decos:
        pts = []
        if d['type'] == 'torch': pts.append(((d['x'] + 0.5) * TS, (d['y'] + 1) * TS - 80, 150))
        for (lx, ly) in d.get('lights', []): pts.append(((d['x'] + d.get('w', 1) * lx) * TS, (d['y'] + d.get('h', 1) * ly) * TS, 90))
        for (cx, cy, r) in pts: dr.ellipse((cx - r, cy - r * 0.8, cx + r, cy + r * 0.8), fill=255)
    light = light.filter(ImageFilter.GaussianBlur(40))
    warm = ImageChops.multiply(base, Image.new('RGB', base.size, (255, 200, 140)))
    return Image.composite(warm, out, light)
os.makedirs(os.path.join(ROOT, 'previews'), exist_ok=True)
full = render(world)
full.convert('RGB').save(os.path.join(ROOT, 'previews', 'el-jardin-overview-full.png'))
full.resize((1280, 1280), Image.LANCZOS).convert('RGB').save(os.path.join(ROOT, 'previews', 'el-jardin-overview.png'))
def crop(name, x0, y0, x1, y1):
    full.crop((x0 * TS, y0 * TS, x1 * TS, y1 * TS)).convert('RGB').save(os.path.join(ROOT, 'previews', name))
crop('el-jardin-pueblo-plaza.png', 10, 10, 30, 31)
crop('el-jardin-cascada-rio.png', 22, 0, 40, 14)
nfull = night(full)
nfull.resize((1280, 1280), Image.LANCZOS).save(os.path.join(ROOT, 'previews', 'el-jardin-overview-noche.png'))
nfull.crop((10 * TS, 10 * TS, 30 * TS, 31 * TS)).save(os.path.join(ROOT, 'previews', 'el-jardin-pueblo-noche.png'))
crop('el-jardin-huerto-y-claro.png', 12, 20, 27, 32)
crop('el-jardin-arboleda-templada.png', 0, 9, 14, 21)
crop('el-jardin-arboleda-tropical-estanque.png', 1, 25, 26, 39)
crop('el-jardin-rio-pesca-oro.png', 24, 0, 40, 40)
crop('el-jardin-cantera.png', 0, 0, 14, 11)
# hoja de referencia de sprites/íconos
ic = [k for k in ITEMS]
ref = Image.new('RGB', (len(ic) * 72 + 8, 90), (52, 44, 36))
for i, k in enumerate(ic):
    ref.paste(Image.open(os.path.join(G, 'icons', '64', f'{k}.png')), (8 + i * 72, 13), Image.open(os.path.join(G, 'icons', '64', f'{k}.png')))
ref.save(os.path.join(ROOT, 'previews', 'items-iconos.png'))
counts = {}
for n in nodes:
    k = n['type'] + (':' + (n.get('species') or n.get('mineral') or n.get('waterBody') or '') )
    counts[k] = counts.get(k, 0) + 1
print('tiles:', len(tile_list), 'nodes:', len(nodes), 'decos:', len(decos))
for k, v in sorted(counts.items()): print(' ', k, v)
# iconos de la interfaz LIFE INC
from pixel import up as _up
os.makedirs(os.path.join(G, 'ui'), exist_ok=True)
for k in ['bolsa', 'habilidades', 'misiones', 'social', 'luna', 'sol', 'moneda', 'ayuda']:
    _up(V.ui_icon(k), 2).save(os.path.join(G, 'ui', f'{k}.png'))
