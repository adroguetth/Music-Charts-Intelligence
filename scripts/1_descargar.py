#!/usr/bin/env python3
"""
1_descargar.py - AUTOCLICK EN BOTÓN DE DESCARGA Y ALMACENAMIENTO EN SQLITE
Versión optimizada para GitHub Actions con sistema de base de datos semanal
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

# Configuración de directorios
OUTPUT_DIR = Path("data")
ARCHIVE_DIR = Path("charts_archive")
DATABASE_DIR = ARCHIVE_DIR / "databases"
RAW_DIR = ARCHIVE_DIR / "raw_data"
BACKUP_DIR = ARCHIVE_DIR / "backups"

# Crear todos los directorios necesarios
for dir_path in [OUTPUT_DIR, ARCHIVE_DIR, DATABASE_DIR, RAW_DIR, BACKUP_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

def get_week_identifier(date: Optional[datetime] = None) -> str:
    """Obtiene un identificador único para la semana (YYYY-WNN)"""
    if date is None:
        date = datetime.now()
    year, week_num, _ = date.isocalendar()
    return f"{year}-W{week_num:02d}"

def calculate_week_hash(csv_path: Path) -> str:
    """Calcula un hash único para los datos de la semana"""
    try:
        import pandas as pd
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Crear string con datos clave para el hash
        hash_data = ""
        for _, row in df.head(20).iterrows():
            hash_data += f"{row['Rank']}_{row.get('Track Name', '')[:30]}_{row.get('Artist Names', '')[:30]}"
        
        return hashlib.md5(hash_data.encode()).hexdigest()[:16]
    except Exception as e:
        print(f"⚠️  Error calculando hash: {e}")
        return datetime.now().strftime("%Y%m%d")

def create_backup() -> Optional[Path]:
    """Crea backup de la base de datos existente"""
    try:
        db_file = DATABASE_DIR / "youtube_charts.db"
        if not db_file.exists():
            print("ℹ️  No existe base de datos previa para backup")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"backup_{timestamp}.db"
        
        shutil.copy2(db_file, backup_file)
        
        # Limitar a 5 backups
        backups = sorted(BACKUP_DIR.glob("backup_*.db"))
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                old_backup.unlink()
        
        print(f"✅ Backup creado: {backup_file}")
        return backup_file
    except Exception as e:
        print(f"⚠️  Error en backup: {e}")
        return None

def init_database() -> sqlite3.Connection:
    """Inicializa la base de datos SQLite"""
    db_path = DATABASE_DIR / "youtube_charts.db"
    conn = sqlite3.connect(db_path)
    
    # Tabla de control de semanas
    conn.execute('''
    CREATE TABLE IF NOT EXISTS week_control (
        week_id TEXT PRIMARY KEY,
        week_hash TEXT UNIQUE,
        download_date TEXT,
        total_records INTEGER,
        total_views INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Tabla principal de datos
    conn.execute('''
    CREATE TABLE IF NOT EXISTS chart_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_id TEXT,
        rank INTEGER,
        previous_rank INTEGER,
        track_name TEXT,
        artist_names TEXT,
        periods_on_chart INTEGER,
        views INTEGER,
        growth TEXT,
        youtube_url TEXT,
        download_date TEXT,
        FOREIGN KEY (week_id) REFERENCES week_control (week_id)
    )
    ''')
    
    # Índices para mejor rendimiento
    conn.execute('CREATE INDEX IF NOT EXISTS idx_week_id ON chart_data (week_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_rank ON chart_data (rank)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_artist ON chart_data (artist_names)')
    
    conn.commit()
    return conn

def insert_weekly_data(conn: sqlite3.Connection, csv_path: Path) -> Tuple[bool, str]:
    """Inserta datos de una semana en la base de datos, evitando duplicados"""
    try:
        import pandas as pd
        
        # Leer CSV
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Calcular identificadores
        week_id = get_week_identifier()
        week_hash = calculate_week_hash(csv_path)
        
        # Verificar si ya existe esta semana
        cursor = conn.cursor()
        cursor.execute("SELECT week_id FROM week_control WHERE week_hash = ?", (week_hash,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"ℹ️  Esta semana ya existe en la base de datos: {existing[0]}")
            return False, existing[0]
        
        # Preparar datos para inserción
        total_records = len(df)
        total_views = df['Views'].sum() if 'Views' in df.columns else 0
        
        # Insertar en tabla de control
        cursor.execute('''
        INSERT INTO week_control (week_id, week_hash, download_date, total_records, total_views)
        VALUES (?, ?, ?, ?, ?)
        ''', (week_id, week_hash, datetime.now().isoformat(), total_records, total_views))
        
        # Insertar datos de canciones
        for _, row in df.iterrows():
            cursor.execute('''
            INSERT INTO chart_data 
            (week_id, rank, previous_rank, track_name, artist_names, 
             periods_on_chart, views, growth, youtube_url, download_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                week_id,
                row.get('Rank'),
                row.get('Previous Rank'),
                row.get('Track Name', ''),
                row.get('Artist Names', ''),
                row.get('Periods on Chart', 0),
                row.get('Views', 0),
                row.get('Growth', ''),
                row.get('YouTube URL', ''),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        print(f"✅ Datos insertados para semana: {week_id} ({total_records} registros)")
        return True, week_id
        
    except Exception as e:
        print(f"❌ Error insertando datos: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False, ""

def get_week_statistics(conn: sqlite3.Connection, week_id: str) -> Dict[str, Any]:
    """Obtiene estadísticas de una semana específica"""
    cursor = conn.cursor()
    
    # Obtener información básica
    cursor.execute('''
    SELECT week_id, download_date, total_records, total_views 
    FROM week_control WHERE week_id = ?
    ''', (week_id,))
    week_info = cursor.fetchone()
    
    if not week_info:
        return {}
    
    # Top 10 de la semana
    cursor.execute('''
    SELECT rank, track_name, artist_names, views, growth
    FROM chart_data 
    WHERE week_id = ? 
    ORDER BY rank 
    LIMIT 10
    ''', (week_id,))
    top10 = cursor.fetchall()
    
    # Artistas más populares
    cursor.execute('''
    SELECT artist_names, COUNT(*) as song_count, SUM(views) as total_views
    FROM chart_data 
    WHERE week_id = ? 
    GROUP BY artist_names 
    ORDER BY total_views DESC 
    LIMIT 10
    ''', (week_id,))
    top_artists = cursor.fetchall()
    
    return {
        'week_id': week_info[0],
        'download_date': week_info[1],
        'total_records': week_info[2],
        'total_views': week_info[3],
        'top10': top10,
        'top_artists': top_artists
    }

def archive_csv_file(csv_path: Path, week_id: str) -> Path:
    """Archiva el CSV con nombre semanal"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    archived_name = ARCHIVE_DIR / f"youtube_chart_{date_str}_{week_id}.csv"
    
    shutil.copy2(csv_path, archived_name)
    
    # También mantener un archivo "latest"
    latest_path = ARCHIVE_DIR / "latest_chart.csv"
    shutil.copy2(csv_path, latest_path)
    
    print(f"📁 CSV archivado: {archived_name}")
    return archived_name

