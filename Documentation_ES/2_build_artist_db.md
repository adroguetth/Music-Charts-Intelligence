# 🎵 Script 2: Artist Country + Genre Detection System, Intelligent Enrichment

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square) ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![Requests](https://img.shields.io/badge/Requests-FF6F61?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia API](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white) ![Wikidata](https://img.shields.io/badge/Wikidata-990000?style=flat-square&logo=wikidata&logoColor=white) ![DeepSeek](https://custom-icon-badges.demolab.com/badge/DeepSeek-4D6BFF?logo=deepseek&logoColor=white&style=flat-square)

## 📥 Quick Downloads
| Document                | Format                                                     |                                                    
| ------------------------- | ------------------------------------------------------------ |
| **🇬🇧 English Documentation** | [PDF](https://drive.google.com/file/d/1viUAxZ7k-qeYYbyvZf2OaP20AfLOgKh2/view?usp=drive_link) |
| **🇪🇸 Spanish Documentation**  | [PDF](https://drive.google.com/file/d/1WBHBreKeVToTBygSyCuYsHQUr_zSl3BT/view?usp=drive_link) |

## 📋 General Description

This project is the second component of the YouTube Charts intelligence system. It takes the raw artist names extracted by the downloader and **enriches them with geographic and genre metadata** by querying multiple open knowledge bases. The result is a structured database of artists with their country of origin and primary music genre.


### Key Features

- **Multi-Source Lookup**: Intelligent cascading queries to MusicBrainz, Wikipedia (summary & infobox), and Wikidata
- **DeepSeek AI Fallback**: Uses DeepSeek API as last resort when all free sources fail (cost-effective, ~$0.002 per 100 artists)
- **Smart Name Variation**: Generates up to 15 variations per artist (accents removed, prefixes stripped, etc.) for maximum match rate
- **Geographic Intelligence**: Country detection from cities, demonyms, and regional references using a curated dictionary of 30,000+ terms
- **Genre Classification**: 200+ macro-genres and 5,000+ subgenre mappings with weighted voting system
- **Country-Specific Rules**: Special handling for 50+ countries (e.g., K-Pop for South Korea, Sertanejo for Brazil)
- **Script Detection**: Automatic language detection for non-Latin scripts (Cyrillic, Devanagari, Arabic, Hangul, etc.)
- **Intelligent Updates**: Only fills missing data, never overwrites existing correct information
- **In-Memory Caching**: Avoids redundant API calls during execution
- **CI/CD Optimized**: Specifically configured for GitHub Actions with progressive fallbacks
- **Rate Limiting**: Built-in delays to respect API quotas and avoid throttling

## 📊 Process Flow Diagram

### **Legend**
| Color        | Type     | Description                   |
| :----------- | :------- | :---------------------------- |
| 🔵 Blue       | Input    | Source data (charts database) |
| 🟠 Orange     | Process  | Internal processing logic     |
| 🟣 Purple     | API      | External service queries      |
| 🟢 Green      | Cache    | In-memory temporary storage   |
| 🔴 Red        | Decision | Conditional branching points  |
| 🟢 Dark Green | Output   | Results and final database    |

### **Diagram 1: Main Flow Overview**

<img src="https://drive.google.com/uc?export=view&id=18uJf6B1ihQs5b3Hv1MZuqnwQs9DNjMjA" alt="Country Search" width="350">

This diagram shows the **high-level pipeline** of the entire system:

1. **Input**: Reads the weekly YouTube Charts database (`youtube_charts_YYYY-WXX.db`)
2. **Extraction**: Reads artist names and splits them (handles "feat.", "&", commas, etc.)
3. **Deduplication**: Creates a list of unique artists to avoid redundant processing
4. **Per-Artist Loop**: For each artist, checks if they already exist in the enriched database
   - **If complete** (country + genre known): Skips to next artist ✅
   - **If missing info**: Searches only the missing fields (country or genre)
   - **If new**: Performs full country and genre search
5. **Country Search** → **Genre Search** → **Voting System** → **Database Update**
6. **After all artists**: Generates a final report and automatically commits changes to GitHub

### **Diagram 2: Country Search (Detailed)**

<img src="https://drive.google.com/uc?export=view&id=1mQx2lJ4bltmssN9VBTnkiFxwQXSJiz7y" alt="Country Search" width="250">

This diagram details the **cascading search strategy** for detecting an artist's country:

1. **Start**: Receives an artist name (may be missing info or new artist)
2. **Name Variations**: Generates up to 15 variations (no accents, no prefixes, etc.)
3. **Cache Check**: First checks in-memory cache to avoid repeat API calls
4. **MusicBrainz**: Queries MusicBrainz API (structured data, high reliability)
   - If found → returns country ✅
5. **Wikipedia English**: If not found, queries Wikipedia English:
   - First checks summary (first paragraph) for patterns like "born in...", "from..."
   - Then checks infobox for fields like "origin", "birth_place", "location"
   - If found → returns country ✅
6. **Wikipedia Priority Languages**: If still not found, tries Wikipedia in languages based on:
   - The artist's country (if already known from previous step)
   - Detected script from the artist's name (Cyrillic → Russian Wikipedia, etc.)
   - If found → returns country ✅
7. **Wikidata**: Final free source, queries Wikidata using properties P27 (country of citizenship) and P19 (place of birth)
8. **DeepSeek AI Fallback**: Only if all free sources fail, queries DeepSeek API (cost-effective)
   - Uses structured prompt asking for country and genre
   - Results are normalized using the same validation functions
   - Rate-limited to 0.5s delay between calls
9. **Result**: Returns either a canonical country name or "Unknown"

### **Diagram 3: Genre Search (Detailed)**

<img src="https://drive.google.com/uc?export=view&id=173wJP4u30DDEN27HaFb52A3nhS1VCg0_" alt="Country Search" width="350">

This diagram shows how the system **collects genre candidates** from multiple sources:

1. **Start**: Receives artist name (and country if already detected)
2. **Name Variations**: Same variation system for maximum match rate
3. **MusicBrainz**: First source, extracts genre tags and their counts
   - Adds candidates with base weight (1.5x for MusicBrainz)
4. **Wikidata**: Second source, queries property P136 (genre)
   - Adds candidates with base weight (1.3x for Wikidata)
5. **Candidate Check**: Checks if we already have at least 3 genre candidates
   - **If yes**: Proceeds directly to voting system
   - **If no**: Continues to Wikipedia search
6. **Wikipedia Priority Languages**: Queries Wikipedia in languages prioritized by:
   - Country (e.g., Korean artists → Korean Wikipedia)
   - Detected script (e.g., Arabic name → Arabic Wikipedia)
7. **Extraction**: Uses pattern matching to extract genres from:
   - **Infobox**: Looks for "genre", "genres", "género" fields
   - **Summary**: Uses NLP patterns like "is a [genre] singer", "known for [genre] music"
8. **Second Check**: If still under 3 candidates, tries Wikipedia in other common languages
9. **DeepSeek AI Fallback**: Only if all free sources return no candidates, queries DeepSeek API
   - Uses the country (if known) as context to improve accuracy
   - Returns a normalized genre or raw string
10. **Final**: All candidates (with their weights and sources) go to the Voting System

### **Diagram 4: Voting & Weight System**

<img src="https://drive.google.com/uc?export=view&id=1ml8-R9svwpnT4bgXhJ3L-FNkqa17N8CN" alt="Country Search" width="250">

This is the **intelligent decision engine** that selects the final genre:

1. **Input**: Receives all genre candidates with their raw weights and sources
2. **Normalization**: Maps each specific subgenre to a macro-genre using the `GENRE_MAPPINGS` dictionary
   - Example: "synth pop", "synth-pop", "synthpop" all → "Pop"
3. **Source Weights**: Applies multipliers based on source reliability:
   - MusicBrainz: ×1.5 (structured, reliable)
   - Wikidata: ×1.3 (semantic, medium reliability)
   - Wikipedia Infobox: ×1.2 (semi-structured)
   - Wikipedia Summary: ×1.0 (free text, lower confidence)
   - Wikipedia Keywords: ×0.5 (lowest confidence)
4. **Script Detection**: Analyzes the artist's name to detect writing system (Cyrillic, Hangul, Arabic, etc.)
5. **Term Bonuses**: Multiplies weight by 1.4x if specific keywords are found:
   - "reggaeton", "trap latino" → boosts Latin genres
   - "k-pop", "korean pop" → boosts K-Pop
   - "sertanejo", "funk brasileiro" → boosts Brazilian genres
6. **Country Priority** (if country known): Applies additional multipliers based on country's genre priority list:
   - 1st priority genre: ×2.0
   - 2nd priority genre: ×1.5
   - 3rd+ priority genres: ×1.2
7. **Country-Specific Rules**: Applies special rules for certain countries:
   - **force_macro**: Forces a specific macro-genre (e.g., Puerto Rico → Reggaetón/Trap Latino)
   - **map_generic_to**: Maps generic genres (Pop, Rock) to regional ones (e.g., Korea → K-Pop/K-Rock)
8. **Script Bonus**: If detected script matches the country's dominant language, applies ×1.2 bonus
9. **Vote Summation**: Adds all weighted votes for each macro-genre
10. **Winner Selection**: Chooses macro-genre with highest total votes
11. **Fallback**: If no winner and country is known, uses the first genre from country's priority list

### **Diagram 5: Database Update**
<img src="https://drive.google.com/uc?export=view&id=1zU7GwiHW3DYDlY7kGLnwC6HqY99SRF5m" alt="Country Search" width="350">

This diagram shows how the system **persists data intelligently**:

1. **Input**: Receives final country and genre data for an artist
2. **Connect**: Opens connection to `artist_countries_genres.db`
3. **Existence Check**: Queries if artist already exists in database
4. **If Artist Exists**:
   - **Check Missing Fields**: Compares existing data with new data
   - **Update Only Missing**: Updates country only if existing is NULL/Unknown and new is known
   - Updates genre only if existing is NULL/Unknown and new is known
   - **Never overwrites** existing correct data!
5. **If Artist is New**:
   - Inserts complete new record with country and genre
6. **Log Statistics**: Records success/failure for reporting
7. **Loop Check**: If more artists remain, returns to main loop
8. **All Artists Processed**:
   - Generates final report with statistics (success rate, new artists, etc.)
9. **GitHub Commit**: Automatically commits and pushes changes to repository

---
## 🔍 Detailed Analysis of `2_build_artist_db.py`

### Code Structure

#### **1. Configuration and Paths**
```python
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CHARTS_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"
ARTIST_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_countries-genres-artist" / "artist_countries_genres.db"
```

The script reads from the downloader's output and creates its own enriched database:

- **Input**: Weekly chart databases from step 1 (`youtube_charts_YYYY-WXX.db`)
- **Output**: Artist metadata database (`artist_countries_genres.db`)
- **Structure**: `charts_archive/2_countries-genres-artist/`

#### **2. Intelligent Name Variation System**

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

**Example for "Lil Wayne":**

```python
Lil Wayne
Wayne
Lil Wayne
Lil Wayne
Wayne
... (hasta 15 variaciones)
```

**Prefix dictionary includes:**

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

#### **3. Geographic Intelligence System**

The heart of country detection is the `COUNTRIES_CANONICAL` dictionary, a curated knowledge base with **30,000+ terms** mapping to 200+ countries.

**Structure example for United States:**

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

**Detection process:**

1. **Direct match**: "canadian" → Canada
2. **City mention**: "from Toronto" → Canada
3. **Regional reference**: "born in Brooklyn" → United States
4. **Demonym**: "argentine singer" → Argentina

#### **4. Genre Classification Ontology**

The `GENRE_MAPPINGS` dictionary contains **5,000+ genre variants** mapped to 200+ macro-genres.

**Example mapping for Electronic music:**

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

**Macro-genre categories (200+):**

- **Global**: `Pop`, `Rock`, `Hip-Hop/Rap`, `R&B/Soul`, `Electrónica/Dance`
- **Regional America**: `Reggaetón/Trap Latino`, `Bachata`, `Cumbia`, `Sertanejo`, `Funk Brasileiro`, `Regional Mexicano`, `Vallenato`
- **Regional Asia**: `K-Pop/K-Rock`, `J-Pop/J-Rock`, `C-Pop/C-Rock`, `T-Pop/T-Rock`, `V-Pop/V-Rock`, `OPM`, `Indonesian Pop/Dangdut`, `Pakistani Pop`
- **Regional Africa**: `Afrobeats`, `Amapiano`, `Bongo Flava`, `Zim Dancehall`, `Kuduro`, `Kizomba/Zouk`
- **Regional Europe**: `Turbo-folk`, `Manele`, `Schlager`, `Chanson`, `Flamenco / Copla`, `Canzone Italiana`
- **Indigenous**: `Māori Pop/Rock`, `Aboriginal Australian Pop/Rock`, `Siberian Indigenous Pop/Rock`, `Hawaiian Pop/Rock`

#### **5. Multi-Source API Queries**

The script queries four knowledge bases in cascade (with DeepSeek as final fallback):

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

**MusicBrainz query:**

```python
url = "https://musicbrainz.org/ws/2/artist/"
params = {'query': artist, 'fmt': 'json', 'limit': 1}
# Retorna etiquetas de género estructuradas con puntuaciones de confianza
```

**Wikipedia infobox extraction:**

```text
# Extrae de Infobox musical artist
# Campos buscados: genre, géneros, genres
# Ejemplo: | genre = [[Pop music|Pop]], [[R&B]]
```

**Wikipedia summary extraction with NLP patterns:**

```python
patterns = [
    r'is\s+(?:a|an)\s+([a-z\s\-]+?)\s+(?:singer|rapper|musician)',
    r'are\s+(?:a|an)\s+([a-z\s\-]+?)\s+(?:band|group)',
    r'known\s+for\s+their\s+([a-z\s\-]+?)\s+music',
    r'genre\s+is\s+([a-z\s\-]+?)(?:\.|,|$)'
]
```

**DeepSeek API fallback:**

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

#### **6. Intelligent Caching System**

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

**Benefits:**

- **Performance**: Avoids redundant API calls for the same artist
- **Politeness**: Reduces load on external services
- **Speed**: In-memory cache for current execution
- **Session reuse**: Keep-alive connections for multiple queries
- **Cost savings**: DeepSeek cache prevents duplicate paid calls

#### **7. Script/Language Detection**

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

**Used for:**

- Prioritizing Wikipedia queries in the right language
- Applying regional bonuses (e.g., Korean script → K-Pop)
- Improving name variation generation
- Providing context to DeepSeek fallback

#### **8. Weighted Voting System**

The `select_primary_genre` function implements a sophisticated voting algorithm:

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

### **`artist` Table Structure**

| Column      | Type   | Description               | Example        |
| :---------- | :----- | :------------------------ | :------------- |
| name        | `TEXT` | Artist name (primary key) | "BTS"          |
| country     | `TEXT` | Canonical country name    | "South Korea"  |
| macro_genre | `TEXT` | Primary macro-genre       | "K-Pop/K-Rock" |

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
