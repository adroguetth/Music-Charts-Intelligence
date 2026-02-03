#!/usr/bin/env python3
"""
1_descargar.py - Descarga directa del CSV de YouTube Charts
Versión ultra-simple: solo hace clic en el botón
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def download_chart():
    """Solo hace clic en el botón de descarga y guarda el CSV"""
    try:
        from playwright.async_api import async_playwright
        
        print("🚀 Iniciando navegador...")
        
        async with async_playwright() as p:
            # Configuración mínima
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()
            
            # Ir a la página
            print("🌐 Cargando página...")
            await page.goto(
                "https://charts.youtube.com/charts/TopSongs/global/weekly",
                wait_until='load',
                timeout=30000
            )
            
            # Dar tiempo a que cargue
            await page.wait_for_timeout(3000)
            
            # 1. PRIMER INTENTO: Hacer clic directamente en el iron-icon que encontraste
            print("🖱️  Intentando clic en iron-icon#icon...")
            try:
                # El elemento exacto que mencionaste: <iron-icon id="icon">
                icon = await page.wait_for_selector('iron-icon#icon', timeout=10000)
                
                # Hacer clic y esperar descarga
                async with page.expect_download() as download_info:
                    await icon.click()
                
                download = await download_info.value
                
            except Exception as e:
                print(f"⚠️  Falló iron-icon: {e}")
                
                # 2. SEGUNDO INTENTO: Buscar el botón padre (paper-icon-button)
                print("🖱️  Intentando clic en paper-icon-button...")
                try:
                    button = await page.wait_for_selector('paper-icon-button', timeout=5000)
                    
                    async with page.expect_download() as download_info:
                        await button.click()
                    
                    download = await download_info.value
                    
                except Exception as e2:
                    print(f"⚠️  Falló paper-icon-button: {e2}")
                    
                    # 3. TERCER INTENTO: Buscar por el SVG específico
                    print("🖱️  Intentando clic por SVG path...")
                    try:
                        # Buscar el path específico que compartiste
                        svg_path = 'svg path[d="M17,18v1H6v-1H17z M16.5,11.4l-0.7-0.7L12,14.4V4h-1v10.4l-3.8-3.8l-0.7,0.7l5,5L16.5,11.4z"]'
                        svg = await page.wait_for_selector(svg_path, timeout=5000)
                        
                        # Subir hasta encontrar un elemento clickeable
                        clickable = await svg.evaluate_handle('''el => {
                            while (el && !el.click) {
                                el = el.parentElement;
                            }
                            return el;
                        }''')
                        
                        if clickable:
                            async with page.expect_download() as download_info:
                                await clickable.click()
                            download = await download_info.value
                        else:
                            raise Exception("No se encontró elemento clickeable")
                            
                    except Exception as e3:
                        print(f"❌ Todos los métodos fallaron: {e3}")
                        
                        # Guardar screenshot para debug
                        await page.screenshot(path=OUTPUT_DIR / 'debug.png')
                        print("📸 Captura guardada en data/raw/debug.png")
                        return None
            
            # Guardar el archivo
            fecha = datetime.now().strftime("%Y%m%d")
            filename = OUTPUT_DIR / f"youtube_top_songs_{fecha}.csv"
            
            await download.save_as(filename)
            print(f"✅ CSV descargado: {filename}")
            
            # Verificar contenido
            if filename.exists():
                with open(filename, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    print(f"📋 Primera línea: {first_line[:100]}...")
            
            await browser.close()
            return str(filename)
            
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("=" * 50)
    print("🎵 DESCARGADOR SIMPLE DE YOUTUBE CHARTS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    csv_path = asyncio.run(download_chart())
    
    if csv_path:
        print(f"\n🎉 ¡ÉXITO! Archivo: {csv_path}")
        
        # Crear enlace simbólico
        try:
            latest = OUTPUT_DIR / "latest_chart.csv"
            if latest.exists():
                latest.unlink()
            os.symlink(csv_path, latest)
            print(f"🔗 Enlace: {latest}")
        except:
            pass
        
        return 0
    else:
        print("\n❌ FALLÓ la descarga")
        return 1

if __name__ == "__main__":
    sys.exit(main())
