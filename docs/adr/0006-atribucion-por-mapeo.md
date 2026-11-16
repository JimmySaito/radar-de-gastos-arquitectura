# ADR-0006: Atribución por mapeo de principales (*showback*)

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
Los proveedores identifican el consumo con identidades técnicas heterogéneas:

| Proveedor | Identidad disponible en uso | Identidad disponible en costo |
|---|---|---|
| Anthropic | `actor` (usuario, service account, API key) | `actor` |
| OpenAI | `user_id`, `api_key_id`, `project_id` | solo `project_id`, `line_item` |
| AWS | tag de asignación de costos (`owner`) | igual |
| Google | etiqueta (`labels.owner`) o proyecto | igual |

El negocio necesita la vista "persona → equipo" (BD2).

## Decisión
- El conector conserva la identidad técnica en `principal` (`user:…`, `api_key:…`, `project:…`, `tag:…`).
- Una **regla de gobierno** `PrincipalMapping(provider, principal) → (member, team)`, administrada por el grupo
  `admins`, se resuelve **al ingerir**. Lo que no tiene mapeo queda como `member = principal` y `team = unassigned`.
- Para OpenAI, el costo se atribuye al proyecto y los tokens al usuario. El dashboard muestra ambos y la
  organización mapea proyectos a equipos.

## Consecuencias
- **+** Funciona con cualquier proveedor y separa la política (gobierno) de la integración (técnica).
- **+** El indicador "% de gasto `unassigned`" es una métrica de gobierno accionable.
- **−** Un cambio de mapeo no reatribuye la historia automáticamente: se aplica en la siguiente relectura de cada
  hecho (el ledger mueve el valor entre celdas, ADR-0004). Reatribuir meses cerrados requiere un *backfill* explícito.
- **−** En OpenAI, el costo por persona es una estimación (tokens × precio), no el dato facturado. Se documenta en el dashboard.
