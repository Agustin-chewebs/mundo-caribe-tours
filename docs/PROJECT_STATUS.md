# Mundo Caribe Tours — Estado del proyecto

_Última actualización: 2026-09-11, tras corregir el visor de historias para que nunca muestre dos historias a la vez (lado a lado)._

## Último commit y estado del deploy

- **Commit:** `217f435` — "Historias: cada foto/video ocupa sola todo el visor (sin overlap)" (rama `main`, subido a GitHub). Anterior: `46f358a` (video sin `loop`, reproduce una sola vez).
- **Deploy:** `~/Desktop/mundo-caribe-cloudflare-deploy` actualizada y verificada (`assets/site.css` y `assets/site.js` — `index.html` no cambió, este fix fue puramente de CSS/JS), lista para arrastrar a Cloudflare — confirmar en vivo en `https://mundo-caribe-tours.ignacioagustindannunzio.workers.dev/` después de subirla. El deploy a Cloudflare **es manual**: no hay auto-deploy configurado desde GitHub todavía — cada cambio requiere regenerar (`python3 scripts/generate_site.py`), copiar `index.html`, `assets/`, `categoria/`, `tour/`, `todos-los-tours/` y `guias/` a esa carpeta, y arrastrarla a Cloudflare ("New deployment").
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
| akumal-cenote-nohoch | Martes a domingo | `weekly` [mar,mié,jue,vie,sáb,dom] | Confirmado por Agustín — lunes bloqueado; antes decía "Consulta disponibilidad" |
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

## Copy y UX del checkout: métodos de pago + "Qué sigue" (agregado 2026-09-10)

Mejora puntual de copy/UX, sin pasarela de pago ni cambios de precio — la web sigue sin cobrar nada: sólo envía una solicitud de reserva por WhatsApp, y Agustín confirma disponibilidad antes de coordinar el pago.

- **Explicación por método de pago** (`PAYMENT_METHOD_NOTES` en `assets/site.js`), visible tanto en el select del carrito como en el resumen de revisión:
  - Tarjeta de crédito/débito (+5%): "Recibís un link de pago por WhatsApp después de confirmar disponibilidad."
  - Efectivo USD y efectivo MXN: "Coordinamos el pago para el día de la excursión."
  - Transferencia USD, ARS y COP: "Te enviamos los datos de pago por WhatsApp tras confirmar."
- **CTA final del paso de revisión** cambiado a "Enviar solicitud por WhatsApp" (antes "Confirmar y enviar por WhatsApp").
- **Bloque "Qué sigue"** junto al CTA final: 1. Agustín confirma cupo. 2. Coordinan método de pago. 3. Recibís horario y punto de salida — sin prometer tiempos concretos.
- Se conserva sin cambios el aviso de que la solicitud no confirma la reserva ni cobra nada.
- **Akumal + Cenote Nohoch**: se quitó "una de las pocas playas hoy libres de sargazo" de la descripción larga (afirmación no atemporal/no verificable) y se reemplazó por una descripción prudente sin esa mención.
- No se agregaron horarios, puntos de salida, políticas, idiomas, zonas de pickup ni condiciones de cancelación — quedan fuera hasta que Agustín los confirme.
- Probado en local: nota correcta para cada método de pago (tarjeta, efectivo, transferencia) en el formulario y en la revisión, CTA y bloque "Qué sigue" visibles en desktop y mobile, y la descripción de Akumal + Cenote Nohoch sin la mención de sargazo.

## Visor de historias "Conocé a Agustín" (última revisión 2026-09-11)

- **Entrada**: anillo circular (foto + "Conocé a Agustín") en el home, debajo del hero (justo después de "Coordinado directo con Agustín por WhatsApp") y antes de "¿Qué querés vivir?". Aro con gradiente propio verde profundo → arena (`--teal-deep` → `--sand`, nada de Instagram). Al tocarlo abre el visor de pantalla completa.
- **22 historias reales de Agustín** (19 fotos + 2 fotos nuevas + 1 video), en `assets/stories/` — nada editado, recortado, sin stickers ni corrección de orientación; algunas quedan "de costado" porque así están guardadas originalmente, a propósito no corregidas. Orden curado a mano en `AGUSTIN_STORIES` (`scripts/generate_site.py`):
  1. **Fija primera**: "Un Agustín de 21 años empezando a encontrarse" (`73DB1620...`).
  2. **Fija segunda**: atardecer en Holbox (`85052D02...`) — completamente limpia, sin texto/ubicación/chip/enlace.
  3. El resto alterna con criterio — paisaje/lugar real → Agustín viviendo la experiencia → aventura/tour → momento humano — sin repetir el mismo tipo dos veces seguidas.
  4. El **video** (`F8E4E379...`, cámara navideña en Playa del Carmen) va avanzado, en el empalme entre una foto de aventura y una de momento personal — nunca al comienzo ni al cierre.
  5. Fotos de fiesta (michelada, yate) deliberadamente avanzadas, nunca al inicio ni sobre el cierre.
  6. **Fija última**: Agustín con su mamá, hermano y ahijado (`74F7FEFD...`) — sin nombres, ubicación ni enlaces; `alt="Agustín junto a su familia durante un viaje"`.
