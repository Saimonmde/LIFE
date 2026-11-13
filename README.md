# Saimon City

Creación y dirección original: **Simón**. Mundo 3D en desarrollo, con mapa del Valle de Aburrá, minería y fundición, inventario, chat y cámara orbital.

## Licencias y contribución

Código propio: **AGPL-3.0-or-later**. Contenidos propios autorizados: **CC-BY-SA-4.0**. Marca y logo: política separada. Three.js conserva MIT y Pixelify Sans conserva SIL OFL 1.1.

- [Alcance y excepciones](LICENSE.md) y [adopción autorizada](ADOPCION.md).
- [Créditos](NOTICE.md) y [avisos de terceros](THIRD-PARTY-NOTICES.md).
- [Manifiesto de recursos](asset-manifest.json).
- [Guía de contribución](CONTRIBUTING.md).
- [Marca](MARCA.md) y [blockchain y propiedad](BLOCKCHAIN-Y-PROPIEDAD.md).

Cada persona conserva sus derechos sobre sus aportaciones. No se transfiere automáticamente copyright, marca ni un bien físico mediante un NFT. La licencia no registra la marca ni convierte el servidor actual en una red descentralizada.

La simulación de **SaiMonCoins (SMC)** y del **Libro Mayor** es educativa. No es dinero real, no tiene valor ni canje, y no transfiere derechos, marca ni bienes. El tope es 21.000.000 SMC; 1 SMC = 100.000.000 saimonitos. Sólo el oro del río emite SMC nuevas. El nombre anterior, Saimon Coins (SAI) con alias Saimony, ya no se usa. El servidor guarda el libro en `state/economy.json` (no se versiona; en el plan gratuito de Render el disco se borra al reciclar la instancia) y sigue leyendo un archivo guardado con el símbolo viejo.

## Mapa del repositorio

Todo está en la raíz. No hay una carpeta `El-Jardin` ni una copia paralela del mapa.

- `server.py` — HTTP, WebSocket, `/healthz` y la autoridad de las SMC.
- `play/` — vista de escritorio: mundo, casa colonial, Parque de Envigado, chat y `simulacion.js` (caballos, SMC, Libro Mayor, lecciones).
- `movil/` — entrada del teléfono; usa la misma vista con botones táctiles.
- `data/el-jardin.json` — el mapa del Valle de Aburrá (10 municipios). `data/el-jardin.js` es la misma carga para abrir sin `fetch`. `data/simulacion.json` — establo, profesora, economía y lecciones, fuera de la casa. `data/valle-offset.json` — el único desplazamiento del Parque de Envigado. `data/relieve-aburra.json` — alturas simplificadas. `data/parque-envigado-bloque.json` — teselas del parque, celda por celda, antes y después de moverlas.
- `graphics/` — arte original: teselas, objetos, personajes e interfaz.
- `tools/` — `relieve_aburra.py` (SRTM), `valle_aburra.py` (regenera el valle), `economy.py`, `test_economy.py` y `test_parques.py`. `tools/build.py` conserva un generador histórico del mapa; no hace falta para jugar.

## Valle de Aburrá

El mapa va de Caldas, al sur, hasta Barbosa, al norte. El río Medellín corre por el fondo del valle y las laderas suben al oriente y al occidente. El Parque de Envigado, la quebrada y El Jardín tutorial se copiaron sin redibujar sus teselas. El único desplazamiento es `VALLE_OFFSET` `{ x: -133, y: 203 }`. `play/casa.js` lo suma a la puerta (226, 64) → (93, 267) y a la llegada (227, 64) → (94, 267). `play/envigado-park.js` lo suma al origen de Sara (214, 52) → (81, 255), así las canecas y el skate del PR #5 siguen dentro del bloque. El mismo número mueve el oro, el establo y la Profesora.

El relieve sale de NASA SRTM GL1 (dominio público), tesela N06W076, remuestreada por `tools/relieve_aburra.py`. En 3D es la malla del terreno, cargada por trozos de 32×32 casillas. En 2D el mapa y el suelo llevan sombreado y curvas de nivel. Para regenerar: `python3 tools/relieve_aburra.py` y después `python3 tools/valle_aburra.py` (sólo desde el mapa original de 352×176).

## Jugar en local

Ejecutar `python3 server.py` y abrir `http://localhost:8765/play/`. Python 3 basta para servir el juego; las herramientas gráficas necesitan Pillow. No ejecutar `tools/build.py` sobre una copia con cambios sin respaldo: ese generador conserva una versión histórica del mapa.

La página `play/licencias.html` ofrece los avisos y una descarga del código fuente correspondiente. La publicación en GitHub se verifica por separado; el estado local de licencia no implica que ya se haya subido un repositorio.

## Ejecución y despliegue de esta versión

Se conservan las instrucciones siguientes de la versión pública. El estado del juego y de la casa colonial permanece intacto con esta actualización de licencias.

# LIFE INC · El Jardín

Juego MMORPG conn skills, economia y batallas PVP PVM en el navegador. **Saimon City** es la zona de inicio: pueblo, río, huerto, cantera y chat entre quienes están conectados. El servidor es Python 3 y solo usa la biblioteca estándar: en el mismo puerto sirve la vista de escritorio (`/play/`), la de teléfono (`/movil/`) y el chat por WebSocket (`/ws`).

## Cómo ejecutarlo en local

Hace falta Python 3.11 o más nuevo. No hay que instalar nada con pip ni npm.

```bash
python3 server.py --host 0.0.0.0 --port 8765
```

- Escritorio: http://127.0.0.1:8765/play/
- Teléfono: http://127.0.0.1:8765/movil/
- `GET /` redirige a `/play/`.
- `GET /healthz` responde `200` (lo usa Render).

Si omites `--port`, el puerto sale de la variable `PORT` y, si no existe, es el `8765`. `--port` siempre gana sobre `PORT`. `./jugar.sh` arranca el mismo servidor en el puerto 8765.

## Render

El archivo `render.yaml` define un servicio web gratuito llamado **lifein**. Cada push a `main` vuelve a desplegarlo. Render inyecta `PORT`; el arranque es `python3 server.py --host 0.0.0.0`.
