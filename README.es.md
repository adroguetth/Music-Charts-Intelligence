# 🎵 Music Charts Intelligence System

**🇬🇧 Looking for the English version?** → [README.md](https://readme.md/)

![WIP](https://img.shields.io/badge/status-WIP-fdd0a2?style=flat-square) 

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Automation](https://img.shields.io/badge/Automation-GitHub_Actions-blue?style=flat-square) ![Web Scraping](https://img.shields.io/badge/Web-Scraping-orange?style=flat-square) ![ETL](https://img.shields.io/badge/ETL-9ecae1?style=flat-square&logo=dataengine&logoColor=white) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square) ![Notebook Generation](https://img.shields.io/badge/Notebook-Generation-blue?style=flat-square) ![AI Insights](https://img.shields.io/badge/AI-Insights-purple?style=flat-square) ![Interactive Dashboards](https://img.shields.io/badge/Interactive_Dashboards-9ecae1?style=flat-square&logo=databricks&logoColor=white)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![Playwright](https://custom-icon-badges.demolab.com/badge/Playwright-2EAD33?logo=playwright&logoColor=white&style=flat-square) ![Selenium](https://img.shields.io/badge/Selenium-43b02a?style=flat-square&logo=selenium&logoColor=white) ![yt-dlp](https://img.shields.io/badge/yt--dlp-FF0000?style=flat-square&logo=youtube&logoColor=white) ![YouTube API](https://img.shields.io/badge/YouTube_API-ff0000?style=flat-square&logo=youtube&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia API](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white) ![Wikidata](https://img.shields.io/badge/Wikidata-990000?style=flat-square&logo=wikidata&logoColor=white) [![DeepSeek](https://custom-icon-badges.demolab.com/badge/DeepSeek-4D6BFF?logo=deepseek&logoColor=white&style=flat-square)](https://deepseek.com) ![Jupyter](https://img.shields.io/badge/Jupyter-f37626?style=flat-square&logo=jupyter&logoColor=white) ![Streamlit](https://img.shields.io/badge/Streamlit-ff4b4b?style=flat-square&logo=streamlit&logoColor=white)

Un pipeline completamente automatizado de extremo a extremo que descarga los charts musicales semanales de YouTube, enriquece cada artista con metadatos geográficos y de género, aumenta cada entrada del chart con metadatos profundos de video de YouTube, y genera notebooks Jupyter con análisis potenciados por IA — todo ejecutándose en GitHub Actions, sin intervención manual.

------

## 📥 Documentación

| Script                                      | Propósito                                                    | Documentación Inglés                                         | Documentación Español                                        |
| :------------------------------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| **1_download.py**                           | Descarga los charts semanales de YouTube (100 canciones) en SQLite | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/1_download.md) · [PDF](https://drive.google.com/file/d/11ANLX6PbK_eIzvHLPqL1rm9NY9rOshhD/view?usp=sharing) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/1_download.md) · [PDF](https://drive.google.com/file/d/1SdLvJnxcKxmQYmLlwoYttHr2Izud4iE5/view?usp=sharing) |
| **2_build_artist_db.py**                    | Enriquece artistas con país + género vía MusicBrainz, Wikipedia, Wikidata | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/2_build_artist_db.md) · [PDF](https://drive.google.com/file/d/1viUAxZ7k-qeYYbyvZf2OaP20AfLOgKh2/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/2_build_artist_db.md) · [PDF](https://drive.google.com/file/d/1WBHBreKeVToTBygSyCuYsHQUr_zSl3BT/view?usp=drive_link) |
| **3_enrich_chart_data.py**                  | Añade metadatos de video de YouTube a cada entrada (sistema de 3 capas) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/3_enrich-chart-data.md) · [PDF](https://drive.google.com/file/d/1XGEx2fRBCpOhU5BfY_YjlKm6zmI41RpB/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/3_enrich-chart-data.md) · [PDF](https://drive.google.com/file/d/1tSFjf_gQQeArdE4n5DLL2I2G_MJW6vE3/view?usp=sharing) |
| **4_1.weekly_charts_notebook_generator.py** | Genera notebooks Jupyter bilingües con insights de IA        | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/4_1.weekly_charts_notebook_generator.md) · PDF | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/4_1.weekly_charts_notebook_generator.md) · PDF |

