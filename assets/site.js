(function () {
  'use strict';

  var WA_NUMBER = '529841191147';

  var LS_CART = 'mc_cart';
  var LS_HOTEL = 'mc_hotel';
  var LS_ROOM = 'mc_room';
  var LS_MAPS = 'mc_maps';
  var LS_CART_VERSION = 'mc_cart_v';
  var CART_VERSION = 2; // bump this whenever the shape of a cart item changes, to auto-clear stale carts

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
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    reveals.forEach(function (el) { obs.observe(el); });
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

  function todayISO() {
    var d = new Date();
    var mm = String(d.getMonth() + 1).padStart(2, '0');
    var dd = String(d.getDate()).padStart(2, '0');
    return d.getFullYear() + '-' + mm + '-' + dd;
  }

  function usd(n) { return '$' + n.toLocaleString('en-US'); }

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
        '<div class="mc-cart-item-detail">' + item.detail + '</div>' +
        '<div class="mc-cart-item-price">' + (typeof item.total === 'number' ? usd(item.total) : 'A cotizar') + '</div>' +
        '</div>' +
        '<button type="button" class="mc-cart-remove" data-idx="' + i + '" aria-label="Quitar">×</button>' +
        '</div>';
    }).join('');

    itemsEl.querySelectorAll('.mc-cart-remove').forEach(function (b) {
      b.addEventListener('click', function () { removeFromCart(parseInt(b.getAttribute('data-idx'), 10)); });
    });

    var hotel = getStr(LS_HOTEL);
    var room = getStr(LS_ROOM);
    var maps = getStr(LS_MAPS);
    // "Personas" = tamaño del grupo, no la suma entre tours (las mismas personas pueden hacer varios tours)
    var totalPersons = cart.reduce(function (max, item) { return Math.max(max, item.headcount || 0); }, 0);

    checkoutEl.innerHTML =
      '<div class="mc-cart-total-row"><span>Total</span><strong>' + usd(total) + (hasQuote ? ' + ítems a cotizar' : '') + '</strong></div>' +
      '<p class="mc-cart-persons">Personas: ' + totalPersons + '</p>' +
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
      '<button type="button" class="btn-primary" id="mc-checkout-cta">Reservar todo por WhatsApp</button>' +
      '<button type="button" class="mc-clear-cart" id="mc-clear-cart">Vaciar carrito</button>';

    document.getElementById('mc-hotel').addEventListener('input', function (e) { setStr(LS_HOTEL, e.target.value); });
    document.getElementById('mc-room').addEventListener('input', function (e) { setStr(LS_ROOM, e.target.value); });
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
    var hotel = getStr(LS_HOTEL);
    var room = getStr(LS_ROOM);
    var maps = getStr(LS_MAPS);
    var lines = ['¡Hola! Quiero reservar estos tours:', ''];
    var total = 0;
    var totalPersons = 0;
    cart.forEach(function (item, i) {
      lines.push((i + 1) + '. ' + item.name);
      lines.push('   ' + item.detail);
      lines.push('   ' + (typeof item.total === 'number' ? usd(item.total) + ' USD' : 'A cotizar'));
      if (typeof item.total === 'number') total += item.total;
      // "Personas" = tamaño del grupo, no la suma entre tours (las mismas personas pueden hacer varios tours)
      totalPersons = Math.max(totalPersons, item.headcount || 0);
      lines.push('');
    });
    lines.push('Total: ' + usd(total) + ' USD');
    lines.push('Personas: ' + totalPersons);
    if (hotel) lines.push('Hotel: ' + hotel + (room ? ' · Habitación: ' + room : ''));
    if (maps) lines.push('Ubicación: ' + maps);
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

    html += '<div class="booking-field"><label for="bw-date">Fecha preferida</label>' +
      '<input type="date" id="bw-date" min="' + todayISO() + '"></div>';

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

    html += '<button type="button" class="btn-primary" id="bw-cta">🛒 Agregar al carrito</button>';
    html += '<div id="bw-added" class="bw-added" hidden>' +
      '<p>✓ Agregado al carrito</p>' +
      '<button type="button" class="btn-primary" id="bw-goto-cart">Ver carrito y reservar →</button>' +
      '<button type="button" class="btn-secondary" id="bw-keep-browsing">Seguir viendo tours</button>' +
      '</div>';
    html += '<p class="booking-fineprint">Se coordina y confirma directo por WhatsApp con Agustín.</p>';

    el.innerHTML = html;

    document.getElementById('bw-date').addEventListener('change', function (e) { state.date = e.target.value; });
    document.getElementById('bw-hotel').addEventListener('input', function (e) { setStr(LS_HOTEL, e.target.value); });
    document.getElementById('bw-room').addEventListener('input', function (e) { setStr(LS_ROOM, e.target.value); });
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
      if (t) t.textContent = usd(calcTotal());
    }

    function infantsSuffix() {
      return (hasInfants && state.infants > 0) ? ', ' + state.infants + ' infante' + (state.infants > 1 ? 's' : '') : '';
    }

    function detailText() {
      if (data.type === 'adult_child') {
        var who = state.adults + (state.adults === 1 ? ' adulto' : ' adultos');
        if (state.children > 0) who += ', ' + state.children + (state.children === 1 ? ' niño' : ' niños');
        return fmtDate(state.date) + ' · ' + who + infantsSuffix();
      }
      if (data.type === 'tiers') return fmtDate(state.date) + ' · ' + data.tiers[state.tierIndex].label + ' · ' + state.persons + ' personas' + infantsSuffix();
      if (data.type === 'duration_group') return fmtDate(state.date) + ' · ' + data.tiers[state.tierIndex].label + ' · ' + state.persons + ' pasajeros';
      if (data.type === 'per_person') return fmtDate(state.date) + ' · ' + state.persons + ' personas' + infantsSuffix();
      return fmtDate(state.date) + ' · ' + state.persons + ' personas (cotización)';
    }

    function headcount() {
      if (data.type === 'adult_child') return state.adults + state.children;
      if (data.type === 'quote') return state.persons;
      return state.persons;
    }

    document.getElementById('bw-cta').addEventListener('click', function () {
      var cart = getCart();
      cart.push({
        name: data.name,
        detail: detailText(),
        total: data.type === 'quote' ? null : calcTotal(),
        headcount: headcount(),
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
    initCarousels();
    initCategoryDropdown();
  });

  // ===========================================================================
  // HORIZONTAL DRAG CAROUSEL
  // ===========================================================================

  function initCarousels() {
    var wraps = document.querySelectorAll('.tour-carousel-wrap');
    wraps.forEach(function (wrap) {
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

      // ---- mouse (desktop) ----
      wrap.addEventListener('mousedown', function (e) {
        isDown = true; dragged = false;
        startX = e.pageX; startScroll = wrap.scrollLeft;
        lastX = e.pageX; lastT = Date.now(); velocity = 0;
        wrap.classList.add('dragging');
        cancelMomentum();
      });
      window.addEventListener('mousemove', function (e) {
        if (!isDown) return;
        e.preventDefault();
        var dx = e.pageX - startX;
        if (Math.abs(dx) > 5) dragged = true;
        wrap.scrollLeft = startScroll - dx;
        var now = Date.now(), dt = now - lastT;
        if (dt > 0) { velocity = (e.pageX - lastX) / dt; lastT = now; lastX = e.pageX; }
      });
      window.addEventListener('mouseup', endDrag);
      wrap.addEventListener('mouseleave', endDrag);

      // ---- touch (mobile): native scroll already works, just track drag distance ----
      // to tell a swipe apart from a tap so we don't accidentally open a tour card.
      var touchStartX = 0;
      wrap.addEventListener('touchstart', function (e) {
        touchStartX = e.touches[0].pageX; dragged = false;
      }, { passive: true });
      wrap.addEventListener('touchmove', function (e) {
        if (Math.abs(e.touches[0].pageX - touchStartX) > 8) dragged = true;
      }, { passive: true });

      // swallow the click that follows a real drag/swipe so cards don't get "activated" by accident
      wrap.addEventListener('click', function (e) {
        if (dragged) { e.preventDefault(); e.stopPropagation(); }
        dragged = false;
      }, true);
    });
  }

  // ===========================================================================
  // CATEGORY DROPDOWN (scroll to section if present on this page, else navigate)
  // ===========================================================================

  function initCategoryDropdown() {
    document.querySelectorAll('.cat-dropdown').forEach(function (select) {
      select.addEventListener('change', function () {
        var opt = select.options[select.selectedIndex];
        var targetId = opt.getAttribute('data-target');
        var url = opt.getAttribute('data-url');
        var targetEl = targetId ? document.getElementById(targetId) : null;
        if (targetEl) {
          targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else if (url) {
          window.location.href = url;
        }
        select.selectedIndex = 0;
      });
    });
  }
})();
