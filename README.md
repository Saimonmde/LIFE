# Saimon City

Creación y dirección original: **Simón**. Mundo 3D en desarrollo, con mapa del Valle de Aburrá, minería y fundición, inventario, chat y cámara orbital.

Life Inc es la red madre del proyecto. Saimon City es el mapa del Valle de Aburrá en construcción, con los parques de sus diez municipios conectados. El mapa jugable es interpretativo; no es una reconstrucción urbana terminada.

## Licencias y contribución

Código propio: **AGPL-3.0-or-later**. Contenidos propios autorizados: **CC-BY-SA-4.0**. Marca y logo: política separada. Three.js conserva MIT y Pixelify Sans conserva SIL OFL 1.1.

- [Alcance y excepciones](LICENSE.md) y [adopción autorizada](ADOPCION.md).
- [Créditos](NOTICE.md) y [avisos de terceros](THIRD-PARTY-NOTICES.md).
- [Manifiesto de recursos](asset-manifest.json).
- [Guía de contribución](CONTRIBUTING.md).
- [Marca](MARCA.md) y [blockchain y propiedad](BLOCKCHAIN-Y-PROPIEDAD.md).

Cada persona conserva sus derechos sobre sus aportaciones. No se transfiere automáticamente copyright, marca ni un bien físico mediante un NFT. La licencia no registra la marca ni convierte el servidor actual en una red descentralizada.

La simulación de **SaiMonCoins (SMC)**, del **Libro Mayor** y del **Libro madre** es educativa. No es dinero real, no tiene valor ni canje, y no transfiere derechos, marca ni bienes. El tope es 21.000.000 SMC. 1 SMC = 100.000.000 **Simonchis (SMH)**, la unidad mínima, como un satoshi. Por ahora 1 SMC se parece, sólo como idea, a 1 BTC o a 1 USDT. Cada SMC nueva pide una prueba de trabajo, una cuenta y el tope del día. La reserva génesis de 210.000 SMC no es emisión nueva. El nombre anterior, Saimon Coins (SAI) con alias Saimony, ya no se usa. Sin `DATABASE_URL`, el servidor guarda el libro, el depósito, los certificados, las cuentas y el tiempo jugado en `state/*.json` (no se versiona; en Render ese disco se borra al reciclar la instancia). Con `DATABASE_URL` ese mismo estado vive en Postgres y sobrevive al redeploy. Sigue leyendo un archivo guardado con el símbolo viejo SAI.

## Mapa del repositorio

Todo está en la raíz. No hay una carpeta `El-Jardin` ni una copia paralela del mapa.

- `server.py` — HTTP, WebSocket, `/healthz` y la autoridad de las SMC.
- `play/` — vista de escritorio: mundo, casa colonial, Parque de Envigado, chat y `simulacion.js` (caballos, SMC, Libro Mayor, lecciones).
- `movil/` — entrada del teléfono; usa la misma vista con botones táctiles.
- `data/el-jardin.json` — el mapa del Valle de Aburrá (10 municipios). `data/el-jardin.js` es la misma carga para abrir sin `fetch`. `data/simulacion.json` — establo, profesora, economía y lecciones, fuera de la casa. `data/valle-offset.json` — el único desplazamiento del Parque de Envigado. `data/relieve-aburra.json` — alturas simplificadas. `data/parque-envigado-bloque.json` — teselas del parque, celda por celda, antes y después de moverlas.
- `graphics/` — arte original: teselas, objetos, personajes e interfaz.
- `tools/` — `relieve_aburra.py` (SRTM), `valle_aburra.py` (regenera el valle), `economy.py`, `libro.py` (libro madre), `nft.py`, `ed25519.py`, `vault.py`, `payout.py`, `verify_nft.py`, `test_economy.py`, `test_libro.py`, `test_nft.py` y `test_parques.py`. `tools/build.py` conserva un generador histórico del mapa; no hace falta para jugar.
- `docs/CERTIFICADOS-SMC.md` — tope de 21 millones, conversión 1:1, certificados, banco y esculturas de reemplazo.
- `graphics/ui/saimon-logo.png` — wordmark de Simón (CC-BY-SA-4.0). El título usa el derivado en oro `saimon-logo-gold.png` junto a la palabra City en una sans seminegra.

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

Hace falta Python 3.11 o más nuevo. En el Mac, sin `DATABASE_URL`, no hace falta pip: el estado queda en `state/`. En Render hace falta `pip install -r requirements.txt` para Postgres.

```bash
python3 server.py --host 0.0.0.0 --port 8765
```

- Escritorio: http://127.0.0.1:8765/play/
- Teléfono: http://127.0.0.1:8765/movil/
- `GET /` redirige a `/play/`.
- `GET /healthz` responde `200` (lo usa Render).

Si omites `--port`, el puerto sale de la variable `PORT` y, si no existe, es el `8765`. `--port` siempre gana sobre `PORT`. `./jugar.sh` arranca el mismo servidor en el puerto 8765.

## Render

El archivo `render.yaml` define el servicio web **lifein**. Cada push a `main` vuelve a desplegarlo. Render inyecta `PORT`; el arranque es `python3 server.py --host 0.0.0.0`.

Si el comando de build del servicio sigue diciendo `echo ok`, cámbialo por:

```bash
pip install -r requirements.txt && python3 tools/update_licensing.py --build-source-only
```

`pip install -r requirements.txt` instala `psycopg` para hablar con Postgres. Sin esa línea el servicio no puede usar la base.

### Variables en el servicio lifein

La base es Postgres 17 (Basic, Virginia), en la red interna del servicio `lifein`. En el panel de la base, copia **Internal Database URL** y pégala en el servicio web:

