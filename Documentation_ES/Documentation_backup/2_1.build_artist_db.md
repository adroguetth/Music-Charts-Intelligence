# 🎵 Script 2: Artist Country + Genre Detection System, Intelligent Enrichment


![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square) 

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![Requests](https://img.shields.io/badge/Requests-FF6F61?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia API](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white) ![Wikidata](https://img.shields.io/badge/Wikidata-990000?style=flat-square&logo=wikidata&logoColor=white) ![DeepSeek](https://custom-icon-badges.demolab.com/badge/DeepSeek-4D6BFF?logo=deepseek&logoColor=white&style=flat-square)

## 📥 Descargas Rápidas

| Documento                       | Formato                                                      |
| :------------------------------ | :----------------------------------------------------------- |
| **🇬🇧 Documentación en Inglés**  | [PDF](https://drive.google.com/file/d/1ar9huV0mMVS0ABgedO5LQWwyA1aEyKvY/view?usp=drive_link) |
| **🇪🇸 Documentación en Español** | [PDF](https://drive.google.com/file/d/1DeaA4FSflAcB-En9yQlu1yvzNpdAOMZO/view?usp=sharing) |

## 📋 Descripción General

Este proyecto es el segundo componente del sistema de inteligencia de charts de YouTube. Toma los nombres de artistas extraídos por el descargador y los **enriquece con metadatos geográficos y de género** consultando múltiples bases de conocimiento abiertas. El resultado es una base de datos estructurada de artistas con su país de origen y género musical principal.

### Características Principales

- **Búsqueda Multi-Fuente**: Consultas en cascada inteligentes a MusicBrainz, Wikipedia (resumen e infobox) y Wikidata
- **Respaldo con IA DeepSeek**: Usa la API de DeepSeek como último recurso cuando todas las fuentes gratuitas fallan (económico, ~$0.002 por 100 artistas)
- **Variación Inteligente de Nombres**: Genera hasta 15 variaciones por artista (acentos eliminados, prefijos eliminados, etc.) para máxima tasa de coincidencia
- **Inteligencia Geográfica**: Detección de país a partir de ciudades, gentilicios y referencias regionales usando un diccionario curado de más de 30,000 términos
- **Clasificación de Géneros**: Más de 200 macro-géneros y más de 5,000 mapeos de subgéneros con sistema de votación ponderada
- **Reglas Específicas por País**: Manejo especial para más de 50 países (ej., K-Pop para Corea del Sur, Sertanejo para Brasil)
- **Detección de Escritura**: Detección automática de idioma para nombres en escrituras no latinas (cirílico, devanagari, árabe, hangul, etc.)
- **Actualizaciones Inteligentes**: Solo completa datos faltantes, nunca sobrescribe información correcta existente
- **Caché en Memoria**: Evita llamadas API redundantes durante la ejecución
- **Optimizado para CI/CD**: Específicamente configurado para GitHub Actions con respaldos progresivos
- **Limitación de Tasa**: Demoras incorporadas para respetar cuotas de API y evitar bloqueos

------

## 📊 Diagrama de Flujo del Proceso

### **Leyenda**

| Color          | Tipo     | Descripción                            |
| :------------- | :------- | :------------------------------------- |
| 🔵 Azul         | Entrada  | Datos fuente (base de datos de charts) |
| 🟠 Naranja      | Proceso  | Lógica de procesamiento interno        |
| 🟣 Púrpura      | API      | Consultas a servicios externos         |
| 🟢 Verde        | Caché    | Almacenamiento temporal en memoria     |
| 🔴 Rojo         | Decisión | Puntos de ramificación condicional     |
| 🟢 Verde Oscuro | Salida   | Resultados y base de datos final       |

### **Diagrama 1: Vista General del Flujo Principal**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/2_build_artist_db/1.png" alt="Diagrama 1: Vista General del Flujo Principal" width="500">

Este diagrama muestra el **pipeline de alto nivel** de todo el sistema:

1. **Entrada**: Lee la base de datos semanal de YouTube Charts (`youtube_charts_YYYY-WXX.db`)
2. **Extracción**: Lee nombres de artistas y los separa (maneja "feat.", "&", comas, etc.)
3. **Deduplicación**: Crea una lista de artistas únicos para evitar procesamiento redundante
4. **Bucle por Artista**: Para cada artista, verifica si ya existe en la base de datos enriquecida
   - **Si está completo** (país + género conocido): Salta al siguiente artista ✅
   - **Si falta información**: Busca solo los campos faltantes (país o género)
   - **Si es nuevo**: Realiza búsqueda completa de país y género
5. **Búsqueda de País** → **Búsqueda de Género** → **Sistema de Votación** → **Actualización de Base de Datos**
6. **Después de todos los artistas**: Genera un reporte final y commitea automáticamente los cambios a GitHub

### **Diagrama 2: Búsqueda de País (Detallada)**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/2_build_artist_db/2.png" alt="Diagrama 2: Búsqueda de País" width="500">

Este diagrama detalla la **estrategia de búsqueda en cascada** para detectar el país de un artista:

1. **Inicio**: Recibe un nombre de artista (puede faltar información o ser nuevo)
2. **Variaciones de Nombre**: Genera hasta 15 variaciones (sin acentos, sin prefijos, etc.)
3. **Verificación de Caché**: Primero verifica en caché en memoria para evitar llamadas API repetidas
4. **MusicBrainz**: Consulta la API de MusicBrainz (datos estructurados, alta confiabilidad)
   - Si se encuentra → retorna país ✅
5. **Wikipedia Inglés**: Si no se encuentra, consulta Wikipedia en inglés:
   - Primero verifica el resumen (primer párrafo) con patrones como "born in...", "from..."
   - Luego verifica el infobox en campos como "origin", "birth_place", "location"
   - Si se encuentra → retorna país ✅
6. **Wikipedia en Idiomas Prioritarios**: Si aún no se encuentra, intenta Wikipedia en idiomas basados en:
   - El país del artista (si ya se conoce del paso anterior)
   - El script detectado del nombre del artista (cirílico → Wikipedia rusa, etc.)
   - Si se encuentra → retorna país ✅
7. **Wikidata**: Última fuente gratuita, consulta Wikidata usando propiedades P27 (país de ciudadanía) y P19 (lugar de nacimiento)
8. **Respaldo con IA DeepSeek**: Solo si todas las fuentes gratuitas fallan, consulta la API de DeepSeek (económico)
   - Usa un prompt estructurado pidiendo país y género
   - Los resultados se normalizan usando las mismas funciones de validación
   - Limitado a 0.5s de demora entre llamadas
9. **Resultado**: Retorna un nombre de país canónico o "Unknown"

### **Diagrama 3: Búsqueda de Género (Detallada)**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/2_build_artist_db/3.png" alt="Diagrama 3: Búsqueda de Género" width="500">

Este diagrama muestra cómo el sistema **recolecta candidatos de género** de múltiples fuentes:

1. **Inicio**: Recibe nombre de artista (y país si ya se detectó)
2. **Variaciones de Nombre**: Mismo sistema de variaciones para máxima tasa de coincidencia
3. **MusicBrainz**: Primera fuente, extrae etiquetas de género y sus conteos
   - Añade candidatos con peso base (1.5× para MusicBrainz)
4. **Wikidata**: Segunda fuente, consulta propiedad P136 (género)
   - Añade candidatos con peso base (1.3× para Wikidata)
5. **Verificación de Candidatos**: Verifica si ya tenemos al menos 3 candidatos de género
   - **Si sí**: Procede directamente al sistema de votación
   - **Si no**: Continúa a la búsqueda en Wikipedia
6. **Wikipedia en Idiomas Prioritarios**: Consulta Wikipedia en idiomas priorizados por:
   - País (ej., artistas coreanos → Wikipedia coreana)
   - Script detectado (ej., nombre árabe → Wikipedia árabe)
7. **Extracción**: Usa coincidencia de patrones para extraer géneros de:
   - **Infobox**: Busca campos "genre", "genres", "género"
   - **Resumen**: Usa patrones NLP como "is a [genre] singer", "known for [genre] music"
8. **Segunda Verificación**: Si aún hay menos de 3 candidatos, intenta Wikipedia en otros idiomas comunes
9. **Respaldo con IA DeepSeek**: Solo si todas las fuentes gratuitas no retornan candidatos, consulta la API de DeepSeek
   - Usa el país (si se conoce) como contexto para mejorar precisión
   - Retorna un género normalizado o texto crudo
10. **Final**: Todos los candidatos (con sus pesos y fuentes) van al Sistema de Votación

### **Diagrama 4: Sistema de Votación y Pesos**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/2_build_artist_db/4.png" alt="Diagrama 4: Sistema de Votación y Pesos" width="500">

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
4. **Detección de Escritura**: Analiza el nombre del artista para detectar el sistema de escritura
5. **Bonificaciones por Término**: Multiplica el peso por 1.4× si se encuentran palabras clave específicas:
   - "reggaeton", "trap latino" → potencia géneros latinos
   - "k-pop", "korean pop" → potencia K-Pop
   - "sertanejo", "funk brasileiro" → potencia géneros brasileños
6. **Prioridad por País** (si se conoce): Aplica multiplicadores adicionales basados en la lista de prioridad de género del país:
   - 1er género prioritario: ×2.0
   - 2do género prioritario: ×1.5
   - 3er+ géneros prioritarios: ×1.2
7. **Reglas Específicas por País**: Aplica reglas especiales para ciertos países:
   - **force_macro**: Fuerza un macro-género específico (ej., Puerto Rico → Reggaetón/Trap Latino)
   - **map_generic_to**: Mapea géneros genéricos (Pop, Rock) a regionales (ej., Corea → K-Pop/K-Rock)
8. **Bonificación por Escritura**: Si el script detectado coincide con el idioma dominante del país, aplica ×1.2
9. **Suma de Votos**: Suma todos los votos ponderados para cada macro-género
10. **Selección del Ganador**: Elige el macro-género con mayor total de votos
11. **Respaldo**: Si no hay ganador y se conoce el país, usa el primer género de la lista de prioridad del país

### **Diagrama 5: Actualización de Base de Datos**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/2_build_artist_db/5.png" alt="Diagrama 5: Actualización de Base de Datos" width="500">

Este diagrama muestra cómo el sistema **persiste los datos inteligentemente**:

1. **Entrada**: Recibe datos finales de país y género para un artista
2. **Conexión**: Abre conexión a `artist_countries_genres.db`
3. **Verificación de Existencia**: Consulta si el artista ya existe en la base de datos
4. **Si el Artista Existe**:
   - **Verificar Campos Faltantes**: Compara datos existentes con nuevos
   - **Actualizar Solo Faltantes**: Actualiza país solo si el existente es NULL/Unknown y el nuevo es conocido
   - Actualiza género solo si el existente es NULL/Unknown y el nuevo es conocido
   - **¡Nunca sobrescribe** datos correctos existentes!
5. **Si el Artista es Nuevo**:
   - Inserta nuevo registro completo con país y género
6. **Registrar Estadísticas**: Registra éxito/fracaso para reportes
7. **Verificación de Bucle**: Si quedan más artistas, retorna al bucle principal
8. **Todos los Artistas Procesados**:
   - Genera reporte final con estadísticas (tasa de éxito, nuevos artistas, etc.)
9. **Commit a GitHub**: Automáticamente commitea y sube los cambios al repositorio

------

## 🔍 Análisis Detallado de `2_build_artist_db.py`

### Estructura del Código

#### **1. Configuración y Rutas**

```python
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CHARTS_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"
ARTIST_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_countries-genres-artist" / "artist_countries_genres.db"
```

El script lee de la salida del descargador y crea su propia base de datos enriquecida:

| Ruta             | Propósito                                                  |
| :--------------- | :--------------------------------------------------------- |
| `CHARTS_DB_DIR`  | Entrada: Bases de datos semanales de charts del Script 1   |
| `ARTIST_DB_PATH` | Salida: Base de datos acumulativa de metadatos de artistas |

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
Variaciones generadas:
1. Lil Wayne
2. Wayne
3. Lil Wayne (sin acentos)
4. Lil Wayne (sin puntos)
5. Wayne (sin prefijo)
```

**Diccionario de prefijos incluye:**

- `dj`, `mc`, `lil`, `young`, `big`, `the`, `los`, `las`, `el`, `la`

#### **3. Sistema de Inteligencia Geográfica**

El corazón de la detección de país es el diccionario `COUNTRIES_CANONICAL`, una base de conocimiento curada con **más de 30,000 términos** mapeados a más de 200 países.

**Ejemplo de estructura para Estados Unidos:**

```python
'United States': {
    # Nombres de países
    'united states', 'usa', 'us', 'america',
    # Gentilicios
    'american', 'estadounidense',
    # Ciudades — Los 50 estados cubiertos
    'new york', 'los angeles', 'chicago', 'miami', ... (500+ ciudades)
}
```

**Proceso de detección:**

| Paso | Método               | Ejemplo                             |
| :--- | :------------------- | :---------------------------------- |
| 1    | Coincidencia directa | "canadian" → Canadá                 |
| 2    | Mención de ciudad    | "from Toronto" → Canadá             |
| 3    | Referencia regional  | "born in Brooklyn" → Estados Unidos |
| 4    | Gentilicio           | "argentine singer" → Argentina      |

#### **4. Ontología de Clasificación de Géneros**

El diccionario `GENRE_MAPPINGS` contiene **más de 5,000 variantes de género** mapeadas a más de 200 macro-géneros.

**Ejemplo de mapeo para música Electrónica:**

```python
'house': ('Electrónica/Dance', 'house'),
'deep house': ('Electrónica/Dance', 'deep house'),
'techno': ('Electrónica/Dance', 'techno'),
'trance': ('Electrónica/Dance', 'trance'),
'edm': ('Electrónica/Dance', 'edm'),
```

**Categorías de macro-géneros (200+):**

| Categoría            | Ejemplos                                               |
| :------------------- | :----------------------------------------------------- |
| **Globales**         | Pop, Rock, Hip-Hop/Rap, R&B/Soul, Electrónica/Dance    |
| **América Regional** | Reggaetón/Trap Latino, Bachata, Cumbia, Sertanejo      |
| **Asia Regional**    | K-Pop/K-Rock, J-Pop/J-Rock, C-Pop/C-Rock, T-Pop/T-Rock |
| **África Regional**  | Afrobeats, Amapiano, Bongo Flava, Zim Dancehall        |
| **Europa Regional**  | Turbo-folk, Manele, Schlager, Chanson, Fado            |
| **Indígenas**        | Māori Pop/Rock, Aboriginal Australian Pop/Rock         |

#### **5. Consultas a Múltiples Fuentes API**

El script consulta cuatro bases de conocimiento en cascada (con DeepSeek como respaldo final):

```python
def search_artist_genre(artist: str, country: Optional[str] = None):
    """
    Flujo de búsqueda optimizado:
    1. MusicBrainz (estructurado, alta confiabilidad) → peso 1.5×
    2. Wikidata (semántico, confiabilidad media) → peso 1.3×
    3. Wikipedia en idiomas prioritarios (texto rico) → peso 1.0-1.2×
    4. API de DeepSeek (respaldo, solo cuando fallan fuentes gratuitas)
    """
```

**Pesos por fuente:**

| Fuente                   | Peso | Razón                                           |
| :----------------------- | :--- | :---------------------------------------------- |
| MusicBrainz              | 1.5× | Estructurado, etiquetas de género confiables    |
| Wikidata                 | 1.3× | Datos semánticos, confiabilidad media           |
| Wikipedia Infobox        | 1.2× | Semi-estructurado, bueno para campos de infobox |
| Wikipedia Resumen        | 1.0× | Texto libre, menor confianza                    |
| Wikipedia Palabras Clave | 0.5× | Confianza más baja, coincidencia de patrones    |

#### **6. Sistema de Caché Inteligente**

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
- **Ahorro de costos**: El caché de DeepSeek evita llamadas pagadas duplicadas

#### **7. Detección de Escritura/Idioma**

```python
def detect_script_from_name(name: str) -> Optional[str]:
    """
    Detecta el sistema de escritura y retorna código ISO 639-1.
    
    Rangos detectados:
    - Devanagari (hi, ne) → India/Nepal
    - Árabe/Urdu (ar/ur) → Medio Oriente/Pakistán
    - Cirílico (ru/uk/bg/sr) → Europa del Este
    - Hangul (ko) → Corea
    - Hanzi/Kanji (zh/ja) → China/Japón
    """
```

**Usado para:**

- Priorizar consultas a Wikipedia en el idioma correcto
- Aplicar bonificaciones regionales (ej., escritura coreana → K-Pop)
- Mejorar la generación de variaciones de nombre
- Proporcionar contexto al respaldo de DeepSeek

#### **8. Sistema de Votación Ponderada**

```python
def select_primary_genre(artist: str, genre_candidates: List[Tuple[str, int, str]],
                         country: Optional[str] = None, detected_lang: Optional[str] = None):
    """
    Sistema de votación ponderada:
    - Peso base de la fuente (MusicBrainz 1.5×, Infobox 1.2×, Wikidata 1.3×)
    - Bonificaciones por término para géneros específicos (K-Pop, Reggaetón, etc.) 1.4×
    - Bonificación por prioridad de país (primer género 2.0×, segundo 1.5×)
    - Reglas específicas por país (force_macro, map_generic_to)
    - Bonificación por detección de escritura (1.2× para región coincidente)
    """
```

**Ejemplo para un artista de Corea del Sur:**

```python
Candidatos de género detectados:
- "k-pop" de MusicBrainz (peso 1.5) → K-Pop/K-Rock
- "pop" de Wikipedia (peso 1.0) → Pop
- "dance" de Wikipedia (peso 0.5) → Electrónica/Dance

País = Corea del Sur (prioridad: K-Pop/K-Rock #1 → 2.0× bonificación)
Escritura detectada = Coreano (1.2× bonificación para K-Pop/K-Rock)

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
        "keywords": ["sertanejo", "funk brasileiro"],
        "bonus_extra": 1.5
    },
    "Puerto Rico": {
        "keywords": ["reggaeton", "trap latino", "urbano"],
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
    Upsert inteligente:
    - Si el artista existe, solo actualiza campos faltantes
    - Nunca sobrescribe datos correctos existentes
    - Registra la fuente de información para transparencia
    """
```

**Ejemplos de escenarios:**

| Escenario | DB Existente | Nueva Búsqueda  | Resultado                                |
| :-------- | :----------- | :-------------- | :--------------------------------------- |
| 1         | (USA, null)  | (null, Hip-Hop) | (USA, Hip-Hop) ✅ Solo género actualizado |
| 2         | (null, Rock) | (UK, Rock)      | (UK, Rock) ✅ Solo país actualizado       |
| 3         | (USA, Pop)   | (Canada, Pop)   | (USA, Pop) ⚠️ Sin sobrescritura           |

### **Estructura de la Tabla `artist`**

| Columna       | Tipo      | Descripción             | Ejemplo        |
| :------------ | :-------- | :---------------------- | :------------- |
| `name`        | TEXT (PK) | Nombre del artista      | "BTS"          |
| `country`     | TEXT      | País de origen canónico | "South Korea"  |
| `macro_genre` | TEXT      | Macro-género primario   | "K-Pop/K-Rock" |

------

## ⚙️ Análisis del Workflow de GitHub Actions (`2_update-artist-db.yml`)

### Estructura del Workflow

```yaml
name: 2- Actualizar Base de Datos de Artistas

on:
  schedule:
    # Se ejecuta cada lunes a las 13:00 UTC (1 hora después de la descarga)
    - cron: '0 13 * * 1'
  
  # Permite ejecución manual
  workflow_dispatch:

env:
  RETENTION_DAYS: 30
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

jobs:
  build-artist-database:
    name: Construir y Actualizar Base de Datos de Artistas
    runs-on: ubuntu-latest
    timeout-minutes: 60
    
    permissions:
      contents: write
```

### Pasos del Job

| Paso | Nombre                                      | Propósito                                         |
| :--- | :------------------------------------------ | :------------------------------------------------ |
| 1    | 📚 Clonar repositorio                        | Clonar repositorio con historial completo         |
| 2    | 🐍 Configurar Python                         | Instalar Python 3.12 con caché de pip             |
| 3    | 📦 Instalar dependencias                     | Instalar requisitos (Playwright no necesario)     |
| 4    | 📁 Asegurar estructura de directorios        | Crear carpetas de bases de datos                  |
| 5    | 🚀 Construir base de datos de artistas       | Ejecutar script principal de enriquecimiento      |
| 6    | ✅ Verificar integridad de la base de datos  | Verificar que la base de datos existe y es válida |
| 7    | 📤 Commit y push de cambios                  | Subir cambios a GitHub (con rebase)               |
| 8    | 📦 Subir artefactos de depuración (en fallo) | Subir datos de depuración para troubleshooting    |
| 9    | 📋 Generar reporte final                     | Generar resumen de ejecución                      |

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

#### **4. 📁 Asegurar Estructura de Directorios**

```yaml
- name: 📁 Asegurar estructura de directorios
  run: |
    mkdir -p charts_archive/1_download-chart/databases
    mkdir -p charts_archive/2_countries-genres-artist
```

#### **5. 🚀 Construir Base de Datos de Artistas**

```yaml
- name: 🚀 Construir base de datos de artistas
  run: |
    python scripts/2_build_artist_db.py
  env:
    GITHUB_ACTIONS: true
    DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
```

#### **6. ✅ Verificar Integridad de la Base de Datos**

```yaml
- name: ✅ Verificar integridad de la base de datos
  run: |
    echo "📊 Verificando base de datos de artistas..."
    DB_PATH="charts_archive/2_countries-genres-artist/artist_countries_genres.db"
    
    if [ -f "$DB_PATH" ]; then
      SIZE=$(stat -c%s "$DB_PATH")
      echo "✅ Base de datos encontrada: $((SIZE / 1024)) KB"
      
      if command -v sqlite3 &> /dev/null; then
        sqlite3 "$DB_PATH" "PRAGMA integrity_check;"
      fi
    else
      echo "❌ Base de datos no encontrada!"
      exit 1
    fi
```

#### **7. 📤 Commit y Push de Cambios**

```yaml
- name: 📤 Commit y push de cambios
  run: |
    git config --global user.name "github-actions[bot]"
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    git add charts_archive/2_countries-genres-artist/
    
    if git diff --cached --quiet; then
      echo "🔭 No hay cambios para commit"
    else
      DATE=$(date +'%Y-%m-%d')
      git commit -m "🤖 Actualizar base de datos de artistas ${DATE} [Automated]"
      git pull --rebase origin main
      git push origin HEAD:main
    fi
```

#### **8. 📦 Subir Artefactos de Depuración (en fallo)**

```python
- name: 📦 Subir artefactos de depuración
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: artist-db-debug-${{ github.run_number }}
    path: |
      charts_archive/
    retention-days: 7
```

#### **9. 📋 Generar Reporte Final**

```yaml
- name: 📋 Generar reporte final
  if: always()
  run: |
    echo "========================================"
    echo "🎵 REPORTE FINAL DE EJECUCIÓN"
    echo "========================================"
    echo "📅 Fecha: $(date)"
    echo "📌 Disparador: ${{ github.event_name }}"
    
    DB_FILE="charts_archive/2_countries-genres-artist/artist_countries_genres.db"
    if [ -f "$DB_FILE" ]; then
      SIZE=$(stat -c%s "$DB_FILE")
      echo "✅ Base de datos de artistas: $((SIZE / 1024)) KB"
      
      if command -v sqlite3 &> /dev/null; then
        ARTIST_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM artist;")
        echo "👤 Artistas procesados: ${ARTIST_COUNT}"
      fi
    fi
```

### Programación Cron

```cron
'0 13 * * 1'  # Minuto 0, Hora 13, Cualquier día del mes, Cualquier mes, Lunes
```

- **Ejecución**: Cada lunes a las 13:00 UTC
- **Desplazamiento**: 1 hora después del workflow de descarga (12:00 UTC)
- **Propósito**: Permite que el workflow de descarga se complete antes de que comience el enriquecimiento

### Secretos Requeridos

| Secreto            | Propósito                                                    |
| :----------------- | :----------------------------------------------------------- |
| `DEEPSEEK_API_KEY` | Usado por el sistema de respaldo de IA DeepSeek para recuperar información de país y género cuando todas las fuentes gratuitas fallan. Opcional; el script continúa sin él. |

------

## 🚀 Instalación y Configuración Local

### Requisitos Previos

- Python 3.7 o superior (3.12 recomendado)
- Git instalado
- Acceso a Internet para consultas API
- (Opcional) Clave API de DeepSeek para respaldo

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

#### **4. Configurar Clave API de DeepSeek (opcional, para respaldo)**

```bash
# Linux/Mac
export DEEPSEEK_API_KEY="tu-clave-api-aqui"

# Windows (Command Prompt)
set DEEPSEEK_API_KEY=tu-clave-api-aqui

# Windows (PowerShell)
$env:DEEPSEEK_API_KEY="tu-clave-api-aqui"
```

#### **5. Ejecutar Prueba Inicial**

```bash
python scripts/2_build_artist_db.py
```

### Configuración de Desarrollo

```bash
# Simular entorno de GitHub Actions
export GITHUB_ACTIONS=true

# Para depuración detallada (muestra candidatos de género)
export LOG_LEVEL=DEBUG
```

---

## 📁 Estructura de Archivos Generada

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
    └── artist_countries_genres.db       # Base de datos enriquecida de artistas
```

### recimiento de la Base de Datos

| Métrica             | Valor                  |
| :------------------ | :--------------------- |
| Ejecución inicial   | 100-200 artistas       |
| Crecimiento semanal | 10-50 nuevos artistas  |
| Tamaño estimado     | ~10KB por 100 artistas |

------

## 🔧 Personalización y Configuración

### Parámetros Ajustables en el Script

```python
# En 2_build_artist_db.py
MIN_CANDIDATES = 3        # Mínimo de candidatos de género antes de buscar en Wikipedia
RETRY_DELAY = 0.5         # Demora entre llamadas API (segundos)
DEFAULT_TIMEOUT = 10      # Timeout de solicitud API (segundos)
DEEPSEEK_RATE_LIMIT = 0.5 # Demora entre llamadas a DeepSeek (segundos)
```

### Configuración del Workflow

```yaml
# En 2-update-artist-database.yml
env:
  RETENTION_DAYS: 30       # Días para artefactos

timeout-minutes: 60        # Timeout total del job (permite límites de tasa API)
```

### Añadir Nuevos Países

```python
# Extender COUNTRIES_CANONICAL
'Nuevo País': {
    'nombre del país', 'gentilicios', 'capital', 'ciudades principales'
}
```

### Añadir Nuevos Mapeos de Género

```python
# Extender GENRE_MAPPINGS
'nuevo subgénero': ('Macro-Género', 'subgénero')
```

### Ajustar Prioridades por País

```python
# Modificar COUNTRY_GENRE_PRIORITY
"Nombre del País": [
    "Género Prioritario 1",   # Recibe 2.0× bonificación
    "Género Prioritario 2",   # Recibe 1.5× bonificación
    "Género Prioritario 3"    # Recibe 1.2× bonificación
]
```

---

## 🐛 Solución de Problemas

### Problemas Comunes y Soluciones

| Error                                        | Causa Probable                 | Solución                                   |
| :------------------------------------------- | :----------------------------- | :----------------------------------------- |
| "No se encontraron bases de datos de charts" | El Script 1 no se ha ejecutado | Ejecutar Script 1 primero                  |
| Timeouts de API en GitHub Actions            | Red lenta o API lenta          | Aumentar `DEFAULT_TIMEOUT`                 |
| Límite de tasa de APIs                       | Demasiadas solicitudes         | Aumentar `RETRY_DELAY`                     |
| Clave API de DeepSeek no configurada         | Secreto faltante               | Añadir `DEEPSEEK_API_KEY` a GitHub Secrets |
| Artista no encontrado en ninguna fuente      | Artista oscuro                 | Añadir reglas de respaldo para el país     |

### Registros y Depuración

**Niveles de log disponibles:**

| Nivel          | Cuándo                | Detalles                                            |
| :------------- | :-------------------- | :-------------------------------------------------- |
| Básico         | Ejecución normal      | Progreso y resultados                               |
| DEBUG          | `LOG_LEVEL=DEBUG`     | Muestra candidatos de género y detalles de votación |
| GitHub Actions | `GITHUB_ACTIONS=true` | Logs mejorados para CI/CD                           |

------

## 📈 Monitoreo y Mantenimiento

### Indicadores de Salud

| Métrica                    | Rango Esperado          | Notas                                     |
| :------------------------- | :---------------------- | :---------------------------------------- |
| Tamaño de la base de datos | +10-50 registros/semana | Crece lentamente                          |
| Tasa de éxito              | >90%                    | Para artistas establecidos                |
| Tiempo de respuesta API    | <2 segundos             | Promedio entre fuentes                    |
| Tasa de acierto de caché   | 30-70%                  | Aumenta con el tamaño de la base de datos |
| Uso de DeepSeek            | <10%                    | Solo cuando fallan fuentes gratuitas      |

### Métricas de Rendimiento

| Métrica                      | Rango Esperado | Notas                                |
| :--------------------------- | :------------- | :----------------------------------- |
| Artistas procesados/hora     | 500-1000       | Depende de tiempos de respuesta API  |
| Tasa de detección de género  | 85-95%         | Más baja para artistas nicho         |
| Tasa de detección de país    | 80-90%         | Más baja para artistas oscuros       |
| Tasa de respaldo de DeepSeek | <10%           | Solo cuando fallan fuentes gratuitas |
| Costo por 100 artistas       | ~$0.002        | Con respaldo de DeepSeek             |

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
  - DeepSeek (API Comercial, solo respaldo)

------

## 🤝 Contribución

1. Reportar problemas con registros completos
2. Proponer mejoras con casos de uso
3. Añadir nuevos mapeos de género con ejemplos
4. Contribuir con variantes de países (especialmente para regiones subrepresentadas)
5. Mantener compatibilidad con la estructura de base de datos existente

------

## 🧪 Limitaciones Conocidas

- **Dependencia de API**: El sistema depende de servicios externos que pueden cambiar o limitar tasa
- **Artistas Nuevos**: Artistas emergentes pueden no aparecer en las bases de conocimiento
- **Géneros Nicho**: Algunos micro-géneros pueden no tener mapeos aún
- **Detección de Escritura**: Basada en heurísticas, puede identificar incorrectamente ocasionalmente
- **Costo de DeepSeek**: Aunque mínimo, requiere clave API y tiene costos de tokens

------

**⭐ Si este proyecto te resulta útil, ¡considera darle una estrella en GitHub!**
