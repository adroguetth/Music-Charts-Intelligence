#!/usr/bin/env python3
"""
Upload PDF files to Google Drive with proper folder structure.

This script uploads generated PDFs to Google Drive maintaining the structure:
notebook/EN/weekly/YYYY-WXX/filename.pdf
notebook/ES/weekly/YYYY-WXX/filename.pdf
"""

import json
import base64
import os
import sys
from pathlib import Path
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def get_or_create_folder(service, parent_id: str, folder_name: str) -> str:
    """
    Get existing folder ID or create a new one.
    
    Args:
        service: Google Drive service instance
        parent_id: Parent folder ID
        folder_name: Name of folder to find/create
    
    Returns:
        Folder ID
    """
    # Search for existing folder
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    
    if folders:
        return folders[0]['id']
    
    # Create new folder
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    print(f"Created folder: {folder_name} (ID: {folder.get('id')})")
    return folder.get('id')

def upload_file(service, file_path: Path, parent_id: str) -> str:
    """
    Upload a file to Google Drive.
    
    Args:
        service: Google Drive service instance
        file_path: Path to file to upload
        parent_id: Parent folder ID
        
    Returns:
        File ID
    """
    file_metadata = {
        'name': file_path.name,
        'parents': [parent_id]
    }
    
    media = MediaFileUpload(
        file_path,
        mimetype='application/pdf',
        resumable=True
    )
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    print(f"  Uploaded: {file_path.name} (ID: {file.get('id')})")
    return file.get('id')

def main():
    """Main upload function."""
    # Get environment variables
    service_account_b64 = os.environ.get('GDRIVE_SERVICE_ACCOUNT')
    root_folder_id = os.environ.get('GDRIVE_ROOT_FOLDER_ID')
    week = os.environ.get('WEEK', '')
    
    if not service_account_b64:
        print("Error: Missing GDRIVE_SERVICE_ACCOUNT environment variable")
        sys.exit(1)
    
    if not root_folder_id:
        print("Error: Missing GDRIVE_ROOT_FOLDER_ID environment variable")
        sys.exit(1)
    
    if not week:
        print("Error: Missing WEEK environment variable")
        sys.exit(1)
    
    print(f"Uploading PDFs for week: {week}")
    print(f"Root folder ID: {root_folder_id}")
    
    # Decode service account credentials
    try:
        credentials_json = base64.b64decode(service_account_b64).decode('utf-8')
        creds_dict = json.loads(credentials_json)
    except Exception as e:
        print(f"Error decoding service account credentials: {e}")
        sys.exit(1)
    
    # Create credentials object
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    
    # Build Drive service
    service = build('drive', 'v3', credentials=credentials)
    
    # Create folder structure: EN/weekly/YYYY-WXX/
    en_weekly_folder = get_or_create_folder(service, root_folder_id, 'EN')
    en_weekly_sub = get_or_create_folder(service, en_weekly_folder, 'weekly')
    en_week_folder = get_or_create_folder(service, en_weekly_sub, week)
    
    # Upload English PDFs
    en_pdfs = Path('pdf_output/EN').glob('*.pdf')
    en_count = 0
    for pdf_path in en_pdfs:
        print(f"Uploading EN: {pdf_path.name}")
        upload_file(service, pdf_path, en_week_folder)
        en_count += 1
    
    # Create folder structure: ES/weekly/YYYY-WXX/
    es_weekly_folder = get_or_create_folder(service, root_folder_id, 'ES')
    es_weekly_sub = get_or_create_folder(service, es_weekly_folder, 'weekly')
    es_week_folder = get_or_create_folder(service, es_weekly_sub, week)
    
    # Upload Spanish PDFs
    es_pdfs = Path('pdf_output/ES').glob('*.pdf')
    es_count = 0
    for pdf_path in es_pdfs:
        print(f"Uploading ES: {pdf_path.name}")
        upload_file(service, pdf_path, es_week_folder)
        es_count += 1
    
    print(f"\nUpload complete!")
    print(f"  EN PDFs uploaded: {en_count}")
    print(f"  ES PDFs uploaded: {es_count}")
    print(f"  Drive location: notebook/EN/weekly/{week}/ and notebook/ES/weekly/{week}/")

if __name__ == "__main__":
    main()
