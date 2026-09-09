#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static site generator for Mundo Caribe Tours.
Reads the DATA below (single source of truth) and emits:
  index.html
  categoria/<slug>/index.html   (one per category)
  tour/<slug>/index.html        (one per tour that has its own page)
Shared assets: assets/site.css, assets/site.js, assets/*.png/webp/jpg
Run from the project root: python3 scripts/generate_site.py
"""
import os
import json
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = 'https://mundo-caribe-tours.ignacioagustindannunzio.workers.dev'
WA_NUMBER = '529841191147'

GENERAL_AGE_NOTE = 'Edades: infantes de 0 a 2 años (sin cargo), niños de 3 a 9 años, adultos desde 10 años en adelante.'
SNORKEL_AGE_NOTE = 'Para hacer snorkel: edad mínima 8 años, edad máxima 65 años.'

INSTAGRAM_URL = 'https://www.instagram.com/mundocaribetours'
GOOGLE_MAPS_URL = 'https://share.google/n1J6T9x87tUbbPaJm'
FACEBOOK_URL = 'https://www.facebook.com/people/Mundo-Caribe-Tours/61569544733150/'
# For travelers planning ahead (trip ~1-3 months out) who aren't ready to
# book specific dates/headcounts via the WhatsApp widget yet — a lighter
# lead-capture form, emailed via Formspree (no backend needed).
FORMSPREE_URL = 'https://formspree.io/f/xljeapok'

# ---------------------------------------------------------------------------
# DATA
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
TOURS = [
    {
        'slug': 'chichen-itza', 'category': 'ruinas', 'photo': 'chichen-itza.jpg',
        'name': 'Chichén Itzá – Historia, Naturaleza y Cultura',
        'desc': 'Guía certificado, cenote Oxman y tiempo libre en Valladolid, Pueblo Mágico.',
        'long_desc': "Descubre la grandeza de Chichén Itzá con un guía certificado, refréscate en el impresionante cenote Oxman y explora las calles coloridas de Valladolid, un Pueblo Mágico lleno de historia y tradición.",
        'duration': '12 horas aprox.', 'availability': 'Consulta disponibilidad',
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
        'duration': '12 horas aprox.', 'availability': 'Consulta disponibilidad',
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
        'long_desc': "Explora Akumal, una de las pocas playas hoy libres de sargazo, donde podrás nadar con tortugas marinas en aguas claras y turquesas, y luego disfruta de la belleza del Cenote Nohoch, una caverna mística con aguas cristalinas, zona de descanso con hamacas y un buffet regional delicioso.",
        'duration': '7-8 horas aprox.', 'availability': 'Consulta disponibilidad',
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

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def wa_link(text):
    return 'https://wa.me/' + WA_NUMBER + '?text=' + urllib.parse.quote(text)


def usd(n):
    return '${:,.0f} USD'.format(n)


def price_summary(pricing):
    t = pricing['type']
    if t == 'adult_child':
        return usd(pricing['adult']) + ' adulto · ' + usd(pricing['child']) + ' niño'
    if t == 'per_person':
        return usd(pricing['price']) + ' por persona'
    if t == 'tiers':
        return 'Desde ' + usd(min(x['price'] for x in pricing['tiers'])) + ' por persona'
    if t == 'duration_group':
        return 'Desde ' + usd(min(x['price'] for x in pricing['tiers'])) + ' el grupo'
    return None


def write_file(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)


# ---------------------------------------------------------------------------
# SHARED TEMPLATE PIECES
# ---------------------------------------------------------------------------

def render_head(title, description, path, og_image=None):
    canonical = BASE_URL + path
    image = og_image or (BASE_URL + '/assets/og-card.jpg')
    return f'''<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">

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
<meta property="og:locale" content="es_MX">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{image}">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Work+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
'''


def render_nav():
    wa_text = 'Hola, quisiera información sobre los tours.'
    cat_links = ''.join(
        f'<a href="/categoria/{c["slug"]}/">{c["title"]}</a>' for c in CATEGORIES
    )
    return f'''<nav class="nav">
  <div class="container">
    <a class="brand" href="/"><img src="/assets/logo.webp" alt="Mundo Caribe Tours">Mundo Caribe Tours</a>
    <ul class="nav-links">
      <li class="nav-dropdown">
        <button class="nav-dropdown-trigger" type="button" aria-expanded="false" aria-haspopup="true">Tours <span class="nav-dropdown-caret">▾</span></button>
        <div class="nav-dropdown-menu">
          {cat_links}
          <div class="nav-dropdown-sep"></div>
          <a class="nav-dropdown-all" href="/todos-los-tours/">Ver todos los tours</a>
        </div>
      </li>
      <li><a href="/#contacto">Contacto</a></li>
    </ul>
    <a class="btn-whatsapp" href="{wa_link(wa_text)}" target="_blank" rel="noopener">WhatsApp</a>
  </div>
</nav>
'''


def render_footer():
    return '''<section id="contacto" class="reveal">
  <div class="container">
    <div class="cta-final">
      <h2>¿Armamos tu próximo viaje?</h2>
      <p>Escribinos y coordinamos todo por WhatsApp.</p>
      <a class="btn-primary" href="''' + wa_link('Hola, quisiera información sobre los tours.') + '''" target="_blank" rel="noopener">Escribinos por WhatsApp</a>
      <div class="handles">
        <a href="''' + INSTAGRAM_URL + '''" target="_blank" rel="noopener">@mundocaribetours</a>
        <a href="''' + FACEBOOK_URL + '''" target="_blank" rel="noopener">Facebook</a>
        <a href="''' + GOOGLE_MAPS_URL + '''" target="_blank" rel="noopener">⭐ Reseñas en Google</a>
        <span>Playa del Carmen, Riviera Maya</span>
      </div>
    </div>

    <div class="contact-form-card">
      <h3>¿Tu viaje es de acá a 1–3 meses?</h3>
      <p>Si todavía no tenés fechas cerradas, dejanos tus datos y te contactamos nosotros para ir armando todo con tiempo, sin apuro.</p>
      <form class="contact-form" id="mc-contact-form" action="''' + FORMSPREE_URL + '''" method="POST">
        <input type="hidden" name="_subject" value="Nueva consulta (viaje 1-3 meses) - Mundo Caribe Tours">
        <div class="booking-field">
          <label for="cf-name">Nombre</label>
          <input type="text" id="cf-name" name="name" required>
        </div>
        <div class="booking-field-row">
          <div class="booking-field">
            <label for="cf-phone">WhatsApp / Teléfono</label>
            <input type="tel" id="cf-phone" name="phone" required>
          </div>
          <div class="booking-field">
            <label for="cf-email">Email</label>
            <input type="email" id="cf-email" name="email">
          </div>
        </div>
        <div class="booking-field-row">
          <div class="booking-field">
            <label for="cf-date">Fecha aproximada del viaje</label>
            <input type="month" id="cf-date" name="fecha_aproximada">
          </div>
          <div class="booking-field">
            <label for="cf-tours">Tours de interés</label>
            <input type="text" id="cf-tours" name="tours_interes" placeholder="Ej: Chichén Itzá, Holbox...">
          </div>
        </div>
        <div class="booking-field">
          <label for="cf-message">Mensaje (opcional)</label>
          <textarea id="cf-message" name="message" rows="3"></textarea>
        </div>
        <button class="btn-primary" type="submit">Enviar</button>
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

<script src="/assets/site.js"></script>
'''


def render_breadcrumb(items):
    # items: list of (label, href_or_None)
    parts = []
    for label, href in items:
        if href:
            parts.append(f'<a href="{href}">{label}</a>')
        else:
            parts.append(label)
    return '<div class="breadcrumb">' + ' / '.join(parts) + '</div>'


def page_shell(head, body):
    return f'''<!DOCTYPE html>
<html lang="es">
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

def render_tour_card(tour):
    photo_html = f'<img class="tour-card-photo" src="/assets/tours/{tour["photo"]}" alt="{tour["name"]}">' if tour.get('photo') else ''
    price = price_summary(tour['pricing'])
    return f'''<a class="tour-card" href="/tour/{tour['slug']}/">
        {photo_html}
        <div class="tour-card-body">
        <h3>{tour['name']}</h3>
        <p class="desc">{tour['desc']}</p>
        <div class="card-price">{price}</div>
        <span class="tour-link">Ver detalles →</span>
        </div>
      </a>'''


def render_quote_card(item):
    return f'''<a class="tour-card" href="{wa_link('¡Hola! Quiero pedir una cotización para: ' + item['name'])}" target="_blank" rel="noopener">
        <div class="tour-card-body">
        <h3>{item['name']}</h3>
        <p class="desc">{item['desc']}</p>
        <span class="quote-badge">Cotización personalizada</span>
        <span class="tour-link">Pedir cotización →</span>
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


def category_cards_row(cat):
    """Cards for a category as a draggable carousel (or plain grid, see cards_row)."""
    if cat['key'] in QUOTE_ITEMS:
        return cards_row(QUOTE_ITEMS[cat['key']], render_quote_card)
    tours_in_cat = [t for t in TOURS if t['category'] == cat['key']]
    return cards_row(tours_in_cat, render_tour_card)


def category_cards_plain(cat):
    """Cards for a category as a plain (non-carousel) grid — used on the 'ver todos' page."""
    if cat['key'] in QUOTE_ITEMS:
        html = ''.join(render_quote_card(item) for item in QUOTE_ITEMS[cat['key']])
    else:
        tours_in_cat = [t for t in TOURS if t['category'] == cat['key']]
        html = ''.join(render_tour_card(t) for t in tours_in_cat)
    return grid_wrap(html)


# ---------------------------------------------------------------------------
# HOMEPAGE
# ---------------------------------------------------------------------------

def render_home():
    title = 'Mundo Caribe Tours — Tours y excursiones en la Riviera Maya'
    desc = 'Tours y excursiones en la Riviera Maya, coordinados directo por WhatsApp: cenotes, ruinas mayas, islas y mucho más.'
    head = render_head(title, desc, '/')

    featured_cards_html = ''.join(render_tour_card(TOUR_BY_SLUG[s]) for s in FEATURED_SLUGS)
    xcaret_quote_card_html = render_quote_card({'name': 'Xcaret', 'desc': 'Parque México · Xcaret Básico'})
    featured_row = carousel_wrap(featured_cards_html + xcaret_quote_card_html)

    cat_sections = ''
    for key in ['ruinas', 'islas', 'aventura']:
        cat = CAT_BY_KEY[key]
        tours_in_cat = [t for t in TOURS if t['category'] == key][:6]
        row = cards_row(tours_in_cat, render_tour_card)
        cat_sections += f'''
<section class="reveal">
  <div class="container">
    <div class="section-head-row">
      <div class="section-head">
        <p class="eyebrow">{cat['title']}</p>
        <h2>{cat['intro'].split('.')[0]}.</h2>
      </div>
      <a class="see-all" href="/categoria/{cat['slug']}/">Ver todos →</a>
    </div>
    {row}
  </div>
</section>
'''

    special_items = []
    for key in ['pesca', 'xcaret', 'transportes', 'vuelos']:
        cat = CAT_BY_KEY[key]
        href = '/tour/pesca-yate-cancun/' if key == 'pesca' else f'/categoria/{cat["slug"]}/'
        special_items.append((cat, href))

    def render_special_card(item):
        cat, href = item
        return f'''<div class="tour-card">
        <div class="tour-card-body">
        <h3>{cat['title']}</h3>
        <p class="desc">{cat['card_desc']}</p>
        <a class="tour-link" href="{href}">Ver más →</a>
        </div>
      </div>'''

    special_row = cards_row(special_items, render_special_card)

    body = render_nav() + f'''
<section class="hero">
  <div class="container">
    <div>
      <p class="hero-eyebrow">Riviera Maya, México</p>
      <h1>Vivan el Caribe mexicano a fondo</h1>
      <p class="lede">Soy Agustín, argentino, y hace 6 años cambié todo por la Riviera Maya — y nunca más me fui. En este tiempo conocí cada cenote, cada ruina y cada isla como para armarte el viaje que a mí me hubiese encantado que me arme alguien. Tours y excursiones coordinados directo por WhatsApp, sin vueltas.</p>
      <div class="hero-actions">
        <a class="btn-primary" href="#tours">Ver tours</a>
        <a class="btn-secondary" href="{wa_link('Hola, quisiera información sobre los tours.')}" target="_blank" rel="noopener">Escribinos por WhatsApp</a>
      </div>
    </div>
    <div class="hero-logo">
      <img src="/assets/logo.webp" alt="Mundo Caribe Tours">
    </div>
  </div>
</section>

<section id="tours" class="reveal">
  <div class="container">
    <div class="section-head">
      <p class="eyebrow">Destacados</p>
      <h2>Nuestros tours más pedidos</h2>
      <p>Elegí un tour para ver el detalle completo, precio y reservar directo por WhatsApp. Deslizá para ver más →</p>
    </div>
    {featured_row}
  </div>
</section>
{cat_sections}
<section class="reveal">
  <div class="container">
    <div class="section-head">
      <p class="eyebrow">Servicios especiales</p>
      <h2>Todo lo que necesitás para tu viaje</h2>
    </div>
    {special_row}
  </div>
</section>
''' + render_footer()

    write_file('index.html', page_shell(head, body))


# ---------------------------------------------------------------------------
# CATEGORY PAGES
# ---------------------------------------------------------------------------

def render_category_page(cat):
    title = f'{cat["title"]} — Mundo Caribe Tours'
    desc = cat['intro']
    path = f'/categoria/{cat["slug"]}/'
    head = render_head(title, desc, path)

    row = category_cards_row(cat)

    body = render_nav() + f'''
<section class="category-hero reveal">
  <div class="container">
    {render_breadcrumb([('Inicio', '/'), (cat['title'], None)])}
    <h1>{cat['title']}</h1>
    <p>{cat['intro']}</p>
  </div>
</section>
<section class="reveal">
  <div class="container">
    {row}
  </div>
</section>
''' + render_footer()

    write_file(f'categoria/{cat["slug"]}/index.html', page_shell(head, body))


# ---------------------------------------------------------------------------
# TOUR PAGES
# ---------------------------------------------------------------------------

def render_tour_page(tour):
    cat = CAT_BY_KEY[tour['category']]
    title = f'{tour["name"]} — Mundo Caribe Tours'
    desc = tour['desc']
    path = f'/tour/{tour["slug"]}/'
    og_image = (BASE_URL + f'/assets/tours/{tour["photo"]}') if tour.get('photo') else None
    head = render_head(title, desc, path, og_image)

    photo_html = f'<img class="tour-hero-photo" src="/assets/tours/{tour["photo"]}" alt="{tour["name"]}">' if tour.get('photo') else ''

    includes_html = ''.join(f'<li>{i}</li>' for i in tour['includes'])

    notes_html = ''
    if tour.get('tax'):
        notes_html += f'<div class="info-note warn">{tour["tax"]}</div>'
    if tour.get('note'):
        notes_html += f'<div class="info-note">{tour["note"]}</div>'
    if tour.get('snorkel'):
        notes_html += f'<div class="info-note">{SNORKEL_AGE_NOTE}</div>'
    if tour['pricing']['type'] == 'adult_child':
        notes_html += f'<div class="info-note">{GENERAL_AGE_NOTE}</div>'

    others = [t for t in TOURS if t['category'] == tour['category'] and t['slug'] != tour['slug']][:3]
    related_html = ''
    if others:
        related_cards = ''.join(render_tour_card(t) for t in others)
        related_html = f'''
<section class="reveal">
  <div class="container">
    <div class="section-head">
      <p class="eyebrow">También te puede interesar</p>
      <h2>Tours relacionados</h2>
    </div>
    <div class="tour-grid">
      {related_cards}
    </div>
  </div>
</section>
'''

    pricing_json = json.dumps(dict(tour['pricing'], name=tour['name']), ensure_ascii=False)

    body = render_nav() + f'''
<section class="reveal">
  <div class="container">
    {render_breadcrumb([('Inicio', '/'), (cat['title'], f'/categoria/{cat["slug"]}/'), (tour['name'], None)])}
    {photo_html}
    <div class="tour-page-grid">
      <div>
        <h1 class="tour-title">{tour['name']}</h1>
        <div class="tour-meta-row">
          <span>⏱ {tour['duration']}</span>
          <span>📅 {tour['availability']}</span>
        </div>
        <p class="tour-longdesc">{tour['long_desc']}</p>

        <h2 class="tour-section-title">Incluye</h2>
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
''' + render_footer()

    write_file(f'tour/{tour["slug"]}/index.html', page_shell(head, body))


def render_all_tours_page():
    title = 'Todos los tours — Mundo Caribe Tours'
    total_items = len(TOURS) + sum(len(v) for v in QUOTE_ITEMS.values())
    desc = 'La lista completa de tours y excursiones de Mundo Caribe Tours en la Riviera Maya, agrupados por categoría.'
    path = '/todos-los-tours/'
    head = render_head(title, desc, path)

    # IMPORTANT: each category group gets its OWN .reveal — never wrap the
    # whole (very tall) list in a single .reveal. An IntersectionObserver
    # threshold is a ratio of the element's own height, so a section taller
    # than roughly viewport/threshold can never reach that ratio and would
    # sit at opacity:0 forever, however far you scroll. That's exactly why
    # this page looked completely empty before.
    groups_html = ''
    for cat in CATEGORIES:
        groups_html += f'''
<div class="all-tours-group reveal">
  <h2>{cat['title']}</h2>
  {category_cards_plain(cat)}
</div>
'''

    body = render_nav() + f'''
<section class="category-hero reveal">
  <div class="container">
    {render_breadcrumb([('Inicio', '/'), ('Todos los tours', None)])}
    <h1>Todos los tours</h1>
    <p>La lista completa, sin recortes — {total_items} tours con precio y detalle, más nuestras experiencias a cotizar.</p>
  </div>
</section>
<section>
  <div class="container">
    {groups_html}
  </div>
</section>
''' + render_footer()

    write_file('todos-los-tours/index.html', page_shell(head, body))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    render_home()
    for cat in CATEGORIES:
        render_category_page(cat)
    for tour in TOURS:
        render_tour_page(tour)
    render_all_tours_page()
    print(f'Generated: 1 home + {len(CATEGORIES)} category pages + {len(TOURS)} tour pages + 1 all-tours page')


if __name__ == '__main__':
    main()
