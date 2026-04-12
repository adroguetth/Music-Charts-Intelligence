"""
Country canonicalization dictionary.

Maps country names, cities, demonyms, and regional variants to canonical
country names. Used for validating and normalizing location data from APIs.
"""

from typing import Dict, Set

# =============================================================================
# CANONICAL COUNTRY MAPPINGS
# =============================================================================
# Format: 'Canonical Country Name': {'variant1', 'variant2', ...}
# Includes: official names, common names, demonyms (EN/ES), major cities,
#           cultural regions, and common misspellings.

COUNTRIES_CANONICAL: Dict[str, Set[str]] = {
    # =========================================================================
    # NORTH AMERICA
    # =========================================================================
    'United States': {
        # Country names
        'united states', 'usa', 'us', 'u.s.', 'u.s.a.', 'america',
        'estados unidos', 'ee.uu.', 'eeuu', 'estadosunidos',
        # Demonyms EN/ES
        'american', 'americano', 'americanos', 'estadounidense', 'estadounidenses',
        # Cities — Northeast
        'new york', 'nyc', 'brooklyn', 'bronx', 'queens', 'manhattan', 'staten island',
        'boston', 'philadelphia', 'philly', 'baltimore', 'pittsburgh',
        'washington d.c.', 'dc', 'newark', 'hartford', 'providence', 'buffalo',
        # Cities — Southeast
        'miami', 'miami beach', 'fort lauderdale', 'orlando', 'tampa', 'jacksonville',
        'atlanta', 'charlotte', 'raleigh', 'nashville', 'memphis', 'new orleans',
        'louisville', 'richmond', 'virginia beach', 'columbia sc',
        # Cities — Midwest
        'chicago', 'detroit', 'cleveland', 'columbus', 'indianapolis',
        'milwaukee', 'minneapolis', 'saint paul', 'st. louis', 'kansas city',
        'cincinnati', 'omaha', 'des moines',
        # Cities — Southwest / Texas
        'houston', 'dallas', 'fort worth', 'san antonio', 'austin', 'el paso',
        'albuquerque', 'tucson', 'phoenix', 'las vegas', 'henderson',
        # Cities — West
        'los angeles', 'la', 'hollywood', 'compton', 'long beach', 'anaheim',
        'san francisco', 'sf', 'bay area', 'oakland', 'san jose',
        'sacramento', 'san diego', 'portland', 'seattle', 'denver',
        'salt lake city', 'boise',
        # Cities — Hawaii / Alaska
        'honolulu', 'anchorage',
    },

    'Canada': {
        'canada', 'canadá', 'canadian', 'canadiense', 'canadienses',
        # EN regional
        'canuck', 'anglo-canadian', 'franco-canadian', 'québécois',
        # Cities
        'toronto', 'montreal', 'montréal', 'vancouver', 'calgary',
        'edmonton', 'ottawa', 'québec city', 'quebec', 'winnipeg',
        'hamilton', 'kitchener', 'victoria', 'london ontario', 'halifax',
        'saskatoon', 'regina', 'windsor', 'oshawa', 'moncton', 'fredericton',
        # Regions
        'ontario', 'british columbia', 'alberta', 'québec', 'nova scotia',
        'new brunswick', 'manitoba', 'saskatchewan',
    },

    'Mexico': {
        'mexico', 'méxico', 'méjico',
        # Demonyms
        'mexican', 'mexicano', 'mexicana', 'mexicanos', 'mexicanas', 'azteca',
        # Cities
        'ciudad de méxico', 'cdmx', 'df', 'distrito federal',
        'guadalajara', 'monterrey', 'puebla', 'tijuana',
        'juárez', 'ciudad juárez', 'léon', 'zapopan', 'nezahualcóyotl',
        'chihuahua', 'naucalpan', 'mérida', 'san luis potosí', 'aguascalientes',
        'hermosillo', 'saltillo', 'mexicali', 'culiacán', 'acapulco',
        'torreón', 'morelia', 'toluca', 'querétaro', 'cancún',
        'veracruz', 'oaxaca', 'xalapa', 'tuxtla gutiérrez',
        # Cultural regions
        'norteño', 'chilango', 'tapatío', 'regiomontano', 'defeño',
    },

    # =========================================================================
    # CENTRAL AMERICA AND THE CARIBBEAN
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
        # Cultural terms
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
    # SOUTH AMERICA
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
        # Regions
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
    # WESTERN EUROPE
    # =========================================================================
    'United Kingdom': {
        'united kingdom', 'uk', 'reino unido', 'great britain', 'britain',
        # Demonyms
        'british', 'english', 'inglés', 'inglesa', 'británico', 'británica',
        'scottish', 'escocés', 'escocesa', 'welsh', 'galés', 'galesa',
        'northern irish', 'ulsterman',
        # Cities — England
        'london', 'londres', 'manchester', 'birmingham', 'liverpool',
        'leeds', 'bristol', 'sheffield', 'nottingham', 'leicester',
        'newcastle', 'coventry', 'southampton', 'oxford', 'cambridge',
        'brighton', 'reading', 'portsmouth', 'sunderland', 'wolverhampton',
        # Cities — Scotland, Wales, Northern Ireland
        'glasgow', 'edinburgh', 'edimburgo', 'aberdeen', 'dundee',
        'cardiff', 'swansea', 'belfast',
        # Cultural regions
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
        # Regions
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
        # Regions
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
        # Regions
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
        # Regions
        'sicilia', 'sicily', 'sardegna', 'sardinia', 'cerdeña',
        'toscana', 'tuscany', 'lazio', 'lombardia', 'lombardy',
        'calabria', 'puglia', 'apulia', 'veneto', 'liguria',
    },

    'Portugal': {
        'portugal', 'portuguese', 'português', 'portugues', 'portuga',
        'lisbon', 'lisboa', 'lisboeta',
        'porto', 'braga', 'coimbra', 'funchal', 'setúbal',
        'aveiro', 'viseu', 'leiria', 'faro', 'évora',
        # Regions and archipelagos
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
    # WEST ASIA / MIDDLE EAST
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
    # SOUTH ASIA
    # =========================================================================
    'India': {
        'india', 'indian', 'indio', 'india', 'bharatiya', 'bharat', 'hindustan',
        # Film industries
        'bollywood', 'tollywood', 'kollywood', 'mollywood', 'sandalwood',
        # Cities
        'mumbai', 'bombay', 'delhi', 'new delhi', 'kolkata', 'calcutta',
        'chennai', 'madras', 'bangalore', 'bengaluru', 'hyderabad',
        'ahmedabad', 'pune', 'surat', 'jaipur', 'lucknow',
        'kanpur', 'nagpur', 'indore', 'thane', 'bhopal',
        'visakhapatnam', 'vizag', 'patna', 'vadodara', 'ludhiana',
        'agra', 'nashik', 'ranchi', 'meerut', 'rajkot', 'varanasi',
        'srinagar', 'amritsar', 'allahabad', 'prayagraj', 'guwahati',
        'chandigarh', 'coimbatore', 'kochi', 'cochin', 'thiruvananthapuram',
        'madurai', 'vijayawada', 'aurangabad', 'gwalior', 'jodhpur',
        # Regional demonyms
        'punjabi', 'bengalí', 'tamul', 'tamil', 'telugu', 'kannada',
        'malayali', 'gujarati', 'marathi', 'rajasthani', 'bihari',
        'assamese', 'odia', 'kashmiri', 'sikh',
        # Regions/States
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
        # Industry
        'lollywood',
        # Regions
        'punjab (pakistan)', 'sindh', 'khyber pakhtunkhwa', 'kpk', 'balochistan',
        'gilgit-baltistan', 'azad kashmir',
    },

    'Bangladesh': {
        'bangladesh', 'bangladeshi', 'bangladesí', 'bangladeshi', 'bangali',
        'dhaka', 'chittagong', 'chattogram', 'khulna', 'rajshahi',
        'sylhet', 'barisal', 'rangpur', 'mymensingh', 'comilla', 'narayanganj',
        # Industry
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
    # EAST ASIA
    # =========================================================================
    'China': {
        'china', 'chinese', 'chino', 'china', 'zhongguo', 'zhonghua',
        'beijingese', 'shanghainese', 'cantonese', 'cantones', 'mandarín',
        # Cities
        'beijing', 'pekín', 'shanghai', 'shanghái', 'hong kong', 'hongkong',
        'guangzhou', 'cantón', 'shenzhen', 'chengdu', 'tianjin',
        'wuhan', 'chongqing', 'nanjing', 'hangzhou', 'xian', "xi'an",
        'qingdao', 'dalian', 'shenyang', 'dongguan', 'foshan',
        'kunming', 'harbin', 'zhengzhou', 'changsha', 'jinan',
        'wuxi', 'suzhou', 'hefei', 'nanchang', 'shijiazhuang',
        'guiyang', 'taiyuan', 'lanzhou', 'urumqi', 'lhasa',
        # Special regions
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
        # Cities
        'tokyo', 'tokio', 'osaka', 'nagoya', 'yokohama', 'sapporo',
        'fukuoka', 'kyoto', 'kobe', 'kawasaki', 'saitama', 'hiroshima',
        'sendai', 'kitakyushu', 'chiba', 'sakai', 'niigata',
        'hamamatsu', 'kumamoto', 'okayama', 'shizuoka', 'naha',
        # Islands
        'okinawa', 'hokkaido', 'kyushu', 'shikoku', 'honshu',
        # Pop culture
        'j-pop', 'jpop', 'j-rock', 'anime', 'otaku',
    },

    'South Korea': {
        'south korea', 'corea del sur', 'korea', 'korean', 'coreano', 'coreana',
        'hanguk', 'koreans', 'hangukssaram',
        # Cities
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
    # SOUTH EAST ASIA
    # =========================================================================
    'Indonesia': {
        'indonesia', 'indonesian', 'indonesio', 'indonesa', 'orang indonesia',
        'javanese', 'javanés', 'sundanese', 'sundanés', 'balinese', 'balinés',
        'jakarta', 'surabaya', 'bandung', 'medan', 'semarang',
        'makassar', 'yogyakarta', 'jogja', 'palembang', 'denpasar',
        'batam', 'pekanbaru', 'bandar lampung', 'malang', 'padang',
        'samarinda', 'balikpapan', 'manado',
        # Islands/regions
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
        # Islands
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
    # CENTRAL ASIA
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
    # NORTH AFRICA
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
    # WEST AFRICA
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
    # EAST AFRICA
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
    # CENTRAL AFRICA
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
    # SOUTH AFRICA
    # =========================================================================
    'South Africa': {
        'south africa', 'sudáfrica', 'south african', 'sudafricano', 'sudafricana',
        'zulu', 'xhosa', 'sotho', 'tswana', 'coloured', 'afrikaner',
        'johannesburg', 'joburg', 'jozi', 'cape town', 'ciudad del cabo',
        'durban', 'pretoria', 'tshwane', 'port elizabeth',
        'gqeberha', 'bloemfontein', 'east london', 'pietermaritzburg',
        'soweto', 'benoni', 'tembisa', 'midrand', 'vereeniging',
        # Regions
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
        # Cities
        'sydney', 'melbourne', 'brisbane', 'perth', 'adelaide',
        'canberra', 'gold coast', 'newcastle', 'wollongong', 'hobart',
        'darwin', 'townsville', 'geelong', 'cairns', 'toowoomba',
        # Regions
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

# =============================================================================
# REVERSE MAPPING: VARIANT → CANONICAL COUNTRY
# =============================================================================
# Generated automatically from COUNTRIES_CANONICAL for O(1) lookups.

VARIANT_TO_COUNTRY: Dict[str, str] = {}
for country, variants in COUNTRIES_CANONICAL.items():
    for v in variants:
        VARIANT_TO_COUNTRY[v] = country
