# 6. Gobierno de TI

Radar de gastos es a la vez un **producto que habilita gobierno** (de costos de IA y nube) y un **sistema que debe ser
gobernado**. Este documento cubre ambas dimensiones con COBIT 2019, el FinOps Framework e ISO/IEC 38500.

## 6.1 Alineación con COBIT 2019

| Objetivo COBIT | Cómo lo soporta Radar de gastos | Evidencia |
|---|---|---|
| **EDM02** Asegurar la entrega de beneficios | Visibilidad del costo por equipo como insumo para evaluar el valor de las iniciativas de IA | Dashboard, `top_teams` |
| **EDM04** Asegurar la optimización de recursos | Identifica concentración de gasto por modelo y proveedor | `top_services`, series |
| **APO06** Gestionar el presupuesto y los costos | Presupuestos mensuales por equipo/proveedor, alertas por umbral, asignación de costos | `services/budgets.py`, `PUT /v1/budgets` |
| **APO09** Gestionar acuerdos de servicio | SLO explícitos (disponibilidad 99,9 %, p95) con alarmas | `observability.tf` |
| **APO10** Gestionar proveedores | Vista comparativa entre proveedores; la atribución apoya renegociaciones | `by_provider` |
| **APO13** Gestionar la seguridad | Modelo de amenazas, mínimo privilegio, cifrado | `docs/security.md` |
| **BAI03** Gestionar la construcción de soluciones | ADR, revisión de código, CI con controles de calidad | `.github/workflows/ci.yml` |
| **BAI06** Gestionar cambios de TI | Cambios de infraestructura por `terraform plan` en PR, despliegue con aprobación de entorno | `deploy.yml` |
| **DSS01** Gestionar operaciones | Runbook, alarmas, dashboard operativo | `docs/runbook.md` |
| **DSS05** Gestionar servicios de seguridad | Secretos en Secrets Manager, rotación sin redespliegue | ADR-0007 |
| **MEA01** Monitorear desempeño y conformidad | KPIs de gobierno (6.4) y métricas técnicas | CloudWatch + dashboard |

## 6.2 FinOps Framework: fases y madurez

| Fase | Actividades habilitadas | Madurez objetivo del PoC |
|---|---|---|
| **Inform** | Ingesta, asignación, *showback*, dashboard | *Walk*: datos diarios, más del 90 % asignado |
| **Optimize** | Comparar modelos y proveedores por costo/token | *Crawl*: vista comparativa, sin recomendaciones automáticas |
| **Operate** | Presupuestos, alertas, políticas de etiquetado (`owner`) | *Crawl → Walk*: alertas automáticas por equipo |

## 6.3 Principios ISO/IEC 38500 aplicados

| Principio | Aplicación |
|---|---|
| Responsabilidad | Cada principal técnico tiene un dueño (persona/equipo) mediante mapeos administrados |
| Estrategia | El *roadmap* de capacidades se alinea con la adopción de IA de la organización |
| Adquisición | La comparación entre proveedores informa decisiones de compra y compromisos de consumo |
| Desempeño | SLO de la plataforma y KPIs de gobierno medidos de forma continua |
| Conformidad | Seguridad por diseño, retención de logs, cifrado; trazabilidad de cambios por IaC |
| Comportamiento humano | La transparencia del consumo por persona promueve el uso responsable (*showback* antes que *chargeback*) |

## 6.4 KPIs de gobierno

| KPI | Fórmula | Meta | Fuente |
|---|---|---|---|
| Cobertura de atribución | costo con `team ≠ unassigned` / costo total | ≥ 95 % | agregados `team` |
| Desvío presupuestario | gasto del mes / presupuesto | ≤ 100 % | `GET /v1/budgets` |
| Frescura de datos | ahora − último dato completo por proveedor | ≤ 24 h | `QueueToLedgerLatency` + latencia del proveedor |
| Costo de la plataforma | costo AWS de Radar de gastos / gasto observado | < 1 % | `default_tags` (autoobservación) |
| Exactitud | Δ entre Radar de gastos y la factura del proveedor al cierre | < 0,5 % | conciliación mensual |

## 6.5 RACI

| Actividad | FinOps | Líder de equipo | Plataforma/SRE | Seguridad | Finanzas |
|---|---|---|---|---|---|
| Registrar conectores y llaves | A | I | R | C | I |
| Mantener mapeos persona/equipo | A/R | C | I | I | I |
| Definir presupuestos | R | C | I | I | A |
| Responder a alertas de presupuesto | C | A/R | I | I | I |
| Operar la plataforma (alarmas, DLQ) | I | I | A/R | I | I |
| Rotar credenciales | I | I | R | A | I |
| Conciliación mensual con facturas | R | I | C | I | A |

R = responsable de ejecutar, A = rinde cuentas (*accountable*), C = consultado, I = informado.

## 6.6 Políticas derivadas

1. **Etiquetado obligatorio:** todo recurso AWS lleva el tag `owner`; las llaves de IA se crean por persona o servicio, nunca compartidas.
2. **Llaves de solo lectura:** para los conectores solo se aprueban credenciales con permisos de lectura de uso y costo.
3. **Revisión trimestral de mapeos:** FinOps revisa el KPI de cobertura y los principales sin asignar.
4. **Umbrales estándar:** presupuestos con alertas al 50, 80 y 100 %; cada alerta se emite una sola vez por umbral y mes (idempotente).
