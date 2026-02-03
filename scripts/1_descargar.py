#!/usr/bin/env python3
"""
1_descargar.py - Descarga automática del CSV de YouTube Charts usando Playwright
"""

import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime
import os
import sys

async def download_youtube_chart():
    """Descarga el CSV de YouTube Charts usando Playwright"""
    
    print("🎵 Iniciando descarga de YouTube Music Charts...")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # URL del chart
    url = "https://charts.youtube.com/charts/TopSongs/global/weekly"
    
    # Configurar Playwright
    async with async_playwright() as p:
        print("🚀 Iniciando navegador...")
        
        # Usar chromium (más ligero para GitHub Actions)
        browser = await p.chromium.launch(
            headless=True,  # Modo sin interfaz para GitHub
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        # Crear contexto con permisos de descarga
        context = await browser.new_context(
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        try:
            # Navegar a la página
            print("🌐 Cargando página de charts...")
            await page.goto(url, wait_until='networkidle', timeout=60000)
            
            # Esperar a que cargue la tabla
            print("⏳ Esperando que cargue la tabla de datos...")
            await page.wait_for_selector('ytmc-chart-table', timeout=30000)
            
            # Buscar el botón de descarga - VAMOS A PROBAR DIFERENTES SELECTORES
            print("🔍 Buscando botón de descarga...")
            
            # Intentar varios selectores posibles
            selectores = [
                'iron-icon#icon',  # Por el ID que encontraste
                'paper-icon-button',  # Por la clase del contenedor
                '[aria-label*="download"]',  # Por atributo aria-label
                '[title*="Download"]',  # Por título
                'button[icon="file-download"]',  # Otro posible selector
                'ytmc-download-button',  # Componente específico de YouTube Music Charts
            ]
            
            boton_descarga = None
            for selector in selectores:
                try:
                    boton_descarga = await page.query_selector(selector)
                    if boton_descarga:
                        print(f"✅ Botón encontrado con selector: {selector}")
                        break
                except:
                    continue
            
            if not boton_descarga:
                # Fallback: buscar cualquier botón que contenga un ícono de descarga
                print("⚠️  Botón específico no encontrado, buscando alternativas...")
                
                # Buscar por el path SVG específico del ícono de descarga
                boton_descarga = await page.query_selector('svg path[d*="M17,18v1H6v-1H17z M16.5,11.4"]')
                if boton_descarga:
                    # Subir al elemento padre que probablemente sea el botón
                    boton_descarga = await boton_descarga.query_selector('xpath=./ancestor::button | ./ancestor::paper-icon-button | ./ancestor::*[@role="button"]')
            
            if not boton_descarga:
                # Último recurso: hacer screenshot para debugging
                print("❌ No se pudo encontrar el botón de descarga")
                await page.screenshot(path='debug_page.png')
                print("📸 Captura de pantalla guardada como debug_page.png")
                
                # Mostrar estructura de la página para debugging
                html = await page.content()
                if 'download' in html.lower():
                    print("ℹ️  La página contiene texto 'download', revisa debug_page.png")
                
                return None
            
            # Configurar la descarga
            print("📥 Configurando descarga...")
            
            # Esperar el evento de descarga
            async with page.expect_download() as download_info:
                # Hacer clic en el botón
                await boton_descarga.click()
                print("🖱️  Clic en botón de descarga realizado")
            
            # Obtener el objeto de descarga
            download = await download_info.value
            
            # Generar nombre de archivo con fecha
            fecha = datetime.now().strftime("%Y%m%d")
            filename = f"youtube_top_songs_{fecha}.csv"
            
            # Guardar el archivo
            await download.save_as(filename)
            print(f"✅ CSV descargado exitosamente: {filename}")
            
            # Verificar el contenido
            try:
                df = pd.read_csv(filename)
                print(f"📊 Registros descargados: {len(df)}")
                print(f"📋 Columnas: {', '.join(df.columns)}")
                
                # Mostrar primeras filas
                print("\n🔽 PRIMERAS 3 CANCIONES DEL CHART:")
                for i, row in df.head(3).iterrows():
                    print(f"  {row.get('Rank', i+1)}. {row.get('Track Name', 'N/A')} - {row.get('Artist Names', 'N/A')}")
                
            except Exception as e:
                print(f"⚠️  Error leyendo CSV: {e}")
                # El archivo podría no ser CSV o tener formato diferente
            
            # Cerrar navegador
            await browser.close()
            
            return filename
            
        except Exception as e:
            print(f"❌ Error durante la descarga: {e}")
            import traceback
            traceback.print_exc()
            
            # Intentar cerrar el navegador incluso si hay error
            try:
                await browser.close()
            except:
                pass
            
            return None

def main():
    """Función principal síncrona"""
    
    # Ejecutar la función asíncrona
    filename = asyncio.run(download_youtube_chart())
    
    if filename:
        print(f"\n🎉 Descarga completada exitosamente!")
        print(f"💾 Archivo guardado como: {filename}")
        
        # Verificar tamaño
        if os.path.exists(filename):
            size_kb = os.path.getsize(filename) / 1024
            print(f"📦 Tamaño del archivo: {size_kb:.1f} KB")
    else:
        print("\n❌ La descarga falló. Revisa los mensajes de error arriba.")
        sys.exit(1)

if __name__ == "__main__":
    main()
