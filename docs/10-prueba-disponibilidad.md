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

Las acciones 1 a 4 están implementadas en el prototipo, con pruebas automatizadas (141 pruebas en total). Su
comportamiento en AWS se verifica repitiendo esta prueba tras redesplegar.

## 10.6 Conclusión

La arquitectura conservó la **integridad** y se **recuperó sola**, que eran las propiedades críticas para un
sistema financiero. La prueba sí expuso debilidades de **observabilidad y experiencia de usuario** que las pruebas
locales no podían revelar: un chequeo de salud que no mira las dependencias, un error sin significado para el
usuario y una alarma calibrada para tráfico alto. Es un ejemplo de por qué el atributo de soportabilidad necesita
evidencia en el entorno real y no solo diseño.
