# 9. Riesgos, *trade-offs* y deuda técnica

## 9.1 Puntos de sensibilidad y *trade-offs* (ATAM)

| ID | Tipo | Descripción | Atributos en tensión |
|---|---|---|---|
| S1 | Sensibilidad | La concurrencia del colector afecta el *throughput* **y** los conflictos OCC sobre agregados calientes | Escalabilidad ↔ Confiabilidad/Costo |
| S2 | Sensibilidad | `lookback_days` determina la frescura de las correcciones **y** el costo de las APIs (p. ej. USD 0,01 por llamada a Cost Explorer) | Confiabilidad ↔ Costo |
| T1 | *Trade-off* | Agregados precalculados: lecturas rápidas a cambio de escrituras 2× más caras y menos flexibilidad analítica | Desempeño ↔ Modificabilidad/Costo |
| T2 | *Trade-off* | Ingesta asíncrona: alta disponibilidad y absorción de picos a cambio de consistencia eventual | Disponibilidad/Escalabilidad ↔ Consistencia |
| T3 | *Trade-off* | Modelo canónico: un único dashboard para todos los proveedores a cambio de perder detalle específico | Interoperabilidad ↔ Fidelidad |
| T4 | *Trade-off* | Tabla compartida (*pool*): costo y operación mínimos a cambio de aislamiento solo lógico | Costo ↔ Seguridad |

## 9.2 Riesgos

| ID | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | Un proveedor cambia o depreca su API de uso | Alta | Medio | Adaptadores aislados y pruebas de contrato; Anthropic ya migró sus reportes en 2026 |
| R2 | Agregados calientes con alta concurrencia | Media | Medio | Límite de concurrencia, métricas `LedgerRetry*`; evolución: *sharding* de celdas |
| R3 | Filtración de una Admin key | Baja | Alto | Solo lectura, Secrets Manager, rotación, IAM por prefijo, gitleaks |
| R4 | Gasto no atribuible (llaves compartidas) | Alta | Medio | KPI de cobertura, política de llaves por persona, revisión trimestral |
| R5 | Diferencias con la factura (créditos, impuestos, descuentos) | Media | Medio | Se documenta que los montos son antes de créditos/impuestos; conciliación mensual |
| R6 | *Throttling* (429) de los proveedores | Media | Bajo | Reintentos con `retry-after`, concurrencia limitada, ventana diaria |
| R7 | Arranques en frío en picos | Media | Bajo | arm64, importaciones diferidas; *provisioned concurrency* si el SLO lo exige |

## 9.3 Deuda técnica conocida

| Deuda | Motivo | Plan |
|---|---|---|
| OpenAI: costo por persona estimado | La API solo agrupa el costo por proyecto | Prorrateo por tokens × precio de catálogo |
| Sin multi-moneda | Todos los proveedores cubiertos facturan en USD | Tabla de tipos de cambio diaria |
| Reatribución histórica manual | El ledger reatribuye al releer, no retroactivamente | Comando de *backfill* con ventana amplia |
| Sin caché de lectura | Simplicidad del PoC | Caché por tenant y rango (CloudFront o ElastiCache Serverless) |
| Créditos y reembolsos de AWS ignorados | El modelo canónico exige métricas ≥ 0 | Hechos de ajuste con signo en una dimensión separada |
| Pruebas de estrés en AWS pendientes | Requieren la cuenta del equipo | Ejecutar el plan de la sección 8.4 |
