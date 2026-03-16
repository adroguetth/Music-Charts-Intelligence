
### Características Principales

- **Sistema de Obtención de 3 Capas**: API de YouTube (prioritaria) → Selenium → yt-dlp (último recurso) para máxima fiabilidad
- **Rendimiento Optimizado**: Procesamiento de 100 canciones en ~2 minutos usando API de YouTube (vs 8+ minutos con yt-dlp puro)
- **Sistema de Pesos para Colaboraciones**: Algoritmo inteligente que determina país y género cuando hay múltiples artistas
- **Jerarquías Culturales por País**: Listas ordenadas de géneros que reflejan la importancia local (ej. K-Pop primero en Corea)
- **Detección de Metadatos de Video**: Identifica si es oficial, lyric video, live performance, remix, etc.
- **Clasificación de Canales**: Detecta VEVO, Topic, Label/Studio, Artist Channel y más
- **Actualización Automática**: Selecciona la base de charts más reciente y genera su versión enriquecida
- **Optimizado para CI/CD**: Diseñado específicamente para ejecutarse en GitHub Actions sin intervención manual

### Diagrama n°1: Flujo de ejecución 

![Diagrama del pipeline](https://drive.google.com/uc?export=view&id=1u7jAa0QWfCIRCLHqKNac_srTz--6qXUo)

Este diagrama muestra el el flujo de ejecución:

- **Entrada**: Busca automáticamente la base de datos más reciente en `charts_archive/1_download-chart/databases/` (orden lexicográfico inverso → `youtube_charts_2026-W11.db`)

- **Descarga de Datos de Artistas**: Obtiene `artist_countries_genres.db` desde GitHub (archivo temporal) y carga en memoria un diccionario `{nombre_normalizado: (país, género)}`

- **Lectura de Canciones**: Conecta con la base de charts y lee las 100 canciones de la tabla `chart_data` (columnas: Rank, Artist Names, Track Name, YouTube URL, etc.)

- **Preparación de Salida**: Crea la tabla `canciones_enriquecidas` en la base de salida (`charts_archive/3_enrich-chart-data/{nombre}_enriched.db`) con índices para consultas rápidas

- **Por cada canción (×100)**:

  a. **Extracción de Artistas**:

  - Separa los nombres usando múltiples delimitadores (`&`, `feat.`, `ft.`, `,`, `y`, `and`, `with`, `x`, `vs`)
  - Ejemplo: `"ROSÉ & Bruno Mars"` → `["ROSÉ", "Bruno Mars"]`

  b. **Consulta de Datos de Artistas**:

  - Normaliza cada nombre (minúsculas, sin caracteres especiales)
  - Busca en el diccionario de artistas
  - Resultado: lista de diccionarios `[{'nombre': x, 'pais': y, 'genero': z}]`

  c. **Sistema de Pesos para Colaboraciones**:

  - Si es **artista único** → usa su país y género
  - Si hay **mayoría absoluta (>50%)** del mismo país → gana ese país + género jerárquico local
  - Si hay **mayoría exacta (50%)**:
    - Con 2 países distintos → gana el mayoritario
    - Con 3+ países → "Multipais" + "Multigénero"
  - Si hay **mayoría relativa (<50%)**:
    - Mismo continente y ≤2 países → gana mayoritario
    - Diferentes continentes → "Multipais" + "Multigénero"
  - Si **todos desconocidos** → "Desconocido" + "Pop"

  d. **Obtención de Metadatos de YouTube** (Sistema de 3 capas):

  - **Capa 1 - API de YouTube (prioritaria)**:

    - Extrae video_id de la URL

    - Consulta YouTube Data API v3

    - Obtiene: duración exacta, likes, comentarios, idioma, fecha, restricciones regionales

    - Tiempo: ~0.3-0.8 segundos por video

    - Si falla (cuota/error) → pasa a Capa 2

  - **Capa 2 - Selenium (respaldo principal)**:

    - Lanza navegador Chrome headless

    - Extrae duración del reproductor, título, nombre del canal

    - Detecta tipo de video por título (oficial, lyric, live)

    - Tiempo: ~3-5 segundos por video

    - Si falla → pasa a Capa 3

  - **Capa 3 - yt-dlp (último recurso)**:

    - Prueba múltiples configuraciones de cliente (android, iOS, web)

    - Con retardos entre intentos para evitar bloqueos

    - Obtiene metadatos completos si es posible

    - Tiempo: ~2-4 segundos por video

  e. **Detección Adicional**:

  - Tipo de video: oficial, lyric, live, remix (por título/descripción)
  - Tipo de canal: VEVO, Topic, Label/Studio, Artist Channel, etc.
  - Trimestre de subida: Q1-Q4 basado en fecha
  - Colaboración: detecta feat./& en título

  f. **Inserción en Base de Datos**:

  - Combina: datos del chart + metadatos + país/género resultante
  - Guarda en `canciones_enriquecidas`
  - Incluye campo `error` si algo falló

### Diagrama n°2: Arquitectura de módulos 

![Diagrama del pipeline](https://drive.google.com/uc?export=view&id=1vmH1MD9o0nEaExZKnvw8xuWm1Oge7qNx)

1. **Tablas de Referencia (Lookup Tables)**:

   - `COUNTRY_TO_CONTINENT`: Mapa que asigna 196 países a sus continentes
   - `GENRE_HIERARCHY`: Listas ordenadas de géneros por país (prioridad cultural local)

2. **Sistema de Pesos para Colaboraciones**:

   - `get_continent`: Obtiene continente de un país desde `COUNTRY_TO_CONTINENT`
   - `infer_genre_by_country`: Selecciona género según jerarquía local cuando hay múltiples artistas del mismo país
   - `resolve_country_and_genre`: Motor principal de decisión con reglas (>50%, =50%, <50%)

3. **Clasificadores de Texto**:

   - `detect_video_type`: Identifica si el video es oficial, lyric, live o remix
   - `detect_collaboration`: Detecta colaboraciones en el título (feat., &, with)
   - `detect_channel_type`: Clasifica el canal (VEVO, Topic, Label/Studio, Artist)
   - `parse_upload_season`: Determina el trimestre de subida (Q1-Q4)

4. **Sistema de Obtención de Metadatos (3 capas)**:

   - **Capa 1 - YouTube API v3**: Obtiene metadatos completos (0.3-0.8s/video). Requiere API key
   - **Capa 2 - Selenium**: Extrae metadatos parciales con navegador headless (3-5s/video)
   - **Capa 3 - yt-dlp**: Último recurso con rotación de clientes (android/ios/web)

5. **Utilidades de Base de Datos de Entrada**:

   - `find_latest_chart_db`: Localiza el archivo .db más reciente en `/databases`
   - `load_chart_songs`: Lee las 100 canciones de la tabla `chart_data`
   - `download_artist_db`: Descarga `artist_countries_genres.db` desde GitHub
   - `build_artist_lookup`: Construye diccionario `{nombre_normalizado: (país, género)}`
   - `get_artist_info`: Consulta información de cada artista en el diccionario

6. **Utilidades de Base de Datos de Salida**:

   - `create_output_table`: Crea tabla `canciones_enriquecidas` con 25 columnas y 4 índices
   - `insert_enriched_row`: Inserta una fila con todos los datos enriquecidos
   - `enriched_songs`: Tabla final con estructura optimizada para consultas

7. **Utilidades de Texto**:

      - `normalize_name`: Limpia nombres (minúsculas, sin caracteres especiales)
      - `parse_artist_list`: Separa artistas usando múltiples delimitadores
      - `_empty_metadata`: Diccionario con valores por defecto (cero/vacío)
  