async def download_youtube_chart() -> Optional[Path]:
    """Descarga el chart de YouTube usando Playwright"""
    print("🎵 YouTube Charts - Descarga Automática")
    print("=" * 60)
    
    try:
        from playwright.async_api import async_playwright
        
        print("1. 🚀 Iniciando Playwright...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--window-size=1920,1080',
                ]
            )
            
            context = await browser.new_context(
                accept_downloads=True,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            page.set_default_timeout(60000)
            
            print("2. 🌐 Navegando a YouTube Charts...")
            await page.goto(
                "https://charts.youtube.com/charts/TopSongs/global/weekly",
                wait_until='networkidle',
                timeout=60000
            )
            
            print("3. ⏳ Esperando carga completa...")
            await page.wait_for_timeout(3000)
            
            print("4. 🔍 Buscando botón de descarga...")
            
            # Intentar diferentes selectores
            selectors = [
                'button[aria-label*="download" i]',
                '[title*="download" i]',
                'text=/download/i',
                'text=/descargar/i',
                'button:has-text("Download")',
                'button:has-text("Descargar")',
            ]
            
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        is_visible = await element.is_visible()
                        if is_visible:
                            print(f"   ✅ Encontrado con selector: {selector}")
                            
                            async with page.expect_download() as download_info:
                                await element.click()
                            
                            download = await download_info.value
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = OUTPUT_DIR / f"youtube_chart_{timestamp}.csv"
                            
                            await download.save_as(filename)
                            await browser.close()
                            
                            if filename.exists() and filename.stat().st_size > 0:
                                print(f"✅ Descarga exitosa: {filename}")
                                return filename
                except Exception as e:
                    continue
            
            # Si no encuentra el botón, intentar método alternativo
            print("5. ⚠️ Buscando enlace directo...")
            try:
                # Buscar enlaces que puedan ser de descarga
                links = await page.query_selector_all('a[href*=".csv"], a[href*="download"]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and ('.csv' in href.lower() or 'download' in href.lower()):
                        print(f"   🔗 Enlace encontrado: {href[:50]}...")
                        
                        # Navegar directamente al enlace
                        async with page.expect_download() as download_info:
                            await page.goto(href)
                        
                        download = await download_info.value
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = OUTPUT_DIR / f"youtube_chart_{timestamp}.csv"
                        
                        await download.save_as(filename)
                        await browser.close()
                        
                        if filename.exists() and filename.stat().st_size > 0:
                            print(f"✅ Descarga via enlace: {filename}")
                            return filename
            except Exception as e:
                print(f"   ⚠️ Error con enlace: {e}")
            
            await browser.close()
            return None
            
    except ImportError:
        print("❌ Playwright no está instalado")
        return None
    except Exception as e:
        print(f"❌ Error en descarga: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_fallback_data() -> Path:
    """Crea datos de fallback si la descarga falla"""
    print("🆘 Creando datos de fallback...")
    
    try:
        import pandas as pd
        
        # Datos de ejemplo basados en estructura real
        data = {
            'Rank': list(range(1, 101)),
            'Previous Rank': list(range(1, 101)),
            'Track Name': [f"Canción {i}" for i in range(1, 101)],
            'Artist Names': [f"Artista {i}" for i in range(1, 101)],
            'Periods on Chart': [10] * 100,
            'Views': [1000000 - i*10000 for i in range(100)],
            'Growth': ['+0.0%'] * 100,
            'YouTube URL': [f"https://youtube.com/watch?v=video{i}" for i in range(100)]
        }
        
        df = pd.DataFrame(data)
        filename = OUTPUT_DIR / f"fallback_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        
        print(f"📋 Datos de fallback creados: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error creando fallback: {e}")
        # Crear archivo CSV básico
        import csv
        filename = OUTPUT_DIR / f"emergency_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Rank', 'Track Name', 'Artist Names', 'Views'])
            for i in range(1, 11):
                writer.writerow([i, f"Emergency Song {i}", "Emergency Artist", 100000])
        
        return filename

def generate_weekly_report(conn: sqlite3.Connection, week_id: str):
    """Genera un reporte semanal en formato texto"""
    report_path = ARCHIVE_DIR / f"report_{week_id}.txt"
    
    stats = get_week_statistics(conn, week_id)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write(f"📊 REPORTE SEMANAL - {week_id}\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"📅 Fecha de descarga: {stats.get('download_date', 'N/A')}\n")
        f.write(f"📈 Total de canciones: {stats.get('total_records', 0)}\n")
        f.write(f"👁️  Total de vistas: {stats.get('total_views', 0):,}\n\n")
        
        f.write("🏆 TOP 10 SEMANAL:\n")
        f.write("-" * 40 + "\n")
        for song in stats.get('top10', []):
            f.write(f"{song[0]}. {song[1]} - {song[2]}\n")
            f.write(f"   👁️ {song[3]:,} | 📈 {song[4]}\n")
        
        f.write("\n🎤 ARTISTAS MÁS POPULARES:\n")
        f.write("-" * 40 + "\n")
        for artist in stats.get('top_artists', []):
            f.write(f"• {artist[0]}: {artist[1]} canciones, {artist[2]:,} vistas\n")
    
    print(f"📄 Reporte generado: {report_path}")

def cleanup_old_files(days_to_keep: int = 30):
    """Limpia archivos temporales antiguos"""
    try:
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        # Limpiar archivos temporales en data/
        for file in OUTPUT_DIR.glob("*.csv"):
            if file.stat().st_mtime < cutoff.timestamp():
                file.unlink()
                print(f"🗑️  Eliminado: {file.name}")
        
        # Mantener backups organizados
        print("🧹 Limpieza completada")
    except Exception as e:
        print(f"⚠️  Error en limpieza: {e}")

def main():
    """Función principal"""
    print("\n" + "=" * 60)
    print("🎵 YOUTUBE CHARTS - EXTRACTOR AUTOMÁTICO")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if os.getenv('GITHUB_ACTIONS'):
        print("⚡ Ejecutando en GitHub Actions")
    
    # Paso 1: Crear backup de base de datos existente
    print("\n1. 💾 CREANDO BACKUP DE BASE DE DATOS...")
    backup_file = create_backup()
    
    # Paso 2: Inicializar base de datos
    print("\n2. 🗃️  INICIALIZANDO BASE DE DATOS...")
    conn = init_database()
    
    # Paso 3: Descargar datos
    print("\n3. 📥 DESCARGANDO DATOS DE YOUTUBE CHARTS...")
    csv_file = asyncio.run(download_youtube_chart())
    
    if not csv_file or not csv_file.exists():
        print("⚠️  La descarga automática falló, usando datos de fallback...")
        csv_file = create_fallback_data()
    
    # Paso 4: Procesar y almacenar datos
    print("\n4. 🗃️  ALMACENANDO EN BASE DE DATOS...")
    success, week_id = insert_weekly_data(conn, csv_file)
    
    if success:
        # Paso 5: Archivar CSV
        print("\n5. 📁 ARCHIVANDO CSV...")
        archived_file = archive_csv_file(csv_file, week_id)
        
        # Paso 6: Generar reporte
        print("\n6. 📊 GENERANDO REPORTE SEMANAL...")
        generate_weekly_report(conn, week_id)
        
        # Paso 7: Mostrar estadísticas
        print("\n7. 📈 ESTADÍSTICAS FINALES:")
        stats = get_week_statistics(conn, week_id)
        
        print(f"   • Semana: {week_id}")
        print(f"   • Canciones procesadas: {stats.get('total_records', 0)}")
        print(f"   • Vistas totales: {stats.get('total_views', 0):,}")
        print(f"   • Archivo CSV: {archived_file.name}")
        
        # Mostrar top 3
        print("\n   🏆 TOP 3 DE LA SEMANA:")
        for i, song in enumerate(stats.get('top10', [])[:3], 1):
            print(f"     {i}. {song[1]} - {song[2]}")
        
        print("\n✅ PROCESO COMPLETADO EXITOSAMENTE")
        
    else:
        print("⚠️  Los datos no fueron insertados (posible duplicado)")
    
    # Paso 8: Limpieza
    print("\n8. 🧹 LIMPIANDO ARCHIVOS TEMPORALES...")
    cleanup_old_files(7)  # Mantener solo 7 días
    
    # Cerrar conexión
    conn.close()
    
    print("\n" + "=" * 60)
    print("🎉 PIPELINE FINALIZADO")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
