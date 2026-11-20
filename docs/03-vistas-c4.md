# 3. Vistas de arquitectura (modelo C4)

## 3.1 Nivel 1: contexto del sistema

```mermaid
flowchart TB
  fin([Finanzas / FinOps]):::person
  lead([Líder de equipo]):::person
  admin([Administrador del tenant]):::person
  ext[Sistemas internos<br/>LLM propio, SaaS, scripts]:::ext

  hub[[Radar de gastos<br/>Observabilidad de consumo<br/>IA + nube]]:::system

  anth[Anthropic<br/>Usage & Cost Analytics API]:::ext
  oai[OpenAI<br/>Organization Usage/Costs API]:::ext
  gcp[Google Cloud<br/>Billing Export en BigQuery]:::ext
  aws[AWS Cost Explorer<br/>cuenta payer]:::ext
  mail[Correo / Chat<br/>vía SNS]:::ext

  fin -- consulta gasto y presupuestos --> hub
  lead -- consulta consumo de su equipo --> hub
  admin -- configura conectores, mapeos, presupuestos --> hub
  ext -- envía registros de consumo, HTTPS + OAuth2 --> hub
  hub -- lee uso y costo, Admin key --> anth
  hub -- lee uso y costo, Admin key --> oai
  hub -- consulta SQL, service account --> gcp
  hub -- GetCostAndUsage, AssumeRole --> aws
  hub -- alertas de presupuesto --> mail

  classDef person fill:#08427b,color:#fff,stroke:#052e56
  classDef system fill:#1168bd,color:#fff,stroke:#0b4884
  classDef ext fill:#999,color:#fff,stroke:#6b6b6b
```

## 3.2 Nivel 2: contenedores

```mermaid
flowchart LR
  user([Usuario]) --> cf[CloudFront + S3<br/>SPA JS / Chart.js]
  user -. OAuth2 PKCE .-> cog[Amazon Cognito<br/>User Pool + Hosted UI]
  m2m([Sistema externo]) -. client_credentials .-> cog
  cf -- HTTPS JSON + JWT --> apigw[API Gateway HTTP<br/>autorizador JWT, throttling]
  m2m -- POST /v1/usage/records --> apigw
  apigw --> api[λ api<br/>Python 3.13 / Powertools]
  api -- Query/Get --> ddb[(DynamoDB<br/>tabla única<br/>hechos + agregados + config)]
  api -- SendMessage --> sqs[(SQS work<br/>+ DLQ)]
  sched[EventBridge Scheduler<br/>rate 1h] --> fan[λ scheduler]
  fan -- SendMessageBatch --> sqs
  sqs -- event source mapping<br/>batch 10, máx. concurrencia --> col[λ collector]
  col -- TransactWriteItems --> ddb
  col -- GetSecretValue --> sm[Secrets Manager]
  col -- HTTPS --> prov[Proveedores externos]
  sched2[EventBridge Scheduler<br/>cron diario] --> bud[λ budget]
  bud --> ddb
  bud --> sns[SNS alertas]
  api & col & fan & bud -. logs, métricas EMF, trazas .-> cw[CloudWatch + X-Ray]
```

| Contenedor | Tecnología | Responsabilidad | Escala |
|---|---|---|---|
| SPA | HTML/JS, Chart.js, CloudFront | Visualización, login PKCE | CDN |
| API | Lambda Python 3.13 arm64 | Consultas, ingesta *push*, gobierno | Concurrencia Lambda, throttling |
| Scheduler | Lambda | *Fan-out* de tareas por conector | 1 invocación/h |
| Collector | Lambda (consumidor SQS) | *Pull* a proveedores y escritura del ledger | Hasta `maximum_concurrency` |
| Budget | Lambda | Evaluación de presupuestos | 1 invocación/día |
| Cola | SQS estándar + DLQ | Amortiguar, reintentar, aislar fallas | Prácticamente ilimitada |
| Ledger | DynamoDB on-demand | Hechos, agregados, configuración | Automática |
| Identidad | Cognito | Usuarios, grupos, clientes M2M | Administrada |

## 3.3 Nivel 3: componentes (código Python)

```mermaid
flowchart TB
  subgraph handlers [handlers · adaptadores primarios]
    H1[api.py]
    H2[collector.py]
    H3[scheduler.py]
    H4[budget.py]
    BS[bootstrap.py<br/>Composition Root]
  end
  subgraph services [services · casos de uso]
    S1[ingestion.py<br/>SchedulePlanner · UsageCollector · UsageIngestor]
    S2[dashboard.py<br/>DashboardService · DateRange]
    S3[budgets.py<br/>BudgetEvaluator]
  end
  subgraph domain [domain · núcleo sin dependencias]
    D1[models.py<br/>UsageRecord · Metrics · Attribution]
    D2[ledger.py<br/>compute_deltas · is_noop]
    D3[ports.py<br/>UsageConnector · UsageRepository · ...]
  end
  subgraph connectors [connectors · adaptadores de proveedores]
    C0[registry.py]
    C1[anthropic_admin.py]
    C2[openai_admin.py]
    C3[aws_cost_explorer.py]
    C4[google_billing.py]
    C5[synthetic.py]
  end
  subgraph adapters [adapters · adaptadores secundarios]
    A1[dynamodb.py]
    A2[aws.py<br/>SQS · SNS · Secrets]
    A3[memory.py]
  end
  handlers --> services
  BS --> adapters
  services --> domain
  services --> C0
  C0 --> C1 & C2 & C3 & C4 & C5
  connectors --> D3
  adapters --> D3
  adapters --> D2
```

