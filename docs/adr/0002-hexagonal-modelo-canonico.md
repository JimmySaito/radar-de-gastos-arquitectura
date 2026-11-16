# ADR-0002: Arquitectura hexagonal y modelo canónico de consumo

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
Cada proveedor expone el consumo de forma distinta: Anthropic agrupa por `actor` y entrega el costo en centavos;
OpenAI separa tokens (por usuario) de costos (por proyecto); AWS usa *cost allocation tags*; Google, filas de
facturación en BigQuery. Los proveedores cambian sus APIs con frecuencia (Anthropic reemplazó sus reportes en 2026).
Además, se quiere probar el núcleo sin la nube.

## Decisión
1. **Modelo canónico** `UsageRecord` (Canonical Data Model, Hohpe y Woolf): hecho diario inmutable con identidad
   natural `(tenant, provider, service, principal, usage_date)` y métricas aditivas.
2. **Puertos y adaptadores** (Cockburn): el dominio define `UsageConnector`, `UsageRepository`,
   `MappingRepository`, `SecretProvider`, `WorkQueue` y `AlertPublisher`. Las implementaciones de AWS y las
   de memoria son intercambiables.
3. **Strategy + Registry** para conectores: `@register(Provider.X)` con carga perezosa del módulo.

## Alternativas consideradas
- *Arquitectura en capas acoplada a boto3:* más simple al inicio, pero impide probar sin AWS y acopla al proveedor.
- *Esquema por proveedor (sin modelo canónico):* evita transformar datos, pero multiplica las consultas y el
  dashboard por cada proveedor (N×M).

## Consecuencias
- **+** Un proveedor nuevo es 1 módulo y 1 registro (QAS-M1). Un cambio de API de un proveedor queda confinado a su adaptador.
- **+** El 100 % de la lógica de dominio y de casos de uso se prueba en memoria (QAS-T1).
- **−** El modelo canónico pierde detalle específico (p. ej. `service_tier`, `inference_geo`). Se acepta porque el
  objetivo es gobierno de costos, no análisis de rendimiento.
- **−** Hay más indirección (interfaces) que en un diseño monolítico.
