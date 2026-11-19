---
title: "UsageHub: arquitectura serverless con un ledger idempotente para el gobierno centralizado del consumo de servicios de IA y nube"
author:
  - "[Nombre del autor 1] — [Programa / Universidad]"
  - "[Nombre del autor 2] — [Programa / Universidad]"
date: "Noviembre de 2026"
lang: es
---

# Resumen

Las organizaciones consumen hoy, en paralelo, modelos de lenguaje de varios proveedores (Anthropic, OpenAI, Google)
y servicios de nube (AWS). Cada proveedor reporta el consumo con unidades, identidades y latencias distintas, lo que
impide responder con oportunidad cuánto se gasta, en qué y quién lo consume. Este trabajo presenta **UsageHub**, una
plataforma FinOps que centraliza esos datos en un modelo canónico, atribuye cada costo a una persona y a un equipo, y
habilita presupuestos con alertas. La contribución técnica central es un **ledger idempotente basado en deltas** sobre
Amazon DynamoDB: combina claves naturales deterministas, transacciones atómicas y control de concurrencia optimista
para garantizar un efecto *exactamente-una-vez* sobre los agregados, aunque la mensajería entregue *al-menos-una-vez*
y los proveedores revisen sus cifras durante horas. La solución se diseñó con arquitectura hexagonal, CQRS y un
estilo serverless orientado a eventos en AWS, se documentó con el modelo C4 y ADR, y se alineó con TOGAF, COBIT 2019,
ISO/IEC 38500 y el FinOps Framework. La evaluación combina 129 pruebas automatizadas (96,4 % de cobertura de ramas),
pruebas basadas en propiedades y pruebas de estrés con inyección de 15 % de mensajes duplicados. En todos los
escenarios medidos el costo agregado coincidió exactamente con el costo real, y la arquitectura cumplió por
construcción los once atributos de calidad exigidos.

**Palabras clave:** FinOps, gobierno de TI, arquitectura serverless, idempotencia, CQRS, arquitectura hexagonal, AWS, IA generativa.

# Abstract

Organizations increasingly consume large language models from several vendors alongside cloud services, each
reporting usage with different units, identities and delays. We present UsageHub, a FinOps platform that consolidates
this data into a canonical model, attributes cost to people and teams, and enforces budgets. Its core is an idempotent,
delta-based ledger on Amazon DynamoDB that guarantees exactly-once effects on aggregates despite at-least-once
delivery and provider-side revisions, using deterministic natural keys, atomic transactions and optimistic concurrency
control. The prototype follows hexagonal architecture, CQRS and an event-driven serverless style on AWS, and is aligned
with TOGAF, COBIT 2019, ISO/IEC 38500 and the FinOps Framework. Property-based and stress tests with 15 % injected
duplicates show zero aggregation error.

# 1. Introducción

La adopción de IA generativa en las empresas ha pasado de pilotos aislados a un consumo transversal y multiproveedor.
Un mismo departamento de ingeniería puede usar Claude para programar, un modelo de OpenAI en un producto y Gemini en
analítica, todo sobre una plataforma de nube con su propia facturación. Desde la perspectiva de **gobierno de TI**,
esta fragmentación produce tres problemas: (i) no existe una visión consolidada y oportuna del gasto; (ii) el costo
queda asociado a identidades técnicas (API keys, proyectos, cuentas) y no a responsables de negocio, lo que impide el
*showback* y el *chargeback*; y (iii) el control es reactivo, porque los excesos se descubren con la factura.

La disciplina **FinOps** propone un modelo operativo de responsabilidad compartida sobre el costo variable de la
tecnología, organizado en las fases *Inform*, *Optimize* y *Operate* [7], [8]. Su primera capacidad es entender el uso
y el costo: ingerir, normalizar y asignar los datos. Esa capacidad plantea un desafío de **arquitectura de software**
poco tratado en la literatura de FinOps: los datos de consumo llegan con retraso (4 a 24 h en el caso de Anthropic
[20]), pueden revisarse después de publicados, y se procesan sobre infraestructura de mensajería que, por diseño,
entrega mensajes al menos una vez. Si se suman ingenuamente, el gasto reportado se infla. En un sistema financiero,
un error de agregación no es un detalle de implementación: compromete la confianza en todo el instrumento de gobierno.

