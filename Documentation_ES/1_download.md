# 🎵 YouTube Charts Scraper - Script 1: Descarga Automatizada

![Texto alternativo](https://img.shields.io/badge/License-MIT-green) ![Texto alternativo](https://img.shields.io/badge/Web-Scraping-orange) [![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](#) [![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=fff)](#) [![NumPy](https://img.shields.io/badge/NumPy-4DABCF?logo=numpy&logoColor=fff)](#) [![Playwright](https://custom-icon-badges.demolab.com/badge/Playwright-2EAD33?logo=playwright&logoColor=fff)](#) [![SQLite](https://img.shields.io/badge/SQLite-%2307405e.svg?logo=sqlite&logoColor=white)](#)


## 📋 Descripción General

Este proyecto consiste en un sistema automatizado para la descarga y almacenamiento semanal de las listas más populares de YouTube. El script `1_download.py` es el primer componente de una serie de herramientas diseñadas para extraer, procesar y analizar datos de YouTube Charts.

### Características Principales

- **Descarga Completa**: Obtiene listas completas de 100 canciones
- **Automatización**: Programación semanal mediante GitHub Actions
- **Almacenamiento Histórico**: Base de datos SQLite con versionado por semana
- **Sistema de Respaldo**: Backups automáticos antes de actualizaciones
- **Robustez**: Múltiples estrategias de detección y modo de respaldo
- **Optimización CI/CD**: Configurado específicamente para GitHub Actions



## 🛠️ Stack Tecnológico

### **Tecnologías Principales**

| Componente | Tecnología | Propósito |
|-----------|-----------|---------|
| **Lenguaje** | Python 3.12+ | Lenguaje principal de desarrollo |
| **Automatización Web** | Playwright | Automatización de navegador para scraping |
| **Procesamiento de Datos** | Pandas | Manipulación y análisis de CSV |
| **Base de Datos** | SQLite3 | Persistencia local de datos |
| **CI/CD** | GitHub Actions | Ejecución semanal automatizada |

### **Arquitectura del Proyecto**

Este script es parte de un pipeline multi-etapa:

1. **Etapa 1 (Actual)**: `1_download.py` - Extracción de datos brutos
2. **Etapa 2 (Futura)**: `2_enrich.py` - Enriquecimiento y procesamiento de datos
3. **Etapa 3+**: Herramientas adicionales de análisis y visualización

### **Flujo General de Datos**

<img src="https://drive.google.com/uc?export=view&id=1iwi96GAMQXgi42aesPn755vN_VRJYx8D"
  width="700"
     alt="Flujo General de Datos">

## 📊 Diagrama de Flujo del Proceso

<img src="https://drive.google.com/uc?export=view&id=1fA6bXnQeZ0vKXHobH65cKFmm251QRJnu" 
     width="400" 
     alt="Diagrama de Flujo del Proceso">

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

- `data/`: Datos temporales y de depuración
- `charts_archive/1_download-chart/`: Archivo principal de datos descargados
  - `databases/`: Bases de datos SQLite por semana
  - `backup/`: Copias de respaldo temporales
  - `latest_chart.csv`: Datos del chart más reciente

#### **2. Detección de Entorno**

```python
IS_GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS') == 'true'
```

El script detecta automáticamente si se ejecuta en GitHub Actions y ajusta:

- Tiempos de espera más largos
- Registros detallados para CI/CD
- Estrategias de recuperación específicas

#### **3. Sistema de Instalación de Dependencias**

```python
def install_playwright():
    """Verificación e instalación completa de Playwright"""
```

Esta función realiza una verificación de tres niveles:

1. Paquete Python de Playwright
2. Binarios del navegador Chromium
3. Dependencias del sistema operativo

<div style="page-break-after: always;"></div>

#### **4. Estrategias de Web Scraping**

El script implementa múltiples enfoques para localizar el botón de descarga:

```python
# 1. Selector primario por ID
download_button = await page.query_selector('#download-button')

# 2. Selector por aria-label (respaldo 1)
download_button = await page.query_selector('[aria-label*="Download"]')

# 3. Selector por texto (respaldo 2)
download_button = await page.query_selector('text=Download')
```

**Características anti-detección:**

- User agent personalizado
- Inyección de JavaScript para ocultar automatización
- Configuración realista de vista y localización
- Encabezados HTTP personalizados



#### **5. Gestión de Base de Datos SQLite**

```python
def update_sqlite_database(csv_path: Path, week_id: str):
```

**Proceso de actualización:**

1. Crear respaldo de la base de datos existente
2. Leer y validar el CSV descargado
3. Agregar metadatos (fecha, semana, timestamp)
4. Usar patrón de tabla temporal para evitar pérdida de datos
5. Crear índices optimizados
6. Actualizar estadísticas

**Estructura de la tabla `chart_data`:**

| Columna            | Tipo      | Descripción             |
| ------------------ | --------- | ----------------------- |
| Rank               | `INTEGER` | Posición en el chart    |
| Previous Rank      | `INTEGER` | Posición anterior       |
| Track Name         | `TEXT`    | Nombre de la canción    |
| Artist Names       | `TEXT`    | Artista(s)              |
| Periods on Chart   | `INTEGER` | Semanas en el chart     |
| Views              | `INTEGER` | Número de vistas        |
| Growth             | `TEXT`    | Porcentaje de crecimiento |
| YouTube URL        | `TEXT`    | Enlace al video         |
| download_date      | `TEXT`    | Fecha de descarga       |
| download_timestamp | `TEXT`    | Timestamp completo      |
| week_id            | `TEXT`    | Identificador de semana |

#### **6. Sistema de Respaldo y Limpieza**

**Respaldos temporales:**

- Creados antes de cada actualización
- Nomenclatura: `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db`
- Retención: 7 días por defecto

**Limpieza de bases de datos antiguas:**

- Retención configurable (52 semanas por defecto)
- Eliminación basada en fecha del nombre de archivo
- Estadísticas de limpieza en registros

#### **7. Modo de Respaldo**

Cuando el scraping no está disponible:

```python
def create_fallback_file():
    """Genera datos de muestra con estructura realista"""
```

- 100 registros simulados

- Estructura idéntica al CSV real

- Metadatos consistentes

- Para desarrollo y recuperación de errores

  <div style="page-break-after: always;"></div>

#### **8. Reportes y Estadísticas**

```python
def list_available_databases():
    """Muestra estadísticas de todas las bases de datos"""
```

Incluye:

- Número total de bases de datos
- Registros por base de datos
- Rango de fechas cubierto
- Tamaños de archivo
- Total de registros acumulados



## ⚙️ Análisis del Workflow de GitHub Actions (`1_download-chart.yml`)

### **Estructura del Workflow**

```yaml
name: Download YouTube Chart
on:
  schedule:
    - cron: '0 12 * * 1'  # Lunes 12:00 UTC
  workflow_dispatch:       # Ejecución manual
  push:                    # Disparador en cambios
```

### **Jobs y Pasos**

#### **Job: `download-and-store`**

- **Sistema operativo**: Ubuntu Latest
- **Timeout**: 30 minutos
- **Permisos**: Acceso de escritura al repositorio

#### **Pasos Detallados:**

**1. 📚 Checkout del Repositorio**

```yaml
uses: actions/checkout@v4
with:
  fetch-depth: 0  # Historial completo para operaciones git
```

<div style="page-break-after: always;"></div>

**2. 🐍 Configuración de Python 3.12**

```yaml
uses: actions/setup-python@v5
with:
  cache: 'pip'  # Caché de dependencias
```

**3. 📦 Instalación de Dependencias**
   - Playwright y navegador Chromium
   - Pandas, NumPy para procesamiento
   - Dependencias del sistema

**4. 📁 Creación de Estructura de Directorios**

```yaml
run: |
  mkdir -p data charts_archive/1_download-chart/databases charts_archive/1_download-chart/backup
```

**5. 🚀 Ejecución del Script Principal**

```yaml
run: |
  python scripts/1_download.py
env:
  GITHUB_ACTIONS: true  # Variable de entorno para detección
```

**6. ✅ Verificación de Resultados**
   - Listado de archivos generados en `charts_archive/1_download-chart/`
   - Estadísticas de tamaño
   - Validación de existencia

**7. 📤 Commit y Push Automático**
   - Configuración automática de usuario
   - Solo hace commit de cambios en `charts_archive/`
   - Mensaje con fecha y semana
   - Push automático a main

**8. 📦 Subida de Artefactos (solo en fallo)**
   - Datos y archivos para depuración
   - Retención: 7 días

**9. 📋 Reporte Final**
   - Estadísticas detalladas
   - Información del disparador
   - Tamaños de archivo
   - Conteo de bases de datos

### **Programación Cron**

```cron
'0 12 * * 1'  # Minuto 0, Hora 12, Cualquier día del mes, Cualquier mes, Lunes
```

- **Ejecución**: Todos los lunes a las 12:00 UTC
- **Equivalente**: 13:00 CET (Hora Central Europea)
- **Consideraciones**: YouTube actualiza los charts los domingos/lunes



## 🚀 Instalación y Configuración Local

### **Requisitos Previos**

- Python 3.7 o superior
- Git instalado
- Acceso a internet para descargas

### **Instalación Paso a Paso**

**1. Clonar el Repositorio**

```bash
git clone <url-del-repositorio>
cd <directorio-del-proyecto>
```

**2. Crear Entorno Virtual (recomendado)**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

**3. Instalar Dependencias**

```bash
pip install -r requirements.txt

# Instalar navegador Playwright
python -m playwright install chromium

# Instalar dependencias del sistema (Linux)
python -m playwright install-deps
```

**4. Ejecutar Prueba Inicial**

```bash
python scripts/1_download.py
```

### **Configuración para Desarrollo**

**Variables de Entorno Opcionales**

```bash
# Para simular entorno de GitHub Actions
export GITHUB_ACTIONS=true

# Para depuración detallada
export PWDEBUG=1
```

**Ejecución con Visualización**

```python
# Modificar en el script:
headless=False  # En lugar de True
```



## 📁 Estructura de Archivos Generados

```text
charts_archive/
├── 1_download-chart/
│   ├── latest_chart.csv              # CSV más reciente (siempre actualizado)
│   ├── databases/
│   │   ├── youtube_charts_2025-W01.db
│   │   ├── youtube_charts_2025-W02.db
│   │   └── ... (una por semana)
│   └── backup/
│       ├── backup_2025-W01_20250106_120500.db
│       └── ... (respaldos temporales)
└── 2_enriched_chart/
    └── (datos enriquecidos futuros)
```

### **Convención de Nomenclatura**

- **Bases de datos**: `youtube_charts_YYYY-WXX.db`
- **Respaldos**: `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db`
- **CSV semanal**: `latest_chart.csv` (siempre sobrescrito)

<div style="page-break-after: always;"></div>

## 🔧 Personalización y Configuración

### **Parámetros Ajustables en el Script**

```python
# En 1_download.py
RETENTION_DAYS = 7      # Días para mantener respaldos
RETENTION_WEEKS = 52    # Semanas para mantener bases de datos
TIMEOUT = 120000        # Timeout en milisegundos (2 minutos)
```

### **Configuración del Workflow**

```yaml
# En 1_download-chart.yml
env:
  RETENTION_DAYS: 30    # Días para artefactos

timeout-minutes: 30     # Timeout total del job
```



## 🐛 Solución de Problemas

### **Problemas Comunes y Soluciones**

**1. Error: "Playwright browsers not installed"**

```bash
# Solución manual
python -m playwright install chromium
python -m playwright install-deps
```

**2. Error: Timeout en GitHub Actions**
   - Verificar conexión de red del runner
   - Aumentar timeout en YML
   - Revisar registros de Playwright

**3. Error: Botón de descarga no encontrado**
   - YouTube puede haber cambiado la interfaz
   - Revisar captura de pantalla en artefactos
   - Actualizar selectores en el código

**4. Error: Base de datos corrupta**
   - Usar respaldos automáticos
   - Verificar permisos de escritura
   - Revisar espacio en disco

### **Registros y Depuración**

**Niveles de registro disponibles:**

1. **Información básica**: Ejecución normal
2. **Debug de GitHub Actions**: Con `GITHUB_ACTIONS=true`
3. **Captura de pantalla de error**: En artefactos al fallar
4. **Estadísticas detalladas**: Reporte final



## 📈 Monitoreo y Mantenimiento

### **Indicadores de Salud**

1. **Tamaño de base de datos**: Crece ~100 registros/semana
2. **Tamaño del CSV**: ~10-50KB por archivo
3. **Tiempo de ejecución**: 2-5 minutos normalmente
4. **Tasa de éxito**: Debería ser >95% en condiciones normales

### **Alertas Recomendadas**

1. **Fallo consecutivo**: 2 o más fallos consecutivos
2. **Tiempo excesivo**: >10 minutos de ejecución
3. **Datos incompletos**: <100 registros en CSV
4. **Espacio en disco**: >1GB en `charts_archive/`



## 📄 Licencia y Atribución

- **Licencia**: MIT

- **Autor**: Alfonso Droguett
  - 🔗 **LinkedIn:** [Alfonso Droguett](https://www.linkedin.com/in/adroguetth/)
  - 🌐 **Portafolio web:** [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/)
  - 📧 **Email:** [adroguett.consultor@gmail.com](mailto:adroguett.consultor@gmail.com)

- **Dependencias**:
  - Playwright (Apache 2.0)
  - Pandas (BSD 3-Clause)
  - NumPy (BSD)

  <div style="page-break-after: always;"></div>

## 🤝 Contribución

1. Reportar problemas con registros completos
2. Proponer mejoras con casos de uso
3. Mantener compatibilidad con la estructura existente
4. Documentar cambios en el README

---

**Nota**: Este Documentacion corresponde específicamente al script `1_download.py`. Para documentación de otros scripts, consultar sus READMEs respectivos.
