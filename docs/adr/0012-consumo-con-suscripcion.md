# ADR-0012: Consumo con suscripción (Claude Code local y costos fijos)

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
Una parte creciente del uso de IA no pasa por APIs facturadas por token, sino por **suscripciones**: claude.ai,
Claude Code con planes Pro/Max, ChatGPT Plus/Team o Gemini. La Usage and Cost Analytics API de Anthropic solo
cubre organizaciones de Claude Console y Claude Enterprise; para cuentas individuales devuelve 404. Lo verificamos
en el prototipo: la organización "Individual Org" obtuvo 404 en la API de analítica y 403 en los reportes *legacy*.
Ignorar este consumo deja un punto ciego en la visión centralizada (P1).

## Decisión
1. **Conector "Claude Code (este equipo)"** (`Provider.CLAUDE_CODE`): lee las sesiones JSONL de `~/.claude/projects`,
   donde cada respuesta trae modelo y `usage`.
   - Deduplica por `message.id` + `requestId`: una respuesta transmitida en *streaming* aparece en varias líneas.
     En la prueba real, 544 líneas se redujeron a 206 respuestas únicas.
   - Calcula un **costo equivalente en API** con una tabla de precios versionada (`connectors/pricing.py`), que
     contempla escritura y lectura de caché y *fast mode*.
2. **Proveedor separado** para Claude Code: el costo **estimado** no se mezcla con el **facturado** de Anthropic, y
   el dashboard lo rotula "(estimado)".
3. **Conector "Suscripción (costo fijo)"**: prorratea la tarifa mensual por día y la registra bajo el proveedor real
   (p. ej. `anthropic`, servicio "Claude Max (suscripción)"). Así aparece en las mismas series, presupuestos y rankings.
4. **Centralización en equipos** mediante `scripts/push_claude_code.py`: cada persona envía su consumo a la API de
   ingesta, que es idempotente (reenviar no duplica). La alternativa empresarial es la telemetría OpenTelemetry de
   Claude Code reenviada a la misma API.

## Alternativas
- *Leer el consumo de claude.ai web:* no existe API para planes individuales. Solo se registra la tarifa del plan.
- *Reportar los tokens de Claude Code sin costo:* pierde comparabilidad con el resto de proveedores.
- *Mezclar el costo estimado con el de Anthropic:* falsearía la conciliación con la factura (KPI de exactitud).

## Consecuencias
- **+** Visibilidad del uso por suscripción, que antes era invisible, con tokens exactos por modelo y día.
- **+** El gasto real del plan entra en presupuestos y *showback*.
- **−** El costo de Claude Code es una estimación que depende de que la tabla de precios esté actualizada (deuda:
  actualizarla al cambiar las tarifas).
- **−** El formato de los registros locales de Claude Code no es un contrato público y puede cambiar. El parser es
  tolerante (ignora líneas inválidas) y su prueba de contrato fija el formato esperado.
- **−** El conector local solo funciona donde están los archivos. En la nube, el camino es el script de *push*.
