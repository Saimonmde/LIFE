# Licencias de Saimon City — inventario y propuesta

Este texto es una propuesta. No cambia la licencia pública. `LICENSE` sigue siendo AGPL-3.0-or-later. Nada de lo que se recomienda aquí entra en vigor hasta que Juan Simón Barrera Jaramillo (Jay Montana) lo apruebe por escrito. Una licencia ya publicada no se revoca: quien recibió el código bajo AGPL conserva esa concesión.

El repositorio es público. El juego en https://lifein.onrender.com es una simulación. Las monedas de dentro no son dinero, no son valores y no prometen un canje. Tokenizar ese mundo, o usarlo como patrón de una economía, necesita consejo legal propio. Este documento no lo sustituye y no promete que un token vaya a existir, a valer o a poder venderse.

## Qué hay hoy en el repositorio

| Tipo | Dónde está | Licencia vigente |
| --- | --- | --- |
| Código del servidor y las herramientas | `server.py`, `tools/*.py`, `jugar.sh` | AGPL-3.0-or-later |
| Código del cliente | `play/*.js`, `play/*.css`, HTML de `play/` y `movil/`, `legal/` | AGPL-3.0-or-later, salvo lo de terceros de abajo |
| Motor 3D de terceros | `play/three.module.js` | MIT (autores de three.js, 2010–2024) |
| Arte 2D propio: teselas, personajes, objetos, materiales, interfaz | `graphics/tiles`, `graphics/characters`, `graphics/objects`, `graphics/materials`, `graphics/ui` | CC BY-SA 4.0 en lo designado en `asset-manifest.json`. Lo de procedencia pendiente no queda liberado |
| Iconos | `graphics/icons/` (16, 32 y 64) y SVG de `graphics/mining/` | CC BY-SA 4.0 si están designados. Si no, siguen pendientes |
| Modelo 3D | `graphics/models/caneca_envigado.glb` | Sidecar CC BY-SA 4.0. Es un escaneo propio de una caneca del Parque de Envigado. El puente de la 4 Sur y el resto del mundo 3D son código (mallas hechas en `play/`), no archivos de modelo |
| Escaneo Scaniverse | El GLB de la caneca está en el repo. `NOTICE.md` todavía dice que la captura no estaba incorporada | No se relicencia en este borrador. Hay que leer las condiciones de Scaniverse antes de ofrecer otra licencia. El escaneo no entrega derechos sobre la caneca física ni sobre el parque |
| Fuentes | `play/PixelifySans.ttf`, `play/fonts/AtkinsonHyperlegible-Regular.ttf`, `play/fonts/Cinzel-wght.ttf` | SIL OFL 1.1. No se pueden relicenciar |
| Textos e instructivo | `docs/`, `legal/`, `data/simon/`, el texto dentro de `play/instructivo.js` y `data/simulacion.json` | El código del instructivo es AGPL. Los textos de contenido designados van hoy en CC BY-SA 4.0 |
| Mapa jugable | `data/el-jardin.json` y su copia `data/el-jardin.js`, el bloque de Envigado, `data/valle-offset.json` | CC BY-SA 4.0 sobre la expresión propia. Los hechos geográficos no son exclusivos del proyecto |
| Datos derivados de OpenStreetMap | `data/valle-geo.json` y `data/valle-geo.js`: centros, parques y el río Medellín simplificado | ODbL 1.0. Hay que mantener la atribución «© colaboradores de OpenStreetMap» |
| Relieve | `data/relieve-aburra.json` y la rejilla dentro de `valle-geo` | Alturas NASA SRTM GL1, dominio público (Gobierno de Estados Unidos). La disposición simplificada del juego está marcada CC BY-SA 4.0 |
| Sonidos | No hay archivos `.wav`, `.ogg` ni `.mp3` | `play/sonido.js` sintetiza los tintineos con Web Audio. Es código, AGPL. No hay música de terceros |

