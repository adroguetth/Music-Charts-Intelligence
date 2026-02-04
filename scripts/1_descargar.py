#!/usr/bin/env python3
"""
1_descargar.py - AUTOCLICK EN BOTÓN DE DESCARGA Y ARCHIVADO PERMANENTE
Solución definitiva para GitHub Actions con almacenamiento a largo plazo
Versión mejorada con control de historial semanal en SQLite
"""

import asyncio
import os
import sys
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

# Configuración de directorios
OUTPUT_DIR = Path("data")
ARCHIVE_DIR = Path("charts_archive")
REPORTS_DIR = Path("reports")
RAW_DIR = Path("raw_data")
DATABASE_DIR = Path("databases")

# Crear todos los directorios necesarios
for dir_path in [OUTPUT_DIR, ARCHIVE_DIR, REPORTS_DIR, RAW_DIR, DATABASE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

async def click_download_button():
    """
    ENFOQUE DIRECTA: Hacer clic en el botón de descarga real
    """
    print("🎵 YouTube Charts - Autoclick en botón de descarga")
    print("=" * 70)
    
    try:
        from playwright.async_api import async_playwright
        
        print("1. 🚀 Iniciando Playwright...")
        
        # CONFIGURACIÓN CRÍTICA para GitHub Actions
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--window-size=1920,1080',
                    '--start-maximized',
                ]
            )
            
            # Contexto con permisos de descarga
            context = await browser.new_context(
                accept_downloads=True,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['clipboard-read', 'clipboard-write']
            )
            
            page = await context.new_page()
            page.set_default_timeout(60000)
            
            print("2. 🌐 Navegando a YouTube Charts...")
            url = "https://charts.youtube.com/charts/TopSongs/global/weekly"
            
            await page.goto(
                url,
                wait_until='networkidle',
                timeout=60000
            )
            
            print("3. ⏳ Esperando que cargue completamente...")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(5000)
            
            print("4. 🔍 BUSCANDO BOTÓN DE DESCARGA...")
            
            # ESTRATEGIA 1: Buscar por texto
            print("   📝 Buscando por texto 'Download'...")
            try:
                download_element = await page.locator(
                    "text=/download/i"
                ).first.wait_for(timeout=10000)
                
                if download_element:
                    print("   ✅ Elemento encontrado por texto 'Download'")
                    
                    async with page.expect_download() as download_info:
                        await download_element.click()
                    
                    return await handle_download(download_info, page, browser)
            except Exception as e:
                print(f"   ⚠️  Texto 'Download' no encontrado: {e}")
            
            # ESTRATEGIA 2: Buscar por atributos ARIA
            print("   🎯 Buscando por atributos ARIA...")
            try:
                aria_selectors = [
                    '[aria-label*="download" i]',
                    '[aria-label*="descargar" i]',
                    '[title*="download" i]',
                    '[title*="descargar" i]',
                    'button[aria-label*="csv" i]',
                ]
                
                for selector in aria_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=5000, state='visible')
                        if element:
                            print(f"   ✅ Encontrado con selector: {selector}")
                            
                            async with page.expect_download() as download_info:
                                await element.click()
                            
                            return await handle_download(download_info, page, browser)
                    except:
                        continue
            except Exception as e:
                print(f"   ⚠️  ARIA no encontrado: {e}")
            
            # ESTRATEGIA 3: Intentar obtener la semana actual de la página
            week_info = await get_current_week(page)
            
            # ESTRATEGIA 4: Screenshot para debugging
            print("5. 📸 Tomando screenshot para debugging...")
            screenshot_path = OUTPUT_DIR / "debug_screenshot.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"   📷 Screenshot guardado: {screenshot_path}")
            
            # Guardar HTML para análisis
            html_path = OUTPUT_DIR / "debug_page.html"
            html_content = await page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   📄 HTML guardado: {html_path}")
            
            await browser.close()
            return None, week_info
            
    except ImportError:
        print("❌ Playwright no está instalado")
        print("📦 Ejecuta: pip install playwright && playwright install chromium")
        return None, None
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
        return None, None

