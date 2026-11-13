# Saimon City

Creación y dirección original: **Simón**. Mundo 3D en desarrollo, con mapa del Valle de Aburrá, minería y fundición, inventario, chat y cámara orbital.

## Versión del valle y economía

Diez municipios conectados, caballo con paso y galope, inicio en casa y logo dorado. La emisión de prueba aprobada es de **21.000.000** de monedas, distribuida desde una tesorería con registro en el servidor. Véase [alcance, controles y persistencia](MUNDO-Y-ECONOMIA.md).

## Licencias y contribución

Código propio: **AGPL-3.0-or-later**. Contenidos propios autorizados: **CC-BY-SA-4.0**. Marca y logo: política separada. Three.js conserva MIT y Pixelify Sans conserva SIL OFL 1.1.

- [Alcance y excepciones](LICENSE.md) y [adopción autorizada](ADOPCION.md).
- [Créditos](NOTICE.md) y [avisos de terceros](THIRD-PARTY-NOTICES.md).
- [Manifiesto de recursos](asset-manifest.json).
- [Guía de contribución](CONTRIBUTING.md).
- [Marca](MARCA.md) y [blockchain y propiedad](BLOCKCHAIN-Y-PROPIEDAD.md).

Cada persona conserva sus derechos sobre sus aportaciones. No se transfiere automáticamente copyright, marca ni un bien físico mediante un NFT. La licencia no registra la marca ni convierte el servidor actual en una red descentralizada.

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
