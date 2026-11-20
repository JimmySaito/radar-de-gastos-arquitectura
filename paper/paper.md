---
title: "Radar de gastos: arquitectura serverless con un ledger idempotente para consolidar el gasto tecnológico recurrente, del consumo de IA y nube a las suscripciones"
author:
  - "Jimmy Arturo Mancera Cuesta — Escuela Colombiana de Ingeniería Julio Garavito"
date: "Noviembre de 2026"
lang: es
---

# Resumen

Las organizaciones y las personas pagan hoy tecnología por dos vías que rara vez se miran juntas: el **consumo
variable** de modelos de lenguaje (Anthropic, OpenAI, Google) y de servicios de nube (AWS), y las **suscripciones de
precio fijo** (licencias SaaS, herramientas de IA, streaming, almacenamiento). Cada proveedor reporta con unidades,
identidades, monedas y calendarios distintos, lo que impide responder con oportunidad cuánto se gasta, en qué, quién y
cuándo llega el próximo cobro. Este trabajo presenta **Radar de gastos**, una plataforma que consolida ambas vías en
un solo instrumento con dos espacios: **Empresa**, que atribuye el consumo a personas y equipos, controla presupuestos
e inventaria licencias, y **Personal**, que proyecta el calendario de cobros de un hogar y reparte las suscripciones
compartidas entre sus miembros. El alcance nació centrado en el consumo de IA y nube y se amplió durante el diseño,
siguiendo la misma tendencia que la literatura de FinOps (*Cloud+*). La contribución técnica central es un **ledger idempotente basado en deltas** sobre
Amazon DynamoDB: combina claves naturales deterministas, transacciones atómicas y control de concurrencia optimista
para garantizar un efecto *exactamente-una-vez* sobre los agregados, aunque la mensajería entregue *al-menos-una-vez*
y los proveedores revisen sus cifras durante horas. La solución se diseñó con arquitectura hexagonal, CQRS y un
estilo serverless orientado a eventos en AWS, se documentó con el modelo C4 y ADR, y se alineó con TOGAF, COBIT 2019,
ISO/IEC 38500 y el FinOps Framework. La evaluación combina 153 pruebas automatizadas (96,5 % de cobertura),
pruebas basadas en propiedades, pruebas de estrés locales y en AWS con inyección de 15 % de mensajes duplicados y
una caída controlada del despliegue en AWS. En todos los escenarios medidos, también en la nube con el ledger
saturado, el costo agregado coincidió exactamente con el costo real; tras la caída los datos quedaron intactos y el servicio se recuperó sin intervención, y la prueba reveló
cuatro debilidades de observabilidad que se corrigieron.

**Palabras clave:** FinOps, gobierno de TI, gestión de suscripciones, SaaS, arquitectura serverless, idempotencia, CQRS, arquitectura hexagonal, AWS, IA generativa.

# Abstract

Organizations and individuals pay for technology through two channels that are seldom viewed together: variable
consumption of large language models and cloud services, and fixed-price subscriptions (SaaS licenses, AI tools,
streaming, storage). Each vendor reports with different units, identities, currencies and billing calendars. We
present Radar de gastos, a platform that consolidates both channels in a single instrument with two spaces: a
business space that attributes consumption to people and teams, enforces budgets and inventories licenses, and a
personal space that projects a household's billing calendar and splits shared subscriptions among its members. The
scope started with AI and cloud consumption and was broadened during design, mirroring the *Cloud+* trend in the
FinOps literature. Its core is an idempotent,
delta-based ledger on Amazon DynamoDB that guarantees exactly-once effects on aggregates despite at-least-once
delivery and provider-side revisions, using deterministic natural keys, atomic transactions and optimistic concurrency
control. The prototype follows hexagonal architecture, CQRS and an event-driven serverless style on AWS, and is aligned
with TOGAF, COBIT 2019, ISO/IEC 38500 and the FinOps Framework. Property-based and stress tests with 15 % injected
duplicates show zero aggregation error.

# 1. Introducción

La adopción de IA generativa en las empresas ha pasado de pilotos aislados a un consumo transversal y multiproveedor.
Un mismo departamento de ingeniería puede usar Claude para programar, un modelo de OpenAI en un producto y Gemini en
analítica, todo sobre una plataforma de nube con su propia facturación. Desde la perspectiva de **gobierno de TI**,
esta fragmentación produce tres problemas: (i) no existe una visión consolidada y oportuna del gasto; (ii) el costo
queda asociado a identidades técnicas (API keys, proyectos, cuentas) y no a responsables de negocio, lo que impide el
*showback* y el *chargeback*; y (iii) el control es reactivo, porque los excesos se descubren con la factura.

La disciplina **FinOps** propone un modelo operativo de responsabilidad compartida sobre el costo variable de la
tecnología, organizado en las fases *Inform*, *Optimize* y *Operate* [7], [8]. Su primera capacidad es entender el uso
y el costo: ingerir, normalizar y asignar los datos. Esa capacidad plantea un desafío de **arquitectura de software**
poco tratado en la literatura de FinOps: los datos de consumo llegan con retraso (4 a 24 h en el caso de Anthropic
[20]), pueden revisarse después de publicados, y se procesan sobre infraestructura de mensajería que, por diseño,
entrega mensajes al menos una vez. Si se suman ingenuamente, el gasto reportado se infla. En un sistema financiero,
un error de agregación no es un detalle de implementación: compromete la confianza en todo el instrumento de gobierno.

El consumo variable, sin embargo, es solo una parte del gasto tecnológico. Junto a él crecen las **suscripciones de
precio fijo**: licencias SaaS que compran las áreas de negocio sin pasar por TI, herramientas de IA pagadas con
tarjeta corporativa y, en el plano personal, servicios de streaming, música, almacenamiento o asistentes de IA que
se renuevan solos. En 2026, las unidades de negocio controlaban el 81 % del gasto SaaS de las organizaciones
analizadas por Zylo y ChatGPT era la aplicación más reembolsada como gasto [32]; en el hogar, los consumidores
estiman su gasto mensual en suscripciones en menos de la mitad de lo que realmente pagan [33]. Que el gasto esté
repartido en muchos cobros pequeños y automáticos no lo hace menor: lo hace **invisible**.

## 1.1 Alcance y su evolución

El proyecto comenzó con un alcance acotado: un tablero centralizado del consumo de servicios de IA (Claude, Gemini,
ChatGPT) y de nube (AWS) por miembro del equipo. Durante la construcción, al conectar cuentas reales, se hicieron
evidentes dos límites de ese planteamiento. Primero, buena parte del uso de IA no pasa por APIs medibles sino por
**planes de suscripción** (claude.ai, ChatGPT Plus, Claude Code con planes Pro o Max), cuyo costo es fijo y cuyo
consumo los proveedores no exponen de forma programática (ADR-0012). Segundo, quienes evaluaban el prototipo
preguntaban por el resto de sus cobros recurrentes, corporativos y personales, porque la pregunta que les importaba
no era "¿cuántos tokens usé?" sino "¿cuánto se me va al mes y cuándo me cobran?".

El alcance se amplió, por tanto, del **consumo de IA y nube** al **gasto tecnológico recurrente consolidado**, en
dos espacios separados (ADR-0013 y ADR-0014):

| Dimensión | Alcance inicial | Alcance final |
|---|---|---|
| Qué se mide | Consumo variable de IA y nube | Consumo variable **y** suscripciones de precio fijo |
| Para quién | Equipos de una organización | Organizaciones (**Empresa**) y hogares (**Personal**) |
| Unidad de atribución | Persona y equipo | Persona y equipo; en lo personal, miembros del hogar con cobros compartidos |
| Horizonte | Gasto ocurrido | Gasto ocurrido **y** cobros próximos (calendario y proyección anual) |
| Fuentes | APIs de proveedores e ingesta *push* | Lo anterior más registro manual guiado por un catálogo de servicios |

