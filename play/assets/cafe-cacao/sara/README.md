# Saimon City · dirección de arte 3D (café y cacao)

Paquete de diseño de Sara. **Solo arte:** no se tocó ningún repositorio.

Unidades en **metros**, orientación **Y-up** (Y = altura, origen en el centro de la parcela al nivel del suelo). El lecho de cada planta mide **1 × 1 m** (apoyo visual); las distancias reales de siembra se documentan abajo. El café en **cosecha** mide unos **2,0 m**; el cacao, unos **3,3–3,5 m**.

Estilo low-poly de cajas, como `play/unified3d.js` (el caballo criollo del juego es un ensamblaje de cajas: cuerpo `#8a5a32`, cuello `#a56b3c`, cabeza `#c48a52`, patas `#6b4224`, unos 1,5 m de alto). Paleta tomada de `/workspace/sara-saimon/README.md`. Colores de vértice; sin texturas pesadas. Un material Lambert de sombreado plano es suficiente en Three.js.

No había carpeta `cafe-cacao` en las entregas de Raimundo ni de Elisa; las etiquetas de proceso son nombres cortos en español.

Regenerar: `python3 /workspace/sara-saimon/3d/src/build_all.py`.

## Hojas de vista previa

Todas llevan el sello **VISTA PREVIA**.

| Archivo | Qué muestra |
| --- | --- |
| `hojas/hoja_plantas_cafe_3d.png` | Café, 5 etapas, LOD cercano y lejano |
| `hojas/hoja_plantas_cacao_3d.png` | Cacao, 5 etapas, LOD cercano y lejano |
| `hojas/hoja_talleres_cafe_3d.png` | Estaciones de café, numeradas |
| `hojas/hoja_talleres_cacao_3d.png` | Estaciones de cacao, numeradas |
| `hojas/hoja_layout_talleres_3d.png` | Plantas de proceso completas |
| `hojas/hoja_iconos_etapas.png` | Íconos de etapas a 256 px |
| `hojas/hoja_iconos_etapas_32px.png` | Prueba de legibilidad a 32 px |

## 1. Plantas

Cinco etapas × dos LOD (`near` < 1.500 triángulos, `far` ≈ 200–400).

| archivo | cultivo | etapa | LOD | triángulos | alto (m) |
| --- | --- | --- | --- | --- | --- |
| plantas/cafe/cafe_siembra_near.glb | cafe | siembra | near | 272 | 0.3603 |
| plantas/cafe/cafe_siembra_far.glb | cafe | siembra | far | 272 | 0.325 |
| plantas/cafe/cafe_crecimiento_near.glb | cafe | crecimiento | near | 460 | 1.04 |
| plantas/cafe/cafe_crecimiento_far.glb | cafe | crecimiento | far | 276 | 1.04 |
| plantas/cafe/cafe_floracion_near.glb | cafe | floracion | near | 1092 | 1.4 |
| plantas/cafe/cafe_floracion_far.glb | cafe | floracion | far | 336 | 1.4 |
| plantas/cafe/cafe_fruto_near.glb | cafe | fruto | near | 1296 | 1.71 |
| plantas/cafe/cafe_fruto_far.glb | cafe | fruto | far | 388 | 1.71 |
| plantas/cafe/cafe_cosecha_near.glb | cafe | cosecha | near | 1296 | 2.0 |
| plantas/cafe/cafe_cosecha_far.glb | cafe | cosecha | far | 404 | 2.0 |
| plantas/cacao/cacao_siembra_near.glb | cacao | siembra | near | 200 | 0.4922 |
| plantas/cacao/cacao_siembra_far.glb | cacao | siembra | far | 208 | 0.46 |
| plantas/cacao/cacao_crecimiento_near.glb | cacao | crecimiento | near | 320 | 1.5266 |
| plantas/cacao/cacao_crecimiento_far.glb | cacao | crecimiento | far | 296 | 1.38 |
| plantas/cacao/cacao_floracion_near.glb | cacao | floracion | near | 480 | 2.3326 |
| plantas/cacao/cacao_floracion_far.glb | cacao | floracion | far | 348 | 2.15 |
| plantas/cacao/cacao_fruto_near.glb | cacao | fruto | near | 616 | 3.353 |
| plantas/cacao/cacao_fruto_far.glb | cacao | fruto | far | 428 | 3.15 |
| plantas/cacao/cacao_cosecha_near.glb | cacao | cosecha | near | 664 | 3.353 |
| plantas/cacao/cacao_cosecha_far.glb | cacao | cosecha | far | 428 | 3.15 |

