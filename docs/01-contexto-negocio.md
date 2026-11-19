# 1. Contexto de negocio

## 1.1 Problema

El gasto en tecnología llega hoy por dos vías que rara vez se miran juntas:

- **Consumo variable.** Las organizaciones usan varios proveedores de IA generativa al mismo tiempo (Claude en
  ingeniería, ChatGPT en producto, Gemini en analítica, modelos en Amazon Bedrock en producción) y servicios de
  nube. Cada proveedor factura en su consola, con su unidad (tokens, solicitudes, horas) y su granularidad de
  identidad (API key, usuario, proyecto, cuenta).
- **Suscripciones de precio fijo.** Licencias SaaS que compran las áreas de negocio sin pasar por TI, planes de IA
  pagados con tarjeta corporativa y, en el hogar, streaming, música, almacenamiento o asistentes de IA que se
  renuevan solos.

Esto produce cuatro fallas de gobierno, tanto en la empresa como en el hogar:

1. **Visibilidad fragmentada.** Nadie puede responder en un minuto "¿cuánto gastamos este mes en tecnología, en qué
   y quién?". La suma total no existe en ningún lugar.
2. **Atribución imposible.** El gasto queda asociado a llaves técnicas o a una tarjeta, no a personas, equipos,
   centros de costo o miembros del hogar. Sin atribución no hay *showback* ni *chargeback*.
3. **Control reactivo.** Los excesos y las renovaciones se descubren cuando llega el cobro. No hay presupuestos,
   alertas tempranas ni calendario de próximos pagos.
4. **Desperdicio invisible.** Licencias sin uso, suscripciones duplicadas entre áreas o personas y planes de IA
   pagados a la vez por suscripción y por API solo se detectan al comparar fuentes lado a lado.

La revisión de literatura del artículo (sección 2) documenta la magnitud del problema y por qué consolidar es una
condición del gobierno y no una comodidad.

## 1.2 Visión

> Un único punto de verdad, gobernado y extensible, sobre el gasto tecnológico recurrente —consumo de IA y nube,
> licencias y suscripciones— de una organización y de un hogar. Cada cobro queda atribuido a un responsable y
> ninguno llega por sorpresa.

## 1.3 Evolución del alcance

El proyecto empezó como un tablero del consumo de IA y nube por miembro del equipo. Al conectarlo con cuentas
reales aparecieron dos límites: buena parte del uso de IA se paga por planes de suscripción cuyo consumo los
proveedores no exponen por API (ADR-0012), y los usuarios querían ver el resto de sus cobros recurrentes. El
alcance se amplió en dos espacios: **Empresa** y **Personal** (ADR-0013), y después se añadieron personas
dentro del hogar (ADR-0014).

| Dimensión | Alcance inicial | Alcance actual |
|---|---|---|
| Qué se mide | Consumo variable de IA y nube | Consumo variable y suscripciones de precio fijo |
| Para quién | Equipos de una organización | Organizaciones (Empresa) y hogares (Personal) |
| Atribución | Persona y equipo | Persona y equipo; miembros del hogar con cobros compartidos |
| Horizonte | Gasto ocurrido | Gasto ocurrido y cobros próximos |

El núcleo (ledger idempotente, modelo canónico, arquitectura hexagonal) no cambió: lo nuevo se agregó como un dominio
independiente detrás de sus propios puertos.

## 1.4 Interesados y preocupaciones

| Interesado | Preocupación principal | Atributo de calidad dominante |
|---|---|---|
| CFO / Finanzas | Costo total y por centro de costo, cierre mensual exacto | Confiabilidad (exactitud) |
| Líder FinOps | Atribución, presupuestos, alertas | Disponibilidad, Interoperabilidad |
| Gestor de activos de TI / Compras | Licencias vigentes, usuarios por licencia, renovaciones | Confiabilidad, Usabilidad |
| Líder de equipo | ¿Quién de mi equipo consume y en qué modelo? | Desempeño (dashboard), Usabilidad |
| Persona u hogar | ¿Cuánto pago al mes, cuándo me cobran y cuánto corresponde a cada uno? | Usabilidad, Seguridad (privacidad) |
| CISO | Custodia de llaves Admin, aislamiento entre unidades de negocio y privacidad de los datos personales | Seguridad |
| Plataforma / SRE | Operación con poco esfuerzo, costo de la propia herramienta | Escalabilidad, Soportabilidad |
| Equipo de desarrollo | Agregar proveedores y dominios sin romper lo existente | Modificabilidad, Testabilidad, Reusabilidad |

## 1.5 *Business drivers*

| ID | *Driver* | Indicador |
|---|---|---|
| BD1 | Reducir el tiempo para conocer el gasto consolidado | De días (conciliación manual) a menos de 1 minuto |
| BD2 | Atribuir al menos 95 % del gasto a un equipo | % del costo con `team ≠ unassigned` |
| BD3 | Detectar desvíos de presupuesto antes del cierre | Alertas al 50, 80 y 100 % del presupuesto mensual |
| BD4 | Incorporar un proveedor nuevo en menos de 1 semana | Esfuerzo medido en archivos y componentes tocados |
| BD5 | Que la herramienta cueste menos del 1 % del gasto que observa | Costo AWS mensual / gasto observado |
| BD6 | Que ningún cobro recurrente llegue por sorpresa | Próximos cobros visibles con al menos 30 días de anticipación; equivalente mensual y proyección anual por moneda |

## 1.6 Alcance del prototipo (PoC)

**Dentro:** conectores de Anthropic, OpenAI, AWS Cost Explorer y Google (Billing Export), uso local de Claude Code y
un conector sintético; ingesta *push* genérica; ledger idempotente; dashboard; mapeo de identidades; presupuestos y
alertas; licencias SaaS de la empresa; suscripciones personales con catálogo de servicios, calendario de cobros,
personas del hogar y reparto de cobros compartidos; vistas de ejemplo; despliegue en AWS con Terraform y entorno
local equivalente; pruebas de estrés.

**Fuera:** facturación interna (*chargeback* contable), detección de anomalías con ML, recomendaciones de
optimización, SSO corporativo con SAML/OIDC externo, conversión entre monedas, detección automática de
suscripciones en cuentas bancarias o correos, y medición del consumo de planes de suscripción que los proveedores no
exponen por API.

## 1.7 Restricciones

- Nube objetivo: **AWS** (requisito del curso).
- Credenciales de proveedores de **solo lectura** (Admin keys de uso/costos).
- Latencia propia de los proveedores: los datos llegan con 4-24 h de retraso y se revisan. El sistema
  no puede ser más fresco que su fuente.
- Los datos del espacio Personal son privados de cada usuario: ni otros miembros del mismo tenant pueden leerlos.