La ampliación no reemplazó el núcleo: el ledger idempotente, el modelo canónico y la arquitectura hexagonal se
mantuvieron, y lo nuevo se agregó como un dominio puro adicional (cobros recurrentes) detrás de sus propios puertos.
Que el cambio de alcance no exigiera rediseñar lo existente es, en sí mismo, evidencia de la **modificabilidad**
buscada. La misma ampliación ocurrió en la disciplina: en 2025 la FinOps Foundation incorporó al marco los *Scopes*
para gobernar SaaS, licencias e IA además de la nube pública (*Cloud+*) [27], y en 2026 el 90 % de los equipos de
FinOps ya gestionaba gasto SaaS y el 98 %, gasto de IA [28].

## 1.2 Pregunta de investigación y contribuciones

Este artículo aborda la pregunta: **¿cómo diseñar una plataforma consolidada, extensible y económica del gasto
tecnológico recurrente —consumo variable de IA y nube más suscripciones de precio fijo— que garantice exactitud de
los agregados bajo entrega duplicada, revisiones de los proveedores y escritura concurrente?** Las contribuciones son:

1. Una arquitectura de referencia serverless en AWS para FinOps multiproveedor, documentada con el modelo C4,
   catorce decisiones de arquitectura (ADR) y escenarios de calidad para once atributos.
2. Un **algoritmo de ledger idempotente basado en deltas** con control de concurrencia optimista, separado como lógica
   de dominio pura y verificado con pruebas basadas en propiedades.
3. Un **modelo de dominio de cobros recurrentes** que proyecta calendarios sin acumular desfases, reparte cobros
   compartidos al centavo y resume por moneda sin inventar tipos de cambio, integrado con el consumo variable en una
   misma herramienta.
4. La alineación explícita de la solución con marcos de arquitectura empresarial (TOGAF, ArchiMate) y de gobierno
   (COBIT 2019, ISO/IEC 38500, FinOps Framework), incluidos KPIs y una matriz RACI.
5. Un prototipo de código abierto con infraestructura como código, CI y un protocolo de pruebas de estrés que verifica
   la **consistencia** y no solo el rendimiento.

El resto del artículo se organiza así: la sección 2 revisa el estado del arte y argumenta por qué consolidar; la 3
describe la metodología; la 4, la implementación; la 5 presenta y discute los resultados; y la 6 concluye y propone
trabajo futuro.

# 2. Revisión de literatura y estado del arte

## 2.1 Gobierno de TI y FinOps

COBIT 2019 [5] define objetivos de gobierno y gestión. Tres son directamente pertinentes: **APO06 (Gestionar el
presupuesto y los costos)**, que exige asignar los costos de TI a los consumidores y controlarlos frente a
presupuestos; **APO10 (Gestionar los proveedores)**, que pide conocer y supervisar los contratos vigentes; y **BAI09
(Gestionar los activos)**, que incluye el inventario y la optimización de licencias. ISO/IEC 38500 [6] establece seis
principios para la dirección de TI (responsabilidad, estrategia, adquisición, desempeño, conformidad y comportamiento
humano), entre ellos que cada uso de TI tenga un responsable identificable. El FinOps Framework [7] y Storment y
Fuller [8] trasladan esos principios al costo variable de la nube y proponen un modelo de madurez (*crawl*, *walk*,
*run*) donde la asignación de costos es requisito de las fases posteriores.

La disciplina amplió su objeto de estudio en los últimos dos años. La actualización de 2025 del marco introdujo los
**Scopes**, que permiten aplicar las mismas capacidades a SaaS, licencias, centros de datos e IA además de la nube
pública, un enfoque que la Fundación denomina *Cloud+* [27]. Las encuestas anuales de practicantes muestran la
velocidad del cambio: en 2025, el 63 % de los equipos ya gestionaba gasto de IA (frente al 31 % un año antes) y el
65 % recibía el encargo de optimizar SaaS [29]; en 2026, esas cifras llegaron al 98 % y al 90 %, con un 64 % que
gestionaba licencias [28]. El problema de fondo no se ha resuelto: el 85 % de las organizaciones considera la
gestión del gasto en la nube su principal desafío, y el desperdicio estimado volvió a crecer, hasta el 29 %, por
primera vez en cinco años, impulsado por las cargas de IA [31].

Para la integración de datos, la especificación abierta **FOCUS** (*FinOps Open Cost and Usage Specification*)
define columnas normalizadas de costo y uso; su versión 1.2 (2025) añadió soporte para facturación SaaS y
normalización multimoneda [30]. FOCUS valida el enfoque de **modelo canónico** adoptado aquí, aunque está pensado
para exportaciones de facturación de grandes proveedores y no para suscripciones que una persona registra a mano.

Estos trabajos definen **qué** debe lograrse (visibilidad, asignación, presupuestos) y, cada vez más, **sobre qué**
(todo el gasto tecnológico, no solo la nube), pero no **cómo** construir una plataforma confiable cuando las fuentes
son heterogéneas, revisables y, en parte, manuales.

## 2.2 Gestión de activos de software y del gasto SaaS

La gestión de activos de software tiene su norma de referencia en ISO/IEC 19770-1 [34], que define los procesos de
inventario, control de licencias y ciclo de vida. Su aplicación al modelo SaaS enfrenta un problema nuevo: la compra
se descentralizó. El índice de Zylo de 2026, construido sobre los datos de sus clientes, reporta que las unidades de
negocio controlan el 81 % del gasto SaaS y TI gestiona directamente solo el 15 %; que el gasto pagado como reembolso
de gastos creció 267 % en un año, con ChatGPT como la aplicación más reembolsada; que el gasto en aplicaciones nativas
de IA creció 108 % (393 % en organizaciones de más de 10.000 empleados); que en promedio el 36 % de las licencias
queda sin usar; y que el 78 % de los líderes de TI encuestados recibió cobros inesperados ligados al consumo o a
precios de IA [32]. La edición de 2025 estimaba en 21 millones de dólares anuales el gasto promedio en licencias sin
uso [38]. Aunque estas cifras provienen de un proveedor del sector y deben leerse con esa cautela, describen el
mismo fenómeno: **el gasto existe, pero no está a la vista de quien debe gobernarlo**.

## 2.3 Economía de las suscripciones y comportamiento

La economía del comportamiento explica por qué el modelo de suscripción dificulta el control del gasto. Thaler [35]
mostró que las personas llevan una **contabilidad mental** por categorías, y que los pagos pequeños y automáticos
quedan fuera de esas cuentas. Gourville y Soman [36] encontraron que, cuando el pago se separa en el tiempo del
consumo, su peso en las decisiones se deprecia: lo que se cobra solo deja de sentirse como gasto. DellaVigna y
Malmendier [37] documentaron que los usuarios de gimnasios con cuota mensual sobrestiman cuánto usarán el servicio y
pagan más que con el pago por visita, y que tardan meses en cancelar membresías que ya no usan.

Los datos de consumo confirman el efecto. En una encuesta de C+R Research a 1.000 consumidores estadounidenses, los
participantes estimaron su gasto mensual en suscripciones en 86 dólares; al detallarlo cobro por cobro, el promedio
fue de 219 dólares. El 74 % dijo que es fácil olvidar los cobros recurrentes y el 42 % reconoció haber seguido
pagando por servicios que ya no usaba [33]. La conclusión para el diseño es directa: **un instrumento de control
debe sacar a la luz el cobro antes de que ocurra**, no solo registrarlo después.

