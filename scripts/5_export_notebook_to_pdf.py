#!/usr/bin/env python3
"""
Exporta el último notebook de Notebook_EN/weekly a PDF usando nbconvert + playwright,
y lo sube a Google Drive usando OAuth 2.0 con refresh token.

Variables de entorno requeridas en GitHub Actions:
    GDRIVE_CLIENT_ID         (de credentials.json)
    GDRIVE_CLIENT_SECRET     (de credentials.json)
    GDRIVE_REFRESH_TOKEN     (generado al autorizar)
    GDRIVE_ROOT_FOLDER_ID    (ID de la carpeta destino en "Mi unidad")
"""

import os
import sys
import subprocess
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ============================================================
# CONFIGURACIÓN
# ============================================================
NOTEBOOKS_DIR = Path("Notebook_EN/weekly")
TEMP_PDF_DIR = Path("temp_pdf")

# Crear directorio temporal
TEMP_PDF_DIR.mkdir(exist_ok=True)

# Leer secretos desde variables de entorno
CLIENT_ID = os.environ.get("GDRIVE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GDRIVE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("GDRIVE_REFRESH_TOKEN")
ROOT_FOLDER_ID = os.environ.get("GDRIVE_ROOT_FOLDER_ID")  # ID de la carpeta en Drive

# Validar que todos los secretos están presentes
if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, ROOT_FOLDER_ID]):
    print("❌ Error: Faltan variables de entorno.")
    print("   Necesitas configurar: GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET,")
    print("   GDRIVE_REFRESH_TOKEN y GDRIVE_ROOT_FOLDER_ID")
    sys.exit(1)


# ============================================================
# FUNCIONES
# ============================================================
def get_authenticated_service():
    """Obtiene servicio autenticado de Google Drive usando refresh token."""
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    # Refrescar token si es necesario
    if creds.expired:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds)


def get_latest_notebook():
    """Retorna el notebook más reciente en Notebook_EN/weekly/"""
    notebooks = list(NOTEBOOKS_DIR.glob("youtube_charts_*.ipynb"))
    if not notebooks:
        print(f"❌ No se encontraron notebooks en {NOTEBOOKS_DIR}")
        sys.exit(1)
    latest = max(notebooks, key=lambda p: p.stat().st_mtime)
    print(f"📓 Notebook seleccionado: {latest.name}")
    return latest


def convert_to_pdf(notebook_path):
    """Convierte notebook a PDF usando nbconvert + playwright"""
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
        print("❌ Error en nbconvert:")
        print(result.stderr)
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


def upload_to_drive(pdf_path, notebook_path):
    """Sube el PDF y el notebook original a Drive"""
    service = get_authenticated_service()

    print(f"📂 Usando carpeta raíz ID: {ROOT_FOLDER_ID}")

    # Crear estructura: Notebook_EN / weekly
    en_folder_id = create_or_get_folder(service, "Notebook_EN", ROOT_FOLDER_ID)
    weekly_folder_id = create_or_get_folder(service, "weekly", en_folder_id)

    # Subir PDF
    print(f"📤 Subiendo PDF: {pdf_path.name}")
    pdf_media = MediaFileUpload(pdf_path, mimetype='application/pdf')
    pdf_metadata = {'name': pdf_path.name, 'parents': [weekly_folder_id]}
    pdf_file = service.files().create(body=pdf_metadata, media_body=pdf_media, fields='id').execute()
    print(f"   ✅ PDF subido, ID: {pdf_file['id']}")

    # Subir notebook original
    print(f"📓 Subiendo notebook: {notebook_path.name}")
    ipynb_media = MediaFileUpload(notebook_path, mimetype='application/x-ipynb+json')
    ipynb_metadata = {'name': notebook_path.name, 'parents': [weekly_folder_id]}
    ipynb_file = service.files().create(body=ipynb_metadata, media_body=ipynb_media, fields='id').execute()
    print(f"   ✅ Notebook subido, ID: {ipynb_file['id']}")


# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "=" * 60)
    print("📤 EXPORTADOR DE NOTEBOOK A PDF + GOOGLE DRIVE")
    print("=" * 60)

    notebook_path = get_latest_notebook()
    pdf_path = convert_to_pdf(notebook_path)
    upload_to_drive(pdf_path, notebook_path)

    print("\n" + "=" * 60)
    print("🎉 ¡PROCESO COMPLETADO CON ÉXITO!")
    print("=" * 60)


if __name__ == "__main__":
    main()
