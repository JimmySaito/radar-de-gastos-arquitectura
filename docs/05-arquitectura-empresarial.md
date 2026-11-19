# 5. Arquitectura empresarial

El análisis sigue el **TOGAF Standard, 10.ª edición (ADM)** y representa las capas con la notación conceptual de
**ArchiMate 3.2** (negocio, aplicación, tecnología), expresada en Mermaid para versionarla como código.

## 5.1 Recorrido del ADM aplicado

| Fase ADM | Salida en este proyecto |
|---|---|
| Preliminar | Principios de arquitectura (5.2), alcance FinOps, repositorio de arquitectura como código |
| A. Visión | Visión, interesados y *drivers* ([01](01-contexto-negocio.md)) |
| B. Arquitectura de negocio | Mapa de capacidades, cadena de valor, actores y roles (5.3, 5.4) |
| C. Sistemas de información | Modelo canónico de datos ([07](07-modelo-datos.md)); componentes de aplicación (5.5) |
| D. Tecnología | Plataforma serverless en AWS ([C4 despliegue](03-vistas-c4.md#34-vista-de-despliegue)) |
| E. Oportunidades y soluciones | *Gap analysis* (5.6) y paquetes de trabajo |
| F. Planificación de la migración | *Roadmap* de transición (5.7) |
| G. Gobierno de la implementación | Revisiones de ADR, CI como control de conformidad ([06](06-gobierno-ti.md)) |
| H. Gestión del cambio | ADR nuevas que reemplazan a las anteriores; métricas de gobierno |
| Gestión de requisitos | Escenarios de calidad trazables a tácticas y pruebas ([02](02-atributos-calidad.md)) |

## 5.2 Principios de arquitectura

| # | Principio | Fundamento | Implicaciones |
|---|---|---|---|
| P1 | **Una sola verdad del consumo** | Las decisiones financieras requieren cifras únicas | Ledger canónico; ningún informe lee directamente de los proveedores |
| P2 | **Todo gasto tiene dueño** | La atribución habilita el *showback* | Mapeo obligatorio; KPI de % sin asignar |
| P3 | **Integración por contrato** | Proveedores cambiantes | Modelo canónico + API versionada + adaptadores |
| P4 | **Seguridad por diseño y mínimo privilegio** | Llaves Admin con alto impacto | Solo lectura, Secrets Manager, IAM por función |
| P5 | **Administrado antes que construido** | Equipo pequeño, BD5 | Serverless; cero servidores propios |
| P6 | **Infraestructura y arquitectura como código** | Trazabilidad y auditoría | Terraform, ADR y diagramas versionados |

## 5.3 Mapa de capacidades de negocio (FinOps)

```mermaid
flowchart TB
  subgraph L0 [Gestión financiera de la tecnología]
    subgraph C1 [Entender el uso y el costo]
      c11[Ingesta de datos de consumo]
      c12[Normalización y asignación]
      c13[Reportes y análisis]
    end
    subgraph C2 [Cuantificar el valor de negocio]
      c21[Presupuestación]
      c22[Pronóstico]
      c23[Unit economics]
    end
    subgraph C3 [Optimizar uso y costo]
      c31[Detección de anomalías]
      c32[Optimización de tarifas y modelos]
    end
    subgraph C4 [Gestionar la práctica FinOps]
      c41[Políticas y gobierno]
      c42[Educación y habilitación]
    end
    subgraph C5 [Gestionar suscripciones y licencias]
      c51[Inventario de licencias SaaS]
      c52[Calendario de cobros y renovaciones]
      c53[Reparto de cobros compartidos]
      c54[Detección de duplicidades]
    end
  end
  classDef poc fill:#2a78d6,color:#fff
  classDef future fill:#e2e1dc,color:#333
  class c11,c12,c13,c21,c41,c51,c52,c53 poc
  class c22,c23,c31,c32,c42,c54 future
```

Leyenda: en azul, las capacidades cubiertas por el PoC; en gris, la evolución futura. Los dominios C1 a C4
corresponden a los del FinOps Framework de la FinOps Foundation. C5 aplica esas capacidades a los *Scopes* de SaaS y
licencias que el marco incorporó en 2025 (*Cloud+*) y, en el espacio Personal, al gasto de un hogar.

## 5.4 Cadena de valor: "del consumo a la decisión"

```mermaid
flowchart LR
  v1[Consumir IA/nube] --> v2[Capturar uso] --> v3[Atribuir a dueño] --> v4[Visualizar] --> v5[Comparar con presupuesto] --> v6[Decidir y optimizar]
```

## 5.5 Vista de capas (estilo ArchiMate)

```mermaid
flowchart TB
  subgraph Negocio
    a1([Actor: Líder FinOps])
    a2([Actor: Líder de equipo])
    p1[Proceso: Revisión mensual de gasto]
    p2[Proceso: Control presupuestario]
    s1{{Servicio de negocio: Showback de consumo}}
  end
  subgraph Aplicación
    as1{{Servicio de aplicación: Consulta de consumo}}
    as2{{Servicio de aplicación: Ingesta de consumo}}
    as3{{Servicio de aplicación: Alertas de presupuesto}}
    ac1[Componente: Dashboard SPA]
    ac2[Componente: API Radar de gastos]
    ac3[Componente: Colector]
    do1[(Objeto de datos: UsageRecord)]
  end
  subgraph Tecnología
    t1[Nodo: AWS Lambda]
    t2[Nodo: DynamoDB]
    t3[Nodo: SQS]
    t4[Nodo: Cognito]
  end
  a1 & a2 --> p1 & p2
  p1 --> s1
  p2 --> s1
  s1 --> as1 & as3
  as1 --> ac1 --> ac2
  as2 --> ac2
  ac2 --> ac3
  ac2 & ac3 --> do1
  ac2 & ac3 --> t1
  do1 --> t2
  ac3 --> t3
  ac2 --> t4
```

## 5.6 *Gap analysis* (línea base → objetivo)

| Dimensión | Línea base (AS-IS) | Objetivo (TO-BE) | Brecha / paquete de trabajo |
|---|---|---|---|
| Datos | Consolas separadas, exportes CSV manuales | Ledger canónico consolidado | WP1: conectores + ledger |
| Atribución | Llaves compartidas sin dueño | Mapeo principal → persona → equipo | WP2: modelo de gobierno + API de mapeos |
| Control | Factura mensual (reactivo) | Presupuestos con alertas al 50/80/100 % | WP3: evaluador de presupuestos |
| Seguridad | Llaves Admin en hojas de cálculo | Secrets Manager + rotación | WP4: custodia y rotación |
| Integración | Ninguna | API abierta para cualquier sistema | WP5: API de ingesta + OpenAPI |
| Operación | N/A | IaC + observabilidad | WP6: Terraform + CloudWatch |

## 5.7 *Roadmap* de transición

```mermaid
gantt
  dateFormat YYYY-MM
  title Arquitecturas de transición
  section Transición 1 (PoC)
  Conectores IA + AWS, ledger, dashboard        :done, t1, 2026-10, 2026-11
  section Transición 2
  SSO corporativo, roles por equipo            :t2a, 2026-12, 2027-01
  Data lake S3 + Athena para análisis ad hoc   :t2b, 2027-01, 2027-02
  section Transición 3
  Pronóstico y detección de anomalías          :t3a, 2027-02, 2027-04
  Chargeback integrado con ERP                 :t3b, 2027-03, 2027-05
```
