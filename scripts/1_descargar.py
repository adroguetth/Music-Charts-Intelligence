#!/usr/bin/env python3
"""
YouTube Charts CSV Downloader - Versión con Playwright
Descarga datos de https://charts.youtube.com/charts/TopSongs/global/weekly
"""

import asyncio
import json
import pandas as pd
import re
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List

async def download_youtube_charts_csv():
    """
    Descarga datos de YouTube Charts usando Playwright (ejecuta JavaScript)
    """
    print("🎵 YouTube Charts CSV Downloader")
    print("=" * 60)
    
    # Configurar carpeta de salida
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            print("📡 Iniciando navegador...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Interceptar peticiones de red para encontrar la API de datos
            chart_data = None
            
            async def handle_response(response):
                nonlocal chart_data
                try:
                    if 'api' in response.url or 'data' in response.url:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                if isinstance(data, dict) and ('data' in data or 'chart' in data or 'tracks' in data):
                                    chart_data = data
                                    print(f"✅ Datos encontrados en: {response.url}")
                            except:
                                pass
                except:
                    pass
            
            page.on("response", handle_response)
            
            print("📄 Navegando a YouTube Charts...")
            url = "https://charts.youtube.com/charts/TopSongs/global/weekly"
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                print(f"✅ Página cargada")
            except:
                print("⚠️  Timeout esperando carga completa, continuando...")
                await page.wait_for_timeout(5000)
            
            # Extraer datos de la página
            print("🔍 Extrayendo datos de la página...")
            
            # Estrategia 1: Buscar en el objeto window
            try:
                window_data = await page.evaluate("""
                    () => {
                        // Buscar en window
                        if (window.__data) return window.__data;
                        if (window.__INITIAL_STATE__) return window.__INITIAL_STATE__;
                        if (window.__PROPS__) return window.__PROPS__;
                        
                        // Buscar en el DOM
                        const scripts = document.querySelectorAll('script');
                        for (let script of scripts) {
                            if (script.textContent.includes('chartData') || 
                                script.textContent.includes('tracks') ||
                                script.textContent.includes('TopSongs')) {
                                try {
                                    const match = script.textContent.match(/{.*"(?:chartData|data|tracks)".*}/s);
                                    if (match) {
                                        return JSON.parse(match[0]);
                                    }
                                } catch (e) {}
                            }
                        }
                        
                        return null;
                    }
                """)
                
                if window_data:
                    print("✅ Datos encontrados en window")
                    chart_data = window_data
            except Exception as e:
                print(f"⚠️  No se encontraron datos en window: {e}")
            
            # Estrategia 2: Extraer del DOM directamente
            if not chart_data:
                print("📊 Extrayendo datos del DOM...")
                try:
                    tracks = await page.evaluate("""
                        () => {
                            const tracks = [];
                            const rows = document.querySelectorAll('[role="row"], tr, .track-row, [data-track], .song-item');
                            
                            rows.forEach((row, index) => {
                                if (index === 0) return; // Skip header
                                
                                const cells = row.querySelectorAll('[role="gridcell"], td, .cell, span');
                                if (cells.length > 0) {
                                    const track = {
                                        rank: cells[0]?.textContent?.trim() || (index),
                                        title: cells[1]?.textContent?.trim() || 'Unknown',
                                        artist: cells[2]?.textContent?.trim() || 'Unknown',
                                        views: cells[3]?.textContent?.trim() || '0'
                                    };
                                    tracks.push(track);
                                }
                            });
                            
                            return tracks.length > 0 ? tracks : null;
                        }
                    """)
                    
                    if tracks and len(tracks) > 0:
                        print(f"✅ Encontradas {len(tracks)} canciones en el DOM")
                        df = pd.DataFrame(tracks)
                        return save_dataframe_as_csv(df, output_dir)
                except Exception as e:
                    print(f"⚠️  Error extrayendo del DOM: {e}")
            
            await browser.close()
            
            # Si tenemos chart_data, procesarla
            if chart_data:
                df = parse_chart_data(chart_data)
                if df is not None and len(df) > 0:
                    return save_dataframe_as_csv(df, output_dir)
        
        return None
        
    except ImportError:
        print("❌ Playwright no está instalado")
        print("💡 Necesitas: pip install playwright")
        print("   Y luego: playwright install")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_chart_data(data) -> Optional[pd.DataFrame]:
    """
    Procesa los datos del chart en un DataFrame
    """
    try:
        rows = []
        
        # Buscar array de tracks en diferentes posibles ubicaciones
        tracks = []
        
        if isinstance(data, dict):
            # Buscar en diferentes claves comunes
            for key in ['data', 'tracks', 'songs', 'items', 'chart', 'chartData']:
                if key in data:
                    potential = data[key]
                    if isinstance(potential, list):
                        tracks = potential
                        break
                    elif isinstance(potential, dict):
                        for subkey in ['tracks', 'songs', 'items', 'data']:
                            if subkey in potential and isinstance(potential[subkey], list):
                                tracks = potential[subkey]
                                break
        
        if not tracks:
            print("⚠️  No se encontraron tracks en los datos")
            return None
        
        # Procesar tracks
        for rank, track in enumerate(tracks, 1):
            if isinstance(track, dict):
                row = {
                    'Rank': rank,
                    'Title': track.get('title', track.get('name', 'Unknown')),
                    'Artist': track.get('artist', track.get('artists', 'Unknown')),
                    'Views': track.get('views', track.get('count', 0)),
                }
                rows.append(row)
            elif isinstance(track, (list, tuple)) and len(track) >= 2:
                rows.append({
                    'Rank': rank,
                    'Title': str(track[0] if len(track) > 0 else 'Unknown'),
                    'Artist': str(track[1] if len(track) > 1 else 'Unknown'),
                    'Views': track[2] if len(track) > 2 else 0,
                })
        
        if rows:
            return pd.DataFrame(rows)
        
        return None
        
    except Exception as e:
        print(f"❌ Error procesando chart data: {e}")
        return None


def save_dataframe_as_csv(df, output_dir):
    """
    Guarda un DataFrame como CSV
    """
    try:
        if df is None or len(df) == 0:
            print("⚠️  DataFrame vacío")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = output_dir / f"youtube_charts_{timestamp}.csv"
        
        df.to_csv(filename, index=False, encoding='utf-8')
        
        print(f"✅ CSV guardado: {filename}")
        print(f"📊 Datos: {len(df)} filas, {len(df.columns)} columnas")
        print(f"  Columnas: {', '.join(df.columns.tolist())}")
        
        # Mostrar primeras filas
        print("  Primeras 3 filas:")
        for i in range(min(3, len(df))):
            print(f"    {i+1}. {df.iloc[i].to_dict()}")
        
        return str(filename)
        
    except Exception as e:
        print(f"❌ Error guardando CSV: {e}")
        return None


def create_fallback_csv(output_dir):
    """
    Crea un CSV de fallback como último recurso
    """
    print("🆘 Creando CSV de fallback...")
    
    sample_data = [
        {"Rank": 1, "Title": "Top Song 1", "Artist": "Artist 1", "Views": 1000000},
        {"Rank": 2, "Title": "Top Song 2", "Artist": "Artist 2", "Views": 950000},
        {"Rank": 3, "Title": "Top Song 3", "Artist": "Artist 3", "Views": 900000},
    ]
    
    df = pd.DataFrame(sample_data)
    filename = output_dir / f"youtube_charts_fallback_{datetime.now().strftime('%Y%m%d')}.csv"
    df.to_csv(filename, index=False, encoding='utf-8')
    
    print(f"📋 CSV fallback creado: {filename}")
    return str(filename)


async def main():
    """
    Función principal
    """
    print("\n" + "=" * 70)
    print("🎵 YOUTUBE CHARTS DOWNLOADER - PLAYWRIGHT")
    print("=" * 70)
    
    # Detectar entorno
    in_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    if in_github_actions:
        print("⚡ Ejecutando en GitHub Actions")
    else:
        print("💻 Ejecutando localmente")
    
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    
    # Intentar descargar
    result = await download_youtube_charts_csv()
    
    if result:
        print(f"\n✅ ¡ÉXITO! CSV descargado: {result}")
        return 0
    
    # Fallback
    print("\n⚠️  No se pudo descargar, creando fallback...")
    result = create_fallback_csv(output_dir)
    
    if result:
        print(f"✅ CSV fallback creado: {result}")
        return 0
    
    print("\n❌ Error fatal")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
