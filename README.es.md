# 🎵 Sistema de Inteligencia de Charts Musicales
**🇬🇧 Looking for the English version?** → [README.md](README.md)

![WIP](https://img.shields.io/badge/status-WIP-fdd0a2?style=flat-square) 

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Automation](https://img.shields.io/badge/Automation-GitHub_Actions-blue?style=flat-square) ![Web Scraping](https://img.shields.io/badge/Web-Scraping-orange?style=flat-square) ![ETL](https://img.shields.io/badge/ETL-9ecae1?style=flat-square&logo=dataengine&logoColor=white) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square) ![Notebook Generation](https://img.shields.io/badge/Notebook-Generation-blue?style=flat-square) ![AI Insights](https://img.shields.io/badge/AI-Insights-purple?style=flat-square) ![Interactive Dashboards](https://img.shields.io/badge/Interactive_Dashboards-9ecae1?style=flat-square&logo=databricks&logoColor=white)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![Playwright](https://custom-icon-badges.demolab.com/badge/Playwright-2EAD33?logo=playwright&logoColor=white&style=flat-square) ![Selenium](https://img.shields.io/badge/Selenium-43b02a?style=flat-square&logo=selenium&logoColor=white) ![yt-dlp](https://img.shields.io/badge/yt--dlp-FF0000?style=flat-square&logo=youtube&logoColor=white) ![YouTube API](https://img.shields.io/badge/YouTube_API-ff0000?style=flat-square&logo=youtube&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia API](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white) ![Wikidata](https://img.shields.io/badge/Wikidata-990000?style=flat-square&logo=wikidata&logoColor=white) [![DeepSeek](https://custom-icon-badges.demolab.com/badge/DeepSeek-4D6BFF?logo=deepseek&logoColor=white&style=flat-square)](https://deepseek.com) ![Jupyter](https://img.shields.io/badge/Jupyter-f37626?style=flat-square&logo=jupyter&logoColor=white) ![Streamlit](https://img.shields.io/badge/Streamlit-ff4b4b?style=flat-square&logo=streamlit&logoColor=white) ![Google Drive](https://img.shields.io/badge/Google%20Drive-4285F4?style=flat-square&logo=googledrive&logoColor=white) ![OAuth 2.0](https://img.shields.io/badge/OAuth-2.0-3C873A?style=flat-square&logo=oauth&logoColor=white)

Un pipeline completamente automatizado de extremo a extremo que descarga los charts musicales semanales de YouTube, enriquece cada artista con metadatos geográficos y de género, aumenta cada entrada del chart con metadatos detallados del video de YouTube, genera notebooks de Jupyter con inteligencia artificial, y archiva todo en Google Drive — todo ejecutándose en GitHub Actions, sin intervención manual requerida.

## 📁 Archivo en Línea

Todos los notebooks y PDFs exportados están disponibles públicamente en:

🔗 **[Archivo de Charts Musicales - Google Drive](https://drive.google.com/drive/folders/1RpfyGHsIY5MThE1bfe0Rc3gk03WoYzpR)**

| Idioma     | Ruta                   | Contenido         |
| :--------- | :--------------------- | :---------------- |
| 🇬🇧 Inglés  | `/Notebook_EN/weekly/` | `.ipynb` + `.pdf` |
| 🇪🇸 Español | `/Notebook_ES/weekly/` | `.ipynb` + `.pdf` |

> El archivo se actualiza semanalmente cada martes a las 12:00 UTC.

## 📥 Documentación

| Script                                      | Propósito                                                   | Documentación en Inglés                                      | Documentación en Español                                    |
| :------------------------------------------ | :---------------------------------------------------------- | :----------------------------------------------------------- | :---------------------------------------------------------- |
| **1_download.py**                           | Descarga los charts semanales de YouTube (100 canciones) a SQLite | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/1_download.md) · [PDF](https://drive.google.com/file/d/11ANLX6PbK_eIzvHLPqL1rm9NY9rOshhD/view?usp=sharing) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/1_download.md) · [PDF](https://drive.google.com/file/d/1SdLvJnxcKxmQYmLlwoYttHr2Izud4iE5/view?usp=sharing) |
| **2_1.build_artist_db.py**                  | Enriquece artistas con país + género vía MusicBrainz, Wikipedia, Wikidata | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/2_1.build_artist_db.md) · [PDF](https://drive.google.com/file/d/1viUAxZ7k-qeYYbyvZf2OaP20AfLOgKh2/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/2_1.build_artist_db.md) · [PDF](https://drive.google.com/file/d/1WBHBreKeVToTBygSyCuYsHQUr_zSl3BT/view?usp=drive_link) |
| **2_2.build_song_catalog.py**               | Construye catálogo canónico de canciones con país/género resuelto | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/2_2.build_song_catalog.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/2_2.build_song_catalog.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=sharing) |
| **3_enrich_chart_data.py**                  | Añade metadatos de video de YouTube a cada entrada del chart (sistema de 3 capas) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/3_enrich-chart-data.md) · [PDF](https://drive.google.com/file/d/1XGEx2fRBCpOhU5BfY_YjlKm6zmI41RpB/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/3_enrich-chart-data.md) · [PDF](https://drive.google.com/file/d/1tSFjf_gQQeArdE4n5DLL2I2G_MJW6vE3/view?usp=sharing) |
| **4_1.weekly_charts_notebook_generator.py** | Genera notebooks Jupyter bilingües con insights de IA       | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/4_1.weekly_charts_notebook_generator.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/4_1.weekly_charts_notebook_generator.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=sharing) |
| **5_export_notebook_to_pdf.py**             | Exporta notebooks a PDF y sube a Google Drive               | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/5_export_notebook_to_pdf.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/5_export_notebook_to_pdf.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=sharing) |