## 2.4 Herramientas existentes

El mercado ofrece herramientas maduras, pero cada categoría cubre un fragmento del gasto. La Tabla 1 resume las
capacidades típicas de cada categoría; es una valoración cualitativa, no una evaluación de productos concretos.

| Categoría | Consumo de IA por API | Nube | Licencias SaaS | Suscripciones personales | Atribución a personas |
|---|---|---|---|---|---|
| Consolas de cada proveedor (AWS Cost Explorer, consolas de Anthropic y OpenAI) | Solo el propio | Solo el propio | — | — | Por llave, proyecto o etiqueta |
| Plataformas FinOps de nube | Si se factura por la nube | ● | Parcial | — | Por etiquetas |
| Plataformas de gestión de SaaS | — | — | ● | — | Por usuario licenciado |
| Pasarelas de LLM (p. ej. LiteLLM [39]) | Solo el tráfico que pasa por la pasarela | — | — | — | Por llave, usuario o equipo |
| Aplicaciones de finanzas personales | — | — | — | ● | Individual |
| **Radar de gastos** | ● | ● | ● | ● (registro manual) | Persona, equipo y miembros del hogar |

*Tabla 1. Cobertura del gasto tecnológico por categoría de herramienta (● = cubierto).*

Dos vacíos resultan de la tabla. Primero, ninguna categoría une el **consumo variable** con las **suscripciones de
precio fijo**, aunque para quien paga ambas son el mismo presupuesto. Segundo, las herramientas corporativas no
contemplan lo personal y las personales no contemplan el consumo por API, cuando la frontera entre ambos es cada vez
más difusa: la misma persona paga un plan de Claude o ChatGPT con su tarjeta y consume la API de su empresa.

## 2.5 Arquitectura empresarial

TOGAF [3] organiza el desarrollo de arquitectura en el ciclo ADM (visión, negocio, sistemas de información,
tecnología, oportunidades, migración, gobierno de la implementación y gestión del cambio). ArchiMate [4] aporta una
notación por capas (negocio, aplicación, tecnología) que relaciona capacidades y procesos con componentes y nodos.
En este trabajo se usan para trazar el problema de negocio (fragmentación del gasto) hasta componentes concretos
y para planificar arquitecturas de transición.

## 2.6 Arquitectura de software y atributos de calidad

Bass, Clements y Kazman [1] formalizan los **escenarios de atributos de calidad** (fuente, estímulo, artefacto,
entorno, respuesta y medida) y catalogan **tácticas** para cada atributo. El método ATAM [2] usa árboles de utilidad
para priorizar escenarios e identifica puntos de sensibilidad y *trade-offs*. El modelo C4 [16] propone cuatro niveles
de abstracción (contexto, contenedores, componentes y código), y los ADR [17] registran decisiones con su contexto y
consecuencias. La **arquitectura hexagonal** [9] aísla el dominio mediante puertos y adaptadores. **CQRS** [15] separa
los modelos de escritura y de lectura para optimizarlos de forma independiente. El **modelo de datos canónico** de
Hohpe y Woolf [10] reduce de N×M a N+M las transformaciones necesarias para integrar sistemas heterogéneos.

## 2.7 Computación serverless

Jonas et al. [14] caracterizan la computación serverless por la abstracción de servidores, el escalado automático a
cero y el pago por uso, e identifican como desafíos el estado, la coordinación y la latencia de arranque. El AWS
Well-Architected Framework y su *Serverless Lens* [18] recomiendan colas como amortiguadores (*queue-based load
leveling*), colas de mensajes fallidos (DLQ) e idempotencia de los consumidores, ya que servicios como SQS estándar
garantizan entrega al menos una vez.

## 2.8 Idempotencia, consistencia y concurrencia

Helland [12] sostiene que en sistemas distribuidos los mensajes se reintentan y, por tanto, toda operación debe
diseñarse para ser idempotente. Kleppmann [11] analiza que la semántica *exactamente-una-vez* no se logra en el
transporte sino en el **efecto**, combinando entrega al-menos-una-vez con procesamiento idempotente. Bailis y Ghodsi
[25] discuten las garantías prácticas de la consistencia eventual. Kung y Robinson [13] introdujeron el **control de
concurrencia optimista** (OCC): las transacciones proceden sin bloqueos y validan conflictos al confirmar, lo que
resulta eficiente cuando los conflictos son poco frecuentes. Brooker [22] muestra que el *backoff* exponencial con
*jitter* reduce la contención en reintentos concurrentes. DeBrie [19] documenta el diseño de tabla única en DynamoDB a
partir de patrones de acceso.

## 2.9 Por qué consolidar el gasto en una sola herramienta

La revisión anterior permite sostener que consolidar no es una comodidad visual, sino una condición del gobierno.
Los argumentos son cinco:

1. **No se gobierna lo que no se ve.** APO06 y la fase *Inform* de FinOps exigen visibilidad como primer paso [5],
   [7]. Cuando el gasto se reparte entre consolas, tarjetas y reembolsos, la suma total no existe en ningún lugar, y
   la decisión se toma sobre una fracción. La brecha entre los 86 dólares estimados y los 219 reales [33], o el 81 %
   del gasto SaaS fuera del control de TI [32], son la misma falla vista desde el hogar y desde la empresa.
2. **La responsabilidad necesita un nombre.** ISO/IEC 38500 pide que cada uso de TI tenga un responsable [6]. Las
   consolas atribuyen el costo a llaves y proyectos; solo una vista consolidada con un mapeo explícito puede
   atribuirlo a personas, equipos o miembros del hogar, condición del *showback* y del *chargeback*.
3. **El control debe ser anticipado.** El sesgo de los pagos automáticos [36] y los cobros inesperados que reporta el
   78 % de los líderes de TI [32] muestran que registrar el gasto después no basta. Un calendario de próximos cobros
   y presupuestos con alertas tempranas convierten el control reactivo en preventivo.
4. **El desperdicio se esconde entre fuentes.** Licencias sin uso (36 % en promedio [32]), suscripciones duplicadas
   entre áreas o miembros de un hogar, y planes de IA pagados a la vez por suscripción y por API solo se detectan al
   comparar fuentes lado a lado. Ninguna consola individual puede revelar una duplicidad que involucra a otra.
5. **El gasto de IA cruza todas las categorías.** La misma capacidad se paga por API, por suscripción individual,
   por licencia corporativa o dentro de la factura de la nube. Gobernarla exige verla completa; de lo contrario, la
   reducción en un canal reaparece en otro.

Consolidar también tiene un costo: más integraciones que mantener, más datos sensibles en un solo lugar y el riesgo
de mostrar cifras incorrectas con apariencia de autoridad. Por eso la exactitud de los agregados (sección 2.8) y la
seguridad de las credenciales son requisitos de primer orden en este diseño, y no atributos secundarios.

## 2.10 Síntesis y brecha

La literatura de gobierno define los objetivos (asignación, presupuestos, inventario) y ya extiende su alcance a
todo el gasto tecnológico; la de comportamiento explica por qué el gasto recurrente escapa al control; y la de
sistemas distribuidos aporta los mecanismos (idempotencia, OCC, colas). Las herramientas existentes, en cambio,
siguen especializadas por tipo de gasto. No se encontró una propuesta que **integre** los tres mundos: un
instrumento que reúna el consumo variable de varios proveedores de IA y nube —donde coinciden tres fuentes de
duplicación: la mensajería, la relectura periódica y las revisiones del proveedor— con las suscripciones de precio
fijo de una organización y de un hogar. Este trabajo propone y evalúa esa integración.

