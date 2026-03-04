#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Artist Country + Genre Detection System
Versión para GitHub Actions
Lee la última base de datos de charts desde charts_archive/1_download-chart/databases/
y actualiza charts_archive/2_artist_countries_genres/artist_countries_genres.db
"""

import os
import sys
import sqlite3
import pandas as pd
import requests
import re
import unicodedata
import time
import logging
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict
from typing import Optional, Tuple, Dict, Set, List

# ============================================================================
# CONFIGURACIÓN - RUTAS RELATIVAS AL REPOSITORIO
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CHARTS_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"
ARTIST_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_artist_countries_genres" / "artist_countries_genres.db"

ARTIST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# ============================================================================
# CACHÉ EN MEMORIA Y SESIONES HTTP
# ============================================================================
_CACHE = {
    'musicbrainz_country': {},
    'wikidata_country': {},
    'wikipedia_country': {},
    'musicbrainz_genre': {},
    'wikidata_genre': {},
    'wikipedia_genre': {},
}

_SESSION_WIKIPEDIA = requests.Session()
_SESSION_WIKIDATA = requests.Session()
_SESSION_MUSICBRAINZ = requests.Session()

# ============================================================================
# FUNCIONES DE VARIACIONES DE NOMBRE
# ============================================================================

def generate_name_variations(name: str) -> List[str]:
    variations = [name]

    no_accents = ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )
    if no_accents != name:
        variations.append(no_accents)

    no_dots = name.replace('.', '')
    if no_dots != name:
        variations.append(no_dots)
        variations.append(no_dots.replace(' ', ''))

    no_hyphens = name.replace('-', ' ')
    if no_hyphens != name:
        variations.append(no_hyphens)

    return list(dict.fromkeys(variations))

ARTIST_PREFIXES = {
    'dj': ['DJ', 'Dj', 'dj'],
    'mc': ['MC', 'Mc', 'mc'],
    'lil': ['Lil', 'lil', 'LIL'],
    'young': ['Young', 'young'],
    'big': ['Big', 'big'],
    'the': ['The', 'the', 'THE'],
    'los': ['Los', 'los'],
    'las': ['Las', 'las'],
    'el': ['El', 'el'],
    'la': ['La', 'la'],
}

def remove_artist_prefixes(name: str) -> List[str]:
    variations = [name]
    for prefix_base, variants in ARTIST_PREFIXES.items():
        for variant in variants:
            pattern = r'^' + re.escape(variant) + r'\s+'
            if re.match(pattern, name):
                without_prefix = re.sub(pattern, '', name)
                if without_prefix:
                    variations.append(without_prefix)
    return list(dict.fromkeys(variations))

def generate_all_variations(name: str) -> List[str]:
    all_vars = set()
    for var in generate_name_variations(name):
        all_vars.add(var)
        for no_prefix in remove_artist_prefixes(var):
            all_vars.add(no_prefix)
            for var2 in generate_name_variations(no_prefix):
                all_vars.add(var2)

    result = [name]
    for var in sorted(all_vars - {name}, key=len, reverse=True):
        if var and len(var) > 1:
            result.append(var)
    return result[:15]

# ============================================================================
# DICCIONARIO DE PAÍSES
# ============================================================================
COUNTRIES_CANONICAL: Dict[str, Set[str]] = {
    # =========================================================================
    # NORTEAMÉRICA
    # =========================================================================
    'United States': {
        # Nombres del país
        'united states', 'usa', 'us', 'u.s.', 'u.s.a.', 'america',
        'estados unidos', 'ee.uu.', 'eeuu', 'estadosunidos',
        # Gentilicios EN/ES
        'american', 'americano', 'americanos', 'estadounidense', 'estadounidenses',
        # Ciudades — Noreste
        'new york', 'nyc', 'brooklyn', 'bronx', 'queens', 'manhattan', 'staten island',
        'boston', 'philadelphia', 'philly', 'baltimore', 'pittsburgh',
        'washington d.c.', 'dc', 'newark', 'hartford', 'providence', 'buffalo',
        # Ciudades — Sureste
        'miami', 'miami beach', 'fort lauderdale', 'orlando', 'tampa', 'jacksonville',
        'atlanta', 'charlotte', 'raleigh', 'nashville', 'memphis', 'new orleans',
        'louisville', 'richmond', 'virginia beach', 'columbia sc',
        # Ciudades — Medio Oeste
        'chicago', 'detroit', 'cleveland', 'columbus', 'indianapolis',
        'milwaukee', 'minneapolis', 'saint paul', 'st. louis', 'kansas city',
        'cincinnati', 'omaha', 'des moines',
        # Ciudades — Suroeste / Texas
        'houston', 'dallas', 'fort worth', 'san antonio', 'austin', 'el paso',
        'albuquerque', 'tucson', 'phoenix', 'las vegas', 'henderson',
        # Ciudades — Oeste
        'los angeles', 'la', 'hollywood', 'compton', 'long beach', 'anaheim',
        'san francisco', 'sf', 'bay area', 'oakland', 'san jose',
        'sacramento', 'san diego', 'portland', 'seattle', 'denver',
        'salt lake city', 'boise',
        # Ciudades — Hawái / Alaska
        'honolulu', 'anchorage',
    },

    'Canada': {
        'canada', 'canadá', 'canadian', 'canadiense', 'canadienses',
        # EN regional
        'canuck', 'anglo-canadian', 'franco-canadian', 'québécois',
        # Ciudades
        'toronto', 'montreal', 'montréal', 'vancouver', 'calgary',
        'edmonton', 'ottawa', 'québec city', 'quebec', 'winnipeg',
        'hamilton', 'kitchener', 'victoria', 'london ontario', 'halifax',
        'saskatoon', 'regina', 'windsor', 'oshawa', 'moncton', 'fredericton',
        # Regiones
        'ontario', 'british columbia', 'alberta', 'québec', 'nova scotia',
        'new brunswick', 'manitoba', 'saskatchewan',
    },

    'Mexico': {
        'mexico', 'méxico', 'méjico',
        # Gentilicios
        'mexican', 'mexicano', 'mexicana', 'mexicanos', 'mexicanas', 'azteca',
        # Ciudades
        'ciudad de méxico', 'cdmx', 'df', 'distrito federal',
        'guadalajara', 'monterrey', 'puebla', 'tijuana',
        'juárez', 'ciudad juárez', 'léon', 'zapopan', 'nezahualcóyotl',
        'chihuahua', 'naucalpan', 'mérida', 'san luis potosí', 'aguascalientes',
        'hermosillo', 'saltillo', 'mexicali', 'culiacán', 'acapulco',
        'torreón', 'morelia', 'toluca', 'querétaro', 'cancún',
        'veracruz', 'oaxaca', 'xalapa', 'tuxtla gutiérrez',
        # Regiones culturales
        'norteño', 'chilango', 'tapatío', 'regiomontano', 'defeño',
    },

    # =========================================================================
    # CENTROAMÉRICA Y CARIBE
    # =========================================================================
    'Cuba': {
        'cuba', 'cuban', 'cubano', 'cubana', 'cubanos', 'cubanas',
        'la habana', 'havana', 'santiago de cuba', 'camagüey',
        'holguín', 'santa clara', 'guantánamo', 'bayamo', 'matanzas',
        'pinar del río', 'cienfuegos', 'las tunas',
    },

    'Puerto Rico': {
        'puerto rico', 'porto rico',
        'puerto rican', 'puertorriqueño', 'puertorriqueña', 'boricua', 'boricuas',
        'portorriqueño', 'borinkén',
        'san juan', 'bayamón', 'carolina', 'ponce', 'caguas',
        'guaynabo', 'arecibo', 'mayagüez', 'trujillo alto', 'fajardo',
    },

    'Dominican Republic': {
        'dominican republic', 'república dominicana', 'rep. dominicana',
        'dominican', 'dominicano', 'dominicana', 'quisqueyano', 'quisqueyana',
        'santo domingo', 'santiago de los caballeros', 'la romana',
        'san pedro de macorís', 'la vega', 'san francisco de macorís',
        'san cristóbal', 'puerto plata', 'higüey',
    },

    'Jamaica': {
        'jamaica', 'jamaican', 'jamaicano', 'jamaicana', 'jamaicans',
        'yardie', 'rasta', 'rastafari',
        'kingston', 'spanish town', 'montego bay', 'portmore',
        'mandeville', 'may pen', 'old harbour',
        # Términos culturales
        'yard', 'yardie', 'jamrock', 'jah',
    },

    'Trinidad and Tobago': {
        'trinidad and tobago', 'trinidad y tobago', 'trinidad', 'tobago',
        'trinidadian', 'trinitense', 'trini',
        'port of spain', 'san fernando', 'chaguanas', 'arima',
    },

    'Barbados': {
        'barbados', 'barbadian', 'barbadense', 'bajan',
        'bridgetown', 'speightstown',
    },

    'Haiti': {
        'haiti', 'haití', 'haitian', 'haitiano', 'haïtien',
        'port-au-prince', 'cap-haïtien', 'gonaïves', 'saint-marc',
        'petionville', 'carrefour', 'jacmel',
    },

    'Costa Rica': {
        'costa rica', 'costa rican', 'costarricense', 'tico', 'tica',
        'san josé', 'alajuela', 'cartago', 'heredia', 'liberia',
        'puntarenas', 'limón',
    },

    'Panama': {
        'panama', 'panamá', 'panamanian', 'panameño', 'panameña',
        'panama city', 'ciudad de panamá', 'colón', 'david',
        'santiago', 'chitré', 'la chorrera', 'arraiján',
    },

    'Guatemala': {
        'guatemala', 'guatemalan', 'guatemalteco', 'guatemalteca', 'chapín', 'chapina',
        'guatemala city', 'ciudad de guatemala', 'mixco', 'quetzaltenango', 'xela',
        'villa nueva', 'san miguel petapa', 'huehuetenango', 'cobán', 'escuintla',
    },

    'Honduras': {
        'honduras', 'honduran', 'hondureño', 'hondureña', 'catracho', 'catracha',
        'tegucigalpa', 'san pedro sula', 'choluteca', 'la ceiba', 'el progreso',
        'danli', 'juticalpa', 'comayagua',
    },

    'El Salvador': {
        'el salvador', 'salvadoran', 'salvadoreño', 'salvadoreña', 'guanaco', 'guanaca',
        'san salvador', 'santa ana', 'san miguel', 'mejicanos', 'soyapango',
        'nueva san salvador', 'apopa', 'delgado',
    },

    'Nicaragua': {
        'nicaragua', 'nicaraguan', 'nicaragüense', 'nica',
        'managua', 'león', 'granada', 'masaya', 'matagalpa',
        'chinandega', 'estelí', 'jinotega',
    },

    'Belize': {
        'belize', 'belice', 'belizean', 'beliceño', 'belizean',
        'belmopan', 'belize city', 'san ignacio', 'orange walk',
    },

    'Cuba': {
        'cuba', 'cuban', 'cubano', 'cubana', 'habanero', 'habanera',
        'la habana', 'havana', 'santiago de cuba', 'camagüey',
        'holguín', 'santa clara', 'guantánamo', 'bayamo', 'matanzas',
        'pinar del río', 'cienfuegos',
    },

    # =========================================================================
    # SUDAMÉRICA
    # =========================================================================
    'Argentina': {
        'argentina', 'argentinian', 'argentine', 'argentino', 'argentina',
        'porteño', 'porteña', 'rioplatense', 'gaucho',
        'buenos aires', 'baires', 'la plata', 'córdoba',
        'rosario', 'mendoza', 'tucumán', 'san miguel de tucumán',
        'mar del plata', 'salta', 'santa fe', 'san juan',
        'resistencia', 'corrientes', 'posadas', 'neuquén',
        'bahía blanca', 'santiago del estero', 'formosa',
    },

    'Brazil': {
        'brazil', 'brasil', 'brazilian', 'brasileiro', 'brasileira',
        'brasileiros', 'carioca', 'paulista', 'paulistano', 'baiano',
        'gaúcho', 'mineiro', 'nordestino',
        'são paulo', 'sp', 'rio de janeiro', 'rio', 'rj',
        'salvador', 'brasília', 'fortaleza', 'belo horizonte', 'bh',
        'manaus', 'curitiba', 'recife', 'porto alegre', 'goiânia',
        'campinas', 'belém', 'natal', 'são luís', 'maceió',
        'campo grande', 'joão pessoa', 'teresina', 'macapá',
        'porto velho', 'cuiabá', 'aracaju', 'florianópolis',
        'vitória', 'uberlândia', 'ribeirão preto',
        # Regiones
        'nordeste', 'nordeste brasileiro', 'amazônia', 'pampa', 'cerrado',
    },

    'Chile': {
        'chile', 'chilean', 'chileno', 'chilena', 'chilenos', 'roto',
        'santiago', 'stgo', 'valparaíso', 'viña del mar', 'concepción',
        'la serena', 'antofagasta', 'temuco', 'rancagua', 'talca',
        'arica', 'iquique', 'chillán', 'puerto montt', 'coquimbo',
        'osorno', 'valdivia', 'punta arenas', 'copiapó',
    },

    'Colombia': {
        'colombia', 'colombian', 'colombiano', 'colombiana', 'colombianos',
        'bogotano', 'bogotana', 'rolo', 'paisa', 'costeño', 'caleño',
        'bogotá', 'bogota', 'medellín', 'medellin', 'cali',
        'barranquilla', 'cartagena', 'cúcuta', 'bucaramanga',
        'pereira', 'santa marta', 'ibagué', 'manizales', 'bello',
        'pasto', 'montería', 'valledupar', 'villavicencio',
        'soledad', 'itagüí', 'palmira', 'buenaventura',
    },

    'Peru': {
        'peru', 'perú', 'peruvian', 'peruano', 'peruana', 'limeño', 'limeña',
        'lima', 'arequipa', 'trujillo', 'cusco', 'cuzco',
        'piura', 'chiclayo', 'iquitos', 'huancayo', 'chimbote',
        'callao', 'tacna', 'pucallpa', 'juliaca', 'ayacucho',
    },

    'Venezuela': {
        'venezuela', 'venezuelan', 'venezolano', 'venezolana', 'venezolanos',
        'caraqueño', 'caraqueña', 'maracucho',
        'caracas', 'maracaibo', 'valencia', 'barquisimeto', 'maracay',
        'ciudad guayana', 'san cristóbal', 'barcelona', 'maturín',
        'cumana', 'barinas', 'guanare', 'acarigua', 'cabimas',
    },

    'Ecuador': {
        'ecuador', 'ecuadorian', 'ecuatoriano', 'ecuatoriana', 'ecuatorianos',
        'quiteño', 'guayaquileño',
        'quito', 'guayaquil', 'cuenca', 'santo domingo',
        'machala', 'durán', 'ibarra', 'ambato', 'riobamba',
        'esmeraldas', 'portoviejo', 'loja',
    },

    'Bolivia': {
        'bolivia', 'bolivian', 'boliviano', 'boliviana', 'bolivianos',
        'paceño', 'cruceño',
        'la paz', 'santa cruz', 'cochabamba', 'oruro', 'sucre',
        'potosí', 'tarija', 'trinidad', 'cobija', 'el alto',
    },

    'Paraguay': {
        'paraguay', 'paraguayan', 'paraguayo', 'paraguaya', 'paraguayos',
        'asunción', 'ciudad del este', 'san lorenzo', 'encarnación',
        'luque', 'capiatá', 'lambaré', 'fernando de la mora',
    },

    'Uruguay': {
        'uruguay', 'uruguayan', 'uruguayo', 'uruguaya', 'charrúa',
        'montevideo', 'montevideano',
        'salto', 'paysandú', 'maldonado', 'punta del este',
        'las piedras', 'rivera', 'tacuarembó', 'melo',
    },

    'Guyana': {
        'guyana', 'guyanese', 'guyanés', 'guyanesa',
        'georgetown', 'linden', 'new amsterdam',
    },

    'Suriname': {
        'suriname', 'surinam', 'surinamese', 'surinamés',
        'paramaribo', 'lelydorp', 'nieuw nickerie',
    },

    # =========================================================================
    # EUROPA OCCIDENTAL
    # =========================================================================
    'United Kingdom': {
        'united kingdom', 'uk', 'reino unido', 'great britain', 'britain',
        # Gentilicios
        'british', 'english', 'inglés', 'inglesa', 'británico', 'británica',
        'scottish', 'escocés', 'escocesa', 'welsh', 'galés', 'galesa',
        'northern irish', 'ulsterman',
        # Ciudades — Inglaterra
        'london', 'londres', 'manchester', 'birmingham', 'liverpool',
        'leeds', 'bristol', 'sheffield', 'nottingham', 'leicester',
        'newcastle', 'coventry', 'southampton', 'oxford', 'cambridge',
        'brighton', 'reading', 'portsmouth', 'sunderland', 'wolverhampton',
        # Ciudades — Escocia, Gales, Irlanda del Norte
        'glasgow', 'edinburgh', 'edimburgo', 'aberdeen', 'dundee',
        'cardiff', 'swansea', 'belfast',
        # Regiones culturales
        'england', 'scotland', 'wales', 'northern ireland',
        'midlands', 'yorkshire', 'cornwall', 'merseyside',
    },

    'Ireland': {
        'ireland', 'irlanda', 'irish', 'irlandés', 'irlandesa', 'éirinn',
        'gaelic', 'gaélico',
        'dublin', 'dublín', 'cork', 'limerick', 'galway',
        'waterford', 'drogheda', 'dundalk', 'swords', 'bray',
    },

    'Spain': {
        'spain', 'españa', 'spanish', 'español', 'española', 'españoles',
        'madrileño', 'catalán', 'catalana', 'vasco', 'vasca', 'andaluz', 'andaluza',
        'ibérico', 'hispano',
        'madrid', 'barcelona', 'bcn', 'valencia', 'seville', 'sevilla',
        'zaragoza', 'málaga', 'murcia', 'bilbao', 'alicante',
        'córdoba', 'granada', 'valladolid', 'palma', 'las palmas',
        'santa cruz de tenerife', 'san sebastián', 'donostia',
        'pamplona', 'santander', 'logroño', 'burgos', 'salamanca',
        'toledo', 'cádiz', 'huelva', 'badajoz', 'mérida', 'oviedo',
        'gijón', 'vigo', 'a coruña', 'santiago de compostela',
        # Regiones
        'cataluña', 'catalonia', 'país vasco', 'basque country',
        'andalucía', 'galicia', 'castilla', 'asturias', 'aragón',
        'extremadura', 'navarra', 'canarias', 'baleares',
    },

    'France': {
        'france', 'francia', 'french', 'francés', 'francesa', 'français',
        'parisino', 'parisina', 'galo', 'gala',
        'paris', 'paris', 'marseille', 'marsella', 'lyon', 'toulouse',
        'nice', 'bordeaux', 'lille', 'strasbourg', 'nantes', 'montpellier',
        'rennes', 'reims', 'grenoble', 'dijon', 'angers', 'saint-étienne',
        'toulon', 'rouen', 'brest', 'metz', 'perpignan',
        # Regiones
        'île-de-france', 'bretagne', 'bretaña', 'normandie', 'normandía',
        'alsace', 'alsacia', 'occitanie', 'loire', 'provence', 'provenza',
        # DOM-TOM
        'martinique', 'martinica', 'guadeloupe', 'guadalupe', 'guyane',
        'la réunion', 'new caledonia', 'nueva caledonia',
    },

    'Germany': {
        'germany', 'alemania', 'german', 'alemán', 'alemana', 'deutsch',
        'berliner', 'bávaro', 'bavarian',
        'berlin', 'berlín', 'hamburg', 'hamburgo', 'munich', 'münchen',
        'cologne', 'köln', 'colonia', 'frankfurt', 'stuttgart',
        'düsseldorf', 'dortmund', 'essen', 'leipzig', 'bremen',
        'dresden', 'hanover', 'hannover', 'nuremberg', 'nürnberg',
        'bonn', 'mannheim', 'karlsruhe', 'augsburg', 'münster',
        'bielefeld', 'wiesbaden', 'bochum', 'freiburg',
        # Regiones
        'bavaria', 'baviera', 'saxony', 'sajonia', 'thuringia', 'thuringia',
        'rhineland', 'westphalia', 'nordrhein-westfalen',
    },

    'Italy': {
        'italy', 'italia', 'italian', 'italiano', 'italiana', 'italiani',
        'romano', 'romana', 'milanés', 'napolitano', 'siciliano', 'sardo',
        'rome', 'roma', 'milan', 'milano', 'naples', 'napoli',
        'turin', 'torino', 'palermo', 'genoa', 'genova',
        'bologna', 'florence', 'firenze', 'venice', 'venezia', 'verona',
        'catania', 'bari', 'messina', 'padova', 'trieste',
        'brescia', 'prato', 'parma', 'modena', 'reggio calabria',
        # Regiones
        'sicilia', 'sicily', 'sardegna', 'sardinia', 'cerdeña',
        'toscana', 'tuscany', 'lazio', 'lombardia', 'lombardy',
        'calabria', 'puglia', 'apulia', 'veneto', 'liguria',
    },

    'Portugal': {
        'portugal', 'portuguese', 'português', 'portugues', 'portuga',
        'lisbon', 'lisboa', 'lisboeta',
        'porto', 'braga', 'coimbra', 'funchal', 'setúbal',
        'aveiro', 'viseu', 'leiria', 'faro', 'évora',
        # Regiones y archipiélagos
        'azores', 'açores', 'madeira', 'algarve', 'alentejo',
    },

    'Netherlands': {
        'netherlands', 'países bajos', 'holland', 'holanda', 'dutch',
        'holandés', 'holandesa', 'nederlander',
        'amsterdam', 'rotterdam', 'the hague', 'den haag', 'la haya',
        'utrecht', 'eindhoven', 'groningen', 'tilburg', 'almere',
        'breda', 'nijmegen', 'arnhem', 'delft', 'leiden', 'haarlem',
    },

    'Belgium': {
        'belgium', 'bélgica', 'belgian', 'belga', 'belges',
        'brussels', 'bruselas', 'bruxelles',
        'antwerp', 'amberes', 'antwerpen', 'ghent', 'gent',
        'charleroi', 'liège', 'lieja', 'bruges', 'brujas', 'brugge',
        'namur', 'mons',
    },

    'Switzerland': {
        'switzerland', 'suiza', 'swiss', 'suizo', 'suiza', 'helvetia',
        'schweizer', 'helvético',
        'zurich', 'zúrich', 'geneva', 'ginebra', 'genf',
        'basel', 'basilea', 'bern', 'berna', 'lausanne', 'lausana',
        'winterthur', 'st. gallen', 'lucerne', 'lugano',
    },

    'Austria': {
        'austria', 'austrian', 'austríaco', 'austríaca', 'österreicher',
        'vienna', 'viena', 'wien', 'vienés', 'vienesa',
        'graz', 'linz', 'salzburg', 'salzburgo', 'innsbruck',
        'klagenfurt', 'wels', 'villach', 'steyr',
    },

    'Sweden': {
        'sweden', 'suecia', 'swedish', 'sueco', 'sueca', 'svensk',
        'stockholmska',
        'stockholm', 'gothenburg', 'göteborg', 'malmö', 'malmo',
        'uppsala', 'västerås', 'örebro', 'linköping', 'helsingborg',
        'norrköping', 'lund', 'umeå',
    },

    'Norway': {
        'norway', 'noruega', 'norwegian', 'noruego', 'noruega', 'norsk',
        'oslo', 'bergen', 'trondheim', 'stavanger', 'drammen',
        'fredrikstad', 'skien', 'tromsø', 'sandefjord',
    },

    'Denmark': {
        'denmark', 'dinamarca', 'danish', 'danés', 'danese', 'dansker',
        'copenhagen', 'copenhague', 'københavn',
        'aarhus', 'odense', 'aalborg', 'esbjerg', 'randers',
        'kolding', 'horsens', 'vejle',
    },

    'Finland': {
        'finland', 'finlandia', 'finnish', 'finlandés', 'finlandesa', 'finno', 'suomalainen',
        'helsinki', 'espoo', 'tampere', 'vantaa', 'oulu',
        'turku', 'jyväskylä', 'lahti', 'kuopio',
    },

    'Iceland': {
        'iceland', 'islandia', 'icelandic', 'islandés', 'íslenskur',
        'reykjavik', 'reykjavík', 'kópavogur', 'hafnarfjörður', 'akureyri',
    },

    'Russia': {
        'russia', 'rusia', 'russian', 'ruso', 'rusa', 'russos', 'rossiya',
        'moscovita',
        'moscow', 'moscú', 'moskva', 'saint petersburg', 'san petersburgo',
        'novosibirsk', 'yekaterinburg', 'kazan', 'nizhny novgorod',
        'chelyabinsk', 'samara', 'ufa', 'krasnoyarsk', 'omsk',
        'voronezh', 'volgograd', 'krasnodar', 'vladivostok',
        'irkutsk', 'saratov', 'tyumen',
    },

    'Ukraine': {
        'ukraine', 'ucrania', 'ukrainian', 'ucraniano', 'ucraniana', 'ukraïnets',
        'kyiv', 'kiev', 'kharkiv', 'kharkov', 'odessa', 'odesa',
        'dnipro', 'donetsk', 'zaporizhzhia', 'lviv', 'lvov',
        'kryvyi rih', 'mykolaiv', 'mariupol', 'cherkasy',
    },

    'Poland': {
        'poland', 'polonia', 'polish', 'polaco', 'polaca', 'polak',
        'varsoviano', 'cracoviano',
        'warsaw', 'varsovia', 'warszawa',
        'krakow', 'cracovia', 'kraków', 'lodz', 'łódź',
        'wroclaw', 'wrocław', 'poznan', 'poznań', 'gdansk', 'gdańsk',
        'szczecin', 'bydgoszcz', 'lublin', 'katowice', 'białystok',
    },

    'Czech Republic': {
        'czech republic', 'czechia', 'república checa', 'chequia', 'czech', 'checo', 'čech',
        'prague', 'praga', 'praha', 'brno', 'ostrava', 'plzen', 'plzeň',
        'liberec', 'olomouc', 'ústí nad labem',
    },

    'Slovakia': {
        'slovakia', 'eslovaquia', 'slovak', 'eslovaco', 'eslovaca',
        'bratislava', 'košice', 'prešov', 'žilina', 'nitra',
    },

    'Hungary': {
        'hungary', 'hungría', 'hungarian', 'húngaro', 'húngara', 'magyar',
        'budapest', 'debrecen', 'szeged', 'miskolc', 'pécs',
        'győr', 'nyíregyháza', 'kecskemét',
    },

    'Romania': {
        'romania', 'rumania', 'rumanía', 'romanian', 'rumano', 'română',
        'bucharest', 'bucarest', 'bucurești',
        'cluj-napoca', 'timisoara', 'timișoara', 'iasi', 'iași',
        'constanta', 'constanța', 'brașov', 'craiova', 'galati',
    },

    'Bulgaria': {
        'bulgaria', 'bulgarian', 'búlgaro', 'búlgara', 'balgarin',
        'sofia', 'sofía', 'plovdiv', 'varna', 'burgas',
        'ruse', 'stara zagora', 'pleven',
    },

    'Greece': {
        'greece', 'grecia', 'greek', 'griego', 'griega', 'hellenic', 'hélenico',
        'athens', 'atenas', 'athina', 'thessaloniki', 'tesalónica',
        'patras', 'heraklion', 'iraklion', 'larissa',
        'volos', 'rhodes', 'rodas', 'corfu', 'corfú',
    },

    'Serbia': {
        'serbia', 'serbian', 'serbio', 'serbia', 'srbin',
        'belgrade', 'belgrado', 'beograd',
        'novi sad', 'niš', 'kragujevac',
    },

    'Croatia': {
        'croatia', 'croacia', 'croatian', 'croata', 'hrvat',
        'zagreb', 'split', 'rijeka', 'osijek', 'zadar',
        'dubrovnik', 'slavonski brod',
    },

    'Albania': {
        'albania', 'albanian', 'albanés', 'albanesa', 'shqiptar',
        'tirana', 'durrës', 'vlorë', 'shkodër', 'fier',
    },

    'North Macedonia': {
        'north macedonia', 'macedonia del norte', 'macedonian', 'macedonio', 'makedonec',
        'skopje', 'bitola', 'kumanovo', 'tetovo',
    },

    'Bosnia and Herzegovina': {
        'bosnia and herzegovina', 'bosnia', 'herzegovina', 'bosnian', 'bosnio',
        'sarajevo', 'banja luka', 'tuzla', 'zenica', 'mostar',
    },

    'Slovenia': {
        'slovenia', 'eslovenia', 'slovenian', 'esloveno', 'slovenec',
        'ljubljana', 'maribor', 'celje', 'koper',
    },

    'Lithuania': {
        'lithuania', 'lituania', 'lithuanian', 'lituano', 'lietuvis',
        'vilnius', 'kaunas', 'klaipėda', 'šiauliai',
    },

    'Latvia': {
        'latvia', 'letonia', 'latvian', 'letón', 'latvietis',
        'riga', 'daugavpils', 'liepāja', 'jelgava',
    },

    'Estonia': {
        'estonia', 'estonian', 'estonio', 'estona', 'eestlane',
        'tallinn', 'tartu', 'narva', 'pärnu',
    },

    # =========================================================================
    # ASIA OCCIDENTAL / MEDIO ORIENTE
    # =========================================================================
    'Turkey': {
        'turkey', 'turquía', 'turkish', 'turco', 'turca', 'türk', 'türkiye',
        'istanbul', 'istambul', 'ankara', 'izmir', 'bursa', 'antalya',
        'adana', 'konya', 'gaziantep', 'şanlıurfa', 'mersin',
        'kayseri', 'eskişehir', 'diyarbakır', 'samsun', 'denizli',
    },

    'Iran': {
        'iran', 'irán', 'iranian', 'iraní', 'persian', 'persa', 'irani',
        'tehran', 'teherán', 'tehrán', 'mashhad', 'isfahan', 'esfahan',
        'karaj', 'shiraz', 'tabriz', 'qom', 'ahvaz',
        'kermanshah', 'rasht', 'urmia', 'zahedan',
    },

    'Iraq': {
        'iraq', 'irak', 'iraqi', 'iraquí', 'iraqiana', 'Iraqiyya',
        'baghdad', 'bagdad', 'basra', 'mosul', 'erbil', 'hewler',
        'kirkuk', 'najaf', 'karbala', 'sulaymaniyah',
    },

    'Saudi Arabia': {
        'saudi arabia', 'arabia saudita', 'arabia saudi', 'ksa', 'saudi',
        'saudí', 'saudia', 'hijazi', 'najdi',
        'riyadh', 'riad', 'jeddah', 'yeda', 'mecca', 'la meca',
        'medina', 'dammam', 'khobar', 'taif', 'tabuk',
    },

    'United Arab Emirates': {
        'united arab emirates', 'emiratos árabes unidos', 'uae', 'emirati', 'emiratí',
        'dubai', 'abu dhabi', 'abu dabi', 'sharjah', 'al ain',
        'ajman', 'ras al khaimah', 'fujairah',
    },

    'Kuwait': {
        'kuwait', 'kuwaiti', 'kuwaití', 'kuwaytiyya',
        'kuwait city', 'al ahmadi', 'hawalli', 'farwaniya',
    },

    'Qatar': {
        'qatar', 'qatari', 'catarí', 'qatariyya',
        'doha', 'al wakrah', 'al khor', 'dukhan',
    },

    'Bahrain': {
        'bahrain', 'baréin', 'bahrainiyya', 'bahraini', 'bareiní',
        'manama', 'riffa', 'muharraq', 'hamad city',
    },

    'Oman': {
        'oman', 'omán', 'omani', 'omaní',
        'muscat', 'mascate', 'salalah', 'sohar', 'nizwa',
    },

    'Yemen': {
        'yemen', 'yemeni', 'yemení', 'yemeniyya',
        'sanaa', 'saná', 'aden', 'adén', 'taiz', 'hodeidah',
    },

    'Israel': {
        'israel', 'israeli', 'israelí', 'yisraeli', 'ivri',
        'jerusalem', 'jerusalén', 'yerushalayim', 'al-quds',
        'tel aviv', 'tel-aviv', 'yafo', 'jaffa', 'haifa', 'heifa',
        'rishon lezion', 'petah tikva', 'ashdod', 'beersheba', 'netanya',
    },

    'Palestine': {
        'palestine', 'palestina', 'palestinian', 'palestino', 'palestina',
        'gaza', 'ramallah', 'nablus', 'hebron', 'jenin', 'tulkarm',
    },

    'Lebanon': {
        'lebanon', 'líbano', 'lebanese', 'libanés', 'libanesa', 'lubnaniyya',
        'beirut', 'bayrut', 'tripoli', 'trípoli', 'sidon', 'tyre', 'sour',
        'zahle', 'jounieh',
    },

    'Syria': {
        'syria', 'siria', 'syrian', 'sirio', 'siria', 'suriyya',
        'damascus', 'damasco', 'dimashq', 'aleppo', 'alepo', 'halab',
        'homs', 'hama', 'latakia', 'deir ez-zor', 'raqqa',
    },

    'Jordan': {
        'jordan', 'jordania', 'jordanian', 'jordano', 'urduniyya',
        'amman', 'aqaba', 'zarqa', 'irbid', 'jerash', 'petra',
    },

    'Afghanistan': {
        'afghanistan', 'afganistán', 'afghan', 'afgano', 'afghani',
        'kabul', 'kandahar', 'herat', 'mazar-i-sharif', 'jalalabad',
        'kunduz', 'ghazni',
    },

    # =========================================================================
    # ASIA MERIDIONAL
    # =========================================================================
    'India': {
        'india', 'indian', 'indio', 'india', 'bharatiya', 'bharat', 'hindustan',
        # Industrias cinematográficas
        'bollywood', 'tollywood', 'kollywood', 'mollywood', 'sandalwood',
        # Ciudades
        'mumbai', 'bombay', 'delhi', 'new delhi', 'kolkata', 'calcutta',
        'chennai', 'madras', 'bangalore', 'bengaluru', 'hyderabad',
        'ahmedabad', 'pune', 'surat', 'jaipur', 'lucknow',
        'kanpur', 'nagpur', 'indore', 'thane', 'bhopal',
        'visakhapatnam', 'vizag', 'patna', 'vadodara', 'ludhiana',
        'agra', 'nashik', 'ranchi', 'meerut', 'rajkot', 'varanasi',
        'srinagar', 'amritsar', 'allahabad', 'prayagraj', 'guwahati',
        'chandigarh', 'coimbatore', 'kochi', 'cochin', 'thiruvananthapuram',
        'madurai', 'vijayawada', 'aurangabad', 'gwalior', 'jodhpur',
        # Gentilicios regionales
        'punjabi', 'bengalí', 'tamul', 'tamil', 'telugu', 'kannada',
        'malayali', 'gujarati', 'marathi', 'rajasthani', 'bihari',
        'assamese', 'odia', 'kashmiri', 'sikh',
        # Regiones/estados
        'punjab', 'gujarat', 'maharashtra', 'tamil nadu', 'kerala',
        'karnataka', 'andhra pradesh', 'telangana', 'west bengal',
        'rajasthan', 'uttar pradesh', 'madhya pradesh', 'bihar',
        'odisha', 'assam', 'jharkhand', 'chhattisgarh', 'goa',
    },

    'Pakistan': {
        'pakistan', 'pakistán', 'pakistani', 'paquistaní', 'pakistaniyya',
        'punjabi (pakistan)', 'sindhi', 'pashtun', 'baloch', 'pathan',
        'karachi', 'lahore', 'islamabad', 'rawalpindi', 'faisalabad',
        'multan', 'gujranwala', 'peshawar', 'quetta', 'sialkot',
        'hyderabad (pk)', 'larkana', 'sukkur', 'bahawalpur', 'sargodha',
        # Industria
        'lollywood',
        # Regiones
        'punjab (pakistan)', 'sindh', 'khyber pakhtunkhwa', 'kpk', 'balochistan',
        'gilgit-baltistan', 'azad kashmir',
    },

    'Bangladesh': {
        'bangladesh', 'bangladeshi', 'bangladesí', 'bangladeshi', 'bangali',
        'dhaka', 'chittagong', 'chattogram', 'khulna', 'rajshahi',
        'sylhet', 'barisal', 'rangpur', 'mymensingh', 'comilla', 'narayanganj',
        # Industria
        'dhallywood',
    },

    'Sri Lanka': {
        'sri lanka', 'ceylon', 'sri lankan', 'ceilanés', 'cingalés', 'sinhala',
        'colombo', 'kandy', 'galle', 'jaffna', 'negombo',
        'trincomalee', 'anuradhapura', 'batticaloa',
    },

    'Nepal': {
        'nepal', 'nepali', 'nepalí', 'nepalese', 'nepales', 'nepálese',
        'kathmandu', 'katmandú', 'pokhara', 'lalitpur', 'biratnagar',
        'bharatpur', 'birgunj', 'dharan',
    },

    'Bhutan': {
        'bhutan', 'bután', 'bhutanese', 'butanés', 'drukpa',
        'thimphu', 'phuntsholing', 'paro',
    },

    'Maldives': {
        'maldives', 'maldivas', 'maldivian', 'maldivo', 'divehi',
        'malé', 'addu city', 'fuvahmulah',
    },

    # =========================================================================
    # ASIA ORIENTAL
    # =========================================================================
    'China': {
        'china', 'chinese', 'chino', 'china', 'zhongguo', 'zhonghua',
        'beijingese', 'shanghainese', 'cantonese', 'cantones', 'mandarín',
        # Ciudades
        'beijing', 'pekín', 'shanghai', 'shanghái', 'hong kong', 'hongkong',
        'guangzhou', 'cantón', 'shenzhen', 'chengdu', 'tianjin',
        'wuhan', 'chongqing', 'nanjing', 'hangzhou', 'xian', "xi'an",
        'qingdao', 'dalian', 'shenyang', 'dongguan', 'foshan',
        'kunming', 'harbin', 'zhengzhou', 'changsha', 'jinan',
        'wuxi', 'suzhou', 'hefei', 'nanchang', 'shijiazhuang',
        'guiyang', 'taiyuan', 'lanzhou', 'urumqi', 'lhasa',
        # Regiones especiales
        'macau', 'macao',
    },

    'Taiwan': {
        'taiwan', 'taiwán', 'taiwanese', 'taiwanés', 'roc', 'formosa',
        'taipei', 'taipéi', 'new taipei', 'taoyuan', 'kaohsiung',
        'taichung', 'tainan', 'keelung', 'hsinchu',
    },

    'Japan': {
        'japan', 'japón', 'japanese', 'japonés', 'japonesa', 'nihonjin',
        'tokyoite', 'osakan', 'osakano',
        # Ciudades
        'tokyo', 'tokio', 'osaka', 'nagoya', 'yokohama', 'sapporo',
        'fukuoka', 'kyoto', 'kobe', 'kawasaki', 'saitama', 'hiroshima',
        'sendai', 'kitakyushu', 'chiba', 'sakai', 'niigata',
        'hamamatsu', 'kumamoto', 'okayama', 'shizuoka', 'naha',
        # Islas
        'okinawa', 'hokkaido', 'kyushu', 'shikoku', 'honshu',
        # Pop culture
        'j-pop', 'jpop', 'j-rock', 'anime', 'otaku',
    },

    'South Korea': {
        'south korea', 'corea del sur', 'korea', 'korean', 'coreano', 'coreana',
        'hanguk', 'koreans', 'hangukssaram',
        # Ciudades
        'seoul', 'seúl', 'busan', 'pusan', 'incheon', 'daegu', 'daejeon',
        'gwangju', 'suwon', 'ulsan', 'changwon', 'goyang',
        'seongnam', 'yongin', 'jeju', 'cheju', 'pohang',
        # Pop culture
        'k-pop', 'kpop', 'k-drama', 'kdrama', 'hallyu', 'k-indie',
    },

    'North Korea': {
        'north korea', 'corea del norte', 'dprk', 'north korean', 'norcoreano',
        'pyongyang', 'hamhung', 'chongjin', 'wonsan',
    },

    'Mongolia': {
        'mongolia', 'mongolian', 'mongol', 'mongoliana',
        'ulaanbaatar', 'ulan bator', 'erdenet', 'darkhan',
    },

    # =========================================================================
    # ASIA SUDORIENTAL
    # =========================================================================
    'Indonesia': {
        'indonesia', 'indonesian', 'indonesio', 'indonesa', 'orang indonesia',
        'javanese', 'javanés', 'sundanese', 'sundanés', 'balinese', 'balinés',
        'jakarta', 'surabaya', 'bandung', 'medan', 'semarang',
        'makassar', 'yogyakarta', 'jogja', 'palembang', 'denpasar',
        'batam', 'pekanbaru', 'bandar lampung', 'malang', 'padang',
        'samarinda', 'balikpapan', 'manado',
        # Islas / regiones
        'java', 'sumatra', 'borneo', 'kalimantan', 'bali',
        'sulawesi', 'papua', 'lombok', 'flores',
    },

    'Philippines': {
        'philippines', 'filipinas', 'filipino', 'filipina', 'pilipino',
        'pinoy', 'pinay', 'pilipinas',
        'manila', 'quezon city', 'davao', 'cebu', 'caloocan',
        'zamboanga', 'antipolo', 'taguig', 'pasig', 'cagayan de oro',
        'makati', 'pasay', 'valenzuela', 'paranaque', 'las piñas',
        'marikina', 'muntinlupa', 'mandaluyong',
        # Islas
        'luzon', 'visayas', 'mindanao', 'palawan', 'cebu island',
    },

    'Thailand': {
        'thailand', 'tailandia', 'thai', 'tailandés', 'tailandesa', 'khon thai',
        'siamese', 'siamés',
        'bangkok', 'krung thep', 'nonthaburi', 'nakhon ratchasima', 'korat',
        'chiang mai', 'hat yai', 'pattaya', 'phuket', 'udon thani',
        'khon kaen', 'surat thani', 'nakhon sawan', 'ayutthaya',
    },

    'Vietnam': {
        'vietnam', 'viet nam', 'vietnamese', 'vietnamita', 'viet', 'nguoi viet',
        'hanoi', 'hà nội', 'ho chi minh city', 'saigon', 'sài gòn',
        'haiphong', 'hải phòng', 'can tho', 'cần thơ', 'danang', 'đà nẵng',
        'bien hoa', 'hue', 'huế', 'nha trang', 'vung tau', 'vinh',
    },

    'Malaysia': {
        'malaysia', 'malasia', 'malaysian', 'malayo', 'malaya', 'orang malaysia',
        'kuala lumpur', 'kl', 'george town', 'penang', 'ipoh',
        'shah alam', 'petaling jaya', 'johor bahru', 'jb',
        'kota kinabalu', 'kuching', 'sandakan', 'malacca', 'melaka',
    },

    'Singapore': {
        'singapore', 'singapur', 'singaporean', 'singapurense',
        'singlish', 'singaporan',
    },

    'Myanmar': {
        'myanmar', 'burma', 'birmanie', 'burmese', 'birmano', 'myanmar naing-ngan',
        'naypyidaw', 'yangon', 'rangoon', 'mandalay', 'mawlamyine',
    },

    'Cambodia': {
        'cambodia', 'camboya', 'cambodian', 'camboyano', 'khmer',
        'phnom penh', 'siem reap', 'battambang', 'sihanoukville',
    },

    'Laos': {
        'laos', 'lao', 'laotian', 'laosiano',
        'vientiane', 'luang prabang', 'pakse', 'savannakhet',
    },

    'Timor-Leste': {
        'timor-leste', 'east timor', 'timor oriental', 'timorese', 'timorense',
        'dili', 'baucau',
    },

    'Brunei': {
        'brunei', 'bruneian', 'bruneiano',
        'bandar seri begawan',
    },

    # =========================================================================
    # ASIA CENTRAL
    # =========================================================================
    'Kazakhstan': {
        'kazakhstan', 'kazajistán', 'kazakhstani', 'kazajo', 'qazaqstanlyq',
        'almaty', 'nur-sultan', 'astana', 'shymkent', 'karaganda',
    },

    'Uzbekistan': {
        'uzbekistan', 'uzbekistán', 'uzbek', 'uzbeko', 'ozbekistonlik',
        'tashkent', 'toshkent', 'samarkand', 'bukhara', 'namangan', 'andijan',
    },

    'Tajikistan': {
        'tajikistan', 'tayikistán', 'tajik', 'tayiko',
        'dushanbe', 'khujand', 'kulob',
    },

    'Kyrgyzstan': {
        'kyrgyzstan', 'kirguistán', 'kyrgyz', 'kirguís',
        'bishkek', 'osh', 'jalal-abad',
    },

    'Turkmenistan': {
        'turkmenistan', 'turkmenistán', 'turkmen', 'turkmeno',
        'ashgabat', 'türkmenabat', 'mary', 'balkanabat',
    },

    'Azerbaijan': {
        'azerbaijan', 'azerbaiyán', 'azerbaijani', 'azerbaiyano', 'azeri',
        'baku', 'bakú', 'ganja', 'sumqayit',
    },

    'Georgia (country)': {
        'georgia', 'georgian', 'georgiano', 'kartvelian',
        'tbilisi', 'tiflis', 'kutaisi', 'batumi', 'rustavi',
    },

    'Armenia': {
        'armenia', 'armenian', 'armenio', 'armeniaca', 'hayastan',
        'yerevan', 'ereván', 'gyumri', 'vanadzor',
    },

    # =========================================================================
    # ÁFRICA DEL NORTE
    # =========================================================================
    'Egypt': {
        'egypt', 'egipto', 'egyptian', 'egipcio', 'egipcia', 'masri', 'masriyyin',
        'cairo', 'el cairo', 'al qahira', 'alexandria', 'alejandría',
        'giza', 'luxor', 'aswan', 'port said', 'suez', 'ismailia',
        'tanta', 'mansoura', 'asyut',
    },

    'Morocco': {
        'morocco', 'marruecos', 'moroccan', 'marroquí', 'marroquíes', 'maghribi',
        'casablanca', 'dar el beida', 'rabat', 'fes', 'fez',
        'marrakech', 'marrakesh', 'tangier', 'tánger', 'agadir',
        'meknes', 'oujda', 'kenitra', 'tetouan', 'sale', 'salé',
    },

    'Algeria': {
        'algeria', 'argelia', 'algerian', 'argelino', 'argelina', 'jazairi',
        'algiers', 'argel', 'alger', 'oran', 'orán', 'constantine',
        'annaba', 'blida', 'batna', 'sétif', 'tlemcen',
    },

    'Tunisia': {
        'tunisia', 'túnez', 'tunisian', 'tunecino', 'tunisien',
        'tunis', 'sfax', 'sousse', 'soussa', 'kairouan', 'bizerte',
        'gabes', 'monastir',
    },

    'Libya': {
        'libya', 'libia', 'libyan', 'libio', 'libi',
        'tripoli', 'trípoli', 'benghazi', 'bengasi', 'misrata', 'bayda',
    },

    'Sudan': {
        'sudan', 'sudán', 'sudanese', 'sudanés', 'sudani',
        'khartoum', 'jartum', 'omdurman', 'port sudan', 'kassala',
    },

    # =========================================================================
    # ÁFRICA OCCIDENTAL
    # =========================================================================
    'Nigeria': {
        'nigeria', 'nigerian', 'nigeriano', 'nigeriana', 'naija',
        'yoruba', 'igbo', 'hausa', 'fulani',
        'lagos', 'kano', 'ibadan', 'abuja', 'port harcourt',
        'benin city', 'maiduguri', 'zaria', 'aba', 'jos',
        'ilorin', 'onitsha', 'warri', 'kaduna', 'enugu',
    },

    'Ghana': {
        'ghana', 'ghanaian', 'ghanés', 'ghanesa', 'ghanaian',
        'akan', 'ashanti', 'akan', 'ewe',
        'accra', 'kumasi', 'tamale', 'sekondi-takoradi',
        'cape coast', 'sunyani', 'koforidua',
    },

    'Ivory Coast': {
        'ivory coast', 'côte d\'ivoire', 'cote d\'ivoire', 'costa de marfil',
        'ivorian', 'ivoriano', 'ivoirien',
        'abidjan', 'bouaké', 'daloa', 'san-pédro', 'yamoussoukro',
    },

    'Senegal': {
        'senegal', 'senegalese', 'senegalés', 'sénégalais',
        'wolof', 'serer', 'pulaar',
        'dakar', 'thiès', 'kaolack', 'ziguinchor', 'saint-louis',
    },

    'Mali': {
        'mali', 'malian', 'maliano',
        'bamako', 'segou', 'mopti', 'timbuktu', 'tombouctou', 'kayes',
    },

    'Guinea': {
        'guinea', 'guinean', 'guineano', 'guinéen',
        'conakry', 'nzérékoré', 'kindia', 'kankan',
    },

    "Burkina Faso": {
        'burkina faso', 'burkinabe', 'burkinabé', 'burkinafasien',
        'ouagadougou', 'bobo-dioulasso', 'koudougou',
    },

    'Togo': {
        'togo', 'togolese', 'togolés',
        'lomé', 'sokodé', 'kara',
    },

    'Benin': {
        'benin', 'beninese', 'beninés', 'béninois',
        'cotonou', 'porto-novo', 'parakou',
    },

    'Cameroon': {
        'cameroon', 'camerún', 'cameroonian', 'camerunés', 'camerounais',
        'douala', 'yaoundé', 'garoua', 'bamenda', 'maroua',
    },

    'Cape Verde': {
        'cape verde', 'cabo verde', 'cap-vert', 'cape verdean', 'caboverdiano',
        'praia', 'mindelo', 'sal',
    },

    'Guinea-Bissau': {
        'guinea-bissau', 'guinea bisáu', 'guinean', 'guineense',
        'bissau', 'bafata',
    },

    'Mauritania': {
        'mauritania', 'mauritanian', 'mauritano', 'mauritanien',
        'nouakchott', 'nouadhibou', 'kiffa',
    },

    'Gambia': {
        'gambia', 'gambian', 'gambiano',
        'banjul', 'serekunda', 'brikama',
    },

    'Sierra Leone': {
        'sierra leone', 'sierra leonean', 'sierraleonés',
        'freetown', 'bo', 'kenema',
    },

    'Liberia': {
        'liberia', 'liberian', 'liberiano',
        'monrovia', 'gbarnga', 'buchanan',
    },

    'Niger': {
        'niger', 'nigerien', 'nigerino',
        'niamey', 'zinder', 'maradi', 'agadez',
    },

    # =========================================================================
    # ÁFRICA ORIENTAL
    # =========================================================================
    'Kenya': {
        'kenya', 'kenia', 'kenyan', 'keniano', 'keniana', 'kenyan',
        'kikuyu', 'luo', 'kalenjin', 'kamba',
        'nairobi', 'mombasa', 'kisumu', 'nakuru', 'eldoret',
        'thika', 'nyeri', 'malindi', 'machakos',
    },

    'Tanzania': {
        'tanzania', 'tanzanian', 'tanzano', 'mtanzania',
        'dar es salaam', 'dodoma', 'mwanza', 'zanzibar',
        'arusha', 'mbeya', 'morogoro', 'tanga',
    },

    'Uganda': {
        'uganda', 'ugandan', 'ugandés', 'muganda',
        'kampala', 'gulu', 'lira', 'mbarara', 'jinja',
    },

    'Rwanda': {
        'rwanda', 'ruanda', 'rwandan', 'ruandés', 'nyarwanda',
        'kigali', 'butare', 'muhanga', 'musanze', 'gisenyi',
    },

    'Ethiopia': {
        'ethiopia', 'etiopía', 'ethiopian', 'etíope', 'ityopiawi',
        'amhara', 'oromo', 'tigrinya',
        'addis ababa', 'dire dawa', 'mekelle', 'gondar', 'adama',
        'jimma', 'awasa', 'bahir dar', 'harar',
    },

    'Somalia': {
        'somalia', 'somali', 'somalí', 'soomaali',
        'mogadishu', 'muqdisho', 'hargeisa', 'kismayo', 'berbera',
    },

    'Eritrea': {
        'eritrea', 'eritrean', 'eritreo',
        'asmara', 'asmera', 'keren', 'massawa',
    },

    'Djibouti': {
        'djibouti', 'yibuti', 'djiboutian', 'yibutiano',
        'djibouti city', 'ciudad de yibuti',
    },

    'Mozambique': {
        'mozambique', 'mozambican', 'mozambiqueño', 'mozambicano',
        'maputo', 'beira', 'nampula', 'tete', 'quelimane',
    },

    'Madagascar': {
        'madagascar', 'malagasy', 'malgache', 'malgacho',
        'antananarivo', 'toamasina', 'antsirabe', 'fianarantsoa',
    },

    'Mauritius': {
        'mauritius', 'mauricio', 'mauritian', 'mauriciano',
        'port louis', 'beau bassin', 'vacoas', 'curepipe',
    },

    'Zimbabwe': {
        'zimbabwe', 'zimbabuense', 'zimbabwean', 'mhizwa',
        'harare', 'bulawayo', 'chitungwiza', 'mutare',
    },

    'Zambia': {
        'zambia', 'zambian', 'zambiano',
        'lusaka', 'kitwe', 'ndola', 'livingstone',
    },

    'Malawi': {
        'malawi', 'malawian', 'malawiano',
        'lilongwe', 'blantyre', 'mzuzu',
    },

    # =========================================================================
    # ÁFRICA CENTRAL
    # =========================================================================
    'Democratic Republic of Congo': {
        'democratic republic of congo', 'drc', 'congo dr', 'república democrática del congo',
        'congolese', 'congoleño', 'mukongó',
        'kinshasa', 'lubumbashi', 'mbuji-mayi', 'kananga', 'kisangani',
        'goma', 'bukavu',
    },

    'Republic of Congo': {
        'republic of congo', 'congo', 'congo-brazzaville', 'república del congo',
        'brazzaville', 'pointe-noire', 'dolisie',
    },

    'Angola': {
        'angola', 'angolan', 'angoleño', 'angolano', 'angolana',
        'luanda', 'huambo', 'lobito', 'benguela', 'lubango',
        'kuito', 'malanje', 'namibe',
    },

    'Gabon': {
        'gabon', 'gabón', 'gabonese', 'gabonés',
        'libreville', 'port-gentil', 'franceville',
    },

    'Central African Republic': {
        'central african republic', 'república centroafricana', 'centrafricain',
        'bangui',
    },

    # =========================================================================
    # ÁFRICA MERIDIONAL
    # =========================================================================
    'South Africa': {
        'south africa', 'sudáfrica', 'south african', 'sudafricano', 'sudafricana',
        'zulu', 'xhosa', 'sotho', 'tswana', 'coloured', 'afrikaner',
        'johannesburg', 'joburg', 'jozi', 'cape town', 'ciudad del cabo',
        'durban', 'pretoria', 'tshwane', 'port elizabeth',
        'gqeberha', 'bloemfontein', 'east london', 'pietermaritzburg',
        'soweto', 'benoni', 'tembisa', 'midrand', 'vereeniging',
        # Regiones
        'gauteng', 'kwazulu-natal', 'western cape', 'eastern cape',
        'northern cape', 'free state', 'limpopo', 'mpumalanga',
        'north west province',
    },

    'Namibia': {
        'namibia', 'namibian', 'namibiano',
        'windhoek', 'walvis bay', 'swakopmund',
    },

    'Botswana': {
        'botswana', 'botswanan', 'botsuanense', 'motswana',
        'gaborone', 'francistown', 'molepolole',
    },

    'Lesotho': {
        'lesotho', 'basotho', 'lesothan', 'mosotho',
        'maseru',
    },

    'Eswatini': {
        'eswatini', 'swaziland', 'swazi', 'swazilandes',
        'mbabane', 'manzini',
    },

    # =========================================================================
    # OCEANÍA
    # =========================================================================
    'Australia': {
        'australia', 'australian', 'australiano', 'australiana',
        'aussie', 'oz',
        # Ciudades
        'sydney', 'melbourne', 'brisbane', 'perth', 'adelaide',
        'canberra', 'gold coast', 'newcastle', 'wollongong', 'hobart',
        'darwin', 'townsville', 'geelong', 'cairns', 'toowoomba',
        # Regiones
        'new south wales', 'nsw', 'victoria', 'vic', 'queensland', 'qld',
        'western australia', 'wa', 'south australia', 'sa',
        'tasmania', 'tas', 'northern territory', 'nt', 'act',
    },

    'New Zealand': {
        'new zealand', 'nueva zelanda', 'nueva zelandia', 'nz', 'aotearoa',
        'kiwi', 'new zealander', 'neozelandés', 'māori', 'maori',
        'auckland', 'wellington', 'christchurch', 'hamilton',
        'dunedin', 'tauranga', 'palmerston north', 'napier', 'hastings',
    },

    'Papua New Guinea': {
        'papua new guinea', 'papua nueva guinea', 'png', 'papuan', 'papuano',
        'port moresby', 'lae', 'mt hagen', 'madang',
    },

    'Fiji': {
        'fiji', 'fijian', 'fiyiano',
        'suva', 'nadi', 'lautoka',
    },

    'Samoa': {
        'samoa', 'samoan', 'samoano',
        'apia', 'american samoa', 'samoa americana', 'pago pago',
    },

    'Tonga': {
        'tonga', 'tongan', 'tongano',
        "nuku'alofa",
    },

    'Hawaii': {
        'hawaii', 'hawái', 'hawaiian', 'hawaiano', 'kanaka maoli',
        'honolulu', 'hilo', 'kailua', 'pearl city',
    },

    'French Polynesia': {
        'french polynesia', 'polinesia francesa', 'polynesian', 'polinesio',
        'tahiti', 'tahití', 'bora bora', 'papeete', 'moorea',
    },

    'Solomon Islands': {
        'solomon islands', 'islas salomón', 'solomon islander',
        'honiara',
    },

    'Vanuatu': {
        'vanuatu', 'ni-vanuatu', 'vanuatense',
        'port vila', 'luganville',
    },
}


VARIANT_TO_COUNTRY: Dict[str, str] = {}
for country, variants in COUNTRIES_CANONICAL.items():
    for v in variants:
        VARIANT_TO_COUNTRY[v] = country

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip('.,;:¿?¡!()[]"\'«»…–—')
    return text

def validate_and_normalize_country(text: str) -> Optional[str]:
    if not text:
        return None

    text_norm = normalize_text(text)

    if text_norm in VARIANT_TO_COUNTRY:
        return VARIANT_TO_COUNTRY[text_norm]

    parts = [p.strip() for p in text_norm.split(',')]
    for part in reversed(parts):
        if part in VARIANT_TO_COUNTRY:
            return VARIANT_TO_COUNTRY[part]

    for variant, country in VARIANT_TO_COUNTRY.items():
        if variant in text_norm and len(variant) > 3:
            return country

    for country_canonical in COUNTRIES_CANONICAL.keys():
        if text_norm == country_canonical.lower():
            return country_canonical
        if text_norm.replace(' ', '') == country_canonical.lower().replace(' ', ''):
            return country_canonical

    return None

# ============================================================================
# DICCIONARIO DE GÉNEROS AMPLIADO (OK)
# ============================================================================

MACRO_GENRES = [
    'Aboriginal Australian Pop/Rock',
    'Afghan Pop/Rock',
    'Afrobeats',
    'Afro-soul',
    'Alpine Folk',
    'Alternative',
    'Amapiano',
    'Apala',
    'Arabic Pop/Rock',
    'Bachata',
    'Balochi Pop/Rock',
    'Bangladeshi Pop/Rock',
    'Benga',
    'Bhutanese Pop/Rock',
    'Bongo',
    'Bongo Flava',
    'Bruneian Pop/Rock',
    'Burmese Pop/Rock',
    'Cambodian Pop/Rock',
    'Canzone Italiana',
    'Chalga',
    'Chanson',
    'Classical',
    'Coladeira',
    'Country',
    'Coupé-Décalé',
    'Cumbia',
    'C-Pop/C-Rock',
    'Dancehall/Reggae',
    'Dansband',
    'Electrónica/Dance',
    'Electroswing',
    'Ethio-jazz',
    'Experimental/Prog/Art',
    'Flamenco / Copla',
    'Folklore/Raíces',
    'Fuji',
    'Funaná',
    'Funk Brasileiro',
    'Gengetone',
    'Gnawa',
    'Hawaiian Pop/Rock',
    'Highlife',
    'Hip-Hop/Rap',
    'HK-Pop/HK-Rock',
    'Hmong Pop/Rock',
    'Indian Pop',
    'Indonesian Pop/Dangdut',
    'Isicathamiya',
    'Iskelmä',
    'Israeli Pop/Rock',
    'Jazz/Blues',
    'Jùjú',
    'J-Pop/J-Rock',
    'Kapuka',
    'Karen Pop/Rock',
    'Kashmiri Pop/Rock',
    'Kizomba/Zouk',
    'Klezmer',
    'Kuduro',
    'Kurdish Pop/Rock',
    'Kwaito',
    'K-Pop/K-Rock',
    'Lao Pop/Rock',
    'Laïko',
    'Macanese Pop/Rock',
    'Malaysian Pop',
    'Maldivian Pop/Rock',
    'Manele',
    'Māori Pop/Rock',
    'Marrabenta',
    'Maskandi',
    'Mbaqanga',
    'Mbalax',
    'Mbube',
    'Metal',
    'Mongolian Pop/Rock/Metal',
    'Nepali Pop/Rock',
    'Northeast Indian Pop/Rock',
    'Ogene',
    'OPM',
    'Pacific Electronica',
    'Pakistani Pop',
    'Papuan Pop/Rock',
    'Pasifika Pop/Rock',
    'PNG Pop/Rock',
    'Pop',
    'Post-Punk/New Wave',
    'Punk',
    'Q-pop/Q-rock',
    'R&B/Soul',
    'Reggaetón/Trap Latino',
    'Regional Mexicano',
    'Rock',
    'Roma Music',
    'Sakara',
    'Schlager',
    'Sertanejo',
    'Shangaan Electro',
    'Siberian Indigenous Pop/Rock',
    'Singaporean Pop',
    'Soukous/Ndombolo',
    'Sri Lankan Pop/Rock',
    'Taarab',
    'Tallava',
    'Tibetan Pop/Rock',
    'Timorese Pop/Rock',
    'Torres Strait Islander Pop/Rock',
    'Tropical/Salsa/Merengue/Bolero',
    'Turkish Pop/Rock',
    'Turbo-folk',
    'T-Pop/T-Rock',
    'TW-Pop/TW-Rock',
    'Uyghur Pop/Rock',
    'Vallenato',
    'V-Pop/V-Rock',
    'Zim Dancehall'
]

GENRE_MAPPINGS = {
    ###############################################################################
    # Pop y derivados (occidental)
    ###############################################################################
    ## Pop mainstream
    'pop': ('Pop', 'pop'),
    'pops': ('Pop', 'pop'),
    'pop music': ('Pop', 'pop'),
    'musica pop': ('Pop', 'pop'),
    'contemporary pop': ('Pop', 'contemporary pop'),
    'mainstream pop': ('Pop', 'mainstream pop'),
    'vocal pop': ('Pop', 'vocal pop'),
    'traditional pop': ('Pop', 'traditional pop'),
    'pop tradicional': ('Pop', 'pop tradicional'),

    ## Dance pop
    'dance pop': ('Pop', 'dance pop'),
    'dance-pop': ('Pop', 'dance-pop'),
    'dancepop': ('Pop', 'dancepop'),

    ## Teen pop
    'teen pop': ('Pop', 'teen pop'),
    'teen-pop': ('Pop', 'teen-pop'),
    'teenpop': ('Pop', 'teenpop'),

    ## Power pop
    'power pop': ('Pop', 'power pop'),
    'power-pop': ('Pop', 'power-pop'),
    'powerpop': ('Pop', 'powerpop'),

    ## Synth pop / Electropop
    'synth pop': ('Pop', 'synth pop'),
    'synth-pop': ('Pop', 'synth-pop'),
    'synthpop': ('Pop', 'synthpop'),
    'electropop': ('Pop', 'electropop'),
    'electro pop': ('Pop', 'electro pop'),

    ## Bubblegum
    'bubblegum pop': ('Pop', 'bubblegum pop'),
    'bubblegum': ('Pop', 'bubblegum'),

    ## Pop rock
    'pop rock': ('Pop', 'pop rock'),
    'pop-rock': ('Pop', 'pop-rock'),
    'pop rock español': ('Pop', 'pop rock español'),

    ## Latin popwith dick
    'pop latino': ('Pop', 'pop latino'),
    'latin pop': ('Pop', 'latin pop'),

    ## Balada
    'balada': ('Pop', 'balada'),
    'balada romántica': ('Pop', 'balada romántica'),
    'balada pop': ('Pop', 'balada pop'),

    ## Singer-songwriter
    'singer songwriter': ('Pop', 'singer-songwriter'),
    'singer-songwriter': ('Pop', 'singer-songwriter'),
    'singer/songwriter': ('Pop', 'singer-songwriter'),
    'cantautor': ('Pop', 'singer-songwriter'),
    'cantautora': ('Pop', 'singer-songwriter'),
    'cantautor pop': ('Pop', 'singer-songwriter'),

    ## Chamber pop / Orchestral pop
    'chamber pop': ('Pop', 'chamber pop'),
    'chamber-pop': ('Pop', 'chamber-pop'),
    'chamber': ('Pop', 'chamber pop'),
    'orchestral pop': ('Pop', 'orchestral pop'),
    'orchestral-pop': ('Pop', 'orchestral-pop'),
    'symphonic pop': ('Pop', 'orchestral pop'),

    ## Baroque pop
    'baroque pop': ('Pop', 'baroque pop'),
    'baroque-pop': ('Pop', 'baroque-pop'),

    ## Sunshine pop
    'sunshine pop': ('Pop', 'sunshine pop'),

    ###############################################################################
    # Rock (género principal)
    ###############################################################################
    ## Rock & Roll
    'rock': ('Rock', 'rock'),
    'rock and roll': ('Rock', 'rock and roll'),
    'rock & roll': ('Rock', 'rock & roll'),
    'rock n roll': ('Rock', 'rock n roll'),
    'rocanrol': ('Rock', 'rocanrol'),
    'rockabilly': ('Rock', 'rockabilly'),

    ## Classic rock
    'classic rock': ('Rock', 'classic rock'),
    'rock clásico': ('Rock', 'rock clásico'),

    ## Hard rock
    'hard rock': ('Rock', 'hard rock'),
    'hard-rock': ('Rock', 'hard-rock'),

    ## Blues rock
    'blues rock': ('Rock', 'blues rock'),
    'blues-rock': ('Rock', 'blues-rock'),

    ## Folk rock
    'folk rock': ('Rock', 'folk rock'),
    'folk-rock': ('Rock', 'folk-rock'),

    ## Garage rock
    'garage rock': ('Rock', 'garage rock'),
    'garage-rock': ('Rock', 'garage-rock'),

    ## Glam rock
    'glam rock': ('Rock', 'glam rock'),
    'glam-rock': ('Rock', 'glam-rock'),

    ## Psychedelic rock
    'psychedelic rock': ('Rock', 'psychedelic rock'),
    'rock psicodélico': ('Rock', 'rock psicodélico'),

    ## Southern rock
    'southern rock': ('Rock', 'southern rock'),

    ## Roots rock
    'roots rock': ('Rock', 'roots rock'),
    'roots-rock': ('Rock', 'roots-rock'),

    ## Swamp rock
    'swamp rock': ('Rock', 'swamp rock'),
    'swamp-rock': ('Rock', 'swamp-rock'),

    ## Arena rock / Stadium rock
    'arena rock': ('Rock', 'arena rock'),
    'stadium rock': ('Rock', 'stadium rock'),

    ## Heartland rock
    'heartland rock': ('Rock', 'heartland rock'),

    ## Rock en español
    'rock en español': ('Rock', 'rock en español'),
    'rock español': ('Rock', 'rock español'),
    'rock latino': ('Rock', 'rock latino'),

    ## Soft rock
    'soft rock': ('Rock', 'soft rock'),

    ###############################################################################
    # Alternative Rock/Indie
    ###############################################################################
    ## Alternative general
    'alternative': ('Alternative', 'alternative'),
    'alternativo': ('Alternative', 'alternativo'),
    'rock alternativo': ('Alternative', 'rock alternativo'),
    'alternative rock': ('Alternative', 'alternative rock'),

    ## Indie
    'indie': ('Alternative', 'indie'),
    'indie rock': ('Alternative', 'indie rock'),
    'indie-rock': ('Alternative', 'indie-rock'),
    'indie folk': ('Alternative', 'indie folk'),

    ## Britpop
    'britpop': ('Alternative', 'britpop'),
    'brit pop': ('Alternative', 'brit pop'),
    'brit-pop': ('Alternative', 'brit-pop'),

    ## Grunge
    'grunge': ('Alternative', 'grunge'),
    'post-grunge': ('Alternative', 'post-grunge'),
    'post grunge': ('Alternative', 'post grunge'),

    ## Emo
    'emo': ('Alternative', 'emo'),
    'emo-pop': ('Alternative', 'emo-pop'),
    'emo pop': ('Alternative', 'emo pop'),
    'emopop': ('Alternative', 'emopop'),

    ## Shoegaze
    'shoegaze': ('Alternative', 'shoegaze'),
    'shoegazing': ('Alternative', 'shoegazing'),
    'uk shoegaze': ('Alternative', 'uk shoegaze'),

    ## Noise pop
    'noise pop': ('Alternative', 'noise pop'),
    'noise-pop': ('Alternative', 'noise-pop'),
    'noisepop': ('Alternative', 'noisepop'),

    ## Lo-fi
    'lo-fi': ('Alternative', 'lo-fi'),
    'lofi': ('Alternative', 'lofi'),
    'low fidelity': ('Alternative', 'lo-fi'),

    ## Post-hardcore
    'post-hardcore': ('Alternative', 'post-hardcore'),
    'post hardcore': ('Alternative', 'post hardcore'),
    'posthardcore': ('Alternative', 'posthardcore'),

    ## Slowcore / Sadcore
    'slowcore': ('Alternative', 'slowcore'),
    'slow core': ('Alternative', 'slow core'),
    'sadcore': ('Alternative', 'sadcore'),
    'sad core': ('Alternative', 'sad core'),

    ## College rock / Madchester / uk post-punk revival
    'madchester': ('Alternative', 'madchester'),
    'baggy': ('Alternative', 'baggy'),
    'c86': ('Alternative', 'c86'),
    'uk post-punk revival': ('Alternative', 'uk post-punk revival'),

    ###############################################################################
    # Metal
    ###############################################################################
    ## Heavy metal
    'metal': ('Metal', 'metal'),
    'heavy metal': ('Metal', 'heavy metal'),
    'heavy-metal': ('Metal', 'heavy-metal'),
    'traditional heavy metal': ('Metal', 'traditional heavy metal'),
    'trad heavy metal': ('Metal', 'trad heavy metal'),
    'nwobhm': ('Metal', 'nwobhm'),

    ## Thrash metal
    'thrash metal': ('Metal', 'thrash metal'),
    'thrash-metal': ('Metal', 'thrash-metal'),
    'thrash': ('Metal', 'thrash'),

    ## Death metal
    'death metal': ('Metal', 'death metal'),
    'death-metal': ('Metal', 'death-metal'),
    'death': ('Metal', 'death'),
    'melodic death metal': ('Metal', 'melodic death metal'),
    'melodeath': ('Metal', 'melodeath'),
    'technical death metal': ('Metal', 'technical death metal'),
    'tech death': ('Metal', 'tech death'),
    'brutal death metal': ('Metal', 'brutal death metal'),

    ## Black metal
    'black metal': ('Metal', 'black metal'),
    'black-metal': ('Metal', 'black-metal'),
    'black': ('Metal', 'black'),
    'atmospheric black metal': ('Metal', 'atmospheric black metal'),
    'symphonic black metal': ('Metal', 'symphonic black metal'),
    'depressive black metal': ('Metal', 'depressive black metal'),
    'dsbm': ('Metal', 'dsbm'),
    'raw black metal': ('Metal', 'raw black metal'),

    ## Power metal
    'power metal': ('Metal', 'power metal'),
    'power-metal': ('Metal', 'power-metal'),
    'power': ('Metal', 'power'),
    'epic power metal': ('Metal', 'epic power metal'),
    'symphonic power metal': ('Metal', 'symphonic power metal'),

    ## Nu metal
    'nu metal': ('Metal', 'nu metal'),
    'nu-metal': ('Metal', 'nu-metal'),
    'nü-metal': ('Metal', 'nü-metal'),

    ## Metalcore / Deathcore
    'metalcore': ('Metal', 'metalcore'),
    'metal core': ('Metal', 'metal core'),
    'melodic metalcore': ('Metal', 'melodic metalcore'),
    'deathcore': ('Metal', 'deathcore'),
    'death core': ('Metal', 'death core'),

    ## Doom metal
    'doom metal': ('Metal', 'doom metal'),
    'doom-metal': ('Metal', 'doom-metal'),
    'doom': ('Metal', 'doom'),
    'epic doom': ('Metal', 'epic doom'),
    'funeral doom': ('Metal', 'funeral doom'),
    'death-doom': ('Metal', 'death-doom'),
    'death doom': ('Metal', 'death doom'),

    ## Gothic metal
    'gothic metal': ('Metal', 'gothic metal'),
    'gothic-metal': ('Metal', 'gothic-metal'),
    'goth metal': ('Metal', 'goth metal'),

    ## Symphonic metal
    'symphonic metal': ('Metal', 'symphonic metal'),
    'symphonic-metal': ('Metal', 'symphonic-metal'),
    'symphonic': ('Metal', 'symphonic'),

    ## Folk metal / Pagan metal (ampliado)
    'folk metal': ('Metal', 'folk metal'),
    'folk-metal': ('Metal', 'folk-metal'),
    'pagan metal': ('Metal', 'pagan metal'),
    'viking metal': ('Metal', 'viking metal'),
    'viking-metal': ('Metal', 'viking-metal'),
    'celtic metal': ('Metal', 'celtic metal'),
    'medieval metal': ('Metal', 'medieval metal'),
    'nordic folk metal': ('Metal', 'nordic folk metal'),
    'eastern european folk metal': ('Metal', 'eastern european folk metal'),
    'hurdy gurdy metal': ('Metal', 'hurdy gurdy metal'),
    'bagpipe metal': ('Metal', 'bagpipe metal'),

    ## Groove metal
    'groove metal': ('Metal', 'groove metal'),
    'groove-metal': ('Metal', 'groove-metal'),
    'post-thrash': ('Metal', 'post-thrash'),

    ## Industrial metal
    'industrial metal': ('Metal', 'industrial metal'),
    'industrial-metal': ('Metal', 'industrial-metal'),

    ## Alternative metal
    'alternative metal': ('Metal', 'alternative metal'),
    'alt-metal': ('Metal', 'alt-metal'),

    ## Glam metal
    'glam metal': ('Metal', 'glam metal'),
    'glam-metal': ('Metal', 'glam-metal'),
    'hair metal': ('Metal', 'hair metal'),
    'pop metal': ('Metal', 'pop metal'),

    ## Speed metal
    'speed metal': ('Metal', 'speed metal'),
    'speed-metal': ('Metal', 'speed-metal'),

    ## Crossover / Grindcore
    'crossover thrash': ('Metal', 'crossover thrash'),
    'grindcore': ('Metal', 'grindcore'),
    'grind': ('Metal', 'grind'),
    'goregrind': ('Metal', 'goregrind'),
    'pornogrind': ('Metal', 'pornogrind'),

    ## Rap metal / Rapeore
    'rap metal': ('Metal', 'rap metal'),
    'rap-metal': ('Metal', 'rap-metal'),
    'rapcore': ('Metal', 'rapcore'),

    ###############################################################################
    # Punk
    ###############################################################################
    ## Punk general
    'punk': ('Punk', 'punk'),
    'punk rock': ('Punk', 'punk rock'),
    'punk-rock': ('Punk', 'punk-rock'),

    ## Hardcore punk
    'hardcore punk': ('Punk', 'hardcore punk'),
    'hardcore-punk': ('Punk', 'hardcore-punk'),
    'hardcore': ('Punk', 'hardcore'),

    ## Pop punk
    'pop punk': ('Punk', 'pop punk'),
    'pop-punk': ('Punk', 'pop-punk'),
    'punk pop': ('Punk', 'punk pop'),
    'punk-pop': ('Punk', 'punk-pop'),
    'happy punk': ('Punk', 'happy punk'),
    'happy-punk': ('Punk', 'happy-punk'),

    ## Ska punk
    'ska punk': ('Punk', 'ska punk'),
    'ska-punk': ('Punk', 'ska-punk'),

    ## Folk punk / Celtic punk
    'celtic punk': ('Punk', 'celtic punk'),
    'folk punk': ('Punk', 'folk punk'),

    ## Anarcho-punk
    'anarcho-punk': ('Punk', 'anarcho-punk'),
    'anarchopunk': ('Punk', 'anarchopunk'),

    ## Crust punk / D-beat
    'crust punk': ('Punk', 'crust punk'),
    'crust': ('Punk', 'crust'),
    'd-beat': ('Punk', 'd-beat'),
    'dbeat': ('Punk', 'dbeat'),

    ## Street punk
    'street punk': ('Punk', 'street punk'),
    'streetpunk': ('Punk', 'streetpunk'),

    ## Horror punk
    'horror punk': ('Punk', 'horror punk'),

    ## Garage punk
    'garage punk': ('Punk', 'garage punk'),
    'garage-punk': ('Punk', 'garage-punk'),

    ## Cowpunk
    'cowpunk': ('Punk', 'cowpunk'),
    'cow punk': ('Punk', 'cow punk'),

    ## Deathrock
    'deathrock': ('Punk', 'deathrock'),
    'death rock': ('Punk', 'death rock'),

    ## Psychobilly
    'psychobilly': ('Punk', 'psychobilly'),

    ## Punk blues
    'punk blues': ('Punk', 'punk blues'),

    ## Queercore / Riot grrrl
    'riot grrrl': ('Punk', 'riot grrrl'),
    'queercore': ('Punk', 'queercore'),
    'taqwacore': ('Punk', 'taqwacore'),
    'gypsy punk': ('Punk', 'gypsy punk'),

    ###############################################################################
    # Post-Punk / New Wave
    ###############################################################################
    ## Post-punk general
    'post-punk': ('Post-Punk/New Wave', 'post-punk'),
    'post punk': ('Post-Punk/New Wave', 'post punk'),
    'postpunk': ('Post-Punk/New Wave', 'postpunk'),

    ## New wave
    'new wave': ('Post-Punk/New Wave', 'new wave'),
    'nueva ola': ('Post-Punk/New Wave', 'nueva ola'),

    ## Gothic rock
    'gothic rock': ('Post-Punk/New Wave', 'gothic rock'),
    'gothic-rock': ('Post-Punk/New Wave', 'gothic-rock'),
    'rock gótico': ('Post-Punk/New Wave', 'rock gótico'),

    ## Darkwave / Coldwave
    'darkwave': ('Post-Punk/New Wave', 'darkwave'),
    'dark wave': ('Post-Punk/New Wave', 'dark wave'),
    'coldwave': ('Post-Punk/New Wave', 'coldwave'),
    'cold wave': ('Post-Punk/New Wave', 'cold wave'),

    ## Ethereal wave
    'ethereal wave': ('Post-Punk/New Wave', 'ethereal wave'),
    'ethereal': ('Post-Punk/New Wave', 'ethereal'),

    ## Minimal wave
    'minimal wave': ('Post-Punk/New Wave', 'minimal wave'),

    ## Synthwave
    'synthwave': ('Post-Punk/New Wave', 'synthwave'),
    'synth wave': ('Post-Punk/New Wave', 'synth wave'),

    ## Electroclash
    'electroclash': ('Post-Punk/New Wave', 'electroclash'),

    ## Dance-punk
    'dance-punk': ('Post-Punk/New Wave', 'dance-punk'),
    'dance punk': ('Post-Punk/New Wave', 'dance punk'),

    ## No wave
    'no wave': ('Post-Punk/New Wave', 'no wave'),
    'nowave': ('Post-Punk/New Wave', 'nowave'),

    ## Yacht rock
    'yacht rock': ('Post-Punk/New Wave', 'yacht rock'),

    ## Revivals
    'post-punk revival': ('Post-Punk/New Wave', 'post-punk revival'),
    'new wave revival': ('Post-Punk/New Wave', 'new wave revival'),
    'indie sleaze': ('Post-Punk/New Wave', 'indie sleaze'),

    ###############################################################################
    # Experimental/Prog/Art
    ###############################################################################
    ## Progressive rock
    'progressive': ('Experimental/Prog/Art', 'progressive'),
    'prog': ('Experimental/Prog/Art', 'prog'),
    'prog rock': ('Experimental/Prog/Art', 'prog rock'),
    'prog-rock': ('Experimental/Prog/Art', 'prog-rock'),
    'progressive rock': ('Experimental/Prog/Art', 'progressive rock'),
    'rock progresivo': ('Experimental/Prog/Art', 'rock progresivo'),

    ## Progressive metal
    'prog metal': ('Experimental/Prog/Art', 'prog metal'),
    'prog-metal': ('Experimental/Prog/Art', 'prog-metal'),
    'progressive metal': ('Experimental/Prog/Art', 'progressive metal'),
    'metal progresivo': ('Experimental/Prog/Art', 'metal progresivo'),

    ## Art rock / Art pop
    'art rock': ('Experimental/Prog/Art', 'art rock'),
    'art-rock': ('Experimental/Prog/Art', 'art-rock'),
    'art pop': ('Experimental/Prog/Art', 'art pop'),
    'art-pop': ('Experimental/Prog/Art', 'art-pop'),
    'artpop': ('Experimental/Prog/Art', 'artpop'),

    ## Avant-garde
    'avant-garde': ('Experimental/Prog/Art', 'avant-garde'),
    'vanguardia': ('Experimental/Prog/Art', 'vanguardia'),
    'avant prog': ('Experimental/Prog/Art', 'avant prog'),
    'avant-prog': ('Experimental/Prog/Art', 'avant-prog'),
    'avant pop': ('Experimental/Prog/Art', 'avant pop'),
    'avant-pop': ('Experimental/Prog/Art', 'avant-pop'),
    'experimental pop': ('Experimental/Prog/Art', 'experimental pop'),

    ## Pop psicodélico
    'pop psicodélico': ('Experimental/Prog/Art', 'pop psicodélico'),
    'psychedelic pop': ('Experimental/Prog/Art', 'psychedelic pop'),

    ## Post-rock
    'post-rock': ('Experimental/Prog/Art', 'post-rock'),
    'post rock': ('Experimental/Prog/Art', 'post rock'),

    ## Math rock / Mathcore
    'math rock': ('Experimental/Prog/Art', 'math rock'),
    'math-rock': ('Experimental/Prog/Art', 'math-rock'),
    'mathcore': ('Experimental/Prog/Art', 'mathcore'),
    'math core': ('Experimental/Prog/Art', 'math core'),

    ## Djent
    'djent': ('Experimental/Prog/Art', 'djent'),

    ## Krautrock
    'krautrock': ('Experimental/Prog/Art', 'krautrock'),

    ## Symphonic rock
    'symphonic rock': ('Experimental/Prog/Art', 'symphonic rock'),
    'rock sinfónico': ('Experimental/Prog/Art', 'rock sinfónico'),

    ## Space rock
    'space rock': ('Experimental/Prog/Art', 'space rock'),
    'space-rock': ('Experimental/Prog/Art', 'space-rock'),

    ## Canterbury scene / RIO / Zeuhl
    'canterbury': ('Experimental/Prog/Art', 'canterbury'),
    'canterbury scene': ('Experimental/Prog/Art', 'canterbury scene'),
    'rio': ('Experimental/Prog/Art', 'rio'),
    'rock in opposition': ('Experimental/Prog/Art', 'rock in opposition'),
    'zeuhl': ('Experimental/Prog/Art', 'zeuhl'),

    ## Música concreta / Electroacústica
    'musique concrete': ('Experimental/Prog/Art', 'musique concrete'),
    'música concreta': ('Experimental/Prog/Art', 'música concreta'),
    'electroacoustic': ('Experimental/Prog/Art', 'electroacoustic'),
    'electroacústica': ('Experimental/Prog/Art', 'electroacústica'),

    ## Noise / Drone
    'noise': ('Experimental/Prog/Art', 'noise'),
    'noise music': ('Experimental/Prog/Art', 'noise music'),
    'drone': ('Experimental/Prog/Art', 'drone'),
    'drone music': ('Experimental/Prog/Art', 'drone music'),

    ## Experimental electrónica / Glitch
    'experimental electronic': ('Experimental/Prog/Art', 'experimental electronic'),
    'electrónica experimental': ('Experimental/Prog/Art', 'electrónica experimental'),
    'glitch': ('Experimental/Prog/Art', 'glitch'),
    'glitch music': ('Experimental/Prog/Art', 'glitch music'),
    'idm': ('Experimental/Prog/Art', 'idm'),
    'braindance': ('Experimental/Prog/Art', 'braindance'),

    ## Minimalismo
    'minimalism': ('Experimental/Prog/Art', 'minimalism'),
    'minimalismo': ('Experimental/Prog/Art', 'minimalismo'),
    'minimal music': ('Experimental/Prog/Art', 'minimal music'),

    ###############################################################################
    # Hip-Hop/Rap/Trap (anglo)
    ###############################################################################
    ## General
    'hip hop': ('Hip-Hop/Rap', 'hip hop'),
    'hip-hop': ('Hip-Hop/Rap', 'hip-hop'),
    'hiphop': ('Hip-Hop/Rap', 'hiphop'),
    'rap': ('Hip-Hop/Rap', 'rap'),

    ## Trap y derivados
    'trap': ('Hip-Hop/Rap', 'trap'),
    'trap anglo': ('Hip-Hop/Rap', 'trap anglo'),
    'cloud rap': ('Hip-Hop/Rap', 'cloud rap'),
    'mumble rap': ('Hip-Hop/Rap', 'mumble rap'),

    ## Drill
    'drill': ('Hip-Hop/Rap', 'drill'),
    'uk drill': ('Hip-Hop/Rap', 'uk drill'),
    'chicago drill': ('Hip-Hop/Rap', 'chicago drill'),
    'brooklyn drill': ('Hip-Hop/Rap', 'brooklyn drill'),

    ## Gangsta rap / G-funk
    'gangsta rap': ('Hip-Hop/Rap', 'gangsta rap'),
    'g-funk': ('Hip-Hop/Rap', 'g-funk'),
    'gfunk': ('Hip-Hop/Rap', 'gfunk'),

    ## Conscious rap / Political hip-hop
    'conscious rap': ('Hip-Hop/Rap', 'conscious rap'),
    'rap conciencia': ('Hip-Hop/Rap', 'rap conciencia'),
    'political hip-hop': ('Hip-Hop/Rap', 'political hip-hop'),
    'political rap': ('Hip-Hop/Rap', 'political rap'),

    ## Escenas regionales (US)
    'east coast': ('Hip-Hop/Rap', 'east coast'),
    'east coast hip hop': ('Hip-Hop/Rap', 'east coast hip hop'),
    'west coast': ('Hip-Hop/Rap', 'west coast'),
    'west coast hip hop': ('Hip-Hop/Rap', 'west coast hip hop'),
    'southern rap': ('Hip-Hop/Rap', 'southern rap'),
    'dirty south': ('Hip-Hop/Rap', 'dirty south'),
    'southern hip hop': ('Hip-Hop/Rap', 'southern hip hop'),

    ## Old school
    'old school rap': ('Hip-Hop/Rap', 'old school rap'),
    'old school hip hop': ('Hip-Hop/Rap', 'old school hip hop'),

    ## Rap rock (solo el que no está en Metal)
    'rap rock': ('Hip-Hop/Rap', 'rap rock'),
    'rap-rock': ('Hip-Hop/Rap', 'rap-rock'),

    ## Alternative hip hop
    'alternative hip hop': ('Hip-Hop/Rap', 'alternative hip hop'),
    'hip hop alternativo': ('Hip-Hop/Rap', 'hip hop alternativo'),

    ## Jazz rap
    'jazz rap': ('Hip-Hop/Rap', 'jazz rap'),
    'jazz-rap': ('Hip-Hop/Rap', 'jazz-rap'),

    ## Horrorcore
    'horrorcore': ('Hip-Hop/Rap', 'horrorcore'),

    ## Boom bap
    'boom bap': ('Hip-Hop/Rap', 'boom bap'),
    'boombap': ('Hip-Hop/Rap', 'boombap'),

    ## Hardcore hip hop
    'hardcore hip hop': ('Hip-Hop/Rap', 'hardcore hip hop'),

    ## Turntablism / Instrumental
    'turntablism': ('Hip-Hop/Rap', 'turntablism'),
    'instrumental hip hop': ('Hip-Hop/Rap', 'instrumental hip hop'),

    ## Crunk
    'crunk': ('Hip-Hop/Rap', 'crunk'),

    ## Snap music
    'snap music': ('Hip-Hop/Rap', 'snap music'),
    'snap': ('Hip-Hop/Rap', 'snap'),

    ## Hyphy
    'hyphy': ('Hip-Hop/Rap', 'hyphy'),

    ## Chopped and screwed
    'chopped and screwed': ('Hip-Hop/Rap', 'chopped and screwed'),
    'screwed': ('Hip-Hop/Rap', 'screwed'),

    ## Emo rap
    'emo rap': ('Hip-Hop/Rap', 'emo rap'),
    'emrap': ('Hip-Hop/Rap', 'emrap'),

    ## Soundcloud rap
    'soundcloud rap': ('Hip-Hop/Rap', 'soundcloud rap'),

    ## UK hip hop / Grime
    'uk hip hop': ('Hip-Hop/Rap', 'uk hip hop'),
    'british hip hop': ('Hip-Hop/Rap', 'british hip hop'),
    'grime': ('Hip-Hop/Rap', 'grime'),

    ## Abstract hip hop
    'abstract hip hop': ('Hip-Hop/Rap', 'abstract hip hop'),

    ## Christian hip hop
    'christian hip hop': ('Hip-Hop/Rap', 'christian hip hop'),
    'gospel rap': ('Hip-Hop/Rap', 'gospel rap'),

    ## Nerdcore
    'nerdcore': ('Hip-Hop/Rap', 'nerdcore'),

    ## Comedy rap
    'comedy rap': ('Hip-Hop/Rap', 'comedy rap'),

    ## Freestyle rap
    'freestyle': ('Hip-Hop/Rap', 'freestyle'),
    'freestyle rap': ('Hip-Hop/Rap', 'freestyle rap'),

    ## Battle rap
    'battle rap': ('Hip-Hop/Rap', 'battle rap'),

    ###############################################################################
    # Reggaetón/Trap Latino
    ###############################################################################
    ## Reggaetón general
    'reggaeton': ('Reggaetón/Trap Latino', 'reggaeton'),
    'reggaetón': ('Reggaetón/Trap Latino', 'reggaetón'),
    'regueton': ('Reggaetón/Trap Latino', 'regueton'),
    'reguetón': ('Reggaetón/Trap Latino', 'reguetón'),

    ## Trap latino
    'trap latino': ('Reggaetón/Trap Latino', 'trap latino'),
    'latin trap': ('Reggaetón/Trap Latino', 'latin trap'),

    ## Música urbana (latina)
    'urbano': ('Reggaetón/Trap Latino', 'urbano'),
    'música urbana': ('Reggaetón/Trap Latino', 'música urbana'),
    'latin urban': ('Reggaetón/Trap Latino', 'latin urban'),

    ## Subgéneros y estilos
    'dembow': ('Reggaetón/Trap Latino', 'dembow'),
    'perreo': ('Reggaetón/Trap Latino', 'perreo'),
    'malianteo': ('Reggaetón/Trap Latino', 'malianteo'),
    'guaracha': ('Reggaetón/Trap Latino', 'guaracha'),
    'rkt': ('Reggaetón/Trap Latino', 'rkt'),
    'neoperreo': ('Reggaetón/Trap Latino', 'neoperreo'),

    ## Reggaetón por temática
    'reggaeton romántico': ('Reggaetón/Trap Latino', 'reggaeton romántico'),
    'reggaetón romántico': ('Reggaetón/Trap Latino', 'reggaetón romántico'),
    'trap romántico': ('Reggaetón/Trap Latino', 'trap romántico'),
    'reggaeton consciente': ('Reggaetón/Trap Latino', 'reggaeton consciente'),
    'reggaetón consciente': ('Reggaetón/Trap Latino', 'reggaetón consciente'),
    'trap pesado': ('Reggaetón/Trap Latino', 'trap pesado'),

    ## Reggaetón clásico / old school
    'reggaeton clásico': ('Reggaetón/Trap Latino', 'reggaeton clásico'),
    'reggaetón clásico': ('Reggaetón/Trap Latino', 'reggaetón clásico'),
    'old school reggaeton': ('Reggaetón/Trap Latino', 'old school reggaeton'),

    ## Fusiones y derivados
    'reggaeton pop': ('Reggaetón/Trap Latino', 'reggaeton pop'),
    'pop reggaeton': ('Reggaetón/Trap Latino', 'pop reggaeton'),
    'trap pop': ('Reggaetón/Trap Latino', 'trap pop'),

    ## Escenas regionales
    'reggaeton puertorriqueño': ('Reggaetón/Trap Latino', 'reggaeton puertorriqueño'),
    'reggaeton colombiano': ('Reggaetón/Trap Latino', 'reggaeton colombiano'),
    'reggaeton argentino': ('Reggaetón/Trap Latino', 'reggaeton argentino'),
    'trap argentino': ('Reggaetón/Trap Latino', 'trap argentino'),
    'trap chileno': ('Reggaetón/Trap Latino', 'trap chileno'),
    'trap español': ('Reggaetón/Trap Latino', 'trap español'),

    ## Underground / Alternativo
    'underground reggaeton': ('Reggaetón/Trap Latino', 'underground reggaeton'),
    'alternativo urbano': ('Reggaetón/Trap Latino', 'alternativo urbano'),

    ## Maratones / Perreo intenso
    'perreo intenso': ('Reggaetón/Trap Latino', 'perreo intenso'),
    'perreo pesado': ('Reggaetón/Trap Latino', 'perreo pesado'),

    ###############################################################################
    # Electrónica/Dance
    ###############################################################################
    ## General
    'electronic': ('Electrónica/Dance', 'electronic'),
    'electrónica': ('Electrónica/Dance', 'electrónica'),
    'electronica': ('Electrónica/Dance', 'electronica'),
    'dance': ('Electrónica/Dance', 'dance'),
    'edm': ('Electrónica/Dance', 'edm'),
    'música electrónica': ('Electrónica/Dance', 'música electrónica'),

    ## House
    'house': ('Electrónica/Dance', 'house'),
    'deep house': ('Electrónica/Dance', 'deep house'),
    'progressive house': ('Electrónica/Dance', 'progressive house'),
    'tech house': ('Electrónica/Dance', 'tech house'),
    'tropical house': ('Electrónica/Dance', 'tropical house'),
    'electro house': ('Electrónica/Dance', 'electro house'),
    'future house': ('Electrónica/Dance', 'future house'),
    'garage house': ('Electrónica/Dance', 'garage house'),
    'chicago house': ('Electrónica/Dance', 'chicago house'),
    'french house': ('Electrónica/Dance', 'french house'),
    'italo house': ('Electrónica/Dance', 'italo house'),
    'latin house': ('Electrónica/Dance', 'latin house'),

    ## Techno
    'techno': ('Electrónica/Dance', 'techno'),
    'detroit techno': ('Electrónica/Dance', 'detroit techno'),
    'minimal techno': ('Electrónica/Dance', 'minimal techno'),
    'industrial techno': ('Electrónica/Dance', 'industrial techno'),
    'acid techno': ('Electrónica/Dance', 'acid techno'),

    ## Trance
    'trance': ('Electrónica/Dance', 'trance'),
    'psytrance': ('Electrónica/Dance', 'psytrance'),
    'progressive trance': ('Electrónica/Dance', 'progressive trance'),
    'uplifting trance': ('Electrónica/Dance', 'uplifting trance'),
    'vocal trance': ('Electrónica/Dance', 'vocal trance'),
    'goa trance': ('Electrónica/Dance', 'goa trance'),

    ## Dubstep / Bass
    'dubstep': ('Electrónica/Dance', 'dubstep'),
    'brostep': ('Electrónica/Dance', 'brostep'),
    'future bass': ('Electrónica/Dance', 'future bass'),
    'trap edm': ('Electrónica/Dance', 'trap edm'),

    ## Drum and Bass
    'drum and bass': ('Electrónica/Dance', 'drum and bass'),
    'drum & bass': ('Electrónica/Dance', 'drum & bass'),
    'dnb': ('Electrónica/Dance', 'dnb'),
    'liquid drum and bass': ('Electrónica/Dance', 'liquid drum and bass'),
    'jungle': ('Electrónica/Dance', 'jungle'),
    'neurofunk': ('Electrónica/Dance', 'neurofunk'),

    ## Ambient / Chill
    'ambient': ('Electrónica/Dance', 'ambient'),
    'chillout': ('Electrónica/Dance', 'chillout'),
    'chill': ('Electrónica/Dance', 'chill'),
    'downtempo': ('Electrónica/Dance', 'downtempo'),
    'lounge': ('Electrónica/Dance', 'lounge'),

    ## Synthwave / Vaporwave
    'vaporwave': ('Electrónica/Dance', 'vaporwave'),
    'chillwave': ('Electrónica/Dance', 'chillwave'),
    'retrowave': ('Electrónica/Dance', 'retrowave'),
    'dreamwave': ('Electrónica/Dance', 'dreamwave'),

    ## Electro
    'electro': ('Electrónica/Dance', 'electro'),

    ## Big Room / Mainstage
    'big room': ('Electrónica/Dance', 'big room'),
    'bigroom': ('Electrónica/Dance', 'bigroom'),
    'festival trap': ('Electrónica/Dance', 'festival trap'),
    'mainstage': ('Electrónica/Dance', 'mainstage'),

    ## Hardcore / Hardstyle
    'hardstyle': ('Electrónica/Dance', 'hardstyle'),
    'hardcore techno': ('Electrónica/Dance', 'hardcore techno'),
    'gabber': ('Electrónica/Dance', 'gabber'),
    'hard trance': ('Electrónica/Dance', 'hard trance'),
    'jumpstyle': ('Electrónica/Dance', 'jumpstyle'),

    ## UK Garage / Bassline
    'uk garage': ('Electrónica/Dance', 'uk garage'),
    'garage': ('Electrónica/Dance', 'garage'),
    '2-step': ('Electrónica/Dance', '2-step'),
    'bassline': ('Electrónica/Dance', 'bassline'),

    ## Disco / Nu-Disco
    'disco': ('Electrónica/Dance', 'disco'),
    'nu-disco': ('Electrónica/Dance', 'nu-disco'),
    'italo disco': ('Electrónica/Dance', 'italo disco'),
    'space disco': ('Electrónica/Dance', 'space disco'),

    ## Acid / Rave
    'acid house': ('Electrónica/Dance', 'acid house'),
    'acid': ('Electrónica/Dance', 'acid'),
    'rave': ('Electrónica/Dance', 'rave'),
    'old school rave': ('Electrónica/Dance', 'old school rave'),

    ## Schranz / Hard Techno
    'schranz': ('Electrónica/Dance', 'schranz'),
    'hard techno': ('Electrónica/Dance', 'hard techno'),
    'mainstream hardcore': ('Electrónica/Dance', 'mainstream hardcore'),
    'industrial hardcore': ('Electrónica/Dance', 'industrial hardcore'),
    'frenchcore': ('Electrónica/Dance', 'frenchcore'),
    'german hardcore': ('Electrónica/Dance', 'german hardcore'),
    'berlin techno': ('Electrónica/Dance', 'berlin techno'),
    'rotterdam techno': ('Electrónica/Dance', 'rotterdam techno'),

    ## Eurodance / Europop
    'eurodance': ('Electrónica/Dance', 'eurodance'),
    'euro house': ('Electrónica/Dance', 'euro house'),
    'euro techno': ('Electrónica/Dance', 'euro techno'),
    'german eurodance': ('Electrónica/Dance', 'german eurodance'),
    'italo dance': ('Electrónica/Dance', 'italo dance'),
    'swedish eurodance': ('Electrónica/Dance', 'swedish eurodance'),
    'dutch eurodance': ('Electrónica/Dance', 'dutch eurodance'),
    'europop': ('Electrónica/Dance', 'europop'),
    'scandinavian pop': ('Electrónica/Dance', 'scandinavian pop'),
    
    ## Phonk
    'phonk': ('Electrónica/Dance', 'phonk'),

    ###############################################################################
    # R&B / Soul (Global) - Ampliado con Funk
    ###############################################################################
    ## R&B General
    'rnb': ('R&B/Soul', 'rnb'),
    'r&b': ('R&B/Soul', 'r&b'),
    'r and b': ('R&B/Soul', 'r and b'),
    'rhythm and blues': ('R&B/Soul', 'rhythm and blues'),
    'rhythm & blues': ('R&B/Soul', 'rhythm & blues'),

    ## Funk (añadido)
    'funk': ('R&B/Soul', 'funk'),
    'funk music': ('R&B/Soul', 'funk music'),
    'p-funk': ('R&B/Soul', 'p-funk'),
    'funk rock': ('R&B/Soul', 'funk rock'),

    ## Soul General
    'soul': ('R&B/Soul', 'soul'),
    'soul music': ('R&B/Soul', 'soul music'),
    'soul clásico': ('R&B/Soul', 'soul clásico'),
    'classic soul': ('R&B/Soul', 'classic soul'),

    ## Contemporary R&B
    'contemporary r&b': ('R&B/Soul', 'contemporary r&b'),
    'contemporary rnb': ('R&B/Soul', 'contemporary rnb'),
    'r&b contemporáneo': ('R&B/Soul', 'r&b contemporáneo'),

    ## Neo-soul
    'neo soul': ('R&B/Soul', 'neo soul'),
    'neo-soul': ('R&B/Soul', 'neo-soul'),
    'neosoul': ('R&B/Soul', 'neosoul'),

    ## Alternative R&B
    'alternative r&b': ('R&B/Soul', 'alternative r&b'),
    'alternative rnb': ('R&B/Soul', 'alternative rnb'),
    'alt r&b': ('R&B/Soul', 'alt r&b'),
    'r&b alternativo': ('R&B/Soul', 'r&b alternativo'),
    'pbr&b': ('R&B/Soul', 'pbr&b'),

    ## Quiet storm
    'quiet storm': ('R&B/Soul', 'quiet storm'),

    ## New jack swing
    'new jack swing': ('R&B/Soul', 'new jack swing'),
    'new jack': ('R&B/Soul', 'new jack'),
    'jack swing': ('R&B/Soul', 'jack swing'),

    ## Funk soul
    'funk soul': ('R&B/Soul', 'funk soul'),
    'soul funk': ('R&B/Soul', 'soul funk'),

    ## Psychedelic soul
    'psychedelic soul': ('R&B/Soul', 'psychedelic soul'),
    'soul psicodélico': ('R&B/Soul', 'soul psicodélico'),

    ## Blue-eyed soul
    'blue eyed soul': ('R&B/Soul', 'blue eyed soul'),
    'blue-eyed soul': ('R&B/Soul', 'blue-eyed soul'),

    ## Trap soul
    'trap soul': ('R&B/Soul', 'trap soul'),
    'trap r&b': ('R&B/Soul', 'trap r&b'),

    ## R&B latino
    'r&b latino': ('R&B/Soul', 'r&b latino'),
    'latin r&b': ('R&B/Soul', 'latin r&b'),
    'rnb latino': ('R&B/Soul', 'rnb latino'),

    ## Northern soul
    'northern soul': ('R&B/Soul', 'northern soul'),

    ## Southern soul
    'southern soul': ('R&B/Soul', 'southern soul'),

    ## Motown soul
    'motown': ('R&B/Soul', 'motown'),
    'motown soul': ('R&B/Soul', 'motown soul'),
    'motown sound': ('R&B/Soul', 'motown sound'),

    ## Philly soul
    'philly soul': ('R&B/Soul', 'philly soul'),
    'philadelphia soul': ('R&B/Soul', 'philadelphia soul'),

    ## Chicago soul
    'chicago soul': ('R&B/Soul', 'chicago soul'),

    ## Memphis soul
    'memphis soul': ('R&B/Soul', 'memphis soul'),

    ## Deep soul
    'deep soul': ('R&B/Soul', 'deep soul'),

    ## Gospel soul
    'gospel soul': ('R&B/Soul', 'gospel soul'),

    ## Smooth soul
    'smooth soul': ('R&B/Soul', 'smooth soul'),

    ## Urban contemporary
    'urban contemporary': ('R&B/Soul', 'urban contemporary'),
    'urban r&b': ('R&B/Soul', 'urban r&b'),

    ## Slow jam
    'slow jam': ('R&B/Soul', 'slow jam'),
    'slow jams': ('R&B/Soul', 'slow jams'),

    ###############################################################################
    # Jazz / Blues (Global)
    ###############################################################################
    ## Jazz General
    'jazz': ('Jazz/Blues', 'jazz'),
    'jazz music': ('Jazz/Blues', 'jazz music'),

    ## Jazz tradicional / Dixieland
    'trad jazz': ('Jazz/Blues', 'trad jazz'),
    'traditional jazz': ('Jazz/Blues', 'traditional jazz'),
    'dixieland': ('Jazz/Blues', 'dixieland'),
    'new orleans jazz': ('Jazz/Blues', 'new orleans jazz'),

    ## Swing / Big band
    'swing': ('Jazz/Blues', 'swing'),
    'big band': ('Jazz/Blues', 'big band'),
    'bigband': ('Jazz/Blues', 'bigband'),

    ## Bebop
    'bebop': ('Jazz/Blues', 'bebop'),
    'bop': ('Jazz/Blues', 'bop'),

    ## Cool jazz
    'cool jazz': ('Jazz/Blues', 'cool jazz'),
    'west coast jazz': ('Jazz/Blues', 'west coast jazz'),

    ## Hard bop
    'hard bop': ('Jazz/Blues', 'hard bop'),

    ## Free jazz
    'free jazz': ('Jazz/Blues', 'free jazz'),
    'avant-garde jazz': ('Jazz/Blues', 'avant-garde jazz'),

    ## Smooth jazz
    'smooth jazz': ('Jazz/Blues', 'smooth jazz'),

    ## Acid jazz
    'acid jazz': ('Jazz/Blues', 'acid jazz'),

    ## Soul jazz
    'soul jazz': ('Jazz/Blues', 'soul jazz'),

    ## Blues General
    'blues': ('Jazz/Blues', 'blues'),
    'blues music': ('Jazz/Blues', 'blues music'),

    ## Delta blues
    'delta blues': ('Jazz/Blues', 'delta blues'),

    ## Chicago blues
    'chicago blues': ('Jazz/Blues', 'chicago blues'),
    'electric blues': ('Jazz/Blues', 'electric blues'),

    ## Rhythm and blues (clásico)
    'rhythm and blues clasico': ('Jazz/Blues', 'rhythm and blues clasico'),
    'r&b clasico': ('Jazz/Blues', 'r&b clasico'),
    'classic r&b': ('Jazz/Blues', 'classic r&b'),

    ## Otros blues
    'piedmont blues': ('Jazz/Blues', 'piedmont blues'),
    'texas blues': ('Jazz/Blues', 'texas blues'),
    'memphis blues': ('Jazz/Blues', 'memphis blues'),
    'swamp blues': ('Jazz/Blues', 'swamp blues'),
    'british blues': ('Jazz/Blues', 'british blues'),
    'country blues': ('Jazz/Blues', 'country blues'),

    ###############################################################################
    # Folklore / Raíces (Global)
    ###############################################################################
    ## Folklore General
    'folklore': ('Folklore/Raíces', 'folklore'),
    'folk': ('Folklore/Raíces', 'folk'),
    'folk music': ('Folklore/Raíces', 'folk music'),
    'traditional folk': ('Folklore/Raíces', 'traditional folk'),
    'folk tradicional': ('Folklore/Raíces', 'folk tradicional'),

    ## Country folk
    'country folk': ('Folklore/Raíces', 'country folk'),

    ## Celtic folk (ampliado)
    'celtic': ('Folklore/Raíces', 'celtic'),
    'celtic folk': ('Folklore/Raíces', 'celtic folk'),
    'música celta': ('Folklore/Raíces', 'música celta'),
    'irish folk': ('Folklore/Raíces', 'irish folk'),
    'scottish folk': ('Folklore/Raíces', 'scottish folk'),
    'sean nós': ('Folklore/Raíces', 'sean nós'),
    'ceilidh': ('Folklore/Raíces', 'ceilidh'),
    'breton music': ('Folklore/Raíces', 'breton music'),
    'musique bretonne': ('Folklore/Raíces', 'musique bretonne'),
    'música galega': ('Folklore/Raíces', 'música galega'),
    'galician folk': ('Folklore/Raíces', 'galician folk'),
    'celtic rock': ('Folklore/Raíces', 'celtic rock'),
    'celtic punk': ('Folklore/Raíces', 'celtic punk'),  # Nota: también existe en Punk, pero se redefine aquí

    ## Fado (ampliado)
    'fado': ('Folklore/Raíces', 'fado'),
    'fado de coimbra': ('Folklore/Raíces', 'fado de coimbra'),
    'fado de lisboa': ('Folklore/Raíces', 'fado de lisboa'),
    'fado vadio': ('Folklore/Raíces', 'fado vadio'),
    'fado fusion': ('Folklore/Raíces', 'fado fusion'),

    ## Nueva Canción / Nova Cançó (ampliado)
    'nueva canción': ('Folklore/Raíces', 'nueva canción'),
    'nova cançó': ('Folklore/Raíces', 'nova cançó'),
    'cantautor catalán': ('Folklore/Raíces', 'cantautor catalán'),
    'cantautor gallego': ('Folklore/Raíces', 'cantautor gallego'),
    'cantautor andaluz': ('Folklore/Raíces', 'cantautor andaluz'),
    'nueva canción rock': ('Folklore/Raíces', 'nueva canción rock'),

    ## Nordic folk
    'nordic folk': ('Folklore/Raíces', 'nordic folk'),
    'scandinavian folk': ('Folklore/Raíces', 'scandinavian folk'),

    ## World music
    'world music': ('Folklore/Raíces', 'world music'),
    'música del mundo': ('Folklore/Raíces', 'música del mundo'),

    ## Música andina
    'andina': ('Folklore/Raíces', 'andina'),
    'música andina': ('Folklore/Raíces', 'música andina'),
    'andean music': ('Folklore/Raíces', 'andean music'),

    ## Folklore latinoamericano
    'folklore latinoamericano': ('Folklore/Raíces', 'folklore latinoamericano'),
    'zamacueca': ('Folklore/Raíces', 'zamacueca'),
    'cueca': ('Folklore/Raíces', 'cueca'),
    'tonada': ('Folklore/Raíces', 'tonada'),
    'milonga': ('Folklore/Raíces', 'milonga'),
    'zamba': ('Folklore/Raíces', 'zamba'),
    'chacarera': ('Folklore/Raíces', 'chacarera'),

    ## Nueva canción / Nueva trova
    'nueva trova': ('Folklore/Raíces', 'nueva trova'),
    'cantautor folk': ('Folklore/Raíces', 'cantautor folk'),
    'trova': ('Folklore/Raíces', 'trova'),

    ## Folk contemporáneo
    'contemporary folk': ('Folklore/Raíces', 'contemporary folk'),
    'folk contemporáneo': ('Folklore/Raíces', 'folk contemporáneo'),
    'freak folk': ('Folklore/Raíces', 'freak folk'),

    ###############################################################################
    # Country
    ###############################################################################
    ## Country General
    'country': ('Country', 'country'),
    'country music': ('Country', 'country music'),
    'música country': ('Country', 'música country'),

    ## Country clásico / Honky tonk
    'classic country': ('Country', 'classic country'),
    'country clásico': ('Country', 'country clásico'),
    'honky tonk': ('Country', 'honky tonk'),

    ## Country pop
    'country pop': ('Country', 'country pop'),
    'country-pop': ('Country', 'country-pop'),

    ## Country rock
    'country rock': ('Country', 'country rock'),
    'country-rock': ('Country', 'country-rock'),

    ## Outlaw country
    'outlaw country': ('Country', 'outlaw country'),

    ## Bluegrass
    'bluegrass': ('Country', 'bluegrass'),
    'bluegrass music': ('Country', 'bluegrass music'),

    ## Americana
    'americana': ('Country', 'americana'),

    ## Western
    'western': ('Country', 'western'),
    'western music': ('Country', 'western music'),
    'cowboy': ('Country', 'cowboy'),

    ## Nashville sound
    'nashville sound': ('Country', 'nashville sound'),
    'nashville country': ('Country', 'nashville country'),

    ## Country alternativo / Alt-country
    'alternative country': ('Country', 'alternative country'),
    'alt-country': ('Country', 'alt-country'),
    'country alternativo': ('Country', 'country alternativo'),
    'insurgent country': ('Country', 'insurgent country'),

    ## Texas country
    'texas country': ('Country', 'texas country'),

    ## Red Dirt
    'red dirt': ('Country', 'red dirt'),

    ## Bakersfield sound
    'bakersfield sound': ('Country', 'bakersfield sound'),

    ## Bluegrass progresivo
    'progressive bluegrass': ('Country', 'progressive bluegrass'),
    'newgrass': ('Country', 'newgrass'),

    ## Country gospel
    'country gospel': ('Country', 'country gospel'),

    ###############################################################################
    # Classical / Academic Music
    ###############################################################################
    ## General
    'classical': ('Classical', 'classical'),
    'classical music': ('Classical', 'classical music'),
    'música clásica': ('Classical', 'música clásica'),
    'musica clasica': ('Classical', 'musica clasica'),
    'academic music': ('Classical', 'academic music'),
    'música académica': ('Classical', 'música académica'),

    ## Symphonic / Orchestral
    'symphonic': ('Classical', 'symphonic'),
    'symphony': ('Classical', 'symphony'),
    'orchestral': ('Classical', 'orchestral'),
    'sinfónica': ('Classical', 'sinfónica'),
    'orquestal': ('Classical', 'orquestal'),

    ## Opera
    'opera': ('Classical', 'opera'),
    'ópera': ('Classical', 'ópera'),
    'operatic': ('Classical', 'operatic'),

    ## Chamber music
    'chamber music': ('Classical', 'chamber music'),
    'música de cámara': ('Classical', 'música de cámara'),

    ## Baroque
    'baroque': ('Classical', 'baroque'),
    'barroco': ('Classical', 'barroco'),

    ## Classicism
    'classicism': ('Classical', 'classicism'),
    'clasicismo': ('Classical', 'clasicismo'),

    ## Romanticism
    'romanticism': ('Classical', 'romanticism'),
    'romanticismo': ('Classical', 'romanticismo'),

    ## Contemporary / Modern
    'contemporary classical': ('Classical', 'contemporary classical'),
    'modern classical': ('Classical', 'modern classical'),
    'clásica contemporánea': ('Classical', 'clásica contemporánea'),
    'clásica moderna': ('Classical', 'clásica moderna'),

    ## Choral / Vocal
    'choral': ('Classical', 'choral'),
    'vocal classical': ('Classical', 'vocal classical'),
    'coral': ('Classical', 'coral'),
    'música coral': ('Classical', 'música coral'),

    ## Zarzuela
    'zarzuela': ('Classical', 'zarzuela'),

    ## Operetta
    'operetta': ('Classical', 'operetta'),
    'opereta': ('Classical', 'opereta'),

    ## Otros términos comunes en inglés
    'classic': ('Classical', 'classic'),  # aunque 'classic' puede ser ambiguo (rock clásico), pero en contexto clásico
    'classical period': ('Classical', 'classical period'),
    'early music': ('Classical', 'early music'),
    'renaissance music': ('Classical', 'renaissance music'),
    'medieval music': ('Classical', 'medieval music'),

    ###############################################################################
    # Dancehall / Reggae (Regional)
    ###############################################################################
    ## Reggae General
    'reggae': ('Dancehall/Reggae', 'reggae'),
    'reggae music': ('Dancehall/Reggae', 'reggae music'),
    'reggae jamaicano': ('Dancehall/Reggae', 'reggae jamaicano'),

    ## Roots reggae
    'roots reggae': ('Dancehall/Reggae', 'roots reggae'),
    'reggae roots': ('Dancehall/Reggae', 'reggae roots'),
    'roots': ('Dancehall/Reggae', 'roots'),

    ## Dancehall
    'dancehall': ('Dancehall/Reggae', 'dancehall'),
    'dance hall': ('Dancehall/Reggae', 'dance hall'),

    ## Ska
    'ska': ('Dancehall/Reggae', 'ska'),
    'ska music': ('Dancehall/Reggae', 'ska music'),
    'ska jamaicano': ('Dancehall/Reggae', 'ska jamaicano'),
    'ska tradicional': ('Dancehall/Reggae', 'ska tradicional'),
    '2 tone': ('Dancehall/Reggae', '2 tone'),
    'ska revival': ('Dancehall/Reggae', 'ska revival'),

    ## Rocksteady
    'rocksteady': ('Dancehall/Reggae', 'rocksteady'),
    'rock steady': ('Dancehall/Reggae', 'rock steady'),

    ## Dub
    'dub': ('Dancehall/Reggae', 'dub'),
    'dub music': ('Dancehall/Reggae', 'dub music'),
    'dub jamaicano': ('Dancehall/Reggae', 'dub jamaicano'),
    'dub poetry': ('Dancehall/Reggae', 'dub poetry'),

    ## Lovers rock
    'lovers rock': ('Dancehall/Reggae', 'lovers rock'),
    'lovers rock reggae': ('Dancehall/Reggae', 'lovers rock reggae'),

    ## Ragga / Raggamuffin
    'ragga': ('Dancehall/Reggae', 'ragga'),
    'raggamuffin': ('Dancehall/Reggae', 'raggamuffin'),
    'ragga reggae': ('Dancehall/Reggae', 'ragga reggae'),
    'raggamuffin reggae': ('Dancehall/Reggae', 'raggamuffin reggae'),

    ## Modern dancehall
    'modern dancehall': ('Dancehall/Reggae', 'modern dancehall'),
    'contemporary dancehall': ('Dancehall/Reggae', 'contemporary dancehall'),
    'dancehall moderno': ('Dancehall/Reggae', 'dancehall moderno'),

    ## Reggae fusión
    'reggae fusion': ('Dancehall/Reggae', 'reggae fusion'),
    'reggae fusión': ('Dancehall/Reggae', 'reggae fusión'),
    'reggae-pop': ('Dancehall/Reggae', 'reggae-pop'),
    'reggae pop': ('Dancehall/Reggae', 'reggae pop'),
    'reggae-rock': ('Dancehall/Reggae', 'reggae-rock'),
    'reggae rock': ('Dancehall/Reggae', 'reggae rock'),

    ## UK reggae
    'uk reggae': ('Dancehall/Reggae', 'uk reggae'),
    'british reggae': ('Dancehall/Reggae', 'british reggae'),
    'lovers rock uk': ('Dancehall/Reggae', 'lovers rock uk'),

    ## Escenas regionales
    'jamaican reggae': ('Dancehall/Reggae', 'jamaican reggae'),
    'dancehall jamaicano': ('Dancehall/Reggae', 'dancehall jamaicano'),

    ## Reggae latino
    'reggae latino': ('Dancehall/Reggae', 'reggae latino'),
    'latin reggae': ('Dancehall/Reggae', 'latin reggae'),
    'reggae en español': ('Dancehall/Reggae', 'reggae en español'),

    ## Reggae brasileño
    'reggae brasileiro': ('Dancehall/Reggae', 'reggae brasileiro'),
    'brazilian reggae': ('Dancehall/Reggae', 'brazilian reggae'),

    ## Reggae africano
    'african reggae': ('Dancehall/Reggae', 'african reggae'),
    'reggae africano': ('Dancehall/Reggae', 'reggae africano'),

    ## Early reggae
    'early reggae': ('Dancehall/Reggae', 'early reggae'),
    'reggae temprano': ('Dancehall/Reggae', 'reggae temprano'),

    ## Nyabinghi
    'nyabinghi': ('Dancehall/Reggae', 'nyabinghi'),
    'nyabinghi drumming': ('Dancehall/Reggae', 'nyabinghi drumming'),

    ## Rub-a-dub
    'rub a dub': ('Dancehall/Reggae', 'rub a dub'),
    'rubadub': ('Dancehall/Reggae', 'rubadub'),

    ## Steppers
    'steppers': ('Dancehall/Reggae', 'steppers'),
    'reggae steppers': ('Dancehall/Reggae', 'reggae steppers'),

    ###############################################################################
    # Bachata (Regional)
    ###############################################################################
    ## Bachata General
    'bachata': ('Bachata', 'bachata'),
    'bachata music': ('Bachata', 'bachata music'),
    'música bachata': ('Bachata', 'música bachata'),

    ## Bachata tradicional
    'bachata tradicional': ('Bachata', 'bachata tradicional'),
    'traditional bachata': ('Bachata', 'traditional bachata'),
    'bachata clásica': ('Bachata', 'bachata clásica'),
    'classic bachata': ('Bachata', 'classic bachata'),
    'bachata original': ('Bachata', 'bachata original'),
    'bachata del campo': ('Bachata', 'bachata del campo'),

    ## Bachata romántica
    'bachata romántica': ('Bachata', 'bachata romántica'),
    'romantic bachata': ('Bachata', 'romantic bachata'),
    'bachata amorosa': ('Bachata', 'bachata amorosa'),
    'bachata de amor': ('Bachata', 'bachata de amor'),

    ## Bachata urbana
    'bachata urbana': ('Bachata', 'bachata urbana'),
    'urban bachata': ('Bachata', 'urban bachata'),
    'bachata callejera': ('Bachata', 'bachata callejera'),
    'bachata moderna': ('Bachata', 'bachata moderna'),
    'modern bachata': ('Bachata', 'modern bachata'),

    ## Bachata sensual
    'bachata sensual': ('Bachata', 'bachata sensual'),
    'sensual bachata': ('Bachata', 'sensual bachata'),
    'bachata sexy': ('Bachata', 'bachata sexy'),

    ## Bachata fusión
    'bachata fusion': ('Bachata', 'bachata fusion'),
    'bachata fusión': ('Bachata', 'bachata fusión'),
    'bachata pop': ('Bachata', 'bachata pop'),
    'pop bachata': ('Bachata', 'pop bachata'),
    'bachata rock': ('Bachata', 'bachata rock'),
    'rock bachata': ('Bachata', 'rock bachata'),
    'bachata house': ('Bachata', 'bachata house'),
    'bachata electronica': ('Bachata', 'bachata electronica'),

    ## Bachata con guitarra
    'bachata con guitarra': ('Bachata', 'bachata con guitarra'),
    'bachata guitar': ('Bachata', 'bachata guitar'),
    'guitar bachata': ('Bachata', 'guitar bachata'),
    'bachata acústica': ('Bachata', 'bachata acústica'),
    'acoustic bachata': ('Bachata', 'acoustic bachata'),

    ## Bachata por épocas
    'bachata 80s': ('Bachata', 'bachata 80s'),
    'bachata 90s': ('Bachata', 'bachata 90s'),
    'bachata 2000s': ('Bachata', 'bachata 2000s'),
    'bachata actual': ('Bachata', 'bachata actual'),

    ## Escenas regionales
    'bachata dominicana': ('Bachata', 'bachata dominicana'),
    'dominican bachata': ('Bachata', 'dominican bachata'),
    'bachata de república dominicana': ('Bachata', 'bachata de república dominicana'),
    'bachata puertorriqueña': ('Bachata', 'bachata puertorriqueña'),
    'puerto rican bachata': ('Bachata', 'puerto rican bachata'),
    'bachata estadounidense': ('Bachata', 'bachata estadounidense'),
    'us bachata': ('Bachata', 'us bachata'),
    'bachata europea': ('Bachata', 'bachata europea'),
    'european bachata': ('Bachata', 'european bachata'),

    ## Bachata instrumental
    'bachata instrumental': ('Bachata', 'bachata instrumental'),
    'instrumental bachata': ('Bachata', 'instrumental bachata'),

    ## Subgéneros específicos
    'bachata amargue': ('Bachata', 'bachata amargue'),
    'amargue': ('Bachata', 'amargue'),
    'bachata de amargue': ('Bachata', 'bachata de amargue'),
    'bachata caliente': ('Bachata', 'bachata caliente'),
    'hot bachata': ('Bachata', 'hot bachata'),

    ## Bachata mainstream
    'bachata mainstream': ('Bachata', 'bachata mainstream'),
    'commercial bachata': ('Bachata', 'commercial bachata'),
    'bachata comercial': ('Bachata', 'bachata comercial'),

    ## Bachata underground
    'bachata underground': ('Bachata', 'bachata underground'),
    'underground bachata': ('Bachata', 'underground bachata'),
    'bachata independiente': ('Bachata', 'bachata independiente'),

    ###############################################################################
    # Cumbia (Regional)
    ###############################################################################
    ## Cumbia General
    'cumbia': ('Cumbia', 'cumbia'),
    'cumbia music': ('Cumbia', 'cumbia music'),
    'música cumbia': ('Cumbia', 'música cumbia'),

    ## Cumbia colombiana (tradicional)
    'cumbia colombiana': ('Cumbia', 'cumbia colombiana'),
    'colombian cumbia': ('Cumbia', 'colombian cumbia'),
    'cumbia tradicional': ('Cumbia', 'cumbia tradicional'),
    'traditional cumbia': ('Cumbia', 'traditional cumbia'),
    'cumbia clásica': ('Cumbia', 'cumbia clásica'),
    'cumbia original': ('Cumbia', 'cumbia original'),
    'cumbia de Colombia': ('Cumbia', 'cumbia de Colombia'),

    ## Cumbia villera (Argentina)
    'cumbia villera': ('Cumbia', 'cumbia villera'),
    'villera': ('Cumbia', 'villera'),
    'cumbia argentina': ('Cumbia', 'cumbia argentina'),
    'argentine cumbia': ('Cumbia', 'argentine cumbia'),
    'cumbia villera argentina': ('Cumbia', 'cumbia villera argentina'),

    ## Cumbia andina / Peruana
    'cumbia andina': ('Cumbia', 'cumbia andina'),
    'andean cumbia': ('Cumbia', 'andean cumbia'),
    'cumbia peruana': ('Cumbia', 'cumbia peruana'),
    'peruvian cumbia': ('Cumbia', 'peruvian cumbia'),
    'cumbia andina peruana': ('Cumbia', 'cumbia andina peruana'),
    'chicha': ('Cumbia', 'chicha'),
    'chicha peruana': ('Cumbia', 'chicha peruana'),

    ## Cumbia mexicana / Sonidera
    'cumbia mexicana': ('Cumbia', 'cumbia mexicana'),
    'mexican cumbia': ('Cumbia', 'mexican cumbia'),
    'cumbia sonidera': ('Cumbia', 'cumbia sonidera'),
    'sonidera': ('Cumbia', 'sonidera'),
    'cumbia sonidero': ('Cumbia', 'cumbia sonidero'),
    'cumbia de México': ('Cumbia', 'cumbia de México'),

    ## Tecnocumbia
    'tecnocumbia': ('Cumbia', 'tecnocumbia'),
    'tecno cumbia': ('Cumbia', 'tecno cumbia'),
    'techno cumbia': ('Cumbia', 'techno cumbia'),
    'cumbia electrónica': ('Cumbia', 'cumbia electrónica'),
    'electronic cumbia': ('Cumbia', 'electronic cumbia'),

    ## Cumbia pop
    'cumbia pop': ('Cumbia', 'cumbia pop'),
    'pop cumbia': ('Cumbia', 'pop cumbia'),
    'cumbia pop latina': ('Cumbia', 'cumbia pop latina'),
    'cumbia comercial': ('Cumbia', 'cumbia comercial'),

    ## Cumbia santafesina
    'cumbia santafesina': ('Cumbia', 'cumbia santafesina'),
    'santafesina': ('Cumbia', 'santafesina'),
    'cumbia de santa fe': ('Cumbia', 'cumbia de santa fe'),

    ## Cumbia rebajada
    'cumbia rebajada': ('Cumbia', 'cumbia rebajada'),
    'rebajada': ('Cumbia', 'rebajada'),
    'cumbia slowed': ('Cumbia', 'cumbia slowed'),
    'cumbia chopped': ('Cumbia', 'cumbia chopped'),

    ## Cumbia psicodélica / Chicha
    'cumbia psicodélica': ('Cumbia', 'cumbia psicodélica'),
    'psychedelic cumbia': ('Cumbia', 'psychedelic cumbia'),
    'cumbia chicha': ('Cumbia', 'cumbia chicha'),

    ## Cumbia tropical
    'cumbia tropical': ('Cumbia', 'cumbia tropical'),
    'tropical cumbia': ('Cumbia', 'tropical cumbia'),
    'cumbia tropical latina': ('Cumbia', 'cumbia tropical latina'),

    ## Cumbia por regiones adicionales
    'cumbia boliviana': ('Cumbia', 'cumbia boliviana'),
    'bolivian cumbia': ('Cumbia', 'bolivian cumbia'),
    'cumbia chilena': ('Cumbia', 'cumbia chilena'),
    'chilean cumbia': ('Cumbia', 'chilean cumbia'),
    'cumbia ecuatoriana': ('Cumbia', 'cumbia ecuatoriana'),
    'ecuadorian cumbia': ('Cumbia', 'ecuadorian cumbia'),
    'cumbia paraguaya': ('Cumbia', 'cumbia paraguaya'),
    'paraguayan cumbia': ('Cumbia', 'paraguayan cumbia'),
    'cumbia uruguaya': ('Cumbia', 'cumbia uruguaya'),
    'uruguayan cumbia': ('Cumbia', 'uruguayan cumbia'),
    'cumbia venezolana': ('Cumbia', 'cumbia venezolana'),
    'venezuelan cumbia': ('Cumbia', 'venezuelan cumbia'),

    ## Cumbia fusión
    'cumbia fusion': ('Cumbia', 'cumbia fusion'),
    'cumbia fusión': ('Cumbia', 'cumbia fusión'),
    'cumbia rock': ('Cumbia', 'cumbia rock'),
    'rock cumbia': ('Cumbia', 'rock cumbia'),
    'cumbia reggae': ('Cumbia', 'cumbia reggae'),
    'reggae cumbia': ('Cumbia', 'reggae cumbia'),
    'cumbia ska': ('Cumbia', 'cumbia ska'),
    'ska cumbia': ('Cumbia', 'ska cumbia'),

    ## Cumbia instrumental
    'cumbia instrumental': ('Cumbia', 'cumbia instrumental'),
    'instrumental cumbia': ('Cumbia', 'instrumental cumbia'),

    ## Cumbia romántica
    'cumbia romántica': ('Cumbia', 'cumbia romántica'),
    'romantic cumbia': ('Cumbia', 'romantic cumbia'),

    ## Cumbia por épocas
    'cumbia 80s': ('Cumbia', 'cumbia 80s'),
    'cumbia 90s': ('Cumbia', 'cumbia 90s'),
    'cumbia 2000s': ('Cumbia', 'cumbia 2000s'),
    'cumbia actual': ('Cumbia', 'cumbia actual'),
    'modern cumbia': ('Cumbia', 'modern cumbia'),

    ## Cumbia underground / alternativa
    'cumbia underground': ('Cumbia', 'cumbia underground'),
    'underground cumbia': ('Cumbia', 'underground cumbia'),
    'cumbia alternativa': ('Cumbia', 'cumbia alternativa'),
    'alternative cumbia': ('Cumbia', 'alternative cumbia'),

    ###############################################################################
    # Sertanejo (Regional - Brasil)
    ###############################################################################
    ## Sertanejo General
    'sertanejo': ('Sertanejo', 'sertanejo'),
    'música sertaneja': ('Sertanejo', 'música sertaneja'),
    'sertanejo music': ('Sertanejo', 'sertanejo music'),
    'sertanejo brasileiro': ('Sertanejo', 'sertanejo brasileiro'),
    'brazilian sertanejo': ('Sertanejo', 'brazilian sertanejo'),

    ## Sertanejo raiz / Tradicional
    'sertanejo raiz': ('Sertanejo', 'sertanejo raiz'),
    'sertanejo tradicional': ('Sertanejo', 'sertanejo tradicional'),
    'traditional sertanejo': ('Sertanejo', 'traditional sertanejo'),
    'sertanejo de raiz': ('Sertanejo', 'sertanejo de raiz'),
    'sertanejo raíz': ('Sertanejo', 'sertanejo raíz'),
    'sertanejo clássico': ('Sertanejo', 'sertanejo clássico'),
    'classic sertanejo': ('Sertanejo', 'classic sertanejo'),
    'sertanejo antigo': ('Sertanejo', 'sertanejo antigo'),
    'old school sertanejo': ('Sertanejo', 'old school sertanejo'),

    ## Sertanejo universitário
    'sertanejo universitário': ('Sertanejo', 'sertanejo universitário'),
    'sertanejo universitaria': ('Sertanejo', 'sertanejo universitaria'),
    'university sertanejo': ('Sertanejo', 'university sertanejo'),
    'sertanejo jovem': ('Sertanejo', 'sertanejo jovem'),
    'young sertanejo': ('Sertanejo', 'young sertanejo'),
    'sertanejo moderno': ('Sertanejo', 'sertanejo moderno'),
    'modern sertanejo': ('Sertanejo', 'modern sertanejo'),

    ## Sertanejo romântico
    'sertanejo romântico': ('Sertanejo', 'sertanejo romântico'),
    'romantic sertanejo': ('Sertanejo', 'romantic sertanejo'),
    'sertanejo de amor': ('Sertanejo', 'sertanejo de amor'),
    'sertanejo apaixonado': ('Sertanejo', 'sertanejo apaixonado'),

    ## Sertanejo pop
    'sertanejo pop': ('Sertanejo', 'sertanejo pop'),
    'pop sertanejo': ('Sertanejo', 'pop sertanejo'),
    'sertanejo comercial': ('Sertanejo', 'sertanejo comercial'),
    'commercial sertanejo': ('Sertanejo', 'commercial sertanejo'),
    'sertanejo mainstream': ('Sertanejo', 'sertanejo mainstream'),

    ## Arrocha
    'arrocha': ('Sertanejo', 'arrocha'),
    'arrocha sertanejo': ('Sertanejo', 'arrocha sertanejo'),
    'sertanejo arrocha': ('Sertanejo', 'sertanejo arrocha'),
    'arrocha romântico': ('Sertanejo', 'arrocha romântico'),

    ## Música caipira
    'música caipira': ('Sertanejo', 'música caipira'),
    'caipira': ('Sertanejo', 'caipira'),
    'musica caipira': ('Sertanejo', 'musica caipira'),
    'caipira music': ('Sertanejo', 'caipira music'),
    'sertanejo caipira': ('Sertanejo', 'sertanejo caipira'),
    'moda caipira': ('Sertanejo', 'moda caipira'),
    'moda de viola': ('Sertanejo', 'moda de viola'),

    ## Sertanejo com viola
    'sertanejo com viola': ('Sertanejo', 'sertanejo com viola'),
    'sertanejo de viola': ('Sertanejo', 'sertanejo de viola'),
    'viola sertaneja': ('Sertanejo', 'viola sertaneja'),
    'sertanejo acústico': ('Sertanejo', 'sertanejo acústico'),
    'acoustic sertanejo': ('Sertanejo', 'acoustic sertanejo'),
    'sertanejo viola caipira': ('Sertanejo', 'sertanejo viola caipira'),

    ## Sertanejo por épocas
    'sertanejo 80s': ('Sertanejo', 'sertanejo 80s'),
    'sertanejo 90s': ('Sertanejo', 'sertanejo 90s'),
    'sertanejo 2000s': ('Sertanejo', 'sertanejo 2000s'),
    'sertanejo 2010s': ('Sertanejo', 'sertanejo 2010s'),
    'sertanejo 2020s': ('Sertanejo', 'sertanejo 2020s'),
    'sertanejo atual': ('Sertanejo', 'sertanejo atual'),
    'current sertanejo': ('Sertanejo', 'current sertanejo'),

    ## Sertanejo fusión
    'sertanejo fusion': ('Sertanejo', 'sertanejo fusion'),
    'sertanejo fusão': ('Sertanejo', 'sertanejo fusão'),
    'sertanejo rock': ('Sertanejo', 'sertanejo rock'),
    'rock sertanejo': ('Sertanejo', 'rock sertanejo'),
    'sertanejo eletrônico': ('Sertanejo', 'sertanejo eletrônico'),
    'eletrônico sertanejo': ('Sertanejo', 'eletrônico sertanejo'),
    'sertanejo reggae': ('Sertanejo', 'sertanejo reggae'),
    'reggae sertanejo': ('Sertanejo', 'reggae sertanejo'),

    ## Sertanejo instrumental
    'sertanejo instrumental': ('Sertanejo', 'sertanejo instrumental'),
    'instrumental sertanejo': ('Sertanejo', 'instrumental sertanejo'),

    ## Duplas sertanejas
    'dupla sertaneja': ('Sertanejo', 'dupla sertaneja'),
    'sertanejo dupla': ('Sertanejo', 'sertanejo dupla'),
    'duplas sertanejas': ('Sertanejo', 'duplas sertanejas'),

    ## Feminejo (sertanejo femenino)
    'feminejo': ('Sertanejo', 'feminejo'),
    'sertanejo feminino': ('Sertanejo', 'sertanejo feminino'),
    'female sertanejo': ('Sertanejo', 'female sertanejo'),
    'sertanejo mulheres': ('Sertanejo', 'sertanejo mulheres'),

    ## Sertanejo gospel
    'sertanejo gospel': ('Sertanejo', 'sertanejo gospel'),
    'gospel sertanejo': ('Sertanejo', 'gospel sertanejo'),
    'sertanejo cristão': ('Sertanejo', 'sertanejo cristão'),

    ## Sertanejo universitário - subcategorías
    'sertanejo universitário antigo': ('Sertanejo', 'sertanejo universitário antigo'),
    'sertanejo universitário novo': ('Sertanejo', 'sertanejo universitário novo'),

    ## Sertanejo por región
    'sertanejo goiano': ('Sertanejo', 'sertanejo goiano'),
    'goiano sertanejo': ('Sertanejo', 'goiano sertanejo'),
    'sertanejo paulista': ('Sertanejo', 'sertanejo paulista'),
    'paulista sertanejo': ('Sertanejo', 'paulista sertanejo'),
    'sertanejo mineiro': ('Sertanejo', 'sertanejo mineiro'),
    'mineiro sertanejo': ('Sertanejo', 'mineiro sertanejo'),
    'sertanejo mato-grossense': ('Sertanejo', 'sertanejo mato-grossense'),

    ## Viola caipira / Viola sertaneja
    'viola caipira': ('Sertanejo', 'viola caipira'),
    'viola sertaneja': ('Sertanejo', 'viola sertaneja'),
    'violeiro': ('Sertanejo', 'violeiro'),
    'violeiros': ('Sertanejo', 'violeiros'),

    ###############################################################################
    # Funk Brasileiro (Regional)
    ###############################################################################
    ## Funk Brasileiro General
    'funk brasileiro': ('Funk Brasileiro', 'funk brasileiro'),
    'brazilian funk': ('Funk Brasileiro', 'brazilian funk'),
    'funk br': ('Funk Brasileiro', 'funk br'),
    'funk nacional': ('Funk Brasileiro', 'funk nacional'),
    'funk do brasil': ('Funk Brasileiro', 'funk do brasil'),
    'funk carioca': ('Funk Brasileiro', 'funk carioca'),
    'funk brasileño': ('Funk Brasileiro', 'funk brasileño'),

    ## Funk carioca / Favela funk
    'carioca funk': ('Funk Brasileiro', 'carioca funk'),
    'favela funk': ('Funk Brasileiro', 'favela funk'),
    'funk do rio': ('Funk Brasileiro', 'funk do rio'),
    'funk do rio de janeiro': ('Funk Brasileiro', 'funk do rio de janeiro'),
    'funk carioca tradicional': ('Funk Brasileiro', 'funk carioca tradicional'),

    ## Funk ostentação
    'funk ostentação': ('Funk Brasileiro', 'funk ostentação'),
    'ostentação funk': ('Funk Brasileiro', 'ostentação funk'),
    'funk ostentacao': ('Funk Brasileiro', 'funk ostentacao'),
    'funk de luxo': ('Funk Brasileiro', 'funk de luxo'),
    'luxury funk': ('Funk Brasileiro', 'luxury funk'),

    ## Funk consciente
    'funk consciente': ('Funk Brasileiro', 'funk consciente'),
    'conscious funk': ('Funk Brasileiro', 'conscious funk'),
    'funk de mensagem': ('Funk Brasileiro', 'funk de mensagem'),
    'funk com consciência': ('Funk Brasileiro', 'funk com consciência'),
    'funk social': ('Funk Brasileiro', 'funk social'),

    ## Funk melody
    'funk melody': ('Funk Brasileiro', 'funk melody'),
    'melody funk': ('Funk Brasileiro', 'melody funk'),
    'funk romântico': ('Funk Brasileiro', 'funk romântico'),
    'romantic funk': ('Funk Brasileiro', 'romantic funk'),
    'funk melody romântico': ('Funk Brasileiro', 'funk melody romântico'),

    ## Funk proibidão
    'funk proibidão': ('Funk Brasileiro', 'funk proibidão'),
    'proibidão': ('Funk Brasileiro', 'proibidão'),
    'funk proibido': ('Funk Brasileiro', 'funk proibido'),
    'proibidao funk': ('Funk Brasileiro', 'proibidao funk'),

    ## Brega funk
    'brega funk': ('Funk Brasileiro', 'brega funk'),
    'funk brega': ('Funk Brasileiro', 'funk brega'),
    'brega-funk': ('Funk Brasileiro', 'brega-funk'),
    'brega funk brasileiro': ('Funk Brasileiro', 'brega funk brasileiro'),

    ## Funk 150 BPM
    'funk 150 bpm': ('Funk Brasileiro', 'funk 150 bpm'),
    '150 bpm funk': ('Funk Brasileiro', '150 bpm funk'),
    'funk 150': ('Funk Brasileiro', 'funk 150'),
    'funk de 150': ('Funk Brasileiro', 'funk de 150'),

    ## Funk mandelão
    'funk mandelão': ('Funk Brasileiro', 'funk mandelão'),
    'mandelão': ('Funk Brasileiro', 'mandelão'),
    'funk mandelao': ('Funk Brasileiro', 'funk mandelao'),
    'mandelao funk': ('Funk Brasileiro', 'mandelao funk'),
    'funk pesado': ('Funk Brasileiro', 'funk pesado'),
    'heavy funk': ('Funk Brasileiro', 'heavy funk'),

    ## Funk paulista
    'funk paulista': ('Funk Brasileiro', 'funk paulista'),
    'paulista funk': ('Funk Brasileiro', 'paulista funk'),
    'funk de são paulo': ('Funk Brasileiro', 'funk de são paulo'),
    'funk sp': ('Funk Brasileiro', 'funk sp'),
    'funk 012': ('Funk Brasileiro', 'funk 012'),

    ## Funk com trap
    'funk com trap': ('Funk Brasileiro', 'funk com trap'),
    'funk trap': ('Funk Brasileiro', 'funk trap'),
    'trap funk': ('Funk Brasileiro', 'trap funk'),
    'funk trap brasileiro': ('Funk Brasileiro', 'funk trap brasileiro'),
    'trap brasileiro': ('Funk Brasileiro', 'trap brasileiro'),

    ## Funk por épocas
    'funk 90s': ('Funk Brasileiro', 'funk 90s'),
    'funk anos 90': ('Funk Brasileiro', 'funk anos 90'),
    'funk 2000s': ('Funk Brasileiro', 'funk 2000s'),
    'funk anos 2000': ('Funk Brasileiro', 'funk anos 2000'),
    'funk 2010s': ('Funk Brasileiro', 'funk 2010s'),
    'funk atual': ('Funk Brasileiro', 'funk atual'),

    ## Funk fusión
    'funk fusion': ('Funk Brasileiro', 'funk fusion'),
    'funk fusão': ('Funk Brasileiro', 'funk fusão'),
    'funk rock': ('Funk Brasileiro', 'funk rock'),
    'rock funk': ('Funk Brasileiro', 'rock funk'),
    'funk pop': ('Funk Brasileiro', 'funk pop'),
    'pop funk': ('Funk Brasileiro', 'pop funk'),
    'funk eletrônico': ('Funk Brasileiro', 'funk eletrônico'),
    'eletrônico funk': ('Funk Brasileiro', 'eletrônico funk'),

    ## Funk instrumental
    'funk instrumental': ('Funk Brasileiro', 'funk instrumental'),
    'instrumental funk': ('Funk Brasileiro', 'instrumental funk'),
    'batidão': ('Funk Brasileiro', 'batidão'),
    'batidão funk': ('Funk Brasileiro', 'batidão funk'),

    ## Vertentes regionais
    'funk de comunidade': ('Funk Brasileiro', 'funk de comunidade'),
    'funk da quebrada': ('Funk Brasileiro', 'funk da quebrada'),
    'funk da favela': ('Funk Brasileiro', 'funk da favela'),
    'funk de rua': ('Funk Brasileiro', 'funk de rua'),

    ## Passinho
    'passinho': ('Funk Brasileiro', 'passinho'),
    'passinho funk': ('Funk Brasileiro', 'passinho funk'),
    'passinho do malafaia': ('Funk Brasileiro', 'passinho do malafaia'),

    ## Funk feminino
    'funk feminino': ('Funk Brasileiro', 'funk feminino'),
    'female funk': ('Funk Brasileiro', 'female funk'),
    'funk das minas': ('Funk Brasileiro', 'funk das minas'),

    ## Funk putaria
    'funk putaria': ('Funk Brasileiro', 'funk putaria'),
    'putaria funk': ('Funk Brasileiro', 'putaria funk'),
    'funk putero': ('Funk Brasileiro', 'funk putero'),

    ## Funk de faculdade
    'funk de faculdade': ('Funk Brasileiro', 'funk de faculdade'),
    'university funk': ('Funk Brasileiro', 'university funk'),

    ## Funk gospel
    'funk gospel': ('Funk Brasileiro', 'funk gospel'),
    'gospel funk': ('Funk Brasileiro', 'gospel funk'),
    'funk cristão': ('Funk Brasileiro', 'funk cristão'),

    ## Funk antigo / Clássico
    'funk antigo': ('Funk Brasileiro', 'funk antigo'),
    'old school funk brasileiro': ('Funk Brasileiro', 'old school funk brasileiro'),
    'funk clássico': ('Funk Brasileiro', 'funk clássico'),
    'classic brazilian funk': ('Funk Brasileiro', 'classic brazilian funk'),

    ###############################################################################
    # Regional Mexicano
    ###############################################################################
    ## General
    'regional mexicano': ('Regional Mexicano', 'regional mexicano'),
    'mexican regional': ('Regional Mexicano', 'mexican regional'),
    'música regional mexicana': ('Regional Mexicano', 'música regional mexicana'),
    'regional music mexicano': ('Regional Mexicano', 'regional music mexicano'),

    ## Banda
    'banda': ('Regional Mexicano', 'banda'),
    'banda sinaloense': ('Regional Mexicano', 'banda sinaloense'),
    'banda music': ('Regional Mexicano', 'banda music'),
    'banda mexicana': ('Regional Mexicano', 'banda mexicana'),
    'banda de viento': ('Regional Mexicano', 'banda de viento'),
    'banda sinaloa': ('Regional Mexicano', 'banda sinaloa'),

    ## Norteño
    'norteño': ('Regional Mexicano', 'norteño'),
    'musica norteña': ('Regional Mexicano', 'musica norteña'),
    'norteño music': ('Regional Mexicano', 'norteño music'),
    'norteño mexicano': ('Regional Mexicano', 'norteño mexicano'),
    'norteño tradicional': ('Regional Mexicano', 'norteño tradicional'),
    'norteño con acordeón': ('Regional Mexicano', 'norteño con acordeón'),

    ## Corridos
    'corridos': ('Regional Mexicano', 'corridos'),
    'corrido': ('Regional Mexicano', 'corrido'),
    'corridos mexicanos': ('Regional Mexicano', 'corridos mexicanos'),
    'corridos tradicionales': ('Regional Mexicano', 'corridos tradicionales'),
    'corridos tumbados': ('Regional Mexicano', 'corridos tumbados'),
    'tumbados': ('Regional Mexicano', 'tumbados'),
    'corridos bélicos': ('Regional Mexicano', 'corridos bélicos'),
    'corridos de la sierra': ('Regional Mexicano', 'corridos de la sierra'),

    ## Mariachi / Ranchera
    'mariachi': ('Regional Mexicano', 'mariachi'),
    'mariachi music': ('Regional Mexicano', 'mariachi music'),
    'mariachi tradicional': ('Regional Mexicano', 'mariachi tradicional'),
    'mariachi moderno': ('Regional Mexicano', 'mariachi moderno'),
    'ranchera': ('Regional Mexicano', 'ranchera'),
    'rancheras': ('Regional Mexicano', 'rancheras'),
    'música ranchera': ('Regional Mexicano', 'música ranchera'),
    'ranchera mexicana': ('Regional Mexicano', 'ranchera mexicana'),

    ## Sierreño
    'sierreño': ('Regional Mexicano', 'sierreño'),
    'sierreño music': ('Regional Mexicano', 'sierreño music'),
    'sierreño mexicano': ('Regional Mexicano', 'sierreño mexicano'),
    'sierreño con guitarra': ('Regional Mexicano', 'sierreño con guitarra'),
    'sierreño con acordeón': ('Regional Mexicano', 'sierreño con acordeón'),
    'sierreño tradicional': ('Regional Mexicano', 'sierreño tradicional'),

    ## Duranguense
    'duranguense': ('Regional Mexicano', 'duranguense'),
    'musica duranguense': ('Regional Mexicano', 'musica duranguense'),
    'duranguense music': ('Regional Mexicano', 'duranguense music'),
    'duranguense de durango': ('Regional Mexicano', 'duranguense de durango'),
    'pasito duranguense': ('Regional Mexicano', 'pasito duranguense'),

    ## Grupero
    'grupero': ('Regional Mexicano', 'grupero'),
    'musica grupera': ('Regional Mexicano', 'musica grupera'),
    'grupero music': ('Regional Mexicano', 'grupero music'),
    'grupero mexicano': ('Regional Mexicano', 'grupero mexicano'),
    'grupero romántico': ('Regional Mexicano', 'grupero romántico'),

    ## Tejano / Tex-Mex
    'tejano': ('Regional Mexicano', 'tejano'),
    'tejano music': ('Regional Mexicano', 'tejano music'),
    'tex mex': ('Regional Mexicano', 'tex mex'),
    'tex-mex': ('Regional Mexicano', 'tex-mex'),
    'texas mexicano': ('Regional Mexicano', 'texas mexicano'),
    'conjunto tejano': ('Regional Mexicano', 'conjunto tejano'),

    ## Tamborazo
    'tamborazo': ('Regional Mexicano', 'tamborazo'),
    'tamborazo zacatecano': ('Regional Mexicano', 'tamborazo zacatecano'),
    'tamborazo music': ('Regional Mexicano', 'tamborazo music'),
    'tamborazo tradicional': ('Regional Mexicano', 'tamborazo tradicional'),

    ## Tierra Caliente
    'tierra caliente': ('Regional Mexicano', 'tierra caliente'),
    'musica de tierra caliente': ('Regional Mexicano', 'musica de tierra caliente'),
    'calentana': ('Regional Mexicano', 'calentana'),
    'musica calentana': ('Regional Mexicano', 'musica calentana'),

    ## Otros subgéneros regionales
    'huapango': ('Regional Mexicano', 'huapango'),
    'son huasteco': ('Regional Mexicano', 'son huasteco'),
    'son jarocho': ('Regional Mexicano', 'son jarocho'),
    'jarocho': ('Regional Mexicano', 'jarocho'),
    'son calentano': ('Regional Mexicano', 'son calentano'),
    'son mexicano': ('Regional Mexicano', 'son mexicano'),
    'abajeño': ('Regional Mexicano', 'abajeño'),

    ## Fusiones contemporáneas
    'regional mexicano urbano': ('Regional Mexicano', 'regional mexicano urbano'),
    'regional fusion': ('Regional Mexicano', 'regional fusion'),
    'regional mexicano pop': ('Regional Mexicano', 'regional mexicano pop'),
    'pop regional mexicano': ('Regional Mexicano', 'pop regional mexicano'),
    'regional mexicano rock': ('Regional Mexicano', 'regional mexicano rock'),
    'rock regional mexicano': ('Regional Mexicano', 'rock regional mexicano'),
    'regional mexicano trap': ('Regional Mexicano', 'regional mexicano trap'),
    'trap regional mexicano': ('Regional Mexicano', 'trap regional mexicano'),

    ## Por época
    'regional mexicano clasico': ('Regional Mexicano', 'regional mexicano clasico'),
    'regional mexicano tradicional': ('Regional Mexicano', 'regional mexicano tradicional'),
    'regional mexicano moderno': ('Regional Mexicano', 'regional mexicano moderno'),
    'regional mexicano contemporáneo': ('Regional Mexicano', 'regional mexicano contemporáneo'),
    'regional mexicano nuevo': ('Regional Mexicano', 'regional mexicano nuevo'),

    ## Instrumental
    'regional mexicano instrumental': ('Regional Mexicano', 'regional mexicano instrumental'),
    'instrumental regional mexicano': ('Regional Mexicano', 'instrumental regional mexicano'),
    'musica de acordeon': ('Regional Mexicano', 'musica de acordeon'),
    'acordeon regional': ('Regional Mexicano', 'acordeon regional'),

    ###############################################################################
    # Vallenato (Regional - Colombia)
    ###############################################################################
    ## Vallenato General
    'vallenato': ('Vallenato', 'vallenato'),
    'música vallenata': ('Vallenato', 'música vallenata'),
    'vallenato music': ('Vallenato', 'vallenato music'),
    'vallenato colombiano': ('Vallenato', 'vallenato colombiano'),
    'colombian vallenato': ('Vallenato', 'colombian vallenato'),
    'vallenato de colombia': ('Vallenato', 'vallenato de colombia'),

    ## Vallenato tradicional
    'vallenato tradicional': ('Vallenato', 'vallenato tradicional'),
    'traditional vallenato': ('Vallenato', 'traditional vallenato'),
    'vallenato clásico': ('Vallenato', 'vallenato clásico'),
    'classic vallenato': ('Vallenato', 'classic vallenato'),
    'vallenato de la costa': ('Vallenato', 'vallenato de la costa'),
    'vallenato costeño': ('Vallenato', 'vallenato costeño'),
    'vallenato auténtico': ('Vallenato', 'vallenato auténtico'),

    ## Vallenato romántico
    'vallenato romántico': ('Vallenato', 'vallenato romántico'),
    'romantic vallenato': ('Vallenato', 'romantic vallenato'),
    'vallenato de amor': ('Vallenato', 'vallenato de amor'),
    'vallenato enamorado': ('Vallenato', 'vallenato enamorado'),
    'vallenato sentimental': ('Vallenato', 'vallenato sentimental'),

    ## Vallenato pop / Vallenato comercial
    'vallenato pop': ('Vallenato', 'vallenato pop'),
    'pop vallenato': ('Vallenato', 'pop vallenato'),
    'vallenato comercial': ('Vallenato', 'vallenato comercial'),
    'commercial vallenato': ('Vallenato', 'commercial vallenato'),
    'vallenato moderno': ('Vallenato', 'vallenato moderno'),
    'modern vallenato': ('Vallenato', 'modern vallenato'),
    'vallenato contemporáneo': ('Vallenato', 'vallenato contemporáneo'),

    ## Vallenato con acordeón
    'vallenato con acordeón': ('Vallenato', 'vallenato con acordeón'),
    'vallenato acordeón': ('Vallenato', 'vallenato acordeón'),
    'acordeón vallenato': ('Vallenato', 'acordeón vallenato'),
    'vallenato de acordeoneros': ('Vallenato', 'vallenato de acordeoneros'),
    'acordeon vallenato': ('Vallenato', 'acordeon vallenato'),
    'vallenato instrumental': ('Vallenato', 'vallenato instrumental'),

    ## Vallenato - cumbia fusión
    'vallenato cumbia': ('Vallenato', 'vallenato cumbia'),
    'cumbia vallenato': ('Vallenato', 'cumbia vallenato'),
    'vallenato - cumbia': ('Vallenato', 'vallenato - cumbia'),
    'vallenato cumbia fusion': ('Vallenato', 'vallenato cumbia fusion'),
    'cumbia vallenata': ('Vallenato', 'cumbia vallenata'),
    'fusion vallenato cumbia': ('Vallenato', 'fusion vallenato cumbia'),

    ## Paseo
    'paseo': ('Vallenato', 'paseo'),
    'paseo vallenato': ('Vallenato', 'paseo vallenato'),
    'vallenato paseo': ('Vallenato', 'vallenato paseo'),
    'paseo tradicional': ('Vallenato', 'paseo tradicional'),
    'paseo costeño': ('Vallenato', 'paseo costeño'),

    ## Merengue vallenato
    'merengue vallenato': ('Vallenato', 'merengue vallenato'),
    'vallenato merengue': ('Vallenato', 'vallenato merengue'),
    'merengue costeño': ('Vallenato', 'merengue costeño'),
    'merengue colombiano': ('Vallenato', 'merengue colombiano'),

    ## Aires vallenatos (ritmos tradicionales)
    'son vallenato': ('Vallenato', 'son vallenato'),
    'puya vallenata': ('Vallenato', 'puya vallenata'),
    'puya': ('Vallenato', 'puya'),
    'merengue': ('Vallenato', 'merengue'),
    'paseo vallenato tradicional': ('Vallenato', 'paseo vallenato tradicional'),

    ## Vallenato por instrumentos
    'vallenato con caja': ('Vallenato', 'vallenato con caja'),
    'vallenato con guacharaca': ('Vallenato', 'vallenato con guacharaca'),
    'vallenato con guitarra': ('Vallenato', 'vallenato con guitarra'),
    'vallenato con bajo': ('Vallenato', 'vallenato con bajo'),

    ## Vallenato por región
    'vallenato cesarense': ('Vallenato', 'vallenato cesarense'),
    'vallenato guajiro': ('Vallenato', 'vallenato guajiro'),
    'vallenato samario': ('Vallenato', 'vallenato samario'),
    'vallenato de la costa caribe': ('Vallenato', 'vallenato de la costa caribe'),
    'vallenato del magdalena': ('Vallenato', 'vallenato del magdalena'),

    ## Vallenato por época
    'vallenato 80s': ('Vallenato', 'vallenato 80s'),
    'vallenato 90s': ('Vallenato', 'vallenato 90s'),
    'vallenato 2000s': ('Vallenato', 'vallenato 2000s'),
    'vallenato actual': ('Vallenato', 'vallenato actual'),
    'vallenato nuevo': ('Vallenato', 'vallenato nuevo'),
    'vallenato de antes': ('Vallenato', 'vallenato de antes'),

    ## Vallenato fusión
    'vallenato fusion': ('Vallenato', 'vallenato fusion'),
    'vallenato fusión': ('Vallenato', 'vallenato fusión'),
    'vallenato rock': ('Vallenato', 'vallenato rock'),
    'rock vallenato': ('Vallenato', 'rock vallenato'),
    'vallenato pop rock': ('Vallenato', 'vallenato pop rock'),
    'vallenato electrónico': ('Vallenato', 'vallenato electrónico'),
    'vallenato tropical': ('Vallenato', 'vallenato tropical'),

    ## Vallenato cristiano
    'vallenato cristiano': ('Vallenato', 'vallenato cristiano'),
    'christian vallenato': ('Vallenato', 'christian vallenato'),
    'vallenato gospel': ('Vallenato', 'vallenato gospel'),

    ## Festival Vallenato
    'festival vallenato': ('Vallenato', 'festival vallenato'),
    'vallenato festival': ('Vallenato', 'vallenato festival'),
    'rey de reyes vallenato': ('Vallenato', 'rey de reyes vallenato'),

    ## Vallenato letras / temática
    'vallenato social': ('Vallenato', 'vallenato social'),
    'vallenato costumbrista': ('Vallenato', 'vallenato costumbrista'),
    'vallenato folclórico': ('Vallenato', 'vallenato folclórico'),
    'vallenato de protesta': ('Vallenato', 'vallenato de protesta'),

    ###############################################################################
    # Música Tropical / Salsa / Merengue / Bolero
    ###############################################################################
    ## Salsa
    'salsa': ('Tropical/Salsa/Merengue/Bolero', 'salsa'),
    'salsa music': ('Tropical/Salsa/Merengue/Bolero', 'salsa music'),
    'salsa dura': ('Tropical/Salsa/Merengue/Bolero', 'salsa dura'),
    'salsa romántica': ('Tropical/Salsa/Merengue/Bolero', 'salsa romántica'),
    'salsa brava': ('Tropical/Salsa/Merengue/Bolero', 'salsa brava'),
    'salsa gorda': ('Tropical/Salsa/Merengue/Bolero', 'salsa gorda'),
    'salsa consciente': ('Tropical/Salsa/Merengue/Bolero', 'salsa consciente'),
    'salsa tradicional': ('Tropical/Salsa/Merengue/Bolero', 'salsa tradicional'),
    'salsa clásica': ('Tropical/Salsa/Merengue/Bolero', 'salsa clásica'),
    'salsa cubana': ('Tropical/Salsa/Merengue/Bolero', 'salsa cubana'),
    'salsa puertorriqueña': ('Tropical/Salsa/Merengue/Bolero', 'salsa puertorriqueña'),
    'salsa neoyorquina': ('Tropical/Salsa/Merengue/Bolero', 'salsa neoyorquina'),
    'salsa colombiana': ('Tropical/Salsa/Merengue/Bolero', 'salsa colombiana'),
    'salsa venezolana': ('Tropical/Salsa/Merengue/Bolero', 'salsa venezolana'),

    ## Merengue
    'merengue': ('Tropical/Salsa/Merengue/Bolero', 'merengue'),
    'merengue dominicano': ('Tropical/Salsa/Merengue/Bolero', 'merengue dominicano'),
    'merengue típico': ('Tropical/Salsa/Merengue/Bolero', 'merengue típico'),
    'merengue de orquesta': ('Tropical/Salsa/Merengue/Bolero', 'merengue de orquesta'),
    'merengue callejero': ('Tropical/Salsa/Merengue/Bolero', 'merengue callejero'),
    'merengue mambo': ('Tropical/Salsa/Merengue/Bolero', 'merengue mambo'),
    'merengue fusión': ('Tropical/Salsa/Merengue/Bolero', 'merengue fusión'),
    'merengue electrónico': ('Tropical/Salsa/Merengue/Bolero', 'merengue electrónico'),
    'merengue moderno': ('Tropical/Salsa/Merengue/Bolero', 'merengue moderno'),
    'merengue clásico': ('Tropical/Salsa/Merengue/Bolero', 'merengue clásico'),
    'perico ripiao': ('Tropical/Salsa/Merengue/Bolero', 'perico ripiao'),
    'merengue con acordeón': ('Tropical/Salsa/Merengue/Bolero', 'merengue con acordeón'),

    ## Bolero
    'bolero': ('Tropical/Salsa/Merengue/Bolero', 'bolero'),
    'bolero music': ('Tropical/Salsa/Merengue/Bolero', 'bolero music'),
    'bolero romántico': ('Tropical/Salsa/Merengue/Bolero', 'bolero romántico'),
    'bolero clásico': ('Tropical/Salsa/Merengue/Bolero', 'bolero clásico'),
    'bolero tradicional': ('Tropical/Salsa/Merengue/Bolero', 'bolero tradicional'),
    'bolero cubano': ('Tropical/Salsa/Merengue/Bolero', 'bolero cubano'),
    'bolero mexicano': ('Tropical/Salsa/Merengue/Bolero', 'bolero mexicano'),
    'bolero puertorriqueño': ('Tropical/Salsa/Merengue/Bolero', 'bolero puertorriqueño'),
    'bolero con guitarra': ('Tropical/Salsa/Merengue/Bolero', 'bolero con guitarra'),
    'bolero con piano': ('Tropical/Salsa/Merengue/Bolero', 'bolero con piano'),
    'bolero instrumental': ('Tropical/Salsa/Merengue/Bolero', 'bolero instrumental'),
    'bolero moderno': ('Tropical/Salsa/Merengue/Bolero', 'bolero moderno'),

    ## Música Tropical general
    'tropical': ('Tropical/Salsa/Merengue/Bolero', 'tropical'),
    'música tropical': ('Tropical/Salsa/Merengue/Bolero', 'música tropical'),
    'tropical music': ('Tropical/Salsa/Merengue/Bolero', 'tropical music'),
    'tropical latina': ('Tropical/Salsa/Merengue/Bolero', 'tropical latina'),
    'ritmos tropicales': ('Tropical/Salsa/Merengue/Bolero', 'ritmos tropicales'),

    ## Son Cubano
    'son cubano': ('Tropical/Salsa/Merengue/Bolero', 'son cubano'),
    'son': ('Tropical/Salsa/Merengue/Bolero', 'son'),
    'son montuno': ('Tropical/Salsa/Merengue/Bolero', 'son montuno'),
    'son tradicional': ('Tropical/Salsa/Merengue/Bolero', 'son tradicional'),
    'son oriental': ('Tropical/Salsa/Merengue/Bolero', 'son oriental'),

    ## Timba
    'timba': ('Tropical/Salsa/Merengue/Bolero', 'timba'),
    'timba cubana': ('Tropical/Salsa/Merengue/Bolero', 'timba cubana'),
    'timba music': ('Tropical/Salsa/Merengue/Bolero', 'timba music'),
    'timba moderna': ('Tropical/Salsa/Merengue/Bolero', 'timba moderna'),

    ## Mambo
    'mambo': ('Tropical/Salsa/Merengue/Bolero', 'mambo'),
    'mambo cubano': ('Tropical/Salsa/Merengue/Bolero', 'mambo cubano'),
    'mambo music': ('Tropical/Salsa/Merengue/Bolero', 'mambo music'),
    'mambo clásico': ('Tropical/Salsa/Merengue/Bolero', 'mambo clásico'),

    ## Cha cha cha
    'cha cha cha': ('Tropical/Salsa/Merengue/Bolero', 'cha cha cha'),
    'chachachá': ('Tropical/Salsa/Merengue/Bolero', 'chachachá'),
    'cha cha cubano': ('Tropical/Salsa/Merengue/Bolero', 'cha cha cubano'),

    ## Guaracha
    'guaracha': ('Tropical/Salsa/Merengue/Bolero', 'guaracha'),
    'guaracha cubana': ('Tropical/Salsa/Merengue/Bolero', 'guaracha cubana'),
    'guaracha tradicional': ('Tropical/Salsa/Merengue/Bolero', 'guaracha tradicional'),

    ## Rumba
    'rumba': ('Tropical/Salsa/Merengue/Bolero', 'rumba'),
    'rumba cubana': ('Tropical/Salsa/Merengue/Bolero', 'rumba cubana'),
    'rumba flamenca': ('Tropical/Salsa/Merengue/Bolero', 'rumba flamenca'),
    'rumba catalana': ('Tropical/Salsa/Merengue/Bolero', 'rumba catalana'),
    'rumba gitana': ('Tropical/Salsa/Merengue/Bolero', 'rumba gitana'),

    ## Porro
    'porro': ('Tropical/Salsa/Merengue/Bolero', 'porro'),
    'porro colombiano': ('Tropical/Salsa/Merengue/Bolero', 'porro colombiano'),
    'porro tradicional': ('Tropical/Salsa/Merengue/Bolero', 'porro tradicional'),
    'porro costeño': ('Tropical/Salsa/Merengue/Bolero', 'porro costeño'),

    ## Festejo / Landó (Perú)
    'festejo': ('Tropical/Salsa/Merengue/Bolero', 'festejo'),
    'festejo peruano': ('Tropical/Salsa/Merengue/Bolero', 'festejo peruano'),
    'landó': ('Tropical/Salsa/Merengue/Bolero', 'landó'),
    'landó peruano': ('Tropical/Salsa/Merengue/Bolero', 'landó peruano'),

    ## Bomba / Plena (Puerto Rico)
    'bomba': ('Tropical/Salsa/Merengue/Bolero', 'bomba'),
    'bomba puertorriqueña': ('Tropical/Salsa/Merengue/Bolero', 'bomba puertorriqueña'),
    'plena': ('Tropical/Salsa/Merengue/Bolero', 'plena'),
    'plena puertorriqueña': ('Tropical/Salsa/Merengue/Bolero', 'plena puertorriqueña'),

    ## Calypso / Soca
    'calypso': ('Tropical/Salsa/Merengue/Bolero', 'calypso'),
    'calypso music': ('Tropical/Salsa/Merengue/Bolero', 'calypso music'),
    'calypso caribeño': ('Tropical/Salsa/Merengue/Bolero', 'calypso caribeño'),
    'calypso tradicional': ('Tropical/Salsa/Merengue/Bolero', 'calypso tradicional'),
    'traditional calypso': ('Tropical/Salsa/Merengue/Bolero', 'traditional calypso'),
    'calypso trinidad': ('Tropical/Salsa/Merengue/Bolero', 'calypso trinidad'),

    'soca': ('Tropical/Salsa/Merengue/Bolero', 'soca'),
    'soca music': ('Tropical/Salsa/Merengue/Bolero', 'soca music'),
    'soca caribeña': ('Tropical/Salsa/Merengue/Bolero', 'soca caribeña'),
    'soca trinidad': ('Tropical/Salsa/Merengue/Bolero', 'soca trinidad'),

    ### Soca clásica
    'soca clásica': ('Tropical/Salsa/Merengue/Bolero', 'soca clásica'),
    'classic soca': ('Tropical/Salsa/Merengue/Bolero', 'classic soca'),
    'soca tradicional': ('Tropical/Salsa/Merengue/Bolero', 'soca tradicional'),
    'old school soca': ('Tropical/Salsa/Merengue/Bolero', 'old school soca'),

    ### Power soca
    'power soca': ('Tropical/Salsa/Merengue/Bolero', 'power soca'),
    'power soca music': ('Tropical/Salsa/Merengue/Bolero', 'power soca music'),
    'soca power': ('Tropical/Salsa/Merengue/Bolero', 'soca power'),

    ### Groovy soca
    'groovy soca': ('Tropical/Salsa/Merengue/Bolero', 'groovy soca'),
    'groove soca': ('Tropical/Salsa/Merengue/Bolero', 'groove soca'),
    'soca groovy': ('Tropical/Salsa/Merengue/Bolero', 'soca groovy'),

    ### Chutney soca
    'chutney soca': ('Tropical/Salsa/Merengue/Bolero', 'chutney soca'),
    'soca chutney': ('Tropical/Salsa/Merengue/Bolero', 'soca chutney'),
    'chutney soca fusion': ('Tropical/Salsa/Merengue/Bolero', 'chutney soca fusion'),

    ### Rapso
    'rapso': ('Tropical/Salsa/Merengue/Bolero', 'rapso'),
    'rapso music': ('Tropical/Salsa/Merengue/Bolero', 'rapso music'),
    'rapso trinidad': ('Tropical/Salsa/Merengue/Bolero', 'rapso trinidad'),

    ### Extempo
    'extempo': ('Tropical/Salsa/Merengue/Bolero', 'extempo'),
    'extempo calypso': ('Tropical/Salsa/Merengue/Bolero', 'extempo calypso'),
    'calypso extempo': ('Tropical/Salsa/Merengue/Bolero', 'calypso extempo'),

    ### Parang soca
    'parang soca': ('Tropical/Salsa/Merengue/Bolero', 'parang soca'),
    'soca parang': ('Tropical/Salsa/Merengue/Bolero', 'soca parang'),
    'parang soca music': ('Tropical/Salsa/Merengue/Bolero', 'parang soca music'),

    ### Bouyon soca (Dominica)
    'bouyon soca': ('Tropical/Salsa/Merengue/Bolero', 'bouyon soca'),
    'bouyon': ('Tropical/Salsa/Merengue/Bolero', 'bouyon'),
    'bouyon music': ('Tropical/Salsa/Merengue/Bolero', 'bouyon music'),
    'bouyon soca dominica': ('Tropical/Salsa/Merengue/Bolero', 'bouyon soca dominica'),
    'dominica bouyon': ('Tropical/Salsa/Merengue/Bolero', 'dominica bouyon'),

    ### Soca moderna / contemporánea
    'soca moderna': ('Tropical/Salsa/Merengue/Bolero', 'soca moderna'),
    'modern soca': ('Tropical/Salsa/Merengue/Bolero', 'modern soca'),
    'soca contemporánea': ('Tropical/Salsa/Merengue/Bolero', 'soca contemporánea'),
    'contemporary soca': ('Tropical/Salsa/Merengue/Bolero', 'contemporary soca'),

    ### Fusiones de soca
    'soca fusion': ('Tropical/Salsa/Merengue/Bolero', 'soca fusion'),
    'soca fusión': ('Tropical/Salsa/Merengue/Bolero', 'soca fusión'),
    'soca pop': ('Tropical/Salsa/Merengue/Bolero', 'soca pop'),
    'pop soca': ('Tropical/Salsa/Merengue/Bolero', 'pop soca'),
    'soca reggae': ('Tropical/Salsa/Merengue/Bolero', 'soca reggae'),
    'reggae soca': ('Tropical/Salsa/Merengue/Bolero', 'reggae soca'),
    'soca dancehall': ('Tropical/Salsa/Merengue/Bolero', 'soca dancehall'),
    'dancehall soca': ('Tropical/Salsa/Merengue/Bolero', 'dancehall soca'),

    ### Soca por regiones
    'soca trinitaria': ('Tropical/Salsa/Merengue/Bolero', 'soca trinitaria'),
    'trinidad soca': ('Tropical/Salsa/Merengue/Bolero', 'trinidad soca'),
    'soca tobago': ('Tropical/Salsa/Merengue/Bolero', 'soca tobago'),
    'soca barbados': ('Tropical/Salsa/Merengue/Bolero', 'soca barbados'),
    'soca grenada': ('Tropical/Salsa/Merengue/Bolero', 'soca grenada'),
    'soca san vicente': ('Tropical/Salsa/Merengue/Bolero', 'soca san vicente'),
    'soca caribe oriental': ('Tropical/Salsa/Merengue/Bolero', 'soca caribe oriental'),

    ### Calypso por épocas
    'calypso 50s': ('Tropical/Salsa/Merengue/Bolero', 'calypso 50s'),
    'calypso 60s': ('Tropical/Salsa/Merengue/Bolero', 'calypso 60s'),
    'calypso 70s': ('Tropical/Salsa/Merengue/Bolero', 'calypso 70s'),
    'calypso 80s': ('Tropical/Salsa/Merengue/Bolero', 'calypso 80s'),
    'calypso moderno': ('Tropical/Salsa/Merengue/Bolero', 'calypso moderno'),

    ### Carnaval / Festival
    'carnival soca': ('Tropical/Salsa/Merengue/Bolero', 'carnival soca'),
    'soca carnival': ('Tropical/Salsa/Merengue/Bolero', 'soca carnival'),
    'road march': ('Tropical/Salsa/Merengue/Bolero', 'road march'),
    'soca road march': ('Tropical/Salsa/Merengue/Bolero', 'soca road march'),
    'carnival calypso': ('Tropical/Salsa/Merengue/Bolero', 'carnival calypso'),

    ## Compás / Méringue (Haití)
    'compas': ('Tropical/Salsa/Merengue/Bolero', 'compas'),
    'compas haitiano': ('Tropical/Salsa/Merengue/Bolero', 'compas haitiano'),
    'méringue': ('Tropical/Salsa/Merengue/Bolero', 'méringue'),

    ## Fusiones tropicales
    'tropical fusion': ('Tropical/Salsa/Merengue/Bolero', 'tropical fusion'),
    'tropical pop': ('Tropical/Salsa/Merengue/Bolero', 'tropical pop'),
    'pop tropical': ('Tropical/Salsa/Merengue/Bolero', 'pop tropical'),
    'tropical rock': ('Tropical/Salsa/Merengue/Bolero', 'tropical rock'),
    'rock tropical': ('Tropical/Salsa/Merengue/Bolero', 'rock tropical'),
    'tropical electronica': ('Tropical/Salsa/Merengue/Bolero', 'tropical electronica'),

    ## Por época
    'tropical clasico': ('Tropical/Salsa/Merengue/Bolero', 'tropical clasico'),
    'tropical 80s': ('Tropical/Salsa/Merengue/Bolero', 'tropical 80s'),
    'tropical 90s': ('Tropical/Salsa/Merengue/Bolero', 'tropical 90s'),
    'tropical moderno': ('Tropical/Salsa/Merengue/Bolero', 'tropical moderno'),
    'tropical contemporáneo': ('Tropical/Salsa/Merengue/Bolero', 'tropical contemporáneo'),

    ###############################################################################
    # EUROPA - Escenas regionales (no globales)
    ###############################################################################

    # NOTA: Los géneros globales como pop, rock, hip-hop, etc. ya están cubiertos
    # en las secciones anteriores. Aquí solo añadimos aquellos con fuerte identidad
    # regional y que no encajan en las categorías estándar.

    ###############################################################################
    # Balcanes
    ###############################################################################

    ## Manele (Rumanía)
    'manele': ('Manele', 'manele'),
    'muzică manele': ('Manele', 'muzică manele'),
    'muzica de petrecere': ('Manele', 'muzica de petrecere'),
    'manele vechi': ('Manele', 'manele vechi'),
    'manele noi': ('Manele', 'manele noi'),
    'manele românești': ('Manele', 'manele românești'),
    'manele aromâne': ('Manele', 'manele aromâne'),
    'manele pop': ('Manele', 'manele pop'),
    'manele house': ('Manele', 'manele house'),

    ## Turbo-folk (Serbia / Balcanes)
    'turbo folk': ('Turbo-folk', 'turbo folk'),
    'turbofolk': ('Turbo-folk', 'turbofolk'),
    'турбо фолк': ('Turbo-folk', 'турбо фолк'),
    'srpski turbo folk': ('Turbo-folk', 'srpski turbo folk'),
    'bugarski turbo folk': ('Turbo-folk', 'bugarski turbo folk'),
    'bosanski turbo folk': ('Turbo-folk', 'bosanski turbo folk'),
    'makedonski turbo folk': ('Turbo-folk', 'makedonski turbo folk'),
    'crnogorski turbo folk': ('Turbo-folk', 'crnogorski turbo folk'),
    'pop-folk balcánico': ('Turbo-folk', 'pop-folk balcánico'),
    'narodna muzika': ('Turbo-folk', 'narodna muzika'),

    ## Tallava (Kosovo / Albania)
    'tallava': ('Tallava', 'tallava'),
    'tallava music': ('Tallava', 'tallava music'),
    'muzikë tallava': ('Tallava', 'muzikë tallava'),
    'tallava kosovare': ('Tallava', 'tallava kosovare'),
    'tallava shqiptare': ('Tallava', 'tallava shqiptare'),
    'tallava moderne': ('Tallava', 'tallava moderne'),
    'tallava pop': ('Tallava', 'tallava pop'),

    ## Chalga / Pop-folk (Bulgaria)
    'chalga': ('Chalga', 'chalga'),
    'чалга': ('Chalga', 'чалга'),
    'popfolk': ('Chalga', 'popfolk'),
    'pop-folk bulgaro': ('Chalga', 'pop-folk bulgaro'),
    'etno pop': ('Chalga', 'etno pop'),
    'payner style': ('Chalga', 'payner style'),

    ## Laïko / Skyladiko (Grecia / Chipre)
    'laiko': ('Laïko', 'laiko'),
    'λαϊκό': ('Laïko', 'λαϊκό'),
    'laïkó': ('Laïko', 'laïkó'),
    'skyladiko': ('Laïko', 'skyladiko'),
    'σκυλάδικο': ('Laïko', 'σκυλάδικο'),
    'modern laiko': ('Laïko', 'modern laiko'),
    'laiko pop': ('Laïko', 'laiko pop'),
    'entechno laiko': ('Laïko', 'entechno laiko'),
    'kritiko laiko': ('Laïko', 'kritiko laiko'),
    'nisiotiko laiko': ('Laïko', 'nisiotiko laiko'),
    'pontiako laiko': ('Laïko', 'pontiako laiko'),

    ###############################################################################
    # Europa Central y Alpes
    ###############################################################################

    ## Oberkrainer / Alpine Folk (Alpes)
    'oberkrainer': ('Alpine Folk', 'oberkrainer'),
    'alpenrock': ('Alpine Folk', 'alpenrock'),
    'volkstümliche musik': ('Alpine Folk', 'volkstümliche musik'),
    'deutsche schlager': ('Alpine Folk', 'deutsche schlager'),
    'österreichische volksmusik': ('Alpine Folk', 'österreichische volksmusik'),
    'schweizer volksmusik': ('Alpine Folk', 'schweizer volksmusik'),
    'südtiroler musik': ('Alpine Folk', 'südtiroler musik'),
    'alpenpop': ('Alpine Folk', 'alpenpop'),
    'volksrock': ('Alpine Folk', 'volksrock'),

    ## Schlager (Alemania / Austria / Suiza / Benelux)
    'schlager': ('Schlager', 'schlager'),
    'volksmusik': ('Schlager', 'volksmusik'),
    'deutsche schlager': ('Schlager', 'deutsche schlager'),
    'schlager pop': ('Schlager', 'schlager pop'),
    'schlager rock': ('Schlager', 'schlager rock'),
    'party schlager': ('Schlager', 'party schlager'),
    'österreichischer schlager': ('Schlager', 'österreichischer schlager'),
    'schweizer schlager': ('Schlager', 'schweizer schlager'),
    'nederlandstalige muziek': ('Schlager', 'nederlandstalige muziek'),

    ###############################################################################
    # Europa del Este y judía
    ###############################################################################

    ## Klezmer / Jewish Music (Europa del Este / Diáspora)
    'klezmer': ('Klezmer', 'klezmer'),
    'klezmer music': ('Klezmer', 'klezmer music'),
    'ייִדישע מוזיק': ('Klezmer', 'ייִדישע מוזיק'),
    'klezmer fusion': ('Klezmer', 'klezmer fusion'),
    'klezmer jazz': ('Klezmer', 'klezmer jazz'),
    'klezmer rock': ('Klezmer', 'klezmer rock'),
    'hasidic music': ('Klezmer', 'hasidic music'),
    'galician klezmer': ('Klezmer', 'galician klezmer'),
    'romanian klezmer': ('Klezmer', 'romanian klezmer'),
    'hungarian klezmer': ('Klezmer', 'hungarian klezmer'),

    ## Roma / Gypsy Music (Europa del Este)
    'romani music': ('Roma Music', 'romani music'),
    'gypsy music': ('Roma Music', 'gypsy music'),
    'muzică țigănească': ('Roma Music', 'muzică țigănească'),
    'cigányzene': ('Roma Music', 'cigányzene'),
    'ромска музика': ('Roma Music', 'ромска музика'),
    'gypsy brass': ('Roma Music', 'gypsy brass'),
    'gypsy jazz': ('Roma Music', 'gypsy jazz'),
    'gypsy punk': ('Roma Music', 'gypsy punk'),
    'gypsy swing': ('Roma Music', 'gypsy swing'),
    'serbian roma music': ('Roma Music', 'serbian roma music'),
    'hungarian roma music': ('Roma Music', 'hungarian roma music'),
    'romanian roma music': ('Roma Music', 'romanian roma music'),
    'spanish roma music': ('Roma Music', 'spanish roma music'),

    ###############################################################################
    # Escandinavia y Nórdicos
    ###############################################################################

    ## Dansband (Suecia / Noruega / Dinamarca)
    'dansband': ('Dansband', 'dansband'),
    'dansbandsmusik': ('Dansband', 'dansbandsmusik'),
    'modern dansband': ('Dansband', 'modern dansband'),
    'dansband pop': ('Dansband', 'dansband pop'),
    'dansband rock': ('Dansband', 'dansband rock'),
    'svensk dansband': ('Dansband', 'svensk dansband'),
    'norsk dansband': ('Dansband', 'norsk dansband'),
    'dansk dansband': ('Dansband', 'dansk dansband'),

    ## Iskelmä / Kuunku (Finlandia)
    'iskelmä': ('Iskelmä', 'iskelmä'),
    'suomalainen iskelmä': ('Iskelmä', 'suomalainen iskelmä'),
    'kuunku': ('Iskelmä', 'kuunku'),
    'humppa': ('Iskelmä', 'humppa'),
    'finntango': ('Iskelmä', 'finntango'),
    'iskelmä rock': ('Iskelmä', 'iskelmä rock'),
    'iskelmä pop': ('Iskelmä', 'iskelmä pop'),

    ###############################################################################
    # Francia y Benelux
    ###############################################################################

    ## Chanson / Variété (Francia / Bélgica / Suiza)
    'chanson': ('Chanson', 'chanson'),
    'chanson française': ('Chanson', 'chanson française'),
    'chanson réaliste': ('Chanson', 'chanson réaliste'),
    'chanson à texte': ('Chanson', 'chanson à texte'),
    'variété française': ('Chanson', 'variété française'),
    'pop française': ('Chanson', 'pop française'),
    'rock français': ('Chanson', 'rock français'),
    'chanson belge': ('Chanson', 'chanson belge'),
    'chanson suisse': ('Chanson', 'chanson suisse'),

    ###############################################################################
    # Reino Unido e Irlanda
    ###############################################################################

    ## Electroswing / Swing Revival (Reino Unido / Europa)
    'electro swing': ('Electroswing', 'electro swing'),
    'electroswing': ('Electroswing', 'electroswing'),
    'swing house': ('Electroswing', 'swing house'),
    'gypsy swing electronic': ('Electroswing', 'gypsy swing electronic'),
    'jazz house': ('Electroswing', 'jazz house'),
    'swing revival': ('Electroswing', 'swing revival'),
    'neo swing': ('Electroswing', 'neo swing'),

    ###############################################################################
    # Italia
    ###############################################################################

    ## Canzone Italiana / Cantautori (Italia)
    'canzone italiana': ('Canzone Italiana', 'canzone italiana'),
    'pop italiano': ('Canzone Italiana', 'pop italiano'),
    'rock italiano': ('Canzone Italiana', 'rock italiano'),
    'cantautore': ('Canzone Italiana', 'cantautore'),
    'cantautori italiani': ('Canzone Italiana', 'cantautori italiani'),
    'sanremo music': ('Canzone Italiana', 'sanremo music'),
    'canzone napoletana': ('Canzone Italiana', 'canzone napoletana'),
    'canzone siciliana': ('Canzone Italiana', 'canzone siciliana'),
    'liscio': ('Canzone Italiana', 'liscio'),

    ###############################################################################
    # España y Portugal (Flamenco / Copla unificado y ampliado)
    ###############################################################################

    ## Flamenco / Copla (España y Portugal) - Categoría unificada y ampliada
    'flamenco': ('Flamenco / Copla', 'flamenco'),
    'cante flamenco': ('Flamenco / Copla', 'cante flamenco'),
    'toque flamenco': ('Flamenco / Copla', 'toque flamenco'),
    'baile flamenco': ('Flamenco / Copla', 'baile flamenco'),

    'flamenco clásico': ('Flamenco / Copla', 'flamenco clásico'),
    'flamenco tradicional': ('Flamenco / Copla', 'flamenco tradicional'),
    'flamenco ortodoxo': ('Flamenco / Copla', 'flamenco ortodoxo'),
    'flamenco puro': ('Flamenco / Copla', 'flamenco puro'),

    'flamenco moderno': ('Flamenco / Copla', 'flamenco moderno'),
    'nuevo flamenco': ('Flamenco / Copla', 'nuevo flamenco'),
    'flamenco contemporáneo': ('Flamenco / Copla', 'flamenco contemporáneo'),
    'flamenco fusión': ('Flamenco / Copla', 'flamenco fusión'),
    'flamenco pop': ('Flamenco / Copla', 'flamenco pop'),
    'flamenco rock': ('Flamenco / Copla', 'flamenco rock'),
    'flamenco jazz': ('Flamenco / Copla', 'flamenco jazz'),
    'flamenco electrónico': ('Flamenco / Copla', 'flamenco electrónico'),
    'flamenco chill': ('Flamenco / Copla', 'flamenco chill'),
    'flamenco latino': ('Flamenco / Copla', 'flamenco latino'),

    'copla': ('Flamenco / Copla', 'copla'),
    'canción española': ('Flamenco / Copla', 'canción española'),
    'copla andaluza': ('Flamenco / Copla', 'copla andaluza'),
    'copla tradicional': ('Flamenco / Copla', 'copla tradicional'),
    'copla moderna': ('Flamenco / Copla', 'copla moderna'),
    'copla fusión': ('Flamenco / Copla', 'copla fusión'),
    'copla pop': ('Flamenco / Copla', 'copla pop'),

    'jota': ('Flamenco / Copla', 'jota'),
    'pasodoble': ('Flamenco / Copla', 'pasodoble'),
    'pasodoble flamenco': ('Flamenco / Copla', 'pasodoble flamenco'),
    'sevillanas': ('Flamenco / Copla', 'sevillanas'),
    'sevillanas flamencas': ('Flamenco / Copla', 'sevillanas flamencas'),
    'rumba flamenca': ('Flamenco / Copla', 'rumba flamenca'),
    'rumba catalana': ('Flamenco / Copla', 'rumba catalana'),
    'rumba gitana': ('Flamenco / Copla', 'rumba gitana'),

    'tanguillos': ('Flamenco / Copla', 'tanguillos'),
    'alegrías': ('Flamenco / Copla', 'alegrías'),
    'bulerías': ('Flamenco / Copla', 'bulerías'),
    'soleá': ('Flamenco / Copla', 'soleá'),
    'seguiriya': ('Flamenco / Copla', 'seguiriya'),
    'fandango': ('Flamenco / Copla', 'fandango'),
    'granaína': ('Flamenco / Copla', 'granaína'),
    'cartagenera': ('Flamenco / Copla', 'cartagenera'),
    'media granaína': ('Flamenco / Copla', 'media granaína'),
    'guajira': ('Flamenco / Copla', 'guajira'),
    'colombiana': ('Flamenco / Copla', 'colombiana'),
    'verdiales': ('Flamenco / Copla', 'verdiales'),
    'malagueña': ('Flamenco / Copla', 'malagueña'),
    'taranto': ('Flamenco / Copla', 'taranto'),
    'taranta': ('Flamenco / Copla', 'taranta'),
    'minera': ('Flamenco / Copla', 'minera'),
    'levantica': ('Flamenco / Copla', 'levantica'),
    'saeta': ('Flamenco / Copla', 'saeta'),

    'fado flamenco': ('Flamenco / Copla', 'fado flamenco'),  # fusión con Portugal
    'portuguese flamenco': ('Flamenco / Copla', 'portuguese flamenco'),

    ###############################################################################
    # Asia - K-Pop/K-Rock (Regional - Corea)
    ###############################################################################
    ## K-Pop General
    'kpop': ('K-Pop/K-Rock', 'kpop'),
    'k-pop': ('K-Pop/K-Rock', 'k-pop'),
    'k pop': ('K-Pop/K-Rock', 'k pop'),
    'korean pop': ('K-Pop/K-Rock', 'korean pop'),
    'corean pop': ('K-Pop/K-Rock', 'corean pop'),
    'música kpop': ('K-Pop/K-Rock', 'música kpop'),

    ## K-pop idol (grupos)
    'kpop idol': ('K-Pop/K-Rock', 'kpop idol'),
    'k-pop idol': ('K-Pop/K-Rock', 'k-pop idol'),
    'idol group': ('K-Pop/K-Rock', 'idol group'),
    'kpop group': ('K-Pop/K-Rock', 'kpop group'),
    'kpop boy group': ('K-Pop/K-Rock', 'kpop boy group'),
    'kpop girl group': ('K-Pop/K-Rock', 'kpop girl group'),
    'boy band kpop': ('K-Pop/K-Rock', 'boy band kpop'),
    'girl group kpop': ('K-Pop/K-Rock', 'girl group kpop'),

    ## K-pop solista
    'kpop solo': ('K-Pop/K-Rock', 'kpop solo'),
    'k-pop solo': ('K-Pop/K-Rock', 'k-pop solo'),
    'solo kpop': ('K-Pop/K-Rock', 'solo kpop'),
    'kpop soloist': ('K-Pop/K-Rock', 'kpop soloist'),

    ## Idol group (subunidades)
    'subunit': ('K-Pop/K-Rock', 'subunit'),
    'kpop subunit': ('K-Pop/K-Rock', 'kpop subunit'),
    'subunidad kpop': ('K-Pop/K-Rock', 'subunidad kpop'),
    'idol subunit': ('K-Pop/K-Rock', 'idol subunit'),

    ## K-rap / K-hip hop
    'khiphop': ('K-Pop/K-Rock', 'khiphop'),
    'k-hiphop': ('K-Pop/K-Rock', 'k-hiphop'),
    'khip hop': ('K-Pop/K-Rock', 'khip hop'),
    'k-rap': ('K-Pop/K-Rock', 'k-rap'),
    'korean hip hop': ('K-Pop/K-Rock', 'korean hip hop'),
    'corean rap': ('K-Pop/K-Rock', 'corean rap'),
    'korean rap': ('K-Pop/K-Rock', 'korean rap'),

    ## K-R&B
    'krnb': ('K-Pop/K-Rock', 'krnb'),
    'k-rnb': ('K-Pop/K-Rock', 'k-rnb'),
    'k rnb': ('K-Pop/K-Rock', 'k rnb'),
    'korean rnb': ('K-Pop/K-Rock', 'korean rnb'),
    'korean r&b': ('K-Pop/K-Rock', 'korean r&b'),
    'corean r&b': ('K-Pop/K-Rock', 'corean r&b'),

    ## Korean ballad
    'korean ballad': ('K-Pop/K-Rock', 'korean ballad'),
    'k-ballad': ('K-Pop/K-Rock', 'k-ballad'),
    'kballad': ('K-Pop/K-Rock', 'kballad'),
    'corean ballad': ('K-Pop/K-Rock', 'corean ballad'),
    'balada coreana': ('K-Pop/K-Rock', 'balada coreana'),

    ## Korean rock (K-rock)
    'krock': ('K-Pop/K-Rock', 'krock'),
    'k-rock': ('K-Pop/K-Rock', 'k-rock'),
    'korean rock': ('K-Pop/K-Rock', 'korean rock'),
    'corean rock': ('K-Pop/K-Rock', 'corean rock'),
    'rock coreano': ('K-Pop/K-Rock', 'rock coreano'),
    'korean indie rock': ('K-Pop/K-Rock', 'korean indie rock'),

    ### Subgéneros de K-rock
    'korean metal': ('K-Pop/K-Rock', 'korean metal'),
    'k-metal': ('K-Pop/K-Rock', 'k-metal'),
    'korean punk': ('K-Pop/K-Rock', 'korean punk'),
    'k-punk': ('K-Pop/K-Rock', 'k-punk'),
    'korean alternative': ('K-Pop/K-Rock', 'korean alternative'),

    ## Korean indie
    'kindie': ('K-Pop/K-Rock', 'kindie'),
    'k-indie': ('K-Pop/K-Rock', 'k-indie'),
    'korean indie': ('K-Pop/K-Rock', 'korean indie'),
    'indie coreano': ('K-Pop/K-Rock', 'indie coreano'),

    ## Korean trot
    'ktrot': ('K-Pop/K-Rock', 'ktrot'),
    'k-trot': ('K-Pop/K-Rock', 'k-trot'),
    'korean trot': ('K-Pop/K-Rock', 'korean trot'),
    'trot coreano': ('K-Pop/K-Rock', 'trot coreano'),
    'ppongjjak': ('K-Pop/K-Rock', 'ppongjjak'),

    ## K-pop experimental
    'kpop experimental': ('K-Pop/K-Rock', 'kpop experimental'),
    'experimental kpop': ('K-Pop/K-Rock', 'experimental kpop'),
    'kpop avantgarde': ('K-Pop/K-Rock', 'kpop avantgarde'),

    ## K-pop fusión
    'kpop fusion': ('K-Pop/K-Rock', 'kpop fusion'),
    'kpop edm': ('K-Pop/K-Rock', 'kpop edm'),
    'kpop electronic': ('K-Pop/K-Rock', 'kpop electronic'),
    'kpop jazz': ('K-Pop/K-Rock', 'kpop jazz'),
    'kpop latin': ('K-Pop/K-Rock', 'kpop latin'),

    ## Generaciones de K-pop
    '1st gen kpop': ('K-Pop/K-Rock', '1st gen kpop'),
    '2nd gen kpop': ('K-Pop/K-Rock', '2nd gen kpop'),
    '3rd gen kpop': ('K-Pop/K-Rock', '3rd gen kpop'),
    '4th gen kpop': ('K-Pop/K-Rock', '4th gen kpop'),
    '5th gen kpop': ('K-Pop/K-Rock', '5th gen kpop'),

    ## K-pop por concepto
    'kpop dark': ('K-Pop/K-Rock', 'kpop dark'),
    'kpop cute': ('K-Pop/K-Rock', 'kpop cute'),
    'kpop sexy': ('K-Pop/K-Rock', 'kpop sexy'),
    'kpop girl crush': ('K-Pop/K-Rock', 'kpop girl crush'),
    'kpop teen crush': ('K-Pop/K-Rock', 'kpop teen crush'),
    'kpop retro': ('K-Pop/K-Rock', 'kpop retro'),
    'kpop concept': ('K-Pop/K-Rock', 'kpop concept'),

    ## K-pop por sonido
    'kpop noise music': ('K-Pop/K-Rock', 'kpop noise music'),
    'kpop orchestral': ('K-Pop/K-Rock', 'kpop orchestral'),
    'kpop orchestrada': ('K-Pop/K-Rock', 'kpop orchestrada'),
    'kpop rock': ('K-Pop/K-Rock', 'kpop rock'),
    'kpop pop rock': ('K-Pop/K-Rock', 'kpop pop rock'),

    ## K-OST (bandas sonoras coreanas)
    'kost': ('K-Pop/K-Rock', 'kost'),
    'k-ost': ('K-Pop/K-Rock', 'k-ost'),
    'korean ost': ('K-Pop/K-Rock', 'korean ost'),
    'korean soundtrack': ('K-Pop/K-Rock', 'korean soundtrack'),
    'drama ost': ('K-Pop/K-Rock', 'drama ost'),
    'k-drama ost': ('K-Pop/K-Rock', 'k-drama ost'),

    ## K-pop acústico / balada
    'kpop acoustic': ('K-Pop/K-Rock', 'kpop acoustic'),
    'acoustic kpop': ('K-Pop/K-Rock', 'acoustic kpop'),
    'kpop ballad': ('K-Pop/K-Rock', 'kpop ballad'),
    'ballad kpop': ('K-Pop/K-Rock', 'ballad kpop'),

    ## K-pop dance
    'kpop dance': ('K-Pop/K-Rock', 'kpop dance'),
    'dance kpop': ('K-Pop/K-Rock', 'dance kpop'),
    'kpop choreo': ('K-Pop/K-Rock', 'kpop choreo'),

    ## K-pop city pop
    'korean city pop': ('K-Pop/K-Rock', 'korean city pop'),
    'k-city pop': ('K-Pop/K-Rock', 'k-city pop'),
    'city pop coreano': ('K-Pop/K-Rock', 'city pop coreano'),

    ## K-pop retro / synth
    'kpop retro': ('K-Pop/K-Rock', 'kpop retro'),
    'kpop synthwave': ('K-Pop/K-Rock', 'kpop synthwave'),
    'kpop 80s': ('K-Pop/K-Rock', 'kpop 80s'),
    'kpop 90s': ('K-Pop/K-Rock', 'kpop 90s'),

    ## K-pop por región (Corea del Sur)
    'kpop seoul': ('K-Pop/K-Rock', 'kpop seoul'),
    'kpop busan': ('K-Pop/K-Rock', 'kpop busan'),
    'kpop daegu': ('K-Pop/K-Rock', 'kpop daegu'),

    ## K-pop companies (estilos)
    'kpop sm': ('K-Pop/K-Rock', 'kpop sm'),
    'sm entertainment style': ('K-Pop/K-Rock', 'sm entertainment style'),
    'kpop yg': ('K-Pop/K-Rock', 'kpop yg'),
    'yg style': ('K-Pop/K-Rock', 'yg style'),
    'kpop jyp': ('K-Pop/K-Rock', 'kpop jyp'),
    'jyp style': ('K-Pop/K-Rock', 'jyp style'),
    'kpop hybe': ('K-Pop/K-Rock', 'kpop hybe'),
    'hybe style': ('K-Pop/K-Rock', 'hybe style'),

    ###############################################################################
    # J-Pop/J-Rock (Regional - Japón)
    ###############################################################################
    ## J-Pop General
    'jpop': ('J-Pop/J-Rock', 'jpop'),
    'j-pop': ('J-Pop/J-Rock', 'j-pop'),
    'j pop': ('J-Pop/J-Rock', 'j pop'),
    'japanese pop': ('J-Pop/J-Rock', 'japanese pop'),
    'japonés pop': ('J-Pop/J-Rock', 'japonés pop'),
    'pop japonés': ('J-Pop/J-Rock', 'pop japonés'),

    ## J-pop mainstream
    'jpop mainstream': ('J-Pop/J-Rock', 'jpop mainstream'),
    'mainstream jpop': ('J-Pop/J-Rock', 'mainstream jpop'),
    'jpop comercial': ('J-Pop/J-Rock', 'jpop comercial'),
    'commercial jpop': ('J-Pop/J-Rock', 'commercial jpop'),

    ## City pop (retro)
    'city pop': ('J-Pop/J-Rock', 'city pop'),
    'japanese city pop': ('J-Pop/J-Rock', 'japanese city pop'),
    'citypop': ('J-Pop/J-Rock', 'citypop'),
    'city pop retro': ('J-Pop/J-Rock', 'city pop retro'),
    '80s city pop': ('J-Pop/J-Rock', '80s city pop'),
    'city pop japonés': ('J-Pop/J-Rock', 'city pop japonés'),

    ## Anisong (anime)
    'anisong': ('J-Pop/J-Rock', 'anisong'),
    'anime song': ('J-Pop/J-Rock', 'anime song'),
    'anison': ('J-Pop/J-Rock', 'anison'),
    'jpop anime': ('J-Pop/J-Rock', 'jpop anime'),
    'anime opening': ('J-Pop/J-Rock', 'anime opening'),
    'anime ending': ('J-Pop/J-Rock', 'anime ending'),
    'anime soundtrack jpop': ('J-Pop/J-Rock', 'anime soundtrack jpop'),

    ## Shibuya-kei
    'shibuya kei': ('J-Pop/J-Rock', 'shibuya kei'),
    'shibuya-kei': ('J-Pop/J-Rock', 'shibuya-kei'),
    'shibuyakei': ('J-Pop/J-Rock', 'shibuyakei'),
    'shibuya pop': ('J-Pop/J-Rock', 'shibuya pop'),

    ## Akishibu-kei
    'akishibu kei': ('J-Pop/J-Rock', 'akishibu kei'),
    'akishibu-kei': ('J-Pop/J-Rock', 'akishibu-kei'),
    'akishibukei': ('J-Pop/J-Rock', 'akishibukei'),

    ## J-rock
    'jrock': ('J-Pop/J-Rock', 'jrock'),
    'j-rock': ('J-Pop/J-Rock', 'j-rock'),
    'j rock': ('J-Pop/J-Rock', 'j rock'),
    'japanese rock': ('J-Pop/J-Rock', 'japanese rock'),
    'rock japonés': ('J-Pop/J-Rock', 'rock japonés'),

    ### Subgéneros de J-rock
    'j-rock alternativo': ('J-Pop/J-Rock', 'j-rock alternativo'),
    'japanese alternative rock': ('J-Pop/J-Rock', 'japanese alternative rock'),
    'japanese indie rock': ('J-Pop/J-Rock', 'japanese indie rock'),
    'japanese punk': ('J-Pop/J-Rock', 'japanese punk'),
    'j-punk': ('J-Pop/J-Rock', 'j-punk'),
    'japanese metal': ('J-Pop/J-Rock', 'japanese metal'),
    'j-metal': ('J-Pop/J-Rock', 'j-metal'),

    ## Visual kei (vertiente pop)
    'visual kei': ('J-Pop/J-Rock', 'visual kei'),
    'visual-kei': ('J-Pop/J-Rock', 'visual-kei'),
    'visual kei pop': ('J-Pop/J-Rock', 'visual kei pop'),
    'visual kei rock': ('J-Pop/J-Rock', 'visual kei rock'),
    'v系': ('J-Pop/J-Rock', 'v系'),

    ### Subgéneros de Visual kei
    'angura kei': ('J-Pop/J-Rock', 'angura kei'),
    'oshare kei': ('J-Pop/J-Rock', 'oshare kei'),
    'kote kei': ('J-Pop/J-Rock', 'kote kei'),
    'nagoya kei': ('J-Pop/J-Rock', 'nagoya kei'),

    ## J-rap / J-hip hop
    'jrap': ('J-Pop/J-Rock', 'jrap'),
    'j-rap': ('J-Pop/J-Rock', 'j-rap'),
    'jhiphop': ('J-Pop/J-Rock', 'jhiphop'),
    'j-hiphop': ('J-Pop/J-Rock', 'j-hiphop'),
    'japanese hip hop': ('J-Pop/J-Rock', 'japanese hip hop'),
    'japanese rap': ('J-Pop/J-Rock', 'japanese rap'),
    'rap japonés': ('J-Pop/J-Rock', 'rap japonés'),

    ## Japanese R&B
    'jrnb': ('J-Pop/J-Rock', 'jrnb'),
    'j-rnb': ('J-Pop/J-Rock', 'j-rnb'),
    'japanese r&b': ('J-Pop/J-Rock', 'japanese r&b'),
    'japanese rnb': ('J-Pop/J-Rock', 'japanese rnb'),
    'r&b japonés': ('J-Pop/J-Rock', 'r&b japonés'),

    ## Japanese ambient pop
    'japanese ambient pop': ('J-Pop/J-Rock', 'japanese ambient pop'),
    'ambient jpop': ('J-Pop/J-Rock', 'ambient jpop'),
    'japanese ambient': ('J-Pop/J-Rock', 'japanese ambient'),
    'ambient pop japones': ('J-Pop/J-Rock', 'ambient pop japones'),

    ## J-pop electrónico / EDM
    'jpop edm': ('J-Pop/J-Rock', 'jpop edm'),
    'jpop electronic': ('J-Pop/J-Rock', 'jpop electronic'),
    'japanese electro': ('J-Pop/J-Rock', 'japanese electro'),
    'jpop dance': ('J-Pop/J-Rock', 'jpop dance'),

    ## J-pop balada
    'jpop ballad': ('J-Pop/J-Rock', 'jpop ballad'),
    'japanese ballad': ('J-Pop/J-Rock', 'japanese ballad'),
    'ballad jpop': ('J-Pop/J-Rock', 'ballad jpop'),
    'jpop romántico': ('J-Pop/J-Rock', 'jpop romántico'),

    ## J-pop por épocas
    'jpop 80s': ('J-Pop/J-Rock', 'jpop 80s'),
    'jpop 90s': ('J-Pop/J-Rock', 'jpop 90s'),
    'jpop 2000s': ('J-Pop/J-Rock', 'jpop 2000s'),
    'jpop 2010s': ('J-Pop/J-Rock', 'jpop 2010s'),
    'jpop 2020s': ('J-Pop/J-Rock', 'jpop 2020s'),
    'jpop moderno': ('J-Pop/J-Rock', 'jpop moderno'),
    'modern jpop': ('J-Pop/J-Rock', 'modern jpop'),
    'classic jpop': ('J-Pop/J-Rock', 'classic jpop'),

    ## J-pop idol
    'jpop idol': ('J-Pop/J-Rock', 'jpop idol'),
    'japanese idol': ('J-Pop/J-Rock', 'japanese idol'),
    'idol jpop': ('J-Pop/J-Rock', 'idol jpop'),
    'jpop boy band': ('J-Pop/J-Rock', 'jpop boy band'),
    'jpop girl group': ('J-Pop/J-Rock', 'jpop girl group'),
    'japanese boy band': ('J-Pop/J-Rock', 'japanese boy band'),
    'japanese girl group': ('J-Pop/J-Rock', 'japanese girl group'),

    ## J-pop / J-rock fusión
    'jpop fusion': ('J-Pop/J-Rock', 'jpop fusion'),
    'jpop rock': ('J-Pop/J-Rock', 'jpop rock'),
    'jrock pop': ('J-Pop/J-Rock', 'jrock pop'),
    'jpop jazz': ('J-Pop/J-Rock', 'jpop jazz'),
    'jazz jpop': ('J-Pop/J-Rock', 'jazz jpop'),
    'jpop folk': ('J-Pop/J-Rock', 'jpop folk'),
    'folk jpop': ('J-Pop/J-Rock', 'folk jpop'),

    ## J-OST (bandas sonoras japonesas)
    'jost': ('J-Pop/J-Rock', 'jost'),
    'j-ost': ('J-Pop/J-Rock', 'j-ost'),
    'japanese ost': ('J-Pop/J-Rock', 'japanese ost'),
    'japanese soundtrack': ('J-Pop/J-Rock', 'japanese soundtrack'),
    'drama ost japones': ('J-Pop/J-Rock', 'drama ost japones'),
    'j-drama ost': ('J-Pop/J-Rock', 'j-drama ost'),

    ## J-pop instrumental
    'jpop instrumental': ('J-Pop/J-Rock', 'jpop instrumental'),
    'instrumental jpop': ('J-Pop/J-Rock', 'instrumental jpop'),

    ## J-pop por región
    'jpop tokyo': ('J-Pop/J-Rock', 'jpop tokyo'),
    'tokyo jpop': ('J-Pop/J-Rock', 'tokyo jpop'),
    'jpop osaka': ('J-Pop/J-Rock', 'jpop osaka'),
    'osaka jpop': ('J-Pop/J-Rock', 'osaka jpop'),

    ## Showa pop
    'showa pop': ('J-Pop/J-Rock', 'showa pop'),
    'showa kayo': ('J-Pop/J-Rock', 'showa kayo'),
    'kayokyoku': ('J-Pop/J-Rock', 'kayokyoku'),

    ## Group sounds
    'group sounds': ('J-Pop/J-Rock', 'group sounds'),
    'gs jpop': ('J-Pop/J-Rock', 'gs jpop'),
    'japanese group sounds': ('J-Pop/J-Rock', 'japanese group sounds'),

    ## J-pop experimental
    'jpop experimental': ('J-Pop/J-Rock', 'jpop experimental'),
    'experimental jpop': ('J-Pop/J-Rock', 'experimental jpop'),
    'avant jpop': ('J-Pop/J-Rock', 'avant jpop'),

    ###############################################################################
    # T-Pop/T-Rock (Regional - Tailandia)
    ###############################################################################
    ## T-Pop General
    'tpop': ('T-Pop/T-Rock', 'tpop'),
    't-pop': ('T-Pop/T-Rock', 't-pop'),
    't pop': ('T-Pop/T-Rock', 't pop'),
    'thai pop': ('T-Pop/T-Rock', 'thai pop'),
    'pop tailandés': ('T-Pop/T-Rock', 'pop tailandés'),
    'música tailandesa': ('T-Pop/T-Rock', 'música tailandesa'),

    ## T-pop moderno
    'tpop moderno': ('T-Pop/T-Rock', 'tpop moderno'),
    'modern tpop': ('T-Pop/T-Rock', 'modern tpop'),
    'contemporary thai pop': ('T-Pop/T-Rock', 'contemporary thai pop'),
    'thai pop moderno': ('T-Pop/T-Rock', 'thai pop moderno'),
    'tpop contemporáneo': ('T-Pop/T-Rock', 'tpop contemporáneo'),

    ## Luk thung (música rural tailandesa)
    'luk thung': ('T-Pop/T-Rock', 'luk thung'),
    'lukthung': ('T-Pop/T-Rock', 'lukthung'),
    'thai country': ('T-Pop/T-Rock', 'thai country'),
    'country tailandés': ('T-Pop/T-Rock', 'country tailandés'),
    'phleng luk thung': ('T-Pop/T-Rock', 'phleng luk thung'),
    'luk thung tradicional': ('T-Pop/T-Rock', 'luk thung tradicional'),

    ## Mor lam (música del noreste)
    'mor lam': ('T-Pop/T-Rock', 'mor lam'),
    'molam': ('T-Pop/T-Rock', 'molam'),
    'mor lam sing': ('T-Pop/T-Rock', 'mor lam sing'),
    'mor lam tradicional': ('T-Pop/T-Rock', 'mor lam tradicional'),
    'laos music': ('T-Pop/T-Rock', 'laos music'),
    'mor lam isan': ('T-Pop/T-Rock', 'mor lam isan'),
    'noreste tailandés': ('T-Pop/T-Rock', 'noreste tailandés'),

    ## Thai rock
    'thai rock': ('T-Pop/T-Rock', 'thai rock'),
    't-rock': ('T-Pop/T-Rock', 't-rock'),
    'trock': ('T-Pop/T-Rock', 'trock'),
    'rock tailandés': ('T-Pop/T-Rock', 'rock tailandés'),

    ### Subgéneros de Thai rock
    'thai alternative rock': ('T-Pop/T-Rock', 'thai alternative rock'),
    'thai indie rock': ('T-Pop/T-Rock', 'thai indie rock'),
    'thai punk': ('T-Pop/T-Rock', 'thai punk'),
    'thai metal': ('T-Pop/T-Rock', 'thai metal'),
    'thai progressive rock': ('T-Pop/T-Rock', 'thai progressive rock'),

    ## Thai rap
    'thai rap': ('T-Pop/T-Rock', 'thai rap'),
    't-rap': ('T-Pop/T-Rock', 't-rap'),
    'thai hip hop': ('T-Pop/T-Rock', 'thai hip hop'),
    't-hiphop': ('T-Pop/T-Rock', 't-hiphop'),
    'rap tailandés': ('T-Pop/T-Rock', 'rap tailandés'),

    ## Thai R&B
    'thai r&b': ('T-Pop/T-Rock', 'thai r&b'),
    'thai rnb': ('T-Pop/T-Rock', 'thai rnb'),
    't-rnb': ('T-Pop/T-Rock', 't-rnb'),
    'r&b tailandés': ('T-Pop/T-Rock', 'r&b tailandés'),

    ## Thai country
    'thai country': ('T-Pop/T-Rock', 'thai country'),
    'country tailandés': ('T-Pop/T-Rock', 'country tailandés'),
    'phleng luk thung': ('T-Pop/T-Rock', 'phleng luk thung'),
    'luk thung moderno': ('T-Pop/T-Rock', 'luk thung moderno'),

    ## T-pop idol
    'tpop idol': ('T-Pop/T-Rock', 'tpop idol'),
    'thai idol': ('T-Pop/T-Rock', 'thai idol'),
    't-idol': ('T-Pop/T-Rock', 't-idol'),
    'thai boy band': ('T-Pop/T-Rock', 'thai boy band'),
    'thai girl group': ('T-Pop/T-Rock', 'thai girl group'),

    ## Thai fusion
    'thai fusion': ('T-Pop/T-Rock', 'thai fusion'),
    'tpop fusion': ('T-Pop/T-Rock', 'tpop fusion'),
    'luk thung pop': ('T-Pop/T-Rock', 'luk thung pop'),
    'mor lam pop': ('T-Pop/T-Rock', 'mor lam pop'),
    'mor lam fusion': ('T-Pop/T-Rock', 'mor lam fusion'),
    'thai electro pop': ('T-Pop/T-Rock', 'thai electro pop'),

    ## Thai indie
    'thai indie': ('T-Pop/T-Rock', 'thai indie'),
    't-indie': ('T-Pop/T-Rock', 't-indie'),
    'indie tailandés': ('T-Pop/T-Rock', 'indie tailandés'),
    'thai independent': ('T-Pop/T-Rock', 'thai independent'),

    ## Thai ballad
    'thai ballad': ('T-Pop/T-Rock', 'thai ballad'),
    't-ballad': ('T-Pop/T-Rock', 't-ballad'),
    'balada tailandesa': ('T-Pop/T-Rock', 'balada tailandesa'),

    ## Thai OST
    'thai ost': ('T-Pop/T-Rock', 'thai ost'),
    't-ost': ('T-Pop/T-Rock', 't-ost'),
    'thai drama ost': ('T-Pop/T-Rock', 'thai drama ost'),
    'thai lakorn ost': ('T-Pop/T-Rock', 'thai lakorn ost'),
    'thai movie soundtrack': ('T-Pop/T-Rock', 'thai movie soundtrack'),

    ## Thai pop por épocas
    'tpop 80s': ('T-Pop/T-Rock', 'tpop 80s'),
    'tpop 90s': ('T-Pop/T-Rock', 'tpop 90s'),
    'tpop 2000s': ('T-Pop/T-Rock', 'tpop 2000s'),
    'tpop 2010s': ('T-Pop/T-Rock', 'tpop 2010s'),
    'tpop 2020s': ('T-Pop/T-Rock', 'tpop 2020s'),
    'thai pop clasico': ('T-Pop/T-Rock', 'thai pop clasico'),
    'classic thai pop': ('T-Pop/T-Rock', 'classic thai pop'),

    ## Thai pop por región
    'bangkok pop': ('T-Pop/T-Rock', 'bangkok pop'),
    'chiang mai pop': ('T-Pop/T-Rock', 'chiang mai pop'),
    'phuket pop': ('T-Pop/T-Rock', 'phuket pop'),
    'isan pop': ('T-Pop/T-Rock', 'isan pop'),

    ## Thai traditional fusion
    'thai traditional pop': ('T-Pop/T-Rock', 'thai traditional pop'),
    'traditional thai music fusion': ('T-Pop/T-Rock', 'traditional thai music fusion'),
    'thai classical fusion': ('T-Pop/T-Rock', 'thai classical fusion'),

    ## Thai electronic
    'thai electronic': ('T-Pop/T-Rock', 'thai electronic'),
    'thai edm': ('T-Pop/T-Rock', 'thai edm'),
    't-edm': ('T-Pop/T-Rock', 't-edm'),

    ## Thai pop instrumental
    'thai pop instrumental': ('T-Pop/T-Rock', 'thai pop instrumental'),
    'instrumental thai pop': ('T-Pop/T-Rock', 'instrumental thai pop'),

    ## Thai jazz pop
    'thai jazz pop': ('T-Pop/T-Rock', 'thai jazz pop'),
    'jazz thai pop': ('T-Pop/T-Rock', 'jazz thai pop'),

    ## String combo (pop tailandés clásico)
    'string combo': ('T-Pop/T-Rock', 'string combo'),
    'thai string': ('T-Pop/T-Rock', 'thai string'),
    'string pop thai': ('T-Pop/T-Rock', 'string pop thai'),

    ###############################################################################
    # V-Pop/V-Rock (Regional - Vietnam)
    ###############################################################################
    ## V-Pop General
    'vpop': ('V-Pop/V-Rock', 'vpop'),
    'v-pop': ('V-Pop/V-Rock', 'v-pop'),
    'v pop': ('V-Pop/V-Rock', 'v pop'),
    'vietnamese pop': ('V-Pop/V-Rock', 'vietnamese pop'),
    'pop vietnamita': ('V-Pop/V-Rock', 'pop vietnamita'),
    'música vietnamita': ('V-Pop/V-Rock', 'música vietnamita'),

    ## V-pop moderno
    'vpop moderno': ('V-Pop/V-Rock', 'vpop moderno'),
    'modern vpop': ('V-Pop/V-Rock', 'modern vpop'),
    'contemporary vietnamese pop': ('V-Pop/V-Rock', 'contemporary vietnamese pop'),
    'vpop contemporáneo': ('V-Pop/V-Rock', 'vpop contemporáneo'),
    'viet pop actual': ('V-Pop/V-Rock', 'viet pop actual'),

    ## Nhạc đỏ (música roja / revolucionaria)
    'nhac do': ('V-Pop/V-Rock', 'nhac do'),
    'nhạc đỏ': ('V-Pop/V-Rock', 'nhạc đỏ'),
    'red music': ('V-Pop/V-Rock', 'red music'),
    'vietnamese revolutionary music': ('V-Pop/V-Rock', 'vietnamese revolutionary music'),
    'música roja vietnamita': ('V-Pop/V-Rock', 'música roja vietnamita'),
    'nhạc cách mạng': ('V-Pop/V-Rock', 'nhạc cách mạng'),

    ## Vietnamese rock
    'vietnamese rock': ('V-Pop/V-Rock', 'vietnamese rock'),
    'v-rock': ('V-Pop/V-Rock', 'v-rock'),
    'vrock': ('V-Pop/V-Rock', 'vrock'),
    'rock vietnamita': ('V-Pop/V-Rock', 'rock vietnamita'),

    ### Subgéneros de Vietnamese rock
    'vietnamese alternative rock': ('V-Pop/V-Rock', 'vietnamese alternative rock'),
    'vietnamese indie rock': ('V-Pop/V-Rock', 'vietnamese indie rock'),
    'vietnamese punk': ('V-Pop/V-Rock', 'vietnamese punk'),
    'vietnamese metal': ('V-Pop/V-Rock', 'vietnamese metal'),
    'vietnamese progressive rock': ('V-Pop/V-Rock', 'vietnamese progressive rock'),

    ## Vietnamese rap
    'vietnamese rap': ('V-Pop/V-Rock', 'vietnamese rap'),
    'v-rap': ('V-Pop/V-Rock', 'v-rap'),
    'vietnamese hip hop': ('V-Pop/V-Rock', 'vietnamese hip hop'),
    'v-hiphop': ('V-Pop/V-Rock', 'v-hiphop'),
    'rap vietnamita': ('V-Pop/V-Rock', 'rap vietnamita'),

    ## Vietnamese folk
    'vietnamese folk': ('V-Pop/V-Rock', 'vietnamese folk'),
    'folk vietnamita': ('V-Pop/V-Rock', 'folk vietnamita'),
    'dan ca': ('V-Pop/V-Rock', 'dan ca'),
    'dân ca': ('V-Pop/V-Rock', 'dân ca'),
    'vietnamese traditional folk': ('V-Pop/V-Rock', 'vietnamese traditional folk'),
    'quan ho': ('V-Pop/V-Rock', 'quan ho'),
    'ca tru': ('V-Pop/V-Rock', 'ca tru'),

    ## Bolero vietnamita
    'vietnamese bolero': ('V-Pop/V-Rock', 'vietnamese bolero'),
    'bolero vietnamita': ('V-Pop/V-Rock', 'bolero vietnamita'),
    'nhac bolero': ('V-Pop/V-Rock', 'nhac bolero'),
    'vietnamese golden music': ('V-Pop/V-Rock', 'vietnamese golden music'),
    'bolero saigon': ('V-Pop/V-Rock', 'bolero saigon'),
    'vietnamese sentimental music': ('V-Pop/V-Rock', 'vietnamese sentimental music'),

    ## Cải lương (teatro musical)
    'cai luong': ('V-Pop/V-Rock', 'cai luong'),
    'cải lương': ('V-Pop/V-Rock', 'cải lương'),
    'vietnamese opera': ('V-Pop/V-Rock', 'vietnamese opera'),
    'vietnamese musical theater': ('V-Pop/V-Rock', 'vietnamese musical theater'),
    'cai luong theater': ('V-Pop/V-Rock', 'cai luong theater'),

    ## V-pop ballad
    'vpop ballad': ('V-Pop/V-Rock', 'vpop ballad'),
    'vietnamese ballad': ('V-Pop/V-Rock', 'vietnamese ballad'),
    'balada vietnamita': ('V-Pop/V-Rock', 'balada vietnamita'),
    'tinh ca': ('V-Pop/V-Rock', 'tinh ca'),

    ## V-pop idol
    'vpop idol': ('V-Pop/V-Rock', 'vpop idol'),
    'vietnamese idol': ('V-Pop/V-Rock', 'vietnamese idol'),
    'v-idol': ('V-Pop/V-Rock', 'v-idol'),
    'vietnamese boy band': ('V-Pop/V-Rock', 'vietnamese boy band'),
    'vietnamese girl group': ('V-Pop/V-Rock', 'vietnamese girl group'),

    ## V-pop fusion
    'vpop fusion': ('V-Pop/V-Rock', 'vpop fusion'),
    'vietnamese fusion': ('V-Pop/V-Rock', 'vietnamese fusion'),
    'vpop rock': ('V-Pop/V-Rock', 'vpop rock'),
    'vpop edm': ('V-Pop/V-Rock', 'vpop edm'),
    'vpop r&b': ('V-Pop/V-Rock', 'vpop r&b'),
    'vpop folk fusion': ('V-Pop/V-Rock', 'vpop folk fusion'),

    ## V-pop por épocas
    'vpop 80s': ('V-Pop/V-Rock', 'vpop 80s'),
    'vpop 90s': ('V-Pop/V-Rock', 'vpop 90s'),
    'vpop 2000s': ('V-Pop/V-Rock', 'vpop 2000s'),
    'vpop 2010s': ('V-Pop/V-Rock', 'vpop 2010s'),
    'vpop 2020s': ('V-Pop/V-Rock', 'vpop 2020s'),
    'vpop clasico': ('V-Pop/V-Rock', 'vpop clasico'),
    'classic vpop': ('V-Pop/V-Rock', 'classic vpop'),
    'vpop pre 75': ('V-Pop/V-Rock', 'vpop pre 75'),
    'vpop post 75': ('V-Pop/V-Rock', 'vpop post 75'),

    ## V-pop por región
    'saigon pop': ('V-Pop/V-Rock', 'saigon pop'),
    'hanoi pop': ('V-Pop/V-Rock', 'hanoi pop'),
    'hcmc pop': ('V-Pop/V-Rock', 'hcmc pop'),
    'danang pop': ('V-Pop/V-Rock', 'danang pop'),

    ## Nhạc trẻ (música juvenil)
    'nhac tre': ('V-Pop/V-Rock', 'nhac tre'),
    'nhạc trẻ': ('V-Pop/V-Rock', 'nhạc trẻ'),
    'young music vietnam': ('V-Pop/V-Rock', 'young music vietnam'),
    'vietnamese youth music': ('V-Pop/V-Rock', 'vietnamese youth music'),

    ## V-pop instrumental
    'vpop instrumental': ('V-Pop/V-Rock', 'vpop instrumental'),
    'instrumental vpop': ('V-Pop/V-Rock', 'instrumental vpop'),

    ## V-pop OST
    'vpop ost': ('V-Pop/V-Rock', 'vpop ost'),
    'v-ost': ('V-Pop/V-Rock', 'v-ost'),
    'vietnamese drama ost': ('V-Pop/V-Rock', 'vietnamese drama ost'),
    'vietnamese movie soundtrack': ('V-Pop/V-Rock', 'vietnamese movie soundtrack'),

    ## V-pop R&B
    'vpop r&b': ('V-Pop/V-Rock', 'vpop r&b'),
    'vietnamese r&b': ('V-Pop/V-Rock', 'vietnamese r&b'),
    'v-rnb': ('V-Pop/V-Rock', 'v-rnb'),

    ## V-pop electronic
    'vpop electronic': ('V-Pop/V-Rock', 'vpop electronic'),
    'vietnamese edm': ('V-Pop/V-Rock', 'vietnamese edm'),
    'v-edm': ('V-Pop/V-Rock', 'v-edm'),

    ## V-pop acoustic
    'vpop acoustic': ('V-Pop/V-Rock', 'vpop acoustic'),
    'acoustic vpop': ('V-Pop/V-Rock', 'acoustic vpop'),
    'vietnamese acoustic': ('V-Pop/V-Rock', 'vietnamese acoustic'),

    ## Nhạc vàng (música amarilla - preguerra)
    'nhac vang': ('V-Pop/V-Rock', 'nhac vang'),
    'nhạc vàng': ('V-Pop/V-Rock', 'nhạc vàng'),
    'yellow music': ('V-Pop/V-Rock', 'yellow music'),
    'south vietnam pre 75': ('V-Pop/V-Rock', 'south vietnam pre 75'),

    ###############################################################################
    # OPM (Original Pilipino Music) (Regional - Filipinas)
    ###############################################################################
    ## OPM General
    'opm': ('OPM', 'opm'),
    'original pilipino music': ('OPM', 'original pilipino music'),
    'filipino music': ('OPM', 'filipino music'),
    'música filipina': ('OPM', 'música filipina'),
    'pinoy music': ('OPM', 'pinoy music'),

    ## Pinoy pop
    'pinoy pop': ('OPM', 'pinoy pop'),
    'p-pop': ('OPM', 'p-pop'),
    'ppop': ('OPM', 'ppop'),
    'filipino pop': ('OPM', 'filipino pop'),
    'pop filipino': ('OPM', 'pop filipino'),

    ### Subgéneros de Pinoy pop
    'pinoy pop idol': ('OPM', 'pinoy pop idol'),
    'pinoy boy band': ('OPM', 'pinoy boy band'),
    'pinoy girl group': ('OPM', 'pinoy girl group'),
    'ppop idol': ('OPM', 'ppop idol'),
    'ppop group': ('OPM', 'ppop group'),

    ## Pinoy rock
    'pinoy rock': ('OPM', 'pinoy rock'),
    'filipino rock': ('OPM', 'filipino rock'),
    'rock filipino': ('OPM', 'rock filipino'),

    ### Subgéneros de Pinoy rock
    'pinoy alternative rock': ('OPM', 'pinoy alternative rock'),
    'pinoy indie rock': ('OPM', 'pinoy indie rock'),
    'pinoy punk': ('OPM', 'pinoy punk'),
    'pinoy metal': ('OPM', 'pinoy metal'),
    'pinoy progressive rock': ('OPM', 'pinoy progressive rock'),
    'pinoy classic rock': ('OPM', 'pinoy classic rock'),

    ## Pinoy R&B
    'pinoy r&b': ('OPM', 'pinoy r&b'),
    'pinoy rnb': ('OPM', 'pinoy rnb'),
    'filipino r&b': ('OPM', 'filipino r&b'),
    'r&b filipino': ('OPM', 'r&b filipino'),

    ## Pinoy hip hop
    'pinoy hip hop': ('OPM', 'pinoy hip hop'),
    'pinoy rap': ('OPM', 'pinoy rap'),
    'filipino hip hop': ('OPM', 'filipino hip hop'),
    'filipino rap': ('OPM', 'filipino rap'),
    'rap filipino': ('OPM', 'rap filipino'),

    ### Subgéneros de Pinoy hip hop
    'pinoy underground rap': ('OPM', 'pinoy underground rap'),
    'pinoy conscious rap': ('OPM', 'pinoy conscious rap'),
    'pinoy trap': ('OPM', 'pinoy trap'),
    'pinoy old school hip hop': ('OPM', 'pinoy old school hip hop'),

    ## Kundiman (balada tradicional)
    'kundiman': ('OPM', 'kundiman'),
    'filipino kundiman': ('OPM', 'filipino kundiman'),
    'traditional kundiman': ('OPM', 'traditional kundiman'),
    'balada filipina': ('OPM', 'balada filipina'),
    'filipino love song': ('OPM', 'filipino love song'),
    'harana': ('OPM', 'harana'),

    ## Manila sound
    'manila sound': ('OPM', 'manila sound'),
    'manila sound music': ('OPM', 'manila sound music'),
    'opm manila sound': ('OPM', 'opm manila sound'),
    'filipino city pop': ('OPM', 'filipino city pop'),
    'manila pop': ('OPM', 'manila pop'),
    '70s manila sound': ('OPM', '70s manila sound'),

    ## Pinoy folk
    'pinoy folk': ('OPM', 'pinoy folk'),
    'filipino folk': ('OPM', 'filipino folk'),
    'folk filipino': ('OPM', 'folk filipino'),
    'pinoy folk rock': ('OPM', 'pinoy folk rock'),
    'filipino folk music': ('OPM', 'filipino folk music'),

    ## Pinoy reggae
    'pinoy reggae': ('OPM', 'pinoy reggae'),
    'filipino reggae': ('OPM', 'filipino reggae'),
    'reggae filipino': ('OPM', 'reggae filipino'),
    'pinoy roots reggae': ('OPM', 'pinoy roots reggae'),
    'pinoy dub': ('OPM', 'pinoy dub'),

    ## Visayan pop (Bisaya)
    'visayan pop': ('OPM', 'visayan pop'),
    'bisaya pop': ('OPM', 'bisaya pop'),
    'cebuano pop': ('OPM', 'cebuano pop'),
    'vispop': ('OPM', 'vispop'),
    'bisrock': ('OPM', 'bisrock'),
    'visayan music': ('OPM', 'visayan music'),
    'cebuano music': ('OPM', 'cebuano music'),

    ## Pinoy jazz
    'pinoy jazz': ('OPM', 'pinoy jazz'),
    'filipino jazz': ('OPM', 'filipino jazz'),
    'jazz filipino': ('OPM', 'jazz filipino'),

    ## Pinoy blues
    'pinoy blues': ('OPM', 'pinoy blues'),
    'filipino blues': ('OPM', 'filipino blues'),

    ## Pinoy bossa nova
    'pinoy bossa nova': ('OPM', 'pinoy bossa nova'),
    'filipino bossa': ('OPM', 'filipino bossa'),

    ## Pinoy electronic
    'pinoy electronic': ('OPM', 'pinoy electronic'),
    'pinoy edm': ('OPM', 'pinoy edm'),
    'filipino electronic': ('OPM', 'filipino electronic'),

    ## Pinoy ballad
    'pinoy ballad': ('OPM', 'pinoy ballad'),
    'filipino ballad': ('OPM', 'filipino ballad'),
    'opm ballad': ('OPM', 'opm ballad'),
    'balada pinoy': ('OPM', 'balada pinoy'),

    ## Pinoy acoustic
    'pinoy acoustic': ('OPM', 'pinoy acoustic'),
    'acoustic opm': ('OPM', 'acoustic opm'),
    'filipino acoustic': ('OPM', 'filipino acoustic'),

    ## OPM por épocas
    'opm 70s': ('OPM', 'opm 70s'),
    'opm 80s': ('OPM', 'opm 80s'),
    'opm 90s': ('OPM', 'opm 90s'),
    'opm 2000s': ('OPM', 'opm 2000s'),
    'opm 2010s': ('OPM', 'opm 2010s'),
    'opm 2020s': ('OPM', 'opm 2020s'),
    'classic opm': ('OPM', 'classic opm'),
    'opm golden era': ('OPM', 'opm golden era'),
    'modern opm': ('OPM', 'modern opm'),

    ## OPM por región
    'tagalog pop': ('OPM', 'tagalog pop'),
    'manila pop': ('OPM', 'manila pop'),
    'cebu pop': ('OPM', 'cebu pop'),
    'davao pop': ('OPM', 'davao pop'),
    'ilocano pop': ('OPM', 'ilocano pop'),
    'kapampangan pop': ('OPM', 'kapampangan pop'),
    'bicolano pop': ('OPM', 'bicolano pop'),
    'hiligaynon pop': ('OPM', 'hiligaynon pop'),
    'waray pop': ('OPM', 'waray pop'),

    ## OPM fusion
    'opm fusion': ('OPM', 'opm fusion'),
    'pinoy fusion': ('OPM', 'pinoy fusion'),
    'filipino world music': ('OPM', 'filipino world music'),
    'pinoy ethnic fusion': ('OPM', 'pinoy ethnic fusion'),

    ## OPM instrumental
    'opm instrumental': ('OPM', 'opm instrumental'),
    'pinoy instrumental': ('OPM', 'pinoy instrumental'),
    'filipino instrumental': ('OPM', 'filipino instrumental'),

    ## OPM OST
    'opm ost': ('OPM', 'opm ost'),
    'filipino drama ost': ('OPM', 'filipino drama ost'),
    'pinoy movie soundtrack': ('OPM', 'pinoy movie soundtrack'),
    'filipino teleserye ost': ('OPM', 'filipino teleserye ost'),

    ## OPM Christmas
    'opm christmas': ('OPM', 'opm christmas'),
    'pinoy christmas songs': ('OPM', 'pinoy christmas songs'),
    'filipino pasko': ('OPM', 'filipino pasko'),
    'christmas opm': ('OPM', 'christmas opm'),

    ## Original Pinoy Music (clásico)
    'original pinoy music classic': ('OPM', 'original pinoy music classic'),
    'opm classic': ('OPM', 'opm classic'),
    'pinoy classic': ('OPM', 'pinoy classic'),

    ## Himig (canciones filipinas)
    'himig': ('OPM', 'himig'),
    'himig opm': ('OPM', 'himig opm'),
    'filipino melody': ('OPM', 'filipino melody'),

    ###############################################################################
    # Indonesian Pop / Dangdut (Regional - Indonesia)
    ###############################################################################
    ## Indonesian Pop General
    'indonesian pop': ('Indonesian Pop/Dangdut', 'indonesian pop'),
    'indo-pop': ('Indonesian Pop/Dangdut', 'indo-pop'),
    'indopop': ('Indonesian Pop/Dangdut', 'indopop'),
    'pop indonesia': ('Indonesian Pop/Dangdut', 'pop indonesia'),
    'musik indonesia': ('Indonesian Pop/Dangdut', 'musik indonesia'),

    ## Indo-Pop moderno
    'indo pop moderno': ('Indonesian Pop/Dangdut', 'indo pop moderno'),
    'modern indonesian pop': ('Indonesian Pop/Dangdut', 'modern indonesian pop'),
    'contemporary indo pop': ('Indonesian Pop/Dangdut', 'contemporary indo pop'),
    'indonesian mainstream pop': ('Indonesian Pop/Dangdut', 'indonesian mainstream pop'),

    ## Indonesian rock
    'indonesian rock': ('Indonesian Pop/Dangdut', 'indonesian rock'),
    'indo-rock': ('Indonesian Pop/Dangdut', 'indo-rock'),
    'rock indonesia': ('Indonesian Pop/Dangdut', 'rock indonesia'),

    ### Subgéneros de Indonesian rock
    'indonesian alternative rock': ('Indonesian Pop/Dangdut', 'indonesian alternative rock'),
    'indonesian indie rock': ('Indonesian Pop/Dangdut', 'indonesian indie rock'),
    'indonesian punk': ('Indonesian Pop/Dangdut', 'indonesian punk'),
    'indonesian metal': ('Indonesian Pop/Dangdut', 'indonesian metal'),
    'jakarta rock': ('Indonesian Pop/Dangdut', 'jakarta rock'),

    ## Indonesian R&B
    'indonesian r&b': ('Indonesian Pop/Dangdut', 'indonesian r&b'),
    'indo r&b': ('Indonesian Pop/Dangdut', 'indo r&b'),
    'r&b indonesia': ('Indonesian Pop/Dangdut', 'r&b indonesia'),

    ## Indonesian hip hop
    'indonesian hip hop': ('Indonesian Pop/Dangdut', 'indonesian hip hop'),
    'indo rap': ('Indonesian Pop/Dangdut', 'indo rap'),
    'indonesian rap': ('Indonesian Pop/Dangdut', 'indonesian rap'),

    ## Indonesian folk / Tradicional
    'indonesian folk': ('Indonesian Pop/Dangdut', 'indonesian folk'),
    'folk indonesia': ('Indonesian Pop/Dangdut', 'folk indonesia'),
    'musik tradisional': ('Indonesian Pop/Dangdut', 'musik tradisional'),
    'gamelan pop': ('Indonesian Pop/Dangdut', 'gamelan pop'),

    ## Indonesian electronic
    'indonesian electronic': ('Indonesian Pop/Dangdut', 'indonesian electronic'),
    'indo edm': ('Indonesian Pop/Dangdut', 'indo edm'),

    ###############################################################################
    ### Dangdut (Subcategoría dentro de Indonesian Pop/Dangdut)
    ###############################################################################
    ## Dangdut General
    'dangdut': ('Indonesian Pop/Dangdut', 'dangdut'),
    'dangdut music': ('Indonesian Pop/Dangdut', 'dangdut music'),
    'musik dangdut': ('Indonesian Pop/Dangdut', 'musik dangdut'),

    ## Dangdut clásico
    'dangdut clásico': ('Indonesian Pop/Dangdut', 'dangdut clásico'),
    'classic dangdut': ('Indonesian Pop/Dangdut', 'classic dangdut'),
    'dangdut klasik': ('Indonesian Pop/Dangdut', 'dangdut klasik'),
    'dangdut tradicional': ('Indonesian Pop/Dangdut', 'dangdut tradicional'),
    'traditional dangdut': ('Indonesian Pop/Dangdut', 'traditional dangdut'),
    'dangdut 80s': ('Indonesian Pop/Dangdut', 'dangdut 80s'),
    'dangdut 90s': ('Indonesian Pop/Dangdut', 'dangdut 90s'),

    ## Dangdut koplo
    'dangdut koplo': ('Indonesian Pop/Dangdut', 'dangdut koplo'),
    'koplo': ('Indonesian Pop/Dangdut', 'koplo'),
    'dangdut koplo modern': ('Indonesian Pop/Dangdut', 'dangdut koplo modern'),
    'koplo dangdut': ('Indonesian Pop/Dangdut', 'koplo dangdut'),
    'dangdut jawa timur': ('Indonesian Pop/Dangdut', 'dangdut jawa timur'),

    ## Dangdut moderno
    'dangdut moderno': ('Indonesian Pop/Dangdut', 'dangdut moderno'),
    'modern dangdut': ('Indonesian Pop/Dangdut', 'modern dangdut'),
    'contemporary dangdut': ('Indonesian Pop/Dangdut', 'contemporary dangdut'),
    'dangdut masa kini': ('Indonesian Pop/Dangdut', 'dangdut masa kini'),

    ## Dangdut house
    'dangdut house': ('Indonesian Pop/Dangdut', 'dangdut house'),
    'house dangdut': ('Indonesian Pop/Dangdut', 'house dangdut'),
    'dangdut house music': ('Indonesian Pop/Dangdut', 'dangdut house music'),

    ## Dangdut remix
    'dangdut remix': ('Indonesian Pop/Dangdut', 'dangdut remix'),
    'remix dangdut': ('Indonesian Pop/Dangdut', 'remix dangdut'),
    'dangdut remix dj': ('Indonesian Pop/Dangdut', 'dangdut remix dj'),

    ## Dangdut elektro
    'dangdut elektro': ('Indonesian Pop/Dangdut', 'dangdut elektro'),
    'dangdut electro': ('Indonesian Pop/Dangdut', 'dangdut electro'),
    'electro dangdut': ('Indonesian Pop/Dangdut', 'electro dangdut'),
    'dangdut electronic': ('Indonesian Pop/Dangdut', 'dangdut electronic'),

    ## Campursari (fusión con javanés)
    'campursari': ('Indonesian Pop/Dangdut', 'campursari'),
    'campur sari': ('Indonesian Pop/Dangdut', 'campur sari'),
    'dangdut campursari': ('Indonesian Pop/Dangdut', 'dangdut campursari'),
    'javanese fusion': ('Indonesian Pop/Dangdut', 'javanese fusion'),
    'musik jawa': ('Indonesian Pop/Dangdut', 'musik jawa'),

    ## Qasidah moderno
    'qasidah': ('Indonesian Pop/Dangdut', 'qasidah'),
    'qasidah modern': ('Indonesian Pop/Dangdut', 'qasidah modern'),
    'kasidah': ('Indonesian Pop/Dangdut', 'kasidah'),
    'dangdut qasidah': ('Indonesian Pop/Dangdut', 'dangdut qasidah'),
    'islamic dangdut': ('Indonesian Pop/Dangdut', 'islamic dangdut'),

    ## Dangdut por región
    'dangdut jakarta': ('Indonesian Pop/Dangdut', 'dangdut jakarta'),
    'jakarta dangdut': ('Indonesian Pop/Dangdut', 'jakarta dangdut'),
    'dangdut jawa': ('Indonesian Pop/Dangdut', 'dangdut jawa'),
    'javanese dangdut': ('Indonesian Pop/Dangdut', 'javanese dangdut'),
    'dangdut sumatra': ('Indonesian Pop/Dangdut', 'dangdut sumatra'),
    'dangdut sunda': ('Indonesian Pop/Dangdut', 'dangdut sunda'),
    'sundanese dangdut': ('Indonesian Pop/Dangdut', 'sundanese dangdut'),
    'dangdut bali': ('Indonesian Pop/Dangdut', 'dangdut bali'),

    ## Dangdut fusión
    'dangdut fusion': ('Indonesian Pop/Dangdut', 'dangdut fusion'),
    'dangdut pop': ('Indonesian Pop/Dangdut', 'dangdut pop'),
    'pop dangdut': ('Indonesian Pop/Dangdut', 'pop dangdut'),
    'dangdut rock': ('Indonesian Pop/Dangdut', 'dangdut rock'),
    'rock dangdut': ('Indonesian Pop/Dangdut', 'rock dangdut'),
    'dangdut reggae': ('Indonesian Pop/Dangdut', 'dangdut reggae'),

    ## Dangdut dangdutan (estilo bailable)
    'dangdutan': ('Indonesian Pop/Dangdut', 'dangdutan'),
    'dangdut dance': ('Indonesian Pop/Dangdut', 'dangdut dance'),
    'dangdut party': ('Indonesian Pop/Dangdut', 'dangdut party'),

    ## Dangdut koplo modern
    'koplo modern': ('Indonesian Pop/Dangdut', 'koplo modern'),
    'modern koplo': ('Indonesian Pop/Dangdut', 'modern koplo'),
    'koplo remix': ('Indonesian Pop/Dangdut', 'koplo remix'),

    ###############################################################################
    ## Indo-Pop por épocas
    'indopop 80s': ('Indonesian Pop/Dangdut', 'indopop 80s'),
    'indopop 90s': ('Indonesian Pop/Dangdut', 'indopop 90s'),
    'indopop 2000s': ('Indonesian Pop/Dangdut', 'indopop 2000s'),
    'indopop 2010s': ('Indonesian Pop/Dangdut', 'indopop 2010s'),
    'indopop 2020s': ('Indonesian Pop/Dangdut', 'indopop 2020s'),
    'classic indopop': ('Indonesian Pop/Dangdut', 'classic indopop'),
    'modern indopop': ('Indonesian Pop/Dangdut', 'modern indopop'),

    ## Indo-Pop por región
    'jakarta pop': ('Indonesian Pop/Dangdut', 'jakarta pop'),
    'bandung pop': ('Indonesian Pop/Dangdut', 'bandung pop'),
    'surabaya pop': ('Indonesian Pop/Dangdut', 'surabaya pop'),
    'bali pop': ('Indonesian Pop/Dangdut', 'bali pop'),
    'yogyakarta pop': ('Indonesian Pop/Dangdut', 'yogyakarta pop'),

    ## Indonesian OST
    'indonesian ost': ('Indonesian Pop/Dangdut', 'indonesian ost'),
    'sinetron ost': ('Indonesian Pop/Dangdut', 'sinetron ost'),
    'indonesian drama ost': ('Indonesian Pop/Dangdut', 'indonesian drama ost'),
    'indonesian movie soundtrack': ('Indonesian Pop/Dangdut', 'indonesian movie soundtrack'),

    ## Indonesian indie
    'indonesian indie': ('Indonesian Pop/Dangdut', 'indonesian indie'),
    'indo indie': ('Indonesian Pop/Dangdut', 'indo indie'),
    'indie indonesia': ('Indonesian Pop/Dangdut', 'indie indonesia'),

    ## Indonesian acoustic
    'indonesian acoustic': ('Indonesian Pop/Dangdut', 'indonesian acoustic'),
    'akustik indonesia': ('Indonesian Pop/Dangdut', 'akustik indonesia'),

    ###############################################################################
    # Malaysian Pop (M-Pop) (Regional - Malasia)
    ###############################################################################
    ## M-Pop General
    'mpop': ('Malaysian Pop', 'mpop'),
    'm-pop': ('Malaysian Pop', 'm-pop'),
    'malaysian pop': ('Malaysian Pop', 'malaysian pop'),
    'pop malasio': ('Malaysian Pop', 'pop malasio'),
    'musik malaysia': ('Malaysian Pop', 'musik malaysia'),

    ## Malay pop (Bahasa Malaysia)
    'malay pop': ('Malaysian Pop', 'malay pop'),
    'pop melayu': ('Malaysian Pop', 'pop melayu'),
    'malay mainstream pop': ('Malaysian Pop', 'malay mainstream pop'),

    ## Malaysian rock
    'malaysian rock': ('Malaysian Pop', 'malaysian rock'),
    'm-rock': ('Malaysian Pop', 'm-rock'),
    'rock malasio': ('Malaysian Pop', 'rock malasio'),

    ### Subgéneros de Malaysian rock
    'malaysian alternative rock': ('Malaysian Pop', 'malaysian alternative rock'),
    'malaysian indie rock': ('Malaysian Pop', 'malaysian indie rock'),
    'malaysian punk': ('Malaysian Pop', 'malaysian punk'),
    'malaysian metal': ('Malaysian Pop', 'malaysian metal'),
    'kuala lumpur rock': ('Malaysian Pop', 'kuala lumpur rock'),

    ## Malaysian R&B
    'malaysian r&b': ('Malaysian Pop', 'malaysian r&b'),
    'm-rnb': ('Malaysian Pop', 'm-rnb'),
    'r&b malasio': ('Malaysian Pop', 'r&b malasio'),

    ## Malaysian hip hop
    'malaysian hip hop': ('Malaysian Pop', 'malaysian hip hop'),
    'm-rap': ('Malaysian Pop', 'm-rap'),
    'malaysian rap': ('Malaysian Pop', 'malaysian rap'),

    ## Malaysian folk / Tradicional
    'malaysian folk': ('Malaysian Pop', 'malaysian folk'),
    'folk malasio': ('Malaysian Pop', 'folk malasio'),
    'musik tradisional malaysia': ('Malaysian Pop', 'musik tradisional malaysia'),

    ## Malaysian electronic
    'malaysian electronic': ('Malaysian Pop', 'malaysian electronic'),
    'm-edm': ('Malaysian Pop', 'm-edm'),

    ## Malaysian ballad
    'malaysian ballad': ('Malaysian Pop', 'malaysian ballad'),
    'balada malasia': ('Malaysian Pop', 'balada malasia'),

    ## Malaysian idol / Grupos
    'malaysian idol': ('Malaysian Pop', 'malaysian idol'),
    'm-idol': ('Malaysian Pop', 'm-idol'),
    'malaysian boy band': ('Malaysian Pop', 'malaysian boy band'),
    'malaysian girl group': ('Malaysian Pop', 'malaysian girl group'),

    ## Malaysian Chinese pop
    'malaysian chinese pop': ('Malaysian Pop', 'malaysian chinese pop'),
    'malaysian mandopop': ('Malaysian Pop', 'malaysian mandopop'),

    ## Malaysian Indian pop
    'malaysian indian pop': ('Malaysian Pop', 'malaysian indian pop'),
    'malaysian tamil pop': ('Malaysian Pop', 'malaysian tamil pop'),

    ## Irama Malaysia (música tradicional malaya)
    'irama malaysia': ('Malaysian Pop', 'irama malaysia'),
    'malay traditional pop': ('Malaysian Pop', 'malay traditional pop'),

    ## Malaysian fusion
    'malaysian fusion': ('Malaysian Pop', 'malaysian fusion'),
    'm-pop fusion': ('Malaysian Pop', 'm-pop fusion'),

    ## Malaysian OST
    'malaysian ost': ('Malaysian Pop', 'malaysian ost'),
    'malaysian drama ost': ('Malaysian Pop', 'malaysian drama ost'),

    ## Malaysian indie
    'malaysian indie': ('Malaysian Pop', 'malaysian indie'),
    'm-indie': ('Malaysian Pop', 'm-indie'),

    ## Malaysian pop por épocas
    'mpop 80s': ('Malaysian Pop', 'mpop 80s'),
    'mpop 90s': ('Malaysian Pop', 'mpop 90s'),
    'mpop 2000s': ('Malaysian Pop', 'mpop 2000s'),
    'mpop 2010s': ('Malaysian Pop', 'mpop 2010s'),
    'mpop 2020s': ('Malaysian Pop', 'mpop 2020s'),
    'classic mpop': ('Malaysian Pop', 'classic mpop'),

    ## Malaysian pop por región
    'kuala lumpur pop': ('Malaysian Pop', 'kuala lumpur pop'),
    'penang pop': ('Malaysian Pop', 'penang pop'),
    'johor pop': ('Malaysian Pop', 'johor pop'),
    'sarawak pop': ('Malaysian Pop', 'sarawak pop'),
    'sabah pop': ('Malaysian Pop', 'sabah pop'),

    ###############################################################################
    # Singaporean Pop (Regional - Singapur)
    ###############################################################################
    ## Singaporean Pop General
    'singaporean pop': ('Singaporean Pop', 'singaporean pop'),
    'sg pop': ('Singaporean Pop', 'sg pop'),
    'singapore pop': ('Singaporean Pop', 'singapore pop'),
    'pop singapurense': ('Singaporean Pop', 'pop singapurense'),
    'musik singapura': ('Singaporean Pop', 'musik singapura'),

    ## Xinyao (Singapur)
    'xinyao': ('Singaporean Pop', 'xinyao'),
    'singapore xinyao': ('Singaporean Pop', 'singapore xinyao'),
    'xin yao': ('Singaporean Pop', 'xin yao'),
    'singapore folk pop': ('Singaporean Pop', 'singapore folk pop'),
    'singapore chinese folk': ('Singaporean Pop', 'singapore chinese folk'),

    ## Singaporean rock
    'singaporean rock': ('Singaporean Pop', 'singaporean rock'),
    'sg rock': ('Singaporean Pop', 'sg rock'),
    'rock singapurense': ('Singaporean Pop', 'rock singapurense'),

    ### Subgéneros de Singaporean rock
    'singapore alternative rock': ('Singaporean Pop', 'singapore alternative rock'),
    'singapore indie rock': ('Singaporean Pop', 'singapore indie rock'),
    'singapore punk': ('Singaporean Pop', 'singapore punk'),
    'singapore metal': ('Singaporean Pop', 'singapore metal'),

    ## Singaporean R&B
    'singaporean r&b': ('Singaporean Pop', 'singaporean r&b'),
    'sg rnb': ('Singaporean Pop', 'sg rnb'),

    ## Singaporean hip hop
    'singaporean hip hop': ('Singaporean Pop', 'singaporean hip hop'),
    'sg rap': ('Singaporean Pop', 'sg rap'),
    'singapore rap': ('Singaporean Pop', 'singapore rap'),

    ## Singaporean English pop
    'singapore english pop': ('Singaporean Pop', 'singapore english pop'),
    'sg english pop': ('Singaporean Pop', 'sg english pop'),

    ## Singaporean Chinese pop
    'singapore chinese pop': ('Singaporean Pop', 'singapore chinese pop'),
    'singapore mandopop': ('Singaporean Pop', 'singapore mandopop'),

    ## Singaporean Malay pop
    'singapore malay pop': ('Singaporean Pop', 'singapore malay pop'),
    'sg malay pop': ('Singaporean Pop', 'sg malay pop'),

    ## Singaporean Tamil pop
    'singapore tamil pop': ('Singaporean Pop', 'singapore tamil pop'),
    'sg tamil pop': ('Singaporean Pop', 'sg tamil pop'),

    ## Singaporean electronic
    'singaporean electronic': ('Singaporean Pop', 'singaporean electronic'),
    'sg edm': ('Singaporean Pop', 'sg edm'),

    ## Singaporean ballad
    'singaporean ballad': ('Singaporean Pop', 'singaporean ballad'),
    'balada singapurense': ('Singaporean Pop', 'balada singapurense'),

    ## Singaporean idol
    'singaporean idol': ('Singaporean Pop', 'singaporean idol'),
    'sg idol': ('Singaporean Pop', 'sg idol'),

    ## Singaporean OST
    'singaporean ost': ('Singaporean Pop', 'singaporean ost'),
    'singapore drama ost': ('Singaporean Pop', 'singapore drama ost'),
    'sg drama soundtrack': ('Singaporean Pop', 'sg drama soundtrack'),

    ## Singaporean indie
    'singaporean indie': ('Singaporean Pop', 'singaporean indie'),
    'sg indie': ('Singaporean Pop', 'sg indie'),

    ## Singaporean pop por épocas
    'sg pop 80s': ('Singaporean Pop', 'sg pop 80s'),
    'sg pop 90s': ('Singaporean Pop', 'sg pop 90s'),
    'sg pop 2000s': ('Singaporean Pop', 'sg pop 2000s'),
    'sg pop 2010s': ('Singaporean Pop', 'sg pop 2010s'),
    'sg pop 2020s': ('Singaporean Pop', 'sg pop 2020s'),
    'classic sg pop': ('Singaporean Pop', 'classic sg pop'),

    ## Singaporean fusion
    'singaporean fusion': ('Singaporean Pop', 'singaporean fusion'),
    'sg fusion': ('Singaporean Pop', 'sg fusion'),

    ## Singaporean acoustic
    'singaporean acoustic': ('Singaporean Pop', 'singaporean acoustic'),
    'sg acoustic': ('Singaporean Pop', 'sg acoustic'),

    ###############################################################################
    # Bruneian Pop/Rock (Regional - Brunéi)
    ###############################################################################
    ## Bruneian Pop General (English / Malay)
    'bruneian pop': ('Bruneian Pop/Rock', 'bruneian pop'),
    'brunei pop': ('Bruneian Pop/Rock', 'brunei pop'),
    'pop bruneano': ('Bruneian Pop/Rock', 'pop bruneano'),
    'bandar seri begawan pop': ('Bruneian Pop/Rock', 'bandar seri begawan pop'),
    'musik brunei': ('Bruneian Pop/Rock', 'musik brunei'),

    ## Bruneian rock
    'bruneian rock': ('Bruneian Pop/Rock', 'bruneian rock'),
    'brunei rock': ('Bruneian Pop/Rock', 'brunei rock'),
    'rock bruneano': ('Bruneian Pop/Rock', 'rock bruneano'),

    ### Subgéneros de Bruneian rock
    'bruneian alternative rock': ('Bruneian Pop/Rock', 'bruneian alternative rock'),
    'bruneian indie rock': ('Bruneian Pop/Rock', 'bruneian indie rock'),
    'bruneian metal': ('Bruneian Pop/Rock', 'bruneian metal'),
    'bruneian punk': ('Bruneian Pop/Rock', 'bruneian punk'),

    ## Bruneian hip hop / Rap
    'bruneian hip hop': ('Bruneian Pop/Rock', 'bruneian hip hop'),
    'bruneian rap': ('Bruneian Pop/Rock', 'bruneian rap'),
    'brunei rap': ('Bruneian Pop/Rock', 'brunei rap'),

    ## Bruneian R&B
    'bruneian r&b': ('Bruneian Pop/Rock', 'bruneian r&b'),
    'bruneian rnb': ('Bruneian Pop/Rock', 'bruneian rnb'),

    ## Bruneian folk / Tradicional
    'bruneian folk': ('Bruneian Pop/Rock', 'bruneian folk'),
    'brunei traditional': ('Bruneian Pop/Rock', 'brunei traditional'),
    'jipin': ('Bruneian Pop/Rock', 'jipin'),
    'adai-adai': ('Bruneian Pop/Rock', 'adai-adai'),

    ## Bruneian fusion
    'bruneian fusion': ('Bruneian Pop/Rock', 'bruneian fusion'),
    'brunei fusion': ('Bruneian Pop/Rock', 'brunei fusion'),

    ## Bruneian pop por región
    'bandar seri begawan pop': ('Bruneian Pop/Rock', 'bandar seri begawan pop'),
    'kuala belait pop': ('Bruneian Pop/Rock', 'kuala belait pop'),
    'tutong pop': ('Bruneian Pop/Rock', 'tutong pop'),

    ###############################################################################
    # Indian Pop / Desi (Regional - India) [Expandida]
    ###############################################################################
    ## Indian Pop General
    'indian pop': ('Indian Pop', 'indian pop'),
    'desi pop': ('Indian Pop', 'desi pop'),
    'indipop': ('Indian Pop', 'indipop'),
    'pop indio': ('Indian Pop', 'pop indio'),
    'música india': ('Indian Pop', 'música india'),

    ## Bollywood / Filmi
    'bollywood': ('Indian Pop', 'bollywood'),
    'filmi': ('Indian Pop', 'filmi'),
    'bollywood music': ('Indian Pop', 'bollywood music'),
    'filmi music': ('Indian Pop', 'filmi music'),
    'bollywood pop': ('Indian Pop', 'bollywood pop'),
    'bollywood soundtrack': ('Indian Pop', 'bollywood soundtrack'),
    'bollywood songs': ('Indian Pop', 'bollywood songs'),

    ## Punjabi pop / Bhangra
    'punjabi pop': ('Indian Pop', 'punjabi pop'),
    'bhangra': ('Indian Pop', 'bhangra'),
    'punjabi bhangra': ('Indian Pop', 'punjabi bhangra'),
    'bhangra pop': ('Indian Pop', 'bhangra pop'),
    'punjabi music': ('Indian Pop', 'punjabi music'),

    ## Indipop (Indian pop)
    'indipop': ('Indian Pop', 'indipop'),
    'indi pop': ('Indian Pop', 'indi pop'),
    'indian mainstream pop': ('Indian Pop', 'indian mainstream pop'),

    ## Ghazal
    'ghazal': ('Indian Pop', 'ghazal'),
    'ghazals': ('Indian Pop', 'ghazals'),
    'urdu ghazal': ('Indian Pop', 'urdu ghazal'),
    'hindi ghazal': ('Indian Pop', 'hindi ghazal'),

    ## Qawwali
    'qawwali': ('Indian Pop', 'qawwali'),
    'qawwali music': ('Indian Pop', 'qawwali music'),
    'sufi qawwali': ('Indian Pop', 'sufi qawwali'),

    ## Sufi rock / Sufi pop
    'sufi rock': ('Indian Pop', 'sufi rock'),
    'sufi pop': ('Indian Pop', 'sufi pop'),
    'sufi fusion': ('Indian Pop', 'sufi fusion'),

    ## Carnatic (clásico del sur)
    'carnatic': ('Indian Pop', 'carnatic'),
    'carnatic music': ('Indian Pop', 'carnatic music'),
    'carnatic classical': ('Indian Pop', 'carnatic classical'),
    'south indian classical': ('Indian Pop', 'south indian classical'),

    ## Hindustani (clásico del norte)
    'hindustani': ('Indian Pop', 'hindustani'),
    'hindustani classical': ('Indian Pop', 'hindustani classical'),
    'north indian classical': ('Indian Pop', 'north indian classical'),

    ## Bengali pop
    'bengali pop': ('Indian Pop', 'bengali pop'),
    'bangla pop': ('Indian Pop', 'bangla pop'),
    'bengali music': ('Indian Pop', 'bengali music'),
    'kolkata pop': ('Indian Pop', 'kolkata pop'),

    ## Tamil pop / Kollywood
    'tamil pop': ('Indian Pop', 'tamil pop'),
    'kollywood': ('Indian Pop', 'kollywood'),
    'tamil film music': ('Indian Pop', 'tamil film music'),
    'tamil cinema songs': ('Indian Pop', 'tamil cinema songs'),
    'chennai pop': ('Indian Pop', 'chennai pop'),

    ## Telugu pop / Tollywood
    'telugu pop': ('Indian Pop', 'telugu pop'),
    'tollywood': ('Indian Pop', 'tollywood'),
    'telugu film music': ('Indian Pop', 'telugu film music'),
    'hyderabad pop': ('Indian Pop', 'hyderabad pop'),

    ## Malayalam pop / Mollywood
    'malayalam pop': ('Indian Pop', 'malayalam pop'),
    'mollywood': ('Indian Pop', 'mollywood'),
    'malayalam film music': ('Indian Pop', 'malayalam film music'),
    'kerala pop': ('Indian Pop', 'kerala pop'),

    ## Bhojpuri pop
    'bhojpuri pop': ('Indian Pop', 'bhojpuri pop'),
    'bhojpuri music': ('Indian Pop', 'bhojpuri music'),
    'bhojpuri film songs': ('Indian Pop', 'bhojpuri film songs'),

    ## Rajasthani folk
    'rajasthani folk': ('Indian Pop', 'rajasthani folk'),
    'rajasthani music': ('Indian Pop', 'rajasthani music'),

    ## Gujarati pop
    'gujarati pop': ('Indian Pop', 'gujarati pop'),
    'gujarati music': ('Indian Pop', 'gujarati music'),
    'garba': ('Indian Pop', 'garba'),
    'dandiya': ('Indian Pop', 'dandiya'),

    ## Marathi pop
    'marathi pop': ('Indian Pop', 'marathi pop'),
    'marathi music': ('Indian Pop', 'marathi music'),

    ## Kannada pop / Sandalwood
    'kannada pop': ('Indian Pop', 'kannada pop'),
    'sandalwood': ('Indian Pop', 'sandalwood'),
    'kannada film music': ('Indian Pop', 'kannada film music'),

    ## Odia pop
    'odia pop': ('Indian Pop', 'odia pop'),
    'oriya music': ('Indian Pop', 'oriya music'),

    ## Assamese pop
    'assamese pop': ('Indian Pop', 'assamese pop'),

    ## Indian rock
    'indian rock': ('Indian Pop', 'indian rock'),
    'desi rock': ('Indian Pop', 'desi rock'),

    ## Indian hip hop
    'indian hip hop': ('Indian Pop', 'indian hip hop'),
    'desi hip hop': ('Indian Pop', 'desi hip hop'),
    'indian rap': ('Indian Pop', 'indian rap'),

    ## Indian R&B
    'indian r&b': ('Indian Pop', 'indian r&b'),

    ## Indian fusion
    'indian fusion': ('Indian Pop', 'indian fusion'),
    'desi fusion': ('Indian Pop', 'desi fusion'),
    'indo fusion': ('Indian Pop', 'indo fusion'),

    ## Indian pop por épocas
    'indipop 80s': ('Indian Pop', 'indipop 80s'),
    'indipop 90s': ('Indian Pop', 'indipop 90s'),
    'indipop 2000s': ('Indian Pop', 'indipop 2000s'),
    'indipop 2010s': ('Indian Pop', 'indipop 2010s'),
    'indipop 2020s': ('Indian Pop', 'indipop 2020s'),
    'classic bollywood': ('Indian Pop', 'classic bollywood'),
    'golden era bollywood': ('Indian Pop', 'golden era bollywood'),

    ###############################################################################
    # Pakistani Pop (Regional - Pakistán) [Mejorada]
    ###############################################################################
    ## Pakistani Pop General
    'pakistani pop': ('Pakistani Pop', 'pakistani pop'),
    'pak pop': ('Pakistani Pop', 'pak pop'),
    'pop pakistaní': ('Pakistani Pop', 'pop pakistaní'),
    'música pakistaní': ('Pakistani Pop', 'música pakistaní'),

    ## Lollywood (Pakistani film industry)
    'lollywood': ('Pakistani Pop', 'lollywood'),
    'lollywood music': ('Pakistani Pop', 'lollywood music'),
    'pakistani film music': ('Pakistani Pop', 'pakistani film music'),
    'lahore pop': ('Pakistani Pop', 'lahore pop'),

    ## Pakistani pop / Desi pop pakistaní
    'pakistani pop music': ('Pakistani Pop', 'pakistani pop music'),
    'pakistani mainstream': ('Pakistani Pop', 'pakistani mainstream'),

    ## Ghazal (Pakistani)
    'pakistani ghazal': ('Pakistani Pop', 'pakistani ghazal'),
    'urdu ghazal pakistan': ('Pakistani Pop', 'urdu ghazal pakistan'),

    ## Qawwali (Pakistani)
    'pakistani qawwali': ('Pakistani Pop', 'pakistani qawwali'),
    'sufi qawwali pakistan': ('Pakistani Pop', 'sufi qawwali pakistan'),

    ## Sufi rock / Sufi pop (Pakistán)
    'pakistani sufi rock': ('Pakistani Pop', 'pakistani sufi rock'),
    'sufi rock pakistan': ('Pakistani Pop', 'sufi rock pakistan'),
    'sufi pop pakistan': ('Pakistani Pop', 'sufi pop pakistan'),

    ## Pakistani rock
    'pakistani rock': ('Pakistani Pop', 'pakistani rock'),
    'pak rock': ('Pakistani Pop', 'pak rock'),

    ### Subgéneros de Pakistani rock
    'pakistani alternative rock': ('Pakistani Pop', 'pakistani alternative rock'),
    'pakistani indie rock': ('Pakistani Pop', 'pakistani indie rock'),
    'pakistani metal': ('Pakistani Pop', 'pakistani metal'),
    'pakistani progressive rock': ('Pakistani Pop', 'pakistani progressive rock'),

    ## Pakistani hip hop
    'pakistani hip hop': ('Pakistani Pop', 'pakistani hip hop'),
    'pakistani rap': ('Pakistani Pop', 'pakistani rap'),
    'urdu hip hop': ('Pakistani Pop', 'urdu hip hop'),

    ## Pakistani R&B
    'pakistani r&b': ('Pakistani Pop', 'pakistani r&b'),

    ## Punjabi pop (Pakistán)
    'pakistani punjabi pop': ('Pakistani Pop', 'pakistani punjabi pop'),
    'punjabi pop pakistan': ('Pakistani Pop', 'punjabi pop pakistan'),

    ## Sindhi Pop (mejoras)
    'sindhi pop': ('Pakistani Pop', 'sindhi pop'),
    'sindhi music': ('Pakistani Pop', 'sindhi music'),
    'sindhi rock': ('Pakistani Pop', 'sindhi rock'),
    'sindhi fusion': ('Pakistani Pop', 'sindhi fusion'),
    'sindhi sufí pop': ('Pakistani Pop', 'sindhi sufí pop'),
    'sindhi rap': ('Pakistani Pop', 'sindhi rap'),

    ## Pashto Pop (mejoras)
    'pashto pop': ('Pakistani Pop', 'pashto pop'),
    'pashto music': ('Pakistani Pop', 'pashto music'),
    'pashto rock': ('Pakistani Pop', 'pashto rock'),
    'pashto fusion': ('Pakistani Pop', 'pashto fusion'),
    'pashto sufí pop': ('Pakistani Pop', 'pashto sufí pop'),
    'pashto rap': ('Pakistani Pop', 'pashto rap'),

    ## Pakistani folk
    'pakistani folk': ('Pakistani Pop', 'pakistani folk'),
    'folk pakistaní': ('Pakistani Pop', 'folk pakistaní'),

    ## Pakistani electronic
    'pakistani electronic': ('Pakistani Pop', 'pakistani electronic'),

    ## Pakistani fusion
    'pakistani fusion': ('Pakistani Pop', 'pakistani fusion'),

    ## Pakistani indie
    'pakistani indie': ('Pakistani Pop', 'pakistani indie'),

    ## Pakistani pop por épocas
    'pak pop 80s': ('Pakistani Pop', 'pak pop 80s'),
    'pak pop 90s': ('Pakistani Pop', 'pak pop 90s'),
    'pak pop 2000s': ('Pakistani Pop', 'pak pop 2000s'),
    'pak pop 2010s': ('Pakistani Pop', 'pak pop 2010s'),
    'pak pop 2020s': ('Pakistani Pop', 'pak pop 2020s'),
    'classic pakistani pop': ('Pakistani Pop', 'classic pakistani pop'),

    ## Pakistani pop por región
    'karachi pop': ('Pakistani Pop', 'karachi pop'),
    'lahore pop': ('Pakistani Pop', 'lahore pop'),
    'islamabad pop': ('Pakistani Pop', 'islamabad pop'),
    'quetta pop': ('Pakistani Pop', 'quetta pop'),
    'peshawar pop': ('Pakistani Pop', 'peshawar pop'),

    ###############################################################################
    # Bangladeshi Pop/Rock (Regional - Bangladesh) [Expandida]
    ###############################################################################
    ## Bangladeshi Pop General (English / Bengali)
    'bangladeshi pop': ('Bangladeshi Pop/Rock', 'bangladeshi pop'),
    'bd pop': ('Bangladeshi Pop/Rock', 'bd pop'),
    'bangla pop': ('Bangladeshi Pop/Rock', 'bangla pop'),
    'pop bangladesí': ('Bangladeshi Pop/Rock', 'pop bangladesí'),
    'bangladesh music': ('Bangladeshi Pop/Rock', 'bangladesh music'),
            'বাংলাদেশী পপ': ('Bangladeshi Pop/Rock', 'বাংলাদেশী পপ'),

    ## Bangladeshi pop moderno
    'modern bangladeshi pop': ('Bangladeshi Pop/Rock', 'modern bangladeshi pop'),
    'contemporary bangla pop': ('Bangladeshi Pop/Rock', 'contemporary bangla pop'),

    ## Dhallywood (cine bangladesí)
    'dhallywood': ('Bangladeshi Pop/Rock', 'dhallywood'),
    'dhallywood music': ('Bangladeshi Pop/Rock', 'dhallywood music'),
    'bangladeshi film music': ('Bangladeshi Pop/Rock', 'bangladeshi film music'),
    'dhaka pop': ('Bangladeshi Pop/Rock', 'dhaka pop'),

    ## Bangladeshi rock
    'bangladeshi rock': ('Bangladeshi Pop/Rock', 'bangladeshi rock'),
    'bd rock': ('Bangladeshi Pop/Rock', 'bd rock'),
    'rock bangladesí': ('Bangladeshi Pop/Rock', 'rock bangladesí'),
    'bangla rock': ('Bangladeshi Pop/Rock', 'bangla rock'),

    ### Subgéneros de Bangladeshi rock
    'bangladeshi alternative rock': ('Bangladeshi Pop/Rock', 'bangladeshi alternative rock'),
    'bangladeshi indie rock': ('Bangladeshi Pop/Rock', 'bangladeshi indie rock'),
    'bangladeshi metal': ('Bangladeshi Pop/Rock', 'bangladeshi metal'),
    'bangladeshi punk': ('Bangladeshi Pop/Rock', 'bangladeshi punk'),
    'chittagong rock': ('Bangladeshi Pop/Rock', 'chittagong rock'),

    ## Bangladeshi hip hop / Rap
    'bangladeshi hip hop': ('Bangladeshi Pop/Rock', 'bangladeshi hip hop'),
    'bd rap': ('Bangladeshi Pop/Rock', 'bd rap'),
    'bangladeshi rap': ('Bangladeshi Pop/Rock', 'bangladeshi rap'),
    'dhaka rap': ('Bangladeshi Pop/Rock', 'dhaka rap'),

    ## Bangladeshi R&B
    'bangladeshi r&b': ('Bangladeshi Pop/Rock', 'bangladeshi r&b'),
    'bangladeshi rnb': ('Bangladeshi Pop/Rock', 'bangladeshi rnb'),

    ## Música tradicional fusionada
    'bangladeshi folk': ('Bangladeshi Pop/Rock', 'bangladeshi folk'),
    'folk bangladesí': ('Bangladeshi Pop/Rock', 'folk bangladesí'),
    'baul': ('Bangladeshi Pop/Rock', 'baul'),
    'baul music': ('Bangladeshi Pop/Rock', 'baul music'),
    'bhatiali': ('Bangladeshi Pop/Rock', 'bhatiali'),
    'bhawaiya': ('Bangladeshi Pop/Rock', 'bhawaiya'),
    'jari gan': ('Bangladeshi Pop/Rock', 'jari gan'),
    'sari gan': ('Bangladeshi Pop/Rock', 'sari gan'),

    ## Rabindra Sangeet
    'rabindra sangeet': ('Bangladeshi Pop/Rock', 'rabindra sangeet'),
    'tagore songs': ('Bangladeshi Pop/Rock', 'tagore songs'),

    ## Nazrul geeti
    'nazrul geeti': ('Bangladeshi Pop/Rock', 'nazrul geeti'),
    'nazrul songs': ('Bangladeshi Pop/Rock', 'nazrul songs'),

    ## Bangladeshi fusion
    'bangladeshi fusion': ('Bangladeshi Pop/Rock', 'bangladeshi fusion'),
    'bd fusion': ('Bangladeshi Pop/Rock', 'bd fusion'),

    ## Bangladeshi indie
    'bangladeshi indie': ('Bangladeshi Pop/Rock', 'bangladeshi indie'),
    'bd indie': ('Bangladeshi Pop/Rock', 'bd indie'),

    ## Bangladeshi pop por región
    'dhaka pop': ('Bangladeshi Pop/Rock', 'dhaka pop'),
    'chittagong pop': ('Bangladeshi Pop/Rock', 'chittagong pop'),
    'khulna pop': ('Bangladeshi Pop/Rock', 'khulna pop'),
    'rajshahi pop': ('Bangladeshi Pop/Rock', 'rajshahi pop'),
    'sylhet pop': ('Bangladeshi Pop/Rock', 'sylhet pop'),

    ## Bangladeshi OST
    'bangladeshi ost': ('Bangladeshi Pop/Rock', 'bangladeshi ost'),
    'dhallywood songs': ('Bangladeshi Pop/Rock', 'dhallywood songs'),

    ## Bangladeshi pop por épocas
    'bd pop 80s': ('Bangladeshi Pop/Rock', 'bd pop 80s'),
    'bd pop 90s': ('Bangladeshi Pop/Rock', 'bd pop 90s'),
    'bd pop 2000s': ('Bangladeshi Pop/Rock', 'bd pop 2000s'),
    'bd pop 2010s': ('Bangladeshi Pop/Rock', 'bd pop 2010s'),
    'bd pop 2020s': ('Bangladeshi Pop/Rock', 'bd pop 2020s'),
    'classic bangladeshi pop': ('Bangladeshi Pop/Rock', 'classic bangladeshi pop'),

    ###############################################################################
    # C-Pop/C-Rock (Regional - China)
    ###############################################################################
    ## C-Pop General
    'cpop': ('C-Pop/C-Rock', 'cpop'),
    'c-pop': ('C-Pop/C-Rock', 'c-pop'),
    'c pop': ('C-Pop/C-Rock', 'c pop'),
    'chinese pop': ('C-Pop/C-Rock', 'chinese pop'),
    'pop chino continental': ('C-Pop/C-Rock', 'pop chino continental'),
    'música china continental': ('C-Pop/C-Rock', 'música china continental'),

    ## Mandopop (chino mandarín)
    'mandopop': ('C-Pop/C-Rock', 'mandopop'),
    'mando-pop': ('C-Pop/C-Rock', 'mando-pop'),
    'mandarin pop': ('C-Pop/C-Rock', 'mandarin pop'),
    'pop mandarín continental': ('C-Pop/C-Rock', 'pop mandarín continental'),

    ## Chinese rock
    'chinese rock': ('C-Pop/C-Rock', 'chinese rock'),
    'c-rock': ('C-Pop/C-Rock', 'c-rock'),
    'rock chino continental': ('C-Pop/C-Rock', 'rock chino continental'),
    'china rock': ('C-Pop/C-Rock', 'china rock'),
    'mandarin rock': ('C-Pop/C-Rock', 'mandarin rock'),
    'beijing rock': ('C-Pop/C-Rock', 'beijing rock'),

    ## Chinese folk
    'chinese folk': ('C-Pop/C-Rock', 'chinese folk'),
    'folk chino': ('C-Pop/C-Rock', 'folk chino'),
    'minyao': ('C-Pop/C-Rock', 'minyao'),

    ## Chinese R&B
    'chinese r&b': ('C-Pop/C-Rock', 'chinese r&b'),
    'c-rnb': ('C-Pop/C-Rock', 'c-rnb'),

    ## C-rap
    'c-rap': ('C-Pop/C-Rock', 'c-rap'),
    'chinese rap': ('C-Pop/C-Rock', 'chinese rap'),
    'chinese hip hop': ('C-Pop/C-Rock', 'chinese hip hop'),

    ## Chinese traditional pop
    'chinese traditional pop': ('C-Pop/C-Rock', 'chinese traditional pop'),
    'shidaiqu': ('C-Pop/C-Rock', 'shidaiqu'),

    ## Chinese indie
    'chinese indie': ('C-Pop/C-Rock', 'chinese indie'),
    'c-indie': ('C-Pop/C-Rock', 'c-indie'),

    ## Chinese OST
    'chinese ost': ('C-Pop/C-Rock', 'chinese ost'),
    'c-ost': ('C-Pop/C-Rock', 'c-ost'),
    'cdrama ost': ('C-Pop/C-Rock', 'cdrama ost'),

    ###############################################################################
    # TW-Pop/TW-Rock (Regional - Taiwán)
    ###############################################################################
    ## TW-Pop General
    'taiwanese pop': ('TW-Pop/TW-Rock', 'taiwanese pop'),
    't-pop': ('TW-Pop/TW-Rock', 't-pop'),
    'tpop': ('TW-Pop/TW-Rock', 'tpop'),
    'pop taiwanés': ('TW-Pop/TW-Rock', 'pop taiwanés'),
    'taiwan pop': ('TW-Pop/TW-Rock', 'taiwan pop'),

    ## Mandopop (Taiwán)
    'taiwanese mandopop': ('TW-Pop/TW-Rock', 'taiwanese mandopop'),
    'taiwan mandopop': ('TW-Pop/TW-Rock', 'taiwan mandopop'),
    'mandopop taiwanés': ('TW-Pop/TW-Rock', 'mandopop taiwanés'),
    'taiwan guoyu pop': ('TW-Pop/TW-Rock', 'taiwan guoyu pop'),

    ## Taiwanese rock
    'taiwanese rock': ('TW-Pop/TW-Rock', 'taiwanese rock'),
    't-rock': ('TW-Pop/TW-Rock', 't-rock'),
    'trock': ('TW-Pop/TW-Rock', 'trock'),
    'rock taiwanés': ('TW-Pop/TW-Rock', 'rock taiwanés'),

    ### Subgéneros de Taiwanese rock
    'taiwanese alternative rock': ('TW-Pop/TW-Rock', 'taiwanese alternative rock'),
    'taiwanese indie rock': ('TW-Pop/TW-Rock', 'taiwanese indie rock'),
    'taiwanese punk': ('TW-Pop/TW-Rock', 'taiwanese punk'),
    'taiwanese metal': ('TW-Pop/TW-Rock', 'taiwanese metal'),
    'taipei rock': ('TW-Pop/TW-Rock', 'taipei rock'),

    ## Taiwanese hip hop / Rap
    'taiwanese hip hop': ('TW-Pop/TW-Rock', 'taiwanese hip hop'),
    'taiwanese rap': ('TW-Pop/TW-Rock', 'taiwanese rap'),
    't-rap': ('TW-Pop/TW-Rock', 't-rap'),
    'taipei rap': ('TW-Pop/TW-Rock', 'taipei rap'),

    ## Taiwanese R&B
    'taiwanese r&b': ('TW-Pop/TW-Rock', 'taiwanese r&b'),
    't-rnb': ('TW-Pop/TW-Rock', 't-rnb'),

    ## Taiwanese folk / Hoklo
    'taiwanese folk': ('TW-Pop/TW-Rock', 'taiwanese folk'),
    'taiwanese folk music': ('TW-Pop/TW-Rock', 'taiwanese folk music'),
    'taiwan hoklo pop': ('TW-Pop/TW-Rock', 'taiwan hoklo pop'),
    'taiwanese minnan': ('TW-Pop/TW-Rock', 'taiwanese minnan'),
    'taiyu pop': ('TW-Pop/TW-Rock', 'taiyu pop'),

    ## Taiwanese indie
    'taiwanese indie': ('TW-Pop/TW-Rock', 'taiwanese indie'),
    't-indie': ('TW-Pop/TW-Rock', 't-indie'),
    'indie taiwanés': ('TW-Pop/TW-Rock', 'indie taiwanés'),

    ## Taiwanese OST
    'taiwanese ost': ('TW-Pop/TW-Rock', 'taiwanese ost'),
    't-ost': ('TW-Pop/TW-Rock', 't-ost'),
    'taiwanese drama ost': ('TW-Pop/TW-Rock', 'taiwanese drama ost'),
    'taiwanese movie soundtrack': ('TW-Pop/TW-Rock', 'taiwanese movie soundtrack'),

    ## Taiwanese pop por épocas
    'taiwanese pop 80s': ('TW-Pop/TW-Rock', 'taiwanese pop 80s'),
    'taiwanese pop 90s': ('TW-Pop/TW-Rock', 'taiwanese pop 90s'),
    'taiwanese pop 2000s': ('TW-Pop/TW-Rock', 'taiwanese pop 2000s'),
    'taiwanese pop 2010s': ('TW-Pop/TW-Rock', 'taiwanese pop 2010s'),
    'taiwanese pop 2020s': ('TW-Pop/TW-Rock', 'taiwanese pop 2020s'),
    'classic taiwanese pop': ('TW-Pop/TW-Rock', 'classic taiwanese pop'),

    ## Taiwanese pop por región
    'taipei pop': ('TW-Pop/TW-Rock', 'taipei pop'),
    'kaohsiung pop': ('TW-Pop/TW-Rock', 'kaohsiung pop'),
    'taichung pop': ('TW-Pop/TW-Rock', 'taichung pop'),
    'tainan pop': ('TW-Pop/TW-Rock', 'tainan pop'),

    ## Taiwanese fusion
    'taiwanese fusion': ('TW-Pop/TW-Rock', 'taiwanese fusion'),
    'taiwanese world music': ('TW-Pop/TW-Rock', 'taiwanese world music'),

    ###############################################################################
    # HK-Pop/HK-Rock (Regional - Hong Kong)
    ###############################################################################
    ## HK-Pop General
    'hkpop': ('HK-Pop/HK-Rock', 'hkpop'),
    'hk-pop': ('HK-Pop/HK-Rock', 'hk-pop'),
    'hong kong pop': ('HK-Pop/HK-Rock', 'hong kong pop'),
    'pop hongkongues': ('HK-Pop/HK-Rock', 'pop hongkongues'),

    ## Cantopop (cantonés - Hong Kong)
    'cantopop': ('HK-Pop/HK-Rock', 'cantopop'),
    'canto-pop': ('HK-Pop/HK-Rock', 'canto-pop'),
    'cantonese pop': ('HK-Pop/HK-Rock', 'cantonese pop'),
    'pop cantonés hk': ('HK-Pop/HK-Rock', 'pop cantonés hk'),

    ## HK-Rock
    'hkrock': ('HK-Pop/HK-Rock', 'hkrock'),
    'hk-rock': ('HK-Pop/HK-Rock', 'hk-rock'),
    'hong kong rock': ('HK-Pop/HK-Rock', 'hong kong rock'),
    'rock hongkongues': ('HK-Pop/HK-Rock', 'rock hongkongues'),

    ## HK-Indie
    'hkindie': ('HK-Pop/HK-Rock', 'hkindie'),
    'hk-indie': ('HK-Pop/HK-Rock', 'hk-indie'),
    'hong kong indie': ('HK-Pop/HK-Rock', 'hong kong indie'),

    ## HK-Rap
    'hkrap': ('HK-Pop/HK-Rock', 'hkrap'),
    'hk-rap': ('HK-Pop/HK-Rock', 'hk-rap'),
    'hong kong rap': ('HK-Pop/HK-Rock', 'hong kong rap'),
    'cantonese rap': ('HK-Pop/HK-Rock', 'cantonese rap'),

    ## HK-R&B
    'hkrnb': ('HK-Pop/HK-Rock', 'hkrnb'),
    'hk-rnb': ('HK-Pop/HK-Rock', 'hk-rnb'),
    'hong kong r&b': ('HK-Pop/HK-Rock', 'hong kong r&b'),

    ## HK OST
    'hk ost': ('HK-Pop/HK-Rock', 'hk ost'),
    'hong kong drama ost': ('HK-Pop/HK-Rock', 'hong kong drama ost'),
    'hong kong movie soundtrack': ('HK-Pop/HK-Rock', 'hong kong movie soundtrack'),

    ###############################################################################
    # Turkish Pop/Rock (Regional - Turquía)
    ###############################################################################
    ## Turkish Pop General
    'turkish pop': ('Turkish Pop/Rock', 'turkish pop'),
    'turk pop': ('Turkish Pop/Rock', 'turk pop'),
    'pop turco': ('Turkish Pop/Rock', 'pop turco'),
    'türkçe pop': ('Turkish Pop/Rock', 'türkçe pop'),
    'turkish mainstream': ('Turkish Pop/Rock', 'turkish mainstream'),

    ## Arabesk (género turco)
    'arabesk': ('Turkish Pop/Rock', 'arabesk'),
    'turkish arabesk': ('Turkish Pop/Rock', 'turkish arabesk'),
    'arabesque': ('Turkish Pop/Rock', 'arabesque'),

    ## Turkish rock
    'turkish rock': ('Turkish Pop/Rock', 'turkish rock'),
    'turk rock': ('Turkish Pop/Rock', 'turk rock'),
    'rock turco': ('Turkish Pop/Rock', 'rock turco'),
    'türkçe rock': ('Turkish Pop/Rock', 'türkçe rock'),

    ### Subgéneros de Turkish rock
    'turkish alternative rock': ('Turkish Pop/Rock', 'turkish alternative rock'),
    'turkish indie rock': ('Turkish Pop/Rock', 'turkish indie rock'),
    'turkish punk': ('Turkish Pop/Rock', 'turkish punk'),
    'turkish metal': ('Turkish Pop/Rock', 'turkish metal'),
    'istanbul rock': ('Turkish Pop/Rock', 'istanbul rock'),
    'anatolian rock': ('Turkish Pop/Rock', 'anatolian rock'),
    'turkish psychedelic rock': ('Turkish Pop/Rock', 'turkish psychedelic rock'),

    ## Turkish hip hop
    'turkish hip hop': ('Turkish Pop/Rock', 'turkish hip hop'),
    'turkish rap': ('Turkish Pop/Rock', 'turkish rap'),
    'rap turco': ('Turkish Pop/Rock', 'rap turco'),

    ## Turkish folk / Halk müziği
    'turkish folk': ('Turkish Pop/Rock', 'turkish folk'),
    'türk halk müziği': ('Turkish Pop/Rock', 'türk halk müziği'),
    'turkish folk pop': ('Turkish Pop/Rock', 'turkish folk pop'),

    ## Turkish classical / Sanat müziği
    'turkish classical': ('Turkish Pop/Rock', 'turkish classical'),
    'türk sanat müziği': ('Turkish Pop/Rock', 'türk sanat müziği'),
    'turkish art music': ('Turkish Pop/Rock', 'turkish art music'),

    ## Turkish pop por épocas
    'turkish pop 80s': ('Turkish Pop/Rock', 'turkish pop 80s'),
    'turkish pop 90s': ('Turkish Pop/Rock', 'turkish pop 90s'),
    'turkish pop 2000s': ('Turkish Pop/Rock', 'turkish pop 2000s'),
    'turkish pop 2010s': ('Turkish Pop/Rock', 'turkish pop 2010s'),
    'turkish pop 2020s': ('Turkish Pop/Rock', 'turkish pop 2020s'),

    ## Turkish pop por región
    'istanbul pop': ('Turkish Pop/Rock', 'istanbul pop'),
    'ankara pop': ('Turkish Pop/Rock', 'ankara pop'),
    'izmir pop': ('Turkish Pop/Rock', 'izmir pop'),

    ###############################################################################
    # Arabic Pop/Rock (Regional - Mundo Árabe)
    ###############################################################################
    ## Arabic Pop General
    'arabic pop': ('Arabic Pop/Rock', 'arabic pop'),
    'arab pop': ('Arabic Pop/Rock', 'arab pop'),
    'pop árabe': ('Arabic Pop/Rock', 'pop árabe'),
    'al-musiqa al-arabiya': ('Arabic Pop/Rock', 'al-musiqa al-arabiya'),

    ## Egyptian pop
    'egyptian pop': ('Arabic Pop/Rock', 'egyptian pop'),
    'pop egipcio': ('Arabic Pop/Rock', 'pop egipcio'),
    'cairo pop': ('Arabic Pop/Rock', 'cairo pop'),

    ## Lebanese pop
    'lebanese pop': ('Arabic Pop/Rock', 'lebanese pop'),
    'pop libanés': ('Arabic Pop/Rock', 'pop libanés'),
    'beirut pop': ('Arabic Pop/Rock', 'beirut pop'),

    ## Khaliji (Gulf pop)
    'khaliji': ('Arabic Pop/Rock', 'khaliji'),
    'gulf pop': ('Arabic Pop/Rock', 'gulf pop'),
    'khaleeji': ('Arabic Pop/Rock', 'khaleeji'),

    ## Maghreb pop (North Africa)
    'maghreb pop': ('Arabic Pop/Rock', 'maghreb pop'),
    'north african pop': ('Arabic Pop/Rock', 'north african pop'),

    ## Arabic rock
    'arabic rock': ('Arabic Pop/Rock', 'arabic rock'),
    'arab rock': ('Arabic Pop/Rock', 'arab rock'),
    'rock árabe': ('Arabic Pop/Rock', 'rock árabe'),

    ### Subgéneros de Arabic rock
    'arab alternative rock': ('Arabic Pop/Rock', 'arab alternative rock'),
    'arab indie rock': ('Arabic Pop/Rock', 'arab indie rock'),
    'arab metal': ('Arabic Pop/Rock', 'arab metal'),
    'oriental metal': ('Arabic Pop/Rock', 'oriental metal'),

    ## Arabic hip hop
    'arabic hip hop': ('Arabic Pop/Rock', 'arabic hip hop'),
    'arab rap': ('Arabic Pop/Rock', 'arab rap'),
    'rap árabe': ('Arabic Pop/Rock', 'rap árabe'),

    ## Raï (Argelia)
    'raï': ('Arabic Pop/Rock', 'raï'),
    'rai': ('Arabic Pop/Rock', 'rai'),
    'algerian rai': ('Arabic Pop/Rock', 'algerian rai'),
    'rai pop': ('Arabic Pop/Rock', 'rai pop'),

    ## Shaabi (Egipto)
    'shaabi': ('Arabic Pop/Rock', 'shaabi'),
    'egyptian shaabi': ('Arabic Pop/Rock', 'egyptian shaabi'),
    'shaabi pop': ('Arabic Pop/Rock', 'shaabi pop'),
    'mahraganat': ('Arabic Pop/Rock', 'mahraganat'),
    'electro shaabi': ('Arabic Pop/Rock', 'electro shaabi'),

    ## Arabic pop por épocas
    'arabic pop 80s': ('Arabic Pop/Rock', 'arabic pop 80s'),
    'arabic pop 90s': ('Arabic Pop/Rock', 'arabic pop 90s'),
    'arabic pop 2000s': ('Arabic Pop/Rock', 'arabic pop 2000s'),
    'arabic pop 2010s': ('Arabic Pop/Rock', 'arabic pop 2010s'),
    'arabic pop 2020s': ('Arabic Pop/Rock', 'arabic pop 2020s'),

    ## Arabic pop por región
    'cairo pop': ('Arabic Pop/Rock', 'cairo pop'),
    'beirut pop': ('Arabic Pop/Rock', 'beirut pop'),
    'dubai pop': ('Arabic Pop/Rock', 'dubai pop'),
    'casablanca pop': ('Arabic Pop/Rock', 'casablanca pop'),
    'tunis pop': ('Arabic Pop/Rock', 'tunis pop'),
    'baghdad pop': ('Arabic Pop/Rock', 'baghdad pop'),
    'amman pop': ('Arabic Pop/Rock', 'amman pop'),
    'damascus pop': ('Arabic Pop/Rock', 'damascus pop'),

    ###############################################################################
    # Israeli Pop/Rock (Regional - Israel)
    ###############################################################################
    ## Israeli Pop General
    'israeli pop': ('Israeli Pop/Rock', 'israeli pop'),
    'israel pop': ('Israeli Pop/Rock', 'israel pop'),
    'pop israelí': ('Israeli Pop/Rock', 'pop israelí'),
    'pop ivri': ('Israeli Pop/Rock', 'pop ivri'),

    ## Mizrahi pop (oriental)
    'mizrahi': ('Israeli Pop/Rock', 'mizrahi'),
    'mizrahi pop': ('Israeli Pop/Rock', 'mizrahi pop'),
    'musika mizrahit': ('Israeli Pop/Rock', 'musika mizrahit'),
    'oriental pop israelí': ('Israeli Pop/Rock', 'oriental pop israelí'),

    ## Israeli rock
    'israeli rock': ('Israeli Pop/Rock', 'israeli rock'),
    'israel rock': ('Israeli Pop/Rock', 'israel rock'),
    'rock israelí': ('Israeli Pop/Rock', 'rock israelí'),

    ### Subgéneros de Israeli rock
    'israeli alternative rock': ('Israeli Pop/Rock', 'israeli alternative rock'),
    'israeli indie rock': ('Israeli Pop/Rock', 'israeli indie rock'),
    'israeli punk': ('Israeli Pop/Rock', 'israeli punk'),
    'israeli metal': ('Israeli Pop/Rock', 'israeli metal'),
    'tel aviv rock': ('Israeli Pop/Rock', 'tel aviv rock'),

    ## Israeli hip hop
    'israeli hip hop': ('Israeli Pop/Rock', 'israeli hip hop'),
    'israeli rap': ('Israeli Pop/Rock', 'israeli rap'),
    'rap israelí': ('Israeli Pop/Rock', 'rap israelí'),

    ## Israeli folk
    'israeli folk': ('Israeli Pop/Rock', 'israeli folk'),
    'israeli folk pop': ('Israeli Pop/Rock', 'israeli folk pop'),

    ## Israeli Mediterranean
    'israeli mediterranean': ('Israeli Pop/Rock', 'israeli mediterranean'),
    'yemenite pop': ('Israeli Pop/Rock', 'yemenite pop'),

    ## Israeli pop por épocas
    'israeli pop 80s': ('Israeli Pop/Rock', 'israeli pop 80s'),
    'israeli pop 90s': ('Israeli Pop/Rock', 'israeli pop 90s'),
    'israeli pop 2000s': ('Israeli Pop/Rock', 'israeli pop 2000s'),
    'israeli pop 2010s': ('Israeli Pop/Rock', 'israeli pop 2010s'),
    'israeli pop 2020s': ('Israeli Pop/Rock', 'israeli pop 2020s'),

    ## Israeli pop por región
    'tel aviv pop': ('Israeli Pop/Rock', 'tel aviv pop'),
    'jerusalem pop': ('Israeli Pop/Rock', 'jerusalem pop'),
    'haifa pop': ('Israeli Pop/Rock', 'haifa pop'),

    ###############################################################################
    # Q-pop/Q-rock (Regional - Kazajistán)
    ###############################################################################
    ## Q-pop General (English / Kazakh)
    'qpop': ('Q-pop/Q-rock', 'qpop'),
    'q-pop': ('Q-pop/Q-rock', 'q-pop'),
    'q pop': ('Q-pop/Q-rock', 'q pop'),
    'kazakh pop': ('Q-pop/Q-rock', 'kazakh pop'),
    'pop kazajo': ('Q-pop/Q-rock', 'pop kazajo'),
    'qazaq pop': ('Q-pop/Q-rock', 'qazaq pop'),

    ## Q-pop idol (grupos)
    'qpop idol': ('Q-pop/Q-rock', 'qpop idol'),
    'q-pop idol': ('Q-pop/Q-rock', 'q-pop idol'),
    'qpop group': ('Q-pop/Q-rock', 'qpop group'),
    'qpop boy band': ('Q-pop/Q-rock', 'qpop boy band'),
    'qpop girl group': ('Q-pop/Q-rock', 'qpop girl group'),
    'kazakh boy band': ('Q-pop/Q-rock', 'kazakh boy band'),
    'kazakh girl group': ('Q-pop/Q-rock', 'kazakh girl group'),

    ## Q-pop solista
    'qpop solo': ('Q-pop/Q-rock', 'qpop solo'),
    'q-pop solo': ('Q-pop/Q-rock', 'q-pop solo'),
    'solo qpop': ('Q-pop/Q-rock', 'solo qpop'),
    'qpop soloist': ('Q-pop/Q-rock', 'qpop soloist'),

    ## Q-rock
    'qrock': ('Q-pop/Q-rock', 'qrock'),
    'q-rock': ('Q-pop/Q-rock', 'q-rock'),
    'kazakh rock': ('Q-pop/Q-rock', 'kazakh rock'),
    'rock kazajo': ('Q-pop/Q-rock', 'rock kazajo'),
    'qazaq rock': ('Q-pop/Q-rock', 'qazaq rock'),

    ### Subgéneros de Q-rock
    'kazakh alternative rock': ('Q-pop/Q-rock', 'kazakh alternative rock'),
    'kazakh indie rock': ('Q-pop/Q-rock', 'kazakh indie rock'),
    'kazakh metal': ('Q-pop/Q-rock', 'kazakh metal'),
    'kazakh folk metal': ('Q-pop/Q-rock', 'kazakh folk metal'),
    'almaty rock': ('Q-pop/Q-rock', 'almaty rock'),

    ## Q-rap / Q-hip hop
    'qrap': ('Q-pop/Q-rock', 'qrap'),
    'q-rap': ('Q-pop/Q-rock', 'q-rap'),
    'qhiphop': ('Q-pop/Q-rock', 'qhiphop'),
    'q-hiphop': ('Q-pop/Q-rock', 'q-hiphop'),
    'kazakh hip hop': ('Q-pop/Q-rock', 'kazakh hip hop'),
    'kazakh rap': ('Q-pop/Q-rock', 'kazakh rap'),
    'rap kazajo': ('Q-pop/Q-rock', 'rap kazajo'),

    ## Q-R&B
    'qrnb': ('Q-pop/Q-rock', 'qrnb'),
    'q-rnb': ('Q-pop/Q-rock', 'q-rnb'),
    'kazakh r&b': ('Q-pop/Q-rock', 'kazakh r&b'),
    'kazakh rnb': ('Q-pop/Q-rock', 'kazakh rnb'),

    ## Q-pop balada
    'qpop ballad': ('Q-pop/Q-rock', 'qpop ballad'),
    'kazakh ballad': ('Q-pop/Q-rock', 'kazakh ballad'),
    'balada kazaja': ('Q-pop/Q-rock', 'balada kazaja'),

    ## Q-pop fusión / Tradicional
    'qpop fusion': ('Q-pop/Q-rock', 'qpop fusion'),
    'kazakh fusion': ('Q-pop/Q-rock', 'kazakh fusion'),
    'q-pop folk': ('Q-pop/Q-rock', 'q-pop folk'),
    'kazakh folk pop': ('Q-pop/Q-rock', 'kazakh folk pop'),
    'dombra pop': ('Q-pop/Q-rock', 'dombra pop'),
    'qobyz pop': ('Q-pop/Q-rock', 'qobyz pop'),

    ## Q-pop por épocas
    'qpop 2010s': ('Q-pop/Q-rock', 'qpop 2010s'),
    'qpop 2020s': ('Q-pop/Q-rock', 'qpop 2020s'),
    'modern qpop': ('Q-pop/Q-rock', 'modern qpop'),
    'contemporary qpop': ('Q-pop/Q-rock', 'contemporary qpop'),
    'classic qpop': ('Q-pop/Q-rock', 'classic qpop'),

    ## Q-pop por región
    'almaty pop': ('Q-pop/Q-rock', 'almaty pop'),
    'astana pop': ('Q-pop/Q-rock', 'astana pop'),
    'nur-sultan pop': ('Q-pop/Q-rock', 'nur-sultan pop'),
    'shymkent pop': ('Q-pop/Q-rock', 'shymkent pop'),

    ## Q-OST
    'qost': ('Q-pop/Q-rock', 'qost'),
    'q-ost': ('Q-pop/Q-rock', 'q-ost'),
    'kazakh ost': ('Q-pop/Q-rock', 'kazakh ost'),
    'kazakh soundtrack': ('Q-pop/Q-rock', 'kazakh soundtrack'),
    'kazakh drama ost': ('Q-pop/Q-rock', 'kazakh drama ost'),

    ## Q-pop electrónico
    'qpop edm': ('Q-pop/Q-rock', 'qpop edm'),
    'qpop electronic': ('Q-pop/Q-rock', 'qpop electronic'),
    'kazakh edm': ('Q-pop/Q-rock', 'kazakh edm'),
    'qpop dance': ('Q-pop/Q-rock', 'qpop dance'),

    ## Q-pop acústico
    'qpop acoustic': ('Q-pop/Q-rock', 'qpop acoustic'),
    'acoustic qpop': ('Q-pop/Q-rock', 'acoustic qpop'),
    'kazakh acoustic': ('Q-pop/Q-rock', 'kazakh acoustic'),

    ###############################################################################
    # Nepali Pop/Rock (Regional - Nepal)
    ###############################################################################
    ## Nepali Pop General (English / Nepali)
    'nepali pop': ('Nepali Pop/Rock', 'nepali pop'),
    'nep pop': ('Nepali Pop/Rock', 'nep pop'),
    'nepal pop': ('Nepali Pop/Rock', 'nepal pop'),
    'pop nepalí': ('Nepali Pop/Rock', 'pop nepalí'),
    'nepali music': ('Nepali Pop/Rock', 'nepali music'),
    'nepali geet': ('Nepali Pop/Rock', 'nepali geet'),

    ## Nepop moderno / Adhunik
    'nepop': ('Nepali Pop/Rock', 'nepop'),
    'modern nepop': ('Nepali Pop/Rock', 'modern nepop'),
    'contemporary nepali pop': ('Nepali Pop/Rock', 'contemporary nepali pop'),
    'adhunik geet': ('Nepali Pop/Rock', 'adhunik geet'),

    ## Nepali rock
    'nepali rock': ('Nepali Pop/Rock', 'nepali rock'),
    'nep rock': ('Nepali Pop/Rock', 'nep rock'),
    'rock nepalí': ('Nepali Pop/Rock', 'rock nepalí'),
    'kathmandu rock': ('Nepali Pop/Rock', 'kathmandu rock'),

    ### Subgéneros de Nepali rock
    'nepali alternative rock': ('Nepali Pop/Rock', 'nepali alternative rock'),
    'nepali indie rock': ('Nepali Pop/Rock', 'nepali indie rock'),
    'nepali punk': ('Nepali Pop/Rock', 'nepali punk'),
    'nepali metal': ('Nepali Pop/Rock', 'nepali metal'),
    'nepali folk metal': ('Nepali Pop/Rock', 'nepali folk metal'),
    'nepali progressive rock': ('Nepali Pop/Rock', 'nepali progressive rock'),

    ## Nepali hip hop / Rap
    'nepali hip hop': ('Nepali Pop/Rock', 'nepali hip hop'),
    'nepali rap': ('Nepali Pop/Rock', 'nepali rap'),
    'nep rap': ('Nepali Pop/Rock', 'nep rap'),
    'kathmandu rap': ('Nepali Pop/Rock', 'kathmandu rap'),

    ## Nepali R&B
    'nepali r&b': ('Nepali Pop/Rock', 'nepali r&b'),
    'nepali rnb': ('Nepali Pop/Rock', 'nepali rnb'),

    ## Nepali folk / Lok geet
    'nepali folk': ('Nepali Pop/Rock', 'nepali folk'),
    'folk nepalí': ('Nepali Pop/Rock', 'folk nepalí'),
    'lok geet': ('Nepali Pop/Rock', 'lok geet'),
    'nepali lok': ('Nepali Pop/Rock', 'nepali lok'),
    'lok pop': ('Nepali Pop/Rock', 'lok pop'),

    ### Variantes regionales del folk
    'tamang selo': ('Nepali Pop/Rock', 'tamang selo'),
    'dohori': ('Nepali Pop/Rock', 'dohori'),
    'dohori geet': ('Nepali Pop/Rock', 'dohori geet'),
    'newa music': ('Nepali Pop/Rock', 'newa music'),
    'newari music': ('Nepali Pop/Rock', 'newari music'),
    'gurung music': ('Nepali Pop/Rock', 'gurung music'),
    'magar music': ('Nepali Pop/Rock', 'magar music'),
    'rai music': ('Nepali Pop/Rock', 'rai music'),
    'limbu music': ('Nepali Pop/Rock', 'limbu music'),

    ## Nepali fusion / World
    'nepali fusion': ('Nepali Pop/Rock', 'nepali fusion'),
    'himalayan fusion': ('Nepali Pop/Rock', 'himalayan fusion'),
    'buddhist fusion': ('Nepali Pop/Rock', 'buddhist fusion'),

    ## Nepali balada / Sugam geet
    'nepali ballad': ('Nepali Pop/Rock', 'nepali ballad'),
    'sugam geet': ('Nepali Pop/Rock', 'sugam geet'),
    'balada nepalí': ('Nepali Pop/Rock', 'balada nepalí'),

    ## Nepali indie
    'nepali indie': ('Nepali Pop/Rock', 'nepali indie'),
    'kathmandu indie': ('Nepali Pop/Rock', 'kathmandu indie'),
    'indie nepalí': ('Nepali Pop/Rock', 'indie nepalí'),

    ## Nepali OST / Cinema
    'nepali ost': ('Nepali Pop/Rock', 'nepali ost'),
    'nepali movie song': ('Nepali Pop/Rock', 'nepali movie song'),
    'kollywood nepal': ('Nepali Pop/Rock', 'kollywood nepal'),
    'nepali film music': ('Nepali Pop/Rock', 'nepali film music'),
    'nepali cinema geet': ('Nepali Pop/Rock', 'nepali cinema geet'),

    ## Nepali pop por épocas
    'nepop 80s': ('Nepali Pop/Rock', 'nepop 80s'),
    'nepop 90s': ('Nepali Pop/Rock', 'nepop 90s'),
    'nepop 2000s': ('Nepali Pop/Rock', 'nepop 2000s'),
    'nepop 2010s': ('Nepali Pop/Rock', 'nepop 2010s'),
    'nepop 2020s': ('Nepali Pop/Rock', 'nepop 2020s'),
    'classic nepop': ('Nepali Pop/Rock', 'classic nepop'),
    'golden era nepop': ('Nepali Pop/Rock', 'golden era nepop'),

    ## Nepali pop por región
    'kathmandu pop': ('Nepali Pop/Rock', 'kathmandu pop'),
    'pokhara pop': ('Nepali Pop/Rock', 'pokhara pop'),
    'lalitpur pop': ('Nepali Pop/Rock', 'lalitpur pop'),
    'bhaktapur pop': ('Nepali Pop/Rock', 'bhaktapur pop'),
    'terai pop': ('Nepali Pop/Rock', 'terai pop'),
    'himalayan pop': ('Nepali Pop/Rock', 'himalayan pop'),

    ## Nepali electronic
    'nepali electronic': ('Nepali Pop/Rock', 'nepali electronic'),
    'nepali edm': ('Nepali Pop/Rock', 'nepali edm'),

    ## Nepali acoustic
    'nepali acoustic': ('Nepali Pop/Rock', 'nepali acoustic'),
    'acoustic nepal': ('Nepali Pop/Rock', 'acoustic nepal'),

    ## Música newar clásica
    'newar classical': ('Nepali Pop/Rock', 'newar classical'),
    'newa dhimay': ('Nepali Pop/Rock', 'newa dhimay'),

    ###############################################################################
    # Mongolian Pop/Rock/Metal (Regional - Mongolia)
    ###############################################################################
    ## Mongolian Pop General (English / Mongolian)
    'mongolian pop': ('Mongolian Pop/Rock/Metal', 'mongolian pop'),
    'mongol pop': ('Mongolian Pop/Rock/Metal', 'mongol pop'),
    'pop mongol': ('Mongolian Pop/Rock/Metal', 'pop mongol'),
    'ulaanbaatar pop': ('Mongolian Pop/Rock/Metal', 'ulaanbaatar pop'),
    'mongol hiip hop': ('Mongolian Pop/Rock/Metal', 'mongol hiip hop'),

    ## Mongolian rock
    'mongolian rock': ('Mongolian Pop/Rock/Metal', 'mongolian rock'),
    'mongol rock': ('Mongolian Pop/Rock/Metal', 'mongol rock'),
    'rock mongol': ('Mongolian Pop/Rock/Metal', 'rock mongol'),
    'ulaanbaatar rock': ('Mongolian Pop/Rock/Metal', 'ulaanbaatar rock'),

    ### Subgéneros de Mongolian rock
    'mongolian alternative rock': ('Mongolian Pop/Rock/Metal', 'mongolian alternative rock'),
    'mongolian indie rock': ('Mongolian Pop/Rock/Metal', 'mongolian indie rock'),
    'mongolian punk': ('Mongolian Pop/Rock/Metal', 'mongolian punk'),

    ## Mongolian metal / Folk metal
    'mongolian metal': ('Mongolian Pop/Rock/Metal', 'mongolian metal'),
    'mongol metal': ('Mongolian Pop/Rock/Metal', 'mongol metal'),
    'mongolian folk metal': ('Mongolian Pop/Rock/Metal', 'mongolian folk metal'),
    'hunnu rock': ('Mongolian Pop/Rock/Metal', 'hunnu rock'),
    'the hu style': ('Mongolian Pop/Rock/Metal', 'the hu style'),

    ## Khoomei fusion (canto gutural)
    'khoomei fusion': ('Mongolian Pop/Rock/Metal', 'khoomei fusion'),
    'throat singing fusion': ('Mongolian Pop/Rock/Metal', 'throat singing fusion'),
    'mongolian throat singing rock': ('Mongolian Pop/Rock/Metal', 'mongolian throat singing rock'),

    ## Mongolian hip hop / Rap
    'mongolian hip hop': ('Mongolian Pop/Rock/Metal', 'mongolian hip hop'),
    'mongolian rap': ('Mongolian Pop/Rock/Metal', 'mongolian rap'),
    'mongol rap': ('Mongolian Pop/Rock/Metal', 'mongol rap'),
    'ulaanbaatar rap': ('Mongolian Pop/Rock/Metal', 'ulaanbaatar rap'),

    ## Mongolian folk / Tradicional
    'mongolian folk': ('Mongolian Pop/Rock/Metal', 'mongolian folk'),
    'mongol folk': ('Mongolian Pop/Rock/Metal', 'mongol folk'),
    'morin khuur fusion': ('Mongolian Pop/Rock/Metal', 'morin khuur fusion'),

    ## Mongolian fusion
    'mongolian fusion': ('Mongolian Pop/Rock/Metal', 'mongolian fusion'),
    'steppe fusion': ('Mongolian Pop/Rock/Metal', 'steppe fusion'),

    ## Mongolian pop por región
    'ulaanbaatar pop': ('Mongolian Pop/Rock/Metal', 'ulaanbaatar pop'),
    'darkhan pop': ('Mongolian Pop/Rock/Metal', 'darkhan pop'),
    'erdent pop': ('Mongolian Pop/Rock/Metal', 'erdent pop'),

    ###############################################################################
    # Afghan Pop/Rock (Regional - Afganistán)
    ###############################################################################
    ## Afghan Pop General (English / Dari/Pashto)
    'afghan pop': ('Afghan Pop/Rock', 'afghan pop'),
    'afghani pop': ('Afghan Pop/Rock', 'afghani pop'),
    'pop afgano': ('Afghan Pop/Rock', 'pop afgano'),
    'kabul pop': ('Afghan Pop/Rock', 'kabul pop'),
    'musica afgana': ('Afghan Pop/Rock', 'musica afgana'),

    ## Afghan pop moderno / Diáspora
    'afghan diaspora pop': ('Afghan Pop/Rock', 'afghan diaspora pop'),
    'modern afghan pop': ('Afghan Pop/Rock', 'modern afghan pop'),
    'contemporary afghan music': ('Afghan Pop/Rock', 'contemporary afghan music'),

    ## Afghan rock
    'afghan rock': ('Afghan Pop/Rock', 'afghan rock'),
    'kabul rock': ('Afghan Pop/Rock', 'kabul rock'),
    'rock afgano': ('Afghan Pop/Rock', 'rock afgano'),

    ### Subgéneros de Afghan rock
    'afghan alternative rock': ('Afghan Pop/Rock', 'afghan alternative rock'),
    'afghan indie rock': ('Afghan Pop/Rock', 'afghan indie rock'),
    'afghan metal': ('Afghan Pop/Rock', 'afghan metal'),

    ## Afghan hip hop / Rap
    'afghan hip hop': ('Afghan Pop/Rock', 'afghan hip hop'),
    'afghan rap': ('Afghan Pop/Rock', 'afghan rap'),
    'kabul rap': ('Afghan Pop/Rock', 'kabul rap'),
    'afghan diaspora rap': ('Afghan Pop/Rock', 'afghan diaspora rap'),

    ## Afghan folk / Clásico
    'afghan folk': ('Afghan Pop/Rock', 'afghan folk'),
    'folk afgano': ('Afghan Pop/Rock', 'folk afgano'),
    'rubab fusion': ('Afghan Pop/Rock', 'rubab fusion'),

    ## Ghazal afgano
    'afghan ghazal': ('Afghan Pop/Rock', 'afghan ghazal'),
    'dari ghazal': ('Afghan Pop/Rock', 'dari ghazal'),
    'pashto ghazal': ('Afghan Pop/Rock', 'pashto ghazal'),

    ## Afghan fusion
    'afghan fusion': ('Afghan Pop/Rock', 'afghan fusion'),
    'kabul fusion': ('Afghan Pop/Rock', 'kabul fusion'),

    ## Afghan pop por región / etnia
    'kabul pop': ('Afghan Pop/Rock', 'kabul pop'),
    'herat pop': ('Afghan Pop/Rock', 'herat pop'),
    'mazar pop': ('Afghan Pop/Rock', 'mazar pop'),
    'pashto pop': ('Afghan Pop/Rock', 'pashto pop'),
    'dari pop': ('Afghan Pop/Rock', 'dari pop'),
    'hazara pop': ('Afghan Pop/Rock', 'hazara pop'),
    'uzbek afghan pop': ('Afghan Pop/Rock', 'uzbek afghan pop'),

    ## Afghan pop post-talibán
    'post taliban music': ('Afghan Pop/Rock', 'post taliban music'),
    'afghan revival': ('Afghan Pop/Rock', 'afghan revival'),

    ###############################################################################
    # Tibetan Pop/Rock (Regional - Tíbet / Diáspora)
    ###############################################################################
    ## Tibetan Pop General (English / Tibetan)
    'tibetan pop': ('Tibetan Pop/Rock', 'tibetan pop'),
    'bod pop': ('Tibetan Pop/Rock', 'bod pop'),
    'pop tibetano': ('Tibetan Pop/Rock', 'pop tibetano'),
    'lhasa pop': ('Tibetan Pop/Rock', 'lhasa pop'),
    'tibetan music': ('Tibetan Pop/Rock', 'tibetan music'),

    ## Tibetan pop moderno / Diáspora
    'tibetan diaspora pop': ('Tibetan Pop/Rock', 'tibetan diaspora pop'),
    'modern tibetan pop': ('Tibetan Pop/Rock', 'modern tibetan pop'),
    'contemporary tibetan music': ('Tibetan Pop/Rock', 'contemporary tibetan music'),
    'dharamshala pop': ('Tibetan Pop/Rock', 'dharamshala pop'),

    ## Tibetan rock
    'tibetan rock': ('Tibetan Pop/Rock', 'tibetan rock'),
    'lhasa rock': ('Tibetan Pop/Rock', 'lhasa rock'),
    'rock tibetano': ('Tibetan Pop/Rock', 'rock tibetano'),
    'tibetan indie rock': ('Tibetan Pop/Rock', 'tibetan indie rock'),

    ### Subgéneros de Tibetan rock
    'tibetan alternative rock': ('Tibetan Pop/Rock', 'tibetan alternative rock'),
    'tibetan metal': ('Tibetan Pop/Rock', 'tibetan metal'),
    'tibetan punk': ('Tibetan Pop/Rock', 'tibetan punk'),

    ## Tibetan hip hop / Rap
    'tibetan hip hop': ('Tibetan Pop/Rock', 'tibetan hip hop'),
    'tibetan rap': ('Tibetan Pop/Rock', 'tibetan rap'),
    'tibetan diaspora rap': ('Tibetan Pop/Rock', 'tibetan diaspora rap'),
    'tibetan resistance rap': ('Tibetan Pop/Rock', 'tibetan resistance rap'),

    ## Tibetan Buddhist fusion
    'buddhist fusion': ('Tibetan Pop/Rock', 'buddhist fusion'),
    'tibetan chant fusion': ('Tibetan Pop/Rock', 'tibetan chant fusion'),
    'mantra pop': ('Tibetan Pop/Rock', 'mantra pop'),
    'buddhist electronic': ('Tibetan Pop/Rock', 'buddhist electronic'),

    ## Tibetan folk / Tradicional
    'tibetan folk': ('Tibetan Pop/Rock', 'tibetan folk'),
    'bod folk': ('Tibetan Pop/Rock', 'bod folk'),
    'tibetan traditional': ('Tibetan Pop/Rock', 'tibetan traditional'),
    'nangma': ('Tibetan Pop/Rock', 'nangma'),
    'toeshey': ('Tibetan Pop/Rock', 'toeshey'),
    'lu': ('Tibetan Pop/Rock', 'lu'),
    'dungchen fusion': ('Tibetan Pop/Rock', 'dungchen fusion'),
    'gyaling fusion': ('Tibetan Pop/Rock', 'gyaling fusion'),

    ## Tibetan fusion
    'tibetan fusion': ('Tibetan Pop/Rock', 'tibetan fusion'),
    'himalayan fusion': ('Tibetan Pop/Rock', 'himalayan fusion'),

    ## Tibetan pop por región
    'lhasa pop': ('Tibetan Pop/Rock', 'lhasa pop'),
    'dharamshala pop': ('Tibetan Pop/Rock', 'dharamshala pop'),
    'kathmandu tibetan pop': ('Tibetan Pop/Rock', 'kathmandu tibetan pop'),
    'boudha pop': ('Tibetan Pop/Rock', 'boudha pop'),

    ## Tibetan OST
    'tibetan ost': ('Tibetan Pop/Rock', 'tibetan ost'),
    'tibetan movie songs': ('Tibetan Pop/Rock', 'tibetan movie songs'),

    ## Tibetan pop por épocas
    'tibetan pop 80s': ('Tibetan Pop/Rock', 'tibetan pop 80s'),
    'tibetan pop 90s': ('Tibetan Pop/Rock', 'tibetan pop 90s'),
    'tibetan pop 2000s': ('Tibetan Pop/Rock', 'tibetan pop 2000s'),
    'tibetan pop 2010s': ('Tibetan Pop/Rock', 'tibetan pop 2010s'),
    'tibetan pop 2020s': ('Tibetan Pop/Rock', 'tibetan pop 2020s'),
    'classic tibetan pop': ('Tibetan Pop/Rock', 'classic tibetan pop'),

    ###############################################################################
    # Uyghur Pop/Rock (Regional - Xinjiang / Diáspora)
    ###############################################################################
    ## Uyghur Pop General (English / Uyghur)
    'uyghur pop': ('Uyghur Pop/Rock', 'uyghur pop'),
    'uighur pop': ('Uyghur Pop/Rock', 'uighur pop'),
    'pop uigur': ('Uyghur Pop/Rock', 'pop uigur'),
    'kashgar pop': ('Uyghur Pop/Rock', 'kashgar pop'),
    'urumqi pop': ('Uyghur Pop/Rock', 'urumqi pop'),
    'uyghur music': ('Uyghur Pop/Rock', 'uyghur music'),
    'uyghur nahxa': ('Uyghur Pop/Rock', 'uyghur nahxa'),

    ## Uyghur pop moderno / Diáspora
    'uyghur diaspora pop': ('Uyghur Pop/Rock', 'uyghur diaspora pop'),
    'modern uyghur pop': ('Uyghur Pop/Rock', 'modern uyghur pop'),
    'contemporary uyghur music': ('Uyghur Pop/Rock', 'contemporary uyghur music'),
    'istanbul uyghur pop': ('Uyghur Pop/Rock', 'istanbul uyghur pop'),

    ## Uyghur rock
    'uyghur rock': ('Uyghur Pop/Rock', 'uyghur rock'),
    'uighur rock': ('Uyghur Pop/Rock', 'uighur rock'),
    'rock uigur': ('Uyghur Pop/Rock', 'rock uigur'),
    'kashgar rock': ('Uyghur Pop/Rock', 'kashgar rock'),

    ### Subgéneros de Uyghur rock
    'uyghur alternative rock': ('Uyghur Pop/Rock', 'uyghur alternative rock'),
    'uyghur indie rock': ('Uyghur Pop/Rock', 'uyghur indie rock'),
    'uyghur metal': ('Uyghur Pop/Rock', 'uyghur metal'),
    'uyghur punk': ('Uyghur Pop/Rock', 'uyghur punk'),
    'uyghur psychedelic rock': ('Uyghur Pop/Rock', 'uyghur psychedelic rock'),

    ## Uyghur hip hop / Rap
    'uyghur hip hop': ('Uyghur Pop/Rock', 'uyghur hip hop'),
    'uyghur rap': ('Uyghur Pop/Rock', 'uyghur rap'),
    'uighur rap': ('Uyghur Pop/Rock', 'uighur rap'),
    'uyghur diaspora rap': ('Uyghur Pop/Rock', 'uyghur diaspora rap'),

    ## Uyghur R&B
    'uyghur r&b': ('Uyghur Pop/Rock', 'uyghur r&b'),
    'uyghur rnb': ('Uyghur Pop/Rock', 'uyghur rnb'),

    ## Muqam fusion (clásico uyghur)
    'muqam': ('Uyghur Pop/Rock', 'muqam'),
    'on ikki muqam': ('Uyghur Pop/Rock', 'on ikki muqam'),
    'muqam fusion': ('Uyghur Pop/Rock', 'muqam fusion'),
    'twelve muqam': ('Uyghur Pop/Rock', 'twelve muqam'),

    ## Uyghur folk / Tradicional
    'uyghur folk': ('Uyghur Pop/Rock', 'uyghur folk'),
    'uighur folk': ('Uyghur Pop/Rock', 'uighur folk'),
    'rawap fusion': ('Uyghur Pop/Rock', 'rawap fusion'),
    'dutar fusion': ('Uyghur Pop/Rock', 'dutar fusion'),
    'ghijek fusion': ('Uyghur Pop/Rock', 'ghijek fusion'),
    'satar fusion': ('Uyghur Pop/Rock', 'satar fusion'),
    'meshrep fusion': ('Uyghur Pop/Rock', 'meshrep fusion'),

    ## Uyghur fusion
    'uyghur fusion': ('Uyghur Pop/Rock', 'uyghur fusion'),
    'silk road fusion': ('Uyghur Pop/Rock', 'silk road fusion'),
    'uyghur world music': ('Uyghur Pop/Rock', 'uyghur world music'),

    ## Uyghur pop por región
    'kashgar pop': ('Uyghur Pop/Rock', 'kashgar pop'),
    'urumqi pop': ('Uyghur Pop/Rock', 'urumqi pop'),
    'turpan pop': ('Uyghur Pop/Rock', 'turpan pop'),
    'hunza pop': ('Uyghur Pop/Rock', 'hunza pop'),
    'istanbul uyghur pop': ('Uyghur Pop/Rock', 'istanbul uyghur pop'),

    ## Uyghur OST
    'uyghur ost': ('Uyghur Pop/Rock', 'uyghur ost'),
    'uyghur film music': ('Uyghur Pop/Rock', 'uyghur film music'),

    ## Uyghur pop por épocas
    'uyghur pop 80s': ('Uyghur Pop/Rock', 'uyghur pop 80s'),
    'uyghur pop 90s': ('Uyghur Pop/Rock', 'uyghur pop 90s'),
    'uyghur pop 2000s': ('Uyghur Pop/Rock', 'uyghur pop 2000s'),
    'uyghur pop 2010s': ('Uyghur Pop/Rock', 'uyghur pop 2010s'),
    'uyghur pop 2020s': ('Uyghur Pop/Rock', 'uyghur pop 2020s'),
    'classic uyghur pop': ('Uyghur Pop/Rock', 'classic uyghur pop'),

    ###############################################################################
    # Timorese Pop/Rock (Regional - Timor-Leste)
    ###############################################################################
    ## Timorese Pop General (English / Tetum / Portugués)
    'timorese pop': ('Timorese Pop/Rock', 'timorese pop'),
    'timor pop': ('Timorese Pop/Rock', 'timor pop'),
    'pop timorense': ('Timorese Pop/Rock', 'pop timorense'),
    'dili pop': ('Timorese Pop/Rock', 'dili pop'),
    'musica timorense': ('Timorese Pop/Rock', 'musica timorense'),
    'musik timor': ('Timorese Pop/Rock', 'musik timor'),

    ## Timorese rock
    'timorese rock': ('Timorese Pop/Rock', 'timorese rock'),
    'timor rock': ('Timorese Pop/Rock', 'timor rock'),
    'rock timorense': ('Timorese Pop/Rock', 'rock timorense'),
    'dili rock': ('Timorese Pop/Rock', 'dili rock'),

    ### Subgéneros de Timorese rock
    'timorese alternative rock': ('Timorese Pop/Rock', 'timorese alternative rock'),
    'timorese indie rock': ('Timorese Pop/Rock', 'timorese indie rock'),
    'timorese punk': ('Timorese Pop/Rock', 'timorese punk'),
    'timorese metal': ('Timorese Pop/Rock', 'timorese metal'),

    ## Timorese hip hop / Rap
    'timorese hip hop': ('Timorese Pop/Rock', 'timorese hip hop'),
    'timorese rap': ('Timorese Pop/Rock', 'timorese rap'),
    'dili rap': ('Timorese Pop/Rock', 'dili rap'),
    'rap timorense': ('Timorese Pop/Rock', 'rap timorense'),

    ## Timorese folk / Tradicional
    'timorese folk': ('Timorese Pop/Rock', 'timorese folk'),
    'folk timorense': ('Timorese Pop/Rock', 'folk timorense'),
    'likurai': ('Timorese Pop/Rock', 'likurai'),
    'tebe': ('Timorese Pop/Rock', 'tebe'),

    ## Fusión portuguesa / lusófona
    'timorese portuguese fusion': ('Timorese Pop/Rock', 'timorese portuguese fusion'),
    'lusophone fusion': ('Timorese Pop/Rock', 'lusophone fusion'),
    'fado timorense': ('Timorese Pop/Rock', 'fado timorense'),

    ## Fusión austronesia
    'austronesian fusion': ('Timorese Pop/Rock', 'austronesian fusion'),
    'timorese island fusion': ('Timorese Pop/Rock', 'timorese island fusion'),

    ## Timorese pop por región
    'dili pop': ('Timorese Pop/Rock', 'dili pop'),
    'baucau pop': ('Timorese Pop/Rock', 'baucau pop'),
    'same pop': ('Timorese Pop/Rock', 'same pop'),
    'ocussi pop': ('Timorese Pop/Rock', 'ocussi pop'),

    ## Timorese post-independencia
    'post independence timor music': ('Timorese Pop/Rock', 'post independence timor music'),
    'timor leste contemporary': ('Timorese Pop/Rock', 'timor leste contemporary'),

    ## Timorese resistencia / protesta
    'timorese protest music': ('Timorese Pop/Rock', 'timorese protest music'),
    'resistencia music': ('Timorese Pop/Rock', 'resistencia music'),

    ###############################################################################
    # Sri Lankan Pop/Rock (Regional - Sri Lanka)
    ###############################################################################
    ## Sri Lankan Pop General (English / Sinhala / Tamil)
    'sri lankan pop': ('Sri Lankan Pop/Rock', 'sri lankan pop'),
    'srilankan pop': ('Sri Lankan Pop/Rock', 'srilankan pop'),
    'lanka pop': ('Sri Lankan Pop/Rock', 'lanka pop'),
    'pop ceilán': ('Sri Lankan Pop/Rock', 'pop ceilán'),
    'sinhala pop': ('Sri Lankan Pop/Rock', 'sinhala pop'),
    'tamil pop sri lanka': ('Sri Lankan Pop/Rock', 'tamil pop sri lanka'),
    'sri lanka baila': ('Sri Lankan Pop/Rock', 'sri lanka baila'),

    ## Baila (género fundamental)
    'baila': ('Sri Lankan Pop/Rock', 'baila'),
    'sri lankan baila': ('Sri Lankan Pop/Rock', 'sri lankan baila'),
    'baila music': ('Sri Lankan Pop/Rock', 'baila music'),
    'kaffirinha': ('Sri Lankan Pop/Rock', 'kaffirinha'),

    ## Sri Lankan rock
    'sri lankan rock': ('Sri Lankan Pop/Rock', 'sri lankan rock'),
    'lanka rock': ('Sri Lankan Pop/Rock', 'lanka rock'),
    'colombo rock': ('Sri Lankan Pop/Rock', 'colombo rock'),
    'sinhala rock': ('Sri Lankan Pop/Rock', 'sinhala rock'),

    ### Subgéneros de rock
    'sri lankan alternative rock': ('Sri Lankan Pop/Rock', 'sri lankan alternative rock'),
    'sri lankan indie rock': ('Sri Lankan Pop/Rock', 'sri lankan indie rock'),
    'sri lankan metal': ('Sri Lankan Pop/Rock', 'sri lankan metal'),
    'sri lankan punk': ('Sri Lankan Pop/Rock', 'sri lankan punk'),

    ## Sri Lankan hip hop / Rap
    'sri lankan hip hop': ('Sri Lankan Pop/Rock', 'sri lankan hip hop'),
    'sri lankan rap': ('Sri Lankan Pop/Rock', 'sri lankan rap'),
    'colombo rap': ('Sri Lankan Pop/Rock', 'colombo rap'),
    'sinhala rap': ('Sri Lankan Pop/Rock', 'sinhala rap'),
    'tamil rap sri lanka': ('Sri Lankan Pop/Rock', 'tamil rap sri lanka'),

    ## Sri Lankan R&B
    'sri lankan r&b': ('Sri Lankan Pop/Rock', 'sri lankan r&b'),
    'sri lankan rnb': ('Sri Lankan Pop/Rock', 'sri lankan rnb'),

    ## Música tradicional fusionada
    'sri lankan folk': ('Sri Lankan Pop/Rock', 'sri lankan folk'),
    'sinhala folk': ('Sri Lankan Pop/Rock', 'sinhala folk'),
    'vannam': ('Sri Lankan Pop/Rock', 'vannam'),
    'virindu': ('Sri Lankan Pop/Rock', 'virindu'),
    'nurthi': ('Sri Lankan Pop/Rock', 'nurthi'),

    ## Sri Lankan fusion
    'sri lankan fusion': ('Sri Lankan Pop/Rock', 'sri lankan fusion'),
    'lanka fusion': ('Sri Lankan Pop/Rock', 'lanka fusion'),

    ## Sri Lankan pop por región
    'colombo pop': ('Sri Lankan Pop/Rock', 'colombo pop'),
    'kandy pop': ('Sri Lankan Pop/Rock', 'kandy pop'),
    'galle pop': ('Sri Lankan Pop/Rock', 'galle pop'),
    'jaffna pop': ('Sri Lankan Pop/Rock', 'jaffna pop'),

    ## Sri Lankan OST
    'sri lankan ost': ('Sri Lankan Pop/Rock', 'sri lankan ost'),
    'sri lankan cinema songs': ('Sri Lankan Pop/Rock', 'sri lankan cinema songs'),

    ## Sri Lankan pop por épocas
    'sri lankan pop 80s': ('Sri Lankan Pop/Rock', 'sri lankan pop 80s'),
    'sri lankan pop 90s': ('Sri Lankan Pop/Rock', 'sri lankan pop 90s'),
    'sri lankan pop 2000s': ('Sri Lankan Pop/Rock', 'sri lankan pop 2000s'),
    'sri lankan pop 2010s': ('Sri Lankan Pop/Rock', 'sri lankan pop 2010s'),
    'classic sri lankan pop': ('Sri Lankan Pop/Rock', 'classic sri lankan pop'),

    ###############################################################################
    # Burmese Pop/Rock (Regional - Myanmar)
    ###############################################################################
    ## Burmese Pop General (English / Burmese)
    'burmese pop': ('Burmese Pop/Rock', 'burmese pop'),
    'myanmar pop': ('Burmese Pop/Rock', 'myanmar pop'),
    'pop birmano': ('Burmese Pop/Rock', 'pop birmano'),
    'yangon pop': ('Burmese Pop/Rock', 'yangon pop'),
    'myanma thachin': ('Burmese Pop/Rock', 'myanma thachin'),

    ## Burmese pop moderno
    'modern burmese pop': ('Burmese Pop/Rock', 'modern burmese pop'),
    'contemporary myanmar pop': ('Burmese Pop/Rock', 'contemporary myanmar pop'),
    'myanmar pop post coup': ('Burmese Pop/Rock', 'myanmar pop post coup'),

    ## Burmese rock
    'burmese rock': ('Burmese Pop/Rock', 'burmese rock'),
    'myanmar rock': ('Burmese Pop/Rock', 'myanmar rock'),
    'yangon rock': ('Burmese Pop/Rock', 'yangon rock'),

    ### Subgéneros de Burmese rock
    'burmese alternative rock': ('Burmese Pop/Rock', 'burmese alternative rock'),
    'burmese indie rock': ('Burmese Pop/Rock', 'burmese indie rock'),
    'burmese metal': ('Burmese Pop/Rock', 'burmese metal'),
    'burmese punk': ('Burmese Pop/Rock', 'burmese punk'),

    ## Burmese hip hop / Rap
    'burmese hip hop': ('Burmese Pop/Rock', 'burmese hip hop'),
    'burmese rap': ('Burmese Pop/Rock', 'burmese rap'),
    'yangon rap': ('Burmese Pop/Rock', 'yangon rap'),
    'myanmar rap': ('Burmese Pop/Rock', 'myanmar rap'),

    ## Burmese R&B
    'burmese r&b': ('Burmese Pop/Rock', 'burmese r&b'),
    'burmese rnb': ('Burmese Pop/Rock', 'burmese rnb'),

    ## Música tradicional fusionada
    'burmese folk': ('Burmese Pop/Rock', 'burmese folk'),
    'myanmar traditional': ('Burmese Pop/Rock', 'myanmar traditional'),
    'mahagita': ('Burmese Pop/Rock', 'mahagita'),
    'yodaya': ('Burmese Pop/Rock', 'yodaya'),
    'mandat': ('Burmese Pop/Rock', 'mandat'),

    ## Burmese fusion
    'burmese fusion': ('Burmese Pop/Rock', 'burmese fusion'),
    'myanmar fusion': ('Burmese Pop/Rock', 'myanmar fusion'),

    ## Burmese pop por región
    'yangon pop': ('Burmese Pop/Rock', 'yangon pop'),
    'mandalay pop': ('Burmese Pop/Rock', 'mandalay pop'),
    'naypyidaw pop': ('Burmese Pop/Rock', 'naypyidaw pop'),

    ## Burmese OST
    'burmese ost': ('Burmese Pop/Rock', 'burmese ost'),
    'myanmar movie songs': ('Burmese Pop/Rock', 'myanmar movie songs'),

    ## Burmese pop por épocas
    'burmese pop 80s': ('Burmese Pop/Rock', 'burmese pop 80s'),
    'burmese pop 90s': ('Burmese Pop/Rock', 'burmese pop 90s'),
    'burmese pop 2000s': ('Burmese Pop/Rock', 'burmese pop 2000s'),
    'burmese pop 2010s': ('Burmese Pop/Rock', 'burmese pop 2010s'),
    'classic burmese pop': ('Burmese Pop/Rock', 'classic burmese pop'),

    ###############################################################################
    # Lao Pop/Rock (Regional - Laos)
    ###############################################################################
    ## Lao Pop General (English / Lao)
    'lao pop': ('Lao Pop/Rock', 'lao pop'),
    'laos pop': ('Lao Pop/Rock', 'laos pop'),
    'pop laosiano': ('Lao Pop/Rock', 'pop laosiano'),
    'vientiane pop': ('Lao Pop/Rock', 'vientiane pop'),
    'phleng lao': ('Lao Pop/Rock', 'phleng lao'),

    ## Mor Lam (género principal)
    'mor lam': ('Lao Pop/Rock', 'mor lam'),
    'molam': ('Lao Pop/Rock', 'molam'),
    'lam lao': ('Lao Pop/Rock', 'lam lao'),
    'mor lam sing': ('Lao Pop/Rock', 'mor lam sing'),
    'mor lam tradicional': ('Lao Pop/Rock', 'mor lam tradicional'),
    'lam saravane': ('Lao Pop/Rock', 'lam saravane'),
    'lam luang': ('Lao Pop/Rock', 'lam luang'),

    ## Lao pop moderno / Fusión
    'lao modern pop': ('Lao Pop/Rock', 'lao modern pop'),
    'contemporary lao pop': ('Lao Pop/Rock', 'contemporary lao pop'),
    'mor lam pop': ('Lao Pop/Rock', 'mor lam pop'),
    'mor lam fusion': ('Lao Pop/Rock', 'mor lam fusion'),

    ## Lao rock
    'lao rock': ('Lao Pop/Rock', 'lao rock'),
    'vientiane rock': ('Lao Pop/Rock', 'vientiane rock'),
    'rock laosiano': ('Lao Pop/Rock', 'rock laosiano'),

    ### Subgéneros de Lao rock
    'lao alternative rock': ('Lao Pop/Rock', 'lao alternative rock'),
    'lao indie rock': ('Lao Pop/Rock', 'lao indie rock'),
    'lao metal': ('Lao Pop/Rock', 'lao metal'),
    'lao punk': ('Lao Pop/Rock', 'lao punk'),

    ## Lao hip hop / Rap
    'lao hip hop': ('Lao Pop/Rock', 'lao hip hop'),
    'lao rap': ('Lao Pop/Rock', 'lao rap'),
    'vientiane rap': ('Lao Pop/Rock', 'vientiane rap'),

    ## Lao folk / Tradicional
    'lao folk': ('Lao Pop/Rock', 'lao folk'),
    'lao traditional': ('Lao Pop/Rock', 'lao traditional'),
    'khene fusion': ('Lao Pop/Rock', 'khene fusion'),

    ## Lao fusion
    'lao fusion': ('Lao Pop/Rock', 'lao fusion'),

    ## Lao pop por región
    'vientiane pop': ('Lao Pop/Rock', 'vientiane pop'),
    'luang prabang pop': ('Lao Pop/Rock', 'luang prabang pop'),
    'pakse pop': ('Lao Pop/Rock', 'pakse pop'),
    'savannakhet pop': ('Lao Pop/Rock', 'savannakhet pop'),

    ## Lao OST
    'lao ost': ('Lao Pop/Rock', 'lao ost'),
    'lao movie songs': ('Lao Pop/Rock', 'lao movie songs'),

    ## Lao pop por épocas
    'lao pop 80s': ('Lao Pop/Rock', 'lao pop 80s'),
    'lao pop 90s': ('Lao Pop/Rock', 'lao pop 90s'),
    'lao pop 2000s': ('Lao Pop/Rock', 'lao pop 2000s'),
    'lao pop 2010s': ('Lao Pop/Rock', 'lao pop 2010s'),
    'lao pop 2020s': ('Lao Pop/Rock', 'lao pop 2020s'),

    ###############################################################################
    # Cambodian Pop/Rock (Regional - Camboya)
    ###############################################################################
    ## Cambodian Pop General (English / Khmer)
    'cambodian pop': ('Cambodian Pop/Rock', 'cambodian pop'),
    'khmer pop': ('Cambodian Pop/Rock', 'khmer pop'),
    'pop camboyano': ('Cambodian Pop/Rock', 'pop camboyano'),
    'phnom penh pop': ('Cambodian Pop/Rock', 'phnom penh pop'),
    'phleng khmer': ('Cambodian Pop/Rock', 'phleng khmer'),

    ## Cambodian rock clásico (60s-70s)
    'khmer rock': ('Cambodian Pop/Rock', 'khmer rock'),
    'cambodian rock': ('Cambodian Pop/Rock', 'cambodian rock'),
    'khmer psychedelic': ('Cambodian Pop/Rock', 'khmer psychedelic'),
    'cambodian garage rock': ('Cambodian Pop/Rock', 'cambodian garage rock'),
    'khmer surf rock': ('Cambodian Pop/Rock', 'khmer surf rock'),
    'cambodian rock and roll': ('Cambodian Pop/Rock', 'cambodian rock and roll'),

    ## Cambodian pop moderno
    'modern cambodian pop': ('Cambodian Pop/Rock', 'modern cambodian pop'),
    'contemporary khmer pop': ('Cambodian Pop/Rock', 'contemporary khmer pop'),
    'khmer pop moderno': ('Cambodian Pop/Rock', 'khmer pop moderno'),

    ## Cambodian rock contemporáneo
    'cambodian modern rock': ('Cambodian Pop/Rock', 'cambodian modern rock'),
    'phnom penh rock': ('Cambodian Pop/Rock', 'phnom penh rock'),

    ### Subgéneros de Cambodian rock
    'cambodian alternative rock': ('Cambodian Pop/Rock', 'cambodian alternative rock'),
    'cambodian indie rock': ('Cambodian Pop/Rock', 'cambodian indie rock'),
    'cambodian metal': ('Cambodian Pop/Rock', 'cambodian metal'),
    'cambodian punk': ('Cambodian Pop/Rock', 'cambodian punk'),

    ## Cambodian hip hop / Rap
    'cambodian hip hop': ('Cambodian Pop/Rock', 'cambodian hip hop'),
    'khmer rap': ('Cambodian Pop/Rock', 'khmer rap'),
    'phnom penh rap': ('Cambodian Pop/Rock', 'phnom penh rap'),

    ## Cambodian R&B
    'cambodian r&b': ('Cambodian Pop/Rock', 'cambodian r&b'),
    'khmer rnb': ('Cambodian Pop/Rock', 'khmer rnb'),

    ## Música tradicional fusionada
    'cambodian folk': ('Cambodian Pop/Rock', 'cambodian folk'),
    'khmer traditional': ('Cambodian Pop/Rock', 'khmer traditional'),
    'pin peat': ('Cambodian Pop/Rock', 'pin peat'),
    'khmer classical': ('Cambodian Pop/Rock', 'khmer classical'),
    'chapei': ('Cambodian Pop/Rock', 'chapei'),
    'chapei fusion': ('Cambodian Pop/Rock', 'chapei fusion'),
    'bhakti fusion': ('Cambodian Pop/Rock', 'bhakti fusion'),

    ## Cambodian fusion
    'cambodian fusion': ('Cambodian Pop/Rock', 'cambodian fusion'),
    'khmer fusion': ('Cambodian Pop/Rock', 'khmer fusion'),

    ## Cambodian pop por región
    'phnom penh pop': ('Cambodian Pop/Rock', 'phnom penh pop'),
    'siem reap pop': ('Cambodian Pop/Rock', 'siem reap pop'),
    'battambang pop': ('Cambodian Pop/Rock', 'battambang pop'),

    ## Cambodian OST
    'cambodian ost': ('Cambodian Pop/Rock', 'cambodian ost'),
    'khmer movie songs': ('Cambodian Pop/Rock', 'khmer movie songs'),

    ## Cambodian pop por épocas
    'khmer pop 60s': ('Cambodian Pop/Rock', 'khmer pop 60s'),
    'khmer pop 70s': ('Cambodian Pop/Rock', 'khmer pop 70s'),
    'khmer pop 80s': ('Cambodian Pop/Rock', 'khmer pop 80s'),
    'khmer pop 90s': ('Cambodian Pop/Rock', 'khmer pop 90s'),
    'khmer pop 2000s': ('Cambodian Pop/Rock', 'khmer pop 2000s'),
    'khmer pop 2010s': ('Cambodian Pop/Rock', 'khmer pop 2010s'),
    'khmer pop 2020s': ('Cambodian Pop/Rock', 'khmer pop 2020s'),

    ###############################################################################
    # Hmong Pop/Rock (Regional - Hmong / Diáspora)
    ###############################################################################
    ## Hmong Pop General (English / Hmong)
    'hmong pop': ('Hmong Pop/Rock', 'hmong pop'),
    'hmong music': ('Hmong Pop/Rock', 'hmong music'),
    'pop hmong': ('Hmong Pop/Rock', 'pop hmong'),
    'hmong nkauj': ('Hmong Pop/Rock', 'hmong nkauj'),

    ## Hmong pop moderno / Diáspora
    'hmong diaspora pop': ('Hmong Pop/Rock', 'hmong diaspora pop'),
    'modern hmong pop': ('Hmong Pop/Rock', 'modern hmong pop'),
    'contemporary hmong music': ('Hmong Pop/Rock', 'contemporary hmong music'),
    'hmong american pop': ('Hmong Pop/Rock', 'hmong american pop'),
    'hmong laos pop': ('Hmong Pop/Rock', 'hmong laos pop'),
    'hmong vietnam pop': ('Hmong Pop/Rock', 'hmong vietnam pop'),
    'hmong thailand pop': ('Hmong Pop/Rock', 'hmong thailand pop'),
    'hmong china pop': ('Hmong Pop/Rock', 'hmong china pop'),

    ## Hmong rock
    'hmong rock': ('Hmong Pop/Rock', 'hmong rock'),
    'hmong rock band': ('Hmong Pop/Rock', 'hmong rock band'),

    ### Subgéneros de Hmong rock
    'hmong alternative rock': ('Hmong Pop/Rock', 'hmong alternative rock'),
    'hmong indie rock': ('Hmong Pop/Rock', 'hmong indie rock'),
    'hmong metal': ('Hmong Pop/Rock', 'hmong metal'),
    'hmong punk': ('Hmong Pop/Rock', 'hmong punk'),

    ## Hmong hip hop / Rap
    'hmong hip hop': ('Hmong Pop/Rock', 'hmong hip hop'),
    'hmong rap': ('Hmong Pop/Rock', 'hmong rap'),
    'hmong american rap': ('Hmong Pop/Rock', 'hmong american rap'),

    ## Hmong R&B
    'hmong r&b': ('Hmong Pop/Rock', 'hmong r&b'),
    'hmong rnb': ('Hmong Pop/Rock', 'hmong rnb'),

    ## Hmong gospel
    'hmong gospel': ('Hmong Pop/Rock', 'hmong gospel'),
    'hmong christian music': ('Hmong Pop/Rock', 'hmong christian music'),

    ## Música tradicional fusionada
    'hmong folk': ('Hmong Pop/Rock', 'hmong folk'),
    'hmong traditional': ('Hmong Pop/Rock', 'hmong traditional'),
    'kwv txhiaj': ('Hmong Pop/Rock', 'kwv txhiaj'),
    'qeej fusion': ('Hmong Pop/Rock', 'qeej fusion'),
    'ncas fusion': ('Hmong Pop/Rock', 'ncas fusion'),

    ## Hmong fusion
    'hmong fusion': ('Hmong Pop/Rock', 'hmong fusion'),

    ## Hmong pop por región (diáspora)
    'minnesota hmong pop': ('Hmong Pop/Rock', 'minnesota hmong pop'),
    'california hmong pop': ('Hmong Pop/Rock', 'california hmong pop'),
    'wisconsin hmong pop': ('Hmong Pop/Rock', 'wisconsin hmong pop'),
    'fresno hmong pop': ('Hmong Pop/Rock', 'fresno hmong pop'),

    ## Hmong pop por épocas
    'hmong pop 80s': ('Hmong Pop/Rock', 'hmong pop 80s'),
    'hmong pop 90s': ('Hmong Pop/Rock', 'hmong pop 90s'),
    'hmong pop 2000s': ('Hmong Pop/Rock', 'hmong pop 2000s'),
    'hmong pop 2010s': ('Hmong Pop/Rock', 'hmong pop 2010s'),
    'hmong pop 2020s': ('Hmong Pop/Rock', 'hmong pop 2020s'),

    ###############################################################################
    # Kurdish Pop/Rock (Regional - Kurdistán / Diáspora)
    ###############################################################################
    ## Kurdish Pop General (English / Kurdish)
    'kurdish pop': ('Kurdish Pop/Rock', 'kurdish pop'),
    'kurdî pop': ('Kurdish Pop/Rock', 'kurdî pop'),
    'pop kurdo': ('Kurdish Pop/Rock', 'pop kurdo'),
    'muzîka kurdî': ('Kurdish Pop/Rock', 'muzîka kurdî'),
    'strana kurdî': ('Kurdish Pop/Rock', 'strana kurdî'),

    ## Kurdish pop moderno / Diáspora
    'kurdish diaspora pop': ('Kurdish Pop/Rock', 'kurdish diaspora pop'),
    'modern kurdish pop': ('Kurdish Pop/Rock', 'modern kurdish pop'),
    'contemporary kurdish music': ('Kurdish Pop/Rock', 'contemporary kurdish music'),

    ## Kurdish rock
    'kurdish rock': ('Kurdish Pop/Rock', 'kurdish rock'),
    'kurdî rock': ('Kurdish Pop/Rock', 'kurdî rock'),
    'rock kurdo': ('Kurdish Pop/Rock', 'rock kurdo'),

    ### Subgéneros de Kurdish rock
    'kurdish alternative rock': ('Kurdish Pop/Rock', 'kurdish alternative rock'),
    'kurdish indie rock': ('Kurdish Pop/Rock', 'kurdish indie rock'),
    'kurdish metal': ('Kurdish Pop/Rock', 'kurdish metal'),
    'kurdish punk': ('Kurdish Pop/Rock', 'kurdish punk'),

    ## Kurdish hip hop / Rap
    'kurdish hip hop': ('Kurdish Pop/Rock', 'kurdish hip hop'),
    'kurdish rap': ('Kurdish Pop/Rock', 'kurdish rap'),
    'rap kurdî': ('Kurdish Pop/Rock', 'rap kurdî'),

    ## Kurdish R&B
    'kurdish r&b': ('Kurdish Pop/Rock', 'kurdish r&b'),
    'kurdish rnb': ('Kurdish Pop/Rock', 'kurdish rnb'),

    ## Música tradicional fusionada
    'kurdish folk': ('Kurdish Pop/Rock', 'kurdish folk'),
    'folk kurdo': ('Kurdish Pop/Rock', 'folk kurdo'),
    'dengbêj fusion': ('Kurdish Pop/Rock', 'dengbêj fusion'),
    'saz fusion': ('Kurdish Pop/Rock', 'saz fusion'),
    'temir fusion': ('Kurdish Pop/Rock', 'temir fusion'),
    'def fusion': ('Kurdish Pop/Rock', 'def fusion'),

    ## Kurdish fusion
    'kurdish fusion': ('Kurdish Pop/Rock', 'kurdish fusion'),

    ## Kurdish pop por región
    'bakur pop': ('Kurdish Pop/Rock', 'bakur pop'),          # Norte (Turquía)
    'bashur pop': ('Kurdish Pop/Rock', 'bashur pop'),        # Sur (Irak)
    'rojhilat pop': ('Kurdish Pop/Rock', 'rojhilat pop'),    # Este (Irán)
    'rojava pop': ('Kurdish Pop/Rock', 'rojava pop'),        # Oeste (Siria)
    'diyarbakir pop': ('Kurdish Pop/Rock', 'diyarbakir pop'),
    'sulaymaniyah pop': ('Kurdish Pop/Rock', 'sulaymaniyah pop'),
    'erbil pop': ('Kurdish Pop/Rock', 'erbil pop'),
    'kermanshah pop': ('Kurdish Pop/Rock', 'kermanshah pop'),

    ## Kurdish OST
    'kurdish ost': ('Kurdish Pop/Rock', 'kurdish ost'),
    'kurdish film music': ('Kurdish Pop/Rock', 'kurdish film music'),

    ## Kurdish pop por épocas
    'kurdish pop 80s': ('Kurdish Pop/Rock', 'kurdish pop 80s'),
    'kurdish pop 90s': ('Kurdish Pop/Rock', 'kurdish pop 90s'),
    'kurdish pop 2000s': ('Kurdish Pop/Rock', 'kurdish pop 2000s'),
    'kurdish pop 2010s': ('Kurdish Pop/Rock', 'kurdish pop 2010s'),
    'kurdish pop 2020s': ('Kurdish Pop/Rock', 'kurdish pop 2020s'),
    'classic kurdish pop': ('Kurdish Pop/Rock', 'classic kurdish pop'),

    ###############################################################################
    # Balochi Pop/Rock (Regional - Baluchistán / Pakistán/Irán/Omán)
    ###############################################################################
    ## Balochi Pop General (English / Balochi)
    'balochi pop': ('Balochi Pop/Rock', 'balochi pop'),
    'baluchi pop': ('Balochi Pop/Rock', 'baluchi pop'),
    'pop balochi': ('Balochi Pop/Rock', 'pop balochi'),
    'balochi music': ('Balochi Pop/Rock', 'balochi music'),
    'بلوچی موسیقی': ('Balochi Pop/Rock', 'بلوچی موسیقی'),  # romanizado: 'balochi musiqi'

    ## Balochi pop moderno / Diáspora
    'balochi diaspora pop': ('Balochi Pop/Rock', 'balochi diaspora pop'),
    'modern balochi pop': ('Balochi Pop/Rock', 'modern balochi pop'),
    'contemporary balochi music': ('Balochi Pop/Rock', 'contemporary balochi music'),

    ## Balochi rock
    'balochi rock': ('Balochi Pop/Rock', 'balochi rock'),
    'baluchi rock': ('Balochi Pop/Rock', 'baluchi rock'),
    'rock balochi': ('Balochi Pop/Rock', 'rock balochi'),

    ### Subgéneros de Balochi rock
    'balochi alternative rock': ('Balochi Pop/Rock', 'balochi alternative rock'),
    'balochi indie rock': ('Balochi Pop/Rock', 'balochi indie rock'),
    'balochi metal': ('Balochi Pop/Rock', 'balochi metal'),

    ## Balochi hip hop / Rap
    'balochi hip hop': ('Balochi Pop/Rock', 'balochi hip hop'),
    'balochi rap': ('Balochi Pop/Rock', 'balochi rap'),
    'baluchi rap': ('Balochi Pop/Rock', 'baluchi rap'),

    ## Balochi R&B
    'balochi r&b': ('Balochi Pop/Rock', 'balochi r&b'),
    'balochi rnb': ('Balochi Pop/Rock', 'balochi rnb'),

    ## Música tradicional fusionada
    'balochi folk': ('Balochi Pop/Rock', 'balochi folk'),
    'folk balochi': ('Balochi Pop/Rock', 'folk balochi'),
    'suroz fusion': ('Balochi Pop/Rock', 'suroz fusion'),
    'benju fusion': ('Balochi Pop/Rock', 'benju fusion'),
    'dohol fusion': ('Balochi Pop/Rock', 'dohol fusion'),
    'nal fusion': ('Balochi Pop/Rock', 'nal fusion'),

    ## Balochi fusion
    'balochi fusion': ('Balochi Pop/Rock', 'balochi fusion'),

    ## Balochi pop por región
    'makran pop': ('Balochi Pop/Rock', 'makran pop'),
    'sistan pop': ('Balochi Pop/Rock', 'sistan pop'),
    'turbat pop': ('Balochi Pop/Rock', 'turbat pop'),
    'quetta pop': ('Balochi Pop/Rock', 'quetta pop'),
    'gwadar pop': ('Balochi Pop/Rock', 'gwadar pop'),
    'iranian balochi pop': ('Balochi Pop/Rock', 'iranian balochi pop'),
    'omani balochi pop': ('Balochi Pop/Rock', 'omani balochi pop'),

    ## Balochi OST
    'balochi ost': ('Balochi Pop/Rock', 'balochi ost'),
    'balochi film music': ('Balochi Pop/Rock', 'balochi film music'),

    ## Balochi pop por épocas
    'balochi pop 80s': ('Balochi Pop/Rock', 'balochi pop 80s'),
    'balochi pop 90s': ('Balochi Pop/Rock', 'balochi pop 90s'),
    'balochi pop 2000s': ('Balochi Pop/Rock', 'balochi pop 2000s'),
    'balochi pop 2010s': ('Balochi Pop/Rock', 'balochi pop 2010s'),
    'balochi pop 2020s': ('Balochi Pop/Rock', 'balochi pop 2020s'),
    'classic balochi pop': ('Balochi Pop/Rock', 'classic balochi pop'),

    ###############################################################################
    # Kashmiri Pop/Rock (Regional - Cachemira / India/Pakistán)
    ###############################################################################
    ## Kashmiri Pop General (English / Kashmiri)
    'kashmiri pop': ('Kashmiri Pop/Rock', 'kashmiri pop'),
    'koshur pop': ('Kashmiri Pop/Rock', 'koshur pop'),
    'pop cachemiro': ('Kashmiri Pop/Rock', 'pop cachemiro'),
    'کٲشُر پاپ': ('Kashmiri Pop/Rock', 'کٲشُر پاپ'),

    ## Kashmiri pop moderno / Diáspora
    'kashmiri diaspora pop': ('Kashmiri Pop/Rock', 'kashmiri diaspora pop'),
    'modern kashmiri pop': ('Kashmiri Pop/Rock', 'modern kashmiri pop'),
    'contemporary kashmiri music': ('Kashmiri Pop/Rock', 'contemporary kashmiri music'),

    ## Kashmiri rock
    'kashmiri rock': ('Kashmiri Pop/Rock', 'kashmiri rock'),
    'koshur rock': ('Kashmiri Pop/Rock', 'koshur rock'),
    'rock cachemiro': ('Kashmiri Pop/Rock', 'rock cachemiro'),

    ### Subgéneros de Kashmiri rock
    'kashmiri alternative rock': ('Kashmiri Pop/Rock', 'kashmiri alternative rock'),
    'kashmiri indie rock': ('Kashmiri Pop/Rock', 'kashmiri indie rock'),
    'kashmiri metal': ('Kashmiri Pop/Rock', 'kashmiri metal'),

    ## Kashmiri hip hop / Rap
    'kashmiri hip hop': ('Kashmiri Pop/Rock', 'kashmiri hip hop'),
    'kashmiri rap': ('Kashmiri Pop/Rock', 'kashmiri rap'),

    ## Kashmiri R&B
    'kashmiri r&b': ('Kashmiri Pop/Rock', 'kashmiri r&b'),
    'kashmiri rnb': ('Kashmiri Pop/Rock', 'kashmiri rnb'),

    ## Música tradicional fusionada (Sufí, Chakri, Rouf)
    'kashmiri folk': ('Kashmiri Pop/Rock', 'kashmiri folk'),
    'kashmiri sufí pop': ('Kashmiri Pop/Rock', 'kashmiri sufí pop'),
    'sufi kashmir': ('Kashmiri Pop/Rock', 'sufi kashmir'),
    'chakri fusion': ('Kashmiri Pop/Rock', 'chakri fusion'),
    'rouf fusion': ('Kashmiri Pop/Rock', 'rouf fusion'),
    'wany fusion': ('Kashmiri Pop/Rock', 'wany fusion'),

    ## Kashmiri fusion
    'kashmiri fusion': ('Kashmiri Pop/Rock', 'kashmiri fusion'),
    'kashmir fusion': ('Kashmiri Pop/Rock', 'kashmir fusion'),

    ## Kashmiri pop por región
    'srinagar pop': ('Kashmiri Pop/Rock', 'srinagar pop'),
    'muzaffarabad pop': ('Kashmiri Pop/Rock', 'muzaffarabad pop'),
    'kashmir valley pop': ('Kashmiri Pop/Rock', 'kashmir valley pop'),
    'jammu pop': ('Kashmiri Pop/Rock', 'jammu pop'),

    ## Kashmiri OST
    'kashmiri ost': ('Kashmiri Pop/Rock', 'kashmiri ost'),
    'kashmiri film music': ('Kashmiri Pop/Rock', 'kashmiri film music'),

    ## Kashmiri pop por épocas
    'kashmiri pop 80s': ('Kashmiri Pop/Rock', 'kashmiri pop 80s'),
    'kashmiri pop 90s': ('Kashmiri Pop/Rock', 'kashmiri pop 90s'),
    'kashmiri pop 2000s': ('Kashmiri Pop/Rock', 'kashmiri pop 2000s'),
    'kashmiri pop 2010s': ('Kashmiri Pop/Rock', 'kashmiri pop 2010s'),
    'kashmiri pop 2020s': ('Kashmiri Pop/Rock', 'kashmiri pop 2020s'),
    'classic kashmiri pop': ('Kashmiri Pop/Rock', 'classic kashmiri pop'),

    ###############################################################################
    # Northeast Indian Pop/Rock (Regional - Nagaland, Manipur, Mizoram, etc.)
    ###############################################################################
    ## Northeast Indian Pop General (English)
    'northeast indian pop': ('Northeast Indian Pop/Rock', 'northeast indian pop'),
    'north east india music': ('Northeast Indian Pop/Rock', 'north east india music'),
    'pop del noreste indio': ('Northeast Indian Pop/Rock', 'pop del noreste indio'),

    ## Naga Pop / Rock
    'naga pop': ('Northeast Indian Pop/Rock', 'naga pop'),
    'naga rock': ('Northeast Indian Pop/Rock', 'naga rock'),
    'naga metal': ('Northeast Indian Pop/Rock', 'naga metal'),
    'naga fusion': ('Northeast Indian Pop/Rock', 'naga fusion'),
    'the naga music': ('Northeast Indian Pop/Rock', 'the naga music'),

    ## Mizo Pop / Rock
    'mizo pop': ('Northeast Indian Pop/Rock', 'mizo pop'),
    'mizo rock': ('Northeast Indian Pop/Rock', 'mizo rock'),
    'mizo gospel': ('Northeast Indian Pop/Rock', 'mizo gospel'),
    'mizo fusion': ('Northeast Indian Pop/Rock', 'mizo fusion'),

    ## Manipuri Pop / Rock
    'manipuri pop': ('Northeast Indian Pop/Rock', 'manipuri pop'),
    'manipuri rock': ('Northeast Indian Pop/Rock', 'manipuri rock'),
    'manipuri fusion': ('Northeast Indian Pop/Rock', 'manipuri fusion'),
    'sankirtan fusion': ('Northeast Indian Pop/Rock', 'sankirtan fusion'),

    ## Khasi Pop / Rock
    'khasi pop': ('Northeast Indian Pop/Rock', 'khasi pop'),
    'khasi rock': ('Northeast Indian Pop/Rock', 'khasi rock'),

    ## Garo Pop / Rock
    'garo pop': ('Northeast Indian Pop/Rock', 'garo pop'),
    'garo rock': ('Northeast Indian Pop/Rock', 'garo rock'),

    ## Arunachali / Sikkimese
    'arunachali pop': ('Northeast Indian Pop/Rock', 'arunachali pop'),
    'sikkimese pop': ('Northeast Indian Pop/Rock', 'sikkimese pop'),

    ## Northeast Indian hip hop / Rap
    'northeast indian hip hop': ('Northeast Indian Pop/Rock', 'northeast indian hip hop'),
    'northeast indian rap': ('Northeast Indian Pop/Rock', 'northeast indian rap'),
    'naga rap': ('Northeast Indian Pop/Rock', 'naga rap'),
    'mizo rap': ('Northeast Indian Pop/Rock', 'mizo rap'),

    ## Northeast Indian R&B
    'northeast indian r&b': ('Northeast Indian Pop/Rock', 'northeast indian r&b'),

    ## Northeast Indian fusion
    'northeast indian fusion': ('Northeast Indian Pop/Rock', 'northeast indian fusion'),

    ## Northeast Indian pop por región
    'kohima pop': ('Northeast Indian Pop/Rock', 'kohima pop'),
    'dimapur pop': ('Northeast Indian Pop/Rock', 'dimapur pop'),
    'aizawl pop': ('Northeast Indian Pop/Rock', 'aizawl pop'),
    'imphal pop': ('Northeast Indian Pop/Rock', 'imphal pop'),
    'shillong pop': ('Northeast Indian Pop/Rock', 'shillong pop'),
    'gangtok pop': ('Northeast Indian Pop/Rock', 'gangtok pop'),
    'itanagar pop': ('Northeast Indian Pop/Rock', 'itanagar pop'),

    ## Northeast Indian OST
    'northeast indian ost': ('Northeast Indian Pop/Rock', 'northeast indian ost'),
    'northeast indian film music': ('Northeast Indian Pop/Rock', 'northeast indian film music'),

    ## Northeast Indian pop por épocas
    'northeast indian pop 80s': ('Northeast Indian Pop/Rock', 'northeast indian pop 80s'),
    'northeast indian pop 90s': ('Northeast Indian Pop/Rock', 'northeast indian pop 90s'),
    'northeast indian pop 2000s': ('Northeast Indian Pop/Rock', 'northeast indian pop 2000s'),
    'northeast indian pop 2010s': ('Northeast Indian Pop/Rock', 'northeast indian pop 2010s'),
    'northeast indian pop 2020s': ('Northeast Indian Pop/Rock', 'northeast indian pop 2020s'),
    'classic northeast indian pop': ('Northeast Indian Pop/Rock', 'classic northeast indian pop'),

    ###############################################################################
    # Maldivian Pop/Rock (Regional - Maldivas)
    ###############################################################################
    ## Maldivian Pop General (English / Dhivehi)
    'maldivian pop': ('Maldivian Pop/Rock', 'maldivian pop'),
    'dhivehi pop': ('Maldivian Pop/Rock', 'dhivehi pop'),
    'pop maldivo': ('Maldivian Pop/Rock', 'pop maldivo'),
    'ދިވެހި ޕޮޕް': ('Maldivian Pop/Rock', 'ދިވެހި ޕޮޕް'),

    ## Maldivian pop moderno
    'modern maldivian pop': ('Maldivian Pop/Rock', 'modern maldivian pop'),
    'contemporary dhivehi pop': ('Maldivian Pop/Rock', 'contemporary dhivehi pop'),

    ## Maldivian rock
    'maldivian rock': ('Maldivian Pop/Rock', 'maldivian rock'),
    'dhivehi rock': ('Maldivian Pop/Rock', 'dhivehi rock'),

    ### Subgéneros de Maldivian rock
    'maldivian alternative rock': ('Maldivian Pop/Rock', 'maldivian alternative rock'),
    'maldivian indie rock': ('Maldivian Pop/Rock', 'maldivian indie rock'),
    'maldivian metal': ('Maldivian Pop/Rock', 'maldivian metal'),
    'maldivian punk': ('Maldivian Pop/Rock', 'maldivian punk'),

    ## Maldivian hip hop / Rap
    'maldivian hip hop': ('Maldivian Pop/Rock', 'maldivian hip hop'),
    'maldivian rap': ('Maldivian Pop/Rock', 'maldivian rap'),
    'dhivehi rap': ('Maldivian Pop/Rock', 'dhivehi rap'),

    ## Maldivian R&B
    'maldivian r&b': ('Maldivian Pop/Rock', 'maldivian r&b'),
    'maldivian rnb': ('Maldivian Pop/Rock', 'maldivian rnb'),

    ## Música tradicional fusionada
    'maldivian folk': ('Maldivian Pop/Rock', 'maldivian folk'),
    'boduberu fusion': ('Maldivian Pop/Rock', 'boduberu fusion'),
    'raivaru pop': ('Maldivian Pop/Rock', 'raivaru pop'),
    'thara fusion': ('Maldivian Pop/Rock', 'thara fusion'),
    'gaa odi fusion': ('Maldivian Pop/Rock', 'gaa odi fusion'),

    ## Maldivian fusion
    'maldivian fusion': ('Maldivian Pop/Rock', 'maldivian fusion'),

    ## Maldivian pop por región
    'male pop': ('Maldivian Pop/Rock', 'male pop'),
    'addu pop': ('Maldivian Pop/Rock', 'addu pop'),
    'fuvahmulah pop': ('Maldivian Pop/Rock', 'fuvahmulah pop'),

    ## Maldivian OST
    'maldivian ost': ('Maldivian Pop/Rock', 'maldivian ost'),
    'dhivehi film music': ('Maldivian Pop/Rock', 'dhivehi film music'),

    ## Maldivian pop por épocas
    'maldivian pop 80s': ('Maldivian Pop/Rock', 'maldivian pop 80s'),
    'maldivian pop 90s': ('Maldivian Pop/Rock', 'maldivian pop 90s'),
    'maldivian pop 2000s': ('Maldivian Pop/Rock', 'maldivian pop 2000s'),
    'maldivian pop 2010s': ('Maldivian Pop/Rock', 'maldivian pop 2010s'),
    'maldivian pop 2020s': ('Maldivian Pop/Rock', 'maldivian pop 2020s'),
    'classic maldivian pop': ('Maldivian Pop/Rock', 'classic maldivian pop'),

    ###############################################################################
    # Bhutanese Pop/Rock (Regional - Bután)
    ###############################################################################
    ## Bhutanese Pop General (English / Dzongkha)
    'bhutanese pop': ('Bhutanese Pop/Rock', 'bhutanese pop'),
    'bhutan pop': ('Bhutanese Pop/Rock', 'bhutan pop'),
    'pop butanés': ('Bhutanese Pop/Rock', 'pop butanés'),
    'rigsar': ('Bhutanese Pop/Rock', 'rigsar'),
    'རིགས་གསར།': ('Bhutanese Pop/Rock', 'རིགས་གསར།'),

    ## Rigsar (género principal)
    'rigsar pop': ('Bhutanese Pop/Rock', 'rigsar pop'),
    'rigsar rock': ('Bhutanese Pop/Rock', 'rigsar rock'),
    'modern rigsar': ('Bhutanese Pop/Rock', 'modern rigsar'),

    ## Bhutanese rock
    'bhutanese rock': ('Bhutanese Pop/Rock', 'bhutanese rock'),
    'rigsar rock': ('Bhutanese Pop/Rock', 'rigsar rock'),

    ### Subgéneros de Bhutanese rock
    'bhutanese alternative rock': ('Bhutanese Pop/Rock', 'bhutanese alternative rock'),
    'bhutanese indie rock': ('Bhutanese Pop/Rock', 'bhutanese indie rock'),
    'bhutanese metal': ('Bhutanese Pop/Rock', 'bhutanese metal'),

    ## Bhutanese hip hop / Rap
    'bhutanese hip hop': ('Bhutanese Pop/Rock', 'bhutanese hip hop'),
    'bhutanese rap': ('Bhutanese Pop/Rock', 'bhutanese rap'),
    'rigsar rap': ('Bhutanese Pop/Rock', 'rigsar rap'),

    ## Bhutanese R&B
    'bhutanese r&b': ('Bhutanese Pop/Rock', 'bhutanese r&b'),
    'bhutanese rnb': ('Bhutanese Pop/Rock', 'bhutanese rnb'),

    ## Música tradicional fusionada
    'bhutanese folk': ('Bhutanese Pop/Rock', 'bhutanese folk'),
    'zhungdra fusion': ('Bhutanese Pop/Rock', 'zhungdra fusion'),
    'boedra fusion': ('Bhutanese Pop/Rock', 'boedra fusion'),
    'sham fusion': ('Bhutanese Pop/Rock', 'sham fusion'),
    'dramyin fusion': ('Bhutanese Pop/Rock', 'dramyin fusion'),

    ## Bhutanese fusion
    'bhutanese fusion': ('Bhutanese Pop/Rock', 'bhutanese fusion'),

    ## Bhutanese pop por región
    'thimphu pop': ('Bhutanese Pop/Rock', 'thimphu pop'),
    'phuentsholing pop': ('Bhutanese Pop/Rock', 'phuentsholing pop'),
    'paro pop': ('Bhutanese Pop/Rock', 'paro pop'),

    ## Bhutanese OST
    'bhutanese ost': ('Bhutanese Pop/Rock', 'bhutanese ost'),
    'bhutanese film music': ('Bhutanese Pop/Rock', 'bhutanese film music'),

    ## Bhutanese pop por épocas
    'bhutanese pop 80s': ('Bhutanese Pop/Rock', 'bhutanese pop 80s'),
    'bhutanese pop 90s': ('Bhutanese Pop/Rock', 'bhutanese pop 90s'),
    'bhutanese pop 2000s': ('Bhutanese Pop/Rock', 'bhutanese pop 2000s'),
    'bhutanese pop 2010s': ('Bhutanese Pop/Rock', 'bhutanese pop 2010s'),
    'bhutanese pop 2020s': ('Bhutanese Pop/Rock', 'bhutanese pop 2020s'),
    'classic bhutanese pop': ('Bhutanese Pop/Rock', 'classic bhutanese pop'),

    ###############################################################################
    # Siberian Indigenous Pop/Rock (Regional - Yakutia, Tuvá, Buriatia, Jakasia)
    ###############################################################################
    ## Siberian Indigenous Pop General (English / Indigenous languages)
    'siberian indigenous pop': ('Siberian Indigenous Pop/Rock', 'siberian indigenous pop'),
    'siberian native music': ('Siberian Indigenous Pop/Rock', 'siberian native music'),
    'pop indígena siberiano': ('Siberian Indigenous Pop/Rock', 'pop indígena siberiano'),

    ## Yakut (Sakha) Pop / Rock
    'yakut pop': ('Siberian Indigenous Pop/Rock', 'yakut pop'),
    'sakha pop': ('Siberian Indigenous Pop/Rock', 'sakha pop'),
    'yakut rock': ('Siberian Indigenous Pop/Rock', 'yakut rock'),
    'sakha rock': ('Siberian Indigenous Pop/Rock', 'sakha rock'),
    'khomus fusion': ('Siberian Indigenous Pop/Rock', 'khomus fusion'),
    'yakut metal': ('Siberian Indigenous Pop/Rock', 'yakut metal'),
    'sakha hip hop': ('Siberian Indigenous Pop/Rock', 'sakha hip hop'),

    ## Tuvan Pop / Rock
    'tuvan pop': ('Siberian Indigenous Pop/Rock', 'tuvan pop'),
    'tyva pop': ('Siberian Indigenous Pop/Rock', 'tyva pop'),
    'tuvan rock': ('Siberian Indigenous Pop/Rock', 'tuvan rock'),
    'tyva rock': ('Siberian Indigenous Pop/Rock', 'tyva rock'),
    'khoomei rock': ('Siberian Indigenous Pop/Rock', 'khoomei rock'),
    'tuvan throat singing fusion': ('Siberian Indigenous Pop/Rock', 'tuvan throat singing fusion'),
    'tuvan metal': ('Siberian Indigenous Pop/Rock', 'tuvan metal'),

    ## Buryat Pop / Rock
    'buryat pop': ('Siberian Indigenous Pop/Rock', 'buryat pop'),
    'buryat rock': ('Siberian Indigenous Pop/Rock', 'buryat rock'),
    'buryat fusion': ('Siberian Indigenous Pop/Rock', 'buryat fusion'),
    'buryat folk': ('Siberian Indigenous Pop/Rock', 'buryat folk'),

    ## Khakass Pop / Rock
    'khakass pop': ('Siberian Indigenous Pop/Rock', 'khakass pop'),
    'khakass rock': ('Siberian Indigenous Pop/Rock', 'khakass rock'),
    'khakass fusion': ('Siberian Indigenous Pop/Rock', 'khakass fusion'),

    ## Otros grupos indígenas (Evenki, Chukchi, etc.)
    'evenki pop': ('Siberian Indigenous Pop/Rock', 'evenki pop'),
    'chukchi pop': ('Siberian Indigenous Pop/Rock', 'chukchi pop'),
    'nanai pop': ('Siberian Indigenous Pop/Rock', 'nanai pop'),
    'udyge pop': ('Siberian Indigenous Pop/Rock', 'udyge pop'),

    ## Siberian Indigenous hip hop / Rap
    'siberian indigenous hip hop': ('Siberian Indigenous Pop/Rock', 'siberian indigenous hip hop'),
    'siberian indigenous rap': ('Siberian Indigenous Pop/Rock', 'siberian indigenous rap'),
    'yakut rap': ('Siberian Indigenous Pop/Rock', 'yakut rap'),
    'tuvan rap': ('Siberian Indigenous Pop/Rock', 'tuvan rap'),
    'buryat rap': ('Siberian Indigenous Pop/Rock', 'buryat rap'),

    ## Siberian Indigenous fusion
    'siberian indigenous fusion': ('Siberian Indigenous Pop/Rock', 'siberian indigenous fusion'),
    'arctic fusion': ('Siberian Indigenous Pop/Rock', 'arctic fusion'),
    'taiga fusion': ('Siberian Indigenous Pop/Rock', 'taiga fusion'),

    ## Siberian Indigenous pop por región
    'yakutsk pop': ('Siberian Indigenous Pop/Rock', 'yakutsk pop'),
    'kyzyl pop': ('Siberian Indigenous Pop/Rock', 'kyzyl pop'),
    'ulan-ude pop': ('Siberian Indigenous Pop/Rock', 'ulan-ude pop'),
    'abakan pop': ('Siberian Indigenous Pop/Rock', 'abakan pop'),

    ## Siberian Indigenous OST
    'siberian indigenous ost': ('Siberian Indigenous Pop/Rock', 'siberian indigenous ost'),
    'siberian indigenous film music': ('Siberian Indigenous Pop/Rock', 'siberian indigenous film music'),

    ## Siberian Indigenous pop por épocas
    'siberian indigenous pop 80s': ('Siberian Indigenous Pop/Rock', 'siberian indigenous pop 80s'),
    'siberian indigenous pop 90s': ('Siberian Indigenous Pop/Rock', 'siberian indigenous pop 90s'),
    'siberian indigenous pop 2000s': ('Siberian Indigenous Pop/Rock', 'siberian indigenous pop 2000s'),
    'siberian indigenous pop 2010s': ('Siberian Indigenous Pop/Rock', 'siberian indigenous pop 2010s'),
    'siberian indigenous pop 2020s': ('Siberian Indigenous Pop/Rock', 'siberian indigenous pop 2020s'),
    'classic siberian indigenous pop': ('Siberian Indigenous Pop/Rock', 'classic siberian indigenous pop'),

    ###############################################################################
    # Papuan Pop/Rock (Regional - Papúa / Indonesia / PNG)
    ###############################################################################
    ## Papuan Pop General (English / Indonesian / Tok Pisin)
    'papuan pop': ('Papuan Pop/Rock', 'papuan pop'),
    'papua pop': ('Papuan Pop/Rock', 'papua pop'),
    'pop papuano': ('Papuan Pop/Rock', 'pop papuano'),
    'musik papua': ('Papuan Pop/Rock', 'musik papua'),
    'pasin musik': ('Papuan Pop/Rock', 'pasin musik'),

    ## Papuan pop moderno
    'modern papuan pop': ('Papuan Pop/Rock', 'modern papuan pop'),
    'contemporary papuan music': ('Papuan Pop/Rock', 'contemporary papuan music'),

    ## Papuan rock
    'papuan rock': ('Papuan Pop/Rock', 'papuan rock'),
    'rock papuano': ('Papuan Pop/Rock', 'rock papuano'),

    ### Subgéneros de Papuan rock
    'papuan alternative rock': ('Papuan Pop/Rock', 'papuan alternative rock'),
    'papuan indie rock': ('Papuan Pop/Rock', 'papuan indie rock'),
    'papuan metal': ('Papuan Pop/Rock', 'papuan metal'),
    'papuan punk': ('Papuan Pop/Rock', 'papuan punk'),

    ## Papuan reggae (muy importante)
    'papuan reggae': ('Papuan Pop/Rock', 'papuan reggae'),
    'reggae papua': ('Papuan Pop/Rock', 'reggae papua'),
    'papuan roots reggae': ('Papuan Pop/Rock', 'papuan roots reggae'),

    ## Papuan hip hop / Rap
    'papuan hip hop': ('Papuan Pop/Rock', 'papuan hip hop'),
    'papuan rap': ('Papuan Pop/Rock', 'papuan rap'),
    'jayapura rap': ('Papuan Pop/Rock', 'jayapura rap'),
    'port moresby rap': ('Papuan Pop/Rock', 'port moresby rap'),

    ## Papuan R&B
    'papuan r&b': ('Papuan Pop/Rock', 'papuan r&b'),
    'papuan rnb': ('Papuan Pop/Rock', 'papuan rnb'),

    ## Música tradicional fusionada
    'papuan folk': ('Papuan Pop/Rock', 'papuan folk'),
    'tifa fusion': ('Papuan Pop/Rock', 'tifa fusion'),
    'pikon fusion': ('Papuan Pop/Rock', 'pikon fusion'),
    'kundu fusion': ('Papuan Pop/Rock', 'kundu fusion'),

    ## Papuan fusion
    'papuan fusion': ('Papuan Pop/Rock', 'papuan fusion'),
    'melanesian fusion': ('Papuan Pop/Rock', 'melanesian fusion'),

    ## Papuan pop por región
    'jayapura pop': ('Papuan Pop/Rock', 'jayapura pop'),
    'port moresby pop': ('Papuan Pop/Rock', 'port moresby pop'),
    'wamena pop': ('Papuan Pop/Rock', 'wamena pop'),
    'merauke pop': ('Papuan Pop/Rock', 'merauke pop'),
    'biak pop': ('Papuan Pop/Rock', 'biak pop'),

    ## Papuan OST
    'papuan ost': ('Papuan Pop/Rock', 'papuan ost'),
    'papuan film music': ('Papuan Pop/Rock', 'papuan film music'),

    ## Papuan pop por épocas
    'papuan pop 80s': ('Papuan Pop/Rock', 'papuan pop 80s'),
    'papuan pop 90s': ('Papuan Pop/Rock', 'papuan pop 90s'),
    'papuan pop 2000s': ('Papuan Pop/Rock', 'papuan pop 2000s'),
    'papuan pop 2010s': ('Papuan Pop/Rock', 'papuan pop 2010s'),
    'papuan pop 2020s': ('Papuan Pop/Rock', 'papuan pop 2020s'),
    'classic papuan pop': ('Papuan Pop/Rock', 'classic papuan pop'),

    ###############################################################################
    # Karen Pop/Rock (Regional - Karen / Myanmar/Tailandia / Diáspora)
    ###############################################################################
    ## Karen Pop General (English / Karen)
    'karen pop': ('Karen Pop/Rock', 'karen pop'),
    'kayin pop': ('Karen Pop/Rock', 'kayin pop'),
    'pop karen': ('Karen Pop/Rock', 'pop karen'),
    'karen music': ('Karen Pop/Rock', 'karen music'),
    'ကညီကျိာ်': ('Karen Pop/Rock', 'ကညီကျိာ်'),

    ## Karen pop moderno / Diáspora
    'karen diaspora pop': ('Karen Pop/Rock', 'karen diaspora pop'),
    'modern karen pop': ('Karen Pop/Rock', 'modern karen pop'),
    'contemporary karen music': ('Karen Pop/Rock', 'contemporary karen music'),

    ## Karen rock
    'karen rock': ('Karen Pop/Rock', 'karen rock'),
    'kayin rock': ('Karen Pop/Rock', 'kayin rock'),
    'rock karen': ('Karen Pop/Rock', 'rock karen'),

    ### Subgéneros de Karen rock
    'karen alternative rock': ('Karen Pop/Rock', 'karen alternative rock'),
    'karen indie rock': ('Karen Pop/Rock', 'karen indie rock'),
    'karen metal': ('Karen Pop/Rock', 'karen metal'),

    ## Karen hip hop / Rap
    'karen hip hop': ('Karen Pop/Rock', 'karen hip hop'),
    'karen rap': ('Karen Pop/Rock', 'karen rap'),

    ## Karen R&B
    'karen r&b': ('Karen Pop/Rock', 'karen r&b'),
    'karen rnb': ('Karen Pop/Rock', 'karen rnb'),

    ## Música tradicional fusionada
    'karen folk': ('Karen Pop/Rock', 'karen folk'),
    'hsa fusion': ('Karen Pop/Rock', 'hsa fusion'),
    'pweh fusion': ('Karen Pop/Rock', 'pweh fusion'),

    ## Karen fusion
    'karen fusion': ('Karen Pop/Rock', 'karen fusion'),

    ## Karen pop por región
    'karen state pop': ('Karen Pop/Rock', 'karen state pop'),
    'mae sot pop': ('Karen Pop/Rock', 'mae sot pop'),
    'karen diaspora pop': ('Karen Pop/Rock', 'karen diaspora pop'),

    ## Karen OST
    'karen ost': ('Karen Pop/Rock', 'karen ost'),
    'karen film music': ('Karen Pop/Rock', 'karen film music'),

    ## Karen pop por épocas
    'karen pop 80s': ('Karen Pop/Rock', 'karen pop 80s'),
    'karen pop 90s': ('Karen Pop/Rock', 'karen pop 90s'),
    'karen pop 2000s': ('Karen Pop/Rock', 'karen pop 2000s'),
    'karen pop 2010s': ('Karen Pop/Rock', 'karen pop 2010s'),
    'karen pop 2020s': ('Karen Pop/Rock', 'karen pop 2020s'),
    'classic karen pop': ('Karen Pop/Rock', 'classic karen pop'),

    ###############################################################################
    # Macanese Pop/Rock (Regional - Macao)
    ###############################################################################
    ## Macanese Pop General (English / Portuguese / Cantonese)
    'macanese pop': ('Macanese Pop/Rock', 'macanese pop'),
    'macau pop': ('Macanese Pop/Rock', 'macau pop'),
    'pop macaense': ('Macanese Pop/Rock', 'pop macaense'),
    'pop de macau': ('Macanese Pop/Rock', 'pop de macau'),
    'música macaense': ('Macanese Pop/Rock', 'música macaense'),

    ## Macanese pop moderno
    'modern macanese pop': ('Macanese Pop/Rock', 'modern macanese pop'),
    'contemporary macau music': ('Macanese Pop/Rock', 'contemporary macau music'),

    ## Macanese rock
    'macanese rock': ('Macanese Pop/Rock', 'macanese rock'),
    'macau rock': ('Macanese Pop/Rock', 'macau rock'),

    ### Subgéneros de Macanese rock
    'macanese alternative rock': ('Macanese Pop/Rock', 'macanese alternative rock'),
    'macanese indie rock': ('Macanese Pop/Rock', 'macanese indie rock'),
    'macanese metal': ('Macanese Pop/Rock', 'macanese metal'),

    ## Macanese hip hop / Rap
    'macanese hip hop': ('Macanese Pop/Rock', 'macanese hip hop'),
    'macanese rap': ('Macanese Pop/Rock', 'macanese rap'),
    'macau rap': ('Macanese Pop/Rock', 'macau rap'),

    ## Macanese R&B
    'macanese r&b': ('Macanese Pop/Rock', 'macanese r&b'),
    'macanese rnb': ('Macanese Pop/Rock', 'macanese rnb'),

    ## Fusión luso-china (Fado macaense, etc.)
    'fado macaense': ('Macanese Pop/Rock', 'fado macaense'),
    'música luso-chinesa': ('Macanese Pop/Rock', 'música luso-chinesa'),
    'cantonese fado': ('Macanese Pop/Rock', 'cantonese fado'),
    'patuá fusion': ('Macanese Pop/Rock', 'patuá fusion'),

    ## Música tradicional fusionada
    'macanese folk': ('Macanese Pop/Rock', 'macanese folk'),
    'música tradicional macaense': ('Macanese Pop/Rock', 'música tradicional macaense'),

    ## Macanese fusion
    'macanese fusion': ('Macanese Pop/Rock', 'macanese fusion'),

    ## Macanese pop por región
    'macau peninsula pop': ('Macanese Pop/Rock', 'macau peninsula pop'),
    'taipa pop': ('Macanese Pop/Rock', 'taipa pop'),
    'coloane pop': ('Macanese Pop/Rock', 'coloane pop'),

    ## Macanese OST
    'macanese ost': ('Macanese Pop/Rock', 'macanese ost'),
    'macau film music': ('Macanese Pop/Rock', 'macau film music'),

    ## Macanese pop por épocas
    'macanese pop 80s': ('Macanese Pop/Rock', 'macanese pop 80s'),
    'macanese pop 90s': ('Macanese Pop/Rock', 'macanese pop 90s'),
    'macanese pop 2000s': ('Macanese Pop/Rock', 'macanese pop 2000s'),
    'macanese pop 2010s': ('Macanese Pop/Rock', 'macanese pop 2010s'),
    'macanese pop 2020s': ('Macanese Pop/Rock', 'macanese pop 2020s'),
    'classic macanese pop': ('Macanese Pop/Rock', 'classic macanese pop'),

    ###############################################################################
    # AFROBEATS (Regional - África Occidental)
    ###############################################################################
    ## Afrobeats General (English / Yoruba / Pidgin)
    'afrobeats': ('Afrobeats', 'afrobeats'),
    'afro beats': ('Afrobeats', 'afro beats'),
    'afropop': ('Afrobeats', 'afropop'),
    'afro pop': ('Afrobeats', 'afro pop'),
    'afrofusion': ('Afrobeats', 'afrofusion'),
    'afro fusion': ('Afrobeats', 'afro fusion'),
    'afro r&b': ('Afrobeats', 'afro r&b'),
    'afro rnb': ('Afrobeats', 'afro rnb'),
    'afro trap': ('Afrobeats', 'afro trap'),
    'afro trap latino': ('Afrobeats', 'afro trap latino'), # Fusión con latino

    ## Escenas nacionales
    'naija pop': ('Afrobeats', 'naija pop'),
    'nigerian pop': ('Afrobeats', 'nigerian pop'),
    'ghanaian pop': ('Afrobeats', 'ghanaian pop'),
    'ghana hiplife': ('Afrobeats', 'ghana hiplife'),
    'hiplife': ('Afrobeats', 'hiplife'),
    'banku music': ('Afrobeats', 'banku music'),
    'azonto': ('Afrobeats', 'azonto'),

    ## Subgéneros y estilos
    'afrohouse': ('Afrobeats', 'afrohouse'),
    'afro house': ('Afrobeats', 'afro house'),
    'afro soul': ('Afrobeats', 'afro soul'),
    'afro soulful': ('Afrobeats', 'afro soulful'),
    'afro dancehall': ('Afrobeats', 'afro dancehall'),
    'afro pop dance': ('Afrobeats', 'afro pop dance'),

    ## Fusiones
    'afrobeats pop': ('Afrobeats', 'afrobeats pop'),
    'afrobeats r&b': ('Afrobeats', 'afrobeats r&b'),
    'afrobeats hip hop': ('Afrobeats', 'afrobeats hip hop'),
    'afrobeats reggae': ('Afrobeats', 'afrobeats reggae'),

    ## Por región
    'lagos pop': ('Afrobeats', 'lagos pop'),
    'accra pop': ('Afrobeats', 'accra pop'),
    'west african pop': ('Afrobeats', 'west african pop'),

    ## En idiomas locales
    'musiqa naija': ('Afrobeats', 'musiqa naija'), # Pidgin
    'afrobeats yoruba': ('Afrobeats', 'afrobeats yoruba'),
    'afrobeats pidgin': ('Afrobeats', 'afrobeats pidgin'),

    ###############################################################################
    # AMAPIANO (Regional - Sudáfrica)
    ###############################################################################
    ## Amapiano General (English / Zulu / Xhosa / Sotho)
    'amapiano': ('Amapiano', 'amapiano'),
    'ama piano': ('Amapiano', 'ama piano'),
    'south african house': ('Amapiano', 'south african house'),
    'sa house': ('Amapiano', 'sa house'),
    'piano music sa': ('Amapiano', 'piano music sa'),

    ## Subgéneros principales
    'amapiano clásico': ('Amapiano', 'amapiano clásico'),
    'amapiano classic': ('Amapiano', 'amapiano classic'),
    'amapiano log drum': ('Amapiano', 'amapiano log drum'),
    'amapiano logdrum': ('Amapiano', 'amapiano logdrum'),
    'amapiano piano': ('Amapiano', 'amapiano piano'),
    'private school amapiano': ('Amapiano', 'private school amapiano'),
    'soulful amapiano': ('Amapiano', 'soulful amapiano'),
    'amapiano soul': ('Amapiano', 'amapiano soul'),
    'amapiano deep': ('Amapiano', 'amapiano deep'),

    ## Estilos relacionados
    'gqom': ('Amapiano', 'gqom'),  # Variante más dura, pero a veces separada
    'gqom music': ('Amapiano', 'gqom music'),
    'durban sound': ('Amapiano', 'durban sound'),
    'durban house': ('Amapiano', 'durban house'),
    'bacardi house': ('Amapiano', 'bacardi house'),

    ## Fusiones
    'amapiano rap': ('Amapiano', 'amapiano rap'),
    'amapiano hip hop': ('Amapiano', 'amapiano hip hop'),
    'amapiano pop': ('Amapiano', 'amapiano pop'),
    'amapiano afrobeat': ('Amapiano', 'amapiano afrobeat'),
    'amapiano r&b': ('Amapiano', 'amapiano r&b'),

    ## Por región
    'johannesburg amapiano': ('Amapiano', 'johannesburg amapiano'),
    'pretoria amapiano': ('Amapiano', 'pretoria amapiano'),
    'durban amapiano': ('Amapiano', 'durban amapiano'),
    'cape town amapiano': ('Amapiano', 'cape town amapiano'),
    'soweto amapiano': ('Amapiano', 'soweto amapiano'),

    ## En idiomas locales
    'umculo we amapiano': ('Amapiano', 'umculo we amapiano'), # Zulu
    'amapiano yase gauteng': ('Amapiano', 'amapiano yase gauteng'),
    'amapiano kasi': ('Amapiano', 'amapiano kasi'), # Township

    ###############################################################################
    # BONGO FLAVA (Regional - Tanzania)
    ###############################################################################
    ## Bongo Flava General (English / Swahili)
    'bongo flava': ('Bongo Flava', 'bongo flava'),
    'bongo flavour': ('Bongo Flava', 'bongo flavour'),
    'tanzanian pop': ('Bongo Flava', 'tanzanian pop'),
    'bongo fleva': ('Bongo Flava', 'bongo fleva'),
    'muziki wa bongo': ('Bongo Flava', 'muziki wa bongo'),

    ## Subgéneros
    'bongo flava clásico': ('Bongo Flava', 'bongo flava clásico'),
    'bongo flava classic': ('Bongo Flava', 'bongo flava classic'),
    'bongo r&b': ('Bongo Flava', 'bongo r&b'),
    'bongo rnb': ('Bongo Flava', 'bongo rnb'),
    'bongo hip hop': ('Bongo Flava', 'bongo hip hop'),
    'bongo rap': ('Bongo Flava', 'bongo rap'),
    'bongo flava romántico': ('Bongo Flava', 'bongo flava romántico'),
    'bongo love': ('Bongo Flava', 'bongo love'),

    ## Estilos relacionados
    'singeli': ('Bongo Flava', 'singeli'),
    'singeli music': ('Bongo Flava', 'singeli music'),
    'zouk love': ('Bongo Flava', 'zouk love'),
    'tanzanian zouk': ('Bongo Flava', 'tanzanian zouk'),
    'afrobeat tanzano': ('Bongo Flava', 'afrobeat tanzano'),

    ## Fusiones
    'bongo flava pop': ('Bongo Flava', 'bongo flava pop'),
    'bongo flava dance': ('Bongo Flava', 'bongo flava dance'),
    'bongo flava reggae': ('Bongo Flava', 'bongo flava reggae'),

    ## Por región
    'dar es salaam pop': ('Bongo Flava', 'dar es salaam pop'),
    'arusha pop': ('Bongo Flava', 'arusha pop'),
    'mwanza pop': ('Bongo Flava', 'mwanza pop'),
    'zanzibar pop': ('Bongo Flava', 'zanzibar pop'),

    ## En swahili
    'bongo flava kiswahili': ('Bongo Flava', 'bongo flava kiswahili'),
    'muziki wa kisasa tanzania': ('Bongo Flava', 'muziki wa kisasa tanzania'),

    ###############################################################################
    # ZIM DANCEHALL (Regional - Zimbabue)
    ###############################################################################
    ## Zim Dancehall General (English / Shona / Ndebele)
    'zim dancehall': ('Zim Dancehall', 'zim dancehall'),
    'zimbabwe dancehall': ('Zim Dancehall', 'zimbabwe dancehall'),
    'zimdancehall': ('Zim Dancehall', 'zimdancehall'),
    'dancehall zimbabwe': ('Zim Dancehall', 'dancehall zimbabwe'),

    ## Subgéneros
    'zim dancehall clásico': ('Zim Dancehall', 'zim dancehall clásico'),
    'zim dancehall classic': ('Zim Dancehall', 'zim dancehall classic'),
    'urban grooves': ('Zim Dancehall', 'urban grooves'),
    'zim hip hop': ('Zim Dancehall', 'zim hip hop'),
    'zim rap': ('Zim Dancehall', 'zim rap'),
    'zim reggae': ('Zim Dancehall', 'zim reggae'),
    'zim r&b': ('Zim Dancehall', 'zim r&b'),

    ## Estilos tradicionales influyentes
    'sungura': ('Zim Dancehall', 'sungura'),
    'sungura music': ('Zim Dancehall', 'sungura music'),
    'chimurenga': ('Zim Dancehall', 'chimurenga'), # Influencia, aunque es género aparte
    'jit': ('Zim Dancehall', 'jit'),

    ## Fusiones
    'zim dancehall pop': ('Zim Dancehall', 'zim dancehall pop'),
    'zim dancehall afrobeat': ('Zim Dancehall', 'zim dancehall afrobeat'),
    'zim dancehall reggae': ('Zim Dancehall', 'zim dancehall reggae'),

    ## Por región
    'harare dancehall': ('Zim Dancehall', 'harare dancehall'),
    'bulawayo dancehall': ('Zim Dancehall', 'bulawayo dancehall'),
    'mutare dancehall': ('Zim Dancehall', 'mutare dancehall'),

    ## En idiomas locales
    'dancehall yemuZimbabwe': ('Zim Dancehall', 'dancehall yemuZimbabwe'), # Shona/Inglés
    'mimhanzi yeZimbabwe': ('Zim Dancehall', 'mimhanzi yeZimbabwe'), # Shona
    'umculo weZimbabwe': ('Zim Dancehall', 'umculo weZimbabwe'), # Ndebele

    ###############################################################################
    # KUDURO (Regional - Angola)
    ###############################################################################
    ## Kuduro General (English / Portuguese)
    'kuduro': ('Kuduro', 'kuduro'),
    'kuduru': ('Kuduro', 'kuduru'),
    'angolan kuduro': ('Kuduro', 'angolan kuduro'),
    'música kuduro': ('Kuduro', 'música kuduro'),

    ## Subgéneros y estilos
    'kuduro clássico': ('Kuduro', 'kuduro clássico'),
    'kuduro moderno': ('Kuduro', 'kuduro moderno'),
    'kuduro batidão': ('Kuduro', 'kuduro batidão'),
    'kuduro progressivo': ('Kuduro', 'kuduro progressivo'),

    ## Fusiones
    'kuduro pop': ('Kuduro', 'kuduro pop'),
    'kuduro house': ('Kuduro', 'kuduro house'),
    'kuduro eletrônico': ('Kuduro', 'kuduro eletrônico'),
    'kuduro hip hop': ('Kuduro', 'kuduro hip hop'),

    ## Por región
    'luanda kuduro': ('Kuduro', 'luanda kuduro'),
    'benguela kuduro': ('Kuduro', 'benguela kuduro'),
    'huambo kuduro': ('Kuduro', 'huambo kuduro'),

    ## En portugués
    'batida angolana': ('Kuduro', 'batida angolana'),
    'musica de luanda': ('Kuduro', 'musica de luanda'),

    ###############################################################################
    # KIZOMBA / ZOUK (Regional - Angola / Cabo Verde)
    ###############################################################################
    ## Kizomba General
    'kizomba': ('Kizomba/Zouk', 'kizomba'),
    'kizomba music': ('Kizomba/Zouk', 'kizomba music'),
    'música kizomba': ('Kizomba/Zouk', 'música kizomba'),
    'kizomba angolana': ('Kizomba/Zouk', 'kizomba angolana'),

    ## Zouk General
    'zouk': ('Kizomba/Zouk', 'zouk'),
    'zouk love': ('Kizomba/Zouk', 'zouk love'),
    'zouk antilhês': ('Kizomba/Zouk', 'zouk antilhês'),  # Antillean zouk
    'zouk brasileiro': ('Kizomba/Zouk', 'zouk brasileiro'),

    ## Subgéneros de Kizomba
    'kizomba clássica': ('Kizomba/Zouk', 'kizomba clássica'),
    'kizomba moderna': ('Kizomba/Zouk', 'kizomba moderna'),
    'kizomba romântica': ('Kizomba/Zouk', 'kizomba romântica'),
    'kizomba sensual': ('Kizomba/Zouk', 'kizomba sensual'),
    'kizomba fusion': ('Kizomba/Zouk', 'kizomba fusion'),
    'ghetto kizomba': ('Kizomba/Zouk', 'ghetto kizomba'),  # Variante urbana

    ## Cabo Verde
    'coladeira': ('Kizomba/Zouk', 'coladeira'),
    'colá': ('Kizomba/Zouk', 'colá'),
    'cabo love': ('Kizomba/Zouk', 'cabo love'),
    'funaná': ('Kizomba/Zouk', 'funaná'),  # Aunque tiene sección propia, también relacionado
    'funaná fusion': ('Kizomba/Zouk', 'funaná fusion'),

    ## Fusiones
    'kizomba pop': ('Kizomba/Zouk', 'kizomba pop'),
    'kizomba house': ('Kizomba/Zouk', 'kizomba house'),
    'kizomba r&b': ('Kizomba/Zouk', 'kizomba r&b'),
    'zouk r&b': ('Kizomba/Zouk', 'zouk r&b'),
    'zouk pop': ('Kizomba/Zouk', 'zouk pop'),

    ## Por región
    'luanda kizomba': ('Kizomba/Zouk', 'luanda kizomba'),
    'praia kizomba': ('Kizomba/Zouk', 'praia kizomba'),
    'lisboa kizomba': ('Kizomba/Zouk', 'lisboa kizomba'),  # Importante en diáspora
    'paris kizomba': ('Kizomba/Zouk', 'paris kizomba'),

    ## En portugués / crioulo
    'morna': ('Kizomba/Zouk', 'morna'),  # Cabo Verde, relacionado pero más tradicional
    'coladera': ('Kizomba/Zouk', 'coladera'),
    'batuku': ('Kizomba/Zouk', 'batuku'),

    ###############################################################################
    # MBALAX (Regional - Senegal)
    ###############################################################################
    ## Mbalax General (English / Wolof / French)
    'mbalax': ('Mbalax', 'mbalax'),
    'mbalakh': ('Mbalax', 'mbalakh'),
    'senegalese pop': ('Mbalax', 'senegalese pop'),
    'mbalax senegal': ('Mbalax', 'mbalax senegal'),

    ## Subgéneros
    'mbalax classique': ('Mbalax', 'mbalax classique'),
    'mbalax moderne': ('Mbalax', 'mbalax moderne'),
    'mbalax dance': ('Mbalax', 'mbalax dance'),
    'mbalax sabar': ('Mbalax', 'mbalax sabar'),  # Basado en ritmo sabar

    ## Fusiones
    'mbalax pop': ('Mbalax', 'mbalax pop'),
    'mbalax hip hop': ('Mbalax', 'mbalax hip hop'),
    'mbalax r&b': ('Mbalax', 'mbalax r&b'),
    'mbalax reggae': ('Mbalax', 'mbalax reggae'),

    ## Por región
    'dakar mbalax': ('Mbalax', 'dakar mbalax'),
    'thiès mbalax': ('Mbalax', 'thiès mbalax'),
    'saint louis mbalax': ('Mbalax', 'saint louis mbalax'),

    ## En wolof / francés
    'mbalax wolof': ('Mbalax', 'mbalax wolof'),
    'musique sénégalaise': ('Mbalax', 'musique sénégalaise'),
    'tassou': ('Mbalax', 'tassou'),

    ###############################################################################
    # COUPÉ-DÉCALÉ (Regional - Costa de Marfil)
    ###############################################################################
    ## Coupé-Décalé General (English / French)
    'coupé décalé': ('Coupé-Décalé', 'coupé décalé'),
    'coupe decale': ('Coupé-Décalé', 'coupe decale'),
    'coupé-décalé': ('Coupé-Décalé', 'coupé-décalé'),
    'ivoirian pop': ('Coupé-Décalé', 'ivoirian pop'),
    'musique ivoirienne': ('Coupé-Décalé', 'musique ivoirienne'),

    ## Subgéneros
    'coupé décalé classique': ('Coupé-Décalé', 'coupé décalé classique'),
    'coupé décalé moderne': ('Coupé-Décalé', 'coupé décalé moderne'),
    'coupé décalé dance': ('Coupé-Décalé', 'coupé décalé dance'),

    ## Estilos relacionados
    'zouglou': ('Coupé-Décalé', 'zouglou'),  # Precursor
    'mapouka': ('Coupé-Décalé', 'mapouka'),

    ## Fusiones
    'coupé décalé pop': ('Coupé-Décalé', 'coupé décalé pop'),
    'coupé décalé hip hop': ('Coupé-Décalé', 'coupé décalé hip hop'),
    'coupé décalé r&b': ('Coupé-Décalé', 'coupé décalé r&b'),

    ## Por región
    'abidjan coupé décalé': ('Coupé-Décalé', 'abidjan coupé décalé'),
    'bouaké coupé décalé': ('Coupé-Décalé', 'bouaké coupé décalé'),
    'yamoussoukro coupé décalé': ('Coupé-Décalé', 'yamoussoukro coupé décalé'),

    ## En francés / nouchi
    'coupé décalé nouchi': ('Coupé-Décalé', 'coupé décalé nouchi'),  # Argot de Abidjan
    'débrouillard music': ('Coupé-Décalé', 'débrouillard music'),

    ###############################################################################
    # SOUKOUS / NDOMBOLO (Regional - RDC / Congo)
    ###############################################################################
    ## Soukous General (English / Lingala / French)
    'soukous': ('Soukous/Ndombolo', 'soukous'),
    'soukous music': ('Soukous/Ndombolo', 'soukous music'),
    'lingala music': ('Soukous/Ndombolo', 'lingala music'),
    'congo music': ('Soukous/Ndombolo', 'congo music'),
    'rumba congolaise': ('Soukous/Ndombolo', 'rumba congolaise'),

    ## Ndombolo
    'ndombolo': ('Soukous/Ndombolo', 'ndombolo'),
    'ndombolo dance': ('Soukous/Ndombolo', 'ndombolo dance'),
    'ndombolo moderne': ('Soukous/Ndombolo', 'ndombolo moderne'),

    ## Subgéneros
    'soukous classique': ('Soukous/Ndombolo', 'soukous classique'),
    'soukous moderne': ('Soukous/Ndombolo', 'soukous moderne'),
    'soukous rumba': ('Soukous/Ndombolo', 'soukous rumba'),
    'soukous pop': ('Soukous/Ndombolo', 'soukous pop'),
    'soukous rock': ('Soukous/Ndombolo', 'soukous rock'),

    ## Por región
    'kinshasa soukous': ('Soukous/Ndombolo', 'kinshasa soukous'),
    'brazzaville soukous': ('Soukous/Ndombolo', 'brazzaville soukous'),
    'lubumbashi soukous': ('Soukous/Ndombolo', 'lubumbashi soukous'),

    ## En lingala / francés
    'mboka lingala': ('Soukous/Ndombolo', 'mboka lingala'),
    'congo rumba': ('Soukous/Ndombolo', 'congo rumba'),
    'musique congolaise': ('Soukous/Ndombolo', 'musique congolaise'),

    ###############################################################################
    # ETHIO-JAZZ (Regional - Etiopía)
    ###############################################################################
    ## Ethio-jazz General (English / Amharic)
    'ethio jazz': ('Ethio-jazz', 'ethio jazz'),
    'ethiojazz': ('Ethio-jazz', 'ethiojazz'),
    'ethiopian jazz': ('Ethio-jazz', 'ethiopian jazz'),
    'éthio-jazz': ('Ethio-jazz', 'éthio-jazz'),

    ## Subgéneros
    'ethio-jazz classique': ('Ethio-jazz', 'ethio-jazz classique'),
    'ethio-jazz moderne': ('Ethio-jazz', 'ethio-jazz moderne'),
    'ethio-funk': ('Ethio-jazz', 'ethio-funk'),
    'ethio-groove': ('Ethio-jazz', 'ethio-groove'),
    'ethio-soul': ('Ethio-jazz', 'ethio-soul'),

    ## Fusión
    'ethio-jazz fusion': ('Ethio-jazz', 'ethio-jazz fusion'),
    'ethio-jazz hip hop': ('Ethio-jazz', 'ethio-jazz hip hop'),
    'ethio-jazz electronic': ('Ethio-jazz', 'ethio-jazz electronic'),

    ## Por región
    'addis ababa jazz': ('Ethio-jazz', 'addis ababa jazz'),
    'gondar jazz': ('Ethio-jazz', 'gondar jazz'),

    ## En amhárico
    'yä ityopya jazz': ('Ethio-jazz', 'yä ityopya jazz'),

    ###############################################################################
    # GNAWA (Regional - Marruecos)
    ###############################################################################
    ## Gnawa General (English / Arabic / French)
    'gnawa': ('Gnawa', 'gnawa'),
    'gnaoua': ('Gnawa', 'gnaoua'),
    'gnawa music': ('Gnawa', 'gnawa music'),
    'musique gnawa': ('Gnawa', 'musique gnawa'),
    'الݣناوة': ('Gnawa', 'الݣناوة'),

    ## Subgéneros
    'gnawa traditionnel': ('Gnawa', 'gnawa traditionnel'),
    'gnawa moderne': ('Gnawa', 'gnawa moderne'),
    'gnawa fusion': ('Gnawa', 'gnawa fusion'),
    'gnawa jazz': ('Gnawa', 'gnawa jazz'),
    'gnawa rock': ('Gnawa', 'gnawa rock'),
    'gnawa electro': ('Gnawa', 'gnawa electro'),

    ## Por región
    'marrakech gnawa': ('Gnawa', 'marrakech gnawa'),
    'essaouira gnawa': ('Gnawa', 'essaouira gnawa'),
    'fes gnawa': ('Gnawa', 'fes gnawa'),
    'casablanca gnawa': ('Gnawa', 'casablanca gnawa'),

    ## En árabe / francés
    'gnawa diwan': ('Gnawa', 'gnawa diwan'),
    'lila gnawa': ('Gnawa', 'lila gnawa'),
    'krakeb music': ('Gnawa', 'krakeb music'),  # Instrumento

    ###############################################################################
    # TAARAB (Regional - Tanzania / Zanzíbar / Kenia)
    ###############################################################################
    ## Taarab General (English / Swahili / Arabic)
    'taarab': ('Taarab', 'taarab'),
    'tarab': ('Taarab', 'tarab'),
    'taarab music': ('Taarab', 'taarab music'),
    'muziki wa taarab': ('Taarab', 'muziki wa taarab'),

    ## Subgéneros
    'taarab classique': ('Taarab', 'taarab classique'),
    'taarab moderne': ('Taarab', 'taarab moderne'),
    'taarab ya kisasa': ('Taarab', 'taarab ya kisasa'),
    'taarab fusion': ('Taarab', 'taarab fusion'),
    'taarab pop': ('Taarab', 'taarab pop'),

    ## Por región
    'zanzibar taarab': ('Taarab', 'zanzibar taarab'),
    'dar es salaam taarab': ('Taarab', 'dar es salaam taarab'),
    'mombasa taarab': ('Taarab', 'mombasa taarab'),
    'lamu taarab': ('Taarab', 'lamu taarab'),
    'kenyan taarab': ('Taarab', 'kenyan taarab'),
    'tanzanian taarab': ('Taarab', 'tanzanian taarab'),

    ## En swahili / árabe
    'kidumbak': ('Taarab', 'kidumbak'),  # Estilo relacionado
    'taarab ya zamani': ('Taarab', 'taarab ya zamani'),
    'ngoma ya taarab': ('Taarab', 'ngoma ya taarab'),

    ###############################################################################
    # KAPUKA (Regional - Kenia)
    ###############################################################################
    ## Kapuka General (English / Swahili / Sheng)
    'kapuka': ('Kapuka', 'kapuka'),
    'kenyan kapuka': ('Kapuka', 'kenyan kapuka'),
    'kapuka music': ('Kapuka', 'kapuka music'),

    ## Subgéneros
    'kapuka classic': ('Kapuka', 'kapuka classic'),
    'kapuka modern': ('Kapuka', 'kapuka modern'),
    'kapuka dance': ('Kapuka', 'kapuka dance'),
    'kapuka pop': ('Kapuka', 'kapuka pop'),

    ## Fusión
    'kapuka hip hop': ('Kapuka', 'kapuka hip hop'),
    'kapuka r&b': ('Kapuka', 'kapuka r&b'),
    'kapuka reggae': ('Kapuka', 'kapuka reggae'),

    ## Por región
    'nairobi kapuka': ('Kapuka', 'nairobi kapuka'),
    'mombasa kapuka': ('Kapuka', 'mombasa kapuka'),
    'kisumu kapuka': ('Kapuka', 'kisumu kapuka'),

    ## En sheng / swahili
    'kapuka sheng': ('Kapuka', 'kapuka sheng'),
    'muziki wa kapuka': ('Kapuka', 'muziki wa kapuka'),

    ###############################################################################
    # GENGETONE (Regional - Kenia)
    ###############################################################################
    ## Gengetone General (English / Swahili / Sheng)
    'gengetone': ('Gengetone', 'gengetone'),
    'genge tone': ('Gengetone', 'genge tone'),
    'kenyan gengetone': ('Gengetone', 'kenyan gengetone'),

    ## Subgéneros
    'gengetone classic': ('Gengetone', 'gengetone classic'),
    'gengetone modern': ('Gengetone', 'gengetone modern'),
    'gengetone dance': ('Gengetone', 'gengetone dance'),
    'gengetone rap': ('Gengetone', 'gengetone rap'),

    ## Fusión
    'gengetone pop': ('Gengetone', 'gengetone pop'),
    'gengetone afrobeat': ('Gengetone', 'gengetone afrobeat'),
    'gengetone r&b': ('Gengetone', 'gengetone r&b'),
    'gengetone bongo': ('Gengetone', 'gengetone bongo'),

    ## Por región
    'nairobi gengetone': ('Gengetone', 'nairobi gengetone'),
    'kiambu gengetone': ('Gengetone', 'kiambu gengetone'),
    'mathare gengetone': ('Gengetone', 'mathare gengetone'),

    ## En sheng
    'gengetone sheng': ('Gengetone', 'gengetone sheng'),
    'sheng rap': ('Gengetone', 'sheng rap'),

    ###############################################################################
    # SHANGAAN ELECTRO (Regional - Sudáfrica / Mozambique)
    ###############################################################################
    ## Shangaan Electro General (English / Tsonga)
    'shangaan electro': ('Shangaan Electro', 'shangaan electro'),
    'shangaan electronic': ('Shangaan Electro', 'shangaan electronic'),
    'shangaan beats': ('Shangaan Electro', 'shangaan beats'),
    'tsonga electro': ('Shangaan Electro', 'tsonga electro'),

    ## Subgéneros
    'shangaan electro classic': ('Shangaan Electro', 'shangaan electro classic'),
    'shangaan electro modern': ('Shangaan Electro', 'shangaan electro modern'),
    'shangaan dance': ('Shangaan Electro', 'shangaan dance'),

    ## Fusión
    'shangaan electro pop': ('Shangaan Electro', 'shangaan electro pop'),
    'shangaan electro house': ('Shangaan Electro', 'shangaan electro house'),

    ## Por región
    'johannesburg shangaan': ('Shangaan Electro', 'johannesburg shangaan'),
    'maputo shangaan': ('Shangaan Electro', 'maputo shangaan'),
    'limpopo shangaan': ('Shangaan Electro', 'limpopo shangaan'),

    ## En tsonga
    'mintirho ya shangaan': ('Shangaan Electro', 'mintirho ya shangaan'),
    'xibelani dance music': ('Shangaan Electro', 'xibelani dance music'),

    ###############################################################################
    # MARRABENTA (Regional - Mozambique)
    ###############################################################################
    ## Marrabenta General (English / Portuguese)
    'marrabenta': ('Marrabenta', 'marrabenta'),
    'mozambican marrabenta': ('Marrabenta', 'mozambican marrabenta'),
    'música marrabenta': ('Marrabenta', 'música marrabenta'),

    ## Subgéneros
    'marrabenta clássica': ('Marrabenta', 'marrabenta clássica'),
    'marrabenta moderna': ('Marrabenta', 'marrabenta moderna'),
    'marrabenta dance': ('Marrabenta', 'marrabenta dance'),
    'marrabenta pop': ('Marrabenta', 'marrabenta pop'),

    ## Fusión
    'marrabenta fusion': ('Marrabenta', 'marrabenta fusion'),
    'marrabenta rock': ('Marrabenta', 'marrabenta rock'),
    'marrabenta hip hop': ('Marrabenta', 'marrabenta hip hop'),

    ## Por región
    'maputo marrabenta': ('Marrabenta', 'maputo marrabenta'),
    'beira marrabenta': ('Marrabenta', 'beira marrabenta'),
    'nampula marrabenta': ('Marrabenta', 'nampula marrabenta'),

    ## En português
    'ritmo marrabenta': ('Marrabenta', 'ritmo marrabenta'),
    'musica de moçambique': ('Marrabenta', 'musica de moçambique'),

    ###############################################################################
    # COLADEIRA (Regional - Cabo Verde) [ya incluida en Kizomba/Zouk, pero se amplía]
    ###############################################################################
    ## Coladeira General (English / Crioulo)
    'coladeira': ('Coladeira', 'coladeira'),
    'koladera': ('Coladeira', 'koladera'),
    'cabo verde coladeira': ('Coladeira', 'cabo verde coladeira'),

    ## Subgéneros
    'coladeira clássica': ('Coladeira', 'coladeira clássica'),
    'coladeira moderna': ('Coladeira', 'coladeira moderna'),
    'coladeira dance': ('Coladeira', 'coladeira dance'),

    ## Fusión
    'coladeira pop': ('Coladeira', 'coladeira pop'),
    'coladeira zouk': ('Coladeira', 'coladeira zouk'),
    'coladeira funaná': ('Coladeira', 'coladeira funaná'),

    ## Por región
    'praia coladeira': ('Coladeira', 'praia coladeira'),
    'mindelo coladeira': ('Coladeira', 'mindelo coladeira'),

    ## En crioulo
    'morna coladeira': ('Coladeira', 'morna coladeira'),
    'musika di koladera': ('Coladeira', 'musika di koladera'),

    ###############################################################################
    # FUNANÁ (Regional - Cabo Verde)
    ###############################################################################
    ## Funaná General (English / Crioulo)
    'funaná': ('Funaná', 'funaná'),
    'funana': ('Funaná', 'funana'),
    'cabo verde funaná': ('Funaná', 'cabo verde funaná'),

    ## Subgéneros
    'funaná tradicional': ('Funaná', 'funaná tradicional'),
    'funaná moderno': ('Funaná', 'funaná moderno'),
    'funaná dance': ('Funaná', 'funaná dance'),
    'funaná fusion': ('Funaná', 'funaná fusion'),

    ## Fusión
    'funaná pop': ('Funaná', 'funaná pop'),
    'funaná eletrônico': ('Funaná', 'funaná eletrônico'),
    'funaná hip hop': ('Funaná', 'funaná hip hop'),

    ## Por región
    'santiago funaná': ('Funaná', 'santiago funaná'),
    'são vicente funaná': ('Funaná', 'são vicente funaná'),

    ## En crioulo
    'batuku funaná': ('Funaná', 'batuku funaná'),
    'musika di funaná': ('Funaná', 'musika di funaná'),

    ###############################################################################
    # BENGA (Regional - Kenia)
    ###############################################################################
    ## Benga General (English / Swahili / Luo)
    'benga': ('Benga', 'benga'),
    'kenyan benga': ('Benga', 'kenyan benga'),
    'benga music': ('Benga', 'benga music'),
    'muziki wa benga': ('Benga', 'muziki wa benga'),

    ## Subgéneros
    'benga classic': ('Benga', 'benga classic'),
    'benga modern': ('Benga', 'benga modern'),
    'benga pop': ('Benga', 'benga pop'),
    'benga dance': ('Benga', 'benga dance'),

    ## Fusión
    'benga fusion': ('Benga', 'benga fusion'),
    'benga rock': ('Benga', 'benga rock'),
    'benga r&b': ('Benga', 'benga r&b'),

    ## Por región
    'kisumu benga': ('Benga', 'kisumu benga'),
    'nairobi benga': ('Benga', 'nairobi benga'),
    'western kenya benga': ('Benga', 'western kenya benga'),

    ## En luo / swahili
    'ohangla benga': ('Benga', 'ohangla benga'),  # Estilo relacionado
    'benga luo': ('Benga', 'benga luo'),

    ###############################################################################
    # HIGHLIFE (Regional - Ghana / Nigeria)
    ###############################################################################
    ## Highlife General (English / Twi / Yoruba)
    'highlife': ('Highlife', 'highlife'),
    'ghana highlife': ('Highlife', 'ghana highlife'),
    'nigerian highlife': ('Highlife', 'nigerian highlife'),
    'west african highlife': ('Highlife', 'west african highlife'),

    ## Subgéneros
    'highlife classic': ('Highlife', 'highlife classic'),
    'highlife modern': ('Highlife', 'highlife modern'),
    'highlife pop': ('Highlife', 'highlife pop'),
    'highlife dance': ('Highlife', 'highlife dance'),
    'highlife guitar': ('Highlife', 'highlife guitar'),
    'highlife brass': ('Highlife', 'highlife brass'),

    ## Estilos relacionados
    'palm wine music': ('Highlife', 'palm wine music'),
    'palm wine highlife': ('Highlife', 'palm wine highlife'),
    'west african guitar music': ('Highlife', 'west african guitar music'),

    ## Fusión
    'highlife fusion': ('Highlife', 'highlife fusion'),
    'highlife afrobeat': ('Highlife', 'highlife afrobeat'),
    'highlife jazz': ('Highlife', 'highlife jazz'),

    ## Por región
    'accra highlife': ('Highlife', 'accra highlife'),
    'lagos highlife': ('Highlife', 'lagos highlife'),
    'kumasi highlife': ('Highlife', 'kumasi highlife'),
    'ibadan highlife': ('Highlife', 'ibadan highlife'),

    ## En twi / yoruba / ga
    'highlife twi': ('Highlife', 'highlife twi'),
    'highlife yoruba': ('Highlife', 'highlife yoruba'),
    'osibisa style': ('Highlife', 'osibisa style'),  # Banda icónica

    ###############################################################################
    # JÙJÚ (Regional - Nigeria)
    ###############################################################################
    ## Jùjú General (English / Yoruba)
    'jùjú': ('Jùjú', 'jùjú'),
    'juju': ('Jùjú', 'juju'),
    'nigerian jùjú': ('Jùjú', 'nigerian jùjú'),
    'yoruba jùjú': ('Jùjú', 'yoruba jùjú'),
    'music jùjú': ('Jùjú', 'music jùjú'),

    ## Subgéneros
    'jùjú classic': ('Jùjú', 'jùjú classic'),
    'jùjú modern': ('Jùjú', 'jùjú modern'),
    'jùjú pop': ('Jùjú', 'jùjú pop'),
    'jùjú dance': ('Jùjú', 'jùjú dance'),
    'jùjú gospel': ('Jùjú', 'jùjú gospel'),

    ## Fusión
    'jùjú fusion': ('Jùjú', 'jùjú fusion'),
    'jùjú afrobeat': ('Jùjú', 'jùjú afrobeat'),
    'jùjú highlife': ('Jùjú', 'jùjú highlife'),

    ## Por región
    'lagos jùjú': ('Jùjú', 'lagos jùjú'),
    'ibadan jùjú': ('Jùjú', 'ibadan jùjú'),
    'abeokuta jùjú': ('Jùjú', 'abeokuta jùjú'),

    ## En yoruba
    'orin jùjú': ('Jùjú', 'orin jùjú'),
    'àdúrà jùjú': ('Jùjú', 'àdúrà jùjú'),

    ###############################################################################
    # FUJI (Regional - Nigeria)
    ###############################################################################
    ## Fuji General (English / Yoruba)
    'fuji': ('Fuji', 'fuji'),
    'nigerian fuji': ('Fuji', 'nigerian fuji'),
    'yoruba fuji': ('Fuji', 'yoruba fuji'),
    'fuji music': ('Fuji', 'fuji music'),

    ## Subgéneros
    'fuji classic': ('Fuji', 'fuji classic'),
    'fuji modern': ('Fuji', 'fuji modern'),
    'fuji pop': ('Fuji', 'fuji pop'),
    'fuji dance': ('Fuji', 'fuji dance'),
    'fuji gospel': ('Fuji', 'fuji gospel'),
    'bọn fuji': ('Fuji', 'bọn fuji'),

    ## Fusión
    'fuji fusion': ('Fuji', 'fuji fusion'),
    'fuji afrobeat': ('Fuji', 'fuji afrobeat'),
    'fuji hip hop': ('Fuji', 'fuji hip hop'),

    ## Por región
    'lagos fuji': ('Fuji', 'lagos fuji'),
    'ibadan fuji': ('Fuji', 'ibadan fuji'),
    'oyo fuji': ('Fuji', 'oyo fuji'),

    ## En yoruba
    'orin fuji': ('Fuji', 'orin fuji'),
    'àpàlà fuji': ('Fuji', 'àpàlà fuji'),  # Relación con apala

    ###############################################################################
    # APALA (Regional - Nigeria)
    ###############################################################################
    ## Apala General (English / Yoruba)
    'apala': ('Apala', 'apala'),
    'àpàlà': ('Apala', 'àpàlà'),
    'nigerian apala': ('Apala', 'nigerian apala'),
    'yoruba apala': ('Apala', 'yoruba apala'),
    'apala music': ('Apala', 'apala music'),

    ## Subgéneros
    'apala classic': ('Apala', 'apala classic'),
    'apala modern': ('Apala', 'apala modern'),
    'apala fusion': ('Apala', 'apala fusion'),

    ## Por región
    'lagos apala': ('Apala', 'lagos apala'),
    'abeokuta apala': ('Apala', 'abeokuta apala'),

    ## En yoruba
    'orin àpàlà': ('Apala', 'orin àpàlà'),

    ###############################################################################
    # SAKARA (Regional - Nigeria)
    ###############################################################################
    ## Sakara General (English / Yoruba)
    'sakara': ('Sakara', 'sakara'),
    'nigerian sakara': ('Sakara', 'nigerian sakara'),
    'yoruba sakara': ('Sakara', 'yoruba sakara'),
    'sakara music': ('Sakara', 'sakara music'),

    ## Subgéneros
    'sakara classic': ('Sakara', 'sakara classic'),
    'sakara modern': ('Sakara', 'sakara modern'),
    'sakara fusion': ('Sakara', 'sakara fusion'),

    ## Por región
    'lagos sakara': ('Sakara', 'lagos sakara'),
    'ibadan sakara': ('Sakara', 'ibadan sakara'),

    ## En yoruba
    'orin sakara': ('Sakara', 'orin sakara'),

    ###############################################################################
    # OGENE (Regional - Nigeria)
    ###############################################################################
    ## Ogene General (English / Igbo)
    'ogene': ('Ogene', 'ogene'),
    'igbo ogene': ('Ogene', 'igbo ogene'),
    'nigerian ogene': ('Ogene', 'nigerian ogene'),
    'ogene music': ('Ogene', 'ogene music'),

    ## Subgéneros
    'ogene classic': ('Ogene', 'ogene classic'),
    'ogene modern': ('Ogene', 'ogene modern'),
    'ogene pop': ('Ogene', 'ogene pop'),
    'ogene fusion': ('Ogene', 'ogene fusion'),

    ## Por región
    'enugu ogene': ('Ogene', 'enugu ogene'),
    'onitsha ogene': ('Ogene', 'onitsha ogene'),
    'aba ogene': ('Ogene', 'aba ogene'),

    ## En igbo
    'ogene igbo': ('Ogene', 'ogene igbo'),
    'egwu ogene': ('Ogene', 'egwu ogene'),

    ###############################################################################
    # ISICATHAMIYA (Regional - Sudáfrica)
    ###############################################################################
    ## Isicathamiya General (English / Zulu)
    'isicathamiya': ('Isicathamiya', 'isicathamiya'),
    'south african isicathamiya': ('Isicathamiya', 'south african isicathamiya'),
    'zulu isicathamiya': ('Isicathamiya', 'zulu isicathamiya'),
    'isicathamiya music': ('Isicathamiya', 'isicathamiya music'),
    'cothoza music': ('Isicathamiya', 'cothoza music'),

    ## Subgéneros
    'isicathamiya classic': ('Isicathamiya', 'isicathamiya classic'),
    'isicathamiya modern': ('Isicathamiya', 'isicathamiya modern'),
    'isicathamiya pop': ('Isicathamiya', 'isicathamiya pop'),
    'isicathamiya gospel': ('Isicathamiya', 'isicathamiya gospel'),

    ## Por región
    'durban isicathamiya': ('Isicathamiya', 'durban isicathamiya'),
    'johannesburg isicathamiya': ('Isicathamiya', 'johannesburg isicathamiya'),
    'kzn isicathamiya': ('Isicathamiya', 'kzn isicathamiya'),

    ## En zulu
    'ingoma yesicathamiya': ('Isicathamiya', 'ingoma yesicathamiya'),
    'umculo wesizulu': ('Isicathamiya', 'umculo wesizulu'),

    ###############################################################################
    # MBUBE (Regional - Sudáfrica)
    ###############################################################################
    ## Mbube General (English / Zulu)
    'mbube': ('Mbube', 'mbube'),
    'south african mbube': ('Mbube', 'south african mbube'),
    'zulu mbube': ('Mbube', 'zulu mbube'),
    'mbube music': ('Mbube', 'mbube music'),
    'mbube choral': ('Mbube', 'mbube choral'),

    ## Subgéneros
    'mbube classic': ('Mbube', 'mbube classic'),
    'mbube modern': ('Mbube', 'mbube modern'),
    'mbube pop': ('Mbube', 'mbube pop'),
    'mbube gospel': ('Mbube', 'mbube gospel'),

    ## Por región
    'johannesburg mbube': ('Mbube', 'johannesburg mbube'),
    'durban mbube': ('Mbube', 'durban mbube'),
    'kzn mbube': ('Mbube', 'kzn mbube'),

    ## En zulu
    'ingoma yombube': ('Mbube', 'ingoma yombube'),
    'umculo wesiZulu': ('Mbube', 'umculo wesiZulu'),

    ###############################################################################
    # MASKANDI (Regional - Sudáfrica)
    ###############################################################################
    ## Maskandi General (English / Zulu)
    'maskandi': ('Maskandi', 'maskandi'),
    'south african maskandi': ('Maskandi', 'south african maskandi'),
    'zulu maskandi': ('Maskandi', 'zulu maskandi'),
    'maskandi music': ('Maskandi', 'maskandi music'),
    'izihlabo': ('Maskandi', 'izihlabo'),

    ## Subgéneros
    'maskandi classic': ('Maskandi', 'maskandi classic'),
    'maskandi modern': ('Maskandi', 'maskandi modern'),
    'maskandi pop': ('Maskandi', 'maskandi pop'),
    'maskandi dance': ('Maskandi', 'maskandi dance'),
    'maskandi guitar': ('Maskandi', 'maskandi guitar'),

    ## Fusión
    'maskandi fusion': ('Maskandi', 'maskandi fusion'),
    'maskandi hip hop': ('Maskandi', 'maskandi hip hop'),
    'maskandi maskandi': ('Maskandi', 'maskandi maskandi'),

    ## Por región
    'durban maskandi': ('Maskandi', 'durban maskandi'),
    'johannesburg maskandi': ('Maskandi', 'johannesburg maskandi'),
    'kzn maskandi': ('Maskandi', 'kzn maskandi'),

    ## En zulu
    'umculo wamaskandi': ('Maskandi', 'umculo wamaskandi'),
    'isishameni': ('Maskandi', 'isishameni'),

    ###############################################################################
    # MBAQANGA (Regional - Sudáfrica)
    ###############################################################################
    ## Mbaqanga General (English / Zulu)
    'mbaqanga': ('Mbaqanga', 'mbaqanga'),
    'south african mbaqanga': ('Mbaqanga', 'south african mbaqanga'),
    'zulu mbaqanga': ('Mbaqanga', 'zulu mbaqanga'),
    'mbaqanga music': ('Mbaqanga', 'mbaqanga music'),

    ## Subgéneros
    'mbaqanga classic': ('Mbaqanga', 'mbaqanga classic'),
    'mbaqanga modern': ('Mbaqanga', 'mbaqanga modern'),
    'mbaqanga pop': ('Mbaqanga', 'mbaqanga pop'),
    'mbaqanga dance': ('Mbaqanga', 'mbaqanga dance'),
    'mbaqanga soul': ('Mbaqanga', 'mbaqanga soul'),

    ## Fusión
    'mbaqanga fusion': ('Mbaqanga', 'mbaqanga fusion'),
    'mbaqanga jazz': ('Mbaqanga', 'mbaqanga jazz'),
    'mbaqanga mbaqanga': ('Mbaqanga', 'mbaqanga mbaqanga'),

    ## Por región
    'soweto mbaqanga': ('Mbaqanga', 'soweto mbaqanga'),
    'johannesburg mbaqanga': ('Mbaqanga', 'johannesburg mbaqanga'),
    'durban mbaqanga': ('Mbaqanga', 'durban mbaqanga'),

    ## En zulu
    'umculo womqangala': ('Mbaqanga', 'umculo womqangala'),
    'isicathulo': ('Mbaqanga', 'isicathulo'),

    ###############################################################################
    # KWAITO (Regional - Sudáfrica)
    ###############################################################################
    ## Kwaito General (English / Zulu / Sotho)
    'kwaito': ('Kwaito', 'kwaito'),
    'south african kwaito': ('Kwaito', 'south african kwaito'),
    'kwaito music': ('Kwaito', 'kwaito music'),
    'umculo wekwaito': ('Kwaito', 'umculo wekwaito'),

    ## Subgéneros
    'kwaito classic': ('Kwaito', 'kwaito classic'),
    'kwaito modern': ('Kwaito', 'kwaito modern'),
    'kwaito house': ('Kwaito', 'kwaito house'),
    'kwaito pop': ('Kwaito', 'kwaito pop'),
    'kwaito dance': ('Kwaito', 'kwaito dance'),
    'kwaito gospel': ('Kwaito', 'kwaito gospel'),

    ## Fusión
    'kwaito fusion': ('Kwaito', 'kwaito fusion'),
    'kwaito hip hop': ('Kwaito', 'kwaito hip hop'),
    'kwaito amapiano': ('Kwaito', 'kwaito amapiano'),

    ## Por región
    'soweto kwaito': ('Kwaito', 'soweto kwaito'),
    'johannesburg kwaito': ('Kwaito', 'johannesburg kwaito'),
    'pretoria kwaito': ('Kwaito', 'pretoria kwaito'),
    'durban kwaito': ('Kwaito', 'durban kwaito'),
    'cape town kwaito': ('Kwaito', 'cape town kwaito'),

    ## En zulu / sotho / tsotsitaal
    'kwaito tsotsitaal': ('Kwaito', 'kwaito tsotsitaal'),
    'kwaito kasi': ('Kwaito', 'kwaito kasi'),
    'mmino wa kwaito': ('Kwaito', 'mmino wa kwaito'),

    ###############################################################################
    # AFRO-SOUL (Regional - Sudáfrica)
    ###############################################################################
    ## Afro-soul General (English / Zulu / Xhosa)
    'afro soul': ('Afro-soul', 'afro soul'),
    'afrosoul': ('Afro-soul', 'afrosoul'),
    'south african afro soul': ('Afro-soul', 'south african afro soul'),
    'afro soul music': ('Afro-soul', 'afro soul music'),

    ## Subgéneros
    'afro soul classic': ('Afro-soul', 'afro soul classic'),
    'afro soul modern': ('Afro-soul', 'afro soul modern'),
    'afro soul pop': ('Afro-soul', 'afro soul pop'),
    'afro soul r&b': ('Afro-soul', 'afro soul r&b'),

    ## Fusión
    'afro soul fusion': ('Afro-soul', 'afro soul fusion'),
    'afro soul jazz': ('Afro-soul', 'afro soul jazz'),
    'afro soul gospel': ('Afro-soul', 'afro soul gospel'),

    ## Por región
    'johannesburg afro soul': ('Afro-soul', 'johannesburg afro soul'),
    'cape town afro soul': ('Afro-soul', 'cape town afro soul'),
    'durban afro soul': ('Afro-soul', 'durban afro soul'),

    ## En zulu / xhosa
    'umculo we afro soul': ('Afro-soul', 'umculo we afro soul'),
    'afro soul yaseMzantsi': ('Afro-soul', 'afro soul yaseMzantsi'),

    ###############################################################################
    # BONGO (Regional - Tanzania) [Precursor de Bongo Flava]
    ###############################################################################
    ## Bongo General (English / Swahili)
    'bongo': ('Bongo', 'bongo'),
    'tanzanian bongo': ('Bongo', 'tanzanian bongo'),
    'bongo music': ('Bongo', 'bongo music'),
    'muziki wa bongo': ('Bongo', 'muziki wa bongo'),

    ## Subgéneros
    'bongo classic': ('Bongo', 'bongo classic'),
    'bongo modern': ('Bongo', 'bongo modern'),
    'bongo pop': ('Bongo', 'bongo pop'),
    'bongo dance': ('Bongo', 'bongo dance'),
    'bongo r&b': ('Bongo', 'bongo r&b'),
    'bongo hip hop': ('Bongo', 'bongo hip hop'),

    ## Por región
    'dar es salaam bongo': ('Bongo', 'dar es salaam bongo'),
    'arusha bongo': ('Bongo', 'arusha bongo'),
    'mwanza bongo': ('Bongo', 'mwanza bongo'),
    'zanzibar bongo': ('Bongo', 'zanzibar bongo'),

    ## En swahili
    'bongo flava ya zamani': ('Bongo', 'bongo flava ya zamani'),
    'muziki wa bongo': ('Bongo', 'muziki wa bongo'),
    'bongo beats': ('Bongo', 'bongo beats'),

    ###############################################################################
    # OCEANÍA - Escenas regionales (indígenas y del Pacífico)
    ###############################################################################

    # NOTA: Australia y Nueva Zelanda como países occidentales tienen pop/rock genérico
    # ya cubierto en las secciones globales. Aquí nos enfocamos en las escenas
    # indígenas y de las islas del Pacífico con identidad propia.

    ###############################################################################
    # Māori Pop/Rock (Regional - Nueva Zelanda / Aotearoa)
    ###############################################################################
    ## Māori Pop General (English / Māori)
    'maori pop': ('Māori Pop/Rock', 'maori pop'),
    'māori pop': ('Māori Pop/Rock', 'māori pop'),
    'pop māori': ('Māori Pop/Rock', 'pop māori'),
    'aotearoa pop': ('Māori Pop/Rock', 'aotearoa pop'),
    'waiata': ('Māori Pop/Rock', 'waiata'),
    'waiata pop': ('Māori Pop/Rock', 'waiata pop'),
    'waiata r&b': ('Māori Pop/Rock', 'waiata r&b'),
    'waiata hip hop': ('Māori Pop/Rock', 'waiata hip hop'),

    ## Māori Rock
    'maori rock': ('Māori Pop/Rock', 'maori rock'),
    'māori rock': ('Māori Pop/Rock', 'māori rock'),
    'rock māori': ('Māori Pop/Rock', 'rock māori'),
    'aotearoa rock': ('Māori Pop/Rock', 'aotearoa rock'),

    ### Subgéneros de rock
    'maori alternative rock': ('Māori Pop/Rock', 'maori alternative rock'),
    'maori indie rock': ('Māori Pop/Rock', 'maori indie rock'),
    'maori metal': ('Māori Pop/Rock', 'maori metal'),

    ## Māori Hip Hop / Rap
    'maori hip hop': ('Māori Pop/Rock', 'maori hip hop'),
    'maori rap': ('Māori Pop/Rock', 'maori rap'),
    'aotearoa hip hop': ('Māori Pop/Rock', 'aotearoa hip hop'),
    'waiata rap': ('Māori Pop/Rock', 'waiata rap'),

    ## Māori R&B / Soul
    'maori r&b': ('Māori Pop/Rock', 'maori r&b'),
    'maori soul': ('Māori Pop/Rock', 'maori soul'),
    'waiata soul': ('Māori Pop/Rock', 'waiata soul'),

    ## Fusión tradicional
    'maori fusion': ('Māori Pop/Rock', 'maori fusion'),
    'taonga puoro fusion': ('Māori Pop/Rock', 'taonga puoro fusion'),
    'haka fusion': ('Māori Pop/Rock', 'haka fusion'),
    'kapa haka pop': ('Māori Pop/Rock', 'kapa haka pop'),

    ## Pacific reggae (NZ version)
    'pacific reggae nz': ('Māori Pop/Rock', 'pacific reggae nz'),
    'new zealand reggae': ('Māori Pop/Rock', 'new zealand reggae'),

    ## Por región (Aotearoa)
    'auckland maori pop': ('Māori Pop/Rock', 'auckland maori pop'),
    'wellington maori pop': ('Māori Pop/Rock', 'wellington maori pop'),
    'rotorua maori pop': ('Māori Pop/Rock', 'rotorua maori pop'),
    'gisborne maori pop': ('Māori Pop/Rock', 'gisborne maori pop'),

    ## En maorí
    'waiata Māori': ('Māori Pop/Rock', 'waiata Māori'),
    'puoro Māori': ('Māori Pop/Rock', 'puoro Māori'),
    'waiata taketake': ('Māori Pop/Rock', 'waiata taketake'),

    ###############################################################################
    # Pasifika Pop/Rock (Regional - Islas del Pacífico: Samoa, Tonga, Fiji, etc.)
    ###############################################################################
    ## Pasifika Pop General (English / Pacific languages)
    'pasifika pop': ('Pasifika Pop/Rock', 'pasifika pop'),
    'pacific pop': ('Pasifika Pop/Rock', 'pacific pop'),
    'pop pasifika': ('Pasifika Pop/Rock', 'pop pasifika'),
    'island pop': ('Pasifika Pop/Rock', 'island pop'),
    'south pacific pop': ('Pasifika Pop/Rock', 'south pacific pop'),

    ## Fiji Pop / Rock
    'fiji pop': ('Pasifika Pop/Rock', 'fiji pop'),
    'fijian pop': ('Pasifika Pop/Rock', 'fijian pop'),
    'fiji rock': ('Pasifika Pop/Rock', 'fiji rock'),
    'fijian rock': ('Pasifika Pop/Rock', 'fijian rock'),
    'viti pop': ('Pasifika Pop/Rock', 'viti pop'),
    'meke fusion': ('Pasifika Pop/Rock', 'meke fusion'),

    ## Samoa Pop / Rock
    'samoan pop': ('Pasifika Pop/Rock', 'samoan pop'),
    'samoa pop': ('Pasifika Pop/Rock', 'samoa pop'),
    'samoan rock': ('Pasifika Pop/Rock', 'samoan rock'),
    'fuego samoa': ('Pasifika Pop/Rock', 'fuego samoa'),

    ## Tonga Pop / Rock
    'tongan pop': ('Pasifika Pop/Rock', 'tongan pop'),
    'tonga pop': ('Pasifika Pop/Rock', 'tonga pop'),
    'tongan rock': ('Pasifika Pop/Rock', 'tongan rock'),
    'kailao fusion': ('Pasifika Pop/Rock', 'kailao fusion'),

    ## Cook Islands / Tahiti / Niue, etc.
    'cook islands pop': ('Pasifika Pop/Rock', 'cook islands pop'),
    'tahitian pop': ('Pasifika Pop/Rock', 'tahitian pop'),
    'tahitian rock': ('Pasifika Pop/Rock', 'tahitian rock'),
    'niuean pop': ('Pasifika Pop/Rock', 'niuean pop'),
    'niuean rock': ('Pasifika Pop/Rock', 'niuean rock'),

    ## Pasifika Hip Hop / Rap
    'pasifika hip hop': ('Pasifika Pop/Rock', 'pasifika hip hop'),
    'pacific hip hop': ('Pasifika Pop/Rock', 'pacific hip hop'),
    'fiji hip hop': ('Pasifika Pop/Rock', 'fiji hip hop'),
    'samoan hip hop': ('Pasifika Pop/Rock', 'samoan hip hop'),
    'tongan hip hop': ('Pasifika Pop/Rock', 'tongan hip hop'),
    'pacific rap': ('Pasifika Pop/Rock', 'pacific rap'),

    ## Pasifika R&B / Soul
    'pasifika r&b': ('Pasifika Pop/Rock', 'pasifika r&b'),
    'pacific r&b': ('Pasifika Pop/Rock', 'pacific r&b'),
    'pacific soul': ('Pasifika Pop/Rock', 'pacific soul'),

    ## Pacific Reggae / Roots
    'pacific reggae': ('Pasifika Pop/Rock', 'pacific reggae'),
    'island reggae': ('Pasifika Pop/Rock', 'island reggae'),
    'pacific roots': ('Pasifika Pop/Rock', 'pacific roots'),
    'fiji reggae': ('Pasifika Pop/Rock', 'fiji reggae'),
    'samoa reggae': ('Pasifika Pop/Rock', 'samoa reggae'),
    'tonga reggae': ('Pasifika Pop/Rock', 'tonga reggae'),

    ## Pacific Dance / Electronic
    'pacific dance': ('Pasifika Pop/Rock', 'pacific dance'),
    'pacific edm': ('Pasifika Pop/Rock', 'pacific edm'),
    'island house': ('Pasifika Pop/Rock', 'island house'),
    'tropical house pacific': ('Pasifika Pop/Rock', 'tropical house pacific'),

    ## En idiomas del Pacífico
    'musika fiji': ('Pasifika Pop/Rock', 'musika fiji'),
    'pehe fiji': ('Pasifika Pop/Rock', 'pehe fiji'),
    'pese samoa': ('Pasifika Pop/Rock', 'pese samoa'),
    'hiva tonga': ('Pasifika Pop/Rock', 'hiva tonga'),
    'ute cook islands': ('Pasifika Pop/Rock', 'ute cook islands'),
    'himene tahiti': ('Pasifika Pop/Rock', 'himene tahiti'),

    ###############################################################################
    # Papua New Guinea Pop/Rock (Regional - PNG)
    ###############################################################################
    ## PNG Pop General (English / Tok Pisin)
    'png pop': ('PNG Pop/Rock', 'png pop'),
    'papua new guinea pop': ('PNG Pop/Rock', 'papua new guinea pop'),
    'pop bilong PNG': ('PNG Pop/Rock', 'pop bilong PNG'),
    'tok pisin pop': ('PNG Pop/Rock', 'tok pisin pop'),

    ## PNG Rock
    'png rock': ('PNG Pop/Rock', 'png rock'),
    'papua new guinea rock': ('PNG Pop/Rock', 'papua new guinea rock'),
    'rock bilong PNG': ('PNG Pop/Rock', 'rock bilong PNG'),

    ### Subgéneros de PNG rock
    'png alternative rock': ('PNG Pop/Rock', 'png alternative rock'),
    'png indie rock': ('PNG Pop/Rock', 'png indie rock'),
    'png metal': ('PNG Pop/Rock', 'png metal'),

    ## PNG Hip Hop / Rap
    'png hip hop': ('PNG Pop/Rock', 'png hip hop'),
    'png rap': ('PNG Pop/Rock', 'png rap'),
    'rap bilong PNG': ('PNG Pop/Rock', 'rap bilong PNG'),
    'png urban music': ('PNG Pop/Rock', 'png urban music'),

    ## PNG R&B
    'png r&b': ('PNG Pop/Rock', 'png r&b'),
    'png rnb': ('PNG Pop/Rock', 'png rnb'),

    ## PNG Reggae
    'png reggae': ('PNG Pop/Rock', 'png reggae'),
    'papua new guinea reggae': ('PNG Pop/Rock', 'papua new guinea reggae'),
    'reggae bilong PNG': ('PNG Pop/Rock', 'reggae bilong PNG'),

    ## PNG Stringband / Acoustic
    'png stringband': ('PNG Pop/Rock', 'png stringband'),
    'stringband music': ('PNG Pop/Rock', 'stringband music'),
    'png acoustic': ('PNG Pop/Rock', 'png acoustic'),

    ## Fusión tradicional
    'png fusion': ('PNG Pop/Rock', 'png fusion'),
    'singsing fusion': ('PNG Pop/Rock', 'singsing fusion'),
    'garamut fusion': ('PNG Pop/Rock', 'garamut fusion'),

    ## Por región
    'port moresby pop': ('PNG Pop/Rock', 'port moresby pop'),
    'lae pop': ('PNG Pop/Rock', 'lae pop'),
    'mount hagen pop': ('PNG Pop/Rock', 'mount hagen pop'),
    'goroka pop': ('PNG Pop/Rock', 'goroka pop'),
    'rabaul pop': ('PNG Pop/Rock', 'rabaul pop'),

    ## En tok pisin
    'musik bilong PNG': ('PNG Pop/Rock', 'musik bilong PNG'),
    'singsing bilong tumbuna': ('PNG Pop/Rock', 'singsing bilong tumbuna'),
    'kundu drums': ('PNG Pop/Rock', 'kundu drums'),

    ###############################################################################
    # Hawaiian Pop/Rock (Regional - Hawái)
    ###############################################################################
    ## Hawaiian Pop General (English / Hawaiian)
    'hawaiian pop': ('Hawaiian Pop/Rock', 'hawaiian pop'),
    'pop hawaiiano': ('Hawaiian Pop/Rock', 'pop hawaiiano'),
    'hawaii pop': ('Hawaiian Pop/Rock', 'hawaii pop'),
    'mele pop': ('Hawaiian Pop/Rock', 'mele pop'),
    'hapa haole': ('Hawaiian Pop/Rock', 'hapa haole'),

    ## Jawaiian (Hawaiian reggae)
    'jawaiian': ('Hawaiian Pop/Rock', 'jawaiian'),
    'hawaiian reggae': ('Hawaiian Pop/Rock', 'hawaiian reggae'),
    'island reggae hawaii': ('Hawaiian Pop/Rock', 'island reggae hawaii'),

    ## Hawaiian Rock
    'hawaiian rock': ('Hawaiian Pop/Rock', 'hawaiian rock'),
    'rock hawaiiano': ('Hawaiian Pop/Rock', 'rock hawaiiano'),
    'hawaii rock': ('Hawaiian Pop/Rock', 'hawaii rock'),

    ### Subgéneros de Hawaiian rock
    'hawaiian alternative rock': ('Hawaiian Pop/Rock', 'hawaiian alternative rock'),
    'hawaiian indie rock': ('Hawaiian Pop/Rock', 'hawaiian indie rock'),
    'hawaiian metal': ('Hawaiian Pop/Rock', 'hawaiian metal'),

    ## Hawaiian Hip Hop / Rap
    'hawaiian hip hop': ('Hawaiian Pop/Rock', 'hawaiian hip hop'),
    'hawaiian rap': ('Hawaiian Pop/Rock', 'hawaiian rap'),
    'rap hawaiiano': ('Hawaiian Pop/Rock', 'rap hawaiiano'),
    'hawaii hip hop': ('Hawaiian Pop/Rock', 'hawaii hip hop'),

    ## Hawaiian R&B / Soul
    'hawaiian r&b': ('Hawaiian Pop/Rock', 'hawaiian r&b'),
    'hawaiian soul': ('Hawaiian Pop/Rock', 'hawaiian soul'),

    ## Slack key guitar / Ki ho'alu
    'slack key guitar': ('Hawaiian Pop/Rock', 'slack key guitar'),
    'ki hoalu': ('Hawaiian Pop/Rock', 'ki hoalu'),
    'slack key fusion': ('Hawaiian Pop/Rock', 'slack key fusion'),

    ## Hula / Mele trad
    'hula fusion': ('Hawaiian Pop/Rock', 'hula fusion'),
    'mele hula': ('Hawaiian Pop/Rock', 'mele hula'),
    'oli fusion': ('Hawaiian Pop/Rock', 'oli fusion'),

    ## Fusión contemporánea
    'hawaiian fusion': ('Hawaiian Pop/Rock', 'hawaiian fusion'),
    'pacific fusion hawaii': ('Hawaiian Pop/Rock', 'pacific fusion hawaii'),

    ## Por región
    'honolulu pop': ('Hawaiian Pop/Rock', 'honolulu pop'),
    'hilo pop': ('Hawaiian Pop/Rock', 'hilo pop'),
    'maui pop': ('Hawaiian Pop/Rock', 'maui pop'),
    'kauai pop': ('Hawaiian Pop/Rock', 'kauai pop'),
    'kona pop': ('Hawaiian Pop/Rock', 'kona pop'),

    ## En hawaiano
    'mele Hawaiʻi': ('Hawaiian Pop/Rock', 'mele Hawaiʻi'),
    'leo Hawaiʻi': ('Hawaiian Pop/Rock', 'leo Hawaiʻi'),
    'pila kī': ('Hawaiian Pop/Rock', 'pila kī'),

    ###############################################################################
    # Aboriginal Australian Pop/Rock (Regional - Australia indígena)
    ###############################################################################
    ## Aboriginal Pop General (English / Indigenous Australian languages)
    'indigenous australian pop': ('Aboriginal Australian Pop/Rock', 'indigenous australian pop'),
    'aboriginal pop': ('Aboriginal Australian Pop/Rock', 'aboriginal pop'),
    'pop aborigen australiano': ('Aboriginal Australian Pop/Rock', 'pop aborigen australiano'),
    'blak pop': ('Aboriginal Australian Pop/Rock', 'blak pop'),

    ## Aboriginal Rock
    'indigenous australian rock': ('Aboriginal Australian Pop/Rock', 'indigenous australian rock'),
    'aboriginal rock': ('Aboriginal Australian Pop/Rock', 'aboriginal rock'),
    'rock aborigen australiano': ('Aboriginal Australian Pop/Rock', 'rock aborigen australiano'),
    'blak rock': ('Aboriginal Australian Pop/Rock', 'blak rock'),

    ### Subgéneros de Aboriginal rock
    'indigenous alternative rock': ('Aboriginal Australian Pop/Rock', 'indigenous alternative rock'),
    'indigenous indie rock': ('Aboriginal Australian Pop/Rock', 'indigenous indie rock'),
    'indigenous metal': ('Aboriginal Australian Pop/Rock', 'indigenous metal'),

    ## Aboriginal Hip Hop / Rap
    'indigenous australian hip hop': ('Aboriginal Australian Pop/Rock', 'indigenous australian hip hop'),
    'aboriginal hip hop': ('Aboriginal Australian Pop/Rock', 'aboriginal hip hop'),
    'aboriginal rap': ('Aboriginal Australian Pop/Rock', 'aboriginal rap'),
    'blak hip hop': ('Aboriginal Australian Pop/Rock', 'blak hip hop'),
    'indigenous rap': ('Aboriginal Australian Pop/Rock', 'indigenous rap'),

    ## Aboriginal R&B / Soul
    'indigenous r&b': ('Aboriginal Australian Pop/Rock', 'indigenous r&b'),
    'aboriginal r&b': ('Aboriginal Australian Pop/Rock', 'aboriginal r&b'),
    'blak soul': ('Aboriginal Australian Pop/Rock', 'blak soul'),

    ## Didgeridoo fusion
    'didgeridoo fusion': ('Aboriginal Australian Pop/Rock', 'didgeridoo fusion'),
    'yidaki fusion': ('Aboriginal Australian Pop/Rock', 'yidaki fusion'),
    'didgeridoo pop': ('Aboriginal Australian Pop/Rock', 'didgeridoo pop'),
    'didgeridoo rock': ('Aboriginal Australian Pop/Rock', 'didgeridoo rock'),

    ## Clapstick / Traditional fusion
    'clapstick fusion': ('Aboriginal Australian Pop/Rock', 'clapstick fusion'),
    'bilma fusion': ('Aboriginal Australian Pop/Rock', 'bilma fusion'),
    'bunggul fusion': ('Aboriginal Australian Pop/Rock', 'bunggul fusion'),

    ## Aboriginal reggae
    'indigenous reggae': ('Aboriginal Australian Pop/Rock', 'indigenous reggae'),
    'aboriginal reggae': ('Aboriginal Australian Pop/Rock', 'aboriginal reggae'),

    ## Por región / nación
    'yolngu pop': ('Aboriginal Australian Pop/Rock', 'yolngu pop'),
    'pitjantjatjara pop': ('Aboriginal Australian Pop/Rock', 'pitjantjatjara pop'),
    'arnhem land pop': ('Aboriginal Australian Pop/Rock', 'arnhem land pop'),
    'central desert pop': ('Aboriginal Australian Pop/Rock', 'central desert pop'),
    'koori pop': ('Aboriginal Australian Pop/Rock', 'koori pop'),
    'murri pop': ('Aboriginal Australian Pop/Rock', 'murri pop'),
    'noongar pop': ('Aboriginal Australian Pop/Rock', 'noongar pop'),
    'palawa pop': ('Aboriginal Australian Pop/Rock', 'palawa pop'),

    ## En lenguas aborígenes
    'inma': ('Aboriginal Australian Pop/Rock', 'inma'),
    'wangga': ('Aboriginal Australian Pop/Rock', 'wangga'),
    'djunga': ('Aboriginal Australian Pop/Rock', 'djunga'),

    ###############################################################################
    # Pacific Electronica / Island EDM (Regional - toda Oceanía)
    ###############################################################################
    ## Pacific Electronica General
    'pacific electronica': ('Pacific Electronica', 'pacific electronica'),
    'island edm': ('Pacific Electronica', 'island edm'),
    'pacific edm': ('Pacific Electronica', 'pacific edm'),
    'oceania electronica': ('Pacific Electronica', 'oceania electronica'),
    'tropical house pacific': ('Pacific Electronica', 'tropical house pacific'),

    ## Subgéneros
    'pacific house': ('Pacific Electronica', 'pacific house'),
    'pacific techno': ('Pacific Electronica', 'pacific techno'),
    'pacific trance': ('Pacific Electronica', 'pacific trance'),
    'pacific ambient': ('Pacific Electronica', 'pacific ambient'),
    'pacific chill': ('Pacific Electronica', 'pacific chill'),

    ## Fusión con elementos tradicionales
    'pacific tribal house': ('Pacific Electronica', 'pacific tribal house'),
    'pacific ethno electronica': ('Pacific Electronica', 'pacific ethno electronica'),
    'didgeridoo electronica': ('Pacific Electronica', 'didgeridoo electronica'),
    'pacific drum and bass': ('Pacific Electronica', 'pacific drum and bass'),

    ## Por región
    'hawaiian electronica': ('Pacific Electronica', 'hawaiian electronica'),
    'maori electronica': ('Pacific Electronica', 'maori electronica'),
    'fiji electronica': ('Pacific Electronica', 'fiji electronica'),
    'png electronica': ('Pacific Electronica', 'png electronica'),
    'samoa electronica': ('Pacific Electronica', 'samoa electronica'),
    'tahitian electronica': ('Pacific Electronica', 'tahitian electronica'),

    ## Pacific DJ / Festival culture
    'pacific dj': ('Pacific Electronica', 'pacific dj'),
    'island festival music': ('Pacific Electronica', 'island festival music'),
    'pacific beach house': ('Pacific Electronica', 'pacific beach house'),

    ###############################################################################
    # Torres Strait Islander Pop/Rock (Regional - Islas del Estrecho de Torres)
    ###############################################################################
    ## Torres Strait Islander General
    'torres strait pop': ('Torres Strait Islander Pop/Rock', 'torres strait pop'),
    'tsi pop': ('Torres Strait Islander Pop/Rock', 'tsi pop'),
    'islander pop': ('Torres Strait Islander Pop/Rock', 'islander pop'),
    'pop del estrecho de torres': ('Torres Strait Islander Pop/Rock', 'pop del estrecho de torres'),

    ## Torres Strait Rock
    'torres strait rock': ('Torres Strait Islander Pop/Rock', 'torres strait rock'),
    'tsi rock': ('Torres Strait Islander Pop/Rock', 'tsi rock'),

    ## Torres Strait Hip Hop / Rap
    'torres strait hip hop': ('Torres Strait Islander Pop/Rock', 'torres strait hip hop'),
    'tsi rap': ('Torres Strait Islander Pop/Rock', 'tsi rap'),

    ## Fusión con danza tradicional
    'warup fusion': ('Torres Strait Islander Pop/Rock', 'warup fusion'),
    'kaber fusion': ('Torres Strait Islander Pop/Rock', 'kaber fusion'),

    ## En lengua del estrecho de Torres
    'ailan pop': ('Torres Strait Islander Pop/Rock', 'ailan pop'),
    'yumi musik': ('Torres Strait Islander Pop/Rock', 'yumi musik'),
}

# ============================================================================
# STOPWORDS PARA GÉNEROS (OK)
# ============================================================================

GENRE_STOPWORDS = {
    'american', 'british', 'canadian', 'australian', 'indian', 'korean',
    'japanese', 'mexican', 'spanish', 'french', 'german', 'italian',
    'brazilian', 'argentine', 'colombian', 'chilean', 'peruvian',
    'venezuelan', 'cuban', 'dominican', 'african', 'nigerian',
    'south african', 'kenyan', 'egyptian', 'moroccan', 'israeli',
    'turkish', 'russian', 'ukrainian', 'polish', 'swedish', 'norwegian',
    'danish', 'finnish', 'dutch', 'belgian', 'swiss', 'austrian',
    'portuguese', 'greek', 'irish', 'scottish', 'welsh', 'english',
    'famous', 'popular', 'well-known', 'acclaimed', 'award-winning',
    'multi-platinum', 'grammy', 'grammy-winning', 'oscar', 'oscar-winning',
    'best-selling', 'successful', 'influential', 'legendary', 'iconic'
}

# ============================================================================
# DICCIONARIO DE PRIORIDAD DE GÉNERO POR PAÍS
# ============================================================================
COUNTRY_GENRE_PRIORITY = {
    # América del Norte
    "United States": [
        "Pop", "Hip-Hop/Rap", "R&B/Soul", "Country", "Rock",
        "Alternative", "Electrónica/Dance", "Reggaetón/Trap Latino",
        "Jazz/Blues", "Classical"
    ],
    "Canada": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Electrónica/Dance", "R&B/Soul", "Reggaetón/Trap Latino",
        "Country", "Classical"
    ],
    "Mexico": [
        "Regional Mexicano", "Reggaetón/Trap Latino", "Pop",
        "Bachata", "Cumbia", "Rock", "Tropical/Salsa/Merengue/Bolero",
        "Classical"
    ],

    # Centroamérica
    "Guatemala": ["Reggaetón/Trap Latino", "Bachata", "Cumbia", "Dancehall/Reggae", "Tropical/Salsa/Merengue/Bolero"],
    "Honduras": ["Reggaetón/Trap Latino", "Bachata", "Cumbia", "Dancehall/Reggae", "Tropical/Salsa/Merengue/Bolero"],
    "El Salvador": ["Reggaetón/Trap Latino", "Bachata", "Cumbia", "Dancehall/Reggae"],
    "Nicaragua": ["Reggaetón/Trap Latino", "Bachata", "Cumbia", "Dancehall/Reggae"],
    "Costa Rica": ["Reggaetón/Trap Latino", "Pop", "Bachata", "Cumbia", "Dancehall/Reggae", "Tropical/Salsa/Merengue/Bolero"],
    "Panama": [
        "Reggaetón/Trap Latino", "Dancehall/Reggae",
        "Tropical/Salsa/Merengue/Bolero", "Cumbia", "Pop"
    ],
    "Belize": ["Dancehall/Reggae", "Reggaetón/Trap Latino", "Pop", "Cumbia"],

    # Caribe
    "Jamaica": ["Dancehall/Reggae"],
    "Puerto Rico": ["Reggaetón/Trap Latino", "Pop"],
    "Dominican Republic": [
        "Reggaetón/Trap Latino", "Bachata", "Tropical/Salsa/Merengue/Bolero", "Dancehall/Reggae"
    ],
    "Cuba": [
        "Reggaetón/Trap Latino", "Tropical/Salsa/Merengue/Bolero",
        "Pop", "Jazz/Blues"
    ],
    "Haiti": ["Reggaetón/Trap Latino", "Tropical/Salsa/Merengue/Bolero", "Pop"],
    "Trinidad and Tobago": [
        "Tropical/Salsa/Merengue/Bolero", "Dancehall/Reggae",
        "Reggaetón/Trap Latino", "Pop"
    ],
    "Bahamas": ["Pop", "Dancehall/Reggae", "R&B/Soul"],
    "Barbados": ["Pop", "Dancehall/Reggae", "R&B/Soul", "Reggaetón/Trap Latino"],
    "Saint Lucia": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],
    "Grenada": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],
    "Saint Vincent and the Grenadines": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],
    "Antigua and Barbuda": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],
    "Dominica": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],
    "Saint Kitts and Nevis": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],

    # Sudamérica
    "Colombia": [
        "Reggaetón/Trap Latino", "Cumbia", "Vallenato",
        "Tropical/Salsa/Merengue/Bolero", "Pop", "Rock"
    ],
    "Venezuela": [
        "Reggaetón/Trap Latino", "Tropical/Salsa/Merengue/Bolero",
        "Pop", "Rock", "Classical"
    ],
    "Ecuador": ["Reggaetón/Trap Latino", "Cumbia", "Folklore/Raíces", "Pop"],
    "Peru": ["Reggaetón/Trap Latino", "Cumbia", "Folklore/Raíces", "Pop"],
    "Bolivia": ["Reggaetón/Trap Latino", "Cumbia", "Folklore/Raíces", "Pop"],
    "Chile": ["Reggaetón/Trap Latino", "Cumbia", "Pop", "Rock", "Folklore/Raíces", "Classical"],
    "Argentina": [
        "Reggaetón/Trap Latino", "Cumbia", "Rock", "Pop", "Folklore/Raíces",
        "Classical"
    ],
    "Paraguay": ["Reggaetón/Trap Latino", "Cumbia", "Folklore/Raíces", "Pop"],
    "Uruguay": ["Reggaetón/Trap Latino", "Cumbia", "Pop", "Rock", "Electrónica/Dance", "Classical"],
    "Brazil": [
        "Sertanejo", "Funk Brasileiro", "Reggaetón/Trap Latino",
        "Pop", "Rock", "Hip-Hop/Rap", "Forró", "Axé", "MPB",
        "Classical"
    ],
    "Guyana": ["Dancehall/Reggae", "Reggaetón/Trap Latino", "Pop"],
    "Suriname": ["Dancehall/Reggae", "Reggaetón/Trap Latino", "Pop"],
    "French Guiana": ["Dancehall/Reggae", "Reggaetón/Trap Latino", "Pop", "Kizomba/Zouk"],

    # Europa Occidental
    "Spain": [
        "Reggaetón/Trap Latino", "Pop", "Hip-Hop/Rap",
        "Flamenco / Copla", "Rock", "Electrónica/Dance",
        "Classical"
    ],
    "Portugal": [
        "Pop", "Hip-Hop/Rap", "Folklore/Raíces",
        "Kizomba/Zouk", "Reggaetón/Trap Latino", "Rock", "Fado",
        "Classical"
    ],
    "United Kingdom": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Electrónica/Dance", "Afrobeats", "Dancehall/Reggae",
        "R&B/Soul", "Classical"
    ],
    "Ireland": [
        "Pop", "Rock", "Alternative", "Hip-Hop/Rap",
        "Folklore/Raíces", "Electrónica/Dance", "Classical"
    ],
    "France": [
        "Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Afrobeats",
        "Chanson", "R&B/Soul", "Rock", "Classical"
    ],
    "Belgium": ["Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock", "Chanson", "Classical"],
    "Netherlands": ["Pop", "Electrónica/Dance", "Hip-Hop/Rap", "Rock", "Alternative", "Classical"],
    "Germany": [
        "Hip-Hop/Rap", "Pop", "Electrónica/Dance", "Schlager",
        "Rock", "Alternative", "Classical"
    ],
    "Austria": [
        "Pop", "Hip-Hop/Rap", "Schlager", "Rock", "Alpine Folk",
        "Classical"
    ],
    "Switzerland": [
        "Pop", "Hip-Hop/Rap", "Alpine Folk", "Rock",
        "Electrónica/Dance", "Schlager", "Classical"
    ],
    "Italy": [
        "Pop", "Hip-Hop/Rap", "Canzone Italiana", "Rock", "Electrónica/Dance",
        "Classical"
    ],
    "Greece": ["Pop", "Hip-Hop/Rap", "Laïko", "Rock", "Electrónica/Dance", "Classical"],
    "Sweden": ["Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock", "Metal", "Dansband", "Classical"],
    "Norway": ["Pop", "Hip-Hop/Rap", "Metal", "Electrónica/Dance", "Rock", "Dansband", "Classical"],
    "Denmark": ["Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock", "Dansband", "Classical"],
    "Finland": ["Pop", "Metal", "Hip-Hop/Rap", "Rock", "Iskelmä", "Electrónica/Dance", "Classical"],
    "Iceland": ["Pop", "Alternative", "Rock", "Hip-Hop/Rap", "Electrónica/Dance", "Classical"],

    # Pequeños estados europeos
    "Luxembourg": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Chanson"],
    "Monaco": ["Pop", "Hip-Hop/Rap", "Chanson", "Electrónica/Dance"],
    "Liechtenstein": ["Pop", "Rock", "Alpine Folk", "Schlager"],
    "Andorra": ["Pop", "Reggaetón/Trap Latino", "Rock", "Flamenco / Copla"],
    "San Marino": ["Pop", "Rock", "Canzone Italiana"],
    "Malta": ["Pop", "Rock", "Hip-Hop/Rap", "Electrónica/Dance"],
    "Cyprus": ["Pop", "Rock", "Hip-Hop/Rap", "Laïko", "Electrónica/Dance"],

    # Europa Oriental y Balcanes
    "Russia": [
        "Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical",
        "Folk"
    ],
    "Ukraine": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Folk"],
    "Poland": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical"],
    "Czech Republic": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical"],
    "Slovakia": ["Pop", "Hip-Hop/Rap", "Rock"],
    "Hungary": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical"],
    "Romania": ["Manele", "Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock"],
    "Bulgaria": ["Chalga", "Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance"],
    "Serbia": ["Turbo-folk", "Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock"],
    "Croatia": ["Pop", "Turbo-folk", "Rock", "Hip-Hop/Rap", "Electrónica/Dance"],
    "Bosnia and Herzegovina": ["Turbo-folk", "Pop", "Rock", "Hip-Hop/Rap"],
    "Montenegro": ["Turbo-folk", "Pop", "Rock"],
    "North Macedonia": ["Turbo-folk", "Pop", "Rock"],
    "Kosovo": ["Tallava", "Pop", "Hip-Hop/Rap", "Turbo-folk", "Rock"],
    "Albania": ["Tallava", "Pop", "Hip-Hop/Rap", "Rock"],
    "Slovenia": ["Pop", "Rock", "Hip-Hop/Rap", "Electrónica/Dance"],
    "Lithuania": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance"],
    "Latvia": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance"],
    "Estonia": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Folk"],
    "Belarus": ["Pop", "Rock", "Hip-Hop/Rap"],
    "Moldova": ["Pop", "Rock", "Hip-Hop/Rap", "Manele"],

    # Oriente Medio y Norte de África
    "Turkey": ["Turkish Pop/Rock", "Pop", "Hip-Hop/Rap", "Rock", "Arabesk", "Classical"],
    "Israel": ["Israeli Pop/Rock", "Pop", "Hip-Hop/Rap", "Rock", "Mizrahi", "Classical"],
    "Lebanon": ["Arabic Pop/Rock", "Pop", "Hip-Hop/Rap"],
    "Syria": ["Arabic Pop/Rock"],
    "Jordan": ["Arabic Pop/Rock", "Pop", "Hip-Hop/Rap"],
    "Iraq": ["Arabic Pop/Rock", "Pop", "Hip-Hop/Rap"],
    "Iran": ["Pop", "Hip-Hop/Rap", "Rock", "Classical Persian"],
    "Egypt": ["Arabic Pop/Rock", "Shaabi", "Hip-Hop/Rap"],
    "Morocco": ["Arabic Pop/Rock", "Gnawa", "Hip-Hop/Rap", "Chaabi"],
    "Algeria": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Raï"],
    "Tunisia": ["Arabic Pop/Rock", "Hip-Hop/Rap"],
    "Libya": ["Arabic Pop/Rock"],
    "Saudi Arabia": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "United Arab Emirates": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "Kuwait": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "Qatar": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "Bahrain": ["Arabic Pop/Rock", "Khaliji"],
    "Oman": ["Arabic Pop/Rock", "Khaliji"],
    "Yemen": ["Arabic Pop/Rock"],

    # África Subsahariana
    "Nigeria": ["Afrobeats", "Hip-Hop/Rap", "Gospel", "Jùjú", "Fuji"],
    "Ghana": ["Afrobeats", "Highlife", "Hip-Hop/Rap", "Gospel"],
    "South Africa": [
        "Amapiano", "Kwaito", "Hip-Hop/Rap", "Afrobeats",
        "Electrónica/Dance", "Maskandi", "Mbaqanga", "Gqom", "Afro-soul"
    ],
    "Tanzania": ["Bongo Flava", "Taarab", "Afrobeats", "Hip-Hop/Rap"],
    "Kenya": ["Afrobeats", "Gengetone", "Kapuka", "Benga", "Hip-Hop/Rap"],
    "Uganda": ["Afrobeats", "Hip-Hop/Rap"],
    "Zimbabwe": ["Zim Dancehall", "Afrobeats", "Amapiano", "Sungura"],
    "Zambia": ["Amapiano", "Afrobeats", "Hip-Hop/Rap"],
    "Mozambique": ["Marrabenta", "Amapiano", "Afrobeats", "Kizomba/Zouk"],
    "Angola": ["Kuduro", "Kizomba/Zouk", "Afrobeats", "Semba"],
    "Ethiopia": ["Ethio-jazz", "Pop", "Hip-Hop/Rap"],
    "Rwanda": ["Afrobeats", "Hip-Hop/Rap"],
    "Senegal": ["Mbalax", "Afrobeats", "Hip-Hop/Rap"],
    "Mali": ["Afrobeats", "Desert Blues"],
    "Ivory Coast": ["Coupé-Décalé", "Afrobeats", "Zouglou", "Hip-Hop/Rap"],
    "Cameroon": ["Afrobeats", "Bikutsi", "Makossa", "Hip-Hop/Rap"],
    "Benin": ["Afrobeats", "Gospel"],
    "Togo": ["Afrobeats"],
    "Burkina Faso": ["Afrobeats"],
    "Niger": ["Afrobeats"],
    "Chad": ["Afrobeats"],
    "Central African Republic": ["Afrobeats"],
    "Equatorial Guinea": ["Afrobeats"],
    "Gabon": ["Afrobeats"],
    "Republic of the Congo": ["Soukous/Ndombolo", "Afrobeats"],
    "Democratic Republic of the Congo": ["Soukous/Ndombolo", "Afrobeats", "Rumba"],
    "Burundi": ["Afrobeats"],
    "Djibouti": ["Afrobeats"],
    "Eritrea": ["Afrobeats"],
    "Somalia": ["Afrobeats", "Qaraami"],
    "Sudan": ["Afrobeats", "Hip-Hop/Rap"],
    "South Sudan": ["Afrobeats"],
    "Malawi": ["Afrobeats"],
    "Botswana": ["Afrobeats", "Amapiano"],
    "Namibia": ["Afrobeats", "Amapiano"],
    "Lesotho": ["Afrobeats", "Amapiano"],
    "Eswatini": ["Afrobeats", "Amapiano"],
    "Madagascar": ["Salegy", "Afrobeats"],
    "Comoros": ["Afrobeats", "Taarab"],
    "Mauritius": ["Sega", "Afrobeats", "Kizomba/Zouk"],
    "Seychelles": ["Sega", "Afrobeats", "Kizomba/Zouk"],
    "Cabo Verde": ["Kizomba/Zouk", "Coladeira", "Funaná", "Morna"],
    "São Tomé and Príncipe": ["Afrobeats", "Kizomba/Zouk"],

    # Asia
    "India": [
        "Indian Pop", "Hip-Hop/Rap", "Bollywood", "Indian Classical",
        "Rock", "Electrónica/Dance"
    ],  # 'Indian Classical' ya cubre la tradición clásica india, no se añade 'Classical'
    "Pakistan": ["Pakistani Pop", "Hip-Hop/Rap", "Qawwali", "Rock"],
    "Bangladesh": ["Bangladeshi Pop/Rock", "Hip-Hop/Rap", "Folk"],
    "Sri Lanka": ["Sri Lankan Pop/Rock", "Baila", "Hip-Hop/Rap"],
    "Nepal": ["Nepali Pop/Rock", "Hip-Hop/Rap", "Folk"],
    "Bhutan": ["Bhutanese Pop/Rock", "Rigsar"],
    "Maldives": ["Maldivian Pop/Rock", "Boduberu fusion"],
    "South Korea": [
        "K-Pop/K-Rock", "Hip-Hop/Rap", "Rock", "Ballad", "Trot",
        "Classical"
    ],
    "Japan": [
        "J-Pop/J-Rock", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Enka", "City Pop",
        "Classical"
    ],
    "China": [
        "C-Pop/C-Rock", "Hip-Hop/Rap", "Folk", "Rock",
        "Classical"
    ],
    "Taiwan": ["TW-Pop/TW-Rock", "Hip-Hop/Rap", "Rock", "Mandopop", "Classical"],
    "Hong Kong": ["HK-Pop/HK-Rock", "Cantopop", "Hip-Hop/Rap", "Classical"],
    "Macau": ["Macanese Pop/Rock", "Cantopop", "Pop"],
    "Mongolia": ["Mongolian Pop/Rock/Metal", "Folk Metal", "Hip-Hop/Rap"],
    "Indonesia": [
        "Indonesian Pop/Dangdut", "Rock", "Hip-Hop/Rap",
        "Electrónica/Dance", "Keroncong"
    ],
    "Malaysia": [
        "Malaysian Pop", "Indonesian Pop/Dangdut", "K-Pop/K-Rock",
        "J-Pop/J-Rock", "Hip-Hop/Rap"
    ],
    "Singapore": [
        "Singaporean Pop", "K-Pop/K-Rock", "J-Pop/J-Rock",
        "C-Pop/C-Rock", "Hip-Hop/Rap"
    ],
    "Philippines": [
        "OPM", "K-Pop/K-Rock", "J-Pop/J-Rock", "Pop",
        "Rock", "Hip-Hop/Rap"
    ],
    "Thailand": [
        "T-Pop/T-Rock", "K-Pop/K-Rock", "J-Pop/J-Rock",
        "Luk Thung", "Mor Lam", "Hip-Hop/Rap"
    ],
    "Vietnam": [
        "V-Pop/V-Rock", "K-Pop/K-Rock", "Hip-Hop/Rap",
        "Bolero Vietnamita", "Folk"
    ],
    "Myanmar": ["Burmese Pop/Rock", "Hip-Hop/Rap"],
    "Cambodia": ["Cambodian Pop/Rock", "Hip-Hop/Rap", "Folk"],
    "Laos": ["Lao Pop/Rock", "Mor Lam", "Hip-Hop/Rap"],
    "Brunei": ["Bruneian Pop/Rock", "Malaysian Pop", "K-Pop/K-Rock"],
    "Timor-Leste": ["Timorese Pop/Rock", "Dancehall/Reggae", "Folk"],

    # Asia Central y Cáucaso
    "Kazakhstan": ["Q-pop/Q-rock", "Pop", "Hip-Hop/Rap", "Folk"],
    "Uzbekistan": ["Pop", "Hip-Hop/Rap", "Folk", "Rock"],
    "Turkmenistan": ["Pop", "Folk"],
    "Kyrgyzstan": ["Pop", "Hip-Hop/Rap", "Folk"],
    "Tajikistan": ["Pop", "Folk"],
    "Azerbaijan": ["Pop", "Hip-Hop/Rap", "Mugham", "Rock"],
    "Georgia": ["Pop", "Hip-Hop/Rap", "Folk", "Rock"],
    "Armenia": ["Pop", "Hip-Hop/Rap", "Folk", "Rock", "Classical"],

    # Oceanía
    "Australia": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Electrónica/Dance", "Country", "Aboriginal Australian Pop/Rock",
        "Classical"
    ],
    "New Zealand": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Māori Pop/Rock", "Electrónica/Dance", "Pacific Reggae",
        "Classical"
    ],
    "Papua New Guinea": ["PNG Pop/Rock", "Dancehall/Reggae", "Stringband", "Folk"],
    "Fiji": ["Pasifika Pop/Rock", "Dancehall/Reggae", "Folk", "Indian Pop"],
    "Samoa": ["Pasifika Pop/Rock", "Dancehall/Reggae", "Folk"],
    "Tonga": ["Pasifika Pop/Rock", "Dancehall/Reggae", "Folk"],
    "Solomon Islands": ["Pasifika Pop/Rock", "Folk"],
    "Vanuatu": ["Pasifika Pop/Rock", "Folk"],
    "Micronesia": ["Pasifika Pop/Rock", "Folk"],
    "Marshall Islands": ["Pasifika Pop/Rock", "Folk"],
    "Palau": ["Pasifika Pop/Rock", "Folk"],
    "Nauru": ["Pasifika Pop/Rock", "Folk"],
    "Kiribati": ["Pasifika Pop/Rock", "Folk"],
    "Tuvalu": ["Pasifika Pop/Rock", "Folk"],
    "Hawaii": ["Hawaiian Pop/Rock", "Pop", "Reggae", "Slack Key Guitar"],
}

DEFAULT_GENRE_PRIORITY = ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Alternative"]

# ============================================================================
# REGLAS ESPECÍFICAS POR PAÍS
# ============================================================================

COUNTRY_SPECIFIC_RULES = {
    "Puerto Rico": {
        "keywords": ["reggaeton", "reggaetón", "trap latino", "urbano", "dembow", "perreo", "neoperreo", "rap", "hip hop"],
        "bonus_extra": 2.0,
        "force_macro": "Reggaetón/Trap Latino"
    },
    "South Korea": {
        "keywords": ["k-pop", "kpop", "korean pop", "k-rap", "k-r&b", "korean hip hop", "korean rock", "idol group"],
        "bonus_extra": 1.5,
        "force_macro": "K-Pop/K-Rock",
        "map_generic_to": "K-Pop/K-Rock"
    },
    "Colombia": {
        "keywords": ["reggaeton", "reggaetón", "vallenato", "cumbia"],
        "bonus_extra": 1.3
    },
    "Brazil": {
        "keywords": ["sertanejo", "funk brasileiro", "funk carioca", "brazilian funk", "funk", "axe", "forro", "mpb"],
        "bonus_extra": 1.5
    },
    "Jamaica": {
        "keywords": ["dancehall", "reggae", "roots reggae", "dub"],
        "bonus_extra": 1.5
    },
    "India": {
        "keywords": ["indian", "bollywood", "punjabi", "bhangra", "filmi", "hindustani", "carnatic", "ghazal", "qawwali", "sufi"],
        "bonus_extra": 1.5
    },
    "Pakistan": {
        "keywords": ["pakistani pop", "urdu", "lollywood", "indian", "bollywood"],
        "bonus_extra": 1.5,
        "prefer_genre": "Pakistani Pop"
    },
    "Bangladesh": {
        "keywords": ["bangladeshi pop", "bengali", "indian"],
        "bonus_extra": 1.5,
        "prefer_genre": "Bangladeshi Pop/Rock"
    },
    "Mexico": {
        "keywords": ["regional mexicano", "banda", "norteño", "corridos", "mariachi", "ranchera"],
        "bonus_extra": 1.3
    },
    "Spain": {
        "keywords": ["reggaeton", "reggaetón", "trap latino", "flamenco", "rumba"],
        "bonus_extra": 1.3
    },
    "United Kingdom": {
        "keywords": ["uk drill", "grime", "britpop", "uk garage"],
        "bonus_extra": 1.3
    },
    "France": {
        "keywords": ["rap français", "french rap", "variété française"],
        "bonus_extra": 1.3
    },
    "Nigeria": {
        "keywords": ["afrobeats", "naija", "afro pop"],
        "bonus_extra": 1.5
    },
    "South Africa": {
        "keywords": ["amapiano", "south african house"],
        "bonus_extra": 1.5
    },
    "Japan": {
        "keywords": ["j-pop", "jpop", "japanese pop", "j-rock", "japanese rock", "anime", "city pop"],
        "bonus_extra": 1.5,
        "force_macro": "J-Pop/J-Rock",
        "map_generic_to": "J-Pop/J-Rock"
    },
    "China": {
        "keywords": ["c-pop", "cpop", "chinese pop", "mandopop", "chinese rock", "c-rock"],
        "bonus_extra": 1.5,
        "force_macro": "C-Pop/C-Rock",
        "map_generic_to": "C-Pop/C-Rock"
    },
    "Taiwan": {
        "keywords": ["taiwanese pop", "t-pop", "taiwanese rock"],
        "bonus_extra": 1.5,
        "force_macro": "TW-Pop/TW-Rock",
        "map_generic_to": "TW-Pop/TW-Rock"
    },
    "Hong Kong": {
        "keywords": ["cantopop", "hong kong pop", "hk-pop", "canto-pop"],
        "bonus_extra": 1.5,
        "force_macro": "HK-Pop/HK-Rock",
        "map_generic_to": "HK-Pop/HK-Rock"
    },
    "Thailand": {
        "keywords": ["t-pop", "thai pop", "thai rock", "luk thung", "mor lam"],
        "bonus_extra": 1.5,
        "force_macro": "T-Pop/T-Rock",
        "map_generic_to": "T-Pop/T-Rock"
    },
    "Vietnam": {
        "keywords": ["v-pop", "vpop", "vietnamese pop", "vietnamese rock"],
        "bonus_extra": 1.5,
        "force_macro": "V-Pop/V-Rock",
        "map_generic_to": "V-Pop/V-Rock"
    },
    "Philippines": {
        "keywords": ["opm", "pinoy pop", "filipino pop", "pinoy rock"],
        "bonus_extra": 1.5,
        "force_macro": "OPM",
        "map_generic_to": "OPM"
    },
    "Indonesia": {
        "keywords": ["indonesian pop", "dangdut", "indo-pop"],
        "bonus_extra": 1.5,
        "force_macro": "Indonesian Pop/Dangdut",
        "map_generic_to": "Indonesian Pop/Dangdut"
    },
    "Malaysia": {
        "keywords": ["malaysian pop", "m-pop", "malay pop"],
        "bonus_extra": 1.5,
        "force_macro": "Malaysian Pop",
        "map_generic_to": "Malaysian Pop"
    },
    "Singapore": {
        "keywords": ["singaporean pop", "sg pop", "xinyao"],
        "bonus_extra": 1.5,
        "force_macro": "Singaporean Pop",
        "map_generic_to": "Singaporean Pop"
    },
    "Turkey": {
        "keywords": ["turkish pop", "turkish rock", "türkçe pop", "arabesk"],
        "bonus_extra": 1.5,
        "force_macro": "Turkish Pop/Rock",
        "map_generic_to": "Turkish Pop/Rock"
    },
    "Egypt": {
        "keywords": ["egyptian pop", "arabic pop", "shaabi"],
        "bonus_extra": 1.5,
        "force_macro": "Arabic Pop/Rock",
        "map_generic_to": "Arabic Pop/Rock"
    },
    "Israel": {
        "keywords": ["israeli pop", "mizrahi"],
        "bonus_extra": 1.5,
        "force_macro": "Israeli Pop/Rock",
        "map_generic_to": "Israeli Pop/Rock"
    },
    "Kazakhstan": {
        "keywords": ["q-pop", "kazakh pop"],
        "bonus_extra": 1.5,
        "force_macro": "Q-pop/Q-rock",
        "map_generic_to": "Q-pop/Q-rock"
    },
    "Nepal": {
        "keywords": ["nepali pop", "nepop"],
        "bonus_extra": 1.5,
        "force_macro": "Nepali Pop/Rock",
        "map_generic_to": "Nepali Pop/Rock"
    },
    "Mongolia": {
        "keywords": ["mongolian pop", "mongolian rock", "mongolian metal"],
        "bonus_extra": 1.5,
        "force_macro": "Mongolian Pop/Rock/Metal",
        "map_generic_to": "Mongolian Pop/Rock/Metal"
    },
    "Afghanistan": {
        "keywords": ["afghan pop", "afghani pop"],
        "bonus_extra": 1.5,
        "force_macro": "Afghan Pop/Rock",
        "map_generic_to": "Afghan Pop/Rock"
    },
    "Sri Lanka": {
        "keywords": ["sri lankan pop", "baila"],
        "bonus_extra": 1.5,
        "force_macro": "Sri Lankan Pop/Rock",
        "map_generic_to": "Sri Lankan Pop/Rock"
    },
    "Myanmar": {
        "keywords": ["burmese pop", "myanmar pop"],
        "bonus_extra": 1.5,
        "force_macro": "Burmese Pop/Rock",
        "map_generic_to": "Burmese Pop/Rock"
    },
    "Laos": {
        "keywords": ["lao pop", "mor lam"],
        "bonus_extra": 1.5,
        "force_macro": "Lao Pop/Rock",
        "map_generic_to": "Lao Pop/Rock"
    },
    "Cambodia": {
        "keywords": ["cambodian pop", "khmer pop", "khmer rock"],
        "bonus_extra": 1.5,
        "force_macro": "Cambodian Pop/Rock",
        "map_generic_to": "Cambodian Pop/Rock"
    },
    "Bhutan": {
        "keywords": ["bhutanese pop", "rigsar"],
        "bonus_extra": 1.5,
        "force_macro": "Bhutanese Pop/Rock",
        "map_generic_to": "Bhutanese Pop/Rock"
    },
    "Maldives": {
        "keywords": ["maldivian pop", "dhivehi pop"],
        "bonus_extra": 1.5,
        "force_macro": "Maldivian Pop/Rock",
        "map_generic_to": "Maldivian Pop/Rock"
    },
    "Papua New Guinea": {
        "keywords": ["png pop", "papua new guinea pop"],
        "bonus_extra": 1.5,
        "force_macro": "PNG Pop/Rock",
        "map_generic_to": "PNG Pop/Rock"
    },
    "Fiji": {
        "keywords": ["fiji pop", "fijian pop"],
        "bonus_extra": 1.5,
        "force_macro": "Pasifika Pop/Rock",
        "map_generic_to": "Pasifika Pop/Rock"
    },
    "Samoa": {
        "keywords": ["samoan pop"],
        "bonus_extra": 1.5,
        "force_macro": "Pasifika Pop/Rock",
        "map_generic_to": "Pasifika Pop/Rock"
    },
    "Tonga": {
        "keywords": ["tongan pop"],
        "bonus_extra": 1.5,
        "force_macro": "Pasifika Pop/Rock",
        "map_generic_to": "Pasifika Pop/Rock"
    },
    "New Zealand": {
        "keywords": ["maori pop", "māori pop", "aotearoa pop", "waiata"],
        "bonus_extra": 1.5,
        "force_macro": "Māori Pop/Rock",
        "map_generic_to": "Māori Pop/Rock"
    },
    "Hawaii": {
        "keywords": ["hawaiian pop", "jawaiian", "hawaiian reggae"],
        "bonus_extra": 1.5,
        "force_macro": "Hawaiian Pop/Rock",
        "map_generic_to": "Hawaiian Pop/Rock"
    },
    "Australia": {
        "keywords": ["indigenous australian pop", "aboriginal pop"],
        "bonus_extra": 1.5,
        "force_macro": "Aboriginal Australian Pop/Rock",
        "map_generic_to": "Aboriginal Australian Pop/Rock"
    }
}

# ============================================================================
# LISTA DE MACROGÉNEROS GENÉRICOS (PARA MAPEO REGIONAL)
# ============================================================================
GENERIC_MACROS = {
    "Pop", "Rock", "Hip-Hop/Rap", "R&B/Soul", "Electrónica/Dance",
    "Alternative", "Metal", "Punk", "Country", "Jazz/Blues", "Folklore/Raíces", "Classical" }


# ============================================================================
# FUNCIÓN DE DETECCIÓN DE ESCRITURA MEJORADA
# ============================================================================

def detect_script_from_name(name: str) -> Optional[str]:
    """
    Detecta el sistema de escritura y, si es posible, el idioma específico.
    Retorna código ISO 639-1 (ej. 'ru', 'uk', 'bg', 'hi', 'ur', etc.) o None.
    """
    # Primero identificar el rango Unicode principal
    if re.search(r'[\u0900-\u097F]', name):      # Devanagari
        # Podríamos intentar distinguir hindi, marathi, nepalí, pero por ahora asumimos hindi
        # y en la búsqueda se probarán otros si es necesario
        return 'hi'
    elif re.search(r'[\u0A80-\u0AFF]', name):    # Gujarati
        return 'gu'
    elif re.search(r'[\u0B00-\u0B7F]', name):    # Oriya
        return 'or'
    elif re.search(r'[\u0B80-\u0BFF]', name):    # Tamil
        return 'ta'
    elif re.search(r'[\u0C00-\u0C7F]', name):    # Telugu
        return 'te'
    elif re.search(r'[\u0C80-\u0CFF]', name):    # Kannada
        return 'kn'
    elif re.search(r'[\u0D00-\u0D7F]', name):    # Malayalam
        return 'ml'
    elif re.search(r'[\u0D80-\u0DFF]', name):    # Sinhala
        return 'si'
    elif re.search(r'[\u0E00-\u0E7F]', name):    # Tailandés
        return 'th'
    elif re.search(r'[\u0F00-\u0FFF]', name):    # Tibetano
        return 'bo'
    elif re.search(r'[\u1000-\u109F]', name):    # Birmano
        return 'my'
    elif re.search(r'[\u1780-\u17FF]', name):    # Jemer
        return 'km'
    elif re.search(r'[\u3040-\u309F\u30A0-\u30FF]', name):  # Japonés
        return 'ja'
    elif re.search(r'[\u4E00-\u9FFF]', name):    # Chino (Han)
        if re.search(r'[\uAC00-\uD7AF]', name):
            return 'ko'  # Coreano (hangul + hanja)
        return 'zh'
    elif re.search(r'[\uAC00-\uD7AF]', name):    # Hangul (coreano)
        return 'ko'
    elif re.search(r'[\u0600-\u06FF]', name) or re.search(r'[\u0750-\u077F]', name):  # Árabe/Urdu
        # Detectar urdu por caracteres específicos: گ چ پ ژ
        if re.search(r'[گچپژ]', name):
            return 'ur'
        else:
            return 'ar'
    elif re.search(r'[\u0400-\u04FF]', name):    # Cirílico
        # Heurísticas simples para distinguir idiomas
        # Ucraniano: і, ї, є, ґ
        if re.search(r'[іїєґ]', name, re.IGNORECASE):
            return 'uk'
        # Búlgaro: ъ (al final de palabra es común)
        if re.search(r'ъ', name, re.IGNORECASE):
            return 'bg'
        # Serbio: ћ, ђ, џ, љ, њ (aunque también usa cirílico)
        if re.search(r'[ћђџљњ]', name, re.IGNORECASE):
            return 'sr'  # o 'sh' para serbocroata, pero usamos 'sr'
        # Por defecto ruso
        return 'ru'
    elif re.search(r'[\u0370-\u03FF]', name):    # Griego
        return 'el'
    elif re.search(r'ñ', name, re.IGNORECASE):   # Ñ española
        return 'es'
    elif re.search(r'[çãõáéíóúâêôàèìòùäëïöü]', name, re.IGNORECASE):  # Acentos latinos
        # Podríamos intentar distinguir portugués (ç, ã, õ) del español, pero por simplicidad
        if re.search(r'[çãõ]', name, re.IGNORECASE):
            return 'pt'
        return 'es'
    return None

# ============================================================================
# FUNCIONES DE NORMALIZACIÓN DE GÉNERO
# ============================================================================

def normalize_genre(genre_text: str) -> Tuple[Optional[str], Optional[str]]:
    if not genre_text:
        return None, None
    text_norm = normalize_text(genre_text)
    if text_norm in GENRE_STOPWORDS:
        return None, None
    if text_norm in GENRE_MAPPINGS:
        macro, sub = GENRE_MAPPINGS[text_norm]
        return macro, sub
    sorted_mappings = sorted(GENRE_MAPPINGS.keys(), key=len, reverse=True)
    for genre_variant in sorted_mappings:
        if genre_variant in text_norm and len(genre_variant) > 3:
            macro, sub = GENRE_MAPPINGS[genre_variant]
            return macro, sub
    text_no_hyphen = text_norm.replace('-', ' ')
    if text_no_hyphen != text_norm and text_no_hyphen in GENRE_MAPPINGS:
        macro, sub = GENRE_MAPPINGS[text_no_hyphen]
        return macro, sub
    text_with_hyphen = text_norm.replace(' ', '-')
    if text_with_hyphen != text_norm and text_with_hyphen in GENRE_MAPPINGS:
        macro, sub = GENRE_MAPPINGS[text_with_hyphen]
        return macro, sub
    return None, None

# ============================================================================
# FUNCIONES DE EXTRACCIÓN DE GÉNERO
# ============================================================================

def extract_genre_from_musicbrainz(mb_data: dict) -> List[Tuple[str, int, str]]:
    candidates = []
    if 'genres' in mb_data:
        for genre in mb_data['genres'][:5]:
            name = genre.get('name', '')
            count = genre.get('count', 1)
            if name:
                candidates.append((name.lower(), count, 'musicbrainz_genres'))
    if 'tags' in mb_data and not candidates:
        for tag in mb_data['tags'][:5]:
            name = tag.get('name', '')
            count = tag.get('count', 1)
            if name:
                candidates.append((name.lower(), count, 'musicbrainz_tags'))
    return candidates

def search_musicbrainz_genre_cached(artist: str) -> List[Tuple[str, int, str]]:
    """Busca en MusicBrainz con caché."""
    if artist in _CACHE['musicbrainz_genre']:
        return _CACHE['musicbrainz_genre'][artist]
    candidates = []
    try:
        url = "https://musicbrainz.org/ws/2/artist/"
        headers = {'User-Agent': 'ArtistDB/5.0 (contact@example.com)'}
        params = {'query': artist, 'fmt': 'json', 'limit': 1}
        resp = _SESSION_MUSICBRAINZ.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('artists'):
                mb_data = data['artists'][0]
                candidates = extract_genre_from_musicbrainz(mb_data)
    except Exception as e:
        logger.debug(f"Error en MusicBrainz para {artist}: {e}")
    _CACHE['musicbrainz_genre'][artist] = candidates
    return candidates

def search_wikidata_genre_cached(artist: str) -> List[Tuple[str, int, str]]:
    """Busca en Wikidata con caché."""
    if artist in _CACHE['wikidata_genre']:
        return _CACHE['wikidata_genre'][artist]
    candidates = []
    try:
        url = "https://www.wikidata.org/w/api.php"
        params_search = {
            'action': 'wbsearchentities',
            'search': artist,
            'language': 'en',
            'format': 'json',
            'limit': 3
        }
        resp = _SESSION_WIKIDATA.get(url, params=params_search, timeout=10)
        data = resp.json()
        if not data.get('search'):
            _CACHE['wikidata_genre'][artist] = candidates
            return candidates
        for result in data['search']:
            qid = result['id']
            params_claims = {
                'action': 'wbgetentities',
                'ids': qid,
                'props': 'claims',
                'format': 'json'
            }
            resp2 = _SESSION_WIKIDATA.get(url, params=params_claims, timeout=10)
            data2 = resp2.json()
            if 'entities' not in data2 or qid not in data2['entities']:
                continue
            entity = data2['entities'][qid]
            claims = entity.get('claims', {})
            if 'P136' in claims:
                for claim in claims['P136'][:3]:
                    try:
                        if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                            dv = claim['mainsnak']['datavalue']
                            if 'value' in dv and 'id' in dv['value']:
                                genre_qid = dv['value']['id']
                                params_label = {
                                    'action': 'wbgetentities',
                                    'ids': genre_qid,
                                    'props': 'labels',
                                    'languages': 'en|es',
                                    'format': 'json'
                                }
                                resp3 = _SESSION_WIKIDATA.get(url, params=params_label, timeout=8)
                                data3 = resp3.json()
                                if 'entities' in data3 and genre_qid in data3['entities']:
                                    labels = data3['entities'][genre_qid].get('labels', {})
                                    genre_name = None
                                    if 'en' in labels:
                                        genre_name = labels['en']['value']
                                    elif 'es' in labels:
                                        genre_name = labels['es']['value']
                                    if genre_name:
                                        candidates.append((genre_name.lower(), 3, 'wikidata'))
                    except Exception as e:
                        logger.debug(f"Error procesando claim de género: {e}")
    except Exception as e:
        logger.debug(f"Error en Wikidata genre search: {e}")
    _CACHE['wikidata_genre'][artist] = candidates
    return candidates

def search_wikipedia_infobox_genre_cached(artist: str, lang: str = 'en') -> List[Tuple[str, int, str]]:
    """Busca en infobox de Wikipedia con caché."""
    key = (artist, lang)
    if key in _CACHE['wikipedia_genre']:
        return _CACHE['wikipedia_genre'][key]
    candidates = []
    try:
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'titles': artist,
            'redirects': 1,
            'format': 'json'
        }
        resp = _SESSION_WIKIPEDIA.get(url, params=params, timeout=8)
        data = resp.json()
        pages = data['query']['pages']
        page_id = next(iter(pages))
        title = pages[page_id].get('title', artist)
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'wikitext',
            'format': 'json',
            'redirects': True
        }
        resp = _SESSION_WIKIPEDIA.get(url, params=params, timeout=10)
        data = resp.json()
        if 'parse' not in data:
            _CACHE['wikipedia_genre'][key] = candidates
            return candidates
        wikitext = data['parse']['wikitext']['*']
        infobox_pattern = r'\{\{\s*Infobox (?:musical artist|band)[\s\S]*?\}\}'
        infobox_match = re.search(infobox_pattern, wikitext, re.IGNORECASE)
        if not infobox_match:
            _CACHE['wikipedia_genre'][key] = candidates
            return candidates
        infobox = infobox_match.group()
        genre_fields = ['genre', 'género', 'genres', 'géneros']
        for field in genre_fields:
            pattern = r'\|?\s*' + field + r'\s*=\s*([^\n|]+)'
            match = re.search(pattern, infobox, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                value = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', value)
                value = re.sub(r'<[^>]+>', '', value)
                value = re.sub(r'\{\{[^}]+\}\}', '', value)
                separators = r',|\sand\s|\sy\s|;'
                genres = re.split(separators, value)
                for g in genres:
                    g = g.strip().lower()
                    if g and len(g) > 2 and g not in GENRE_STOPWORDS:
                        candidates.append((g, 2, f'wikipedia_{lang}_infobox'))
    except Exception as e:
        logger.debug(f"Error en Wikipedia infobox genre: {e}")
    _CACHE['wikipedia_genre'][key] = candidates
    return candidates

def search_wikipedia_summary_genre_cached(artist: str, lang: str = 'en') -> List[Tuple[str, int, str]]:
    """Busca en resumen de Wikipedia con caché."""
    key = (artist, lang)
    if key in _CACHE['wikipedia_genre']:
        return _CACHE['wikipedia_genre'][key]
    candidates = []
    try:
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(artist)}"
        headers = {'User-Agent': 'ArtistDB/5.0'}
        resp = _SESSION_WIKIPEDIA.get(url, headers=headers, timeout=8)
        if resp.status_code != 200:
            _CACHE['wikipedia_genre'][key] = candidates
            return candidates
        data = resp.json()
        extract = data.get('extract', '').lower()
        if not extract:
            _CACHE['wikipedia_genre'][key] = candidates
            return candidates

        # Patrones de extracción
        pattern1 = r'is\s+(?:a|an)\s+([a-z\s\-]+?)\s+(?:singer|rapper|musician|artist|songwriter|producer|dj|band|group|duo|trio)'
        matches = re.findall(pattern1, extract)
        for match in matches:
            candidate = match.strip()
            subgenres = re.split(r'\s+(?:and|y)\s+|\s*,\s*', candidate)
            for sub in subgenres:
                sub = sub.strip()
                if sub and len(sub) > 2 and sub not in GENRE_STOPWORDS:
                    candidates.append((sub, 1, f'wikipedia_{lang}_summary'))

        pattern2 = r'(?:american|british|canadian|australian|indian|korean|japanese|mexican|spanish|french|german|italian|brazilian|argentine|colombian|chilean|peruvian|venezuelan|puerto rican|cuban|dominican|african|nigerian|south african|kenyan|egyptian|moroccan|israeli|turkish|russian|ukrainian|polish|swedish|norwegian|danish|finnish|dutch|belgian|swiss|austrian|portuguese|greek|irish|scottish|welsh|english)\s+([a-z\s\-]+?)\s+(?:singer|rapper|musician|artist|songwriter|producer|dj|band|group|duo)'
        matches = re.findall(pattern2, extract)
        for match in matches:
            candidate = match.strip() if isinstance(match, str) else match[0].strip()
            subgenres = re.split(r'\s+(?:and|y)\s+|\s*,\s*', candidate)
            for sub in subgenres:
                sub = sub.strip()
                if sub and len(sub) > 2 and sub not in GENRE_STOPWORDS:
                    candidates.append((sub, 1, f'wikipedia_{lang}_summary'))

        pattern3 = r'are\s+(?:a|an)\s+([a-z\s\-]+?)\s+(?:band|group|duo)'
        matches = re.findall(pattern3, extract)
        for match in matches:
            candidate = match.strip()
            subgenres = re.split(r'\s+(?:and|y)\s+|\s*,\s*', candidate)
            for sub in subgenres:
                sub = sub.strip()
                if sub and len(sub) > 2 and sub not in GENRE_STOPWORDS:
                    candidates.append((sub, 1, f'wikipedia_{lang}_summary'))

        pattern4 = r'playing\s+([a-z\s\-]+?)\s+music'
        matches = re.findall(pattern4, extract)
        for match in matches:
            candidate = match.strip()
            if candidate and len(candidate) > 2 and candidate not in GENRE_STOPWORDS:
                candidates.append((candidate, 1, f'wikipedia_{lang}_summary'))

        pattern5 = r'known\s+for\s+their\s+([a-z\s\-]+?)\s+music'
        matches = re.findall(pattern5, extract)
        for match in matches:
            candidate = match.strip()
            if candidate and len(candidate) > 2 and candidate not in GENRE_STOPWORDS:
                candidates.append((candidate, 1, f'wikipedia_{lang}_summary'))

        pattern6 = r'genre\s+is\s+([a-z\s\-]+?)(?:\.|,|$)'
        matches = re.findall(pattern6, extract)
        for match in matches:
            candidate = match.strip()
            if candidate and len(candidate) > 2 and candidate not in GENRE_STOPWORDS:
                candidates.append((candidate, 1, f'wikipedia_{lang}_summary'))

        # Lista de palabras clave ampliada
        genre_keywords = ['pop', 'rock', 'hip hop', 'rap', 'trap', 'reggaeton',
                         'reggaetón', 'cumbia', 'bachata', 'salsa', 'metal',
                         'punk', 'indie', 'alternative', 'electrónica', 'dance',
                         'k-pop', 'j-pop', 'bollywood', 'country', 'folk',
                         'reggae', 'dancehall', 'afrobeats', 'edm', 'house', 'techno',
                         'pakistani pop', 'bangladeshi pop', 'urdu', 'punjabi', 'bhangra',
                         'sertanejo', 'funk brasileiro', 'amapiano', 'afrobeat']
        for keyword in genre_keywords:
            if keyword in extract and keyword not in GENRE_STOPWORDS:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, extract):
                    candidates.append((keyword, 0.5, f'wikipedia_{lang}_keyword'))
    except Exception as e:
        logger.debug(f"Error en Wikipedia summary genre: {e}")
    _CACHE['wikipedia_genre'][key] = candidates
    return candidates

# ============================================================================
# FUNCIÓN PRINCIPAL DE BÚSQUEDA DE GÉNERO (con mejoras)
# ============================================================================

def search_artist_genre(artist: str, country: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    Busca el género principal con un flujo optimizado:
    1. MusicBrainz (siempre, con caché)
    2. Wikidata (siempre, con caché)
    3. Wikipedia en idiomas prioritarios según país y escritura, con parada temprana
    """
    all_candidates = []
    variations = generate_all_variations(artist)
    detected_lang = detect_script_from_name(artist)

    # --- MusicBrainz (siempre) ---
    for var in variations[:2]:
        candidates = search_musicbrainz_genre_cached(var)
        all_candidates.extend(candidates)
        if candidates:
            break
        time.sleep(0.5)

    # --- Wikidata (siempre) ---
    if not all_candidates:
        for var in variations[:2]:
            candidates = search_wikidata_genre_cached(var)
            all_candidates.extend(candidates)
            if candidates:
                break
            time.sleep(0.5)

    MIN_CANDIDATES = 3

    # --- Wikipedia en idiomas prioritarios ---
    priority_langs = []
    if country:
        country_lang_map = {
            'India': ['hi', 'ta', 'te', 'ml', 'kn', 'gu', 'or', 'bn', 'en'],
            'Pakistan': ['ur', 'en'],
            'Bangladesh': ['bn', 'en'],
            'South Korea': ['ko', 'en'],
            'Japan': ['ja', 'en'],
            'China': ['zh', 'en'],
            'Mongolia': ['mn', 'en'],
            'Kazakhstan': ['kk', 'ru', 'en'],
            'Nepal': ['ne', 'en'],
            'Russia': ['ru', 'en'],
            'Ukraine': ['uk', 'ru', 'en'],
            'Brazil': ['pt', 'en'],
            'Mexico': ['es', 'en'],
            'Spain': ['es', 'en'],
            'France': ['fr', 'en'],
            'Germany': ['de', 'en'],
            'Italy': ['it', 'en'],
            'Turkey': ['tr', 'en'],
            'Egypt': ['ar', 'en'],
            'Israel': ['he', 'en'],
        }
        priority_langs.extend(country_lang_map.get(country, ['en', 'es']))
    else:
        if detected_lang:
            priority_langs.append(detected_lang)
        priority_langs.append('en')

    seen = set()
    priority_langs = [lang for lang in priority_langs if not (lang in seen or seen.add(lang))]

    if len(all_candidates) < MIN_CANDIDATES:
        for var in variations[:1]:
            for lang in priority_langs:
                candidates = search_wikipedia_infobox_genre_cached(var, lang)
                all_candidates.extend(candidates)
                if len(all_candidates) >= MIN_CANDIDATES:
                    break
                if not candidates:
                    candidates = search_wikipedia_summary_genre_cached(var, lang)
                    all_candidates.extend(candidates)
                if len(all_candidates) >= MIN_CANDIDATES:
                    break
                time.sleep(0.3)
            if len(all_candidates) >= MIN_CANDIDATES:
                break

    if len(all_candidates) < MIN_CANDIDATES:
        other_langs = ['es', 'pt', 'fr', 'de', 'it', 'ru', 'ar', 'zh', 'ja', 'ko']
        for lang in other_langs:
            if lang in priority_langs:
                continue
            for var in variations[:1]:
                candidates = search_wikipedia_infobox_genre_cached(var, lang)
                all_candidates.extend(candidates)
                if len(all_candidates) >= MIN_CANDIDATES:
                    break
                if not candidates:
                    candidates = search_wikipedia_summary_genre_cached(var, lang)
                    all_candidates.extend(candidates)
                if len(all_candidates) >= MIN_CANDIDATES:
                    break
                time.sleep(0.3)
            if len(all_candidates) >= MIN_CANDIDATES:
                break

    # --- Fallback si no hay candidatos pero conocemos el país ---
    if not all_candidates and country:
        priority = COUNTRY_GENRE_PRIORITY.get(country, DEFAULT_GENRE_PRIORITY)
        if priority:
            return priority[0], f"Género: fallback por país ({country})"
        # <-- MEJORA

    if all_candidates:
        primary_genre = select_primary_genre(artist, all_candidates, country, detected_lang)
        sources = set(s for _, _, s in all_candidates)
        return primary_genre, f"Género: {', '.join(sources)}"

    return None, "Género no encontrado"

def select_primary_genre(artist: str, genre_candidates: List[Tuple[str, int, str]],
                         country: Optional[str] = None, detected_lang: Optional[str] = None) -> Optional[str]:
    """
    Selecciona el género principal con sistema de pesos mejorado y mapeo regional.
    """
    if not genre_candidates:
        return None

    # Mapear cada candidato a su macro-género
    macro_votes = defaultdict(float)
    detailed_info = []

    for subgenre, weight, source in genre_candidates:
        macro, normalized_sub = normalize_genre(subgenre)
        if macro:
            final_weight = weight

            # Bonus por fuente
            if 'musicbrainz' in source:
                final_weight *= 1.5
            if 'infobox' in source:
                final_weight *= 1.2
            if 'wikidata' in source:
                final_weight *= 1.3

            # Bonus específicos por términos (ayudan a identificar subgéneros)
            sub_lower = subgenre.lower()
            # Latino
            if any(term in sub_lower for term in ['reggaeton', 'reggaetón', 'regueton', 'reguetón', 'trap latino', 'urbano', 'dembow', 'perreo']):
                final_weight *= 1.4
                if macro != 'Reggaetón/Trap Latino':
                    macro = 'Reggaetón/Trap Latino'
            # Corea
            if any(term in sub_lower for term in ['k-pop', 'kpop', 'korean pop', 'k-rap', 'k-r&b']):
                final_weight *= 1.4
                if macro != 'K-Pop/K-Rock':
                    macro = 'K-Pop/K-Rock'
            # Japón
            if any(term in sub_lower for term in ['j-pop', 'jpop', 'japanese pop']):
                final_weight *= 1.4
                if macro != 'J-Pop/J-Rock':
                    macro = 'J-Pop/J-Rock'
            # India / Sur de Asia
            if any(term in sub_lower for term in ['indian', 'bollywood', 'punjabi', 'bhangra']):
                final_weight *= 1.3
            if any(term in sub_lower for term in ['pakistani pop', 'urdu', 'lollywood']):
                final_weight *= 1.3
            if any(term in sub_lower for term in ['bangladeshi pop', 'bengali']):
                final_weight *= 1.3
            # Brasil
            if any(term in sub_lower for term in ['sertanejo', 'funk brasileiro', 'funk carioca', 'funk']):  # <-- MEJORA (añadido 'funk')
                final_weight *= 1.4
                # No forzamos, las reglas de país harán su trabajo
            # África
            if any(term in sub_lower for term in ['afrobeats', 'naija', 'amapiano']):
                final_weight *= 1.4

            macro_votes[macro] += final_weight
            detailed_info.append(f"{subgenre}→{macro} ({source}:{final_weight:.1f})")
        else:
            # Si no se pudo mapear, ver si es un macro conocido
            for known_macro in MACRO_GENRES:
                if subgenre.lower() == known_macro.lower():
                    macro_votes[known_macro] += weight
                    detailed_info.append(f"{subgenre}→{known_macro} ({source})")
                    break

    # --- MAPEO DE GÉNEROS GENÉRICOS A REGIONALES ---
    # Si el país tiene map_generic_to, añadimos votos extra para cada candidato genérico
    if country and country in COUNTRY_SPECIFIC_RULES:
        rule = COUNTRY_SPECIFIC_RULES[country]
        map_to = rule.get("map_generic_to")
        if map_to:
            # Recorremos los candidatos originales (sin normalizar) para detectar genéricos
            for subgenre, weight, source in genre_candidates:
                macro, _ = normalize_genre(subgenre)
                if macro and macro in GENERIC_MACROS:
                    # Añadimos un voto al macro regional con el mismo peso (ya bonificado)  # <-- MEJORA
                    macro_votes[map_to] += weight  # antes era weight * 0.8
                    detailed_info.append(f"map_generic: {subgenre}→{map_to} (weight {weight:.1f})")

    # --- APLICAR BONUS POR PAÍS (según prioridad) ---
    if country and macro_votes:
        priority = COUNTRY_GENRE_PRIORITY.get(country, DEFAULT_GENRE_PRIORITY)
        for macro in list(macro_votes.keys()):
            if macro in priority:
                idx = priority.index(macro)
                if idx == 0:
                    macro_votes[macro] *= 2.0
                elif idx == 1:
                    macro_votes[macro] *= 1.5
                else:
                    macro_votes[macro] *= 1.2

    # --- APLICAR REGLAS ESPECÍFICAS POR PAÍS (keywords, force_macro, prefer_genre) ---
    if country and macro_votes and country in COUNTRY_SPECIFIC_RULES:
        rule = COUNTRY_SPECIFIC_RULES[country]
        for macro in list(macro_votes.keys()):
            for subgenre, _, _ in genre_candidates:
                sub_lower = subgenre.lower()
                if any(kw in sub_lower for kw in rule["keywords"]):
                    if "force_macro" in rule and macro != rule["force_macro"]:
                        peso = macro_votes.pop(macro)
                        macro_votes[rule["force_macro"]] += peso * rule["bonus_extra"]
                    elif "prefer_genre" in rule and macro == rule["prefer_genre"]:
                        macro_votes[macro] *= rule["bonus_extra"]
                    else:
                        macro_votes[macro] *= rule["bonus_extra"]
                    break

    # --- BONUS POR ESCRITURA DETECTADA Y PAÍS ---
    if detected_lang and country:
        # Sur de Asia
        if detected_lang in ['hi', 'ta', 'te', 'ml', 'kn', 'gu', 'or', 'bn'] and country in ['India', 'Pakistan', 'Bangladesh']:
            for m in ['Indian Pop', 'Pakistani Pop', 'Bangladeshi Pop/Rock']:  # <-- MEJORA (nombres actualizados)
                if m in macro_votes:
                    macro_votes[m] *= 1.2
        # Corea
        if detected_lang == 'ko' and country == 'South Korea':
            if 'K-Pop/K-Rock' in macro_votes:
                macro_votes['K-Pop/K-Rock'] *= 1.2
        # Japón
        if detected_lang == 'ja' and country == 'Japan':
            if 'J-Pop/J-Rock' in macro_votes:
                macro_votes['J-Pop/J-Rock'] *= 1.2
        # China
        if detected_lang == 'zh' and country == 'China':
            if 'C-Pop/C-Rock' in macro_votes:
                macro_votes['C-Pop/C-Rock'] *= 1.2
        # Mongolia
        if detected_lang == 'mn' and country == 'Mongolia':
            if 'Mongolian Pop/Rock/Metal' in macro_votes:
                macro_votes['Mongolian Pop/Rock/Metal'] *= 1.2
        # Mundo árabe
        if detected_lang == 'ar' and country in ['Egypt', 'Saudi Arabia', 'UAE', 'Morocco', 'Algeria', 'Tunisia']:
            if 'Arabic Pop/Rock' in macro_votes:
                macro_votes['Arabic Pop/Rock'] *= 1.2
        # Turquía
        if detected_lang == 'tr' and country == 'Turkey':
            if 'Turkish Pop/Rock' in macro_votes:
                macro_votes['Turkish Pop/Rock'] *= 1.2
        # Kazajistán
        if detected_lang == 'kk' and country == 'Kazakhstan':
            if 'Q-pop/Q-rock' in macro_votes:
                macro_votes['Q-pop/Q-rock'] *= 1.2

    # Mostrar candidatos en debug
    if detailed_info and logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Candidatos para género de {len(genre_candidates)} fuentes: {', '.join(detailed_info)}")

    if macro_votes:
        primary_macro = max(macro_votes.items(), key=lambda x: x[1])[0]
        if len(macro_votes) > 1 and logger.isEnabledFor(logging.DEBUG):
            sorted_votes = sorted(macro_votes.items(), key=lambda x: x[1], reverse=True)
            if sorted_votes[0][1] / sorted_votes[1][1] < 1.5:
                logger.debug(f"  📊 Múltiples géneros detectados: {dict(sorted_votes)}")
        return primary_macro

    return None

# ============================================================================
# FUNCIONES DE PAÍS (con caché)
# ============================================================================

def search_musicbrainz_country_cached(artist: str) -> Tuple[Optional[str], str]:
    if artist in _CACHE['musicbrainz_country']:
        return _CACHE['musicbrainz_country'][artist]
    try:
        url = "https://musicbrainz.org/ws/2/artist/"
        headers = {'User-Agent': 'ArtistDB/5.0 (contact@example.com)'}
        params = {'query': artist, 'fmt': 'json', 'limit': 5}
        resp = _SESSION_MUSICBRAINZ.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            _CACHE['musicbrainz_country'][artist] = (None, "Not found")
            return None, "Not found"
        data = resp.json()
        if not data.get('artists'):
            _CACHE['musicbrainz_country'][artist] = (None, "Not found")
            return None, "Not found"
        artist_lower = artist.lower()
        best_score = 0.0
        best_artist = None
        for mb_artist in data['artists'][:5]:
            mb_name = mb_artist.get('name', '').lower()
            bonus = 0.3 if (artist_lower in mb_name or mb_name in artist_lower) else 0.0
            score = SequenceMatcher(None, artist_lower, mb_name).ratio() + bonus
            if score > best_score:
                best_score = score
                best_artist = mb_artist
        if best_score < 0.55:
            _CACHE['musicbrainz_country'][artist] = (None, "Not found")
            return None, "Not found"
        for field in ['area', 'begin-area']:
            if field in best_artist:
                country_raw = best_artist[field].get('name', '')
                if country_raw:
                    country_norm = validate_and_normalize_country(country_raw)
                    if country_norm:
                        _CACHE['musicbrainz_country'][artist] = (country_norm, f"MusicBrainz ({artist})")
                        return country_norm, f"MusicBrainz ({artist})"
        _CACHE['musicbrainz_country'][artist] = (None, "Not found")
        return None, "Not found"
    except Exception as e:
        logger.debug(f"MusicBrainz country error: {e}")
        _CACHE['musicbrainz_country'][artist] = (None, "Not found")
        return None, "Not found"

def search_wikipedia_infobox_country_cached(artist: str, lang: str = 'en') -> Optional[str]:
    key = (artist, lang)
    if key in _CACHE['wikipedia_country']:
        return _CACHE['wikipedia_country'][key]
    try:
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'titles': artist,
            'redirects': 1,
            'format': 'json'
        }
        resp = _SESSION_WIKIPEDIA.get(url, params=params, timeout=8)
        data = resp.json()
        pages = data['query']['pages']
        page_id = next(iter(pages))
        title = pages[page_id].get('title', artist)
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'wikitext',
            'format': 'json',
            'redirects': True
        }
        resp = _SESSION_WIKIPEDIA.get(url, params=params, timeout=10)
        data = resp.json()
        if 'parse' not in data:
            _CACHE['wikipedia_country'][key] = None
            return None
        wikitext = data['parse']['wikitext']['*']
        infobox_pattern = r'\{\{\s*Infobox (?:musical artist|band)[\s\S]*?\}\}'
        infobox_match = re.search(infobox_pattern, wikitext, re.IGNORECASE)
        if not infobox_match:
            _CACHE['wikipedia_country'][key] = None
            return None
        infobox = infobox_match.group()
        fields = ['origin', 'birth_place', 'location', 'from', 'country']
        for field in fields:
            field_pattern = r'\|?\s*' + field + r'\s*=\s*([^\n|]+)'
            field_match = re.search(field_pattern, infobox, re.IGNORECASE)
            if field_match:
                value = field_match.group(1).strip()
                value = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', value)
                value = re.sub(r'<[^>]+>', '', value)
                country_norm = validate_and_normalize_country(value)
                if country_norm:
                    _CACHE['wikipedia_country'][key] = country_norm
                    return country_norm
        _CACHE['wikipedia_country'][key] = None
        return None
    except Exception as e:
        logger.debug(f"Wikipedia infobox {lang} country error: {e}")
        _CACHE['wikipedia_country'][key] = None
        return None

def search_wikipedia_summary_country_cached(artist: str, lang: str = 'en') -> Optional[str]:
    key = (artist, lang)
    if key in _CACHE['wikipedia_country']:
        return _CACHE['wikipedia_country'][key]
    try:
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(artist)}"
        headers = {'User-Agent': 'ArtistDB/5.0'}
        resp = _SESSION_WIKIPEDIA.get(url, headers=headers, timeout=8)
        if resp.status_code != 200:
            _CACHE['wikipedia_country'][key] = None
            return None
        data = resp.json()
        extract = data.get('extract', '').lower()
        if not extract:
            _CACHE['wikipedia_country'][key] = None
            return None
        patterns = [
            r'is\s+(?:a|an)\s+([a-z\s]+?)\s+(?:singer|rapper|musician|artist|songwriter|producer|dj|band|group)',
            r'was\s+(?:a|an)\s+([a-z\s]+?)\s+(?:singer|rapper|musician|artist|songwriter|producer|dj|band|group)',
            r'are\s+(?:a|an)\s+([a-z\s]+?)\s+(?:band|group|duo)',
            r'from\s+([a-z\s]+?)(?:\.|,|\s+who|\s+is|\s+was)',
            r'born\s+in\s+([^,]+?)(?:\.|,)',
            r'formed\s+in\s+([^,]+?)(?:\.|,)',
        ]
        for pattern in patterns:
            match = re.search(pattern, extract)
            if match:
                candidate = match.group(1).strip()
                if 2 <= len(candidate) <= 35:
                    country = validate_and_normalize_country(candidate)
                    if country:
                        _CACHE['wikipedia_country'][key] = country
                        return country
        _CACHE['wikipedia_country'][key] = None
        return None
    except Exception as e:
        logger.debug(f"Wikipedia summary {lang} country error: {e}")
        _CACHE['wikipedia_country'][key] = None
        return None

def search_wikidata_country_cached(artist: str) -> Optional[str]:
    if artist in _CACHE['wikidata_country']:
        return _CACHE['wikidata_country'][artist]
    try:
        url = "https://www.wikidata.org/w/api.php"
        params = {
            'action': 'wbsearchentities',
            'search': artist,
            'language': 'en',
            'format': 'json',
            'limit': 3
        }
        resp = _SESSION_WIKIDATA.get(url, params=params, timeout=10)
        data = resp.json()
        if not data.get('search'):
            _CACHE['wikidata_country'][artist] = None
            return None
        for result in data['search']:
            qid = result['id']
            params = {
                'action': 'wbgetentities',
                'ids': qid,
                'props': 'claims',
                'format': 'json'
            }
            resp = _SESSION_WIKIDATA.get(url, params=params, timeout=10)
            data2 = resp.json()
            if 'entities' not in data2 or qid not in data2['entities']:
                continue
            entity = data2['entities'][qid]
            claims = entity.get('claims', {})
            for prop in ['P27', 'P19']:
                if prop in claims:
                    for claim in claims[prop]:
                        if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                            dv = claim['mainsnak']['datavalue']
                            if 'value' in dv and 'id' in dv['value']:
                                q_country = dv['value']['id']
                                params_label = {
                                    'action': 'wbgetentities',
                                    'ids': q_country,
                                    'props': 'labels',
                                    'languages': 'en|es',
                                    'format': 'json'
                                }
                                resp3 = _SESSION_WIKIDATA.get(url, params=params_label, timeout=8)
                                data3 = resp3.json()
                                if 'entities' not in data3 or q_country not in data3['entities']:
                                    continue
                                country_entity = data3['entities'][q_country]
                                labels = country_entity.get('labels', {})
                                if 'en' in labels:
                                    country_name = labels['en']['value']
                                elif 'es' in labels:
                                    country_name = labels['es']['value']
                                else:
                                    continue
                                country_canonical = validate_and_normalize_country(country_name)
                                if country_canonical:
                                    _CACHE['wikidata_country'][artist] = country_canonical
                                    return country_canonical
        _CACHE['wikidata_country'][artist] = None
        return None
    except Exception as e:
        logger.debug(f"Wikidata country error: {e}")
        _CACHE['wikidata_country'][artist] = None
        return None

def search_country(artist: str) -> Tuple[Optional[str], str]:
    variations = generate_all_variations(artist)

    for var in variations[:3]:  # limitar variaciones
        country, source = search_musicbrainz_country_cached(var)
        if country:
            info = f" (var: {var})" if var != artist else ""
            return country, f"MusicBrainz{info}"
    time.sleep(0.8)

    for var in variations[:3]:
        country = search_wikipedia_summary_country_cached(var, 'en')
        if country:
            info = f" (var: {var})" if var != artist else ""
            return country, f"Wikipedia EN summary{info}"

        country = search_wikipedia_infobox_country_cached(var, 'en')
        if country:
            info = f" (var: {var})" if var != artist else ""
            return country, f"Wikipedia EN infobox{info}"
    time.sleep(0.3)

    # Probar idiomas prioritarios según país detectado
    detected_lang = detect_script_from_name(artist)
    priority_langs = []
    if detected_lang:
        priority_langs.append(detected_lang)
    priority_langs.extend(['es', 'pt', 'fr', 'de', 'it', 'hi', 'ko', 'ja', 'zh', 'ar', 'tr', 'ru'])
    seen = set()
    priority_langs = [lang for lang in priority_langs if not (lang in seen or seen.add(lang))]

    for lang in priority_langs:
        for var in variations[:2]:
            country = search_wikipedia_summary_country_cached(var, lang)
            if country:
                info = f" (var: {var})" if var != artist else ""
                return country, f"Wikipedia {lang.upper()}{info}"
            time.sleep(0.2)

    for var in variations[:3]:
        country = search_wikidata_country_cached(var)
        if country:
            info = f" (var: {var})" if var != artist else ""
            return country, f"Wikidata{info}"

    return None, "Not found"

# ============================================================================
# FUNCIONES DE BASE DE DATOS
# ============================================================================

def create_database():
    """Crea la base de datos con la columna de género"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artist'")
        exists = cursor.fetchone()
        if not exists:
            cursor.execute('''
                CREATE TABLE artist (
                    name TEXT PRIMARY KEY,
                    country TEXT,
                    macro_genre TEXT
                )
            ''')
            conn.commit()
            logger.info("✅ Table 'artist' created (name, country, macro_genre)")
        else:
            cursor.execute("PRAGMA table_info(artist)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'macro_genre' not in columns:
                cursor.execute("ALTER TABLE artist ADD COLUMN macro_genre TEXT")
                conn.commit()
                logger.info("✅ Added 'macro_genre' column to existing table")
            else:
                logger.info("✅ Table 'artist' exists with all columns")
        conn.close()
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        raise

def artist_in_database(artist: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Retorna: (existe, country, macro_genre)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT country, macro_genre FROM artist WHERE name = ?', (artist,))
        res = cursor.fetchone()
        conn.close()
        if res:
            return True, res[0], res[1]
        else:
            return False, None, None
    except Exception as e:
        logger.debug(f"Database query error: {e}")
        return False, None, None

def insert_artist(artist: str, country: str, genre: Optional[str] = None, source: str = ""):
    """Inserta o actualiza un artista con país y género"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT country, macro_genre FROM artist WHERE name = ?', (artist,))
        existing = cursor.fetchone()
        if existing:
            existing_country, existing_genre = existing
            update_country = country != 'Unknown' and (not existing_country or existing_country == 'Unknown')
            update_genre = genre and genre != 'Unknown' and (not existing_genre or existing_genre == 'Unknown' or existing_genre is None)
            if update_country or update_genre:
                set_clauses = []
                params = []
                if update_country:
                    set_clauses.append("country = ?")
                    params.append(country)
                if update_genre:
                    set_clauses.append("macro_genre = ?")
                    params.append(genre)
                params.append(artist)
                cursor.execute(f'''
                    UPDATE artist
                    SET {', '.join(set_clauses)}
                    WHERE name = ?
                ''', params)
                conn.commit()
                if source:
                    logger.info(f"  🔄 {artist} → País: {country if update_country else existing_country} | Género: {genre if update_genre else existing_genre} ({source})")
        else:
            cursor.execute('''
                INSERT INTO artist (name, country, macro_genre)
                VALUES (?, ?, ?)
            ''', (artist, country, genre))
            conn.commit()
            if source:
                logger.info(f"  ➕ {artist} → País: {country} | Género: {genre or 'N/A'} ({source})")
            else:
                logger.info(f"  ✅ {artist} → País: {country} | Género: {genre or 'N/A'}")
        conn.close()
    except Exception as e:
        logger.error(f"Error inserting {artist}: {e}")

def count_artists_in_database() -> int:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM artist')
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except:
        return 0
# ============================================================================
# FUNCIÓN PARA OBTENER LA ÚLTIMA BASE DE DATOS DE CHARTS
# ============================================================================
def get_latest_chart_database() -> Optional[Path]:
    if not CHARTS_DB_DIR.exists():
        logger.error(f"❌ Directorio no encontrado: {CHARTS_DB_DIR}")
        return None
    db_files = list(CHARTS_DB_DIR.glob("youtube_charts_*.db"))
    if not db_files:
        logger.error("❌ No se encontraron bases de datos de charts")
        return None
    latest = max(db_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"📁 Usando base de datos: {latest.name}")
    return latest

# ============================================================================
# FUNCIÓN PARA OBTENER ARTISTAS DESDE LA BASE DE DATOS DE CHARTS
# ============================================================================
def get_artists_from_chart_db(db_path: Path) -> Set[str]:
    if not db_path.exists():
        logger.error(f"❌ Archivo no encontrado: {db_path}")
        return set()
    artists = set()
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(chart_data)")
        columns = [col[1] for col in cursor.fetchall()]
        artist_column = None
        for col in ['Artist Names', 'Artist', 'Artists', 'artist', 'Artista']:
            if col in columns:
                artist_column = col
                break
        if not artist_column:
            logger.error("❌ No se encontró columna de artistas en chart_data")
            conn.close()
            return set()
        safe_column = f'"{artist_column}"' if ' ' in artist_column else artist_column
        cursor.execute(f"SELECT {safe_column} FROM chart_data WHERE {safe_column} IS NOT NULL")
        rows = cursor.fetchall()
        for row in rows:
            if row[0]:
                artists.update(split_artists(str(row[0])))
        conn.close()
        logger.info(f"📊 {len(artists)} artistas únicos en la base de datos de charts")
        return artists
    except Exception as e:
        logger.error(f"❌ Error leyendo base de datos: {e}")
        if 'conn' in locals():
            conn.close()
        return set()

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================
def main():
    logger.info("="*80)
    logger.info("🎵 Artist Country + Genre Detection System - MODO GITHUB")
    logger.info(f"📁 DB de charts: {CHARTS_DB_DIR}")
    logger.info(f"💾 DB de artistas: {ARTIST_DB_PATH}")
    logger.info("="*80)

    create_database()

    chart_db = get_latest_chart_database()
    if not chart_db:
        logger.error("❌ No se pudo obtener la base de datos de charts. Abortando.")
        sys.exit(1)

    chart_artists = get_artists_from_chart_db(chart_db)
    if not chart_artists:
        logger.error("❌ No se encontraron artistas en la base de datos.")
        sys.exit(1)

    logger.info(f"🎯 {len(chart_artists)} artistas únicos a procesar\n")

    in_db = 0
    new_found = 0
    not_found = 0
    genre_found = 0

    for i, artist in enumerate(sorted(chart_artists), 1):
        exists, db_country, db_genre = artist_in_database(artist)

        if exists and db_country and db_country != 'Unknown' and db_genre and db_genre != 'Unknown':
            logger.info(f"  ✅ {artist} → {db_country} | {db_genre}")
            in_db += 1
            genre_found += 1
        else:
            if exists:
                logger.info(f"  🔍 {artist} (en DB - País: {db_country or '?'} | Género: {db_genre or '?'}, buscando info faltante...)")
            else:
                logger.info(f"  🔍 {artist} (nuevo, buscando...)")

            country, country_source = search_country(artist)

            genre = None
            genre_source = ""
            if not db_genre or db_genre == 'Unknown':
                genre, genre_source = search_artist_genre(artist, country)

            final_country = country if country else (db_country if db_country else "Unknown")
            final_genre = genre if genre else (db_genre if db_genre else None)

            source_combined = []
            if country_source != "Not found":
                source_combined.append(country_source)
            if genre_source and genre_source != "Género no encontrado":
                source_combined.append(genre_source)

            final_source = " | ".join(source_combined) if source_combined else ""

            insert_artist(artist, final_country, final_genre, final_source)

            if country and country != 'Unknown':
                new_found += 1
            if genre:
                genre_found += 1
            if not country and not genre:
                not_found += 1

        if i % 10 == 0:
            logger.info(f"\n  📊 {i}/{len(chart_artists)} | "
                        f"✅ Completos: {in_db} | 🔍 Nuevos país: {new_found} | 🎵 Nuevos género: {genre_found} | ❌ Sin info: {not_found}\n")

    logger.info("\n" + "="*80)
    logger.info(f"📈 SUMMARY")
    logger.info(f"   Total artistas procesados: {len(chart_artists)}")
    if len(chart_artists) > 0:
        logger.info(f"   ✅ Completos (país+género): {in_db} ({in_db/len(chart_artists)*100:.1f}%)")
        logger.info(f"   🔍 Nuevos país encontrados: {new_found} ({new_found/len(chart_artists)*100:.1f}%)")
        logger.info(f"   🎵 Nuevos género encontrados: {genre_found} ({genre_found/len(chart_artists)*100:.1f}%)")
        logger.info(f"   ❌ Sin información: {not_found} ({not_found/len(chart_artists)*100:.1f}%)")
    logger.info(f"   🗃️  Total en DB: {count_artists_in_database()}")
    logger.info("="*80)

if __name__ == "__main__":
    main()

