# Economía SMC

Simulación educativa. No es dinero real.

## Escala

1 SMC = 100 Simonchis (SMH). La constante es `SMH_PER_SMC` en `tools/economy.py` y la misma cifra en `play/simulacion.js`. El tope sigue siendo 21.000.000 SMC.

Hasta 2026 el corte era 100.000.000 SMH por SMC. Al arrancar, `migrate_denomination` convierte cada saldo entero una sola vez:

`nuevo = round(viejo / 1_000_000)`

Así el SMC no cambia: 500 SMC viejos (50.000.000.000 SMH) quedan en 50.000 SMH, que siguen siendo 500 SMC. La bandera `meta.smhPerSmc = 100` impide repetirlo. El banco usa `meta.vaultSmhPerSmc`. Cada cuenta se anota antes y después. La reparación de saldos imposibles no corre en ese mismo paso y no usa el divisor 1.000.000, así que no se aplica dos veces.

El Libro madre no se reescribe: las firmas siguen sobre el entero original. Una cadena sin `smhPerSmc: 100` se cuenta, para el cupo y los saldos públicos, dividiendo esos enteros por 1.000.000. Una cadena nueva nace ya con la bandera y no se toca.

La Plata no entra en esa conversión. 1 SMP sigue siendo 100.000.000 platicas (SPH). El cambio publicado se conserva: 100 SMP = 1 SMC.

## Oro y cobre

El oro sólo sale de los ríos. El tope de oro es `GOLD_DAILY_SMC = 50` por jugador y por día (se puede subir con `MINE_DAILY_SMC` si la fórmula de antigüedad ya es mayor).

Cuando ese cupo se acaba, o cuando todas las vetas del río están en descanso, el cobre de la mina puede pagar SMC. El tope es `COPPER_DAILY_SMC = 150` por jugador y por día, aparte del oro. Usa las mismas trabas que el oro: hay que moverse, esperar el cooldown y no pasar las pruebas por hora. No crea un segundo libro ni salta el tope de 21.000.000. El HUD y Acuñar dicen: «Oro agotado: mina cobre, hasta 150 SMC hoy».
