# Fichas y medallas con QR

Propuesta. No está encendida en la web. El prototipo del servidor sólo responde si la variable `FICHAS_FISICAS` vale `1`. Sin eso, `/ficha/` y `/api/fichas/` responden como si no existieran.

Esto no cambia las reglas de Simoncoin, Simonplata ni Simonchis. No acuña. No promete un token. No diseña un objeto que se parezca al dinero del Banco de la República.

## Lo que el QR no prueba

**El QR, el rastro y el pase en la app no prueban que tengas la pieza en la mano ni que el metal sea auténtico o puro. No prometen dinero oficial ni valor.**

Una foto del código abre la misma página. El servidor sólo comprueba que el enlace fue firmado y qué cuenta del juego tiene asociada la ficha. No pesa el metal, no lo ensaya y no ve si la pieza está delante de la cámara.

Para afirmar posesión física, autenticidad o pureza haría falta algo aparte de esta app:

- un ensayo independiente del metal;
- un certificado del refinador o de quien acuñó la pieza;
- una cápsula o sello que se note si alguien la abrió;
- mirar la pieza en persona en el momento de entregarla.

Nada de eso lo sustituye el QR ni el historial de pases. La ficha no es dinero del Banco de la República y este sistema no le asigna un precio.

## Cómo se llama

En Colombia una pieza no puede imitar la moneda o el billete de curso legal. Estas piezas se llaman **fichas** o **medallas coleccionables**. No son pesos, no son un medio de pago oficial y no se presentan como dinero del Estado.

Simoncoin, Simonplata y Simonchis siguen siendo saldos del juego. La ficha física representa una cantidad que ya existía en una de esas cuentas y que queda apartada mientras la pieza circula. Si algún día se quiere un token negociable fuera del juego, hace falta consejo legal. Este texto no lo sustituye y no promete una emisión, un precio ni un mercado.

## Qué lleva cada pieza

Cada ficha tiene un identificador propio en el almacén del servidor, el mismo donde ya vive la economía cuando hay `DATABASE_URL`, o el JSON de economía cuando no la hay. El prototipo guarda la ficha dentro de ese documento para que el apartado y el registro entren juntos.

El QR impreso o grabado no lleva el secreto. Lleva una dirección:

`https://lifein.onrender.com/ficha/FIC-…?m=…`

`m` es un HMAC de la pieza con una clave que sólo está en el servidor. Sin ese código la página pública no confirma la ficha: responde igual que si el identificador no existiera, para no delatar cuáles son válidos.

La página pública, cuando el código cuadra, muestra serie, metal de juego, peso, fecha de emisión, estado y la lista de hechos (emisión, pase, pérdida, robo, revocación, retiro). No muestra nombre, correo, teléfono ni el identificador de la cuenta. El historial dice qué pasó, no quién es la persona.

Hay un número de serie por pieza. Puede grabarse al lado del QR para que una persona lo lea sin cámara. El serie solo no alcanza para dar la ficha por buena: hace falta el HMAC.

Opcional, y fuera del QR: un segundo código escondido (interior del engaste, etiqueta que se rompe) o un NFC. El prototipo guarda el segundo código como un hash. Retirar la ficha de la circulación lo pide si la pieza lo tiene. El NFC no está implementado; el documento lo deja como refuerzo físico, no como algo que el servidor ya lea.

## Una lectura no transfiere

Cualquiera puede fotografiar el QR y abrirlo. Por eso leer sólo **empieza** un pase. Crea una intención y enseña la página. El titular no cambia. El saldo no cambia.

Para que la ficha pase de una cuenta a otra hace falta que las dos personas hayan entrado con su cuenta, y las cuatro respuestas del intercambio que ya existe:

1. Quien tiene la ficha acepta esa lectura.
2. Quien la recibe acepta la misma lectura.
3. Quien la entrega confirma.
4. Quien la recibe confirma.

Hasta la cuarta respuesta no hay pase. Si la ficha ya no está en esa cuenta, si está marcada como perdida, robada o revocada, o si hay lecturas seguidas en sitios distintos, el servidor no la mueve.

El pase es atómico: o cambia el titular y queda el apunte, o no cambia nada. La cantidad apartada en `reserva_fichas` sigue igual. No entra en la billetera gastable de quien recibe. La ficha es la custodia. Quien la recibe la ve en su cuenta como pieza, no como saldo suelto para gastar otra vez.

## Cómo no se duplica el valor

Emitir una ficha descuenta el saldo gastable de quien la pide y suma la misma cantidad a `reserva_fichas`. El total del metal no crece. `minedSmh` y los topes no se tocan. Si no hay saldo, no nace la ficha.

Mientras circula, esa cantidad sigue en la reserva. No se puede gastar en el juego y a la vez tener la medalla. Eso es el respaldo: una pieza, una cantidad ya emitida, apartada.

Retirar la ficha (fundirla o darla de baja en el juego) devuelve esa cantidad a la billetera gastable de quien la tiene en ese momento, y el estado pasa a `retirada`. Tampoco acuña. Si la pieza tiene segundo código, hay que presentarlo: no viaja en el QR.

Un pase entre dos cuentas no toca la reserva ni la billetera gastable. Sólo cambia el titular interno.

## Copias, pérdida y robo

Una foto del QR abre la misma página. No completa el pase. Además:

- El HMAC impide fabricar una dirección válida a partir del serie.
- El segundo código o un NFC, si se usan, no salen en la foto.
- Cada lectura puede llevar un lugar en texto corto, no una coordenada. Si la misma ficha se lee en dos lugares distintos dentro de diez minutos, queda una alerta y no se aceptan pases nuevos hasta que se revise. La página pública dice que hubo lecturas en sitios distintos. No publica el lugar ni a la persona.
- Perdida, robada o revocada las marca quien tiene la ficha en la cuenta. Esos estados bloquean el pase. El saldo sigue apartado. No se entrega a quien sólo tenga la foto.

El servidor no decide solo que una ficha fue robada por ver dos lecturas. La alerta detiene los pases. La marca de robo la pone la cuenta titular.

## Libro

Cada emisión, pase, marca y retiro deja un hecho en el libro de fichas y un apunte en el libro público de la economía. El apunte público dice que hubo una ficha coleccionable y la cantidad. No dice de quién a quién. El mismo criterio que el intercambio entre jugadores: las partes no se publican.

## Qué está escrito y qué no

`tools/fichas.py` hace emitir, leer, las cuatro respuestas, marcar y retirar. `tools/test_fichas.py` cubre el apartado sin acuñar, la página sin datos personales, la lectura que no transfiere, el pase sólo a la cuarta confirmación, la alerta de dos lugares y el segundo código fuera del QR.

El servidor engancha `/ficha/` y `/api/fichas/` sólo con `FICHAS_FISICAS=1`. Apagado, que es el valor de ahora, esas rutas responden 404.

No hay impresión del QR en el juego, no hay NFC y no hay una pantalla nueva en el cliente. Eso queda para cuando Jay lo pida, después de este borrador.
