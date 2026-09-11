(function () {
  'use strict';

  var WA_NUMBER = '529841191147';

  var LS_CART = 'mc_cart';
  var LS_NAME = 'mc_name';
  var LS_HOTEL = 'mc_hotel';
  var LS_ROOM = 'mc_room';
  var LS_MAPS = 'mc_maps';
  var LS_PAYMENT = 'mc_payment';
  var LS_CART_VERSION = 'mc_cart_v';
  var CART_VERSION = 4; // bump this whenever the shape of a cart item changes, to auto-clear stale carts

  // ---------- payment methods ----------
  // All tour prices are in USD. Fixed reference rate given by Agustín, used
  // to auto-convert the total when paying cash in pesos mexicanos.
  var MXN_REFERENCE_RATE = 16.50;
  var CARD_SURCHARGE = 0.05; // 5% recargo si paga con tarjeta
  var PAYMENT_METHODS = [
    { value: 'usd_transfer', label: 'Transferencia en USD (cuenta en EE.UU.)' },
    { value: 'cash_usd', label: 'Efectivo en USD' },
    { value: 'cash_mxn', label: 'Efectivo en pesos mexicanos' },
    { value: 'ars_transfer', label: 'Transferencia en pesos argentinos (cotización del día)' },
    { value: 'cop_transfer', label: 'Transferencia en pesos colombianos (cotización del día)' },
    { value: 'card', label: 'Tarjeta de crédito/débito (+5% recargo)' }
  ];
  function paymentSelectHtml(id, current) {
    var opts = '<option value="">Elegí un método de pago</option>' + PAYMENT_METHODS.map(function (m) {
      return '<option value="' + m.value + '"' + (m.value === current ? ' selected' : '') + '>' + m.label + '</option>';
    }).join('');
    return '<select id="' + id + '">' + opts + '</select>';
  }
  function paymentLabel(value) {
    var m = PAYMENT_METHODS.filter(function (p) { return p.value === value; })[0];
    return m ? m.label : '';
  }
  function withSurcharge(total, paymentValue) {
    return paymentValue === 'card' ? Math.round(total * (1 + CARD_SURCHARGE)) : total;
  }
  function mxn(n) { return '$' + Math.round(n).toLocaleString('en-US') + ' MXN'; }
  // Formats a base USD total for display/messaging, applying the card
  // surcharge and/or the automatic USD->MXN conversion depending on the
  // chosen payment method.
  function formatTotal(baseTotal, paymentValue) {
    var total = withSurcharge(baseTotal, paymentValue);
    if (paymentValue === 'cash_mxn') {
      return mxn(total * MXN_REFERENCE_RATE) + ' (' + usd(total) + ')';
    }
    return usd(total);
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

  function openCart() {
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
  }

  function renderCartDrawer() {
    var cart = getCart();
    var itemsEl = document.getElementById('mc-cart-items');
    var checkoutEl = document.getElementById('mc-cart-checkout');
    if (!itemsEl) return;

    if (cart.length === 0) {
      itemsEl.innerHTML = '<p class="mc-cart-empty">Todavía no agregaste ningún tour. Elegí uno y tocá "Agregar al carrito" para armar tu reserva.</p>';
      checkoutEl.innerHTML = '';
      return;
    }

    var total = 0;
    var hasQuote = false;
    itemsEl.innerHTML = cart.map(function (item, i) {
      if (typeof item.total === 'number') total += item.total;
      else hasQuote = true;
      return '<div class="mc-cart-item">' +
        (item.photo ? '<img src="' + item.photo + '" alt="">' : '<div class="mc-cart-item-noimg">🌴</div>') +
        '<div class="mc-cart-item-info">' +
        '<div class="mc-cart-item-name">' + item.name + '</div>' +
        '<div class="mc-cart-item-detail">' + cartItemDateLine(item) + '</div>' +
        '<div class="mc-cart-item-detail">' + cartItemPaxLine(item) + '</div>' +
        '<div class="mc-cart-item-price">' + (typeof item.total === 'number' ? usd(item.total) : 'A cotizar') + '</div>' +
        '</div>' +
        '<button type="button" class="mc-cart-remove" data-idx="' + i + '" aria-label="Quitar">×</button>' +
        '</div>';
    }).join('');

    itemsEl.querySelectorAll('.mc-cart-remove').forEach(function (b) {
      b.addEventListener('click', function () { removeFromCart(parseInt(b.getAttribute('data-idx'), 10)); });
    });

    var name = getStr(LS_NAME);
    var hotel = getStr(LS_HOTEL);
    var room = getStr(LS_ROOM);
    var maps = getStr(LS_MAPS);
    var payment = getStr(LS_PAYMENT);
    var anyTentative = cart.some(function (item) { return item.tentative; });

    checkoutEl.innerHTML =
      '<div class="mc-cart-total-row"><span>Total</span><strong>' + formatTotal(total, payment) + (hasQuote ? ' + ítems a cotizar' : '') + '</strong></div>' +
      (payment === 'card' ? '<p class="mc-cart-persons">Incluye 5% de recargo por pago con tarjeta.</p>' : '') +
      (anyTentative ? '<p class="mc-cart-persons">⚠️ Uno o más tours tienen fecha tentativa — Agustín confirma disponibilidad por WhatsApp.</p>' : '') +
      '<div class="booking-field"><label for="mc-name">Nombre completo</label>' +
      '<input type="text" id="mc-name" placeholder="Nombre y apellido de quien reserva" value="' + name.replace(/"/g, '&quot;') + '"></div>' +
      '<div class="booking-field-row">' +
      '<div class="booking-field"><label for="mc-hotel">Hotel / lugar de hospedaje</label>' +
      '<input type="text" id="mc-hotel" placeholder="Ej: Hotel Grand Sirenis" value="' + hotel.replace(/"/g, '&quot;') + '"></div>' +
      '<div class="booking-field booking-field-narrow"><label for="mc-room">N° de habitación</label>' +
      '<input type="text" id="mc-room" placeholder="Ej: 204" value="' + room.replace(/"/g, '&quot;') + '"></div>' +
      '</div>' +
      '<div class="booking-field">' +
      '<button type="button" class="btn-secondary mc-loc-btn" id="mc-share-location">📍 Compartir mi ubicación</button>' +
      '<div id="mc-loc-status" class="mc-loc-status">' + (maps ? '✓ Ubicación agregada' : '') + '</div>' +
      '</div>' +
      '<div class="booking-field"><label for="mc-payment">Método de pago</label>' +
      paymentSelectHtml('mc-payment', payment) + '</div>' +
      '<p class="payment-note">Precios en USD (1 USD = $' + MXN_REFERENCE_RATE.toFixed(2) + ' MXN, conversión automática si pagás en pesos mexicanos). Transferencia en pesos argentinos o colombianos: cotización del día, datos de pago por WhatsApp.</p>' +
      '<button type="button" class="btn-primary" id="mc-checkout-cta">Reservar todo por WhatsApp</button>' +
      '<p class="contact-form-status" id="mc-checkout-status"></p>' +
      '<p class="booking-fineprint">Esto no confirma la reserva ni cobra nada — Agustín confirma disponibilidad y coordina el pago directo por WhatsApp.</p>' +
      '<button type="button" class="mc-clear-cart" id="mc-clear-cart">Vaciar carrito</button>';

    document.getElementById('mc-name').addEventListener('input', function (e) { setStr(LS_NAME, e.target.value); e.target.classList.toggle('field-invalid', !e.target.value.trim()); });
    document.getElementById('mc-hotel').addEventListener('input', function (e) { setStr(LS_HOTEL, e.target.value); e.target.classList.toggle('field-invalid', !e.target.value.trim()); });
    document.getElementById('mc-room').addEventListener('input', function (e) { setStr(LS_ROOM, e.target.value); e.target.classList.toggle('field-invalid', !e.target.value.trim()); });
    document.getElementById('mc-payment').addEventListener('change', function (e) { setStr(LS_PAYMENT, e.target.value); renderCartDrawer(); });
    document.getElementById('mc-share-location').addEventListener('click', shareLocation);
    document.getElementById('mc-clear-cart').addEventListener('click', function () {
      if (confirm('¿Vaciar todo el carrito?')) { setCart([]); updateCartBadge(); renderCartDrawer(); }
    });
    document.getElementById('mc-checkout-cta').addEventListener('click', sendCartToWhatsApp);
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

  function sendCartToWhatsApp() {
    var cart = getCart();
    if (cart.length === 0) return;
    var name = getStr(LS_NAME);
    var hotel = getStr(LS_HOTEL);
    var room = getStr(LS_ROOM);
    var maps = getStr(LS_MAPS);
    var payment = getStr(LS_PAYMENT);

    // Re-check every item's date against ITS OWN schedule right before
    // sending — a date that was valid when added could, in principle,
    // no longer be (cart loaded from an old localStorage snapshot, etc).
    // Visually blocking bad days in the calendar isn't enough on its own.
    var invalidTour = cart.filter(function (item) { return !isDateAllowed(item.date, item.schedule); })[0];

    var missing = [];
    if (!name.trim()) missing.push('el nombre completo');
    if (!hotel.trim()) missing.push('el hotel');
    if (!room.trim()) missing.push('el número de habitación');
    if (!payment) missing.push('el método de pago');
    if (invalidTour || missing.length) {
      var status = document.getElementById('mc-checkout-status');
      if (status) {
        status.textContent = invalidTour
          ? 'La fecha de "' + invalidTour.name + '" ya no es válida — abrí ese tour y elegí otra.'
          : 'Completá ' + missing.join(', ') + ' antes de reservar.';
        status.className = 'contact-form-status error';
      }
      ['mc-name', 'mc-hotel', 'mc-room', 'mc-payment'].forEach(function (id) {
        var f = document.getElementById(id);
        if (!f) return;
        var isMissing = (id === 'mc-name' && !name.trim()) || (id === 'mc-hotel' && !hotel.trim()) || (id === 'mc-room' && !room.trim()) || (id === 'mc-payment' && !payment);
        f.classList.toggle('field-invalid', isMissing);
      });
      return;
    }

    // Each tour keeps its OWN date and its OWN passenger breakdown — never
    // summed or shared across tours, so the same travel party doing two
    // excursions isn't miscounted as twice the people.
    var lines = ['¡Hola! Quiero reservar estos tours:', '', 'Reserva a nombre de: ' + name, ''];
    var total = 0;
    var anyTentative = false;
    cart.forEach(function (item, i) {
      lines.push((i + 1) + '. ' + item.name);
      lines.push('   ' + cartItemDateLine(item));
      lines.push('   ' + cartItemPaxLine(item));
      lines.push('   ' + (typeof item.total === 'number' ? usd(item.total) : 'A cotizar'));
      if (typeof item.total === 'number') total += item.total;
      if (item.tentative) anyTentative = true;
      lines.push('');
    });
    lines.push('Total: ' + formatTotal(total, payment) + (payment === 'card' ? ' (incluye 5% de recargo por tarjeta)' : ''));
    lines.push('Método de pago: ' + paymentLabel(payment));
    lines.push('Hotel: ' + hotel + ' · Habitación: ' + room);
    if (maps) lines.push('Ubicación: ' + maps);
    lines.push('');
    lines.push('⚠️ Esto no es una reserva confirmada ni un cobro — Agustín confirma disponibilidad' + (anyTentative ? ' (hay fechas tentativas a coordinar)' : '') + ' y coordina el pago directo por WhatsApp.');
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

    var state = { date: '', adults: 1, children: 0, infants: 0, persons: 1, tierIndex: 0 };
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

    function counterRow(id, label, sub) {
      return '<div class="counter-row">' +
        '<div class="counter-label">' + label + (sub ? '<small>' + sub + '</small>' : '') + '</div>' +
        '<div class="counter-controls">' +
        '<button type="button" class="counter-btn" data-dec="' + id + '" aria-label="Restar">−</button>' +
        '<span class="counter-value" id="val-' + id + '">1</span>' +
        '<button type="button" class="counter-btn" data-inc="' + id + '" aria-label="Sumar">+</button>' +
        '</div></div>';
    }

    var html = '<h3>' + (data.type === 'quote' ? 'Pedí tu cotización' : 'Reservá este tour') + '</h3>';

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

    if (data.type === 'tiers' || data.type === 'duration_group') {
      html += '<div class="booking-field"><label>' + (data.type === 'duration_group' ? 'Duración' : 'Opción') + '</label><div class="tier-options" id="bw-tiers">';
      data.tiers.forEach(function (t, i) {
        html += '<label class="tier-option' + (i === 0 ? ' selected' : '') + '" data-tier="' + i + '">' +
          '<span><input type="radio" name="bw-tier" value="' + i + '"' + (i === 0 ? ' checked' : '') + '> ' + t.label + '</span>' +
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
      html += '<div class="booking-total-row"><span class="label">Total</span><span class="total" id="bw-total">' + usd(calcTotal()) + '</span></div>';
    }

    html += '<div class="booking-field"><label for="bw-name">Nombre completo</label>' +
      '<input type="text" id="bw-name" placeholder="Nombre y apellido de quien reserva" value="' + getStr(LS_NAME).replace(/"/g, '&quot;') + '"></div>';
    html += '<div class="booking-field-row">' +
      '<div class="booking-field"><label for="bw-hotel">Hotel / lugar de hospedaje</label>' +
      '<input type="text" id="bw-hotel" placeholder="Ej: Hotel Grand Sirenis" value="' + getStr(LS_HOTEL).replace(/"/g, '&quot;') + '"></div>' +
      '<div class="booking-field booking-field-narrow"><label for="bw-room">N° de habitación</label>' +
      '<input type="text" id="bw-room" placeholder="Ej: 204" value="' + getStr(LS_ROOM).replace(/"/g, '&quot;') + '"></div>' +
      '</div>';
    html += '<div class="booking-field">' +
      '<button type="button" class="btn-secondary mc-loc-btn" id="bw-share-location">📍 Compartir mi ubicación</button>' +
      '<div id="bw-loc-status" class="mc-loc-status">' + (getStr(LS_MAPS) ? '✓ Ubicación agregada' : '') + '</div>' +
      '</div>';
    html += '<div class="booking-field"><label for="bw-payment">Método de pago</label>' +
      paymentSelectHtml('bw-payment', getStr(LS_PAYMENT)) + '</div>';
    html += '<p class="payment-note">Precios en USD (1 USD = $' + MXN_REFERENCE_RATE.toFixed(2) + ' MXN, conversión automática si pagás en pesos mexicanos). Transferencia en pesos argentinos o colombianos: cotización del día, datos de pago por WhatsApp.</p>';

    html += '<button type="button" class="btn-primary" id="bw-cta">🛒 Agregar al carrito</button>';
    html += '<p class="contact-form-status" id="bw-checkout-status"></p>';
    html += '<div id="bw-added" class="bw-added" hidden>' +
      '<p>✓ Agregado al carrito</p>' +
      '<button type="button" class="btn-primary" id="bw-goto-cart">Ver carrito y reservar →</button>' +
      '<button type="button" class="btn-secondary" id="bw-keep-browsing">Seguir viendo tours</button>' +
      '</div>';
    html += '<p class="booking-fineprint">Se coordina y confirma directo por WhatsApp con Agustín.</p>';

    el.innerHTML = html;
    updateTotal(); // re-sync in case a payment method (card +5%) was already remembered from a previous visit

    var datepickerEl = document.getElementById('bw-datepicker');
    initDatePicker(datepickerEl, {
      schedule: data.schedule,
      tentative: tentative,
      onSelect: function (iso) {
        state.date = iso;
        datepickerEl.classList.remove('field-invalid');
      }
    });

    document.getElementById('bw-name').addEventListener('input', function (e) { setStr(LS_NAME, e.target.value); e.target.classList.toggle('field-invalid', !e.target.value.trim()); });
    document.getElementById('bw-hotel').addEventListener('input', function (e) { setStr(LS_HOTEL, e.target.value); e.target.classList.toggle('field-invalid', !e.target.value.trim()); });
    document.getElementById('bw-room').addEventListener('input', function (e) { setStr(LS_ROOM, e.target.value); e.target.classList.toggle('field-invalid', !e.target.value.trim()); });
    document.getElementById('bw-payment').addEventListener('change', function (e) { setStr(LS_PAYMENT, e.target.value); e.target.classList.toggle('field-invalid', !e.target.value); updateTotal(); });
    document.getElementById('bw-share-location').addEventListener('click', function () {
      var status = document.getElementById('bw-loc-status');
      if (!navigator.geolocation) { status.textContent = 'Tu navegador no permite compartir ubicación.'; return; }
      status.textContent = 'Buscando tu ubicación…';
      navigator.geolocation.getCurrentPosition(function (pos) {
        setStr(LS_MAPS, 'https://www.google.com/maps?q=' + pos.coords.latitude + ',' + pos.coords.longitude);
        status.textContent = '✓ Ubicación agregada';
      }, function () {
        status.textContent = 'No pudimos obtener tu ubicación. No hay problema, con el hotel alcanza.';
      }, { timeout: 10000 });
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

    function updateTotal() {
      var t = document.getElementById('bw-total');
      if (!t) return;
      var payment = getStr(LS_PAYMENT);
      t.textContent = formatTotal(calcTotal(), payment) + (payment === 'card' ? ' (+5% tarjeta)' : '');
    }

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

    document.getElementById('bw-cta').addEventListener('click', function () {
      var name = getStr(LS_NAME);
      var hotel = getStr(LS_HOTEL);
      var room = getStr(LS_ROOM);
      var payment = getStr(LS_PAYMENT);
      // Re-check the date against the schedule here too — greying out
      // invalid days in the calendar isn't enough on its own (state could
      // in principle hold a stale/invalid value some other way).
      var dateOk = isDateAllowed(state.date, data.schedule);
      var missing = [];
      if (!dateOk) missing.push('una fecha válida para este tour');
      if (!name.trim()) missing.push('el nombre completo');
      if (!hotel.trim()) missing.push('el hotel');
      if (!room.trim()) missing.push('el número de habitación');
      if (!payment) missing.push('el método de pago');
      if (missing.length) {
        var status = document.getElementById('bw-checkout-status');
        if (status) {
          status.textContent = 'Completá ' + missing.join(', ') + ' antes de agregar al carrito.';
          status.className = 'contact-form-status error';
        }
        datepickerEl.classList.toggle('field-invalid', !dateOk);
        ['bw-name', 'bw-hotel', 'bw-room', 'bw-payment'].forEach(function (id) {
          var f = document.getElementById(id);
          if (!f) return;
          var isMissing = (id === 'bw-name' && !name.trim()) || (id === 'bw-hotel' && !hotel.trim()) || (id === 'bw-room' && !room.trim()) || (id === 'bw-payment' && !payment);
          f.classList.toggle('field-invalid', isMissing);
        });
        return;
      }
      var cart = getCart();
      var fields = cartFields();
      cart.push({
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
        url: pageUrl,
        photo: photoSrc,
      });
      setCart(cart);
      updateCartBadge();
      document.getElementById('bw-cta').hidden = true;
      document.getElementById('bw-added').hidden = false;
    });
    document.getElementById('bw-goto-cart').addEventListener('click', function () { window.mcOpenCart(); });
    document.getElementById('bw-keep-browsing').addEventListener('click', function () {
      document.getElementById('bw-added').hidden = true;
      document.getElementById('bw-cta').hidden = false;
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
  });

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
})();
