# Mundo Caribe Tours — Estado del proyecto

_Última actualización: 2026-09-10, tras mover los datos del huésped exclusivamente al checkout final._

## Último commit y estado del deploy

- **Commit:** `431db64` — "Mueve datos del huésped (nombre, hotel, ubicación, pago) sólo al checkout final" (rama `main`, subido a GitHub).
- **Deploy:** carpeta `~/Desktop/mundo-caribe-cloudflare-deploy` regenerada y verificada (sin campos de huésped en `bw-*`, `CART_VERSION` sin cambios), lista para arrastrar a Cloudflare — confirmar en vivo en `https://mundo-caribe-tours.ignacioagustindannunzio.workers.dev/` después de subirla. El deploy a Cloudflare **es manual**: no hay auto-deploy configurado desde GitHub todavía — cada cambio requiere regenerar (`python3 scripts/generate_site.py`), copiar `index.html`, `assets/`, `categoria/`, `tour/` y `todos-los-tours/` a esa carpeta, y arrastrarla a Cloudflare ("New deployment").
- Netlify quedó pausado y desconectado de GitHub (decisión tomada por consumo de créditos); ya no es el host activo.

## Tabla final de disponibilidad (17 tours)

| Tour (slug) | Texto visible (`availability`) | Tipo (`schedule`) | Detalle |
|---|---|---|---|
| chichen-itza | Diario | `daily` | Confirmado por Agustín — antes decía "Consulta disponibilidad" |
| chichen-itza-plus | Diario | `daily` | Confirmado por Agustín — antes decía "Consulta disponibilidad" |
| tulum | Diario | `daily` | |
| tulum-casa-tortuga | Consulta disponibilidad | `on_request` | **Pendiente**: no confirmado si tiene días fijos |
| tulum-tortugas-akumal | Martes a domingo | `weekly` [mar,mié,jue,vie,sáb,dom] | Lunes bloqueado |
| coba-sunset | Lunes, miércoles y sábados | `weekly` [lun,mié,sáb] | |
| holbox | Lunes, miércoles y viernes | `weekly` [lun,mié,vie] | |
| isla-contoy-mujeres | Martes, jueves y domingos | `weekly` [mar,jue,dom] | |
| isla-mujeres-catamaran | Diario | `daily` | |
| bacalar | Martes, jueves y sábados | `weekly` [mar,jue,sáb] | |
| cozumel | Diario | `daily` | |
| tiburon-ballena | Junio a septiembre | `seasonal` [jun-sep] | Tentativa dentro de temporada, sin días de semana fijos conocidos |
| atv-casa-jaguar | Diario | `daily` | |
| akumal-cenote-nohoch | Consulta disponibilidad | `on_request` | **Pendiente**: no confirmado si tiene días fijos |
| akumal-expres | Martes a domingo | `weekly` [mar,mié,jue,vie,sáb,dom] | Lunes bloqueado |
| casa-tortuga-cenotes | Diario | `daily` | |
| pesca-yate-cancun | Salida: Marina Kaybal, Z.H. Cancún | `on_request` | **Confirmado** todo el año — aviso propio: "Agustín confirma disponibilidad según yate, clima y logística" (vía `schedule_note`, no el aviso genérico) |

Fuente única de verdad: campo `schedule` en `scripts/generate_site.py`, transcripto a mano por Agustín tour por tour — nunca se interpreta el texto de `availability` en tiempo de ejecución.

## Cómo funciona el calendario propio

Reemplaza por completo el `<input type="date">` nativo (no podía bloquear días de semana puntuales ni abrir de forma consistente entre navegadores).

- **Un solo campo clickeable**: un `<button>` "trigger" que ocupa todo el campo — se abre tocando cualquier parte, no solo un ícono.
- **Popover con grilla mensual**: navegación mes anterior/siguiente, encabezado de días D-L-M-M-J-V-S.
- **Bloqueo visual real**: los días no disponibles usan `aria-disabled="true"` (no el atributo `disabled` nativo) — se ven apagados y tachados, pero siguen siendo alcanzables con flechas del teclado para que un usuario de teclado pueda *ver* que están bloqueados, no que se salteen en silencio. Ni clic ni Enter los seleccionan.
- **Teclado completo**: Enter/Espacio abre el trigger y selecciona el día enfocado (roving tabindex); flechas ←→↑↓ navegan dentro del mes; Escape cierra y devuelve el foco al campo; clic afuera también cierra.
- **Mensaje si se intenta un día bloqueado**: "Ese día no está disponible para este tour." (antes no pasaba nada).
- **Zona horaria**: "hoy" se calcula con `Intl.DateTimeFormat({timeZone: 'America/Cancun'})`, nunca con la hora local del dispositivo del visitante. El día de semana de cualquier fecha se calcula con aritmética UTC pura (`Date.UTC` + `getUTCDay`), inmune al huso horario de quien mira la pantalla.
- **Un calendario por tour**: cada tour agregado al carrito guarda su propia fecha — nunca un calendario ni una fecha compartida entre varios tours del mismo carrito.