# 3. Metodología

## 3.1 Enfoque

Se siguió un enfoque de **investigación en ciencia del diseño** (*design science*): identificación del problema,
definición de objetivos, diseño y construcción de un artefacto (el prototipo), demostración y evaluación. El diseño
de la arquitectura fue **guiado por atributos de calidad** [1]:

1. **Contexto y *drivers*:** interesados, preocupaciones y cinco *business drivers* medibles (p. ej. conocer el gasto
   consolidado en menos de un minuto o atribuir al menos el 95 % del costo).
2. **Árbol de utilidad y escenarios:** once escenarios de calidad priorizados por importancia y dificultad (ATAM [2]).
3. **Selección de tácticas y patrones** por escenario, registrada en ADR.
4. **Arquitectura empresarial:** recorrido del ADM de TOGAF, principios de arquitectura, mapa de capacidades FinOps y
   *gap analysis*.
5. **Gobierno:** mapeo a objetivos de COBIT 2019, principios de ISO/IEC 38500, KPIs y RACI.
6. **Construcción iterativa** con desarrollo guiado por pruebas en el núcleo de dominio.
7. **Evaluación:** pruebas automatizadas, pruebas de propiedades, pruebas de estrés con verificación de consistencia y
   análisis de *trade-offs*.

La ciencia del diseño es iterativa: cada demostración puede redefinir el problema. Así ocurrió aquí. La evaluación
del primer artefacto con cuentas reales mostró que el consumo por API era solo una parte del gasto que los usuarios
querían controlar, y el problema se redefinió como se describe en la sección 1.1. Cada ampliación siguió el mismo
procedimiento: un ADR con las alternativas consideradas (0012 a 0014), un dominio nuevo detrás de puertos propios,
pruebas del dominio antes de la interfaz y verificación de que las pruebas existentes seguían pasando sin cambios.

## 3.2 Tecnologías

| Ámbito | Tecnología | Justificación |
|---|---|---|
| Lenguaje | Python 3.13, Pydantic v2, `mypy --strict` | SDKs oficiales de los proveedores; validación en los bordes |
| Cómputo | AWS Lambda (arm64/Graviton) | Escala a cero; mejor precio/rendimiento |
| Mensajería | Amazon SQS estándar + DLQ | Nivelación de carga, aislamiento de fallas |
| Datos | Amazon DynamoDB *on-demand* | Transacciones ACID, OCC por condiciones, escalado automático |
| API e identidad | API Gateway HTTP, Amazon Cognito | Autorizador JWT nativo, OAuth 2.0 (PKCE y *client credentials*) |
| Planificación | EventBridge Scheduler | Recolección horaria y evaluación diaria de presupuestos |
| Frontend | SPA estática, Chart.js (servido desde el propio origen), CloudFront + S3 | Sin servidores; cabeceras de seguridad en el borde; funciona sin internet en local |
| Observabilidad | AWS Lambda Powertools, CloudWatch, X-Ray | Logs estructurados, métricas EMF, trazas |
| IaC y CI | Terraform (módulos), GitHub Actions (OIDC) | Reproducibilidad y gobierno de cambios |
| Pruebas | pytest, Hypothesis [24], moto, respx, k6 | Pirámide completa sin depender de la nube |

## 3.3 Patrones de diseño aplicados

Arquitectura hexagonal (puertos y adaptadores), modelo de datos canónico, Adapter + Strategy + Registry para
conectores, CQRS con agregados precalculados, *Repository*, *Composition Root*, consumidores en competencia
(*competing consumers*), *queue-based load leveling*, DLQ, respuesta de lote parcial (*bulkhead* por mensaje),
control de concurrencia optimista, reintento con *backoff* exponencial y *full jitter*, y *singleton* perezoso por
contenedor de ejecución.

# 4. Implementación

## 4.1 Visión general

La Figura 1 (vista de contenedores C4, en `docs/03-vistas-c4.md`) muestra dos rutas de entrada que confluyen en una
cola SQS. En la ruta **pull**, EventBridge invoca cada hora una función que publica una tarea por conector
habilitado y el colector consulta la API del proveedor. En la ruta **push**, cualquier sistema envía registros a
`POST /v1/usage/records` autenticado con OAuth 2.0. El colector normaliza y escribe en el ledger. La API sirve al
dashboard desde agregados precalculados, y una función diaria evalúa presupuestos y publica alertas en SNS.

## 4.2 Modelo canónico y conectores

Cada conector traduce la respuesta de su proveedor a `UsageRecord`, un hecho diario inmutable con identidad natural
(tenant, proveedor, servicio, principal, fecha) y métricas aditivas (tokens de entrada, salida y caché, solicitudes y
costo en `Decimal`). Algunas particularidades que el diseño absorbe:

- **Anthropic:** se usa la *Usage and Cost Analytics API* mediante el SDK oficial
  (`client.beta.organization.analytics.usage/cost`), agrupando por `actor` y `model`. El costo llega en centavos y se
  convierte a dólares. Las ventanas se dividen en tramos de 31 días, el máximo por solicitud [20].
- **OpenAI:** la API de uso agrupa tokens por usuario o API key, pero la de costos solo por proyecto [21]. El tipado del
  modelo canónico obliga a hacer explícita esa asimetría (ADR-0006).
- **AWS:** Cost Explorer agrupado por servicio y *cost allocation tag* `owner`, leído mediante `AssumeRole` con
  `ExternalId` en la cuenta *payer*. El consumo de Claude vía Amazon Bedrock aparece como servicio de AWS.
- **Google:** consulta parametrizada a la exportación de facturación en BigQuery, con validación del nombre de tabla
  para prevenir inyección SQL.

Un proveedor nuevo se agrega con un módulo y una línea de registro (`@register(Provider.X)`). El registro carga los
módulos de forma diferida para no penalizar el arranque en frío.

## 4.3 El ledger idempotente basado en deltas

El núcleo es la función pura `compute_deltas(previo, nuevo, atribución)`, que devuelve el ajuste por celda agregada
(fecha × proveedor × {persona, equipo, servicio}):

- **Primera escritura:** +nuevo en tres celdas.
- **Reescritura idéntica:** conjunto vacío. Se detecta antes con `content_hash` y no se escribe nada.
- **Revisión:** +(nuevo − previo) en cada celda.
- **Reatribución:** −previo en las celdas antiguas y +nuevo en las nuevas. Las celdas coincidentes se fusionan, porque
  DynamoDB no permite operar dos veces sobre el mismo ítem en una transacción.

El adaptador de DynamoDB aplica el resultado de forma atómica:

```
repetir hasta 8 veces:
    previo ← GetItem(hecho, ConsistentRead)
    si sin_cambios(previo, nuevo): devolver UNCHANGED
    TransactWriteItems(
        Put(hecho, version = v+1, condición: version = v  |  attribute_not_exists),
        Update(celda_i, ADD Δ_i)  para cada celda)
    si éxito: devolver CREATED | REVISED
    si ConditionalCheckFailed o TransactionConflict: esperar U(0, base·2^intento)
lanzar ConcurrencyError  → el mensaje vuelve a SQS y, tras 5 intentos, a la DLQ
```

La condición sobre `version` implementa OCC [13]: si dos colectores leyeron la misma versión, solo uno confirma; el
otro relee, recalcula el delta respecto de la versión ganadora y reintenta. El hecho y sus agregados se actualizan
en la misma transacción, así que el modelo de lectura nunca diverge del ledger. Como el delta respecto de la misma
versión es cero, **reprocesar un mensaje es inocuo**, y eso hace seguros los reintentos de SQS, el *redrive* desde la
DLQ y los *backfills*.

