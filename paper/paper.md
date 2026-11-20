---
title: "Radar de gastos: cómo reunir el gasto en IA, nube y suscripciones sin perder exactitud"
author:
  - "Jimmy Arturo Mancera Cuesta"
  - "Escuela Colombiana de Ingeniería Julio Garavito"
date: "Noviembre de 2026"
lang: es
---

# Resumen

Hoy en día existen múltiples desafíos a la hora de entender el consumo que se realiza en tecnología, ya sea por
servicios de inteligencia artificial y de nube, que se cobra según el uso, o las **suscripciones de precio fijo**,
como licencias de software, herramientas de IA, plataformas de video o almacenamiento. Cada proveedor informa a su
manera, con unidades, monedas y fechas de cobro distintas, de modo que nadie puede responder a tiempo cuánto se gasta,
en qué, quién lo gasta y cuándo llega el próximo cobro. Este trabajo presenta **Radar de gastos**, una plataforma que
reúne ambos caminos en una sola vista, con un espacio denominado **Empresa**, que asigna el gasto a personas y equipos
y controla presupuestos y licencias, y un espacio **Personal**, que anticipa los cobros de un hogar y reparte las
suscripciones compartidas. La idea inicial era medir solo el consumo de IA y nube, pero al probarla con usuarios se
amplió a todas las suscripciones. Ese mismo cambio lo hizo **FinOps**, la práctica con la que las empresas reúnen a
finanzas, tecnología y negocio para controlar juntos el gasto en tecnología, que pasó de ocuparse solo de la nube a
incluir también el software por suscripción y la IA. La plataforma funciona en la nube de Amazon (AWS) y solo genera
costo cuando se usa, y se diseñó siguiendo marcos internacionales de buenas prácticas para administrar la tecnología
en las empresas, como COBIT e ISO/IEC 38500. Su principal garantía es la **exactitud**: ningún gasto se cuenta dos
veces, aunque los datos lleguen repetidos o los proveedores los corrijan después. Para comprobarlo, se sometió a
cientos de envíos simultáneos con un 15 % de datos repetidos a propósito y se provocó una caída del servicio. En
todos los casos los totales coincidieron al centavo con el gasto real, no se perdió información y el servicio se
recuperó solo. Las pruebas también mostraron dos puntos donde la plataforma se volvía lenta, que se corrigieron y se
midieron de nuevo.

**Palabras clave:** FinOps, gobierno de TI, gestión de suscripciones, gestión del gasto tecnológico, SaaS,
computación en la nube, arquitectura de software, AWS, inteligencia artificial generativa.

**Keywords:** FinOps, IT governance, subscription management, technology spend management, SaaS, cloud computing,
software architecture, AWS, generative AI.

# 1. Introducción

La inteligencia artificial generativa pasó en poco tiempo de ser un experimento a convertirse en un gasto diario de
muchas áreas. Un mismo departamento puede usar Claude para programar, un modelo de OpenAI dentro de un producto y
Gemini para analizar datos, y todo funciona sobre servicios de nube que se facturan por separado. Esta dispersión es
un problema de **gobierno de TI**, es decir, de cómo una organización dirige y controla su tecnología, y se manifiesta
de tres formas:

1. **Nadie ve el total a tiempo.** COBIT 2019, el marco internacional más usado para gobernar la tecnología en las
   empresas, exige conocer y asignar los costos tecnológicos para poder controlarlos (ISACA, 2018). Sin embargo, el
   85 % de las organizaciones considera que controlar su gasto en la nube es su principal desafío (Flexera, 2026).
2. **El gasto no tiene dueño.** Los proveedores asocian el consumo a códigos técnicos, proyectos o cuentas, no a
   personas ni a áreas. La norma ISO/IEC 38500, que fija principios para dirigir la tecnología, pide que cada uso
   tenga un responsable identificable (ISO/IEC, 2015). Sin ese responsable no se puede mostrar a cada área lo que
   gasta ni cobrárselo.
3. **El control llega tarde.** Los excesos se descubren cuando llega la factura: el 78 % de los líderes de TI
   consultados por Zylo recibió cobros inesperados relacionados con la IA (Zylo, 2026).

Para enfrentar estos problemas surgió **FinOps** (de *finanzas* y *operaciones*), una práctica en la que finanzas,
tecnología y negocio comparten la responsabilidad del gasto en tecnología. Funciona en tres etapas: primero
**informar** (saber cuánto se gasta y quién lo gasta), luego **optimizar** (reducir lo innecesario) y finalmente
**operar** (convertirlo en una rutina) (FinOps Foundation, s. f.; Storment y Fuller, 2023). La primera etapa parece
sencilla, pero tiene una dificultad poco tratada: los proveedores entregan los datos con horas de retraso, de 4 a 24
en el caso de Anthropic (Anthropic, 2026), los corrigen después de publicarlos y, al transmitirlos, a veces llegan
repetidos. Si se suman sin cuidado, el gasto reportado aparece inflado, y una herramienta financiera que muestra
cifras infladas pierde toda credibilidad.

Además, el consumo de IA y nube es solo una parte del gasto. Junto a él crecen las **suscripciones de precio fijo**:
licencias de software que las áreas compran sin pasar por TI, herramientas de IA pagadas con tarjeta corporativa y,
en el hogar, servicios de video, música o almacenamiento que se renuevan solos. En 2026, las áreas de negocio, y no
TI, controlaban el 81 % del gasto en software por suscripción de las organizaciones analizadas por Zylo, y ChatGPT era
la aplicación que más se pagaba con reembolsos de gastos (Zylo, 2026). En el hogar, las personas creen gastar en
suscripciones menos de la mitad de lo que realmente pagan (C+R Research, 2022). Que el gasto esté repartido en muchos
cobros pequeños y automáticos no lo hace menor: lo hace **invisible**.

## 1.1 Alcance y su evolución

El proyecto comenzó con un objetivo acotado: un tablero que mostrara cuánto consume cada miembro de un equipo en
servicios de IA (Claude, Gemini, ChatGPT) y de nube (AWS). Al conectarlo con cuentas reales aparecieron dos límites.
Primero, buena parte del uso de IA no se paga por consumo sino con **planes de precio fijo**, y los proveedores no
informan cuánto se usan. Segundo, quienes probaban el prototipo preguntaban por el resto de sus cobros,
de la empresa y personales, porque lo que querían saber no era cuánto habían usado, sino cuánto se les va al mes y
cuándo les cobran.

Por eso el proyecto pasó de medir el **consumo de IA y nube** a cubrir todo el **gasto tecnológico recurrente**, en
dos espacios separados, como resume la Tabla 1.

*Tabla 1. Alcance inicial y final del proyecto*

| Dimensión | Alcance inicial | Alcance final |
|---|---|---|
| Qué se mide | Consumo de IA y nube | Consumo de IA y nube, y suscripciones de precio fijo |
| Para quién | Equipos de una organización | Organizaciones (espacio Empresa) y hogares (espacio Personal) |
| A quién se asigna el gasto | Personas y equipos | Personas y equipos; en el hogar, miembros con cobros compartidos |
| Horizonte | Gasto ya ocurrido | Gasto ocurrido y próximos cobros, con calendario y proyección anual |
| De dónde salen los datos | Conexión con los proveedores | Lo anterior, más registro guiado de suscripciones |

