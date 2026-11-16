# ADR-0008: Terraform con módulos reutilizables

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
La infraestructura debe ser reproducible, revisable en PR y replicable en entornos (dev, prod) y cuentas (payer).

## Decisión
- **Terraform** (≥ 1.9, proveedor AWS ~> 5.80) con estado remoto en S3 y bloqueo nativo.
- **Módulos** genéricos con interfaz explícita (`variables.tf` / `outputs.tf`): `lambda_function` (rol de mínimo
  privilegio, logs con retención, X-Ray, alarma de errores), `sqs_queue` (DLQ, cifrado, alarmas), `static_site`
  (S3 + CloudFront OAC + cabeceras de seguridad) y `cost_reader_role` (cuenta payer con ExternalId).
- Un directorio por entorno (`envs/dev`) que compone los módulos. `default_tags` para el *cost allocation*
  (la propia herramienta se autoobserva).
- CI: `terraform fmt -check`, `terraform validate` y `checkov`. Despliegue por OIDC, sin llaves estáticas.

## Alternativas
- *AWS CDK:* lenguaje general y *constructs* de alto nivel, pero exclusivo de AWS y su *plan* es menos legible para revisión.
- *AWS SAM:* excelente para Lambda, pero más limitado para Cognito, CloudFront y multi-cuenta.

## Consecuencias
- **+** Reutilización medible: `lambda_function` se instancia 4 veces y `sqs_queue` es independiente del dominio.
- **+** `terraform plan` como artefacto de revisión del cambio (gobierno de cambios, COBIT BAI06).
- **−** El empaquetado de Lambda ocurre fuera de Terraform (`scripts/build_lambda.py`), en un paso previo explícito.
