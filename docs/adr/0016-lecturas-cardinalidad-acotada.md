# ADR-0016: Lecturas del dashboard con cardinalidad acotada

- **Estado:** Aceptada · **Fecha:** 2026-11-20 · Complementa ADR-0003

## Contexto
ADR-0003 precalcula agregados por dimensión (persona, equipo, servicio) para que el dashboard no recorra hechos. La
prueba de estrés en AWS mostró que eso no basta cuando una dimensión tiene cardinalidad alta: el resumen
(`/v1/summary`) calculaba el total y el top de personas leyendo **todas** las celdas del agregado por persona, y
`/v1/timeseries` usaba esa misma dimensión para la serie por proveedor. Con 29.150 personas en un mes, las lecturas
tuvieron p95 de 2 a 12 s y la alarma de latencia se disparó. Una caché corta por instancia no compensó: la API escaló
a unas 60 instancias y cada una empezaba con la caché vacía.

## Decisión
1. **El total y el desglose por proveedor salen de la dimensión de equipos.** Cada hecho suma exactamente una vez en
   cada dimensión, así que el total es el mismo, y los equipos son pocos.
2. **El top de personas va en su propia ruta** (`/v1/summary/members`). El resumen solo lee equipos y servicios; el
   dashboard pide el top en paralelo y llena esa tarjeta cuando llega, sin bloquear el resto.
3. **La serie diaria por proveedor usa la dimensión de equipos**, no la de personas.
4. **Caché corta de lecturas en la API** (`READ_CACHE_SECONDS`, 15 s): absorbe consultas repetidas del mismo tenant,
   rango y dimensión. La escritura no pasa por ella.

## Alternativas consideradas
| Opción | Por qué no |
|---|---|
| Vista materializada del top-N (tarea programada) | Mantiene el contrato de la API, pero añade un componente, retraso de hasta un minuto y su propia operación. Queda como evolución si el top de personas también debe ser instantáneo. |
| Caché compartida (ElastiCache, DAX) | Resuelve las cachés frías por instancia, pero con costo fijo y otra pieza que operar; desproporcionado para el prototipo. |
| Limitar el top a las personas mapeadas | Cambia la semántica: el gasto sin asignar es justo lo que el top debe revelar (ADR-0006). |

## Consecuencias
- **+** El resumen lee un número constante de celdas: 6 con cualquier cantidad de personas (medido en local:
  antes 60.006 con 60.000 personas). El coste lineal queda aislado en una petición que no bloquea la pantalla.
- **+** El contrato cambia de forma explícita y documentada (OpenAPI); el resto del resumen no cambia.
- **−** Una petición más por carga del dashboard, y la tarjeta del top de personas aparece un instante después.
- **−** El top de personas sigue siendo O(n) en la cardinalidad. Si llega a ser un problema, la evolución es la vista
  materializada.
- **−** La latencia en AWS con esta corrección quedó pendiente de medir (el laboratorio se desactivó, ADR-0017).
