# LIFE INC · El Jardín — esquema del mapa (`data/el-jardin.json`) · versión 4

Documento para cargar El Jardín desde el cliente de Sara (Vite + React + TypeScript + Socket.io) y desde el servidor.
Todo el JSON está en UTF-8. Las rutas de imágenes son **relativas a la carpeta `El-Jardin/`**.
`data/el-jardin.js` es exactamente el mismo objeto como `window.EL_JARDIN = {...}` (sólo para abrir la vista previa sin servidor); el juego debe usar el `.json`.
**Es un único mapa**: v3 extiende el mismo El Jardín de v2 (40×40, 64 px, ortogonal); no hay un segundo mapa.

## 0. Visión educativa (LIFE INC)

LIFE INC es un **juego educativo en línea**: cada habilidad representa una práctica real que se aprende haciéndola
(recolectar fruta madura, sembrar y cosechar, pescar con red, cazar, talar con cuidado, extraer piedra y metales, lavar oro con batea).
Cada habilidad del JSON trae un campo `learn` con una frase de lo que enseña en la vida real.
v3 añade **habilidades futuras** como *stubs* (`stub: true`, nivel 1, sin sistema todavía): `astrologia`, `combate`, `religion`, `artesania`.
El capataz lo explica en su diálogo: aquí se aprende practicando oficios reales.
Marca pública: `brand.name = "LIFE INC"`; la zona siempre se llama **"El Jardín"** (con tilde).

## 0.1 Cambios v3 → v4 (datos 3D, sólo se agregan campos)

- `version: 4`. `compat.minReaderVersion` sigue en 2: **todos los campos nuevos son opcionales**; un lector v3 (o v2) que los ignore funciona igual (mismo `ground`, `collision`, `nodes`, `decorations`, `quests`, `chat`).
- Campos nuevos: `elevation`, `waterBodies.<id>.waterLevel` / `bedLevel`, `render3d`, `materials3d`, `terrainMaterials`, `volumes3d`, `decorations[].d3` (casas). Detalle en **§14**.
- También se agregó `circadian` (opcional): ciclo compartido día/noche de 10 minutos por fase. Detalle en **§15**. Un lector que lo ignore sigue funcionando.
- El cliente principal (Three.js, cámara orbital con zoom y rotación) extruye **esta misma rejilla**; no hay mapa isométrico ni segundo mapa. `orientation` sigue `"orthogonal"`.
- Arte 2D: las casas se repintaron con volumen 3/4 (mismas claves de sprite, ancla `anchorX: 96`), se agregaron `fogata` (decoración `campfire` en (22,21)) y rocas musgosas de orilla (`boulder`, sprites `roca_orilla_0/1`).

## 0.2 Cambios v2 → v3 (sólo se agregan campos)

- `version: 3`, `compat: { minReaderVersion: 2 }`: un lector v2 sigue funcionando (mismo `ground`, `collision`, `nodes`, `items`).
- Nuevos campos raíz: `brand`, `render`, `playerVariants`, `npcs`, `doors`, `quests`, `chat`, `startingCoins`.
- Teselas nuevas `cobble` (plaza empedrada) y el puente se movió de ids (ver §3).
- `decorations[]` puede tener `w`, `h` (huella en casillas), `frames` + `frameMs` (animación), `sortOffset`, `light` (antorcha) y `lights` (ventanas).
- Nodos nuevos: `wood_tree` (pinos → `madera`) y rocas de `piedra` (`mineral_rock` con `mineral: "piedra"`).
- Ítems nuevos: `madera`, `piedra` (categoría `material`) y `hacha` (herramienta, la entrega el capataz).
- `spawn` ahora es **(10,28)**, sobre el camino de tierra junto al estanque (inicio del tutorial).
- Pueblo (casa del capataz, casa de piedra, puesto, fuente, antorchas), cascada animada al norte del río turquesa, puente de madera con barandas, entrada de mina.

## 1. Coordenadas

- Rejilla **ortogonal** (cuadrada). `x` = columna (0…39, oeste→este), `y` = fila (0…39, norte→sur). Origen arriba-izquierda.
- `tileSize` = 64 px → mapa de 2560 × 2560 px. `render.metersPerTile = 2` (1 casilla = 2 m; el chat de proximidad usa 30 m = 15 casillas).
- Todos los `x`,`y` de nodos, decoración, NPC, puertas y `spawn` son coordenadas de casilla (enteros).