## 4.4 Modelo de datos

Se usa una tabla única con claves compuestas. Los hechos se guardan en `T#{tenant}#F#{mes}` y los agregados en
`T#{tenant}#A#{dimensión}#{mes}`, con `SK = fecha#proveedor#valor`. Una consulta de 90 días lee como máximo cuatro
particiones por dimensión, sin importar el volumen de hechos. El particionamiento mensual acota el tamaño de las
colecciones y distribuye la escritura.

## 4.5 Seguridad y multi-tenancy

El autorizador JWT de API Gateway valida los tokens de Cognito antes de invocar a Lambda. El tenant se obtiene
**exclusivamente** de la claim inmutable `custom:tenant_id`, o de la configuración `client_id → tenant` en el caso de
clientes M2M. Un cuerpo que incluya `tenant_id` se rechaza, lo que mitiga la vulnerabilidad BOLA (OWASP API1:2023
[23]). Las llaves Admin de los proveedores, de solo lectura, se guardan en Secrets Manager con caché TTL de 5 min.
Cada función tiene un rol IAM propio con acciones explícitas. Los datos en reposo (tabla, logs, variables de entorno,
tópico de alertas y horarios) se cifran con una llave KMS administrada por el cliente con rotación anual. El
frontend se sirve desde un *bucket* privado con OAC y una política de seguridad de contenido (CSP) que solo permite
scripts del propio origen.

## 4.6 Infraestructura, observabilidad y CI

Terraform compone cuatro módulos reutilizables: `lambda_function` (instanciado cuatro veces), `sqs_queue`,
`static_site` y `cost_reader_role`. Powertools emite métricas de negocio en formato EMF (`RecordsWritten`,
`RecordsUnchanged`, `LedgerRetry*`, `QueueToLedgerLatency`) sin llamadas síncronas. Un dashboard operativo y alarmas
de SLO (5xx > 1 %, p95 > 800 ms, DLQ > 0, edad de la cola > 15 min) completan la soportabilidad. El pipeline de CI
ejecuta formato, lint (incluido bandit), `mypy --strict`, pruebas con umbral de cobertura, `pip-audit`, `checkov` y
`terraform validate`. Checkov actúa como barrera: un hallazgo nuevo detiene el pipeline, y cada excepción aceptada
se justifica en el propio recurso. Un script reproduce el despliegue completo (empaquetado, Terraform, datos de
ejemplo y alta del administrador), y el mismo código corre en local sin AWS como entorno de respaldo.

## 4.7 Dashboard

La SPA presenta KPIs (costo, tokens, solicitudes y equipo con más gasto), costo diario apilado por proveedor o equipo,
rankings de personas y modelos con desglose por proveedor, y el estado de los presupuestos con icono y texto (el color
no es la única señal). Los colores son fijos por proveedor y usan una paleta validada para daltonismo, con modo
oscuro y vista de tabla accesible.

La aplicación separa dos conjuntos de datos: **Datos reales** (el tenant del usuario) y **Ejemplo** (un tenant de
demostración de solo lectura). Desde la vista real, una pantalla de **Configuración** permite a los administradores
operar sin consola de AWS (ADR-0011):

- registrar conexiones con un formulario que se genera desde un catálogo declarativo de proveedores;
- *probar* las credenciales leyendo los últimos tres días sin escribir en el ledger;
- sincronizar bajo demanda y ver el estado del último sync de cada conexión;
- asignar a personas y equipos las identidades técnicas detectadas, con el porcentaje de gasto ya atribuido como KPI;
- definir presupuestos.

Las credenciales se custodian tras un puerto `SecretStore` (Secrets Manager en la nube, archivos fuera del
repositorio en local) y nunca se devuelven al navegador.

Finalmente, la aplicación distingue dos espacios (ADR-0013). En **Empresa** está el consumo descrito, más las
**licencias SaaS** con número de usuarios. En **Personal**, cada persona registra sus suscripciones, sean de IA o
no (streaming, música, software, almacenamiento), con monto, moneda, ciclo y fecha de cobro.

Un módulo de dominio puro calcula el calendario de cobros desde una fecha ancla, sin acumular desfases, y ajusta
al último día los meses más cortos. También calcula el equivalente mensual y un resumen agrupado por moneda: no
convierte divisas para no introducir tipos de cambio no verificados. Con eso el panel muestra próximos cobros,
calendario y proyección anual. Lo personal se indexa por el `sub` del token, así que ni otros miembros del tenant
pueden leerlo.

En el espacio personal se pueden crear **perfiles de personas** y asignar cada suscripción a una o varias
(ADR-0014). Lo compartido se reparte con un algoritmo que distribuye los centavos sobrantes para que las partes
sumen exactamente el cobro. La tarjeta "Gasto por persona" y el panel filtrado se derivan de la misma vista, lo
que garantiza que muestren cifras idénticas. Un hogar de ejemplo generado al vuelo, con fechas relativas a hoy,
permite explorar el panel sin datos propios.

# 5. Resultados y evaluación

## 5.1 Verificación funcional y estática

| Indicador | Resultado |
|---|---|
| Pruebas automatizadas | 153 (107 unitarias, 2 de propiedades, 15 de integración con AWS emulado, 29 de handlers) |
| Cobertura (líneas y ramas) | 96,5 % (umbral: 80 %) |
| Tipado estático | `mypy --strict`: 0 errores en 38 módulos |
| Lint y seguridad estática | `ruff` y `bandit`: 0 hallazgos; `pip-audit`: 0 vulnerabilidades conocidas |
| Seguridad de la infraestructura | Checkov: 291 controles aprobados, 0 fallidos, 24 excepciones justificadas |
| Tiempo de la suite | ≈ 11 s, sin cuenta de AWS |

La primera prueba de propiedades genera secuencias arbitrarias de hasta 12 revisiones con costos, tokens y atribuciones
aleatorias, cada una entregada entre una y tres veces. Verifica que, en las tres dimensiones, el agregado sea igual a
la última versión del hecho y que solo quede la última atribución. Las pruebas de integración inyectan
`TransactionConflict` y `ConditionalCheckFailed` y simulan dos *workers* que leen la misma versión. En todos los casos
el resultado converge al valor correcto. La segunda prueba de propiedades cubre el dominio de cobros recurrentes:
para fechas ancla, ventanas y ciclos de facturación arbitrarios, verifica que los cobros proyectados sean
estrictamente crecientes y caigan dentro de la ventana, incluidos los meses cortos. Otras pruebas del mismo dominio
comprueban que el reparto de un cobro compartido sume exactamente el total y que la vista por persona coincida al
centavo con el resumen del hogar.

## 5.2 Pruebas de estrés con verificación de consistencia

Se ejecutaron tres perfiles de carga abierta (*load*, *stress* y *spike*) contra el mismo handler de la API desplegado
en un servidor local de un solo proceso, con repositorio en memoria. La carga fue mixta: 50 % ingesta en lotes de 25
registros con **15 % de lotes reenviados** para simular reintentos, y 50 % lecturas de resumen. Al final de cada
corrida, el generador compara el costo agregado que reporta la API con la suma exacta de los registros únicos aceptados.

