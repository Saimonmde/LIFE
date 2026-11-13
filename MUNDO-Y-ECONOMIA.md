# Valle, montura y economía de prueba

Esta versión conserva el inicio en la casa colonial, la mina y los controles existentes. Amplía el mapa de 352×176 a 352×448 casillas. Incluye destinos a los parques principales de los diez municipios solicitados. El relieve y las plazas son una interpretación procedural; no son levantamientos topográficos ni reconstrucciones históricas verificadas.

El caballo espera junto a la casa de Envigado. «Montar caballo» acerca al personaje; tocarlo de nuevo monta. Se puede elegir paso o galope y desmontar. Al entrar a la casa o a la mina se desmonta automáticamente. La montura es una primera versión local; todavía no se sincroniza visualmente con otros jugadores.

El logo dorado conserva la reserva de marca. El texto Saimon City usa la fuente gótica UnifrakturMaguntia, con su licencia OFL existente.

## Monedas y libro mayor

Economía de prueba, sin blockchain, tokens, valor monetario real ni cuentas verificadas. El suministro inicial de prueba aprobado por el usuario es 21.000.000, configurable mediante SAIMON_COIN_SUPPLY **antes de crear la base**. Al reabrir una base existente se conserva el suministro de su génesis.

La fundición en el horno central de la mina exige créditos de mineral registrados por el servidor. El servidor decide la cantidad recogida, comprueba la zona, proximidad y regeneración. Al fundir monedas transfiere saldo desde la tesorería, sin incrementar la emisión. Valida la receta y procesa los reintentos con identificadores únicos. SQLite confirma las operaciones de forma atómica. El diario impide modificaciones/borrados ordinarios y enlaza registros mediante hashes; no constituye consenso descentralizado ni protege contra el administrador del servidor.

Cada navegador recibe una clave aleatoria para recuperar su monedero invitado. El nombre público no es la contraseña. Si se borra el almacenamiento del navegador se pierde la recuperación de ese monedero; todavía no hay cuentas ni recuperación de claves.

El botón Libro mayor muestra el saldo, tesorería, circulación y las últimas veinte transferencias del monedero. Las monedas antiguas de demostración quedan separadas; no se convierten automáticamente. Las recompensas de misión actuales son puntos de misión, fuera de la emisión fija. Los lingotes y el inventario general continúan en el guardado local. El control de movimiento todavía acepta posiciones del cliente: hace falta validación de movimiento y una migración completa del inventario antes de usar esta economía como sistema competitivo resistente a trampas.

## Persistencia y despliegue

La base local es data/economy.sqlite3 (excluida de Git, del archivo de fuentes y del servidor estático). SAIMON_ECONOMY_DB permite ubicarla en almacenamiento persistente. El servicio Render gratuito actual no garantiza persistencia de archivos entre despliegues: no debe considerarse una economía permanente allí hasta conectar una base o volumen persistente. El despliegue no crea servicios de pago ni emite activos reales.

Copiar la base con la API de respaldo de SQLite al realizar respaldos activos; no copiar solamente el archivo mientras hay un WAL activo. No reemplazar una base con otra nueva para una actualización del código.