**Regla de dependencias:** las flechas apuntan hacia el dominio. `domain` no importa nada de
`services`, `adapters`, `handlers` ni de bibliotecas de AWS.

## 3.4 Vista de despliegue

```mermaid
flowchart TB
  subgraph Region [AWS us-east-1 · servicios regionales multi-AZ]
    subgraph Edge
      CF[CloudFront<br/>PriceClass_100]
    end
    S3[(S3 privado<br/>OAC)]
    APIGW[API Gateway HTTP]
    L[Lambda arm64 ×4<br/>+ layer de dependencias]
    Q[(SQS + DLQ)]
    D[(DynamoDB<br/>PITR)]
    C[Cognito]
    SM[Secrets Manager]
    EB[EventBridge Scheduler]
    CW[CloudWatch / X-Ray / SNS]
  end
  subgraph Payer [Cuenta payer de AWS Organizations]
    R[IAM role radar-gastos-cost-reader<br/>ExternalId]
    CE[Cost Explorer]
  end
  CF --> S3
  L -- sts:AssumeRole --> R --> CE
```

**Variante en AWS Academy Learner Lab (ADR-0017).** La cuenta del laboratorio no permite crear roles IAM ni usar
CloudFront o X-Ray, y admite como máximo 10 ejecuciones concurrentes de Lambda:

```mermaid
flowchart TB
  subgraph Lab [AWS Academy Learner Lab · us-east-1]
    APIGW2[API Gateway HTTP<br/>sirve también el dashboard]
    L2[Lambda arm64 ×4<br/>rol LabRole · concurrencia reservada 4+3+1+1]
    Q2[(SQS + DLQ<br/>consumidor máx. 3)]
    D2[(DynamoDB<br/>celdas en 8 shards)]
    C2[Cognito]
    SM2[Secrets Manager]
    EB2[EventBridge Scheduler<br/>rol LabRole]
    CW2[CloudWatch / SNS<br/>sin X-Ray]
  end
  Browser[Navegador] -- HTTPS --> APIGW2 --> L2
  L2 --> Q2 --> L2
  L2 --> D2
  L2 --> SM2
  EB2 --> L2
```

## 3.5 Vista dinámica: ingesta *push* con duplicado

```mermaid
sequenceDiagram
  autonumber
  participant X as Sistema externo
  participant G as API Gateway
  participant A as λ api
  participant Q as SQS
  participant C as λ collector
  participant D as DynamoDB
  X->>G: POST /v1/usage/records (JWT)
  G->>G: valida firma/aud/exp
  G->>A: evento v2 + claims
  A->>A: tenant ← claim; valida esquema
  A->>Q: SendMessageBatch (≤200 registros/msg)
  A-->>X: 202 {accepted, record_ids}
  Q->>C: lote (≤10 mensajes)
  loop por registro
    C->>D: GetItem(hecho, ConsistentRead)
    alt contenido idéntico
      C->>C: UNCHANGED (sin escritura)
    else nuevo o revisado
      C->>D: TransactWriteItems[Put hecho (version=v) + ADD Δ en 3 agregados]
      alt ConditionalCheckFailed / TransactionConflict
        C->>C: backoff con jitter y reintento
      end
    end
  end
  C-->>Q: batchItemFailures (solo los fallidos)
  Note over Q,C: Si el mensaje se entrega de nuevo, todos los registros salen UNCHANGED.
```

## 3.6 Vista dinámica: recolección *pull* horaria

```mermaid
sequenceDiagram
  participant E as EventBridge
  participant S as λ scheduler
  participant Q as SQS
  participant C as λ collector
  participant SM as Secrets Manager
  participant P as Proveedor
  participant D as DynamoDB
  E->>S: rate(1 hour)
  S->>D: Query CFG#CONNECTOR
  S->>Q: 1 tarea por conector [hoy-lookback, mañana)
  Q->>C: CollectTask
  C->>SM: GetSecretValue (caché 5 min)
  C->>P: GET uso + costo (paginado, reintentos 429/5xx)
  P-->>C: filas del proveedor
  C->>C: normaliza → UsageRecord (RecordBuilder)
  C->>D: upsert idempotente por registro
```
