# Simon en Saimon City

Simon IA y Simon IO son el mismo asistente. La pantalla está en `/play/simon.html`. El buscador de apartamentos está en `/play/apartamentos.html`.

No se hace merge ni despliegue sin el sí explícito de Jay.

## Qué responde

- Apartamentos en Medellín, Envigado, Sabaneta, Itagüí, La Estrella, Caldas, Bello, Copacabana, Girardota y Barbosa.
- Operaciones: arriendo, renta corta y venta. La renta corta es por días, por semanas o por contratos de 3, 6 o 12 meses, sólo cuando la publicación lo dice.
- Preguntas generales, con la fuente citada. Si no hay clave de buscador, usa un respaldo y lo dice.
- RentoCity sigue siendo el motor principal. Su sitio público no trae inventario: el catálogo entra por feed.

La herramienta que llama el asistente es `search_apartments` (`data/apartments/agent-tool.json`). No inventa anuncios ni enlaces. No usa presión ni urgencia falsa. El ritmo (voz, pausa, respuesta por partes) se adapta a cómo escribe o habla la persona y tiene tope en la velocidad que ella eligió.

## Memoria y reseñas

Hace falta consentimiento. El aviso está en el chat y en `/privacidad`. Los mensajes, el ritmo, los casos y las reseñas se cifran en reposo con `SIMON_DATA_KEY`. Sin esa variable el proceso crea `state/simon-data.key`, que en Render no sobrevive a un reinicio.

`DELETE /api/simon/datos` borra lo de esa sesión. Al cerrar, Simon pregunta si se abrió un enlace, si hubo solución (sí, parcialmente o no), una valoración opcional de 1 a 5, un comentario opcional y si la reseña es pública o privada.

`/play/admin/resenas.html` lista todas, con filtros y tres cifras: tasa de resueltos (sí / total), valoración media y proporción de chats con un enlace abierto. Pide la cabecera `X-Simon-Admin`. `/play/resenas.html` muestra sólo las públicas.

Con `DATABASE_URL` las tablas `apartment_listings`, `apartment_source_status` y `simon_records` van a Postgres. Si no está, se usan SQLite en `state/`.

## Variables en Render

Todas van en `render.yaml` con `sync: false`. Se pegan en el panel, no en git.

| Variable | Para qué |
| --- | --- |
| `DATABASE_URL` | Postgres. Sin ella, SQLite local. |
| `SIMON_DATA_KEY` | Cifrado de la memoria. Obligatoria en Render. |
| `SIMON_ADMIN_TOKEN` | Panel de reseñas. |
| `SIMON_COOKIE_SECURE` | `1` en HTTPS para marcar la cookie Secure. |
| `SIMON_WEB_SEARCH_PROVIDER` | `brave` (predeterminado), `serper`, `google` o `duckduckgo`. |
| `BRAVE_SEARCH_API_KEY` | Clave de Brave Search. |
| `SERPER_API_KEY` | Clave de Serper. |
| `GOOGLE_API_KEY` y `GOOGLE_CSE_ID` | Programmable Search. |
| `SIMON_LLM_API_KEY` | Opcional. Redacta a partir de los datos ya buscados. |
| `SIMON_LLM_BASE_URL` | Compatible con OpenAI. Por defecto `https://api.openai.com/v1`. |
| `SIMON_LLM_MODEL` | Por defecto `gpt-4o-mini`. |
| `SIMON_LIVE_SEARCH` | `0` apaga la lectura en vivo durante el chat. |
| `RENTOCITY_FEED_URL`, `RENTOCITY_HOSTS`, `RENTOCITY_FEED_TOKEN` | Feed de RentoCity. |
| `ABURRA_FEED_URL`, `ABURRA_HOSTS` | Agencia del Valle de Aburrá, cuando se confirme el dominio. |

## Índice

```sh
python3 tools/apartment_sync.py --source fincaraiz --max-pages 2
python3 -m unittest discover -s tools -p 'test_*.py'
```

El sincronizador respeta `robots.txt`, espera al menos un segundo y no guarda fotos. Una pasada corta no recorre todo el inventario. No hay una ruta pública para lanzar el rastreo.