Terceros que ya tienen su aviso y no se tocan: Three.js (MIT), Pixelify Sans (OFL, 2021), Atkinson Hyperlegible (OFL, Braille Institute, 2020), Cinzel (OFL, 2020). El detalle está en `THIRD-PARTY-NOTICES.md` y en `LICENSES/`.

## Código: MIT o seguir en AGPL

Hoy el código propio obliga a quien modifica el servidor y lo ofrece por red a publicar el código de esa versión. Esa es la AGPL. Sirve si la prioridad es que nadie cierre el juego y lo explote sin devolver el código.

MIT permite usar, modificar y vender el código, también dentro de un producto cerrado, con tal de conservar el aviso de copyright. Sirve si la prioridad es que otras personas y empresas adopten el patrón de economía del mundo sin tener que publicar su servidor. El coste es real: alguien puede hacer un fork comercial y no compartir los cambios.

Recomendación: no sustituir la AGPL en este paso. Si Jay quiere el patrón reutilizable en productos que no publican el servidor, puede ofrecer después una concesión adicional MIT sobre el código del que es titular. Quien ya clonó el repo bajo AGPL sigue pudiendo usarlo bajo AGPL. MIT no borra esa copia. Hace falta estar seguro de que cada contribución es suya o tiene permiso del autor. Sara y cualquier otra persona que haya aportado código conservan lo suyo hasta que acepten el cambio.

## Arte, iconos y 3D

Hoy lo designado está en CC BY-SA 4.0: se puede usar con fines comerciales, hay que atribuir, indicar cambios y compartir las adaptaciones con la misma licencia.

- CC BY 4.0: atribución, uso comercial permitido, sin obligar a la misma licencia. Es la que mejor encaja si un mundo tokenizado o un producto ajeno necesita mezclar el arte sin arrastrar el compartir igual.
- CC BY-SA 4.0: la de ahora. Protege que las mejoras del arte sigan abiertas. Complica meterlas en una obra que no pueda ser compartir igual.
- CC BY-NC 4.0: prohíbe el uso comercial. Cierra la puerta a vender, a una plataforma de pago y a casi cualquier tokenización con ánimo de lucro. No se recomienda.

Recomendación: CC BY 4.0 para el arte 2D, los iconos y el modelo 3D propios, cuando Jay lo apruebe y sólo sobre lo que él puede licenciar. Lo de procedencia pendiente en `asset-manifest.json` sigue sin licencia hasta que se aclare. El GLB de la caneca no se mueve de CC BY-SA hasta revisar Scaniverse.

## Textos, fuentes, mapa y marca

Los textos propios (instructivo, docs, lecciones) pueden pasar a CC BY 4.0: atribución, uso comercial, sin compartir igual. Hoy están en la línea de CC BY-SA.

Las fuentes se quedan en OFL. No hace falta, ni se puede, pasarlas a MIT o a CC.

Los datos que salen de OpenStreetMap se quedan en ODbL, con la atribución visible. El aviso está en `LICENSES/ODbL-NOTICE.txt`. El relieve SRTM sigue siendo dominio público y se cita como tal.

Los nombres y los logos no viajan con MIT ni con Creative Commons. Quedan reservados como marcas, estén o no registradas: **Saimon City**, **Simoncoin**, **Simonplata**, **Simonchis** y **RentoCity**. Usar el código o el arte no autoriza a presentar otro servicio, otro token o otra comunidad como oficial. El estado del registro sigue siendo el de `MARCA.md`: no consta aquí una solicitud ni un registro.

## Monedas del juego

Simoncoin, Simonplata y Simonchis son fichas de la simulación. No son dinero, no son un valor, no se canjean y este texto no promete una emisión, una venta ni un mercado. Si en el futuro se quiere un token de verdad, eso es una decisión legal aparte: hay que preguntar a quien pueda asesorar en valores, juegos y datos personales. Este repositorio no la toma.