> El README de cada script contiene análisis detallado del código, opciones de configuración y guías de solución de problemas. Este documento cubre el sistema en su conjunto.

------

## 🗂️ Arquitectura del Sistema

El pipeline procesa datos en cuatro etapas distintas, cada una construyendo sobre la salida de la anterior:

```text
YouTube Charts (web)
        │
        ▼
┌───────────────────┐
│   Script 1        │  → Datos brutos del chart (100 canciones/semana)
│   1_download.py   │    Rank, Track, Artist, Views, URL
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 2        │  → Base de datos de referencia de artistas
│ 2_build_artist_db │    Artista → País + Género
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 3        │  → Entradas de chart completamente enriquecidas
│ 3_enrich_chart_   │    25 campos por canción
│      data.py      │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 4        │  → Notebooks Jupyter bilingües
│ 4_1.weekly_charts │    25+ visualizaciones + insights de IA
│   _notebook_      │    (Inglés y Español)
│   generator.py    │
└───────────────────┘
        │
        ▼
   Listo para Análisis
```

### Flujo de Datos Entre Scripts

| Etapa    | Entrada                                          | Salida                                | Registros                     |
| :------- | :----------------------------------------------- | :------------------------------------ | :---------------------------- |
| Script 1 | Página web de YouTube Charts                     | `youtube_charts_YYYY-WXX.db`          | 100 canciones/semana          |
| Script 2 | Base de datos del Script 1 (nombres de artistas) | `artist_countries_genres.db`          | Crece ~10–50 artistas/semana  |
| Script 3 | DB del Script 1 + DB del Script 2                | `youtube_charts_YYYY-WXX_enriched.db` | 100 filas enriquecidas/semana |
| Script 4 | DB enriquecida del Script 3                      | `Notebook_EN/` + `Notebook_ES/`       | 2 notebooks/semana            |

------

## ⚙️ Programa de Automatización

Los cuatro scripts son orquestados por GitHub Actions y se ejecutan automáticamente cada lunes:

| Workflow                          | Horario (UTC) | Lógica de Disparo       | Timeout |
| :-------------------------------- | :------------ | :---------------------- | :------ |
| `1_download-chart.yml`            | Lunes 12:00   | Cron + manual + push    | 30 min  |
| `2_update-artist-db.yml`          | Lunes 13:00   | Cron + después Script 1 | 60 min  |
| `3_enrich-chart-data.yml`         | Lunes 14:00   | Cron + después Script 2 | 60 min  |
| `4_generate-weekly-notebooks.yml` | Lunes 15:00   | Cron + después Script 3 | 20 min  |

Los intervalos de 1 hora entre cada workflow aseguran que el paso anterior haya terminado antes de que comience el siguiente. Cada workflow commitea su salida directamente de vuelta al repositorio — sin necesidad de almacenamiento externo.

### Línea de Tiempo del Flujo de Ejecución (Lunes)

```text
12:00 UTC ─→ Script 1: Descarga de charts
    ↓
13:00 UTC ─→ Script 2: Enriquecimiento de artistas
    ↓
14:00 UTC ─→ Script 3: Enriquecimiento de charts
    ↓
15:00 UTC ─→ Script 4: Generación de notebooks
    ↓
15:10 UTC ─→ Notebooks ejecutados y commiteados
```

### Secretos Requeridos

| Secreto            | Usado Por | Propósito                                               |
| :----------------- | :-------- | :------------------------------------------------------ |
| `YOUTUBE_API_KEY`  | Script 3  | API de YouTube Data v3 para metadatos de video (Capa 1) |
| `DEEPSEEK_API_KEY` | Script 4  | IA DeepSeek para generar insights en los notebooks      |