## 2. Campos raíz

| campo | tipo | descripción |
|---|---|---|
| `id`, `name` | `"el-jardin"`, `"El Jardín"` | |
| `version` | `4` | sube cuando cambia el formato (v4 = datos 3D opcionales) |
| `compat` | `{ minReaderVersion: 2, note }` | v3 y v4 son aditivos |
| `brand` | `{ name: "LIFE INC", zoneTitle: "El Jardín", kind: "educativo", pitch }` | marca pública |
| `render` | `{ projection: "orthogonal", camera, metersPerTile: 2 }` | |
| `orientation`, `tileSize`, `width`, `height` | | `"orthogonal"`, 64, 40, 40 |
| `tileset` | objeto | `{ image: "graphics/tileset.png", columns: 16, tileSize: 64, count: 154 }` |
| `tiles` | `{ [id]: { key, kind, walkable } }` | |
| `ground` | `number[40][40]` | **`ground[y][x]`** = id de tesela |
| `collision` | `(0\|1)[40][40]` | 1 = bloqueado (agua, nodos sólidos, huellas de edificios/decoración sólida, NPC) |
| `waterBodies` | objeto | `rio_claro` y `estanque` con sus casillas `[x,y]` |
| `spawn` | `{ x: 10, y: 28, facing: "down" }` | camino de tierra junto al agua |
| `areas` | `{id,x,y,w,h,name}[]` | `plaza`, `pueblo`, `huerto`, `cascada`, `arboleda_templada`, `arboleda_tropical`, `pinar`, `cantera`, `rio`, `estanque` |
| `sprites` | `{ [key]: { image, w, h, anchorX, anchorY } }` | catálogo |
| `player`, `playerVariants` | | hoja base + 5 colores (`azul`, `rojo`, `amarillo`, `verde`, `morado`) |
| `npcs` | array | §9 |
| `doors` | array | §10 |
| `quests` | array | §11 (Primeros Pasos + tutorial) |
| `chat` | objeto | §12 |
| `startingCoins` | `100` | monedas iniciales |
| `nodes` | array | 65 interactuables (§5) |
| `decorations` | array | 90 elementos (§4.1) |
| `items`, `skills`, `starterInventory`, `interaction` | | §7, §8 |
| `elevation` (v4) | `number[40][40]` | **`elevation[y][x]`** en **metros** (§14) |
| `render3d`, `materials3d`, `terrainMaterials`, `volumes3d` (v4) | objetos | datos 3D opcionales (§14) |
| `circadian` (v4, aditivo) | objeto | ciclo día/noche compartido, 10 min por fase (§15) |

## 3. Teselas de suelo

Atlas `graphics/tileset.png`, 16 columnas de 64 px. Para el id `n`: `sx = (n % 16) * 64`, `sy = floor(n / 16) * 64`. También sueltas en `graphics/tiles/`.

| `kind` | ids | caminable | notas |
|---|---|---|---|
| `grass` | 0–3 | sí | césped, 4 variantes que tilean sin costuras |
| `grass_flowers` | 4–5 | sí | césped con flores |
| `grass_worn` | 6–9 | sí | césped pisado con piedritas |
| `path` | 10–56 | sí | camino de tierra, 47 variantes autotile |
| `water` | 57–103 | **no** | agua turquesa con orilla, 47 variantes autotile |
| `cobble` | 104–150 | sí | **v3**: empedrado de la plaza, 47 variantes autotile |
| `bridge` | 151–153 | sí | puente de tablas sobre el río (fila y=19) |

**Autotile**: `key` = `<grupo>_XXXXXXXX`, 8 bits de vecinos del mismo grupo en orden `N E S W NE SE SW NW` (juego "blob" de 47; las diagonales cuentan sólo si sus dos ortogonales son 1). Fuera del mapa se considera "continúa".
**Ojo, cambio de ids respecto a v2**: el puente pasó de 104–106 a 151–153. Usa siempre `tiles[id].kind`, no ids fijos.

## 4. Sprites y orden de dibujo (Y-sort)

