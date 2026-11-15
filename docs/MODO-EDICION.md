# Editar mundo

La capa de ediciones es un JSON aparte del mapa de `data/el-jardin.json` y de los guardados de cada cuenta. El servidor la manda al entrar y, al guardar, la reenvía por el WebSocket a quien esté conectado.

Sólo un administrador escribe. El papel sale de `social.role_of` (`admin` o `simon`, el dueño), de las marcas `admin` / `owner` / `dev`, o de correos en `ADMIN_USERS`. Quien no lo es no ve «Editar mundo (admin)» al final del menú ⚙. Un POST o un mensaje `world_edit` de otra cuenta responde 403 y no cambia el archivo.

## Pública y de muestras

`LIFE_ENV` vale `public` si no se define.

| | Pública | Muestras |
| --- | --- | --- |
| Variable | `LIFE_ENV=public` | `LIFE_ENV=preview` |
| Archivo | `state/world-edits.json` | `state/world-edits-preview.json` |
| Almacén | `world_edits` | `world_edits_preview` |
| Señal | ninguna | la pastilla VERSIÓN DE MUESTRAS |
| Sembrar / restablecer | no | sí, con la palabra RESTABLECER |

Así un ensayo no pisa el mundo que ven los jugadores.

En `render.yaml` el servicio `lifein` queda en `public`. El bloque comentado `lifein-preview` es la misma rama con `LIFE_ENV=preview`. No está activo: hay que pegarlo como segundo servicio si se quiere un sitio de muestras. Este cambio no despliega nada.

## Pasar un diseño de muestras al mundo público

En muestras, exporta el diseño (JSON `life-world-design`). En el servicio público, un administrador importa ese archivo, escribe `PROMOVER` y confirma. El diseño entra en la lista y, si se aplica, sustituye la capa publicada. El mapa base sigue igual. `REVERTIR` vacía la capa y deja una versión anterior en el historial.
