# 8. Estrategia de pruebas

## 8.1 Pirámide de pruebas

| Nivel | Herramientas | Qué valida | Cantidad |
|---|---|---|---|
| Unitarias | pytest | Modelo, ledger (deltas), servicios, conectores (incl. Claude Code local), catálogo, configuración de conexiones, persistencia local, gastos recurrentes (calendario de cobros, equivalentes, resumen, personas y reparto exacto) | 95 |
| Propiedades | Hypothesis | Los agregados convergen a la última versión con duplicados y revisiones arbitrarias; los cobros recurrentes son crecientes y caen dentro de la ventana para cualquier fecha y ciclo | 2 |
| Integración | moto (DynamoDB, SQS, SNS, Secrets Manager) | Transacciones, OCC con conflictos inyectados, paginación, consultas entre meses, custodia de secretos, gastos recurrentes y personas | 15 |
| Handlers / contrato | Eventos reales de API Gateway v2 y SQS | Autorización, aislamiento de tenants, lote parcial, configuración de conexiones, vista de ejemplo, privacidad de suscripciones personales, filtro por persona, ejemplo personal de solo lectura y permisos de licencias | 17 |
| Estáticas | ruff, mypy --strict, bandit, checkov, terraform validate | Estilo, tipos, seguridad del código e IaC | CI |
| Carga / estrés | k6 (AWS), `loadgen.py` (local y AWS) | Rendimiento, elasticidad, consistencia bajo duplicados | 4 escenarios |

Cobertura (líneas y ramas): **96,5 %** con 153 pruebas (umbral de CI: 80 %). Tiempo de la suite: alrededor de 11 s, sin cuenta de AWS.

## 8.2 Plan de pruebas de estrés

| Escenario | Perfil | Objetivo | Criterio de aceptación |
|---|---|---|---|
| **Load** | 50 req/s × 25 registros (1.250 registros/s), 10 min | Comportamiento nominal | p95 < 500 ms; errores < 1 %; DLQ = 0 |
| **Stress** | Rampa de 10 a 1.000 req/s en 11 min | Punto de quiebre y modo de falla | Degradación controlada (429 de API Gateway, no 5xx); sin pérdida de datos |
| **Spike** | 20 → 500 req/s en 10 s, se sostiene 2 min | Elasticidad y arranques en frío | *Backlog* drenado en < 15 min; DLQ = 0 |
| **Soak** | 30 req/s durante 1 h | Fugas y degradación | p95 estable (±10 %) |
| **Consistencia** | Cualquier perfil con 10-15 % de lotes duplicados | QAS-R1 | Costo agregado = Σ costo de los registros únicos (Δ = 0) |

Métricas observadas: latencia (p50/p95/p99) de API Gateway, `ConcurrentExecutions` y `Throttles` del colector,
`ApproximateAgeOfOldestMessage`, `LedgerRetry*` (conflictos OCC), `QueueToLedgerLatency`, consumo de WCU y DLQ.

## 8.3 Resultados medidos — entorno local

**Entorno:** Windows 11, Python 3.13, servidor local de un solo proceso (`scripts/local_server.py`) que ejecuta
**el mismo handler** de Lambda con repositorio en memoria. Generador: `scripts/loadgen.py`, modo mixto
(50 % ingesta, 50 % lectura), 25 registros por lote, 15 % de lotes duplicados, 32 conexiones. Duración: unos 30 s por escenario.

| Escenario | Peticiones | req/s logradas | Registros/s | Duplicados enviados | Ingesta p50 / p95 / p99 (ms) | Lectura p50 / p95 / p99 (ms) | Errores | Costo esperado = observado |
|---|---|---|---|---|---|---|---|---|
| Load (60 req/s objetivo) | 1.049 | 28,2 | 287,4 | 75 | 593 / 2.297 / 3.152 | 1.073 / 2.796 / 6.383 | 1,8 % (lecturas con *timeout*) | 266.870,15 = 266.870,15 ✔ |
| Stress (rampa 6→120 req/s) | 964 | 28,4 | 322,8 | 78 | 355 / 1.875 / 2.490 | 606 / 3.034 / 5.535 | 2,1 % (lecturas) | 274.696,88 = 274.696,88 ✔ |
| Spike (12→120 req/s) | 688 | 22,9 | 235,2 | 60 | 246 / 1.165 / 1.456 | 326 / 1.645 / 5.371 | 2,5 % (lecturas) | 177.450,48 = 177.450,48 ✔ |