| Escenario | Peticiones | req/s | Registros/s | Lotes duplicados | Ingesta p50/p95/p99 (ms) | Lectura p50/p95/p99 (ms) | Errores | Costo esperado vs. observado (USD) |
|---|---|---|---|---|---|---|---|---|
| Load | 1.049 | 28,2 | 287,4 | 75 | 593 / 2.297 / 3.152 | 1.073 / 2.796 / 6.383 | 1,8 % | 266.870,15 = 266.870,15 |
| Stress | 964 | 28,4 | 322,8 | 78 | 355 / 1.875 / 2.490 | 606 / 3.034 / 5.535 | 2,1 % | 274.696,88 = 274.696,88 |
| Spike | 688 | 22,9 | 235,2 | 60 | 246 / 1.165 / 1.456 | 326 / 1.645 / 5.371 | 2,5 % | 177.450,48 = 177.450,48 |

**Exactitud.** En los tres escenarios, con 213 lotes duplicados en total (5.325 registros reenviados), el error de
agregación fue **0,00 USD**. Esto confirma empíricamente el escenario QAS-R1.

**Disponibilidad de la ingesta.** El 100 % de las peticiones de ingesta fue aceptado (HTTP 202). Los errores
observados (1,8-2,5 %) corresponden exclusivamente a lecturas que superaron el *timeout* del cliente cuando el proceso
estaba saturado.

**Rendimiento.** El techo de alrededor de 28 req/s y las latencias de segundos **son propios del arnés local**: un
único proceso de Python, limitado por el GIL, que además drena la cola sincrónicamente en el hilo de cada petición.
No son representativos del despliegue en AWS, donde la API y el colector escalan como funciones independientes. Aun
así, el experimento aporta un resultado útil para la arquitectura: la **consulta de resumen es la operación más costosa
en CPU** (tres consultas de agregados más ordenamientos, con p99 superior a 5 s bajo saturación). Esto respalda la
decisión de precalcular agregados (CQRS) y señala la caché de lectura como la siguiente optimización.

**Pruebas de estrés en AWS.** Los mismos tres perfiles se ejecutaron contra el despliegue en AWS Academy Learner
Lab, con carga mixta, 15 % de lotes duplicados y métricas del servidor leídas de CloudWatch (detalle en
`docs/08-estrategia-pruebas.md`, sección 8.4). La carga se redujo a 20 req/s base y 2 minutos por escenario para no
agotar el crédito del laboratorio.

| Escenario | Peticiones | Registros/s | Lotes duplicados | Ingesta p50 / p95 (ms) | Lectura p50 / p95 (ms) | Errores | Conflictos OCC | DLQ | Esperado = observado (USD) |
|---|---|---|---|---|---|---|---|---|---|
| Load | 2.400 | 213,3 | 170 | 130 / 199 | 1.027 / 1.953 | 0 % | 24.262 | 0 | 648.727,51 = 648.727,51 |
| Stress | 2.014 | 147,2 | 158 | 129 / 346 | 4.780 / 10.113 | 0,05 % | 16.188 | 0 | 525.235,32 = 525.235,32 |
| Spike | 1.051 | 90,4 | 76 | 132 / 481 | 5.082 / 12.032 | 0,19 % | 8.137 | 0 | 279.914,39 = 279.914,39 |

**Exactitud en la nube.** Con 404 lotes duplicados y 48.587 reintentos por conflicto, el costo agregado coincidió
al centavo con la suma de los registros únicos en las tres corridas, una vez procesada la cola. Es la confirmación
en AWS del escenario QAS-R1.

**Ingesta.** El 100 % de los lotes fue aceptado, con p95 entre 199 y 481 ms (objetivo: 500 ms) y sin mensajes en la
DLQ ni *throttling* de DynamoDB.

**Cuello de botella de escritura.** Los colectores llegaron a su concurrencia máxima (20) y se serializaron en las
celdas agregadas compartidas por todos los registros de una corrida: la capacidad efectiva del ledger fue de unos
100 registros/s, la cola acumuló hasta 390 mensajes y los datos tardaron minutos en reflejarse. Es el punto de
sensibilidad S1 anticipado en el diseño, ahora cuantificado: el control de concurrencia optimista preserva la
exactitud a costa de la frescura, y el *sharding* de celdas calientes (ADR-0004) es la siguiente mejora.

**Lecturas.** El resumen tuvo p95 de 2 a 12 s porque recorre todas las celdas del agregado por persona del rango:
el generador usa un principal distinto por registro y el tenant de carga acumuló 29.150. Aunque esa cardinalidad
exagera el caso real, el costo lineal es un defecto de diseño que la prueba local no podía revelar. La alarma de
latencia lo detectó, pero osciló entre ALARM y OK por falta de histéresis.

**Segunda corrida con *shards*.** Se repartió cada celda agregada en 8 *shards* elegidos por el identificador del
hecho, de modo que revisiones y reatribuciones siguen tocando las mismas celdas, y se repitieron los tres escenarios.
Los conflictos bajaron entre 69 y 86 %, la cola dejó de acumular trabajo, los datos se reflejaron en 10 a 17 s en
lugar de 7 a 8 minutos, desaparecieron los errores y el costo coincidió al centavo dentro de la propia verificación.
El ledger pasó de unos 100 a unos 245 registros/s en el pico. Las lecturas no mejoraron en el p95, porque el top de
personas siguió recorriendo todas sus celdas; se separó en su propia ruta, corrección que no alcanzó a medirse en la
nube.

**Incidente.** Al terminar la segunda corrida, AWS Academy desactivó la cuenta del laboratorio: el entorno permite
como máximo 10 ejecuciones concurrentes de Lambda y la prueba llegó a 64 en la API y 20 en el colector. Se había verificado el límite técnico de la
cuenta, no la restricción documentada del laboratorio. El modo laboratorio de la infraestructura reserva ahora
concurrencia por función (9 en total) para que el exceso se rechace en vez de superar el límite. El incidente ilustra
un punto de gobierno de TI: las cuotas de la plataforma son requisitos no funcionales y deben vivir en la
infraestructura como código.

**Caída controlada en AWS.** El prototipo se desplegó en AWS Academy Learner Lab, que no permite crear roles IAM
ni usar CloudFront o X-Ray: las funciones usan el rol del laboratorio y la propia API sirve el dashboard por HTTPS.
Sobre ese despliegue se terminó la sesión del laboratorio para provocar una caída real y se midió el sistema desde
fuera (el detalle está en `docs/10-prueba-disponibilidad.md`). Al terminar la sesión, una *service control policy*
de AWS Organizations niega a las funciones el acceso a DynamoDB y a CloudWatch Logs.

| Medición | Resultado |
|---|---|
| Consultas de datos | 500 desde 00:06:17 hasta la recuperación; última correcta a las 00:04:48 |
| Dashboard, Cognito y autorizador JWT | Disponibles durante toda la caída (mediana de 125 ms frente a 131 ms) |
| Integridad (antes → después) | 6.313 → 6.313 ítems; 2.807 → 2.807 hechos; cola y DLQ en 0 |
| Recuperación | Automática: la primera consulta tras reiniciar el laboratorio respondió 200 (411 ms) |
| Detección | La alarma de errores de la función se disparó en ≈ 1 min; la de tasa de 5xx no |
| Respaldo | El mismo código, ejecutado en local, sirvió el dashboard durante la caída |

La prueba confirmó las propiedades críticas (integridad y recuperación) y expuso cuatro debilidades que las
pruebas locales no podían revelar: un chequeo de salud que respondía 200 sin poder leer la base de datos, un error
500 sin significado para el usuario, un dashboard que mostraba datos de otro rango sin avisarlo, y una alarma de 5xx
calibrada para tráfico alto. Las cuatro se corrigieron (chequeo `/v1/ready`, respuestas 503 con `Retry-After`, aviso
de datos desactualizados y alarma de 2 de 5 minutos) y quedaron cubiertas por pruebas automatizadas. Al
repetir la caída tras redesplegar, `/v1/ready` respondió 503 mientras `/v1/health` seguía en 200, el usuario vio el
mensaje de indisponibilidad en lugar del error genérico, y la alarma de 5xx pasó a ALARM en unos 2 minutos y volvió
a OK unos 4 minutos después de la recuperación, con ambos avisos entregados por correo. La sesión reveló además que
la CSP de producción bloqueaba estilos en línea del dashboard que en local, sin CSP, sí se aplicaban; se corrigió y
el entorno local adoptó la misma política.

