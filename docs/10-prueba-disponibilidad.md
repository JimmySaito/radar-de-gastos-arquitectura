# 10. Prueba de disponibilidad: caída controlada en AWS

Prueba realizada el 20 de noviembre de 2026 sobre el despliegue en AWS Academy Learner Lab (`us-east-1`). Los
datos crudos están en el repositorio del prototipo: `docs/results/aws-lab-caida.json` (fases, huella de datos y
observaciones) y `docs/results/aws-lab-caida-sondas.jsonl` (cada medición: fase, hora, ruta, código y latencia).

## 10.1 Objetivo e hipótesis

Verificar el escenario de **disponibilidad** y el de **confiabilidad** ante la pérdida del entorno de ejecución:

- **H1.** Si el entorno deja de estar disponible, ningún dato se pierde ni se duplica.
- **H2.** Al restablecerse el entorno, el servicio vuelve sin intervención manual ni redespliegue.
- **H3.** La caída se detecta con las alarmas definidas.
- **H4.** Existe un entorno de respaldo que permite continuar la operación (o la demostración).

## 10.2 Método

| Fase | Acción | Medición |
|---|---|---|
| Línea base | Ambiente activo, usuario con sesión iniciada | Sondas HTTP sin credenciales; huella de datos (ítems, hechos, usuarios); cifras del dashboard |
| Caída | **End Lab**: el laboratorio termina la sesión | Las mismas sondas; pruebas manuales con sesión abierta e incógnito; respaldo local |
| Recuperación | **Start Lab** y credenciales nuevas | Huella de datos, colas, sondas, logs de acceso de API Gateway, métricas y alarmas de CloudWatch |

Las sondas cubren cinco rutas públicas: `/v1/health` (Lambda sin base de datos), `/` y `/config.json` (dashboard
servido por la API), `/v1/summary` sin token (debe responder 401 desde el autorizador JWT) y la pantalla de inicio
de sesión de Cognito.

## 10.3 Resultados

**Línea de tiempo** (logs de acceso de API Gateway, UTC):

| Hora | Evento |
|---|---|
| 00:04:48 | Última consulta de datos correcta (`GET /v1/summary` → 200) |
| ≈ 00:05 | *End Lab* |
| 00:06:17 | Primera consulta de datos fallida (500) |
| 00:07:13 | La alarma `api-errors` (errores de la Lambda) pasa a **ALARM** y publica en SNS |
| 00:12:06 | Primera consulta correcta después de *Start Lab* (200, 411 ms) |
| 00:13:13 | La alarma vuelve a **OK** |

**Disponibilidad por componente durante la caída:**

| Componente | Resultado |
|---|---|
| Dashboard (archivos y `config.json`) | Disponible (200; mediana de 125 ms frente a 131 ms en la línea base) |
| Cognito (inicio de sesión) | Disponible: se inició sesión desde una ventana de incógnito |
| Autorizador JWT | Disponible (401 sin token) |
| `/v1/health` | 200 durante toda la caída (ver hallazgo 1) |
| Consultas de datos | **No disponibles**: 500 |
| Logs de la función | No se escribieron entre 00:05 y 00:12 |
| Respaldo local | Disponible, con los datos locales del usuario |

**Causa**, registrada en el campo `integrationErr` del log de acceso:
`AccessDeniedException` al ejecutar `dynamodb:Query` con el rol `LabRole`, por una denegación explícita en una
*service control policy* de AWS Organizations que el laboratorio aplica al terminar la sesión. La misma política
explica la ausencia de logs de la función: tampoco pudo escribir en CloudWatch Logs. Los logs de acceso de API
Gateway, que escribe el propio servicio y no la función, sí se conservaron y fueron la evidencia principal.

**Integridad de los datos** (antes → después): 6.313 → 6.313 ítems; 2.807 → 2.807 hechos de ejemplo; 1 → 1
usuario; cola de trabajo y DLQ en 0. El dashboard mostró las mismas cifras (6.275,08 USD en 30 días).

## 10.4 Evaluación de las hipótesis

| Hipótesis | Resultado | Evidencia |
|---|---|---|
| H1. Sin pérdida ni duplicación | **Confirmada** | Huella idéntica antes y después |
| H2. Recuperación automática | **Confirmada** | Primera consulta tras *Start Lab* correcta, sin redesplegar |
| H3. Detección por alarmas | **Parcial** | `api-errors` se disparó en ≈ 1 min; `api-5xx` no; el correo no llegó porque la suscripción SNS estaba sin confirmar |
| H4. Respaldo operativo | **Confirmada** | El servidor local funcionó durante toda la caída |

La caída duró unos siete minutos y no coincidió con la recolección horaria, por lo que **esta prueba no ejercitó**
los reintentos de SQS ni la DLQ; esos mecanismos están cubiertos por las pruebas de integración y quedan como
siguiente experimento en la nube.

