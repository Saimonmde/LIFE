# Mantenimiento de licencias, créditos y copias

Regla indicada por Simón: mantener actualizados los Creative Commons y los avisos del proyecto conforme se incorporan cambios; reemplazar el estado visible por el más reciente y guardar un respaldo cuando sea necesario.

## En cada actualización

1. Conservar las licencias ya adoptadas: AGPL-3.0-or-later para código propio y CC BY-SA 4.0 para contenidos designados. Una nueva versión del juego no requiere inventar una nueva licencia ni retirar los permisos de versiones anteriores. No migrar a otra versión de Creative Commons automáticamente sin una decisión aplicable del titular.
2. Registrar recursos nuevos o modificados, sus autores, procedencia, cambios y licencias. Verificar autorización antes de designar nuevos contenidos como CC. Mantener marca y terceros separados.
3. Conservar en un respaldo el manifiesto y los avisos anteriores cuando cambien. El historial de Git será adicional; no sustituye los datos de procedencia de cada recurso.
4. Regenerar el paquete de código fuente para que corresponda a la versión ofrecida en el juego. No incluir archivos de entorno, claves ni cachés.
5. Comprobar el alcance de cada actualización antes de publicarla y conservar los avisos de terceros.

## Herramienta local

`python3 tools/update_licensing.py --check` revisa inventario y paquete sin escribir.

`python3 tools/update_licensing.py` actualiza el inventario, registra cambios para revisión, respalda los avisos antes de sobrescribirlos y reconstruye `releases/saimoncity-fuente.zip`. No concede por sí sola una licencia a recursos nuevos y no publica en GitHub.

La autorización de un recurso nuevo se documentará expresamente en el manifiesto después de verificar procedencia y derechos. Un archivo cambiado conserva el historial de las versiones ya licenciadas: el estado «requiere revisión» no revoca los permisos concedidos sobre esas versiones o sus partes previamente licenciadas.