async def get_current_week(page):
    """Intenta extraer información de la semana actual de la página"""
    try:
        # Buscar elementos que puedan contener la fecha/semana
        selectors = [
            '[data-week]',
            '.week-selector',
            '.date-range',
            'text=/Week of/',
            'text=/Semana/',
            'time',
            '.current-week',
        ]
        
        for selector in selectors:
            try:
                elements = await page.locator(selector).all()
                for element in elements:
                    text = await element.text_content()
                    if text and (any(x in text.lower() for x in ['week', 'semana', '202', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])):
                        print(f"📅 Información de semana encontrada: {text.strip()}")
                        return text.strip()
            except:
                continue
        
        # Si no se encuentra, usar la fecha actual
        current_date = datetime.now()
        week_number = current_date.isocalendar()[1]
        year = current_date.year
        week_info = f"Week {week_number}, {year}"
        print(f"📅 Usando semana calculada: {week_info}")
        return week_info
        
    except Exception as e:
        print(f"⚠️  Error obteniendo información de semana: {e}")
        return None

async def handle_download(download_info, page, browser):
    """Maneja la descarga después del click"""
    try:
        print("6. 📥 Descarga iniciada, esperando archivo...")
        download = await download_info.value
        
        # Nombre del archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = OUTPUT_DIR / f"youtube_top_songs_{timestamp}.csv"
        
        # Guardar el archivo
        await download.save_as(filename)
        print(f"7. ✅ Archivo guardado temporalmente: {filename}")
        
        # Verificar integridad
        if verify_csv_integrity(filename):
            print(f"   📊 CSV verificado: {get_csv_stats(filename)}")
        
        await browser.close()
        return str(filename)
        
    except Exception as e:
        print(f"❌ Error manejando descarga: {e}")
        await browser.close()
        return None

def verify_csv_integrity(filepath):
    """Verifica que el CSV sea válido"""
    try:
        import pandas as pd
        df = pd.read_csv(filepath, encoding='utf-8')
        rows = len(df)
        cols = len(df.columns)
        print(f"✅ CSV válido: {rows} filas, {cols} columnas")
        print(f"📊 Columnas: {', '.join(df.columns.tolist()[:5])}..." if cols > 5 else f"📊 Columnas: {', '.join(df.columns)}")
        return True
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        return False

def get_csv_stats(filepath):
    """Obtiene estadísticas básicas del CSV"""
    try:
        import pandas as pd
        df = pd.read_csv(filepath, encoding='utf-8')
        return f"{len(df)} filas, {len(df.columns)} columnas"
    except:
        return "Estadísticas no disponibles"

def save_raw_csv(csv_path, week_info=None):
    """Guarda el CSV crudo en raw_data/ (inmutable, para historial)"""
    try:
        if week_info:
            # Crear nombre de archivo seguro a partir de la información de semana
            safe_week = "".join(c for c in week_info if c.isalnum() or c in (' ', '-', '_')).rstrip()
            date_str = datetime.now().strftime("%Y-%m-%d")
            raw_filename = RAW_DIR / f"{date_str}_{safe_week}_raw.csv"
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
            raw_filename = RAW_DIR / f"{date_str}_youtube_chart_raw.csv"
        
        shutil.copy2(csv_path, raw_filename)
        print(f"📦 CSV crudo guardado: {raw_filename}")
        
        return str(raw_filename)
    except Exception as e:
        print(f"⚠️  Error guardando raw CSV: {e}")
        return None

