#!/usr/bin/env python3
"""
1_descargar.py - Descarga el CSV interceptando la API de YouTube Charts
"""

import asyncio
import os
import sys
import json
import csv
from datetime import datetime
from pathlib import Path
import requests

# Configuración
OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def download_chart_with_api():
    """Encuentra y descarga usando la API interna"""
    try:
        from playwright.async_api import async_playwright
        import re
        
        print("🚀 Iniciando Playwright para encontrar API...")
        
        async with async_playwright() as p:
            # Navegador más rápido
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800}
            )
            
            page = await context.new_page()
            
            # Variable para capturar la URL de la API
            api_url = None
            
            # Interceptar requests
            async def handle_request(request):
                nonlocal api_url
                url = request.url
                
                # Buscar endpoints que parezcan APIs de datos
                if any(pattern in url.lower() for pattern in [
                    '/chart?', 
                    '/export?', 
                    'download.csv', 
                    'export.csv',
                    'data.csv',
                    'chart.csv',
                    'top100.csv'
                ]):
                    print(f"🔍 Posible API encontrada: {url}")
                    api_url = url
                
                # También buscar respuestas JSON que contengan datos del chart
                if 'application/json' in request.headers.get('content-type', ''):
                    try:
                        response = await request.response()
                        if response:
                            body = await response.text()
                            if '"rank"' in body.lower() or '"track"' in body.lower():
                                print(f"📊 JSON con datos encontrado: {url}")
                                api_url = url
                    except:
                        pass
            
            # Escuchar requests
            page.on("request", handle_request)
            
            try:
                # Navegar a la página
                url = "https://charts.youtube.com/charts/TopSongs/global/weekly"
                print(f"🌐 Navegando a: {url}")
                
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Hacer clic en el botón para activar la API
                print("🖱️  Intentando activar descarga...")
                
                # Intentar diferentes formas de activar la descarga
                selectores = [
                    'a[download]',
                    'button[aria-label*="Download"]',
                    'button[title*="Download"]',
                    '[data-tooltip*="Download"]',
                    'iron-icon#icon',
                    'paper-icon-button',
                    'ytmc-download-button'
                ]
                
                for selector in selectores:
                    try:
                        elementos = await page.query_selector_all(selector)
                        if elementos:
                            print(f"✅ Elemento encontrado: {selector}")
                            await elementos[0].click()
                            await asyncio.sleep(2)  # Esperar a que se active la API
                            break
                    except:
                        continue
                
                # Esperar un poco más para capturar requests
                print("⏳ Esperando llamadas a API...")
                await asyncio.sleep(5)
                
                if api_url:
                    print(f"🎯 URL de API capturada: {api_url}")
                    
                    # Cerrar Playwright - ya no lo necesitamos
                    await browser.close()
                    
                    # Ahora descargar directamente con requests
                    return await download_direct_from_api(api_url)
                else:
                    print("⚠️  No se encontró API, intentando método alternativo...")
                    
                    # Método alternativo: buscar datos en el HTML
                    return await extract_from_page_html(page)
                    
            finally:
                await browser.close()
                
    except Exception as e:
        print(f"❌ Error con Playwright: {e}")
        import traceback
        traceback.print_exc()
        return None

async def download_direct_from_api(api_url):
    """Descarga directamente desde la URL de la API"""
    print(f"📥 Descargando desde API: {api_url}")
    
    try:
        # Headers para parecer un navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/csv,application/json',
            'Referer': 'https://charts.youtube.com/'
        }
        
        # Hacer la petición
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Determinar el tipo de contenido
        content_type = response.headers.get('content-type', '').lower()
        
        # Generar nombre de archivo
        fecha = datetime.now().strftime("%Y%m%d")
        
        if 'csv' in content_type or response.text.strip().startswith('rank,'):
            # Es CSV
            filename = OUTPUT_DIR / f"youtube_top_songs_{fecha}.csv"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"✅ CSV descargado: {filename}")
            return str(filename)
            
        elif 'json' in content_type or response.text.strip().startswith('{') or response.text.strip().startswith('['):
            # Es JSON, convertirlo a CSV
            try:
                data = response.json()
                filename = await convert_json_to_csv(data, fecha)
                return filename
            except:
                # Guardar el JSON por si acaso
                json_filename = OUTPUT_DIR / f"youtube_data_{fecha}.json"
                with open(json_filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"⚠️  Datos JSON guardados (necesitan conversión): {json_filename}")
                return None
                
        else:
            # Guardar como está
            filename = OUTPUT_DIR / f"youtube_data_{fecha}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"⚠️  Datos guardados como texto: {filename}")
            return str(filename)
            
    except Exception as e:
        print(f"❌ Error descargando desde API: {e}")
        return None