## 5.3 Evaluación por atributo de calidad

| Atributo | Mecanismo | Evidencia | Estado |
|---|---|---|---|
| Confiabilidad | Ledger con deltas, transacciones, OCC | Pruebas de propiedades y de estrés con duplicados | **Verificado** |
| Disponibilidad | Cola + DLQ, lote parcial, servicios multi-AZ, chequeo `/v1/ready`, 503 con `Retry-After` | Aislamiento de fallas por mensaje; caída controlada en AWS (recuperación automática, datos intactos) | Verificado; SLO bajo carga por medir |
| Desempeño | Asincronía, CQRS, particiones mensuales | AWS: ingesta p95 199-481 ms; lecturas p95 2-12 s por la cardinalidad del agregado por persona | Ingesta verificada; lecturas por mejorar |
| Escalabilidad | Lambda + SQS + DynamoDB *on-demand*, concurrencia acotada | AWS: la cola absorbió los picos sin pérdidas ni DLQ; el ledger se limitó a ≈ 100 registros/s por celdas calientes | Verificado, con límite cuantificado |
| Seguridad | JWT, tenant desde la claim, mínimo privilegio, cifrado con CMK | `test_tenant_isolation`, modelo STRIDE, Checkov sin fallos | **Verificado** |
| Interoperabilidad | Modelo canónico, OpenAPI 3.1, OAuth 2.0 | Ingesta *push* de extremo a extremo | **Verificado** |
| Modificabilidad | Hexagonal, Strategy/Registry | Proveedor nuevo = 1 módulo + 1 registro; ampliación del alcance sin modificar el ledger | **Verificado** |
| Mantenibilidad | Capas, tipado estricto, lint en CI | 0 hallazgos estáticos | **Verificado** |
| Testabilidad | Puertos + dobles en memoria + moto | 96,5 % de cobertura sin AWS | **Verificado** |
| Reusabilidad | Módulos Terraform y conectores desacoplados | `lambda_function` × 4 | **Verificado** |
| Soportabilidad | Logs JSON, X-Ray, EMF, runbook, alarmas | Caída en AWS: detección en ≈ 1 min y causa identificada en los logs de acceso | Verificado, con mejoras aplicadas |

## 5.4 Fortalezas

1. **Corrección por construcción:** la lógica de deltas es una función pura, probada de forma exhaustiva, y el
   adaptador solo garantiza atomicidad y aislamiento.
2. **Costo proporcional al uso:** sin cómputo ocioso, coherente con el *driver* BD5. La propia plataforma se
   autoobserva mediante `default_tags`.
3. **Extensibilidad real:** la API *push* convierte a "cualquier sistema" en fuente sin desarrollo adicional, y los
   conectores aíslan los cambios frecuentes de las APIs de los proveedores.
4. **Gobierno integrado:** atribución, presupuestos con alertas idempotentes, KPIs y RACI conectan la herramienta con
   APO06 y con las fases *Inform* y *Operate* de FinOps; el inventario de licencias aporta a APO10 y BAI09.
5. **Una sola vista del gasto:** consumo variable y suscripciones de precio fijo, de la empresa y del hogar, conviven
   en un mismo instrumento, que es el vacío identificado en la Tabla 1.

## 5.5 Limitaciones

1. **Agregados calientes:** la tasa de conflictos OCC crece con la concurrencia sobre una misma celda (punto de
   sensibilidad S1). La concurrencia del consumidor está acotada; la solución estructural (*sharding* de celdas) no se
   implementó.
2. **Costo de escritura:** cada registro implica una lectura consistente y una transacción de hasta cuatro ítems
   (2× WCU), el precio de lecturas rápidas.
3. **Atribución en OpenAI:** el costo por persona no está disponible en la fuente y debe estimarse.
4. **Montos antes de créditos e impuestos:** se requiere conciliación con la factura para el cierre contable.
5. **Validación en la nube acotada:** las pruebas de estrés en AWS usaron una carga reducida (20 req/s base, 2
   minutos por escenario), no se ejecutó la prueba de larga duración (*soak*), y la corrección de las lecturas no se
   midió en la nube porque el laboratorio se desactivó al superar su límite de concurrencia de Lambda.
6. **Lecturas sensibles a la cardinalidad:** el resumen recorre todas las celdas del agregado por persona; con
   miles de identidades distintas su latencia crece linealmente (medido en AWS).
7. **Aislamiento lógico:** el modelo *pool* de tabla compartida puede no bastar para clientes regulados [26].
8. **Suscripciones registradas a mano:** a diferencia de las aplicaciones de finanzas personales, el prototipo no
   detecta cobros en cuentas bancarias o correos; su exactitud depende de que el usuario mantenga el registro al día.
9. **Sin conversión de divisas:** los totales se presentan por moneda para no introducir tipos de cambio no
   verificados, lo que impide una cifra única cuando se paga en varias monedas.
10. **Consumo de los planes de suscripción:** los proveedores no exponen por API el uso de planes como claude.ai o
   ChatGPT Plus; solo se registra su precio fijo y, para Claude Code, una estimación a partir de los registros locales.
11. **Evaluación con usuarios pendiente:** la utilidad del espacio personal para reducir gasto no se midió con un
    estudio de usuarios.

## 5.6 Mejoras propuestas

*Sharding* de agregados calientes y agregación vía DynamoDB Streams; caché de lectura por tenant y rango; *data lake*
en S3 con Athena para análisis *ad hoc*; IAM con `dynamodb:LeadingKeys` para reforzar el aislamiento; pronóstico de
gasto y detección de anomalías; conciliación automática con facturas; importación y exportación en formato FOCUS
[30]; detección de suscripciones duplicadas entre miembros o áreas; y conversión de divisas con una fuente de tipos
de cambio auditable.

# 6. Conclusión

Este trabajo mostró que el gobierno del consumo multiproveedor de IA y nube es, ante todo, un problema de
**exactitud de datos en un sistema distribuido**, y que puede resolverse con una arquitectura serverless económica si
la idempotencia se diseña como propiedad del dominio y no como un detalle de la infraestructura. El ledger basado en
deltas, con transacciones y control de concurrencia optimista, logró error de agregación nulo bajo duplicados
inyectados, revisiones y escritura concurrente, verificado tanto por pruebas basadas en propiedades como por pruebas
de estrés con comprobación de consistencia.

El trabajo mostró también que el problema era más amplio de lo que planteaba su versión inicial. El gasto
tecnológico de una organización o de un hogar no se divide en "consumo de IA" y "todo lo demás": se paga por API, por
suscripción, por licencia y por reembolso, y gran parte se renueva sin que nadie lo decida de nuevo. La literatura de
FinOps llegó a la misma conclusión con los *Scopes* [27], y los datos de mercado y de comportamiento [32], [33], [36]
explican por qué el gasto fragmentado y automático escapa al control. Ampliar el alcance sin rediseñar el núcleo fue
posible porque la arquitectura aislaba cada dominio detrás de puertos, lo que valida la apuesta por la
modificabilidad.

