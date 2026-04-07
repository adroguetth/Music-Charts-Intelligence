# 🎵 Script 1: Automated Data Acquisition from YouTube Charts

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Web Scraping](https://img.shields.io/badge/Web-Scraping-orange?style=flat-square) 

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white) [![Playwright](https://custom-icon-badges.demolab.com/badge/Playwright-2EAD33?logo=playwright&logoColor=white&style=flat-square)](https://playwright.dev) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white)

## 📋 Descripción General

Este script es el **primer componente** del sistema de inteligencia de charts de YouTube. Automatiza la descarga semanal del chart oficial de YouTube (100 canciones) y almacena los datos en una base de datos SQLite versionada con seguimiento histórico completo.

El script utiliza **Playwright** para automatización de navegador headless con sofisticadas medidas anti-detección, implementa **múltiples selectores de respaldo** para manejar cambios en la interfaz de YouTube, e incluye un **sistema completo de respaldos** para prevenir pérdida de datos.

### Características Principales

- **Descarga Completa**: Recupera el CSV completo de 100 canciones con todas las métricas del chart (posición, vistas, crecimiento, etc.)
- **Anti-Detección**: User agent personalizado, inyección de JavaScript, configuración de viewport realista
- **Múltiples Estrategias de Selectores**: 4 métodos de respaldo para localizar el botón de descarga
- **Almacenamiento Versionado**: Bases de datos SQLite semanales con identificadores ISO (YYYY-WXX)
- **Respaldos Automáticos**: Crea respaldos antes de cualquier actualización de la base de datos
- **Limpieza Inteligente**: Elimina automáticamente respaldos antiguos (7 días) y bases de datos (52 semanas)
- **Modo de Respaldo**: Genera datos de muestra realistas cuando el scraping falla
- **Optimizado para CI/CD**: Específicamente configurado para GitHub Actions con logging detallado

------

## 📊 Diagrama de Flujo del Proceso

### **Leyenda**

| Color          | Tipo             | Descripción                                                  |
| :------------- | :--------------- | :----------------------------------------------------------- |
| 🔵 Azul         | Entrada / Inicio | Página web de YouTube Charts, configuración                  |
| 🟠 Naranja      | Proceso          | Automatización del navegador, operaciones de archivos        |
| 🔴 Rojo         | Decisión         | Puntos de ramificación condicional (¿funciona el selector?, ¿existe el archivo?) |
| 🟢 Verde        | Almacenamiento   | Bases de datos SQLite, respaldos, archivos CSV               |
| 🟣 Púrpura      | Externo          | Entorno de GitHub Actions                                    |
| 🟢 Verde Oscuro | Salida           | Base de datos final, reporte de éxito                        |

### **Diagrama 1: Vista General del Flujo Principal**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/1_download/1.png" alt="Diagrama 1: Vista General del Flujo Principal" width="500">

Este diagrama muestra el **pipeline de alto nivel** de todo el script:

1. **Inicio**: Navega a la URL de YouTube Charts (`https://charts.youtube.com/charts/TopSongs/global/weekly`)
2. **Verificación de Dependencias**: Verifica que el paquete Playwright y el navegador Chromium estén instalados
   - **Si faltan**: Auto-instala vía pip y playwright CLI
   - **Si falla**: Cae a generación de datos de muestra
3. **Lanzamiento del Navegador**: Lanza Chromium headless con medidas anti-detección:
   - User agent personalizado (Chrome 120)
   - Flags de automatización deshabilitadas
   - Inyección de JavaScript para ocultar `navigator.webdriver`
   - Viewport realista (1920×1080) y locale (en-US)
4. **Navegación a la Página**: Carga la página de YouTube Charts, espera estado `networkidle`
5. **Desplazamiento y Espera**: Se desplaza 5 veces (800px cada una) para activar contenido lazy-loaded
6. **Búsqueda del Botón de Descarga**: Intenta 4 estrategias de selectores de respaldo
   - **Si se encuentra**: Hace clic en el botón y espera la descarga
   - **Si no se encuentra**: Toma captura de pantalla, usa datos de muestra de respaldo
7. **Descarga del CSV**: Guarda el CSV de 100 canciones con métricas completas del chart
8. **Actualización de SQLite**: Crea respaldo, lee CSV con pandas, añade metadatos, inserta datos
9. **Creación de Índices**: Construye `idx_week`, `idx_rank`, `idx_artist` para optimización de consultas
10. **Limpieza**: Elimina respaldos antiguos (>7 días) y bases de datos antiguas (>52 semanas)
11. **Salida**: Base de datos lista para el Script 2 (`youtube_charts_YYYY-WXX.db`)

### **Diagrama 2: Estrategia de Múltiples Selectores**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/1_download/2.png" alt="Diagrama 2: Estrategia de Múltiples Selectores" width="500">

Este diagrama detalla las **4 estrategias de respaldo** para localizar el botón de descarga:

1. **Selector 1 (Principal)**: `#download-button` (basado en ID)
   - Más específico, más rápido cuando está disponible
   - Timeout: 15 segundos
   - **Si se encuentra** → Hace clic, descarga CSV, retorna éxito ✅
   - **Si no se encuentra** → Continúa al Selector 2
2. **Selector 2 (Respaldo 1)**: `paper-icon-button[title="download"]`
   - Apunta a elementos Polymer con atributo title
   - Timeout: 10 segundos
   - **Si se encuentra** → Hace clic, descarga CSV, retorna éxito ✅
   - **Si no se encuentra** → Continúa al Selector 3
3. **Selector 3 (Respaldo 2)**: `button[aria-label*="download" i]`
   - Coincidencia de patrón aria-label sin distinción de mayúsculas/minúsculas
   - Timeout: 10 segundos
   - **Si se encuentra** → Hace clic, descarga CSV, retorna éxito ✅
   - **Si no se encuentra** → Continúa al Respaldo Final
4. **Respaldo Final**: Itera sobre todos los botones (`button, paper-icon-button, iron-icon`)
   - Busca en el HTML palabras clave: `download`, `descarga`, `export`, `csv`
   - Intenta cada botón que coincida secuencialmente
   - **Si se encuentra** → Hace clic, descarga CSV, retorna éxito ✅
   - **Si no se encuentra** → Toma captura de pantalla, usa datos de muestra

**Cada selector incluye:**

- Verificación de visibilidad (`is_visible()`)
- Desplazamiento a la vista si es necesario (`scroll_into_view_if_needed()`)
- Pausa de 2 segundos después del desplazamiento
- Timeout de descarga de 15-45 segundos

### **Diagrama 3: Proceso de Actualización de Base de Datos SQLite**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/1_download/3.png" alt="Diagrama 3: Proceso de Actualización de Base de Datos SQLite" width="500">

Este diagrama muestra el **proceso seguro de actualización de la base de datos**:

1. **Lectura del CSV**: Carga el archivo CSV con pandas
   - Intenta codificación UTF-8 primero
   - Cae a Latin-1 si UTF-8 falla
   - Valida 100 canciones (o menos si está incompleto)
2. **Adición de Columnas de Metadatos**: Inyecta campos de seguimiento
   - `download_date`: Fecha actual (AAAA-MM-DD)
   - `download_time`: Hora actual (HH:MM:SS)
   - `week_id`: Identificador ISO de semana (AAAA-WXX)
   - `timestamp`: Marca de tiempo completa (AAAAMMDD_HHMMSS)
3. **Verificación de Base de Datos Existente**: ¿Existe `youtube_charts_AAAA-WXX.db`?
   - **Si SÍ**: Crea respaldo con marca de tiempo antes de cualquier modificación
     - Nombrado del respaldo: `backup_AAAA-WXX_AAAAMMDD_HHMMSS.db`
     - Ubicación: `charts_archive/1_download-chart/backup/`
   - **Si NO**: Procede directamente a la actualización
4. **Creación de Tabla Temporal**: Crea tabla `temp_AAAAMMDD_HHMMSS`
   - Escribe nuevos datos en la tabla temporal primero
   - Previene pérdida de datos si falla la escritura
5. **Eliminación de Registros Antiguos**: Elimina datos existentes para `week_id` actual
   - Asegura reemplazo limpio (no acumulación)
   - Solo afecta la semana actual, preserva otras semanas
6. **Inserción de Nuevos Datos**: Mueve datos de la tabla temporal a la tabla principal
   - Si se detecta conflicto de esquema → Elimina y recrea la tabla
   - Confirma la transacción después de la inserción exitosa
7. **Creación de Índices**: Construye índices optimizados
   - `idx_date` en `download_date`
   - `idx_week` en `week_id`
   - `idx_rank` en `Rank`
   - `idx_artist` en `Artist Names`
8. **Verificación y Reporte**: Cuenta registros totales y fechas únicas
   - Salida: "✅ Base de datos actualizada exitosamente"
   - Muestra: registros totales, fechas únicas, ubicación del archivo

**Garantía de Seguridad**: El patrón de tabla temporal + respaldo asegura que si algún paso falla, los datos originales permanecen intactos y pueden restaurarse desde el respaldo.

------

## 🔍 Análisis Detallado de `1_download.py`

### Estructura del Código

#### **1. Configuración Inicial y Directorios**

```python
# Directorios principales
OUTPUT_DIR = Path("data")
ARCHIVE_DIR = Path("charts_archive/1_download-chart")
DATABASE_DIR = ARCHIVE_DIR / "databases"
BACKUP_DIR = ARCHIVE_DIR / "backup"
```

El script organiza los datos en una estructura jerárquica:

| Directorio                         | Propósito                              | Retención                 |
| :--------------------------------- | :------------------------------------- | :------------------------ |
| `data/`                            | Datos temporales y de depuración       | Efímera                   |
| `charts_archive/1_download-chart/` | Archivo principal de datos descargados | Permanente                |
| `databases/`                       | Bases de datos SQLite por semana       | 52 semanas (configurable) |
| `backup/`                          | Copias de respaldo temporales          | 7 días (configurable)     |

#### **2. Sistema de Instalación de Dependencias**

```python
def install_playwright():
    """Verificación e instalación completa de Playwright"""
```

Esta función realiza una **verificación de tres niveles**:

| Nivel | Verificación                       | Acción si falta                        |
| :---- | :--------------------------------- | :------------------------------------- |
| 1     | Paquete Python Playwright          | `pip install playwright pandas`        |
| 2     | Binarios del navegador Chromium    | `playwright install chromium`          |
| 3     | Dependencias del sistema operativo | `playwright install-deps` (solo Linux) |

#### **3. Medidas Anti-Detección**

El script implementa múltiples técnicas para evitar la detección de bots:

```python
# Argumentos del navegador
args=[
    '--disable-blink-features=AutomationControlled',  # Ocultar automatización
    '--disable-features=IsolateOrigins',              # Reducir huellas
]

# Inyección de JavaScript para ocultar automatización
await context.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
""")

# User agent y cabeceras realistas
user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
```

#### **4. Estrategia de Múltiples Selectores**

El script intenta **4 métodos diferentes** para localizar el botón de descarga:

| Prioridad | Selector                              | Descripción                                                  |
| :-------- | :------------------------------------ | :----------------------------------------------------------- |
| 1         | `#download-button`                    | Más específico, basado en ID                                 |
| 2         | `paper-icon-button[title="download"]` | Respaldo por atributo title                                  |
| 3         | `button[aria-label*="download" i]`    | Respaldo por patrón aria-label                               |
| 4         | Iterar sobre todos los botones        | Buscar palabras clave: 'download', 'descarga', 'export', 'csv' |

Cada selector incluye:

- Verificación de visibilidad
- Desplazamiento a la vista si es necesario
- Timeout de 15-45 segundos
- Captura de pantalla en caso de fallo

#### **5. Gestión de Base de Datos SQLite**

```python
def update_sqlite_database(csv_path: Path, week_id: str):
```

**Proceso de actualización con garantías de seguridad:**

| Paso | Operación                                | Propósito                                                 |
| :--- | :--------------------------------------- | :-------------------------------------------------------- |
| 1    | Leer CSV con Pandas                      | Cargar datos en DataFrame                                 |
| 2    | Añadir columnas de metadatos             | `download_date`, `week_id`, `timestamp`                   |
| 3    | Crear respaldo                           | Antes de cualquier modificación                           |
| 4    | Crear tabla temporal                     | Evitar pérdida de datos durante la actualización          |
| 5    | Eliminar registros antiguos de la semana | Reemplazo limpio (no acumulación)                         |
| 6    | Insertar nuevos datos                    | Desde la tabla temporal                                   |
| 7    | Crear índices                            | Optimizar consultas: `idx_week`, `idx_rank`, `idx_artist` |

**Esquema de la tabla `chart_data`:**

| Columna            | Tipo    | Descripción                                |
| :----------------- | :------ | :----------------------------------------- |
| `Rank`             | INTEGER | Posición en el chart (1-100)               |
| `Previous Rank`    | INTEGER | Posición en la semana anterior             |
| `Track Name`       | TEXT    | Título de la canción                       |
| `Artist Names`     | TEXT    | Artista(s), puede incluir colaboraciones   |
| `Periods on Chart` | INTEGER | Número de semanas en el chart              |
| `Views`            | INTEGER | Conteo total de vistas                     |
| `Growth`           | TEXT    | Porcentaje de crecimiento semana a semana  |
| `YouTube URL`      | TEXT    | Enlace directo al video                    |
| `download_date`    | TEXT    | Fecha de descarga (AAAA-MM-DD)             |
| `download_time`    | TEXT    | Hora de descarga (HH:MM:SS)                |
| `week_id`          | TEXT    | Identificador ISO de semana (AAAA-WXX)     |
| `timestamp`        | TEXT    | Marca de tiempo completa (AAAAMMDD_HHMMSS) |

#### **6. Sistema de Respaldos y Limpieza**

**Creación de Respaldos:**

- Activada antes de cualquier actualización de la base de datos
- Convención de nombrado: `backup_AAAA-WXX_AAAAMMDD_HHMMSS.db`
- Ubicación: `charts_archive/1_download-chart/backup/`

**Políticas de Limpieza:**

| Elemento       | Retención  | Configurable      |
| :------------- | :--------- | :---------------- |
| Respaldos      | 7 días     | `RETENTION_DAYS`  |
| Bases de datos | 52 semanas | `RETENTION_WEEKS` |

```python
def cleanup_old_backups(days: int = 7):
    """Elimina archivos de respaldo más antiguos que los días especificados."""
    
def cleanup_old_databases(weeks: int = 52):
    """Elimina archivos de base de datos más antiguos que las semanas especificadas."""
```

#### **7. Modo de Respaldo (Fallback)**

Cuando el scraping no está disponible (problemas de red, cambios en YouTube, etc.):

```python
def create_fallback_file():
    """Genera 100 registros de muestra realistas"""
```

**Estructura de datos de muestra:**

- 100 canciones con métricas realistas
- Mismo formato CSV que los YouTube Charts reales
- Incluye todas las columnas esperadas por los scripts posteriores
- Permite desarrollo y pruebas sin scraping en vivo

#### **8. Reportes y Estadísticas**

```python
def list_available_databases():
    """Muestra estadísticas de todas las bases de datos"""
```

La salida incluye:

- Número de bases de datos
- Registros por base de datos
- Rango de fechas cubierto
- Tamaños de archivo
- Registros totales acumulados

**Ejemplo de salida:**

```text
📦 Bases de datos disponibles (12):
   • 2025-W01: 100 registros, 245.3 KB
     📅 2025-01-06 a 2025-01-06
   • 2025-W02: 100 registros, 248.1 KB
     📅 2025-01-13 a 2025-01-13
   ...
   📊 TOTAL: 1,200 registros en 12 bases de datos
```

---

## ⚙️ Análisis del Workflow de GitHub Actions (`1_download-chart.yml`)

### Estructura del Workflow

```yaml
name: 1- Descargar Chart de YouTube

on:
  schedule:
    # Se ejecuta cada lunes a las 12:00 UTC
    - cron: '0 12 * * 1'
  
  # Permite ejecución manual del workflow
  workflow_dispatch:
  
  # Se dispara con push a main si cambian scripts de Python
  push:
    branches:
      - main
    paths:
      - 'scripts/*.py'

env:
  # Número de días para retener artefactos
  RETENTION_DAYS: 30

jobs:
  download-and-store:
    name: Descargar y Almacenar Charts de YouTube
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    permissions:
      contents: write
```

### Pasos del Job

| Paso | Nombre                            | Propósito                                      |
| :--- | :-------------------------------- | :--------------------------------------------- |
| 1    | 📚 Clonar repositorio              | Clonar repositorio con historial completo      |
| 2    | 🐍 Configurar Python               | Instalar Python 3.12 con caché de pip          |
| 3    | 📦 Instalar dependencias           | Instalar requisitos + Playwright + Chromium    |
| 4    | 📁 Crear estructura de directorios | Crear carpetas de bases de datos y respaldos   |
| 5    | 🚀 Ejecutar script de descarga     | Ejecutar script principal de scraping          |
| 6    | ✅ Verificar resultados            | Listar archivos generados y tamaños            |
| 7    | 📤 Commit y push                   | Subir cambios a GitHub (con rebase)            |
| 8    | 📦 Subir artefactos (en fallo)     | Subir datos de depuración para troubleshooting |
| 9    | 📋 Reporte final                   | Generar resumen de ejecución                   |

### Pasos Detallados

#### **1. 📚 Clonar Repositorio**

```yaml
- name: 📚 Clonar repositorio
  uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Historial completo para operaciones git
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
    python -m playwright install chromium
    python -m playwright install-deps
```

#### **4. 🚀 Ejecutar Script Principal**

```yaml
- name: 🚀 Descargar Charts de YouTube
  run: |
    python scripts/1_download.py
  env:
    GITHUB_ACTIONS: true
```

#### **5. ✅ Verificar Resultados**

```yaml
- name: ✅ Verificar resultados
  run: |
    echo "📂 Contenido de charts_archive/1_download-chart/:"
    ls -la charts_archive/1_download-chart/
    echo "📊 Archivos de base de datos:"
    ls -la charts_archive/1_download-chart/databases/
```

#### **6. 📤 Commit y Push**

```yaml
- name: 📤 Commit y push
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add charts_archive/1_download-chart/
    git commit -m "📊 Actualización de Chart de YouTube $(date '+%Y-%m-%d') [Automated]" || echo "Sin cambios"
    git push
```

#### **7. 📋 Reporte Final**

```yaml
- name: 📋 Resumen
  run: |
    echo "=========================================="
    echo "✅ Descarga de Charts de YouTube Completada!"
    echo "📅 Semana: $(python scripts/1_download.py --get-week)"
    echo "=========================================="
```

### Programación Cron

```cron
'0 12 * * 1'  # Minuto 0, Hora 12, Cualquier día del mes, Cualquier mes, Lunes
```

- **Ejecución**: Cada lunes a las 12:00 UTC
- **Equivalente**: 13:00 CET / 08:00 EST
- **Justificación**: YouTube actualiza sus charts los domingos/lunes
- **Línea de Tiempo del Pipeline**:
  - `12:00 UTC` → Script 1: Descargar charts
  - `13:00 UTC` → Script 2: Enriquecimiento de artistas
  - `14:00 UTC` → Script 3: Enriquecimiento de charts
  - `15:00 UTC` → Script 4: Generación de notebooks

### Secretos Requeridos

| Secreto | Propósito                                                    |
| :------ | :----------------------------------------------------------- |
| Ninguno | El Script 1 no requiere claves API. Funciona completamente con los YouTube Charts públicos y la automatización del navegador Playwright. |

### Variables de Entorno

| Variable         | Valor  | Propósito                                             |
| :--------------- | :----- | :---------------------------------------------------- |
| `GITHUB_ACTIONS` | `true` | Deshabilita prompts interactivos, habilita modo CI/CD |
| `RETENTION_DAYS` | `30`   | Días para retener artefactos de depuración            |

------

## 🚀 Instalación y Configuración Local

### Requisitos Previos

- Python 3.7 o superior (3.12 recomendado)
- Git instalado
- Acceso a Internet para descargas

### Instalación Paso a Paso

#### 1. **Clonar el Repositorio**

```bash
git clone https://github.com/adroguetth/Music-Charts-Intelligence.git
cd Music-Charts-Intelligence
```

#### 2. **Crear Entorno Virtual (recomendado)**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

#### 3. **Instalar Dependencias**

```bash
pip install -r requirements.txt

# Instalar navegador Playwright
python -m playwright install chromium

# Instalar dependencias del sistema (solo Linux)
python -m playwright install-deps
```

#### 4. **Ejecutar Prueba Inicial**

```bash
python scripts/1_download.py
```

### Configuración de Desarrollo

```bash
# Simular entorno de GitHub Actions
export GITHUB_ACTIONS=true

# Habilitar depuración visual (modo no headless)
export PWDEBUG=1

# Ejecutar con navegador visible (editar script: headless=False)
```

---

## 📁 Estructura de Archivos Generada

```text
charts_archive/
├── 1_download-chart/
│   ├── latest_chart.csv              # CSV más reciente (siempre actualizado)
│   ├── databases/
│   │   ├── youtube_charts_2025-W01.db
│   │   ├── youtube_charts_2025-W02.db
│   │   └── ... (uno por semana, 52 semanas retenidas)
│   └── backup/
│       ├── backup_2025-W01_20250106_120500.db
│       └── ... (temporales, 7 días retenidos)
```

### Convención de Nombrado

| Tipo          | Patrón                               | Ejemplo                              |
| :------------ | :----------------------------------- | :----------------------------------- |
| Base de datos | `youtube_charts_AAAA-WXX.db`         | `youtube_charts_2025-W14.db`         |
| Respaldo      | `backup_AAAA-WXX_AAAAMMDD_HHMMSS.db` | `backup_2025-W14_20250406_120500.db` |
| CSV           | `latest_chart.csv`                   | Siempre sobrescrito                  |

------

## 🔧 Personalización y Configuración

### Parámetros Ajustables en el Script

```python
# En 1_download.py
RETENTION_DAYS = 7      # Días para mantener respaldos
RETENTION_WEEKS = 52    # Semanas para mantener bases de datos
TIMEOUT = 120000        # Timeout del navegador en milisegundos
```

### Configuración del Workflow

```yaml
# En .github/workflows/1_download-chart.yml
env:
  RETENTION_DAYS: 30    # Retención de artefactos de GitHub

timeout-minutes: 30     # Timeout total del job
```

## 🐛 Solución de Problemas

### Problemas Comunes y Soluciones

| Error                                       | Causa Probable             | Solución                                            |
| :------------------------------------------ | :------------------------- | :-------------------------------------------------- |
| `Playwright browsers not installed`         | Chromium faltante          | `python -m playwright install chromium`             |
| `Timeout esperando botón de descarga`       | Interfaz de YouTube cambió | Revisar artefacto de captura, actualizar selectores |
| `CSV tiene 0 filas`                         | Descarga fallida           | Verificar red, usar modo de respaldo                |
| `Base de datos bloqueada`                   | Acceso concurrente         | Esperar o reiniciar, verificar respaldo existente   |
| `ImportError: No module named 'playwright'` | Paquete faltante           | `pip install playwright`                            |

### Depuración con Capturas de Pantalla

Cuando no se puede encontrar el botón de descarga, el workflow sube automáticamente una captura de pantalla como artefacto. Descárgala desde GitHub Actions → Artifacts → `screenshot-failure`.

------

## 📈 Monitoreo y Mantenimiento

### Indicadores de Salud

| Métrica                 | Esperado    | Umbral de Alerta      |
| :---------------------- | :---------- | :-------------------- |
| Tiempo de ejecución     | 2-5 minutos | >10 minutos           |
| Filas del CSV           | 100         | <100                  |
| Tamaño de base de datos | 200-300 KB  | <100 KB               |
| Tasa de éxito           | >95%        | 2 fallos consecutivos |

### Niveles de Logging

| Nivel      | Cuándo                | Detalles                     |
| :--------- | :-------------------- | :--------------------------- |
| Básico     | Ejecución normal      | Progreso y resultados        |
| Depuración | `GITHUB_ACTIONS=true` | Logs completos del navegador |
| Captura    | En fallo              | Captura de pantalla subida   |
| Traza      | `PWDEBUG=1`           | Depuración interactiva       |

------

## 📄 Licencia y Atribución

- **Licencia**: MIT
- **Autor**: Alfonso Droguett
  - 🔗 **LinkedIn:** [Alfonso Droguett](https://www.linkedin.com/in/adroguetth/)
  - 🌐 **Portafolio web:** [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/)
  - 📧 **Email:** adroguett.consultor@gmail.com
- **Dependencias**:
  - Playwright (Apache 2.0)
  - Pandas (BSD 3-Clause)
  - NumPy (BSD)

------

## 🤝 Contribución

1. Reportar problemas con logs completos
2. Actualizar selectores si YouTube cambia su interfaz
3. Mantener compatibilidad con el esquema de base de datos existente
4. Probar cambios localmente antes de enviar PRs
5. Documentar nuevas características en este README

------

**⭐ Si este proyecto te resulta útil, ¡considera darle una estrella en GitHub!**