Sprite de una casilla: su píxel `(anchorX, anchorY)` va sobre el **centro inferior de la casilla**:
```
drawX = x*64 + 32 - anchorX
drawY = (y+1)*64 - anchorY
```
Decoración con huella `w×h` (v3): el ancla va en el centro inferior de la huella:
```
drawX = (x + w/2)*64 - anchorX
drawY = (y + h)*64   - anchorY
clave de orden = (y + h)*64 + (sortOffset || 0)
```
Orden: suelo → nodos de agua (`fishing_spot`, `nodo_oro_fluvial`) → todo lo demás ordenado por la clave (pie del objeto; `y` fraccionario para lo que se mueve) y luego por `x`.

### 4.1 `decorations[]`
Campos: `id`, `type`, `x`, `y`, `sprite`, `solid`, opcionales `w`, `h`, `frames` (keys de sprites), `frameMs`, `sortOffset`, `name`, `text`, `light: {radius, color}`, `lights: [[fx,fy],…]` (posición relativa 0–1 dentro de la huella, para ventanas iluminadas de noche).
Tipos: `campfire` (v4: `fogata` en (22,21), 3 cuadros, `light`), `building` (`casa_capataz` 3×3 en (14,13), `casa_piedra` 3×3 en (18,13)), `stall` (puesto 2×1), `fountain` (fuente 2×2 animada en (19,18)), `torch` (6 antorchas animadas con `light`), `waterfall` (cascada 12×4 en (26,0), 3 cuadros a 160 ms), `mine_entrance` (2×2), `fence`, `bridge_rail` (`sortOffset: 40`), `tree_roble`, `bush`, `boulder`, `sign` ("El Jardín").

## 5. Nodos (`nodes[]`)

Campos comunes: `id` (único), `type`, `x`, `y`, `skill`, `states`, `initialState`, `sprites` (estado → key de `sprites`), `solid`, `xp`, `respawnMs`.

**Alcance**: el jugador interactúa si está en una casilla caminable a distancia Chebyshev 1 (8 vecinos) del nodo: `max(|px-nx|,|py-ny|) === 1`.
El servidor debe validar esa distancia y la herramienta; el cliente sólo propone la acción.

### 5.1 `fruit_tree` — recoger fruta (`skill: "gathering"`) — 18 nodos
```json
{ "id":"arbol_mango_1","type":"fruit_tree","species":"mango","grove":"tropical","x":13,"y":29,
  "skill":"gathering","item":"mango","solid":true,"states":["full","picked"],"initialState":"full",
  "sprites":{"full":"tree_mango_full","picked":"tree_mango_picked"},
  "yield":{"item":"mango","min":1,"max":3},"bonus":{"item":"mango_seed","chance":0.25},"xp":10,"respawnMs":25000 }
```
Ciclo: `full` → (clic) da `rand(min..max)` de la fruta + con `bonus.chance` 1 semilla → `picked` → tras `respawnMs` → `full`.
Especies: templadas `manzana`, `pera`, `naranja` (arboleda oeste); tropicales `mango`, `banano`, `coco` (arboleda sur). 3 árboles de cada una.
El tronco es sólido (la casilla del árbol está en `collision`).

### 5.2 `farm_plot` — sembrar (`skill: "planting"`) — 12 nodos (`parcela_1`…`parcela_12`, El Huerto)
```json
{ "id":"parcela_1","type":"farm_plot","x":17,"y":26,"skill":"planting","solid":true,
  "states":["empty","planted","grown"],"initialState":"empty",
  "accepts":["manzana_seed","pera_seed","naranja_seed","mango_seed","banano_seed","coco_seed"],"growMs":15000,
  "sprites":{"empty":"plot_empty","planted":"plot_planted","grown":{"mango":"plot_grown_mango", "...":"..."}},
  "harvest":{"fruitMin":2,"fruitMax":3,"seedChance":0.6},"xp":{"plant":8,"harvest":12} }
```
Ciclo: `empty` → (clic con semilla aceptada; se consume 1) → `planted` (guardar `crop = items[seed].grows` y `readyAt = now + growMs`) →
al llegar `readyAt` → `grown` (sprite `sprites.grown[crop]`) → (clic) da `rand(fruitMin..fruitMax)` de `crop` + con `seedChance` 1 semilla `crop_seed` → `empty`.
Estado por parcela en servidor: `{ state, crop, readyAt }`.