Datos crudos: `radar-de-gastos/docs/results/local-*.json`.

**Interpretación:**
- **Confiabilidad (QAS-R1) confirmada:** en los tres escenarios, con 60-78 lotes duplicados inyectados, el costo
  agregado coincide al centavo con la suma de los registros únicos.
- **El 100 % de las ingestas fue aceptado (202).** Los errores corresponden solo a lecturas que superaron el
  *timeout* del cliente cuando el proceso estaba saturado.
- **El techo de alrededor de 28 req/s es del arnés local, no de la arquitectura:** un único proceso de Python
  (GIL) que, además, drena la cola de forma síncrona en el mismo hilo de la petición. El cliente descartó
  peticiones (`client_dropped`) al saturarse. En AWS, la API y el colector son funciones independientes que escalan
  horizontalmente. El experimento local aísla el **costo de CPU de la aplicación**: la lectura de resumen
  (3 consultas de agregados + ordenamientos) es la operación más costosa, lo que respalda la decisión CQRS y sugiere
  caché para rangos frecuentes.

## 8.4 Resultados en AWS

**Entorno:** AWS Academy Learner Lab (`us-east-1`), despliegue en modo laboratorio (funciones con `LabRole`, API
que sirve el dashboard, sin X-Ray). Colector con concurrencia máxima de 20 (`collector_max_concurrency`). Generador:
`scripts/stress_aws.py`, que obtiene un token OAuth 2.0 *client credentials*, ejecuta `scripts/loadgen.py` (50 %
ingesta en lotes de 25 registros con **15 % de lotes duplicados**, 50 % lecturas de resumen, 64 conexiones) y lee de
CloudWatch las métricas del servidor de cada ventana. La ingesta va a un tenant dedicado (`pruebas-carga`). El
cliente corrió desde un equipo personal en Bogotá (latencia de red incluida en las cifras del cliente). Fecha:
20 de noviembre de 2026, 01:16–01:52 UTC. Datos crudos: `radar-de-gastos/docs/results/aws-{load,stress,spike}.json`.

La carga se redujo respecto del plan de la sección 8.2 (20 req/s base y 2 minutos por escenario, frente a 50 req/s
y 10 minutos) para no agotar el crédito del laboratorio; la prueba *soak* no se ejecutó.

**Cliente:**

| Escenario | Peticiones | req/s logradas | Registros/s | Lotes duplicados | Ingesta p50 / p95 / p99 (ms) | Lectura p50 / p95 / p99 (ms) | Errores |
|---|---|---|---|---|---|---|---|
| Load (20 req/s) | 2.400 | 19,7 | 213,3 | 170 | 130 / 199 / 461 | 1.027 / 1.953 / 2.073 | 0 % |
| Stress (rampa 2→38 req/s) | 2.014 | 14,2 | 147,2 | 158 | 129 / 346 / 1.946 | 4.780 / 10.113 / 15.781 | 0,05 % (1 lectura 503) |
| Spike (4→40 req/s) | 1.051 | 8,4 | 90,4 | 76 | 132 / 481 / 2.209 | 5.082 / 12.032 / 19.014 | 0,19 % (1 lectura 503, 1 *timeout* 500) |

**Servidor (CloudWatch):**

| Escenario | Concurrencia máx. API / colector | Registros escritos en el ledger | Conflictos OCC (reintentos) | Duración p95 del colector | Mensajes visibles máx. / edad máx. (s) | DLQ | *Throttling* DynamoDB |
|---|---|---|---|---|---|---|---|
| Load | 24 / **20** | 23.353 | 24.262 | 43,9 s | 340 / 406 | 0 | 0 |
| Stress | 64 / **20** | 18.004 | 16.188 | 59,8 s | 390 / 465 | 0 | 0 |
| Spike | 64 / **20** | 11.284 | 8.137 | 46,8 s | 87 / 468 | 0 | 0 |