### Mapeo estado del servidor → modelo (para quien integra)

Hoy el servidor y `farm_plot` solo tienen tres claves: `empty`, `planted`, `grown`. El manifiesto `manifest.json` usa exactamente esas claves en `serverState`, y propone claves extra en `suggestedState` por si se amplía el ciclo.

| Estado del servidor (hoy) | Modelo near / far (café; igual con `cacao_`) | Fallback 2D | `serverState` en el manifiesto |
| --- | --- | --- | --- |
| `empty` | *(ninguno; usar la parcela vacía del juego, `plot_empty`)* | `../sprites/` no aplica; parcela actual | `empty` |
| `planted` | `plantas/cafe/cafe_siembra_near.glb` y `cafe_siembra_far.glb` | `../sprites/plot_cafe_siembra.png` y `iconos-etapas/cafe_01_siembra.png` | `planted` |
| `grown` | `plantas/cafe/cafe_cosecha_near.glb` y `cafe_cosecha_far.glb` | `../sprites/plot_cafe_cosecha.png` y `iconos-etapas/cafe_05_cosecha.png` | `grown` |

Etapas 3D que hoy **no** tienen clave en el servidor. Si se añaden, el manifiesto ya las nombra así:

| Etapa 3D | GLB (prefijo `plantas/{cultivo}/{cultivo}_`) | `suggestedState` | Fallback 2D |
| --- | --- | --- | --- |
| `crecimiento` | `crecimiento_near.glb` / `_far.glb` | `growing` | `../sprites/plot_{cultivo}_crecimiento.png` y el ícono `02_crecimiento` |
| `floracion` | `floracion_near.glb` / `_far.glb` | `flowering` | ícono `03_floracion` (no hay sprite 2D de planta) |
| `fruto` | `fruto_near.glb` / `_far.glb` | `fruiting` | ícono `cafe_04_cereza_madura` o `cacao_04_mazorca` |

Si el servidor se queda en tres estados: `planted` → siembra, `grown` → cosecha. `crecimiento` puede usarse como aspecto intermedio de `planted` si se prefiere más lectura a distancia.

En Three.js, cambiar de LOD por distancia (por ejemplo `near` bajo 18 m, `far` más allá). Ambas mallas comparten origen y escala **1** (metros). Los nombres de archivo son estables; el cargador ligero debe leer `manifest.json` y no inventar rutas.

## 2. Talleres de procesamiento

Una estación pequeña por paso (< 3.000 tris) y un `layout` con la línea completa más cultivos de fondo (LOD lejano).

**Café:** despulpado → fermentado → lavado → secado en marquesina → trilla → bultos.

**Cacao:** quiebre de mazorca → fermentación en cajones → secado → selección → kilos registrados (báscula).