- **Una sola historia por pantalla, siempre** (corregido 2026-09-11): `.mc-story-media` centraba antes la foto/video activo con flexbox mientras el elemento se autodimensionaba según su tamaño intrínseco (`width:auto;height:auto;max-width:100%;max-height:100%`) — bajo ciertas condiciones (fotos cargando por red real, avance rápido/consecutivo) ese cálculo podía quedar mal resuelto y la foto activa se veía corrida hacia un costado con una franja vacía al lado, dando la impresión de "dos historias lado a lado". Ahora la foto/video activo es siempre `position:absolute; inset:0; width:100%; height:100%; object-fit:contain` dentro de `.mc-story-media` (`position:relative; overflow:hidden`) — ocupa el 100% del área de medios sin excepción, sin ningún cálculo de centrado externo que pueda fallar; `object-fit:contain` resuelve el letterboxing puertas adentro del propio elemento, sin recortar ni distorsionar la imagen. Sigue habiendo un único `<img>` y un único `<video>` montados (nunca una fila/grilla/carrusel de historias) — el que no corresponde al índice activo queda `hidden` (`display:none`, sin espacio ni interacción). El área transparente sobre cada sticker (`#mc-story-hit`) se recalculó para este nuevo modelo (`positionHit()` ahora calcula a mano el rectángulo realmente visible dentro del letterbox, usando `naturalWidth`/`naturalHeight`) — los 5 enlaces siguen alineados exactamente sobre su sticker, verificado.
- **El video**: el archivo original (`F8E4E379-....MOV`, HEVC) no es reproducible de forma confiable en todos los navegadores/dispositivos, así que se convirtió **una sola vez** a `.mp4` (H.264, mismo aspecto vertical 9:16, `avconvert --preset Preset960x540`, ~2.1MB para 5s) — mismo contenido, sólo cambia el códec/contenedor. El `.MOV` original no se sube al sitio (queda solo en `~/Downloads/Fotos Agustin para MundoCaribe/` en la máquina de Agustín). El `<video>` tiene `autoplay`, `muted`, `playsinline` y `preload="metadata"` — **sin `loop`** (corregido 2026-09-11: antes se repetía indefinidamente). Al entrar a esa historia se reinicializa de verdad desde 0 (`src` + `load()` + `currentTime = 0`) y reproduce una sola vez. La barra de progreso dura exactamente lo mismo que el video (se lee `video.duration` real al cargar los metadatos), pero **quien dispara el avance a la siguiente historia es únicamente el evento `ended`** del video — la barra nunca hace el avance ella misma en ese caso, para que las dos cosas no compitan y salteen una historia. Si el video falla al cargar/reproducir (o nunca queda listo), no se traba ni entra en loop: se marca completo y avanza solo, igual que si hubiera terminado. Tocar siguiente/anterior o cerrar el visor mientras el video corre lo pausa al instante y limpia sus listeners/timers — nunca sigue sonando ni reproduciéndose de fondo (no tiene audio de todos modos, pero tampoco sigue avanzando cuadros).
- **Enlaces sin chip visible**: no hay ningún chip, pill ni texto agregado encima de ninguna foto. Sólo 5 fotos tienen un enlace confirmado por Agustín, y en cada una es un área **transparente** (`#mc-story-hit`) posicionada a mano (`pos`: left/top/width/height en % de la foto, en `AGUSTIN_STORIES`) exactamente sobre el sticker original de esa foto — abre en pestaña nueva (`target="_blank" rel="noopener noreferrer"`): Playa de Xpu-Ha, ATIK World Tulum, Marina Tower Center, Sian Ka'an y @puravida.wey. La posición se recalcula en JS contra el tamaño real de la foto en pantalla (al cargar la imagen y al cambiar el tamaño de la ventana). Las demás 17 historias no tienen ninguna acción — no se inventó ningún enlace.
- **Xplor by Xcaret / Xavage: sin enlace.** Ese parque cerró — sus dos fotos quedan tal cual, con su logo/branding original en la imagen, pero sin chip, sin etiqueta y sin ningún enlace.
- **Comportamiento del visor** (`initAgustinStories` en `assets/site.js`, sin librerías externas, sin React/Tailwind/Framer Motion — sólo se tomó como referencia de interacción un story-viewer externo, nunca su código ni su marca): una barra de progreso por historia, autoplay (5s por foto; la duración real del video en la suya), tap izquierda/derecha (o clic) y swipe para navegar, mantener presionado pausa (pausa también el video) y soltar reanuda, **flechas ‹ › de escritorio que sólo aparecen al pasar el mouse** (`hover: hover` + `pointer: fine` — nunca en touch), botón de cerrar siempre visible, teclado (flechas + Escape), y respeta `prefers-reduced-motion`: sin autoplay ni barra animada — el video igual reproduce (es el contenido que el visitante abrió a propósito) pero no avanza solo. Sin likes, comentarios, avatares múltiples, timestamps, CTAs ni ningún elemento de red social.
- No se tocó ningún precio, tour, disponibilidad ni lógica de checkout existente — cambio aislado al home.
- Probado en local en desktop y mobile: orden de las 22 historias, autoplay foto y video, duración de la barra del video verificada contra `video.duration` real, el video llega a `currentTime === duration` y avanza sola vez (sin reiniciarse ni repetirse), interrumpir el video a mitad de reproducción (tocar siguiente o cerrar) lo pausa de inmediato y queda congelado ahí — nunca se reanuda ni sigue de fondo, verificado esperando varios segundos después—, el error de carga forzado con una URL de video inexistente avanza solo a los ~2s sin trabar el visor, pausa/reanudación por mantener presionado, tap y swipe en ambas direcciones, flechas de escritorio (aparecen sólo con el mouse encima, ausentes en mobile), cierre al pasar la última foto, tecla Escape, alt de la foto familiar, y las 5 áreas transparentes + las 2 fotos de Xplor re-verificadas en sus posiciones.

