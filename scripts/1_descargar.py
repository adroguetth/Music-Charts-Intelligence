#!/usr/bin/env python3
"""
1_descargar.py - Descarga automática del CSV de YouTube Charts
Versión mejorada para GitHub Actions
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Configuración
OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def download_chart():
    """Descarga el chart usando Playwright"""
    try:
        from playwright.async_api import async_playwright
        
        print("🚀 Iniciando Playwright...")
        
        async with async_playwright() as p:
            # Configurar navegador para GitHub Actions
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer'
                ]
            )
            
            context = await browser.new_context(
                accept_downloads=True,
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            try:
                # Navegar a la página
                url = "https://charts.youtube.com/charts/TopSongs/global/weekly"
                print(f"🌐 Navegando a: {url}")
                
                await page.goto(url, wait_until='networkidle', timeout=60000)
                
                # Esperar a que cargue el contenido
                await page.wait_for_load_state('networkidle')
                
                # Estrategia 1: Buscar botones de descarga comunes
                print("🔍 Buscando botón de descarga...")
                
                # Intentar diferentes selectores
                selectores = [
                    'button[aria-label*="Download"]',
                    'button[title*="Download"]',
                    'a[download]',
                    'iron-icon#icon',
                    'paper-icon-button',
                    'ytmc-download-button',
                    'svg path[d*="M17,18v1H6v-1H17z"]',  # Path específico que encontraste
                ]
                
                boton = None
                for selector in selectores:
                    try:
                        elementos = await page.query_selector_all(selector)
                        if elementos:
                            boton = elementos[0]
                            print(f"✅ Botón encontrado: {selector}")
                            break
                    except:
                        continue
                
                if not boton:
                    # Estrategia 2: Buscar por texto
                    print("⚠️  Botón no encontrado por selectores, buscando por texto...")
                    try:
                        boton = await page.query_selector('text/Download')
                        if not boton:
                            boton = await page.query_selector('text/Descargar')
                    except:
                        pass
                
                if not boton:
                    # Guardar screenshot para debugging
                    debug_path = OUTPUT_DIR / "debug_page.png"
                    await page.screenshot(path=str(debug_path))
                    print(f"❌ Botón no encontrado. Screenshot guardado: {debug_path}")
                    return None
                
                # Preparar descarga
                print("📥 Preparando descarga...")
                
                async with page.expect_download() as download_info:
                    # Intentar hacer clic
                    try:
                        await boton.click()
                    except:
                        # Si falla el clic, usar JavaScript
                        await page.evaluate('(element) => element.click()', boton)
                
                # Esperar descarga
                download = await download_info.value
                
                # Nombre del archivo
                fecha = datetime.now().strftime("%Y%m%d")
                filename = OUTPUT_DIR / f"youtube_top_songs_{fecha}.csv"
                
                # Guardar archivo
                await download.save_as(filename)
                print(f"✅ Archivo guardado: {filename}")
                
                # Verificar que existe
                if filename.exists():
                    size_kb = filename.stat().st_size / 1024
                    print(f"📦 Tamaño: {size_kb:.1f} KB")
                    
                    # Leer primeras líneas para verificar
                    with open(filename, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:3]
                        if lines:
                            print("📋 Primeras líneas del CSV:")
                            for line in lines:
                                print(f"  {line.strip()}")
                
                return str(filename)
                
            finally:
                await browser.close()
                
    except ImportError:
        print("❌ Playwright no está instalado. Ejecuta: pip install playwright")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Función principal"""
    print("=" * 60)
    print("🎵 YOUTUBE MUSIC CHARTS DOWNLOADER")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Verificar si estamos en GitHub Actions
    if os.getenv('GITHUB_ACTIONS'):
        print("⚡ Ejecutando en GitHub Actions")
    
    # Descargar el chart
    csv_path = asyncio.run(download_chart())
    
    if csv_path and os.path.exists(csv_path):
        print(f"\n🎉 ¡ÉXITO! Chart descargado correctamente")
        print(f"📁 Ruta: {csv_path}")
        
        # También crear un enlace simbólico al archivo más reciente
        try:
            latest_link = OUTPUT_DIR / "youtube_chart_latest.csv"
            if latest_link.exists():
                latest_link.unlink()
            os.symlink(csv_path, latest_link)
            print(f"🔗 Enlace creado: {latest_link}")
        except:
            pass
            
        return 0
    else:
        print("\n❌ FALLÓ la descarga del chart")
        return 1

if __name__ == "__main__":
    sys.exit(main())
