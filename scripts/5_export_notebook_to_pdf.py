#!/usr/bin/env python3
"""
Exporta el último notebook de Notebook_EN/weekly a PDF usando nbconvert + playwright,
y lo sube a Google Drive.

Uso:
    python scripts/5_export_notebook_to_pdf.py

Variables de entorno requeridas:
    GDRIVE_SERVICE_ACCOUNT_JSON (contenido del JSON de la cuenta de servicio, en base64)
    GDRIVE_ROOT_FOLDER_ID      (ID de la carpeta raíz en Drive donde se guardará)
    (opcional) GDRIVE_FOLDER_ID - si se quiere una subcarpeta específica, pero usaremos estructura fija.
"""

import os
import sys
import json
import base64
import subprocess
import glob
from pathlib import Path
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuración
NOTEBOOKS_DIR = Path("Notebook_EN/weekly")
TEMP_PDF_DIR = Path("temp_pdf")
TEMP_PDF_DIR.mkdir(exist_ok=True)

# Variables de entorno
SERVICE_ACCOUNT_JSON_B64 = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
ROOT_FOLDER_ID = os.environ.get("GDRIVE_ROOT_FOLDER_ID")

if not SERVICE_ACCOUNT_JSON_B64 or not ROOT_FOLDER_ID:
    print("❌ Faltan variables de entorno: GDRIVE_SERVICE_ACCOUNT_JSON y GDRIVE_ROOT_FOLDER_ID")
    sys.exit(1)

def get_latest_notebook():
    """Retorna la ruta del notebook más reciente en Notebook_EN/weekly/"""
    notebooks = list(NOTEBOOKS_DIR.glob("youtube_charts_*.ipynb"))
    if not notebooks:
        print("❌ No se encontraron notebooks en", NOTEBOOKS_DIR)
        sys.exit(1)
    # Ordenar por fecha de modificación (más reciente primero)
    latest = max(notebooks, key=lambda p: p.stat().st_mtime)
    print(f"📓 Notebook seleccionado: {latest.name}")
    return latest

def convert_to_pdf(notebook_path):
    """Convierte notebook a PDF usando nbconvert + playwright (Chromium)"""
    pdf_path = TEMP_PDF_DIR / f"{notebook_path.stem}.pdf"
    # Asegurar que playwright está instalado y los navegadores descargados
    subprocess.run(["playwright", "install", "chromium"], check=False)
    # Ejecutar nbconvert con --to webpdf (usa Chromium headless)
    cmd = [
        "jupyter", "nbconvert", "--to", "webpdf",
        "--output", str(pdf_path),
        str(notebook_path)
    ]
    print(f"🔄 Convirtiendo {notebook_path.name} a PDF...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Error en nbconvert:")
        print(result.stderr)
        sys.exit(1)
    print(f"✅ PDF generado: {pdf_path}")
    return pdf_path

def create_or_get_folder(service, folder_name, parent_id):
    """Crea una carpeta en Drive si no existe, retorna su ID."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
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

def upload_to_drive(pdf_path, notebook_path):
    """Sube el PDF y el notebook original a Drive en la ruta Notebook_EN/weekly/"""
    # Decodificar cuenta de servicio
    service_account_info = json.loads(base64.b64decode(SERVICE_ACCOUNT_JSON_B64))
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    service = build('drive', 'v3', credentials=creds)

    # Crear estructura de carpetas: Notebook_EN / weekly
    en_folder_id = create_or_get_folder(service, "Notebook_EN", ROOT_FOLDER_ID)
    weekly_folder_id = create_or_get_folder(service, "weekly", en_folder_id)

    # Subir PDF
    pdf_media = MediaFileUpload(pdf_path, mimetype='application/pdf')
    pdf_file_name = pdf_path.name
    pdf_metadata = {'name': pdf_file_name, 'parents': [weekly_folder_id]}
    pdf_file = service.files().create(body=pdf_metadata, media_body=pdf_media, fields='id').execute()
    print(f"📤 PDF subido a Drive, ID: {pdf_file['id']}")

    # Subir también el notebook original (ipynb) como respaldo
    ipynb_media = MediaFileUpload(notebook_path, mimetype='application/x-ipynb+json')
    ipynb_metadata = {'name': notebook_path.name, 'parents': [weekly_folder_id]}
    ipynb_file = service.files().create(body=ipynb_metadata, media_body=ipynb_media, fields='id').execute()
    print(f"📓 Notebook original subido a Drive, ID: {ipynb_file['id']}")

def main():
    notebook_path = get_latest_notebook()
    pdf_path = convert_to_pdf(notebook_path)
    upload_to_drive(pdf_path, notebook_path)
    print("🎉 Proceso completado con éxito.")

if __name__ == "__main__":
    main()
