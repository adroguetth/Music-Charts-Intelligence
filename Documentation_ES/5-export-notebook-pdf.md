# Script 5: Exportador de Notebooks a PDF + Subida a Google Drive

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![PDF Export](https://img.shields.io/badge/PDF-Export-red?style=flat-square) ![Google Drive](https://img.shields.io/badge/Google-Drive-4285F4?style=flat-square)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=flat-square&logo=jupyter&logoColor=white) ![Playwright](https://custom-icon-badges.demolab.com/badge/Playwright-2EAD33?logo=playwright&logoColor=white&style=flat-square) ![Google Drive API](https://img.shields.io/badge/Google_Drive_API-4285F4?style=flat-square&logo=google-drive&logoColor=white)

## 📥 Descargas Rápidas

| Documento | Formato |
| :-------- | :------ |
| **🇬🇧 Documentación en Inglés** | [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=drive_link) |
| **🇪🇸 Documentación en Español** | [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=sharing) |
| **📁 Notebooks y archivos PDF archivados** | [Google Drive Folder](https://drive.google.com/drive/folders/1RpfyGHsIY5MThE1bfe0Rc3gk03WoYzpR) |

## 📋 Descripción General

Este script es el **quinto componente** del sistema de inteligencia de charts de YouTube. Toma los notebooks semanales de Jupyter generados por el Script 4 y los **exporta a PDF**, luego **sube tanto los notebooks originales como los PDFs a Google Drive** para archivo a largo plazo.

El script escanea los directorios de notebooks en inglés y español, determina la semana más reciente usando comparación de semana ISO (manejando correctamente los límites de año), convierte cada notebook a PDF usando `nbconvert` con el backend de Playwright (Chromium), y organiza los archivos en una jerarquía de carpetas estructurada en Google Drive.

### Características Principales

- **Soporte Bilingüe**: Procesa notebooks en inglés (`Notebook_EN/weekly/`) y español (`Notebook_ES/weekly/`)
- **Ordenamiento por Semana ISO**: Identifica correctamente la semana más reciente (ej. `2026-W01` > `2025-W52`)
- **Conversión a PDF**: Usa `nbconvert --to webpdf` con Playwright Chromium (no requiere LaTeX)
- **Organización Estructurada en Drive**: Crea carpetas anidadas: `weekly/ → youtube_charts_YYYY-WXX/ → EN/ y ES/`
- **Autenticación OAuth 2.0**: Usa tokens de actualización para acceso persistente sin reautenticación manual
- **Subidas Idempotentes**: Crea carpetas solo si no existen; nunca duplica archivos
- **Ejecución Manual o Programada**: Se ejecuta cada martes a las 12:00 UTC o mediante activación manual
- **Cero Escrituras en el Repositorio**: No hace commits a GitHub; solo lee notebooks y sube a Drive
- **Optimizado para CI/CD**: Diseñado para GitHub Actions con dependencias mínimas

------

## 📊 Diagramas de Flujo de Procesos

### **Leyenda**

| Color | Tipo | Descripción |
| :---- | :--- | :---------- |
| 🔵 Azul | Entrada | Directorios de notebooks (EN y ES) |
| 🟠 Naranja | Proceso | Conversión a PDF, creación de carpetas, subida de archivos |
| 🟣 Púrpura | API Externa | API de Google Drive (OAuth 2.0) |
| 🟢 Verde | Salida | Estructura de carpetas en Google Drive |
| 🔴 Rojo | Decisión | Verificaciones condicionales (notebook existe, selección de semana) |

### **Diagrama 1: Vista General del Flujo Principal**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/5_export_notebook_to_pdf/1.png" alt="Diagrama 1: Vista General del Flujo Principal" width="600">

Este diagrama muestra el **pipeline de alto nivel** de todo el script:

1. **Entrada**: Escanea `Notebook_EN/weekly/` y `Notebook_ES/weekly/` en busca de archivos `youtube_charts_*.ipynb`
2. **Detección de Semana**: Extrae identificadores de semana ISO de todos los nombres de notebook, determina la semana más reciente (año + número de semana)
3. **Selección de Notebook**: Para la semana más reciente, localiza el notebook correspondiente en cada idioma (si está disponible)
4. **Conversión a PDF**: Convierte cada notebook a PDF usando `nbconvert --to webpdf` con Playwright Chromium
5. **Autenticación en Drive**: Autentica con Google Drive usando token de actualización OAuth 2.0
6. **Creación de Carpetas**: Crea u obtiene IDs de carpetas para:
   - Carpeta raíz (especificada por el usuario, normalmente `GDRIVE_ROOT_FOLDER_ID`)
   - Carpeta padre `weekly` (creada una vez, reutilizada entre semanas)
   - Carpeta específica de la semana (ej. `youtube_charts_2026-W16`)
   - Subcarpetas de idioma (`EN/` y `ES/`)
7. **Subida de Archivos**: Sube tanto los archivos `.ipynb` como `.pdf` a sus respectivas carpetas de idioma
8. **Limpieza**: Elimina los archivos PDF temporales del runner

### **Diagrama 2: Estructura de Carpetas en Google Drive**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/5_export_notebook_to_pdf/2.png" alt="Diagrama 2: Estructura de Carpetas en Google Drive" width="700">

Este diagrama muestra la **jerarquía de carpetas destino** en Google Drive:

```text
Mi Drive/
└── (GDRIVE_ROOT_FOLDER_ID)           # Carpeta raíz especificada por el usuario
    └── weekly/                       # Carpeta padre fija (creada una vez)
        └── youtube_charts_2026-W16/  # Carpeta específica de la semana
            ├── EN/                    # Subcarpeta de idioma inglés
            │   ├── youtube_charts_2026-W16.ipynb
            │   └── youtube_charts_2026-W16.pdf
            └── ES/                    # Subcarpeta de idioma español
                ├── youtube_charts_2026-W16.ipynb
                └── youtube_charts_2026-W16.pdf

```

**Lógica de Creación de Carpetas:**

- El ID de la carpeta raíz (`GDRIVE_ROOT_FOLDER_ID`) es proporcionado por el usuario
- La carpeta `weekly/` se crea una vez si no existe
- Las carpetas de semana (ej. `youtube_charts_2026-W16`) se crean por ejecución
- Las subcarpetas de idioma (`EN/`, `ES/`) se crean solo si existe un notebook para ese idioma

### **Diagrama 3: Lógica de Detección de Semana**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_ES/Diagramas/5_export_notebook_to_pdf/3.png" alt="Diagrama 3: Lógica de Detección de Semana" width="500">

Este diagrama detalla el **algoritmo de selección de semana**:

1. **Entrada**: Lista de todos los notebooks de `Notebook_EN/weekly/` y `Notebook_ES/weekly/`
2. **Análisis de Nombre**: Extrae año y semana usando regex `(\d{4})-W(\d{1,2})`
3. **Creación de Tuplas**: Convierte a tuplas `(año, semana)` para comparación
4. **Ordenamiento**: Ordena tuplas en orden descendente (año más alto primero, luego semana más alta)
5. **Selección**: Toma la primera tupla como la semana más reciente
6. **Salida**: Devuelve el par `(año, semana)`

**Ejemplo:**

```text
Notebooks:
  - youtube_charts_2025-W52.ipynb → (2025, 52)
  - youtube_charts_2026-W01.ipynb → (2026, 1)
  - youtube_charts_2026-W02.ipynb → (2026, 2)

Ordenado: (2026, 2) > (2026, 1) > (2025, 52)
Más reciente: (2026, 2) → 2026-W02
```



------

## 🔍 Análisis Detallado de `5_export_notebook_to_pdf.py`

### Estructura del Código

#### **1. Configuración de Rutas**

```python
NOTEBOOKS_EN_DIR = Path("Notebook_EN/weekly")
NOTEBOOKS_ES_DIR = Path("Notebook_ES/weekly")
TEMP_PDF_DIR = Path("temp_pdf")
TEMP_PDF_DIR.mkdir(exist_ok=True)
```

| Ruta               | Propósito                                                    |
| :----------------- | :----------------------------------------------------------- |
| `NOTEBOOKS_EN_DIR` | Entrada: Notebooks en inglés del Script 4                    |
| `NOTEBOOKS_ES_DIR` | Entrada: Notebooks en español del Script 4                   |
| `TEMP_PDF_DIR`     | Almacenamiento temporal para PDFs generados (eliminados después de subir) |

#### **2. Variables de Entorno (Requeridas)**

| Variable                | Fuente                   | Propósito                                      |
| :---------------------- | :----------------------- | :--------------------------------------------- |
| `GDRIVE_CLIENT_ID`      | Google Cloud Console     | Identificador de cliente OAuth 2.0             |
| `GDRIVE_CLIENT_SECRET`  | Google Cloud Console     | Secreto de cliente OAuth 2.0                   |
| `GDRIVE_REFRESH_TOKEN`  | Generado vía flujo OAuth | Token de larga duración para acceso a la API   |
| `GDRIVE_ROOT_FOLDER_ID` | URL de Google Drive      | ID de la carpeta destino (ej. `1ABCxyz123...`) |

#### **3. Autenticación OAuth 2.0**

```python
def get_authenticated_service():
    """
    Construye y devuelve un servicio autenticado de Google Drive usando un token de actualización.

    Crea un objeto Credentials a partir de client_id, client_secret y refresh_token.
    Actualiza automáticamente el token de acceso si ha expirado.
    """
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    if creds.expired:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds)
```

**Flujo de Autenticación:**

1. Las credenciales se construyen a partir del `refresh_token` almacenado
2. Si el token de acceso ha expirado, se actualiza automáticamente
3. El alcance `drive.file` limita el acceso a archivos creados o abiertos por la aplicación

#### **4. Funciones de Detección de Semana**

```python
def get_week_from_filename(filename: str) -> tuple:
    """Extrae la semana ISO (año, número de semana) del nombre de un notebook."""
    match = re.search(r'(\d{4})-W(\d{1,2})', filename)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (0, 0)

def get_latest_week_from_all_notebooks() -> tuple:
    """Escanea los directorios EN y ES para encontrar la semana más reciente."""
    all_notebooks = []
    for dir_path in [NOTEBOOKS_EN_DIR, NOTEBOOKS_ES_DIR]:
        if dir_path.exists():
            for nb in dir_path.glob("youtube_charts_*.ipynb"):
                week = get_week_from_filename(nb.name)
                if week != (0, 0):
                    all_notebooks.append((week, nb))
    if not all_notebooks:
        return None
    all_notebooks.sort(key=lambda x: x[0], reverse=True)
    return all_notebooks[0][0]
```



**Por qué es importante:**

- El ordenamiento lexicográfico de cadenas (`"2026-W01"` vs `"2025-W52"`) funciona, pero convertir a tuplas aseguta la corrección
- Escanear ambos directorios asegura que se seleccione la semana más reciente en todos los idiomas

#### **5. Conversión a PDF**

```python
def convert_to_pdf(notebook_path: Path) -> Path:
    """Convierte un notebook de Jupyter a PDF usando nbconvert con backend de playwright."""
    pdf_filename = f"{notebook_path.stem}.pdf"
    pdf_path = TEMP_PDF_DIR / pdf_filename

    subprocess.run(["playwright", "install", "chromium"], check=False)

    cmd = [
        "jupyter", "nbconvert", "--to", "webpdf",
        "--output-dir", str(TEMP_PDF_DIR),
        "--output", pdf_filename,
        str(notebook_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error en nbconvert:", result.stderr)
        sys.exit(1)

    if not pdf_path.exists():
        print(f"PDF no encontrado en la ruta esperada: {pdf_path}")
        sys.exit(1)

    return pdf_path
```

**Puntos clave:**

- `--to webpdf` usa Chromium de Playwright (no requiere LaTeX)
- `playwright install chromium` asegura que el navegador esté disponible (idempotente)
- El directorio de salida se establece explícitamente para evitar problemas de resolución de rutas

#### **6. Gestión de Carpetas en Google Drive**

```python
def create_or_get_folder(service, folder_name: str, parent_id: str) -> str:
    """Crea una carpeta en Google Drive si no existe, de lo contrario devuelve su ID."""
    query = (f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' "
             f"and '{parent_id}' in parents and trashed=false")
    response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    files = response.get('files', [])

    if files:
        return files[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder['id']
```

**Garantía de Idempotencia:**

- Múltiples ejecuciones del script no crearán carpetas duplicadas
- Las carpetas existentes se detectan mediante consulta a la API y se reutilizan

#### **7. Subida de Archivos**

```python
def upload_file(service, file_path: Path, parent_folder_id: str, mime_type: str) -> str:
    """Sube un archivo a Google Drive dentro de una carpeta padre especificada."""
    media = MediaFileUpload(file_path, mimetype=mime_type)
    metadata = {'name': file_path.name, 'parents': [parent_folder_id]}
    uploaded = service.files().create(body=metadata, media_body=media, fields='id').execute()
    return uploaded['id']
```

**Tipos MIME Utilizados:**

- `.ipynb` → `application/x-ipynb+json`
- `.pdf` → `application/pdf`

------

## ⚙️ Análisis del Workflow de GitHub Actions (`5-export-notebook-pdf.yml`)

### Estructura del Workflow

```yaml
name: Export Notebooks to PDF and Upload to Drive

on:
  schedule:
    - cron: '0 12 * * 2'      # Martes 12:00 UTC
  workflow_dispatch:
    inputs:
      week:
        description: 'Semana a exportar (YYYY-WXX). Vacío para auto-detección'
        required: false
        default: ''
      language:
        description: 'Idioma a exportar'
        required: true
        default: 'both'
        type: choice
        options: ['both', 'en', 'es']

env:
  RETENTION_DAYS: 30
```

### Pasos del Job

| Paso | Nombre                                | Propósito                                                    |
| :--- | :------------------------------------ | :----------------------------------------------------------- |
| 1    | 📚 Checkout del repositorio            | Clonar repositorio (profundidad mínima)                      |
| 2    | 🐍 Configurar Python                   | Instalar Python 3.12 con caché de pip                        |
| 3    | 📦 Instalar dependencias               | Instalar jupyter, nbconvert, playwright, librerías de Google API |
| 4    | 📂 Verificar directorios de notebooks  | Verificar existencia de carpetas EN/ES                       |
| 5    | 🚀 Ejecutar script de exportación      | Ejecutar la exportación principal a PDF y subida a Drive     |
| 6    | 📤 Subir artefactos (en caso de fallo) | Capturar PDFs y logs para depuración                         |
| 7    | 🧹 Limpiar                             | Eliminar archivos PDF temporales                             |
| 8    | 📋 Informe final                       | Mostrar resumen de ejecución                                 |

### Pasos Detallados

#### **1. 📚 Checkout del Repositorio**

```yaml
- name: 📚 Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 1
```



#### **2. 🐍 Configurar Python**

```yaml
- name: 🐍 Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'
```



#### **3. 📦 Instalar Dependencias**

```yaml
- name: 📦 Install dependencies
  run: |
    pip install --upgrade pip
    pip install jupyter nbconvert playwright google-api-python-client google-auth-oauthlib
    playwright install chromium
```



#### **4. 📂 Verificar Directorios de Notebooks**

```yaml
- name: 📂 Verify notebook directories
  run: |
    echo "📁 Checking notebook directories..."
    
    if [ -d "Notebook_EN/weekly" ]; then
      echo "✅ Notebook_EN/weekly exists"
      ls -la Notebook_EN/weekly/ | head -10
    else
      echo "⚠️ Notebook_EN/weekly not found"
    fi
    
    if [ -d "Notebook_ES/weekly" ]; then
      echo "✅ Notebook_ES/weekly exists"
      ls -la Notebook_ES/weekly/ | head -10
    else
      echo "⚠️ Notebook_ES/weekly not found"
    fi
```



#### **5. 🚀 Ejecutar Script de Exportación**

```yaml
- name: 🚀 Run export script
  run: python scripts/5_export_notebook_to_pdf.py
  env:
    GDRIVE_CLIENT_ID: ${{ secrets.GDRIVE_CLIENT_ID }}
    GDRIVE_CLIENT_SECRET: ${{ secrets.GDRIVE_CLIENT_SECRET }}
    GDRIVE_REFRESH_TOKEN: ${{ secrets.GDRIVE_REFRESH_TOKEN }}
    GDRIVE_ROOT_FOLDER_ID: ${{ secrets.GDRIVE_ROOT_FOLDER_ID }}
    EXPORT_WEEK: ${{ github.event.inputs.week || '' }}
    EXPORT_LANGUAGE: ${{ github.event.inputs.language || 'both' }}
```



#### **6. 📤 Subir Artefactos (en caso de fallo)**

```yaml
- name: 📤 Upload artifacts (on failure)
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: export-debug-${{ github.run_number }}
    path: |
      temp_pdf/
      scripts/5_export_notebook_to_pdf.py.log
    retention-days: ${{ env.RETENTION_DAYS }}
```



#### **7. 🧹 Limpiar**

```yaml
- name: 🧹 Cleanup
  if: always()
  run: rm -rf temp_pdf/
```



#### **8. 📋 Informe Final**

```yaml
- name: 📋 Final report
  if: always()
  run: |
    echo "========================================"
    echo "📤 EXPORT EXECUTION REPORT"
    echo "========================================"
    echo "📅 Date: $(date)"
    echo "📌 Trigger: ${{ github.event_name }}"
    echo ""
    
    if [ "${{ github.event_name }}" = "schedule" ]; then
      echo "   • Triggered by: Scheduled cron (Tuesday 12:00 UTC)"
    elif [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
      echo "   • Triggered by: Manual dispatch"
      echo "   • Week input: ${{ github.event.inputs.week || 'auto' }}"
      echo "   • Language input: ${{ github.event.inputs.language || 'both' }}"
    fi
    
    echo ""
    echo "📁 Notebook directories:"
    echo "   EN: $(ls Notebook_EN/weekly/*.ipynb 2>/dev/null | wc -l) notebooks"
    echo "   ES: $(ls Notebook_ES/weekly/*.ipynb 2>/dev/null | wc -l) notebooks"
```



### Programación Cron

```cron
'0 12 * * 2'  # Minuto 0, Hora 12, Cualquier día del mes, Cualquier mes, Martes
```

- **Ejecución**: Cada martes a las 12:00 UTC
- **Desfase**: 21 horas después del Script 4.1 (lunes 15:00 UTC)

### Disparadores de Ejecución

Este workflow se ejecuta **solo** en:

- **Ejecución programada**: Cada martes a las 12:00 UTC
- **Ejecución manual**: Mediante `workflow_dispatch` desde la interfaz de GitHub Actions

> **Nota**: La ejecución automática en `git push` está desactivada. El script solo lee notebooks y sube a Drive sin hacer commits al repositorio.

### Secretos Requeridos

| Secreto                 | Propósito                                                    |
| :---------------------- | :----------------------------------------------------------- |
| `GDRIVE_CLIENT_ID`      | ID de cliente OAuth 2.0 desde Google Cloud Console           |
| `GDRIVE_CLIENT_SECRET`  | Secreto de cliente OAuth 2.0 desde Google Cloud Console      |
| `GDRIVE_REFRESH_TOKEN`  | Token de actualización de larga duración (generado una vez vía flujo OAuth) |
| `GDRIVE_ROOT_FOLDER_ID` | ID de la carpeta destino en Google Drive                     |

------

## 🚀 Instalación y Configuración Local

### Prerrequisitos

- Python 3.7 o superior (3.12 recomendado)
- Git instalado
- Acceso a Internet
- Proyecto de Google Cloud con API de Drive habilitada
- Credenciales OAuth 2.0 (tipo aplicación de escritorio)
- ID de carpeta de Google Drive para almacenamiento

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
pip install jupyter nbconvert playwright google-api-python-client google-auth-oauthlib
playwright install chromium
```



#### **4. Configurar Credenciales OAuth 2.0 de Google Drive**

**Paso 1: Crear credenciales OAuth 2.0 en Google Cloud Console**

- Ir a [Google Cloud Console](https://console.cloud.google.com/)
- Habilitar la API de Google Drive
- Crear ID de cliente OAuth 2.0 para **Aplicación de escritorio**
- Descargar el archivo `credentials.json`

**Paso 2: Generar un token de actualización (configuración única)**

Crear un script temporal:

```python
# generate_refresh_token.py
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json',
    ['https://www.googleapis.com/auth/drive.file']
)
creds = flow.run_local_server(port=0)
print(f"Refresh token: {creds.refresh_token}")
```



Ejecutarlo:

```bash
python generate_refresh_token.py
```



Copiar el token de actualización impreso.

#### **5. Configurar Variables de Entorno**

```bash
# Linux/Mac
export GDRIVE_CLIENT_ID="your_client_id.apps.googleusercontent.com"
export GDRIVE_CLIENT_SECRET="GOCSPX-xxxx"
export GDRIVE_REFRESH_TOKEN="1//0gxxxx"
export GDRIVE_ROOT_FOLDER_ID="1ABCxyz123..."

# Windows (Command Prompt)
set GDRIVE_CLIENT_ID=your_client_id.apps.googleusercontent.com
set GDRIVE_CLIENT_SECRET=GOCSPX-xxxx
set GDRIVE_REFRESH_TOKEN=1//0gxxxx
set GDRIVE_ROOT_FOLDER_ID=1ABCxyz123...
```



#### **6. Ejecutar Prueba Inicial**

```bash
python scripts/5_export_notebook_to_pdf.py
```



### Configuración de Desarrollo

```bash
# Simular entorno de GitHub Actions
export GITHUB_ACTIONS=true

# Probar con una semana específica
export EXPORT_WEEK="2026-W16"

# Probar con un idioma específico
export EXPORT_LANGUAGE="en"
```



------

## 📁 Estructura de Archivos Generada

### Local (Temporal)

```text
temp_pdf/
├── youtube_charts_2026-W16.pdf
└── (eliminado después de subir)
```



### Google Drive (Permanente)

```text
Mi Drive/
└── (GDRIVE_ROOT_FOLDER_ID)/
    └── weekly/
        └── youtube_charts_2026-W16/
            ├── EN/
            │   ├── youtube_charts_2026-W16.ipynb
            │   └── youtube_charts_2026-W16.pdf
            └── ES/
                ├── youtube_charts_2026-W16.ipynb
                └── youtube_charts_2026-W16.pdf
```



### Estimaciones de Almacenamiento

| Métrica                           | Valor         |
| :-------------------------------- | :------------ |
| Tamaño de notebook (ejecutado)    | 500 KB - 2 MB |
| Tamaño de PDF                     | 200 KB - 1 MB |
| Almacenamiento por semana (EN+ES) | ~1-3 MB       |
| Almacenamiento anual (52 semanas) | ~50-150 MB    |
| Cuota gratuita de Google Drive    | 15 GB         |

------

## 🔧 Personalización y Configuración

### Parámetros Ajustables en el Script

```python
# En 5_export_notebook_to_pdf.py
NOTEBOOKS_EN_DIR = Path("Notebook_EN/weekly")
NOTEBOOKS_ES_DIR = Path("Notebook_ES/weekly")
TEMP_PDF_DIR = Path("temp_pdf")

# Configuración de conversión a PDF (vía nbconvert)
# --to webpdf usa Playwright Chromium
```



### Configuración del Workflow

```yaml
# En .github/workflows/5-export-notebook-pdf.yml
env:
  RETENTION_DAYS: 30       # Días para retener artefactos de depuración

timeout-minutes: 20        # Tiempo máximo total del job
```



### Agregar Soporte para Más Idiomas

```python
# Agregar nuevo directorio
NOTEBOOKS_FR_DIR = Path("Notebook_FR/weekly")

# Extender lista de idiomas
for lang, dir_path in [('en', NOTEBOOKS_EN_DIR), ('es', NOTEBOOKS_ES_DIR), ('fr', NOTEBOOKS_FR_DIR)]:
    # ... lógica de procesamiento
```



### Personalizar la Estructura de Carpetas

```python
# Cambiar el nombre de la carpeta padre
weekly_folder_id = create_or_get_folder(service, "music_charts_archive", ROOT_FOLDER_ID)

# Cambiar el nombre de la carpeta de semana
week_folder_name = f"week_{year}_{week:02d}"
```



------

## 🐛 Solución de Problemas

### Problemas Comunes y Soluciones

| Error                                 | Causa Probable                                               | Solución                                                     |
| :------------------------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| `Missing environment variables`       | Secretos no configurados                                     | Agregar `GDRIVE_CLIENT_ID`, `GDRIVE_CLIENT_SECRET`, `GDRIVE_REFRESH_TOKEN`, `GDRIVE_ROOT_FOLDER_ID` a los secretos de GitHub |
| `No notebooks found`                  | El Script 4 no se ha ejecutado o el directorio de salida está vacío | Ejecutar el Script 4 primero o verificar `Notebook_EN/weekly/` y `Notebook_ES/weekly/` |
| `nbconvert error`                     | Playwright no instalado o Chromium faltante                  | Ejecutar `playwright install chromium`                       |
| `HttpError 403: storageQuotaExceeded` | La cuenta de servicio no tiene cuota                         | Usar OAuth 2.0 con cuenta personal de Google (como está implementado) |
| `Invalid refresh token`               | Token expirado o revocado                                    | Volver a ejecutar `generate_refresh_token.py` para obtener un nuevo token |
| `Folder not found`                    | `GDRIVE_ROOT_FOLDER_ID` es incorrecto                        | Verificar el ID de la carpeta en la URL de Drive             |
| `Week detection incorrect`            | El patrón del nombre del archivo no coincide                 | Asegurar que los notebooks sigan el formato `youtube_charts_YYYY-WXX.ipynb` |

### Depuración con Registros

**Habilitar salida verbosa:**

```bash
# Configurar nivel de depuración antes de ejecutar
export LOG_LEVEL=DEBUG
python scripts/5_export_notebook_to_pdf.py
```



**Verificar notebooks locales:**

```bash
ls -la Notebook_EN/weekly/
ls -la Notebook_ES/weekly/
```



**Probar la autenticación de Google Drive por separado:**

```python
# quick_test.py
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

creds = Credentials(
    token=None,
    refresh_token=os.environ.get("GDRIVE_REFRESH_TOKEN"),
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ.get("GDRIVE_CLIENT_ID"),
    client_secret=os.environ.get("GDRIVE_CLIENT_SECRET"),
    scopes=["https://www.googleapis.com/auth/drive.file"]
)
if creds.expired:
    creds.refresh(Request())
service = build('drive', 'v3', credentials=creds)
print("¡Autenticación exitosa!")
```



### Métricas de Rendimiento

| Fase                             | Duración (típica)        | Notas                                                 |
| :------------------------------- | :----------------------- | :---------------------------------------------------- |
| Escaneo de notebooks             | <0.5 segundos            | Operaciones del sistema de archivos                   |
| Detección de semana              | <0.1 segundos            | Análisis regex + ordenamiento                         |
| Conversión a PDF (por notebook)  | 30-60 segundos           | Depende del tamaño del notebook y las visualizaciones |
| Creación de carpetas en Drive    | 1-2 segundos por carpeta | Llamadas a la API (idempotentes)                      |
| Subida de archivos (por archivo) | 2-5 segundos             | Depende del tamaño del archivo y la red               |
| **Total (EN+ES)**                | **~2-4 minutos**         | Para notebooks típicos                                |

------

## 📄 Licencia y Atribución

- **Licencia**: MIT
- **Autor**: Alfonso Droguett
  - 🔗 **LinkedIn:** [Alfonso Droguett](https://www.linkedin.com/in/adroguetth/)
  - 🌐 **Portafolio web:** [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/)
  - 📧 **Email:** adroguett.consultor@gmail.com
- **Tecnologías**:
  - Jupyter, nbconvert, Playwright (generación de PDF)
  - Google Drive API v3 (almacenamiento en la nube)
  - OAuth 2.0 (autenticación)

------

## 🤝 Contribución

1. Reportar problemas con registros completos (incluir la semana y el idioma que fallaron)
2. Proponer mejoras para la calidad de conversión a PDF (temas CSS, tamaño de página)
3. Agregar soporte para idiomas adicionales (francés, alemán, portugués, etc.)
4. Implementar exportación de rango de semanas (exportar múltiples semanas a la vez)
5. Agregar generación de metadata.json dentro de las carpetas de semana
6. Mejorar el manejo de errores para subidas parciales (lógica de reintentos)

------

## 🧪 Limitaciones Conocidas

- **Dependencia de Playwright**: Requiere descarga de Chromium (~300 MB) en la primera ejecución
- **Sin Subidas Incrementales**: Sube los mismos archivos cada ejecución (idempotente pero no consciente de diferencias)
- **Procesamiento de Semana Única**: Solo procesa la semana más reciente por ejecución
- **Expiración de Token OAuth**: Los tokens de actualización pueden expirar si no se usan durante 6+ meses (requiere reautorización)
- **Sin Compresión de PDF**: Los archivos se suben tal como están (sin optimización de tamaño)
- **Codificación de Idiomas**: EN y ES están codificados; agregar nuevos idiomas requiere modificación del script

------

**⭐ Si encuentras útil este proyecto, ¡considera darle una estrella en GitHub!**
