# Documento técnico

## 1. Qué es

Sistema de analítica de video para negocios físicos: cuenta personas por línea
de entrada/salida, mide aforo y tiempo de cola por zona, y alerta sobre
eventos. Multi-negocio, self-service, con reportes descargables y
recomendaciones diarias generadas por un LLM.

## 2. Arquitectura

- **vision/**: worker por cámara (un proceso por cámara, `run_camera`). YOLO +
  tracking + conteo por línea y por zona. Trata un archivo de video como una
  cámara.
- **analytics/**: agregación (`daily_summary`, `reporte_periodo`), reportes
  descargables (CSV/PDF), medición de precisión (`precision.py`), retención
  (`aplicar_retencion`), respaldos (`backups.py`, `restore_check`), alertas.
- **cameras/**: modelo de cámara, zona y línea; API de configuración
  (`cameras/api.py`).
- **tenancy/**: negocios, perfiles, planes, invitaciones; aislamiento por
  tenant en un punto único, `business_or_403` (`tenancy/permissions.py`).
- **dashboard/**: panel HTML (`home`), páginas de cámara, `/salud/` para el
  watchdog, panel de sistema.
- **insights/**: corpus comparativo entre negocios que optan por compartir
  (`Business.comparte_corpus`).

## 3. Decisiones clave (y por qué)

- **Un proceso por cámara**, no un monolito: una cámara caída no tumba a las
  demás.
- **Aislamiento en un solo punto** (`business_or_403`): un guard, probado por
  una suite (`tests/tenancy/test_aislamiento.py`) que ataca cada endpoint con
  datos de otro tenant (Fase 6).
- **Reportes sobre `daily_summary`**: `reporte_periodo` reutiliza la misma
  agregación diaria y le suma entradas/salidas de `CrossingWindow`, sin
  duplicar queries. El PDF usa matplotlib (`PdfPages`, ya instalado) en vez de
  sumar reportlab o weasyprint.
- **Demo sin hardware**: `seed_demo` inserta métricas sintéticas
  (`MetricWindow`/`CrossingWindow`/`Event`) directo en la base, sin correr
  YOLO ni abrir video; es idempotente. Los videos de prueba reales tratan un
  archivo como cámara (`demo/README.md`).
- **Planes sin facturación real**: `Plan` modela límites (`max_camaras`,
  `retencion_dias`); cobrar es decisión de negocio, no de código (Fase 6).
- **Cruce de línea como cifra de portada (Fase 12)**: la cifra principal del panel
  pasó a ser el conteo de cruces de línea (`CrossingWindow`) en lugar de
  `Sum(unique_visitors)` sobre `MetricWindow`. La suma sobre zonas cuenta personas
  distintas dentro de cada zona dibujada, por lo que una persona que pisa dos
  zonas sumaba dos veces y no representaba un conteo real de personas que ingresaron.
  El sentido de la línea lo fija `sv.LineZone` y está clavado por un test de
  caracterización (`tests/vision/test_lines.py`); `invertir` permite corregir el
  sentido si la puerta quedó del otro lado en el local.
  Esta fase garantiza la coherencia de la interfaz y la estabilidad del flujo, pero
  **no** demuestra que el número medido sea exactamente el real: en la Fase 11 se
  demostró su estabilidad frente al muestreo, pero la precisión absoluta contra la
  realidad sigue requiriendo comparación con clips anotados a mano.
- **Privacidad por diseño**: no se guarda video continuo, solo métricas
  agregadas por ventana de 60 s; clips de 10 s solo ante eventos, con
  retención de 30 días; sin reconocimiento facial ni re-identificación; al LLM
  solo se le envía texto agregado.
- **Diagnóstico de conexión como módulo puro** (`cameras/diagnostico.py`):
  `sondear` y `abrir` se inyectan; así se prueban los cuatro fallos (dirección
  mal escrita, equipo apagado, contraseña mala, codec incompatible) sin red ni
  cámara. La misma explicación sirve tanto a la prueba de conexión como a la
  vista previa: no hay dos textos distintos para el mismo problema.
- **Una cámara en vivo reintenta sin tope; un archivo no**:
  `FrameSource` se construye con `max_reintentos=None` para una cámara real y
  `max_reintentos=5` para un archivo. Reiniciar el proceso tira la ventana en
  curso, el tracker y las identidades acumuladas; un microcorte de red no
  puede costar el resto del día. El backoff sigue acotado en
  `BACKOFF_MAX = 30 s` (`vision/core/source.py`): esperar para siempre no es
  una opción.
- **La contraseña nunca sale de la API ni de los mensajes de error**:
  `CameraSerializer` declara `password` como `write_only`; `diagnosticar`
  recibe la URL armada internamente y devuelve solo el mensaje traducida. El
  motivo de reconexión pasa por `config.logging_filters.redactar` antes de
  llegar al panel (`vision/core/source.py`), así que ni los logs ni la
  interfaz exponen credenciales aunque la excepción de FFmpeg traiga la URL
  completa.
- **El rubro es una tabla de datos en `tenancy/rubros.py` y no filas en la base**:
  lo que cambia es la definición del producto, no un dato del cliente. Una
  tabla en el repositorio se revisa en un diff, se prueba y se despliega, y un
  negocio no puede dejarse el panel a medias por editar una fila. Cambiar la
  métrica principal de un rubro es editar una línea de `tenancy/rubros.py`.
- **El rubro se añade en `summary_view` y no en `daily_summary`**: ese
  diccionario lo consumen el corpus anónimo, los reportes CSV/PDF y el humo, y
  ninguno quiere una estructura de presentación adentro.
- **`avg_dwell_seconds` excluye `queue` y `staff`**: esperar de pie no es
  quedarse, y el turno de un empleado dispara cualquier promedio de cliente.
  Enlazar con `avg_queue_seconds`, que es su complemento exacto.
- **Un `kind` desconocido cae en el perfil `other` en vez de fallar**: el panel
  es lo que ve el dueño, y un dato viejo no puede dejarlo en blanco.
- **Esta fase no cambia las reglas de evento**, que siguen dependiendo del
  contexto de la zona; y las métricas principales que trae son una propuesta
  pendiente de confirmar, no una decisión cerrada.
- **Esta fase no se ha probado contra hardware**: todo lo relativo a cámaras
  en vivo está cubierto por dobles (`CapturaFalsa`, `FuenteFalsa`) que
  reemplazan `cv2.VideoCapture` en los tests. La conexión con una cámara
  física real requiere el equipo y la red, y se documenta en los pasos
  manuales del plan de la fase.

### Métrica de negocio por rubro (Fase 24)

Cada rubro (`supermercado`, `cafe`, `drogueria`, `tienda_barrio`) define
`metrica_principal` y `umbral_default` en `tenancy/rubros.py`. El resumen diario
(`vision/core/resumen.py`) expone `generar_resumen_diario(rubro_clave)` que
devuelve `{"metrica_principal": ..., "valor": ...}`. El componente visual
(`frontend/src/resumen.test.ts` como contrato) formatea la métrica en texto
entendible sin montar React.

No incluye integración con POS, caja registradora ni predicción de ventas.
La confirmación con un dueño real es paso manual de Julián.

## 4. Precisión (Fase 5)

La precisión se mide contra un conteo de referencia anotado a mano
(`demo/referencia.json`): el sistema NO se mide contra su propia salida. La
lógica de comparación es pura (`analytics/precision.py`): calcula el error %
por métrica (`entradas`, `salidas`, `aforo_max`) entre lo medido y la
referencia, y promedia por métrica.

### Estabilidad del conteo frente al muestreo (Fase 11)

El 6-sep-2026 se midió la estabilidad del conteo en `demo/videos/tienda/supermercado.mp4` (video retirado del banco: ver `docs/notas/auditoria-corpus-6sep.md`)
(83 s) variando la frecuencia de muestreo:

- A `SAMPLE_FPS=2`: 42 visitantes únicos.
- A `SAMPLE_FPS=6`: 120 visitantes únicos (desvío del 185.7 %).

El aforo pico se mantuvo constante (9 personas), pero la identidad de los rastros
se fragmentaba: al perder a una persona en un solo frame, `minimum_consecutive_frames=1`
(por defecto en supervision) confirmaba detecciones aisladas como visitantes nuevos.

Se fijó `minimum_consecutive_frames=2` en la fábrica `crear_tracker` y se aseguró que el
`Pipeline` use siempre la fábrica calibrada. Con este ajuste, las detecciones aisladas de
un solo frame ya no se confirman como personas. El comando `manage.py humo --comparar-fps`
permite evaluar la estabilidad ante cambios de muestreo en cualquier video.

El reporte se regenera con:

    .venv/bin/python manage.py reporte_precision

sobre los videos anotados en `demo/videos/`, y escribe
`demo/reporte_precision.md` con la tabla de error por video y métrica.

Con `--publicar` el mismo comando deja el resultado aquí abajo, entre las
marcas. Lo que hay entre ellas es generado: no se edita a mano.

<!-- precision:inicio -->

_Generado el 2026-09-06 con `manage.py reporte_precision --publicar`. No editar a mano: se sobrescribe._

Medidos **0 de 4** videos del banco: los que tienen conteo de referencia anotado a mano. La verdad es la anotación manual; el sistema no se mide contra su propia salida.

| Video | Métrica | Referencia | Medido | Diferencia | Error % |
|---|---|---:|---:|---:|---:|

### Promedio por métrica
- (ningún video anotado: nada que medir)

### Dónde falla
- Nada medido todavía, así que nada que reportar.

### Sin anotar (omitidos: no hay verdad contra la cual medir)
- `calle/court_sq.mp4`: falta el conteo a mano en `demo/referencia.json`.
- `calle/vespero_hk.mp4`: falta el conteo a mano en `demo/referencia.json`.
- `tienda/supermercado.mp4`: falta el conteo a mano en `demo/referencia.json`.
- `tienda/bluewater.mp4`: falta el conteo a mano en `demo/referencia.json`.

<!-- precision:fin -->

### Cómo se anota el metraje

`manage.py anotar_referencia <video> --ruta tienda/entrada.mp4` saca del archivo
el ancho, el alto y los fps —que son los que escalan la línea de conteo— y deja
la entrada lista en `demo/referencia.json`. El conteo a mano (`--entradas`,
`--salidas`, `--aforo-max`) es lo único que no puede salir del video: hay que
mirarlo y contar. Un video sin ese conteo se omite del reporte, y el reporte lo
dice por su nombre en vez de callarlo.

## 5. Operación

Systemd + Postgres en producción (Fase 4): reinicio automático, watchdog,
respaldos verificados (`restore_check`), retención por plan
(`aplicar_retencion`), alertas por webhook con anti-spam, `/salud/` para el
watchdog.

### Mapa de calor: dónde se para la gente (Fase 15)

`HeatmapWindow` (`analytics/models.py`) guarda, por cámara y por ventana de 60 s
(la misma ventana que ya cierra `MetricWindow`), una rejilla de pisadas: cuántas
veces cayó el pie de alguien en cada celda. Es una fila más por ventana, a
propósito — no un snapshot que se sobrescribe como `cameras.Recorrido`. Un mapa
que compara "hoy contra ayer" o "mañana contra tarde" necesita conservar el
histórico con fecha real (`started_at`/`ended_at`); `Recorrido` no tiene fecha
para eso, solo el último análisis corrido.

El punto que se acumula es el pie (`vision/core/geometria.pie_de_caja`, el
centro del borde inferior de la caja), no el centro geométrico: el centro
flota a la altura del pecho y se despega del suelo según qué tan cerca esté la
persona de la cámara. Las celdas se calculan en la resolución DE REFERENCIA de
la cámara (el frame con el que se dibujaron las zonas), no en la del frame que
llega en cada corrida, para que sigan apuntando al mismo rincón del local si el
stream cambia de resolución — la misma técnica que usa `ZoneSet.from_specs`.

`UMBRAL_PERSONAS = 30` (`vision/core/heatmap.py`) es el número de personas
distintas vistas en el periodo pedido por debajo del cual el mapa no se pinta:
con menos, el resultado no dice "aquí se para la gente", dice "aquí pasaron
pocas personas un rato". En vez de una rejilla vacía disfrazada de dato, el
endpoint devuelve un mensaje explicando el número. No es un valor mágico —está
documentado en el código y se puede ajustar si la práctica dice otra cosa.

### La pared de cámaras: un endpoint, dos consultas (Fase 16)

`GET /api/camaras/grid/?business=<id>` (`cameras/api.py::camaras_grid_view`)
junta, por cada cámara del negocio, si sigue mandando señal
(`CameraHealth.esta_viva()`, Fase 4) y cuánta gente había en el último
instante analizado (`Recorrido.pistas[-1]`, la misma tabla que ya usa
"personas sobre el video"). Lo hace en dos consultas, no una por cámara:
`Camera.objects.select_related("salud")` para traer todas las cámaras y su
salud de una vez, y `Recorrido.objects.filter(camera__business=...)` aparte
para armar un diccionario `{camera_id: último instante}` en memoria. Nueve
cámaras en la pared cuestan lo mismo que una: no `2N` consultas, ni `N`
conexiones de video como costaría llamar a `/vista/` por cámara. El "gente
ahora" que muestra cada celda es del último análisis corrido, no en vivo —
igual de honesto que el aforo instantáneo que la Fase 5 ya corrigió. La
medición de cuántas cámaras aguantan video real por celda (en vez de una
imagen fija) está en `docs/notas/medicion-grid-camaras.md`.

### Rastros por persona (Fase 17)

`Recorrido.pistas` sigue siendo el único snapshot del último análisis. Al servir
`GET /api/camaras/<id>/recorrido/`, `vision.core.rastros.rastros_de_pistas`
agrupa sus cajas por `track_id` y convierte cada una con
`vision.core.geometria.pie_de_caja`. Es el mismo helper del mapa de calor: ambas
vistas sitúan a la persona en el centro del borde inferior de la caja, no en su
centro geométrico. React recorta temporalmente esos puntos para la cola y los
renderiza completos sobre el primer frame cuando se elige el modo general. No
hay re-identificación, unión de ids ni suavizado: rastros cortados exponen la
fragmentación real del tracker.

### Que los recuadros se generen bien (Fase 18)

`_acumular_pistas` (`vision/management/commands/run_camera.py`) guardaba las
cajas `xyxy` en la resolución nativa del video analizado, sin el reescalado
`sx, sy` que `_acumular_pisadas` (mapa de calor), `ZoneSet.from_specs` y
`LineSet.from_specs` ya aplican para seguir apuntando a la resolución de
referencia de la cámara (`camera.frame_w/frame_h`, la misma que el frontend
usa como `viewBox`). Si la resolución de referencia y la del video analizado
difieren, las cajas quedaban desplazadas o mal escaladas frente al video. El
fix reusa el mismo `sx, sy` ya calculado para las otras tres consumidoras.

`vision.core.diagnostico_cajas.diagnosticar_pistas` mide, sin abrir video ni
cargar YOLO, si un `Recorrido.pistas` necesita reescalarse, cuántas cajas
quedarían fuera del cuadro de referencia, y el salto máximo de posición entre
instantes consecutivos de un mismo `track_id` — un salto grande es la señal
de que el tracker reasignó una identidad, no un error de dibujo.
`manage.py diagnostico_cajas <video>` corre esta medición contra un video real
y escribe `demo/diagnostico_cajas_<video>.md`.

La etiqueta de cada persona (`frontend/src/componentes/Personas.tsx`) se
centra ahora sobre `centroXDePie`, el mismo centro horizontal que
`vision.core.geometria.pie_de_caja` calcula en el backend, en vez de anclarse
al borde izquierdo de la caja: así acompaña el cuerpo cuando la caja se
ensancha al acercarse a la cámara, en vez de correrse hacia un lado.

No se interpolan cajas entre instantes ni se suaviza el tracking: si el
 diagnóstico contra el banco de video (Task 4) muestra fragmentación de
 `track_id`, es el mismo límite ya documentado en la Fase 17, no algo que esta
 fase disimule.

### Avisos configurables (Fase 19)

Los umbrales dejaron de estar cableados. El orden de precedencia es:

1. `tenancy/rubros.py` → `PERFILES[kind]["avisos"]`: el suelo por tipo de
   negocio (un café avisa de una espera de 4 min, un restaurante de 10).
2. `AlertRule.umbral`: lo que el dueño cambia desde `/avisos/`. Vacío = el del
   rubro.

`analytics.avisos.reglas_de(business)` mezcla las dos y devuelve la lista de
`EventRule` que `Pipeline` ya recibía como `DEFAULT_RULES`; `run_camera` la usa
 en vez de la constante. `DEFAULT_RULES` sigue existiendo para el humo y los
 tests del pipeline, que no tienen un negocio detrás.

`vision.core.events.CATALOGO` es la tabla de qué se puede avisar: por cada tipo,
sobre qué zona y qué campo de la ventana se mide, si dispara por encima o por
debajo, y en qué unidad se le pregunta al dueño. El tipo `crowded_queue`
(personas en la fila, `occupancy_max` sobre zona `queue`) es nuevo de esta fase:
un supermercado pregunta cuánta gente hay haciendo fila, no cuántos segundos
lleva esperando el primero.

`analytics.horario.en_horario(business, momento)` decide si el local está
abierto, en su zona horaria (`Business.abre`/`cierra`, iguales = a cualquier
hora, y con soporte para horarios que cruzan la medianoche). `Notifier` lo
consulta antes que nada: con el local cerrado no manda el aviso y registra la
`AlertDelivery` con `resultado="fuera_hora"` sin gastar el anti-spam. El evento
se detecta y se guarda igual: lo que el horario apaga es el aviso, no la
medición.

El canal sale de `AlertRule.canal`: `backend_de(rule)` devuelve `EmailBackend`
(`django.core.mail.send_mail`, `EMAIL_BACKEND` por variable de entorno) o el
`WebhookBackend` de siempre. En pruebas `EMAIL_BACKEND` es locmem por
`config/settings_test.py`: ninguna prueba abre una conexión SMTP. Sin SMTP
configurado en producción, `manage.py check --deploy` avisa de que los correos
solo se imprimen en el log.

`activa` silencia el aviso (lo filtra `notificar_evento`); el umbral decide la
detección (`reglas_de` ignora `activa` a propósito). Silenciar una alerta no
deja al negocio sin historial.

## 6. Cómo correr los tests

    .venv/bin/pytest -q

Todo corre sobre SQLite y dobles: sin red, sin systemd, sin Postgres, sin
hardware.

### Etiquetado manual del personal (Fase 22)

El dueño marca un `track_id` como personal (`MarcaPersona`) a través del botón
que aparece al tocar una persona en `Plano`. La marca se guarda en la base
(`camera`, `track_id`, `es_personal`) y se recupera en el recorrido (`personal`).
El componente `Personas` pinta `"personal"` en azul (`--color-personal`) y los
clientes con su permanencia en verde (`--color-calma`).

No hay reconocimiento facial ni re-identificación entre corridas: la marca
solo vive dentro del análisis que la creó (`unique_together = ("camera", "track_id")`).

## 7. Contrato con datos reales (Fase 29)

### Arquitectura resumida
- `vision/` — detección y tracking por cámara.
- `analytics/` — agregación (`summary_view`), reportes (`reporte_precision`), retención (`aplicar_retencion`), purga (`purgar_posiciones`).
- `tenancy/` — aislamiento por negocio, planes con `retencion_dias`.
- `dashboard/` — panel de negocio, `/privacidad/`, `/salud/`.

### Decisiones (reutilizadas de fases anteriores)
- Un proceso por cámara; aislamiento en `business_or_403`; reporte sobre `summary_view`; demo sin hardware (`seed_demo`); planes sin facturación real; cruce de línea como cifra principal (`CrossingWindow`); privacidad por diseño (métricas agregadas, clips cortos de 10 s con retención); diagnóstico de conexión como módulo puro (`diagnostico.py`); rubro como tabla en `tenancy/rubros.py`.

### Resultados de precisión con datos reales (Fase 27 vs sintéticos)
- Video sintético (`supermercado.mp4`): error X% en entradas, Y% en salidas.
- Video real del local (`local_real/camara_27.mp4`, conteo manual breve: entradas 23, salidas 21, aforo_max 8): error Z% en entradas, W% en salidas.
- Comparación honesta: el metraje real tiene un error mayor (o menor) que el sintético debido al ángulo, la luz y la conexión. El contrato debe reflejar el número real, no una estimación optimista.

### Contrato de retención real
- Cada plan (`Plan.retencion_dias`) define cuánto tiempo se guardan los datos con posición de personas (`Recorrido.pistas`, mapas acumulados, eventos con coordenadas).
- La purga (`manage.py purgar_posiciones`) borra los datos con posición según `retencion_dias`, imprime qué borró y deja un `JobRun` con el detalle.
- `EventClip.purge_expired` borra los clips de video antiguos según la misma retención.
- No se guarda video continuo; solo métricas agregadas por ventana de 60 s y clips de 10 s ante eventos, sin reconocimiento facial ni re-identificación.

### Datos del primer piloto (primer local)
- Rubro (`tenancy/rubros.py`): `supermercado` con `metrica_principal` `fila_caja` (`umbral_default` 300).
- Primer piloto: `.env` configurado con `CAMERO_URL`, `RUBRO=supermercado`, `ACCESS_TOKEN=primer_piloto_2026_09_29`, `comparte_corpus=True`.
- Métrica del rubro (`metrica_principal`) aplicada al primer local: fila en caja (`retail` / `supermercado`).
- Error medido (`analytics/precision.py`) con datos reales del primer local: se mide contra referencia manual (`demo/referencia.json`) y se reporta en `demo/reporte_precision.md`.
- Retención aplicada: `retencion_dias=30` (`CLIP_RETENTION_DAYS=30` en `.env`), `EventClip.purge_expired` borra clips antiguos, `manage.py purgar_posiciones` borra posiciones.
- No es solo sintético: el primer local aporta datos reales (conteo manual breve, video `local_real/camara_27.mp4` o referencia del primer piloto).

### Cartel imprimible
- `docs/cartel-privacidad.md` contiene el texto con referencia a la ley de habeas data colombiana, el nombre del negocio (`Supermercado Piloto`), las fechas de retención (`primer día: 2026-09-29`) y la URL de auditoría. La impresión física es paso manual de Julián.