Los Scripts 1 y 2 no requieren claves API. El Script 3 funciona sin clave pero cae a métodos más lentos (Selenium, yt-dlp). El Script 4 funciona sin DeepSeek pero muestra texto de marcador de posición en lugar de insights de IA.

------

## 🔬 Cómo Funciona Cada Script

### Script 1 — Descarga de Charts de YouTube

Se ejecuta cada lunes y extrae las 100 canciones principales de YouTube Charts usando Playwright con un navegador Chromium headless. Implementa múltiples estrategias de selectores CSS para encontrar el botón de descarga, oculta las huellas de automatización con cabeceras personalizadas e inyección de JavaScript, y cae a datos de muestra si la interfaz de YouTube cambia.

Cada ejecución semanal produce una nueva base de datos SQLite versionada. Antes de escribir, crea una copia de seguridad temporal del archivo existente para prevenir pérdida de datos. Las bases de datos antiguas se limpian automáticamente según un período de retención configurable (predeterminado: 52 semanas).

**Detalles técnicos clave:**

- Anti-detección: user agent personalizado, `navigator.webdriver` oculto, viewport realista
- 3 selectores de respaldo para el botón de descarga (`#download-button`, `aria-label`, texto)
- Nombrado de respaldos: `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db`
- Datos de respaldo: 100 registros sintéticos con estructura idéntica a los datos reales

------

### Script 2 — Construcción de Base de Datos de Artistas

Toma cada nombre de artista único de la base de datos del Script 1 y lo enriquece con país de origen y género musical primario. Para cada artista, genera hasta 15 variaciones de nombre (eliminando acentos, quitando prefijos, etc.) y los consulta en tres bases de conocimiento externas en orden en cascada.

**Detección de país** utiliza un diccionario curado de más de 30,000 términos geográficos (ciudades, gentilicios, referencias regionales) para extraer señales de ubicación de las respuestas de API. Verifica MusicBrainz primero (estructurado, confiable), luego Wikipedia en inglés (resumen e infobox), luego Wikipedia en idiomas prioritarios (elegidos según script detectado o país conocido), y finalmente Wikidata (propiedades P27 y P19).

**Detección de género** recolecta candidatos de las etiquetas de MusicBrainz y la propiedad P136 de Wikidata, luego aplica un sistema de votación ponderada a través de más de 200 macro-géneros y más de 5,000 mapeos de subgéneros. Se aplican bonificaciones de prioridad específicas por país (ej., K-Pop recibe un multiplicador de 2.0× para artistas de Corea del Sur).

El script nunca sobrescribe datos existentes — solo completa campos faltantes. Esto hace que las re-ejecuciones sean seguras e incrementales.

**Detalles técnicos clave:**

- 15 variaciones de nombre por artista (ej., "The Beatles" → "Beatles", "beatles", etc.)
- Caché en memoria previene llamadas API duplicadas dentro de una sesión
- Detección de script (cirílico, hangul, devanagari, árabe, etc.) guía la selección de idioma de Wikipedia
- Votación ponderada: peso MusicBrainz > peso Wikipedia > peso Wikidata
- Bonificaciones de género específicas por país para más de 50 países

------

### Script 3 — Enriquecimiento de Datos de Charts

Toma la base de datos de charts más reciente del Script 1 y la base de datos de artistas del Script 2 y produce una salida completamente enriquecida con 25 campos por canción. El script técnicamente más complejo del sistema, recupera metadatos de video de YouTube usando una estrategia de 3 capas que siempre intenta el método más rápido primero.

**Capa 1 — API de YouTube Data v3** (0.3–0.8s/video): Recupera duración exacta, conteo de likes, conteo de comentarios, idioma de audio, restricciones regionales y fecha de subida. Se usa cuando hay una clave API válida y queda cuota.

**Capa 2 — Selenium** (3–5s/video): Lanza un navegador Chrome headless y extrae metadatos directamente del reproductor de YouTube. Se usa como respaldo cuando la API no está disponible o la cuota está agotada.

