# Integración de la entrega local de Codex

GitHub `main` es la única fuente. Esta nota dice qué se trajo de la copia local que nunca se subió (14 de noviembre de 2026) y qué se dejó fuera. No se copió `state/`, ni cuentas, ni saldos, ni tokens.

## API de intercambio (para café, cacao y el resto)

El módulo genérico ya está en `tools/trades.py`. No hace falta otro. Quien acredite bolsas lo hace en la mochila del servidor, no en el `localStorage` del navegador:

```python
import purses
purses.credit(vault_state, nombre_visible, 'bolsa_cafe', 1)
purses.credit(vault_state, nombre_visible, 'bolsa_cacao', 1)
```

Esos dos ids son el contrato. También vale cualquier `^[a-z][a-z0-9_]{0,31}$` sin editar `trades.py`. Después hay que guardar el vault con la misma persistencia del depósito. El mensaje `economy` de esa persona trae `purse.items` y `purse.catalog`.

Oferta, en enteros:

```python
{'smc': 0, 'smp': 0, 'cobre': 0, 'items': {'bolsa_cafe': 1, 'bolsa_cacao': 1}}
```

`smc` son SMH (1 SMC = 100.000.000). `smp` son SPH. `cobre` son Simonchis enteras. `amountSmh` sigue siendo alias de `smc`.

WebSocket, sólo entre las dos conexiones:

| Cliente | Servidor |
| --- | --- |
| `{t:'trade_start', peer}` | `trade_state` a las dos |
| `{t:'trade_offer', id, revision, offer}` | sube `revision` y borra aceptaciones |
| `{t:'trade_accept', id, revision}` | primera aceptación |
| `{t:'trade_confirm', id, revision}` | segunda; a la cuarta se mueve el saldo |
| `{t:'trade_cancel', id}` | `trade_end` |

Reglas que se conservan de la entrega: una sesión por persona, billetera desbloqueada, las dos en la ciudad, a 15 casillas (30 m) o menos, 180 s sin actividad, y una versión vieja se rechaza. No se aparta el saldo entre la aceptación y la confirmación. El libro público (`historia` y `/api/libro`) anota el monto y el objeto, y omite los nombres. La firma del libro madre sí conoce las cuentas de SMC; esa vista no se publica.

`balances(name)` devuelve `{smc, smp, cobre, items}`. `commit(...)` persiste economía, libro y vault en un solo `save_bundle`.

## Qué se portó

- `tools/trades.py`, `tools/purses.py` y la ventana `play/economy-ui.js`: el protocolo de cuatro respuestas, ampliado a Simonplata, Simonchis y objetos. En Jugadores, en el nombre sobre la escena y al pulsar a la otra persona se abre el intercambio.
- El puente de la 4 Sur. `tools/bridge4sur.py` lo estampa en memoria al arrancar el servidor. `play/bridge4sur.js` hace lo mismo sobre el mapa que carga el cliente y dibuja el tablero, las barandas, los pilones y 51 tirantes. No se reescribió `data/el-jardin.json`. Es una recreación por código con 560 m y pilones de 47 m nominales, a 0,2 unidades de motor por metro, entre x 82–138 e y 238–242. El escaneo de Polycam queda en `scan.status = not-loaded`. Los dos accesos salen en Destinos.
- Banco e inventario, sólo donde faltaba: el botón Banco e inventario, el aviso de billetera bloqueada o de saldo en caché, la emisión de hoy (disponible, límite y pendiente, sin sumarla al saldo) y los iconos y nombres de los objetos del depósito. Guardar y retirar SMC, SMP y objetos siguen siendo los que ya tenía main. Esas operaciones piden conexión y billetera desbloqueada.

## Qué se dejó fuera

- `state/`, cuentas, saldos, tokens y cualquier `economy.json` o `vault.json` de la copia local.
- `comfort.js`, `persistence.js`, `journey-core.js` y el parche de apartamentos: main ya tiene cuenta, casa, paneles y apartamentos, y otros cambios de interfaz van en paralelo.
- La franja de monedas, las flechas de los paneles, la fecha de aventura de 1777 y el botón Correr. El cajón y el HUD de main ya muestran las tres monedas.
- Reescribir el mapa o aplicar `banco-trade.patch` encima de `server.py`. El parche estaba hecho contra un `server.py` anterior e incluía cambios que main ya tiene.
- Cargar el GLB del puente. No venía en la entrega.
- Tratar el modo de archivos como una transacción financiera. Sigue el `save_bundle` que ya existe: en Postgres es una transacción; en archivos cada reemplazo es atómico, pero un corte a mitad puede desajustar economía y libro.
