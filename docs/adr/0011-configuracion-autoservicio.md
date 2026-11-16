# ADR-0011: Configuración en autoservicio y separación datos reales / ejemplo

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
El prototipo inicial solo mostraba datos sintéticos, y registrar un conector exigía crear el secreto a mano en
Secrets Manager y llamar a la API con su ARN. Eso no es usable por un líder FinOps sin perfil técnico. Además,
mezclar datos de demostración con los reales confunde y pone en riesgo la confianza en las cifras (P1, "una
sola verdad del consumo").

## Decisión
1. **Dos conjuntos de datos aislados:** *Datos reales* (el tenant del token) y *Ejemplo* (tenant `demo`). El
   ejemplo se lee con `?dataset=demo`, es de solo lectura y no permite escribir: toda escritura usa el tenant del token.
2. **Pantalla de Configuración** (grupo `admins`): conexiones, personas y equipos, presupuestos e ingesta por API.
3. **Formulario dirigido por catálogo:** `GET /v1/providers` describe los campos de cada proveedor (etiqueta, tipo,
   obligatoriedad, si es secreto, ayuda). La UI se genera a partir de él, así que un proveedor nuevo no toca el frontend (QAS-M1).
4. **Custodia de credenciales detrás de un puerto `SecretStore`:** en AWS, Secrets Manager con el nombre
   `usagehub/{tenant}/{conexión}` (IAM restringido a ese prefijo y borrado con ventana de recuperación de 7 días);
   en local, archivos en `~/.usagehub` fuera del repositorio. **Los valores secretos nunca se devuelven**: la UI
   solo sabe qué campos están definidos y un campo vacío conserva el valor guardado.
5. **"Probar conexión" sin efectos:** lee los últimos 3 días del proveedor sin escribir en el ledger. Los errores
   se depuran (se enmascaran las credenciales y se acota el largo) antes de mostrarse.
6. **Estado operativo visible:** el colector registra en cada conexión el último sync (éxito o error, registros y
   ventana). Así se reduce el tiempo de diagnóstico sin abrir CloudWatch (QAS-SU1).
7. **Gobierno guiado:** `GET /v1/identities` lista las identidades técnicas con gasto, con las no asignadas primero
   y el % de cobertura de atribución (KPI de gobierno, BD2).

## Alternativas
- *Configurar solo por IaC o CLI:* reproducible, pero excluye a usuarios de negocio.
- *Devolver las llaves enmascaradas parcialmente (p. ej. `sk-…abcd`):* útil para identificarlas, pero filtra
  información. Se prefirió no devolver nada; el usuario las distingue por el nombre de la conexión.
- *Formularios codificados por proveedor en el frontend:* más simples al inicio, pero rompen el principio Open/Closed.

## Consecuencias
- **+** La herramienta pasa de demostración a producto usable: alta de una fuente en menos de 2 minutos sin consola de AWS.
- **+** La superficie de seguridad queda acotada y probada: tenant derivado del token, secretos write-only y errores depurados.
- **−** El Lambda de la API ahora necesita permisos de escritura en Secrets Manager (acotados al prefijo) y acceso
  saliente a los proveedores para "Probar conexión", y su timeout sube a 29 s.
- **−** En local, las credenciales quedan en archivos de texto en el perfil del usuario (con permisos 0600 en POSIX).
  Es aceptable para uso individual; en equipos se debe usar el despliegue en AWS.