## 10.5 Hallazgos y acciones

| # | Hallazgo | Riesgo | Acción tomada |
|---|---|---|---|
| 1 | `/v1/health` respondió 200 con la base de datos inaccesible | Un monitor externo habría reportado el servicio sano | Nuevo `GET /v1/ready`, que consulta DynamoDB y responde 503 si falla; `/v1/health` queda como sonda de vivacidad |
| 2 | El usuario veía "Internal Server Error" | Mensaje inútil y sin indicación de reintento | Los errores de AWS que indican indisponibilidad (permisos, limitación, caída o conexión) se responden con **503**, un mensaje claro y `Retry-After`, sin exponer detalles internos |
| 3 | La pantalla marcaba "7 días" con datos de 30, sin aviso | Decisiones sobre datos que no corresponden al rango | El dashboard conserva los últimos datos atenuados, vuelve a marcar el rango que realmente muestra e indica la hora de la última consulta |
| 4 | La alarma de tasa de 5xx no se disparó | Una caída con poco tráfico pasa inadvertida | La alarma ahora exige 2 de 5 minutos (antes 3 de 3) y avisa también la recuperación. Como los errores de AWS ya no terminan en excepción de la Lambda, esta alarma pasa a ser la señal principal |
| 5 | Sin logs de la función durante la caída | Pérdida de observabilidad justo en el incidente | Documentado en el runbook: revisar primero los logs de acceso de API Gateway. Recomendado para producción: registros que no dependan del rol de la aplicación |
| 6 | Suscripción SNS sin confirmar | Las alarmas no llegan a nadie | Paso explícito en la guía de despliegue |

Las acciones 1 a 4 están implementadas en el prototipo, con pruebas automatizadas, y se verificaron en AWS
repitiendo la prueba (sección 10.6).

## 10.6 Repetición tras las correcciones

Se redesplegó el prototipo (2 recursos creados, 5 modificados, 1 reemplazado: la capa de dependencias) y se repitió
la caída con una sonda continua sobre `/v1/ready` y `/v1/health` cada 10 s (`docs/results/aws-lab-caida2-sonda.jsonl`,
134 mediciones).

| Corrección | Resultado en AWS |
|---|---|
| 1. `/v1/ready` | 503 durante toda la caída y `/v1/health` 200 en las 67 mediciones: la sonda distingue vivacidad de disponibilidad. Último 503 a las 00:38:55, primer 200 a las 00:39:06 (recuperación fechada con 11 s de precisión) |
| 2. Respuesta 503 | El dashboard mostró *"El servicio de datos no está disponible en este momento. Intenta de nuevo en unos minutos."* |
| 3. Datos desactualizados | No verificable en AWS: la pestaña abierta conservaba el código anterior al redespliegue (hallazgo 7). Verificado en local con el código nuevo: aviso con la hora de la última consulta, rango correcto y datos atenuados |
| 4. Alarma de 5xx | **ALARM** a las 00:35:12 (errores del 50 % en 00:33 y 00:34) y **OK** a las 00:43:12, unos 4 minutos después de la recuperación, por la ventana de 5 minutos; ambos avisos llegaron por correo con la suscripción ya confirmada |

La repetición destapó dos hallazgos más:

| # | Hallazgo | Acción |
|---|---|---|
| 7 | Una pestaña abierta antes del despliegue sigue ejecutando el código anterior hasta que se recarga | Documentado; la mejora natural es versionar los archivos estáticos para invalidarlos en cada despliegue |
| 8 | En AWS las barras de "Gasto por persona" y los colores de avatares y categorías no se veían: la CSP (`style-src 'self'`) bloquea los atributos de estilo en línea, y en local no había CSP | Los estilos dinámicos se aplican desde JavaScript (permitido por la CSP) y los fijos pasaron a clases; el servidor local envía ahora la misma CSP que AWS, y una prueba automatizada impide reintroducir estilos o manejadores en línea. Verificado en AWS tras redesplegar: barras y colores visibles |

El hallazgo 8 no estaba relacionado con la caída, pero lo reveló la misma sesión de uso real. Muestra el valor de que
el entorno local reproduzca las políticas del de producción: la diferencia entre ambos ocultaba el defecto.

## 10.7 Conclusión

La arquitectura conservó la **integridad** y se **recuperó sola**, que eran las propiedades críticas para un
sistema financiero. La prueba sí expuso debilidades de **observabilidad y experiencia de usuario** que las pruebas
locales no podían revelar: un chequeo de salud que no mira las dependencias, un error sin significado para el
usuario y una alarma calibrada para tráfico alto. Es un ejemplo de por qué el atributo de soportabilidad necesita
evidencia en el entorno real y no solo diseño.
