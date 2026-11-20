# Registro de decisiones de arquitectura (ADR)

| ADR | Título | Estado | Atributos |
|---|---|---|---|
| [0001](0001-serverless-orientado-a-eventos.md) | Arquitectura serverless orientada a eventos en AWS | Aceptada | Escalabilidad, Disponibilidad, Costo |
| [0002](0002-hexagonal-modelo-canonico.md) | Arquitectura hexagonal y modelo canónico de consumo | Aceptada | Modificabilidad, Testabilidad, Interoperabilidad |
| [0003](0003-dynamodb-single-table-cqrs.md) | DynamoDB *single-table* con agregados precalculados (CQRS) | Aceptada | Desempeño, Escalabilidad |
| [0004](0004-ledger-idempotente-occ.md) | Ledger idempotente con deltas y concurrencia optimista | Aceptada | Confiabilidad |
| [0005](0005-sqs-dlq-partial-batch.md) | SQS con DLQ y respuesta de lote parcial | Aceptada | Disponibilidad, Confiabilidad |
| [0006](0006-atribucion-por-mapeo.md) | Atribución por mapeo de principales (*showback*) | Aceptada | Gobierno, Modificabilidad |
| [0007](0007-cognito-multitenant.md) | Cognito (PKCE + client credentials) y aislamiento multi-tenant | Aceptada | Seguridad |
| [0008](0008-terraform-modular.md) | Terraform con módulos reutilizables | Aceptada | Reusabilidad, Mantenibilidad |
| [0009](0009-python-lambda-arm64-powertools.md) | Python 3.13 en Lambda arm64 con Powertools | Aceptada | Soportabilidad, Desempeño |
| [0010](0010-ventana-movil-relectura.md) | Ventana móvil de relectura (*lookback*) | Aceptada | Confiabilidad, Costo |
| [0011](0011-configuracion-autoservicio.md) | Configuración en autoservicio y separación datos reales / ejemplo | Aceptada | Usabilidad, Seguridad, Modificabilidad |
| [0012](0012-consumo-con-suscripcion.md) | Consumo con suscripción (Claude Code local y costos fijos) | Aceptada (reemplazada en parte por 0013) | Interoperabilidad, Confiabilidad |
| [0013](0013-espacios-empresa-personal.md) | Espacios Empresa y Personal con gastos recurrentes | Aceptada | Usabilidad, Seguridad, Modificabilidad |
| [0014](0014-personas-y-ejemplo-personal.md) | Personas en el espacio personal y ejemplo generado al vuelo | Aceptada | Usabilidad, Confiabilidad |
| [0015](0015-shards-celdas-agregadas.md) | Celdas agregadas repartidas en *shards* | Aceptada (implementa la evolución de 0004) | Escalabilidad, Confiabilidad |
| [0016](0016-lecturas-cardinalidad-acotada.md) | Lecturas del dashboard con cardinalidad acotada | Aceptada | Desempeño, Escalabilidad |
| [0017](0017-modo-laboratorio-y-cuotas.md) | Modo laboratorio y cuotas de la plataforma como código | Aceptada | Disponibilidad, Seguridad, Gobierno |
| [0018](0018-paridad-local-nube.md) | Entorno local equivalente a la nube como respaldo | Aceptada | Disponibilidad, Testabilidad, Seguridad |

Plantilla: Contexto → Decisión → Alternativas consideradas → Consecuencias (+/−).
