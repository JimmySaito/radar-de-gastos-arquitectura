# ADR-0013: Espacios Empresa y Personal con gastos recurrentes

- **Estado:** Aceptada · **Fecha:** 2026-11-19 · **Reemplaza en parte:** ADR-0012 (conector "Suscripción (costo fijo)")

## Contexto
Los usuarios quieren entender **cuánto gastan al mes** tanto en la empresa como en su vida personal, y no solo
en IA: streaming, música, software, almacenamiento o gimnasio. El conector de "suscripción de costo fijo"
(ADR-0012) mezclaba gastos personales con el consumo corporativo, no registraba la **fecha de cobro** y
prorrateaba por día, lo que no corresponde a cómo se cobran las suscripciones.

## Decisión
1. **Dos espacios en la navegación principal:** *Empresa* (consumo de APIs, atribución, presupuestos y licencias
   SaaS) y *Personal* (mis suscripciones). Cada uno tiene su panel y su configuración, que se abre con el engranaje
   según el espacio activo.
2. **Entidad `RecurringExpense`** (dominio puro, `domain/recurring.py`): monto, moneda, ciclo (semanal, mensual,
   trimestral o anual) y una **fecha ancla de cobro**; opcionalmente fechas de inicio y cancelación y, en empresa,
   usuarios, responsable y equipo.
   - Los cobros se proyectan **siempre desde el ancla** (no de forma acumulativa) y ajustan al último día del mes:
     un día 31 cae el 30 o el 28/29 sin desplazar los meses siguientes.
   - El equivalente mensual normaliza los ciclos (anual / 12, semanal × 52 / 12).
3. **Propiedad de los datos:**
   - Lo personal pertenece a la persona (`user:{sub}` del token). Ningún otro miembro del tenant, ni un admin, lo
     ve por la API.
   - Lo de empresa pertenece al tenant (`tenant:{id}`): todos lo leen y solo `admins` escribe.
4. **Multimoneda sin conversión:** los totales se agrupan por moneda ISO 4217. No se convierte, para no introducir
   tipos de cambio no verificados en cifras financieras (P1).
5. **Catálogos declarativos** (`recurring_catalog.py`) de servicios comunes por espacio, con categoría y ciclo
   sugeridos y **sin precios** (varían por país y en el tiempo).
6. **Avisos:** el resumen marca los cobros a 3 días o menos (`soon`). La UI los señala con ícono y texto, no solo
   con color.

## Alternativas
- *Mantener el conector de costo fijo:* sin fecha de cobro ni separación personal/empresa, y con un prorrateo
  diario poco intuitivo.
- *Convertir a una moneda base con una API de tipos de cambio:* agrega una dependencia externa y cifras estimadas;
  queda como trabajo futuro y opcional.
- *Guardar lo personal en el navegador (localStorage):* se pierde al cambiar de equipo y no sirve en la nube. Se
  usa solo para preferencias (moneda predeterminada).

## Consecuencias
- **+** Una visión del gasto mensual completo, personal y corporativo, con fechas de cobro y renovaciones próximas.
- **+** La lógica de calendario es pura y está probada con casos límite (fin de mes, años bisiestos) y con pruebas
  basadas en propiedades.
- **−** Sin conversión de moneda no hay un "total general" único cuando hay varias monedas.
- **−** Los avisos solo se muestran en la aplicación. Las notificaciones por correo (SNS por persona) quedan como
  trabajo futuro.
- **−** Los registros creados con el conector "Suscripción (costo fijo)" siguen funcionando (el tipo sigue
  registrado), pero ya no se ofrece en el formulario. Conviene migrarlos a *Licencias y suscripciones*.
