# Estructura unificada — propuesta

No se mueve ningún archivo en este cambio. El juego público pide rutas fijas (`/play/`, `/data/`, `/graphics/`, `/movil/`). Moverlas ahora rompería la web que ya está en Render.

La idea es un solo árbol, con una carpeta por tipo de material, para que la licencia de cada cosa se vea por el sitio donde vive. El mapa de licencias vigente, sin aplicar la propuesta, está en `.reuse/dep5`.

## Carpetas propuestas

| Carpeta | Qué iría ahí | Sale de |
| --- | --- | --- |
| `codigo/` | Servidor, herramientas y cliente | `server.py`, `tools/`, `play/*.js`, `play/*.css`, HTML de `play/` y `movil/` |
| `arte/2d/` | Teselas, personajes, objetos, materiales, interfaz | `graphics/tiles`, `graphics/characters`, `graphics/objects`, `graphics/materials`, `graphics/ui` |
| `arte/3d/` | Modelos | `graphics/models/` (hoy sólo la caneca). Las mallas hechas por código se quedan con el cliente hasta que se exporten |
| `iconos/` | Iconos de inventario y minería | `graphics/icons/`, `graphics/mining/` |
| `textos/` | Instructivo, docs, páginas legales, lecciones | `docs/`, `legal/`, `data/simon/`, los textos de `data/simulacion.json` |
| `datos-mapa/` | Valle, OSM, relieve, parque | `data/el-jardin.*`, `data/valle-geo.*`, `data/relieve-aburra.json`, `data/parque-envigado-bloque.json`, `data/valle-offset.json` |
| `sonidos/` | Archivos de audio, cuando existan | Hoy está vacía. `play/sonido.js` sigue en el código porque no hay archivos |
| `docs/` | Puede quedarse como está, o pasar los textos largos a `textos/` y dejar aquí sólo la propuesta y las licencias | `docs/` |

`LICENSES/`, `LICENSE`, `NOTICE.md` y `CREDITS.md` se quedan en la raíz. No se mezclan con el arte.

## Cómo migrar, cuando Jay lo pida

1. No se hace en el mismo paso que un cambio de licencia. Primero se aprueba la licencia. Después se mueven carpetas.
2. Cada mudanza conserva el archivo y su sidecar `.license`.
3. El servidor sigue respondiendo las rutas viejas. La forma segura es servir el archivo nuevo también en la ruta antigua (`/graphics/...`, `/data/...`, `/play/...`) hasta que el cliente publicado use las nuevas. Render no perdona un 404 en un script con `?v=`.
4. Se actualiza `.reuse/dep5` en el mismo commit que mueve la carpeta, para que el mapa no mienta.
5. Se prueba el juego en local (entrar, caminar, abrir el banco, oír el tintineo) y se comprueba `/play/index.html` en la web después del deploy.
6. Los datos ODbL no se mezclan en una carpeta con licencia CC. `datos-mapa/` puede tener dos subcarpetas, `osm/` y `propio/`, para que el aviso de OpenStreetMap no se pierda.

Hasta ese momento el árbol de carpetas de este repositorio es el que ya está en `main`.
