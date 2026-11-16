# ADR-0004: Ledger idempotente con deltas y concurrencia optimista

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
Hay tres fuentes de duplicación o cambio que, mal tratadas, falsean el gasto reportado:
1. SQS estándar entrega **al menos una vez**; Lambda reintenta lotes.
2. Los proveedores **revisan** las cifras de un día durante 24 h o más; la ventana móvil (ADR-0010) relee días ya cargados.
3. Varios colectores pueden escribir **concurrentemente** el mismo hecho o la misma celda agregada.

El requisito QAS-R1 exige error cero en el agregado.

## Decisión
1. **Identidad determinista:** `record_id = sha256(clave natural)`. Las métricas no forman parte de la identidad.
2. **Upsert con deltas** (función pura `compute_deltas`): Δ = nuevo − anterior por celda agregada. Si cambió la
   atribución, se resta de las celdas antiguas y se suma a las nuevas, fusionando las celdas repetidas.
3. **Atomicidad:** `TransactWriteItems` = Put del hecho + `ADD Δ` en cada agregado.
4. **Control de concurrencia optimista:** el Put del hecho lleva la condición `attribute_not_exists(PK)` en la
   primera escritura o `version = :v` después. Ante `ConditionalCheckFailed` o `TransactionConflict` se relee y
   se reintenta con *backoff* exponencial y *full jitter* (hasta 8 intentos). Al agotarlos, el mensaje vuelve a SQS.
5. **Cortocircuito:** si el `content_hash` y la atribución no cambiaron, no se escribe (`UNCHANGED`).

## Alternativas consideradas
| Opción | Por qué no |
|---|---|
| SQS FIFO con deduplicación | Solo deduplica 5 minutos y por `MessageDeduplicationId`; no resuelve revisiones ni relecturas horas después. Además limita el *throughput*. |
| Powertools Idempotency (tabla de llaves) | Deduplica invocaciones, no hechos de negocio revisados; no calcula deltas. |
| Recalcular agregados por lotes (*batch*) | Correcto pero no inmediato; costoso de reconstruir en cada carga. |
| Bloqueo pesimista | Requiere un componente de *locking* y aumenta la latencia; DynamoDB favorece OCC. |
| Streams de DynamoDB para agregar | Desacopla la escritura, pero los streams también entregan al menos una vez y se necesitaría idempotencia en el agregador. Queda como evolución si aparecen agregados calientes. |

## Consecuencias
- **+** Efecto exactamente-una-vez sobre los agregados, verificado por pruebas de propiedades y de carga con duplicados.
- **+** Reprocesar desde la DLQ o hacer *backfill* es seguro por construcción.
- **−** Cada registro cuesta 1 lectura consistente + 1 transacción (2× WCU), más reintentos bajo contención.
- **−** **Punto de sensibilidad:** los conflictos crecen con la concurrencia sobre la misma celda (p. ej. todos los
  registros de un equipo en el mismo día). Mitigaciones: limitar `maximum_concurrency` del consumidor y, como
  evolución, fragmentar (*shard*) los agregados calientes (`…#value#shardN`) y sumarlos en la lectura.