Este artículo aborda la pregunta: **¿cómo diseñar una plataforma centralizada, extensible y económica de observabilidad
del consumo de IA y nube que garantice exactitud de los agregados bajo entrega duplicada, revisiones de los proveedores
y escritura concurrente?** Las contribuciones son:

1. Una arquitectura de referencia serverless en AWS para FinOps multiproveedor, documentada con el modelo C4, diez
   decisiones de arquitectura (ADR) y escenarios de calidad para once atributos.
2. Un **algoritmo de ledger idempotente basado en deltas** con control de concurrencia optimista, separado como lógica
   de dominio pura y verificado con pruebas basadas en propiedades.
3. La alineación explícita de la solución con marcos de arquitectura empresarial (TOGAF, ArchiMate) y de gobierno
   (COBIT 2019, ISO/IEC 38500, FinOps Framework), incluidos KPIs y una matriz RACI.
4. Un prototipo de código abierto con infraestructura como código, CI y un protocolo de pruebas de estrés que verifica
   la **consistencia** y no solo el rendimiento.

El resto del artículo se organiza así: la sección 2 revisa la literatura; la 3 describe la metodología; la 4, la
implementación; la 5 presenta y discute los resultados; y la 6 concluye y propone trabajo futuro.

# 2. Revisión de literatura

## 2.1 Gobierno de TI y FinOps

COBIT 2019 [5] define objetivos de gobierno y gestión; el objetivo **APO06 (Gestionar el presupuesto y los costos)**
exige asignar los costos de TI a los consumidores y controlar el gasto frente a presupuestos. ISO/IEC 38500 [6]
establece seis principios para la dirección de TI (responsabilidad, estrategia, adquisición, desempeño, conformidad y
comportamiento humano), entre ellos que cada uso de TI tenga un responsable identificable. El FinOps Framework [7] y
Storment y Fuller [8] trasladan esos principios al costo variable de la nube y proponen un modelo de madurez
(*crawl*, *walk*, *run*) donde la asignación de costos es requisito de las fases posteriores. Estos trabajos definen
**qué** debe lograrse (visibilidad, asignación, presupuestos), pero no **cómo** construir una plataforma confiable
cuando las fuentes son heterogéneas y revisables. Esa es la brecha que aborda este trabajo.

## 2.2 Arquitectura empresarial

TOGAF [3] organiza el desarrollo de arquitectura en el ciclo ADM (visión, negocio, sistemas de información,
tecnología, oportunidades, migración, gobierno de la implementación y gestión del cambio). ArchiMate [4] aporta una
notación por capas (negocio, aplicación, tecnología) que relaciona capacidades y procesos con componentes y nodos.
En este trabajo se usan para trazar el problema de negocio (fragmentación del gasto) hasta componentes concretos
y para planificar arquitecturas de transición.

## 2.3 Arquitectura de software y atributos de calidad

Bass, Clements y Kazman [1] formalizan los **escenarios de atributos de calidad** (fuente, estímulo, artefacto,
entorno, respuesta y medida) y catalogan **tácticas** para cada atributo. El método ATAM [2] usa árboles de utilidad
para priorizar escenarios e identifica puntos de sensibilidad y *trade-offs*. El modelo C4 [16] propone cuatro niveles
de abstracción (contexto, contenedores, componentes y código), y los ADR [17] registran decisiones con su contexto y
consecuencias. La **arquitectura hexagonal** [9] aísla el dominio mediante puertos y adaptadores. **CQRS** [15] separa
los modelos de escritura y de lectura para optimizarlos de forma independiente. El **modelo de datos canónico** de
Hohpe y Woolf [10] reduce de N×M a N+M las transformaciones necesarias para integrar sistemas heterogéneos.

## 2.4 Computación serverless

Jonas et al. [14] caracterizan la computación serverless por la abstracción de servidores, el escalado automático a
cero y el pago por uso, e identifican como desafíos el estado, la coordinación y la latencia de arranque. El AWS
Well-Architected Framework y su *Serverless Lens* [18] recomiendan colas como amortiguadores (*queue-based load
leveling*), colas de mensajes fallidos (DLQ) e idempotencia de los consumidores, ya que servicios como SQS estándar
garantizan entrega al menos una vez.

## 2.5 Idempotencia, consistencia y concurrencia