| archivo | paso | triángulos |
| --- | --- | --- |
| talleres/cafe/cafe_estacion_01_despulpado.glb | Despulpado | 280 |
| talleres/cafe/cafe_estacion_02_fermentado.glb | Fermentado | 300 |
| talleres/cafe/cafe_estacion_03_lavado.glb | Lavado | 188 |
| talleres/cafe/cafe_estacion_04_secado.glb | Secado en marquesina | 852 |
| talleres/cafe/cafe_estacion_05_trilla.glb | Trilla | 308 |
| talleres/cafe/cafe_estacion_06_bultos.glb | Bultos | 352 |
| talleres/cacao/cacao_estacion_01_quiebre.glb | Quiebre de mazorca | 200 |
| talleres/cacao/cacao_estacion_02_fermentacion_cajones.glb | Fermentación en cajones | 264 |
| talleres/cacao/cacao_estacion_03_secado.glb | Secado | 648 |
| talleres/cacao/cacao_estacion_04_seleccion.glb | Selección | 228 |
| talleres/cacao/cacao_estacion_05_kilos_registrados.glb | Kilos registrados | 216 |
| talleres/cafe/cafe_layout.glb | None | 4748 |
| talleres/cacao/cacao_layout.glb | None | 3752 |

IDs sugeridos: `taller_cafe`, `taller_cacao`, o uno por estación (`cafe_estacion_01_despulpado`, …). Colocarlos junto a los cultivos en Las Palmas.

## 3. Íconos de etapas

Carpeta `iconos-etapas/`. PNG transparente 256×256 y 64×64, más SVG. Pensados para leerse a **32 px**: silueta simple, contraste fuerte, sin texto. El café lleva anillo rojo cereza y badge de cereza; el cacao, anillo amarillo-naranja y badge de mazorca.

| archivo (256 / 64 / SVG) | etiqueta |
| --- | --- |
| `cafe_01_siembra.png` · `64/cafe_01_siembra.png` · `cafe_01_siembra.svg` | Siembra |
| `cafe_02_crecimiento.png` · `64/cafe_02_crecimiento.png` · `cafe_02_crecimiento.svg` | Crecimiento |
| `cafe_03_floracion.png` · `64/cafe_03_floracion.png` · `cafe_03_floracion.svg` | Floración |
| `cafe_04_cereza_madura.png` · `64/cafe_04_cereza_madura.png` · `cafe_04_cereza_madura.svg` | Cereza madura |
| `cafe_05_cosecha.png` · `64/cafe_05_cosecha.png` · `cafe_05_cosecha.svg` | Cosecha |
| `cafe_06_despulpado.png` · `64/cafe_06_despulpado.png` · `cafe_06_despulpado.svg` | Despulpado |
| `cafe_07_fermentacion.png` · `64/cafe_07_fermentacion.png` · `cafe_07_fermentacion.svg` | Fermentación |
| `cafe_08_lavado.png` · `64/cafe_08_lavado.png` · `cafe_08_lavado.svg` | Lavado |
| `cafe_09_secado.png` · `64/cafe_09_secado.png` · `cafe_09_secado.svg` | Secado |
| `cafe_10_trilla.png` · `64/cafe_10_trilla.png` · `cafe_10_trilla.svg` | Trilla |
| `cafe_11_bulto.png` · `64/cafe_11_bulto.png` · `cafe_11_bulto.svg` | Bulto |
| `cacao_01_siembra.png` · `64/cacao_01_siembra.png` · `cacao_01_siembra.svg` | Siembra |
| `cacao_02_crecimiento.png` · `64/cacao_02_crecimiento.png` · `cacao_02_crecimiento.svg` | Crecimiento |
| `cacao_03_floracion.png` · `64/cacao_03_floracion.png` · `cacao_03_floracion.svg` | Floración |
| `cacao_04_mazorca.png` · `64/cacao_04_mazorca.png` · `cacao_04_mazorca.svg` | Mazorca |
| `cacao_05_cosecha.png` · `64/cacao_05_cosecha.png` · `cacao_05_cosecha.svg` | Cosecha |
| `cacao_06_quiebre.png` · `64/cacao_06_quiebre.png` · `cacao_06_quiebre.svg` | Quiebre de mazorca |
| `cacao_07_fermentacion_cajones.png` · `64/cacao_07_fermentacion_cajones.png` · `cacao_07_fermentacion_cajones.svg` | Fermentación en cajones |
| `cacao_08_secado.png` · `64/cacao_08_secado.png` · `cacao_08_secado.svg` | Secado |
| `cacao_09_seleccion.png` · `64/cacao_09_seleccion.png` · `cacao_09_seleccion.svg` | Selección |
| `cacao_10_kilos_registrados.png` · `64/cacao_10_kilos_registrados.png` · `cacao_10_kilos_registrados.svg` | Kilos registrados |
| `planta_procesamiento.png` · `64/planta_procesamiento.png` · `planta_procesamiento.svg` | Planta de procesamiento |

