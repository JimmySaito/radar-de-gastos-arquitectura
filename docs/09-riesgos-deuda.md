# 9. Riesgos, *trade-offs* y deuda técnica

## 9.1 Puntos de sensibilidad y *trade-offs* (ATAM)

| ID | Tipo | Descripción | Atributos en tensión |
|---|---|---|---|
| S1 | Sensibilidad | La concurrencia del colector afecta el *throughput* **y** los conflictos OCC sobre agregados calientes. Medido en AWS: con 20 colectores y celdas sin repartir, ≈ 100 registros/s y minutos de retraso; con 8 *shards*, ≈ 245 registros/s y segundos (ADR-0015) | Escalabilidad ↔ Confiabilidad/Costo |
| S2 | Sensibilidad | `lookback_days` determina la frescura de las correcciones **y** el costo de las APIs (p. ej. USD 0,01 por llamada a Cost Explorer) | Confiabilidad ↔ Costo |
| T1 | *Trade-off* | Agregados precalculados: lecturas rápidas a cambio de escrituras 2× más caras y menos flexibilidad analítica | Desempeño ↔ Modificabilidad/Costo |
| T2 | *Trade-off* | Ingesta asíncrona: alta disponibilidad y absorción de picos a cambio de consistencia eventual | Disponibilidad/Escalabilidad ↔ Consistencia |
| T3 | *Trade-off* | Modelo canónico: un único dashboard para todos los proveedores a cambio de perder detalle específico | Interoperabilidad ↔ Fidelidad |
| T4 | *Trade-off* | Tabla compartida (*pool*): costo y operación mínimos a cambio de aislamiento solo lógico | Costo ↔ Seguridad |
| S3 | Sensibilidad | La cardinalidad de una dimensión determina el costo de leerla: el top de personas es O(n). Medido en AWS: p95 de 2-12 s con 29.150 personas; el resumen pasó a leer 6 celdas fijas (ADR-0016) | Desempeño ↔ Funcionalidad |
| T5 | *Trade-off* | *Shards* en los agregados: menos conflictos de escritura a cambio de leer hasta N ítems por celda caliente | Escalabilidad ↔ Desempeño de lectura |

## 9.2 Riesgos

| ID | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | Un proveedor cambia o depreca su API de uso | Alta | Medio | Adaptadores aislados y pruebas de contrato; Anthropic ya migró sus reportes en 2026 |
| R2 | Agregados calientes con alta concurrencia | Media | Medio | *Shards* de celdas (ADR-0015), límite de concurrencia y métricas `LedgerRetry*`; materializado en la prueba de estrés y mitigado |
| R3 | Filtración de una Admin key | Baja | Alto | Solo lectura, Secrets Manager, rotación, IAM por prefijo, gitleaks |
| R4 | Gasto no atribuible (llaves compartidas) | Alta | Medio | KPI de cobertura, política de llaves por persona, revisión trimestral |
| R5 | Diferencias con la factura (créditos, impuestos, descuentos) | Media | Medio | Se documenta que los montos son antes de créditos/impuestos; conciliación mensual |
| R6 | *Throttling* (429) de los proveedores | Media | Bajo | Reintentos con `retry-after`, concurrencia limitada, ventana diaria |
| R7 | Arranques en frío en picos | Media | Bajo | arm64, importaciones diferidas; *provisioned concurrency* si el SLO lo exige |
| R8 | Superar una cuota de la plataforma (p. ej. 10 Lambdas concurrentes en Learner Lab) | Media | **Alto** | **Materializado:** desactivó el primer laboratorio. Cuotas codificadas en Terraform (concurrencia reservada) y generador de estrés bloqueado en el laboratorio (ADR-0017) |
| R9 | El entorno de demostración no está disponible el día de la presentación | Media | Alto | Respaldo local equivalente, sin dependencias externas y con la misma CSP (ADR-0018) |
| R10 | Diferencias entre local y nube ocultan defectos | Media | Medio | **Materializado** con la CSP (barras vacías en AWS). Misma CSP en local y prueba contra estilos en línea (ADR-0018) |

## 9.3 Deuda técnica conocida

| Deuda | Motivo | Plan |
|---|---|---|
| OpenAI: costo por persona estimado | La API solo agrupa el costo por proyecto | Prorrateo por tokens × precio de catálogo |
| Sin multi-moneda | Todos los proveedores cubiertos facturan en USD | Tabla de tipos de cambio diaria |
| Reatribución histórica manual | El ledger reatribuye al releer, no retroactivamente | Comando de *backfill* con ventana amplia |
| Caché de lectura solo por instancia | Simplicidad del PoC (ADR-0016) | Caché compartida (ElastiCache Serverless o DAX) si las cachés frías vuelven a dominar la latencia |
| Créditos y reembolsos de AWS ignorados | El modelo canónico exige métricas ≥ 0 | Hechos de ajuste con signo en una dimensión separada |
| Lecturas en AWS tras ADR-0016 sin medir | El laboratorio se desactivó antes de redesplegar | Repetir una prueba solo de lecturas, respetando la cuota del laboratorio |
| Top de personas O(n) | Separarlo bastó para el resumen | Vista materializada del top-N si debe ser instantáneo (ADR-0016) |
| Prueba de larga duración (*soak*) no ejecutada | Crédito y cuotas del laboratorio | Ejecutarla en una cuenta sin cuota de concurrencia |
