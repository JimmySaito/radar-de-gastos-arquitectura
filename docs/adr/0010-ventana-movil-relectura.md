# ADR-0010: Ventana móvil de relectura (*lookback*)

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
La Usage and Cost Analytics API de Anthropic publica datos con 4 a 24 h de retraso y los meses cerrados pueden
revisarse. OpenAI y AWS Cost Explorer tienen comportamientos similares (Cost Explorer se actualiza varias veces
al día). Leer solo "ayer" pierde las correcciones.

## Decisión
Cada hora, el scheduler pide a cada conector la ventana `[hoy − lookback_days, mañana)`, con `lookback_days = 3`
por defecto (configurable de 1 a 31 por conector). El ledger idempotente (ADR-0004) convierte la relectura en
escrituras solo de lo que cambió.

## Consecuencias
- **+** Converge a la cifra final del proveedor sin lógica especial de "cierre".
- **+** Un *backfill* es el mismo mecanismo con una ventana mayor.
- **−** Costo de las llamadas: Cost Explorer cobra USD 0,01 por solicitud (24 × 30 ≈ USD 7,2 al mes por conector
  con frecuencia horaria). Se puede bajar la frecuencia de AWS a 4 veces por día.
- **−** Cada registro releído cuesta al menos una lectura consistente aunque no haya cambiado (`UNCHANGED`). La
  proporción real de `UNCHANGED` se observa en la métrica `RecordsUnchanged` y es un indicador para ajustar `lookback_days`.
