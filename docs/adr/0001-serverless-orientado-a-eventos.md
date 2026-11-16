# ADR-0001: Arquitectura serverless orientada a eventos en AWS

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
La carga es muy irregular: ráfagas horarias de recolección, picos de ingesta *push* a fin de mes y lecturas
esporádicas del dashboard. El *driver* BD5 exige que la herramienta cueste poco frente al gasto que observa,
y el equipo es pequeño, sin capacidad para operar servidores.

## Decisión
Usar servicios administrados y *serverless*: API Gateway HTTP, Lambda, SQS, DynamoDB *on-demand*, EventBridge
Scheduler, Cognito y CloudFront. La comunicación entre la recepción y el procesamiento es asíncrona y pasa por SQS.

## Alternativas consideradas
| Opción | Por qué se descartó |
|---|---|
| ECS Fargate + RDS PostgreSQL | Costo fijo (ALB, RDS, NAT) de USD 60-100/mes incluso sin uso; obliga a escalar a mano. |
| EKS | La complejidad operativa es desproporcionada para el alcance. |
| Kinesis Data Streams | Ordenamiento por *shard* innecesario; costo por *shard*-hora; SQS basta para el volumen. |
| Step Functions para la recolección | Útil si hubiera flujos largos con varios pasos; aquí cada tarea es un único paso. |

## Consecuencias
- **+** Escala a cero (costo casi nulo en reposo) y escala horizontalmente sin planificar capacidad.
- **+** Alta disponibilidad multi-AZ heredada de los servicios administrados.
- **−** Arranques en frío (mitigados con arm64, *layer* liviano e importaciones diferidas).
- **−** Dependencia de AWS (*lock-in*), acotada por la arquitectura hexagonal (ADR-0002).
- **−** Límite de 15 min por invocación: los *backfills* largos se dividen en ventanas.