La ampliación no obligó a rehacer lo construido: la parte que garantiza la exactitud se mantuvo y lo nuevo se agregó
como un módulo independiente. Que un cambio de este tamaño no exigiera rediseñar demuestra que la solución es fácil de
modificar, una de las cualidades que se buscaban. FinOps recorrió el mismo camino: en 2025 su organización de
referencia, la FinOps Foundation, amplió el marco para incluir el software por suscripción, las licencias y la IA, no
solo la nube (FinOps Foundation, 2025a), y en 2026 el 90 % de los equipos de FinOps ya gestionaba suscripciones de
software y el 98 %, gasto en IA (FinOps Foundation, 2026).

## 1.2 Pregunta de investigación y contribuciones

Este artículo responde a la pregunta: **¿Cómo construir una plataforma que reúna en una sola vista el gasto en IA,
nube y suscripciones, que admita nuevos proveedores con facilidad, que cueste poco operarla y que entregue cifras
exactas aunque los datos lleguen repetidos o corregidos?** Los aportes del trabajo son:

1. Un diseño de referencia para gestionar el gasto tecnológico de varios proveedores, con dieciocho decisiones
   documentadas y evaluado frente a once cualidades exigidas por el curso, como seguridad, disponibilidad y
   facilidad de cambio.
2. Un mecanismo para registrar el gasto que **no cuenta dos veces**, comprobado con pruebas automáticas y con pruebas
   de carga en la nube.
3. Un módulo de suscripciones que anticipa las fechas de cobro, reparte al centavo los cobros compartidos y suma por
   moneda sin inventar tipos de cambio.
4. La conexión de la solución con los marcos de gobierno de TI (COBIT 2019, ISO/IEC 38500 y FinOps), mediante
   indicadores y responsables definidos.
5. Un prototipo de código abierto cuyas pruebas miden la **exactitud** de las cifras y no solo la velocidad.

La sección 2 presenta los conceptos de base; la 3, lo que dice la literatura y por qué conviene consolidar el gasto;
la 4, el método de trabajo; la 5, la solución construida; la 6, los resultados; la 7, las conclusiones, y la 8, el
trabajo futuro. El Anexo A reúne el detalle técnico y el Anexo B, un glosario.

# 2. Marco teórico

## 2.1 Arquitectura empresarial

La arquitectura empresarial busca que la tecnología responda a los objetivos del negocio. Su marco más difundido,
TOGAF, propone recorrer en orden la visión, el negocio, los sistemas, la tecnología y el plan de transición (The Open
Group, 2022b), y ArchiMate ofrece una notación para dibujar cómo se conectan esos niveles (The Open Group, 2022a). En
este trabajo se usaron para partir del problema de negocio, la dispersión del gasto, y llegar a una solución concreta
con un plan para ponerla en marcha.

## 2.2 Arquitectura de software y cualidades del sistema

La arquitectura de software define las piezas de un sistema y cómo se relacionan. Bass et al. (2021) proponen
expresar lo que se espera del sistema con **escenarios de calidad**: situaciones concretas y medibles, como "si un
dato llega dos veces, el total no cambia". El método ATAM ayuda a priorizar esos escenarios y a detectar cuándo
mejorar una cualidad empeora otra (Kazman et al., 2000). Para documentar la solución se usaron el modelo C4, que
describe el sistema en cuatro niveles de detalle (Brown, s. f.), y los registros de decisiones o ADR, que guardan
cada decisión con sus razones (Nygard, 2011).

Para que el sistema pueda cambiar sin romperse se aplicaron tres ideas conocidas. La primera es separar las reglas
del negocio de la tecnología que las rodea, como un aparato que funciona con distintos enchufes (Cockburn, 2005). La
segunda es traducir los datos de todos los proveedores a un **formato común**, para que incorporar uno nuevo no
obligue a tocar los demás (Hohpe y Woolf, 2003). La tercera es separar el registro de los datos de su consulta, de
modo que cada uno se optimice por su lado (Fowler, 2011).

## 2.3 Computación en la nube sin servidores

En la modalidad **sin servidores** (*serverless*), la empresa no compra ni administra equipos: el proveedor de nube
ejecuta el programa solo cuando hay trabajo, lo amplía cuando aumenta la demanda y cobra únicamente por el uso real
(Jonas et al., 2019). Las guías de AWS recomiendan organizar el trabajo en **filas de espera** (colas) que absorben
los picos, y preparar el sistema para recibir un mismo mensaje más de una vez, porque esas filas no garantizan
entregarlo una sola vez (Amazon Web Services, s. f.).

## 2.4 Exactitud de los datos

Cuando un sistema está repartido en varias piezas que se comunican, los mensajes se reenvían si hay dudas sobre su
llegada. Por eso cada operación debe poder repetirse sin cambiar el resultado (Helland, 2012). Kleppmann (2017)
explica que no se puede evitar que un dato llegue dos veces, pero sí que se cuente dos veces. Bailis y Ghodsi (2013)
analizan cuándo los datos de un sistema así pueden considerarse al día. El Anexo A explica cómo se aplicaron estas
ideas.

# 3. Estado del arte

## 3.1 Gobierno de TI y FinOps

COBIT 2019 organiza el gobierno de TI en objetivos (ISACA, 2018). Tres son centrales para este trabajo: **gestionar
el presupuesto y los costos** (APO06), que exige asignar los costos a quienes los generan y compararlos con un
presupuesto; **gestionar los proveedores** (APO10), que pide conocer y supervisar los contratos vigentes; y
**gestionar los activos** (BAI09), que incluye el inventario de licencias. ISO/IEC 38500 establece seis principios
para dirigir la tecnología, entre ellos que cada uso tenga un responsable (ISO/IEC, 2015). FinOps y Storment y Fuller
(2023) llevan estos principios al gasto en nube y señalan que asignar cada costo a un responsable es el primer paso
de todo lo demás.

FinOps amplió su alcance en los últimos dos años. En 2025 la FinOps Foundation empezó a aplicar su marco también al
software por suscripción, las licencias, los centros de datos y la IA, un enfoque que llamó *Cloud+* (FinOps
Foundation, 2025a). Sus encuestas anuales muestran la velocidad del cambio: en 2025, el 63 % de los equipos de FinOps
ya gestionaba gasto en IA, frente al 31 % del año anterior, y el 65 % debía controlar el gasto en software por
suscripción (FinOps Foundation, 2025c); en 2026 esas cifras llegaron al 98 % y al 90 %, y el 64 % gestionaba
licencias (FinOps Foundation, 2026). El problema sigue abierto: el 85 % de las organizaciones considera el control del
gasto en la nube su principal desafío, y el gasto desperdiciado volvió a crecer, hasta el 29 %, por primera vez en
cinco años, impulsado por la IA (Flexera, 2026).

Para que los datos de todos los proveedores se puedan comparar, la FinOps Foundation publicó FOCUS, un formato común y
abierto para reportar costos y uso, cuya versión 1.2 incorporó el software por suscripción y las monedas múltiples
(FinOps Foundation, 2025b). FOCUS respalda la idea de un formato común que usa este trabajo, aunque está pensado para
los grandes proveedores de nube y no para suscripciones que una persona registra a mano.