## Reglas de validación

Función única `isDateAllowed(iso, schedule)` en `assets/site.js`, invocada en **tres** momentos (bloquear visualmente no alcanza por sí solo):

1. Al pintar el calendario (decide qué celdas quedan `aria-disabled`).
2. Al tocar "Agregar al carrito" — vuelve a chequear la fecha elegida contra el `schedule` de ese tour antes de guardarla.
3. Al tocar "Reservar todo por WhatsApp" — recorre **cada tour del carrito** y revalida su fecha contra su propio `schedule` guardado; si alguna ya no es válida, bloquea el envío y señala cuál tour corregir.

Reglas por tipo:
- `weekly`: sólo los días de semana listados en `days` (convención `Date.getDay()`: 0=domingo…6=sábado).
- `daily`: cualquier fecha futura.
- `seasonal`: cualquier fecha futura dentro de los meses listados en `months`.
- `on_request`: cualquier fecha futura, siempre marcada tentativa.
- En todos los casos: las fechas pasadas (según "hoy" en Cancún) quedan bloqueadas.

## Checkout final (agregado 2026-09-10)

- **Editar un tour ya agregado**: cada ítem del carrito tiene un `id` propio; el botón "Editar" navega a la página de ese tour, la precarga con la fecha/pasajeros/opción guardados (banner "Estás editando este tour en tu carrito", con link para cancelar sin guardar), y al confirmar reemplaza el ítem en el carrito en vez de duplicarlo. `CART_VERSION` 4→5.
- **Paso de revisión antes de enviar**: "Revisar y reservar" valida todo (nombre, hotel, habitación, método de pago, fecha de cada tour) y muestra un resumen de solo lectura — cada tour con su fecha/pax/precio, total, y los datos del huésped — antes de "Confirmar y enviar por WhatsApp" (que vuelve a validar una vez más). "Volver a editar" regresa al formulario sin perder nada.
- Probado de punta a punta en local: agregar, editar sin duplicar, cancelar edición sin guardar, entrar a revisión, volver a editar, y el mensaje final de WhatsApp con el formato esperado.

## Datos del huésped sólo en el checkout (agregado 2026-09-10)

- Cada página de tour ahora pide únicamente **fecha** y **pasajeros** (adultos/niños/infantes según el tipo de tour) — el widget de reserva del tour ya no tiene campos de nombre, hotel, habitación, ubicación ni método de pago.
- **Nombre completo, hotel, habitación, ubicación y método de pago se piden una única vez**, en el carrito/checkout — sin cambios ahí, ya funcionaban así (ver "Checkout final" arriba).
- El total mostrado en la página de cada tour ahora es el precio base en USD, sin recargo de tarjeta ni conversión a MXN (esa lógica depende del método de pago, que sólo se elige en el checkout). El precio final con recargo/conversión sigue viéndose correctamente en el carrito y en el mensaje de WhatsApp.
- El ítem que se guarda en el carrito nunca tuvo datos del huésped (siempre fueron sólo campos propios del tour: fecha, pax, precio, id) — este cambio es puramente de UI/orden de los pasos, no tocó la estructura de datos ni requirió bump de `CART_VERSION`.
- Probado en local: agregar al carrito sin ver campos de huésped, editar un ítem (banner y precarga de fecha/pax sin campos de huésped), guardar sin duplicar, y el paso de revisión + mensaje de WhatsApp siguen mostrando nombre/hotel/habitación/pago correctamente.

## Cambios pendientes

- **Confirmar disponibilidad real** de `tulum-casa-tortuga` y `akumal-cenote-nohoch` (hoy `on_request` por falta de dato, no por decisión definitiva).
- **Auto-deploy a Cloudflare**: sigue sin configurarse: cada cambio requiere el paso manual de arrastrar la carpeta.
- Nada de precios ni lógica de cálculo se tocó en esta fase — siguen como quedaron en las fases anteriores.

## Próximo objetivo

Sin definir todavía — el checkout final (datos del huésped una sola vez y sólo en el carrito, fecha/pasajeros por tour, editar ítems, paso de revisión) ya está construido y probado. Próximo paso sugerido: que Agustín lo pruebe en la URL real de Cloudflare y traiga feedback, o defina la siguiente prioridad (ej. confirmar los tours `on_request` pendientes, configurar auto-deploy, u otra mejora).
