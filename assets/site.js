(function () {
  'use strict';

  var WA_NUMBER = '529841191147';

  var LS_CART = 'mc_cart';
  var LS_NAME = 'mc_name';
  var LS_HOTEL = 'mc_hotel';
  var LS_ROOM = 'mc_room';
  var LS_MAPS = 'mc_maps';
  var LS_PAYMENT = 'mc_payment';
  var LS_ZONE = 'mc_zone';
  var LS_EDIT_ID = 'mc_edit_id'; // single-use flag: "open this tour's widget pre-filled to edit cart item X"
  var LS_CART_VERSION = 'mc_cart_v';
  var CART_VERSION = 6; // bump this whenever the shape of a cart item changes, to auto-clear stale carts

  function genId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 8); }

  // ---------- pickup zones & their supplements ----------
  // All published prices already assume pickup from Playa del Carmen /
  // Playacar (zone 1) — zones 1 and 2 carry no supplement. Zone 3's
  // supplement is per-tour (see zone3SurchargeMXN in each tour's own
  // pricing data, emitted by scripts/generate_site.py) and only affects
  // the 3 tours that actually have one; every other tour is 0 in zone 3.
  // Zone 4 is a flat per-person surcharge on every tour EXCEPT the ones
  // marked zoneExempt (pesca-yate-cancun has its own fixed pickup point,
  // Marina Kaybal, and isn't part of this hotel-zone transport system).
  var ZONES = [
    { value: 'pdc_playacar', label: 'Playa del Carmen / Playacar' },
    { value: 'cancun', label: 'Cancún' },
    { value: 'occidental_tulum', label: 'Hoteles Occidental/Xcaret hasta Tulum' },
    { value: 'costa_mujeres', label: 'Costa Mujeres / Puerto Juárez / Isla Blanca' }
  ];
  var DEFAULT_ZONE = 'pdc_playacar';
  // Shown right under the zone selector, both in the tour widget and in
  // the cart — reassures a guest who isn't sure where their hotel falls
  // that picking the default zone is a safe provisional choice: it never
  // silently confirms the hotel IS in that zone, any real charge still
  // gets confirmed by Agustín on WhatsApp before the booking proceeds.
  var ZONE_HELP_NOTE = '¿No sabés en qué zona está tu hotel? Elegí Playa del Carmen / Playacar. Si corresponde un cargo adicional por ubicación, te lo vamos a avisar por WhatsApp y esperamos tu confirmación antes de seguir con la reserva.';
  var ZONE4_FLAT_SURCHARGE_MXN = 300;

  function getZone() {
    var z = getStr(LS_ZONE);
    return ZONES.some(function (zz) { return zz.value === z; }) ? z : DEFAULT_ZONE;
  }
  function setZone(v) { setStr(LS_ZONE, v); }
  function zoneLabel(v) {
    var z = ZONES.filter(function (zz) { return zz.value === v; })[0];
    return z ? z.label : ZONES[0].label;
  }
  function zoneSelectHtml(id, current) {
    var opts = ZONES.map(function (z) {
      return '<option value="' + z.value + '"' + (z.value === current ? ' selected' : '') + '>' + z.label + '</option>';
    }).join('');
    return '<select id="' + id + '">' + opts + '</select>';
  }
  // MXN supplement per PAYING person (adults + children — infants never
  // pay it) for one tour's own pricing data, at a given zone.
  function zoneSurchargeMXNPerPerson(data, zoneValue) {
    if (data.zoneExempt) return 0;
    if (zoneValue === 'occidental_tulum') return data.zone3SurchargeMXN || 0;
    if (zoneValue === 'costa_mujeres') return ZONE4_FLAT_SURCHARGE_MXN;
    return 0;
  }
  // Same, but reading the fields persisted on an already-added cart item
  // (see cartFields()/the bw-cta handler) instead of live tour-pricing data.
  function zoneSurchargeMXNPerPersonForItem(item, zoneValue) {
    if (item.zoneExempt) return 0;
    if (zoneValue === 'occidental_tulum') return item.zone3SurchargeMXN || 0;
    if (zoneValue === 'costa_mujeres') return ZONE4_FLAT_SURCHARGE_MXN;
    return 0;
  }
  // Every paying traveler on a cart item — adults+children for adult_child
  // tours, persons for per_person/tiers/duration_group. Infants excluded.
  function payingPax(item) {
    return (item.adults || 0) + (item.children || 0) + (item.persons || 0);
  }
  function itemZoneSupplementMXN(item, zoneValue) {
    return payingPax(item) * zoneSurchargeMXNPerPersonForItem(item, zoneValue);
  }
  function mxnToUsd(mxnAmount) { return mxnAmount / MXN_REFERENCE_RATE; }
  // An item's own total (base tour price, USD) plus its zone supplement
  // (converted to USD at the same reference rate used everywhere else),
  // rounded once for display. null for quote-only items (no total at all).
  function itemDisplayTotalUsd(item, zoneValue) {
    if (typeof item.total !== 'number') return null;
    return Math.round(item.total + mxnToUsd(itemZoneSupplementMXN(item, zoneValue)));
  }

  // ---------- payment methods ----------
  // All tour prices are in USD. Fixed reference rate given by Agustín, used
  // to auto-convert totals to pesos mexicanos wherever a method needs it.
  var MXN_REFERENCE_RATE = 16.50;
  var CARD_SURCHARGE = 0.05; // 5% recargo si paga con tarjeta
  // Three groups, shown as the main choice; each has its own concrete
  // payment options. "kind" drives how a total is formatted for that
  // option (see formatPaymentTotal): mxn_final = converted to MXN, no
  // surcharge, final price. usd_final = shown in USD, no surcharge, final
  // price. card_mxn = converted to MXN + 5% surcharge. usd_ref = shown in
  // USD as a REFERENCE only — real data/quote follows by WhatsApp, never
  // auto-converted to ARS/COP/EUR or to a BTC amount.
  var PAYMENT_GROUPS = [
    {
      key: 'pay_on_tour',
      label: 'Pagar el día del tour',
      featured: true,
      blurb: 'Reservá ahora y pagá el día del tour, cuando la transportación llegue al punto acordado.',
      options: [
        { value: 'cash_mxn', label: 'Efectivo en pesos mexicanos', kind: 'mxn_final' },
        { value: 'cash_usd', label: 'Efectivo en dólares estadounidenses', kind: 'usd_final' },
        { value: 'card', label: 'Tarjeta Visa o Mastercard (+5% recargo)', kind: 'card_mxn' }
      ]
    },
    {
      key: 'transfer',
      label: 'Transferencia',
      blurb: 'Podés pagar por transferencia en pesos mexicanos, dólares estadounidenses, pesos argentinos, pesos colombianos o euros. Te enviamos por WhatsApp los datos correspondientes y, cuando haga falta convertir la moneda, la cotización vigente del día.',
      conditions: [
        'Los datos para realizar la transferencia se enviarán por WhatsApp.',
        'Para continuar con la reserva, el pago debe aparecer acreditado en el estado de cuenta del operador.',
        'El tour debe estar pagado al 100% antes de confirmar la reserva.'
      ],
      // Shown only when the chosen currency actually needs a quote (i.e.
      // anything but transfer_mxn) — mentioning "cotización" next to MXN
      // would be confusing since no conversion ever happens there.
      quoteConditions: [
        'La cotización proporcionada será válida únicamente durante ese día.',
        'La cotización corresponde solo a la conversión de moneda — no es un cargo adicional sobre el precio del tour.'
      ],
      options: [
        { value: 'transfer_mxn', label: 'MXN — CLABE/SPEI', kind: 'mxn_final' },
        { value: 'transfer_usd', label: 'USD — ACH o wire', kind: 'usd_ref' },
        { value: 'transfer_ars', label: 'ARS — pesos argentinos', kind: 'usd_ref' },
        { value: 'transfer_cop', label: 'COP — pesos colombianos', kind: 'usd_ref' },
        { value: 'transfer_eur', label: 'EUR — SEPA', kind: 'usd_ref' }
      ]
    },
    {
      key: 'crypto',
      label: 'Criptomonedas',
      blurb: 'La dirección y la red para enviar el pago se comparten por WhatsApp.',
      conditions: [
        'La dirección y la red se proporcionarán por WhatsApp.',
        'Se requiere recibir el 100% del pago antes de confirmar la reserva.'
      ],
      options: [
        { value: 'crypto_btc', label: 'Bitcoin (BTC)', kind: 'usd_ref_btc' },
        { value: 'crypto_usdt', label: 'USDT', kind: 'usd_ref' },
        { value: 'crypto_usdc', label: 'USDC', kind: 'usd_ref' }
      ]
    }
  ];

  function findPaymentOption(value) {
    for (var g = 0; g < PAYMENT_GROUPS.length; g++) {
      var group = PAYMENT_GROUPS[g];
      for (var o = 0; o < group.options.length; o++) {
        if (group.options[o].value === value) return { group: group, option: group.options[o] };
      }
    }
    return null;
  }
  function paymentLabel(value) {
    var f = findPaymentOption(value);
    return f ? f.option.label : '';
  }
  // Short, honest note shown next to the chosen method — what actually
  // happens after choosing it. No payment gateway involved anywhere;
  // everything is coordinated by Agustín on WhatsApp once he confirms
  // availability.
  function paymentNote(value) {
    var f = findPaymentOption(value);
    if (!f) return '';
    var kind = f.option.kind;
    if (kind === 'card_mxn') return 'El tipo de cambio aplicado por tu banco puede variar.';
    if (kind === 'usd_ref_btc') return 'Te enviaremos por WhatsApp la dirección, la red y la cotización en BTC.';
    if (f.group.key === 'crypto') return 'Te enviaremos por WhatsApp la dirección y la red — el monto a enviar es el mismo total en USD.';
    if (f.group.key === 'transfer') return f.option.value === 'transfer_mxn'
      ? 'Te enviaremos por WhatsApp los datos para transferir (CLABE/SPEI).'
      : 'Te enviaremos por WhatsApp los datos y la cotización correspondiente.';
    return 'Coordinamos el pago para el día de la excursión, directo con Agustín.';
  }
  function mxn(n) { return '$' + Math.round(n).toLocaleString('en-US') + ' MXN'; }
  // Formats a base USD total for display/messaging according to the
  // chosen payment option's "kind" (see PAYMENT_GROUPS above). Falls back
  // to a plain USD figure if nothing valid is chosen yet.
  function formatPaymentTotal(baseUsdTotal, paymentValue) {
    var f = findPaymentOption(paymentValue);
    var rounded = Math.round(baseUsdTotal);
    if (!f) return usd(rounded);
    var kind = f.option.kind;
    if (kind === 'mxn_final') return mxn(rounded * MXN_REFERENCE_RATE);
    if (kind === 'card_mxn') return mxn(Math.round(rounded * MXN_REFERENCE_RATE * (1 + CARD_SURCHARGE)));
    return usd(rounded); // usd_final, usd_ref, usd_ref_btc
  }
  function isValidPaymentValue(value) {
    return !!findPaymentOption(value);
  }

  // ---------- storage helpers ----------
  function ensureCartVersion() {
    try {
      var v = parseInt(localStorage.getItem(LS_CART_VERSION), 10);
      if (v !== CART_VERSION) {
        localStorage.removeItem(LS_CART);
        localStorage.setItem(LS_CART_VERSION, String(CART_VERSION));
      }
    } catch (e) {}
  }
  function getCart() {
    try { return JSON.parse(localStorage.getItem(LS_CART)) || []; } catch (e) { return []; }
  }
  function setCart(arr) {
    try { localStorage.setItem(LS_CART, JSON.stringify(arr)); } catch (e) {}
  }
  function getStr(key) {
    try { return localStorage.getItem(key) || ''; } catch (e) { return ''; }
  }
  function setStr(key, val) {
    try { localStorage.setItem(key, val); } catch (e) {}
  }

  // ---------- reveal on scroll ----------
  function initReveal() {
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var reveals = document.querySelectorAll('.reveal');
    if (reduce || !('IntersectionObserver' in window)) {
      reveals.forEach(function (el) { el.classList.add('visible'); });
      return;
    }
    // threshold 0 (not e.g. 0.15): a .reveal section taller than the viewport
    // can never reach a fixed intersection RATIO like 0.15, because the max
    // achievable ratio is capped at (viewport height / section height) — a
    // tall section would then sit at opacity:0 forever, no matter how much
    // you scroll. threshold 0 fires as soon as a single pixel is visible, so
    // it works regardless of how tall the revealed content is.
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0, rootMargin: '0px 0px -10% 0px' });
    reveals.forEach(function (el) { obs.observe(el); });

    // Safety net: IntersectionObserver callbacks can be delayed or skipped
    // entirely by the browser in edge cases (background/prerendered tabs,
    // bfcache restores, some mobile browsers under load) — when that
    // happens the content is stuck at opacity:0 forever, which is worse
    // than no animation at all. Force everything visible after a short
    // delay no matter what the observer did, so content is NEVER
    // permanently invisible.
    function forceRevealAll() {
      reveals.forEach(function (el) {
        el.classList.add('visible');
      });
      obs.disconnect();
    }
    setTimeout(forceRevealAll, 1200);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) forceRevealAll();
    });
  }

  function waLink(text) {
    return 'https://wa.me/' + WA_NUMBER + '?text=' + encodeURIComponent(text);
  }

  function fmtDate(iso) {
    if (!iso) return 'A coordinar';
    var parts = iso.split('-');
    var meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    var d = parseInt(parts[2], 10), m = parseInt(parts[1], 10) - 1, y = parts[0];
    return d + ' ' + meses[m] + ' ' + y;
  }

  // Each cart item carries its OWN date and its OWN headcount — a cart with
  // several tours never shares one calendar or one passenger count, since
  // different tours in the same reservation can carry different people/dates.
  function cartItemDateLine(item) {
    if (!item.date) return item.tentative ? 'Fecha a coordinar (sin días fijos)' : 'Sin fecha elegida';
    return (item.tentative ? 'Fecha tentativa: ' : 'Fecha: ') + fmtDate(item.date);
  }
  function cartItemPaxLine(item) {
    var bits = [];
    if (item.optionLabel) bits.push(item.optionLabel);
    if (item.adults != null) {
      bits.push(item.adults + (item.adults === 1 ? ' adulto' : ' adultos'));
      if (item.children) bits.push(item.children + (item.children === 1 ? ' niño' : ' niños'));
    } else if (item.persons != null) {
      bits.push(item.persons + (item.persons === 1 ? ' persona' : ' personas'));
    }
    if (item.infants) bits.push(item.infants + (item.infants === 1 ? ' infante' : ' infantes'));
    var totalPax = (item.adults || 0) + (item.children || 0) + (item.persons || 0) + (item.infants || 0);
    return bits.join(', ') + ' — ' + totalPax + ' pax para transporte';
  }
  // Joins non-zero pax categories as natural Spanish prose ("2 adultos, 1
  // niño y 1 infante"), used by the WhatsApp message. Never mentions a
  // category with count 0. Tours priced 'adult_child' (which actually
  // charge a different price per age) get "adultos"/"niños" split out;
  // every other pricing type keeps its existing "personas" wording, since
  // those widgets never asked for an adults/children split in the first
  // place (same price regardless of age) — infants are still their own
  // category everywhere, since no pricing type ever charges for them.
  function joinSpanishList(parts) {
    if (parts.length === 0) return '';
    if (parts.length === 1) return parts[0];
    return parts.slice(0, -1).join(', ') + ' y ' + parts[parts.length - 1];
  }
  function waPaxPhrase(item) {
    var parts = [];
    if (item.adults != null) {
      if (item.adults) parts.push(item.adults + (item.adults === 1 ? ' adulto' : ' adultos'));
      if (item.children) parts.push(item.children + (item.children === 1 ? ' niño' : ' niños'));
    } else if (item.persons != null && item.persons) {
      parts.push(item.persons + (item.persons === 1 ? ' persona' : ' personas'));
    }
    if (item.infants) parts.push(item.infants + (item.infants === 1 ? ' infante' : ' infantes'));
    return joinSpanishList(parts);
  }
  // Clear, separate line for the zone supplement (never folded silently
  // into the price) — shown on the tour widget before adding AND in the
  // cart/review, always in the real currency (MXN), per person.
  function cartItemZoneLine(item, zoneValue) {
    var mxnAmount = itemZoneSupplementMXN(item, zoneValue);
    if (!mxnAmount) return '';
    var pax = payingPax(item);
    return '<div class="mc-cart-item-detail mc-zone-supplement">+ ' + mxn(mxnAmount) + ' de cargo adicional por ubicación (' + pax + (pax === 1 ? ' pasajero' : ' pasajeros') + ')</div>';
  }

  // "Today" as the calendar (Cancún/Riviera Maya, no DST) sees it — NOT the
  // visitor's own device timezone, which could disagree by hours and shift
  // the day near midnight. Intl with a fixed timeZone gives us that
  // directly, no library needed.
  var CANCUN_TZ = 'America/Cancun';
  var cancunTodayFmt = null;
  function cancunTodayISO() {
    if (!cancunTodayFmt) {
      cancunTodayFmt = new Intl.DateTimeFormat('en-CA', { timeZone: CANCUN_TZ, year: 'numeric', month: '2-digit', day: '2-digit' });
    }
    return cancunTodayFmt.format(new Date()); // en-CA formats as YYYY-MM-DD
  }

  // Weekday (0=domingo..6=sábado) of a plain Y-M-D calendar date. Deliberately
  // NOT `new Date(iso).getDay()` — that parses the string as UTC midnight and
  // then reads it back in the BROWSER'S LOCAL timezone, which can land on the
  // wrong calendar day entirely depending on the visitor's offset. Date.UTC +
  // getUTCDay never touches any local timezone, so the same iso always gives
  // the same weekday everywhere.
  function isoWeekday(iso) {
    var p = iso.split('-').map(Number);
    return new Date(Date.UTC(p[0], p[1] - 1, p[2])).getUTCDay();
  }

  function usd(n) { return '$' + n.toLocaleString('en-US') + ' USD'; }

  // ===========================================================================
  // CUSTOM CALENDAR — a compact field that opens a popover grid showing
  // only the days a tour actually runs. Replaces the native
  // <input type="date">, which can't grey out individual weekdays in its
  // own picker UI, and whose click-to-open area is inconsistent across
  // browsers (clicking the text often just moves a cursor; only the tiny
  // icon reliably opens the calendar).
  //
  // Blocked days use `aria-disabled` (not the native `disabled`
  // attribute) so they stay reachable by arrow-key navigation — a
  // fully-disabled button can't receive focus at all, which would make it
  // impossible to arrow onto a blocked day to see it's blocked. The click
  // and Enter/Space handlers both explicitly ignore aria-disabled cells,
  // so nothing blocked is ever selectable, visually or by keyboard.
  // ===========================================================================

  var MESES_LARGO = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

  function daysInMonth(y, m) { return new Date(Date.UTC(y, m, 0)).getUTCDate(); } // m is 1-12
  function pad2(n) { return n < 10 ? '0' + n : '' + n; }
  function isoOf(y, m, d) { return y + '-' + pad2(m) + '-' + pad2(d); }

  // THE single source of truth for "can this date be picked" — used by
  // the calendar to greek out cells AND, separately, called again as a
  // hard gate right before adding to cart / sending the WhatsApp message.
  // Visually blocking a day is not enough on its own: the date actually
  // has to be re-checked at both of those moments too.
  function isDateAllowed(iso, schedule) {
    if (!iso || !schedule) return false;
    if (iso < cancunTodayISO()) return false;
    if (schedule.type === 'weekly') return schedule.days.indexOf(isoWeekday(iso)) !== -1;
    if (schedule.type === 'seasonal') return schedule.months.indexOf(parseInt(iso.split('-')[1], 10)) !== -1;
    return true; // daily, on_request: any future date
  }
  function isTentativeSchedule(schedule) {
    return !schedule || schedule.type === 'seasonal' || schedule.type === 'on_request';
  }

  function datePickerHtml(id) {
    return '<div class="mc-datepicker" id="' + id + '">' +
      '<button type="button" class="mc-dp-trigger" aria-haspopup="true" aria-expanded="false">' +
      '<span class="mc-dp-trigger-text">Elegí una fecha</span><span class="mc-dp-trigger-icon">📅</span>' +
      '</button>' +
      '<div class="mc-dp-panel" hidden>' +
      '<div class="mc-dp-head">' +
      '<button type="button" class="mc-dp-nav" data-dir="-1" aria-label="Mes anterior">‹</button>' +
      '<span class="mc-dp-month"></span>' +
      '<button type="button" class="mc-dp-nav" data-dir="1" aria-label="Mes siguiente">›</button>' +
      '</div>' +
      '<div class="mc-dp-weekdays"><span>D</span><span>L</span><span>M</span><span>M</span><span>J</span><span>V</span><span>S</span></div>' +
      '<div class="mc-dp-grid" role="grid"></div>' +
      '<p class="mc-dp-blocked-msg" aria-live="polite" hidden>Ese día no está disponible para este tour.</p>' +
      '</div>' +
      '</div>';
  }

  // container: an element already holding the picker's static markup (see
  // datePickerHtml). opts: { schedule, initialISO: string|null, tentative:
  // bool, onSelect: function(iso) }
  function initDatePicker(container, opts) {
    var todayISO = cancunTodayISO();
    var todayParts = todayISO.split('-').map(Number);
    var viewYear = todayParts[0], viewMonth = todayParts[1]; // 1-12
    var selectedISO = opts.initialISO || null;
    if (selectedISO) {
      var sp = selectedISO.split('-').map(Number);
      viewYear = sp[0]; viewMonth = sp[1];
    }

    var trigger = container.querySelector('.mc-dp-trigger');
    var triggerText = container.querySelector('.mc-dp-trigger-text');
    var panel = container.querySelector('.mc-dp-panel');
    var monthEl = container.querySelector('.mc-dp-month');
    var gridEl = container.querySelector('.mc-dp-grid');
    var prevBtn = container.querySelector('[data-dir="-1"]');
    var nextBtn = container.querySelector('[data-dir="1"]');
    var blockedMsgEl = container.querySelector('.mc-dp-blocked-msg');

    function updateTriggerText() {
      if (!selectedISO) { triggerText.textContent = 'Elegí una fecha'; return; }
      triggerText.textContent = (opts.tentative ? 'Fecha tentativa: ' : 'Fecha elegida: ') + fmtDate(selectedISO);
    }
    updateTriggerText();

    function open() {
      panel.hidden = false;
      trigger.setAttribute('aria-expanded', 'true');
      blockedMsgEl.hidden = true;
      render();
      var toFocus = gridEl.querySelector('.mc-dp-day[tabindex="0"]') || gridEl.querySelector('.mc-dp-day');
      if (toFocus) toFocus.focus();
    }
    function close() {
      panel.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
    }
    trigger.addEventListener('click', function () {
      if (panel.hidden) open(); else close();
    });
    document.addEventListener('click', function (e) {
      if (!panel.hidden && !container.contains(e.target)) close();
    });
    container.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !panel.hidden) { close(); trigger.focus(); }
    });

    function render() {
      monthEl.textContent = MESES_LARGO[viewMonth - 1] + ' ' + viewYear;
      gridEl.innerHTML = '';
      var firstWd = isoWeekday(isoOf(viewYear, viewMonth, 1));
      for (var i = 0; i < firstWd; i++) {
        var blank = document.createElement('span');
        blank.className = 'mc-dp-blank';
        gridEl.appendChild(blank);
      }
      var total = daysInMonth(viewYear, viewMonth);
      var cells = [];
      for (var d = 1; d <= total; d++) {
        var iso = isoOf(viewYear, viewMonth, d);
        var allowed = isDateAllowed(iso, opts.schedule);
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'mc-dp-day';
        btn.setAttribute('role', 'gridcell');
        btn.textContent = d;
        btn.setAttribute('data-iso', iso);
        btn.setAttribute('aria-disabled', allowed ? 'false' : 'true');
        btn.tabIndex = -1;
        if (iso === selectedISO) btn.classList.add('selected');
        if (iso === todayISO) btn.classList.add('today');
        cells.push(btn);
        gridEl.appendChild(btn);
      }
      // Roving tabindex: exactly one cell is tab-reachable — the selected
      // day if it's in view, else today if it's in view, else the first
      // enabled day, else just the first cell so focus always lands
      // somewhere when opening the picker.
      var roving = cells.filter(function (b) { return b.getAttribute('data-iso') === selectedISO; })[0]
        || cells.filter(function (b) { return b.getAttribute('data-iso') === todayISO; })[0]
        || cells.filter(function (b) { return b.getAttribute('aria-disabled') === 'false'; })[0]
        || cells[0];
      if (roving) roving.tabIndex = 0;
      prevBtn.disabled = (viewYear === todayParts[0] && viewMonth === todayParts[1]);
    }

    function selectCell(cell) {
      if (!cell) return;
      if (cell.getAttribute('aria-disabled') === 'true') {
        blockedMsgEl.hidden = false;
        return;
      }
      blockedMsgEl.hidden = true;
      selectedISO = cell.getAttribute('data-iso');
      updateTriggerText();
      close();
      trigger.focus();
      opts.onSelect(selectedISO);
    }

    gridEl.addEventListener('click', function (e) {
      var cell = e.target.closest('.mc-dp-day');
      if (cell) selectCell(cell);
    });

    // Roving-tabindex arrow key navigation: moves focus WITHIN the
    // current month grid (±1 day, ±7 days). Blocked cells stay reachable
    // (they're aria-disabled, not `disabled`) so a keyboard user can
    // land on one and see it's blocked, not just have it silently skipped.
    gridEl.addEventListener('keydown', function (e) {
      var current = e.target.closest('.mc-dp-day');
      if (!current) return;
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectCell(current); return; }
      var delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[e.key];
      if (!delta) return;
      e.preventDefault();
      var cells = Array.prototype.slice.call(gridEl.querySelectorAll('.mc-dp-day'));
      var idx = cells.indexOf(current) + delta;
      if (idx < 0 || idx >= cells.length) return; // simple same-month clamp
      var next = cells[idx];
      current.tabIndex = -1;
      next.tabIndex = 0;
      next.focus();
    });

    prevBtn.addEventListener('click', function () {
      viewMonth--; if (viewMonth < 1) { viewMonth = 12; viewYear--; }
      render();
    });
    nextBtn.addEventListener('click', function () {
      viewMonth++; if (viewMonth > 12) { viewMonth = 1; viewYear++; }
      render();
    });

    return { getSelected: function () { return selectedISO; } };
  }

  // ===========================================================================
  // CART (global, injected on every page)
  // ===========================================================================

  function cartCount() { return getCart().length; }

  function updateCartBadge() {
    var badge = document.getElementById('mc-cart-badge');
    if (!badge) return;
    var n = cartCount();
    badge.textContent = n;
    badge.style.display = n > 0 ? 'flex' : 'none';
  }

  function injectCartUI() {
    if (document.getElementById('mc-cart-btn')) return;

    var btn = document.createElement('button');
    btn.id = 'mc-cart-btn';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Ver carrito de reserva');
    btn.innerHTML = '🛒<span id="mc-cart-badge" class="mc-cart-badge">0</span>';
    document.body.appendChild(btn);

    var overlay = document.createElement('div');
    overlay.id = 'mc-cart-overlay';
    overlay.className = 'mc-cart-overlay';
    overlay.innerHTML = '<div class="mc-cart-drawer" role="dialog" aria-label="Carrito de reserva">' +
      '<div class="mc-cart-head"><h3>Tu reserva</h3><button type="button" id="mc-cart-close" aria-label="Cerrar">×</button></div>' +
      '<div id="mc-cart-items" class="mc-cart-items"></div>' +
      '<div id="mc-cart-checkout" class="mc-cart-checkout"></div>' +
      '</div>';
    document.body.appendChild(overlay);

    btn.addEventListener('click', function () { openCart(); });
    overlay.addEventListener('click', function (e) { if (e.target === overlay) closeCart(); });
    document.getElementById('mc-cart-close').addEventListener('click', closeCart);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && overlay.classList.contains('open')) closeCart();
    });

    updateCartBadge();
  }

  var cartReviewMode = false; // toggles the drawer between the editable form and the read-only review step
  function openCart() {
    cartReviewMode = false; // always reopen fresh in the editable form, never mid-review
    renderCartDrawer();
    document.getElementById('mc-cart-overlay').classList.add('open');
  }
  function closeCart() {
    document.getElementById('mc-cart-overlay').classList.remove('open');
  }
  window.mcOpenCart = openCart;

  function removeFromCart(idx) {
    var cart = getCart();
    cart.splice(idx, 1);
    setCart(cart);
    updateCartBadge();
    renderCartDrawer();
    // If the tour just removed has its own booking widget open on this
    // same page (e.g. the drawer opened over that tour's page), its
    // "Agregado al carrito" button needs to re-enable right away.
    if (window.__mcBookingSync) window.__mcBookingSync();
  }

  function renderCartDrawer() {
    var cart = getCart();
    var itemsEl = document.getElementById('mc-cart-items');
    var checkoutEl = document.getElementById('mc-cart-checkout');
    if (!itemsEl) return;

    if (cart.length === 0) {
      cartReviewMode = false;
      itemsEl.innerHTML = '<p class="mc-cart-empty">Todavía no agregaste ningún tour. Elegí uno y tocá "Agregar al carrito" para armar tu reserva.</p>';
      checkoutEl.innerHTML = '';
      return;
    }

    if (cartReviewMode) { renderCartReview(cart); return; }

    var zone = getZone();
    var total = 0;
    var totalSupplementMXN = 0;
    var hasQuote = false;
    itemsEl.innerHTML = cart.map(function (item, i) {
      if (typeof item.total === 'number') { total += item.total; totalSupplementMXN += itemZoneSupplementMXN(item, zone); }
      else hasQuote = true;
      return '<div class="mc-cart-item">' +
        (item.photo ? '<img src="' + item.photo + '" alt="">' : '<div class="mc-cart-item-noimg">🌴</div>') +
        '<div class="mc-cart-item-info">' +
        '<div class="mc-cart-item-name">' + item.name + '</div>' +
        '<div class="mc-cart-item-detail">' + cartItemDateLine(item) + '</div>' +
        '<div class="mc-cart-item-detail">' + cartItemPaxLine(item) + '</div>' +
        cartItemZoneLine(item, zone) +
        '<div class="mc-cart-item-price">' + (typeof item.total === 'number' ? usd(itemDisplayTotalUsd(item, zone)) : 'A cotizar') + '</div>' +
        '<button type="button" class="mc-cart-edit" data-idx="' + i + '">Editar</button>' +
        '</div>' +
        '<button type="button" class="mc-cart-remove" data-idx="' + i + '" aria-label="Quitar">×</button>' +
        '</div>';
    }).join('');

    itemsEl.querySelectorAll('.mc-cart-remove').forEach(function (b) {
      b.addEventListener('click', function () { removeFromCart(parseInt(b.getAttribute('data-idx'), 10)); });
    });
    itemsEl.querySelectorAll('.mc-cart-edit').forEach(function (b) {
      b.addEventListener('click', function () {
        var item = cart[parseInt(b.getAttribute('data-idx'), 10)];
        // single-use flag: that tour's own widget picks this up on load,
        // pre-fills itself from this exact cart item, and REPLACES it in
        // place instead of adding a duplicate when saved
        setStr(LS_EDIT_ID, item.id);
        window.location.href = item.url;
      });
    });

    var name = getStr(LS_NAME);
    var hotel = getStr(LS_HOTEL);
    var room = getStr(LS_ROOM);
    var maps = getStr(LS_MAPS);
    var payment = getStr(LS_PAYMENT);
    var combinedUsd = total + mxnToUsd(totalSupplementMXN);
    var anyTentative = cart.some(function (item) { return item.tentative; });

    checkoutEl.innerHTML =
      '<div class="mc-cart-total-row"><span>Total</span><strong>' + formatPaymentTotal(combinedUsd, payment) + (hasQuote ? ' + ítems a cotizar' : '') + '</strong></div>' +
      (totalSupplementMXN ? '<p class="mc-cart-persons">Incluye ' + mxn(totalSupplementMXN) + ' de cargo adicional por ubicación.</p>' : '') +
      (findPaymentOption(payment) && findPaymentOption(payment).option.kind === 'card_mxn' ? '<p class="mc-cart-persons">Incluye 5% de recargo por pago con tarjeta.</p>' : '') +
      (anyTentative ? '<p class="mc-cart-persons">⚠️ Uno o más tours tienen fecha tentativa — Agustín confirma disponibilidad por WhatsApp.</p>' : '') +
      '<div class="booking-field"><label for="mc-zone">Zona de recogida</label>' +
      zoneSelectHtml('mc-zone', zone) +
      '<p class="payment-note">Todos los precios publicados ya incluyen salida desde Playa del Carmen / Playacar.</p>' +
      '<p class="payment-note mc-zone-help">' + ZONE_HELP_NOTE + '</p>' +
      '</div>' +
      '<div class="booking-field"><label for="mc-name">Nombre completo</label>' +
      '<input type="text" id="mc-name" placeholder="Nombre y apellido de quien reserva" value="' + name.replace(/"/g, '&quot;') + '"></div>' +
      '<div class="booking-field-row">' +
      '<div class="booking-field"><label for="mc-hotel">Hotel / lugar de hospedaje</label>' +
      '<input type="text" id="mc-hotel" placeholder="Ej: Hotel Grand Sirenis" value="' + hotel.replace(/"/g, '&quot;') + '"></div>' +
      '<div class="booking-field booking-field-narrow"><label for="mc-room">N° de habitación</label>' +
      '<input type="text" id="mc-room" placeholder="Ej: 204, o «Pendiente»" value="' + room.replace(/"/g, '&quot;') + '"></div>' +
      '</div>' +
      '<div class="booking-field">' +
      '<button type="button" class="btn-secondary mc-loc-btn" id="mc-share-location">📍 Compartir mi ubicación</button>' +
      '<div id="mc-loc-status" class="mc-loc-status">' + (maps ? '✓ Ubicación agregada' : '') + '</div>' +
      '</div>' +
      '<div class="booking-field"><label>Método de pago</label>' +
      paymentPickerHtml(payment) +
      '</div>' +
      '<button type="button" class="btn-primary" id="mc-review-cta">Revisar y reservar</button>' +
      '<p class="contact-form-status" id="mc-checkout-status"></p>' +
      '<button type="button" class="mc-clear-cart" id="mc-clear-cart">Vaciar carrito</button>';

    document.getElementById('mc-zone').addEventListener('change', function (e) { setZone(e.target.value); renderCartDrawer(); });
    document.getElementById('mc-name').addEventListener('input', function (e) { setStr(LS_NAME, e.target.value); e.target.classList.toggle('field-invalid', !e.target.value.trim()); });
    document.getElementById('mc-hotel').addEventListener('input', function (e) { setStr(LS_HOTEL, e.target.value); e.target.classList.toggle('field-invalid', !e.target.value.trim()); });
    document.getElementById('mc-room').addEventListener('input', function (e) { setStr(LS_ROOM, e.target.value); e.target.classList.toggle('field-invalid', !e.target.value.trim()); });
    bindPaymentPicker(function () { renderCartDrawer(); });
    document.getElementById('mc-share-location').addEventListener('click', shareLocation);
    document.getElementById('mc-clear-cart').addEventListener('click', function () {
      if (confirm('¿Vaciar todo el carrito?')) {
        setCart([]);
        updateCartBadge();
        renderCartDrawer();
        if (window.__mcBookingSync) window.__mcBookingSync();
      }
    });
    document.getElementById('mc-review-cta').addEventListener('click', goToReview);
  }

  // ---------- payment method picker UI (grouped: pagar el día del tour /
  // transferencia / criptomonedas) — shared markup for the cart drawer.
  // The review step (renderCartReview) shows the SAME choice read-only,
  // never re-renders this interactive picker.
  function paymentPickerHtml(current) {
    var f = findPaymentOption(current);
    var selectedGroupKey = f ? f.group.key : PAYMENT_GROUPS[0].key;
    var groupsHtml = PAYMENT_GROUPS.map(function (g) {
      var isSel = g.key === selectedGroupKey;
      return '<label class="payment-group-option' + (g.featured ? ' featured' : '') + (isSel ? ' selected' : '') + '">' +
        '<span class="payment-group-head">' +
        '<input type="radio" name="mc-payment-group" value="' + g.key + '"' + (isSel ? ' checked' : '') + '>' +
        '<strong>' + g.label + '</strong>' + (g.featured ? '<span class="payment-group-badge">Recomendado</span>' : '') +
        '</span>' +
        '<span class="payment-group-blurb">' + g.blurb + '</span>' +
        '</label>';
    }).join('');
    return '<div class="payment-groups" id="mc-payment-groups">' + groupsHtml + '</div>' +
      '<div id="mc-payment-suboptions">' + paymentSuboptionsHtml(selectedGroupKey, current) + '</div>';
  }
  function paymentSuboptionsHtml(groupKey, current) {
    var group = PAYMENT_GROUPS.filter(function (g) { return g.key === groupKey; })[0];
    if (!group) return '';
    var validCurrent = group.options.some(function (o) { return o.value === current; }) ? current : group.options[0].value;
    var selectHtml = '<select id="mc-payment-option">' + group.options.map(function (o) {
      return '<option value="' + o.value + '"' + (o.value === validCurrent ? ' selected' : '') + '>' + o.label + '</option>';
    }).join('') + '</select>';
    var neededsQuote = group.key === 'transfer' && validCurrent !== 'transfer_mxn';
    var allConditions = (group.conditions || []).concat(neededsQuote ? (group.quoteConditions || []) : []);
    var conditionsHtml = allConditions.length
      ? '<ul class="payment-conditions">' + allConditions.map(function (c) { return '<li>' + c + '</li>'; }).join('') + '</ul>'
      : '';
    var noteHtml = paymentNote(validCurrent) ? '<p class="payment-note">' + paymentNote(validCurrent) + '</p>' : '';
    // Selecting a group with no prior valid selection in it silently
    // commits its first option as the default — keeps LS_PAYMENT always
    // pointing at a real, priceable option (never a bare group with
    // nothing chosen underneath it).
    if (validCurrent !== current) setStr(LS_PAYMENT, validCurrent);
    return '<div class="booking-field">' + selectHtml + '</div>' + conditionsHtml + noteHtml;
  }
  function bindPaymentPicker(onChange) {
    var groupsEl = document.getElementById('mc-payment-groups');
    if (!groupsEl) return;
    groupsEl.querySelectorAll('input[name="mc-payment-group"]').forEach(function (radio) {
      radio.addEventListener('change', function () {
        var group = PAYMENT_GROUPS.filter(function (g) { return g.key === radio.value; })[0];
        setStr(LS_PAYMENT, group.options[0].value);
        onChange();
      });
    });
    var subEl = document.getElementById('mc-payment-option');
    if (subEl) {
      subEl.addEventListener('change', function (e) { setStr(LS_PAYMENT, e.target.value); onChange(); });
    }
  }

  // Read-only recap shown after "Revisar y reservar" passes validation —
  // nothing here is editable; "Volver a editar" goes back to the form,
  // "Confirmar y enviar" re-validates once more (dates can in principle
  // go stale while lingering on this screen) and opens WhatsApp.
  function renderCartReview(cart) {
    var itemsEl = document.getElementById('mc-cart-items');
    var checkoutEl = document.getElementById('mc-cart-checkout');
    var name = getStr(LS_NAME);
    var hotel = getStr(LS_HOTEL);
    var room = getStr(LS_ROOM);
    var maps = getStr(LS_MAPS);
    var payment = getStr(LS_PAYMENT);
    var zone = getZone();
    var total = 0;
    var totalSupplementMXN = 0;
    var hasQuote = false;

    itemsEl.innerHTML = '<p class="mc-review-label">Revisá tu reserva antes de enviarla</p>' + cart.map(function (item) {
      if (typeof item.total === 'number') { total += item.total; totalSupplementMXN += itemZoneSupplementMXN(item, zone); }
      else hasQuote = true;
      return '<div class="mc-cart-item">' +
        (item.photo ? '<img src="' + item.photo + '" alt="">' : '<div class="mc-cart-item-noimg">🌴</div>') +
        '<div class="mc-cart-item-info">' +
        '<div class="mc-cart-item-name">' + item.name + '</div>' +
        '<div class="mc-cart-item-detail">' + cartItemDateLine(item) + '</div>' +
        '<div class="mc-cart-item-detail">' + cartItemPaxLine(item) + '</div>' +
        cartItemZoneLine(item, zone) +
        '<div class="mc-cart-item-price">' + (typeof item.total === 'number' ? usd(itemDisplayTotalUsd(item, zone)) : 'A cotizar') + '</div>' +
        '</div></div>';
    }).join('');

    var combinedUsd = total + mxnToUsd(totalSupplementMXN);
    checkoutEl.innerHTML =
      '<div class="mc-cart-total-row"><span>Total</span><strong>' + formatPaymentTotal(combinedUsd, payment) + (hasQuote ? ' + ítems a cotizar' : '') + '</strong></div>' +
      '<div class="mc-review-summary">' +
      '<p><strong>Nombre:</strong> ' + name + '</p>' +
      '<p><strong>Hotel:</strong> ' + hotel + ' · Habitación ' + (room.trim() || 'Pendiente') + '</p>' +
      '<p><strong>Zona de recogida:</strong> ' + zoneLabel(zone) + '</p>' +
      (zone === DEFAULT_ZONE ? '<p class="mc-payment-hint">Si tu hotel está fuera de la zona seleccionada y corresponde un cargo adicional por ubicación, te lo informaremos por WhatsApp. No continuaremos con la reserva sin tu confirmación.</p>' : '') +
      (maps ? '<p><strong>Ubicación compartida:</strong> sí</p>' : '') +
      '<p><strong>Método de pago:</strong> ' + paymentLabel(payment) + '</p>' +
      (paymentNote(payment) ? '<p class="mc-payment-hint">' + paymentNote(payment) + '</p>' : '') +
      '</div>' +
      '<p class="booking-fineprint">Esto no confirma la reserva ni cobra nada — Agustín confirma disponibilidad y coordina el pago directo por WhatsApp.</p>' +
      '<div class="mc-next-steps">' +
      '<p class="mc-next-steps-title">Qué sigue:</p>' +
      '<ol><li>Agustín confirma cupo.</li><li>Coordinan método de pago.</li><li>Recibís horario y punto de salida.</li></ol>' +
      '</div>' +
      '<button type="button" class="btn-primary" id="mc-confirm-send">Enviar solicitud por WhatsApp</button>' +
      '<p class="contact-form-status" id="mc-checkout-status"></p>' +
      '<button type="button" class="btn-secondary" id="mc-back-to-edit">← Volver a editar</button>';

    document.getElementById('mc-confirm-send').addEventListener('click', confirmAndSendWhatsApp);
    document.getElementById('mc-back-to-edit').addEventListener('click', backToEdit);
  }

  function shareLocation() {
    var status = document.getElementById('mc-loc-status');
    if (!navigator.geolocation) {
      if (status) status.textContent = 'Tu navegador no permite compartir ubicación. Escribí el hotel arriba.';
      return;
    }
    if (status) status.textContent = 'Buscando tu ubicación…';
    navigator.geolocation.getCurrentPosition(function (pos) {
      var link = 'https://www.google.com/maps?q=' + pos.coords.latitude + ',' + pos.coords.longitude;
      setStr(LS_MAPS, link);
      if (status) status.textContent = '✓ Ubicación agregada';
    }, function () {
      if (status) status.textContent = 'No pudimos obtener tu ubicación. Escribí el nombre del hotel arriba, no hay problema.';
    }, { timeout: 10000 });
  }

  // Re-checks every item's date against ITS OWN schedule (a date that was
  // valid when added could, in principle, no longer be — cart loaded from
  // an old localStorage snapshot, a day boundary crossed while lingering
  // on the review screen, etc.) plus the shared guest fields. Pure: no DOM
  // side effects, so it's safe to call both to decide whether to enter the
  // review step and again right before actually sending.
  function checkoutValidate(cart, name, hotel, room, payment) {
    var invalidTour = cart.filter(function (item) { return !isDateAllowed(item.date, item.schedule); })[0];
    var missing = [];
    if (!name.trim()) missing.push('el nombre completo');
    if (!hotel.trim()) missing.push('el hotel');
    if (!room.trim()) missing.push('el número de habitación (o escribí "Pendiente")');
    if (!isValidPaymentValue(payment)) missing.push('el método de pago');
    return { ok: !invalidTour && missing.length === 0, missing: missing, invalidTour: invalidTour };
  }

  function showCheckoutErrors(result) {
    var status = document.getElementById('mc-checkout-status');
    if (status) {
      status.textContent = result.invalidTour
        ? 'La fecha de "' + result.invalidTour.name + '" ya no es válida — abrí ese tour y elegí otra.'
        : 'Completá ' + result.missing.join(', ') + ' antes de reservar.';
      status.className = 'contact-form-status error';
    }
    var name = getStr(LS_NAME), hotel = getStr(LS_HOTEL), room = getStr(LS_ROOM), payment = getStr(LS_PAYMENT);
    ['mc-name', 'mc-hotel', 'mc-room'].forEach(function (id) {
      var f = document.getElementById(id);
      if (!f) return;
      var isMissing = (id === 'mc-name' && !name.trim()) || (id === 'mc-hotel' && !hotel.trim()) || (id === 'mc-room' && !room.trim());
      f.classList.toggle('field-invalid', isMissing);
    });
    var groupsEl = document.getElementById('mc-payment-groups');
    if (groupsEl) groupsEl.classList.toggle('field-invalid', !isValidPaymentValue(payment));
  }

  // "Total a pagar" + "Método de pago" + whatever else that specific
  // method needs spelled out (recargo, datos que llegan por WhatsApp,
  // cotización, etc.) — the exact adaptation each payment kind needs per
  // spec, kept in one place so the message never drifts from the actual
  // charge shown in the cart.
  function paymentMessageLines(payment, totalUsd) {
    var f = findPaymentOption(payment);
    var lines = ['Total a pagar: ' + formatPaymentTotal(totalUsd, payment) + (f && f.option.kind === 'card_mxn' ? ' (recargo del 5% ya incluido)' : '')];
    lines.push('Método de pago: ' + paymentLabel(payment));
    if (f) {
      if (f.option.kind === 'card_mxn') {
        lines.push('El tipo de cambio aplicado por tu banco puede variar.');
      } else if (f.option.value === 'transfer_mxn') {
        lines.push('Quedo a la espera de los datos para transferir (CLABE/SPEI) por WhatsApp.');
      } else if (f.group.key === 'transfer') {
        lines.push('Quedo a la espera de los datos y la cotización correspondiente por WhatsApp.');
      } else if (f.option.kind === 'usd_ref_btc') {
        lines.push('Quedo a la espera de la dirección, la red y la cotización en BTC por WhatsApp.');
      } else if (f.group.key === 'crypto') {
        lines.push('Quedo a la espera de la dirección y la red por WhatsApp.');
      }
    }
    return lines;
  }

  // Each tour keeps its OWN date and its OWN passenger breakdown — never
  // summed or shared across tours, so the same travel party doing two
  // excursions isn't miscounted as twice the people. Guest data (nombre,
  // hotel, habitación, método de pago) appears exactly once, after the
  // tour list, no matter how many tours are in the cart.
  function buildWhatsAppLines(cart, name, hotel, room, maps, payment) {
    var zone = getZone();
    var lines = ['Hola, me llamo ' + name + ' y quiero solicitar la reserva de los siguientes tours:', ''];
    var total = 0;
    var totalSupplementMXN = 0;
    cart.forEach(function (item, i) {
      var subtotal = itemDisplayTotalUsd(item, zone);
      lines.push((i + 1) + '. ' + item.name);
      lines.push(cartItemDateLine(item));
      var pax = waPaxPhrase(item);
      if (pax) lines.push('Pasajeros: ' + pax);
      lines.push('Subtotal: ' + (subtotal != null ? usd(subtotal) : 'A cotizar'));
      if (subtotal != null) { total += item.total; totalSupplementMXN += itemZoneSupplementMXN(item, zone); }
      lines.push('');
    });
    lines.push('Hotel: ' + hotel);
    lines.push('Habitación: ' + (room.trim() || 'Pendiente'));
    var combinedUsd = total + mxnToUsd(totalSupplementMXN);
    lines = lines.concat(paymentMessageLines(payment, combinedUsd));
    if (maps) lines.push('Ubicación compartida: ' + maps);
    lines.push('El horario de recogida y el punto de encuentro me serán enviados cuando la reserva quede confirmada.');
    lines.push('Entiendo que esta solicitud todavía no constituye una reserva confirmada. La disponibilidad y los detalles del pago serán coordinados directamente por WhatsApp.');
    return lines;
  }

  function goToReview() {
    var cart = getCart();
    if (cart.length === 0) return;
    var name = getStr(LS_NAME), hotel = getStr(LS_HOTEL), room = getStr(LS_ROOM), payment = getStr(LS_PAYMENT);
    var result = checkoutValidate(cart, name, hotel, room, payment);
    if (!result.ok) { showCheckoutErrors(result); return; }
    cartReviewMode = true;
    renderCartDrawer();
  }

  function backToEdit() {
    cartReviewMode = false;
    renderCartDrawer();
  }

  function confirmAndSendWhatsApp() {
    var cart = getCart();
    if (cart.length === 0) return;
    var name = getStr(LS_NAME), hotel = getStr(LS_HOTEL), room = getStr(LS_ROOM), maps = getStr(LS_MAPS), payment = getStr(LS_PAYMENT);
    var result = checkoutValidate(cart, name, hotel, room, payment);
    if (!result.ok) {
      // Something went stale while sitting on the review screen (rare) —
      // bounce back to the editable form with the specific error shown,
      // rather than silently failing to open WhatsApp.
      cartReviewMode = false;
      renderCartDrawer();
      showCheckoutErrors(result);
      return;
    }
    var lines = buildWhatsAppLines(cart, name, hotel, room, maps, payment);
    window.open(waLink(lines.join('\n')), '_blank', 'noopener');
  }

  // ===========================================================================
  // BOOKING WIDGET (per tour page)
  // ===========================================================================

  function initBooking() {
    var el = document.getElementById('booking-widget');
    if (!el) return;
    var dataEl = document.getElementById('tour-pricing');
    if (!dataEl) return;
    var data = JSON.parse(dataEl.textContent);
    var pageUrl = window.location.href;
    var photoEl = document.querySelector('.tour-hero-photo');
    var photoSrc = photoEl ? photoEl.getAttribute('src') : null;

    // Arrived here via "Editar" on a cart item? Pre-fill this widget from
    // that exact item and, on save, REPLACE it in the cart in place
    // instead of adding a duplicate. LS_EDIT_ID is single-use: consumed
    // (cleared) the instant we read it, so a later plain visit to this
    // same tour page never re-triggers edit mode by accident.
    var editItemId = getStr(LS_EDIT_ID);
    if (editItemId) setStr(LS_EDIT_ID, '');
    var editIndex = -1, editItem = null;
    if (editItemId) {
      var existingCart = getCart();
      for (var ci = 0; ci < existingCart.length; ci++) {
        if (existingCart[ci].id === editItemId && existingCart[ci].url === pageUrl) {
          editIndex = ci; editItem = existingCart[ci]; break;
        }
      }
    }

    var state = { date: '', adults: 1, children: 0, infants: 0, persons: 1, tierIndex: 0, zone: getZone() };
    if (editItem) {
      state.date = editItem.date || '';
      if (editItem.adults != null) state.adults = editItem.adults;
      if (editItem.children != null) state.children = editItem.children;
      if (editItem.persons != null) state.persons = editItem.persons;
      state.infants = editItem.infants || 0;
      if (editItem.optionLabel && data.tiers) {
        for (var ti = 0; ti < data.tiers.length; ti++) {
          if (data.tiers[ti].label === editItem.optionLabel) { state.tierIndex = ti; break; }
        }
      }
    }
    var hasInfants = data.type === 'adult_child' || data.type === 'per_person' || data.type === 'tiers';
    // schedule.type 'seasonal' or 'on_request' = no known fixed weekly
    // cadence, so any allowed date is pickable but must read as tentative,
    // never as a confirmed slot (see the `schedule` field in the data).
    var tentative = isTentativeSchedule(data.schedule);

    function calcTotal() {
      // infants (0-2 años) never add to the price, in any pricing model
      if (data.type === 'adult_child') return state.adults * data.adult + state.children * data.child;
      if (data.type === 'per_person') return state.persons * data.price;
      if (data.type === 'tiers') return state.persons * data.tiers[state.tierIndex].price;
      if (data.type === 'duration_group') return data.tiers[state.tierIndex].price;
      return null;
    }
    // Every paying traveler currently configured in the widget (mirrors
    // payingPax() for an already-added cart item) — adults+children for
    // adult_child tours, persons for everything else. Infants never pay.
    function currentPayingPax() {
      return data.type === 'adult_child' ? (state.adults + state.children) : state.persons;
    }
    function zoneSupplementMXNForState() {
      return currentPayingPax() * zoneSurchargeMXNPerPerson(data, state.zone);
    }
    // The live preview total shown on THIS page, before adding to cart —
    // base price + zone supplement, converted to USD. The cart item's own
    // `total` field (set at add time, below) stays base-only; the zone
    // supplement is always recomputed from the current zone wherever it's
    // displayed, so changing zone later in the cart updates it there too.
    function calcDisplayTotal() {
      var base = calcTotal();
      if (base == null) return null;
      return Math.round(base + mxnToUsd(zoneSupplementMXNForState()));
    }

    function counterRow(id, label, sub) {
      return '<div class="counter-row">' +
        '<div class="counter-label">' + label + (sub ? '<small>' + sub + '</small>' : '') + '</div>' +
        '<div class="counter-controls">' +
        '<button type="button" class="counter-btn" data-dec="' + id + '" aria-label="Restar">−</button>' +
        '<span class="counter-value" id="val-' + id + '">1</span>' +
        '<button type="button" class="counter-btn" data-inc="' + id + '" aria-label="Sumar">+</button>' +
        '</div></div>';
    }

    var html = editItem
      ? '<p class="mc-editing-banner">✎ Estás editando este tour en tu carrito. <a href="#" id="bw-cancel-edit">Cancelar</a></p>'
      : '';
    html += '<h3>' + (data.type === 'quote' ? 'Pedí tu cotización' : 'Reservá este tour') + '</h3>';

    if (data.type !== 'quote' && data.type !== 'duration_group') {
      var priceLabel = data.type === 'adult_child'
        ? usd(data.adult) + ' <small>adulto</small> · ' + usd(data.child) + ' <small>niño</small>'
        : (data.type === 'tiers' ? usd(data.tiers[0].price) + ' <small>desde, por persona</small>' : usd(data.price) + ' <small>por persona</small>');
      html += '<div class="booking-price">' + priceLabel + '</div>';
    } else if (data.type === 'duration_group') {
      html += '<div class="booking-price">' + usd(data.tiers[0].price) + ' <small>desde, por el grupo (hasta ' + (data.maxGroup || 7) + ' personas)</small></div>';
    }

    var seasonMonths = data.schedule && data.schedule.type === 'seasonal' ? data.schedule.months : null;
    // A tour can override the generic tentative-note wording with its own
    // real reason (e.g. pesca-yate-cancun: boat/weather/logistics) via
    // `scheduleNote` — falls back to the generic "no fixed days" note.
    var tentativeNote = data.scheduleNote || ('Este tour no tiene días fijos de operación' +
      (seasonMonths ? ' (opera de ' + MESES_LARGO[seasonMonths[0] - 1] + ' a ' + MESES_LARGO[seasonMonths[seasonMonths.length - 1] - 1] + ')' : '') +
      ' — la fecha queda sujeta a que Agustín confirme disponibilidad por WhatsApp.');
    html += '<div class="booking-field"><label>' + (tentative ? 'Fecha tentativa' : 'Fecha preferida') + '</label>' +
      datePickerHtml('bw-datepicker') +
      (tentative ? '<p class="payment-note">' + tentativeNote + '</p>' : '') +
      '</div>';

    // Pickup zone: skipped entirely for tours marked zoneExempt (only
    // pesca-yate-cancun today — it has its own fixed pickup point, Marina
    // Kaybal, so a hotel-zone supplement doesn't apply there at all).
    if (!data.zoneExempt) {
      html += '<div class="booking-field"><label>Zona de recogida</label>' +
        zoneSelectHtml('bw-zone', state.zone) +
        '<p class="payment-note">Todos los precios publicados ya incluyen salida desde Playa del Carmen / Playacar.</p>' +
        '<p class="payment-note mc-zone-help">' + ZONE_HELP_NOTE + '</p>' +
        '<p class="payment-note mc-zone-supplement" id="bw-zone-note" hidden></p>' +
        '</div>';
    }

    if (data.type === 'tiers' || data.type === 'duration_group') {
      html += '<div class="booking-field"><label>' + (data.type === 'duration_group' ? 'Duración' : 'Opción') + '</label><div class="tier-options" id="bw-tiers">';
      data.tiers.forEach(function (t, i) {
        html += '<label class="tier-option' + (i === state.tierIndex ? ' selected' : '') + '" data-tier="' + i + '">' +
          '<span><input type="radio" name="bw-tier" value="' + i + '"' + (i === state.tierIndex ? ' checked' : '') + '> ' + t.label + '</span>' +
          '<span class="tier-price">' + usd(t.price) + (data.type === 'tiers' ? '/persona' : '') + '</span></label>';
      });
      html += '</div></div>';
    }

    if (data.type === 'adult_child') {
      html += '<div class="booking-field">' +
        counterRow('adults', 'Adultos', '10 años en adelante') +
        counterRow('children', 'Niños', '3 a 9 años') +
        '</div>';
    } else if (data.type !== 'duration_group') {
      html += '<div class="booking-field">' + counterRow('persons', 'Personas', null) + '</div>';
    } else {
      html += '<div class="booking-field">' + counterRow('persons', 'Pasajeros', 'Hasta ' + (data.maxGroup || 7) + ' por embarcación') + '</div>';
    }

    if (hasInfants) {
      html += '<div class="booking-field">' + counterRow('infants', 'Infantes', '0 a 2 años · sin cargo, pero cuentan para el transporte') + '</div>';
    }

    if (data.type !== 'quote' && data.type !== 'duration_group') {
      html += '<div class="booking-total-row"><span class="label">Total</span><span class="total" id="bw-total">' + usd(calcDisplayTotal()) + '</span></div>';
    }

    // Guest data (nombre, hotel, habitación, ubicación, método de pago) is
    // asked ONCE, in the cart/checkout — not repeated on every tour page.
    // This widget only decides what varies per tour: fecha y pasajeros.
    html += '<button type="button" class="btn-primary" id="bw-cta">' + (editItem ? 'Guardar cambios' : '🛒 Agregar al carrito') + '</button>';
    html += '<p class="contact-form-status" id="bw-checkout-status"></p>';
    html += '<div id="bw-added" class="bw-added" hidden>' +
      '<p>' + (editItem ? '✓ Cambios guardados' : '✓ Agregado al carrito') + '</p>' +
      '<button type="button" class="btn-primary" id="bw-goto-cart">Ver carrito y reservar →</button>' +
      '<button type="button" class="btn-secondary" id="bw-keep-browsing">Seguir viendo tours</button>' +
      '</div>';
    html += '<p class="booking-fineprint">Se coordina y confirma directo por WhatsApp con Agustín.</p>';

    el.innerHTML = html;
    updateTotal();

    var datepickerEl = document.getElementById('bw-datepicker');
    initDatePicker(datepickerEl, {
      schedule: data.schedule,
      tentative: tentative,
      initialISO: state.date || null,
      onSelect: function (iso) {
        state.date = iso;
        datepickerEl.classList.remove('field-invalid');
      }
    });

    function bindCounter(id, key, min, max) {
      var valEl = document.getElementById('val-' + id);
      if (!valEl) return;
      valEl.textContent = state[key];
      el.querySelectorAll('[data-dec="' + id + '"]').forEach(function (b) {
        b.addEventListener('click', function () { if (state[key] > min) { state[key]--; valEl.textContent = state[key]; updateTotal(); } });
      });
      el.querySelectorAll('[data-inc="' + id + '"]').forEach(function (b) {
        b.addEventListener('click', function () { if (state[key] < max) { state[key]++; valEl.textContent = state[key]; updateTotal(); } });
      });
    }
    if (data.type === 'adult_child') { bindCounter('adults', 'adults', 1, 30); bindCounter('children', 'children', 0, 30); }
    else if (data.type !== 'duration_group') bindCounter('persons', 'persons', 1, 30);
    else bindCounter('persons', 'persons', 1, data.maxGroup || 7);
    if (hasInfants) bindCounter('infants', 'infants', 0, 10);

    var tierEls = el.querySelectorAll('.tier-option');
    tierEls.forEach(function (opt) {
      opt.addEventListener('click', function () {
        tierEls.forEach(function (o) { o.classList.remove('selected'); });
        opt.classList.add('selected');
        opt.querySelector('input').checked = true;
        state.tierIndex = parseInt(opt.getAttribute('data-tier'), 10);
        if (data.type === 'duration_group') {
          var priceEl = el.querySelector('.booking-price');
          if (priceEl) priceEl.innerHTML = usd(data.tiers[state.tierIndex].price) + ' <small>por el grupo (hasta ' + (data.maxGroup || 7) + ' personas)</small>';
        }
        updateTotal();
      });
    });

    // Payment method (and its card surcharge / MXN conversion) is chosen
    // later, in the cart — this page shows the base price plus the zone
    // supplement (if any), always clearly broken out in its own line.
    function updateTotal() {
      var t = document.getElementById('bw-total');
      if (t) t.textContent = usd(calcDisplayTotal());
      var noteEl = document.getElementById('bw-zone-note');
      if (noteEl) {
        var mxnAmt = zoneSupplementMXNForState();
        if (mxnAmt > 0) {
          var pax = currentPayingPax();
          noteEl.hidden = false;
          noteEl.textContent = '+ ' + mxn(mxnAmt) + ' de cargo adicional por ubicación (' + pax + (pax === 1 ? ' pasajero' : ' pasajeros') + '), ya incluido en el total.';
        } else {
          noteEl.hidden = true;
        }
      }
    }
    var zoneSelectEl = document.getElementById('bw-zone');
    if (zoneSelectEl) {
      zoneSelectEl.addEventListener('change', function (e) {
        state.zone = e.target.value;
        setZone(state.zone);
        updateTotal();
      });
    }

    // Duplicate-prevention (see the "Agregado al carrito" CTA below): a
    // tour already sitting in the cart can't be added a second time from
    // this page — the only way to change it is the cart's own "Editar",
    // which arrives here with editItem set and bypasses this check
    // entirely. Re-checked (not just set once) so it stays correct if the
    // cart changes elsewhere while this page is open (see
    // window.__mcBookingSync, wired from removeFromCart()).
    function isAlreadyInCart() {
      return !editItem && getCart().some(function (i) { return i.url === pageUrl; });
    }
    function refreshAddState() {
      var ctaBtn = document.getElementById('bw-cta');
      if (!ctaBtn) return;
      if (isAlreadyInCart()) {
        ctaBtn.disabled = true;
        ctaBtn.textContent = '✓ Agregado al carrito';
      } else {
        ctaBtn.disabled = false;
        ctaBtn.textContent = editItem ? 'Guardar cambios' : '🛒 Agregar al carrito';
      }
    }
    refreshAddState();
    window.__mcBookingSync = refreshAddState;

    // Structured passenger fields for this cart item — kept per-tour
    // (never summed/shared with other tours in the same cart), so pricing
    // and the WhatsApp summary always reflect THIS tour's own group.
    function cartFields() {
      var f = { optionLabel: null, adults: null, children: null, persons: null, infants: hasInfants ? state.infants : 0 };
      if (data.type === 'adult_child') { f.adults = state.adults; f.children = state.children; }
      else if (data.type === 'tiers') { f.persons = state.persons; f.optionLabel = data.tiers[state.tierIndex].label; }
      else if (data.type === 'duration_group') { f.persons = state.persons; f.optionLabel = data.tiers[state.tierIndex].label; }
      else { f.persons = state.persons; } // per_person, quote
      return f;
    }

    // Guards against both duplicate-adds this CTA can otherwise cause:
    // `adding` blocks a second click firing before this (synchronous)
    // handler finishes and disables the button; `isAlreadyInCart()` blocks
    // an add from a stale render (e.g. two tabs on the same tour page).
    var adding = false;
    document.getElementById('bw-cta').addEventListener('click', function () {
      if (adding || isAlreadyInCart()) return;
      // Re-check the date against the schedule here too — greying out
      // invalid days in the calendar isn't enough on its own (state could
      // in principle hold a stale/invalid value some other way). Guest
      // data (nombre, hotel, pago, etc.) is validated later, in the cart.
      var dateOk = isDateAllowed(state.date, data.schedule);
      if (!dateOk) {
        var status = document.getElementById('bw-checkout-status');
        if (status) {
          status.textContent = 'Elegí una fecha válida para este tour antes de agregar al carrito.';
          status.className = 'contact-form-status error';
        }
        datepickerEl.classList.add('field-invalid');
        return;
      }
      adding = true;
      var cart = getCart();
      var fields = cartFields();
      var record = {
        id: editItem ? editItem.id : genId(),
        name: data.name,
        date: state.date,
        tentative: tentative,
        schedule: data.schedule,
        optionLabel: fields.optionLabel,
        adults: fields.adults,
        children: fields.children,
        persons: fields.persons,
        infants: fields.infants,
        total: data.type === 'quote' ? null : calcTotal(),
        zoneExempt: !!data.zoneExempt,
        zone3SurchargeMXN: data.zone3SurchargeMXN || null,
        url: pageUrl,
        photo: photoSrc,
      };
      if (editIndex !== -1) cart[editIndex] = record; else cart.push(record);
      setCart(cart);
      updateCartBadge();
      refreshAddState();
      document.getElementById('bw-added').hidden = false;
      adding = false;
    });
    var cancelEditLink = document.getElementById('bw-cancel-edit');
    if (cancelEditLink) {
      cancelEditLink.addEventListener('click', function (e) { e.preventDefault(); window.mcOpenCart(); });
    }
    document.getElementById('bw-goto-cart').addEventListener('click', function () { window.mcOpenCart(); });
    // Only dismisses the one-time confirmation banner — the CTA underneath
    // stays exactly as refreshAddState() left it (disabled + "Agregado al
    // carrito" for a fresh add), it's never reset back to addable here.
    document.getElementById('bw-keep-browsing').addEventListener('click', function () {
      document.getElementById('bw-added').hidden = true;
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    ensureCartVersion();
    initReveal();
    injectCartUI();
    initBooking();
    initNavDropdown();
    initMobileMenu();
    initCarousels();
    initContactForm();
    initAgustinStories();
    initFaq();
    initReviewsCarousel();
  });

  // ---------- FAQ accordion (home) ----------
  function initFaq() {
    var triggers = document.querySelectorAll('.faq-trigger');
    triggers.forEach(function (btn) {
      var answer = document.getElementById(btn.getAttribute('aria-controls'));
      if (!answer) return;
      btn.addEventListener('click', function () {
        var isOpen = btn.getAttribute('aria-expanded') === 'true';
        btn.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
        answer.hidden = isOpen;
      });
    });
  }

  // ---------- mobile nav (hamburger + panel) ----------
  function initMobileMenu() {
    var burger = document.querySelector('.nav-burger');
    var menu = document.getElementById('mobile-menu');
    if (!burger || !menu) return;

    function open() {
      menu.hidden = false;
      burger.setAttribute('aria-expanded', 'true');
    }
    function close() {
      menu.hidden = true;
      burger.setAttribute('aria-expanded', 'false');
    }

    burger.addEventListener('click', function (e) {
      e.stopPropagation(); // keep this click from also hitting the "outside click" listener below
      if (menu.hidden) open(); else close();
    });
    // tapping any link inside (category, "ver todos", Contacto, WhatsApp) closes the panel,
    // so e.g. the #contacto in-page anchor scrolls to a section that's actually visible
    menu.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') close();
    });
    document.addEventListener('click', function (e) {
      if (!menu.hidden && !menu.contains(e.target)) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !menu.hidden) { close(); burger.focus(); }
    });
    // resizing past the mobile breakpoint (e.g. rotating a tablet) shouldn't
    // leave the panel stuck open behind the now-visible desktop nav
    window.addEventListener('resize', function () {
      if (window.innerWidth > 640 && !menu.hidden) close();
    });
  }

  // ---------- contact form (Formspree, for travelers still 1-3 months out) ----------
  function initContactForm() {
    var form = document.getElementById('mc-contact-form');
    if (!form) return;
    var status = document.getElementById('mc-contact-status');
    var btn = form.querySelector('button[type="submit"]');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      btn.disabled = true;
      status.textContent = 'Enviando...';
      status.className = 'contact-form-status';
      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' }
      }).then(function (res) {
        if (res.ok) {
          form.reset();
          status.textContent = '¡Gracias! Te contactamos pronto.';
          status.className = 'contact-form-status ok';
        } else {
          throw new Error('bad status');
        }
      }).catch(function () {
        status.textContent = 'No se pudo enviar. Probá de nuevo o escribinos por WhatsApp.';
        status.className = 'contact-form-status error';
      }).then(function () {
        btn.disabled = false;
      });
    });
  }

  // ===========================================================================
  // NAV "TOURS" DROPDOWN (categories + "Ver todos los tours")
  // ===========================================================================

  function initNavDropdown() {
    var dropdowns = document.querySelectorAll('.nav-dropdown');
    dropdowns.forEach(function (dd) {
      var trigger = dd.querySelector('.nav-dropdown-trigger');
      if (!trigger) return;
      function close() {
        dd.classList.remove('open');
        trigger.setAttribute('aria-expanded', 'false');
      }
      function toggle(e) {
        e.stopPropagation();
        var willOpen = !dd.classList.contains('open');
        dropdowns.forEach(function (other) { other.classList.remove('open'); });
        if (willOpen) {
          dd.classList.add('open');
          trigger.setAttribute('aria-expanded', 'true');
        } else {
          close();
        }
      }
      trigger.addEventListener('click', toggle);
      dd.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { close(); trigger.focus(); }
      });
    });
    document.addEventListener('click', function () {
      dropdowns.forEach(function (dd) { dd.classList.remove('open'); });
    });
  }

  // ===========================================================================
  // HORIZONTAL DRAG CAROUSEL — infinite loop via cloned card sets
  // ===========================================================================

  function initCarousels() {
    var wraps = document.querySelectorAll('.tour-carousel-wrap');
    wraps.forEach(function (wrap) {
      var track = wrap.querySelector('.tour-carousel');
      if (!track) return;
      var originalCards = Array.prototype.slice.call(track.children);
      // fewer than 2 cards: nothing to loop, leave as a plain (non-scrolling) row
      if (originalCards.length < 2) return;

      // triple the set: [clone][originals][clone] so we can silently jump
      // between equivalent scroll positions and never hit a hard edge
      var beforeFrag = document.createDocumentFragment();
      var afterFrag = document.createDocumentFragment();
      originalCards.forEach(function (card) { beforeFrag.appendChild(card.cloneNode(true)); });
      originalCards.forEach(function (card) { afterFrag.appendChild(card.cloneNode(true)); });
      track.insertBefore(beforeFrag, track.firstChild);
      track.appendChild(afterFrag);

      var setWidth = 0;
      function measure() {
        setWidth = track.scrollWidth / 3;
      }
      measure();
      wrap.scrollLeft = setWidth; // start on the middle (real) set

      var isDown = false, dragged = false, startX = 0, startScroll = 0;
      var lastX = 0, lastT = 0, velocity = 0, momentumId = null;

      function cancelMomentum() {
        if (momentumId) { cancelAnimationFrame(momentumId); momentumId = null; }
      }
      function startMomentum() {
        var vel = velocity * 16;
        function step() {
          vel *= 0.95;
          wrap.scrollLeft -= vel;
          if (Math.abs(vel) > 0.5) momentumId = requestAnimationFrame(step);
          else momentumId = null;
        }
        if (Math.abs(vel) > 0.5) momentumId = requestAnimationFrame(step);
      }
      function endDrag() {
        if (!isDown) return;
        isDown = false;
        wrap.classList.remove('dragging');
        if (dragged) startMomentum();
      }

      // seamless loop: when the scroll position drifts into either clone
      // set, jump it back by exactly one set-width. Also nudge startScroll
      // by the same amount so an in-progress drag doesn't fight the jump
      // on the next mousemove tick.
      wrap.addEventListener('scroll', function () {
        if (setWidth <= 0) return;
        if (wrap.scrollLeft <= 0) {
          wrap.scrollLeft += setWidth;
          startScroll += setWidth;
        } else if (wrap.scrollLeft >= setWidth * 2) {
          wrap.scrollLeft -= setWidth;
          startScroll -= setWidth;
        }
      });

      // ---- mouse (desktop) ----
      wrap.addEventListener('mousedown', function (e) {
        isDown = true; dragged = false;
        startX = e.pageX; startScroll = wrap.scrollLeft;
        lastX = e.pageX; lastT = Date.now(); velocity = 0;
        // NOTE: do NOT add .dragging here. .dragging sets pointer-events:none
        // on .tour-card (below) so cards don't intercept the drag — but if we
        // added it on mousedown, a plain click (mousedown+mouseup with zero
        // movement) would ALSO get pointer-events:none applied to the <a>
        // mid-gesture, so the browser's re-hit-test on mouseup/click misses
        // the anchor entirely and navigation silently never fires. This was
        // breaking every single click on a carousel card on desktop, not
        // just real drags. Only add .dragging once we've confirmed an
        // actual drag (see mousemove below).
        cancelMomentum();
      });
      window.addEventListener('mousemove', function (e) {
        if (!isDown) return;
        e.preventDefault();
        var dx = e.pageX - startX;
        if (Math.abs(dx) > 5) {
          dragged = true;
          wrap.classList.add('dragging');
        }
        wrap.scrollLeft = startScroll - dx;
        var now = Date.now(), dt = now - lastT;
        if (dt > 0) { velocity = (e.pageX - lastX) / dt; lastT = now; lastX = e.pageX; }
      });
      window.addEventListener('mouseup', endDrag);
      wrap.addEventListener('mouseleave', endDrag);

      // ---- touch (mobile): native scroll already works, just track drag
      // distance so we can tell a swipe apart from a tap and not accidentally
      // open a tour card ----
      var touchStartX = 0;
      wrap.addEventListener('touchstart', function (e) {
        touchStartX = e.touches[0].pageX; dragged = false;
      }, { passive: true });
      wrap.addEventListener('touchmove', function (e) {
        if (Math.abs(e.touches[0].pageX - touchStartX) > 8) dragged = true;
      }, { passive: true });

      // swallow the click that follows a real drag/swipe so cards don't
      // get "activated" by accident
      wrap.addEventListener('click', function (e) {
        if (dragged) { e.preventDefault(); e.stopPropagation(); }
        dragged = false;
      }, true);

      window.addEventListener('resize', measure);
    });
  }

  // ===========================================================================
  // GOOGLE REVIEWS CAROUSEL (home) — auto-advancing, pausable, draggable,
  // swipeable, arrow- and keyboard-navigable, infinite loop
  // ===========================================================================
  //
  // Built on the same technique as the tour carousel above (real native
  // scrollLeft + a triple clone set so the loop can jump silently between
  // equivalent positions) instead of the old CSS @keyframes approach,
  // because a transform-driven animation can't be dragged or nudged by
  // arrow/keyboard input without fighting it. A single requestAnimationFrame
  // loop nudges scrollLeft forward continuously; drag, touch, arrows and
  // keyboard all just move that same scrollLeft, so pausing/resuming the
  // loop is never a jump — the automatic movement just picks back up
  // smoothly from wherever the visitor left it.
  function initReviewsCarousel() {
    var wrap = document.getElementById('review-carousel-wrap') || document.querySelector('.review-carousel-wrap');
    if (!wrap) return;
    var track = wrap.querySelector('.review-carousel');
    if (!track) return;
    var originalCards = Array.prototype.slice.call(track.children);
    if (originalCards.length < 2) return; // nothing meaningful to loop

    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // With only a handful of real review cards, one real "set" can be
    // narrower than the visible viewport (.container maxes out at
    // 1160px, one set of 3 cards is under 1000px). A single clone set on
    // each side (old approach) then never leaves enough scrollable
    // buffer for the wraparound correction below to fire before the
    // browser clamps scrollLeft at its native end — the carousel visibly
    // stalls instead of looping. Stacking BUFFER_SETS clone sets on each
    // side guarantees a safety margin far wider than any realistic
    // viewport, so the jump always happens well before that clamp.
    var BUFFER_SETS = 3;
    for (var side = 0; side < BUFFER_SETS; side++) {
      var beforeFrag = document.createDocumentFragment();
      var afterFrag = document.createDocumentFragment();
      originalCards.forEach(function (card) {
        var b = card.cloneNode(true); b.setAttribute('aria-hidden', 'true'); beforeFrag.appendChild(b);
      });
      originalCards.forEach(function (card) {
        var a = card.cloneNode(true); a.setAttribute('aria-hidden', 'true'); afterFrag.appendChild(a);
      });
      track.insertBefore(beforeFrag, track.firstChild);
      track.appendChild(afterFrag);
    }

    var setWidth = 0;
    var totalWidth = 0;
    function measure() {
      setWidth = track.scrollWidth / (BUFFER_SETS * 2 + 1);
      totalWidth = track.scrollWidth;
    }
    measure();
    wrap.scrollLeft = setWidth * BUFFER_SETS; // start on the middle (real) set

    wrap.addEventListener('scroll', function () {
      if (setWidth <= 0) return;
      // Keep at least one full set of buffer beyond both edges of the
      // visible viewport at all times; jump by a whole number of set
      // widths (identical clones) so the correction is pixel-seamless.
      if (wrap.scrollLeft <= setWidth) wrap.scrollLeft += setWidth * BUFFER_SETS;
      else if (wrap.scrollLeft + wrap.clientWidth >= totalWidth - setWidth) wrap.scrollLeft -= setWidth * BUFFER_SETS;
    });
    window.addEventListener('resize', measure);

    // ---- continuous autoplay ----
    var AUTO_SPEED = 0.4; // px/frame — slow enough to stay readable
    var paused = false;
    var rafId = null;
    function tick() {
      if (!paused) wrap.scrollLeft += AUTO_SPEED;
      rafId = requestAnimationFrame(tick);
    }
    function startAutoplay() { if (!reduce && rafId === null) rafId = requestAnimationFrame(tick); }
    function stopAutoplay() { if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; } }
    function pause() { paused = true; }
    function resume() { paused = false; }

    wrap.addEventListener('mouseenter', pause);
    wrap.addEventListener('mouseleave', resume);
    wrap.addEventListener('focusin', pause);
    wrap.addEventListener('focusout', resume);
    wrap.addEventListener('touchstart', pause, { passive: true });
    wrap.addEventListener('touchend', resume);
    wrap.addEventListener('touchcancel', resume);

    // ---- mouse drag (desktop) — same drag-vs-click distinction as the
    // tour carousel: .dragging (which disables pointer-events on cards)
    // is only added once real movement is confirmed, never on a plain
    // click, and text selection is disabled via CSS on the wrap itself. ----
    var isDown = false, dragged = false, startX = 0, startScroll = 0;
    wrap.addEventListener('mousedown', function (e) {
      isDown = true; dragged = false; startX = e.pageX; startScroll = wrap.scrollLeft;
      pause();
    });
    window.addEventListener('mousemove', function (e) {
      if (!isDown) return;
      e.preventDefault();
      var dx = e.pageX - startX;
      if (Math.abs(dx) > 5) { dragged = true; wrap.classList.add('dragging'); }
      wrap.scrollLeft = startScroll - dx;
    });
    function endDrag() {
      if (!isDown) return;
      isDown = false;
      wrap.classList.remove('dragging');
      resume();
    }
    window.addEventListener('mouseup', endDrag);
    wrap.addEventListener('mouseleave', endDrag);
    wrap.addEventListener('click', function (e) {
      if (dragged) { e.preventDefault(); e.stopPropagation(); }
      dragged = false;
    }, true);

    // ---- touch swipe: overflow-x:auto already gives native swipe
    // scrolling for free — only pause/resume (above) is needed here. ----

    // ---- keyboard (ArrowLeft/ArrowRight on the focusable wrap, which
    // carries tabindex="0" in the markup) — no visible nav buttons, but
    // the carousel stays keyboard-operable once focused. ----
    function cardStep() {
      var first = track.querySelector('.tour-card');
      if (!first) return wrap.clientWidth;
      var gap = parseFloat(window.getComputedStyle(track).gap) || 0;
      return first.getBoundingClientRect().width + gap;
    }
    wrap.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); wrap.scrollBy({ left: cardStep(), behavior: reduce ? 'auto' : 'smooth' }); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); wrap.scrollBy({ left: -cardStep(), behavior: reduce ? 'auto' : 'smooth' }); }
    });

    startAutoplay();

    // Reacting live to a change in the visitor's motion preference: stop
    // or (re)start the auto-advance loop — drag/arrows/keyboard keep
    // working either way, since those are visitor-initiated, not
    // automatic, motion.
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', function (e) {
      reduce = e.matches;
      if (reduce) stopAutoplay(); else startAutoplay();
    });
  }

  // ===========================================================================
  // "CONOCÉ A AGUSTÍN" STORY VIEWER (home)
  // ===========================================================================
  //
  // Instagram-style story viewer, built from scratch (no library, no
  // Instagram branding/icons/logo anywhere): one progress bar per photo,
  // tap left/right (desktop click or mobile tap) or swipe to move between
  // photos, press-and-hold to pause, autoplay that advances on its own,
  // and a discrete chip (location pin / mention) on the few photos that
  // carry a confirmed link — opened in a new tab, never inline navigation.
  // Respects prefers-reduced-motion: no autoplay, no animated progress
  // fill — the viewer becomes fully manual (tap/swipe/keys still work).

  var STORY_DURATION_MS = 5000;

  function initAgustinStories() {
    var entry = document.getElementById('mc-story-entry');
    var dataEl = document.getElementById('agustin-stories-data');
    var overlay = document.getElementById('mc-story-overlay');
    if (!entry || !dataEl || !overlay) return;

    var stories = JSON.parse(dataEl.textContent);
    var barsEl = document.getElementById('mc-story-bars');
    var imgEl = document.getElementById('mc-story-img');
    var videoEl = document.getElementById('mc-story-video');
    var hitEl = document.getElementById('mc-story-hit');
    var media = document.getElementById('mc-story-media');
    var closeBtn = document.getElementById('mc-story-close');
    var prevBtn = document.getElementById('mc-story-prev');
    var nextBtn = document.getElementById('mc-story-next');
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    barsEl.innerHTML = stories.map(function () {
      return '<div class="mc-story-bar"><div class="mc-story-bar-fill"></div></div>';
    }).join('');
    var fills = Array.prototype.slice.call(barsEl.querySelectorAll('.mc-story-bar-fill'));

    var index = 0;
    var currentAnim = null;

    function stopTimer() {
      if (currentAnim) { currentAnim.cancel(); currentAnim = null; }
    }
    function pauseTimer() {
      if (currentAnim && currentAnim.playState === 'running') currentAnim.pause();
      if (stories[index].type === 'video') videoEl.pause();
    }
    function resumeTimer() {
      if (currentAnim && currentAnim.playState === 'paused') currentAnim.play();
      if (stories[index].type === 'video') videoEl.play().catch(function () {});
    }
    // durationMs: fixed for photos, but a video's bar has to last exactly
    // as long as the video itself — the caller passes the real duration
    // once it's known (the video's metadata), not before. autoAdvance is
    // false for video: the bar there is purely visual, driven by the
    // SAME duration as the video, but what actually triggers "next" is
    // the video's own `ended` event (see onVideoEnded) — never both, or
    // a late/duplicate advance could skip a story.
    function startTimer(durationMs, autoAdvance) {
      var fill = fills[index];
      if (reduceMotion) {
        // No auto-advance, no animated motion — just mark progress
        // statically so the viewer still shows where you are. A video
        // still plays once (it's the content the visitor opened), it
        // just won't auto-advance to the next story on its own.
        fill.style.width = '100%';
        return;
      }
      fill.style.width = '';
      currentAnim = fill.animate(
        [{ width: '0%' }, { width: '100%' }],
        { duration: durationMs, easing: 'linear', fill: 'forwards' }
      );
      if (autoAdvance !== false) currentAnim.onfinish = function () { goNext(); };
    }

    // ---- video stories: a single source of truth for "move on" ----
    // `currentVideoStory` identifies which story object the video
    // element's listeners currently belong to. Combined with actually
    // removing those listeners in clearVideoHandlers() (called before
    // every render and on close), a handler left over from a story the
    // visitor has already navigated away from can never fire again —
    // and even if one somehow did, this guard makes it a no-op.
    var currentVideoStory = null;
    var videoFallbackTimer = null;

    function clearVideoHandlers() {
      videoEl.removeEventListener('loadedmetadata', onVideoReady);
      videoEl.removeEventListener('ended', onVideoEnded);
      videoEl.removeEventListener('error', onVideoError);
      videoEl.removeEventListener('stalled', onVideoError);
      if (videoFallbackTimer) { clearTimeout(videoFallbackTimer); videoFallbackTimer = null; }
    }
    function stopVideo() {
      clearVideoHandlers();
      currentVideoStory = null;
      videoEl.pause();
    }
    function onVideoReady() {
      if (stories[index] !== currentVideoStory) return; // stale — visitor already moved on
      var d = videoEl.duration;
      startTimer((isFinite(d) && d > 0 ? d : 5) * 1000, false);
    }
    function onVideoEnded() {
      if (stories[index] !== currentVideoStory) return;
      // Same rule as photos under reduced motion: nothing advances on
      // its own, the video just stays on its last frame until the
      // visitor taps/swipes manually.
      if (reduceMotion) return;
      goNext();
    }
    function onVideoError() {
      if (stories[index] !== currentVideoStory) return;
      // Couldn't load or play this video — never strand the viewer on a
      // stuck/looping frame: mark this story "done" and move on shortly,
      // same as it would if it had actually finished playing.
      var failed = currentVideoStory;
      clearVideoHandlers();
      currentVideoStory = null;
      if (fills[index]) fills[index].style.width = '100%';
      videoFallbackTimer = setTimeout(function () {
        if (stories[index] === failed) goNext();
      }, 2000);
    }

    // No visible chip/pill/text of our own — the tap target is an
    // invisible rectangle laid exactly over that photo's OWN original
    // sticker (location pin or mention), sized/positioned from `pos`
    // (percent of the photo itself, measured by hand per photo). A photo
    // with no confirmed link gets no tap target at all.
    var currentTag = null;
    function positionHit() {
      if (!currentTag) return;
      // The <img> box now always fills the whole media area (see CSS —
      // it's `position:absolute; inset:0` with `object-fit:contain`),
      // so it's no longer the same rectangle as the visible picture
      // when the photo's own aspect ratio doesn't match the screen's.
      // Work out that inner "letterboxed" picture rect by hand (the
      // standard object-fit:contain math) before placing the hit area.
      var mediaRect = media.getBoundingClientRect();
      var boxRect = imgEl.getBoundingClientRect(); // == the full media area
      var nw = imgEl.naturalWidth, nh = imgEl.naturalHeight;
      if (!nw || !nh || boxRect.width === 0 || boxRect.height === 0) return; // not loaded/laid out yet
      var boxAspect = boxRect.width / boxRect.height;
      var picAspect = nw / nh;
      var picW, picH;
      if (picAspect > boxAspect) { picW = boxRect.width; picH = picW / picAspect; }
      else { picH = boxRect.height; picW = picH * picAspect; }
      var picLeft = (boxRect.left - mediaRect.left) + (boxRect.width - picW) / 2;
      var picTop = (boxRect.top - mediaRect.top) + (boxRect.height - picH) / 2;
      var pos = currentTag.pos;
      hitEl.style.left = (picLeft + (pos.left / 100) * picW) + 'px';
      hitEl.style.top = (picTop + (pos.top / 100) * picH) + 'px';
      hitEl.style.width = ((pos.width / 100) * picW) + 'px';
      hitEl.style.height = ((pos.height / 100) * picH) + 'px';
    }
    function updateHit(tag) {
      currentTag = (tag && tag.pos) ? tag : null;
      if (!currentTag) { hitEl.hidden = true; return; }
      hitEl.href = tag.url;
      hitEl.setAttribute('aria-label', tag.label);
      hitEl.hidden = false;
      positionHit();
    }

    function renderIndex() {
      fills.forEach(function (fill, i) { fill.style.width = i < index ? '100%' : '0%'; });
      stopTimer();
      stopVideo(); // detach the previous video story's listeners/timers before anything else
      var s = stories[index];
      if (s.type === 'video') {
        imgEl.hidden = true;
        videoEl.hidden = false;
        videoEl.setAttribute('aria-label', s.alt || '');
        currentVideoStory = s;
        videoEl.addEventListener('ended', onVideoEnded);
        videoEl.addEventListener('error', onVideoError);
        videoEl.addEventListener('stalled', onVideoError);
        // Reinitialize fully from 0 every time this story is entered —
        // re-assigning .src and calling .load() forces a real reset
        // instead of possibly resuming wherever a previous play left off.
        videoEl.src = s.src;
        videoEl.load();
        videoEl.currentTime = 0;
        // The bar has to run exactly as long as the video — wait for its
        // real duration (metadata) before starting it, instead of
        // guessing with the photos' fixed duration.
        if (videoEl.readyState >= 1 && isFinite(videoEl.duration) && videoEl.duration > 0) onVideoReady();
        else videoEl.addEventListener('loadedmetadata', onVideoReady);
        // Safety net: if the video never fires 'loadedmetadata'/'ended'/
        // 'error' at all (silent network hang, odd device quirk), don't
        // strand the viewer indefinitely — move on after a few seconds.
        videoFallbackTimer = setTimeout(function () {
          if (stories[index] === s) { clearVideoHandlers(); currentVideoStory = null; goNext(); }
        }, 8000);
        var playPromise = videoEl.play();
        if (playPromise && playPromise.catch) playPromise.catch(onVideoError);
      } else {
        videoEl.hidden = true;
        imgEl.hidden = false;
        imgEl.alt = s.alt || '';
        imgEl.src = s.src;
        startTimer(STORY_DURATION_MS);
      }
      updateHit(s.tag);
    }

    function showIndex(i) {
      if (i < 0) i = 0;
      if (i >= stories.length) { closeViewer(); return; }
      index = i;
      renderIndex();
    }
    function goNext() { showIndex(index + 1); }
    function goPrev() { showIndex(index - 1); }

    function openViewer(startIndex) {
      document.body.style.overflow = 'hidden';
      overlay.hidden = false;
      showIndex(startIndex || 0);
    }
    function closeViewer() {
      stopTimer();
      stopVideo();
      overlay.hidden = true;
      document.body.style.overflow = '';
    }

    entry.addEventListener('click', function () { openViewer(0); });
    closeBtn.addEventListener('click', closeViewer);
    prevBtn.addEventListener('click', function (e) { e.stopPropagation(); goPrev(); });
    nextBtn.addEventListener('click', function (e) { e.stopPropagation(); goNext(); });
    document.addEventListener('keydown', function (e) {
      if (overlay.hidden) return;
      if (e.key === 'Escape') closeViewer();
      else if (e.key === 'ArrowRight') goNext();
      else if (e.key === 'ArrowLeft') goPrev();
    });

    // Tap left/right (desktop click or a quick mobile tap) navigates;
    // press-and-hold pauses and resumes on release; a real horizontal
    // drag/swipe navigates instead — same drag-vs-click distinction the
    // tour carousel uses elsewhere in this file, adapted for one axis.
    var TAP_MAX_MS = 300, MOVE_TOLERANCE = 10, SWIPE_THRESHOLD = 50;
    var pStart = null;
    media.addEventListener('pointerdown', function (e) {
      if (e.target.closest('.mc-story-hit') || e.target.closest('.mc-story-nav')) return;
      pStart = { x: e.clientX, y: e.clientY, t: Date.now() };
      pauseTimer();
    });
    media.addEventListener('pointerup', function (e) {
      if (!pStart) return;
      var dx = e.clientX - pStart.x, dy = e.clientY - pStart.y, dt = Date.now() - pStart.t;
      var absDx = Math.abs(dx), absDy = Math.abs(dy);
      pStart = null;
      if (absDx > SWIPE_THRESHOLD && absDx > absDy) { dx < 0 ? goNext() : goPrev(); return; }
      if (dt <= TAP_MAX_MS && absDx < MOVE_TOLERANCE && absDy < MOVE_TOLERANCE) {
        var rect = media.getBoundingClientRect();
        var relX = (e.clientX - rect.left) / rect.width;
        relX < 0.35 ? goPrev() : goNext();
        return;
      }
      resumeTimer();
    });
    media.addEventListener('pointercancel', function () { pStart = null; resumeTimer(); });

    // The image loads asynchronously and the viewport can resize/rotate
    // while a photo with a tap target is open — both change the photo's
    // actual rendered box, so the invisible hit area has to be
    // recomputed against it each time, not just once on render.
    imgEl.addEventListener('load', positionHit);
    window.addEventListener('resize', function () { if (!overlay.hidden) positionHit(); });

    // Reacting live to a change in the visitor's motion preference (rare,
    // but cheap to handle): stop the running animation and re-render the
    // current story in whichever mode now applies.
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', function (e) {
      reduceMotion = e.matches;
      if (!overlay.hidden) {
        stopTimer();
        if (stories[index].type === 'video') {
          var d = videoEl.duration;
          startTimer((isFinite(d) && d > 0 ? d : 5) * 1000, false);
        } else {
          startTimer(STORY_DURATION_MS);
        }
      }
    });
  }
})();