En resumen, estos marcos dicen **qué** debe lograrse (ver el gasto, asignarlo y presupuestarlo) y, cada vez más,
**sobre qué** (todo el gasto tecnológico), pero no **cómo** construir una herramienta confiable cuando las fuentes
son muchas, se corrigen con el tiempo y en parte se registran a mano.

## 3.2 Gestión de licencias y del gasto en software por suscripción

La norma ISO/IEC 19770-1 define cómo llevar el inventario y el control de las licencias de software (ISO/IEC, 2017).
Aplicarla al software por suscripción, conocido como SaaS (*software as a service*), tiene una dificultad nueva: ya
no compra solo TI, sino cada área. Según el informe de Zylo de 2026, las áreas de negocio controlan el 81 % de ese
gasto y TI solo el 15 %; el gasto pagado con reembolsos creció un 267 % en un año, con ChatGPT como la aplicación más
reembolsada; el gasto en aplicaciones de IA creció un 108 % (393 % en organizaciones de más de 10.000 empleados); en
promedio, el 36 % de las licencias no se usa; y el 78 % de los líderes de TI recibió cobros inesperados relacionados
con la IA (Zylo, 2026). El informe de 2025 estimaba en 21 millones de dólares al año el gasto promedio en licencias
sin uso (Zylo, 2025). Aunque estas cifras vienen de una empresa del sector y deben leerse con cautela, describen el
mismo fenómeno: **el gasto existe, pero no está a la vista de quien debe controlarlo**.

## 3.3 Por qué las suscripciones escapan al control

La economía del comportamiento explica por qué las suscripciones se descontrolan. Thaler (1999) mostró que las
personas llevan **cuentas mentales** separadas por categorías y que los pagos pequeños y automáticos quedan fuera de
ellas. Gourville y Soman (1998) encontraron que, cuando el pago ocurre lejos del momento de uso, pesa menos en las
decisiones: lo que se cobra solo deja de sentirse como gasto. DellaVigna y Malmendier (2006) documentaron que quienes
pagan una mensualidad de gimnasio creen que irán más de lo que van, pagan más que si pagaran por visita y tardan
meses en cancelar.

Las encuestas lo confirman. En un estudio con 1.000 consumidores de Estados Unidos, los participantes calcularon que
gastaban 86 dólares al mes en suscripciones, pero al revisar cobro por cobro el promedio real fue de 219; el 74 % dijo
que es fácil olvidar los cobros recurrentes y el 42 % reconoció seguir pagando servicios que ya no usaba (C+R
Research, 2022). La conclusión para el diseño es clara: **una herramienta de control debe mostrar el cobro antes de
que ocurra**, no solo registrarlo después.

## 3.4 Herramientas existentes

El mercado ofrece buenas herramientas, pero cada tipo cubre solo una parte del gasto. La Tabla 2 resume lo que cubre
cada categoría; es una valoración general, no una evaluación de productos concretos.

*Tabla 2. Qué parte del gasto cubre cada tipo de herramienta (● = lo cubre; No = no lo cubre)*

| Categoría | Consumo de IA | Nube | Licencias de software | Suscripciones personales | Asigna el gasto a |
|---|---|---|---|---|---|
| Consola de cada proveedor (AWS, Anthropic, OpenAI) | Solo el propio | Solo el propio | No | No | Códigos o proyectos |
| Herramientas de control del gasto en nube | Si se paga por la nube | ● | Parcial | No | Etiquetas |
| Herramientas de gestión de licencias | No | No | ● | No | Usuario con licencia |
| Intermediarios de acceso a IA (p. ej. LiteLLM, de BerriAI, s. f.) | Solo lo que pasa por ellos | No | No | No | Código, usuario o equipo |
| Aplicaciones de finanzas personales | No | No | No | ● | La persona |
| **Radar de gastos** | ● | ● | ● | ● (registro manual) | Persona, equipo y miembros del hogar |

De la tabla salen dos vacíos. Ninguna categoría une el **consumo variable** con las **suscripciones de precio fijo**,
aunque para quien paga son el mismo presupuesto. Y las herramientas de empresa no contemplan lo personal, ni las
personales el consumo de IA de la empresa, aunque la frontera es cada vez más difusa: una misma persona paga un plan
de Claude o ChatGPT con su tarjeta y usa la IA de su empresa.

## 3.5 Por qué consolidar el gasto en una sola herramienta

Consolidar no es una comodidad visual, sino una condición para controlar el gasto. Hay cinco razones:

1. **No se controla lo que no se ve.** COBIT y la primera etapa de FinOps exigen visibilidad (ISACA, 2018; FinOps
   Foundation, s. f.). Si el gasto está repartido entre consolas, tarjetas y reembolsos, el total no existe en ningún
   lugar y se decide sobre una fracción. La diferencia entre los 86 dólares que las personas creen gastar y los 219
   que pagan (C+R Research, 2022), y el 81 % del gasto en software fuera del control de TI (Zylo, 2026), son la misma
   falla vista desde el hogar y desde la empresa.
2. **Cada gasto necesita un responsable.** ISO/IEC 38500 lo exige (ISO/IEC, 2015). Las consolas asignan el costo a
   códigos y proyectos; solo una vista consolidada puede asignarlo a personas, equipos o miembros del hogar.
3. **El control debe anticiparse.** El efecto de los pagos automáticos (Gourville y Soman, 1998) y los cobros
   inesperados que reporta el 78 % de los líderes de TI (Zylo, 2026) muestran que registrar el gasto después no
   basta. Un calendario de próximos cobros y presupuestos con alertas tempranas permiten actuar antes.
4. **El desperdicio se esconde entre fuentes.** Las licencias sin uso (36 % en promedio, según Zylo, 2026), las
   suscripciones duplicadas entre áreas o miembros del hogar y los planes de IA pagados dos veces solo se detectan al
   comparar las fuentes lado a lado.
5. **La IA se paga por todos los caminos.** La misma herramienta se paga por consumo, por suscripción individual, por
   licencia de la empresa o dentro de la factura de la nube; si se mira un solo camino, lo que se ahorra en uno
   reaparece en otro.

Consolidar también tiene costos: más conexiones que mantener, más información sensible en un mismo lugar y el riesgo
de mostrar cifras equivocadas con apariencia de verdad. Por eso la exactitud y la protección de las credenciales son
prioridades de este diseño.

## 3.6 Síntesis y vacío identificado

Los marcos de gobierno definen los objetivos y ya abarcan todo el gasto tecnológico; la economía del comportamiento
explica por qué el gasto recurrente escapa al control; y la ingeniería de software ofrece técnicas para que las
cifras sean exactas. Las herramientas existentes, en cambio, siguen especializadas por tipo de gasto. No se encontró
una propuesta que **integre** los tres frentes: una herramienta que reúna el consumo de varios proveedores de IA y
nube, con sus datos repetidos y corregidos, y las suscripciones de una organización y de un hogar. Este trabajo
propone y evalúa esa integración.

# 4. Metodología

## 4.1 Enfoque

Se siguió el enfoque de **ciencia del diseño**, que consiste en identificar un problema, construir una solución,
probarla y aprender de los resultados. El trabajo avanzó en siete pasos:

1. **Contexto y objetivos de negocio:** quiénes usarían la herramienta, qué les preocupa y seis objetivos medibles,
   por ejemplo conocer el gasto total en menos de un minuto o asignar al menos el 95 % del costo a un equipo.
