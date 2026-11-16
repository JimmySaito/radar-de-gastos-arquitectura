# ADR-0009: Python 3.13 en Lambda arm64 con Powertools

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
Hay SDKs oficiales de todos los proveedores en Python (`anthropic`, `boto3`, `google-cloud-bigquery`); OpenAI se
consume por REST con `httpx`. El equipo domina Python. Se necesita observabilidad homogénea con poco código.

## Decisión
- Python 3.13 en **Graviton (arm64)**: alrededor de 20 % menos costo por GB-s y mejor relación precio/rendimiento.
- **Pydantic v2** para validar en los bordes (API, mensajes, conectores).
- **AWS Lambda Powertools:** logs JSON con correlación, métricas EMF sin llamadas síncronas a CloudWatch, trazas
  X-Ray, enrutador HTTP y procesamiento de lotes parciales.
- Calidad estática: `mypy --strict` y `ruff`.

## Consecuencias
- **+** La soportabilidad sale de serie (QAS-SU1); las métricas de negocio cuestan 0 llamadas a la API.
- **+** El tipado estricto detecta errores de integración con los SDK. Por ejemplo, reveló los valores válidos de
  `actor_types` del SDK de Anthropic.
- **−** El arranque en frío de Python con Pydantic ronda 300-800 ms. Se mitiga con importaciones diferidas de los
  SDK de proveedores y con más memoria en la API.
