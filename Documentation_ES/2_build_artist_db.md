# 🎵 Script 2: Artist Country + Genre Detection System, Intelligent Enrichment

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square) ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![Requests](https://img.shields.io/badge/Requests-FF6F61?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia API](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white) ![Wikidata](https://img.shields.io/badge/Wikidata-990000?style=flat-square&logo=wikidata&logoColor=white) ![DeepSeek](https://custom-icon-badges.demolab.com/badge/DeepSeek-4D6BFF?logo=deepseek&logoColor=white&style=flat-square)

## 📥 Quick Downloads
| Document                | Format                                                     |                                                    
| ------------------------- | ------------------------------------------------------------ |
| **🇬🇧 English Documentation** | [PDF](https://drive.google.com/file/d/1viUAxZ7k-qeYYbyvZf2OaP20AfLOgKh2/view?usp=drive_link) |
| **🇪🇸 Spanish Documentation**  | [PDF](https://drive.google.com/file/d/1WBHBreKeVToTBygSyCuYsHQUr_zSl3BT/view?usp=drive_link) |

## 📋 Descripción General

Este proyecto es el segundo componente del sistema de inteligencia de YouTube Charts. Toma los nombres de artistas extraídos por el descargador y los **enriquece con metadatos geográficos y de género** consultando múltiples bases de conocimiento abiertas. El resultado es una base de datos estructurada de artistas con su país de origen y género musical principal.

### Características Principales

- **Búsqueda Multi-Fuente**: Consultas en cascada inteligentes a MusicBrainz, Wikipedia (resumen e infobox) y Wikidata
- **DeepSeek IA como Respaldo**: Usa la API de DeepSeek como último recurso cuando fallan todas las fuentes gratuitas (económico, ~$0.002 por 100 artistas)
- **Variación Inteligente de Nombres**: Genera hasta 15 variaciones por artista (acentos eliminados, prefijos quitados, etc.) para máxima tasa de coincidencia
- **Inteligencia Geográfica**: Detección de país a partir de ciudades, gentilicios y referencias regionales usando un diccionario curado de más de 30,000 términos
- **Clasificación de Géneros**: Más de 200 macro-géneros y 5,000+ mapeos de subgéneros con sistema de votación ponderada
- **Reglas Específicas por País**: Manejo especial para más de 50 países (ej. K-Pop para Corea del Sur, Sertanejo para Brasil)
- **Detección de Escritura**: Detección automática de idioma para escrituras no latinas (Cirílico, Devanagari, Árabe, Hangul, etc.)
- **Actualizaciones Inteligentes**: Solo completa datos faltantes, nunca sobrescribe información correcta existente
- **Caché en Memoria**: Evita llamadas API redundantes durante la ejecución
- **Optimizado para CI/CD**: Configurado específicamente para GitHub Actions con respaldos progresivos
- **Límites de Tasa**: Retrasos integrados para respetar cuotas de API y evitar bloqueos

## 📊 Diagramas de Flujo del Proceso

### **Leyenda**

| Color          | Tipo     | Descripción                            |
| :------------- | :------- | :------------------------------------- |
| 🔵 Azul         | Entrada  | Datos fuente (base de datos de charts) |
| 🟠 Naranja      | Proceso  | Lógica de procesamiento interno        |
| 🟣 Morado       | API      | Consultas a servicios externos         |
| 🟢 Verde        | Caché    | Almacenamiento temporal en memoria     |
| 🔴 Rojo         | Decisión | Puntos de ramificación condicional     |
| 🟢 Verde Oscuro | Salida   | Resultados y base de datos final       |

### **Diagrama 1: Vista General del Flujo Principal**

<img src="https://drive.google.com/uc?export=view&id=1Bn8U0DY8ds-hESUBxgssPtqAPvsq1YLw" alt="Flujo Principal" width="400">

Este diagrama muestra el **pipeline de alto nivel** de todo el sistema:

1. **Entrada**: Lee la base de datos semanal de YouTube Charts (`youtube_charts_YYYY-WXX.db`)
2. **Extracción**: Lee nombres de artistas y los divide (maneja "feat.", "&", comas, etc.)
3. **Desduplicación**: Crea una lista de artistas únicos para evitar procesamiento redundante
4. **Bucle por Artista**: Para cada artista, verifica si ya existe en la base de datos enriquecida
   - **Si está completo** (país + género conocidos): Salta al siguiente artista ✅
   - **Si falta información**: Busca solo los campos faltantes (país o género)
   - **Si es nuevo**: Realiza búsqueda completa de país y género
5. **Búsqueda de País** → **Búsqueda de Género** → **Sistema de Votación** → **Actualización de Base de Datos**
6. **Después de todos los artistas**: Genera un informe final y confirma automáticamente los cambios en GitHub

### **Diagrama 2: Búsqueda de País (Detallada)**

<img src="https://drive.google.com/uc?export=view&id=1932QMOwkdTmppIw1awhWgMa-b0dWLk2w" alt="Búsqueda de País" width="250">

Este diagrama detalla la **estrategia de búsqueda en cascada** para detectar el país de un artista:

1. **Inicio**: Recibe un nombre de artista (puede faltar información o ser nuevo)
2. **Variaciones de Nombre**: Genera hasta 15 variaciones (sin acentos, sin prefijos, etc.)
3. **Verificación de Caché**: Primero verifica la caché en memoria para evitar llamadas API repetidas
4. **MusicBrainz**: Consulta la API de MusicBrainz (datos estructurados, alta confiabilidad)
   - Si se encuentra → retorna país ✅
5. **Wikipedia en Inglés**: Si no se encuentra, consulta Wikipedia en inglés:
   - Primero verifica el resumen (primer párrafo) en busca de patrones como "nacido en...", "de..."
   - Luego verifica la infobox en busca de campos como "origin", "birth_place", "location"
   - Si se encuentra → retorna país ✅
6. **Wikipedia en Idiomas Prioritarios**: Si aún no se encuentra, intenta Wikipedia en idiomas basados en:
   - El país del artista (si ya se conoce del paso anterior)
   - La escritura detectada del nombre del artista (Cirílico → Wikipedia en ruso, etc.)
   - Si se encuentra → retorna país ✅
7. **Wikidata**: Última fuente gratuita, consulta Wikidata usando las propiedades P27 (país de ciudadanía) y P19 (lugar de nacimiento)
8. **DeepSeek IA como Respaldo**: Solo si fallan todas las fuentes gratuitas, consulta la API de DeepSeek (económico)
   - Usa un prompt estructurado pidiendo país y género
   - Los resultados se normalizan usando las mismas funciones de validación
   - Limitado a 0.5s de retraso entre llamadas
9. **Resultado**: Retorna un nombre de país canónico o "Desconocido"

### **Diagrama 3: Búsqueda de Género (Detallada)**

<img src="https://drive.google.com/uc?export=view&id=1kPow9lkOp_g5MBzKmWi0nyivbE89JtHY" alt="Búsqueda de Género" width="200">

Este diagrama muestra cómo el sistema **recopila candidatos de género** de múltiples fuentes:

1. **Inicio**: Recibe nombre del artista (y país si ya está detectado)
2. **Variaciones de Nombre**: Mismo sistema de variaciones para máxima tasa de coincidencia
3. **MusicBrainz**: Primera fuente, extrae etiquetas de género y sus conteos
   - Agrega candidatos con peso base (1.5x para MusicBrainz)
4. **Wikidata**: Segunda fuente, consulta la propiedad P136 (género)
   - Agrega candidatos con peso base (1.3x para Wikidata)
5. **Verificación de Candidatos**: Verifica si ya tenemos al menos 3 candidatos de género
   - **Si es sí**: Procede directamente al sistema de votación
   - **Si es no**: Continúa con la búsqueda en Wikipedia
6. **Wikipedia en Idiomas Prioritarios**: Consulta Wikipedia en idiomas priorizados por:
   - País (ej. artistas coreanos → Wikipedia en coreano)
   - Escritura detectada (ej. nombre árabe → Wikipedia en árabe)
7. **Extracción**: Usa coincidencia de patrones para extraer géneros de:
   - **Infobox**: Busca campos "genre", "genres", "género"
   - **Resumen**: Usa patrones de NLP como "es un cantante de [género]", "conocido por música [género]"
8. **Segunda Verificación**: Si aún hay menos de 3 candidatos, intenta Wikipedia en otros idiomas comunes
9. **DeepSeek IA como Respaldo**: Solo si todas las fuentes gratuitas no devuelven candidatos, consulta la API de DeepSeek
   - Usa el país (si se conoce) como contexto para mejorar la precisión
   - Retorna un género normalizado o texto sin procesar
10. **Final**: Todos los candidatos (con sus pesos y fuentes) van al Sistema de Votación

### **Diagrama 4: Sistema de Votación y Pesos**

<img src="https://drive.google.com/uc?export=view&id=1hopeWo6XpnalvK98aDi5fqdZwSSPtYTl" alt="Actualización de Base de Datos" width="350">

Este es el **motor de decisión inteligente** que selecciona el género final:

1. **Entrada**: Recibe todos los candidatos de género con sus pesos y fuentes originales
2. **Normalización**: Mapea cada subgénero específico a un macro-género usando el diccionario `GENRE_MAPPINGS`
   - Ejemplo: "synth pop", "synth-pop", "synthpop" todos → "Pop"
3. **Pesos por Fuente**: Aplica multiplicadores basados en la confiabilidad de la fuente:
   - MusicBrainz: ×1.5 (estructurado, confiable)
   - Wikidata: ×1.3 (semántico, confiabilidad media)
   - Wikipedia Infobox: ×1.2 (semi-estructurado)
   - Wikipedia Resumen: ×1.0 (texto libre, menor confianza)
   - Wikipedia Palabras Clave: ×0.5 (confianza más baja)
4. **Detección de Escritura**: Analiza el nombre del artista para detectar el sistema de escritura (Cirílico, Hangul, Árabe, etc.)
5. **Bonificaciones por Término**: Multiplica el peso por 1.4x si se encuentran palabras clave específicas:
   - "reggaeton", "trap latino" → aumenta géneros latinos
   - "k-pop", "korean pop" → aumenta K-Pop
   - "sertanejo", "funk brasileiro" → aumenta géneros brasileños
6. **Prioridad por País** (si el país es conocido): Aplica multiplicadores adicionales basados en la lista de prioridad de géneros del país:
   - 1er género prioritario: ×2.0
   - 2do género prioritario: ×1.5
   - 3er+ géneros prioritarios: ×1.2
7. **Reglas Específicas por País**: Aplica reglas especiales para ciertos países:
   - **force_macro**: Fuerza un macro-género específico (ej. Puerto Rico → Reggaetón/Trap Latino)
   - **map_generic_to**: Mapea géneros genéricos (Pop, Rock) a regionales (ej. Corea → K-Pop/K-Rock)
8. **Bonificación por Escritura**: Si la escritura detectada coincide con el idioma dominante del país, aplica ×1.2
9. **Suma de Votos**: Suma todos los votos ponderados para cada macro-género
10. **Selección del Ganador**: Elige el macro-género con mayor total de votos
11. **Respaldo**: Si no hay ganador y el país es conocido, usa el primer género de la lista de prioridad del país

### **Diagrama 5: Actualización de Base de Datos**

<img src="https://drive.google.com/uc?export=view&id=1IKXuumnAqDQEW3TfxK-XDldHsAMhWOXG" alt="Actualización de Base de Datos" width="350">

Este diagrama muestra cómo el sistema **persiste los datos de forma inteligente**:

1. **Entrada**: Recibe los datos finales de país y género para un artista
2. **Conectar**: Abre conexión a `artist_countries_genres.db`
3. **Verificación de Existencia**: Consulta si el artista ya existe en la base de datos
4. **Si el Artista Existe**:
   - **Verificar Campos Faltantes**: Compara los datos existentes con los nuevos
   - **Actualizar Solo Faltantes**: Actualiza país solo si el existente es NULL/Desconocido y el nuevo es conocido
   - Actualiza género solo si el existente es NULL/Desconocido y el nuevo es conocido
   - **¡Nunca sobrescribe** datos correctos existentes!
5. **Si el Artista es Nuevo**:
   - Inserta un nuevo registro completo con país y género
6. **Registrar Estadísticas**: Registra éxito/fracaso para el informe
7. **Verificación de Bucle**: Si quedan más artistas, vuelve al bucle principal
8. **Todos los Artistas Procesados**:
   - Genera informe final con estadísticas (tasa de éxito, nuevos artistas, etc.)
9. **Commit en GitHub**: Confirma y sube automáticamente los cambios al repositorio
    
---
## Análisis Detallado de `2_build_artist_db.py`

### Estructura del Código

#### **1. Configuración y Rutas**
```python
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CHARTS_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"
ARTIST_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_countries-genres-artist" / "artist_countries_genres.db"
```

El script lee la salida del descargador y crea su propia base de datos enriquecida:
- **Entrada**: Bases de datos semanales de charts del paso 1 (`youtube_charts_YYYY-WXX.db`)
- **Salida**: Base de datos de metadatos de artistas (`artist_countries_genres.db`)
- **Estructura**: `charts_archive/2_countries-genres-artist/`

#### **2. Sistema Inteligente de Variación de Nombres**

```python
def generate_all_variations(name: str) -> List[str]:
    """
    Genera hasta 15 variaciones de un nombre de artista:
    - Original
    - Sin acentos
    - Sin puntos
    - Sin guiones
    - Sin prefijos (DJ, MC, Lil, The, etc.)
    - Combinaciones de lo anterior
    """
```

**Ejemplo para "Lil Wayne":**

```python
Lil Wayne
Wayne
Lil Wayne
Lil Wayne
Wayne
... (hasta 15 variaciones)
```

**El diccionario de prefijos incluye:**

```python
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
```

#### **3. Sistema de Inteligencia Geográfica**

El corazón de la detección de país es el diccionario `COUNTRIES_CANONICAL`, una base de conocimiento curada con **más de 30,000 términos** mapeados a más de 200 países.

**Ejemplo de estructura para Estados Unidos:**

```python
'United States': {
    # Nombres de países
    'united states', 'usa', 'us', 'u.s.', 'u.s.a.', 'america',
    'estados unidos', 'ee.uu.', 'eeuu', 'estadosunidos',
    # Gentilicios
    'american', 'americano', 'americanos', 'estadounidense', 'estadounidenses',
    # Ciudades — Cubre los 50 estados
    'new york', 'nyc', 'brooklyn', 'los angeles', 'la', 'chicago',
    'houston', 'phoenix', 'philadelphia', 'san antonio', 'san diego',
    'dallas', 'austin', 'miami', 'atlanta', 'boston', ... (500+ ciudades)
}
```

**Proceso de detección:**
1. **Coincidencia directa**: "canadian" → Canadá
2. **Mención de ciudad**: "from Toronto" → Canadá
3. **Referencia regional**: "born in Brooklyn" → Estados Unidos
4. **Gentilicio**: "argentine singer" → Argentina

#### **4. Ontología de Clasificación de Géneros**

El diccionario `GENRE_MAPPINGS` contiene **más de 5,000 variantes de géneros** mapeadas a más de 200 macro-géneros.s.

**Ejemplo de mapeo para música electrónica:**

```python
# Variantes de House
'house': ('Electrónica/Dance', 'house'),
'deep house': ('Electrónica/Dance', 'deep house'),
'progressive house': ('Electrónica/Dance', 'progressive house'),
'tech house': ('Electrónica/Dance', 'tech house'),
'tropical house': ('Electrónica/Dance', 'tropical house'),

# Variantes de Techno
'techno': ('Electrónica/Dance', 'techno'),
'detroit techno': ('Electrónica/Dance', 'detroit techno'),
'minimal techno': ('Electrónica/Dance', 'minimal techno'),

# Variantes de Trance
'trance': ('Electrónica/Dance', 'trance'),
'psytrance': ('Electrónica/Dance', 'psytrance'),
'goa trance': ('Electrónica/Dance', 'goa trance'),
```

**Categorías de macro-géneros (más de 200):**

- **Globales**: `Pop`, `Rock`, `Hip-Hop/Rap`, `R&B/Soul`, `Electrónica/Dance`
- **América Regional**: `Reggaetón/Trap Latino`, `Bachata`, `Cumbia`, `Sertanejo`, `Funk Brasileiro`, `Regional Mexicano`, `Vallenato`
- **Asia Regional**: `K-Pop/K-Rock`, `J-Pop/J-Rock`, `C-Pop/C-Rock`, `T-Pop/T-Rock`, `V-Pop/V-Rock`, `OPM`, `Indonesian Pop/Dangdut`, `Pakistani Pop`
- **África Regional**: `Afrobeats`, `Amapiano`, `Bongo Flava`, `Zim Dancehall`, `Kuduro`, `Kizomba/Zouk`
- **Europa Regional**: `Turbo-folk`, `Manele`, `Schlager`, `Chanson`, `Flamenco / Copla`, `Canzone Italiana`
- **Indígenas**: `Māori Pop/Rock`, `Aboriginal Australian Pop/Rock`, `Siberian Indigenous Pop/Rock`, `Hawaiian Pop/Rock`

#### **5. Multi-Source API Queries**

El script consulta cuatro bases de conocimiento en cascada (con DeepSeek como respaldo final):

```python
def search_artist_genre(artist: str, country: Optional[str] = None):
    """
    Flujo de búsqueda optimizado:
    1. MusicBrainz (estructurado, alta confiabilidad) → 1.5x peso
    2. Wikidata (semántico, confiabilidad media) → 1.3x peso
    3. Wikipedia en idiomas prioritarios (texto rico) → 1.0-1.2x peso
    4. API de DeepSeek (respaldo, solo cuando fallan todas las fuentes gratuitas) → resultado normalizado
    """
```

**Consulta a MusicBrainz:**

```python
url = "https://musicbrainz.org/ws/2/artist/"
params = {'query': artist, 'fmt': 'json', 'limit': 1}
# Retorna etiquetas de género estructuradas con puntuaciones de confianza
```

**Extracción de infobox de Wikipedia:**

```text
# Extrae de Infobox musical artist
# Campos buscados: genre, géneros, genres
# Ejemplo: | genre = [[Pop music|Pop]], [[R&B]]
```

**Extracción de resumen de Wikipedia con patrones de NLP:**

```python
patterns = [
    r'is\s+(?:a|an)\s+([a-z\s\-]+?)\s+(?:singer|rapper|musician)',
    r'are\s+(?:a|an)\s+([a-z\s\-]+?)\s+(?:band|group)',
    r'known\s+for\s+their\s+([a-z\s\-]+?)\s+music',
    r'genre\s+is\s+([a-z\s\-]+?)(?:\.|,|$)'
]
```

**Respaldo con API de DeepSeek:**

```python
def search_deepseek_fallback(artist: str, context_country: Optional[str] = None):
    """
    Usa IA de DeepSeek como último recurso cuando fallan todas las fuentes gratuitas.
    - Costo: ~146-1194 tokens por solicitud (~$0.002 por 100 artistas)
    - Limitado por tasa: 0.5s de retraso entre llamadas
    - Almacenado en caché para evitar solicitudes redundantes
    - Retorna país y género normalizados
    """
```

#### **6. Sistema Inteligente de Caché**

```python
_CACHE = {
    'musicbrainz_country': {},
    'wikidata_country': {},
    'wikipedia_country': {},
    'musicbrainz_genre': {},
    'wikidata_genre': {},
    'wikipedia_genre': {},
}

_DEEPSEEK_CACHE = {}  # Caché para resultados de DeepSeek
```

**Beneficios:**

- **Rendimiento**: Evita llamadas API redundantes para el mismo artista
- **Cortesía**: Reduce la carga en servicios externos
- **Velocidad**: Caché en memoria para la ejecución actual
- **Reutilización de sesiones**: Conexiones persistentes para múltiples consultas
- **Ahorro de costos**: Caché de DeepSeek evita llamadas pagadas duplicadas

#### **7. Detección de Escritura/Idioma**

```python
def detect_script_from_name(name: str) -> Optional[str]:
    """
    Detecta el sistema de escritura y retorna código de idioma ISO 639-1.
    
    Rangos detectados:
    - Devanagari (hi, ne) → India/Nepal
    - Tamil (ta) → Sur de India/Sri Lanka
    - Árabe/Urdu (ar/ur) → Medio Oriente/Pakistán
    - Cirílico (ru/uk/bg/sr) → Europa del Este
    - Hangul (ko) → Corea
    - Hanzi/Kanji (zh/ja) → China/Japón
    """
```
**Usado para:**

- Priorizar consultas de Wikipedia en el idioma correcto
- Aplicar bonificaciones regionales (ej. escritura coreana → K-Pop)
- Mejorar la generación de variaciones de nombre
- Proporcionar contexto al respaldo de DeepSeek

#### **8. Sistema de Votación Ponderada**

La función `select_primary_genre` implementa un sofisticado algoritmo de votación:

```python
def select_primary_genre(artist: str, genre_candidates: List[Tuple[str, int, str]],
                         country: Optional[str] = None, detected_lang: Optional[str] = None):
    """
    Sistema de votación ponderada:
    - Peso base de la fuente (MusicBrainz 1.5x, Infobox 1.2x, Wikidata 1.3x)
    - Bonificaciones por término para géneros específicos (K-Pop, Reggaetón, etc.) 1.4x
    - Bonificación por prioridad de país (primer género 2.0x, segundo 1.5x)
    - Reglas específicas por país (force_macro, map_generic_to)
    - Bonificación por detección de escritura (1.2x para región coincidente)
    """
```

**Ejemplo para un artista de Corea del Sur:**

```python
Candidatos de género detectados:
- "k-pop" de MusicBrainz (peso 1.5) → K-Pop/K-Rock
- "pop" de Wikipedia (peso 1.0) → Pop
- "dance" de Wikipedia (peso 0.5) → Electrónica/Dance

País = Corea del Sur (prioridad: K-Pop/K-Rock #1 → 2.0x bonus)
Escritura detectada = Coreano (1.2x bonus para K-Pop/K-Rock)

Votos finales:
- K-Pop/K-Rock: (1.5 × 2.0 × 1.2) = 3.6
- Pop: (1.0 × 1.2) = 1.2
- Electrónica/Dance: (0.5 × 1.2) = 0.6

Ganador: K-Pop/K-Rock ✓
```

#### **9. Reglas Específicas por País**

```python
COUNTRY_SPECIFIC_RULES = {
    "South Korea": {
        "keywords": ["k-pop", "kpop", "korean pop", "idol group"],
        "bonus_extra": 1.5,
        "force_macro": "K-Pop/K-Rock",
        "map_generic_to": "K-Pop/K-Rock"  # Mapea "pop" → K-Pop
    },
    "Brazil": {
        "keywords": ["sertanejo", "funk brasileiro", "funk carioca", "brazilian funk"],
        "bonus_extra": 1.5
    },
    "Jamaica": {
        "keywords": ["dancehall", "reggae", "roots reggae", "dub"],
        "bonus_extra": 1.5
    },
    "Puerto Rico": {
        "keywords": ["reggaeton", "reggaetón", "trap latino", "urbano", "dembow"],
        "bonus_extra": 2.0,
        "force_macro": "Reggaetón/Trap Latino"
    },
    # ... más de 50 países con reglas específicas
}
```

#### **10. Actualizaciones Inteligentes de Base de Datos**

```python
def insert_artist(artist: str, country: str, genre: Optional[str] = None, source: str = ""):
    """
    Inserción/actualización inteligente:
    - Si el artista existe, solo actualiza campos faltantes
    - Nunca sobrescribe datos correctos existentes
    - Rastrea la fuente de información para transparencia
    """
```

**Ejemplos de escenarios:**

```python
Artista ya en BD: (País: USA, Género: null)
Nueva búsqueda encuentra: (País: null, Género: Hip-Hop)
Resultado: (País: USA, Género: Hip-Hop)  ✓ Solo se actualiza el género

Artista ya en BD: (País: null, Género: Rock)
Nueva búsqueda encuentra: (País: UK, Género: Rock)
Resultado: (País: UK, Género: Rock)  ✓ Solo se actualiza el país
```

### **Estructura de la Tabla `artist`**
| Columna     | Tipo   | Descripción                         | Ejemplo        |
| :---------- | :----- | :---------------------------------- | :------------- |
| name        | `TEXT` | Nombre del artista (clave primaria) | "BTS"          |
| country     | `TEXT` | Nombre de país canónico             | "South Korea"  |
| macro_genre | `TEXT` | Macro-género principal              | "K-Pop/K-Rock" |

---
## ⚙️ Análisis del Workflow de GitHub Actions (`2-update-artist-database.yml`)

### **Estructura del Workflow**

```yaml
name: 2- Update Artist Database

on:
  schedule:
    # Se ejecuta cada lunes a las 13:00 UTC (1 hora después de la descarga)
    - cron: '0 13 * * 1'
  
  # Permitir ejecución manual
  workflow_dispatch:

env:
  RETENTION_DAYS: 30
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true   # Adelantar a Node.js 24

jobs:
  build-artist-database:
    name: Build and Update Artist Database
    runs-on: ubuntu-latest
    timeout-minutes: 60
    
    permissions:
      contents: write
```

### **Jobs y Pasos**

#### **Job: `build-artist-database`**

- **Sistema operativo**: Ubuntu Latest
- **Tiempo máximo**: 60 minutos (permite límites de tasa de API y llamadas a DeepSeek)
- **Permisos**: Escritura en el repositorio

#### **Pasos Detallados:**

1. **📚 Checkout del Repositorio**

```yaml
uses: actions/checkout@v4
with:
  fetch-depth: 0  # Historial completo para operaciones git
```

2. **🐍 Configuración de Python 3.12**

```yaml
uses: actions/setup-python@v5
with:
  cache: 'pip'  # Caché de dependencias
```

3. **📦 Instalación de Dependencias**

```yaml
run: |
  pip install -r requirements.txt
```

4. **📁 Creación de Estructura de Directorios**

```yaml
run: |
  mkdir -p charts_archive/1_download-chart/databases
  mkdir -p charts_archive/2_countries-genres-artist
```

5. **🚀 Ejecución del Script Principal con Clave API de DeepSeek**

```yaml
- name: 🚀 Build artist database
  run: |
    python scripts/2_build_artist_db.py
  env:
    GITHUB_ACTIONS: true
    DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
```

6. **✅ Verificación de Integridad de la Base de Datos**
```python
- name: ✅ Verify database integrity
  run: |
    echo "📊 Verifying artist database..."
    DB_PATH="charts_archive/2_countries-genres-artist/artist_countries_genres.db"
    
    # Verificar contenido del directorio
    echo "📂 Directory contents:"
    ls -la charts_archive/2_countries-genres-artist/
    
    # Verificar que la base de datos existe y tiene tamaño
    if [ -f "$DB_PATH" ]; then
      SIZE=$(stat -c%s "$DB_PATH")
      echo "✅ Database found: $((SIZE / 1024)) KB"
      
      # Opcional: Verificar integridad de la base de datos con sqlite3
      if command -v sqlite3 &> /dev/null; then
        echo "🔍 Checking database integrity..."
        sqlite3 "$DB_PATH" "PRAGMA integrity_check;"
      fi
    else
      echo "❌ Database not found!"
      exit 1
    fi
```

7. **📤 Commit y Push Automáticos**
```yaml
- name: 📤 Commit and push changes
  run: |
    echo "📝 Preparing commit..."
    
    # Configurar usuario de git para commits automatizados
    git config --global user.name "github-actions[bot]"
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    
    # Agregar solo archivos de la base de datos de artistas
    git add charts_archive/2_countries-genres-artist/
    
    # Verificar si hay cambios para commit
    if git diff --cached --quiet; then
      echo "🔭 No changes to commit"
    else
      DATE=$(date +'%Y-%m-%d')
      git commit -m "🤖 Update artist database ${DATE} [Automated]"
      
      # Traer últimos cambios con rebase para evitar commits de merge
      echo "⬇️ Pulling latest changes with rebase..."
      git pull --rebase origin main
      
      echo "⬆️ Pushing changes to repository..."
      git push origin HEAD:main
      echo "✅ Changes pushed successfully"
    fi
```

8. **📦 Subida de Artefactos (en caso de fallo)**

```yaml
- name: 📦 Upload debug artifacts
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: artist-db-debug-${{ github.run_number }}
    path: |
      charts_archive/
    retention-days: 7
```

9. **📋 Informe Final**
```yaml
- name: 📋 Generate final report
  if: always()
  run: |
    echo "========================================"
    echo "🎵 FINAL EXECUTION REPORT"
    echo "========================================"
    echo "📅 Date: $(date)"
    echo "📌 Trigger: ${{ github.event_name }}"
    echo "🔗 Commit: ${{ github.sha }}"
    echo ""
    
    DB_FILE="charts_archive/2_countries-genres-artist/artist_countries_genres.db"
    if [ -f "$DB_FILE" ]; then
      SIZE=$(stat -c%s "$DB_FILE")
      echo "✅ Artist database: $((SIZE / 1024)) KB"
      
      # Contar artistas
      if command -v sqlite3 &> /dev/null; then
        ARTIST_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM artist;" 2>/dev/null || echo "N/A")
        echo "👤 Artists processed: ${ARTIST_COUNT}"
      fi
    else
      echo "⚠️ Artist database not found"
    fi
    
    echo ""
    echo "📊 Trigger details:"
    if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
      echo "   • Triggered by: Manual dispatch"
    elif [ "${{ github.event_name }}" = "schedule" ]; then
      echo "   • Triggered by: Scheduled cron (Monday 13:00 UTC)"
    fi
    
    echo ""
    echo "✅ Process completed"
    echo "========================================"
```

### Programación Cron*

```cron
'0 13 * * 1'  # Minuto 0, Hora 13, Cualquier día del mes, Cualquier mes, Lunes
```
- **Ejecución**: Cada lunes a las 13:00 UTC
- **Desfase**: 1 hora después del workflow de descarga (12:00 UTC)
- **Propósito**: Permite que el workflow de descarga complete antes de que comience el enriquecimiento

---

## 🔐 Secretos Requeridos
| Secreto            | Propósito                                                    |
| :----------------- | :----------------------------------------------------------- |
| `DEEPSEEK_API_KEY` | Utilizado por el sistema de respaldo DeepSeek AI para obtener información de país y género cuando todas las fuentes gratuitas (MusicBrainz, Wikidata, Wikipedia) fallan en devolver resultados. Requerido solo para la funcionalidad de respaldo; el script continúa sin él si no se proporciona. |

---

## 🚀 Instalación y Configuración Local

### **Prerequisites**
- Python 3.7 o superior
- Git instalado
- Acceso a Internet para consultas API
- (Opcional) Clave API de DeepSeek para respaldo

### **Instalación Paso a Paso**

1. **Clonar el Repositorio**
```bash
git clone <repository-url>
cd <project-directory>
```

2. **Crear Entorno Virtual (recomendado)**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instalar Dependencias**

```bash
pip install -r requirements.txt
```

4. **Configurar Clave API de DeepSeek (opcional, para respaldo)**
```bash
# Linux/Mac
export DEEPSEEK_API_KEY="tu-clave-api-aqui"

# Windows (Command Prompt)
set DEEPSEEK_API_KEY=tu-clave-api-aqui

# Windows (PowerShell)
$env:DEEPSEEK_API_KEY="tu-clave-api-aqui"
```

5. **Ejecutar Prueba Inicial**
```bash
python scripts/2_build_artist_db.py
```

### **Configuración de Desarrollo**
```bash
# Para simular el entorno de GitHub Actions
export GITHUB_ACTIONS=true

# Para depuración detallada (muestra candidatos de género)
export LOG_LEVEL=DEBUG
```

---

## 📁 Generated File Structure
```text
charts_archive/
├── 1_download-chart/
│   ├── latest_chart.csv
│   ├── databases/
│   │   ├── youtube_charts_2025-W01.db
│   │   ├── youtube_charts_2025-W02.db
│   │   └── ...
│   └── backup/
│       └── ...
└── 2_countries-genres-artist/          # ← Salida de este script
    └── artist_countries_genres.db       # Base de datos de artistas enriquecida
```

### **Database Growth**
- Ejecución inicial: 100-200 artistas
- Crecimiento semanal: 10-50 nuevos artistas (solo los nuevos de charts semanales)
- Tamaño estimado: ~10KB por 100 artistas

---

## 🔧 Personalización y Configuración

### **Parámetros Ajustables en el Script**

```python
# En 2_build_artist_db.py
MIN_CANDIDATES = 3        # Mínimo de candidatos de género antes de búsqueda en Wikipedia
RETRY_DELAY = 0.5          # Retraso entre llamadas API (segundos)
DEFAULT_TIMEOUT = 10       # Tiempo de espera de API (segundos)
DEEPSEEK_RATE_LIMIT = 0.5  # Retraso entre llamadas a DeepSeek (segundos)
```

### **Configuración del Workflow**

```yaml
# En 2-update-artist-database.yml
env:
  RETENTION_DAYS: 30       # Días para artefactos

timeout-minutes: 60        # Tiempo máximo del job (permite límites de tasa de API)
```

### **Agregar Nuevos Países**

```python
# Extender COUNTRIES_CANONICAL
'New Country': {
    'nombre del país', 'gentilicios', 'capital', 'ciudades principales'
}
```

### **Agregar Nuevos Mapeos de Géneros**

```python
# Extender GENRE_MAPPINGS
'nuevo subgénero': ('Macro-Género', 'subgénero')
```

### **Ajustar Prioridades por País**

```python
# Modificar COUNTRY_GENRE_PRIORITY
"Nombre del País": [
    "Género Prioritario 1",   # Obtiene 2.0x bonificación
    "Género Prioritario 2",   # Obtiene 1.5x bonificación
    "Género Prioritario 3"    # Obtiene 1.2x bonificación
]
```
---

## 🐛 Solución de Problemas

### Problemas Comunes y Soluciones

1. **Error: "No chart databases found"**
   - Run the download workflow (script 1) first
   - Check if `charts_archive/1_download-chart/databases/` exists
   - Verify file permissions
2. **Error: Tiempo de espera de API en GitHub Actions**

```bash
# Aumentar tiempos de espera en el script
DEFAULT_TIMEOUT = 20
RETRY_DELAY = 1.0
```

3. **Error: Límite de tasa de API**
- El script incluye retrasos entre llamadas
- Para lotes grandes, considerar agregar retrasos más largos
- Monitorear encabezados de respuesta de API para información de límites de tasa

4. **Error: Clave API de DeepSeek no configurada**
- Agregar `DEEPSEEK_API_KEY` a los Secretos de GitHub
- Para pruebas locales, configurar variable de entorno
- El script continúa sin DeepSeek si falta la clave

5. **Error: Artista no encontrado en ninguna fuente**
- Verificar si el nombre del artista tiene caracteres especiales
- Intentar búsqueda manual en MusicBrainz
- Agregar reglas de respaldo para el país
- DeepSeek puede ayudar con artistas oscuros

### **Registros y Depuración**

**Niveles de registro disponibles:**
1. **Información básica**: Muestra progreso y resultados
2. **Modo DEBUG**: Muestra candidatos de género y detalles de votación
3. **Modo GitHub Actions**: Registro mejorado para CI/CD
4. **Registro verbose de API**: Descomentar declaraciones `print` en funciones API
5. **Registro de respaldo DeepSeek**: Muestra cuando se usa el respaldo de IA

---

## 📈 Monitoreo y Mantenimiento

### **Indicadores de Salud**

1. **Tamaño de la base de datos**: Crece ~10-50 registros/semana
2. **Tasa de éxito**: Debería ser >90% para artistas establecidos
3. **Tiempo de respuesta de API**: <2 segundos promedio
4. **Tasa de aciertos de caché**: Aumenta con el tiempo a medida que se acumulan artistas
5. **Uso de DeepSeek**: Debería ser bajo (<10% de artistas)

### **Métricas de Rendimiento**

| Métrica                     | Rango Esperado | Notas                                           |
| :-------------------------- | :------------- | :---------------------------------------------- |
| Artistas procesados/hora    | 500-1000       | Depende de los tiempos de respuesta de API      |
| Tasa de aciertos de caché   | 30-70%         | Aumenta con el tamaño de la base de datos       |
| Tasa de detección de género | 85-95%         | Menor para artistas muy nicho                   |
| Tasa de detección de país   | 80-90%         | Menor para artistas con poca presencia en línea |
| Tasa de respaldo DeepSeek   | <10%           | Solo se usa cuando fallan las fuentes gratuitas |
| Costo por 100 artistas      | ~$0.002        | Con respaldo DeepSeek                           |

------

## 📄 Licencia y Atribución

- **Licencia**: MIT
- **Autor**: Alfonso Droguett
  - 🔗 **LinkedIn:** [Alfonso Droguett](https://www.linkedin.com/in/adroguetth/)
  - 🌐 **Portafolio web:** [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/)
  - 📧 **Email:** adroguett.consultor@gmail.com
- **Fuentes de Datos**:
  - MusicBrainz (Licencia GPL)
  - Wikipedia (CC BY-SA)
  - Wikidata (CC0)
  - DeepSeek (API comercial, solo como respaldo)

------

## 🤝 Contribución

1. Reportar problemas con registros completos
2. Proponer mejoras con casos de uso
3. Agregar nuevos mapeos de géneros con ejemplos
4. Contribuir con variantes de países (especialmente para regiones subrepresentadas)
5. Mantener compatibilidad con la estructura de base de datos existente

------

## 🧪 Limitaciones Conocidas y Mejoras Futuras

### **Limitaciones Actuales**

- **Dependencia de API**: El sistema depende de servicios externos que pueden cambiar o limitar la tasa
- **Artistas Nuevos**: Los artistas emergentes pueden no aparecer en las bases de conocimiento
- **Géneros de Nicho**: Algunos micro-géneros pueden no tener mapeos aún
- **MCs Brasileños**: Actualmente reciben `Sertanejo` como respaldo (orden de lista de prioridad)
- **Detección de Escritura**: Basada en heurísticas, puede identificar incorrectamente ocasionalmente
- **Costo de DeepSeek**: Aunque mínimo, requiere clave API y tiene costos de tokens
------

**⭐ If you find this project useful, please consider starring it on GitHub!**