**Implicaciones para la práctica.** (i) Las plataformas FinOps deberían tratar la entrega duplicada y las revisiones
de los proveedores como casos normales y no excepcionales. (ii) Un modelo canónico más una API de ingesta abierta
convierte la integración de N proveedores en un problema lineal y desacopla la organización de los cambios de cada
proveedor. (iii) Los marcos de gobierno (COBIT APO06, APO10, BAI09; ISO/IEC 38500) ganan efectividad cuando se
traducen a capacidades verificables: KPIs calculados por el sistema, alertas idempotentes y responsables explícitos
(RACI). (iv) Consolidar el consumo variable y las suscripciones en una sola vista es una condición del gobierno, no
una comodidad: es la única forma de ver el total, asignar responsables, anticipar cobros y detectar duplicidades
entre fuentes.

**Trabajo futuro.** Implementar el *sharding* de celdas calientes y un total diario de cardinalidad baja para el resumen, y repetir el protocolo de estrés con la carga completa y la prueba de larga duración; repetir la caída controlada durante una recolección para ejercitar los reintentos y la DLQ; cuantificar la relación entre concurrencia y
conflictos OCC para dimensionar el *sharding* de agregados; incorporar pronóstico y detección de anomalías sobre el
ledger; evaluar el modelo de aislamiento *silo* frente a *pool* para escenarios regulados; adoptar FOCUS como formato
de intercambio; y medir con usuarios si la vista consolidada reduce el gasto no deseado.

# Referencias

[1] L. Bass, P. Clements y R. Kazman, *Software Architecture in Practice*, 4.ª ed. Boston, MA, EE. UU.: Addison-Wesley, 2021.

[2] R. Kazman, M. Klein y P. Clements, "ATAM: Method for Architecture Evaluation," Software Engineering Institute, Carnegie Mellon University, Rep. téc. CMU/SEI-2000-TR-004, 2000.

[3] The Open Group, *The TOGAF Standard, 10th Edition*. The Open Group, 2022.

[4] The Open Group, *ArchiMate 3.2 Specification*. The Open Group, 2022.

[5] ISACA, *COBIT 2019 Framework: Governance and Management Objectives*. Schaumburg, IL, EE. UU.: ISACA, 2018.

[6] *Information technology — Governance of IT for the organization*, ISO/IEC 38500:2015, 2015.

[7] FinOps Foundation, "FinOps Framework." [En línea]. Disponible: https://www.finops.org/framework/

[8] J. R. Storment y M. Fuller, *Cloud FinOps: Collaborative, Real-Time Cloud Value Decision Making*, 2.ª ed. Sebastopol, CA, EE. UU.: O'Reilly Media, 2023.

[9] A. Cockburn, "Hexagonal architecture," 2005. [En línea]. Disponible: https://alistair.cockburn.us/hexagonal-architecture/

[10] G. Hohpe y B. Woolf, *Enterprise Integration Patterns: Designing, Building, and Deploying Messaging Solutions*. Boston, MA, EE. UU.: Addison-Wesley, 2003.

[11] M. Kleppmann, *Designing Data-Intensive Applications*. Sebastopol, CA, EE. UU.: O'Reilly Media, 2017.

[12] P. Helland, "Idempotence is not a medical condition," *Communications of the ACM*, vol. 55, n.º 5, pp. 56–65, 2012.

[13] H. T. Kung y J. T. Robinson, "On optimistic methods for concurrency control," *ACM Transactions on Database Systems*, vol. 6, n.º 2, pp. 213–226, 1981.

[14] E. Jonas et al., "Cloud programming simplified: A Berkeley view on serverless computing," University of California, Berkeley, Rep. téc. UCB/EECS-2019-3, 2019.

[15] M. Fowler, "CQRS," 2011. [En línea]. Disponible: https://martinfowler.com/bliki/CQRS.html

[16] S. Brown, "The C4 model for visualising software architecture." [En línea]. Disponible: https://c4model.com

[17] M. Nygard, "Documenting architecture decisions," 2011. [En línea]. Disponible: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions

[18] Amazon Web Services, "AWS Well-Architected Framework — Serverless Applications Lens." [En línea]. Disponible: https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/

[19] A. DeBrie, *The DynamoDB Book*, 2020.

[20] Anthropic, "Usage and Cost Analytics API," Claude Platform Docs, 2026. [En línea]. Disponible: https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api

[21] OpenAI, "Usage API and Costs API reference," OpenAI Platform Docs. [En línea]. Disponible: https://platform.openai.com/docs/api-reference/usage

[22] M. Brooker, "Exponential backoff and jitter," AWS Architecture Blog, 2015. [En línea]. Disponible: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

[23] OWASP Foundation, "OWASP API Security Top 10 — 2023." [En línea]. Disponible: https://owasp.org/API-Security/editions/2023/en/0x11-t10/

[24] D. R. MacIver, Z. Hatfield-Dodds et al., "Hypothesis: A new approach to property-based testing," *Journal of Open Source Software*, vol. 4, n.º 43, p. 1891, 2019.

[25] P. Bailis y A. Ghodsi, "Eventual consistency today: Limitations, extensions, and beyond," *Communications of the ACM*, vol. 56, n.º 5, pp. 55–63, 2013.

[26] Amazon Web Services, "SaaS Tenant Isolation Strategies," AWS Whitepaper, 2020.

[27] FinOps Foundation, "2025 FinOps Framework: Scopes and Cloud+," 2025. [En línea]. Disponible: https://www.finops.org/insights/2025-finops-framework/

[28] FinOps Foundation, "State of FinOps 2026," Linux Foundation, comunicado del 19 de febrero de 2026 (1.192 encuestados). [En línea]. Disponible: https://www.linuxfoundation.org/press/state-of-finops-survey-ai-value-and-skills-top-priorities-as-finops-matures-across-technology-value-98-manage-ai-90-saas-64-licensing-48-data-center-1

[29] FinOps Foundation, "State of FinOps 2025," 2025. [En línea]. Disponible: https://data.finops.org/2025-report/

[30] FinOps Foundation, *FinOps Open Cost and Usage Specification (FOCUS)*, versión 1.2, 2025. [En línea]. Disponible: https://focus.finops.org/

[31] Flexera, "2026 State of the Cloud Report," comunicado del 18 de marzo de 2026. [En línea]. Disponible: https://www.flexera.com/about-us/press-center/flexera-finds-cloud-value-is-rising-while-ai-waste-grows

[32] Zylo, "2026 SaaS Management Index," comunicado del 29 de enero de 2026. [En línea]. Disponible: https://zylo.com/news/2026-saas-management-index

[33] C+R Research, "Subscription service statistics and costs," encuesta a 1.000 consumidores de EE. UU., 2022. [En línea]. Disponible: https://crresearch.com/blog/subscription-service-statistics-and-costs/

[34] *Information technology — IT asset management — Part 1: IT asset management systems — Requirements*, ISO/IEC 19770-1:2017, 2017.

[35] R. H. Thaler, "Mental accounting matters," *Journal of Behavioral Decision Making*, vol. 12, n.º 3, pp. 183–206, 1999.

[36] J. T. Gourville y D. Soman, "Payment depreciation: The behavioral effects of temporally separating payments from consumption," *Journal of Consumer Research*, vol. 25, n.º 2, pp. 160–174, 1998.

[37] S. DellaVigna y U. Malmendier, "Paying not to go to the gym," *American Economic Review*, vol. 96, n.º 3, pp. 694–719, 2006.

[38] Zylo, "2025 SaaS Management Index," comunicado del 16 de enero de 2025. [En línea]. Disponible: https://zylo.com/news/2025-saas-management-index

[39] BerriAI, "LiteLLM — Spend tracking," documentación. [En línea]. Disponible: https://docs.litellm.ai/docs/proxy/cost_tracking