> El README de cada script contiene análisis detallado del código, opciones de configuración y guías de solución de problemas. Este documento cubre el sistema en su conjunto.

------

## 🗂️ Arquitectura del Sistema

El pipeline procesa datos en cinco etapas distintas, cada una construyendo sobre la salida de la anterior:

```text
YouTube Charts (web)
        │
        ▼
┌───────────────────┐
│   Script 1        │  → Datos brutos del chart (100 canciones/semana)
│   1_download.py   │    Rank, Canción, Artista, Vistas, URL
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 2.1      │  → Base de datos de referencia de artistas
│ build_artist_db   │    Artista → País + Género
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 2.2      │  → Catálogo de canciones (canciones únicas)
│build_song_catalog │    nombre_artista, nombre_canción, país, género
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 3        │  → Entradas de chart completamente enriquecidas
│ 3_enrich_chart_   │    25 campos por canción (incluyendo FK del catálogo)
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
┌───────────────────┐
│   Script 5        │  → Exportación a PDF + archivo en Google Drive
│ 5_export_notebook │    Notebook_EN/ + Notebook_ES/ → Drive
│   _to_pdf.py      │    Carpetas estructuradas: weekly/YYYY-WXX/EN/ES/
└───────────────────┘
        │
        ▼
   Archivado y Listo
```

### Flujo de Datos Entre Scripts

| Etapa      | Entrada                                          | Salida                                       | Registros                     |
| :--------- | :----------------------------------------------- | :------------------------------------------- | :---------------------------- |
| Script 1   | Página web de YouTube Charts                     | `youtube_charts_YYYY-WXX.db`                 | 100 canciones/semana          |
| Script 2.1 | Base de datos del Script 1 (nombres de artistas) | `artist_countries_genres.db`                 | Crece ~10–50 artistas/semana  |
| Script 2.2 | DB del Script 1 + DB del Script 2.1              | `build_song.db` (catálogo canónico)          | Crece ~10–50 canciones/semana |
| Script 3   | DB del Script 1 + catálogo del Script 2.2        | `youtube_charts_YYYY-WXX_enriched.db`        | 100 filas enriquecidas/semana |
| Script 4   | DB enriquecida del Script 3                      | `Notebook_EN/` + `Notebook_ES/` notebooks    | 2 notebooks/semana            |
| Script 5   | Notebooks del Script 4                           | Google Drive (`weekly/YYYY-WXX/EN/` + `ES/`) | PDFs + notebooks originales   |

------

## ⚙️ Programación de la Automatización

Los cinco scripts son orquestados por GitHub Actions y se ejecutan automáticamente cada semana:

| Workflow                            | Horario (UTC) | Lógica de Activación              | Timeout |
| :---------------------------------- | :------------ | :-------------------------------- | :------ |
| `1_download-chart.yml`              | Lunes 12:00   | Cron + manual (push desactivado)  | 30 min  |
| `2_1.update-artist-db.yml`          | Lunes 13:00   | Cron + manual (push desactivado)  | 60 min  |
| `2_2.build-song-catalog.yml`        | Lunes 13:15   | Cron + manual (push desactivado)  | 15 min  |
| `3_enrich-chart-data.yml`           | Lunes 14:00   | Cron + manual (push desactivado)  | 60 min  |
| `4_1.generate-weekly-notebooks.yml` | Lunes 15:00   | Cron + manual (push desactivado)  | 20 min  |
| `5_export-notebook-pdf.yml`         | Martes 12:00  | Cron + manual (sin triggers push) | 20 min  |

> **Nota**: La ejecución automática en `git push` ha sido desactivada para todos los workflows. Los cambios en los scripts no activan los workflows automáticamente. Para probar cambios, use la ejecución manual o espere la próxima ejecución programada.

Los intervalos entre cada workflow aseguran que el paso anterior haya terminado antes de que comience el siguiente. Cada workflow commitea su salida directamente de vuelta al repositorio. El Script 5 se ejecuta el martes para permitir tiempo para revisión manual de los notebooks antes del archivado.

### Línea de Tiempo del Flujo de Ejecución

```text
Lunes 12:00 UTC ─→ Script 1: Descargar charts
        ↓
Lunes 13:00 UTC ─→ Script 2.1: Enriquecimiento de artistas
        ↓
Lunes 13:15 UTC ─→ Script 2.2: Catálogo de canciones
        ↓
Lunes 14:00 UTC ─→ Script 3: Enriquecimiento de charts
        ↓
Lunes 15:00 UTC ─→ Script 4: Generación de notebooks
        ↓
Martes 12:00 UTC ─→ Script 5: Exportar a PDF + Google Drive
```



