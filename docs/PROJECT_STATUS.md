# Mundo Caribe Tours — Estado del proyecto

_Última actualización: 2026-09-10, al cierre de la Fase 3 (disponibilidad y calendario)._

## Último commit y estado del deploy

- **Commit:** `fe730ca` — "Fase 3: calendario de disponibilidad propio, accesible, y checkout con fecha por tour" (rama `main`, subido a GitHub).
- **Deploy:** confirmado en vivo en `https://mundo-caribe-tours.ignacioagustindannunzio.workers.dev/` — verificado que el `site.js` publicado tiene `CART_VERSION = 4` y que `chichen-itza` sirve `"schedule": {"type": "daily"}`, coincidiendo con el repo. El deploy a Cloudflare **es manual**: no hay auto-deploy configurado desde GitHub todavía — cada cambio requiere regenerar (`python3 scripts/generate_site.py`), copiar `index.html`, `assets/`, `categoria/`, `tour/` y `todos-los-tours/` a la carpeta `~/Desktop/mundo-caribe-cloudflare-deploy`, y arrastrarla a Cloudflare ("New deployment").
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

## Cambios pendientes

- **Confirmar disponibilidad real** de `tulum-casa-tortuga` y `akumal-cenote-nohoch` (hoy `on_request` por falta de dato, no por decisión definitiva).
- **Auto-deploy a Cloudflare**: sigue sin configurarse: cada cambio requiere el paso manual de arrastrar la carpeta.
- **Checkout final**: no iniciado (ver próximo objetivo).
- Nada de precios, lógica de cálculo, carrito ni métodos de pago se tocó en esta fase — siguen como quedaron en las fases anteriores.

## Próximo objetivo

Checkout final: pedir los datos del huésped **una sola vez** para toda la reserva (nombre completo, hotel, número de habitación, método de pago — el nombre ya se agregó en esta fase; hotel/habitación/pago ya se pedían una sola vez desde antes), manteniendo la **fecha y los pasajeros de cada tour por separado** (nunca sumados ni compartidos entre tours), y un mensaje final de WhatsApp que resuma todo con claridad, sin prometer disponibilidad automática ni cobrar nada.