| Variable | Obligatoria | Para qué |
| --- | --- | --- |
| `DATABASE_URL` | para persistir | URL interna `postgresql://…` de Render. Sin ella se usan los JSON de `state/`. |
| `NFT_PRIVATE_KEY` | recomendada | 64 hexadecimales (32 bytes). Firma los certificados. Si falta, el servidor genera una y la guarda en Postgres (`nft_seed`), nunca en git. |
| `PUBLIC_URL` | recomendada | `https://lifein.onrender.com` — origen de las redirecciones OAuth. |
| `GOOGLE_CLIENT_ID` | para Google | Cliente OAuth de Google Cloud. |
| `GOOGLE_CLIENT_SECRET` | para Google | Secreto de ese cliente. |
| `FACEBOOK_APP_ID` | para Facebook | App de Meta. |
| `FACEBOOK_APP_SECRET` | para Facebook | Secreto de esa app. |
| `RESEND_API_KEY` | correo, opción A | API de Resend. |
| `EMAIL_FROM` | con Resend | Remitente, por ejemplo `Saimon City <cuentas@tudominio>`. |
| `SMTP_HOST` | correo, opción B | Servidor SMTP si no usas Resend. |
| `SMTP_PORT` | con SMTP | Normalmente `587`. |
| `SMTP_USER` | con SMTP | Usuario. |
| `SMTP_PASSWORD` | con SMTP | Contraseña. |
| `SMTP_FROM` | con SMTP | Remitente. |
| `TWILIO_ACCOUNT_SID` | para SMS | Cuenta de Twilio. |
| `TWILIO_AUTH_TOKEN` | para SMS | Token de Twilio. |
| `TWILIO_VERIFY_SERVICE_SID` | para SMS | Servicio Verify (`VA…`). |

El botón de cada proveedor aparece sólo si sus variables están puestas. Si no hay ninguna, la pantalla sigue dejando entrar con el nombre, como hasta ahora. Crear cuenta pide correo y teléfono a la vez: hace falta un emisor de correo (Resend o SMTP) y Twilio Verify.

URIs de redirección, exactas:

- `https://lifein.onrender.com/auth/google/callback`
- `https://lifein.onrender.com/auth/facebook/callback`

En local, si no defines `PUBLIC_URL`, el servidor usa el host de la petición (`http://127.0.0.1:8765/auth/google/callback`).

### Google

1. En [Google Cloud Console](https://console.cloud.google.com/apis/credentials) crea un proyecto.
2. Pantalla de consentimiento OAuth: externo, en prueba, con tu correo.
3. Credenciales → Crear ID de cliente OAuth → Aplicación web.
4. Orígenes de JavaScript autorizados: `https://lifein.onrender.com`.
5. URI de redirección autorizada: `https://lifein.onrender.com/auth/google/callback`.
6. Copia el ID y el secreto a `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`.

### Facebook

1. En [Meta for Developers](https://developers.facebook.com/apps/) crea una app de tipo consumidor.
2. Añade el producto Facebook Login → Web.
3. URI de redirección de OAuth válida: `https://lifein.onrender.com/auth/facebook/callback`.
4. Copia el identificador y el secreto a `FACEBOOK_APP_ID` y `FACEBOOK_APP_SECRET`.
5. Mientras la app esté en desarrollo, sólo entran los administradores y testers.

### Twilio Verify

1. En Twilio crea un servicio Verify.
2. Copia Account SID, Auth Token y el SID del servicio (`VA…`) a `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` y `TWILIO_VERIFY_SERVICE_SID`.
3. El teléfono se escribe con prefijo internacional (`+57…`). El código SMS caduca a los 10 minutos. Hay como máximo 5 envíos por hora.

### Correo

Resend: verifica un dominio, crea una API key y define `RESEND_API_KEY` y `EMAIL_FROM`.

O SMTP: `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD` y `SMTP_FROM`.

El código del correo también caduca a los 10 minutos. Quien ya jugaba con un nombre y un `X-Wallet-Token` puede escribir el mismo nombre: la cuenta nueva se ata a esa billetera y no pierde las SMC.

## Libro madre y Simonchis

Cada bateada de oro en el río acuña un registro único en el libro madre, por ejemplo `SMC-3-A1B2C3D4`. Lleva monto en SMH enteros, billetera, río, hora, nonce de una prueba de trabajo barata, hash SHA-256, hash anterior y firma Ed25519 con `NFT_PRIVATE_KEY`. No se vuelve a emitir el mismo código. En Postgres el código tiene una clave única (`libro_ids`); sin `DATABASE_URL` el conjunto vive en `state/libro-ids.json` y la cadena en `state/libro-madre.json` (almacén `libro_madre`).

Los saldos, el banco y las transferencias usan sólo enteros SMH. Un saldo que ya estaba en saimonitos no se multiplica otra vez: 1 saimonito = 1 SMH. Un contador guardado en SMC, como el total minado, se multiplica una vez por 100.000.000. El tope es 2.100.000.000.000.000 SMH. Más de 8 decimales se rechaza, para no crear ni destruir un Simonchi al redondear.

En el juego, el panel **Libro madre** (también en `/movil/`) muestra las últimas acuñaciones. Al batear, un aviso dice `Acuñaste SMC-…` y abre ese registro. El saldo se puede ver en SMC o en SMH; `/pagar` acepta `1,5 SMC` o `12345 SMH`.

Lectura pública:

- `GET /api/libro`
- `GET /api/libro/<id>`
- `GET /api/libro/verificar`

`LIBRO_DIFICULTAD` (1 a 20, por defecto 12) es cuántos bits en cero pide la prueba de trabajo. Si tarda, el servidor baja un bit para no frenar la partida.
