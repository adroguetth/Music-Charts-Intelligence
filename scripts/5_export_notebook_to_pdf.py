#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Notebook to PDF Exporter + Google Drive Uploader - Main Orchestrator
====================================================================
Exports the most recent notebooks (EN and ES) to PDF and uploads them to Google Drive.

This script orchestrates:
1. Scan both Notebook_EN/weekly and Notebook_ES/weekly directories
2. Determine the most recent week across all available notebooks (using ISO week comparison)
3. Convert each found notebook (EN and/or ES) to PDF using nbconvert + playwright
4. Upload to Google Drive with the following structure:
   weekly/
     └── youtube_charts_YYYY-WXX/
         ├── EN/
         │   ├── notebook.ipynb
         │   └── notebook.pdf
         └── ES/
             ├── notebook.ipynb
             └── notebook.pdf

Requirements:
- Python 3.7+
- jupyter, nbconvert, playwright
- google-api-python-client, google-auth-oauthlib

Environment Variables:
    GDRIVE_CLIENT_ID       (from credentials.json)
    GDRIVE_CLIENT_SECRET   (from credentials.json)
    GDRIVE_REFRESH_TOKEN   (generated once via OAuth)
    GDRIVE_ROOT_FOLDER_ID  (ID of the target folder in "My Drive")

Author: Alfonso Droguett
License: MIT
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

# ============================================================================
# PATH CONFIGURATION
# ============================================================================
NOTEBOOKS_EN_DIR = Path("Notebook_EN/weekly")
NOTEBOOKS_ES_DIR = Path("Notebook_ES/weekly")
TEMP_PDF_DIR = Path("temp_pdf")
TEMP_PDF_DIR.mkdir(exist_ok=True)

