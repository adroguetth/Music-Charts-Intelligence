#!/usr/bin/env python3
"""
Simple YouTube Charts CSV Downloader
Optimizado para GitHub Actions - Rápido y confiable
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

def download_youtube_charts_csv():
    """
    Descarga el CSV de YouTube Charts de forma simple
    """
    print("🎵 Iniciando descarga de YouTube Charts...")
    print("=" * 60)
    
    # Configurar carpeta de salida
    output_dir = Path(os.environ.get('DATA_OUTPUT', './data'))
    output_dir.mkdir(exist_ok=True)
    
    # Headers para no ser bloqueado
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://charts.youtube.com/'
    }
    
    try:
        print("📡 Conectando a YouTube Charts...")
        
        # URL de YouTube Charts
        url = "https://charts.youtube.com/charts/TopSongs/global/weekly"
        
        # Realizar request
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Conexión exitosa (Status: {response.status_code})")
        print(f"📄 Tamaño de respuesta: {len(response.text)} bytes")
        
        # Intentar extraer datos JSON embebidos en HTML
        charts_data = extract_charts_data(response.text)
        
        if charts_data:
            # Guardar como CSV
            output_file = save_as_csv(charts_data, output_dir)
            print(f"✅ CSV guardado en: {output_file}")
            return str(output_file)
        else:
            print("⚠️ No se pudieron extraer datos del HTML")
            print("💡 Intentando método alternativo...")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Error: Timeout en la conexión (30 segundos)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la solicitud: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None

def extract_charts_data(html_content):
    """
    Extrae datos de gráficos del contenido HTML
    Busca JSON embebido en la página
    """
    import json
    import re
    
    try:
        # Patrones comunes donde YouTube embebe datos JSON
        patterns = [
            r'var ytInitialData = ({.*?});',
            r'"chartData":\s*({.*?})',
            r'"items":\s*(\[.*?\])',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html_content, re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    data = json.loads(json_str)
                    
                    # Intentar procesar datos
                    songs = process_json_data(data)
                    if songs and len(songs) > 0:
                        return songs
                except (json.JSONDecodeError, IndexError):
                    continue
        
        # Si no encuentra JSON, intenta parsear tabla HTML
        songs = extract_from_html_table(html_content)
        if songs:
            return songs
        
        return None
        
    except Exception as e:
        print(f"⚠️ Error extrayendo datos: {e}")
        return None

def process_json_data(data, max_depth=10, current_depth=0):
    """
    Procesa recursivamente estructura JSON buscando canciones
    """
    songs = []
    
    if current_depth > max_depth:
        return songs
    
    if isinstance(data, dict):
        # Buscar claves que contengan información de canciones
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                songs.extend(process_json_data(value, max_depth, current_depth + 1))
            
            # Detectar si este objeto es una canción
            if any(k in data for k in ['title', 'videoId', 'artist']):
                song = extract_song_from_dict(data)
                if song:
                    songs.append(song)
                    break
    
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                songs.extend(process_json_data(item, max_depth, current_depth + 1))
    
    return songs

def extract_song_from_dict(obj):
    """
    Extrae información de canción de un diccionario
    """
    try:
        # Variaciones de nombres de campos
        title = None
        for key in ['title', 'name', 'videoTitle', 'trackName']:
            if key in obj:
                title = obj[key]
                if isinstance(title, dict) and 'simpleText' in title:
                    title = title['simpleText']
                break
        
        artist = None
        for key in ['artist', 'artistName', 'author', 'creator']:
            if key in obj:
                artist = obj[key]
                if isinstance(artist, dict) and 'simpleText' in artist:
                    artist = artist['simpleText']
                break
        
        video_id = obj.get('videoId') or obj.get('id')
        
        if title and artist:
            return {
                'rank': obj.get('rank', ''),
                'artist': str(artist),
                'song': str(title),
                'video_id': video_id,
                'url': f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
            }
    except:
        pass
    
    return None

def extract_from_html_table(html_content):
    """
    Intenta extraer datos de tabla HTML
    """
    try:
        # Buscar tablas en el HTML
        dfs = pd.read_html(html_content)
        
        if dfs and len(dfs) > 0:
            # Usar la primera tabla encontrada
            df = dfs[0]
            
            # Renombrar columnas estándar
            if len(df.columns) >= 2:
                return df.to_dict('records')
    except:
        pass
    
    return None

def save_as_csv(data, output_dir):
    """
    Guarda datos como CSV
    """
    if not data:
        return None
    
    try:
        df = pd.DataFrame(data)
        
        # Limpiar y ordenar columnas
        if 'rank' not in df.columns:
            df.insert(0, 'rank', range(1, len(df) + 1))
        
        # Agregar fecha
        df['date'] = datetime.now().strftime('%Y-%m-%d')
        
        # Reordenar columnas
        cols_order = ['rank', 'artist', 'song', 'video_id', 'url', 'date']
        existing_cols = [c for c in cols_order if c in df.columns]
        other_cols = [c for c in df.columns if c not in existing_cols]
        df = df[existing_cols + other_cols]
        
        # Guardar
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"youtube_charts_{timestamp}.csv"
        filepath = output_dir / filename
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        print(f"📊 Datos guardados:")
        print(f"   - Filas: {len(df)}")
        print(f"   - Columnas: {len(df.columns)}")
        
        return filepath
        
    except Exception as e:
        print(f"❌ Error guardando CSV: {e}")
        return None

def create_sample_csv(output_dir):
    """
    Crea un CSV de ejemplo si todo falla
    Útil para testing en GitHub Actions
    """
    sample_data = {
        'rank': [1, 2, 3, 4, 5],
        'artist': ['Artist 1', 'Artist 2', 'Artist 3', 'Artist 4', 'Artist 5'],
        'song': ['Song A', 'Song B', 'Song C', 'Song D', 'Song E'],
        'video_id': ['xxx1', 'xxx2', 'xxx3', 'xxx4', 'xxx5'],
        'url': [
            'https://www.youtube.com/watch?v=xxx1',
            'https://www.youtube.com/watch?v=xxx2',
            'https://www.youtube.com/watch?v=xxx3',
            'https://www.youtube.com/watch?v=xxx4',
            'https://www.youtube.com/watch?v=xxx5',
        ],
        'date': [datetime.now().strftime('%Y-%m-%d')] * 5
    }
    
    df = pd.DataFrame(sample_data)
    filepath = output_dir / "youtube_charts_sample.csv"
    df.to_csv(filepath, index=False, encoding='utf-8')
    
    print(f"📋 CSV de ejemplo creado en: {filepath}")
    return filepath

def main():
    """
    Función principal
    """
    print("\n" + "=" * 60)
    print("🎵 YouTube Charts Downloader")
    print("   GitHub Actions Optimized")
    print("=" * 60 + "\n")
    
    # Detectar si está en GitHub Actions
    in_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    if in_github_actions:
        print("🔧 Ejecutando en GitHub Actions")
    else:
        print("💻 Ejecutando localmente")
    
    # Intentar descargar
    result = download_youtube_charts_csv()
    
    if result:
        print("\n" + "=" * 60)
        print("✅ ¡ÉXITO!")
        print("=" * 60)
        print(f"📁 Archivo: {result}")
        return 0
    else:
        print("\n" + "=" * 60)
        print("⚠️ Descarga automática fallida")
        print("=" * 60)
        print("\n💡 Alternativas:")
        print("1. Descarga manual: https://charts.youtube.com/charts/TopSongs/global/weekly")
        print("2. Usa Google Sheets: =IMPORTDATA('...')")
        print("3. Usa la API de YouTube (requiere API key)")
        
        # Crear CSV de ejemplo
        output_dir = Path(os.environ.get('DATA_OUTPUT', './data'))
        output_dir.mkdir(exist_ok=True)
        # create_sample_csv(output_dir)
        
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
