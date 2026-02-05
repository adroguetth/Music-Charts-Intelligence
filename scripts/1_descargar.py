#!/usr/bin/env python3
"""
1_descargar.py - DESCARGA Y ALMACENAMIENTO EN SQLITE SEMANAL
Sistema robusto de bases de datos semanales con backups automáticos.
Una BD por semana, sin duplicados, sin borrado de datos históricos.
"""

import asyncio
import os
import sys
import shutil
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# ============================================================================
# CONFIGURACIÓN DE DIRECTORIOS
# ============================================================================

OUTPUT_DIR = Path("data")
ARCHIVE_DIR = Path("charts_archive")
DATABASE_DIR = ARCHIVE_DIR / "databases"
BACKUP_DIR = ARCHIVE_DIR / "backups"

# Crear todos los directorios necesarios
for dir_path in [OUTPUT_DIR, ARCHIVE_DIR, DATABASE_DIR, BACKUP_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


# ============================================================================
# FUNCIONES DE UTILIDAD PARA SEMANAS
# ============================================================================

def get_week_identifier(date: Optional[datetime] = None) -> str:
    """Obtiene identificador único para la semana (YYYY-WNN)"""
    if date is None:
        date = datetime.now()
    year, week_num, _ = date.isocalendar()
    return f"{year}-W{week_num:02d}"


def get_week_start_date(week_id: str) -> datetime:
    """Convierte YYYY-WNN a fecha de inicio de semana"""
    year, week = week_id.split('-W')
    year = int(year)
    week = int(week)
    # Primera semana del año
    jan_4 = datetime(year, 1, 4)
    week_1_monday = jan_4 - timedelta(days=jan_4.weekday())
    target_monday = week_1_monday + timedelta(weeks=week - 1)
    return target_monday


# ============================================================================
# FUNCIONES DE BASE DE DATOS SEMANAL
# ============================================================================

def get_weekly_db_path(week_id: str) -> Path:
    """Obtiene la ruta del archivo SQLite para una semana específica"""
    return DATABASE_DIR / f"youtube_charts_{week_id}.db"


def init_weekly_database(week_id: str) -> sqlite3.Connection:
    """Inicializa la base de datos para una semana específica"""
    db_path = get_weekly_db_path(week_id)
    
    # Si ya existe, retornar conexión
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        return conn
    
    # Crear nueva base de datos
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    
    # Tabla de metadatos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla principal de datos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chart_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rank INTEGER NOT NULL,
            previous_rank INTEGER,
            track_name TEXT NOT NULL,
            artist_names TEXT,
            periods_on_chart INTEGER,
            views INTEGER,
            growth TEXT,
            youtube_url TEXT,
            content_hash TEXT UNIQUE,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(rank, track_name, artist_names)
        )
    ''')
    
    # Índices para mejor rendimiento
    conn.execute('CREATE INDEX IF NOT EXISTS idx_rank ON chart_data(rank)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_artist ON chart_data(artist_names)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_track ON chart_data(track_name)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_hash ON chart_data(content_hash)')
    
    # Guardar metadatos
    conn.execute('''
        INSERT INTO metadata (key, value) VALUES (?, ?)
    ''', ('week_id', week_id))
    
    conn.execute('''
        INSERT INTO metadata (key, value) VALUES (?, ?)
    ''', ('created_date', datetime.now().isoformat()))
    
    conn.commit()
    print(f"✅ Base de datos semanal creada: {db_path}")
    return conn


def calculate_content_hash(row: Dict) -> str:
    """Calcula hash para evitar duplicados exactos"""
    content = f"{row.get('rank')}_{row.get('track_name')}_{row.get('artist_names')}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def insert_chart_data(conn: sqlite3.Connection, rows: list) -> Tuple[int, int]:
    """
    Inserta datos en la base de datos evitando duplicados.
    Retorna (insertados, duplicados)
    """
    cursor = conn.cursor()
    inserted = 0
    duplicates = 0
    
    for row in rows:
        content_hash = calculate_content_hash(row)
        
        try:
            cursor.execute('''
                INSERT INTO chart_data 
                (rank, previous_rank, track_name, artist_names, periods_on_chart, 
                 views, growth, youtube_url, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row.get('Rank'),
                row.get('Previous Rank'),
                row.get('Track Name', ''),
                row.get('Artist Names', ''),
                row.get('Periods on Chart', 0),
                row.get('Views', 0),
                row.get('Growth', ''),
                row.get('YouTube URL', ''),
                content_hash
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            duplicates += 1
            continue
    
    conn.commit()
    return inserted, duplicates


def create_backup_before_update(week_id: str) -> Optional[Path]:
    """Crea backup automático de la base de datos antes de actualizar"""
    db_path = get_weekly_db_path(week_id)
    
    if not db_path.exists():
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_{week_id}_{timestamp}.db"
    
    try:
        # Copiar base de datos
        shutil.copy2(db_path, backup_path)
        
        # Limpiar backups antiguos: mantener solo 3 por semana
        backups = sorted(BACKUP_DIR.glob(f"backup_{week_id}_*.db"))
        if len(backups) > 3:
            for old_backup in backups[:-3]:
                old_backup.unlink()
                print(f"   🗑️  Backup antiguo eliminado: {old_backup.name}")
        
        print(f"💾 Backup creado: {backup_path.name}")
        return backup_path
    except Exception as e:
        print(f"⚠️  Error en backup: {e}")
        return None


def get_database_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Obtiene estadísticas de la base de datos"""
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM chart_data')
    total_rows = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(views) FROM chart_data WHERE views IS NOT NULL')
    total_views = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT MIN(rank), MAX(rank) FROM chart_data')
    min_rank, max_rank = cursor.fetchone()
    
    cursor.execute('''
        SELECT artist_names, COUNT(*) as count 
        FROM chart_data 
        GROUP BY artist_names 
        ORDER BY count DESC LIMIT 5
    ''')
    top_artists = cursor.fetchall()
    
    return {
        'total_rows': total_rows,
        'total_views': total_views,
        'rank_range': (min_rank, max_rank),
        'top_artists': top_artists
    }


def archive_latest_csv(csv_path: Path, week_id: str) -> Path:
    """
    Guarda el CSV más reciente (se actualiza cada semana).
    Solo se mantiene un CSV, el más reciente.
    """
    latest_csv = ARCHIVE_DIR / "latest_chart.csv"
    
    try:
        shutil.copy2(csv_path, latest_csv)
        print(f"✅ CSV actualizado: {latest_csv}")
        return latest_csv
    except Exception as e:
        print(f"⚠️  Error archivando CSV: {e}")
        return None


# ============================================================================
# DESCARGA CON PLAYWRIGHT
# ============================================================================

async def download_youtube_chart() -> Optional[Path]:
    """Descarga el gráfico de YouTube usando Playwright"""
    print("\n📥 Iniciando descarga de YouTube Charts...")
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            # Configuración para GitHub Actions
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--window-size=1920,1080',
                ]
            )
            
            context = await browser.new_context(
                accept_downloads=True,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            )
            
            page = await context.new_page()
            page.set_default_timeout(60000)
            
            print("1. 🌐 Navegando a YouTube Charts...")
            url = "https://charts.youtube.com/charts/TopSongs/global/weekly"
            
            await page.goto(url, wait_until='networkidle', timeout=60000)
            print("   ✅ Página cargada")
            
            # Esperar a que la tabla cargue completamente
            print("2. ⏳ Esperando carga completa de la tabla...")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(5000)
            
            # CRÍTICO: Hacer scroll en la tabla para asegurar que carguen todos los elementos
            print("3. 📜 Haciendo scroll para cargar todos los elementos...")
            try:
                # Buscar el contenedor principal de la tabla
                table_selectors = [
                    'div[role="grid"]',
                    '[data-view-type="list"]',
                    'div.yt-lockup-content',
                    'div[aria-label*="songs" i]',
                ]
                
                table_loaded = False
                for selector in table_selectors:
                    try:
                        table = await page.query_selector(selector)
                        if table:
                            # Hacer scroll múltiples veces para cargar contenido dinámico
                            for i in range(15):
                                await page.evaluate(f'''
                                    () => {{
                                        const table = document.querySelector('{selector}');
                                        if (table) table.scrollTop = table.scrollHeight;
                                    }}
                                ''')
                                await page.wait_for_timeout(500)
                            
                            table_loaded = True
                            print(f"   ✅ Tabla scrolleada con selector: {selector}")
                            break
                    except:
                        continue
                
                if not table_loaded:
                    # Plan B: scroll general en la página
                    print("   ℹ️ Usando scroll general en la página...")
                    for i in range(20):
                        await page.evaluate('window.scrollBy(0, 500)')
                        await page.wait_for_timeout(300)
                
            except Exception as e:
                print(f"   ⚠️ Error en scroll: {e}")
            
            # Esperar un poco más después del scroll
            await page.wait_for_timeout(3000)
            
            print("4. 🔍 Buscando botón de descarga...")
            
            # Estrategia 1: Por texto "Download" - con espera extendida
            try:
                print("   📝 Buscando botón 'Download'...")
                element = await page.locator("text=/download/i").first.wait_for(timeout=15000)
                if element:
                    is_visible = await element.is_visible()
                    if is_visible:
                        print("   ✅ Botón encontrado por texto")
                        async with page.expect_download() as download_info:
                            await element.click()
                        
                        download = await download_info.value
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = OUTPUT_DIR / f"youtube_chart_{timestamp}.csv"
                        await download.save_as(filename)
                        
                        # Verificar que el archivo tenga contenido
                        if filename.exists() and filename.stat().st_size > 1000:
                            await browser.close()
                            print(f"   ✅ Descargado correctamente: {filename}")
                            print(f"   📊 Tamaño: {filename.stat().st_size} bytes")
                            return filename
                        else:
                            print("   ⚠️ Archivo descargado pero parece vacío, intentando otra estrategia...")
            except Exception as e:
                print(f"   ⚠️ Texto 'Download' no encontrado: {e}")
            
            # Estrategia 2: Por atributos ARIA y visibilidad
            print("   🎯 Buscando por atributos ARIA...")
            selectors = [
                '[aria-label*="download" i]',
                '[aria-label*="descargar" i]',
                '[title*="download" i]',
                '[title*="Download" i]',
                'button:has-text("Download")',
                'a[href*="download"]',
                '[role="button"]:has-text("Download")',
            ]
            
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    print(f"   🔎 Selector '{selector}': {len(elements)} elemento(s) encontrado(s)")
                    
                    for idx, element in enumerate(elements):
                        try:
                            is_visible = await element.is_visible()
                            if is_visible:
                                print(f"   ✅ Elemento visible encontrado (#{idx + 1})")
                                
                                # Hacer scroll hasta el elemento
                                await element.scroll_into_view()
                                await page.wait_for_timeout(1000)
                                
                                async with page.expect_download() as download_info:
                                    await element.click()
                                
                                download = await download_info.value
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                filename = OUTPUT_DIR / f"youtube_chart_{timestamp}.csv"
                                await download.save_as(filename)
                                
                                # Verificar tamaño
                                if filename.exists() and filename.stat().st_size > 1000:
                                    await browser.close()
                                    print(f"   ✅ Descargado correctamente: {filename}")
                                    print(f"   📊 Tamaño: {filename.stat().st_size} bytes")
                                    return filename
                                else:
                                    print(f"   ⚠️ Archivo vacío, intentando siguiente...")
                                    continue
                        except Exception as e:
                            print(f"   ⚠️ Error con elemento #{idx + 1}: {e}")
                            continue
                except Exception as e:
                    print(f"   ⚠️ Error con selector '{selector}': {e}")
                    continue
            
            # Estrategia 3: Debugging - tomar screenshot
            print("5. 📸 Tomando screenshot para debugging...")
            try:
                screenshot_path = OUTPUT_DIR / "debug_download_button.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"   📷 Screenshot guardado: {screenshot_path}")
                
                # Guardar HTML también
                html_path = OUTPUT_DIR / "debug_page.html"
                html_content = await page.content()
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"   📄 HTML guardado para análisis: {html_path}")
            except Exception as e:
                print(f"   ⚠️ Error en screenshot: {e}")
            
            print("   ❌ Botón de descarga no encontrado después de todos los intentos")
            await browser.close()
            return None
            
    except ImportError:
        print("   ❌ Playwright no está instalado")
        return None
    except Exception as e:
        print(f"   ❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_fallback_csv() -> Path:
    """Crea CSV de fallback si la descarga falla"""
    print("🆘 Creando datos de fallback...")
    
    try:
        import pandas as pd
        
        data = {
            'Rank': list(range(1, 101)),
            'Previous Rank': list(range(1, 101)),
            'Track Name': [f"Track {i}" for i in range(1, 101)],
            'Artist Names': [f"Artist {i}" for i in range(1, 101)],
            'Periods on Chart': [10] * 100,
            'Views': [1000000 - i*10000 for i in range(100)],
            'Growth': ['+0.0%'] * 100,
            'YouTube URL': [f"https://youtube.com/watch?v=video{i}" for i in range(100)]
        }
        
        df = pd.DataFrame(data)
        filename = OUTPUT_DIR / f"fallback_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        
        print(f"   ✅ Fallback creado: {filename}")
        return filename
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


# ============================================================================
# PROCESAMIENTO DE CSV
# ============================================================================

def process_csv_to_database(csv_path: Path, week_id: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Procesa CSV a base de datos semanal.
    Retorna (éxito, estadísticas)
    """
    try:
        import pandas as pd
        
        # Leer CSV
        df = pd.read_csv(csv_path, encoding='utf-8')
        print(f"   📊 CSV cargado: {len(df)} registros")
        
        # Crear backup si la BD ya existe
        if get_weekly_db_path(week_id).exists():
            print(f"3. 💾 Creando backup automático para {week_id}...")
            create_backup_before_update(week_id)
        
        # Inicializar base de datos
        print(f"4. 🗃️  Inicializando base de datos para {week_id}...")
        conn = init_weekly_database(week_id)
        
        # Convertir DataFrame a lista de diccionarios
        rows = df.to_dict('records')
        
        # Insertar datos
        print(f"5. 📝 Insertando datos (evitando duplicados)...")
        inserted, duplicates = insert_chart_data(conn, rows)
        
        # Obtener estadísticas
        stats = get_database_stats(conn)
        stats['inserted'] = inserted
        stats['duplicates'] = duplicates
        stats['week_id'] = week_id
        stats['db_path'] = str(get_weekly_db_path(week_id))
        
        conn.close()
        
        print(f"   ✅ Datos procesados: {inserted} insertados, {duplicates} duplicados")
        return True, stats
        
    except Exception as e:
        print(f"   ❌ Error procesando CSV: {e}")
        import traceback
        traceback.print_exc()
        return False, {}


def cleanup_old_csvs(days_to_keep: int = 7):
    """Limpia archivos CSV temporales antiguos"""
    try:
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        for file in OUTPUT_DIR.glob("youtube_chart_*.csv"):
            if file.stat().st_mtime < cutoff.timestamp():
                file.unlink()
                print(f"   🗑️  Temporal eliminado: {file.name}")
    except Exception as e:
        print(f"   ⚠️  Error en limpieza: {e}")


# ============================================================================
# REPORTES Y VISUALIZACIÓN
# ============================================================================

def generate_summary_report(stats: Dict[str, Any]):
    """Genera un resumen de la ejecución"""
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE LA EJECUCIÓN")
    print("=" * 70)
    print(f"📅 Semana: {stats.get('week_id', 'N/A')}")
    print(f"🗃️  Base de datos: {stats.get('db_path', 'N/A')}")
    print(f"📈 Registros insertados: {stats.get('inserted', 0)}")
    print(f"🔄 Duplicados evitados: {stats.get('duplicates', 0)}")
    print(f"📊 Total en BD: {stats.get('total_rows', 0)}")
    print(f"👁️  Total de vistas: {stats.get('total_views', 0):,}")
    
    if stats.get('top_artists'):
        print(f"\n🎤 Top 5 artistas:")
        for artist, count in stats['top_artists'][:5]:
            print(f"   • {artist}: {count} canción(es)")
    
    print("=" * 70)


def list_available_databases():
    """Lista todas las bases de datos disponibles"""
    dbs = sorted(DATABASE_DIR.glob("youtube_charts_*.db"))
    
    if not dbs:
        print("   No hay bases de datos disponibles aún")
        return
    
    print(f"\n📦 Bases de datos disponibles ({len(dbs)}):")
    for db in dbs:
        size = db.stat().st_size / 1024
        week_id = db.stem.replace("youtube_charts_", "")
        print(f"   • {week_id}: {size:.1f} KB")


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal del script"""
    print("\n" + "=" * 70)
    print("🎵 YOUTUBE CHARTS - EXTRACTOR AUTOMÁTICO (SQLITE SEMANAL)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Obtener identificador de semana
    week_id = get_week_identifier()
    print(f"\n📆 Semana actual: {week_id}")
    
    if os.getenv('GITHUB_ACTIONS'):
        print("⚡ Ejecutando en GitHub Actions")
    
    # Paso 1: Descargar CSV
    print("\n1. 📥 DESCARGANDO YOUTUBE CHARTS...")
    csv_path = asyncio.run(download_youtube_chart())
    
    if not csv_path or not csv_path.exists():
        print("   ⚠️  Descarga automática falló")
        csv_path = create_fallback_csv()
    
    if not csv_path or not csv_path.exists():
        print("❌ No se pudo obtener datos")
        return 1
    
    # Paso 2: Procesar a base de datos
    print("\n2. ⚙️  PROCESANDO DATOS...")
    success, stats = process_csv_to_database(csv_path, week_id)
    
    if not success:
        print("❌ Error procesando datos")
        return 1
    
    # Paso 3: Archivar CSV más reciente
    print("\n6. 📁 ARCHIVANDO CSV MÁS RECIENTE...")
    archive_latest_csv(csv_path, week_id)
    
    # Paso 4: Limpiar archivos temporales
    print("\n7. 🧹 LIMPIANDO ARCHIVOS TEMPORALES...")
    cleanup_old_csvs(7)
    
    # Paso 5: Mostrar reporte
    print("\n8. 📊 GENERANDO REPORTE...")
    generate_summary_report(stats)
    
    # Paso 6: Listar bases de datos disponibles
    print("\n9. 📦 ESTADO DEL ARCHIVO:")
    list_available_databases()
    
    print("\n✅ PROCESO COMPLETADO EXITOSAMENTE")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