2. **Escenarios de calidad:** once situaciones concretas que la solución debía resolver, ordenadas por importancia y
   dificultad (Kazman et al., 2000).
3. **Decisiones de diseño** para cada escenario, registradas con las alternativas descartadas.
4. **Arquitectura empresarial:** recorrido del ciclo de TOGAF, principios, capacidades del negocio y diferencias entre
   la situación actual y la deseada.
5. **Gobierno:** relación con COBIT 2019 e ISO/IEC 38500, indicadores y una matriz que define quién es responsable de
   cada tarea.
6. **Construcción por etapas**, escribiendo primero las pruebas de cada regla del negocio.
7. **Evaluación:** pruebas automáticas, pruebas de carga que verifican la exactitud, una caída provocada del servicio
   y análisis de las ventajas y desventajas de cada decisión.

Este enfoque permite que cada prueba cambie el problema, y así ocurrió: probar el primer prototipo con cuentas reales
mostró que el consumo de IA era solo una parte del gasto, y el objetivo se amplió como se explica en la sección 1.1.
Cada ampliación siguió el mismo procedimiento: una decisión documentada, un módulo independiente, pruebas antes de la
pantalla y verificación de que lo anterior seguía funcionando.

## 4.2 Tecnologías

La Tabla 3 resume las piezas de la solución, todas de AWS salvo las dos últimas, y por qué se eligieron.

*Tabla 3. Componentes de la solución*

| Componente | Qué hace | Por qué se eligió |
|---|---|---|
| Funciones en la nube (AWS Lambda) | Ejecutan el programa solo cuando hay trabajo | No cuestan nada cuando no se usan y crecen solas con la demanda |
| Fila de espera (Amazon SQS) | Guarda el trabajo pendiente | Absorbe los picos y evita que una falla detenga todo |
| Base de datos (Amazon DynamoDB) | Guarda el gasto y sus totales | Guarda varios cambios de una vez, o ninguno, y crece sin planearlo |
| Acceso e identidad (API Gateway y Cognito) | Controlan quién entra y qué ve | Usan estándares abiertos de inicio de sesión |
| Programador de tareas (EventBridge) | Pide a cada proveedor sus datos cada hora | Automatiza la recolección |
| Monitoreo (CloudWatch) | Registra el funcionamiento y envía alertas | Detecta problemas a tiempo |
| Tablero web | Muestra el gasto, los presupuestos y los cobros | También funciona en un computador personal, sin nube |
| Terraform y GitHub Actions | Instalan la plataforma y revisan cada cambio de forma automática | Cambios repetibles y controlados |

## 4.3 Principios de diseño

El diseño se apoya en cinco principios. Las reglas del negocio se separan de la tecnología, para poder cambiar de
base de datos o de proveedor sin reescribirlas. Los datos de todos los proveedores se traducen a un formato común.
Los totales se calculan al guardar cada dato y no al consultarlos, para que el tablero responda rápido. El trabajo
pasa por una fila de espera que absorbe los picos. Y cada operación puede repetirse sin alterar el resultado. El
Anexo A detalla cómo se aplicó cada principio.

# 5. Implementación

## 5.1 Visión general

Los datos llegan a la plataforma por dos caminos. En el primero, cada hora la plataforma pide a cada proveedor
conectado su consumo reciente. En el segundo, cualquier sistema de la organización puede enviar sus propios registros
de gasto de forma segura. Ambos caminos dejan el trabajo en una fila de espera; un proceso lo toma, lo traduce al
formato común y lo guarda. El tablero consulta los totales ya calculados, y una tarea diaria compara el gasto con los
presupuestos y envía alertas. La documentación del repositorio presenta este flujo en diagramas.

## 5.2 Conexión con los proveedores

Cada proveedor entrega sus datos de forma distinta, y la plataforma absorbe esas diferencias. Anthropic informa el
costo en centavos y en periodos de hasta 31 días (Anthropic, 2026); OpenAI informa el consumo por usuario, pero el
costo solo por proyecto (OpenAI, s. f.); AWS informa el gasto por servicio y por etiqueta de responsable; y Google lo
entrega en su herramienta de análisis de datos. Agregar un proveedor nuevo solo requiere un módulo adicional, sin
modificar los existentes.

## 5.3 Un registro que no cuenta dos veces

El corazón de la plataforma es su registro del gasto, que funciona como un libro contable. Cada gasto diario tiene
una identidad única, formada por el proveedor, el servicio, el responsable y la fecha. Cuando un dato llega, el
registro lo compara con lo que ya tenía y suma solo la diferencia: si el dato es idéntico, no hace nada; si el
proveedor lo corrigió, ajusta la diferencia; y si cambió el responsable, lo resta del anterior y lo suma al nuevo. El
gasto y sus totales se guardan juntos, en una sola operación que se completa entera o no se hace, de modo que los
totales siempre cuadran con el detalle.

Si dos procesos intentan modificar el mismo gasto al mismo tiempo, solo uno lo logra y el otro vuelve a intentarlo.
Como repetir un dato no suma nada, volver a procesar información es seguro. Y para que muchos procesos no tengan que
esperar turno para actualizar el mismo total, cada total se reparte en varias partes que se suman al consultarlo. El Anexo A presenta el procedimiento completo.

## 5.4 Seguridad y privacidad

Cada organización ve solo sus datos: la plataforma identifica la organización a partir de la sesión del usuario, no
de lo que este envía, lo que impide consultar datos ajenos, uno de los riesgos más comunes en este tipo de servicios
(OWASP Foundation, 2023). Las claves de acceso a los proveedores solo permiten leer el consumo, se guardan cifradas y
nunca se muestran en pantalla. Cada componente tiene únicamente los permisos que necesita y toda la información se
guarda cifrada.

## 5.5 Instalación, monitoreo y control de calidad

Toda la plataforma está descrita en archivos de configuración, de modo que se instala completa con un solo comando y
siempre de la misma forma. Un tablero de operación y alarmas por correo avisan cuando aumentan los errores, cuando el
sistema responde lento o cuando se acumula trabajo sin procesar. Cada cambio en el código pasa por revisiones
automáticas de calidad y seguridad que lo detienen si encuentran un problema nuevo.

El prototipo se instaló en un laboratorio académico de AWS, que tiene más restricciones que una cuenta normal; para
respetarlas se creó una configuración especial. El mismo programa funciona también en un computador
personal, con las mismas protecciones, como respaldo para las demostraciones.

## 5.6 Tablero

El tablero muestra el costo total, el volumen de uso de los servicios de IA, el equipo con más gasto, el costo diario
por proveedor o por equipo, las personas y los servicios que más consumen y el estado de los presupuestos, con iconos
y texto para que el color no sea la única señal. Distingue los **datos reales** de una **vista de ejemplo**, y una
pantalla de configuración permite a los administradores conectar proveedores, probar las claves sin guardarlas,
asignar responsables y definir presupuestos sin conocimientos técnicos.

El espacio **Empresa** agrega las licencias de software con su número de usuarios. En el espacio **Personal**, cada
persona registra sus suscripciones, de IA o de cualquier otro tipo, con su monto, moneda, frecuencia y fecha de
cobro. La plataforma calcula el calendario de cobros, incluso en los meses más cortos, el equivalente mensual y la
proyección anual, y suma por moneda para no usar tipos de cambio sin verificar. Se pueden crear perfiles para cada
miembro del hogar y repartir las suscripciones compartidas al centavo. La información personal es privada:
ni siquiera otros miembros de la misma organización pueden verla.