**Consistencia (QAS-R1):** la verificación de `loadgen.py` termina a los 300 s; en ese momento el ledger había
procesado el 94-95 % del costo, porque quedaba trabajo en cola. Al vaciarse la cola se verificó de nuevo cada corrida
con `scripts/verify_load_runs.py`:

| Escenario | Costo esperado (USD) | Observado a los 300 s | Observado con la cola vacía |
|---|---|---|---|
| Load | 648.727,51 | 611.307,33 | **648.727,51** ✔ |
| Stress | 525.235,32 | 496.458,97 | **525.235,32** ✔ |
| Spike | 279.914,39 | 267.055,92 | **279.914,39** ✔ |

**Criterios de aceptación:**

| Criterio | Resultado |
|---|---|
| p95 de ingesta < 500 ms | ✔ 199 / 346 / 481 ms |
| Errores < 1 % | ✔ 0 % / 0,05 % / 0,19 % |
| DLQ = 0 | ✔ en los tres escenarios |
| Exactitud (Δ = 0) | ✔ en los tres, con 404 lotes duplicados (10.100 registros reenviados) |
| *Backlog* drenado en < 15 min | ✔ cola visible en 0 a los pocos minutos de cada escenario y vacía en la verificación final (01:59 UTC) |
| Latencia de lectura (objetivo p95 < 800 ms de la alarma) | ✘ 1,9 a 12 s |

**Interpretación:**

1. **La ingesta escala y es exacta.** API Gateway y Lambda aceptaron el 100 % de los lotes con p95 por debajo del
   objetivo, y el costo agregado coincidió al centavo con la suma de los registros únicos en las tres corridas, pese
   a 48.587 reintentos por conflicto.
2. **El cuello de botella de escritura son las celdas agregadas calientes (punto de sensibilidad S1).** Todos los
   registros de una corrida comparten día, equipo y servicio, así que cada transacción actualiza los mismos dos
   ítems de agregado. El control de concurrencia optimista serializa a los 20 colectores: la capacidad efectiva fue de
   unos 100 registros/s frente a hasta 250 de llegada, la duración del colector subió a 44-60 s y la cola acumuló
   *backlog*. Algunos lotes agotaron sus 8 reintentos y volvieron a la cola (20 errores de la función), que los
   reentregó tras el *visibility timeout*; ninguno llegó a la DLQ. La exactitud se mantuvo; se degradó la frescura
   (latencia de cola a ledger p95 de varios minutos). La solución estructural es repartir esas celdas en *shards*
   (ADR-0004).
3. **La lectura de resumen escala con la cardinalidad de personas.** `summary` lee todas las celdas del agregado por
   persona del rango para calcular el total y el top 10. El generador asigna un principal distinto a cada registro,
   así que el tenant de carga acumuló 29.150 celdas en noviembre y cada lectura las recorrió: p50 de 1 s en *load* y
   de 5 s en los escenarios siguientes, cuando había más datos. La cardinalidad del generador exagera el caso real,
   pero el costo O(n) es un defecto de diseño: el total debe salir de una dimensión de cardinalidad baja y el top-N de
   una estructura precalculada.
4. **El cliente también se saturó.** Con lecturas de varios segundos, las 64 conexiones del generador quedaron
   ocupadas y descartó 505 y 293 peticiones en *stress* y *spike*; por eso las tasas logradas son menores que las
   objetivo. Las cifras de esos escenarios miden el sistema bajo lecturas lentas, no su techo de ingesta.
5. **Observabilidad:** la alarma de latencia p95 se disparó correctamente (01:23, p95 de 1,1 s), pero osciló entre
   ALARM y OK seis veces en media hora, porque evalúa 2 periodos de 5 minutos cada minuto y el periodo en curso,
   todavía incompleto, la devuelve a OK. Necesita histéresis (más periodos para volver a OK), como ya se hizo con la
   alarma de 5xx.

### 8.4.1 Segunda corrida: celdas agregadas en *shards*

Tras repartir cada celda agregada en 8 shards (ADR-0004), calcular el total del resumen desde la dimensión de
equipos y agregar una caché de lecturas de 15 s, se repitieron los tres escenarios con los mismos parámetros
(`docs/results/aws-*-sharding.json`):

