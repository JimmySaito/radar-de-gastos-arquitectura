# ADR-0007: Cognito (PKCE + client credentials) y aislamiento multi-tenant

- **Estado:** Aceptada · **Fecha:** 2026-11-16

## Contexto
Hay dos tipos de cliente: personas (dashboard) y sistemas (ingesta *push*). Varios tenants (unidades de negocio o
clientes) comparten la plataforma. La amenaza principal es el acceso cruzado entre tenants (OWASP API1:2023, BOLA).

## Decisión
- **Amazon Cognito**. Para personas: Authorization Code + **PKCE** (cliente público, sin secreto en el navegador),
  MFA TOTP opcional y alta solo por administradores. Para sistemas: **client credentials** con el scope
  `radar-gastos/ingest`.
- El atributo inmutable `custom:tenant_id` va en el id token. Para clientes M2M, la relación `client_id → tenant`
  es configuración del despliegue.
- El autorizador JWT de API Gateway valida firma, emisor, audiencia y expiración antes de invocar Lambda.
- **El tenant nunca proviene del cliente:** el cuerpo con `tenant_id` se rechaza (`extra="forbid"`) y todas las claves
  de datos llevan el prefijo `T#{tenant}`.
- Grupo `admins` para las operaciones de gobierno (conectores, mapeos, presupuestos).

## Alternativas
- *API keys de API Gateway (REST API + usage plans):* no identifican personas y requieren REST API (más costosa).
- *IdP corporativo (Entra ID/Okta) directo:* recomendado en producción; Cognito puede federarlo sin cambiar la API.
- *Autorizador Lambda propio:* más flexible, pero agrega latencia y código de seguridad propio.

## Consecuencias
- **+** Estándares abiertos (OAuth 2.0/OIDC) que cualquier sistema puede consumir (interoperabilidad).
- **+** El aislamiento se puede probar automáticamente (`test_tenant_isolation`).
- **−** El aislamiento es lógico (tabla compartida). Para clientes regulados se recomienda *silo* por cuenta o tabla
  (patrón *pool* → *silo* de AWS SaaS Lens) o IAM *fine-grained access control* con `dynamodb:LeadingKeys`.
