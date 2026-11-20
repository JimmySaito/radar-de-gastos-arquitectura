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

Cobertura (líneas y ramas): **96,4 %** con 141 pruebas (umbral de CI: 80 %). Tiempo de la suite: alrededor de 11 s, sin cuenta de AWS.

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

> **Pendiente de ejecución en la cuenta de AWS del equipo.** Los comandos y criterios están definidos y la plantilla
> de resultados abajo se completa con la salida de k6 y del dashboard operativo de CloudWatch. No se reportan
> cifras que no se hayan medido.

```bash
make deploy
TOKEN=$(curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=client_credentials -d scope=radar-gastos/ingest \
        "$COGNITO_DOMAIN/oauth2/token" | jq -r .access_token)
for s in load stress spike; do
  k6 run -e BASE_URL=$API -e TOKEN=$TOKEN -e SCENARIO=$s --summary-export=results/aws-$s.json tests/load/k6_ingest.js
done
python scripts/loadgen.py --base-url $API --token $TOKEN --scenario spike --rps 100 --duration 300 \
       --dup-rate 0.15 --verify-timeout 600 --out results/aws-consistency.json
```

| Escenario | req/s pico | p95 API (ms) | p99 API (ms) | 429 | 5xx | Concurrencia máx. del colector | Edad máx. de la cola (s) | DLQ | Conflictos OCC | Consistencia |
|---|---|---|---|---|---|---|---|---|---|---|
| Load | | | | | | | | | | |
| Stress | | | | | | | | | | |
| Spike | | | | | | | | | | |
| Soak | | | | | | | | | | |
