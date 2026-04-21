# Script 3: Sistema de Enriquecimiento de Charts de YouTube

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Web Scraping](https://img.shields.io/badge/Web-Scraping-orange?style=flat-square) ![ETL](https://img.shields.io/badge/ETL-9ecae1?style=flat-square) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white) ![yt-dlp](https://img.shields.io/badge/yt--dlp-FF6F61?style=flat-square&logo=youtube&logoColor=white) ![YouTube API](https://img.shields.io/badge/YouTube_API-FF0000?style=flat-square&logo=youtube&logoColor=white)


## 📥 Descargas Rápidas

| Documento                       | Formato                                                      |
| :------------------------------ | :----------------------------------------------------------- |
| **🇬🇧 Documentación en Inglés**  | [PDF](https://drive.google.com/file/d/1XGEx2fRBCpOhU5BfY_YjlKm6zmI41RpB/view?usp=drive_link) |
| **🇪🇸 Documentación en Español** | [PDF](https://drive.google.com/file/d/1tSFjf_gQQeArdE4n5DLL2I2G_MJW6vE3/view?usp=drive_link) |

> **📚 Documentación Anterior:** Para la versión anterior de este script (con el sistema de ponderación de colaboraciones incluido), consulte la [Documentación Legacy del Script 3](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/Documentation_backup/3_enrich-chart-data.md)

## 📋 Descripción General

Este script es el **tercer componente** del sistema de inteligencia de Charts de YouTube. Toma la base de datos semanal de charts (del Script 1) y la **base de datos del catálogo de canciones (del Script 2_2)**, luego **enriquece cada canción con metadatos detallados del video de YouTube** utilizando un sistema inteligente de fallback de tres capas.

El script extrae duración del video, likes, comentarios, fecha de publicación, idioma de audio, restricciones regionales, y clasifica el tipo de video (oficial/lyric/en vivo), el tipo de canal (VEVO/Topic/Artista) y patrones de colaboración. **La información de país y género ya no se resuelve en este script** – se lee directamente del catálogo de canciones (`build_song.db`) donde fueron pre-resueltos por el algoritmo de ponderación de colaboraciones del Script 2_2.

### Características Principales

- **Sistema de Recuperación de 3 Capas**: YouTube API (prioridad) → Selenium → yt-dlp (último recurso) para máxima confiabilidad
- **Rendimiento Optimizado**: Procesa 100 canciones en ~2 minutos usando YouTube API (vs. 8+ minutos con solo yt-dlp)
- **Integración con Catálogo de Canciones**: Lee `artist_country`, `macro_genre`, `artists_found` e `id` desde `build_song.db` (salida del Script 2_2)
- **Relación de Clave Foránea**: La columna `id` ahora referencia `artist_track.id` del catálogo
- **Detección de Metadatos de Video**: Identifica si un video es oficial, lyric, en vivo, o versión remix/especial
- **Clasificación de Canales**: Detecta VEVO, Topic, Label/Studio, Canal de Artista, y más
- **Actualizaciones Automáticas**: Selecciona la base de datos de charts más reciente y genera su versión enriquecida
- **Optimizado para CI/CD**: Diseñado específicamente para ejecutarse en GitHub Actions sin intervención manual

### Cambios de Versión

| Característica                          | [Anterior (Legacy)](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/Documentation_backup/3_enrich-chart-data.md) | Versión Actual                         |
| :-------------------------------------- | :----------------------------------------------------------- | :------------------------------------- |
| **Resolución de País/Género**           | Script 3 (semanal, por canción)                              | Script 2_2 (una vez por canción única) |
| **Fuente de Base de Datos de Artistas** | Descarga desde URL de GitHub                                 | Lee `build_song.db` local              |
| **Ponderación de Colaboraciones**       | Incluido en Script 3                                         | Movido al Script 2_2                   |
| **COUNTRY_TO_CONTINENT**                | Definido en Script 3                                         | Movido al Script 2_2                   |
| **GENRE_HIERARCHY**                     | Definido en Script 3                                         | Movido al Script 2_2                   |
| **resolve_country_and_genre()**         | En Script 3                                                  | Movido al Script 2_2                   |
| **Columna `id` de Salida**              | AUTOINCREMENT                                                | Clave foránea a `artist_track.id`      |

------

## 📊 Diagrama de Flujo de Procesos

### **Leyenda**

| Color          | Tipo           | Descripción                                                  |
| :------------- | :------------- | :----------------------------------------------------------- |
| 🔵 Azul         | Entrada        | Datos fuente (base de datos de charts + catálogo de canciones) |
| 🟠 Naranja      | Proceso        | Lógica de procesamiento interno                              |
| 🟣 Púrpura      | API            | Consultas a servicios externos (YouTube API, Selenium, yt-dlp) |
| 🟢 Verde        | Almacenamiento | Bases de datos SQLite, archivos temporales                   |
| 🔴 Rojo         | Decisión       | Puntos de bifurcación condicional                            |
| 🟢 Verde Oscuro | Salida         | Base de datos enriquecida                                    |

### **Diagrama 1: Vista General del Flujo Principal**

<img src="https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/Diagramas/3_enrich_chart_data/1.png?raw=true" alt="Diagrama 1: Vista General del Flujo Principal" width="500">

Este diagrama muestra el **pipeline de alto nivel** de todo el sistema:

1. **Entrada**: Localiza la base de datos de charts más reciente (`youtube_charts_YYYY-WXX.db`) del Script 1
2. **Cargar Catálogo de Canciones**: Lee `build_song.db` del Script 2_2 (ya no descarga la base de datos de artistas de GitHub)
3. **Construir Búsqueda**: Crea un diccionario en memoria `{(artist_names, track_name): (id, country, genre, artists_found)}` para búsquedas O(1)
4. **Cargar Canciones**: Lee 100 canciones de la tabla `chart_data`
5. **Crear Tabla de Salida**: Configura la tabla `enriched_songs` con 25 columnas + índices (incluyendo clave foránea al catálogo)
6. **Bucle por Canción**: Para cada canción (1 a 100):
   - **Buscar Datos en Catálogo**: Consulta el diccionario para obtener `id`, `artist_country`, `macro_genre`, `artists_found`
   - **Obtener Metadatos de YouTube**: Fallback de 3 capas (API → Selenium → yt-dlp)
   - **Clasificar Video**: Detecta tipo, canal, colaboración, temporada de publicación
   - **Insertar Fila**: Guarda los datos enriquecidos con el ID del catálogo como clave foránea
7. **Salida**: Base de datos enriquecida lista para el Script 4 (generación de notebooks)

### **Diagrama 2: Sistema de Recuperación de Metadatos de 3 Capas**

<img src="https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/Diagramas/3_enrich_chart_data/2.png?raw=true" alt="Diagrama 2: Sistema de Recuperación de Metadatos de 3 Capas" width="600">


Este diagrama detalla la **estrategia de recuperación en cascada** para metadatos de videos de YouTube:

1. **Inicio**: Recibe URL del video de YouTube y cadena CSV de artistas
2. **Capa 1 – YouTube Data API v3** (0.3–0.8s/video):
   - Extrae video_id de la URL (patrón de 11 caracteres)
   - Consulta la API por `snippet`, `contentDetails`, `statistics`
   - Recupera: duración, likes, comentarios, idioma de audio, fecha de publicación, restricciones de región
   - **Si tiene éxito** → Retorna metadatos completos ✅
   - **Si falla** (sin clave, cuota excedida, error) → Procede a la Capa 2
3. **Capa 2 – Selenium Headless Browser** (3–5s/video):
   - Lanza navegador Chrome sin interfaz gráfica
   - Navega a la página del video, espera el elemento del título
   - Extrae: título, duración (del reproductor), nombre del canal, fecha de publicación (de meta etiqueta)
   - **Nota**: Selenium NO retorna likes, comentarios o idioma de audio
   - **Si tiene éxito** → Retorna metadatos parciales ✅
   - **Si falla** → Procede a la Capa 3
4. **Capa 3 – yt-dlp con Rotación de Clientes** (2–4s/video):
   - Prueba múltiples configuraciones de cliente de reproducción secuencialmente:
     - `android` (más confiable)
     - `ios` (buen fallback)
     - `android + web` (combinación)
     - `web` (navegador estándar)
   - Cada intento incluye reintentos y demoras para evitar detección de bot
   - **Si alguno tiene éxito** → Retorna metadatos completos ✅
   - **Si todos fallan** → Retorna metadatos vacíos con mensaje de error
5. **Salida**: Retorna un diccionario de metadatos con 15+ campos (algunos pueden estar vacíos en caso de fallo)

### **Diagrama 3: Integración con Catálogo de Canciones**

<img src="https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/Diagramas/3_enrich_chart_data/3.png?raw=true" alt="Diagrama 3: Integración con Catálogo de Canciones" width="650">

Este diagrama muestra el **flujo de búsqueda en el catálogo** que reemplaza al antiguo sistema de ponderación de colaboraciones:

1. **Entrada**: Recibe `artist_names` y `track_name` de la fila del chart
2. **Búsqueda en Catálogo**: Consulta el diccionario `song_catalog_lookup` con la clave `(artist_names, track_name)`
3. **Si se Encuentra**:
   - Recupera `song_id`, `artist_country`, `macro_genre`, `artists_found`
   - Usa estos valores directamente en la salida enriquecida
   - **No se realiza resolución de país/género** (ya fue hecho por Script 2_2)
4. **Si no se Encuentra**:
   - Establece `song_id = NULL`
   - Establece `artist_country = "Unknown"`
   - Establece `macro_genre = "Pop"`
   - Establece `artists_found = "0/0"`
5. **Salida**: Fila enriquecida con la relación de clave foránea adecuada

> **Nota**: El sistema de ponderación de colaboraciones (`COUNTRY_TO_CONTINENT`, `GENRE_HIERARCHY`, `resolve_country_and_genre()`) ha sido **movido al Script 2_2**. El Script 3 ahora consume los valores pre-resueltos.

------

## 🔍 Análisis Detallado de `3_enrich_chart_data.py`

### Estructura del Código

#### **1. Configuración y Rutas**

```python
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

# Entrada: Bases de datos semanales de charts del Script 1
INPUT_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"

# Entrada: Base de datos del catálogo de canciones del Script 2_2 (REEMPLAZA la descarga de DB de artistas)
SONG_CATALOG_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_2.build-song-catalog" / "build_song.db"

# Salida: Bases de datos enriquecidas para el Script 4
OUTPUT_DIR = PROJECT_ROOT / "charts_archive" / "3_enrich-chart-data"
```

El script integra los dos componentes:

| Ruta                   | Propósito                                                    |
| :--------------------- | :----------------------------------------------------------- |
| `INPUT_DB_DIR`         | Entrada: Bases de datos semanales de charts del Script 1     |
| `SONG_CATALOG_DB_PATH` | Entrada: Catálogo de canciones con país/género pre-resuelto del Script 2_2 |
| `OUTPUT_DIR`           | Salida: Bases de datos enriquecidas para el Script 4         |

**Cambios respecto a la versión anterior:**

- **ELIMINADO**: `URL_ARTIST_DB` (ya no descarga la base de datos de artistas de GitHub)

- **AGREGADO**: `SONG_CATALOG_DB_PATH` (lee el catálogo local en su lugar)

  

#### **2. Tablas de Referencia Centrales (ELIMINADAS)**

Las siguientes tablas han sido **eliminadas** del Script 3 ya que fueron movidas al Script 2_2:

- ~~`COUNTRY_TO_CONTINENT`~~ (mapeo de 196 países)
- ~~`GENRE_HIERARCHY`~~ (jerarquías de géneros por país)

Estas ahora se mantienen exclusivamente en `2_2.build_song_catalog.py`.



#### **3. Sistema de Recuperación de Metadatos de 3 Capas**

```python
def fetch_video_metadata(url: str, artists_csv: str = "", api_key: str = None) -> dict:
    """
    Orquesta la estrategia de recuperación de metadatos de tres capas.
    
    Capa 1 — YouTube Data API v3 (requiere YOUTUBE_API_KEY):
        Metadatos completos: duración, likes, comentarios, idioma, fecha, restricciones.
        Sale inmediatamente si tiene éxito.
    
    Capa 2 — Navegador headless Selenium:
        Metadatos parciales: duración, tipo de canal, fecha, banderas de tipo de video.
        Se usa cuando la API está ausente o devuelve error.
    
    Capa 3 — yt-dlp con rotación anti-bloqueo de clientes:
        Prueba clientes android → ios → android+web → web en orden.
        Último recurso; puede ser más lento y aún fallar contra detección agresiva de bots.
    """
```



**Capa 1 – YouTube Data API v3:**

```python
# Extraer ID de video de la URL
vid_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
video_id = vid_match.group(1)

youtube = build('youtube', 'v3', developerKey=api_key)
response = youtube.videos().list(
    part='snippet,contentDetails,statistics',
    id=video_id
).execute()

# Campos recuperados:
# - duration: isodate.parse_duration() → segundos
# - likeCount, commentCount
# - defaultAudioLanguage
# - regionRestriction (bloqueado/permitido)
# - publishedAt → fecha y trimestre
# - title, description, channelTitle
```



**Capa 2 – Selenium Headless Browser:**

```python
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get(url)
title = driver.find_element(By.CSS_SELECTOR, "h1.ytd-video-primary-info-renderer").text
duration = driver.find_element(By.CSS_SELECTOR, "span.ytp-time-duration").text
channel = driver.find_element(By.CSS_SELECTOR, "a.ytd-channel-name").text
date = driver.find_element(By.CSS_SELECTOR, "meta[itemprop='datePublished']").get_attribute("content")
```



**Capa 3 – yt-dlp con Rotación de Clientes:**

```python
client_options = [
    {'player_client': ['android']},        # Más confiable
    {'player_client': ['ios']},            # Buen fallback
    {'player_client': ['android', 'web']}, # Combinación
    {'player_client': ['web']},            # Navegador estándar
]

for opts in client_options:
    ydl_config = {
        'quiet': True,
        'skip_download': True,
        'extractor_retries': 5,
        'sleep_interval': 2,
        **opts
    }
    with yt_dlp.YoutubeDL(ydl_config) as ydl:
        info = ydl.extract_info(url, download=False)
        if info:
            break  # Éxito
```



#### **4. Sistema de Ponderación de Colaboraciones (ELIMINADO)**

Las siguientes funciones han sido **eliminadas** del Script 3:

- ~~`resolve_country_and_genre(artists_info: list) -> tuple`~~
- ~~`infer_genre_by_country(artists_info: List[Dict]) -> str`~~
- ~~`get_continent(country: str) -> str`~~

Estas funciones fueron movidas al Script 2_2 donde se ejecutan **una vez por canción única** en el momento de inserción en el catálogo, en lugar de semanalmente por aparición en el chart.

**Antes (Legacy):**

- Cada semana: 100 canciones × resolución de país/género
- Total: ~5,200 resoluciones por año

**Después (Actual):**

- Cada canción única: 1 resolución en la inserción del catálogo

- Total: ~500-1,000 resoluciones por año (dependiendo de la tasa de canciones nuevas)

  

#### **5. Clasificadores de Texto**

**Detección de Tipo de Video:**

```python
def detect_video_type(title: str, description: str = "") -> dict:
    full_text = f"{title.lower()} {description.lower()}"
    
    is_official = any(kw in full_text for kw in ['official', 'official music video'])
    is_lyric = any(kw in title.lower() for kw in ['lyric', 'lyrics', 'letra'])
    is_live = any(kw in full_text for kw in ['live', 'concert', 'performance'])
    is_special = any(kw in title.lower() for kw in ['remix', 'sped up', 'slowed', 'acoustic'])
    
    return {
        'is_official_video': is_official,
        'is_lyric_video': is_lyric,
        'is_live_performance': is_live,
        'is_special_version': is_special
    }
```



**Detección de Colaboración:**

```python
def detect_collaboration(title: str, artists_csv: str) -> dict:
    collab_patterns = [r'\sft\.\s', r'\sfeat\.\s', r'\s&\s', r'\sx\s', r'\swith\s']
    is_collab = any(re.search(p, title.lower()) for p in collab_patterns)
    
    if artists_csv:
        artist_count = artists_csv.count('&') + artists_csv.count(',') + 1
    else:
        artist_count = 2 if is_collab else 1
    
    return {'is_collaboration': is_collab, 'artist_count': min(artist_count, 10)}
```



**Clasificación de Tipo de Canal:**

```python
def detect_channel_type(channel_title: str) -> dict:
    ch = channel_title.lower()
    
    if 'vevo' in ch:
        return {'channel_type': 'VEVO'}
    elif 'topic' in ch:
        return {'channel_type': 'Topic'}
    elif any(w in ch for w in ['records', 'music', 'label', 'studios']):
        return {'channel_type': 'Label/Studio'}
    elif any(w in ch for w in ['official', 'artist', 'band', 'singer']):
        return {'channel_type': 'Artist Channel'}
    else:
        return {'channel_type': 'General'}
```



#### **6. Búsqueda en Catálogo de Canciones**

```python
def load_song_catalog_lookup() -> dict:
    """
    Carga el catálogo de canciones (tabla artist_track) en un diccionario en memoria.
    
    La clave es una tupla de (artist_names, track_name) exactamente como está almacenada.
    El valor es una tupla de (id, artist_country, macro_genre, artists_found).
    
    Returns:
        dict: {(artist_names, track_name): (id, country, genre, artists_found)}
    """
    catalog_lookup = {}
    if not SONG_CATALOG_DB_PATH.exists():
        print(f"⚠️  Catálogo de canciones no encontrado en {SONG_CATALOG_DB_PATH}.")
        print("   Por favor, ejecute 2_2.build_song_catalog.py primero para crear el catálogo.")
        return catalog_lookup
    
    conn = sqlite3.connect(SONG_CATALOG_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT artist_names, track_name, id, artist_country, macro_genre, artists_found
        FROM artist_track
    """)
    rows = cursor.fetchall()
    conn.close()
    
    for artist_names, track_name, song_id, country, genre, found in rows:
        catalog_lookup[(artist_names, track_name)] = (song_id, country, genre, found)
    
    return catalog_lookup
```



#### **7. Procesamiento de Nombres de Artistas**

```python
def parse_artist_list(artist_names: str) -> list:
    """Divide nombres de artistas en bruto usando múltiples delimitadores."""
    text = artist_names
    for sep in ['&', 'feat.', 'ft.', ',', ' y ', ' and ', ' with ', ' x ', ' vs ']:
        text = text.replace(sep, '|')
    return [part.strip() for part in text.split('|') if part.strip()]

def normalize_name(name: str) -> str:
    """Normaliza el nombre del artista para búsqueda en diccionario."""
    name = re.sub(r'\s+', ' ', str(name)).strip().lower()
    name = re.sub(r'[^\w\s]', '', name)  # Eliminar puntuación
    return name
```



> **Nota**: `parse_artist_list()` y `normalize_name()` todavía se usan para la detección de colaboraciones en títulos de video, pero **NO** para la resolución de país/género.



#### **8. Esquema de Base de Datos de Salida (ACTUALIZADO)**

```sqlite
CREATE TABLE enriched_songs (
    id INTEGER UNIQUE,                     -- Clave foránea a artist_track.id (era AUTOINCREMENT)
    rank INTEGER,
    artist_names TEXT,
    track_name TEXT,
    periods_on_chart INTEGER,
    views INTEGER,
    youtube_url TEXT,
    duration_s INTEGER,
    duration_ms TEXT,
    upload_date TEXT,
    likes INTEGER,
    comment_count INTEGER,
    audio_language TEXT,
    is_official_video BOOLEAN,
    is_lyric_video BOOLEAN,
    is_live_performance BOOLEAN,
    upload_season TEXT,
    channel_type TEXT,
    is_collaboration BOOLEAN,
    artist_count INTEGER,
    region_restricted BOOLEAN,
    artist_country TEXT,                   -- Del catálogo (antes se resolvía aquí)
    macro_genre TEXT,                      -- Del catálogo (antes se resolvía aquí)
    artists_found TEXT,                    -- Del catálogo (antes se generaba aquí)
    error TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimización de consultas
CREATE INDEX idx_country ON enriched_songs(artist_country);
CREATE INDEX idx_genre ON enriched_songs(macro_genre);
CREATE INDEX idx_upload_date ON enriched_songs(upload_date);
CREATE INDEX idx_error ON enriched_songs(error);
```



**Cambios en el Esquema:**

| Columna          | [Anterior (Legacy)](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/Documentation_backup/3_enrich-chart-data.md) | Actual                                         |
| :--------------- | :----------------------------------------------------------- | :--------------------------------------------- |
| `id`             | `INTEGER PRIMARY KEY AUTOINCREMENT`                          | `INTEGER UNIQUE` (referencia de clave foránea) |
| `artist_country` | Resuelto por Script 3 cada semana                            | Leído del catálogo (pre-resuelto)              |
| `macro_genre`    | Resuelto por Script 3 cada semana                            | Leído del catálogo (pre-resuelto)              |
| `artists_found`  | Generado por Script 3 cada semana                            | Leído del catálogo (pre-resuelto)              |

------

## ⚙️ Análisis del Workflow de GitHub Actions (`3_enrich-chart-data.yml`)

### Estructura del Workflow

```yaml
name: 3 - Enrich Chart Data

on:
  schedule:
    # Ejecutar cada lunes a las 14:00 UTC (después de que complete Script 2.2)
    - cron: '00 14 * * 1'
  
  workflow_dispatch:

env:
  RETENTION_WEEKS: 78
```

### Pasos del Job

| Paso | Nombre                                | Propósito                                                    |
| :--- | :------------------------------------ | :----------------------------------------------------------- |
| 1    | 📚 Checkout del repositorio            | Clonar repositorio con historial completo                    |
| 2    | 🐍 Configurar Python                   | Instalar Python 3.12 con caché de pip                        |
| 3    | 📦 Instalar dependencias               | Instalar requirements (selenium, yt-dlp, etc.)               |
| 4    | 📁 Crear estructura de directorios     | Crear carpetas de entrada y salida                           |
| 5    | 🔍 Verificar existencia del catálogo   | Verificar que `build_song.db` existe antes de proceder (NUEVO) |
| 6    | 🚀 Ejecutar script de enriquecimiento  | Ejecutar el script principal de enriquecimiento              |
| 7    | ✅ Verificar resultados                | Listar archivos generados y tamaños                          |
| 8    | 📤 Commit y push de cambios            | Subir cambios a GitHub (con rebase)                          |
| 9    | 📦 Subir artefactos (en caso de fallo) | Subir datos de depuración para solución de problemas         |
| 10   | 🧹 Limpiar bases de datos antiguas     | Eliminar bases de datos con más de 78 semanas                |
| 11   | 📋 Informe final                       | Generar resumen de ejecución                                 |

### Pasos Detallados

#### **1. 📚 Checkout del Repositorio**

```yaml
- name: 📚 Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
```



#### **2. 🐍 Configurar Python**

```yaml
- name: 🐍 Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: 'pip'
```



#### **3. 📦 Instalar Dependencias**

```yaml
- name: 📦 Install dependencies
  run: |
    pip install -r requirements.txt
```



#### **4. 📁 Crear Estructura de Directorios**

```yaml
- name: 📁 Create directory structure
  run: |
    mkdir -p charts_archive/1_download-chart/databases
    mkdir -p charts_archive/3_enrich-chart-data
```



#### **5. 🔍 Verificar Existencia del Catálogo de Canciones**

```yaml
- name: 🔍 Verify song catalog database exists
  run: |
    if [ ! -f "charts_archive/2_2.build-song-catalog/build_song.db" ]; then
      echo "❌ Song catalog database not found at charts_archive/2_2.build-song-catalog/build_song.db"
      echo "   Please ensure script 2_2 has run successfully before this workflow."
      exit 1
    fi
    echo "✅ Song catalog database found"
    SIZE=$(stat -c%s "charts_archive/2_2.build-song-catalog/build_song.db")
    echo "   Size: $((SIZE / 1024)) KB"
```



#### **6. 🚀 Ejecutar Script de Enriquecimiento**

```yaml
- name: 🚀 Run enrichment script
  run: |
    python scripts/3_enrich_chart_data.py
  env:
    YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
    GITHUB_ACTIONS: true
```



#### **7. ✅ Verificar Resultados**

```yaml
- name: ✅ Verify results
  run: |
    echo "📊 Verifying execution results..."
    echo "📂 Contents of charts_archive/3_enrich-chart-data/:"
    ls -lah charts_archive/3_enrich-chart-data/
    
    echo -e "\n🗃️ Enriched databases:"
    ls -lah charts_archive/3_enrich-chart-data/*_enriched.db 2>/dev/null || echo "No enriched databases found"
```



#### **8. 📤 Commit y Push de Cambios**

```yaml
- name: 📤 Commit and push changes
  run: |
    git config --global user.name "github-actions[bot]"
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    git add charts_archive/3_enrich-chart-data/
    
    if git diff --cached --quiet; then
      echo "🔭 No changes to commit"
    else
      DATE=$(date +'%Y-%m-%d')
      WEEK=$(date +'%Y-W%W')
      git commit -m "🤖 Enriched chart data (catalog-linked) ${DATE} (Week ${WEEK}) [Automated]"
      git pull --rebase origin main
      git push origin HEAD:main
    fi
```



#### **9. 📦 Subir Artefactos (en caso de fallo)**

```yaml
- name: 📦 Upload artifacts (on failure)
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: enrich-debug-${{ github.run_number }}
    path: |
      scripts/3_enrich_chart_data.py.log
      charts_archive/3_enrich-chart-data/
    retention-days: 7
```



#### **10. 🧹 Limpiar Bases de Datos Antiguas**

```yaml
- name: 🧹 Clean old databases
  run: |
    echo "🧹 Cleaning enriched databases older than ${{ env.RETENTION_WEEKS }} weeks..."
    find charts_archive/3_enrich-chart-data/ \
      -name "*_enriched.db" \
      -type f \
      -mtime +$((RETENTION_WEEKS * 7)) \
      -delete
```



#### **11. 📋 Informe Final**

```yaml
- name: 📋 Final report
  if: always()
  run: |
    echo "========================================"
    echo "🎵 ENRICHMENT EXECUTION REPORT"
    echo "========================================"
    echo "📅 Date: $(date)"
    echo "📌 Trigger: ${{ github.event_name }}"
    
    LATEST_DB=$(ls -t charts_archive/3_enrich-chart-data/*_enriched.db 2>/dev/null | head -1)
    if [ -f "$LATEST_DB" ]; then
      echo "✅ Latest enriched database: $(basename $LATEST_DB)"
      SIZE=$(stat -c%s "$LATEST_DB")
      echo "📊 Size: $((SIZE / 1024)) KB"
      
      if command -v sqlite3 &> /dev/null; then
        echo ""
        echo "📊 Database statistics:"
        TOTAL=$(sqlite3 "$LATEST_DB" "SELECT COUNT(*) FROM enriched_songs;" 2>/dev/null)
        LINKED=$(sqlite3 "$LATEST_DB" "SELECT COUNT(*) FROM enriched_songs WHERE id IS NOT NULL;" 2>/dev/null)
        MULTI=$(sqlite3 "$LATEST_DB" "SELECT COUNT(*) FROM enriched_songs WHERE artist_country = 'Multi-country';" 2>/dev/null)
        ERROR=$(sqlite3 "$LATEST_DB" "SELECT COUNT(*) FROM enriched_songs WHERE error != '';" 2>/dev/null)
        
        echo "   • Total songs: $TOTAL"
        echo "   • Linked to catalog: $LINKED ($(( LINKED * 100 / TOTAL ))%)"
        echo "   • Multi-country: $MULTI"
        echo "   • With errors: $ERROR"
      fi
    fi
```



### Programación Cron
```cron
'00 14 * * 1'  # Minuto 0, Hora 14, Cualquier día del mes, Cualquier mes, Lunes
```
- **Ejecución**: Cada lunes a las 14:00 UTC
- **Desfase**: 2 horas después del Script 1 (12:00 UTC) y 45 minutos después del Script 2.2 (13:15 UTC)
- **Propósito**: Permite que el Script 2.2 complete y genere `build_song.db` antes de que comience el enriquecimiento

### Disparadores de Ejecución

Este workflow se ejecuta **solo** en:

- **Ejecución programada**: Cada lunes a las 14:00 UTC
- **Ejecución manual**: Mediante `workflow_dispatch` desde la interfaz de GitHub Actions

> **Nota**: La ejecución automática en `git push` ha sido desactivada. Los cambios en scripts o en el catálogo de canciones no activan este workflow automáticamente. Para probar cambios, use la ejecución manual o espere la próxima ejecución programada.

### Línea de Tiempo del Flujo de Ejecución

```text
Lunes 12:00 UTC ─→ Script 1: Descargar charts
    ↓
13:00 UTC ─→ Script 2.1: Enriquecimiento de artistas
    ↓
13:15 UTC ─→ Script 2.2: Construir catálogo de canciones
    ↓
14:00 UTC ─→ Script 3: Enriquecimiento de charts (ESTE WORKFLOW)
    ↓
15:00 UTC ─→ Script 4: Generación de notebooks
    ↓
Martes 12:00 UTC ─→ Script 5: Exportar a PDF + Drive
```

### Secretos Requeridos

| Secreto           | Propósito                                                    |
| :---------------- | :----------------------------------------------------------- |
| `YOUTUBE_API_KEY` | Clave de YouTube Data API v3 para recuperar metadatos de video (Capa 1). Opcional; el script recurre a Selenium/yt-dlp sin ella. |

------

## 🚀 Instalación y Configuración Local

### Prerrequisitos

- Python 3.7 o superior (3.12 recomendado)
- Git instalado
- Acceso a Internet
- Bases de datos semanales de charts del Script 1 (`charts_archive/1_download-chart/databases/`)
- **Base de datos del catálogo de canciones del Script 2_2** (`charts_archive/2_2.build-song-catalog/build_song.db`) - **NUEVO REQUISITO**
- (Opcional) Clave de YouTube Data API v3 para recuperación más rápida de metadatos

### Instalación Paso a Paso

#### **1. Clonar el Repositorio**

```bash
git clone https://github.com/adroguetth/Music-Charts-Intelligence.git
cd Music-Charts-Intelligence
```



#### **2. Crear Entorno Virtual (recomendado)**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```



#### **3. Instalar Dependencias**

```bash
pip install -r requirements.txt
```



#### **4. Configurar Clave de YouTube API (opcional pero recomendado)**

```bash
# Linux/Mac
export YOUTUBE_API_KEY="tu-clave-api-aqui"

# Windows (Command Prompt)
set YOUTUBE_API_KEY=tu-clave-api-aqui

# Windows (PowerShell)
$env:YOUTUBE_API_KEY="tu-clave-api-aqui"
```



#### **5. Asegurar que el Catálogo de Canciones Exista**

```bash
# Verificar que el catálogo del Script 2_2 existe
ls -la charts_archive/2_2.build-song-catalog/build_song.db
```



#### **6. Ejecutar Prueba Inicial**

```bash
python scripts/3_enrich_chart_data.py
```



### Configuración de Desarrollo

```bash
# Simular entorno de GitHub Actions
export GITHUB_ACTIONS=true

# Ejecutar sin confirmación interactiva
export YOUTUBE_API_KEY="tu-clave-api"
```



------

## 📁 Estructura de Archivos Generada

```text
charts_archive/
├── 1_download-chart/
│   ├── databases/
│   │   ├── youtube_charts_2025-W01.db
│   │   ├── youtube_charts_2025-W02.db
│   │   └── ...
│   └── backup/
├── 2_2.build-song-catalog/
│   └── build_song.db                       # Catálogo de canciones (entrada requerida)
└── 3_enrich-chart-data/                    # ← Salida de este script
    ├── youtube_charts_2025-W01_enriched.db
    ├── youtube_charts_2025-W02_enriched.db
    └── ...
```



### Crecimiento de la Base de Datos

| Métrica                  | Valor                 |
| :----------------------- | :-------------------- |
| Canciones semanales      | 100                   |
| Tamaño por base de datos | 200-300 KB            |
| Almacenamiento anual     | 15-20 MB              |
| Retención                | 78 semanas (1.5 años) |

------

## 🔧 Personalización y Configuración

### Parámetros Ajustables en el Script

```python
# En 3_enrich_chart_data.py
SLEEP_BETWEEN_VIDEOS = 0.1      # Pausa entre videos (segundos)
YT_DLP_RETRIES = 5               # Reintentos para yt-dlp
SELENIUM_TIMEOUT = 10            # Tiempo de espera de Selenium (segundos)
```



### Configuración del Workflow

```yaml
# En 3_enrich-chart-data.yml
env:
  RETENTION_WEEKS: 78       # Semanas a retener bases de datos

timeout-minutes: 60          # Tiempo máximo total del job
```



### Agregar Nuevos Delimitadores de Artistas

```python
# En parse_artist_list()
separators = [
    '&', 'feat.', 'ft.', ',', ' y ', ' and ',
    ' with ', ' x ', ' vs ',           # Existentes
    ' présentation ', ' en duo avec ', # Francés
    ' und ', ' & ',                    # Alemán
    ' e ', ' com '                     # Portugués
]
```

> **Nota**: Estos delimitadores ahora solo se usan para la detección de colaboraciones en títulos de video, no para la resolución de país/género.


------

## 🐛 Solución de Problemas

### Problemas Comunes y Soluciones

| Error                                 | Causa Probable                | Solución                                             |
| :------------------------------------ | :---------------------------- | :--------------------------------------------------- |
| `Song catalog not found`              | Script 2_2 no se ha ejecutado | Ejecutar `2_2.build_song_catalog.py` primero         |
| `No module named 'isodate'`           | Librería faltante             | `pip install isodate`                                |
| `Selenium: ChromeDriver not found`    | Chrome no instalado           | `sudo apt-get install google-chrome-stable`          |
| `No database found`                   | Script 1 no se ha ejecutado   | Ejecutar Script 1 primero                            |
| `Sign in to confirm you're not a bot` | YouTube bloquea yt-dlp        | Configurar `YOUTUBE_API_KEY`                         |
| `API key not valid`                   | Clave inválida                | Verificar en Google Cloud Console                    |
| `Quota exceeded`                      | Límite diario alcanzado       | El script recurre automáticamente a Selenium         |
| `NULL id in enriched output`          | Canción no está en catálogo   | Ejecutar Script 2_2 para agregar canciones faltantes |

### Métricas de Rendimiento

| Escenario          | Tiempo       | Notas                            |
| :----------------- | :----------- | :------------------------------- |
| Con clave de API   | ~2 minutos   | 0.3-0.8s por video               |
| Sin API (Selenium) | 5-7 minutos  | Depende de la carga de la página |
| Sin API (yt-dlp)   | 8-10 minutos | Puede ser bloqueado              |

### Migración desde la Versión Anterior

Si estaba usando la versión anterior del Script 3 (con el sistema de ponderación de colaboraciones incorporado), siga estos pasos para migrar:

1. **Ejecutar Script 2_2** para construir el catálogo de canciones con país/género resuelto
2. **Actualizar su workflow** para asegurar que el Script 2_2 se ejecute antes del Script 3
3. **Eliminar** cualquier modificación personalizada a `COUNTRY_TO_CONTINENT` o `GENRE_HIERARCHY` del Script 3
4. **Agregar** esas personalizaciones al Script 2_2 en su lugar
5. **Volver a ejecutar** el Script 3 – ahora leerá los valores pre-resueltos del catálogo

------

## 📄 Licencia y Atribución

- **Licencia**: MIT
- **Autor**: Alfonso Droguett
  - 🔗 **LinkedIn:** [Alfonso Droguett](https://www.linkedin.com/in/adroguetth/)
  - 🌐 **Portafolio web:** [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/)
  - 📧 **Email:** adroguett.consultor@gmail.com
- **Fuentes de Datos**:
  - YouTube Data API v3
  - Sitio web de YouTube (a través de Selenium/yt-dlp)
  - Catálogo de canciones del Script 2_2

------

## 🤝 Contribución

1. Reportar problemas con registros completos
2. Proponer mejoras con casos de uso
3. Agregar nuevos patrones de detección de tipo de video
4. Mejorar los patrones de detección de colaboraciones
5. Mantener la compatibilidad con el esquema de base de datos existente

---

**⭐ Si encuentra útil este proyecto, ¡considere darle una estrella en GitHub!**