### 5.3 `fishing_spot` — pescar con red (`skill: "fishing"`, `tool: "red_pesca"`) — 5 nodos
Río: `pesca_rio_1` (32,7), `pesca_rio_2` (28,24), `pesca_rio_3` (32,34) → tabla `trucha` 65 / `bocachico` 35.
Estanque: `pesca_estanque_1` (8,31), `pesca_estanque_2` (3,34) → `mojarra`.
Están **sobre casillas de agua** de la orilla (`waterBody` indica cuál). Ciclo: `active` → (clic con `red_pesca` en el inventario) 1 pez según `yield.table` (pesos) → `depleted` → `respawnMs` (15 s) → `active`.

### 5.4 `nodo_oro_fluvial` — oro en el río (`skill: "mining"`, `method: "fluvial"`, `tool: "batea"`) — 4 nodos
`oro_fluvial_1` (34,10), `oro_fluvial_2` (31,13), `oro_fluvial_3` (31,28), `oro_fluvial_4` (31,37). **Todos sobre casillas de `rio_claro`** (no hay oro en tierra ni en el estanque).
Ciclo: `active` → (clic con `batea`) con probabilidad `successChance` (0.75) da 1 `pepita_oro` y pasa a `depleted`; si falla, sólo sale arena y el nodo sigue `active` → `respawnMs` (30 s) → `active`.
Puede compartir el río con la pesca, pero son nodos distintos en casillas distintas.

### 5.5 `mineral_rock` — piedra, cobre y plata en tierra (`skill: "mining"`, `method: "terrestre"`, `tool: "pico"`) — 11 nodos
Campo nuevo `mineral` (`"piedra"`, `"cobre"`, `"plata"`).
**Piedra** (v3): `roca_piedra_1..4` en (23,6) (25,8) (22,10) (26,5), junto al pinar → 1–2 `piedra`, respawn 15 s, sprites `rock_piedra` / `rock_piedra_depleted`. Es la que pide Primeros Pasos.
Cantera noroeste. Cobre: `roca_cobre_1..4` → `mineral_cobre` (respawn 18 s). Plata: `roca_plata_1..3` → `mineral_plata` (25 s).
Ciclo: `active` → (clic con `pico`) 1 mineral → `depleted` (sprite `rock_depleted`) → `active`. Rocas sólidas.

### 5.6 `animal` — cazar con lanza (`skill: "hunting"`, `tool: "lanza"`) — 9 nodos
`conejo_1..4`, `venado_1..2`, `ave_1..3`. `x`,`y` = casilla **hogar**; el animal deambula hasta `wanderRadius` (2) casillas (Chebyshev) por césped caminable, sin pisar el camino.
**No son sólidos.** Estados `alive` → (clic con `lanza`) → `hunted` (oculto) → `respawnMs` (25 s) → `alive` en su casa.
`yield` es una lista `{ item, min, max, chance }`: conejo → carne (+piel 50%); venado → 2–3 carne + piel; ave → 1–3 plumas (+carne 60%).
Es recolección tipo "gather", sin combate ni vida. En multijugador, el servidor debe ser la autoridad de la posición de los animales.

### 5.7 `wood_tree` — talar pinos (`skill: "woodcutting"`, `tool: "hacha"`) — 6 nodos (v3)
```json
{ "id":"pino_1","type":"wood_tree","species":"pino","x":13,"y":9,"skill":"woodcutting","tool":"hacha","solid":true,
  "states":["standing","stump"],"initialState":"standing","sprites":{"standing":"tree_pino","stump":"tree_pino_stump"},
  "yield":{"item":"madera","min":2,"max":3},"xp":12,"respawnMs":20000 }
```
`pino_1..6` en el pinar al norte del pueblo: (13,9) (15,7) (17,10) (12,6) (18,6) (20,9). Ciclo `standing` → (clic con `hacha`) 2–3 `madera` → `stump` (tocón, sigue sólido) → 20 s → `standing`.

## 6. Jugador (`player`, `playerVariants`)
`graphics/characters/player.png` y `player_<color>.png`: 3 columnas × 4 filas de 48×80. Filas `down`=0, `left`=1, `right`=2, `up`=3; cuadro 0 = quieto; al caminar `walkFrames: [1,0,2,0]`. Ancla `(24, 92)` con la fórmula de §4.
El capataz usa la misma estructura de hoja (`graphics/characters/capataz.png`).

