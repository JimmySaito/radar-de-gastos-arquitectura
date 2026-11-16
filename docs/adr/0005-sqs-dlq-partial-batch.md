# ADR-0005: SQS con DLQ y respuesta de lote parcial

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
Un proveedor caído, una credencial vencida o un mensaje malformado no deben bloquear al resto de los tenants ni de
los conectores (QAS-A1). La ingesta *push* debe absorber ráfagas sin rechazar clientes (QAS-S1).

## Decisión
- Una cola SQS estándar como *buffer* entre la API/scheduler y el colector (*queue-based load leveling*).
- *Event source mapping* con `batch_size=10`, `ReportBatchItemFailures` y `maximum_concurrency` configurable.
- DLQ tras `maxReceiveCount=5`, con retención de 14 días, alarma inmediata y *redrive* habilitado.
- *Visibility timeout* = 6 × timeout del colector (recomendación de AWS).

## Consecuencias
- **+** Aislamiento de fallas por mensaje (*bulkhead*); solo se reintenta lo fallido.
- **+** La API responde 202 en milisegundos, independientemente de la carga de escritura.
- **+** La concurrencia máxima protege DynamoDB (conflictos) y los *rate limits* de los proveedores.
- **−** Consistencia eventual: el dato *push* aparece en el dashboard segundos después.
- **−** Si todos los mensajes de un lote fallan, Powertools lanza la excepción para que Lambda reintente el lote completo (comportamiento esperado).
