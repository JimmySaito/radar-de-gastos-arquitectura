# ADR-0018: Entorno local equivalente a la nube como respaldo

- **Estado:** Aceptada · **Fecha:** 2026-11-20

## Contexto
El entorno local (`scripts/local_server.py`) ejecuta el mismo handler de la API con almacenamiento en archivos. Se
usaba para desarrollar y, tras perder el laboratorio de AWS (ADR-0017), pasó a ser el entorno de la presentación.
Tres diferencias con la nube causaron o habrían causado fallos:

1. Chart.js se cargaba desde un CDN: sin internet, el respaldo local no dibujaba gráficas.
2. En local no había CSP. En AWS la política `style-src 'self'` bloqueó los estilos en línea del dashboard y las
   barras de "Gasto por persona" quedaron vacías; en local se veían bien, así que el defecto pasó inadvertido.
3. La configuración hecha en local (conexiones, suscripciones, personas) había que rehacerla a mano en la nube.

## Decisión
1. **Sin dependencias externas en el navegador:** Chart.js se incluye en `frontend/vendor`, verificado contra su hash
   SRI y con su licencia; la CSP pasa a `script-src 'self'`.
2. **La misma CSP y cabeceras en local que en la nube:** el servidor local usa las cabeceras del módulo `web` de la
   API. Los estilos dinámicos se aplican desde JavaScript (permitido por la CSP) y una prueba automatizada impide
   reintroducir estilos o manejadores en línea.
3. **Migración entre entornos por puertos:** `services/migration.py` copia conexiones (sus credenciales pasan al
   almacén de secretos de destino), mapeos, presupuestos, licencias, suscripciones y personas entre cualquier par de
   repositorios. Es idempotente, tiene simulacro y nunca expone credenciales; no copia el historial de consumo, que el
   destino vuelve a leer de los proveedores.

## Alternativas consideradas
| Opción | Por qué no |
|---|---|
| CSP más permisiva (`'unsafe-inline'`) | Resuelve el síntoma debilitando la seguridad en la nube. |
| Emular AWS en local (LocalStack) | Mayor fidelidad de servicios, pero más pesado de operar y no resolvía la diferencia que causó el fallo: la CSP. |
| Exportar e importar la configuración con archivos | Expone credenciales en archivos intermedios. |

## Consecuencias
- **+** Un defecto de CSP o de dependencias externas aparece en desarrollo, no en la nube.
- **+** El respaldo local funciona sin internet (salvo la sincronización con los proveedores) y puede sostener la
  presentación con el mismo código.
- **+** Pasar de local a la nube toma segundos: se usó para migrar la configuración real a AWS.
- **−** La paridad es de la capa web y de la lógica, no de la infraestructura: concurrencia, colas y cuotas solo se
  observan en la nube (ADR-0015, ADR-0017).