## 7. Ítems (`items`)
```json
{ "id":"madera","name":"Madera","category":"material","stackable":true,"maxStack":999,
  "icon":{"16":"graphics/icons/16/madera.png","32":"graphics/icons/32/madera.png","64":"graphics/icons/64/madera.png"} }
```
| categoría | ids |
|---|---|
| `fruit` | `manzana`, `pera`, `naranja` (templadas) · `mango`, `banano`, `coco` (tropicales) |
| `seed` (campo `grows`) | `manzana_seed` … `coco_seed` |
| `fish` | `trucha`, `bocachico`, `mojarra` |
| `hunt` | `carne`, `piel`, `pluma` |
| `material` (v3) | `madera`, `piedra` |
| `mineral` | `mineral_cobre`, `mineral_plata`, `pepita_oro` (sólo fluvial) |
| `tool` (no apilable) | `red_pesca`, `lanza`, `pico`, `batea`, `hacha` (v3, `givenBy: "capataz"`) |

`starterInventory`: `red_pesca`, `lanza`, `pico`, `batea` + 2 de cada semilla. El `hacha` la entrega el capataz al completar el paso 1.

## 8. Habilidades (`skills`)
Cada habilidad: `{ name, learn, … }`; las futuras llevan `stub: true` (nivel 1 fijo, sin mecánica todavía). `skills.order` da el orden de la UI; `skills.xpCurve` describe el nivel: `floor(sqrt(xp/25)) + 1`.

| id | nombre | estado |
|---|---|---|
| `gathering` | Recolección | activa (árboles frutales) |
| `woodcutting` | Tala | activa (pinos, `hacha`) |
| `planting` | Siembra | activa (parcelas) |
| `fishing` | Pesca | activa (`red_pesca`) |
| `hunting` | Caza | activa (`lanza`) |
| `mining` | Minería | activa: `methods.terrestre` (`pico`: piedra, cobre, plata) y `methods.fluvial` (`batea`: oro, `onlyOn: "rio_claro"`) |
| `astrologia` | Astrología | *stub* educativo |
| `combate` | Combate | *stub* educativo |
| `religion` | Religión | *stub* educativo |
| `artesania` | Artesanía | *stub* educativo |

## 9. NPC (`npcs[]`)
```json
{ "id":"capataz","name":"Capataz","x":17,"y":17,"facing":"down","solid":true,
  "sheet":"graphics/characters/capataz.png","questGiver":"primeros_pasos",
  "dialog":{ "intro":["…"], "inProgress":["…"], "done":["…"], "after":["…"] } }
```
`dialog.intro` se muestra la primera vez (bienvenida: "mi trabajo es recibir a quienes llegan"; aquí se aprende haciendo), `inProgress` mientras faltan materiales, `done` al entregar, `after` después. El cliente muestra cada línea con "Toca aquí para continuar". La casilla del NPC es sólida.

## 10. Puertas (`doors[]`)
```json
{ "id":"puerta_capataz","building":"casa_capataz","x":15,"y":15,"approach":{"x":15,"y":16},"action":"talk","target":"capataz" }
```
La puerta es una casilla sólida del edificio. El jugador camina a `approach` y al tocarla se ejecuta `action` (`talk` → el capataz sale a recibirlo). **Aún no hay interiores.**

## 11. Misiones (`quests[]`) — Primeros Pasos
```json
{ "id":"primeros_pasos","name":"Primeros Pasos","giver":"capataz","autoStart":true,"order":"requires","turnIn":"capataz",
  "steps":[
    { "id":"hablar_capataz","text":"Habla con el capataz","type":"talk","target":"capataz","count":1,
      "onComplete":{"giveItems":[{"item":"hacha","qty":1}]} },
    { "id":"recolectar_madera","text":"Recolecta 10 de madera","type":"collect","item":"madera","count":10,"requires":["hablar_capataz"],"nodes":["pino_1","…"] },
    { "id":"extraer_piedra","text":"Extrae 5 de piedra","type":"collect","item":"piedra","count":5,"requires":["hablar_capataz"],"nodes":["roca_piedra_1","…"] } ],
  "reward":{"coins":250,"xp":{"woodcutting":40,"mining":40}},
  "tutorial":{ "stages":[ … ] } }
```
- Tipos de paso: `talk` (hablar con `target`) y `collect` (sumar `count` del `item` recogido **después** de que se cumplan los `requires`).
- El panel muestra cada paso con casilla ✔ y contador `(n/count)` actualizado en vivo.
- Al completar todos, se vuelve con `turnIn` para recibir `reward`.
- `tutorial.stages[]` (guía visual del cliente): `{ id, box, prompt?, arrow, completeWhen }`
  - `box`: texto de la caja de objetivo que queda fija en pantalla ("esta caja te recordará lo que debes hacer").
  - `prompt`: `{ title: "Continuemos", text }` aviso grande opcional.
  - `arrow`: dónde va la flecha amarilla intermitente (y la marca del minimapa): `{kind:"tile",x,y}`, `{kind:"door",id}`, `{kind:"npc",id}`, `{kind:"nearest",nodeType,mineral?,state?}` o `null`.
  - `completeWhen`: `{type:"reach",x,y,radius}`, `{type:"door",id}`, `{type:"step",step}`, `{type:"questDone"}` o `null`.
  - Etapas: `seguir_camino` (llegar a (15,20) en la plaza) → `entrar_puerta` (aviso "Continuemos" + flecha en la puerta) → `hablar_capataz` → `madera` → `piedra` → `entregar` → `libre`.

