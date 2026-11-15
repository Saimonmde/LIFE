# Trabajar en Saimon City desde Codex u otro editor

GitHub `main` de https://github.com/Saimonmde/LIFE es la única fuente. El juego publicado es https://lifein.onrender.com . Una copia local que no se haya actualizado con ese `main` no es una base válida: en noviembre de 2026 una sesión trabajó así, no pudo subir nada y el resultado quedó fuera del repositorio.

## Antes de editar

1. Clona el repositorio, o, si ya tienes una carpeta, entra en ella y trae `main`:

```bash
git clone https://github.com/Saimonmde/LIFE.git
cd LIFE
git checkout main
git pull origin main
```

2. No abras una carpeta vieja del Escritorio, de Archivo ni de un zip de entrega. No copies `state/`, cuentas, saldos, tokens ni `.env` de un servidor a otro.
3. Crea una rama por cada función. No acumules temas distintos en la misma rama.
4. Abre un pull request hacia `main`. Las pruebas tienen que pasar antes de fusionar. Una prueba que falla bloquea la publicación.

## Pruebas

Hace falta Python 3.11 o más nuevo, con `scrypt`, y Node.

```bash
python3 -m unittest discover -s tools -p 'test_*.py'
node tools/test_historia.js
node tools/test_layout_mint.js
node tools/test_llegada.js
node tools/test_motion.js
node tools/test_bridge_geometry.mjs
```

En local: `python3 server.py --host 0.0.0.0 --port 8765` y abre http://127.0.0.1:8765/play/ .

## Publicar

El servicio de Render es **lifein**, id `srv-dbq9e98n74is73ch8dig`. `render.yaml` pide autoDeploy en cada push a `main`, pero ese disparo automático no está ocurriendo. Fusionar el pull request no publica solo.

Después de fusionar, hay que lanzar el deploy por la API de Render (hace falta una clave con permiso sobre ese servicio):

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Accept: application/json" \
  https://api.render.com/v1/services/srv-dbq9e98n74is73ch8dig/deploys
```

Cuando el deploy quede en `live`, comprueba que la página publicada sirve los `?v=` nuevos y que el proceso responde:

```bash
curl -fsS https://lifein.onrender.com/healthz
curl -fsS https://lifein.onrender.com/play/index.html | grep '?v='
```

Un servidor local encendido, o un push que GitHub aceptó, no demuestran que la web pública ya cambió. No reinicies la base de datos como parte del deploy. No crees otro servicio, otro dominio ni otra economía para saltarte la falta de credenciales.

El intercambio entre jugadores, el puente de la 4 Sur y lo que se dejó fuera de la copia local están en `docs/INTEGRACION-CODEX.md`. Quien acredite bolsas de café o de cacao usa `purses.credit` y `tools/trades.py`; no hace falta otro módulo de intercambio.
