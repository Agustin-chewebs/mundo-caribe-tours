(function () {
  'use strict';

  var WA_NUMBER = '529841191147';

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

  // ---------- booking widget ----------
  function initBooking() {
    var el = document.getElementById('booking-widget');
    if (!el) return;
    var dataEl = document.getElementById('tour-pricing');
    if (!dataEl) return;
    var data = JSON.parse(dataEl.textContent);
    var pageUrl = window.location.href;

    var state = { date: '', adults: 1, children: 0, persons: 1, tierIndex: 0 };

    function usd(n) { return '$' + n.toLocaleString('en-US'); }

    function calcTotal() {
      if (data.type === 'adult_child') {
        return state.adults * data.adult + state.children * data.child;
      }
      if (data.type === 'per_person') {
        return state.persons * data.price;
      }
      if (data.type === 'tiers') {
        return state.persons * data.tiers[state.tierIndex].price;
      }
      if (data.type === 'duration_group') {
        return data.tiers[state.tierIndex].price;
      }
      return null;
    }

    function counterRow(id, label, sub, min, max) {
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
      html += '<div class="booking-field">' + counterRow('adults', 'Adultos', null, 1, 30) + counterRow('children', 'Niños', null, 0, 30) + '</div>';
    } else if (data.type !== 'duration_group') {
      html += '<div class="booking-field">' + counterRow('persons', 'Personas', null, 1, 30) + '</div>';
    } else {
      html += '<div class="booking-field">' + counterRow('persons', 'Pasajeros', 'Hasta ' + (data.maxGroup || 7) + ' por embarcación', 1, data.maxGroup || 7) + '</div>';
    }

    if (data.type !== 'quote' && data.type !== 'duration_group') {
      html += '<div class="booking-total-row"><span class="label">Total estimado</span><span class="total" id="bw-total">' + usd(calcTotal()) + '</span></div>';
    }

    html += '<button type="button" class="btn-primary" id="bw-cta">' + (data.type === 'quote' ? 'Pedir cotización por WhatsApp' : 'Reservar por WhatsApp') + '</button>';
    html += '<p class="booking-fineprint">Se coordina y confirma directo por WhatsApp con Agustín.</p>';

    el.innerHTML = html;

    // wire up date
    document.getElementById('bw-date').addEventListener('change', function (e) {
      state.date = e.target.value;
    });

    // wire up counters
    function bindCounter(id, key, min, max) {
      var valEl = document.getElementById('val-' + id);
      if (!valEl) return;
      valEl.textContent = state[key];
      el.querySelectorAll('[data-dec="' + id + '"]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          if (state[key] > min) { state[key]--; valEl.textContent = state[key]; updateTotal(); }
        });
      });
      el.querySelectorAll('[data-inc="' + id + '"]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          if (state[key] < max) { state[key]++; valEl.textContent = state[key]; updateTotal(); }
        });
      });
    }
    if (data.type === 'adult_child') {
      bindCounter('adults', 'adults', 1, 30);
      bindCounter('children', 'children', 0, 30);
    } else if (data.type !== 'duration_group') {
      bindCounter('persons', 'persons', 1, 30);
    } else {
      bindCounter('persons', 'persons', 1, data.maxGroup || 7);
    }

    // wire up tiers
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
      var totalEl = document.getElementById('bw-total');
      if (totalEl) totalEl.textContent = usd(calcTotal());
    }

    document.getElementById('bw-cta').addEventListener('click', function () {
      var lines = [];
      lines.push('¡Hola! Quiero ' + (data.type === 'quote' ? 'pedir una cotización' : 'reservar') + ': ' + data.name);
      lines.push('Fecha: ' + fmtDate(state.date));
      if (data.type === 'adult_child') {
        lines.push('Adultos: ' + state.adults + ' · Niños: ' + state.children);
        lines.push('Total estimado: ' + usd(calcTotal()) + ' USD');
      } else if (data.type === 'tiers') {
        lines.push('Opción: ' + data.tiers[state.tierIndex].label);
        lines.push('Personas: ' + state.persons);
        lines.push('Total estimado: ' + usd(calcTotal()) + ' USD');
      } else if (data.type === 'duration_group') {
        lines.push('Duración: ' + data.tiers[state.tierIndex].label);
        lines.push('Pasajeros: ' + state.persons);
        lines.push('Total estimado: ' + usd(calcTotal()) + ' USD (para el grupo)');
      } else if (data.type === 'per_person') {
        lines.push('Personas: ' + state.persons);
        lines.push('Total estimado: ' + usd(calcTotal()) + ' USD');
      } else {
        lines.push('Personas: ' + state.persons);
      }
      lines.push(pageUrl);
      window.open(waLink(lines.join('\n')), '_blank', 'noopener');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initReveal();
    initBooking();
  });
})();