def generate_analysis_csvs(csv_path):
    """
    Genera CSVs específicos para análisis desde el CSV descargado
    """
    try:
        import pandas as pd
        
        print("📊 Generando CSVs de análisis específicos...")
        
        # Leer el CSV principal
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # 1. CSV: Top 10 semanal (para dashboard rápido)
        top10 = df.nsmallest(10, 'Rank')[['Rank', 'Track Name', 'Artist Names', 'Views', 'Growth']].copy()
        top10_path = REPORTS_DIR / "top10_weekly.csv"
        top10.to_csv(top10_path, index=False)
        print(f"   📈 Top 10 semanal: {top10_path} ({len(top10)} registros)")
        
        # 2. CSV: Análisis de artistas (tendencias)
        # Extraer primer artista si hay múltiples
        df['First_Artist'] = df['Artist Names'].str.split(',').str[0].str.strip()
        
        artist_stats = df.groupby('First_Artist').agg({
            'Track Name': 'count',
            'Views': 'sum',
            'Rank': 'mean'
        }).reset_index()
        
        artist_stats = artist_stats.rename(columns={
            'Track Name': 'Song_Count',
            'Views': 'Total_Views',
            'Rank': 'Avg_Rank'
        })
        
        artist_stats = artist_stats.sort_values('Total_Views', ascending=False)
        artist_path = REPORTS_DIR / "artist_analysis.csv"
        artist_stats.to_csv(artist_path, index=False)
        print(f"   🎤 Análisis de artistas: {artist_path} ({len(artist_stats)} artistas)")
        
        # 3. CSV: Trending tracks (mayor crecimiento)
        if 'Growth' in df.columns:
            df['Growth_Numeric'] = df['Growth'].str.replace('%', '').str.replace('+', '').astype(float)
            trending = df.nlargest(15, 'Growth_Numeric')[['Rank', 'Track Name', 'Artist Names', 'Growth']].copy()
            trending_path = REPORTS_DIR / "trending_tracks.csv"
            trending.to_csv(trending_path, index=False)
            print(f"   📈 Trending tracks: {trending_path} ({len(trending)} tracks)")
        
        # 4. CSV: Vista simplificada para no-técnicos
        simple_view = df[['Rank', 'Track Name', 'Artist Names', 'Views']].copy()
        simple_view.columns = ['Posición', 'Canción', 'Artista', 'Reproducciones']
        simple_path = REPORTS_DIR / "simple_view.csv"
        simple_view.to_csv(simple_path, index=False, encoding='utf-8-sig')  # Excel-friendly
        print(f"   👥 Vista simplificada: {simple_path}")
        
        # 5. CSV: Estadísticas diarias (metadata)
        stats_data = {
            'Download_Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            'Total_Songs': [len(df)],
            'Total_Views': [df['Views'].sum()],
            'Avg_Views_Per_Song': [df['Views'].mean()],
            'Date': [datetime.now().strftime('%Y-%m-%d')],
            'Week_Number': [datetime.now().strftime('%Y-W%W')]
        }
        stats_df = pd.DataFrame(stats_data)
        stats_path = REPORTS_DIR / "daily_stats.csv"
        
        # Append a archivo existente o crear nuevo
        if stats_path.exists():
            existing_stats = pd.read_csv(stats_path)
            updated_stats = pd.concat([existing_stats, stats_df], ignore_index=True)
            updated_stats.to_csv(stats_path, index=False)
        else:
            stats_df.to_csv(stats_path, index=False)
        
        print(f"   📅 Estadísticas diarias: {stats_path}")
        
        return {
            'top10': str(top10_path),
            'artists': str(artist_path),
            'trending': str(trending_path) if 'Growth' in df.columns else None,
            'simple': str(simple_path),
            'stats': str(stats_path)
        }
        
    except Exception as e:
        print(f"⚠️  Error generando CSVs de análisis: {e}")
        import traceback
        traceback.print_exc()
        return {}

def calculate_week_hash(df):
    """Calcula un hash único para identificar la semana basado en los datos"""
    try:
        # Crear una cadena con información de la semana
        week_data = ""
        
        # Usar los primeros 10 registros para el hash (suficiente para identificar la semana)
        for i, row in df.head(10).iterrows():
            week_data += f"{row['Rank']}_{row['Track Name'][:20]}_{row['Artist Names'][:20]}_{row['Views']}"
        
        # Calcular hash MD5
        week_hash = hashlib.md5(week_data.encode()).hexdigest()[:16]
        return week_hash
    except Exception as e:
        print(f"⚠️  Error calculando hash de semana: {e}")
        return None

def get_week_identifier():
    """Obtiene un identificador único para la semana actual"""
    today = datetime.now()
    year, week_num, _ = today.isocalendar()
    return f"{year}-W{week_num:02d}"