async def extract_from_page_html(page):
    """Extrae datos directamente del HTML de la página"""
    print("📄 Extrayendo datos del HTML...")
    
    try:
        # Obtener el HTML
        html = await page.content()
        
        # Buscar datos en el HTML
        import re
        
        # Patrones para buscar datos de tabla
        patterns = [
            r'<tr[^>]*>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>(.*?)</td>.*?</tr>',
            r'"rank":\s*(\d+).*?"title":\s*"(.*?)".*?"artist":\s*"(.*?)"',
            r'(\d+)\s*-\s*(.*?)\s*-\s*(.*?)(?:\n|$)',
        ]
        
        datos = []
        
        # Método 1: Buscar por estructura de tabla
        print("🔍 Buscando estructura de tabla...")
        table_match = re.search(r'<table[^>]*>.*?</table>', html, re.DOTALL)
        if table_match:
            table_html = table_match.group(0)
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
            
            for row in rows[:101]:  # Máximo 100 filas
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) >= 3:
                    rank = re.sub(r'<[^>]+>', '', cells[0]).strip()
                    track = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    artist = re.sub(r'<[^>]+>', '', cells[2]).strip()
                    
                    if rank.isdigit() and track and artist:
                        datos.append([rank, track, artist])
        
        # Método 2: Buscar datos estructurados en JSON dentro del HTML
        print("🔍 Buscando datos JSON...")
        json_patterns = [
            r'__INITIAL_DATA__\s*=\s*(\{.*?\})',
            r'ytInitialData\s*=\s*(\{.*?\})',
            r'"chartData":\s*(\[.*?\])',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1)
                    data = json.loads(json_str)
                    datos = extract_from_json(data)
                    if datos:
                        break
                except:
                    continue
        
        if datos:
            # Guardar como CSV
            fecha = datetime.now().strftime("%Y%m%d")
            filename = OUTPUT_DIR / f"youtube_top_songs_{fecha}.csv"
            
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Rank', 'Track Name', 'Artist Names', 'Views', 'Weeks on Chart'])
                
                for i, (rank, track, artist) in enumerate(datos[:100], 1):
                    writer.writerow([i, track, artist, '', ''])
            
            print(f"✅ {len(datos)} canciones extraídas del HTML: {filename}")
            return str(filename)
        else:
            print("❌ No se pudieron extraer datos del HTML")
            return None
            
    except Exception as e:
        print(f"❌ Error extrayendo del HTML: {e}")
        return None

def extract_from_json(data):
    """Extrae datos del chart desde JSON"""
    datos = []
    
    def search_in_dict(obj, path=""):
        if isinstance(obj, dict):
            # Buscar arrays que contengan datos de canciones
            for key, value in obj.items():
                if isinstance(value, list) and len(value) > 0:
                    first_item = value[0]
                    if isinstance(first_item, dict):
                        # Verificar si tiene campos como rank, title, artist
                        if all(k in first_item for k in ['rank', 'title', 'artist']):
                            print(f"✅ Datos encontrados en: {path}.{key}")
                            for item in value:
                                if isinstance(item, dict):
                                    rank = item.get('rank', '')
                                    track = item.get('title', item.get('track', ''))
                                    artist = item.get('artist', item.get('artistNames', ''))
                                    if rank and track:
                                        datos.append([str(rank), str(track), str(artist)])
                            return True
                
                # Recursión
                if search_in_dict(value, f"{path}.{key}"):
                    return True
                    
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if search_in_dict(item, f"{path}[{i}]"):
                    return True
                    
        return False
    
    search_in_dict(data, "root")
    return datos

async def convert_json_to_csv(data, fecha):
    """Convierte datos JSON a CSV"""
    try:
        filename = OUTPUT_DIR / f"youtube_top_songs_{fecha}.csv"
        
        # Intentar extraer datos del JSON
        datos = extract_from_json(data)
        
        if datos:
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Rank', 'Track Name', 'Artist Names', 'Views', 'Weeks on Chart'])
                
                for row in datos[:100]:
                    writer.writerow(row)
            
            print(f"✅ JSON convertido a CSV: {filename}")
            return str(filename)
        else:
            print("❌ No se pudieron extraer datos del JSON")
            return None
            
    except Exception as e:
        print(f"❌ Error convirtiendo JSON: {e}")
        return None

def main():
    """Función principal"""
    print("=" * 60)
    print("🎵 YOUTUBE MUSIC CHARTS DOWNLOADER (Método API)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if os.getenv('GITHUB_ACTIONS'):
        print("⚡ Ejecutando en GitHub Actions")
    
    # Ejecutar descarga
    csv_path = asyncio.run(download_chart_with_api())
    
    if csv_path and os.path.exists(csv_path):
        print(f"\n🎉 ¡ÉXITO! Chart descargado correctamente")
        print(f"📁 Ruta: {csv_path}")
        
        # Mostrar tamaño
        size_kb = os.path.getsize(csv_path) / 1024
        print(f"📦 Tamaño: {size_kb:.1f} KB")
        
        # Mostrar primeras líneas
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:5]
                print("\n📋 Primeras líneas:")
                for line in lines:
                    print(f"  {line.strip()}")
        except:
            pass
            
        return 0
    else:
        print("\n❌ FALLÓ la descarga del chart")
        print("💡 Posibles soluciones:")
        print("   1. YouTube podría haber cambiado su estructura")
        print("   2. Intenta ejecutar localmente primero para debuggear")
        print("   3. Revisa si necesitas aceptar cookies")
        return 1

if __name__ == "__main__":
    sys.exit(main())