## 12. Chat (`chat`) y protocolo WebSocket de la vista previa
```json
{ "channels":["Global","Proximidad","Clan","Grupo"], "proximityMeters":30, "metersPerTile":2, "server":"ws://<host>:8765/ws" }
```
Las pestañas son **exactamente** Global, Proximidad, Clan, Grupo (no hay pestaña de comercio).
`server.py` (Python 3, sólo librería estándar) sirve la vista previa y el WebSocket en el **puerto 8765**, ruta `/ws`. Mensajes JSON con campo `t`:

| dirección | `t` | campos |
|---|---|---|
| cliente → servidor | `hello` | `name, color, clan, group, level` |
| cliente → servidor | `move` | `x, y` (casillas, pueden ser fraccionarias), `dir`, `moving`, `level` |
| cliente → servidor | `chat` | `channel` (`global`/`proximidad`/`clan`/`grupo`), `text` (≤160) |
| cliente → servidor | `ping` | `c` |
| servidor → cliente | `welcome` | `id, you, players[], proximityTiles` |
| servidor → todos | `join` / `leave` / `player` / `move` | jugador público `{id,name,color,clan,group,x,y,dir,level,bot}` |
| servidor → destinatarios | `chat` | `channel, from, fromId, clan, text, ts, bot` |
| servidor → cliente | `system`, `pong` | |

Reglas: `proximidad` = jugadores a ≤ 15 casillas (30 m); `clan` = mismo clan; `grupo` = mismo grupo. Comandos: `/grupo nombre`, `/clan nombre`. Límite 6 mensajes / 5 s. Cierra conexiones sin mensajes en 45 s.
En el cliente de Sara se puede mapear 1:1 a eventos Socket.io (`chat:send`, `chat:message`, `player:move`, …).

### 12.1 Eventos sugeridos para nodos (servidor autoritativo)
```
cliente → servidor  "node:interact"  { nodeId, itemId? }
servidor → todos    "node:state"     { nodeId, state, crop?, until }
servidor → jugador  "inventory:add"  { item, qty }
servidor → jugador  "xp:add"         { skill, amount }
servidor → jugador  "quest:progress" { questId, stepId, n }
servidor → todos    "animal:move"    { nodeId, x, y }
```
El servidor valida distancia (Chebyshev 1), herramienta, estado y semilla. En la vista previa actual el estado de nodos y misión es **local** a cada navegador.

## 13. Regenerar
`cd El-Jardin/tools && python3 build.py` (Python 3 + Pillow). Vuelve a pintar teselas, sprites, íconos, JSON y vistas previas. Todo el arte es original y procedural.

## 14. Datos 3D (v4) — para el cliente Three.js

Todo es **aditivo y opcional**. Unidades: **metros**. 1 casilla = **2 m** de lado (`render3d.metersPerTile`). El sprite 2D usa 32 px por metro (64 px = 1 casilla).

### 14.1 Ejes y conversión de rejilla a mundo
```
worldX = (x + 0.5) * 2        // x = columna (oeste → este)
worldZ = (y + 0.5) * 2        // y = fila (norte → sur); el norte del mapa es -Z
worldY = elevation[y][x]      // eje Y hacia arriba
```
`render3d.upAxis = "y"`. Una huella `w×h` ocupa de `(x*2, y*2)` a `((x+w)*2, (y+h)*2)` en X/Z.