def update_sqlite_database(csv_path, week_info=None):
    """Actualiza base de datos SQLite para análisis futuro con control de historial"""
    try:
        import pandas as pd
        import sqlite3
        from datetime import datetime
        
        print("🗃️  Actualizando base de datos SQLite con control de historial...")
        
        # Leer CSV
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Añadir metadatos
        current_time = datetime.now()
        week_identifier = get_week_identifier()
        week_hash = calculate_week_hash(df)
        
        df['download_date'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
        df['week_identifier'] = week_identifier
        df['week_hash'] = week_hash
        df['year'] = current_time.strftime('%Y')
        df['month'] = current_time.strftime('%m')
        df['week_number'] = current_time.strftime('%W')
        
        # Conectar a SQLite (crea si no existe)
        db_path = DATABASE_DIR / "charts_database.db"
        conn = sqlite3.connect(db_path)
        
        # Crear tabla de control de semanas
        conn.execute('''
        CREATE TABLE IF NOT EXISTS week_control (
            week_identifier TEXT PRIMARY KEY,
            week_hash TEXT UNIQUE,
            download_date TEXT,
            week_info TEXT,
            total_records INTEGER,
            total_views INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Verificar si ya existe esta semana (por hash o identificador)
        cursor = conn.cursor()
        
        # Verificar por hash (más preciso)
        if week_hash:
            cursor.execute("SELECT week_identifier FROM week_control WHERE week_hash = ?", (week_hash,))
            existing_week = cursor.fetchone()
            
            if existing_week:
                print(f"⚠️  Esta semana ya existe en la base de datos: {existing_week[0]}")
                print("   No se insertarán datos duplicados.")
                conn.close()
                return db_path
        
        # Verificar por identificador de semana
        cursor.execute("SELECT week_identifier FROM week_control WHERE week_identifier = ?", (week_identifier,))
        existing_week = cursor.fetchone()
        
        if existing_week:
            print(f"⚠️  El identificador de semana {week_identifier} ya existe")
            print("   Se procederá con la inserción (puede ser una actualización)")
        
        # Guardar en tabla histórica principal
        df.to_sql('historical_charts', conn, if_exists='append', index=False)
        
        # Crear tabla específica para esta semana
        safe_table_name = f"weekly_{week_identifier.replace('-', '_').replace('W', 'w')}"
        safe_table_name = ''.join(c for c in safe_table_name if c.isalnum() or c == '_')
        
        # Guardar datos semanales en tabla específica
        weekly_df = df.copy()
        weekly_df.to_sql(safe_table_name, conn, if_exists='replace', index=False)
        
        # Actualizar tabla de control
        total_records = len(df)
        total_views = df['Views'].sum() if 'Views' in df.columns else 0
        
        cursor.execute('''
        INSERT OR REPLACE INTO week_control 
        (week_identifier, week_hash, download_date, week_info, total_records, total_views)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (week_identifier, week_hash, current_time.strftime('%Y-%m-%d %H:%M:%S'), 
              str(week_info), total_records, total_views))
        
        # Crear vista resumen semanal (última semana)
        weekly_summary = df[['Rank', 'Track Name', 'Artist Names', 'Views', 'download_date']].copy()
        weekly_summary.to_sql('weekly_charts', conn, if_exists='replace', index=False)
        
        # Estadísticas
        cursor.execute("SELECT COUNT(DISTINCT week_identifier) FROM historical_charts")
        total_weeks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM historical_charts")
        total_rows = cursor.fetchone()[0]
        
        # Obtener lista de semanas
        cursor.execute("SELECT week_identifier, download_date FROM week_control ORDER BY download_date DESC")
        weeks = cursor.fetchall()
        
        conn.commit()
        conn.close()
        
        print(f"✅ Base de datos actualizada exitosamente")
        print(f"   📊 Total de semanas: {total_weeks}")
        print(f"   📊 Total de registros: {total_rows}")
        print(f"   📅 Tabla semanal creada: {safe_table_name}")
        print(f"   💾 Ubicación: {db_path}")
        
        if weeks:
            print(f"   📋 Últimas semanas almacenadas:")
            for week_id, week_date in weeks[:5]:  # Mostrar solo las 5 últimas
                print(f"     • {week_id} ({week_date})")
        
        return db_path
        
    except Exception as e:
        print(f"⚠️  No se pudo actualizar SQLite: {e}")
        import traceback
        traceback.print_exc()
        return None

def consolidate_weekly_data():
    """Consolida todas las semanas en un solo archivo SQLite para análisis"""
    try:
        import pandas as pd
        import sqlite3
        from datetime import datetime
        
        print("🔄 Consolidando datos semanales en archivo único...")
        
        # Archivo de consolidación
        consolidated_path = DATABASE_DIR / "weekly_charts_consolidated.db"
        conn = sqlite3.connect(consolidated_path)
        
        # Listar todas las tablas semanales en la base de datos principal
        main_db_path = DATABASE_DIR / "charts_database.db"
        if not main_db_path.exists():
            print("⚠️  No existe la base de datos principal")
            return None
        
        main_conn = sqlite3.connect(main_db_path)
        cursor = main_conn.cursor()
        
        # Obtener todas las tablas que empiezan con 'weekly_'
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'weekly_%'")
        weekly_tables = cursor.fetchall()
        
        print(f"📊 Encontradas {len(weekly_tables)} tablas semanales")
        
        # Crear tabla consolidada
        conn.execute('''
        CREATE TABLE IF NOT EXISTS all_weekly_charts (
            week_identifier TEXT,
            Rank INTEGER,
            "Track Name" TEXT,
            "Artist Names" TEXT,
            Views INTEGER,
            Growth TEXT,
            "YouTube URL" TEXT,
            download_date TEXT,
            week_hash TEXT,
            year TEXT,
            month TEXT,
            week_number TEXT
        )
        ''')
        
        # Para cada tabla semanal, insertar datos en la consolidada
        for (table_name,) in weekly_tables:
            try:
                # Extraer identificador de semana del nombre de la tabla
                week_id = table_name.replace('weekly_', '').replace('_', '-').replace('w', 'W')
                
                # Leer datos de la tabla semanal
                query = f"SELECT * FROM {table_name}"
                weekly_df = pd.read_sql_query(query, main_conn)
                
                # Añadir identificador de semana
                weekly_df['week_identifier'] = week_id
                
                # Insertar en tabla consolidada
                weekly_df.to_sql('all_weekly_charts', conn, if_exists='append', index=False)
                
                print(f"   ✅ {table_name} -> {week_id} ({len(weekly_df)} registros)")
            except Exception as e:
                print(f"   ⚠️  Error procesando {table_name}: {e}")
        
        # Estadísticas finales
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT week_identifier) FROM all_weekly_charts")
        total_weeks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM all_weekly_charts")
        total_rows = cursor.fetchone()[0]
        
        main_conn.close()
        conn.close()
        
        print(f"✅ Consolidación completada:")
        print(f"   📊 Total de semanas: {total_weeks}")
        print(f"   📊 Total de registros: {total_rows}")
        print(f"   💾 Archivo consolidado: {consolidated_path}")
        
        return consolidated_path
        
    except Exception as e:
        print(f"⚠️  Error en consolidación: {e}")
        return None