# 6. Resultados y evaluación

## 6.1 Calidad del software

La plataforma tiene 163 pruebas automáticas que revisan el 96,4 % del código en unos 15 segundos, sin necesidad de
conectarse a la nube. Las revisiones automáticas de calidad y de seguridad no encontraron problemas (Tabla A3 del
Anexo A). Algunas pruebas generan miles de combinaciones al azar de datos repetidos, corregidos y reasignados, y
comprueban que el total final siempre sea el correcto.

## 6.2 Pruebas de carga

Una **prueba de carga** simula a muchos usuarios usando el sistema al mismo tiempo, para ver cómo responde. Se
simularon tres situaciones: un uso constante, un uso que crece poco a poco y un pico repentino. En todas, la mitad de
los envíos traía datos de gasto y la otra mitad consultaba el tablero, y el **15 % de los datos se reenviaba a
propósito**, para comprobar que los repetidos no se sumaran. Al final se comparaba el total de la plataforma con la
suma real de los datos únicos.

Primero se probó en un computador personal: con 213 envíos repetidos, el error fue de 0,00 dólares. Luego se probó en
AWS, con una carga reducida para no agotar el crédito del laboratorio. La Tabla 4 resume los resultados en la nube.

*Tabla 4. Resultados de las pruebas de carga en AWS*

| Situación | Envíos | Datos aceptados | Tiempo de respuesta al recibir datos (95 % de los casos) | Exactitud |
|---|---|---|---|---|
| Uso constante | 2.400 | 100 % | Menos de 0,2 s | Total exacto |
| Uso creciente | 2.014 | 100 % | Menos de 0,35 s | Total exacto |
| Pico repentino | 1.051 | 100 % | Menos de 0,5 s | Total exacto |

**Exactitud.** Con 404 envíos repetidos, el total coincidió al centavo con el gasto real en las tres pruebas. Es la
confirmación, en un entorno real, de la garantía central de la plataforma.

**Recepción de datos.** La plataforma aceptó todos los datos y respondió en menos de medio segundo en el 95 % de los
casos, mejor que la meta, sin errores relevantes ni trabajo perdido.

**Primer punto lento: la actualización de los totales.** Todos los datos de una prueba afectaban los mismos totales,
así que los procesos tenían que esperar turno para actualizarlos, como una fila ante una sola caja. La plataforma
procesaba unos 100 registros por segundo y los datos tardaban de 7 a 8 minutos en verse en el tablero: seguían siendo
exactos, pero llegaban tarde. Se corrigió repartiendo cada total en varias partes, como abrir más cajas, y se
repitieron las pruebas (Tabla 5).

*Tabla 5. Efecto de repartir los totales, con la misma carga*

| Indicador | Antes | Después |
|---|---|---|
| Procesos que tuvieron que reintentar | Base | Entre 69 % y 86 % menos |
| Registros procesados por segundo (pico) | Cerca de 100 | Cerca de 245 |
| Tiempo hasta ver el dato en el tablero | 7 a 8 minutos | 10 a 17 segundos |
| Trabajo acumulado sin procesar | Hasta 390 envíos | Ninguno |
| Errores | Hasta 0,19 % | 0 % |
| Exactitud | Exacta al terminar | Exacta en todo momento |

**Segundo punto lento: las consultas del tablero.** Para calcular el total y el ranking, el tablero recorría el
gasto de todas las personas. Como cada dato de prueba simulaba una persona distinta, se acumularon más de 29.000, y
las consultas tardaron de 2 a 12 segundos. Se corrigió calculando el total a partir de los equipos, que son pocos, y
cargando el ranking de personas por separado. En el computador personal, el resumen pasó a leer siempre la
misma pequeña cantidad de información, sin importar cuántas personas haya; antes, con 60.000 personas, recorría más de
60.000 registros. Esta mejora no alcanzó a medirse en la nube.

**Incidente.** Al terminar la segunda ronda de pruebas, el laboratorio de AWS desactivó la cuenta, porque permite como
máximo 10 procesos simultáneos y la prueba llegó a más de 80. Se había revisado el límite general de AWS, pero no la
regla propia del laboratorio. Ahora la plataforma limita los procesos a 9, de modo que el exceso espera o se rechaza
en lugar de romper la regla. El incidente deja una lección de gobierno de TI: las reglas del proveedor
deben quedar programadas en la configuración, no solo escritas en un documento.

## 6.3 Prueba de disponibilidad

Para saber qué pasa si la plataforma pierde el acceso a sus datos, se apagó a propósito la sesión del laboratorio,
lo que le retira los permisos, y se observó el resultado desde afuera (Tabla 6).

*Tabla 6. Caída provocada del servicio en AWS*

| Qué se midió | Resultado |
|---|---|
| Consultas de datos | No disponibles durante la caída |
| Tablero, inicio de sesión y control de acceso | Disponibles todo el tiempo |
| Integridad de los datos | Ninguna pérdida ni duplicado: 6.313 registros antes y después |
| Recuperación | Automática, sin reinstalar nada |
| Detección | Una alarma avisó cerca de un minuto después |
| Respaldo | La versión en el computador personal siguió funcionando |

La prueba confirmó lo más importante para una herramienta financiera: los datos no se pierden y el servicio se
recupera solo. También reveló cuatro debilidades que no se veían en el computador personal: un chequeo que decía
"todo bien" aunque los datos no estuvieran disponibles, un mensaje de error que no explicaba nada al usuario, un
tablero que mostraba datos viejos sin advertirlo y una alarma que no reaccionaba cuando había poco uso. Las cuatro se
corrigieron. Al repetir la caída, el chequeo detectó el problema, el usuario vio un mensaje claro y llegaron por
correo los avisos de caída y de recuperación.

## 6.4 Evaluación por cualidad

El curso exigía once cualidades, llamadas atributos de calidad. La Tabla 7 resume cómo se cumplió cada una.

*Tabla 7. Evaluación por atributo de calidad*

| Atributo | Qué significa para el negocio | Evidencia | Estado |
|---|---|---|---|
| Confiabilidad | Las cifras son exactas | Totales exactos en todas las pruebas, también con datos repetidos | Verificado |
| Disponibilidad | El servicio sigue funcionando y se recupera | Caída provocada: sin pérdida de datos y recuperación automática | Verificado |
| Desempeño | Responde rápido | Datos recibidos en menos de medio segundo; consultas corregidas, pendientes de medir en la nube | Parcial |
| Escalabilidad | Soporta más uso sin rediseñarse | Absorbió los picos; con la mejora procesa 2,4 veces más | Verificado |
| Seguridad | Cada quien ve solo lo suyo | Pruebas de separación entre organizaciones y revisiones de seguridad sin fallas | Verificado |
| Interoperabilidad | Se conecta con otros sistemas | Proveedores y sistemas externos envían datos en un formato común | Verificado |
| Modificabilidad | Cambia sin romperse | Un proveedor nuevo es un módulo; el alcance se amplió sin rehacer lo existente | Verificado |
| Mantenibilidad | Es fácil de mantener | Revisiones automáticas de calidad sin hallazgos | Verificado |
| Facilidad de prueba | Se comprueba sin la nube | 96,4 % del código revisado por pruebas automáticas | Verificado |
| Reutilización | Sus piezas sirven en otros proyectos | Piezas de instalación reutilizadas cuatro veces | Verificado |
| Soporte | Se opera y diagnostica fácilmente | Alarmas, registros y guía de operación; causa de la caída identificada | Verificado |

