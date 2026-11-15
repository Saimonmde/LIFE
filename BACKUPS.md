# Respaldos de Saimon City

Esta guía es para volver a un momento del juego sin miedo de borrar la ciudad que está en vivo.

Hay dos cosas distintas en cada respaldo:

1. **El código** de ese momento. Queda como una etiqueta de git y como un Release de GitHub.
2. **Los datos** (jugadores, monedas, libro, opiniones). Van en un archivo cifrado, porque este repositorio es público.

La ciudad que se juega en https://lifein.onrender.com sigue en `main`. Mirar un respaldo no la cambia.

## Cuándo se crea uno

Cada vez que se fusiona un pull request en `main`, GitHub crea un respaldo solo. Render sigue desplegando el juego como siempre: si el respaldo falla, la ciudad no se detiene.

También puedes pedirlo a mano: en GitHub, Actions → **Respaldo de Saimon City** → **Run workflow**.

Para saltarte uno (un arreglo de una letra, por ejemplo) escribe `[sin-respaldo]` en el título del pull request, o ponle la etiqueta `sin-respaldo`.

Para forzar uno aunque no venga de un pull request, escribe `[respaldo]` en el mensaje, o ponle la etiqueta `respaldo`.

## Cómo se llama

El nombre lleva la hora de Bogotá y el commit. El título del Release lleva tres cosas:

- La **fecha real** en America/Bogota.
- El **año y la fecha de juego**. El día cero es el 1 de enero de 1777. Cada 20 minutos reales son un día de juego. El ancla es la del servidor (`GAME_CLOCK_EPOCH`, si no la época guardada en la base, si no la que está en `tools/reloj.py`). No usa el reloj del navegador.
- Un **resumen en español**, armado con el título y la primera frase de cada pull request fusionado.

Ejemplo de título: `2026-11-15 04:08 Bogotá · año 1842 · Incluye: abre la casa colonial.`

## Qué entra en la copia de datos

| Qué | Dónde vive | ¿Entra? |
| --- | --- | --- |
| Jugadores y tiempo jugado | `players` | Sí |
| Cuentas (correo, teléfono, sesión) | `accounts` | Sí, sólo dentro del cifrado |
| Monedas, billeteras y bloques | `economy` | Sí |
| Libro madre | `libro_madre` y `libro_ids` | Sí |
| Depósito del banquito | `vault` | Sí |
| Certificados y su semilla | `nft` y `nft_seed` | Sí, la semilla sólo dentro del cifrado |
| Opiniones | tabla `simon_records`, tipo `feedback` | Sí |
| Notas de Simón (charlas y casos) | `simon_records`, tipos `conversation` y `case` | Sí |
| Anuncios de apartamentos | sus tablas | Sí, dentro del cifrado |
| Casas y muebles | el navegador de cada jugador (`lifeinc.casa.v1`) | No. El servidor no los tiene |
| Mascotas | — | No. El juego todavía no las guarda |

Si hay `DATABASE_URL`, la copia sale de Postgres (`pg_dump` y, además, un JSON de las tablas). Sin esa variable, sale de la carpeta `state/`.

El Release público sólo muestra fechas y conteos (cuántos jugadores, cuántos bloques). No muestra nombres, correos, saldos ni la semilla.

## Por qué va cifrado

El repositorio es público. Un Release de un repositorio público lo puede descargar cualquiera. Una copia en claro de la base llevaría correos, teléfonos, sesiones, la semilla de los certificados y las notas de Simón.

Por eso el archivo `saimon-datos-….lifebak` va cifrado con la frase `BACKUP_PASSPHRASE`. Sin esa frase el archivo no se lee. La frase no se guarda en git ni en el Release.

Si además configuras un almacén S3 (o compatible, como R2), el archivo cifrado se sube ahí y **no** se adjunta al Release. En el Release queda sólo el `manifiesto.json`, que no tiene datos privados.

## Qué tienes que configurar

En el repositorio de GitHub: **Settings → Secrets and variables → Actions → New repository secret**.

El valor se pega ahí. No lo pongas en un archivo del proyecto ni en el chat del pull request.

