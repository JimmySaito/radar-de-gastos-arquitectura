# 1. Contexto de negocio

## 1.1 Problema

Las organizaciones adoptan varios proveedores de IA generativa al mismo tiempo: Claude en ingeniería,
ChatGPT en producto, Gemini en analítica y modelos en Amazon Bedrock en producción. Cada proveedor
factura en su consola, con su unidad (tokens, requests, horas) y su granularidad de identidad (API key,
usuario, proyecto, cuenta). Esto produce tres fallas de gobierno:

1. **Visibilidad fragmentada.** Nadie puede responder en un minuto "¿cuánto gastamos en IA este mes y en qué?".
2. **Atribución imposible.** El gasto queda asociado a llaves técnicas, no a personas, equipos ni centros de costo.
   Sin atribución no hay *showback* ni *chargeback*.
3. **Control reactivo.** Los excesos se descubren al llegar la factura. No hay presupuestos ni alertas tempranas.

## 1.2 Visión

> Un único punto de verdad, gobernado y extensible, sobre el consumo de servicios de IA y nube.
> Cualquier persona puede consultarlo y cada dólar queda atribuido a un responsable.

## 1.3 Interesados y preocupaciones

| Interesado | Preocupación principal | Atributo de calidad dominante |
|---|---|---|
| CFO / Finanzas | Costo total y por centro de costo, cierre mensual exacto | Confiabilidad (exactitud) |
| Líder FinOps | Atribución, presupuestos, alertas | Disponibilidad, Interoperabilidad |
| Líder de equipo | ¿Quién de mi equipo consume y en qué modelo? | Desempeño (dashboard), Usabilidad |
| CISO | Custodia de llaves Admin y aislamiento entre unidades de negocio | Seguridad |
| Plataforma / SRE | Operación con poco esfuerzo, costo de la propia herramienta | Escalabilidad, Soportabilidad |
| Equipo de desarrollo | Agregar proveedores sin romper lo existente | Modificabilidad, Testabilidad, Reusabilidad |

## 1.4 *Business drivers*

| ID | *Driver* | Indicador |
|---|---|---|
| BD1 | Reducir el tiempo para conocer el gasto consolidado | De días (conciliación manual) a menos de 1 minuto |
| BD2 | Atribuir al menos 95 % del gasto a un equipo | % del costo con `team ≠ unassigned` |
| BD3 | Detectar desvíos de presupuesto antes del cierre | Alertas al 50, 80 y 100 % del presupuesto mensual |
| BD4 | Incorporar un proveedor nuevo en menos de 1 semana | Esfuerzo medido en archivos y componentes tocados |
| BD5 | Que la herramienta cueste menos del 1 % del gasto que observa | Costo AWS mensual / gasto observado |

## 1.5 Alcance del prototipo (PoC)

**Dentro:** conectores de Anthropic, OpenAI, AWS Cost Explorer y Google (Billing Export) más un sintético; ingesta
*push* genérica; ledger idempotente; dashboard; mapeo de identidades; presupuestos y alertas; despliegue en AWS
con Terraform; pruebas de estrés.

**Fuera:** facturación interna (*chargeback* contable), detección de anomalías con ML, recomendaciones de
optimización, SSO corporativo con SAML/OIDC externo, multi-moneda con tipos de cambio.

## 1.6 Restricciones

- Nube objetivo: **AWS** (requisito del curso).
- Credenciales de proveedores de **solo lectura** (Admin keys de uso/costos).
- Latencia propia de los proveedores: los datos llegan con 4-24 h de retraso y se revisan. El sistema
  no puede ser más fresco que su fuente.