## 6.5 Fortalezas

1. **Exactitud por diseño:** la regla que evita contar dos veces está aislada y probada a fondo.
2. **Costo proporcional al uso:** no hay equipos encendidos esperando trabajo.
3. **Facilidad para crecer:** cualquier sistema puede enviar sus datos, y los cambios de un proveedor no afectan a los
   demás.
4. **Gobierno integrado:** responsables, presupuestos con alertas e indicadores conectan la herramienta con COBIT y
   con FinOps.
5. **Una sola vista del gasto:** consumo y suscripciones, de la empresa y del hogar, en un mismo lugar, que es el
   vacío identificado en la Tabla 2.

## 6.6 Limitaciones

1. **Pruebas en la nube acotadas:** la carga se redujo por las reglas del laboratorio, no se hizo una prueba de larga
   duración y la mejora de las consultas no se midió en la nube porque el laboratorio se desactivó.
2. **El ranking de personas** todavía recorre a todas las personas, así que se vuelve más lento a medida que crecen.
3. **El costo de OpenAI por persona** debe estimarse, porque el proveedor solo lo informa por proyecto.
4. **Montos antes de descuentos e impuestos:** para el cierre contable hay que compararlos con la factura.
5. **Suscripciones registradas a mano:** a diferencia de algunas aplicaciones de finanzas personales, no se detectan
   cobros en cuentas bancarias o correos.
6. **Sin conversión de monedas:** los totales se presentan por moneda.
7. **Uso de los planes de IA de precio fijo:** los proveedores no lo informan; solo se registra su precio.
8. **Datos de varias organizaciones en una misma base:** están separados por la plataforma, pero un sector regulado
   podría exigir bases independientes (Amazon Web Services, 2020).
9. **Sin estudio con usuarios:** no se midió si la herramienta ayuda a reducir el gasto no deseado.

## 6.7 Mejoras propuestas

Calcular por adelantado el ranking de personas; compartir los resultados de consultas recientes entre todas las
copias de la plataforma; analizar el gasto histórico; reforzar la separación entre organizaciones; pronosticar el
gasto y detectar comportamientos inusuales; comparar automáticamente con las facturas; intercambiar datos en el
formato FOCUS (FinOps Foundation, 2025b); detectar suscripciones duplicadas entre personas o áreas; y convertir
monedas con una fuente oficial de tipos de cambio.

# 7. Conclusiones

- Controlar el gasto en IA y nube de varios proveedores es, ante todo, un problema de **información exacta**. Este
  trabajo mostró que puede resolverse con una solución en la nube de bajo costo si la regla de "no contar dos veces"
  se trata como una regla del negocio y no como un detalle técnico. Las cifras fueron exactas en todas las pruebas,
  en el computador personal y en AWS.
- Las pruebas en la nube mostraron que la exactitud no basta: también importa que los datos lleguen a tiempo y que el
  tablero responda rápido. Los dos puntos lentos encontrados se corrigieron sin tocar la parte central de la
  plataforma, y los datos pasaron a verse en segundos y no en minutos.
- El problema era más amplio de lo que planteaba la idea inicial. El gasto tecnológico de una organización o de un
  hogar se paga por consumo, por suscripción, por licencia y por reembolso, y gran parte se renueva sin que nadie lo
  vuelva a decidir. FinOps llegó a la misma conclusión al ampliar su marco (FinOps Foundation, 2025a), y los datos de
  mercado y de comportamiento explican por qué el gasto disperso y automático se escapa del control (Zylo, 2026; C+R
  Research, 2022; Gourville y Soman, 1998).
- **Una herramienta de gasto debe dar por hecho que los datos llegarán repetidos o corregidos.** Los mensajes se
  reenvían en todo sistema distribuido (Helland, 2012), las filas de espera pueden entregarlos dos veces (Amazon Web
  Services, s. f.) y los proveedores corrigen sus datos con horas de retraso (Anthropic, 2026). En este trabajo, 404
  envíos repetidos en AWS terminaron con un error de 0,00 dólares (sección 6.2).
- **Un formato común facilita sumar proveedores** y protege a la organización de los cambios de cada uno, como
  proponen Hohpe y Woolf (2003) y, para la facturación, FOCUS (FinOps Foundation, 2025b). Aquí, agregar un proveedor
  requirió un solo módulo, y la ampliación del alcance no modificó lo existente (sección 6.4).
- **Los marcos de gobierno funcionan mejor cuando se convierten en funciones concretas.** COBIT 2019 (ISACA, 2018),
  ISO/IEC 38500 (ISO/IEC, 2015) y FinOps (FinOps Foundation, s. f.) definen objetivos; la plataforma los convierte en
  indicadores, presupuestos con alertas y responsables. El incidente del laboratorio mostró el caso contrario: una
  regla que solo estaba escrita no protegió nada hasta que se programó en la configuración (sección 6.2).
- **Reunir el consumo y las suscripciones en una sola vista es una condición para controlar el gasto, no una
  comodidad.** El gasto disperso y automático se escapa del control por razones de comportamiento (Thaler, 1999;
  Gourville y Soman, 1998) y de organización (Zylo, 2026), y las personas subestiman su gasto en suscripciones en más
  de la mitad (C+R Research, 2022). Ver el total, asignar responsables, anticipar cobros y detectar duplicados exige
  reunir las fuentes (sección 3.5), y ninguna herramienta existente cubre ambos caminos (Tabla 2).

# 8. Trabajo futuro

- **Consultas en la nube:** medir en AWS la velocidad del tablero después de la mejora de las consultas.
- **Pruebas completas:** repetir las pruebas de carga con el volumen previsto y durante más tiempo, en una cuenta sin
  las restricciones del laboratorio.
- **Fallas durante la recolección:** repetir la caída provocada mientras se recogen datos de los proveedores.
- **Ajuste de capacidad:** definir en cuántas partes conviene repartir cada total según el volumen de uso.
- **Pronóstico y alertas inteligentes:** anticipar el gasto y detectar comportamientos inusuales.
- **Sectores regulados:** evaluar bases de datos independientes para cada organización.
- **Intercambio de datos:** adoptar FOCUS como formato de intercambio (FinOps Foundation, 2025b).
- **Evaluación con usuarios:** medir si la vista consolidada ayuda a reducir el gasto no deseado.

# Referencias bibliográficas

Amazon Web Services. (s. f.). *AWS Well-Architected Framework: Serverless applications lens*. https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/

Amazon Web Services. (2020). *SaaS tenant isolation strategies* [Documento técnico]. Amazon Web Services.

Anthropic. (2026). *Usage and Cost Analytics API*. Claude Platform Docs. https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api

Bailis, P., y Ghodsi, A. (2013). Eventual consistency today: Limitations, extensions, and beyond. *Communications of the ACM, 56*(5), 55–63.

Bass, L., Clements, P., y Kazman, R. (2021). *Software architecture in practice* (4.ª ed.). Addison-Wesley.

BerriAI. (s. f.). *LiteLLM: Spend tracking*. https://docs.litellm.ai/docs/proxy/cost_tracking