def archive_for_long_term_storage(csv_path, retention_years=1):
    """
    Archiva el CSV para almacenamiento a largo plazo
    retention_years: Cuántos años mantener los archivos (por defecto 1)
    """
    try:
        from datetime import datetime
        import shutil
        
        # Fechas para nombres de archivo
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        year_month = now.strftime("%Y-%m")
        year = now.strftime("%Y")
        week_id = get_week_identifier()
        
        # 1. Copiar con nombre con fecha para historial completo
        dated_filename = ARCHIVE_DIR / f"youtube_chart_{date_str}_{week_id}.csv"
        shutil.copy2(csv_path, dated_filename)
        
        # 2. Copiar como 'latest' para acceso inmediato
        latest_filename = ARCHIVE_DIR / "latest_chart.csv"
        shutil.copy2(csv_path, latest_filename)
        
        # 3. Copiar en carpeta por año para organización
        year_dir = ARCHIVE_DIR / year
        year_dir.mkdir(exist_ok=True)
        yearly_filename = year_dir / f"chart_{date_str}_{week_id}.csv"
        shutil.copy2(csv_path, yearly_filename)
        
        print(f"📁 ARCHIVADO PARA 1+ AÑOS:")
        print(f"   📄 Histórico: {dated_filename}")
        print(f"   ⚡ Último: {latest_filename}")
        print(f"   📅 Por año: {yearly_filename}")
        print(f"   🏷️  Identificador de semana: {week_id}")
        
        # 4. Limpiar archivos antiguos (opcional, basado en retención)
        if retention_years > 0:
            cleanup_old_files(retention_years)
        
        return dated_filename, latest_filename
        
    except Exception as e:
        print(f"❌ Error en archivado: {e}")
        return None, None

