# Economía SMC

Simulación educativa. No es dinero real.

## Escala

La única moneda que se muestra es la Simon Coin (SMC). El tope sigue siendo 21.000.000 SMC.

El entero guardado es un céntimo de SMC: 1 SMC = 100 céntimos, y 1 unidad = 0,01 SMC, exacto. Antes ese céntimo se llamaba Simonchi (SMH) y la constante sigue siendo `SMH_PER_SMC = 100` en `tools/economy.py`, la misma cifra que usa el baúl para no perder un céntimo. En pantalla el saldo se escribe en SMC, con coma decimal cuando hace falta: 1.250 unidades son 12,5 SMC.

Al arrancar, `migrate_smh_display` corre una sola vez. No divide esos enteros: volver a dividirlos los haría cien veces más chicos y rompería el baúl y las firmas. La bandera `meta.smhShownAsSmc` lo impide. Un saldo que todavía no es entero se pasa a céntimos sin redondear de más: 0,5 SMC queda en 50 unidades.

Hasta 2026 el corte era 100.000.000 unidades por SMC. `migrate_denomination` ya convirtió esa escala, una sola vez:

`nuevo = round(viejo / 1_000_000)`

Así el SMC no cambia: 500 SMC viejos quedan en 50.000 unidades, que siguen siendo 500 SMC. La bandera `meta.smhPerSmc = 100` impide repetirlo. El banco usa `meta.vaultSmhPerSmc`. Esa reparación no corre en el mismo paso que `migrate_smh_display`.

El Libro madre no se reescribe: las firmas siguen sobre el entero original. Una cadena sin `smhPerSmc: 100` se cuenta, para el cupo y los saldos públicos, dividiendo esos enteros por 1.000.000. Una cadena nueva nace ya con la bandera y no se toca.

La plata, el cobre suelto y el mineral de oro ya no son otra moneda. Su pase a SMC lo hace `tools/una_moneda.py` con las tasas de Jay (1 SMP = 0,01 SMC, 1 cobre = 0,001 SMC, 1 mineral de oro = 0,1 SMC). Este paso no las vuelve a convertir.

## Oro y cobre

El oro sólo sale de los ríos. El tope de oro es `GOLD_DAILY_SMC = 50` por jugador y por día (se puede subir con `MINE_DAILY_SMC` si la fórmula de antigüedad ya es mayor).

Cuando ese cupo se acaba, o cuando todas las vetas del río están en descanso, el cobre de la mina puede pagar SMC. El tope es `COPPER_DAILY_SMC = 150` por jugador y por día, aparte del oro. Usa las mismas trabas que el oro: hay que moverse, esperar el cooldown y no pasar las pruebas por hora. No crea un segundo libro ni salta el tope de 21.000.000. El HUD y Acuñar dicen: «Oro agotado: mina cobre, hasta 150 SMC hoy».

## Libro madre

La vista del libro madre muestra las Simon Coins minadas en el mundo, frente al tope de 21.000.000 SMC, y las minadas a nombre del jugador. Esas cifras salen de los registros firmados. No se parte el entero ni se cambia el código único.
