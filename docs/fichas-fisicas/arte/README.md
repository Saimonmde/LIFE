# Saimon City · fichas físicas coleccionables

Diseño de Sara · Diseñadora gráfica, para Jay Montana / Saimon City.

**El QR que se ve en estos SVG, PDF y vistas previas es solo de EJEMPLO.** Codifica la palabra `EJEMPLO`, va tachado y no es el código de ninguna pieza. Antes de grabar una ficha numerada hay que borrarlo y poner el QR único de esa pieza.

**Solo diseño.** Esta copia vive en el borrador `docs/fichas-fisicas/arte/`. No enciende el prototipo del servidor (`FICHAS_FISICAS` sigue apagado) y no cambia las licencias del juego.

Los SVG de las caras están en **milímetros reales** (`width="39mm"` y `viewBox="0 0 39 39"`, 1 unidad = 1 mm).

Todas las hojas de concepto en `hojas/` y los renders de `previews/` llevan el sello **VISTA PREVIA**.

El generador está en `src/build_monedas_fisicas.py`. Sigue apuntando a la carpeta de trabajo de Sara y a la fuente Inter de ese entorno; no es un paso del juego ni del deploy.

## Qué es (y qué no es)

Estas piezas son **fichas o medallas coleccionables** de Saimon City. **No son moneda legal**, **no tienen valor monetario** y **no tienen valor en pesos**.

Cada cara lleva una leyenda clara:

- anverso: `FICHA COLECCIONABLE · SIN VALOR MONETARIO`
- reverso: `COLECCIONABLE · NO ES MONEDA LEGAL`

El diseño **no imita** la moneda legal colombiana. A propósito se evitó:

- el escudo nacional y cualquier composición que lo recuerde (cóndor, cornucopia, gorro frigio, islas, navío)
- la leyenda «República de Colombia» y la mención al Banco de la República
- valores en pesos, el signo de peso o de dólar, denominaciones o un layout de moneda oficial (dentículos o perlado denso, cordoncillo de canto de curso legal, retratos institucionales)
- una serie de tamaños que se lea como «misma moneda, distinta denominación»: Simonplata y Simonchis tienen temática, borde y composición distintos

El sello central es la **S estilizada del juego** (la misma curva de `iconos/simonplata.svg` e `iconos/simonchis.svg`): una ese abierta, **sin barra vertical**, que no funciona como signo de peso ni de dólar.

## Las dos fichas

| Ficha | Metal visual | Tamaño primario | QR | Nº de serie (marcador) | Tema del anverso | Borde |
| --- | --- | --- | --- | --- | --- | --- |
| Simonplata | plata | **39 mm** | 15 mm | `SMP-000001` | S de Saimon City, montañas de Las Palmas, café y cacao; casa de bahareque en el reverso | pares de caña de guadua (12 haces) |
| Simonchis | cobre | **34 mm** | 14 mm | `SCH-000001` | S de Saimon City, café y cacao protagonistas, loma baja | 12 granos de café |

Ambas se pueden fabricar en el rango **30–39 mm**. El QR **no se escala por debajo de 12 mm**. Si se fabrica a 30 mm, el diseño se recompone (no es un escalado uniforme): el QR queda en 12 mm y la tipografía se mantiene en 1,20 mm o más. Esa comprobación está en `svg/variantes-30mm/` y en `hojas/hoja_comparacion_tamanos.png`.

## Archivos

```
monedas-fisicas/
  README.md
  fonts/NOTICE.txt
  src/build_monedas_fisicas.py
  svg/simonplata_39mm_anverso.svg
  svg/simonplata_39mm_reverso.svg
  svg/simonchis_34mm_anverso.svg
  svg/simonchis_34mm_reverso.svg
  svg/capas/…_corte.svg
  svg/capas/…_anverso_grabado.svg
  svg/capas/…_reverso_grabado.svg
  svg/variantes-30mm/simonplata_30mm_anverso.svg
  svg/variantes-30mm/simonplata_30mm_reverso.svg
  svg/variantes-30mm/simonchis_30mm_anverso.svg
  svg/variantes-30mm/simonchis_30mm_reverso.svg
  pdf/  (una cara por archivo, generado con cairosvg)
  previews/  (renders metálicos de cada cara primaria)
  hojas/hoja_vistas_metalicas.png
  hojas/hoja_comparacion_tamanos.png
  hojas/hoja_mecanica_cotas.png
```

Cada SVG de cara tiene tres capas (también como archivos sueltos):

