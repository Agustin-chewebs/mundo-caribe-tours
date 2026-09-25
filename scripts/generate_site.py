#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static site generator for Mundo Caribe Tours — bilingual (ES/EN).
Reads the DATA below (single source of truth) and emits, for EACH language
in LANGS, a full parallel tree:
  index.html                        (es, at the site root)
  categoria/<slug>/index.html
  tour/<slug>/index.html
  en/index.html                     (en, mirrored under /en/)
  en/categoria/<slug>/index.html
  en/tour/<slug>/index.html
  ...
Shared assets: assets/site.css, assets/site.js, assets/*.png/webp/jpg (never
duplicated per language — same URL for both).

Translation architecture (see docs/PROJECT_STATUS.md for the full writeup):
  - Business data (pricing, schedule, slugs, zone rules) lives ONCE, in
    Spanish-keyed structures (TOURS, CATEGORIES, ...) — never duplicated.
  - Human-language fields on that data (name, desc, long_desc, ...) are
    overridden per-locale by a parallel *_EN dict keyed the same way
    (by slug/key), read through the tour_text()/cat_text()/... helpers.
  - All static UI chrome (buttons, labels, nav, validation messages, the
    WhatsApp message templates, etc.) lives in the single UI dict below,
    keyed UI[lang][key] — both the Python-rendered HTML and the JS runtime
    (via an embedded <script id="mc-i18n"> JSON blob) read from this same
    dict, so no string is ever translated/typed twice.
  - validate_translations() runs at the top of main() and raises loudly if
    any Spanish source text is missing its English counterpart.

Run from the project root: python3 scripts/generate_site.py
"""
import os
import json
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = 'https://mundocaribetours.chewebs.com'
WA_NUMBER = '529841191147'
LANGS = ('es', 'en')

GENERAL_AGE_NOTE = 'Edades: infantes de 0 a 2 años (sin cargo), niños de 3 a 9 años, adultos desde 10 años en adelante.'
SNORKEL_AGE_NOTE = 'Para hacer snorkel: edad mínima 8 años, edad máxima 65 años.'
GENERAL_AGE_NOTE_EN = 'Ages: infants 0–2 (no charge), children 3–9, adults 10 and up.'
SNORKEL_AGE_NOTE_EN = 'To snorkel: minimum age 8, maximum age 65.'

INSTAGRAM_URL = 'https://www.instagram.com/mundocaribetours'
GOOGLE_MAPS_URL = 'https://share.google/n1J6T9x87tUbbPaJm'
# Direct link for the "Reseñas reales" section on the home (Ver todas las
# reseñas en Google →) — the exact URL supplied for that section, kept
# separate from GOOGLE_MAPS_URL (used elsewhere for the general listing).
GOOGLE_REVIEWS_URL = 'https://maps.app.goo.gl/qujMgBHTCgYXxWCr9'
FACEBOOK_URL = 'https://www.facebook.com/people/Mundo-Caribe-Tours/61569544733150/'

# ---------------------------------------------------------------------------
# DATA (Spanish — single source of truth for business content/structure)
# ---------------------------------------------------------------------------

CATEGORIES = [
    {
        'slug': 'cultura-maya-ruinas', 'key': 'ruinas', 'title': 'Cultura Maya & Ruinas',
        'intro': 'Viaja en el tiempo hasta las grandes ciudades mayas. Chichén Itzá, Tulum y Cobá, con cenotes y guías certificados incluidos en cada recorrido.',
        'card_desc': 'Chichén Itzá, Tulum y Cobá — historia frente al mar y en la selva.',
    },
    {
        'slug': 'islas-catamaranes', 'key': 'islas', 'title': 'Islas & Catamaranes',
        'intro': 'Aguas turquesas, catamaranes y snorkel en los mejores arrecifes del Caribe mexicano: Isla Mujeres, Isla Contoy, Holbox, Bacalar y Cozumel.',
        'card_desc': 'Isla Mujeres, Isla Contoy, Holbox, Bacalar y Cozumel.',
    },
    {
        'slug': 'aventura-acuatica', 'key': 'aventura', 'title': 'Aventura Acuática',
        'intro': 'Cenotes, cuatrimotos y snorkel con tortugas: la Riviera Maya más aventurera, para quienes buscan adrenalina y naturaleza en el mismo día.',
        'card_desc': 'Cenotes, tortugas de Akumal y aventura en ATV por la selva.',
    },
    {
        'slug': 'pesca-deportiva', 'key': 'pesca', 'title': 'Pesca Deportiva',
        'intro': 'Salidas en yate privado desde Cancún, con capitán y tripulación experta, para pasar el día pescando en altamar.',
        'card_desc': 'Salidas en yate privado desde Cancún, por hora o compartidas.',
    },
    {
        'slug': 'xperiencias-xcaret', 'key': 'xcaret', 'title': 'Xperiencias by Xcaret',
        'intro': 'Los parques del Grupo Xcaret: naturaleza, aventura y cultura mexicana. Precio y disponibilidad se cotizan al momento según fecha.',
        'card_desc': 'Xcaret, Xplor, Xel-Há, Xenses, Xoximilco y Xenotes.',
    },
    {
        'slug': 'transportes', 'key': 'transportes', 'title': 'Transportes',
        'intro': 'Traslados privados puerta a puerta en la Riviera Maya, de 1 a la cantidad de pasajeros que necesites.',
        'card_desc': 'Traslados privados aeropuerto-hotel, Chichén Itzá, Valladolid, cenotes y centros comerciales.',
    },
    {
        'slug': 'vuelos-hoteles', 'key': 'vuelos', 'title': 'Vuelos y Hoteles',
        'intro': 'Armamos tu viaje completo: cotizamos vuelos y estadías en hoteles de la Riviera Maya a medida.',
        'card_desc': 'Cotizamos tus vuelos y tu estadía para armar el viaje completo.',
    },
]
CAT_BY_KEY = {c['key']: c for c in CATEGORIES}

# Tours with their own page (rich content + booking widget)
#
# 'schedule': structured source of truth for the booking calendar (Phase 3,
# 2026-09-10). Transcribed BY HAND from each tour's real 'availability'
# text below and from Agustín's explicit classification — never parsed
# from that text at runtime, never guessed. One of four types:
#   - {'type': 'weekly', 'days': [...]} — fixed days of the week, using
#     JS's Date.getDay() convention: 0=domingo, 1=lunes, 2=martes,
#     3=miércoles, 4=jueves, 5=viernes, 6=sábado. Only these days are
#     selectable; the date is a real confirmed slot.
#   - {'type': 'daily'} — runs every day; any future date is a real
#     confirmed slot.
#   - {'type': 'seasonal', 'months': [...]} — only runs within these
#     months (1-12); any day inside that window is selectable, but with
#     no known weekly cadence it's shown as TENTATIVE (Agustín confirms).
#   - {'type': 'on_request'} — no real fixed schedule at all (its
#     'availability' text just says "Consulta disponibilidad", or for
#     pesca-yate-cancun that field actually holds a pickup point, not
#     days): any future date is selectable but always TENTATIVE.
# All dates (calendar + these schedule windows) are additionally capped at
# a rolling one-calendar-month-ahead maximum — see cancunMaxDateISO() in
# assets/site.js — never more than a month out regardless of schedule type.
TOURS = [
    {
        'slug': 'chichen-itza', 'category': 'ruinas', 'photo': 'chichen-itza.jpg',
        'name': 'Chichén Itzá – Historia, Naturaleza y Cultura',
        'desc': 'Guía certificado, cenote Oxman y tiempo libre en Valladolid, Pueblo Mágico.',
        'long_desc': "Descubre la grandeza de Chichén Itzá con un guía certificado, refréscate en el impresionante cenote Oxman y explora las calles coloridas de Valladolid, un Pueblo Mágico lleno de historia y tradición.",
        'duration': '12 horas aprox.', 'availability': 'Diario',
        'schedule': {'type': 'daily'},
        'includes': ['Transportación redonda', 'Entrada a Chichén Itzá + tiempo libre', 'Recorrido con guía certificado',
                     "Ticket de entrada al cenote Oxman + chaleco salvavidas", 'Comida buffet con platillos típicos y 1 bebida no alcohólica',
                     'Tiempo libre en Valladolid'],
        'tax': None, 'note': None,
        'pricing': {'type': 'adult_child', 'adult': 97, 'child': 78},
    },
    {
        'slug': 'chichen-itza-plus', 'category': 'ruinas', 'photo': 'chichen-itza-plus.jpg',
        'name': 'Chichén Itzá Plus – Historia, Naturaleza y Cultura en un Solo Día',
        'desc': 'Una de las 7 Maravillas del Mundo + 2 cenotes y comida buffet en hacienda.',
        'long_desc': "Descubre una de las 7 Maravillas del Mundo acompañado por un guía experto. Refréscate en los impresionantes cenotes Suytún e Ik'kil y disfruta de una comida buffet en una hermosa hacienda. Un día lleno de historia, cultura y naturaleza.",
        'duration': '12 horas aprox.', 'availability': 'Diario',
        'schedule': {'type': 'daily'},
        'includes': ['Transportación redonda', 'Visita guiada en Chichén Itzá', 'Tiempo libre en la zona arqueológica',
                     'Ticket de entrada a cenote Suytún', "Ticket de entrada a cenote Ik'kil",
                     'Comida buffet (incluye 1 bebida no alcohólica)', 'Tiempo libre en Valladolid'],
        'tax': None, 'note': None,
        'pricing': {'type': 'adult_child', 'adult': 109, 'child': 90},
    },
    {
        'slug': 'tulum', 'category': 'ruinas', 'photo': 'tulum.jpg',
        'name': 'Tulum',
        'desc': 'Visita guiada a las ruinas de Tulum, frente al mar. Entrada, guía certificado y tiempo libre para fotos.',
        'long_desc': "Visita guiada a las ruinas de Tulum, uno de los sitios arqueológicos más impactantes de la Riviera. Ideal para amantes de la historia y paisajes únicos.",
        'duration': '2.5 horas aprox.', 'availability': 'Diario',
        'schedule': {'type': 'daily'},
        'includes': ['Entrada al sitio arqueológico', 'Recorrido con guía certificado', 'Tiempo libre para fotos'],
        'tax': 'Impuesto federal (no incluido): $265 MXN, se paga directo en el sitio', 'note': None,
        'pricing': {'type': 'per_person', 'price': 55},
    },
    {
        'slug': 'tulum-casa-tortuga', 'category': 'ruinas', 'photo': 'tulum-casa-tortuga.jpg',
        'name': 'Tulum + Casa Tortuga – Historia y Naturaleza en un Solo Día',
        'desc': 'Ruinas de Tulum con guía certificado + los 4 cenotes de Casa Tortuga.',
        'long_desc': "Explora las imponentes ruinas de Tulum con un guía certificado y sumérgete en los mágicos Cenotes Casa Tortuga, rodeados de naturaleza.",
        'duration': '8 horas aprox.', 'availability': 'Consulta disponibilidad',
        'schedule': {'type': 'on_request'},
        'includes': ['Transportación redonda', 'Entrada y recorrido guiado en Tulum',
                     'Visita a los 4 cenotes de Casa Tortuga (Dorca, Wisho, Tres Zapotes y Campana)',
                     'Tiempo libre para nadar', 'Comida típica mexicana'],
        'tax': 'Impuesto federal (no incluido): $265 MXN, se paga en la Zona Arqueológica de Tulum', 'note': None,
        'pricing': {'type': 'per_person', 'price': 97},
    },
    {
        'slug': 'tulum-tortugas-akumal', 'category': 'ruinas', 'photo': 'tulum-tortugas-akumal.jpg',
        'name': 'Tulum + Tortugas en Akumal – Historia y Naturaleza en el Caribe',
        'desc': 'Zona arqueológica de Tulum + snorkel con tortugas en Akumal.',
        'long_desc': "Descubre la magia de Tulum, una de las zonas arqueológicas más impresionantes, y vive la emoción de nadar con tortugas en Akumal. Una experiencia única que combina cultura e interacción con la vida marina.",
        'duration': '8 horas aprox.', 'availability': 'Martes a domingo',
        'schedule': {'type': 'weekly', 'days': [0, 2, 3, 4, 5, 6]},
        'includes': ['Transportación redonda', 'Entrada y recorrido guiado en Tulum', 'Tiempo libre en la zona arqueológica',
                     'Snorkel con tortugas en Akumal', 'Equipo completo de snorkel y chaleco salvavidas',
                     'Guía especializado durante la actividad', 'Comida (bebidas no incluidas)'],
        'tax': 'Impuesto federal de Tulum (no incluido): $265 MXN, se paga en el sitio', 'note': None,
        'snorkel': True,
        'pricing': {'type': 'per_person', 'price': 121},
    },
    {
        'slug': 'coba-sunset', 'category': 'ruinas', 'photo': 'coba-sunset.jpg',
        'name': 'Cobá Sunset – Historia y Naturaleza en una Mañana Perfecta',
        'desc': 'Cobá sin multitudes, cenote Choo Ha y ritual maya en aldea local.',
        'long_desc': "Descubre Cobá después de las multitudes, explora su impresionante zona arqueológica y refréscate en el cenote Choo Ha. Además, vive un ritual maya auténtico en una aldea local.",
        'duration': '6 horas aprox.', 'availability': 'Lunes, miércoles y sábados',
        'schedule': {'type': 'weekly', 'days': [1, 3, 6]},
        'includes': ['Transportación redonda', 'Entrada y tiempo libre en Cobá', 'Entrada y nado en el cenote Choo Ha',
                     'Comida buffet con platillos típicos', 'Visita a una aldea maya con ritual de purificación'],
        'tax': 'Impuesto de Cobá (no incluido): $330 MXN, se paga directo en el sitio', 'note': None,
        'pricing': {'type': 'per_person', 'price': 60},
    },
    {
        'slug': 'holbox', 'category': 'islas', 'photo': 'holbox.jpg',
        'name': 'Holbox: Aventura en Islas y Naturaleza',
        'desc': 'Ojo de agua de Yalahau, Isla de la Pasión y calles coloridas de Holbox.',
        'long_desc': "Explora Holbox, un paraíso de arenas blancas y aguas cristalinas. Nada en el refrescante ojo de agua de Yalahau, descubre la belleza de la Isla de la Pasión y recorre las coloridas calles de Holbox en bicicleta o a pie.",
        'duration': '10 horas aprox.', 'availability': 'Lunes, miércoles y viernes',
        'schedule': {'type': 'weekly', 'days': [1, 3, 5]},
        'includes': ['Transportación redonda', 'Box lunch', 'Bebidas a bordo', 'Comida a la carta + 1 bebida no alcohólica',
                     'Alquiler de bicicleta (1 hora)', 'Nado en el ojo de agua de Yalahau', 'Visita a la Isla de la Pasión',
                     'Tiempo libre en Holbox'],
        'tax': 'Impuesto (no incluido): $35 MXN, pago directo', 'note': None,
        'pricing': {'type': 'per_person', 'price': 97},
    },
    {
        'slug': 'isla-contoy-mujeres', 'category': 'islas', 'photo': 'isla-contoy-mujeres.jpg',
        'name': 'Isla Contoy + Isla Mujeres – Naturaleza y Encanto',
        'desc': 'Snorkel en Isla Contoy y tiempo libre en Isla Mujeres, con comida regional.',
        'long_desc': "Descubre dos joyas del Caribe en un solo día. Explora la hermosa Isla Contoy, un paraíso virgen ideal para los amantes de la naturaleza. Nada en sus aguas cristalinas y relájate con tiempo libre en Isla Mujeres.",
        'duration': '8 horas aprox.', 'availability': 'Martes, jueves y domingos',
        'schedule': {'type': 'weekly', 'days': [0, 2, 4]},
        'includes': ['Transportación redonda', 'Paseo en bote', 'Snorkel en Isla Contoy (equipo incluido)',
                     'Tiempo libre en Isla Contoy e Isla Mujeres', 'Bebidas a bordo', 'Comida regional (pollo o pescado a la Tikinxic)'],
        'tax': 'Impuesto federal (no incluido): USD 23 ($360 MXN)', 'note': None,
        'snorkel': True,
        'pricing': {'type': 'per_person', 'price': 111},
    },
    {
        'slug': 'isla-mujeres-catamaran', 'category': 'islas', 'photo': 'isla-mujeres-catamaran.jpg',
        'name': 'Isla Mujeres en Catamarán – Mar, Sol y Diversión',
        'desc': 'Catamarán con barra libre, snorkel en arrecife y club de playa con buffet.',
        'long_desc': "Disfruta de un día increíble navegando hacia Isla Mujeres en un catamarán con barra libre, música y las mejores vibras. Haz snorkel en un arrecife, relájate en un club de playa con buffet y explora el encantador centro de la isla.",
        'duration': '8 horas aprox.', 'availability': 'Diario',
        'schedule': {'type': 'daily'},
        'includes': ['Transportación redonda', 'Paseo en catamarán', 'Club de playa con camastros', 'Comida buffet',
                     'Barra libre (a bordo y en el club de playa)', 'Snorkel en arrecife (equipo incluido)',
                     'Spinnaker (según clima)', 'Tiempo libre en Isla Mujeres'],
        'tax': None, 'note': 'El precio incluye el impuesto federal (USD 20); se abona antes de abordar la embarcación',
        'snorkel': True,
        'pricing': {'type': 'per_person', 'price': 75},
    },
    {
        'slug': 'bacalar', 'category': 'islas', 'photo': 'bacalar.jpg',
        'name': 'Bacalar: Aventura en la Laguna de los 7 Colores',
        'desc': 'Cenotes Negro, Cocalitos y Esmeralda, Isla de los Pájaros y Canal de los Piratas.',
        'long_desc': "Explora la espectacular Laguna de Bacalar a bordo de una lancha y maravíllate con sus aguas cristalinas y vibrantes tonos azules. Nada en cenotes subacuáticos, visita la Isla de los Pájaros y navega por el legendario Canal de los Piratas.",
        'duration': '10 horas aprox.', 'availability': 'Martes, jueves y sábados',
        'schedule': {'type': 'weekly', 'days': [2, 4, 6]},
        'includes': ['Transportación redonda', 'Paseo en lancha', 'Visita a Cenote Negro, Cenote Cocalitos y Cenote Esmeralda',
                     'Isla de los Pájaros', 'Canal de los Piratas', 'Comida a la carta (pollo o pescado) + 1 bebida no alcohólica'],
        'tax': None, 'note': 'No permite cancelaciones una vez reservada la fecha',
        'pricing': {'type': 'per_person', 'price': 97},
    },
    {
        'slug': 'cozumel', 'category': 'islas', 'photo': 'cozumel.jpg',
        'name': 'Cozumel - El Cielo y El Cielito',
        'desc': 'Catamarán exclusivo con paradas de snorkel en El Cielo, El Cielito y Chankanaab.',
        'long_desc': "Explorá Cozumel en un catamarán exclusivo. Paradas para snorkel en El Cielo, El Cielito y Chankanaab, más alimentos y bebidas incluidos. Una experiencia VIP sobre el mar turquesa.",
        'duration': '7 horas aprox.', 'availability': 'Diario',
        'schedule': {'type': 'daily'},
        'includes': ['Paseo en catamarán de 5 horas', 'Snorkel en 3 paradas (El Cielo, El Cielito y Chankanaab)',
                     'Alimentos y bebidas a bordo', 'Equipo de snorkel incluido'],
        'tax': 'No incluye ferry a Cozumel: USD 30 viaje redondo aprox.', 'note': None,
        'snorkel': True,
        'pricing': {'type': 'per_person', 'price': 109},
    },
    {
        'slug': 'tiburon-ballena', 'category': 'islas', 'photo': 'tiburon-ballena.jpg',
        'name': 'Tiburón Ballena',
        'desc': 'Nadá junto al pez más grande del mundo. Tour 100% regulado y guías certificados.',
        'long_desc': "Viví la experiencia única de nadar junto al pez más grande del mundo. Tour 100% regulado y seguro, con guías certificados y equipo profesional.",
        'duration': '8 horas aprox.', 'availability': 'Junio a septiembre',
        'schedule': {'type': 'seasonal', 'months': [6, 7, 8, 9]},
        'includes': ['Transportación desde Playa del Carmen', 'Lancha rápida hasta el área de avistamiento',
                     'Equipo completo de snorkel', 'Guía certificado', 'Box lunch y bebidas'],
        'tax': None, 'note': 'No apto para embarazadas',
        'snorkel': True,
        'pricing': {'type': 'per_person', 'price': 163},
    },
    {
        'slug': 'atv-casa-jaguar', 'category': 'aventura', 'photo': 'atv-casa-jaguar.jpg',
        'name': "ATV's Casa Jaguar – Aventura y Cenotes",
        'desc': 'Cuatrimoto por la selva y cenotes Jaguar, Alux y Nohoch.',
        'long_desc': "Siente la adrenalina al recorrer la selva en cuatrimoto y explora los impresionantes cenotes Jaguar, Alux y Nohoch. Un tour perfecto para los amantes de la aventura y la naturaleza.",
        'duration': '4 horas aprox.', 'availability': 'Diario',
        'schedule': {'type': 'daily'},
        'includes': ['Transportación redonda', 'Recorrido en cuatrimoto (sencilla o doble)', 'Nado en el cenote Alux',
                     'Visita a la caverna de Nohoch', 'Exploración del cenote Jaguar', 'Snack para recargar energía'],
        'tax': None, 'note': 'No admite infantes · llevar ropa cómoda, traje de baño y calzado cerrado',
        'pricing': {'type': 'tiers', 'tiers': [
            {'label': 'Individual (1 por cuatrimoto)', 'price': 72},
            {'label': 'Doble (2 por cuatrimoto, c/u)', 'price': 54},
        ]},
    },
    {
        'slug': 'akumal-cenote-nohoch', 'category': 'aventura', 'photo': 'akumal-cenote-nohoch.jpg',
        'name': 'Akumal + Cenote Nohoch – Aventura entre Tortugas y Naturaleza Subterránea',
        'desc': 'Nado con tortugas en Akumal y Cenote Nohoch, con zona de hamacas.',
        'long_desc': "Explora Akumal, una playa ideal para nadar con tortugas marinas en aguas claras y turquesas, y luego disfruta de la belleza del Cenote Nohoch, una caverna mística con aguas cristalinas, zona de descanso con hamacas y un buffet regional delicioso.",
        'duration': '7-8 horas aprox.', 'availability': 'Martes a domingo',
        'schedule': {'type': 'weekly', 'days': [0, 2, 3, 4, 5, 6]},
        'includes': ['Transportación redonda', 'Snorkel guiado con tortugas en Akumal', 'Equipo de snorkel incluido',
                     'Entrada al Cenote Nohoch', 'Acceso a zona de hamacas y descanso', 'Comida buffet regional'],
        'tax': None, 'note': 'Actividad sujeta a condiciones del mar, cupos limitados',
        'snorkel': True,
        'pricing': {'type': 'per_person', 'price': 97},
    },
    {
        'slug': 'akumal-expres', 'category': 'aventura', 'photo': 'akumal-expres.jpg',
        'name': 'Akumal Exprés – Nada con Tortugas y Relájate en la Playa',
        'desc': 'Snorkel guiado con tortugas en su hábitat natural y tiempo libre en la playa.',
        'long_desc': "Vive una experiencia inolvidable nadando con tortugas en su hábitat natural en Akumal. Un guía experto te acompañará en el recorrido y luego podrás relajarte en la playa.",
        'duration': '2 a 4 horas aprox. (turno 1: 7:50-11h · turno 2: 10-14h)', 'availability': 'Martes a domingo',
        'schedule': {'type': 'weekly', 'days': [0, 2, 3, 4, 5, 6]},
        'includes': ['Transportación ida y vuelta', 'Equipo de snorkel', 'Guía durante el recorrido', 'Chaleco salvavidas',
                     'Tiempo libre en la playa', 'Impuestos incluidos'],
        'tax': None, 'note': None,
        'snorkel': True,
        'pricing': {'type': 'per_person', 'price': 72},
    },
    {
        'slug': 'casa-tortuga-cenotes', 'category': 'aventura', 'photo': 'casa-tortuga-cenotes.jpg',
        'name': 'Casa Tortuga CENOTES',
        'desc': 'Los 4 cenotes de Casa Tortuga (Wisho, Campana, Tres Zapotes y Dorca).',
        'long_desc': "Descubrí la magia de Casa Tortuga: cuatro cenotes únicos rodeados de naturaleza, ideales para nadar y explorar. Elegí la opción que mejor se adapte a tu plan, desde una visita corta hasta el paquete completo con transporte, tirolesas y comida.",
        'duration': 'Variable según opción', 'availability': 'Diario',
        'schedule': {'type': 'daily'},
        'includes': ['Entrada a los 4 cenotes (Wisho, Campana, Tres Zapotes y Dorca)',
                     'Tiempo libre para nadar y explorar',
                     'Con Plus: transportación redonda desde Playa del Carmen, tirolesas y comida típica mexicana'],
        'tax': None, 'note': 'Solo entrada: ideal si tenés vehículo propio o ya estás en la zona (sin transporte ni comida)',
        'pricing': {'type': 'tiers', 'tiers': [
            {'label': 'Solo entrada (sin transporte ni comida)', 'price': 48},
            {'label': '+ Comida o tirolesa', 'price': 72},
            {'label': 'Plus: transporte + tirolesas + comida', 'price': 90},
        ]},
    },
    {
        'slug': 'pesca-yate-cancun', 'category': 'pesca', 'photo': None,
        'name': 'Experiencia de Pesca en Yate de 33 Pies - Cancún',
        'desc': 'Salidas en yate privado desde Cancún, con capitán y tripulación experta.',
        'long_desc': "Sal a pescar a bordo de un yate de 33 pies con capitán y tripulación experta, equipo de pesca profesional y todo lo necesario para vivir una aventura completa en altamar. Máximo 7 pasajeros por salida.",
        'duration': 'Según duración elegida', 'availability': 'Salida: Marina Kaybal, Z.H. Cancún',
        # Confirmed by Agustín (2026-09-10): on_request all year, no fixed
        # days — but with its own reason (boat/weather/logistics), not the
        # generic "no fixed weekly schedule" wording used for the other
        # on_request tours, hence the custom schedule_note below.
        'schedule': {'type': 'on_request'},
        'schedule_note': 'Agustín confirma disponibilidad según yate, clima y logística.',
        'includes': ['Tripulación experta (capitán y marineros)', 'Equipo profesional (8 cañas, carretes, buscador de peces, señuelos)',
                     'Licencias de pesca deportiva', 'Bebidas a bordo (aguas, refrescos, cervezas y hielo)', 'Snacks ligeros',
                     'Equipo de seguridad (chalecos y botiquín)', 'Áreas de descanso con sombra', 'Equipo de snorkel y toallas'],
        'tax': 'Impuesto portuario (no incluido): USD 10 por persona', 'note': 'Pesca compartida (4 horas), días 2 y 16 de cada mes: USD 146 + impuesto portuario',
        'pricing': {'type': 'duration_group', 'maxGroup': 7, 'tiers': [
            {'label': '4 horas', 'price': 679}, {'label': '6 horas', 'price': 779},
            {'label': '8 horas', 'price': 879}, {'label': '12 horas', 'price': 1130},
        ]},
    },
]
TOUR_BY_SLUG = {t['slug']: t for t in TOURS}

# Pickup-zone supplements (added 2026-09-24). All published prices already
# assume pickup from Playa del Carmen / Playacar (zones 1-2: no supplement).
# Zone 3 supplement is per-tour and ONLY applies to these 3 tours — every
# other tour is unaffected in zone 3. Zone 4 is a flat per-person surcharge
# on every tour EXCEPT pesca-yate-cancun, which has its own fixed pickup
# point (Marina Kaybal) and was explicitly excluded from the pickup-zone
# system by Agustín (2026-09-24) rather than treated as a hotel transfer.
ZONE3_SURCHARGES_MXN = {
    'isla-mujeres-catamaran': 250,
    'isla-contoy-mujeres': 200,
    'tiburon-ballena': 200,
}
ZONE_EXEMPT_SLUGS = {'pesca-yate-cancun'}

# Quote-only items shown as cards on their category page, no dedicated page
QUOTE_ITEMS = {
    'xcaret': [
        {'name': 'Xcaret', 'desc': 'Parque México · Xcaret Básico'},
        {'name': 'Xplor', 'desc': 'Xplor Día – Aventura extrema'},
        {'name': 'Xel-Há', 'desc': 'Parque acuático natural'},
        {'name': 'Xenses', 'desc': 'Parque de sensaciones'},
        {'name': 'Xoximilco - Fiesta Mexicana', 'desc': 'Recorrido en trajinera con música en vivo'},
        {'name': 'Xenotes by Xcaret', 'desc': 'Recorrido de cenotes en la selva'},
    ],
    'transportes': [
        {'name': 'Traslado Aeropuerto ↔ Hotel', 'desc': 'Privado · De 1 a la cantidad de pasajeros que necesites'},
        {'name': 'Transporte privado a Chichén Itzá', 'desc': 'Ida y vuelta · De 1 a la cantidad de pasajeros que necesites'},
        {'name': 'Transporte privado a Valladolid', 'desc': 'Ida y vuelta · De 1 a la cantidad de pasajeros que necesites'},
        {'name': 'Transporte privado a cenotes', 'desc': 'Ida y vuelta · De 1 a la cantidad de pasajeros que necesites'},
        {'name': 'Transporte privado a Chiquilá (Holbox)', 'desc': 'Ida y vuelta · De 1 a la cantidad de pasajeros que necesites'},
        {'name': 'Transporte privado a centros comerciales', 'desc': 'Ida y vuelta · De 1 a la cantidad de pasajeros que necesites'},
    ],
    'vuelos': [
        {'name': 'Vuelos', 'desc': 'Nacionales e internacionales · Cotización personalizada según fechas y origen'},
        {'name': 'Estadías en hoteles', 'desc': 'Hoteles y resorts en la Riviera Maya · Cotización personalizada según fechas y ocupación'},
    ],
}

# Featured on homepage ("Tours más pedidos"): real tour slugs + a quote card for Xcaret
FEATURED_SLUGS = ['chichen-itza-plus', 'isla-mujeres-catamaran', 'holbox', 'cozumel', 'tiburon-ballena']

# "¿Qué querés vivir?" home selector (2026-09-10): 4 paths — 3 lead to a
# real, already-built category page (chosen photo is one of that
# category's own real tour photos), the 4th is a direct WhatsApp ask for
# a personal recommendation instead of a destination.
PATH_TILES = [
    {'key': 'ruinas', 'label': 'Ruinas y cultura', 'href': '/categoria/cultura-maya-ruinas/', 'photo': 'chichen-itza-plus.jpg'},
    {'key': 'islas', 'label': 'Islas y mar', 'href': '/categoria/islas-catamaranes/', 'photo': 'isla-mujeres-catamaran.jpg'},
    {'key': 'aventura', 'label': 'Cenotes y aventura', 'href': '/categoria/aventura-acuatica/', 'photo': 'atv-casa-jaguar.jpg'},
]

# Short experience tag shown on tour cards. This is a category-level
# label, not a per-tour claim — the project has no per-tour "ideal for"
# field, so it's presented as a plain tag ("Historia y cultura"), never
# phrased as "Ideal para..." (which would imply a specific recommendation
# this tour doesn't actually carry as data).
CATEGORY_TAG = {
    'ruinas': 'Historia y cultura',
    'islas': 'Islas y mar',
    'aventura': 'Aventura y cenotes',
}

# Home FAQ section (added 2026-09-11), between "Servicios especiales" and
# contacto. Single source of truth for both the visible accordion and the
# FAQPage structured data — the JSON-LD is built from this same list, so
# it can never drift from what's actually shown on the page. Wording is
# exactly what Agustín gave; nothing here is guessed or extrapolated
# (no cancellation policy beyond the no-show clause, no pickup times, no
# weather policy, no card-at-pickup, no invented kid/quota rules).
#
# FAQ #11's copy was updated 2026-09-25 to match the new "future trip /
# no fixed date" contact form below (same rewording the form itself uses)
# instead of the old "1 a 3 meses" framing it replaced — flagged as
# lightly-authored copy in that PR's summary, not a new business rule.
FAQS = [
    {
        'q': '¿Hasta cuándo puedo reservar o cambiar la fecha?',
        'a': 'Las reservas y cambios de fecha se hacen hasta las 20:00 del día anterior, hora local de Playa del Carmen. Así podemos coordinar transporte, cupos y operación sin improvisar.',
    },
    {
        'q': '¿La reserva queda confirmada automáticamente?',
        'a': 'No. La web organiza tu solicitud y Agustín confirma disponibilidad por WhatsApp. Una reserva queda confirmada cuando se completa el método de pago que hayan coordinado.',
    },
    {
        'q': '¿Cómo sé qué días opera cada tour?',
        'a': 'En cada ficha vas a ver los días operativos y el calendario sólo deja elegir fechas disponibles para ese tour. Si aparece "Consultá disponibilidad", elegís una fecha tentativa y Agustín la confirma directamente por WhatsApp.',
    },
    {
        'q': '¿Qué pasa si no me presento o quiero reprogramar el mismo día?',
        'a': 'Un no-show o una reprogramación el mismo día requiere un adelanto de $250 MXN por persona para volver a coordinar la operación. Ese importe se descuenta del total del tour cuando se realiza. Si después de pagarlo la reserva se vuelve a cancelar, no hay devolución.',
    },
    {
        'q': '¿Cómo puedo pagar?',
        'a': 'Con tarjeta coordinamos un link de pago. También podés pagar en efectivo USD o MXN al momento del pickup, justo antes de hacer el tour. Si preferís transferencia, se paga el valor completo del tour y la reserva se confirma una vez acreditado el depósito.',
    },
    {
        'q': '¿La web me cobra al hacer la reserva?',
        'a': 'No. La web no procesa un pago automático. Primero mandás la solicitud y coordinás el pago con Agustín por WhatsApp según el método que elijas.',
    },
    {
        'q': '¿Puedo reservar más de un tour en el mismo viaje?',
        'a': 'Sí. Podés agregar varios tours, elegir una fecha para cada uno y enviar una sola solicitud. Tus datos de contacto se completan una vez y después revisamos juntos que el itinerario tenga sentido.',
    },
    {
        'q': '¿Qué datos necesito para reservar?',
        'a': 'Nombre de quien reserva, hotel, número de habitación, cantidad de adultos, niños e infantes, y método de pago. Los infantes no pagan, pero sí los contamos para organizar la transportación.',
    },
    {
        'q': '¿El traslado a Cozumel está incluido?',
        'a': 'La transportación de Cozumel está incluida a partir de 4 personas. Si son 2 o 3 personas, escribime antes: buscamos una alternativa y ajustamos el precio por el inconveniente.',
    },
    {
        'q': '¿Viajan en grupo grande?',
        'a': 'Para grupos de 10 personas o más, escribime desde la sección de contacto o por WhatsApp. Te armamos un presupuesto especial según la cantidad de pasajeros, fechas y plan que buscan.',
    },
    {
        'q': 'Todavía no tengo fecha definida o mi viaje es más adelante, ¿igual puedo consultar?',
        'a': 'Sí. Las reservas se hacen con hasta un mes de anticipación. Si todavía no sabés la fecha exacta o tu viaje es más adelante, escribinos por WhatsApp o dejá tus datos en el formulario de contacto y te ayudamos a planificar.',
    },
]

# "Conocé a Agustín" story viewer (home). Photos are Agustín's own,
# untouched (no crop, no edit, stickers left as-is) — order is curated by
# hand, not random. See previous revisions of this file for the full
# curation rationale (fixed intro/closing photos, alternating criteria,
# party photos placed later, video mid-sequence). `tag` is only set for
# photos with an explicit, confirmed link from Agustín; `pos` is measured
# by hand in percent of the photo itself. Tag labels are official place/
# business names or handles — never translated (see UI/tour_text helpers,
# which only ever touch descriptive text, not proper nouns).
AGUSTIN_STORIES = [
    {'file': '73DB1620-354E-4F1A-A292-32E337B52ED9.JPG', 'tag': None},
    {'file': '85052D02-77C8-4E2C-8209-768EB53517B4.JPG', 'tag': None},
    {'file': '9FE46935-BC9E-4314-B75B-C1E4CD5D2782.JPG', 'tag': None},
    {'file': '508D33D4-A80D-49E0-A8FC-3F43D32F49B8.JPG', 'tag': None},
    {'file': '18220B3C-E527-4116-BD4F-E5E308EF746C.JPG', 'tag': None},
    {'file': 'A8E0A5E5-41B3-45B8-8402-AB332684C7C7.JPG', 'tag': None},
    {'file': '18CF1303-40E8-4C82-8293-57781418C3BD.JPG', 'tag': None},
    {'file': '9E7063C3-BBA3-4DFE-A10A-E8ED82B77C6D.JPG', 'tag': None},
    {'file': 'C20F7DA9-2CA0-4BF5-BB0B-0FFD3BF9A9C4.JPG', 'tag': {
        'type': 'maps', 'label': 'ATIK World Tulum',
        'url': 'https://maps.app.goo.gl/qMsWNdN8GG8sZc92A',
        'pos': {'left': 16, 'top': 74, 'width': 67, 'height': 7}}},
    {'file': '93D223B9-97FA-4309-9673-3B907F9A95ED.JPG', 'tag': None},
    {'file': '26E88537-A8F4-4292-A1F9-9C87074E29BD.JPG', 'tag': None},
    {'file': 'C5C68CEC-2A0A-4E92-958B-866E7A3BA276.JPG', 'tag': None},
    {'file': '5A00AAF0-5D22-4749-8230-E5E54E51151F.JPG', 'tag': None},
    {'file': '70F8514D-5307-4341-AD23-73B5D22A81E9.JPG', 'tag': {
        'type': 'maps', 'label': "Sian Ka'an · Reserva de la Biosfera",
        'url': 'https://maps.app.goo.gl/2PZxa7mA4U2pAAHW7',
        'pos': {'left': 20, 'top': 21, 'width': 57, 'height': 5}}},
    {'file': 'FD94F6C5-4EB0-4AB8-B8F5-8295A4A2257F.JPG', 'tag': {
        'type': 'maps', 'label': 'Marina Tower Center, Puerto Cancún',
        'url': 'https://maps.app.goo.gl/H2GBiMk6z55NbCSQ9',
        'pos': {'left': 58, 'top': 11, 'width': 37, 'height': 5}}},
    {'file': 'DBDF124B-F458-4DE1-B5E4-5D53F813A0D1.JPG', 'tag': None},
    {'file': 'F8E4E379-7210-478B-973E-8399FCF55AE3.mp4', 'type': 'video', 'tag': None},
    {'file': 'D7C971EA-1CB5-4252-A3CD-D83431A870D8.JPG', 'tag': {
        'type': 'maps', 'label': 'Playa de Xpu-Ha',
        'url': 'https://maps.app.goo.gl/gYmiBgkPqPkvBeMt7',
        'pos': {'left': 3, 'top': 24, 'width': 30, 'height': 7}}},
    {'file': '5F937755-BB0B-434A-A8FC-DABD27EB1668.JPG', 'tag': None},
    {'file': '0E5F81A1-EA04-4ED3-83F8-755A382F76EA.JPG', 'tag': {
        'type': 'mention', 'label': '@puravida.wey',
        'url': 'https://www.instagram.com/puravida.wey/',
        'pos': {'left': 20, 'top': 6, 'width': 38, 'height': 4}}},
    {'file': 'C758011B-6608-477E-B2D0-295D9450640B.JPG', 'tag': None},
    {'file': '74F7FEFD-FB33-4CB8-8672-A80F3416BFC8.JPG', 'tag': None,
     'alt': 'Agustín junto a su familia durante un viaje', 'alt_en': 'Agustín with his family during a trip'},
]

# ---------------------------------------------------------------------------
# GOOGLE REVIEWS DATA (home). Only real, verifiable reviews — no invented
# names, text, ratings, dates, photos or count. `text_en` is a human
# translation (authored for this feature, flagged for review), never a
# live/automatic translation — shown by default on the English site, with
# a "See original" toggle that reveals `text` unchanged (see
# render_reviews_section). Names/initials are never translated.
# ---------------------------------------------------------------------------

REVIEWS = [
    {
        'name': 'Milagro Martinez', 'initials': 'MM',
        'text': 'Muchas gracias por estas increibles vacaiones!!! Todo muy profesional y tal cual como lo imaginas !! Definitivamemte volveremos a contratar sus servicios !',
        'text_en': "Thank you so much for these incredible vacations!!! Everything was so professional, exactly as you'd imagine!! We will definitely book with them again!",
    },
    {
        'name': 'Micaela Benitez', 'initials': 'MB',
        'text': 'Muy buena atención, predisposición y servicio de parte de Mundo Caribe Tours. Es super importante poder contar con proveedores de suma confianza a la hora de recomendarles servicios a pasajeros.',
        'text_en': "Excellent attention, willingness to help, and service from Mundo Caribe Tours. Having suppliers you can fully trust is so important when recommending services to travelers.",
    },
    {
        'name': 'Matías Van Asten', 'initials': 'MV',
        'text': 'Conocí islas mujeres, una experiencia impresionante',
        'text_en': 'I visited Isla Mujeres — an amazing experience.',
    },
]

# ---------------------------------------------------------------------------
# ENGLISH OVERLAYS — human-language field overrides, keyed exactly like the
# Spanish source above. Every translatable field on every TOURS/CATEGORIES/
# QUOTE_ITEMS/FAQS/PATH_TILES/CATEGORY_TAG entry MUST have a matching key
# here; validate_translations() (see HELPERS) fails the build loudly if one
# is missing, so no Spanish text can silently leak onto the English site.
# Brand name, proper nouns, official place/hotel/park names, slugs and all
# numbers/prices are NEVER overridden here — they're identical in both
# languages and simply fall through untouched (see tour_text()/cat_text()).
# ---------------------------------------------------------------------------

TOURS_EN = {
    'chichen-itza': {
        'name': 'Chichén Itzá – History, Nature and Culture',
        'desc': 'Certified guide, Oxman cenote, and free time in Valladolid, a Pueblo Mágico.',
        'long_desc': "Discover the grandeur of Chichén Itzá with a certified guide, cool off at the stunning Oxman cenote, and explore the colorful streets of Valladolid, a Pueblo Mágico full of history and tradition.",
        'duration': 'About 12 hours', 'availability': 'Daily',
        'includes': ['Round-trip transportation', 'Chichén Itzá admission + free time', 'Guided tour with a certified guide',
                     'Oxman cenote admission ticket + life jacket', 'Buffet lunch with local dishes and 1 non-alcoholic drink',
                     'Free time in Valladolid'],
        'tax': None, 'note': None,
    },
    'chichen-itza-plus': {
        'name': 'Chichén Itzá Plus – History, Nature and Culture in One Day',
        'desc': 'One of the 7 Wonders of the World + 2 cenotes and buffet lunch at a hacienda.',
        'long_desc': "Discover one of the 7 Wonders of the World with an expert guide. Cool off at the stunning Suytún and Ik'kil cenotes and enjoy a buffet lunch at a beautiful hacienda. A day full of history, culture, and nature.",
        'duration': 'About 12 hours', 'availability': 'Daily',
        'includes': ['Round-trip transportation', 'Guided visit to Chichén Itzá', 'Free time at the archaeological site',
                     'Suytún cenote admission ticket', "Ik'kil cenote admission ticket",
                     'Buffet lunch (includes 1 non-alcoholic drink)', 'Free time in Valladolid'],
        'tax': None, 'note': None,
    },
    'tulum': {
        'name': 'Tulum',
        'desc': 'Guided visit to the Tulum ruins, right on the sea. Admission, certified guide, and free time for photos.',
        'long_desc': "Guided visit to the Tulum ruins, one of the most striking archaeological sites on the Riviera. Ideal for history lovers and unique scenery.",
        'duration': 'About 2.5 hours', 'availability': 'Daily',
        'includes': ['Admission to the archaeological site', 'Guided tour with a certified guide', 'Free time for photos'],
        'tax': 'Federal tax (not included): $265 MXN, paid directly on site', 'note': None,
    },
    'tulum-casa-tortuga': {
        'name': 'Tulum + Casa Tortuga – History and Nature in One Day',
        'desc': 'Tulum ruins with a certified guide + the 4 cenotes of Casa Tortuga.',
        'long_desc': "Explore the imposing ruins of Tulum with a certified guide and dive into the magical Casa Tortuga cenotes, surrounded by nature.",
        'duration': 'About 8 hours', 'availability': 'Check availability',
        'includes': ['Round-trip transportation', 'Admission and guided tour of Tulum',
                     'Visit to the 4 Casa Tortuga cenotes (Dorca, Wisho, Tres Zapotes, and Campana)',
                     'Free time for swimming', 'Traditional Mexican meal'],
        'tax': 'Federal tax (not included): $265 MXN, paid at the Tulum Archaeological Site', 'note': None,
    },
    'tulum-tortugas-akumal': {
        'name': 'Tulum + Akumal Turtles – History and Nature in the Caribbean',
        'desc': 'Tulum archaeological site + snorkeling with turtles in Akumal.',
        'long_desc': "Discover the magic of Tulum, one of the most impressive archaeological sites, and experience the thrill of swimming with turtles in Akumal. A unique experience combining culture and interaction with marine life.",
        'duration': 'About 8 hours', 'availability': 'Tuesday to Sunday',
        'includes': ['Round-trip transportation', 'Admission and guided tour of Tulum', 'Free time at the archaeological site',
                     'Snorkeling with turtles in Akumal', 'Full snorkel gear and life jacket',
                     'Specialized guide during the activity', 'Meal (drinks not included)'],
        'tax': 'Tulum federal tax (not included): $265 MXN, paid on site', 'note': None,
    },
    'coba-sunset': {
        'name': 'Cobá Sunset – History and Nature in a Perfect Morning',
        'desc': 'Cobá without the crowds, Choo Ha cenote, and a Mayan ritual in a local village.',
        'long_desc': "Discover Cobá after the crowds, explore its impressive archaeological site, and cool off at the Choo Ha cenote. Plus, experience an authentic Mayan ritual in a local village.",
        'duration': 'About 6 hours', 'availability': 'Monday, Wednesday, and Saturday',
        'includes': ['Round-trip transportation', 'Admission and free time at Cobá', 'Admission and swim at the Choo Ha cenote',
                     'Buffet lunch with local dishes', 'Visit to a Mayan village with a purification ritual'],
        'tax': 'Cobá admission fee (not included): $330 MXN, paid directly on site', 'note': None,
    },
    'holbox': {
        'name': 'Holbox: Island and Nature Adventure',
        'desc': 'Yalahau spring, Isla de la Pasión, and the colorful streets of Holbox.',
        'long_desc': "Explore Holbox, a paradise of white sand and crystal-clear water. Swim in the refreshing Yalahau spring, discover the beauty of Isla de la Pasión, and stroll the colorful streets of Holbox by bike or on foot.",
        'duration': 'About 10 hours', 'availability': 'Monday, Wednesday, and Friday',
        'includes': ['Round-trip transportation', 'Box lunch', 'Drinks on board', 'À la carte meal + 1 non-alcoholic drink',
                     'Bike rental (1 hour)', 'Swim at the Yalahau spring', 'Visit to Isla de la Pasión',
                     'Free time in Holbox'],
        'tax': 'Fee (not included): $35 MXN, paid directly', 'note': None,
    },
    'isla-contoy-mujeres': {
        'name': 'Isla Contoy + Isla Mujeres – Nature and Charm',
        'desc': 'Snorkeling in Isla Contoy and free time in Isla Mujeres, with regional food.',
        'long_desc': "Discover two Caribbean gems in a single day. Explore the beautiful Isla Contoy, an unspoiled paradise ideal for nature lovers. Swim in its crystal-clear waters and unwind with free time in Isla Mujeres.",
        'duration': 'About 8 hours', 'availability': 'Tuesday, Thursday, and Sunday',
        'includes': ['Round-trip transportation', 'Boat ride', 'Snorkeling in Isla Contoy (gear included)',
                     'Free time in Isla Contoy and Isla Mujeres', 'Drinks on board', 'Regional meal (Tikinxic chicken or fish)'],
        'tax': 'Federal tax (not included): USD 23 ($360 MXN)', 'note': None,
    },
    'isla-mujeres-catamaran': {
        'name': 'Isla Mujeres by Catamaran – Sea, Sun and Fun',
        'desc': 'Catamaran with open bar, reef snorkeling, and a beach club with buffet.',
        'long_desc': "Enjoy an incredible day sailing to Isla Mujeres on a catamaran with an open bar, music, and the best vibes. Go snorkeling on a reef, relax at a beach club with a buffet, and explore the charming town center of the island.",
        'duration': 'About 8 hours', 'availability': 'Daily',
        'includes': ['Round-trip transportation', 'Catamaran ride', 'Beach club with loungers', 'Buffet lunch',
                     'Open bar (on board and at the beach club)', 'Reef snorkeling (gear included)',
                     'Spinnaker (weather permitting)', 'Free time in Isla Mujeres'],
        'tax': None, 'note': 'The price includes the federal tax (USD 20); paid before boarding',
    },
    'bacalar': {
        'name': 'Bacalar: Adventure in the Lagoon of Seven Colors',
        'desc': 'Cenote Negro, Cocalitos, and Esmeralda, Isla de los Pájaros, and the Pirates’ Channel.',
        'long_desc': "Explore the spectacular Bacalar Lagoon aboard a boat and marvel at its crystal-clear water and vibrant shades of blue. Swim in underwater cenotes, visit Isla de los Pájaros, and sail along the legendary Pirates' Channel.",
        'duration': 'About 10 hours', 'availability': 'Tuesday, Thursday, and Saturday',
        'includes': ['Round-trip transportation', 'Boat ride', 'Visit to Cenote Negro, Cenote Cocalitos, and Cenote Esmeralda',
                     'Isla de los Pájaros', "Pirates' Channel", 'À la carte meal (chicken or fish) + 1 non-alcoholic drink'],
        'tax': None, 'note': 'No cancellations once the date is booked',
    },
    'cozumel': {
        'name': 'Cozumel - El Cielo and El Cielito',
        'desc': 'Exclusive catamaran with snorkel stops at El Cielo, El Cielito, and Chankanaab.',
        'long_desc': "Explore Cozumel on an exclusive catamaran. Snorkel stops at El Cielo, El Cielito, and Chankanaab, plus food and drinks included. A VIP experience over turquoise waters.",
        'duration': 'About 7 hours', 'availability': 'Daily',
        'includes': ['5-hour catamaran ride', 'Snorkeling at 3 stops (El Cielo, El Cielito, and Chankanaab)',
                     'Food and drinks on board', 'Snorkel gear included'],
        'tax': 'Cozumel ferry not included: approx. USD 30 round trip', 'note': None,
    },
    'tiburon-ballena': {
        'name': 'Whale Shark',
        'desc': 'Swim next to the biggest fish in the world. A 100% regulated tour with certified guides.',
        'long_desc': "Live the unique experience of swimming next to the biggest fish in the world. A 100% regulated and safe tour, with certified guides and professional equipment.",
        'duration': 'About 8 hours', 'availability': 'June to September',
        'includes': ['Transportation from Playa del Carmen', 'Speedboat to the sighting area',
                     'Full snorkel gear', 'Certified guide', 'Box lunch and drinks'],
        'tax': None, 'note': 'Not suitable for pregnant travelers',
    },
    'atv-casa-jaguar': {
        'name': "ATVs Casa Jaguar – Adventure and Cenotes",
        'desc': 'ATV ride through the jungle and the Jaguar, Alux, and Nohoch cenotes.',
        'long_desc': "Feel the adrenaline riding an ATV through the jungle and explore the stunning Jaguar, Alux, and Nohoch cenotes. A perfect tour for adventure and nature lovers.",
        'duration': 'About 4 hours', 'availability': 'Daily',
        'includes': ['Round-trip transportation', 'ATV ride (single or double)', 'Swim at the Alux cenote',
                     'Visit to the Nohoch cave', 'Exploration of the Jaguar cenote', 'Snack to recharge'],
        'tax': None, 'note': 'Not suitable for infants · wear comfortable clothes, a swimsuit, and closed-toe shoes',
        'tier_labels': ['Single (1 per ATV)', 'Double (2 per ATV, each)'],
    },
    'akumal-cenote-nohoch': {
        'name': 'Akumal + Cenote Nohoch – Adventure Among Turtles and Underground Nature',
        'desc': 'Swim with turtles in Akumal and Cenote Nohoch, with a hammock area.',
        'long_desc': "Explore Akumal, a beach ideal for swimming with sea turtles in clear turquoise water, then enjoy the beauty of Cenote Nohoch, a mystical cavern with crystal-clear water, a hammock rest area, and a delicious regional buffet.",
        'duration': 'About 7-8 hours', 'availability': 'Tuesday to Sunday',
        'includes': ['Round-trip transportation', 'Guided snorkeling with turtles in Akumal', 'Snorkel gear included',
                     'Admission to Cenote Nohoch', 'Access to the hammock rest area', 'Regional buffet lunch'],
        'tax': None, 'note': 'Activity subject to sea conditions, limited spots',
    },
    'akumal-expres': {
        'name': 'Akumal Express – Swim with Turtles and Relax on the Beach',
        'desc': 'Guided snorkeling with turtles in their natural habitat and free time on the beach.',
        'long_desc': "Have an unforgettable experience swimming with turtles in their natural habitat in Akumal. An expert guide will accompany you, and afterward you can relax on the beach.",
        'duration': '2 to 4 hours approx. (shift 1: 7:50–11am · shift 2: 10am–2pm)', 'availability': 'Tuesday to Sunday',
        'includes': ['Round-trip transportation', 'Snorkel gear', 'Guide during the tour', 'Life jacket',
                     'Free time on the beach', 'Taxes included'],
        'tax': None, 'note': None,
    },
    'casa-tortuga-cenotes': {
        'name': 'Casa Tortuga CENOTES',
        'desc': 'The 4 cenotes of Casa Tortuga (Wisho, Campana, Tres Zapotes, and Dorca).',
        'long_desc': "Discover the magic of Casa Tortuga: four unique cenotes surrounded by nature, perfect for swimming and exploring. Choose the option that best fits your plan, from a short visit to the full package with transportation, zip-lines, and food.",
        'duration': 'Varies by option', 'availability': 'Daily',
        'includes': ['Admission to the 4 cenotes (Wisho, Campana, Tres Zapotes, and Dorca)',
                     'Free time for swimming and exploring',
                     'With Plus: round-trip transportation from Playa del Carmen, zip-lines, and traditional Mexican food'],
        'tax': None, 'note': 'Admission only: ideal if you have your own vehicle or are already in the area (no transportation or food)',
        'tier_labels': ['Admission only (no transportation or food)', '+ Food or zip-line', 'Plus: transportation + zip-lines + food'],
    },
    'pesca-yate-cancun': {
        'name': '33-Foot Yacht Fishing Experience - Cancún',
        'desc': 'Private yacht trips from Cancún, with an expert captain and crew.',
        'long_desc': "Go fishing aboard a 33-foot yacht with an expert captain and crew, professional fishing gear, and everything you need for a complete deep-sea adventure. Maximum 7 passengers per trip.",
        'duration': 'Depends on the option chosen', 'availability': 'Departure: Marina Kaybal, Cancún Hotel Zone',
        'schedule_note': 'Agustín confirms availability based on the boat, weather, and logistics.',
        'includes': ['Expert crew (captain and deckhands)', 'Professional gear (8 rods, reels, fish finder, lures)',
                     'Sport fishing licenses', 'Drinks on board (water, soft drinks, beer, and ice)', 'Light snacks',
                     'Safety equipment (life jackets and first-aid kit)', 'Shaded rest areas', 'Snorkel gear and towels'],
        'tax': 'Port tax (not included): USD 10 per person', 'note': 'Shared fishing trip (4 hours), on the 2nd and 16th of each month: USD 146 + port tax',
        'tier_labels': ['4 hours', '6 hours', '8 hours', '12 hours'],
    },
}

CATEGORIES_EN = {
    'cultura-maya-ruinas': {
        'title': 'Mayan Culture & Ruins',
        'intro': 'Travel back in time to the great Mayan cities. Chichén Itzá, Tulum, and Cobá, with cenotes and certified guides included on every tour.',
        'card_desc': 'Chichén Itzá, Tulum, and Cobá — history by the sea and in the jungle.',
    },
    'islas-catamaranes': {
        'title': 'Islands & Catamarans',
        'intro': 'Turquoise waters, catamarans, and snorkeling on the best reefs of the Mexican Caribbean: Isla Mujeres, Isla Contoy, Holbox, Bacalar, and Cozumel.',
        'card_desc': 'Isla Mujeres, Isla Contoy, Holbox, Bacalar, and Cozumel.',
    },
    'aventura-acuatica': {
        'title': 'Water Adventure',
        'intro': 'Cenotes, ATVs, and snorkeling with turtles: the most adventurous side of the Riviera Maya, for those seeking adrenaline and nature in the same day.',
        'card_desc': "Cenotes, Akumal's turtles, and ATV adventure through the jungle.",
    },
    'pesca-deportiva': {
        'title': 'Sport Fishing',
        'intro': 'Private yacht trips from Cancún, with an expert captain and crew, for a full day of deep-sea fishing.',
        'card_desc': 'Private yacht trips from Cancún, by the hour or shared.',
    },
    'xperiencias-xcaret': {
        'title': 'Xperiencias by Xcaret',
        'intro': 'The Grupo Xcaret parks: nature, adventure, and Mexican culture. Price and availability are quoted based on your dates.',
        'card_desc': 'Xcaret, Xplor, Xel-Há, Xenses, Xoximilco, and Xenotes.',
    },
    'transportes': {
        'title': 'Transportation',
        'intro': 'Private door-to-door transfers across the Riviera Maya, from 1 up to as many passengers as you need.',
        'card_desc': 'Private transfers: airport-hotel, Chichén Itzá, Valladolid, cenotes, and shopping malls.',
    },
    'vuelos-hoteles': {
        'title': 'Flights and Hotels',
        'intro': "We'll put together your whole trip: custom quotes for flights and hotel stays across the Riviera Maya.",
        'card_desc': 'We quote your flights and your stay to build the complete trip.',
    },
}

QUOTE_ITEMS_EN = {
    'xcaret': [
        {'name': 'Xcaret', 'desc': 'México Park · Basic Xcaret ticket'},
        {'name': 'Xplor', 'desc': 'Xplor Día – Extreme adventure'},
        {'name': 'Xel-Há', 'desc': 'Natural water park'},
        {'name': 'Xenses', 'desc': 'Park of sensations'},
        {'name': 'Xoximilco - Fiesta Mexicana', 'desc': 'Trajinera boat ride with live music'},
        {'name': 'Xenotes by Xcaret', 'desc': 'Jungle cenote tour'},
    ],
    'transportes': [
        {'name': 'Airport ↔ Hotel Transfer', 'desc': 'Private · From 1 up to as many passengers as you need'},
        {'name': 'Private transportation to Chichén Itzá', 'desc': 'Round trip · From 1 up to as many passengers as you need'},
        {'name': 'Private transportation to Valladolid', 'desc': 'Round trip · From 1 up to as many passengers as you need'},
        {'name': 'Private transportation to cenotes', 'desc': 'Round trip · From 1 up to as many passengers as you need'},
        {'name': 'Private transportation to Chiquilá (Holbox)', 'desc': 'Round trip · From 1 up to as many passengers as you need'},
        {'name': 'Private transportation to shopping malls', 'desc': 'Round trip · From 1 up to as many passengers as you need'},
    ],
    'vuelos': [
        {'name': 'Flights', 'desc': 'Domestic and international · Custom quote based on dates and origin'},
        {'name': 'Hotel stays', 'desc': 'Hotels and resorts across the Riviera Maya · Custom quote based on dates and occupancy'},
    ],
}

FAQS_EN = [
    {
        'q': 'How far in advance can I book or change a date?',
        'a': 'Bookings and date changes can be made until 8:00 PM the day before, Playa del Carmen local time. This lets us coordinate transportation, spots, and operations without last-minute scrambling.',
    },
    {
        'q': 'Is my booking automatically confirmed?',
        'a': 'No. The website organizes your request, and Agustín confirms availability over WhatsApp. A booking is confirmed once the payment method you agreed on has been completed.',
    },
    {
        'q': 'How do I know which days each tour runs?',
        'a': 'Each tour page shows its operating days, and the calendar only lets you pick dates available for that tour. If it says "Check availability," you choose a tentative date and Agustín confirms it directly over WhatsApp.',
    },
    {
        'q': "What happens if I'm a no-show or want to reschedule the same day?",
        'a': "A no-show or a same-day reschedule requires a $250 MXN per-person deposit to coordinate the operation again. That amount is deducted from the tour's total once it takes place. If the booking is cancelled again after paying it, there's no refund.",
    },
    {
        'q': 'How can I pay?',
        'a': 'For card payments, we set up a payment link. You can also pay in cash, USD or MXN, right at pickup, just before the tour. If you prefer a bank transfer, the full tour price is paid upfront, and the booking is confirmed once the deposit clears.',
    },
    {
        'q': 'Does the website charge me when I book?',
        'a': "No. The website doesn't process any automatic payment. You send your request first, then coordinate payment with Agustín over WhatsApp using the method you choose.",
    },
    {
        'q': 'Can I book more than one tour for the same trip?',
        'a': "Yes. You can add several tours, choose a date for each one, and send a single request. Your contact details are filled in once, and then we'll go over the itinerary together to make sure it makes sense.",
    },
    {
        'q': 'What information do I need to book?',
        'a': "The name of the person booking, hotel, room number, number of adults, children, and infants, and payment method. Infants don't pay, but we do count them to organize transportation.",
    },
    {
        'q': 'Is the Cozumel transfer included?',
        'a': "Cozumel transportation is included for groups of 4 or more. If you're 2 or 3 people, message me beforehand — we'll find an alternative and adjust the price for the inconvenience.",
    },
    {
        'q': 'Traveling in a large group?',
        'a': "For groups of 10 people or more, message me through the contact section or on WhatsApp. We'll put together a special quote based on your number of travelers, dates, and the plan you're after.",
    },
    {
        'q': "I don't have exact dates yet, or my trip is further away — can I still reach out?",
        'a': "Yes. Bookings can be made up to one month in advance. If you don't know your exact dates yet or your trip is further away, message us on WhatsApp or leave your details in the contact form and we'll help you plan.",
    },
]

PATH_TILES_EN = {
    'ruinas': 'Ruins and culture',
    'islas': 'Islands and sea',
    'aventura': 'Cenotes and adventure',
}

CATEGORY_TAG_EN = {
    'ruinas': 'History and culture',
    'islas': 'Islands and sea',
    'aventura': 'Adventure and cenotes',
}

# ---------------------------------------------------------------------------
# UI STRINGS — every static/dynamic chrome string on the site, in one place.
# UI[lang][key]. Read by Python (render_* functions, via T()) AND by the
# JS runtime (the whole UI[lang] dict is embedded as JSON on every page —
# see render_i18n_script() — so assets/site.js never hardcodes a
# translatable string; it only ever reads window.MC_I18N.key). Templates
# use {placeholder} tokens, replaced with .replace() in JS or .format()-
# style f-strings in Python — no library, matches the rest of the project.
# ---------------------------------------------------------------------------

UI = {'es': {}, 'en': {}}

UI['es'] = {
    # ---- nav / footer ----
    'general_wa_text': 'Hola, quisiera información sobre los tours.',
    'nav_tours': 'Tours', 'nav_guides': 'Guías', 'nav_contact': 'Contacto',
    'nav_view_all_tours': 'Ver todos los tours', 'nav_open_menu_aria': 'Abrir menú',
    'nav_whatsapp_btn': 'WhatsApp', 'mobile_menu_wa_btn': 'Escribinos por WhatsApp',
    'lang_switch_aria': 'Idioma',
    'footer_cta_heading': '¿Armamos tu próximo viaje?',
    'footer_cta_sub': 'Escribinos y coordinamos todo por WhatsApp.',
    'footer_cta_btn': 'Escribinos por WhatsApp',
    'footer_handle_reviews': '⭐ Reseñas en Google',
    'footer_location': 'Playa del Carmen, Riviera Maya',
    'breadcrumb_home': 'Inicio',
    # ---- future-trip / no-fixed-date contact form (WhatsApp-based) ----
    'future_form_heading': '¿Aún no tienes una fecha definida o tu viaje es más adelante?',
    'future_form_sub': 'Las reservas se realizan con hasta un mes de anticipación. Si todavía no conoces la fecha exacta o falta más tiempo para tu viaje, escríbenos por WhatsApp y te ayudaremos a planificar.',
    'future_form_name_label': 'Nombre',
    'future_form_phone_label': 'WhatsApp / Teléfono',
    'future_form_email_label': 'Email',
    'future_form_date_label': 'Fecha aproximada del viaje',
    'future_form_nodate_label': 'Todavía no tengo fecha definida',
    'future_form_tours_label': 'Tours de interés',
    'future_form_tours_placeholder': 'Ej: Chichén Itzá, Holbox...',
    'future_form_message_label': 'Mensaje (opcional)',
    'future_form_submit': 'Enviar',
    'future_form_missing': 'Completá tu nombre y WhatsApp antes de enviar.',
    'future_form_opened': 'Abrimos WhatsApp con tu consulta.',
    'future_form_nodate_value': 'sin fecha definida',
    'future_form_greeting_tpl': 'Hola, me llamo {name}. Todavía no tengo fecha definida o mi viaje es más adelante — quisiera más información:',
    'future_form_phone_wa_label': 'WhatsApp/Teléfono',
    'future_form_email_wa_label': 'Email',
    'future_form_date_wa_label': 'Fecha aproximada',
    'future_form_tours_wa_label': 'Tours de interés',
    'future_form_message_wa_label': 'Mensaje',
    'future_form_disclaimer': 'Esto no es una reserva confirmada ni un recordatorio automático — es el punto de partida para planificar juntos por WhatsApp.',
    # ---- home ----
    'home_title': 'Mundo Caribe Tours — Tours y excursiones en la Riviera Maya',
    'home_desc': 'Tours y excursiones en la Riviera Maya, coordinados directo por WhatsApp: cenotes, ruinas mayas, islas y mucho más.',
    'hero_eyebrow': 'Riviera Maya, México',
    'hero_h1': 'Vivan el Caribe mexicano a fondo',
    'hero_lede': 'Soy Agustín, argentino, vivo en la Riviera Maya hace 6 años. Conozco cada cenote, ruina e isla para armarte el viaje ideal.',
    'hero_btn_plan': 'Encontrá tu plan',
    'hero_btn_wa': 'Hablá conmigo por WhatsApp',
    'hero_signal': '🤝 Coordinado directo con Agustín por WhatsApp',
    'hero_photo_alt': 'Laguna de Bacalar, Riviera Maya',
    'stories_label': 'Conocé a Agustín',
    'story_prev_aria': 'Historia anterior', 'story_next_aria': 'Historia siguiente', 'story_close_aria': 'Cerrar',
    'planes_eyebrow': 'Elegí tu plan', 'planes_h2': '¿Qué querés vivir?',
    'planes_sub': 'Contame qué te llama más y te llevo directo a esos tours.',
    'planes_view_tours': 'Ver tours →',
    'planes_wa_tile_h3': 'No sé, recomendame vos', 'planes_wa_tile_link': 'Hablar por WhatsApp →',
    'planes_wa_text': '¡Hola! Todavía no sé qué tour elegir — ¿me recomendás algo según lo que busco?',
    'featured_eyebrow': 'Destacados', 'featured_h2': 'Nuestros tours más pedidos',
    'featured_sub': 'Elegí un tour para ver el detalle completo, precio y reservar directo por WhatsApp. Deslizá para ver más →',
    'special_eyebrow': 'Servicios especiales', 'special_h2': 'Todo lo que necesitás para tu viaje',
    'special_view_more': 'Ver más →',
    'xcaret_quote_desc': 'Parque México · Xcaret Básico',
    # ---- reviews ----
    'reviews_eyebrow': 'Reseñas reales', 'reviews_h2': 'Lo cuentan quienes ya vivieron el Caribe',
    'reviews_sub': 'Experiencias reales de viajeros que eligieron Mundo Caribe Tours.',
    'reviews_summary': '5.0 en Google · 5 opiniones', 'reviews_cta': 'Ver todas las reseñas en Google →',
    'reviews_source': 'Reseña de Google', 'reviews_stars_aria': 'Calificación: 5 de 5 estrellas',
    'reviews_group_aria': 'Reseñas de clientes',
    'reviews_see_original': 'Ver texto original', 'reviews_view_translation': 'Ver traducción al inglés',
    # ---- faq ----
    'faq_eyebrow': 'Antes de reservar', 'faq_h2': 'Las dudas que más me preguntan',
    'faq_sub': 'Si algo no está claro, escribime. Prefiero ayudarte a elegir bien antes que venderte cualquier cosa.',
    'faq_cta': '¿Te quedó una duda? Hablá conmigo por WhatsApp',
    'faq_wa_text': 'Hola, tengo una duda antes de reservar.',
    # ---- tour cards / tour page ----
    'tour_card_link': 'Ver tour y reservar →', 'quote_badge': 'Cotización personalizada',
    'quote_card_link': 'Pedir cotización →', 'quote_wa_prefix': '¡Hola! Quiero pedir una cotización para: ',
    'tour_includes_h2': 'Incluye', 'related_eyebrow': 'También te puede interesar', 'related_h2': 'Tours relacionados',
    'all_tours_title': 'Todos los tours — Mundo Caribe Tours',
    'all_tours_meta_desc': 'La lista completa de tours y excursiones de Mundo Caribe Tours en la Riviera Maya, agrupados por categoría.',
    'all_tours_h1': 'Todos los tours',
    'all_tours_desc_tpl': 'La lista completa, sin recortes — {n} tours con precio y detalle, más nuestras experiencias a cotizar.',
    'guides_title': 'Guías del Caribe — Mundo Caribe Tours',
    'guides_meta_desc': 'Guías reales de Agustín para elegir mejor tu experiencia en la Riviera Maya.',
    'guides_h1': 'Guías del Caribe',
    'guides_sub': 'Consejos y recomendaciones reales de Agustín para armar tu viaje por la Riviera Maya.',
    'guides_empty': 'Próximamente: guías reales para elegir mejor tu experiencia en Riviera Maya.',
    # ---- calendar / date picker ----
    'dp_choose_date': 'Elegí una fecha', 'dp_prev_month_aria': 'Mes anterior', 'dp_next_month_aria': 'Mes siguiente',
    'dp_weekdays': ['D', 'L', 'M', 'M', 'J', 'V', 'S'],
    'dp_tentative_prefix': 'Fecha tentativa: ', 'dp_selected_prefix': 'Fecha elegida: ',
    'dp_blocked_schedule': 'Ese día no está disponible para este tour.',
    'dp_blocked_past': 'Esa fecha ya pasó.',
    'dp_blocked_too_far': 'Las reservas se pueden hacer con hasta un mes de anticipación desde hoy. Para fechas más lejanas o si todavía no tenés fecha definida, <a href="#contacto">completá este formulario</a> y te ayudamos a planificar.',
    'months_long': ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'],
    'months_short': ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'],
    # ---- cart / checkout ----
    'cart_view_aria': 'Ver carrito de reserva', 'cart_title': 'Tu reserva', 'cart_close_aria': 'Cerrar',
    'cart_dialog_aria': 'Carrito de reserva',
    'cart_empty': 'Todavía no agregaste ningún tour. Elegí uno y tocá "Agregar al carrito" para armar tu reserva.',
    'cart_quote_label': 'A cotizar', 'cart_edit_btn': 'Editar', 'cart_remove_aria': 'Quitar',
    'cart_total_label': 'Total', 'cart_quote_suffix': ' + ítems a cotizar',
    'cart_zone_charge_note_tpl': 'Incluye {amount} de cargo adicional por ubicación.',
    'cart_card_surcharge_note': 'Incluye 5% de recargo por pago con tarjeta.',
    'cart_tentative_warning': '⚠️ Uno o más tours tienen fecha tentativa — Agustín confirma disponibilidad por WhatsApp.',
    'zone_field_label': 'Zona de recogida',
    'zone_price_note': 'Todos los precios publicados ya incluyen salida desde Playa del Carmen / Playacar.',
    'zone_help_note': '¿No sabés en qué zona está tu hotel? Elegí Playa del Carmen / Playacar. Si corresponde un cargo adicional por ubicación, te lo vamos a avisar por WhatsApp y esperamos tu confirmación antes de seguir con la reserva.',
    'zone_pdc_label': 'Playa del Carmen / Playacar', 'zone_cancun_label': 'Cancún',
    'zone_occidental_label': 'Hoteles Occidental/Xcaret hasta Tulum',
    'zone_costa_mujeres_label': 'Costa Mujeres / Puerto Juárez / Isla Blanca',
    'name_field_label': 'Nombre completo', 'name_field_placeholder': 'Nombre y apellido de quien reserva',
    'hotel_field_label': 'Hotel / lugar de hospedaje', 'hotel_field_placeholder': 'Ej: Hotel Grand Sirenis',
    'room_field_label': 'N° de habitación', 'room_field_placeholder': 'Ej: 204, o «Pendiente»',
    'room_pending': 'Pendiente',
    'share_location_btn': '📍 Compartir mi ubicación', 'location_added': '✓ Ubicación agregada',
    'location_searching': 'Buscando tu ubicación…',
    'location_unsupported': 'Tu navegador no permite compartir ubicación. Escribí el hotel arriba.',
    'location_error': 'No pudimos obtener tu ubicación. Escribí el nombre del hotel arriba, no hay problema.',
    'payment_field_label': 'Método de pago', 'review_cta_btn': 'Revisar y reservar',
    'clear_cart_btn': 'Vaciar carrito', 'clear_cart_confirm': '¿Vaciar todo el carrito?',
    'payment_recommended_badge': 'Recomendado',
    # ---- payment groups ----
    'pay_group_pay_on_tour_label': 'Pagar el día del tour',
    'pay_group_pay_on_tour_blurb': 'Reservá ahora y pagá el día del tour, cuando la transportación llegue al punto acordado.',
    'pay_opt_cash_mxn': 'Efectivo en pesos mexicanos', 'pay_opt_cash_usd': 'Efectivo en dólares estadounidenses',
    'pay_opt_card': 'Tarjeta Visa o Mastercard (+5% recargo)',
    'pay_group_transfer_label': 'Transferencia',
    'pay_group_transfer_blurb': 'Podés pagar por transferencia en pesos mexicanos, dólares estadounidenses, pesos argentinos, pesos colombianos o euros. Te enviamos por WhatsApp los datos correspondientes y, cuando haga falta convertir la moneda, la cotización vigente del día.',
    'pay_transfer_cond1': 'Los datos para realizar la transferencia se enviarán por WhatsApp.',
    'pay_transfer_cond2': 'Para continuar con la reserva, el pago debe aparecer acreditado en el estado de cuenta del operador.',
    'pay_transfer_cond3': 'El tour debe estar pagado al 100% antes de confirmar la reserva.',
    'pay_transfer_quote_cond1': 'La cotización proporcionada será válida únicamente durante ese día.',
    'pay_transfer_quote_cond2': 'La cotización corresponde solo a la conversión de moneda — no es un cargo adicional sobre el precio del tour.',
    'pay_opt_transfer_mxn': 'MXN — CLABE/SPEI', 'pay_opt_transfer_usd': 'USD — ACH o wire',
    'pay_opt_transfer_ars': 'ARS — pesos argentinos', 'pay_opt_transfer_cop': 'COP — pesos colombianos',
    'pay_opt_transfer_eur': 'EUR — SEPA',
    'pay_group_crypto_label': 'Criptomonedas',
    'pay_group_crypto_blurb': 'La dirección y la red para enviar el pago se comparten por WhatsApp.',
    'pay_crypto_cond1': 'La dirección y la red se proporcionarán por WhatsApp.',
    'pay_crypto_cond2': 'Se requiere recibir el 100% del pago antes de confirmar la reserva.',
    'pay_opt_btc': 'Bitcoin (BTC)', 'pay_opt_usdt': 'USDT', 'pay_opt_usdc': 'USDC',
    'pay_note_card': 'El tipo de cambio aplicado por tu banco puede variar.',
    'pay_note_btc': 'Te enviaremos por WhatsApp la dirección, la red y la cotización en BTC.',
    'pay_note_crypto_other': 'Te enviaremos por WhatsApp la dirección y la red — el monto a enviar es el mismo total en USD.',
    'pay_note_transfer_mxn': 'Te enviaremos por WhatsApp los datos para transferir (CLABE/SPEI).',
    'pay_note_transfer_other': 'Te enviaremos por WhatsApp los datos y la cotización correspondiente.',
    'pay_note_default': 'Coordinamos el pago para el día de la excursión, directo con Agustín.',
    # ---- review step ----
    'review_label': 'Revisá tu reserva antes de enviarla', 'review_name_label': 'Nombre:',
    'review_hotel_label': 'Hotel:', 'review_room_prefix': ' · Habitación ',
    'review_zone_label': 'Zona de recogida:',
    'review_zone_hint': 'Si tu hotel está fuera de la zona seleccionada y corresponde un cargo adicional por ubicación, te lo informaremos por WhatsApp. No continuaremos con la reserva sin tu confirmación.',
    'review_location_shared_label': 'Ubicación compartida:', 'review_location_shared_yes': 'sí',
    'review_payment_label': 'Método de pago:',
    'review_fineprint': 'Esto no confirma la reserva ni cobra nada — Agustín confirma disponibilidad y coordina el pago directo por WhatsApp.',
    'review_next_steps_title': 'Qué sigue:', 'review_next_step1': 'Agustín confirma cupo.',
    'review_next_step2': 'Coordinan método de pago.', 'review_next_step3': 'Recibís horario y punto de salida.',
    'review_send_btn': 'Enviar solicitud por WhatsApp', 'review_back_btn': '← Volver a editar',
    # ---- validation ----
    'error_missing_name': 'el nombre completo', 'error_missing_hotel': 'el hotel',
    'error_missing_room': 'el número de habitación (o escribí "Pendiente")',
    'error_missing_payment': 'el método de pago',
    'error_missing_tpl': 'Completá {fields} antes de reservar.',
    'error_invalid_tour_tpl': 'La fecha de "{name}" ya no es válida — abrí ese tour y elegí otra.',
    'error_invalid_tour_too_far_tpl': 'La fecha de "{name}" ya supera el máximo de un mes de anticipación. Abrí ese tour para elegir otra fecha, o <a href="#contacto">completá el formulario de contacto</a> si tu viaje es más adelante.',
    # ---- WhatsApp message ----
    'wa_greeting_tpl': 'Hola, me llamo {name} y quiero solicitar la reserva de los siguientes tours:',
    'wa_passengers_label': 'Pasajeros: ', 'wa_subtotal_label': 'Subtotal: ',
    'wa_hotel_label': 'Hotel: ', 'wa_room_label': 'Habitación: ',
    'wa_pickup_note': 'El horario de recogida y el punto de encuentro me serán enviados cuando la reserva quede confirmada.',
    'wa_disclaimer': 'Entiendo que esta solicitud todavía no constituye una reserva confirmada. La disponibilidad y los detalles del pago serán coordinados directamente por WhatsApp.',
    'wa_total_label': 'Total a pagar: ', 'wa_card_surcharge_note': ' (recargo del 5% ya incluido)',
    'wa_payment_method_label': 'Método de pago: ',
    'wa_note_transfer_mxn': 'Quedo a la espera de los datos para transferir (CLABE/SPEI) por WhatsApp.',
    'wa_note_transfer_other': 'Quedo a la espera de los datos y la cotización correspondiente por WhatsApp.',
    'wa_note_btc': 'Quedo a la espera de la dirección, la red y la cotización en BTC por WhatsApp.',
    'wa_note_crypto_other': 'Quedo a la espera de la dirección y la red por WhatsApp.',
    'wa_location_shared_label': 'Ubicación compartida: ',
    # ---- pluralization / lists / dates ----
    'plural_adult': {'one': '{n} adulto', 'other': '{n} adultos'},
    'plural_child': {'one': '{n} niño', 'other': '{n} niños'},
    'plural_person': {'one': '{n} persona', 'other': '{n} personas'},
    'plural_infant': {'one': '{n} infante', 'other': '{n} infantes'},
    'plural_passenger': {'one': '{n} pasajero', 'other': '{n} pasajeros'},
    'list_connector': 'y',
    'wa_pax_transport_suffix_tpl': ' — {n} pax para transporte',
    'date_not_chosen': 'Sin fecha elegida', 'date_tbd': 'Fecha a coordinar (sin días fijos)',
    'date_confirmed_prefix': 'Fecha: ', 'date_unspecified_short': 'A coordinar',
    'zone_charge_line_tpl': '+ {amount} de cargo adicional por ubicación ({pax})',
    # ---- booking widget ----
    'bw_quote_title': 'Pedí tu cotización', 'bw_book_title': 'Reservá este tour',
    'bw_price_adult_label': 'adulto', 'bw_price_child_label': 'niño',
    'bw_price_from_person': 'desde, por persona', 'bw_price_per_person': 'por persona',
    'bw_price_from_group_tpl': 'desde, por el grupo (hasta {n} personas)',
    'bw_price_per_group_tpl': 'por el grupo (hasta {n} personas)',
    'bw_date_tentative_label': 'Fecha tentativa', 'bw_date_preferred_label': 'Fecha preferida',
    'bw_tentative_note_generic_tpl': 'Este tour no tiene días fijos de operación{season} — la fecha queda sujeta a que Agustín confirme disponibilidad por WhatsApp.',
    'bw_tentative_note_season_tpl': ' (opera de {start} a {end})',
    'bw_zone_label': 'Zona de recogida', 'bw_duration_label': 'Duración', 'bw_option_label': 'Opción',
    'bw_per_person_suffix': '/persona',
    'bw_adults_label': 'Adultos', 'bw_adults_sub': '10 años en adelante',
    'bw_children_label': 'Niños', 'bw_children_sub': '3 a 9 años',
    'bw_persons_label': 'Personas', 'bw_passengers_label': 'Pasajeros',
    'bw_passengers_sub_tpl': 'Hasta {n} por embarcación',
    'bw_infants_label': 'Infantes', 'bw_infants_sub': '0 a 2 años · sin cargo, pero cuentan para el transporte',
    'bw_total_label': 'Total', 'bw_save_btn': 'Guardar cambios', 'bw_add_btn': '🛒 Agregar al carrito',
    'bw_saved_msg': '✓ Cambios guardados', 'bw_added_msg': '✓ Agregado al carrito',
    'bw_goto_cart_btn': 'Ver carrito y reservar →', 'bw_keep_browsing_btn': 'Seguir viendo tours',
    'bw_fineprint': 'Se coordina y confirma directo por WhatsApp con Agustín.',
    'bw_editing_banner': '✎ Estás editando este tour en tu carrito.', 'bw_cancel_edit': 'Cancelar',
    'bw_choose_valid_date_error': 'Elegí una fecha válida para este tour antes de agregar al carrito.',
    'counter_minus_aria': 'Restar', 'counter_plus_aria': 'Sumar',
}

UI['en'] = {
    'general_wa_text': "Hi, I'd like information about the tours.",
    'nav_tours': 'Tours', 'nav_guides': 'Guides', 'nav_contact': 'Contact',
    'nav_view_all_tours': 'See all tours', 'nav_open_menu_aria': 'Open menu',
    'nav_whatsapp_btn': 'WhatsApp', 'mobile_menu_wa_btn': 'Message us on WhatsApp',
    'lang_switch_aria': 'Language',
    'footer_cta_heading': "Let's plan your next trip?",
    'footer_cta_sub': "Message us and we'll coordinate everything on WhatsApp.",
    'footer_cta_btn': 'Message us on WhatsApp',
    'footer_handle_reviews': '⭐ Reviews on Google',
    'footer_location': 'Playa del Carmen, Riviera Maya',
    'breadcrumb_home': 'Home',
    # ---- future-trip / no-fixed-date contact form (WhatsApp-based) ----
    'future_form_heading': 'No exact dates yet, or is your trip further away?',
    'future_form_sub': 'Bookings can be made up to one month in advance. If you do not know your exact dates yet or your trip is further away, send us a WhatsApp message and we will help you plan.',
    'future_form_name_label': 'Name',
    'future_form_phone_label': 'WhatsApp / Phone',
    'future_form_email_label': 'Email',
    'future_form_date_label': 'Approximate travel date',
    'future_form_nodate_label': "I don't have a date yet",
    'future_form_tours_label': "Tours you're interested in",
    'future_form_tours_placeholder': 'E.g. Chichén Itzá, Holbox...',
    'future_form_message_label': 'Message (optional)',
    'future_form_submit': 'Send',
    'future_form_missing': 'Fill in your name and WhatsApp number before sending.',
    'future_form_opened': 'We opened WhatsApp with your message.',
    'future_form_nodate_value': 'no fixed date yet',
    'future_form_greeting_tpl': "Hi, my name is {name}. I don't have exact dates yet or my trip is further away — I'd like more information:",
    'future_form_phone_wa_label': 'WhatsApp/Phone',
    'future_form_email_wa_label': 'Email',
    'future_form_date_wa_label': 'Approximate date',
    'future_form_tours_wa_label': 'Tours of interest',
    'future_form_message_wa_label': 'Message',
    'future_form_disclaimer': "This isn't a confirmed booking or an automatic reminder — it's just the starting point to plan together over WhatsApp.",
    # ---- home ----
    'home_title': 'Mundo Caribe Tours — Tours and Excursions in the Riviera Maya',
    'home_desc': 'Tours and excursions in the Riviera Maya, coordinated directly over WhatsApp: cenotes, Mayan ruins, islands, and much more.',
    'hero_eyebrow': 'Riviera Maya, Mexico',
    'hero_h1': 'Experience the Mexican Caribbean to the fullest',
    'hero_lede': "I'm Agustín, from Argentina, and I've lived in the Riviera Maya for 6 years. I know every cenote, ruin, and island to help you plan the perfect trip.",
    'hero_btn_plan': 'Find your plan',
    'hero_btn_wa': 'Chat with me on WhatsApp',
    'hero_signal': '🤝 Coordinated directly with Agustín over WhatsApp',
    'hero_photo_alt': 'Bacalar Lagoon, Riviera Maya',
    'stories_label': 'Meet Agustín',
    'story_prev_aria': 'Previous story', 'story_next_aria': 'Next story', 'story_close_aria': 'Close',
    'planes_eyebrow': 'Choose your plan', 'planes_h2': 'What do you want to experience?',
    'planes_sub': "Tell me what interests you most and I'll take you straight to those tours.",
    'planes_view_tours': 'See tours →',
    'planes_wa_tile_h3': 'Not sure, you pick for me', 'planes_wa_tile_link': 'Chat on WhatsApp →',
    'planes_wa_text': "Hi! I'm not sure which tour to pick yet — could you recommend something based on what I'm looking for?",
    'featured_eyebrow': 'Featured', 'featured_h2': 'Our most popular tours',
    'featured_sub': 'Pick a tour to see the full details, price, and book directly on WhatsApp. Swipe to see more →',
    'special_eyebrow': 'Special services', 'special_h2': 'Everything you need for your trip',
    'special_view_more': 'See more →',
    'xcaret_quote_desc': 'México Park · Basic Xcaret ticket',
    # ---- reviews ----
    'reviews_eyebrow': 'Real reviews', 'reviews_h2': 'Hear it from those who already experienced the Caribbean',
    'reviews_sub': 'Real experiences from travelers who chose Mundo Caribe Tours.',
    'reviews_summary': '5.0 on Google · 5 reviews', 'reviews_cta': 'See all reviews on Google →',
    'reviews_source': 'Google review', 'reviews_stars_aria': 'Rating: 5 out of 5 stars',
    'reviews_group_aria': 'Customer reviews',
    'reviews_see_original': 'See original', 'reviews_view_translation': 'View English translation',
    # ---- faq ----
    'faq_eyebrow': 'Before you book', 'faq_h2': 'Frequently asked questions',
    'faq_sub': "If something isn't clear, message me. I'd rather help you choose well than just sell you something.",
    'faq_cta': 'Still have a question? Chat with me on WhatsApp',
    'faq_wa_text': 'Hi, I have a question before booking.',
    # ---- tour cards / tour page ----
    'tour_card_link': 'View tour and book →', 'quote_badge': 'Custom quote',
    'quote_card_link': 'Request a quote →', 'quote_wa_prefix': "Hi! I'd like a quote for: ",
    'tour_includes_h2': 'Included', 'related_eyebrow': 'You might also like', 'related_h2': 'Related tours',
    'all_tours_title': 'All Tours — Mundo Caribe Tours',
    'all_tours_meta_desc': 'The complete list of Mundo Caribe Tours tours and excursions in the Riviera Maya, grouped by category.',
    'all_tours_h1': 'All tours',
    'all_tours_desc_tpl': 'The complete list, no cuts — {n} tours with price and details, plus our quote-on-request experiences.',
    'guides_title': 'Caribbean Guides — Mundo Caribe Tours',
    'guides_meta_desc': "Real guides from Agustín to help you choose the best experience in the Riviera Maya.",
    'guides_h1': 'Caribbean Guides',
    'guides_sub': 'Real tips and recommendations from Agustín to help plan your trip through the Riviera Maya.',
    'guides_empty': 'Coming soon: real guides to help you choose the best experience in the Riviera Maya.',
    # ---- calendar / date picker ----
    'dp_choose_date': 'Choose a date', 'dp_prev_month_aria': 'Previous month', 'dp_next_month_aria': 'Next month',
    'dp_weekdays': ['S', 'M', 'T', 'W', 'T', 'F', 'S'],
    'dp_tentative_prefix': 'Tentative date: ', 'dp_selected_prefix': 'Selected date: ',
    'dp_blocked_schedule': "That day isn't available for this tour.",
    'dp_blocked_past': 'That date has already passed.',
    'dp_blocked_too_far': 'Bookings can be made up to one month ahead of today. For dates further out, or if you don’t have a fixed date yet, <a href="#contacto">fill out this form</a> and we’ll help you plan.',
    'months_long': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
    'months_short': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    # ---- cart / checkout ----
    'cart_view_aria': 'View booking cart', 'cart_title': 'Your booking', 'cart_close_aria': 'Close',
    'cart_dialog_aria': 'Booking cart',
    'cart_empty': 'You haven’t added any tours yet. Pick one and tap "Add to cart" to start your booking.',
    'cart_quote_label': 'Quote on request', 'cart_edit_btn': 'Edit', 'cart_remove_aria': 'Remove',
    'cart_total_label': 'Total', 'cart_quote_suffix': ' + items to quote',
    'cart_zone_charge_note_tpl': 'Includes {amount} in location surcharge.',
    'cart_card_surcharge_note': 'Includes a 5% card payment surcharge.',
    'cart_tentative_warning': '⚠️ One or more tours have a tentative date — Agustín confirms availability over WhatsApp.',
    'zone_field_label': 'Pickup zone',
    'zone_price_note': 'All published prices already include pickup from Playa del Carmen / Playacar.',
    'zone_help_note': "Not sure which zone your hotel is in? Choose Playa del Carmen / Playacar. If a location surcharge applies, we'll let you know over WhatsApp and wait for your confirmation before moving forward with the booking.",
    'zone_pdc_label': 'Playa del Carmen / Playacar', 'zone_cancun_label': 'Cancún',
    'zone_occidental_label': 'Occidental/Xcaret hotels through Tulum',
    'zone_costa_mujeres_label': 'Costa Mujeres / Puerto Juárez / Isla Blanca',
    'name_field_label': 'Full name', 'name_field_placeholder': 'First and last name of the person booking',
    'hotel_field_label': 'Hotel / place of stay', 'hotel_field_placeholder': 'E.g. Hotel Grand Sirenis',
    'room_field_label': 'Room number', 'room_field_placeholder': 'E.g. 204, or "Pending"',
    'room_pending': 'Pending',
    'share_location_btn': '📍 Share my location', 'location_added': '✓ Location added',
    'location_searching': 'Looking for your location…',
    'location_unsupported': "Your browser doesn't support sharing your location. Please type your hotel above.",
    'location_error': "We couldn't get your location. Just type your hotel name above, no problem.",
    'payment_field_label': 'Payment method', 'review_cta_btn': 'Review and book',
    'clear_cart_btn': 'Clear cart', 'clear_cart_confirm': 'Clear the entire cart?',
    'payment_recommended_badge': 'Recommended',
    # ---- payment groups ----
    'pay_group_pay_on_tour_label': 'Pay on the day of the tour',
    'pay_group_pay_on_tour_blurb': 'Book now and pay on the day of the tour, when transportation arrives at the agreed pickup point.',
    'pay_opt_cash_mxn': 'Cash in Mexican pesos', 'pay_opt_cash_usd': 'Cash in US dollars',
    'pay_opt_card': 'Visa or Mastercard (+5% surcharge)',
    'pay_group_transfer_label': 'Bank transfer',
    'pay_group_transfer_blurb': "You can pay by bank transfer in Mexican pesos, US dollars, Argentine pesos, Colombian pesos, or euros. We'll send you the details over WhatsApp and, whenever a currency conversion is needed, that day's exchange rate.",
    'pay_transfer_cond1': "The transfer details will be sent over WhatsApp.",
    'pay_transfer_cond2': "For the booking to proceed, the payment must show as cleared in the operator's account statement.",
    'pay_transfer_cond3': 'The tour must be paid in full before the booking is confirmed.',
    'pay_transfer_quote_cond1': 'The quote provided is valid only for that day.',
    'pay_transfer_quote_cond2': "The quote is only for the currency conversion — it's not an extra charge on the tour price.",
    'pay_opt_transfer_mxn': 'MXN — CLABE/SPEI', 'pay_opt_transfer_usd': 'USD — ACH or wire',
    'pay_opt_transfer_ars': 'ARS — Argentine pesos', 'pay_opt_transfer_cop': 'COP — Colombian pesos',
    'pay_opt_transfer_eur': 'EUR — SEPA',
    'pay_group_crypto_label': 'Cryptocurrency',
    'pay_group_crypto_blurb': 'The address and network to send the payment are shared over WhatsApp.',
    'pay_crypto_cond1': 'The address and network will be provided over WhatsApp.',
    'pay_crypto_cond2': '100% of the payment must be received before the booking is confirmed.',
    'pay_opt_btc': 'Bitcoin (BTC)', 'pay_opt_usdt': 'USDT', 'pay_opt_usdc': 'USDC',
    'pay_note_card': 'The exchange rate applied by your bank may vary.',
    'pay_note_btc': "We'll send you the address, network, and BTC quote over WhatsApp.",
    'pay_note_crypto_other': "We'll send you the address and network over WhatsApp — the amount to send is the same total in USD.",
    'pay_note_transfer_mxn': "We'll send you the transfer details (CLABE/SPEI) over WhatsApp.",
    'pay_note_transfer_other': "We'll send you the details and the corresponding quote over WhatsApp.",
    'pay_note_default': "We'll coordinate payment for the day of the tour, directly with Agustín.",
    # ---- review step ----
    'review_label': 'Review your booking before sending it', 'review_name_label': 'Name:',
    'review_hotel_label': 'Hotel:', 'review_room_prefix': ' · Room ',
    'review_zone_label': 'Pickup zone:',
    'review_zone_hint': "If your hotel is outside the selected zone and a location surcharge applies, we'll let you know over WhatsApp. We won't move forward with the booking without your confirmation.",
    'review_location_shared_label': 'Shared location:', 'review_location_shared_yes': 'yes',
    'review_payment_label': 'Payment method:',
    'review_fineprint': "This doesn't confirm the booking or charge anything — Agustín confirms availability and coordinates payment directly over WhatsApp.",
    'review_next_steps_title': "What's next:", 'review_next_step1': 'Agustín confirms availability.',
    'review_next_step2': 'You coordinate the payment method.', 'review_next_step3': "You'll receive the pickup time and location.",
    'review_send_btn': 'Send request via WhatsApp', 'review_back_btn': '← Back to edit',
    # ---- validation ----
    'error_missing_name': 'your full name', 'error_missing_hotel': 'the hotel',
    'error_missing_room': 'the room number (or type "Pending")',
    'error_missing_payment': 'the payment method',
    'error_missing_tpl': 'Please fill in {fields} before booking.',
    'error_invalid_tour_tpl': 'The date for "{name}" is no longer valid — open that tour and choose another.',
    'error_invalid_tour_too_far_tpl': 'The date for "{name}" is now beyond the one-month advance limit. Open that tour to pick another date, or <a href="#contacto">fill out the contact form</a> if your trip is further away.',
    # ---- WhatsApp message ----
    'wa_greeting_tpl': "Hi, my name is {name} and I'd like to request a booking for the following tours:",
    'wa_passengers_label': 'Passengers: ', 'wa_subtotal_label': 'Subtotal: ',
    'wa_hotel_label': 'Hotel: ', 'wa_room_label': 'Room: ',
    'wa_pickup_note': 'I understand the pickup time and meeting point will be sent to me once the booking is confirmed.',
    'wa_disclaimer': "I understand this request doesn't yet constitute a confirmed booking. Availability and payment details will be coordinated directly over WhatsApp.",
    'wa_total_label': 'Total to pay: ', 'wa_card_surcharge_note': ' (5% surcharge already included)',
    'wa_payment_method_label': 'Payment method: ',
    'wa_note_transfer_mxn': "I'll wait for the transfer details (CLABE/SPEI) over WhatsApp.",
    'wa_note_transfer_other': "I'll wait for the details and the corresponding quote over WhatsApp.",
    'wa_note_btc': "I'll wait for the address, network, and BTC quote over WhatsApp.",
    'wa_note_crypto_other': "I'll wait for the address and network over WhatsApp.",
    'wa_location_shared_label': 'Shared location: ',
    # ---- pluralization / lists / dates ----
    'plural_adult': {'one': '{n} adult', 'other': '{n} adults'},
    'plural_child': {'one': '{n} child', 'other': '{n} children'},
    'plural_person': {'one': '{n} person', 'other': '{n} people'},
    'plural_infant': {'one': '{n} infant', 'other': '{n} infants'},
    'plural_passenger': {'one': '{n} passenger', 'other': '{n} passengers'},
    'list_connector': 'and',
    'wa_pax_transport_suffix_tpl': ' — {n} pax for transportation',
    'date_not_chosen': 'No date chosen', 'date_tbd': 'Date to be arranged (no fixed days)',
    'date_confirmed_prefix': 'Date: ', 'date_unspecified_short': 'To be arranged',
    'zone_charge_line_tpl': '+ {amount} in location surcharge ({pax})',
    # ---- booking widget ----
    'bw_quote_title': 'Request your quote', 'bw_book_title': 'Book this tour',
    'bw_price_adult_label': 'adult', 'bw_price_child_label': 'child',
    'bw_price_from_person': 'from, per person', 'bw_price_per_person': 'per person',
    'bw_price_from_group_tpl': 'from, for the group (up to {n} people)',
    'bw_price_per_group_tpl': 'for the group (up to {n} people)',
    'bw_date_tentative_label': 'Tentative date', 'bw_date_preferred_label': 'Preferred date',
    'bw_tentative_note_generic_tpl': "This tour doesn't have fixed operating days{season} — the date is subject to Agustín confirming availability over WhatsApp.",
    'bw_tentative_note_season_tpl': ' (runs from {start} to {end})',
    'bw_zone_label': 'Pickup zone', 'bw_duration_label': 'Duration', 'bw_option_label': 'Option',
    'bw_per_person_suffix': '/person',
    'bw_adults_label': 'Adults', 'bw_adults_sub': 'Ages 10 and up',
    'bw_children_label': 'Children', 'bw_children_sub': 'Ages 3 to 9',
    'bw_persons_label': 'People', 'bw_passengers_label': 'Passengers',
    'bw_passengers_sub_tpl': 'Up to {n} per boat',
    'bw_infants_label': 'Infants', 'bw_infants_sub': 'Ages 0 to 2 · no charge, but counted for transportation',
    'bw_total_label': 'Total', 'bw_save_btn': 'Save changes', 'bw_add_btn': '🛒 Add to cart',
    'bw_saved_msg': '✓ Changes saved', 'bw_added_msg': '✓ Added to cart',
    'bw_goto_cart_btn': 'View cart and book →', 'bw_keep_browsing_btn': 'Keep browsing tours',
    'bw_fineprint': 'Coordinated and confirmed directly with Agustín over WhatsApp.',
    'bw_editing_banner': "✎ You're editing this tour in your cart.", 'bw_cancel_edit': 'Cancel',
    'bw_choose_valid_date_error': 'Choose a valid date for this tour before adding it to your cart.',
    'counter_minus_aria': 'Decrease', 'counter_plus_aria': 'Increase',
}

UI['es']['price_from'] = 'Desde'
UI['en']['price_from'] = 'From'
UI['es']['price_the_group'] = 'el grupo'
UI['en']['price_the_group'] = 'the group'
UI['es']['bw_zone_note_tpl'] = '+ {amount} de cargo adicional por ubicación ({pax}), ya incluido en el total.'
UI['en']['bw_zone_note_tpl'] = '+ {amount} in location surcharge ({pax}), already included in the total.'

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def wa_link(text):
    return 'https://wa.me/' + WA_NUMBER + '?text=' + urllib.parse.quote(text)


def usd(n):
    return '${:,.0f} USD'.format(n)


def T(lang, key, **kwargs):
    """Look up a UI string for `lang`, formatting any {placeholder} tokens
    via kwargs. THE single source of truth for every static/dynamic piece
    of chrome text on the site — see the UI dict above. assets/site.js
    reads the exact same dict (embedded as JSON, see render_i18n_script)
    instead of ever hardcoding a translatable string of its own."""
    value = UI[lang][key]
    return value.format(**kwargs) if kwargs else value


def tour_text(tour, field, lang):
    """Localized value of a translatable TOURS field — falls back to the
    Spanish source for lang=='es' or for any field with no EN override."""
    if lang == 'es':
        return tour.get(field)
    return TOURS_EN.get(tour['slug'], {}).get(field, tour.get(field))


def tour_tier_label(tour, index, lang):
    if lang == 'en':
        labels = TOURS_EN.get(tour['slug'], {}).get('tier_labels')
        if labels:
            return labels[index]
    return tour['pricing']['tiers'][index]['label']


def cat_text(cat, field, lang):
    if lang == 'es':
        return cat.get(field)
    return CATEGORIES_EN.get(cat['slug'], {}).get(field, cat.get(field))


def quote_items_for(cat_key, lang):
    items = QUOTE_ITEMS.get(cat_key, [])
    if lang == 'es':
        return items
    overrides = QUOTE_ITEMS_EN.get(cat_key, [])
    return [dict(item, **(overrides[i] if i < len(overrides) else {})) for i, item in enumerate(items)]


def faqs_for(lang):
    return FAQS if lang == 'es' else FAQS_EN


def path_tile_label(tile, lang):
    return tile['label'] if lang == 'es' else PATH_TILES_EN.get(tile['key'], tile['label'])


def category_tag_for(cat_key, lang):
    table = CATEGORY_TAG if lang == 'es' else CATEGORY_TAG_EN
    return table.get(cat_key)


def review_text(review, lang):
    return review['text'] if lang == 'es' else review.get('text_en', review['text'])


def story_alt(story, lang):
    if lang == 'en':
        return story.get('alt_en', story.get('alt', ''))
    return story.get('alt', '')


# Pickup-point tours (only pesca-yate-cancun today) store their departure
# point in the 'availability' field with a language-specific marker prefix
# instead of real operating days — this keeps that classification correct
# in either language without parsing the Spanish text at runtime.
PICKUP_PREFIX = {'es': 'Salida:', 'en': 'Departure:'}


def tour_schedule_bits(tour, lang):
    """Split a tour's localized 'availability' text back into (days,
    pickup) — never both, never invented. See PICKUP_PREFIX above."""
    avail = tour_text(tour, 'availability', lang)
    if not avail:
        return None, None
    prefix = PICKUP_PREFIX[lang]
    if avail.startswith(prefix):
        return None, avail[len(prefix):].strip()
    return avail, None


def price_summary(pricing, lang):
    t = pricing['type']
    if t == 'adult_child':
        return (usd(pricing['adult']) + ' ' + T(lang, 'bw_price_adult_label') + ' · ' +
                usd(pricing['child']) + ' ' + T(lang, 'bw_price_child_label'))
    if t == 'per_person':
        return usd(pricing['price']) + ' ' + T(lang, 'bw_price_per_person')
    if t == 'tiers':
        return T(lang, 'price_from') + ' ' + usd(min(x['price'] for x in pricing['tiers'])) + ' ' + T(lang, 'bw_price_per_person')
    if t == 'duration_group':
        return T(lang, 'price_from') + ' ' + usd(min(x['price'] for x in pricing['tiers'])) + ' ' + T(lang, 'price_the_group')
    return None


def write_file(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)


def U(path, lang):
    """Localized URL for an internal absolute path ('/', '/tour/foo/',
    '/#contacto', ...). Spanish is the site root, unprefixed — existing
    URLs never change. English mirrors the exact same tree under /en/.
    NEVER used for '/assets/...' — shared static files are identical for
    both languages and are never duplicated under /en/."""
    return path if lang == 'es' else '/en' + path


def out_file(path, lang):
    """Filesystem path (relative to ROOT) that U(path, lang) is served
    from as a static index.html file."""
    rel = path.strip('/')
    filename = (rel + '/index.html') if rel else 'index.html'
    return ('en/' + filename) if lang == 'en' else filename


def render_i18n_script(lang):
    """The single UI[lang] dict, embedded once per page as JSON — the only
    way assets/site.js ever sees translatable text (see initBooking,
    renderCartDrawer, etc. reading window.MC_I18N)."""
    return '<script type="application/json" id="mc-i18n">' + json.dumps(UI[lang], ensure_ascii=False) + '</script>'


def validate_translations():
    """Runs once at the top of main(). Raises loudly if any Spanish source
    text is missing its English counterpart, so untranslated copy can
    never silently ship on the English site."""
    errors = []
    if set(UI['es'].keys()) != set(UI['en'].keys()):
        errors.append('UI dict key mismatch: ' + str(set(UI['es']) ^ set(UI['en'])))
    tour_fields = ['name', 'desc', 'long_desc', 'duration', 'availability', 'tax', 'note']
    for tour in TOURS:
        overrides = TOURS_EN.get(tour['slug'])
        if not overrides:
            errors.append('TOURS_EN missing entry for slug=' + tour['slug'])
            continue
        for field in tour_fields:
            if tour.get(field) is not None and not overrides.get(field):
                errors.append('TOURS_EN[%s] missing field %r' % (tour['slug'], field))
        if tour.get('includes') and (not overrides.get('includes') or len(overrides['includes']) != len(tour['includes'])):
            errors.append('TOURS_EN[%s] includes length mismatch' % tour['slug'])
        if tour.get('schedule_note') and not overrides.get('schedule_note'):
            errors.append('TOURS_EN[%s] missing schedule_note' % tour['slug'])
        if tour['pricing']['type'] in ('tiers', 'duration_group'):
            labels = overrides.get('tier_labels')
            if not labels or len(labels) != len(tour['pricing']['tiers']):
                errors.append('TOURS_EN[%s] missing/incomplete tier_labels' % tour['slug'])
    for cat in CATEGORIES:
        if cat['slug'] not in CATEGORIES_EN:
            errors.append('CATEGORIES_EN missing entry for slug=' + cat['slug'])
    for key, items in QUOTE_ITEMS.items():
        overrides = QUOTE_ITEMS_EN.get(key)
        if not overrides or len(overrides) != len(items):
            errors.append('QUOTE_ITEMS_EN[%s] length mismatch' % key)
    if len(FAQS) != len(FAQS_EN):
        errors.append('FAQS_EN length mismatch')
    for review in REVIEWS:
        if not review.get('text_en'):
            errors.append('REVIEWS missing text_en for ' + review['name'])
    for tile in PATH_TILES:
        if tile['key'] not in PATH_TILES_EN:
            errors.append('PATH_TILES_EN missing key=' + tile['key'])
    for key in CATEGORY_TAG:
        if key not in CATEGORY_TAG_EN:
            errors.append('CATEGORY_TAG_EN missing key=' + key)
    if errors:
        raise SystemExit('Translation validation failed:\n' + '\n'.join('  - ' + e for e in errors))

# ---------------------------------------------------------------------------
# SHARED TEMPLATE PIECES
# ---------------------------------------------------------------------------

def render_head(lang, title, description, path, og_image=None):
    canonical = BASE_URL + U(path, lang)
    image = og_image or (BASE_URL + '/assets/og-card.jpg')
    other_lang = 'en' if lang == 'es' else 'es'
    alt_url_path = U(path, other_lang)
    hreflang_links = ''.join(
        f'<link rel="alternate" hreflang="{l}" href="{BASE_URL}{U(path, l)}">' for l in LANGS
    ) + f'<link rel="alternate" hreflang="x-default" href="{BASE_URL}{U(path, "es")}">'
    og_locale = 'es_MX' if lang == 'es' else 'en_US'
    # Blocking (no async/defer), placed before anything else in <head> so it
    # runs before the parser reaches <body> — a mismatched language never
    # gets a chance to paint, so there's no flash of the wrong language.
    # Manual selection (localStorage 'mc_lang', set by the ES/EN switcher in
    # render_nav) always wins over the navigator.language auto-detection;
    # with neither, English browsers land on English, everyone else on
    # Spanish. Wrapped in try/catch: if localStorage throws (private mode,
    # blocked storage), it just does nothing — the page still renders
    # correctly in whatever language its own URL already is.
    lang_detect_script = ('<script>(function(){try{var s=localStorage.getItem(\'mc_lang\');'
                           'var w=s||((navigator.language||\'\').toLowerCase().indexOf(\'en\')===0?\'en\':\'es\');'
                           'if(w!==' + json.dumps(lang) + '){location.replace(' + json.dumps(alt_url_path) + ');}'
                           '}catch(e){}})();</script>')
    return f'''<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{lang_detect_script}
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
{hreflang_links}

<link rel="icon" type="image/png" sizes="512x512" href="/assets/favicon-512.png">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png">

<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Mundo Caribe Tours">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="{og_locale}">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{image}">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Work+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
'''


def render_lang_switch(lang, path):
    """ES/EN links to this exact page's counterpart in the other language
    (never just the home page) — real <a> tags, so it works with no JS,
    keyboard, and screen readers alike. `aria-current` + a non-color style
    (see .lang-link.active in site.css) mark the active language; clicking
    either persists the choice via data-lang-link (see site.js), so manual
    selection always wins over auto-detection on future visits."""
    def link(l):
        active = ' active' if l == lang else ''
        current = 'true' if l == lang else 'false'
        return f'<a href="{U(path, l)}" data-lang-link="{l}" class="lang-link{active}" aria-current="{current}">{l.upper()}</a>'
    return f'<div class="lang-switch" role="group" aria-label="{T(lang, "lang_switch_aria")}">{link("es")}{link("en")}</div>'


def render_nav(lang, path):
    wa_text = T(lang, 'general_wa_text')
    cat_links = ''.join(
        f'<a href="{U("/categoria/" + c["slug"] + "/", lang)}">{cat_text(c, "title", lang)}</a>' for c in CATEGORIES
    )
    lang_switch = render_lang_switch(lang, path)
    return f'''<nav class="nav">
  <div class="container">
    <a class="brand" href="{U('/', lang)}"><img src="/assets/logo.webp" alt="Mundo Caribe Tours">Mundo Caribe Tours</a>
    <ul class="nav-links">
      <li class="nav-dropdown">
        <button class="nav-dropdown-trigger" type="button" aria-expanded="false" aria-haspopup="true">{T(lang, 'nav_tours')} <span class="nav-dropdown-caret">▾</span></button>
        <div class="nav-dropdown-menu">
          {cat_links}
          <div class="nav-dropdown-sep"></div>
          <a class="nav-dropdown-all" href="{U('/todos-los-tours/', lang)}">{T(lang, 'nav_view_all_tours')}</a>
        </div>
      </li>
      <li><a href="{U('/guias/', lang)}">{T(lang, 'nav_guides')}</a></li>
      <li><a href="{U('/#contacto', lang)}">{T(lang, 'nav_contact')}</a></li>
    </ul>
    <div class="nav-right">
      {lang_switch}
      <a class="btn-whatsapp" href="{wa_link(wa_text)}" target="_blank" rel="noopener">{T(lang, 'nav_whatsapp_btn')}</a>
      <button class="nav-burger" type="button" aria-label="{T(lang, 'nav_open_menu_aria')}" aria-expanded="false" aria-controls="mobile-menu">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
  <div id="mobile-menu" class="mobile-menu" hidden>
    <div class="container">
      <p class="mobile-menu-label">{T(lang, 'nav_tours')}</p>
      <div class="mobile-menu-cats">
        {cat_links}
      </div>
      <a class="mobile-menu-all" href="{U('/todos-los-tours/', lang)}">{T(lang, 'nav_view_all_tours')}</a>
      <div class="nav-dropdown-sep"></div>
      <a class="mobile-menu-link" href="{U('/guias/', lang)}">{T(lang, 'nav_guides')}</a>
      <a class="mobile-menu-link" href="{U('/#contacto', lang)}">{T(lang, 'nav_contact')}</a>
      {lang_switch}
      <a class="btn-whatsapp mobile-menu-wa" href="{wa_link(wa_text)}" target="_blank" rel="noopener">{T(lang, 'mobile_menu_wa_btn')}</a>
    </div>
  </div>
</nav>
'''


def render_footer(lang):
    """The 'future trip / no fixed date yet' form (retitled + rescoped
    2026-09-25, see the PR that added this) is a pure client-side WhatsApp
    composer now, not a Formspree POST — see initFutureTripForm() in
    site.js. `cf-nodate` lets a visitor explicitly say they don't know
    their dates yet without leaving the month field in some fake/guessed
    state."""
    return f'''<section id="contacto" class="reveal">
  <div class="container">
    <div class="cta-final">
      <h2>{T(lang, 'footer_cta_heading')}</h2>
      <p>{T(lang, 'footer_cta_sub')}</p>
      <a class="btn-primary" href="{wa_link(T(lang, 'general_wa_text'))}" target="_blank" rel="noopener">{T(lang, 'footer_cta_btn')}</a>
      <div class="handles">
        <a href="{INSTAGRAM_URL}" target="_blank" rel="noopener">@mundocaribetours</a>
        <a href="{FACEBOOK_URL}" target="_blank" rel="noopener">Facebook</a>
        <a href="{GOOGLE_MAPS_URL}" target="_blank" rel="noopener">{T(lang, 'footer_handle_reviews')}</a>
        <span>{T(lang, 'footer_location')}</span>
      </div>
    </div>

    <div class="contact-form-card">
      <h3>{T(lang, 'future_form_heading')}</h3>
      <p>{T(lang, 'future_form_sub')}</p>
      <form class="contact-form" id="mc-contact-form">
        <div class="booking-field">
          <label for="cf-name">{T(lang, 'future_form_name_label')}</label>
          <input type="text" id="cf-name" name="name" required>
        </div>
        <div class="booking-field-row">
          <div class="booking-field">
            <label for="cf-phone">{T(lang, 'future_form_phone_label')}</label>
            <input type="tel" id="cf-phone" name="phone" required>
          </div>
          <div class="booking-field">
            <label for="cf-email">{T(lang, 'future_form_email_label')}</label>
            <input type="email" id="cf-email" name="email">
          </div>
        </div>
        <div class="booking-field-row">
          <div class="booking-field">
            <label for="cf-date">{T(lang, 'future_form_date_label')}</label>
            <input type="month" id="cf-date" name="fecha_aproximada">
            <label class="contact-form-nodate"><input type="checkbox" id="cf-nodate"> {T(lang, 'future_form_nodate_label')}</label>
          </div>
          <div class="booking-field">
            <label for="cf-tours">{T(lang, 'future_form_tours_label')}</label>
            <input type="text" id="cf-tours" name="tours_interes" placeholder="{T(lang, 'future_form_tours_placeholder')}">
          </div>
        </div>
        <div class="booking-field">
          <label for="cf-message">{T(lang, 'future_form_message_label')}</label>
          <textarea id="cf-message" name="message" rows="3"></textarea>
        </div>
        <button class="btn-primary" type="submit">{T(lang, 'future_form_submit')}</button>
        <p class="contact-form-status" id="mc-contact-status" aria-live="polite"></p>
      </form>
    </div>
  </div>
</section>

<footer>
  <div class="container">
    <span>Mundo Caribe Tours</span>
  </div>
</footer>

{render_i18n_script(lang)}
<script src="/assets/site.js"></script>
'''


def render_breadcrumb(items):
    # items: list of (label, href_or_None) — labels/hrefs already localized by the caller
    parts = []
    for label, href in items:
        if href:
            parts.append(f'<a href="{href}">{label}</a>')
        else:
            parts.append(label)
    return '<div class="breadcrumb">' + ' / '.join(parts) + '</div>'


def page_shell(head, body, lang):
    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
{head}</head>
<body>
{body}
</body>
</html>
'''

# ---------------------------------------------------------------------------
# CARDS
# ---------------------------------------------------------------------------

def render_tour_card(tour, lang):
    photo_html = f'<img class="tour-card-photo" src="/assets/tours/{tour["photo"]}" alt="{tour_text(tour, "name", lang)}">' if tour.get('photo') else ''
    price = price_summary(tour['pricing'], lang)
    days, pickup = tour_schedule_bits(tour, lang)
    meta_bits = [f'<span>⏱ {tour_text(tour, "duration", lang)}</span>']
    if days:
        meta_bits.append(f'<span>📅 {days}</span>')
    if pickup:
        meta_bits.append(f'<span>📍 {pickup}</span>')
    tag = category_tag_for(tour['category'], lang)
    tag_html = f'<span class="card-tag">{tag}</span>' if tag else ''
    return f'''<a class="tour-card" href="{U('/tour/' + tour['slug'] + '/', lang)}">
        {photo_html}
        <div class="tour-card-body">
        <h3>{tour_text(tour, 'name', lang)}</h3>
        <p class="desc">{tour_text(tour, 'desc', lang)}</p>
        <div class="card-meta-row">{''.join(meta_bits)}</div>
        {tag_html}
        <div class="card-price">{price}</div>
        <span class="tour-link">{T(lang, 'tour_card_link')}</span>
        </div>
      </a>'''


def render_quote_card(item, lang):
    # `item` arrives already localized (see quote_items_for) — its own
    # name/desc are never re-looked-up here.
    return f'''<a class="tour-card" href="{wa_link(T(lang, 'quote_wa_prefix') + item['name'])}" target="_blank" rel="noopener">
        <div class="tour-card-body">
        <h3>{item['name']}</h3>
        <p class="desc">{item['desc']}</p>
        <span class="quote-badge">{T(lang, 'quote_badge')}</span>
        <span class="tour-link">{T(lang, 'quote_card_link')}</span>
        </div>
      </a>'''


def carousel_wrap(cards_html):
    return f'<div class="tour-carousel-wrap"><div class="tour-carousel">{cards_html}</div></div>'


def grid_wrap(cards_html):
    return f'<div class="tour-grid">{cards_html}</div>'


def cards_row(items, render_fn):
    """Render a row of cards as a draggable infinite carousel when there's
    enough of them to make one meaningful (2+), otherwise a plain grid."""
    html = ''.join(render_fn(i) for i in items)
    if len(items) >= 2:
        return carousel_wrap(html)
    return grid_wrap(html)


def category_cards_row(cat, lang):
    """Cards for a category as a draggable carousel (or plain grid, see cards_row)."""
    if cat['key'] in QUOTE_ITEMS:
        items = quote_items_for(cat['key'], lang)
        return cards_row(items, lambda item: render_quote_card(item, lang))
    tours_in_cat = [t for t in TOURS if t['category'] == cat['key']]
    return cards_row(tours_in_cat, lambda t: render_tour_card(t, lang))


def category_cards_plain(cat, lang):
    """Cards for a category as a plain (non-carousel) grid — used on the 'ver todos' page."""
    if cat['key'] in QUOTE_ITEMS:
        html = ''.join(render_quote_card(item, lang) for item in quote_items_for(cat['key'], lang))
    else:
        tours_in_cat = [t for t in TOURS if t['category'] == cat['key']]
        html = ''.join(render_tour_card(t, lang) for t in tours_in_cat)
    return grid_wrap(html)


def esc_attr(s):
    """Minimal HTML-attribute escaping for the few places (review toggle
    data-* attributes) where we embed longer free text inside a quoted
    HTML attribute rather than as element content."""
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')

# ---------------------------------------------------------------------------
# "CONOCÉ A AGUSTÍN" STORY VIEWER (home)
# ---------------------------------------------------------------------------

def render_agustin_stories(lang):
    """Entry ring + JSON payload for the story viewer. All viewer behavior
    lives in assets/site.js — this only ships the curated order, photo
    data, and this page's own localized `alt` text (tag labels are proper
    nouns/handles, identical in both languages, see story_alt())."""
    stories_json = json.dumps([
        {
            'src': '/assets/stories/' + s['file'],
            'type': s.get('type', 'photo'),
            'alt': story_alt(s, lang),
            'tag': s['tag'],
        }
        for s in AGUSTIN_STORIES
    ], ensure_ascii=False)
    first_photo = '/assets/stories/' + AGUSTIN_STORIES[0]['file']
    label = T(lang, 'stories_label')
    return f'''<section class="reveal mc-story-entry-section">
  <div class="container">
    <button type="button" id="mc-story-entry" class="mc-story-entry" aria-haspopup="dialog">
      <span class="mc-story-ring"><img src="{first_photo}" alt="" loading="lazy"></span>
      <span class="mc-story-entry-label">{label}</span>
    </button>
  </div>
</section>
<script type="application/json" id="agustin-stories-data">{stories_json}</script>
<div id="mc-story-overlay" class="mc-story-overlay" hidden role="dialog" aria-modal="true" aria-label="{label}">
  <div class="mc-story-bars" id="mc-story-bars"></div>
  <div class="mc-story-header">
    <span class="mc-story-header-name">{label}</span>
    <button type="button" class="mc-story-close" id="mc-story-close" aria-label="{T(lang, 'story_close_aria')}">×</button>
  </div>
  <div class="mc-story-media" id="mc-story-media">
    <img id="mc-story-img" src="" alt="">
    <video id="mc-story-video" autoplay muted playsinline preload="metadata" hidden></video>
    <a id="mc-story-hit" class="mc-story-hit" href="#" target="_blank" rel="noopener noreferrer" hidden></a>
    <button type="button" class="mc-story-nav mc-story-nav-prev" id="mc-story-prev" aria-label="{T(lang, 'story_prev_aria')}">‹</button>
    <button type="button" class="mc-story-nav mc-story-nav-next" id="mc-story-next" aria-label="{T(lang, 'story_next_aria')}">›</button>
  </div>
</div>'''


# ---------------------------------------------------------------------------
# GOOGLE REVIEWS (home)
# ---------------------------------------------------------------------------

def render_reviews_section(lang):
    """Native review cards, own continuous-loop carousel (see
    .review-carousel-wrap in site.css / initReviewsCarousel in site.js).
    Spanish shows the original text verbatim, no toggle at all. English
    shows the human-authored translation (text_en) by default, with a
    "See original"/"View English translation" button that swaps the text
    in place, client-side, no reload. Wired via data-review-idx (never an
    `id`) so the carousel's cloned card sets (aria-hidden, several copies
    per review for the infinite loop) can never produce duplicate IDs;
    toggling any copy updates every copy sharing that index at once (see
    site.js), so a clone that scrolls into view later always matches."""
    def render_review_card(item, idx):
        shown = review_text(item, lang)
        toggle_html = ''
        if lang == 'en':
            toggle_html = (
                f'<button type="button" class="review-toggle" data-review-idx="{idx}" data-state="translated" '
                f'data-original="{esc_attr(item["text"])}" data-translated="{esc_attr(item["text_en"])}" '
                f'data-label-original="{esc_attr(T(lang, "reviews_see_original"))}" '
                f'data-label-translated="{esc_attr(T(lang, "reviews_view_translation"))}">{T(lang, "reviews_see_original")}</button>'
            )
        return f'''<div class="tour-card review-card">
        <div class="review-stars" role="img" aria-label="{T(lang, 'reviews_stars_aria')}">★★★★★</div>
        <p class="review-quote" data-review-idx="{idx}">“{shown}”</p>
        {toggle_html}
        <div class="review-footer">
          <span class="review-avatar" aria-hidden="true">{item['initials']}</span>
          <div>
            <span class="review-name">{item['name']}</span>
            <span class="review-source">{T(lang, 'reviews_source')}</span>
          </div>
        </div>
      </div>'''

    cards_html = ''.join(render_review_card(r, i) for i, r in enumerate(REVIEWS))

    return f'''<section id="resenas" class="reveal">
  <div class="container">
    <div class="section-head">
      <p class="eyebrow">{T(lang, 'reviews_eyebrow')}</p>
      <h2>{T(lang, 'reviews_h2')}</h2>
      <p>{T(lang, 'reviews_sub')}</p>
      <p class="review-summary"><span aria-hidden="true">★</span> {T(lang, 'reviews_summary')}</p>
      <a class="btn-secondary review-cta" href="{GOOGLE_REVIEWS_URL}" target="_blank" rel="noopener noreferrer">{T(lang, 'reviews_cta')}</a>
    </div>
    <div class="review-carousel-wrap" id="review-carousel-wrap" tabindex="0" role="group" aria-roledescription="carrusel" aria-label="{T(lang, 'reviews_group_aria')}">
      <div class="review-carousel">
        {cards_html}
      </div>
    </div>
  </div>
</section>'''


# ---------------------------------------------------------------------------
# TRAVELAGENCY STRUCTURED DATA (home)
# ---------------------------------------------------------------------------

def render_travel_agency_jsonld(lang):
    telephone = '+52 ' + WA_NUMBER[2:5] + ' ' + WA_NUMBER[5:8] + ' ' + WA_NUMBER[8:]
    data = {
        '@context': 'https://schema.org',
        '@type': 'TravelAgency',
        'name': 'Mundo Caribe Tours',
        'url': BASE_URL + U('/', lang),
        'telephone': telephone,
        'address': {
            '@type': 'PostalAddress',
            'addressLocality': 'Playa del Carmen',
            'addressRegion': 'Quintana Roo',
            'addressCountry': 'MX',
        },
        'sameAs': [INSTAGRAM_URL, FACEBOOK_URL, GOOGLE_MAPS_URL],
    }
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


# ---------------------------------------------------------------------------
# FAQ (home, between "Servicios especiales" and contacto)
# ---------------------------------------------------------------------------

def render_faq_section(lang):
    """Accessible accordion — toggled open/closed in assets/site.js.
    FAQPage JSON-LD is generated from the exact same (localized) list as
    the visible markup, so the structured data can never say something
    the page doesn't, in either language."""
    faqs = faqs_for(lang)
    items_html = ''
    for i, item in enumerate(faqs):
        q_id = f'faq-q-{i}'
        a_id = f'faq-a-{i}'
        items_html += f'''<div class="faq-item">
        <h3 class="faq-question">
          <button type="button" class="faq-trigger" id="{q_id}" aria-expanded="false" aria-controls="{a_id}">
            <span>{item['q']}</span>
            <span class="faq-icon" aria-hidden="true"></span>
          </button>
        </h3>
        <div class="faq-answer" id="{a_id}" role="region" aria-labelledby="{q_id}" hidden>
          <p>{item['a']}</p>
        </div>
      </div>'''

    faq_jsonld = json.dumps({
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [
            {
                '@type': 'Question',
                'name': item['q'],
                'acceptedAnswer': {'@type': 'Answer', 'text': item['a']},
            }
            for item in faqs
        ],
    }, ensure_ascii=False)

    return f'''<section id="faq" class="reveal">
  <div class="container">
    <div class="section-head">
      <p class="eyebrow">{T(lang, 'faq_eyebrow')}</p>
      <h2>{T(lang, 'faq_h2')}</h2>
      <p>{T(lang, 'faq_sub')}</p>
    </div>
    <div class="faq-list">
      {items_html}
    </div>
    <p class="faq-cta">
      <a href="{wa_link(T(lang, 'faq_wa_text'))}" target="_blank" rel="noopener">{T(lang, 'faq_cta')}</a>
    </p>
  </div>
</section>
<script type="application/ld+json">{faq_jsonld}</script>'''

# ---------------------------------------------------------------------------
# HOMEPAGE
# ---------------------------------------------------------------------------

def render_home(lang):
    title = T(lang, 'home_title')
    desc = T(lang, 'home_desc')
    head = render_head(lang, title, desc, '/')

    featured_cards_html = ''.join(render_tour_card(TOUR_BY_SLUG[s], lang) for s in FEATURED_SLUGS)
    xcaret_quote_card_html = render_quote_card({'name': 'Xcaret', 'desc': T(lang, 'xcaret_quote_desc')}, lang)
    featured_row = carousel_wrap(featured_cards_html + xcaret_quote_card_html)

    path_tiles_html = ''.join(f'''<a class="path-tile" href="{U(t['href'], lang)}">
        <img src="/assets/tours/{t['photo']}" alt="{path_tile_label(t, lang)}">
        <div class="path-tile-label">
          <h3>{path_tile_label(t, lang)}</h3>
          <span>{T(lang, 'planes_view_tours')}</span>
        </div>
      </a>''' for t in PATH_TILES)
    whatsapp_tile_html = f'''<a class="path-tile path-tile-whatsapp" href="{wa_link(T(lang, 'planes_wa_text'))}" target="_blank" rel="noopener">
        <div class="path-tile-label">
          <h3>{T(lang, 'planes_wa_tile_h3')}</h3>
          <span>{T(lang, 'planes_wa_tile_link')}</span>
        </div>
      </a>'''
    path_selector = f'''<section id="planes" class="reveal">
  <div class="container">
    <div class="section-head">
      <p class="eyebrow">{T(lang, 'planes_eyebrow')}</p>
      <h2>{T(lang, 'planes_h2')}</h2>
      <p>{T(lang, 'planes_sub')}</p>
    </div>
    <div class="path-grid">
      {path_tiles_html}
      {whatsapp_tile_html}
    </div>
  </div>
</section>'''

    special_items = []
    for key in ['pesca', 'xcaret', 'transportes', 'vuelos']:
        cat = CAT_BY_KEY[key]
        href = U('/tour/pesca-yate-cancun/', lang) if key == 'pesca' else U(f'/categoria/{cat["slug"]}/', lang)
        special_items.append((cat, href))

    def render_special_card(item):
        cat, href = item
        return f'''<div class="tour-card">
        <div class="tour-card-body">
        <h3>{cat_text(cat, 'title', lang)}</h3>
        <p class="desc">{cat_text(cat, 'card_desc', lang)}</p>
        <a class="tour-link" href="{href}">{T(lang, 'special_view_more')}</a>
        </div>
      </div>'''

    special_row = cards_row(special_items, render_special_card)

    body = render_nav(lang, '/') + f'''
<section class="hero">
  <div class="container">
    <div class="hero-copy">
      <p class="hero-eyebrow">{T(lang, 'hero_eyebrow')}</p>
      <h1>{T(lang, 'hero_h1')}</h1>
      <p class="lede">{T(lang, 'hero_lede')}</p>
      <div class="hero-actions">
        <a class="btn-primary" href="#planes">{T(lang, 'hero_btn_plan')}</a>
        <a class="btn-secondary" href="{wa_link(T(lang, 'general_wa_text'))}" target="_blank" rel="noopener">{T(lang, 'hero_btn_wa')}</a>
      </div>
      <p class="hero-signal">{T(lang, 'hero_signal')}</p>
    </div>
    <div class="hero-photo">
      <img src="/assets/tours/bacalar.jpg" alt="{T(lang, 'hero_photo_alt')}" loading="eager">
    </div>
  </div>
</section>

{render_agustin_stories(lang)}

{path_selector}

<section id="tours" class="reveal">
  <div class="container">
    <div class="section-head">
      <p class="eyebrow">{T(lang, 'featured_eyebrow')}</p>
      <h2>{T(lang, 'featured_h2')}</h2>
      <p>{T(lang, 'featured_sub')}</p>
    </div>
    {featured_row}
  </div>
</section>

{render_reviews_section(lang)}

<section class="reveal">
  <div class="container">
    <div class="section-head">
      <p class="eyebrow">{T(lang, 'special_eyebrow')}</p>
      <h2>{T(lang, 'special_h2')}</h2>
    </div>
    {special_row}
  </div>
</section>

{render_faq_section(lang)}

{render_travel_agency_jsonld(lang)}
''' + render_footer(lang)

    write_file(out_file('/', lang), page_shell(head, body, lang))

# ---------------------------------------------------------------------------
# CATEGORY PAGES
# ---------------------------------------------------------------------------

def render_category_page(cat, lang):
    title = f'{cat_text(cat, "title", lang)} — Mundo Caribe Tours'
    desc = cat_text(cat, 'intro', lang)
    path = f'/categoria/{cat["slug"]}/'
    head = render_head(lang, title, desc, path)

    row = category_cards_row(cat, lang)

    body = render_nav(lang, path) + f'''
<section class="category-hero reveal">
  <div class="container">
    {render_breadcrumb([(T(lang, 'breadcrumb_home'), U('/', lang)), (cat_text(cat, 'title', lang), None)])}
    <h1>{cat_text(cat, 'title', lang)}</h1>
    <p>{cat_text(cat, 'intro', lang)}</p>
  </div>
</section>
<section class="reveal">
  <div class="container">
    {row}
  </div>
</section>
''' + render_footer(lang)

    write_file(out_file(path, lang), page_shell(head, body, lang))


# ---------------------------------------------------------------------------
# TOUR PAGES
# ---------------------------------------------------------------------------

def render_tour_page(tour, lang):
    cat = CAT_BY_KEY[tour['category']]
    name = tour_text(tour, 'name', lang)
    title = f'{name} — Mundo Caribe Tours'
    desc = tour_text(tour, 'desc', lang)
    path = f'/tour/{tour["slug"]}/'
    og_image = (BASE_URL + f'/assets/tours/{tour["photo"]}') if tour.get('photo') else None
    head = render_head(lang, title, desc, path, og_image)

    photo_html = f'<img class="tour-hero-photo" src="/assets/tours/{tour["photo"]}" alt="{name}">' if tour.get('photo') else ''

    includes = tour_text(tour, 'includes', lang) or tour['includes']
    includes_html = ''.join(f'<li>{i}</li>' for i in includes)

    notes_html = ''
    tax = tour_text(tour, 'tax', lang)
    note = tour_text(tour, 'note', lang)
    if tax:
        notes_html += f'<div class="info-note warn">{tax}</div>'
    if note:
        notes_html += f'<div class="info-note">{note}</div>'
    if tour.get('snorkel'):
        notes_html += f'<div class="info-note">{SNORKEL_AGE_NOTE if lang == "es" else SNORKEL_AGE_NOTE_EN}</div>'
    if tour['pricing']['type'] == 'adult_child':
        notes_html += f'<div class="info-note">{GENERAL_AGE_NOTE if lang == "es" else GENERAL_AGE_NOTE_EN}</div>'

    others = [t for t in TOURS if t['category'] == tour['category'] and t['slug'] != tour['slug']][:3]
    related_html = ''
    if others:
        related_cards = ''.join(render_tour_card(t, lang) for t in others)
        related_html = f'''
<section class="reveal">
  <div class="container">
    <div class="section-head">
      <p class="eyebrow">{T(lang, 'related_eyebrow')}</p>
      <h2>{T(lang, 'related_h2')}</h2>
    </div>
    <div class="tour-grid">
      {related_cards}
    </div>
  </div>
</section>
'''

    # pricing_json bridges Python -> JS (see #tour-pricing / initBooking).
    # Tier labels are baked in the page's own language here; everything
    # else in `pricing` (numbers, type) is language-agnostic business data.
    pricing = dict(tour['pricing'])
    if 'tiers' in pricing:
        pricing = dict(pricing, tiers=[
            dict(t, label=tour_tier_label(tour, i, lang)) for i, t in enumerate(pricing['tiers'])
        ])
    schedule_note = tour_text(tour, 'schedule_note', lang) if tour.get('schedule_note') else None
    pricing_json = json.dumps(dict(
        pricing, name=name,
        schedule=tour['schedule'],
        scheduleNote=schedule_note,
        zoneExempt=tour['slug'] in ZONE_EXEMPT_SLUGS,
        zone3SurchargeMXN=ZONE3_SURCHARGES_MXN.get(tour['slug']),
    ), ensure_ascii=False)

    body = render_nav(lang, path) + f'''
<section class="reveal">
  <div class="container">
    {render_breadcrumb([(T(lang, 'breadcrumb_home'), U('/', lang)), (cat_text(cat, 'title', lang), U(f'/categoria/{cat["slug"]}/', lang)), (name, None)])}
    {photo_html}
    <div class="tour-page-grid">
      <div>
        <h1 class="tour-title">{name}</h1>
        <div class="tour-meta-row">
          <span>⏱ {tour_text(tour, 'duration', lang)}</span>
          <span>📅 {tour_text(tour, 'availability', lang)}</span>
        </div>
        <p class="tour-longdesc">{tour_text(tour, 'long_desc', lang)}</p>

        <h2 class="tour-section-title">{T(lang, 'tour_includes_h2')}</h2>
        <ul class="includes-list">{includes_html}</ul>
        {notes_html}
      </div>
      <div>
        <div class="booking-widget" id="booking-widget"></div>
        <script type="application/json" id="tour-pricing">{pricing_json}</script>
      </div>
    </div>
  </div>
</section>
{related_html}
''' + render_footer(lang)

    write_file(out_file(path, lang), page_shell(head, body, lang))

def render_all_tours_page(lang):
    title = T(lang, 'all_tours_title')
    total_items = len(TOURS) + sum(len(v) for v in QUOTE_ITEMS.values())
    desc = T(lang, 'all_tours_meta_desc')
    path = '/todos-los-tours/'
    head = render_head(lang, title, desc, path)

    # IMPORTANT: each category group gets its OWN .reveal — never wrap the
    # whole (very tall) list in a single .reveal (see initReveal in
    # site.js — a threshold-based IntersectionObserver can never reach a
    # fixed ratio on a section taller than roughly viewport/threshold).
    groups_html = ''
    for cat in CATEGORIES:
        groups_html += f'''
<div class="all-tours-group reveal">
  <h2>{cat_text(cat, 'title', lang)}</h2>
  {category_cards_plain(cat, lang)}
</div>
'''

    body = render_nav(lang, path) + f'''
<section class="category-hero reveal">
  <div class="container">
    {render_breadcrumb([(T(lang, 'breadcrumb_home'), U('/', lang)), (T(lang, 'all_tours_h1'), None)])}
    <h1>{T(lang, 'all_tours_h1')}</h1>
    <p>{T(lang, 'all_tours_desc_tpl', n=total_items)}</p>
  </div>
</section>
<section>
  <div class="container">
    {groups_html}
  </div>
</section>
''' + render_footer(lang)

    write_file(out_file(path, lang), page_shell(head, body, lang))


# ---------------------------------------------------------------------------
# "GUÍAS DEL CARIBE" (blog base, added 2026-09-11) — empty on purpose, see
# the original schema note in project history. A real guide's translatable
# fields follow the same convention as AGUSTIN_STORIES: an optional
# '<field>_en' key read by guide_text() below; nothing invented here since
# GUIDES has no real content yet.
# ---------------------------------------------------------------------------
GUIDES = []


def guide_text(guide, field, lang):
    if lang == 'en' and guide.get(field + '_en'):
        return guide[field + '_en']
    return guide.get(field)


def render_guide_card(guide, lang):
    return f'''<a class="tour-card guide-card" href="{U('/guias/' + guide['slug'] + '/', lang)}">
        <img class="tour-card-photo" src="/assets/guias/{guide['image']}" alt="{guide_text(guide, 'title', lang)}" loading="lazy">
        <div class="tour-card-body">
        <span class="card-meta">{guide_text(guide, 'category', lang)}</span>
        <h3>{guide_text(guide, 'title', lang)}</h3>
        <p class="desc">{guide_text(guide, 'description', lang)}</p>
        </div>
      </a>'''


def render_guides_index(lang):
    title = T(lang, 'guides_title')
    desc = T(lang, 'guides_meta_desc')
    path = '/guias/'
    head = render_head(lang, title, desc, path)

    if GUIDES:
        content = grid_wrap(''.join(render_guide_card(g, lang) for g in GUIDES))
    else:
        content = f'''<div class="guides-empty reveal">
          <p>{T(lang, 'guides_empty')}</p>
        </div>'''

    body = render_nav(lang, path) + f'''
<section class="category-hero reveal">
  <div class="container">
    {render_breadcrumb([(T(lang, 'breadcrumb_home'), U('/', lang)), (T(lang, 'guides_h1'), None)])}
    <h1>{T(lang, 'guides_h1')}</h1>
    <p>{T(lang, 'guides_sub')}</p>
  </div>
</section>
<section class="reveal">
  <div class="container">
    {content}
  </div>
</section>
''' + render_footer(lang)

    write_file(out_file(path, lang), page_shell(head, body, lang))


def render_guide_page(guide, lang):
    """Renders one guide/article page. Not called on any real content yet
    (GUIDES is empty) — kept ready for the day a real guide is added."""
    seo = guide.get('seo') or {}
    title = seo.get('title') or f'{guide_text(guide, "title", lang)} — Mundo Caribe Tours'
    desc = seo.get('description') or guide_text(guide, 'description', lang)
    path = f'/guias/{guide["slug"]}/'
    og_image = BASE_URL + f'/assets/guias/{guide["image"]}'
    head = render_head(lang, title, desc, path, og_image=og_image)

    body = render_nav(lang, path) + f'''
<section class="category-hero reveal">
  <div class="container">
    {render_breadcrumb([(T(lang, 'breadcrumb_home'), U('/', lang)), (T(lang, 'guides_h1'), U('/guias/', lang)), (guide_text(guide, 'title', lang), None)])}
    <p class="guide-meta">{guide_text(guide, 'category', lang)} · {guide['date']}</p>
    <h1>{guide_text(guide, 'title', lang)}</h1>
  </div>
</section>
<section class="reveal">
  <div class="container guide-article">
    <img class="guide-hero-photo" src="/assets/guias/{guide['image']}" alt="{guide_text(guide, 'title', lang)}">
    {guide_text(guide, 'content_html', lang)}
  </div>
</section>
''' + render_footer(lang)

    write_file(out_file(path, lang), page_shell(head, body, lang))


# ---------------------------------------------------------------------------
# SITEMAP & ROBOTS.TXT
# ---------------------------------------------------------------------------

def sitemap_paths():
    """Every real canonical (language-neutral) URL the generator emits,
    built from the same source lists as the pages themselves so it can
    never drift out of sync when a tour/category/guide is added/removed."""
    paths = ['/', '/todos-los-tours/', '/guias/']
    paths += [f'/categoria/{c["slug"]}/' for c in CATEGORIES]
    paths += [f'/tour/{t["slug"]}/' for t in TOURS]
    paths += [f'/guias/{g["slug"]}/' for g in GUIDES]
    return paths


def render_sitemap():
    """One <url> entry per (path, language) pair, each annotated with
    xhtml:link rel="alternate" hreflang entries pointing at its
    counterpart in every language plus x-default — the standard way to
    tell search engines two URLs are translations of the same page rather
    than duplicate content. No lastmod/priority: no real per-page dates."""
    entries = []
    for p in sitemap_paths():
        alts = ''.join(
            f'    <xhtml:link rel="alternate" hreflang="{l}" href="{BASE_URL}{U(p, l)}"/>\n' for l in LANGS
        )
        alts += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{BASE_URL}{U(p, "es")}"/>\n'
        for lang in LANGS:
            entries.append(f'  <url>\n    <loc>{BASE_URL}{U(p, lang)}</loc>\n{alts}  </url>\n')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + ''.join(entries) +
           '</urlset>\n')
    write_file('sitemap.xml', xml)


def render_robots():
    robots = ('User-agent: *\n'
              'Allow: /\n'
              '\n'
              f'Sitemap: {BASE_URL}/sitemap.xml\n')
    write_file('robots.txt', robots)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    validate_translations()
    for lang in LANGS:
        render_home(lang)
        for cat in CATEGORIES:
            render_category_page(cat, lang)
        for tour in TOURS:
            render_tour_page(tour, lang)
        render_all_tours_page(lang)
        render_guides_index(lang)
        for guide in GUIDES:
            render_guide_page(guide, lang)
    render_sitemap()
    render_robots()
    print(f'Generated ({"+".join(LANGS)}): 1 home + {len(CATEGORIES)} category pages + {len(TOURS)} tour pages + '
          f'1 all-tours page + 1 guides index + {len(GUIDES)} guide pages, per language, + sitemap.xml + robots.txt')


if __name__ == '__main__':
    main()