Brooker, M. (2015). *Exponential backoff and jitter*. AWS Architecture Blog. https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

Brown, S. (s. f.). *The C4 model for visualising software architecture*. https://c4model.com

C+R Research. (2022). *Subscription service statistics and costs*. https://crresearch.com/blog/subscription-service-statistics-and-costs/

Cockburn, A. (2005). *Hexagonal architecture*. https://alistair.cockburn.us/hexagonal-architecture/

DeBrie, A. (2020). *The DynamoDB book*.

DellaVigna, S., y Malmendier, U. (2006). Paying not to go to the gym. *American Economic Review, 96*(3), 694–719.

FinOps Foundation. (s. f.). *FinOps Framework*. https://www.finops.org/framework/

FinOps Foundation. (2025a). *2025 FinOps Framework: Scopes and Cloud+*. https://www.finops.org/insights/2025-finops-framework/

FinOps Foundation. (2025b). *FinOps Open Cost and Usage Specification (FOCUS)* (versión 1.2). https://focus.finops.org/

FinOps Foundation. (2025c). *State of FinOps 2025*. https://data.finops.org/2025-report/

FinOps Foundation. (2026, 19 de febrero). *State of FinOps 2026* [Comunicado de prensa]. Linux Foundation. https://www.linuxfoundation.org/press/state-of-finops-survey-ai-value-and-skills-top-priorities-as-finops-matures-across-technology-value-98-manage-ai-90-saas-64-licensing-48-data-center-1

Flexera. (2026, 18 de marzo). *2026 State of the Cloud Report* [Comunicado de prensa]. https://www.flexera.com/about-us/press-center/flexera-finds-cloud-value-is-rising-while-ai-waste-grows

Fowler, M. (2011). *CQRS*. https://martinfowler.com/bliki/CQRS.html

Gourville, J. T., y Soman, D. (1998). Payment depreciation: The behavioral effects of temporally separating payments from consumption. *Journal of Consumer Research, 25*(2), 160–174.

Helland, P. (2012). Idempotence is not a medical condition. *Communications of the ACM, 55*(5), 56–65.

Hohpe, G., y Woolf, B. (2003). *Enterprise integration patterns: Designing, building, and deploying messaging solutions*. Addison-Wesley.

ISACA. (2018). *COBIT 2019 framework: Governance and management objectives*. ISACA.

ISO/IEC. (2015). *Information technology — Governance of IT for the organization* (ISO/IEC 38500:2015).

ISO/IEC. (2017). *Information technology — IT asset management — Part 1: IT asset management systems — Requirements* (ISO/IEC 19770-1:2017).

Jonas, E., Schleier-Smith, J., Sreekanti, V., Tsai, C.-C., Khandelwal, A., Pu, Q., Shankar, V., Carreira, J., Krauth, K., Yadwadkar, N., Gonzalez, J. E., Popa, R. A., Stoica, I., y Patterson, D. A. (2019). *Cloud programming simplified: A Berkeley view on serverless computing* (Informe técnico UCB/EECS-2019-3). University of California, Berkeley.

Kazman, R., Klein, M., y Clements, P. (2000). *ATAM: Method for architecture evaluation* (Informe técnico CMU/SEI-2000-TR-004). Software Engineering Institute, Carnegie Mellon University.

Kleppmann, M. (2017). *Designing data-intensive applications*. O'Reilly Media.

Kung, H. T., y Robinson, J. T. (1981). On optimistic methods for concurrency control. *ACM Transactions on Database Systems, 6*(2), 213–226.

MacIver, D. R., Hatfield-Dodds, Z., et al. (2019). Hypothesis: A new approach to property-based testing. *Journal of Open Source Software, 4*(43), 1891. https://doi.org/10.21105/joss.01891

Nygard, M. (2011, 15 de noviembre). *Documenting architecture decisions*. Cognitect. https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions

OpenAI. (s. f.). *Usage API and Costs API reference*. OpenAI Platform Docs. https://platform.openai.com/docs/api-reference/usage

OWASP Foundation. (2023). *OWASP API Security Top 10*. https://owasp.org/API-Security/editions/2023/en/0x11-t10/

Storment, J. R., y Fuller, M. (2023). *Cloud FinOps: Collaborative, real-time cloud value decision making* (2.ª ed.). O'Reilly Media.

Thaler, R. H. (1999). Mental accounting matters. *Journal of Behavioral Decision Making, 12*(3), 183–206.

The Open Group. (2022a). *ArchiMate 3.2 specification*. The Open Group.

The Open Group. (2022b). *The TOGAF standard* (10.ª ed.). The Open Group.

Zylo. (2025, 16 de enero). *2025 SaaS Management Index* [Comunicado de prensa]. https://zylo.com/news/2025-saas-management-index

Zylo. (2026, 29 de enero). *2026 SaaS Management Index* [Comunicado de prensa]. https://zylo.com/news/2026-saas-management-index

# Anexo A. Detalle técnico

Este anexo reúne el detalle técnico para quien quiera revisarlo; el repositorio de arquitectura amplía cada punto
con diagramas C4, informes de pruebas y dieciocho registros de decisión (ADR-0001 a ADR-0018). Los temas del cuerpo
del artículo se justifican en estos registros:

- **Suscripciones de IA de precio fijo** (sección 1.1): ADR-0012.
- **Espacios Empresa y Personal, y miembros del hogar** (secciones 1.1 y 5.6): ADR-0013 y ADR-0014.
- **Pantalla de configuración sin consola de AWS** (sección 5.6): ADR-0011.
- **Totales repartidos en varias partes** (secciones 5.3 y 6.2): ADR-0015.
- **Consultas del tablero más rápidas** (sección 6.2): ADR-0016.
- **Configuración para el laboratorio y límite de procesos** (secciones 5.5 y 6.2): ADR-0017.
- **Versión local equivalente como respaldo** (sección 5.5): ADR-0018.

## A.1 Arquitectura y patrones

La solución sigue una arquitectura hexagonal, de puertos y adaptadores (Cockburn, 2005), con un modelo de datos
canónico (Hohpe y Woolf, 2003) y separación de escritura y lectura con totales precalculados (CQRS, Fowler, 2011).
Usa conectores intercambiables por proveedor (Adapter, Strategy y Registry), una cola SQS con cola de mensajes
fallidos (DLQ), consumidores en paralelo con respuesta por lote parcial, control de concurrencia optimista (Kung y
Robinson, 1981), reintentos con espera exponencial aleatoria (Brooker, 2015), totales repartidos en *shards*
(ADR-0015), caché de lectura con vencimiento y consultas separadas según el número de valores de cada dimensión
(ADR-0016).

## A.2 Conectores

Cada conector traduce la respuesta de su proveedor a `UsageRecord`, un hecho diario inmutable con identidad natural
(tenant, proveedor, servicio, principal, fecha) y métricas sumables (tokens de entrada, salida y caché, solicitudes y
costo en `Decimal`):

- **Anthropic:** *Usage and Cost Analytics API* con el SDK oficial, agrupada por `actor` y `model`; el costo llega en
  centavos y las ventanas se dividen en tramos de 31 días (Anthropic, 2026).
- **OpenAI:** la API de uso agrupa tokens por usuario o llave, y la de costos solo por proyecto (OpenAI, s. f.;
  ADR-0006).
