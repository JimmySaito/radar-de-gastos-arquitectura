# UsageHub — Repositorio de arquitectura

Artefactos de **Arquitectura de Software**, **Arquitectura Empresarial** y **Gobierno de TI** de
UsageHub, una plataforma FinOps que centraliza el consumo de proveedores de IA (Anthropic/Claude,
OpenAI, Google Gemini) y de nube (AWS) con atribución por persona y equipo.

El código del prototipo vive en el repositorio [`usage-hub`](../usage-hub).

## Contenido

| # | Documento | Qué responde |
|---|---|---|
| 1 | [Contexto de negocio](docs/01-contexto-negocio.md) | Problema, interesados, *drivers*, alcance del PoC |
| 2 | [Atributos de calidad](docs/02-atributos-calidad.md) | Árbol de utilidad y 11 escenarios QAS con tácticas y evidencia |
| 3 | [Vistas C4](docs/03-vistas-c4.md) | Contexto, contenedores, componentes, despliegue y dinámica |
| 4 | [Decisiones (ADR)](docs/adr/README.md) | 12 decisiones con alternativas y consecuencias |
| 5 | [Arquitectura empresarial](docs/05-arquitectura-empresarial.md) | TOGAF ADM, capacidades, capas ArchiMate, *gap analysis* |
| 6 | [Gobierno de TI](docs/06-gobierno-ti.md) | COBIT 2019, FinOps Framework, ISO/IEC 38500, RACI, KPIs |
| 7 | [Modelo de datos](docs/07-modelo-datos.md) | Modelo canónico y patrones de acceso de DynamoDB |
| 8 | [Estrategia de pruebas](docs/08-estrategia-pruebas.md) | Pirámide de pruebas, plan de estrés, resultados |
| 9 | [Riesgos y deuda técnica](docs/09-riesgos-deuda.md) | Riesgos, puntos de sensibilidad y *trade-offs* (ATAM) |
| — | [Artículo](paper/paper.md) | Artículo científico del proyecto |

## Convenciones

- Diagramas como código en **Mermaid**: se versionan, se revisan en PR y GitHub los muestra sin herramientas extra.
- Decisiones en formato **ADR** (Nygard/MADR): una por archivo, inmutables. Si una decisión cambia, se escribe otra que la reemplaza.
- Escenarios de calidad con la plantilla de seis partes de Bass, Clements y Kazman (fuente, estímulo,
  artefacto, entorno, respuesta y medida de respuesta).