### Secretos Requeridos

| Secreto                 | Usado Por | Propósito                                              |
| :---------------------- | :-------- | :----------------------------------------------------- |
| `YOUTUBE_API_KEY`       | Script 3  | YouTube Data API v3 para metadatos de video (Capa 1)   |
| `DEEPSEEK_API_KEY`      | Script 4  | DeepSeek AI para generar insights en notebooks         |
| `GDRIVE_CLIENT_ID`      | Script 5  | ID de cliente OAuth 2.0 para API de Google Drive       |
| `GDRIVE_CLIENT_SECRET`  | Script 5  | Secreto de cliente OAuth 2.0 para API de Google Drive  |
| `GDRIVE_REFRESH_TOKEN`  | Script 5  | Token de actualización para acceso persistente a Drive |
| `GDRIVE_ROOT_FOLDER_ID` | Script 5  | ID de la carpeta raíz en Google Drive para archivo     |

Los Scripts 1, 2.1 y 2.2 no requieren claves de API. El Script 3 funciona sin clave pero recurre a métodos más lentos (Selenium, yt-dlp). El Script 4 funciona sin DeepSeek pero muestra texto de marcador de posición en lugar de insights de IA. El Script 5 requiere credenciales OAuth 2.0 (tipo aplicación de escritorio) con la API de Drive habilitada.

------

## 🔬 Cómo Funciona Cada Script

### Script 1 — Descargar Charts de YouTube

Se ejecuta cada lunes y extrae las 100 mejores canciones de YouTube Charts usando Playwright con un navegador Chromium sin interfaz gráfica. Implementa múltiples estrategias de selectores CSS para encontrar el botón de descarga, oculta las huellas de automatización con cabeceras personalizadas e inyección de JavaScript, y recurre a datos de muestra si la interfaz de YouTube cambia.

Cada ejecución semanal produce una nueva base de datos SQLite versionada. Antes de escribir, crea una copia de seguridad temporal del archivo existente para prevenir pérdida de datos. Las bases de datos antiguas se limpian automáticamente según un período de retención configurable (predeterminado: 52 semanas).

**Detalles técnicos clave:**

- Anti-detección: agente de usuario personalizado, `navigator.webdriver` oculto, viewport realista
- 3 selectores alternativos para el botón de descarga (`#download-button`, `aria-label`, texto)
- Nombres de respaldo: `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db`
- Datos de respaldo: 100 registros sintéticos con estructura idéntica a los datos reales

------

### Script 2.1 — Construir Base de Datos de Artistas

Toma cada nombre de artista único de la base de datos del Script 1 y lo enriquece con país de origen y género musical principal. Para cada artista, genera hasta 15 variaciones de nombre (eliminando acentos, quitando prefijos, etc.) y las consulta a través de tres bases de conocimiento externas en orden en cascada.

**Detección de país** utiliza un diccionario curado de más de 30,000 términos geográficos (ciudades, gentilicios, referencias regionales) para extraer señales de ubicación de las respuestas de la API. Verifica MusicBrainz primero (estructurado, confiable), luego Wikipedia en inglés (resumen e infobox), luego Wikipedia en idiomas prioritarios (elegidos según el script detectado o país conocido), y finalmente Wikidata (propiedades P27 y P19).

**Detección de género** recolecta candidatos de las etiquetas de MusicBrainz y la propiedad P136 de Wikidata, luego aplica un sistema de votación ponderada a través de más de 200 macro-géneros y más de 5,000 mapeos de subgéneros. Se aplican bonificaciones de prioridad específicas por país (ej., K-Pop obtiene un multiplicador de 2.0× para artistas de Corea del Sur).

El script nunca sobrescribe datos existentes — solo completa campos faltantes. Esto hace que las re-ejecuciones sean seguras e incrementales.

**Detalles técnicos clave:**

- 15 variaciones de nombre por artista (ej., "The Beatles" → "Beatles", "beatles", etc.)
- Caché en memoria evita llamadas API duplicadas dentro de una sesión
- Detección de escritura (cirílico, hangul, devanagari, árabe, etc.) guía la selección de idioma de Wikipedia
- Votación ponderada: peso de MusicBrainz > peso de Wikipedia > peso de Wikidata
- Bonificaciones de género específicas por país para más de 100 países

------

### Script 2.2 — Construir Catálogo de Canciones

Construye un catálogo canónico de canciones extrayendo pares distintos `(artist_names, track_name)` de la base de datos semanal de charts y resolviendo país y género **una vez por canción única** usando el sistema de ponderación de colaboraciones (movido del Script 3). Esto elimina el procesamiento redundante a través de múltiples apariciones en los charts.

El script carga metadatos de artistas de la base de datos del Script 2.1, aplica el algoritmo de colaboración a pistas con múltiples artistas (mayoría absoluta → mayoría relativa → Multi-country), y mantiene una base de datos SQLite idempotente con claves sustitutas auto-incrementales.

**Detalles técnicos clave:**

- Desduplicación por clave natural: `(artist_names, track_name)`
- Ponderación de colaboraciones: mapa de continentes de 196 países, más de 100 jerarquías de géneros
- Fase 5: repara registros históricos incompletos (rellena país/género faltante)
- Migración de esquema: agrega automáticamente las columnas `artist_country`, `macro_genre`, `artists_found`