| Capa / archivo | Color | Uso |
| --- | --- | --- |
| `corte` | trazo rojo `#FF0000`, 0,10 mm, sin relleno | contorno de corte láser o de troquel, diámetro exacto |
| `grabado` | negro `#000000` | arte, leyendas, cartela de serie, marcas de esquina del QR, QR de ejemplo y sello EJEMPLO |
| `anotaciones` | azul `#0055AA` | cotas y avisos para el fabricante; **no se graba** |

En el reverso, el grupo `qr-ejemplo` y el grupo `sello-ejemplo` son una muestra. Hay que **borrarlos y grabar un QR único real** en la zona reservada (el cuadrado marcado con esquinas en L). El código de muestra codifica solo la palabra `EJEMPLO` (QR versión 1, corrección H, 21 módulos) y además va tachado con la palabra **EJEMPLO**, para que no se use como código válido.

## Medidas y tolerancias

| Pieza | Ø primaria | QR | Zona de silencio | Área reservada (QR + silencio) |
| --- | --- | --- | --- | --- |
| Simonplata | 39 mm | 15 × 15 mm | 1,0 mm | 17 × 17 mm |
| Simonchis | 34 mm | 14 × 14 mm | 0,9 mm | 15,8 × 15,8 mm |
| Variante 30 mm (ambas) | 30 mm | 12 × 12 mm | 0,8 mm | 13,6 × 13,6 mm |

- Trazo mínimo: **0,20 mm**. Tipografía mínima: **1,20 mm** de altura (Inter Bold / ExtraBold, para que el palo no baje de ~0,20 mm).
- Módulo del QR de ejemplo: 0,71 mm (15 mm), 0,67 mm (14 mm), 0,57 mm (12 mm). Conviene no usar un QR de más módulos que una versión 2 si se mantiene este tamaño.
- Espesor sugerido (orientativo, no es una orden de fabricación): **2,0–2,5 mm**.
- Profundidad de grabado láser sugerida: 0,15–0,30 mm. Si se troquela en relieve, un relieve de unos 0,3–0,4 mm.
- Tolerancias sugeridas: diámetro **±0,10 mm**; posición del QR **±0,20 mm**; tamaño del QR **+0,3 / −0,0 mm** y nunca por debajo de 12 mm.
- El número de serie va en una cartela, con el formato `SMP-000001` / `SCH-000001` como marcador de posición.

La comparación a **escala 1:1 (300 dpi)** está en `hojas/hoja_comparacion_tamanos.png`. El plano de cotas de `hojas/hoja_mecanica_cotas.png` está a **escala 2:1** para que se lean las medidas.

## Tipografía y licencias

Los textos de las fichas van **convertidos a trazos** en los SVG. No se incrustan ni se redistribuyen archivos `.ttf`.

- **Inter**, de Rasmus Andersson / The Inter Project Authors. Licencia: SIL Open Font License 1.1. Uso: toda la tipografía de las fichas y de las hojas (sans moderna, en negrita o extranegrita para soportar el grabado).
- **UnifrakturMaguntia** no se usa en este paquete (queda reservada al título gótico del cartel «Reglas de la Mina»).

Los archivos de fuente no se copian aquí. Ver `fonts/NOTICE.txt` y `/workspace/sara-saimon/fonts/NOTICE.txt`.

La licencia MIT para el código del juego y Creative Commons para el arte, los textos y los íconos es una **propuesta**, no un cambio de las licencias que ya existan en el repositorio. Este paquete no altera esas licencias. Una tokenización, si llegara a haberla, queda solo como meta documentada: estas fichas no tienen valor monetario.

## Procedencia

| Campo | Dato |
| --- | --- |
| Autora | Sara · Diseñadora gráfica |
| Para | Jay Montana / Saimon City |
| Género | arte original, generado por programa (no es un calco de moneda legal ni de un sello oficial) |
| Sello S | la misma curva de los íconos del Libro mayor en `/workspace/sara-saimon/iconos/simonplata.svg` y `simonchis.svg` |
| QR de ejemplo | matriz de un QR versión 1, corrección H, payload `EJEMPLO`, incrustada en el script; no hay un código real grabado |
| Script | `/workspace/sara-saimon/monedas-fisicas/src/build_monedas_fisicas.py` |
| Cómo regenerar | `python3 /workspace/sara-saimon/monedas-fisicas/src/build_monedas_fisicas.py` |

## Nota legal breve

Estas fichas son un artículo de colección del juego Saimon City. No son medio de pago, no expresan un valor en pesos colombianos ni en otra moneda de curso legal, y no deben fabricarse ni presentarse de un modo que pueda confundirse con el efectivo del Banco de la República. El QR de las vistas previas es un ejemplo y hay que sustituirlo por un código único real antes de grabar una pieza numerada.
