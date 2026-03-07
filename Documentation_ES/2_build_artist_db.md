# Script 2: Artist Country + Genre Detection System, Enriquecimiento Inteligente
![MIT](https://img.shields.io/badge/License-MIT-green) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue) [![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](#) [![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=fff)](#) ![Requests](https://img.shields.io/badge/Requests-FF6F61?logo=python&logoColor=fff) [![SQLite](https://img.shields.io/badge/SQLite-%2307405e.svg?logo=sqlite&logoColor=white)](#) ![musicbrainz](https://img.shields.io/badge/MusicBrainz-BA478F?logo=musicbrainz&logoColor=white) ![Wikipedia](https://img.shields.io/badge/Wikipedia-000000?logo=wikipedia&logoColor=white)

## 📋 Descripción General

Este proyecto es el segundo componente del sistema de inteligencia de YouTube Charts. Toma los nombres de artistas en bruto extraídos por el descargador y los **enriquece con metadatos geográficos y de género** consultando múltiples bases de conocimiento abiertas. El resultado es una base de datos estructurada de artistas con su país de origen y género musical principal.

### Características Principales

- **Búsqueda Multi-Fuente**: Consultas inteligentes en cascada a MusicBrainz, Wikipedia (resumen e infobox) y Wikidata
- **Variación Inteligente de Nombres**: Genera hasta 15 variaciones por artista (sin acentos, prefijos eliminados, etc.) para máxima tasa de coincidencia
- **Inteligencia Geográfica**: Detección de país a partir de ciudades, gentilicios y referencias regionales usando un diccionario curado de más de 30.000 términos
- **Clasificación de Géneros**: Más de 200 macro-géneros y 5.000+ mapeos de subgéneros con sistema de votación ponderada
- **Reglas Específicas por País**: Manejo especial para más de 50 países (ej. K-Pop para Corea del Sur, Sertanejo para Brasil)
- **Detección de Escritura**: Detección automática de idioma para escrituras no latinas (cirílico, devanagari, árabe, hangul, etc.)
- **Actualizaciones Inteligentes**: Solo completa datos faltantes, nunca sobrescribe información correcta existente
- **Caché en Memoria**: Evita llamadas API redundantes durante la ejecución
- **Optimizado para CI/CD**: Configurado específicamente para GitHub Actions con fallbacks progresivos

## 📊 Diagrama de Flujo del Proceso

```mermaid
graph TD
    classDef input fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef process fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef api fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef cache fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px;
    classDef decision fill:#ffebee,stroke:#b71c1c,stroke-width:2px;
    classDef output fill:#e0f2f1,stroke:#004d40,stroke-width:2px;
    A[(Base de Datos de Charts<br/>youtube_charts_YYYY-WXX.db)] --> B[Leer artistas del chart]
    B --> C[Separar artistas<br/>(manejar feat., &, etc.)]
    C --> D{Obtener lista de<br/>artistas únicos}
    D --> E[Por cada artista...]
    E --> F{¿El artista ya existe<br/>en artist_countries_genres.db?}
    F -->|Sí, con país y género| G[Mostrar ✅ y continuar]
    F -->|Sí, pero falta información| H[Buscar solo información faltante]
    F -->|No| I[Buscar país y género completos]
    H --> J[Iniciar búsqueda de país]
    I --> J
    
    subgraph Búsqueda_País [🔍 Búsqueda de País]
        J --> K[Generar variaciones<br/>de nombre]
        K --> L[Consultar MusicBrainz<br/>(caché)]
        L --> M{¿País encontrado?}
        M -->|Sí| N[✅ País detectado]
        M -->|No| O[Consultar Wikipedia EN<br/>(resumen + infobox)]
        O --> P{¿País encontrado?}
        P -->|Sí| N
        P -->|No| Q[Consultar Wikipedia en<br/>idiomas prioritarios*]
        Q --> R{¿País encontrado?}
        R -->|Sí| N
        R -->|No| S[Consultar Wikidata]
        S --> T{¿País encontrado?}
        T -->|Sí| N
        T -->|No| U[País = Desconocido]
    end
    N --> V[Iniciar búsqueda de género]
    U --> V
    
    subgraph Búsqueda_Género [🎵 Búsqueda de Género]
        V --> W[Generar variaciones<br/>de nombre]
        W --> X[MusicBrainz<br/>(géneros/etiquetas)]
        X --> Y[Añadir candidatos<br/>con pesos]
        Y --> Z[Wikidata<br/>(propiedad P136)]
        Z --> AA[Añadir candidatos<br/>con pesos]
        
        AA --> AB{¿Ya tenemos<br/>3+ candidatos?}
        AB -->|No| AC[Wikipedia en idiomas<br/>prioritarios**]
        AC --> AD[Extraer de infobox<br/>y resumen usando patrones]
        AD --> AE[Añadir candidatos<br/>con pesos]
        
        AE --> AF{¿Ya tenemos<br/>3+ candidatos?}
        AF -->|No| AG[Wikipedia en otros<br/>idiomas comunes]
        AG --> AH[Extraer y añadir]
        
        AB -->|Sí| AI[Seleccionar género<br/>principal]
        AF -->|Sí| AI
        AH --> AI
    end
    subgraph Votación [⚖️ Sistema de Votación y Pesos]
        AI --> AJ[Recibir todos<br/>los candidatos con pesos]
        AJ --> AK[Normalizar a<br/>macro-género]
        AK --> AL[Aplicar pesos por fuente]
        AL --> AM[Detectar escritura<br/>del nombre]
        AM --> AN[Bonus por términos<br/>específicos]
        AN --> AO{¿País<br/>detectado?}
        
        AO -->|Sí| AP[Aplicar prioridad de país<br/>(2.0x, 1.5x, 1.2x)]
        AP --> AQ[Aplicar reglas específicas<br/>del país (force_macro, etc.)]
        
        AO -->|No| AR[Aplicar bonus por escritura<br/>si corresponde]
        AQ --> AS[Sumar votos y<br/>seleccionar ganador]
        AR --> AS
        
        AS --> AT[Fallback: primer género<br/>de prioridad del país]
    end
    AT --> AU{¿Hay un género<br/>ganador?}
    AU -->|No y país conocido| AV[Preparar datos finales]
    AU -->|Sí| AW[Conectar a<br/>artist_countries_genres.db]
    AV --> AW
    AW --> AX[Actualizar solo<br/>campos faltantes]
    N --> AX
    U --> AX
    
    AX --> AY[Insertar nuevo registro]
    
    AY --> AZ{¿El artista<br/>ya existe?}
    AZ -->|Sí| BA[(artist.db<br/>actualizada)]
    AZ -->|No| BB[Registrar estadísticas<br/>y continuar al siguiente artista]
    
    BA --> BC[Todos los artistas procesados]
    BB --> BC
    BC --> BD[Generar reporte final<br/>con estadísticas]
    BD --> E
    E --> BE[Hacer commit y push<br/>al repositorio]
    BE --> BF[(* Idiomas prioritarios: basados en país y escritura detectada]
    BF --> BG[** ej. Corea → ko, en; India → hi, ta, te, en; etc.]
    class A input;
    class BC output;
    class J,W process;
    class L,X,Z,AC,AG api;
    class AL,AM,AN,AP,AQ,AS,AT votación;
    class F,AZ,AO,AU decisión;
    class N,AW,BG output;
    N1[s53]
    N2[s54]
    
    N1 -.-> Q
    N2 -.-> AC
```

### **Leyenda**

| Color          | Tipo     | Descripción                               |
| :------------- | :------- | :---------------------------------------- |
| 🔵 Azul         | Entrada  | Datos de origen (base de datos de charts) |
| 🟠 Naranja      | Proceso  | Lógica de procesamiento interno           |
| 🟣 Púrpura      | API      | Consultas a servicios externos            |
| 🟢 Verde        | Caché    | Almacenamiento temporal en memoria        |
| 🔴 Rojo         | Decisión | Puntos de bifurcación condicional         |
| 🟢 Verde Oscuro | Salida   | Resultados y base de datos final          |

### **Flujo Simplificado**

1. **Entrada**: Lee la base de datos semanal de charts (`youtube_charts_YYYY-WXX.db`)
2. **Extracción**: Obtiene y separa los nombres de artistas (maneja feat., &, etc.)
3. **Deduplicación**: Crea lista de artistas únicos
4. **Por cada artista**:
   - Verifica si ya existe en `artist_countries_genres.db`
   - Si está completo → salta
   - Si falta información → busca solo los campos faltantes
   - Si es nuevo → busca país y género completos
5. **Búsqueda de País**: MusicBrainz → Wikipedia EN → Wikipedia otros idiomas → Wikidata
6. **Búsqueda de Género**: MusicBrainz → Wikidata → Wikipedia (con detección de idioma)
7. **Sistema de Votación**:
   - Normaliza candidatos a macro-géneros
   - Aplica pesos por fuente
   - Bonus por términos específicos
   - Aplica prioridad de país (2.0x, 1.5x, 1.2x)
   - Aplica reglas específicas por país (force_macro, map_generic_to)
   - Bonus por detección de escritura
8. **Actualización de Base de Datos**: Inserta o actualiza con lógica parcial (solo campos faltantes)
9. **Reporte**: Estadísticas finales y commit automático

## 🔍 Análisis Detallado de `2_build_artist_db.py`

### Estructura del Código

#### **1. Configuración y Rutas**

```python
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CHARTS_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"
ARTIST_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_artist_countries_genres" / "artist_countries_genres.db"
```

El script lee la salida del descargador y crea su propia base de datos enriquecida:

- **Entrada**: Bases de datos semanales de charts del paso 1 (`youtube_charts_YYYY-WXX.db`)
- **Salida**: Base de datos de metadatos de artistas (`artist_countries_genres.db`)
- **Estructura**: `charts_archive/2_artist_countries_genres/`

#### **2. Sistema Inteligente de Variación de Nombres**