| Métrica | Load (antes → después) | Stress | Spike |
|---|---|---|---|
| Conflictos OCC | 24.262 → **4.553** | 16.188 → **5.088** | 8.137 → **1.104** |
| Mensajes visibles en cola (máx.) | 340 → **0** | 390 → **0** | 87 → **0** |
| Cola → ledger, p95 | 430 s → **17 s** | 470 s → **10 s** | 481 s → **12 s** |
| Convergencia exacta | No en 300 s → **17 s** | No → **inmediata** | No → **inmediata** |
| Errores | 0 % → 0 % | 0,05 % → **0 %** | 0,19 % → **0 %** |
| Lotes que agotaron reintentos | 2 → **0** | 17 → **0** | 1 → **0** |
| Lectura p50 / p95 (ms) | 1.027 / 1.953 → 847 / 8.055 | 4.780 / 10.113 → 924 / 12.437 | 5.082 / 12.032 → 1.597 / 17.024 |

El cuello de escritura desapareció: el ledger alcanzó unos 245 registros/s en el pico (antes ≈ 100), la cola no
acumuló trabajo y el costo coincidió al centavo dentro de la propia verificación. Las lecturas, en cambio, empeoraron
en el p95: el top de personas siguió recorriendo todas sus celdas, que se duplicaron al sumarse las de la corrida
anterior, y la caché por instancia no compensó con unas 60 instancias de la API arrancando en frío. Se corrigió
separando el top de personas en su propia ruta (`/v1/summary/members`) para que el resumen solo lea dimensiones de
cardinalidad baja; esa corrección no alcanzó a medirse en AWS (ver 8.4.2).

### 8.4.2 Incidente: desactivación del laboratorio

Al terminar la segunda corrida (02:27 UTC), AWS Academy desactivó la cuenta del laboratorio. Learner Lab permite como
máximo **10 entornos de ejecución de Lambda concurrentes** y desactiva la cuenta al superarlos; ambas corridas lo
superaron (API hasta 64 y colector hasta 20). El presupuesto no fue la causa (0 de 50 USD usados). Se había verificado
el límite técnico de la cuenta (400) pero no la restricción documentada del laboratorio.

Acciones: el modo laboratorio reserva concurrencia por función (API 4, colector 3, horarios 1 + 1 = 9), de modo que el
exceso se rechaza en lugar de superar el límite, y `scripts/stress_aws.py` se niega a ejecutarse en una cuenta de
Learner Lab sin `--allow-lab`. La lección es de gobierno de TI: las cuotas de la plataforma son un requisito no
funcional del despliegue y deben estar en la infraestructura como código, no solo en la documentación.

### 8.4.3 Corrección de las lecturas, medida en local

La separación del top de personas (`/v1/summary/members`) no alcanzó a desplegarse antes de la desactivación del
laboratorio, y el segundo laboratorio disponible no permite crear Lambda, DynamoDB, SQS, API Gateway ni Cognito. Se
midió en local con `scripts/bench_reads.py`, que reproduce la cardinalidad del generador de carga (un principal
distinto por registro) y cuenta las celdas agregadas que lee cada petición (`docs/results/local-lecturas.json`):

| Personas | Antes: una petición (celdas · ms) | Resumen ahora | Top de personas, aparte |
|---|---|---|---|
| 1.000 | 1.006 · 3 | **6** · 0,2 | 1.000 · 3 |
| 10.000 | 10.006 · 39 | **6** · 2 | 10.000 · 37 |
| 30.000 | 30.006 · 217 | **6** · 11 | 30.000 · 206 |
| 60.000 | 60.006 · 460 | **6** · 31 | 60.000 · 429 |

El resumen lee un número constante de celdas, independiente de la cardinalidad; el coste lineal queda aislado en la
petición del top de personas, que el dashboard carga en paralelo sin bloquear el resto. El tiempo residual del resumen
en local se debe a que el repositorio en memoria recorre todas las celdas para filtrar por dimensión; en DynamoDB cada
dimensión es una partición propia y la lectura se limita a esas celdas. La latencia en la nube con esta corrección
queda pendiente de medir.