## "Guías del Caribe" — base del blog (agregado 2026-09-11)

Sección preparada pero **sin contenido todavía** — a propósito: nada de posts de relleno ni tarjetas de ejemplo.

- **Nav**: link discreto "Guías" en el menú de escritorio y mobile, entre "Tours" y "Contacto" (no desplaza Tours, WhatsApp ni el carrito).
- **Ruta índice**: `/guias/` (`render_guides_index()` en `scripts/generate_site.py`) — con `GUIDES` vacía muestra el estado vacío intencional: "Próximamente: guías reales para elegir mejor tu experiencia en Riviera Maya." dentro de un marco punteado (se ve preparado, no roto).
- **Estructura lista para el primer artículo real** — nada de esto está conectado a un CMS, IA, automatización, feed ni analítica; es sólo la estructura de datos + la función que ya sabe renderizar una página cuando haya contenido real.

### Cómo publicar la primera guía real

1. Elegir las fotos de la guía y copiarlas a `assets/guias/` (crear la carpeta si no existe todavía — hoy no existe porque no hay ninguna guía).
2. Abrir `scripts/generate_site.py`, buscar `GUIDES = []` y agregar un diccionario por artículo, con esta forma exacta:
   ```python
   GUIDES = [
       {
           'title': 'Título del artículo',
           'slug': 'titulo-del-articulo',            # define la URL: /guias/titulo-del-articulo/
           'date': '2026-09-15',                      # fecha de publicación
           'description': 'Resumen corto (1-2 líneas) para la tarjeta y el SEO.',
           'category': 'Cenotes',                      # etiqueta libre mostrada en la tarjeta
           'image': 'nombre-de-la-foto.jpg',           # debe existir en assets/guias/
           'content_html': '<p>Cuerpo del artículo en HTML...</p>',
           # 'seo': {'title': '...', 'description': '...'},  # opcional, si querés un título/descripción distinto para buscadores
       },
   ]
   ```
3. Correr `python3 scripts/generate_site.py` — genera automáticamente `/guias/` (ahora con la tarjeta del artículo) y `/guias/<slug>/index.html` con el artículo completo.
4. Copiar los cambios a `~/Desktop/mundo-caribe-cloudflare-deploy` (igual que cualquier otro cambio del sitio, ver arriba) y arrastrar la carpeta a Cloudflare.

No hace falta tocar `render_guide_card`, `render_guides_index` ni `render_guide_page` — ya están listos; sólo se agrega contenido a la lista `GUIDES`.

## Cambios pendientes

- **Confirmar disponibilidad real** de `tulum-casa-tortuga` (hoy `on_request` por falta de dato, no por decisión definitiva).
- **Auto-deploy a Cloudflare**: sigue sin configurarse: cada cambio requiere el paso manual de arrastrar la carpeta.
- **Guías del Caribe**: sigue sin ningún artículo publicado — a la espera de contenido real de Agustín (ver instrucciones de publicación arriba).
- Nada de precios ni lógica de cálculo se tocó en esta fase — siguen como quedaron en las fases anteriores.

## Próximo objetivo

Sin definir todavía — el checkout final, el visor "Conocé a Agustín" (con video y las dos fotos fijas) y la base de "Guías del Caribe" ya están construidos y probados. Próximo paso sugerido: que Agustín lo pruebe en la URL real de Cloudflare y traiga feedback, escriba la primera guía real (ver instrucciones de publicación arriba), o defina la siguiente prioridad (ej. confirmar los tours `on_request` pendientes, configurar auto-deploy, u otra mejora).