Helland [12] sostiene que en sistemas distribuidos los mensajes se reintentan y, por tanto, toda operación debe
diseñarse para ser idempotente. Kleppmann [11] analiza que la semántica *exactamente-una-vez* no se logra en el
transporte sino en el **efecto**, combinando entrega al-menos-una-vez con procesamiento idempotente. Bailis y Ghodsi
[25] discuten las garantías prácticas de la consistencia eventual. Kung y Robinson [13] introdujeron el **control de
concurrencia optimista** (OCC): las transacciones proceden sin bloqueos y validan conflictos al confirmar, lo que
resulta eficiente cuando los conflictos son poco frecuentes. Brooker [22] muestra que el *backoff* exponencial con
*jitter* reduce la contención en reintentos concurrentes. DeBrie [19] documenta el diseño de tabla única en DynamoDB a
partir de patrones de acceso.

## 2.6 Síntesis y brecha

La literatura de gobierno define los objetivos (asignación, presupuestos) y la de sistemas distribuidos aporta los
mecanismos (idempotencia, OCC, colas). Sin embargo, no se encontró una propuesta que **integre** ambos mundos para el
caso específico del consumo multiproveedor de IA, donde coinciden tres fuentes de duplicación: la mensajería, la
relectura periódica y las revisiones del proveedor. Este trabajo propone y evalúa esa integración.

# 3. Metodología

## 3.1 Enfoque

Se siguió un enfoque de **investigación en ciencia del diseño** (*design science*): identificación del problema,
definición de objetivos, diseño y construcción de un artefacto (el prototipo), demostración y evaluación. El diseño
de la arquitectura fue **guiado por atributos de calidad** [1]:

1. **Contexto y *drivers*:** interesados, preocupaciones y cinco *business drivers* medibles (p. ej. conocer el gasto
   consolidado en menos de un minuto o atribuir al menos el 95 % del costo).
2. **Árbol de utilidad y escenarios:** once escenarios de calidad priorizados por importancia y dificultad (ATAM [2]).
3. **Selección de tácticas y patrones** por escenario, registrada en ADR.
4. **Arquitectura empresarial:** recorrido del ADM de TOGAF, principios de arquitectura, mapa de capacidades FinOps y
   *gap analysis*.
5. **Gobierno:** mapeo a objetivos de COBIT 2019, principios de ISO/IEC 38500, KPIs y RACI.
6. **Construcción iterativa** con desarrollo guiado por pruebas en el núcleo de dominio.
7. **Evaluación:** pruebas automatizadas, pruebas de propiedades, pruebas de estrés con verificación de consistencia y
   análisis de *trade-offs*.

## 3.2 Tecnologías

| Ámbito | Tecnología | Justificación |
|---|---|---|
| Lenguaje | Python 3.13, Pydantic v2, `mypy --strict` | SDKs oficiales de los proveedores; validación en los bordes |
| Cómputo | AWS Lambda (arm64/Graviton) | Escala a cero; mejor precio/rendimiento |
| Mensajería | Amazon SQS estándar + DLQ | Nivelación de carga, aislamiento de fallas |
| Datos | Amazon DynamoDB *on-demand* | Transacciones ACID, OCC por condiciones, escalado automático |
| API e identidad | API Gateway HTTP, Amazon Cognito | Autorizador JWT nativo, OAuth 2.0 (PKCE y *client credentials*) |
| Planificación | EventBridge Scheduler | Recolección horaria y evaluación diaria de presupuestos |
| Frontend | SPA estática, Chart.js, CloudFront + S3 | Sin servidores; cabeceras de seguridad en el borde |
| Observabilidad | AWS Lambda Powertools, CloudWatch, X-Ray | Logs estructurados, métricas EMF, trazas |
| IaC y CI | Terraform (módulos), GitHub Actions (OIDC) | Reproducibilidad y gobierno de cambios |
| Pruebas | pytest, Hypothesis [24], moto, respx, k6 | Pirámide completa sin depender de la nube |

## 3.3 Patrones de diseño aplicados

Arquitectura hexagonal (puertos y adaptadores), modelo de datos canónico, Adapter + Strategy + Registry para
conectores, CQRS con agregados precalculados, *Repository*, *Composition Root*, consumidores en competencia
(*competing consumers*), *queue-based load leveling*, DLQ, respuesta de lote parcial (*bulkhead* por mensaje),
control de concurrencia optimista, reintento con *backoff* exponencial y *full jitter*, y *singleton* perezoso por
contenedor de ejecución.

# 4. Implementación

