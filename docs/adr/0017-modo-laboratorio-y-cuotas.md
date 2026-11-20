# ADR-0017: Modo laboratorio y cuotas de la plataforma en la infraestructura como código

- **Estado:** Aceptada · **Fecha:** 2026-11-20 · Adapta ADR-0001, ADR-0007 y ADR-0008 a cuentas restringidas

## Contexto
El prototipo debía desplegarse en AWS Academy Learner Lab, una cuenta con restricciones que el diseño original no
contemplaba (verificadas con llamadas de solo lectura y pruebas controladas):

- No se pueden crear roles IAM; existe un rol preparado, `LabRole`.
- CloudFront y X-Ray no están disponibles.
- Como máximo **10 entornos de ejecución de Lambda concurrentes** en toda la cuenta; superarlo desactiva la cuenta.

La primera versión del modo laboratorio resolvió los roles, CloudFront y X-Ray, pero no la cuota de concurrencia, que
estaba documentada en el *Readme* del laboratorio y no en los límites técnicos de la cuenta (400). Durante la segunda
prueba de estrés la API llegó a 64 ejecuciones simultáneas y el colector a 20, y la cuenta se desactivó con pérdida de
todos los recursos (sección 8.4.2). Un segundo laboratorio disponible no permite crear Lambda, DynamoDB, SQS, API
Gateway ni Cognito.

## Decisión
Un **modo laboratorio** que el script de despliegue activa al detectar la sesión `voclabs`, mediante tres variables de
Terraform y sin tocar el despliegue normal:

1. `lab_role_arn`: las funciones y EventBridge Scheduler usan `LabRole`; el módulo `lambda_function` acepta un rol
   existente en lugar de crear uno.
2. `frontend_hosting = "api"`: la propia API sirve el dashboard por HTTPS, con `config.json` generado y las mismas
   cabeceras de seguridad que CloudFront. `enable_cmk = false` y X-Ray en *PassThrough*.
3. **Cuotas como código:** concurrencia reservada por función (API 4, colector 3, horarios 1 + 1 = 9) y concurrencia
   máxima del consumidor SQS en 3. Bajo carga, el exceso se rechaza con 429/500 en lugar de superar la cuota. El
   generador de estrés se niega a ejecutarse en una cuenta de laboratorio sin una opción explícita.

## Alternativas consideradas
| Opción | Por qué no |
|---|---|
| Entorno de Terraform separado para el laboratorio | Duplica la infraestructura y deja que ambos entornos diverjan; las variables mantienen un único código. |
| Sitio estático en S3 sin CloudFront | Solo HTTP: Cognito exige HTTPS en las URL de retorno (salvo `localhost`). |
| Documentar la cuota y confiar en no superarla | Es lo que falló: una cuota que solo vive en un documento no protege nada. |
| Desplegar en EC2 en el segundo laboratorio | No es la arquitectura evaluada, sin Cognito ni HTTPS, y con las credenciales de proveedores en una máquina pública. |

## Consecuencias
- **+** El mismo código despliega en una cuenta normal o en el laboratorio; el laboratorio se detecta solo.
- **+** La cuota de concurrencia es imposible de superar por diseño, no por disciplina.
- **−** En el laboratorio el sistema escala mucho menos (9 ejecuciones): las pruebas de carga allí miden el
  comportamiento bajo rechazo, no el techo de la arquitectura.
- **−** Se pierden CloudFront (caché en el borde), la CMK propia y las trazas de X-Ray en ese modo.
- **Lección de gobierno de TI:** las cuotas y políticas de la plataforma son requisitos no funcionales del
  despliegue. Deben verificarse contra la documentación del proveedor, no solo contra lo que la API permite, y
  codificarse en la infraestructura como código.
