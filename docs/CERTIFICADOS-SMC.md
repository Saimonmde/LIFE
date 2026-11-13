# Certificados SMC, banco y conversión

Simulación educativa. Las SaiMonCoins (SMC) no son dinero real, no se venden y no se retiran.

## Tope

Hay como máximo 21.000.000 SMC. La reserva génesis (210.000 SMC, para recompensas de misión) ya cuenta dentro de ese tope y no es una emisión nueva: se conserva, no se borra. El río, el turno de la cantera y la conversión de monedas antiguas emiten sólo con una prueba de trabajo aceptada, y se detienen cuando no queda cupo, cuando la red ya emitió el cupo del día (144 pruebas, una cada 10 minutos) o cuando la cuenta llegó a su tope. El premio de cada prueba empieza en 1 SMC y se parte a la mitad cada 10,5 millones minados. Una cuenta nueva puede recibir 0,25 SMC al día; con el tiempo, el juego y las misiones llega como máximo a 6,25 SMC. Nadie, ni una cuenta de administración, tiene un cupo distinto. Un invitado juega y recoge objetos, pero no recibe SMC. Si una conversión no cabe entera, se acredita sólo el tramo del día y el resto queda pendiente.

## Conversión

- 1 moneda antigua del Jardín (el contador que no era SMC) = 1 SMC.
- Un saldo viejo guardado como SAI ya está en las mismas unidades. Al abrirlo sólo cambia el nombre a SMC. No se vuelve a multiplicar.
- La conversión de cada nombre ocurre una sola vez.

## Certificados

Cada emisión nueva crea un registro con id, código único (`SMC-…`), dueño, cantidad, fecha, casilla o fundición, hash anterior y firma Ed25519. Mover SMC al banquito, pagar a otro jugador o cobrar una misión desde la reserva no crea certificado.

La clave privada sale de la variable `NFT_PRIVATE_KEY` (64 caracteres hexadecimales) o se genera en `state/nft-key.json`. Ese archivo no se versiona. La clave pública se publica en `/api/nft/pubkey`.

- `GET /api/nft/list`
- `GET /api/nft/<id>` devuelve JSON compatible con metadatos ERC-721, por si más adelante se ancla. Hoy no hay cadena pública ni gas.
- `python3 tools/verify_nft.py state/nft.json` comprueba eslabones y firmas.

`state/` vive en el disco del servidor. En Render ese disco se pierde al redeploy: el libro, los certificados, el depósito y el tiempo jugado (`state/players.json`) vuelven a empezar. Está dicho en el aviso del juego. El tiempo sólo suma sesiones con latido (30 s) y corta a los 90 s de silencio.

## Banco

La Casa bancaria está junto al Parque de Envigado, fuera del bloque reservado (puerta en 113, 256; se entra desde 113, 257). Dentro hay mostrador, banquero y banquito.

El banquito y el baúl de la casa son el mismo depósito, guardado en el servidor (`state/vault.json`). Depositar o retirar SMC mueve saldo entre la billetera y el depósito: no cambia la cantidad emitida. Los objetos depositados quedan en ese depósito.

No hay un sistema de muerte que tire la mochila. Si más adelante una caída suelta lo que el jugador lleva encima, el depósito no entra en esa pérdida.

## Monedas acuñadas en el horno

En el horno, «Acuñar monedas» crea objetos de la mochila (`moneda_cobre`, `moneda_plata`, `moneda_oro`) y lingotes. Esos objetos no son SMC y no pasan por el libro mayor. «Acreditar SMC» sigue siendo la única vía de la fundidora que emite SaiMonCoins, y sólo después de la prueba de trabajo y del tope del día: lo hace el servidor, con código `SMC-…` y la subunidad SMH (1 SMC = 100.000.000 SMH). Sin esa prueba el mineral no se gasta y no aparece saldo. La mochila de objetos se guarda en el navegador, igual que el resto del inventario.

## Turno de la cantera

Ocho golpes de cobre o plata, con al menos un segundo entre ellos, pagan 10 SMC y un certificado. El oro del río sigue siendo la única bateada de oro. El adaptador OnePay/USDT existe en `tools/payout.py` y rechaza cualquier pago. En pantalla se lee que SMC no tiene valor real.

## Plata (SMP)

La Plata es otra moneda del libro, no un objeto de la mochila. 1 SMP = 100.000.000 platicas (SPH), enteros. El tope es 84.000.000 SMP y no hay premine ni reserva. El premio de cada prueba empieza en 5 SMP y se parte a la mitad cada 42 millones minados. La red apunta a 144 pruebas al día. Una cuenta nueva mina hasta 5 SMP ese día; con la edad de la cuenta (hasta 60 días), las horas jugadas (hasta 40) y las misiones (hasta 10) el tope llega a 125 SMP.

Se mina con la misma prueba firmada de un solo uso, en cualquier momento, también cuando la cuenta ya llenó su tope de SMC. Hacen falta cuenta, caminar, la pausa entre pruebas y los límites por IP. Un invitado no recibe nada. Una marca de administración no cambia el cupo.

De cada SMC nueva (río, horno que acredita SMC, turno o conversión) un quinto pasa al fondo de cambio y cuatro quintos se quedan en la billetera. El total emitido no cambia y sigue dentro de los 21.000.000 y del tope del día. Las misiones salen de la reserva génesis y no alimentan ese fondo.

Cambiar Plata por SMC quema la Plata (no vuelve al cupo minable) y paga SMC sólo desde ese fondo, a razón de 100 SMP = 1 SMC. El cambio no llama a la emisión: `minedSmh` no sube. Cada cuenta puede recibir hoy como máximo un quinto de su propio tope diario de SMC, y como máximo la décima parte del fondo (lo que ya había más lo que entró hoy). Entre todas las cuentas, hoy sólo puede salir la mitad del fondo. Así una sola cuenta no se queda con el oro apartado.

## Esculturas de reemplazo en Envigado

No había una obra pedida en el historial, y el bronce del Primer Poblado sigue fuera. En el parque hay tres piezas abstractas propias, sobre plinto, para que Jay las cambie:

1. **Anillo** — un anillo sobre un plinto, en la casilla 96, 264.
2. **Columna** — tres bloques desplazados sobre un plinto, en 102, 265.
3. **Óvalo** — un óvalo sobre un plinto, en 105, 268.

También hay cuatro bancas bajas (95, 262; 105, 262; 98, 270; 105, 270) y las tres canecas. Todas tienen colisión. El camino del parque sigue siendo transitable.