| Secreto | ¿Hace falta? | Qué pegar |
| --- | --- | --- |
| `BACKUP_PASSPHRASE` | Sí, para los datos | Una frase larga (20 caracteres o más). Guárdala en tu gestor de contraseñas. Sin ella sólo se etiqueta el código |
| `DATABASE_URL` | Sí, para copiar la ciudad de Render | La **External Database URL** de Postgres. La URL interna no sirve: GitHub no está en la red privada de Render |
| `GAME_CLOCK_EPOCH` | Sólo si el servicio web la tiene | El mismo número que en el servicio `lifein` |
| `SIMON_DATA_KEY` | Recomendada | La misma clave del servicio. Hace falta para leer las notas de Simón después de restaurar. Si está puesta, viaja **dentro** del archivo cifrado |
| `BACKUP_S3_BUCKET` | No | Si quieres el archivo fuera de GitHub |
| `BACKUP_S3_ACCESS_KEY_ID` | Con el bucket | Llave de acceso |
| `BACKUP_S3_SECRET_ACCESS_KEY` | Con el bucket | Llave secreta |
| `BACKUP_S3_ENDPOINT` | Si no es AWS | Por ejemplo el endpoint de R2 |
| `BACKUP_S3_REGION` | No | En AWS, `us-east-1`. Con endpoint, puedes dejarla vacía |

Cuando ya estén `BACKUP_PASSPHRASE` y `DATABASE_URL`, adjunta la base a un respaldo que se creó sin datos:

1. Actions → **Respaldo de Saimon City** → **Run workflow**.
2. Marca **solo datos**.
3. Si el respaldo no es el commit de hoy, pega su etiqueta en **etiqueta**.

## Ver la lista

En tu copia del repositorio:

```bash
git fetch origin --tags
python3 tools/respaldos.py listar
```

Verás la fecha de Bogotá, el año de juego y la fecha de juego, el más reciente primero. También puedes abrir la página de Releases en GitHub.

## Volver a una versión del código

Esto crea una carpeta nueva. `main` no se mueve y lifein.onrender.com no cambia.

```bash
python3 tools/respaldos.py codigo --etiqueta respaldo-20261115-0408-218e52a
cd restauracion/respaldo-20261115-0408-218e52a
python3 server.py --host 127.0.0.1 --port 8766
```

Ábrelo en http://127.0.0.1:8766/play/ . Usa otro puerto para no chocar con un servidor que ya tengas en el 8765.

Para desplegar **una copia** en Render (no el servicio `lifein`):

```bash
git fetch origin tag respaldo-20261115-0408-218e52a
git switch -c restauracion/respaldo-20261115-0408-218e52a respaldo-20261115-0408-218e52a
git push -u origin restauracion/respaldo-20261115-0408-218e52a
```

Crea un servicio web nuevo con esa rama y **otra** base Postgres. No cambies la rama de `lifein` si no quieres que la ciudad en vivo vuelva a ese código.

## Restaurar los datos en una copia

La frase se lee de la variable de entorno, no de la línea de comandos (así no queda en la lista de procesos).

```bash
export BACKUP_PASSPHRASE='la frase que guardaste'
python3 tools/respaldos.py restaurar --etiqueta respaldo-20261115-0408-218e52a
```

Los archivos quedan en `restauracion/<etiqueta>/state/`. Si antes corriste `codigo`, esa carpeta es el juego de esa fecha y arranca sin `DATABASE_URL`, leyendo esos JSON.

Para cargar los datos en **otra** base, vacía:

```bash
python3 tools/respaldos.py restaurar \
  --etiqueta respaldo-20261115-0408-218e52a \
  --database-url 'postgresql://USUARIO:CLAVE@HOST:5432/ciudad_copia'
```

Si esa base ya tiene filas, el comando se detiene. `--reemplazar` borra las filas de esa otra base y escribe las del respaldo. Sigue sin tocar la base cuyo URL es `DATABASE_URL`.

Hace falta `pg_restore` (el paquete `postgresql-client`) cuando el respaldo trae el volcado binario. Si no está, se usan las tablas en JSON.

La clave de Simón, si iba en el cifrado, queda en `state/simon-data.key` dentro de la copia. No la subas a git.

## Lo que no debes hacer para mirar

No uses `--produccion`. Esa bandera es la única que puede escribir encima de la base en vivo o de la carpeta `state/` del servidor. No hace falta para ver una copia ni para reorganizarla.

No pegues `DATABASE_URL`, la frase ni `SIMON_DATA_KEY` en el repositorio, en un Release ni en un pull request.
