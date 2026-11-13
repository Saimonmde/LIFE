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