- **AWS:** Cost Explorer por servicio y etiqueta `owner`, mediante `AssumeRole` con `ExternalId` en la cuenta
  pagadora.
- **Google:** consulta parametrizada a la exportación de facturación en BigQuery, con validación del nombre de tabla.

## A.3 Algoritmo del registro

La función pura `compute_deltas(previo, nuevo, atribución)` devuelve el ajuste para cada total (fecha × proveedor ×
{persona, equipo, servicio}): en la primera escritura suma el valor en tres totales; si el dato es idéntico, no hace
nada; si se revisó, suma la diferencia; y si cambió la atribución, resta de los totales anteriores y suma en los
nuevos. El adaptador de DynamoDB lo aplica como muestra la Figura A1.

*Figura A1. Algoritmo de escritura del registro*

```
repetir hasta 8 veces:
    previo ← GetItem(hecho, ConsistentRead)
    si sin_cambios(previo, nuevo): devolver UNCHANGED
    TransactWriteItems(
        Put(hecho, version = v+1, condición: version = v  |  attribute_not_exists),
        Update(total_i, ADD Δ_i)  para cada total)
    si éxito: devolver CREATED | REVISED
    si ConditionalCheckFailed o TransactionConflict: esperar U(0, base·2^intento)
lanzar ConcurrencyError  → el mensaje vuelve a SQS y, tras 5 intentos, a la DLQ
```

La condición sobre versión implementa el control optimista: si dos procesos leyeron la misma versión, solo uno
confirma y el otro relee y reintenta. El hecho y sus totales se guardan en la misma transacción. Cada total se reparte
en *N* *shards*, elegidos por el identificador del hecho para que sus revisiones toquen siempre las mismas celdas, y
la lectura los suma (ADR-0015).

## A.4 Modelo de datos

Se usa una tabla única de DynamoDB con claves compuestas (DeBrie, 2020). Los hechos se guardan en
`T#{tenant}#F#{mes}` y los totales en `T#{tenant}#A#{dimensión}#{mes}`, con `SK = fecha#proveedor#valor`; una consulta
de 90 días lee como máximo cuatro particiones por dimensión. El resumen solo lee las dimensiones con pocos valores
(equipos y servicios), y el ranking de personas se pide aparte (ADR-0016).

## A.5 Cifras detalladas de las pruebas

*Tabla A1. Pruebas de carga en el computador personal*

| Escenario | Peticiones | req/s | Registros/s | Lotes repetidos | Ingesta p50/p95/p99 (ms) | Lectura p50/p95/p99 (ms) | Errores | Costo esperado = observado (USD) |
|---|---|---|---|---|---|---|---|---|
| Carga constante | 1.049 | 28,2 | 287,4 | 75 | 593 / 2.297 / 3.152 | 1.073 / 2.796 / 6.383 | 1,8 % | 266.870,15 = 266.870,15 |
| Carga creciente | 964 | 28,4 | 322,8 | 78 | 355 / 1.875 / 2.490 | 606 / 3.034 / 5.535 | 2,1 % | 274.696,88 = 274.696,88 |
| Pico repentino | 688 | 22,9 | 235,2 | 60 | 246 / 1.165 / 1.456 | 326 / 1.645 / 5.371 | 2,5 % | 177.450,48 = 177.450,48 |

Los errores locales correspondieron solo a consultas que superaron el tiempo de espera del cliente con el equipo
saturado; el 100 % de los datos enviados fue aceptado.

*Tabla A2. Pruebas de carga en AWS, primera ronda*

| Escenario | Peticiones | Registros/s | Lotes repetidos | Ingesta p50/p95 (ms) | Lectura p50/p95 (ms) | Errores | Conflictos OCC | DLQ | Costo esperado = observado (USD) |
|---|---|---|---|---|---|---|---|---|---|
| Carga constante | 2.400 | 213,3 | 170 | 130 / 199 | 1.027 / 1.953 | 0 % | 24.262 | 0 | 648.727,51 = 648.727,51 |
| Carga creciente | 2.014 | 147,2 | 158 | 129 / 346 | 4.780 / 10.113 | 0,05 % | 16.188 | 0 | 525.235,32 = 525.235,32 |
| Pico repentino | 1.051 | 90,4 | 76 | 132 / 481 | 5.082 / 12.032 | 0,19 % | 8.137 | 0 | 279.914,39 = 279.914,39 |

*Tabla A3. Verificación del software*

| Indicador | Resultado |
|---|---|
| Pruebas automáticas | 163 (112 unitarias, 2 de propiedades con Hypothesis, 19 de integración con AWS emulado y 30 de la API) |
| Cobertura | 96,4 % de líneas y ramas (umbral: 80 %) |
| Tipado estático | `mypy --strict`: 0 errores en 41 módulos |
| Estilo y seguridad del código | `ruff` y `bandit`: 0 hallazgos; `pip-audit`: 0 vulnerabilidades conocidas |
| Seguridad de la infraestructura | Checkov: 242 controles aprobados, 0 fallidos y 26 excepciones justificadas |

Las pruebas de propiedades usan Hypothesis (MacIver et al., 2019). La segunda ronda en AWS, con los totales
repartidos, y la prueba de disponibilidad se detallan en las secciones 8.4 y 10 del repositorio de arquitectura; la
Tabla 5 resume su efecto.

# Anexo B. Glosario

- **ADR (registro de decisión de arquitectura):** documento breve que justifica una decisión de diseño con sus
  alternativas y consecuencias.
- **Arquitectura empresarial:** disciplina que alinea la tecnología de una organización con sus objetivos de negocio.
- **Atributo de calidad:** cualidad que debe tener un sistema además de funcionar, como seguridad, disponibilidad o
  facilidad de cambio.
- **AWS (Amazon Web Services):** servicio de computación en la nube de Amazon.
- **COBIT 2019:** marco internacional de buenas prácticas para gobernar y gestionar la tecnología en las empresas.
- **Control optimista:** forma de manejar cambios simultáneos en la que todos avanzan y, si chocan, uno reintenta.
- **Fila de espera (cola de mensajes):** lugar donde se guarda el trabajo pendiente hasta que un proceso lo atiende.
- **FinOps:** práctica en la que finanzas, tecnología y negocio comparten la responsabilidad de controlar el gasto en
  tecnología.
- **Gobierno de TI:** forma en que una organización dirige, controla y rinde cuentas sobre su tecnología.
- **Idempotencia:** propiedad de una operación que puede repetirse sin cambiar el resultado.
- **ISO/IEC 38500:** norma internacional con los principios para dirigir el uso de la tecnología en una organización.
- **Nube:** servicios de cómputo y almacenamiento que se alquilan por internet en lugar de comprar equipos propios.
- **Prueba de carga:** simulación de muchos usuarios a la vez para medir cómo responde un sistema.
- **Registro del gasto (ledger):** libro donde se guarda cada gasto y sus totales.
- **SaaS (software como servicio):** software que se paga por suscripción y se usa a través de internet.
- **Serverless (sin servidores):** modalidad de nube en la que el proveedor administra los equipos y se paga solo por
  uso.
- **Shard:** cada una de las partes en que se reparte un total para que varios procesos lo actualicen sin esperar
  turno.
- **Tenant:** cada organización que usa la plataforma, con sus datos separados de los demás.
- **Token:** unidad en la que los servicios de IA miden y cobran el texto que procesan.