**Capa 3 — yt-dlp** (2–4s/video): Intenta múltiples configuraciones de cliente (Android, iOS, Web) con demoras de reintento para evitar la detección de bots. Se usa como último recurso.

Más allá de los metadatos de video, el script también clasifica cada entrada usando análisis de texto: detecta si un video es oficial, un video lírico, una presentación en vivo o un remix; clasifica el tipo de canal (VEVO, Topic, Label/Studio, Artist Channel); y resuelve país/género para colaboraciones usando un algoritmo de mayoría ponderada.

**Detalles técnicos clave:**

- Mapa de 196 países a continentes para resolver colaboraciones multi-país
- Resolución de colaboraciones: mayoría absoluta (>50%) → mayoría relativa → Multicountry
- Más de 100 jerarquías de género específicas por país para desempates
- Detecta colaboraciones vía patrones regex (feat., ft., &, x, with, con)
- Detección de tipo de canal vía coincidencia de palabras clave
- Temporada de subida (Q1–Q4) derivada de la fecha de subida

------

### Script 4 — Generación de Notebooks con IA

Toma la base de datos enriquecida del Script 3 y genera automáticamente notebooks profesionales de Jupyter con análisis visual completo e insights generados por IA tanto en inglés como en español. El sistema produce dos notebooks completamente ejecutados por semana que contienen **más de 25 visualizaciones**, **12 secciones de análisis** y **comentarios generados por IA** mediante la API de DeepSeek, todo almacenado en caché para evitar llamadas redundantes a la API.

**Secciones del notebook incluyen:**

- Introducción (resumen semanal generado por IA)
- Estadísticas generales (canciones, países, géneros, vistas, likes)
- Análisis por país (distribución geográfica, gráfico circular, gráficos de barras)
- Análisis por género (treemap, tasas de engagement, mapa de calor)
- Métricas de canciones (top canciones por vistas, likes, engagement)
- Métricas de video (rendimiento por tipo de video oficial/lírico/en vivo)
- Análisis temporal (tendencias por trimestre de lanzamiento)
- Análisis de colaboraciones (rendimiento solista vs colaboración)
- Resumen ejecutivo (resumen estratégico de 30 líneas generado por IA)

**Detalles técnicos clave:**

