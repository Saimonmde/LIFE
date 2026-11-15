# Procedencia del paquete 3D · café, cacao y talleres

## Autoría

Sara · Diseñadora gráfica, para Jay Montana / Saimon City (LIFE).

Todos los GLB, íconos de etapas, hojas de previsualización y el `manifest.json` de este directorio son arte original de este trabajo. No se importaron modelos de librerías, tiendas ni capturas de terceros.

## Cómo se hizo

Generación programática en Python: primitivas low-poly (cajas, cilindros, octaedros, hojas en diamante) con colores de vértice, exportadas a glTF binario (`.glb`) con trimesh. Las previsualizaciones se rasterizan por software (z-buffer Lambert) y se sellan «VISTA PREVIA». Los íconos de etapas se dibujan en SVG y se rasterizan a PNG 256 y 64.

Script orquestador: `/workspace/sara-saimon/3d/src/build_all.py`.

| Módulo | Qué genera |
| --- | --- |
| `3d/src/meshkit.py` | Primitivas Y-up en metros, paleta, exportación y validación de GLB |
| `3d/src/plants.py` | Café y cacao, cinco etapas, LOD `near` / `far` |
| `3d/src/stations.py` | Estaciones de proceso y layouts combinados |
| `3d/src/render.py` | Hojas de previsualización selladas |
| `3d/src/icons_etapas.py` | Íconos de etapa y de proceso (`iconos-etapas/`) |

Para regenerar todo este directorio: `python3 /workspace/sara-saimon/3d/src/build_all.py`.

Nombres de archivo estables (API del paquete): `plantas/{cultivo}/{cultivo}_{etapa}_{near|far}.glb`, `talleres/{cultivo}/{cultivo}_estacion_{paso}.glb`, `talleres/{cultivo}/{cultivo}_layout.glb`, `iconos-etapas/{cultivo}_{nn}_{paso}.png` (y `.svg`, más `64/`). El cargador ligero de cultivos debe leer `manifest.json`, no inventar rutas. Convención documentada en `README.md`.

## Referencias (solo como referencia)

Se usaron para encajar estilo, escala y estados del servidor. No se calcó geometría ni se reutilizaron bitmaps ajenos como mallas o texturas.

Clon de lectura de [Saimonmde/LIFE](https://github.com/Saimonmde/LIFE), `main` @ `be44879` (copia local `/tmp/LIFE`):

- `play/unified3d.js` — estilo de cajas low-poly del mundo, orientación Y-up, ~2 m por casilla (`x*2+1`), colores y altura (~1,5 m) del caballo criollo (`buildHorse`), jugador ~2 m. No hay un GLB del caballo; solo se tomaron esas proporciones y colores como medida.
- `play/estilo-jabo.js` — lenguaje visual general.
- `data/el-jardin.json` — estados actuales de `farm_plot`: `empty`, `planted`, `grown`. El manifiesto propone claves intermedias (`growing`, `flowering`, `fruiting`) sin aplicarlas en el servidor.

Se revisó, solo como contexto, material de equipos vecinos. No había un set de nombres de pasos que copiar:

- `/workspace/elisa-saimon/LEEME.md`, `plan-redes.md`, `textos-principiantes.md`.
- Al inicio no existían esas carpetas; más adelante se publicó `/workspace/raimundo-saimon/cafe-cacao/README.md`, usado solo como referencia (ver arriba).
- `/workspace/raimundo-saimon/recorrido/` — capturas de recorridos, no usadas como base de modelado.

Paleta, siluetas de etapa y sprites de respaldo 2D salen del propio paquete 2D de Sara en `/workspace/sara-saimon/` (`cultivos/`, `sprites/plot_*`, `talleres/`, `iconos/`, `README.md`). Esos PNG se listan en `manifest.json` como `fallback2d` para móvil; no se incrustan dentro de los GLB.


También se consultó, **solo como referencia de medidas, porte y nomenclatura**, el inventario `/workspace/raimundo-saimon/cafe-cacao/README.md` (15 de noviembre de 2026): 34 fuentes institucionales verificadas (Cenicafé, FNC, AGROSAVIA, Fedecacao, Red Cacaotera, UPTC) y 7 fichas de Wikimedia Commons, citadas como enlaces, sin descargar ni incorporar ninguna foto. Esas referencias no se calcó ni se usaron como textura, plano o modelo. Donde la fuente no trae un dato (largo de la mazorca, cm del costal de fique, alto del arco del túnel de café, alto de las paseras de cacao), el paquete declara un **criterio de Sara** en `3d/README.md`. El arte sigue siendo original.

## Fuentes

En las hojas de previsualización y el sello «VISTA PREVIA» se usa **Inter** (Rasmus Andersson / The Inter Project Authors), SIL Open Font License 1.1. Ver `/workspace/sara-saimon/fonts/NOTICE.txt`. No se redistribuyen archivos `.ttf`. Los GLB no llevan tipografía.

## Licencia (solo una propuesta)

Se propone, para cuando el equipo decida publicarlo: código de generación bajo MIT, y modelos / íconos / texto / hojas bajo una licencia Creative Commons. **Eso es solo una propuesta.** No cambia ninguna licencia ya existente del repo LIFE ni de este paquete, y no autoriza por sí sola a republicar, tokenizar ni vender estos archivos.

## Tokenización

Cualquier mención a tokenizar o acuñar este arte (o el juego) es solo una meta documentada. No es un hecho, no está aplicada y no forma parte de este entregable.

## Notas

Paquete de diseño, no de código de juego. No se publicó nada al repositorio desde aquí.