------

### Script 3 — Enriquecer Datos de Charts

Toma la base de datos de charts más reciente del Script 1 y el catálogo de canciones del Script 2.2 y produce una salida completamente enriquecida con 25 campos por canción. El script más complejo técnicamente del sistema, recupera metadatos de video de YouTube usando una estrategia de 3 capas que siempre intenta el método más rápido primero.

**Capa 1 — YouTube Data API v3** (0.3–0.8s/video): Recupera duración exacta, cantidad de likes, comentarios, idioma de audio, restricciones regionales y fecha de publicación. Usado cuando hay una clave de API válida y queda cuota.

**Capa 2 — Selenium** (3–5s/video): Lanza un navegador Chrome sin interfaz gráfica y extrae metadatos directamente del reproductor de YouTube. Usado como respaldo cuando la API no está disponible o la cuota está agotada.

**Capa 3 — yt-dlp** (2–4s/video): Prueba múltiples configuraciones de cliente (Android, iOS, Web) con demoras de reintento para evitar la detección de bots. Usado como último recurso.

Más allá de los metadatos de video, el script también clasifica cada entrada usando análisis de texto: detecta si un video es oficial, lyric, una presentación en vivo o un remix; clasifica el tipo de canal (VEVO, Topic, Label/Studio, Artist Channel); y vincula cada canción a su ID de catálogo como clave foránea.

**Detalles técnicos clave:**

- País/género ahora leídos del catálogo de canciones (pre-resueltos por Script 2.2)
- Relación de clave foránea: `enriched_songs.id` referencia `artist_track.id`
- Detecta colaboraciones mediante patrones regex (feat., ft., &, x, with, con)
- Detección de tipo de canal mediante coincidencia de palabras clave
- Temporada de publicación (Q1–Q4) derivada de la fecha de publicación

------

### Script 4 — Generar Notebooks con IA

Toma la base de datos enriquecida del Script 3 y genera automáticamente notebooks profesionales de Jupyter con análisis visual completo e insights generados por IA tanto en inglés como en español. El sistema produce dos notebooks completamente ejecutados por semana que contienen **más de 25 visualizaciones**, **12 secciones de análisis** y **comentarios generados por IA** mediante la API de DeepSeek, todo almacenado en caché para evitar llamadas redundantes a la API.

**Secciones del notebook incluyen:**

- Introducción (resumen semanal generado por IA)
- Estadísticas generales (canciones, países, géneros, vistas, likes)
- Análisis por país (distribución geográfica, gráfico circular, gráficos de barras)
- Análisis por género (treemap, tasas de engagement, mapa de calor)
- Métricas de canciones (mejores canciones por vistas, likes, engagement)
- Métricas de video (rendimiento por tipo de video oficial/lyric/en vivo)
- Análisis temporal (tendencias por trimestre de publicación)
- Análisis de colaboraciones (rendimiento solista vs colaboración)
- Resumen ejecutivo (resumen estratégico de 30 líneas generado por IA)

**Detalles técnicos clave:**

