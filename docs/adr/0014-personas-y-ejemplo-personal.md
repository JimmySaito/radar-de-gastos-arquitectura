# ADR-0014: Personas en el espacio personal y ejemplo generado al vuelo

- **Estado:** Aceptada · **Fecha:** 2026-11-19 · **Complementa:** ADR-0013

## Contexto
En un hogar o grupo, las suscripciones se reparten entre varias personas y muchas son compartidas (un plan
familiar de Netflix o Spotify). Saber "cuánto gasta Jimmy" exige asignar cada gasto a personas y repartir lo
compartido sin que las cifras dejen de cuadrar. Además, los usuarios nuevos necesitan un ejemplo para entender
el panel antes de cargar sus datos.

## Decisión
1. **Perfiles (`Profile`)** por dueño del espacio personal (`user:{sub}`): nombre y relación (Yo, Pareja, Hija…).
   Se gestionan en *Personal → Configuración* o desde el propio formulario de una suscripción.
2. **Asignación múltiple:** cada gasto personal tiene `member_ids`. Sin personas, queda "Sin asignar"; con varias,
   es compartido.
3. **Reparto exacto:** un cobro compartido entre n se divide con `split_evenly`, que reparte los centavos
   sobrantes de modo que las partes **suman exactamente** el cobro (100 = 33,34 + 33,33 + 33,33).
4. **Una sola fuente para las vistas por persona:** `for_member` produce la vista de una persona, con la fracción
   de cada gasto en el campo interno `share`. `by_member` se calcula **a partir de esa misma vista**, de modo que
   la tarjeta "Gasto por persona" y el panel filtrado por esa persona siempre muestran las mismas cifras. Se
   detectó una diferencia de un centavo entre ambos caminos durante la verificación y se corrigió unificándolos.
5. **Integridad al eliminar una persona:** sus gastos se conservan y la persona se quita de ellos (pasan a sin
   asignar o quedan entre las demás).
6. **Ejemplo personal generado al vuelo:** con `dataset=demo`, la API construye un hogar ficticio (Jimmy, María y
   Sofía) en un repositorio en memoria, con **fechas relativas a hoy**. Siempre hay cobros próximos, nunca se
   escribe en la base de datos y es de solo lectura: una escritura con `dataset=demo` va a los datos propios.

## Alternativas
- *Asignar cada gasto a una sola persona:* no representa los planes familiares.
- *Repartir con redondeo independiente por persona:* las partes podrían no sumar el total por uno o dos centavos.
- *Guardar el ejemplo en la base de datos:* sus fechas envejecen y requiere volver a sembrarlo.

## Consecuencias
- **+** Visión del gasto por persona y del total del hogar, coherentes entre sí al centavo en ciclos mensuales.
- **+** Un ejemplo siempre vigente que explica el producto sin datos reales.
- **−** En planes no mensuales (anual, trimestral), la suma de los equivalentes mensuales por persona puede
  diferir del equivalente total en un centavo, porque cada parte se redondea al dividir entre 12 o 3. Lo que
  cuadra exactamente es el cobro.
- **−** El reparto es siempre en partes iguales. Los porcentajes personalizados quedan como trabajo futuro.
