# Ejecución mensual

Estado: tarea programada activa en el chat operativo privado. Primer lunes a viernes del mes a las 09:00 America/Chicago. Próxima ejecución al crearla: 2 de noviembre de 2026. No se aplica calendario de festivos. El usuario adjuntará manualmente los tres reportes en ese chat.

1. Exportar los tres reportes del mes completo. Usar ubicación correcta, concurso Eat In, ventas All dayparts/All departments y filtros de tarjetas acordados en tiempos.
2. Guardarlos en `inputs/AAAA-MM/`. Mantener los originales sin edición. No poner dos versiones del mismo reporte para el mismo período.
3. Revisar `private/config.local.json`: plantilla de turnos, incorporaciones y exclusiones. Conservar una copia privada por mes si se desea historial inalterable.
4. Ejecutar el CLI documentado en README. Si falta un archivo, empleado o total, corregir el dato de origen o configuración; no sustituir por cero.
5. Revisar los tres resultados. Generar el Excel con el flujo local existente y verificar fórmulas y formato antes de imprimir.
6. Publicar en Telegram solo cuando el usuario lo solicite explícitamente. Generar un borrador no constituye autorización de envío.

## Programación y recepción

Ejecutar para el mes anterior usando los tres archivos adjuntos al chat. Colocarlos en una carpeta privada de entrada para el CLI. Si falta alguno, dejar el mes pendiente y pedir únicamente lo faltante. No regenerar ni notificar si entradas, configuración y resultado no cambiaron. Avisar ante un resultado nuevo, un fallo o una acción requerida. La primera ejecución futura todavía no ha sido observada.

La adquisición de archivos desde Rosnet es un paso independiente: no se ha verificado acceso API ni descarga automática. La programación no elimina ese paso mientras los archivos se entreguen manualmente.

## Excel

El archivo de agosto/septiembre ya se generó con fórmulas y seis hojas revisadas visualmente. Su constructor inicial usa el runtime de Codex y períodos fijos. La tarea programada instruye al agente a adaptar períodos, filas y referencias a los datos nuevos y verificar cada hoja. Esto es un flujo asistido por agente; todavía no existe un exportador Excel portable y desatendido en el CLI público.
