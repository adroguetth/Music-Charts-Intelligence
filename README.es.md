# 🎵 Sistema de Inteligencia de Music Charts
![MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square) ![Automation](https://img.shields.io/badge/Automation-GitHub_Actions-blue?style=flat-square) ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white) ![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white) ![yt-dlp](https://img.shields.io/badge/yt--dlp-FF6F61?style=flat-square&logo=youtube&logoColor=white) ![YouTube API](https://img.shields.io/badge/YouTube_API-FF0000?style=flat-square&logo=youtube&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white)

Un pipeline completamente automatizado de principio a fin que descarga los charts musicales semanales de YouTube, enriquece cada artista con metadatos geográficos y de género, y luego aumenta cada entrada del chart con metadatos profundos de video de YouTube — todo ejecutándose en GitHub Actions, sin intervención manual requerida.

## 📥 Documentación

| Script                     | Propósito                                                    | Docs Inglés                                                  | Docs Español                                                 |
| :------------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| **1_download.py**          | Descarga charts semanales de YouTube (100 canciones) a SQLite | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/1_download.md) · [PDF](https://drive.google.com/file/d/11ANLX6PbK_eIzvHLPqL1rm9NY9rOshhD/view?usp=sharing) | README · [PDF](https://drive.google.com/file/d/1SdLvJnxcKxmQYmLlwoYttHr2Izud4iE5/view?usp=sharing) |
| **2_build_artist_db.py**   | Enriquece artistas con país + género vía MusicBrainz, Wikipedia, Wikidata | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/2_build_artist_db.md) · [PDF](https://drive.google.com/file/d/1viUAxZ7k-qeYYbyvZf2OaP20AfLOgKh2/view?usp=drive_link) | README · [PDF](https://drive.google.com/file/d/1WBHBreKeVToTBygSyCuYsHQUr_zSl3BT/view?usp=drive_link) |
| **3_enrich_chart_data.py** | Agrega metadatos de video YouTube a cada entrada (sistema de 3 capas) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/3_enrich-chart-data.md) · [PDF](https://drive.google.com/file/d/1XGEx2fRBCpOhU5BfY_YjlKm6zmI41RpB/view?usp=drive_link)                                             | README · [PDF](https://drive.google.com/file/d/1tSFjf_gQQeArdE4n5DLL2I2G_MJW6vE3/view?usp=sharing)                                                              |

> El README de cada script contiene análisis detallado del código, opciones de configuración y guías de solución de problemas. Este documento cubre el sistema en su conjunto.

## 🗂️ Arquitectura del Sistema

El pipeline procesa datos en tres etapas distintas, cada una construyendo sobre la salida de la anterior:
```text
YouTube Charts (web)
        │
        ▼
┌───────────────────┐
│   Script 1        │  → Datos crudos del chart (100 canciones/semana)
│   1_download.py   │    Rank, Canción, Artista, Vistas, URL
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
   Base de Datos SQLite
   (lista para análisis)
```
### Flujo de Datos entre Scripts

| Etapa    | Entrada                                   | Salida                                | Registros                     |
| :------- | :---------------------------------------- | :------------------------------------ | :---------------------------- |
| Script 1 | Página web YouTube Charts                 | `youtube_charts_YYYY-WXX.db`          | 100 canciones/semana          |
| Script 2 | Base de datos Script 1 (nombres artistas) | `artist_countries_genres.db`          | Crece ~10–50 artistas/semana  |
| Script 3 | DB Script 1 + DB Script 2                 | `youtube_charts_YYYY-WXX_enriched.db` | 100 filas enriquecidas/semana |

# ⚙️ Programación de Automatización

Los tres scripts son orquestados por GitHub Actions y se ejecutan automáticamente cada lunes:

| Workflow                  | Horario (UTC) | Lógica de Disparo       | Timeout |
| :------------------------ | :------------ | :---------------------- | :------ |
| `1_download-chart.yml`    | Lunes 12:00   | Cron + manual + push    | 30 min  |
| `2_update-artist-db.yml`  | Lunes 13:00   | Cron + después Script 1 | 60 min  |
| `3_enrich-chart-data.yml` | Lunes 14:00   | Cron + después Script 2 | 60 min  |

Los espacios de 1 hora entre cada workflow aseguran que el paso anterior haya terminado antes de que comience el siguiente. Cada workflow guarda su salida directamente en el repositorio — no se necesita almacenamiento externo.

### Secretos Requeridos

| Secreto           | Usado Por | Propósito                                               |
| :---------------- | :-------- | :------------------------------------------------------ |
| `YOUTUBE_API_KEY` | Script 3  | API de YouTube Data v3 para metadatos de video (Capa 1) |

Los Scripts 1 y 2 no requieren claves API. El Script 3 funciona sin clave pero recurre a métodos más lentos (Selenium, yt-dlp).

## 🔬 Cómo Funciona Cada Script

### Script 1 — Descargar YouTube Charts

Se ejecuta cada lunes y extrae las 100 canciones principales de YouTube Charts usando Playwright con un navegador Chromium headless. Implementa múltiples estrategias de selectores CSS para encontrar el botón de descarga, oculta huellas de automatización con headers personalizados e inyección de JavaScript, y recurre a datos de muestra si la interfaz de YouTube cambia.

Cada ejecución semanal produce una nueva base de datos SQLite versionada. Antes de escribir, crea una copia de seguridad temporal del archivo existente para evitar pérdida de datos. Las bases antiguas se limpian automáticamente según un período de retención configurable (por defecto: 52 semanas).

**Detalles técnicos clave:**

- Anti-detección: user agent personalizado, `navigator.webdriver` oculto, viewport realista
- 3 selectores de respaldo para el botón de descarga (`#download-button`, `aria-label`, texto)
- Nombrado de backup: `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db`
- Datos de respaldo: 100 registros sintéticos con estructura idéntica a los datos reales

### Script 2 — Construir Base de Datos de Artistas

Toma cada nombre de artista único de la base de datos del Script 1 y lo enriquece con país de origen y género musical principal. Para cada artista, genera hasta 15 variaciones de nombre (eliminando acentos, quitando prefijos, etc.) y las consulta en tres bases de conocimiento externas en orden en cascada.

**Detección de país** usa un diccionario curado de más de 30,000 términos geográficos (ciudades, gentilicios, referencias regionales) para extraer señales de ubicación de las respuestas de API. Primero verifica MusicBrainz (estructurado, confiable), luego Wikipedia en inglés (resumen e infobox), luego Wikipedia en idiomas prioritarios (elegidos según escritura detectada o país conocido), y finalmente Wikidata (propiedades P27 y P19).

**Detección de género** recopila candidatos de etiquetas de MusicBrainz y la propiedad P136 de Wikidata, luego aplica un sistema de votación ponderada a través de más de 200 macro-géneros y más de 5,000 mapeos de subgéneros. Se aplican bonificaciones de prioridad específicas por país (ej., K-Pop obtiene un multiplicador 2.0× para artistas surcoreanos).

El script nunca sobrescribe datos existentes — solo completa campos faltantes. Esto hace que las re-ejecuciones sean seguras e incrementales.

**Detalles técnicos clave:**

- 15 variaciones de nombre por artista (ej., "The Beatles" → "Beatles", "beatles", etc.)
- Caché en memoria evita llamadas API duplicadas dentro de una sesión
- Detección de escritura (cirílico, hangul, devanagari, árabe, etc.) guía selección de idioma de Wikipedia
- Votación ponderada: peso MusicBrainz > peso Wikipedia > peso Wikidata
- Bonificaciones de género específicas por país para más de 50 países

### Script 3 — Enriquecer Datos del Chart

Toma la base de datos de charts más reciente del Script 1 y la base de datos de artistas del Script 2 y produce una salida completamente enriquecida con 25 campos por canción. El script más técnicamente complejo del sistema, recupera metadatos de video de YouTube usando una estrategia de 3 capas que siempre intenta el método más rápido primero.

**Capa 1 — API de YouTube Data v3** (0.3–0.8s/video): Recupera duración exacta, número de likes, número de comentarios, idioma de audio, restricciones regionales y fecha de subida. Se usa cuando hay una clave API válida disponible y queda cuota.

**Capa 2 — Selenium** (3–5s/video): Lanza un navegador Chrome headless y extrae metadatos directamente del reproductor de YouTube. Se usa como respaldo cuando la API no está disponible o la cuota está agotada.

**Capa 3 — yt-dlp** (2–4s/video): Prueba múltiples configuraciones de cliente (Android, iOS, Web) con retardos de reintento para evitar detección de bot. Se usa como último recurso.

Más allá de los metadatos de video, el script también clasifica cada entrada usando análisis de texto: detecta si un video es oficial, lyric video, actuación en vivo o remix; clasifica el tipo de canal (VEVO, Topic, Label/Studio, Artist Channel); y resuelve país/género para colaboraciones usando un algoritmo de mayoría ponderada.

**Detalles técnicos clave:**

- Mapa de continentes de 196 países para resolver colaboraciones multi-país
- Resolución de colaboraciones: mayoría absoluta (>50%) → mayoría relativa → Multipaís
- Más de 100 jerarquías de géneros específicas por país para desempates
- Detecta colaboraciones vía patrones regex (feat., ft., &, x, with, con)
- Detección de tipo de canal mediante coincidencia de palabras clave
- Temporada de subida (Q1–Q4) derivada de la fecha de subida

## 📁 Estructura del Repositorio

~~~text
Music-Charts-Intelligence/
├── .github/workflows/
│   ├── 1_download-chart.yml
│   ├── 2_update-artist-db.yml
│   └── 3_enrich-chart-data.yml
│
├── scripts/
│   ├── 1_download.py
│   ├── 2_build_artist_db.py
│   └── 3_enrich_chart_data.py
│
├── charts_archive/
│   ├── 1_download-chart/
│   │   ├── latest_chart.csv              # Chart más reciente (siempre actualizado)
│   │   ├── databases/
│   │   │   ├── youtube_charts_2025-W01.db
│   │   │   ├── youtube_charts_2025-W02.db
│   │   │   └── ...                       # Un archivo por semana
│   │   └── backup/
│   │       └── ...                       # Backups temporales pre-actualización
│   │
│   ├── 2_countries-genres-artist/
│   │   └── artist_countries_genres.db    # Base de datos acumulativa de artistas
│   │
│   └── 3_enrich-chart-data/
│       ├── youtube_charts_2025-W01_enriched.db
│       ├── youtube_charts_2025-W02_enriched.db
│       └── ...                           # Una base enriquecida por semana
│
├── Documentation_EN/
│   ├── 1_download.md
│   ├── 2_build_artist_db.md
│   └── 3_enrich_chart_data.md
│
├── Documentation_ES/
│   ├── 1_download.md
│   ├── 2_build_artist_db.md
│   └── 3_enrich_chart_data.md
│
├── requirements.txt
├── .gitignore
│
├── README.es.md
└── README.md
~~~

### Política de Retención de Datos

| Datos                                         | Retención                | Configurable                  |
| :-------------------------------------------- | :----------------------- | :---------------------------- |
| Bases de datos semanales de charts (Script 1) | 52 semanas               | `RETENTION_WEEKS` en script   |
| Archivos de backup (Script 1)                 | 7 días                   | `RETENTION_DAYS` en script    |
| Bases de datos enriquecidas (Script 3)        | 78 semanas               | `RETENTION_WEEKS` en workflow |
| Base de datos de artistas (Script 2)          | Permanente (acumulativa) | —                             |

## 🗄️ Esquemas de Base de Datos

### Salida Script 1 — Tabla `chart_data`

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

### Salida Script 2 — Tabla `artist`

| Columna       | Tipo      | Descripción                 | Ejemplo          |
| :------------ | :-------- | :-------------------------- | :--------------- |
| `name`        | TEXT (PK) | Nombre canónico del artista | `"BTS"`          |
| `country`     | TEXT      | País de origen              | `"South Korea"`  |
| `macro_genre` | TEXT      | Género principal            | `"K-Pop/K-Rock"` |

### Salida Script 3 — Tabla `enriched_songs` (25 campos)

| Categoría           | Campos                                                       |
| :------------------ | :----------------------------------------------------------- |
| **Identificadores** | `rank`, `artist_names`, `track_name`                         |
| **Métricas Chart**  | `periods_on_chart`, `views`, `youtube_url`                   |
| **Metadatos Video** | `duration_s`, `duration_ms`, `upload_date`, `likes`, `comment_count`, `audio_language` |
| **Flags Video**     | `is_official_video`, `is_lyric_video`, `is_live_performance`, `is_special_version` |
| **Contexto**        | `upload_season`, `channel_type`, `is_collaboration`, `artist_count`, `region_restricted` |
| **Enriquecimiento** | `artist_country`, `macro_genre`, `artists_found`             |
| **Control**         | `error`, `processing_date`                                   |

## 🚀 Inicio Rápido

### Requisitos Previos

- Python 3.7 o superior (3.12 recomendado)
- Git
- Acceso a internet
- Clave de API de YouTube Data v3 (opcional — solo necesaria para Script 3 Capa 1)

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
 
# Instalar navegador Playwright (solo Script 1)
python -m playwright install chromium
python -m playwright install-deps  # Solo Linux
```

### Ejecutar los Scripts

```bash
# Paso 1: Descargar los YouTube Charts de esta semana
python scripts/1_download.py
 
# Paso 2: Enriquecer la base de datos de artistas
python scripts/2_build_artist_db.py
 
# Paso 3: Enriquecer entradas del chart con metadatos de YouTube
export YOUTUBE_API_KEY="tu-clave-api"   # Opcional pero recomendado
python scripts/3_enrich_chart_data.py
```

Cada script puede ejecutarse independientemente. Los Scripts 2 y 3 dependen de que exista la salida del Script 1, y el Script 3 también usa la base de datos de artistas del Script 2 si está disponible.

### Variables de Entorno

```bash
# Simular entorno de GitHub Actions (desactiva indicaciones interactivas)
export GITHUB_ACTIONS=true
 
# Clave de API de YouTube Data v3 (Script 3, Capa 1)
export YOUTUBE_API_KEY="tu-clave-aquí"
 
# Depuración visual de Playwright (Script 1)
export PWDEBUG=1
```

## 📊 Ejemplo de Salida

Después de una ejecución completa del pipeline, una salida semanal típica se ve así:

```text
✅ Script 1: Actualización Chart YouTube 2025-W11 — 100 canciones descargadas
✅ Script 2: Base de datos de artistas actualizada — 23 nuevos artistas enriquecidos (2,346 total)
✅ Script 3: Chart enriquecido — 100 canciones procesadas en 2m 04s
 
📊 Estadísticas Semanales (2025-W11):
   • Países distintos detectados:    28
   • Géneros distintos detectados:    15
   • Colaboraciones multi-país:   24 (24.0%)
   • Videos musicales oficiales:   61 (61.0%)
   • Tasa éxito API (Script 3):    98%
```

## 📈 Referencia de Rendimiento

| Script                   | Tiempo Típico | Cuello de Botella                            |
| :----------------------- | :------------ | :------------------------------------------- |
| Script 1                 | 2–5 minutos   | Carga de página / inicio Playwright          |
| Script 2                 | 10–30 minutos | Límites de tasa API (MusicBrainz, Wikipedia) |
| Script 3 (con clave API) | ~2 minutos    | Cuota API YouTube                            |
| Script 3 (solo Selenium) | ~5–7 minutos  | Navegador headless por video                 |
| Script 3 (solo yt-dlp)   | ~8–10 minutos | Retardos anti-bot                            |

## 🔧 Referencia de Configuración

### Script 1 — `1_download.py`

```python
RETENTION_DAYS = 7        # Días para mantener archivos de backup
RETENTION_WEEKS = 52      # Semanas para mantener bases de datos semanales
TIMEOUT = 120000          # Timeout del navegador Playwright (ms)
```

### Script 2 — `2_build_artist_db.py`

```python
MIN_CANDIDATES = 3        # Mínimo candidatos de género antes de consultar Wikipedia
RETRY_DELAY = 0.5         # Retardo entre llamadas API (segundos)
DEFAULT_TIMEOUT = 10      # Timeout de solicitud API (segundos)
```

### Script 3 — `3_enrich_chart_data.py`

```python
SLEEP_BETWEEN_VIDEOS = 0.1    # Pausa entre videos (segundos)
YT_DLP_RETRIES = 5            # Intentos de reintento yt-dlp
SELENIUM_TIMEOUT = 10         # Timeout de carga de página Selenium (segundos)
```

### Nivel de Workflow (`*.yml` archivos)

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
```

## 🧩 Extendiendo el Sistema

### Añadir un Nuevo Delimitador de Artista (Script 2 y 3)

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
'nombre nuevo subgénero': ('Macro-Género', 'subgénero')
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

## 🐛 Problemas Comunes

| Error                                 | Causa Probable                      | Solución                                                     |
| :------------------------------------ | :---------------------------------- | :----------------------------------------------------------- |
| `Playwright browsers not installed`   | Falta binario Chromium              | `python -m playwright install chromium`                      |
| `No chart databases found`            | Script 1 aún no se ha ejecutado     | Ejecutar Script 1 primero                                    |
| `Sign in to confirm you're not a bot` | yt-dlp bloqueado por YouTube        | Configurar `YOUTUBE_API_KEY`; el script recurre automáticamente a Selenium |
| `Quota exceeded`                      | Límite diario API YouTube alcanzado | El script recurre automáticamente a Selenium/yt-dlp          |
| `API key not valid`                   | Clave inválida o restringida        | Verificar clave en Google Cloud Console                      |
| `No module named 'isodate'`           | Dependencia faltante                | `pip install isodate`                                        |
| Script 3 muy lento (>10 min)          | Clave API faltante o fallando       | Verificar que `YOUTUBE_API_KEY` esté configurada y sea válida |

Para solución de problemas detallada, consulta la documentación individual de cada script enlazada en la tabla al inicio de este README.

## 🧪 Limitaciones Conocidas

- **Cambios en Interfaz de YouTube**: Los selectores CSS del Script 1 pueden romperse si YouTube rediseña su página de Charts. Se guardan capturas de pantalla como artefactos en caso de fallo.
- **Cuotas de API**: La API de YouTube Data v3 tiene una cuota diaria de 10,000 unidades. El Script 3 procesa 100 videos por ejecución (~100–200 unidades), por lo que una sola ejecución usa aproximadamente 1–2% de la cuota diaria.
- **Artistas Emergentes**: El Script 2 depende de MusicBrainz, Wikipedia y Wikidata. Artistas que debutaron recientemente pueden no tener aún suficientes entradas en estas bases de conocimiento.
- **Colaboraciones Complejas**: Colaboraciones con 5+ artistas de diferentes continentes se resuelven como "Multipaís / Multigénero" — la ponderación de contribución individual aún no está implementada.
- **Grupos K-Pop con Miembros Extranjeros**: Actualmente asignados a Corea del Sur independientemente de las nacionalidades individuales de los miembros.

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

**Dependencias Clave**:

- Playwright (Apache 2.0) — Automatización de navegador Script 1
- Selenium (Apache 2.0) — Navegador de respaldo Script 3
- yt-dlp (Unlicense) — Metadatos de último recurso Script 3
- Pandas (BSD 3-Clause) — Procesamiento de datos
- Requests (Apache 2.0) — Llamadas API

## 🤝 Contribuciones

1. **Reportar problemas** con logs completos (incluir la columna `error` de la base de datos de salida cuando sea relevante)
2. **Proponer mejoras** con casos de uso concretos
3. **Añadir mapeos de género** — especialmente para regiones subrepresentadas
4. **Mejorar selectores CSS** para el Script 1 cuando YouTube actualice su interfaz
5. **Mantener compatibilidad hacia atrás** con el esquema de base de datos existente

```bash
# Flujo de contribución estándar
git checkout -b feature/nombre-de-tu-funcionalidad
# hacer cambios, probar localmente
git commit -m "Añade: breve descripción del cambio"
git push origin feature/nombre-de-tu-funcionalidad
# abrir un Pull Request
```

---

**⭐ Si encuentras útil este proyecto, ¡considera darle una estrella en GitHub!**