Rutas sugeridas: `graphics/ui/etapas/{nombre}.svg` y `graphics/icons/64/{nombre}.png`.

## Paleta

| Uso | Hex |
| --- | --- |
| Tierra | `#6B4A2F` `#7E5A3A` `#533821` |
| Madera / borde de parcela | `#8A5A32` `#A07048` `#C4A070` |
| Hoja de café | `#2F7D3A` `#4CA35A` `#6BC46E` |
| Cereza (Cromacafé® 1–8, saturado) | `#6E8A48` `#C4B45A` `#E0A05A` `#C0262D` `#A01C28` `#7A2C3A` `#4E1C28` `#2B2420` |
| Hoja de cacao | `#2E6B34` `#4E8F3E` · brote `#9A4A2E` |
| Mazorca | `#e5a02a` `#c45a2a` `#7a2c3a` |
| Flor | `#f6e7c4` `#e8c4c0` `#F2C230` |
| Teja / muro | `#a85a3a` `#f3ead7` |
| Metal / agua | `#8d9398` `#4a545a` `#6a9bb0` |
| Oro (detalle) | `#F2C230` `#B8860B` |

## Integración con Three.js (`GLTFLoader`)

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const loader = new GLTFLoader();
loader.load('graphics/models/cafe_cosecha_near.glb', (gltf) => {
  const root = gltf.scene;
  // Ya viene en metros, Y-up, origen en el suelo.
  root.position.set(plot.x, 0, plot.z);
  root.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
      // Colores de vértice: no sustituir el mapa.
      if (o.material && o.material.map == null) o.material.vertexColors = true;
      o.material.flatShading = true;
    }
  });
  scene.add(root);
});
```

El mundo del juego usa ~2 m por casilla (`play/unified3d.js`: `x*2+1`). El lecho de 1×1 m cabe en media casilla, o en un plot de 1 m si se unifica la escala. El caballo del juego mide ~1,5 m: el café en cosecha (~2,0 m) le supera un poco la cruz y le llega casi a la altura del jugador (~2 m); el cacao (~3,3–3,5 m) los sobrepasa. En el mapa, el cacao se planta en una malla de **3 × 3 m**; los árboles de sombrío del café, en una malla de **12 × 12 m** (máx. 70 árboles/ha si el café va a más de 5.000 plantas/ha).

## Escala y medidas (referencias + criterio de Sara)

Las cifras con fuente salen de `/workspace/raimundo-saimon/cafe-cacao/README.md` (34 fuentes institucionales y 7 fichas de Wikimedia, solo enlaces). Se usaron **solo como referencia de medidas y de porte**. El arte de este paquete es original: no se copiaron fotos, planos ni texturas.

| Qué | En el modelo | Fuente o criterio |
| --- | --- | --- |
| Café, 24 meses (floración) | ~1,40 m | Cenicafé 1 / Caturra / Castillo® en Naranjal: 140–147 cm |
| Café adulto (cosecha) | ~2,0 m | Rango adulto 2,0–2,4 m (AT 426, Catuai en m; Tabla 1 de Castillo®/Colombia 2,27 / 2,37 **sin unidad escrita**). Se toma 2,0 m, el lado bajo del rango. Crecimiento y fruto quedan proporcionales. |
| Café, forma | Un tallo, ramas laterales en pisos, copa cónica | AT 426, silueta de Castillo® / Colombia |
| Cerezas, 8 colores | `crom_1`…`crom_8` en floración (flores + verdes tempranos), fruto (1–4) y cosecha (sobre todo 4–5, algo de 6–7, raro 8) | Cromacafé® (Cenicafé). Los hex se saturaron un poco para leerse en el celular; no son una copia colorimétrica de la tabla Lab. |
| Diámetro de la cereza | ~3,5 cm en el LOD cercano | **Criterio de Sara.** Cromacafé® da la masa en g, no el diámetro en mm. Se agrandó para que se lea a distancia. |
| Secador solar de café | Piso **2 × 10 m**, cama a **80 cm**, capa 3 cm, 4 paseras de 1 m² debajo, 10 postes | Cenicafé, AT 353 (túnel de 20 m²). Cenicafé no acota una “marquesina” con ese nombre; el archivo se llama `cafe_estacion_04_secado` por estabilidad. |
| Alto del arco del túnel de café | 2,0 m al centro | **Criterio de Sara.** El AT 353 no trae esa altura. |
| Cilindro de la despulpadora (dato de desarrollo) | 14 cm de diámetro × 22 cm de largo en el AT 294. En el modelo el tambor se ve más grande, para que la máquina se lea de un vistazo (tolva cónica y volante son la silueta). | Cenicafé, Gaviota, AT 294 · escala visual, criterio de Sara |
| Tanques de fermentación de café | Dos tinas de ~0,90 m de diámetro y 0,85 m de alto, con agua | **Criterio de Sara.** No hay una talla única verificada para una finca pequeña. |
| Saco de fique | ~**60 × 95 cm** de cara, 40 cm de fondo, para unos **60–70 kg** | **Criterio de Sara.** Las fuentes oficiales distinguen la carga de 125 kg de pergamino y el saco de 70 kg de excelso, pero no dan los cm del costal. |
| Cacao, siembra | Malla **3 × 3 m** (el lecho visual de la planta sigue midiendo 1 × 1 m) | AGROSAVIA, modelo Santander 2021: 1.100 plantas/ha, o 1.280 en tresbolillo |
| Cacao, altura | ~3,3–3,5 m en fruto / cosecha | AGROSAVIA: límite de manejo **3,5 m** (no se verificó la altura sin podar) |
| Mazorca | **20–25 cm** de largo, costillas, colgando del tronco y de las ramas (caulifloría) | **Criterio de Sara.** La longitud en cm no se pudo verificar (el catálogo Fedecacao 2015 no cargó). En fruto van verde-amarillas; en cosecha, amarillas, naranjas y burdeos, según la madurez descrita por AGROSAVIA. |
| Cajón de fermentación | Tres cajones de **1 × 1 × 0,9 m**, tipo escalera, el primero a 0,30 m del suelo | Tabla Red Cacaotera 2025 (450 kg fresco / 150 kg seco). El tipo escalera lo describe AGROSAVIA. |
| Secador de cacao | **2,5 × 6,0 m**, **2,55 m** al centro del arco, dos paseras | Unidad modular AGROSAVIA. La altura de las paseras (0,70 m) es **criterio de Sara**; el plano leído no la traía. |
| Árboles de sombrío del café | No hay GLB de sombrío en este paquete. Colocarlos en malla **12 × 12 m**. El primer piso de sombra, como mínimo a 3× la altura del cafeto (café de 2 m → 6 m). | Farfán 2021; Cenicafé AT 440 |


El cargador ligero de GLB del equipo de cultivos debe leer **`manifest.json`** (en esta misma carpeta). Ahí está, para cada cultivo y etapa, el GLB cercano, el lejano, el PNG 2D de respaldo para móvil, el recuento de triángulos, la escala (`1`, en metros) y la clave `serverState`. Las estaciones de proceso van en `stations`. Los nombres de esos archivos no se deben cambiar sin avisar: son la API del paquete.

Contadores detallados: `counts.json`. Autoría y referencias: `PROVENANCE.md`.
