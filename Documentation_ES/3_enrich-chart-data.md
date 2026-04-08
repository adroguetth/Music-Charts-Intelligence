# Script 3: YouTube Chart Enrichment System

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Web Scraping](https://img.shields.io/badge/Web-Scraping-orange?style=flat-square) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white) ![yt-dlp](https://img.shields.io/badge/yt--dlp-FF6F61?style=flat-square&logo=youtube&logoColor=white) ![YouTube API](https://img.shields.io/badge/YouTube_API-FF0000?style=flat-square&logo=youtube&logoColor=white) 

## 📥 Descargas Rápidas

| Documento                       | Formato                                                      |
| :------------------------------ | :----------------------------------------------------------- |
| **🇬🇧 Documentación en Inglés**  | [PDF](https://drive.google.com/file/d/1XGEx2fRBCpOhU5BfY_YjlKm6zmI41RpB/view?usp=drive_link) |
| **🇪🇸 Documentación en Español** | [PDF](https://drive.google.com/file/d/1tSFjf_gQQeArdE4n5DLL2I2G_MJW6vE3/view?usp=sharing) |

## 📋 Descripción General

Este script es el **tercer componente** del sistema de inteligencia de charts de YouTube. Toma la base de datos de charts semanal (del Script 1) y la base de datos de artistas (del Script 2), y luego **enriquece cada canción con metadatos detallados de video de YouTube** usando un sistema inteligente de 3 capas.

El script extrae duración de video, likes, comentarios, fecha de subida, idioma de audio, restricciones regionales, y clasifica el tipo de video (oficial/lírico/en vivo), el tipo de canal (VEVO/Topic/Artista), y los patrones de colaboración. También resuelve país y género para pistas con múltiples artistas usando un algoritmo de colaboración ponderada.

### Características Principales

- **🔄 Sistema de 3 Capas**: API de YouTube (prioridad) → Selenium → yt-dlp (último recurso) para máxima confiabilidad
- **⚡ Rendimiento Optimizado**: Procesa 100 canciones en ~2 minutos usando la API de YouTube (vs. 8+ minutos con solo yt-dlp)
- **👥 Sistema de Colaboración Ponderada**: Algoritmo inteligente que determina país y género cuando hay múltiples artistas
- **🗺️ Jerarquías Culturales por País**: Listas de géneros ordenadas que reflejan importancia local (ej., K-Pop primero en Corea del Sur)
- **📝 Detección de Metadatos de Video**: Identifica si un video es oficial, lírico, presentación en vivo o remix
- **📺 Clasificación de Canales**: Detecta VEVO, Topic, Label/Studio, Artist Channel y más
- **🔄 Actualizaciones Automáticas**: Selecciona la base de datos de charts más reciente y genera su versión enriquecida
- **🔧 Optimizado para CI/CD**: Específicamente diseñado para ejecutarse en GitHub Actions sin intervención manual

------

## 📊 Diagrama de Flujo del Proceso

### **Leyenda**

| Color          | Tipo           | Descripción                                                  |
| :------------- | :------------- | :----------------------------------------------------------- |
| 🔵 Azul         | Entrada        | Datos fuente (base de datos de charts + base de datos de artistas) |
| 🟠 Naranja      | Proceso        | Lógica de procesamiento interno                              |
| 🟣 Púrpura      | API            | Consultas a servicios externos (API YouTube, Selenium, yt-dlp) |
| 🟢 Verde        | Almacenamiento | Bases de datos SQLite, archivos temporales                   |
| 🔴 Rojo         | Decisión       | Puntos de ramificación condicional                           |
| 🟢 Verde Oscuro | Salida         | Base de datos enriquecida                                    |

### **Diagrama 1: Vista General del Flujo Principal**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/3_enrich_chart_data/1.png" alt="Diagrama 1: Vista General del Flujo Principal" width="700">

Este diagrama muestra el **pipeline de alto nivel** de todo el sistema:

1. **Entrada**: Localiza la base de datos de charts más reciente (`youtube_charts_YYYY-WXX.db`) del Script 1
2. **Descargar DB de Artistas**: Obtiene `artist_countries_genres.db` de GitHub (archivo temporal)
3. **Construir Diccionario**: Crea diccionario en memoria `{nombre_normalizado: (país, género)}` para búsquedas O(1)
4. **Cargar Canciones**: Lee 100 canciones de la tabla `chart_data`
5. **Crear Tabla de Salida**: Configura la tabla `enriched_songs` con 25 columnas + índices
6. **Bucle por Canción**: Para cada canción (1 a 100):
   - **Extraer Artistas**: Separa nombres usando delimitadores (&, feat., ft., etc.)
   - **Buscar Datos de Artistas**: Consulta el diccionario para país/género de cada artista
   - **Resolución de Colaboración**: Aplica algoritmo ponderado para determinar país/género final
   - **Obtener Metadatos de YouTube**: Sistema de 3 capas (API → Selenium → yt-dlp)
   - **Clasificar Video**: Detecta tipo, tipo de canal, colaboración, temporada de subida
   - **Insertar Fila**: Guarda datos enriquecidos en la base de datos de salida
7. **Limpieza**: Elimina el archivo temporal de la base de datos de artistas
8. **Salida**: Base de datos enriquecida lista para el Script 4 (generación de notebooks)

### **Diagrama 2: Sistema de Recuperación de Metadatos de 3 Capas**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/3_enrich_chart_data/2.png" alt="Diagrama 2: Sistema de Recuperación de Metadatos de 3 Capas" width="700">

Este diagrama detalla la **estrategia de recuperación en cascada** para metadatos de video de YouTube:

1. **Inicio**: Recibe URL de video de YouTube y string CSV de artistas
2. **Capa 1 – API de YouTube Data v3** (0.3–0.8s/video):
   - Extrae video_id de la URL (patrón de 11 caracteres)
   - Consulta API para `snippet`, `contentDetails`, `statistics`
   - Recupera: duración, likes, comentarios, idioma de audio, fecha de subida, restricciones regionales
   - **Si tiene éxito** → Retorna metadatos completos ✅
   - **Si falla** (sin clave, cuota excedida, error) → Procede a Capa 2
3. **Capa 2 – Selenium Navegador Headless** (3–5s/video):
   - Lanza navegador Chrome headless
   - Navega a la página de video, espera elemento de título
   - Extrae: título, duración (del reproductor), nombre del canal, fecha de subida (de meta tag)
   - **Nota**: Selenium NO retorna likes, comentarios o idioma de audio
   - **Si tiene éxito** → Retorna metadatos parciales ✅
   - **Si falla** → Procede a Capa 3
4. **Capa 3 – yt-dlp con Rotación de Clientes** (2–4s/video):
   - Intenta múltiples configuraciones de cliente secuencialmente:
     - `android` (más confiable)
     - `ios` (buen respaldo)
     - `android + web` (combinación)
     - `web` (navegador estándar)
   - Cada intento incluye reintentos y demoras para evitar detección de bots
   - **Si alguno tiene éxito** → Retorna metadatos completos ✅
   - **Si todos fallan** → Retorna metadatos vacíos con mensaje de error

### **Diagrama 3: Sistema de Colaboración Ponderada**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/3_enrich_chart_data/3.png" alt="Diagrama 3: Sistema de Colaboración Ponderada" width="700">

Este diagrama muestra el **motor de decisión inteligente** para pistas con múltiples artistas:

| Regla                                    | Condición                             | Resultado                                              |
| :--------------------------------------- | :------------------------------------ | :----------------------------------------------------- |
| **Regla 1 – Mayoría Absoluta**           | >50% del mismo país                   | Retorna país mayoritario + infiere género de jerarquía |
| **Regla 2 – División 50/50 Exacta**      | =50% con exactamente 2 países         | Retorna país mayoritario + infiere género              |
| **Regla 3 – División 50/50 (3+ países)** | =50% con 3+ países                    | Retorna "Multi-country" + "Multi-genre"                |
| **Regla 4 – Mayoría Relativa**           | <50% con mismo continente y ≤2 países | Retorna país mayoritario + infiere género              |
| **Regla 5 – Caso contrario**             | <50% con diferentes continentes       | Retorna "Multi-country" + "Multi-genre"                |
| **Regla 6 – Respaldo**                   | Sin artistas conocidos                | Retorna "Unknown" + "Pop"                              |

**Inferencia de Género** (`infer_genre_by_country`):

- Recupera la jerarquía de género del país desde `GENRE_HIERARCHY`
- Si un solo género tiene >50% entre los artistas → lo usa
- Si no, elige el género de mayor rango presente en los géneros conocidos
- Respalda al primer género de la jerarquía

------

## 🔍 Análisis Detallado de `3_enrich_chart_data.py`

### Estructura del Código

#### **1. Configuración y Rutas**

```python
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
INPUT_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"
URL_ARTIST_DB = "https://github.com/adroguetth/Music-Charts-Intelligence/raw/refs/heads/main/charts_archive/2_countries-genres-artist/artist_countries_genres.db"
OUTPUT_DIR = PROJECT_ROOT / "charts_archive" / "3_enrich-chart-data"
```

El script integra los dos componentes anteriores:

| Ruta            | Propósito                                                    |
| :-------------- | :----------------------------------------------------------- |
| `INPUT_DB_DIR`  | Entrada: Bases de datos semanales de charts del Script 1     |
| `URL_ARTIST_DB` | Referencia: Base de datos de artistas del Script 2 (descargada temporalmente) |
| `OUTPUT_DIR`    | Salida: Bases de datos enriquecidas para el Script 4         |

#### **2. Tablas de Referencia Principal**

**Mapa País → Continente (196 países):**

```python
COUNTRY_TO_CONTINENT = {
    "South Korea": "Asia", "Japan": "Asia", "China": "Asia",
    "United States": "America", "Canada": "America",
    "United Kingdom": "Europe", "France": "Europe",
    "Nigeria": "Africa", "South Africa": "Africa",
    "Australia": "Oceania", "New Zealand": "Oceania",
    # ... 196 países en total
}
```

**Jerarquías de Género por País (prioridad cultural local):**

```python
GENRE_HIERARCHY = {
    "South Korea": ["K-Pop/K-Rock", "Hip-Hop/Rap", "Rock", "Ballad", "Trot"],
    "Brazil": ["Sertanejo", "Funk Brasileiro", "Reggaeton/Latin Trap", "Pop", "Rock"],
    "Nigeria": ["Afrobeats", "Hip-Hop/Rap", "Gospel", "Jùjú", "Fuji"],
    # ... más de 100 países con jerarquías personalizadas
}
```

#### **3. Sistema de Recuperación de Metadatos de 3 Capas**

```python
def fetch_video_metadata(url: str, artists_csv: str = "", api_key: str = None) -> dict:
    """
    Orquesta la estrategia de recuperación de metadatos de tres capas.
    
    Capa 1 — API de YouTube Data v3:
        Metadatos completos: duración, likes, comentarios, idioma, fecha, restricciones.
        Termina inmediatamente en caso de éxito.
    
    Capa 2 — Selenium navegador headless:
        Metadatos parciales: duración, tipo de canal, fecha, flags de tipo de video.
        Usado cuando la API no está disponible o retorna error.
    
    Capa 3 — yt-dlp con rotación de clientes anti-bloqueo:
        Prueba android → ios → android+web → web en orden.
        Último recurso; puede ser más lento y aún fallar.
    """
```

**Capa 1 – API de YouTube Data v3:**

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

**Capa 2 – Selenium Navegador Headless:**

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
    {'player_client': ['android']},     # Más confiable
    {'player_client': ['ios']},         # Buen respaldo
    {'player_client': ['android', 'web']},  # Combinación
    {'player_client': ['web']},         # Navegador estándar
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

#### **4. Sistema de Colaboración Ponderada**

```python
def resolve_country_and_genre(artists_info: list) -> tuple:
    """
    Aplica el algoritmo de colaboración ponderada para determinar un solo
    país y género para una pista potencialmente con múltiples artistas.
    
    Árbol de decisión:
        Regla 1 – Mayoría absoluta (>50%): asignar país mayoritario + su género
        Regla 2 – División exacta 50/50 (2 países): asignar país mayoritario
        Regla 3 – División exacta 50/50 (3+ países): Multi-country / Multi-genre
        Regla 4 – Mayoría relativa (<50%): asignar si mismo continente y ≤2 países
        Regla 5 – Caso contrario: Multi-country / Multi-genre
    """
```

**Ejemplos de escenarios:**

| Escenario | Artistas                       | Países        | Resultado                          |
| :-------- | :----------------------------- | :------------ | :--------------------------------- |
| 1         | BTS (solo)                     | Corea del Sur | Corea del Sur, K-Pop/K-Rock        |
| 2         | ROSÉ (CS) + Bruno Mars (USA)   | 2 distintos   | Multi-country, Multi-genre         |
| 3         | Bad Bunny (PR) + J Balvin (CO) | 2 distintos   | Multi-country, Multi-genre         |
| 4         | 3 artistas USA + 1 UK          | 75% USA       | Estados Unidos, Pop (de jerarquía) |
| 5         | Todos desconocidos             | Ninguno       | Unknown, Pop                       |

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

#### **6. Procesamiento de Nombres de Artistas**

```python
def parse_artist_list(artist_names: str) -> list:
    """Separa nombres de artistas usando múltiples delimitadores."""
    text = artist_names
    for sep in ['&', 'feat.', 'ft.', ',', ' y ', ' and ', ' with ', ' x ', ' vs ']:
        text = text.replace(sep, '|')
    return [part.strip() for part in text.split('|') if part.strip()]

def normalize_name(name: str) -> str:
    """Normaliza nombre de artista para búsqueda en diccionario."""
    name = re.sub(r'\s+', ' ', str(name)).strip().lower()
    name = re.sub(r'[^\w\s]', '', name)  # Eliminar puntuación
    return name
```

#### **7. Esquema de la Base de Datos de Salida**

```sqlite
CREATE TABLE enriched_songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    artist_country TEXT,
    macro_genre TEXT,
    artists_found TEXT,
    error TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimización de consultas
CREATE INDEX idx_country ON enriched_songs(artist_country);
CREATE INDEX idx_genre ON enriched_songs(macro_genre);
CREATE INDEX idx_upload_date ON enriched_songs(upload_date);
CREATE INDEX idx_error ON enriched_songs(error);
```

---

## ⚙️ Análisis del Workflow de GitHub Actions (`3_enrich-chart-data.yml`)

### Estructura del Workflow

```yaml
name: 3- Enriquecer Datos de Charts

on:
  schedule:
    # Se ejecuta cada lunes a las 14:00 UTC (2 horas después de la descarga)
    - cron: '0 14 * * 1'
  
  # Permite ejecución manual del workflow
  workflow_dispatch:
  
  # Se dispara con push a main si cambia el script de enriquecimiento
  push:
    branches:
      - main
    paths:
      - 'scripts/3_enrich_chart_data.py'
      - '.github/workflows/3_enrich-chart-data.yml'

env:
  # Número de semanas para retener bases de datos enriquecidas (1.5 años)
  RETENTION_WEEKS: 78
```

### Pasos del Job

| Paso | Nombre                               | Propósito                                       |
| :--- | :----------------------------------- | :---------------------------------------------- |
| 1    | 📚 Clonar repositorio                 | Clonar repositorio con historial completo       |
| 2    | 🐍 Configurar Python                  | Instalar Python 3.12 con caché de pip           |
| 3    | 📦 Instalar dependencias              | Instalar requisitos (selenium, yt-dlp, etc.)    |
| 4    | 📁 Crear estructura de directorios    | Crear carpetas de entrada y salida              |
| 5    | 🚀 Ejecutar script de enriquecimiento | Ejecutar script principal de enriquecimiento    |
| 6    | ✅ Verificar resultados               | Listar archivos generados y tamaños             |
| 7    | 📤 Commit y push de cambios           | Subir cambios a GitHub (con rebase)             |
| 8    | 📦 Subir artefactos (en fallo)        | Subir datos de depuración para troubleshooting  |
| 9    | 🧹 Limpiar bases de datos antiguas    | Eliminar bases de datos anteriores a 78 semanas |
| 10   | 📋 Reporte final                      | Generar resumen de ejecución                    |

### Pasos Detallados

#### **1. 📚 Clonar Repositorio**

```yaml
- name: 📚 Clonar repositorio
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

#### **2. 🐍 Configurar Python**

```yaml
- name: 🐍 Configurar Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: 'pip'
```

#### **3. 📦 Instalar Dependencias**

```yaml
- name: 📦 Instalar dependencias
  run: |
    pip install -r requirements.txt
```

#### **4. 📁 Crear Estructura de Directorios**

```yaml
- name: 📁 Crear estructura de directorios
  run: |
    mkdir -p charts_archive/1_download-chart/databases
    mkdir -p charts_archive/3_enrich-chart-data
```

#### **5. 🚀 Ejecutar Script de Enriquecimiento**

```yaml
- name: 🚀 Ejecutar script de enriquecimiento
  run: |
    python scripts/3_enrich_chart_data.py
  env:
    YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
    GITHUB_ACTIONS: true
```

#### **6. ✅ Verificar Resultados**

```yaml
- name: ✅ Verificar resultados
  run: |
    echo "📊 Verificando resultados de ejecución..."
    echo "📂 Contenido de charts_archive/3_enrich-chart-data/:"
    ls -lah charts_archive/3_enrich-chart-data/
```

#### **7. 📤 Commit y Push de Cambios**

```yaml
- name: 📤 Commit y push de cambios
  run: |
    git config --global user.name "github-actions[bot]"
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    git add charts_archive/3_enrich-chart-data/
    
    if git diff --cached --quiet; then
      echo "🔭 No hay cambios para commit"
    else
      DATE=$(date +'%Y-%m-%d')
      WEEK=$(date +'%Y-W%W')
      git commit -m "🤖 Datos de charts enriquecidos ${DATE} (Semana ${WEEK}) [Automated]"
      git pull --rebase origin main
      git push origin HEAD:main
    fi
```

#### **8. 📦 Subir Artefactos (en fallo)**

```yaml
- name: 📦 Subir artefactos (en fallo)
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: enrich-debug-${{ github.run_number }}
    path: |
      charts_archive/3_enrich-chart-data/
    retention-days: 7
```

#### **9. 🧹 Limpiar Bases de Datos Antiguas**

```yaml
- name: 🧹 Limpiar bases de datos antiguas
  run: |
    echo "🧹 Limpiando bases de datos enriquecidas anteriores a ${{ env.RETENTION_WEEKS }} semanas..."
    find charts_archive/3_enrich-chart-data/ \
      -name "*_enriched.db" \
      -type f \
      -mtime +$((RETENTION_WEEKS * 7)) \
      -delete
```

#### **10. 📋 Reporte Final**

```yaml
- name: 📋 Reporte final
  if: always()
  run: |
    echo "========================================"
    echo "🎵 REPORTE DE EJECUCIÓN DE ENRIQUECIMIENTO"
    echo "========================================"
    echo "📅 Fecha: $(date)"
    echo "📌 Disparador: ${{ github.event_name }}"
    
    LATEST_DB=$(ls -t charts_archive/3_enrich-chart-data/*_enriched.db 2>/dev/null | head -1)
    if [ -f "$LATEST_DB" ]; then
      echo "✅ Base de datos enriquecida más reciente: $(basename $LATEST_DB)"
      SIZE=$(stat -c%s "$LATEST_DB")
      echo "📊 Tamaño: $((SIZE / 1024)) KB"
    fi
```

### Programación Cron

```cron
'0 14 * * 1'  # Minuto 0, Hora 14, Cualquier día del mes, Cualquier mes, Lunes
```

- **Ejecución**: Cada lunes a las 14:00 UTC
- **Desplazamiento**: 2 horas después del Script 1 (12:00 UTC) y 1 hora después del Script 2 (13:00 UTC)
- **Propósito**: Permite que los workflows anteriores se completen antes de que comience el enriquecimiento

### Secretos Requeridos

| Secreto           | Propósito                                                    |
| :---------------- | :----------------------------------------------------------- |
| `YOUTUBE_API_KEY` | Clave de API de YouTube Data v3 para recuperar metadatos de video (Capa 1). Opcional; el script cae a Selenium/yt-dlp sin ella. |

------

## 🚀 Instalación y Configuración Local

### Requisitos Previos

- Python 3.7 o superior (3.12 recomendado)
- Git instalado
- Acceso a Internet
- (Opcional) Clave de API de YouTube Data v3 para recuperación más rápida de metadatos

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

#### **4. Configurar Clave API de YouTube (opcional pero recomendado)**

```bash
# Linux/Mac
export YOUTUBE_API_KEY="tu-clave-api-aqui"

# Windows (Command Prompt)
set YOUTUBE_API_KEY=tu-clave-api-aqui

# Windows (PowerShell)
$env:YOUTUBE_API_KEY="tu-clave-api-aqui"
```

#### **5. Ejecutar Prueba Inicial**

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

---

## 📁 Estructura de Archivos Generada

```text
charts_archive/
├── 1_download-chart/
│   ├── databases/
│   │   ├── youtube_charts_2025-W01.db
│   │   ├── youtube_charts_2025-W02.db
│   │   └── ...
│   └── backup/
├── 2_countries-genres-artist/
│   └── artist_countries_genres.db       # Base de datos de artistas (descargada temporalmente)
└── 3_enrich-chart-data/                  # ← Salida de este script
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
SLEEP_BETWEEN_VIDEOS = 0.1    # Pausa entre videos (segundos)
YT_DLP_RETRIES = 5             # Intentos de reintento de yt-dlp
SELENIUM_TIMEOUT = 10          # Timeout de carga de página de Selenium (segundos)
```

### Configuración del Workflow

```yaml
# En 3_enrich-chart-data.yml
env:
  RETENTION_WEEKS: 78       # Semanas para retener bases de datos

timeout-minutes: 60          # Timeout total del job
```

### Añadir Nuevos Delimitadores de Artistas

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

### Ampliar Jerarquías de Género

```python
# En GENRE_HIERARCHY
"Nuevo País": [
    "Género Prioritario 1",   # Prioridad 1
    "Género Prioritario 2",   # Prioridad 2
    "Género Prioritario 3"    # Prioridad 3
]
```

---

## 🐛 Solución de Problemas

### Problemas Comunes y Soluciones

| Error                                 | Causa Probable                 | Solución                                    |
| :------------------------------------ | :----------------------------- | :------------------------------------------ |
| `No module named 'isodate'`           | Librería faltante              | `pip install isodate`                       |
| `Selenium: ChromeDriver not found`    | Chrome no instalado            | `sudo apt-get install google-chrome-stable` |
| `No database found`                   | El Script 1 no se ha ejecutado | Ejecutar Script 1 primero                   |
| `Sign in to confirm you're not a bot` | yt-dlp bloqueado por YouTube   | Configurar `YOUTUBE_API_KEY`                |
| `API key not valid`                   | Clave inválida                 | Verificar clave en Google Cloud Console     |
| `Quota exceeded`                      | Límite diario alcanzado        | El script cae automáticamente a Selenium    |

### Métricas de Rendimiento

| Escenario          | Tiempo       | Notas                      |
| :----------------- | :----------- | :------------------------- |
| Con clave API      | ~2 minutos   | 0.3-0.8s por video         |
| Sin API (Selenium) | 5-7 minutos  | Depende de carga de página |
| Sin API (yt-dlp)   | 8-10 minutos | Puede ser bloqueado        |

------

## 📄 Licencia y Atribución

- **Licencia**: MIT
- **Autor**: Alfonso Droguett
  - 🔗 **LinkedIn:** [Alfonso Droguett](https://www.linkedin.com/in/adroguetth/)
  - 🌐 **Portafolio web:** [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/)
  - 📧 **Email:** adroguett.consultor@gmail.com
- **Fuentes de Datos**:
  - API de YouTube Data v3
  - Sitio web de YouTube (vía Selenium/yt-dlp)
  - Base de datos de artistas del Script 2

------

## 🤝 Contribución

1. Reportar problemas con registros completos
2. Proponer mejoras con casos de uso
3. Añadir nuevas jerarquías de género para países faltantes
4. Mejorar patrones de detección de colaboraciones
5. Mantener compatibilidad con el esquema de base de datos existente

------

**⭐ Si este proyecto te resulta útil, ¡considera darle una estrella en GitHub!**