# ============================================================================
# ENVIRONMENT VARIABLES (required)
# ============================================================================
CLIENT_ID = os.environ.get("GDRIVE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GDRIVE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("GDRIVE_REFRESH_TOKEN")
ROOT_FOLDER_ID = os.environ.get("GDRIVE_ROOT_FOLDER_ID")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, ROOT_FOLDER_ID]):
    print("ERROR: Missing required environment variables.")
    print("Required: GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN, GDRIVE_ROOT_FOLDER_ID")
    sys.exit(1)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_authenticated_service():
    """
    Build and return an authenticated Google Drive service using a refresh token.

    Creates Credentials object from client_id, client_secret, and refresh_token.
    Automatically refreshes the access token if expired.

    Returns:
        googleapiclient.discovery.Resource: Authenticated Drive service.
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


def get_week_from_filename(filename: str) -> tuple:
    """
    Extract ISO week (year, week number) from a notebook filename.

    Pattern: youtube_charts_YYYY-WXX.ipynb -> (YYYY, XX)

    Args:
        filename: The notebook filename.

    Returns:
        tuple: (year, week) as integers. Returns (0, 0) if no match.
    """
    match = re.search(r'(\d{4})-W(\d{1,2})', filename)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (0, 0)


def get_latest_week_from_all_notebooks() -> tuple:
    """
    Scan EN and ES notebook directories to find the most recent week.

    Collects all notebooks, extracts their week identifiers, and returns the
    maximum (year, week) across all available files.

    Returns:
        tuple: (year, week) of the most recent week, or None if no notebooks found.
    """
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


def convert_to_pdf(notebook_path: Path) -> Path:
    """
    Convert a Jupyter notebook to PDF using nbconvert with playwright backend.

    Args:
        notebook_path: Path to the .ipynb file.

    Returns:
        Path: Path to the generated PDF file.

    Exits:
        On conversion failure, prints error and exits with code 1.
    """
    pdf_filename = f"{notebook_path.stem}.pdf"
    pdf_path = TEMP_PDF_DIR / pdf_filename

    # Ensure playwright browsers are installed (idempotent)
    subprocess.run(["playwright", "install", "chromium"], check=False)

    cmd = [
        "jupyter", "nbconvert", "--to", "webpdf",
        "--output-dir", str(TEMP_PDF_DIR),
        "--output", pdf_filename,
        str(notebook_path)
    ]
    print(f"Converting: {notebook_path.name} to PDF...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("nbconvert error:")
        print(result.stderr)
        sys.exit(1)

    if not pdf_path.exists():
        print(f"PDF not found at expected path: {pdf_path}")
        sys.exit(1)

    print(f"PDF generated: {pdf_path}")
    return pdf_path


def create_or_get_folder(service, folder_name: str, parent_id: str) -> str:
    """
    Create a folder in Google Drive if it doesn't exist, otherwise return its ID.

    Args:
        service: Authenticated Drive service.
        folder_name: Name of the folder to create or locate.
        parent_id: ID of the parent folder.

    Returns:
        str: Folder ID.
    """
    query = (f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' "
             f"and '{parent_id}' in parents and trashed=false")
    response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    files = response.get('files', [])

    if files:
        print(f"   Folder exists: {folder_name}")
        return files[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        print(f"   Folder created: {folder_name}")
        return folder['id']


def upload_file(service, file_path: Path, parent_folder_id: str, mime_type: str) -> str:
    """
    Upload a file to Google Drive under a specified parent folder.

    Args:
        service: Authenticated Drive service.
        file_path: Local path to the file.
        parent_folder_id: ID of the destination folder.
        mime_type: MIME type of the file.

    Returns:
        str: ID of the uploaded file.
    """
    media = MediaFileUpload(file_path, mimetype=mime_type)
    metadata = {'name': file_path.name, 'parents': [parent_folder_id]}
    uploaded = service.files().create(body=metadata, media_body=media, fields='id').execute()
    print(f"   Uploaded: {file_path.name}")
    return uploaded['id']


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main execution function.

    Workflow:
    1. Verify that notebook directories exist.
    2. Find the most recent week across all notebooks (EN + ES).
    3. Locate the notebook for that week in each language.
    4. Convert each notebook to PDF.
    5. Build the target folder hierarchy in Drive:
       root_folder/weekly/week_folder/EN/ and /ES/
    6. Upload both .ipynb and .pdf files.
    7. Clean up temporary files.
    """
    print("\n" + "=" * 60)
    print("NOTEBOOK TO PDF EXPORTER + GOOGLE DRIVE UPLOADER")
    print("=" * 60)

    # Validate source directories
    if not NOTEBOOKS_EN_DIR.exists() and not NOTEBOOKS_ES_DIR.exists():
        print("ERROR: Neither Notebook_EN/weekly nor Notebook_ES/weekly exists.")
        sys.exit(1)

    # Determine the most recent week
    latest_week = get_latest_week_from_all_notebooks()
    if not latest_week:
        print("ERROR: No notebooks found in any language directory.")
        sys.exit(1)

    year, week = latest_week
    week_str = f"{year}-W{week:02d}"
    print(f"\nMost recent week detected: {week_str}")

    # Locate notebooks for that week in each language
    en_notebook = None
    es_notebook = None

    en_pattern = f"*{week_str}*.ipynb"
    if NOTEBOOKS_EN_DIR.exists():
        en_matches = list(NOTEBOOKS_EN_DIR.glob(en_pattern))
        if en_matches:
            en_notebook = en_matches[0]
            print(f"   EN notebook found: {en_notebook.name}")

    if NOTEBOOKS_ES_DIR.exists():
        es_matches = list(NOTEBOOKS_ES_DIR.glob(en_pattern))
        if es_matches:
            es_notebook = es_matches[0]
            print(f"   ES notebook found: {es_notebook.name}")

    if not en_notebook and not es_notebook:
        print("ERROR: No notebooks found for the most recent week.")
        sys.exit(1)

    # Convert to PDF
    pdfs = {}
    if en_notebook:
        pdfs['en'] = convert_to_pdf(en_notebook)
    if es_notebook:
        pdfs['es'] = convert_to_pdf(es_notebook)

    # Upload to Drive
    service = get_authenticated_service()

    # Create or get the parent "weekly" folder
    print(f"\nCreating/verifying parent folder: weekly")
    weekly_folder_id = create_or_get_folder(service, "weekly", ROOT_FOLDER_ID)

    # Create or get the week-specific folder inside "weekly"
    week_folder_name = f"youtube_charts_{week_str}"
    print(f"\nCreating/verifying week folder: {week_folder_name}")
    week_folder_id = create_or_get_folder(service, week_folder_name, weekly_folder_id)

    # Upload each language's notebook and PDF
    for lang, notebook_path in [('en', en_notebook), ('es', es_notebook)]:
        if not notebook_path:
            continue
        print(f"\nProcessing language: {lang.upper()}")
        lang_folder_id = create_or_get_folder(service, lang.upper(), week_folder_id)

        print("   Uploading notebook...")
        upload_file(service, notebook_path, lang_folder_id, 'application/x-ipynb+json')
        print("   Uploading PDF...")
        pdf_path = pdfs[lang]
        upload_file(service, pdf_path, lang_folder_id, 'application/pdf')

    # Clean up temporary files
    for f in TEMP_PDF_DIR.glob("*.pdf"):
        f.unlink()
    print("\nTemporary files removed.")

    print("\n" + "=" * 60)
    print("EXPORT COMPLETED SUCCESSFULLY")
    print(f"Drive structure:")
    print(f"   {ROOT_FOLDER_ID}/")
    print(f"   └── weekly/")
    print(f"       └── {week_folder_name}/")
    print(f"           ├── EN/ (notebook.ipynb + .pdf)")
    print(f"           └── ES/ (notebook.ipynb + .pdf)")
    print("=" * 60)


if __name__ == "__main__":
    main()
