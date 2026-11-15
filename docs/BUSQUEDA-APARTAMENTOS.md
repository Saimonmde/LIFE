# Búsqueda de apartamentos

Actualización posterior: Simon IA/IO vive en este repositorio y la búsqueda cubre arriendo, renta corta y venta. El detalle nuevo está en [SIMON.md](SIMON.md). Lo que sigue es la nota de la primera entrega local.

# Búsqueda de apartamentos — entrega local para Jay

Rama local: `feat/apartment-search`. No se hizo push, merge ni despliegue. La carpeta `Juego/` no tenía Git; se inicializó allí un repositorio local con una instantánea base y esta rama. No es una rama descargada del repositorio remoto y todavía debe reconciliarse con su versión actual antes de publicar. La autorización previa que figura en otros documentos no reemplaza la instrucción actual de Jay: **main y producción requieren su sí explícito**.

## Estado y límites reales

Implementado: índice compartido SQLite/Postgres, normalización, filtros, deduplicación conservadora, sincronizador acotado, estado de cada fuente, endpoints compartidos de Simon IA/IO y pantalla `/play/apartamentos.html` (enlace en la entrada del juego).

**Aún no está resuelto el objetivo completo de encontrar inventario real de todas las fuentes.** La prueba de sincronización desde este ejecutor no pudo resolver DNS: cero anuncios externos incorporados. Los conectores HTML están implementados, pero necesitan validación y, donde no exista JSON-LD compatible, adaptación al HTML/API real del sitio. No se presenta el registro de un dominio como prueba de que ya se ingiera su inventario. No se cargaron anuncios inventados ni resultados de buscadores como inventario vigente.

No se encontró código de agentes existentes Simon IA/IO en esta copia. Las rutas nuevas ejecutan la búsqueda real en el índice y permiten probar ambos nombres desde la pantalla; **no sustituyen la conexión pendiente al orquestador de agentes de otra aplicación**. El análisis de texto cubre peticiones comunes, no una conversación general con un modelo de lenguaje. La respuesta enumera los filtros interpretados. Solicitudes con venta o comodidades no soportadas producen una aclaración, en lugar de prometer coincidencias.

También faltan la URL/API del Rentocity colombiano indicado por Jay y el dominio exacto de «Arrendamientos del Valle de Aburrá». Se preguntaron al usuario. No se eligió otra empresa por similitud de nombre.

## Fuentes y evidencia

Registro ampliable: `data/apartments/sources.json`. No hay condición de afiliación comercial.

| Fuente | Conector y estado de esta entrega |
| --- | --- |
| Rentocity, prioridad 0 | Feed paginado configurable. Falta URL/API y lista de dominios de publicaciones. |
| Metro Cuadrado | Descubrimiento desde búsquedas de los 10 municipios, JSON-LD y respaldo de ficha visible. No validado en vivo desde el ejecutor. |
| Finca Raíz | Descubrimiento por los 10 municipios y JSON-LD. No validado en vivo; puede requerir adaptación a datos de su aplicación. |
| Arrendamientos del Sur / Panda | Dominio `pandainmobiliaria.inmo.co`, extracción JSON-LD. No validado en vivo. |
| Arrendamientos del Valle de Aburrá | Feed configurable; identidad/dominio pendientes. |
| Sur Vivienda, Espacio Urbano, Panorama, Ayurá, del Norte | Descubrimiento y JSON-LD. No se afirma cobertura completa de sus publicaciones. |

Páginas consultadas durante el desarrollo:

- [Rentocity público](https://www.rentocity.com/): describe administración de propiedades, sin catálogo colombiano comprobado. No se asumió que sea el motor de Jay.
- [Panda Inmobiliaria](https://pandainmobiliaria.inmo.co/): identifica a Panda como marca de Arrendamientos del Sur S.A.S.
- [Sur Vivienda](https://www.survivienda.com/Paginas/), [Panorama](https://arrendamientospanorama.com/listado_arriendos.asp), [Espacio Urbano](https://www.espaciourbano.com/listado_arriendos.asp) y [directorio oficial de La Lonja](https://lonja.org.co/afiliados-1/) para identificar agencias y dominios.
- [Ficha Metro Cuadrado 23074-M6771804](https://www.metrocuadrado.com/inmueble/arriendo-apartamento-itagui-viviendas-del-sur-3-habitaciones-2-banos-1-garajes/23074-M6771804): se pudieron leer Itagüí, Viviendas del Sur, $3.000.000 y 75 m² con la herramienta web. Se guardó un extracto factual mínimo reconstruido exclusivamente para una prueba; no se importó como anuncio reciente ni se confirmó su disponibilidad.

Los accesos web de investigación pueden usar caché y no demuestran conectividad del sincronizador en producción. El catálogo no cubre todavía «todas» las agencias principales; se amplía agregando fuentes verificadas y adaptadores, sin cambiar la búsqueda ni los agentes.

## Probar localmente

Desde `Juego/`, con Python 3.11+ para el servidor completo (con `hashlib.scrypt`), y Node para las verificaciones JavaScript:

```sh
python3 -m unittest discover -s tools -p 'test_apartments.py' -v
node --check play/apartamentos.js
python3 tools/apartment_sync.py --source metrocuadrado --max-pages 40
python3 server.py --host 127.0.0.1 --port 8871 --sin-bots
```

Abrir `http://127.0.0.1:8871/play/apartamentos.html`. Revisar primero «Fuentes y estado de actualización». Buscar en un municipio con datos indexados, luego con presupuesto, barrio, área, habitaciones y baños. Probar una búsqueda sin coincidencias y ambos agentes. Verificar que cada resultado abre la ficha original y presenta fecha de observación. No se incluye una opción pública de importación ni una ruta que dispare rastreo desde una solicitud de usuario.

APIs:

```sh
curl 'http://127.0.0.1:8871/api/apartamentos?municipality=Envigado&max_price=2500000&min_bedrooms=2'
curl 'http://127.0.0.1:8871/api/apartamentos/fuentes'
curl -X POST 'http://127.0.0.1:8871/api/simon-ia/apartamentos' -H 'Content-Type: application/json' -d '{"message":"Encuéntrame un apartamento en Envigado hasta 2,5 millones con 2 habitaciones"}'
curl -X POST 'http://127.0.0.1:8871/api/simon-io/apartamentos' -H 'Content-Type: application/json' -d '{"message":"Apartamento en Bello hasta 1800000","filters":{"min_bathrooms":2}}'
```

Filtros estructurados: `municipality`, `neighborhood`, `min_price`, `max_price`, `min_area_m2`, `min_bedrooms`, `min_bathrooms`, `limit` (máximo 50), `offset` (máximo 10000). Precio en COP, área en m². `filters` complementa/sobrescribe el texto en las rutas de agentes. `results` incluye `publications` con todas las fuentes y enlaces de la coincidencia, precio, fechas y `applied_filters` en agentes.

El orquestador de Simon debe invocar `search_apartments` (contrato en `data/apartments/agent-tool.json`), consumir la respuesta y presentar únicamente sus resultados y enlaces. Cero resultados significa cero coincidencias recientes **en el índice**, no ausencia de oferta en el mercado. Errores/configuraciones pendientes de fuentes se devuelven por separado. No debe usar la memoria del modelo para completar anuncios faltantes.

## Conectar Rentocity y otras agencias

Configurar secretos sólo en el entorno, nunca en Git:

- `RENTOCITY_FEED_URL`: endpoint real del motor principal.
- `RENTOCITY_HOSTS`: dominios HTTPS permitidos de fichas, separados por coma.
- `RENTOCITY_FEED_TOKEN`: Bearer opcional, sólo para ese feed.
- `ABURRA_FEED_URL`, `ABURRA_HOSTS`: equivalentes para la agencia pendiente.
- `APARTMENTS_SOURCES_FILE`: ruta opcional a otro registro de fuentes administrado por el operador.

Contrato de feed (lista simple o `{listings: [...], next: "?page=2"}`):

```json
{
  "listings": [{
    "property_type": "apartamento",
    "operation": "arriendo",
    "currency": "COP",
    "price": 2500000,
    "municipality": "Envigado",
    "neighborhood": "La Magnolia",
    "area_m2": 70,
    "bedrooms": 2,
    "bathrooms": 2,
    "original_url": "https://DOMINIO-REAL/ficha/ID-REAL",
    "published_at": null,
    "active": true
  }],
  "next": null
}
```

Este ejemplo de contrato no es un anuncio y no se incluye en el índice. Los campos opcionales no conocidos quedan en `null`. `address` y `unit` explícitos ayudan a la deduplicación; no se inventan. Precio, moneda, municipio, tipo, operación y enlace de ficha válido son obligatorios. `published_at` es la fecha declarada por la fuente o `null`; `checked_at` es el momento en que el sincronizador leyó la publicación.

Feeds y páginas están limitados a HTTPS, dominios del operador, IP públicas, 4 MiB por documento, 15 s por solicitud y presupuesto de páginas. Se revalidan redirecciones y no se reenvían tokens a otro origen. HTML público respeta `robots.txt` y retardo; no evade autenticación, CAPTCHA ni bloqueos. Si una fuente no permite acceso o cambia su formato, se registra un fallo y se necesita su feed o adaptar el conector. No hay una API pública para proporcionar URLs arbitrarias.

## Persistencia, actualización y deduplicación

SQLite: `state/apartments.sqlite3` o `APARTMENTS_DB_PATH`. `state/` no se versiona. Con `DATABASE_URL`, se usan tablas dedicadas Postgres (`apartment_listings`, `apartment_source_status`), sin tocar saldos, cuentas o libros. En Render con disco efímero hay que usar Postgres o un disco persistente; la ruta SQLite por sí sola no sobrevive a reciclados.

Antes de habilitar la función en producción, el operador debe ejecutar la sincronización inicial y programar el comando cada 6 horas en el mismo almacén. **No se creó ninguna tarea programada ni se cambió Render en esta entrega.** El presupuesto predeterminado de 40 páginas por fuente es una pasada parcial: revisar `truncated`, ampliar el presupuesto o adaptar paginación/discovery. No afirma haber recorrido todo el inventario.

Cada publicación se actualiza por fuente + URL canónica. No se fusionan edificios enteros por parecido de precio/barrio/área. La fusión entre fuentes exige dirección y unidad explícitas más área, habitaciones y baños iguales, o idéntico enlace canónico. Se conserva cada publicación original con precio/fecha. Rentocity tiene prioridad como representante si está presente; otras fuentes siguen siendo consultables sin afiliación. La deduplicación conservadora puede dejar repeticiones cuando falta identidad de unidad.

No se borran anuncios por no aparecer en una pasada parcial o por un fallo de red. Se excluyen los marcados inactivos y los que lleven más de 48 horas sin observarse. Esto no equivale a confirmar disponibilidad telefónica. Los filtros se ejecutan sobre los documentos persistidos y la búsqueda ordena por precio; para inventarios muy grandes debe medirse rendimiento y llevar los filtros a columnas indexadas/SQL antes de escalar.

## Validación realizada

- 14 pruebas específicas aprobadas: diez municipios, normalización, filtros y nulos, enlaces, deduplicación y unidades distintas, prioridad Rentocity, caducidad e inactividad, persistencia/upsert, paginación con fallo parcial, feeds sin configurar, JSON-LD, extracto Metro Cuadrado, parser de peticiones, entradas inválidas, SSRF y procesamiento HTTP GET/HEAD/POST de ambos agentes con índice aislado.
- Prueba de sincronización de las 10 fuentes, máximo una página: 2 `configuration_required`, 8 `error` por DNS (`gaierror`), cero anuncios aceptados. No es una validación de conectores en vivo.
- Suite general ejecutada antes de las últimas 2 pruebas nuevas: 100 pruebas, 11 errores y 2 omitidas. Nueve errores por `hashlib.scrypt` ausente en el Python 3.9 del sistema y dos por Node no instalado. No se modificó la autenticación para ocultarlos.
- No se pudo ejecutar `node --check`: Node ausente.
- No se pudo realizar QA visual/servidor real: el sandbox deniega abrir el puerto local (`PermissionError`). La prueba HTTP específica usa lector/escritor en memoria y no prueba sockets ni un navegador.
- Postgres no validado en vivo: no hay una base de pruebas disponible. Debe verificarse con una base aislada antes de producción.

Pendientes para aceptación: datos de conexión de las dos fuentes ambiguas, acceso de red, resultados reales ingiridos y verificados por cada conector principal, cobertura/discovery de agencias adicionales, conexión al código real de los agentes, QA de navegador, validación de persistencia Postgres y reconciliación con el repositorio remoto. Después, Jay decide explícitamente si autoriza merge y despliegue.