## 4.1 Visión general

La Figura 1 (vista de contenedores C4, en `docs/03-vistas-c4.md`) muestra dos rutas de entrada que confluyen en una
cola SQS. En la ruta **pull**, EventBridge invoca cada hora una función que publica una tarea por conector
habilitado y el colector consulta la API del proveedor. En la ruta **push**, cualquier sistema envía registros a
`POST /v1/usage/records` autenticado con OAuth 2.0. El colector normaliza y escribe en el ledger. La API sirve al
dashboard desde agregados precalculados, y una función diaria evalúa presupuestos y publica alertas en SNS.

## 4.2 Modelo canónico y conectores

Cada conector traduce la respuesta de su proveedor a `UsageRecord`, un hecho diario inmutable con identidad natural
(tenant, proveedor, servicio, principal, fecha) y métricas aditivas (tokens de entrada, salida y caché, solicitudes y
costo en `Decimal`). Algunas particularidades que el diseño absorbe:

- **Anthropic:** se usa la *Usage and Cost Analytics API* mediante el SDK oficial
  (`client.beta.organization.analytics.usage/cost`), agrupando por `actor` y `model`. El costo llega en centavos y se
  convierte a dólares. Las ventanas se dividen en tramos de 31 días, el máximo por solicitud [20].
- **OpenAI:** la API de uso agrupa tokens por usuario o API key, pero la de costos solo por proyecto [21]. El tipado del
  modelo canónico obliga a hacer explícita esa asimetría (ADR-0006).
- **AWS:** Cost Explorer agrupado por servicio y *cost allocation tag* `owner`, leído mediante `AssumeRole` con
  `ExternalId` en la cuenta *payer*. El consumo de Claude vía Amazon Bedrock aparece como servicio de AWS.
- **Google:** consulta parametrizada a la exportación de facturación en BigQuery, con validación del nombre de tabla
  para prevenir inyección SQL.

Un proveedor nuevo se agrega con un módulo y una línea de registro (`@register(Provider.X)`). El registro carga los
módulos de forma diferida para no penalizar el arranque en frío.

## 4.3 El ledger idempotente basado en deltas

El núcleo es la función pura `compute_deltas(previo, nuevo, atribución)`, que devuelve el ajuste por celda agregada
(fecha × proveedor × {persona, equipo, servicio}):

- **Primera escritura:** +nuevo en tres celdas.
- **Reescritura idéntica:** conjunto vacío. Se detecta antes con `content_hash` y no se escribe nada.
- **Revisión:** +(nuevo − previo) en cada celda.
- **Reatribución:** −previo en las celdas antiguas y +nuevo en las nuevas. Las celdas coincidentes se fusionan, porque
  DynamoDB no permite operar dos veces sobre el mismo ítem en una transacción.

El adaptador de DynamoDB aplica el resultado de forma atómica:

```
repetir hasta 8 veces:
    previo ← GetItem(hecho, ConsistentRead)
    si sin_cambios(previo, nuevo): devolver UNCHANGED
    TransactWriteItems(
        Put(hecho, version = v+1, condición: version = v  |  attribute_not_exists),
        Update(celda_i, ADD Δ_i)  para cada celda)
    si éxito: devolver CREATED | REVISED
    si ConditionalCheckFailed o TransactionConflict: esperar U(0, base·2^intento)
lanzar ConcurrencyError  → el mensaje vuelve a SQS y, tras 5 intentos, a la DLQ
```

La condición sobre `version` implementa OCC [13]: si dos colectores leyeron la misma versión, solo uno confirma; el
otro relee, recalcula el delta respecto de la versión ganadora y reintenta. El hecho y sus agregados se actualizan
en la misma transacción, así que el modelo de lectura nunca diverge del ledger. Como el delta respecto de la misma
versión es cero, **reprocesar un mensaje es inocuo**, y eso hace seguros los reintentos de SQS, el *redrive* desde la
DLQ y los *backfills*.

## 4.4 Modelo de datos

Se usa una tabla única con claves compuestas. Los hechos se guardan en `T#{tenant}#F#{mes}` y los agregados en
`T#{tenant}#A#{dimensión}#{mes}`, con `SK = fecha#proveedor#valor`. Una consulta de 90 días lee como máximo cuatro
particiones por dimensión, sin importar el volumen de hechos. El particionamiento mensual acota el tamaño de las
colecciones y distribuye la escritura.