### 14.2 `elevation[y][x]` (metros, mismo índice que `ground[y][x]`)
Altura de la superficie del terreno en el centro de la casilla.
| terreno | valor |
|---|---|
| césped | 0.0 – 0.5 (ondulación suave); pinar +0.3; cantera (noroeste) hasta +0.6 |
| camino | 0.0 |
| plaza empedrada (`cobble`) | 0.15 |
| puente (`bridge`) | 0.3 (tablero sobre el agua) |
| agua (`water`) | **lecho**: río −1.4, estanque −1.1 |
| acantilado (`K`, filas 0–3, x 26–37) | **7.0** (meseta alta); hombros de césped a los lados 1.2–3.9 |
La superficie del agua es plana: `waterBodies.rio_claro.waterLevel = -0.5` (lecho `bedLevel = -1.4`), `waterBodies.estanque.waterLevel = -0.4` (lecho −1.1).
Para el terreno, interpola entre centros de casillas (o usa escalones). Para colisión sigue usando `collision[y][x]`.

### 14.3 `render3d`
```json
{ "units":"meters","metersPerTile":2,"upAxis":"y","pixelsPerMeter":32,
  "camera":{"mode":"orbit","defaultPitchDeg":50,"defaultYawDeg":0,"defaultDistance":28,"minDistance":8,"maxDistance":70,
            "minPitchDeg":25,"maxPitchDeg":80,"rotate":true,"target":"player"},
  "waterfall":{"decoration":"cascada","columns":[31,32,33],"lipRow":3,"topElevation":7.0,"bottomElevation":-0.5,"material":"agua_turquesa","foamRow":4},
  "cliff":{"x":26,"y":0,"w":12,"h":4,"topElevation":7.0,"material":"roca_acantilado"},
  "lighting":{"sun":{"azimuthDeg":135,"elevationDeg":50,"color":"#fff1d0"},"night":{"ambient":"#2a3560","torchColor":"#ffb050"}} }
```
Elige `lighting.sun` o `lighting.night` según el ciclo de **§15** (no uses un reloj distinto).
La cascada cae desde el borde del acantilado (fila `lipRow` = 3, columnas 31–33, 7.0 m) hasta la superficie del río en la fila `foamRow` = 4 (−0.5 m). El sprite 2D `cascada_0..2` se puede usar como textura animada del plano de caída.

### 14.4 `materials3d` y `terrainMaterials`
`materials3d[id] = { texture, size: 64, repeatMeters: 2, fromTile?, color?, opacity?, animated? }` (texturas tileables 64×64; cada una cubre 2 m).
| id | archivo | uso |
|---|---|---|
| `cesped` | `graphics/tiles/000_grass_0.png` | suelo |
| `camino_tierra` | `graphics/tiles/<id>_path_11111111.png` | caminos |
| `agua_turquesa` | `graphics/tiles/<id>_water_11111111.png` (+ `color #2aa8b8`, `opacity 0.82`, `animated`) | río, estanque, cascada |
| `empedrado` | `graphics/tiles/<id>_cobble_11111111.png` | plaza |
| `puente_tablas` | `graphics/tiles/<id>_bridge_*.png` | tablero del puente |
| `muro_yeso_vigas` | `graphics/materials/muro_yeso_vigas.png` | muros casa del capataz |
| `muro_piedra_clara` | `graphics/materials/muro_piedra_clara.png` | muros casa de piedra |
| `zocalo_piedra` | `graphics/materials/zocalo_piedra.png` | zócalo / chimeneas |
| `techo_tejas_rojas` | `graphics/materials/techo_tejas_rojas.png` | techo capataz |
| `techo_pizarra_azul` | `graphics/materials/techo_pizarra_azul.png` | techo casa de piedra |
| `madera_tablas` | `graphics/materials/madera_tablas.png` | vallas, barandas, puesto, marcos |
| `roca_acantilado` | `graphics/materials/roca_acantilado.png` | acantilado, rocas, mina |
| `arena_orilla` | `graphics/materials/arena_orilla.png` | orillas / lecho |
| `piedra_fuente` | `graphics/materials/piedra_fuente.png` | fuente |
| `toldo_rayas` | `graphics/materials/toldo_rayas.png` | toldo del puesto |
Las rutas exactas (con su número de tesela) están en el JSON; **léelas de `materials3d[id].texture`**, no las escribas a mano.
`terrainMaterials` asocia cada `tiles[id].kind` a un material: `grass/grass_flowers/grass_worn → cesped`, `path → camino_tierra`, `water → agua_turquesa`, `cobble → empedrado`, `bridge → puente_tablas`, más `cliff → roca_acantilado` y `shore → arena_orilla`.

