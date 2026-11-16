# ADR-0003: DynamoDB *single-table* con agregados precalculados (CQRS)

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
Los patrones de acceso son conocidos y pocos: (1) leer y escribir un hecho por clave natural; (2) sumar costo
y tokens por día × proveedor × {persona, equipo, servicio} en un rango; (3) leer la configuración del tenant.
Sumar los hechos crudos en cada consulta (decenas de miles de ítems para 90 días) no cumple QAS-P2.

## Decisión
- Una tabla DynamoDB *on-demand* con claves compuestas `PK/SK` (ver [modelo de datos](../07-modelo-datos.md)).
- **CQRS:** el lado de escritura mantiene el *ledger* de hechos; el lado de lectura consulta **agregados diarios
  precalculados** por dimensión, actualizados en la misma transacción que el hecho (consistencia fuerte entre ambos).
- Particionamiento **mensual** de hechos y agregados.

## Alternativas consideradas
| Opción | Evaluación |
|---|---|
| Aurora Serverless v2 (SQL) | `GROUP BY` flexible, pero tiene costo mínimo por ACU, requiere VPC y conexiones desde Lambda (RDS Proxy). |
| Timestream / InfluxDB | Bueno para series, pero débil en *upsert* idempotente y en transacciones. |
| Athena sobre S3 (data lake) | Muy barato para análisis *ad hoc*, pero tiene latencia de segundos y no sirve para un dashboard interactivo. Se considera como complemento futuro. |
| Agregar en lectura con GSI | Más simple de escribir, pero la latencia crece con el volumen. |

## Consecuencias
- **+** Lecturas O(días × proveedores × valores) independientes del volumen de hechos; latencia de un dígito de ms por página.
- **+** Sin servidores ni conexiones que administrar.
- **−** Cada escritura toca hasta 4 ítems (≈ 2× WCU por transacción). Es el costo explícito de leer rápido.
- **−** Las nuevas dimensiones de análisis requieren nuevos agregados y un *backfill* (menos flexible que SQL).
- **−** Riesgo de **agregados calientes** (la celda de un equipo o modelo popular en el día actual); ver ADR-0004 y la sección de riesgos.