## 4.5 Seguridad y multi-tenancy

El autorizador JWT de API Gateway valida los tokens de Cognito antes de invocar a Lambda. El tenant se obtiene
**exclusivamente** de la claim inmutable `custom:tenant_id`, o de la configuración `client_id → tenant` en el caso de
clientes M2M. Un cuerpo que incluya `tenant_id` se rechaza, lo que mitiga la vulnerabilidad BOLA (OWASP API1:2023
[23]). Las llaves Admin de los proveedores, de solo lectura, se guardan en Secrets Manager con caché TTL de 5 min.
Cada función tiene un rol IAM propio con acciones explícitas. El frontend se sirve desde un *bucket* privado con OAC y
una política de seguridad de contenido (CSP) estricta.

## 4.6 Infraestructura, observabilidad y CI

Terraform compone cuatro módulos reutilizables: `lambda_function` (instanciado cuatro veces), `sqs_queue`,
`static_site` y `cost_reader_role`. Powertools emite métricas de negocio en formato EMF (`RecordsWritten`,
`RecordsUnchanged`, `LedgerRetry*`, `QueueToLedgerLatency`) sin llamadas síncronas. Un dashboard operativo y alarmas
de SLO (5xx > 1 %, p95 > 800 ms, DLQ > 0, edad de la cola > 15 min) completan la soportabilidad. El pipeline de CI
ejecuta formato, lint (incluido bandit), `mypy --strict`, pruebas con umbral de cobertura, `pip-audit`, `checkov` y
`terraform validate`. El despliegue usa credenciales temporales vía OIDC.

## 4.7 Dashboard

La SPA presenta KPIs (costo, tokens, solicitudes y equipo con más gasto), costo diario apilado por proveedor o equipo,
rankings de personas y modelos con desglose por proveedor, y el estado de los presupuestos con icono y texto (el color
no es la única señal). Los colores son fijos por proveedor y usan una paleta validada para daltonismo, con modo
oscuro y vista de tabla accesible.

La aplicación separa dos conjuntos de datos: **Datos reales** (el tenant del usuario) y **Ejemplo** (un tenant de
demostración de solo lectura). Desde la vista real, una pantalla de **Configuración** permite a los administradores
operar sin consola de AWS (ADR-0011):

- registrar conexiones con un formulario que se genera desde un catálogo declarativo de proveedores;
- *probar* las credenciales leyendo los últimos tres días sin escribir en el ledger;
- sincronizar bajo demanda y ver el estado del último sync de cada conexión;
- asignar a personas y equipos las identidades técnicas detectadas, con el porcentaje de gasto ya atribuido como KPI;
- definir presupuestos.

Las credenciales se custodian tras un puerto `SecretStore` (Secrets Manager en la nube, archivos fuera del
repositorio en local) y nunca se devuelven al navegador.

Finalmente, la aplicación distingue dos espacios (ADR-0013). En **Empresa** está el consumo descrito, más las
**licencias SaaS** con número de usuarios. En **Personal**, cada persona registra sus suscripciones, sean de IA o
no (streaming, música, software, almacenamiento), con monto, moneda, ciclo y fecha de cobro.

Un módulo de dominio puro calcula el calendario de cobros desde una fecha ancla, sin acumular desfases, y ajusta
al último día los meses más cortos. También calcula el equivalente mensual y un resumen agrupado por moneda: no
convierte divisas para no introducir tipos de cambio no verificados. Con eso el panel muestra próximos cobros,
calendario y proyección anual. Lo personal se indexa por el `sub` del token, así que ni otros miembros del tenant
pueden leerlo.

En el espacio personal se pueden crear **perfiles de personas** y asignar cada suscripción a una o varias
(ADR-0014). Lo compartido se reparte con un algoritmo que distribuye los centavos sobrantes para que las partes
sumen exactamente el cobro. La tarjeta "Gasto por persona" y el panel filtrado se derivan de la misma vista, lo
que garantiza que muestren cifras idénticas. Un hogar de ejemplo generado al vuelo, con fechas relativas a hoy,
permite explorar el panel sin datos propios.

# 5. Resultados y evaluación

## 5.1 Verificación funcional y estática