### 14.5 `volumes3d` (volumen por tipo) y `decorations[].d3` (por instancia)
`volumes3d.decorationTypes[type]` y `volumes3d.nodeTypes[type]` dan `{ shape, height (m), billboard?, materials?, … }`:
| tipo | shape | alto (m) | notas |
|---|---|---|---|
| `building` | `house_gable` | muro 4.0 + techo 3.2 | cumbrera paralela a X, alero 0.4 m; huella w×h |
| `stall` | `stall` | 2.6 | `madera_tablas` + `toldo_rayas` |
| `fountain` | `fountain` | 2.4 (pila 0.6, radio 1.8) | `piedra_fuente` + `agua_turquesa` |
| `torch` / `campfire` | `pole` / `campfire` | 2.2 / 0.8 | billboard + luz (`light`) |
| `waterfall` | `cliff` | 7.0 | ver `render3d.waterfall` |
| `mine_entrance` | `mine` | 3.0 | |
| `fence` / `bridge_rail` | `fence` / `rail` | 1.1 / 1.0 | |
| `tree_roble`, `bush`, `sign` | billboard | 6.0 / 1.0 / 1.6 | |
| `boulder` | `rock` | 1.2 | |
| `fruit_tree` | billboard | 5.0 (coco 7.0, banano 4.5) | |
| `wood_tree` | billboard | 8.0 (tocón 0.6) | |
| `farm_plot`, `mineral_rock` | billboard | 0.3 / 1.0 | |
| `fishing_spot`, `nodo_oro_fluvial` | `water_decal` | 0 | sobre `waterLevel` |
| `animal` | billboard | conejo 0.5, venado 1.6, ave 0.5 | |
| personajes | billboard | 1.8 | `volumes3d.characters` |
"billboard" = plano vertical con el sprite 2D existente (ancla en el pie, alto = `h_px / 32` m).

Casas (`decorations[].d3`, sobreescribe el tipo):
```json
"casa_capataz": { "wallHeight":4.0,"roofHeight":3.2,
  "materials":{"walls":"muro_yeso_vigas","base":"zocalo_piedra","roof":"techo_tejas_rojas","trim":"madera_tablas"},
  "door":{"door":"puerta_capataz","face":"south"},"chimney":{"fx":0.65,"height":1.4} }
"casa_piedra":  { "wallHeight":4.2,"roofHeight":3.4,
  "materials":{"walls":"muro_piedra_clara","base":"zocalo_piedra","roof":"techo_pizarra_azul","trim":"madera_tablas"},
  "door":{"face":"south","fx":0.5},"dormer":true,"chimney":{"fx":0.2,"height":1.4} }
```
La puerta interactuable sigue siendo `doors[0]` (casilla (15,15), se toca desde (15,16)).

## 15. Ciclo circadiano (`circadian`)

Campo raíz opcional. Todas las clientes deben calcular la misma fase con el reloj Unix, para que el pueblo se vea de día o de noche a la vez.

```json
{
  "enabled": true,
  "phaseDurationMinutes": 10,
  "phases": ["day", "night"],
  "epochMs": 0,
  "sync": "unix"
}
```

Fórmula:

```
index = floor((nowMs - epochMs) / (phaseDurationMinutes * 60000)) % phases.length
fase  = phases[index]
```

- `nowMs` es `Date.now()` (milisegundos Unix). `epochMs` vale `0`.
- Cada fase dura **10 minutos**. Luego alterna: día → noche → día.
- `day` usa `render3d.lighting.sun`. `night` usa `render3d.lighting.night` (ambiente `#2a3560` y antorchas `#ffb050`; las decoraciones con `light` / `lights` siguen encendidas).
- Un ciclo completo (día + noche) dura 20 minutos.
- No hace falta que el servidor envíe la fase: si todos usan esta fórmula, coinciden.

La vista previa en `play/` aplica el ciclo sola y anuncia en el chat «Amanece en El Jardín» / «Anochece en El Jardín». La tecla **N** solo previsualiza el otro momento hasta el próximo cambio real.
