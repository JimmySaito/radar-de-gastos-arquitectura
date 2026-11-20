# ADR-0015: Celdas agregadas repartidas en *shards*

- **Estado:** Aceptada · **Fecha:** 2026-11-20 · Implementa la evolución prevista en ADR-0004

## Contexto
ADR-0004 identificó un punto de sensibilidad (S1): los conflictos del control de concurrencia optimista crecen
cuando muchos colectores actualizan la misma celda agregada. La prueba de estrés en AWS lo cuantificó (sección 8.4):
todos los registros de una corrida compartían día, equipo y servicio, así que cada transacción actualizaba los mismos
dos ítems. Con 20 colectores en paralelo hubo 24.262 reintentos en 2 minutos, el ledger se limitó a unos 100
registros/s frente a 250 de llegada, la cola acumuló *backlog* y los datos tardaron 7 a 8 minutos en reflejarse. La
exactitud se mantuvo; la frescura no.

## Decisión
1. Cada celda agregada se reparte en `N` *shards* (`AGGREGATE_SHARDS`, 8 en AWS). El *shard* se agrega al final del
   SK (`…#{valor}#~{n}`); el *shard* 0 no lleva sufijo, de modo que con `N = 1` las claves son las de siempre.
2. Un hecho escribe **siempre en el mismo shard**, `n = sha256(record_id) mod N`. Sus revisiones y reatribuciones
   restan y suman sobre las mismas celdas, y `compute_deltas` no cambia: el reparto es un detalle del adaptador.
3. La lectura suma los *shards* de cada celda. El valor de la dimensión se guarda como atributo (`agg_value`) para no
   depender del formato del SK; las celdas antiguas, sin ese atributo, se siguen leyendo.

## Alternativas consideradas
| Opción | Por qué no |
|---|---|
| Subir la concurrencia del colector | Más colectores sobre las mismas celdas aumentan los conflictos; es el problema, no la solución. |
| Agregar con DynamoDB Streams y un único escritor por celda | Serializa por diseño, pero añade un componente, latencia y otra fuente de entrega al-menos-una-vez que también exige idempotencia (ADR-0004). |
| *Shard* aleatorio por escritura | Reparte igual, pero una revisión podría restar en un *shard* distinto del que sumó: rompe la exactitud. |
| Recalcular agregados por lotes | Exacto, pero no inmediato y caro de reconstruir. |

## Consecuencias
- **+** Medido en AWS con la misma carga: conflictos −69 a −86 %, cola sin *backlog*, datos visibles en 10 a 17 s,
  ledger de ≈ 245 registros/s en el pico, cero lotes agotando reintentos y costo exacto en las tres corridas.
- **+** Compatible hacia atrás: no requiere migrar datos ni cambiar el dominio.
- **−** Una celda caliente ocupa hasta `N` ítems: las lecturas de esa celda leen hasta `N` veces más ítems. Es
  despreciable para equipos y servicios (pocas celdas) y no afecta a personas (cada una suele tener pocos hechos).
- **±** `N` puede cambiarse entre despliegues sin migrar datos: si un hecho escrito con el `N` anterior se revisa
  después, su delta cae en otro *shard* y uno de ellos puede quedar con valores negativos, pero la lectura suma todos
  los *shards* y el total es exacto (prueba `test_changing_the_number_of_shards_keeps_totals_exact`). Lo que no debe
  hacerse es leer *shards* sueltos.