| Indicador | Resultado |
|---|---|
| Pruebas automatizadas | 129 (95 unitarias, 2 de propiedades, 15 de integración con AWS emulado, 17 de handlers) |
| Cobertura de ramas | 96,4 % (umbral: 80 %) |
| Tipado estático | `mypy --strict`: 0 errores en 38 módulos |
| Lint y seguridad estática | `ruff` (incluye reglas de bandit): 0 hallazgos |
| Tiempo de la suite | ≈ 11 s, sin cuenta de AWS |

La prueba de propiedades genera secuencias arbitrarias de hasta 12 revisiones con costos, tokens y atribuciones
aleatorias, cada una entregada entre una y tres veces. Verifica que, en las tres dimensiones, el agregado sea igual a
la última versión del hecho y que solo quede la última atribución. Las pruebas de integración inyectan
`TransactionConflict` y `ConditionalCheckFailed` y simulan dos *workers* que leen la misma versión. En todos los casos
el resultado converge al valor correcto.

## 5.2 Pruebas de estrés con verificación de consistencia

Se ejecutaron tres perfiles de carga abierta (*load*, *stress* y *spike*) contra el mismo handler de la API desplegado
en un servidor local de un solo proceso, con repositorio en memoria. La carga fue mixta: 50 % ingesta en lotes de 25
registros con **15 % de lotes reenviados** para simular reintentos, y 50 % lecturas de resumen. Al final de cada
corrida, el generador compara el costo agregado que reporta la API con la suma exacta de los registros únicos aceptados.

| Escenario | Peticiones | req/s | Registros/s | Lotes duplicados | Ingesta p50/p95/p99 (ms) | Lectura p50/p95/p99 (ms) | Errores | Costo esperado vs. observado (USD) |
|---|---|---|---|---|---|---|---|---|
| Load | 1.049 | 28,2 | 287,4 | 75 | 593 / 2.297 / 3.152 | 1.073 / 2.796 / 6.383 | 1,8 % | 266.870,15 = 266.870,15 |
| Stress | 964 | 28,4 | 322,8 | 78 | 355 / 1.875 / 2.490 | 606 / 3.034 / 5.535 | 2,1 % | 274.696,88 = 274.696,88 |
| Spike | 688 | 22,9 | 235,2 | 60 | 246 / 1.165 / 1.456 | 326 / 1.645 / 5.371 | 2,5 % | 177.450,48 = 177.450,48 |

**Exactitud.** En los tres escenarios, con 213 lotes duplicados en total (5.325 registros reenviados), el error de
agregación fue **0,00 USD**. Esto confirma empíricamente el escenario QAS-R1.

**Disponibilidad de la ingesta.** El 100 % de las peticiones de ingesta fue aceptado (HTTP 202). Los errores
observados (1,8-2,5 %) corresponden exclusivamente a lecturas que superaron el *timeout* del cliente cuando el proceso
estaba saturado.

**Rendimiento.** El techo de alrededor de 28 req/s y las latencias de segundos **son propios del arnés local**: un
único proceso de Python, limitado por el GIL, que además drena la cola sincrónicamente en el hilo de cada petición.
No son representativos del despliegue en AWS, donde la API y el colector escalan como funciones independientes. Aun
así, el experimento aporta un resultado útil para la arquitectura: la **consulta de resumen es la operación más costosa
en CPU** (tres consultas de agregados más ordenamientos, con p99 superior a 5 s bajo saturación). Esto respalda la
decisión de precalcular agregados (CQRS) y señala la caché de lectura como la siguiente optimización.

**Pruebas en AWS.** El protocolo para la nube (k6 con escenarios *load*, *stress*, *spike* y *soak*, más la
verificación de consistencia de `loadgen.py`) está automatizado en el repositorio, con criterios de aceptación
explícitos (p95 de ingesta < 500 ms, errores < 1 %, DLQ = 0, *backlog* drenado en < 15 min). Sus resultados deben
incorporarse al ejecutarlo en la cuenta de AWS del equipo. Este artículo no reporta cifras de la nube que no se
hayan medido.

## 5.3 Evaluación por atributo de calidad