- Más de 25 visualizaciones estáticas usando matplotlib, seaborn y squarify (sin JavaScript)
- Sistema de caché por semana e idioma para insights de IA (basado en hash MD5)
- Retención de ventana deslizante: mantiene solo los últimos 6 notebooks por idioma
- Estilo inspirado en YouTube (#FF0000, #F9F9F9, etc.)
- Cero JavaScript — todos los gráficos compatibles con vista previa de GitHub

------

## 📁 Estructura del Repositorio

```text
Music-Charts-Intelligence/
├── .github/workflows/
│   ├── 1_download-chart.yml
│   ├── 2_update-artist-db.yml
│   ├── 3_enrich-chart-data.yml
│   └── 4_generate-weekly-notebooks.yml
│
├── scripts/
│   ├── 1_download.py
│   ├── 2_build_artist_db.py
│   ├── 3_enrich_chart_data.py
│   └── 4_1.weekly_charts_notebook_generator.py
│
├── charts_archive/
│   ├── 1_download-chart/
│   │   ├── latest_chart.csv              # Chart más reciente (siempre actualizado)
│   │   ├── databases/
│   │   │   ├── youtube_charts_2025-W01.db
│   │   │   ├── youtube_charts_2025-W02.db
│   │   │   └── ...                       # Un archivo por semana
│   │   └── backup/
│   │       └── ...                       # Respaldos temporales pre-actualización
│   │
│   ├── 2_countries-genres-artist/
│   │   └── artist_countries_genres.db    # Base de datos acumulativa de artistas
│   │
│   └── 3_enrich-chart-data/
│       ├── youtube_charts_2025-W01_enriched.db
│       ├── youtube_charts_2025-W02_enriched.db
│       └── ...                           # Una DB enriquecida por semana
│
├── Notebook_EN/                           # Notebooks en inglés (salida Script 4)
│   └── weekly/
│       ├── youtube_charts_2025-W14.ipynb
│       ├── cache/
│       │   └── youtube_charts_2025-W14_en.json
│       └── ...
│
├── Notebook_ES/                           # Notebooks en español (salida Script 4)
│   └── weekly/
│       ├── youtube_charts_2025-W14.ipynb
│       ├── cache/
│       │   └── youtube_charts_2025-W14_es.json
│       └── ...
│
├── Documentation_EN/
│   ├── 1_download.md
│   ├── 2_build_artist_db.md
│   ├── 3_enrich_chart_data.md
│   └── 4_1.weekly_charts_notebook_generator.md
│
├── Documentation_ES/
│   ├── 1_download.md
│   ├── 2_build_artist_db.md
│   ├── 3_enrich_chart_data.md
│   └── 4_1.weekly_charts_notebook_generator.md
│
├── requirements.txt
├── .gitignore
│
├── README.es.md
└── README.md
```

### Política de Retención de Datos

| Dato                                          | Retención                | Configurable                  |
| :-------------------------------------------- | :----------------------- | :---------------------------- |
| Bases de datos semanales de charts (Script 1) | 52 semanas               | `RETENTION_WEEKS` en script   |
| Archivos de respaldo (Script 1)               | 7 días                   | `RETENTION_DAYS` en script    |
| Bases de datos enriquecidas (Script 3)        | 78 semanas               | `RETENTION_WEEKS` en workflow |
| Notebooks (Script 4)                          | 6 más recientes          | `MAX_KEEP` en workflow        |
| Caché de notebooks (Script 4)                 | 6 más recientes          | `MAX_KEEP` en workflow        |
| Base de datos de artistas (Script 2)          | Permanente (acumulativa) | —                             |

------

## 🗄️ Esquemas de Bases de Datos

### Salida del Script 1 — Tabla `chart_data`

| Columna              | Tipo    | Descripción                                   |
| :------------------- | :------ | :-------------------------------------------- |
| `Rank`               | INTEGER | Posición en el chart (1–100)                  |
| `Previous Rank`      | INTEGER | Posición en la semana anterior                |
| `Track Name`         | TEXT    | Título de la canción                          |
| `Artist Names`       | TEXT    | Artista(s), puede incluir colaboraciones      |
| `Periods on Chart`   | INTEGER | Número de semanas en el chart                 |
| `Views`              | INTEGER | Conteo total de vistas                        |
| `Growth`             | TEXT    | Porcentaje de crecimiento semana a semana     |
| `YouTube URL`        | TEXT    | Enlace directo al video                       |
| `download_date`      | TEXT    | Fecha de descarga                             |
| `download_timestamp` | TEXT    | Marca de tiempo completa                      |
| `week_id`            | TEXT    | Identificador ISO de semana (ej., `2025-W11`) |

### Salida del Script 2 — Tabla `artist`

| Columna       | Tipo      | Descripción                 | Ejemplo          |
| :------------ | :-------- | :-------------------------- | :--------------- |
| `name`        | TEXT (PK) | Nombre canónico del artista | `"BTS"`          |
| `country`     | TEXT      | País de origen              | `"South Korea"`  |
| `macro_genre` | TEXT      | Género principal            | `"K-Pop/K-Rock"` |

### Salida del Script 3 — Tabla `enriched_songs` (25 campos)

| Categoría              | Campos                                                       |
| :--------------------- | :----------------------------------------------------------- |
| **Identificadores**    | `rank`, `artist_names`, `track_name`                         |
| **Métricas del Chart** | `periods_on_chart`, `views`, `youtube_url`                   |
| **Metadatos de Video** | `duration_s`, `duration_ms`, `upload_date`, `likes`, `comment_count`, `audio_language` |
| **Flags de Video**     | `is_official_video`, `is_lyric_video`, `is_live_performance`, `is_special_version` |
| **Contexto**           | `upload_season`, `channel_type`, `is_collaboration`, `artist_count`, `region_restricted` |
| **Enriquecimiento**    | `artist_country`, `macro_genre`, `artists_found`             |
| **Control**            | `error`, `processing_date`                                   |

------

## 🚀 Inicio Rápido

### Requisitos Previos

- Python 3.7 o superior (3.12 recomendado)
- Git
- Acceso a Internet
- Clave API de YouTube Data v3 (opcional — solo necesaria para Script 3 Capa 1)
- Clave API de DeepSeek (opcional — solo necesaria para Script 4 insights de IA)

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/adroguetth/Music-Charts-Intelligence
cd Music-Charts-Intelligence

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate       # Linux/Mac
# venv\Scripts\activate        # Windows

# Instalar todas las dependencias
pip install -r requirements.txt

# Instalar navegador Playwright (Script 1 solamente)
python -m playwright install chromium
python -m playwright install-deps  # Linux solamente
```

### Ejecución de los Scripts

```bash
# Paso 1: Descargar los charts de YouTube de esta semana
python scripts/1_download.py

# Paso 2: Enriquecer la base de datos de artistas
python scripts/2_build_artist_db.py

# Paso 3: Enriquecer las entradas del chart con metadatos de YouTube
export YOUTUBE_API_KEY="tu-clave-api"   # Opcional pero recomendado
python scripts/3_enrich_chart_data.py

# Paso 4: Generar notebooks con IA
export DEEPSEEK_API_KEY="tu-clave-api"  # Opcional para insights de IA
python scripts/4_1.weekly_charts_notebook_generator.py
```

Cada script puede ejecutarse independientemente. Los Scripts 2, 3 y 4 dependen de que existan las salidas de los scripts anteriores.

### Variables de Entorno

```bash
# Simular entorno de GitHub Actions (deshabilita prompts interactivos)
export GITHUB_ACTIONS=true

# Clave API de YouTube Data v3 (Script 3, Capa 1)
export YOUTUBE_API_KEY="tu-clave-aqui"

# Clave API de DeepSeek (Script 4, insights de IA)
export DEEPSEEK_API_KEY="tu-clave-aqui"

# Depuración visual de Playwright (Script 1)
export PWDEBUG=1
```

---

## 📊 Ejemplo de Salida

Después de una ejecución completa del pipeline, una salida semanal típica se ve así:

```text
✅ Script 1: YouTube Chart Update 2025-W11 — 100 songs downloaded
✅ Script 2: Artist database updated — 23 new artists enriched (2,346 total)
✅ Script 3: Chart enriched — 100 songs processed in 2m 04s
✅ Script 4: Notebooks generated — EN + ES notebooks with AI insights

📊 Weekly Stats (2025-W11):
   • Distinct countries detected:    28
   • Distinct genres detected:       15
   • Multi-country collaborations:   24 (24.0%)
   • Official music videos:          61 (61.0%)
   • API success rate (Script 3):    98%
```

## 📈 Referencia de Rendimiento

| Script                   | Tiempo Típico | Cuello de Botella                               |
| :----------------------- | :------------ | :---------------------------------------------- |
| Script 1                 | 2–5 minutos   | Carga de página / inicio de Playwright          |
| Script 2                 | 10–30 minutos | Límites de tasa de API (MusicBrainz, Wikipedia) |
| Script 3 (con clave API) | ~2 minutos    | Cuota de API de YouTube                         |
| Script 3 (solo Selenium) | ~5–7 minutos  | Navegador headless por video                    |
| Script 3 (solo yt-dlp)   | ~8–10 minutos | Demoras anti-bot                                |
| Script 4 (con caché)     | ~1–2 minutos  | Ejecución de notebook                           |
| Script 4 (semana nueva)  | ~3–5 minutos  | Llamadas a API de DeepSeek                      |

------

## 🔧 Referencia de Configuración

### Script 1 — `1_download.py`

```python
RETENTION_DAYS = 7        # Días para mantener archivos de respaldo
RETENTION_WEEKS = 52      # Semanas para mantener bases de datos semanales
TIMEOUT = 120000          # Timeout del navegador Playwright (ms)
```

### Script 2 — `2_build_artist_db.py`

```python
MIN_CANDIDATES = 3        # Mínimo de candidatos de género antes de consultar Wikipedia
RETRY_DELAY = 0.5         # Demora entre llamadas API (segundos)
DEFAULT_TIMEOUT = 10      # Timeout de solicitud API (segundos)
```

### Script 3 — `3_enrich_chart_data.py`

```python
SLEEP_BETWEEN_VIDEOS = 0.1    # Pausa entre videos (segundos)
YT_DLP_RETRIES = 5             # Intentos de reintento de yt-dlp
SELENIUM_TIMEOUT = 10          # Timeout de carga de página de Selenium (segundos)
```

### Script 4 — `4_1.weekly_charts_notebook_generator.py`

```python
# Máx tokens para insights de IA
if section in ["introduction", "executive_summary"]:
    max_tokens = 2000  # Aumentado para resumen de 30 líneas
else:
    max_tokens = 600

# Temperatura para creatividad de IA
"temperature": 0.7  # Rango: 0.0 (determinista) a 1.0 (creativo)
```

### Nivel de Workflow (`*.yml`)

```yaml
# Script 1
timeout-minutes: 30

# Script 2
timeout-minutes: 60
env:
  RETENTION_DAYS: 30

# Script 3
timeout-minutes: 60
env:
  RETENTION_WEEKS: 78

# Script 4
timeout-minutes: 20
env:
  MAX_KEEP: 6  # Notebooks a retener por idioma
```

---

## 🧩 Extendiendo el Sistema

### Añadir un Nuevo Delimitador de Artistas (Script 2 y 3)

```python
separators = [
    '&', 'feat.', 'ft.', ',', ' y ', ' and ', ' with ', ' x ', ' vs ',
    ' présente ',      # Francés
    ' und ',           # Alemán
    ' e ', ' com '     # Portugués
]
```

### Añadir un Nuevo Mapeo de Género (Script 2)

```python
# En GENRE_MAPPINGS
'new subgenre name': ('Macro-Genre', 'subgenre')
```

### Añadir una Nueva Jerarquía de Género por País (Script 3)

```python
# En GENRE_HIERARCHY
"Nombre del País": [
    "Género Prioritario 1",   # Seleccionado primero en desempates
    "Género Prioritario 2",
    "Género Prioritario 3"
]
```

### Ajustar Bonificaciones de Género por País (Script 2)

```python
# En COUNTRY_GENRE_PRIORITY
"Nombre del País": [
    "Género Prioritario 1",   # Multiplicador 2.0×
    "Género Prioritario 2",   # Multiplicador 1.5×
    "Género Prioritario 3"    # Multiplicador 1.2×
]
```

## 🐛 Problemas Comunes

| Error                                             | Causa Probable                            | Solución                                                     |
| :------------------------------------------------ | :---------------------------------------- | :----------------------------------------------------------- |
| `Playwright browsers not installed`               | Binario de Chromium faltante              | `python -m playwright install chromium`                      |
| `No chart databases found`                        | El Script 1 no se ha ejecutado            | Ejecutar Script 1 primero                                    |
| `Sign in to confirm you're not a bot`             | yt-dlp bloqueado por YouTube              | Configurar `YOUTUBE_API_KEY`; el script cae a Selenium automáticamente |
| `Quota exceeded`                                  | Límite diario de API de YouTube alcanzado | El script cae automáticamente a Selenium/yt-dlp              |
| `API key not valid`                               | Clave inválida o restringida              | Verificar clave en Google Cloud Console                      |
| `No module named 'isodate'`                       | Dependencia faltante                      | `pip install isodate`                                        |
| `ModuleNotFoundError: No module named 'squarify'` | Librería de treemap faltante              | `pip install squarify`                                       |
| `DeepSeek API key not configured`                 | Secreto faltante para Script 4            | Añadir `DEEPSEEK_API_KEY` a GitHub Secrets o env             |
| Script 3 muy lento (>10 min)                      | Clave API faltante o fallando             | Verificar que `YOUTUBE_API_KEY` esté configurada y sea válida |
| Script 4 muy lento (>5 min)                       | Sin caché, primera ejecución de la semana | Normal; ejecuciones subsiguientes usan caché                 |

Para solución de problemas detallada, ver la documentación individual de cada script enlazada en la tabla al inicio de este README.

------

## 🧪 Limitaciones Conocidas

- **Cambios en la interfaz de YouTube**: Los selectores CSS del Script 1 pueden fallar si YouTube rediseña su página de Charts. Se guardan capturas de pantalla como artefactos en caso de fallo.
- **Cuotas de API**: La API de YouTube Data v3 tiene una cuota diaria de 10,000 unidades. El Script 3 procesa 100 videos por ejecución (~100–200 unidades), por lo que una ejecución usa aproximadamente 1–2% de la cuota diaria.
- **Artistas Emergentes**: El Script 2 depende de MusicBrainz, Wikipedia y Wikidata. Los artistas que debutaron recientemente pueden no tener aún suficientes entradas en estas bases de conocimiento.
- **Colaboraciones Complejas**: Las colaboraciones con más de 5 artistas de diferentes continentes se resuelven como "Multicountry / Multigenre" — la ponderación de contribución individual aún no está implementada.
- **Grupos de K-Pop con miembros extranjeros**: Actualmente asignados a Corea del Sur independientemente de las nacionalidades individuales de los miembros.
- **Soporte de Idiomas**: El Script 4 solo soporta notebooks en inglés y español (otros idiomas requerirían nuevos prompts).

------

## 📄 Licencia y Atribución

**Licencia**: MIT

**Autor**: Alfonso Droguett

- 🔗 [LinkedIn](https://www.linkedin.com/in/adroguetth/)
- 🌐 [Portafolio](https://www.adroguett-portfolio.cl/)
- 📧 adroguett.consultor@gmail.com

**Fuentes de Datos Externas**:

- [MusicBrainz](https://musicbrainz.org/) — Licencia GPL
- [Wikipedia](https://www.wikipedia.org/) — CC BY-SA
- [Wikidata](https://www.wikidata.org/) — CC0
- [YouTube Data API v3](https://developers.google.com/youtube/v3) — Términos de Servicio de Google APIs
- [DeepSeek API](https://deepseek.com/) — API Comercial (solo respaldo)

**Dependencias Clave**:

- Playwright (Apache 2.0) — Automatización de navegador del Script 1
- Selenium (Apache 2.0) — Navegador de respaldo del Script 3
- yt-dlp (Unlicense) — Último recurso del Script 3
- Pandas (BSD 3-Clause) — Procesamiento de datos
- Requests (Apache 2.0) — Llamadas API
- Jupyter (BSD 3-Clause) — Generación de notebooks
- Matplotlib, Seaborn, Squarify — Visualizaciones

------

## 🤝 Contribución

1. **Reportar problemas** con registros completos (incluir la columna `error` de la base de datos de salida cuando sea relevante)
2. **Proponer mejoras** con casos de uso concretos
3. **Añadir mapeos de género** — especialmente para regiones subrepresentadas
4. **Mejorar selectores CSS** para el Script 1 cuando YouTube actualice su interfaz
5. **Mantener compatibilidad hacia atrás** con el esquema de base de datos existente

```bash
# Flujo de contribución estándar
git checkout -b feature/nombre-de-tu-caracteristica
# hacer cambios, probar localmente
git commit -m "Añadir: breve descripción del cambio"
git push origin feature/nombre-de-tu-caracteristica
# abrir un Pull Request
```

---

**⭐ Si este proyecto te resulta útil, ¡considera darle una estrella en GitHub!**