- Más de 25 visualizaciones estáticas usando matplotlib, seaborn y squarify (sin JavaScript)
- Sistema de caché por semana e idioma para insights de IA (basado en hash MD5)
- Retención de ventana deslizante: mantiene solo los últimos 6 notebooks por idioma
- Estilo inspirado en YouTube (#FF0000, #F9F9F9, etc.)
- Cero JavaScript — todos los gráficos compatibles con la vista previa de GitHub

------

### Script 5 — Exportar a PDF + Google Drive

Exporta los notebooks semanales (EN y ES) a PDF usando `nbconvert --to webpdf` con Playwright Chromium (no requiere LaTeX) y sube tanto los notebooks originales como los PDFs a Google Drive para archivo a largo plazo. El script escanea ambos directorios de notebooks, determina la semana más reciente usando comparación de semana ISO (manejando correctamente los límites de año), y organiza los archivos en una jerarquía de carpetas estructurada.

**Detalles técnicos clave:**

- Soporte bilingüe: procesa tanto `Notebook_EN/weekly/` como `Notebook_ES/weekly/`
- Ordenamiento por semana ISO: identifica correctamente la semana más reciente (`2026-W01` > `2025-W52`)
- Organización estructurada en Drive: `weekly/ → youtube_charts_YYYY-WXX/ → EN/ y ES/`
- Autenticación OAuth 2.0 con token de actualización (sin reautenticación manual)
- Subidas idempotentes: crea carpetas solo si no existen

------

## 📁 Estructura del Repositorio

```text
Music-Charts-Intelligence/
├── .github/workflows/
│   ├── 1_download-chart.yml
│   ├── 2_1.update-artist-db.yml
│   ├── 2_2.build-song-catalog.yml
│   ├── 3_enrich-chart-data.yml
│   ├── 4_1.generate-weekly-notebooks.yml
│   └── 5_export-notebook-pdf.yml
│
├── scripts/
│   ├── 1_download.py
│   ├── 2_1.build_artist_db.py                    # Orquestador principal (~120 líneas)
│   ├── 2_2.build_song_catalog.py
│   ├── 3_enrich_chart_data.py
│   ├── 4_1.weekly_charts_notebook_generator.py
│   └── 5_export_notebook_to_pdf.py
│
├── build_artist_db/                              # Paquete modular (Script 2.1)
│   ├── __init__.py                               # Exportaciones de API pública
│   ├── config.py                                 # Rutas, logging, caché, sesiones HTTP
│   ├── country_detector.py                       # Orquestación de búsqueda de país
│   ├── genre_detector.py                         # Búsqueda de género + votación ponderada
│   │
│   ├── dictionaries/                             # Datos estáticos (se pueden actualizar independientemente)
│   │   ├── __init__.py
│   │   ├── countries.py                          # 30,000+ variantes de país → nombres canónicos
│   │   ├── genres.py                             # 5,000+ variantes de género → macro-géneros
│   │   ├── macro_genres.py                       # Lista de todos los 200+ macro-géneros válidos
│   │   ├── country_rules.py                      # Prioridades de género por país + reglas específicas
│   │   └── stopwords.py                          # Palabras a filtrar de la extracción de géneros
│   │
│   ├── utils/                                    # Utilidades reutilizables
│   │   ├── __init__.py
│   │   ├── text_utils.py                         # Normalización, variaciones, detección de escritura
│   │   ├── cache.py                              # Acceso a caché global (re-exportación)
│   │   ├── db_utils.py                           # Creación, lectura, inserción, actualización SQLite
│   │   └── artist_parser.py                      # División de cadenas con múltiples artistas
│   │
│   └── apis/                                     # Clientes de API externas (conectables)
│       ├── __init__.py
│       ├── musicbrainz.py                        # Cliente de API de MusicBrainz
│       ├── wikidata.py                           # Cliente de API de Wikidata
│       ├── wikipedia.py                          # Cliente de API de Wikipedia (infobox + resumen)
│       └── deepseek.py                           # Cliente de IA DeepSeek (fallback)
│
├── charts_archive/
│   ├── 1_download-chart/
│   │   ├── latest_chart.csv
│   │   ├── databases/
│   │   │   ├── youtube_charts_2025-W01.db
│   │   │   ├── youtube_charts_2025-W02.db
│   │   │   └── ...
│   │   └── backup/
│   │
│   ├── 2_1.countries-genres-artist/
│   │   └── artist_countries_genres.db
│   │
│   ├── 2_2.build-song-catalog/
│   │   └── build_song.db
│   │
│   └── 3_enrich-chart-data/
│       ├── youtube_charts_2025-W01_enriched.db
│       ├── youtube_charts_2025-W02_enriched.db
│       └── ...
│
├── Notebook_EN/                                   # Notebooks en inglés (salida del Script 4)
│   └── weekly/
│       ├── youtube_charts_2025-W14.ipynb
│       ├── cache/
│       │   └── youtube_charts_2025-W14_en.json
│       └── ...
│
├── Notebook_ES/                                   # Notebooks en español (salida del Script 4)
│   └── weekly/
│       ├── youtube_charts_2025-W14.ipynb
│       ├── cache/
│       │   └── youtube_charts_2025-W14_es.json
│       └── ...
│
├── Documentation_EN/                              # Documentación en inglés
├── Documentation_ES/                              # Documentación en español
│
├── requirements.txt
├── .gitignore
│
├── README.es.md
└── README.md
```



### Política de Retención de Datos

| Datos                                         | Retención                | Configurable                     |
| :-------------------------------------------- | :----------------------- | :------------------------------- |
| Bases de datos semanales de charts (Script 1) | 52 semanas               | `RETENTION_WEEKS` en el script   |
| Archivos de respaldo (Script 1)               | 7 días                   | `RETENTION_DAYS` en el script    |
| Base de datos de artistas (Script 2.1)        | Permanente (acumulativa) | —                                |
| Catálogo de canciones (Script 2.2)            | Permanente (acumulativa) | —                                |
| Bases de datos enriquecidas (Script 3)        | 78 semanas               | `RETENTION_WEEKS` en el workflow |
| Notebooks (Script 4)                          | 6 más recientes          | `MAX_KEEP` en el workflow        |
| Caché de notebooks (Script 4)                 | 6 más recientes          | `MAX_KEEP` en el workflow        |
| Archivo de Google Drive (Script 5)            | Permanente (cuota 15 GB) | —                                |

------

## 🗄️ Esquemas de Base de Datos

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
| `week_id`            | TEXT    | Identificador de semana ISO (ej., `2025-W11`) |

### Salida del Script 2.1 — Tabla `artist`

| Columna       | Tipo      | Descripción                 | Ejemplo          |
| :------------ | :-------- | :-------------------------- | :--------------- |
| `name`        | TEXT (PK) | Nombre canónico del artista | `"BTS"`          |
| `country`     | TEXT      | País de origen              | `"South Korea"`  |
| `macro_genre` | TEXT      | Género principal            | `"K-Pop/K-Rock"` |

### Salida del Script 2.2 — Tabla `artist_track`

| Columna          | Tipo                              | Descripción                                              | Ejemplo                   |
| :--------------- | :-------------------------------- | :------------------------------------------------------- | :------------------------ |
| `id`             | INTEGER PRIMARY KEY AUTOINCREMENT | Clave sustituta (secuencial)                             | `1`, `2`, `3`...          |
| `artist_names`   | VARCHAR(200) NOT NULL             | Nombre(s) del artista desde el chart                     | `"Bad Bunny"`             |
| `track_name`     | VARCHAR(200) NOT NULL             | Título de la canción                                     | `"DtMF"`                  |
| `artist_country` | TEXT NOT NULL                     | País resuelto (o "Multi-country"/"Unknown")              | `"Puerto Rico"`           |
| `macro_genre`    | TEXT NOT NULL                     | Género resuelto (o "Multi-genre"/"Pop")                  | `"Reggaetón/Trap Latino"` |
| `artists_found`  | TEXT                              | Proporción de artistas coincidentes (coincidentes/total) | `"1/1"` o `"2/3"`         |

### Salida del Script 3 — Tabla `enriched_songs` (25 campos)

| Categoría                | Campos                                                       |
| :----------------------- | :----------------------------------------------------------- |
| **Identificadores**      | `rank`, `id` (FK a `artist_track.id`), `artist_names`, `track_name` |
| **Métricas del Chart**   | `periods_on_chart`, `views`, `youtube_url`                   |
| **Metadatos de Video**   | `duration_s`, `duration_ms`, `upload_date`, `likes`, `comment_count`, `audio_language` |
| **Indicadores de Video** | `is_official_video`, `is_lyric_video`, `is_live_performance` |
| **Contexto**             | `upload_season`, `channel_type`, `is_collaboration`, `artist_count`, `region_restricted` |
| **Enriquecimiento**      | `artist_country`, `macro_genre`, `artists_found` (del catálogo) |
| **Control**              | `error`, `processed_at`                                      |

------

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.7 o superior (3.12 recomendado)
- Git
- Acceso a Internet
- Clave de YouTube Data API v3 (opcional — solo necesaria para la Capa 1 del Script 3)
- Clave de API de DeepSeek (opcional — solo necesaria para los insights de IA del Script 4)
- Proyecto de Google Cloud con API de Drive habilitada + credenciales OAuth 2.0 (opcional — solo necesarias para el Script 5)

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

# Instalar el navegador Playwright (solo Script 1)
python -m playwright install chromium
python -m playwright install-deps  # Solo Linux
```



### Ejecutar los Scripts

```bash
# Paso 1: Descargar los charts de esta semana
python scripts/1_download.py

# Paso 2.1: Enriquecer la base de datos de artistas
python scripts/2_1.build_artist_db.py

# Paso 2.2: Construir el catálogo de canciones
python scripts/2_2.build_song_catalog.py

# Paso 3: Enriquecer las entradas del chart con metadatos de YouTube
export YOUTUBE_API_KEY="tu-clave-api"   # Opcional pero recomendado
python scripts/3_enrich_chart_data.py

# Paso 4: Generar notebooks con IA
export DEEPSEEK_API_KEY="tu-clave-api"  # Opcional para insights de IA
python scripts/4_1.weekly_charts_notebook_generator.py

# Paso 5: Exportar a PDF y subir a Google Drive
export GDRIVE_CLIENT_ID="tu-client-id"
export GDRIVE_CLIENT_SECRET="tu-client-secret"
export GDRIVE_REFRESH_TOKEN="tu-refresh-token"
export GDRIVE_ROOT_FOLDER_ID="tu-folder-id"
python scripts/5_export_notebook_to_pdf.py
```



Cada script se puede ejecutar de forma independiente. Los Scripts 2.1, 2.2, 3, 4 y 5 dependen de que existan las salidas de los scripts anteriores.

### Variables de Entorno

```bash
# Simular entorno de GitHub Actions (desactiva indicaciones interactivas)
export GITHUB_ACTIONS=true

# Clave de YouTube Data API v3 (Script 3, Capa 1)
export YOUTUBE_API_KEY="tu-clave-aqui"

# Clave de API de DeepSeek (Script 4, insights de IA)
export DEEPSEEK_API_KEY="tu-clave-aqui"

# OAuth 2.0 de Google Drive (Script 5)
export GDRIVE_CLIENT_ID="tu-client-id.apps.googleusercontent.com"
export GDRIVE_CLIENT_SECRET="GOCSPX-xxxx"
export GDRIVE_REFRESH_TOKEN="1//0gxxxx"
export GDRIVE_ROOT_FOLDER_ID="1ABCxyz123..."

# Depuración visual de Playwright (Script 1)
export PWDEBUG=1
```



------

## 📊 Ejemplo de Salida

Después de una ejecución completa del pipeline, una salida semanal típica se ve así:

```text
✅ Script 1: Actualización de Chart de YouTube 2025-W11 — 100 canciones descargadas
✅ Script 2.1: Base de datos de artistas actualizada — 23 nuevos artistas enriquecidos (2,346 total)
✅ Script 2.2: Catálogo de canciones actualizado — 15 nuevas canciones agregadas (1,234 total)
✅ Script 3: Chart enriquecido — 100 canciones procesadas en 2m 04s
✅ Script 4: Notebooks generados — Notebooks EN + ES con insights de IA
✅ Script 5: Exportado a Drive — PDFs subidos a weekly/2025-W11/

📊 Estadísticas Semanales (2025-W11):
   • Países distintos detectados:    28
   • Géneros distintos detectados:   15
   • Colaboraciones multi-país:      24 (24.0%)
   • Videos musicales oficiales:     61 (61.0%)
   • Tasa de éxito de API (Script 3):    98%
   • Tasa de enlace al catálogo (Script 3):   97%
```



------

## 📈 Referencia de Rendimiento

| Script                   | Tiempo Típico | Cuello de Botella                               |
| :----------------------- | :------------ | :---------------------------------------------- |
| Script 1                 | 2–5 minutos   | Carga de página / inicio de Playwright          |
| Script 2.1               | 10–30 minutos | Límites de tasa de API (MusicBrainz, Wikipedia) |
| Script 2.2               | 3–8 segundos  | Operaciones SQLite                              |
| Script 3 (con clave API) | ~2 minutos    | Cuota de API de YouTube                         |
| Script 3 (solo Selenium) | ~5–7 minutos  | Navegador sin cabeza por video                  |
| Script 3 (solo yt-dlp)   | ~8–10 minutos | Demoras anti-bot                                |
| Script 4 (con caché)     | ~1–2 minutos  | Ejecución de notebook                           |
| Script 4 (semana nueva)  | ~3–5 minutos  | Llamadas a la API de DeepSeek                   |
| Script 5                 | ~2–4 minutos  | Conversión a PDF + subida a Drive               |

------

## 🔧 Referencia de Configuración

### Script 1 — `1_download.py`

```python
RETENTION_DAYS = 7        # Días para mantener archivos de respaldo
RETENTION_WEEKS = 52      # Semanas para mantener bases de datos semanales
TIMEOUT = 120000          # Tiempo de espera del navegador Playwright (ms)
```



### Script 2.1 — `2_1.build_artist_db.py`

```python
MIN_CANDIDATES = 3        # Mínimo de candidatos de género antes de consultar Wikipedia
RETRY_DELAY = 0.5         # Demora entre llamadas API (segundos)
DEFAULT_TIMEOUT = 10      # Tiempo de espera de solicitud API (segundos)
```



### Script 2.2 — `2_2.build_song_catalog.py`

```python
progress_interval = max(1, total_extracted // 4)  # Intervalos de reporte de progreso
```



### Script 3 — `3_enrich_chart_data.py`

```python
SLEEP_BETWEEN_VIDEOS = 0.1    # Pausa entre videos (segundos)
YT_DLP_RETRIES = 5             # Intentos de reintento para yt-dlp
SELENIUM_TIMEOUT = 10          # Tiempo de espera de carga de página de Selenium (segundos)
```



### Script 4 — `4_1.weekly_charts_notebook_generator.py`

```python
# Máximo de tokens para insights de IA
if section in ["introduction", "executive_summary"]:
    max_tokens = 2000  # Para resumen de 30 líneas
else:
    max_tokens = 600

# Temperatura para creatividad de IA
"temperature": 0.7  # Rango: 0.0 (determinista) a 1.0 (creativo)
```



### Script 5 — `5_export_notebook_to_pdf.py`

```python
NOTEBOOKS_EN_DIR = Path("Notebook_EN/weekly")
NOTEBOOKS_ES_DIR = Path("Notebook_ES/weekly")
TEMP_PDF_DIR = Path("temp_pdf")  # Almacenamiento temporal para PDFs
```



### Nivel de workflow (archivos `*.yml`)

```yaml
# Script 1
timeout-minutes: 30

# Script 2.1
timeout-minutes: 60
env:
  RETENTION_DAYS: 30

# Script 2.2
timeout-minutes: 15

# Script 3
timeout-minutes: 60
env:
  RETENTION_WEEKS: 78

# Script 4
timeout-minutes: 20
env:
  MAX_KEEP: 6  # Notebooks a retener por idioma

# Script 5
timeout-minutes: 20
env:
  RETENTION_DAYS: 30
```



------

## 🧩 Extendiendo el Sistema

### Agregar un Nuevo Delimitador de Artistas (Scripts 2.1, 2.2, 3)

```python
separators = [
    '&', 'feat.', 'ft.', ',', ' y ', ' and ', ' with ', ' x ', ' vs ',
    ' présente ',      # Francés
    ' und ',           # Alemán
    ' e ', ' com '     # Portugués
]
```



### Agregar un Nuevo Mapeo de Género (Script 2.1)

```python
# En GENRE_MAPPINGS
'nuevo nombre de subgénero': ('Macro-Género', 'subgénero')
```



### Agregar una Nueva Jerarquía de Género por País (Script 2.2)

```python
# En GENRE_HIERARCHY
"Nombre del País": [
    "Género Prioritario 1",   # Seleccionado primero en desempates
    "Género Prioritario 2",
    "Género Prioritario 3"
]
```



### Ajustar Bonificaciones de Género por País (Script 2.1)

```python
# En COUNTRY_GENRE_PRIORITY
"Nombre del País": [
    "Género Prioritario 1",   # Multiplicador 2.0×
    "Género Prioritario 2",   # Multiplicador 1.5×
    "Género Prioritario 3"    # Multiplicador 1.2×
]
```



### Agregar una Nueva Sección de Análisis (Script 4)

1. Agregar título de sección en `get_section_titles()`
2. Agregar prompt en `get_ai_insight()` (inglés y español)
3. Agregar resumen de datos en `get_data_summaries()`
4. Agregar celda de código en `generate_notebook()`
5. Agregar a la lista `sections` en la ejecución principal

------

## 🐛 Problemas Comunes

| Error                                             | Causa Probable                            | Solución                                                     |
| :------------------------------------------------ | :---------------------------------------- | :----------------------------------------------------------- |
| `Playwright browsers not installed`               | Binario de Chromium faltante              | `python -m playwright install chromium`                      |
| `No chart databases found`                        | El Script 1 no se ha ejecutado            | Ejecutar el Script 1 primero                                 |
| `Sign in to confirm you're not a bot`             | YouTube bloquea yt-dlp                    | Configurar `YOUTUBE_API_KEY`; el script recurre a Selenium   |
| `Quota exceeded`                                  | Límite diario de API de YouTube alcanzado | El script recurre automáticamente a Selenium/yt-dlp          |
| `API key not valid`                               | Clave inválida o restringida              | Verificar la clave en Google Cloud Console                   |
| `No module named 'isodate'`                       | Dependencia faltante                      | `pip install isodate`                                        |
| `ModuleNotFoundError: No module named 'squarify'` | Biblioteca de treemap faltante            | `pip install squarify`                                       |
| `DeepSeek API key not configured`                 | Secreto faltante para Script 4            | Agregar `DEEPSEEK_API_KEY` a los Secretos de GitHub o env    |
| `HttpError 403: storageQuotaExceeded`             | La cuenta de servicio no tiene cuota      | Usar OAuth 2.0 con cuenta personal de Google (Script 5)      |
| `Invalid refresh token`                           | Token expirado o revocado                 | Re-ejecutar `generate_refresh_token.py` para Script 5        |
| Script 3 muy lento (>10 min)                      | Clave de API faltante o fallando          | Verificar que `YOUTUBE_API_KEY` esté configurada y sea válida |
| Script 4 muy lento (>5 min)                       | Sin caché, primera ejecución de la semana | Normal; las ejecuciones posteriores usan caché               |

Para solución de problemas detallada, consulte la documentación de cada script enlazada en la tabla al principio de este README.

------

## 🧪 Limitaciones Conocidas

- **Cambios en la Interfaz de YouTube**: Los selectores CSS del Script 1 pueden fallar si YouTube rediseña su página de Charts. Se guardan capturas de pantalla como artefactos en caso de fallo.
- **Cuotas de API**: La API de YouTube Data v3 tiene una cuota diaria de 10,000 unidades. El Script 3 procesa 100 videos por ejecución (~100–200 unidades), por lo que una sola ejecución usa aproximadamente el 1–2% de la cuota diaria.
- **Artistas Emergentes**: El Script 2.1 depende de MusicBrainz, Wikipedia y Wikidata. Los artistas que debutaron recientemente pueden no tener aún suficientes entradas en estas bases de conocimiento.
- **Colaboraciones Complejas**: Las colaboraciones con 5+ artistas de diferentes continentes se resuelven como "Multi-country / Multi-genre" — aún no se implementa la ponderación de contribución individual.
- **Grupos de K-Pop con Miembros Extranjeros**: Actualmente asignados a Corea del Sur independientemente de las nacionalidades de los miembros individuales.
- **Soporte de Idiomas**: El Script 4 solo soporta notebooks en inglés y español (otros idiomas requerirían nuevos prompts).
- **Cuota de Google Drive**: El Script 5 usa OAuth 2.0 con una cuenta personal de Google (15 GB gratis). Las cuentas de servicio no tienen cuota de almacenamiento y no pueden subir a unidades personales.

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
- yt-dlp (Unlicense) — Metadatos de último recurso del Script 3
- Pandas (BSD 3-Clause) — Procesamiento de datos
- Requests (Apache 2.0) — Llamadas a API
- Jupyter (BSD 3-Clause) — Generación de notebooks
- Matplotlib, Seaborn, Squarify — Visualizaciones
- Google API Client (Apache 2.0) — Subida a Drive del Script 5

------

## 🤝 Contribución

1. **Reportar problemas** con registros completos (incluya la columna `error` de la base de datos de salida cuando sea relevante)
2. **Proponer mejoras** con casos de uso concretos
3. **Agregar mapeos de géneros** — especialmente para regiones subrepresentadas
4. **Mejorar los selectores CSS** para el Script 1 cuando YouTube actualice su interfaz
5. **Mantener la compatibilidad hacia atrás** con el esquema de base de datos existente

```bash
# Flujo de contribución estándar
git checkout -b feature/nombre-de-tu-caracteristica
# hacer cambios, probar localmente
git commit -m "Add: breve descripción del cambio"
git push origin feature/nombre-de-tu-caracteristica
# abrir un Pull Request
```



------

**⭐ Si encuentras útil este proyecto, ¡considera darle una estrella en GitHub!**