| Atributo | Mecanismo | Evidencia | Estado |
|---|---|---|---|
| Confiabilidad | Ledger con deltas, transacciones, OCC | Pruebas de propiedades y de estrés con duplicados | **Verificado** |
| Disponibilidad | Cola + DLQ, lote parcial, servicios multi-AZ | Prueba de aislamiento de fallas por mensaje | Verificado en pruebas; SLO por medir en AWS |
| Desempeño | Asincronía, CQRS, particiones mensuales | Medición local; umbrales k6 definidos | Parcial (pendiente en AWS) |
| Escalabilidad | Lambda + SQS + DynamoDB *on-demand*, concurrencia acotada | Escenarios *stress*/*spike* definidos | Por diseño; pendiente en AWS |
| Seguridad | JWT, tenant desde la claim, mínimo privilegio, cifrado | `test_tenant_isolation`, modelo STRIDE | **Verificado** |
| Interoperabilidad | Modelo canónico, OpenAPI 3.1, OAuth 2.0 | Ingesta *push* de extremo a extremo | **Verificado** |
| Modificabilidad | Hexagonal, Strategy/Registry | Proveedor nuevo = 1 módulo + 1 registro | **Verificado** |
| Mantenibilidad | Capas, tipado estricto, lint en CI | 0 hallazgos estáticos | **Verificado** |
| Testabilidad | Puertos + dobles en memoria + moto | 96,4 % de cobertura sin AWS | **Verificado** |
| Reusabilidad | Módulos Terraform y conectores desacoplados | `lambda_function` × 4 | **Verificado** |
| Soportabilidad | Logs JSON, X-Ray, EMF, runbook, alarmas | Dashboard operativo en IaC | Por diseño |

## 5.4 Fortalezas

1. **Corrección por construcción:** la lógica de deltas es una función pura, probada de forma exhaustiva, y el
   adaptador solo garantiza atomicidad y aislamiento.
2. **Costo proporcional al uso:** sin cómputo ocioso, coherente con el *driver* BD5. La propia plataforma se
   autoobserva mediante `default_tags`.
3. **Extensibilidad real:** la API *push* convierte a "cualquier sistema" en fuente sin desarrollo adicional, y los
   conectores aíslan los cambios frecuentes de las APIs de los proveedores.
4. **Gobierno integrado:** atribución, presupuestos con alertas idempotentes, KPIs y RACI conectan la herramienta con
   APO06 y con las fases *Inform* y *Operate* de FinOps.

## 5.5 Limitaciones

1. **Agregados calientes:** la tasa de conflictos OCC crece con la concurrencia sobre una misma celda (punto de
   sensibilidad S1). La concurrencia del consumidor está acotada; la solución estructural (*sharding* de celdas) no se
   implementó.
2. **Costo de escritura:** cada registro implica una lectura consistente y una transacción de hasta cuatro ítems
   (2× WCU), el precio de lecturas rápidas.
3. **Atribución en OpenAI:** el costo por persona no está disponible en la fuente y debe estimarse.
4. **Montos antes de créditos e impuestos:** se requiere conciliación con la factura para el cierre contable.
5. **Validación en la nube pendiente:** las cifras de rendimiento y elasticidad en AWS aún deben medirse con el
   protocolo provisto.
6. **Aislamiento lógico:** el modelo *pool* de tabla compartida puede no bastar para clientes regulados [26].

## 5.6 Mejoras propuestas

*Sharding* de agregados calientes y agregación vía DynamoDB Streams; caché de lectura por tenant y rango; *data lake*
en S3 con Athena para análisis *ad hoc*; IAM con `dynamodb:LeadingKeys` para reforzar el aislamiento; pronóstico de
gasto y detección de anomalías; conciliación automática con facturas.

# 6. Conclusión

Este trabajo mostró que el gobierno del consumo multiproveedor de IA y nube es, ante todo, un problema de
**exactitud de datos en un sistema distribuido**, y que puede resolverse con una arquitectura serverless económica si
la idempotencia se diseña como propiedad del dominio y no como un detalle de la infraestructura. El ledger basado en
deltas, con transacciones y control de concurrencia optimista, logró error de agregación nulo bajo duplicados
inyectados, revisiones y escritura concurrente, verificado tanto por pruebas basadas en propiedades como por pruebas
de estrés con comprobación de consistencia.

**Implicaciones para la práctica.** (i) Las plataformas FinOps deberían tratar la entrega duplicada y las revisiones
de los proveedores como casos normales y no excepcionales. (ii) Un modelo canónico más una API de ingesta abierta
convierte la integración de N proveedores en un problema lineal y desacopla la organización de los cambios de cada
proveedor. (iii) Los marcos de gobierno (COBIT APO06, ISO/IEC 38500) ganan efectividad cuando se traducen a
capacidades verificables: KPIs calculados por el sistema, alertas idempotentes y responsables explícitos (RACI).

**Trabajo futuro.** Ejecutar y publicar el protocolo de estrés en AWS; cuantificar la relación entre concurrencia y
conflictos OCC para dimensionar el *sharding* de agregados; incorporar pronóstico y detección de anomalías sobre el
ledger; y evaluar el modelo de aislamiento *silo* frente a *pool* para escenarios regulados.

# Referencias

[1] L. Bass, P. Clements y R. Kazman, *Software Architecture in Practice*, 4.ª ed. Boston, MA, EE. UU.: Addison-Wesley, 2021.

[2] R. Kazman, M. Klein y P. Clements, "ATAM: Method for Architecture Evaluation," Software Engineering Institute, Carnegie Mellon University, Rep. téc. CMU/SEI-2000-TR-004, 2000.

[3] The Open Group, *The TOGAF Standard, 10th Edition*. The Open Group, 2022.

[4] The Open Group, *ArchiMate 3.2 Specification*. The Open Group, 2022.

[5] ISACA, *COBIT 2019 Framework: Governance and Management Objectives*. Schaumburg, IL, EE. UU.: ISACA, 2018.

[6] *Information technology — Governance of IT for the organization*, ISO/IEC 38500:2015, 2015.

[7] FinOps Foundation, "FinOps Framework." [En línea]. Disponible: https://www.finops.org/framework/

[8] J. R. Storment y M. Fuller, *Cloud FinOps: Collaborative, Real-Time Cloud Value Decision Making*, 2.ª ed. Sebastopol, CA, EE. UU.: O'Reilly Media, 2023.

[9] A. Cockburn, "Hexagonal architecture," 2005. [En línea]. Disponible: https://alistair.cockburn.us/hexagonal-architecture/

[10] G. Hohpe y B. Woolf, *Enterprise Integration Patterns: Designing, Building, and Deploying Messaging Solutions*. Boston, MA, EE. UU.: Addison-Wesley, 2003.

[11] M. Kleppmann, *Designing Data-Intensive Applications*. Sebastopol, CA, EE. UU.: O'Reilly Media, 2017.

[12] P. Helland, "Idempotence is not a medical condition," *Communications of the ACM*, vol. 55, n.º 5, pp. 56–65, 2012.

[13] H. T. Kung y J. T. Robinson, "On optimistic methods for concurrency control," *ACM Transactions on Database Systems*, vol. 6, n.º 2, pp. 213–226, 1981.

[14] E. Jonas et al., "Cloud programming simplified: A Berkeley view on serverless computing," University of California, Berkeley, Rep. téc. UCB/EECS-2019-3, 2019.

[15] M. Fowler, "CQRS," 2011. [En línea]. Disponible: https://martinfowler.com/bliki/CQRS.html

[16] S. Brown, "The C4 model for visualising software architecture." [En línea]. Disponible: https://c4model.com

[17] M. Nygard, "Documenting architecture decisions," 2011. [En línea]. Disponible: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions

[18] Amazon Web Services, "AWS Well-Architected Framework — Serverless Applications Lens." [En línea]. Disponible: https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/

[19] A. DeBrie, *The DynamoDB Book*, 2020.

[20] Anthropic, "Usage and Cost Analytics API," Claude Platform Docs, 2026. [En línea]. Disponible: https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api

[21] OpenAI, "Usage API and Costs API reference," OpenAI Platform Docs. [En línea]. Disponible: https://platform.openai.com/docs/api-reference/usage

[22] M. Brooker, "Exponential backoff and jitter," AWS Architecture Blog, 2015. [En línea]. Disponible: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

[23] OWASP Foundation, "OWASP API Security Top 10 — 2023." [En línea]. Disponible: https://owasp.org/API-Security/editions/2023/en/0x11-t10/

[24] D. R. MacIver, Z. Hatfield-Dodds et al., "Hypothesis: A new approach to property-based testing," *Journal of Open Source Software*, vol. 4, n.º 43, p. 1891, 2019.

[25] P. Bailis y A. Ghodsi, "Eventual consistency today: Limitations, extensions, and beyond," *Communications of the ACM*, vol. 56, n.º 5, pp. 55–63, 2013.

[26] Amazon Web Services, "SaaS Tenant Isolation Strategies," AWS Whitepaper, 2020.