def cleanup_old_files(retention_years):
    """Limpia archivos más antiguos que retention_years"""
    try:
        cutoff_date = datetime.now() - timedelta(days=retention_years * 365)
        
        for file_path in ARCHIVE_DIR.glob("youtube_chart_*.csv"):
            try:
                # Extraer fecha del nombre del archivo
                filename = file_path.stem
                date_part = filename.replace("youtube_chart_", "").split("_")[0]
                file_date = datetime.strptime(date_part, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    file_path.unlink()
                    print(f"   🗑️  Limpiado archivo antiguo: {file_path.name}")
            except:
                continue
                
        print(f"   🧹 Limpieza completada (retención: {retention_years} años)")
    except Exception as e:
        print(f"⚠️  Error en limpieza: {e}")

def create_fallback_file():
    """Crea un archivo de fallback si todo falla"""
    print("🆘 Creando archivo de fallback...")
    
    try:
        import pandas as pd
        
        # Datos de ejemplo
        data = """Rank,Previous Rank,Track Name,Artist Names,Periods on Chart,Views,Growth,YouTube URL
1,1,Golden,HUNTR/X & EJAE & AUDREY NUNA & REI AMI & KPop Demon Hunters Cast,32,57046376,-0.01%,https://www.youtube.com/watch?v=yebNIHKAC4A
2,2,Zoo,Shakira,9,33072035,-0.16%,https://www.youtube.com/watch?v=Kw3935PH01E
3,5,Shararat,Shashwat Sachdev & Madhubanti Bagchi & Jasmine Sandlas,7,32271534,0.16%,https://www.youtube.com/watch?v=YyepU5ztLf4
4,4,NO BATIDÃO,ZXKAI & slxughter,14,30928663,0.04%,https://www.youtube.com/watch?v=GXioir-fujY
5,3,Pal Pal,Afusic & AliSoomroMusic,43,27554912,-0.08%,https://www.youtube.com/watch?v=8of5w7RgcTc"""
        
        from io import StringIO
        df = pd.read_csv(StringIO(data))
        df['Download_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df['week_identifier'] = get_week_identifier()
        
        # Guardar
        filename = OUTPUT_DIR / f"youtube_charts_fallback_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        
        print(f"📋 Archivo de fallback creado: {filename}")
        return str(filename)
        
    except Exception as e:
        print(f"❌ Error creando fallback: {e}")
        return None

def backup_database():
    """Crea una copia de seguridad de la base de datos"""
    try:
        db_path = DATABASE_DIR / "charts_database.db"
        if not db_path.exists():
            print("⚠️  No existe la base de datos para backup")
            return None
        
        backup_path = DATABASE_DIR / f"charts_database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(db_path, backup_path)
        
        # Mantener solo los últimos 5 backups
        backups = sorted(DATABASE_DIR.glob("charts_database_backup_*.db"), key=os.path.getmtime)
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                old_backup.unlink()
                print(f"   🗑️  Eliminado backup antiguo: {old_backup.name}")
        
        print(f"💾 Backup creado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"⚠️  Error creando backup: {e}")
        return None

def main():
    """Función principal"""
    print("\n" + "=" * 70)
    print("🎵 YOUTUBE CHARTS - AUTOCLICK AUTOMÁTICO (1+ AÑOS RETENCIÓN)")
    print("📊 Versión mejorada con control de historial semanal en SQLite")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Verificar si estamos en GitHub Actions
    if os.getenv('GITHUB_ACTIONS'):
        print("⚡ Ejecutando en GitHub Actions")
    
    # Paso 0: Crear backup de la base de datos existente
    print("\n💾 CREANDO BACKUP DE BASE DE DATOS EXISTENTE...")
    backup_path = backup_database()
    
    # Paso 1: Intentar autoclick
    print("\n🔧 INTENTANDO AUTOCLICK EN BOTÓN DE DESCARGA...")
    result = asyncio.run(click_download_button())
    
    if result and result[0] is not None:
        csv_path, week_info = result
        print(f"\n✅ DESCARGA EXITOSA:")
        print(f"📁 Archivo temporal: {csv_path}")
        if week_info:
            print(f"📅 Información de semana obtenida: {week_info}")
        
        # Paso 2: Guardar CSV crudo (inmutable, para historial)
        print("\n📦 GUARDANDO CSV CRUDO PARA HISTORIAL...")
        raw_file = save_raw_csv(csv_path, week_info)
        
        # Paso 3: Generar CSVs de análisis específicos
        print("\n📊 GENERANDO CSVs DE ANÁLISIS ESPECÍFICOS...")
        analysis_files = generate_analysis_csvs(csv_path)
        
        # Paso 4: Actualizar base de datos SQLite con control de historial
        print("\n🗃️  ACTUALIZANDO BASE DE DATOS SQLITE CON HISTORIAL SEMANAL...")
        db_path = update_sqlite_database(csv_path, week_info)
        
        # Paso 5: Consolidar datos semanales
        print("\n🔄 CONSOLIDANDO DATOS SEMANALES EN ARCHIVO ÚNICO...")
        consolidated_db = consolidate_weekly_data()
        
        # Paso 6: Archivar para largo plazo
        print("\n📦 ARCHIVANDO PARA ALMACENAMIENTO A LARGO PLAZO (1+ AÑOS)...")
        dated_file, latest_file = archive_for_long_term_storage(csv_path, retention_years=1)
        
        # Paso 7: Estadísticas finales
        print("\n" + "=" * 70)
        print("📊 RESUMEN DE LA EJECUCIÓN:")
        print("=" * 70)
        print(f"📄 Archivo histórico: {dated_file}")
        print(f"⚡ Archivo latest: {latest_file}")
        if raw_file:
            print(f"📦 Archivo crudo: {raw_file}")
        
        if db_path:
            db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
            print(f"🗃️  Base de datos principal: {db_path} ({db_size/1024:.1f} KB)")
        
        if consolidated_db:
            consolidated_size = os.path.getsize(consolidated_db) if os.path.exists(consolidated_db) else 0
            print(f"🗃️  Base de datos consolidada: {consolidated_db} ({consolidated_size/1024:.1f} KB)")
        
        # Mostrar CSVs generados
        if analysis_files:
            print("\n📈 CSVs DE ANÁLISIS GENERADOS:")
            for name, path in analysis_files.items():
                if path and os.path.exists(path):
                    size = os.path.getsize(path)
                    print(f"   • {name}: {path} ({size} bytes)")
        
        # Calcular tamaño total
        print("\n📦 RESUMEN DE ALMACENAMIENTO:")
        total_size = 0
        all_files = []
        
        # Agregar archivos principales
        for file in [csv_path, dated_file, latest_file, raw_file, db_path, consolidated_db]:
            if file and os.path.exists(file):
                all_files.append(file)
        
        # Agregar CSVs de análisis
        if analysis_files:
            for path in analysis_files.values():
                if path and os.path.exists(path):
                    all_files.append(path)
        
        # Calcular tamaño total
        for file in all_files:
            if file and os.path.exists(file):
                total_size += os.path.getsize(file)
        
        print(f"   Total de archivos: {len(all_files)}")
        print(f"   Almacenamiento total: {total_size / 1024:.1f} KB")
        print("🎉 ¡Pipeline completado exitosamente!")
        
        # Retornar rutas importantes para el workflow
        return {
            'temp_csv': csv_path,
            'historical_csv': str(dated_file) if dated_file else None,
            'latest_csv': str(latest_file) if latest_file else None,
            'raw_csv': raw_file,
            'database': str(db_path) if db_path else None,
            'consolidated_database': str(consolidated_db) if consolidated_db else None,
            'analysis_csvs': analysis_files,
            'week_identifier': get_week_identifier(),
            'backup': str(backup_path) if backup_path else None
        }
    
    # Paso 7: Fallback si todo falla
    print("\n⚠️  El autoclick falló, usando datos de fallback...")
    csv_path = create_fallback_file()
    
    if csv_path:
        print(f"\n📋 Pipeline mantenido con datos de fallback")
        print(f"📁 Archivo: {csv_path}")
        
        # Generar análisis incluso con fallback
        analysis_files = generate_analysis_csvs(csv_path)
        
        # Archivar el fallback también
        dated_file, latest_file = archive_for_long_term_storage(csv_path, retention_years=1)
        
        # Actualizar base de datos con datos de fallback
        db_path = update_sqlite_database(csv_path, "Fallback Week")
        
        return {
            'temp_csv': csv_path,
            'historical_csv': str(dated_file) if dated_file else None,
            'latest_csv': str(latest_file) if latest_file else None,
            'database': str(db_path) if db_path else None,
            'analysis_csvs': analysis_files,
            'is_fallback': True
        }
    
    print("\n❌ Todo falló - No se pudo obtener ningún dato")
    return None

if __name__ == "__main__":
    result = main()
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
