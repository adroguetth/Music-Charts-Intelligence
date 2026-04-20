#!/usr/bin/env python3
"""
Exporta los notebooks (EN y ES) de la semana más reciente a PDF y los sube a Google Drive.
Crea una carpeta por semana (ej. youtube_charts_2026-W16) y dentro:
  - EN/ (notebook.ipynb + notebook.pdf)
  - ES/ (notebook.ipynb + notebook.pdf)

Uso:
    python scripts/5_export_notebook_to_pdf_v3.py

Variables de entorno requeridas:
    GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN, GDRIVE_ROOT_FOLDER_ID
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ============================================================
# CONFIGURACIÓN
# ============================================================
NOTEBOOKS_EN_DIR = Path("Notebook_EN/weekly")
NOTEBOOKS_ES_DIR = Path("Notebook_ES/weekly")
TEMP_PDF_DIR = Path("temp_pdf")
TEMP_PDF_DIR.mkdir(exist_ok=True)

# Leer secretos
CLIENT_ID = os.environ.get("GDRIVE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GDRIVE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("GDRIVE_REFRESH_TOKEN")
ROOT_FOLDER_ID = os.environ.get("GDRIVE_ROOT_FOLDER_ID")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, ROOT_FOLDER_ID]):
    print("❌ Faltan variables de entorno.")
    sys.exit(1)


# ============================================================
# FUNCIONES DE AYUDA
# ============================================================
def get_authenticated_service():
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


def get_week_from_filename(filename: str) -> tuple:
    """Extrae (año, semana) del nombre del archivo: youtube_charts_2026-W16.ipynb -> (2026, 16)"""
    match = re.search(r'(\d{4})-W(\d{1,2})', filename)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (0, 0)


def get_latest_week_from_all_notebooks():
    """Escanea ambas carpetas y retorna la semana más reciente (año, semana)."""
    all_notebooks = []
    for dir_path in [NOTEBOOKS_EN_DIR, NOTEBOOKS_ES_DIR]:
        if dir_path.exists():
            for nb in dir_path.glob("youtube_charts_*.ipynb"):
                week = get_week_from_filename(nb.name)
                if week != (0, 0):
                    all_notebooks.append((week, nb))
    if not all_notebooks:
        return None
    # Ordenar por semana descendente y tomar la primera
    all_notebooks.sort(key=lambda x: x[0], reverse=True)
    return all_notebooks[0][0]  # (year, week)


def convert_to_pdf(notebook_path: Path) -> Path:
    """Convierte notebook a PDF, devuelve ruta del PDF generado."""
    pdf_filename = f"{notebook_path.stem}.pdf"
    pdf_path = TEMP_PDF_DIR / pdf_filename

    # Asegurar playwright
    subprocess.run(["playwright", "install", "chromium"], check=False)

    cmd = [
        "jupyter", "nbconvert", "--to", "webpdf",
        "--output-dir", str(TEMP_PDF_DIR),
        "--output", pdf_filename,
        str(notebook_path)
    ]
    print(f"🔄 Convirtiendo {notebook_path.name} a PDF...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Error en nbconvert:", result.stderr)
        sys.exit(1)
    if not pdf_path.exists():
        print(f"❌ No se encontró el PDF en {pdf_path}")
        sys.exit(1)
    print(f"✅ PDF generado: {pdf_path}")
    return pdf_path


def create_or_get_folder(service, folder_name, parent_id):
    """Crea una carpeta si no existe, retorna su ID."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    files = response.get('files', [])
    if files:
        print(f"   📁 Carpeta existente: {folder_name}")
        return files[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        print(f"   📁 Carpeta creada: {folder_name}")
        return folder['id']


def upload_file(service, file_path, parent_folder_id, mime_type):
    """Sube un archivo a una carpeta de Drive."""
    media = MediaFileUpload(file_path, mimetype=mime_type)
    metadata = {'name': file_path.name, 'parents': [parent_folder_id]}
    uploaded = service.files().create(body=metadata, media_body=media, fields='id').execute()
    print(f"   ✅ Subido: {file_path.name}")
    return uploaded['id']


# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "=" * 60)
    print("📤 EXPORTADOR DE NOTEBOOKS (EN + ES) A PDF + DRIVE")
    print("=" * 60)

    # Verificar que las carpetas de notebooks existen
    if not NOTEBOOKS_EN_DIR.exists() and not NOTEBOOKS_ES_DIR.exists():
        print("❌ No existen las carpetas Notebook_EN/weekly o Notebook_ES/weekly")
        sys.exit(1)

    # 1. Determinar la semana más reciente entre todos los notebooks (EN y ES)
    latest_week = get_latest_week_from_all_notebooks()
    if not latest_week:
        print("❌ No se encontraron notebooks en ninguna carpeta.")
        sys.exit(1)

    year, week = latest_week
    week_str = f"{year}-W{week:02d}"
    print(f"\n📆 Semana más reciente detectada: {week_str}")

    # 2. Buscar notebooks para esa semana en cada idioma
    en_notebook = None
    es_notebook = None

    # Buscar en EN: archivo que contenga la semana (ej. youtube_charts_2026-W16.ipynb)
    en_pattern = f"*{week_str}*.ipynb"
    en_matches = list(NOTEBOOKS_EN_DIR.glob(en_pattern)) if NOTEBOOKS_EN_DIR.exists() else []
    if en_matches:
        # Si hay múltiples (ej. con sufijos), tomar el primero
        en_notebook = en_matches[0]
        print(f"   🇬🇧 Notebook EN encontrado: {en_notebook.name}")

    # Buscar en ES
    es_matches = list(NOTEBOOKS_ES_DIR.glob(en_pattern)) if NOTEBOOKS_ES_DIR.exists() else []
    if es_matches:
        es_notebook = es_matches[0]
        print(f"   🇪🇸 Notebook ES encontrado: {es_notebook.name}")

    if not en_notebook and not es_notebook:
        print("❌ No se encontraron notebooks para la semana más reciente.")
        sys.exit(1)

    # 3. Convertir a PDF los que existan
    pdfs = {}
    if en_notebook:
        pdfs['en'] = convert_to_pdf(en_notebook)
    if es_notebook:
        pdfs['es'] = convert_to_pdf(es_notebook)

    # 4. Subir a Drive
    service = get_authenticated_service()

    # Crear carpeta raíz para la semana (ej. "youtube_charts_2026-W16")
    week_folder_name = f"youtube_charts_{week_str}"
    print(f"\n📁 Creando/verificando carpeta: {week_folder_name}")
    week_folder_id = create_or_get_folder(service, week_folder_name, ROOT_FOLDER_ID)

    # Subir cada idioma
    for lang, notebook_path in [('en', en_notebook), ('es', es_notebook)]:
        if not notebook_path:
            continue
        # Crear subcarpeta del idioma (EN o ES)
        print(f"\n🌐 Procesando idioma: {lang.upper()}")
        lang_folder_id = create_or_get_folder(service, lang.upper(), week_folder_id)

        # Subir notebook original
        print(f"   📓 Subiendo notebook...")
        upload_file(service, notebook_path, lang_folder_id, 'application/x-ipynb+json')
        # Subir PDF
        print(f"   📄 Subiendo PDF...")
        pdf_path = pdfs[lang]
        upload_file(service, pdf_path, lang_folder_id, 'application/pdf')

    # 5. Limpiar archivos temporales
    for f in TEMP_PDF_DIR.glob("*.pdf"):
        f.unlink()
    print("\n🧹 Archivos temporales eliminados.")

    print("\n" + "=" * 60)
    print("🎉 ¡EXPORTACIÓN COMPLETADA!")
    print(f"📁 Carpeta en Drive: {week_folder_name}")
    print("=" * 60)


if __name__ == "__main__":
    main()
