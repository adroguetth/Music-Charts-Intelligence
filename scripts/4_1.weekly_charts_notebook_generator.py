#!/usr/bin/env python3
"""
Weekly Music Charts Analysis Notebook Generator
================================================
Automated generator for Jupyter notebooks that perform comprehensive analysis
of YouTube music charts data, including AI-generated insights via DeepSeek API.

Features:
- Automatic database download from GitHub or local fallback
- AI-generated insights for each analysis section with language support
- Caching system per week and language to avoid redundant API calls
- Generates two notebooks: English and Spanish
- Full analysis with 12 sections + introduction + attribution + 25+ visualizations

Usage:
    python 4_1.weekly_charts_notebook_generator.py [--week YYYY-WXX] [--language en|es|both]

Environment Variables:
    DEEPSEEK_API_KEY: Your DeepSeek API key

Output:
    Creates notebook files in:
    - Notebook_EN/weekly/youtube_charts_YYYY-WXX.ipynb
    - Notebook_ES/weekly/youtube_charts_YYYY-WXX.ipynb

Author: Alfonso Droguett
License: MIT
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
import os
import sys
import json
import requests
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from scipy.stats import gaussian_kde
import warnings
import nbformat as nbf
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell

warnings.filterwarnings('ignore')

# ============================================================
# Configuration
# ============================================================

class Config:
    """Configuration settings for the notebook generator."""

    # GitHub repository
    REPO_OWNER = "adroguetth"
    REPO_NAME = "Music-Charts-Intelligence"
    FOLDER_PATH = "charts_archive/3_enrich-chart-data"

    # Local paths
    LOCAL_DB_PATH = Path(".")
    CHARTS_ARCHIVE_PATH = Path("charts_archive/3_enrich-chart-data")
    
    # Output paths
    OUTPUT_EN_PATH = Path("Notebook_EN/weekly")
    OUTPUT_ES_PATH = Path("Notebook_ES/weekly")
    CACHE_EN_PATH = Path("Notebook_EN/weekly/cache")
    CACHE_ES_PATH = Path("Notebook_ES/weekly/cache")

    # DeepSeek API
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

    # Colors (YouTube-inspired)
    YT_RED = '#FF0000'
    YT_RED_DARK = '#CC0000'
    YT_BG = '#FFFFFF'
    YT_SURFACE = '#F9F9F9'
    YT_TEXT = '#0F0F0F'
    YT_GRAY = '#606060'
    YT_GRID = '#E5E5E5'


# ============================================================
# AI Insights with Language-Specific Cache
# ============================================================

class AIInsightsCache:
    """
    Cache manager for AI-generated insights to avoid redundant API calls.
    
    Cache is isolated by week and language to ensure:
    - Different language versions don't share cache
    - Each weekly analysis has its own cache file
    - Cache keys are data-fingerprint based for content validation
    """
    
    def __init__(self, week: str, language: str):
        """
        Initialize cache manager.
        
        Args:
            week: Week identifier (YYYY-WXX)
            language: Language code ('en' or 'es')
        """
        self.week = week
        self.language = language
        self.cache_dir = Config.CACHE_EN_PATH if language == 'en' else Config.CACHE_ES_PATH
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / f"youtube_charts_{week}_{language}.json"
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cache from disk with error handling."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load cache {self.cache_file}: {e}")
                return {}
        return {}

    def _save_cache(self) -> None:
        """Persist cache to disk."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Failed to save cache {self.cache_file}: {e}")

    def _get_data_hash(self, df: pd.DataFrame, section: str) -> str:
        """
        Generate data fingerprint hash for cache key.
        
        Uses key columns that indicate data freshness. Different sections
        use different data subsets to optimize hash computation.
        
        Args:
            df: DataFrame with music chart data
            section: Analysis section identifier
            
        Returns:
            MD5 hash of data subset
        """
        if section == 'general_stats':
            key_data = f"{len(df)}_{df['views'].sum()}_{df['likes'].sum()}"
        elif section == 'top_countries':
            key_data = df['artist_country'].value_counts().head(10).to_string()
        elif section == 'genre_engagement':
            key_data = df.groupby('macro_genre')['engagement'].mean().to_string()
        elif section == 'temporal':
            key_data = df.groupby('upload_quarter')['views'].sum().to_string()
        elif section == 'introduction':
            key_data = f"{len(df)}_{df['views'].sum()}_{df['likes'].sum()}_{df['artist_country'].nunique()}_{df['macro_genre'].nunique()}"
        elif section in ('top_songs_views', 'top_songs_likes', 'top_songs_engagement'):
            key_data = df.nlargest(10, section.split('_')[-1])['track_name'].to_string()
        else:
            key_data = df.to_string()
            
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_insight(self, section: str, df: pd.DataFrame, data_summary: Dict) -> Optional[str]:
        """
        Retrieve cached insight if available and data hasn't changed.
        
        Args:
            section: Analysis section identifier
            df: Full DataFrame for hash generation
            data_summary: Summary dict (unused, kept for API consistency)
            
        Returns:
            Cached insight text or None if not found
        """
        data_hash = self._get_data_hash(df, section)
        key = f"{section}_{data_hash}"
        return self.cache.get(key)

    def save_insight(self, section: str, df: pd.DataFrame, data_summary: Dict, insight: str) -> None:
        """
        Save insight to cache with data fingerprint.
        
        Args:
            section: Analysis section identifier
            df: Full DataFrame for hash generation
            data_summary: Summary dict (unused, kept for API consistency)
            insight: AI-generated insight text
        """
        data_hash = self._get_data_hash(df, section)
        key = f"{section}_{data_hash}"
        self.cache[key] = insight
        self._save_cache()


def get_ai_insight(section: str, data_summary: Dict, df: pd.DataFrame, language: str, week: str) -> str:
    """
    Query DeepSeek API for section insights with language-aware caching.
    
    Args:
        section: Analysis section identifier
        data_summary: Pre-aggregated metrics for the section
        df: Full DataFrame for cache key generation
        language: Output language ('en' or 'es')
        week: Week identifier for cache isolation (YYYY-WXX)
    
    Returns:
        AI-generated insight text or error message
    """
    cache = AIInsightsCache(week, language)

    # Check cache first
    cached = cache.get_insight(section, df, data_summary)
    if cached:
        print(f"   Using cached insight for {section} ({language})")
        return cached

    print(f"   Generating new insight for {section} ({language})...")

    if not Config.DEEPSEEK_API_KEY:
        return "AI insights not available (API key not configured). Set DEEPSEEK_API_KEY environment variable."

    # Language-specific prompts
    if language == 'es':
        prompts = {
            "introduction": f"""
Escribe una introducción atractiva y personalizada para un informe semanal de charts musicales de YouTube, basada en estos datos:

- Total canciones analizadas: {data_summary.get('total_songs', 'N/A')}
- Países representados: {data_summary.get('unique_countries', 'N/A')}
- Géneros musicales: {data_summary.get('unique_genres', 'N/A')}
- Total de vistas: {data_summary.get('total_views', 0):,}
- Total de likes: {data_summary.get('total_likes', 0):,}
- Promedio de vistas por canción: {data_summary.get('avg_views', 0):,.0f}
- Promedio de likes por canción: {data_summary.get('avg_likes', 0):,.0f}

La introducción debe:
- Ser persuasiva, invitando al lector a explorar el informe.
- Destacar la riqueza y diversidad de los datos (geográfica, de géneros, volumen de interacción).
- Mencionar brevemente qué tipo de insights se encontrarán (tendencias por país, engagement por género, rendimiento de colaboraciones, etc.).
- Ser original y variar cada semana (no un texto genérico).
- Tener una extensión de 6-8 líneas en español.

No uses títulos ni markdown, solo texto plano en un solo párrafo.
""",
            "general_stats": f"""
Analiza estas estadísticas generales de música:
- Total canciones: {data_summary.get('total_songs', 'N/A')}
- Países únicos: {data_summary.get('unique_countries', 'N/A')}
- Géneros únicos: {data_summary.get('unique_genres', 'N/A')}
- Total vistas: {data_summary.get('total_views', 0):,}
- Total likes: {data_summary.get('total_likes', 0):,}
- Promedio vistas: {data_summary.get('avg_views', 0):,.0f}
- Promedio likes: {data_summary.get('avg_likes', 0):,.0f}

Proporciona un análisis explicativo (4-5 líneas) en español destacando:
- Diversidad geográfica y de géneros, y qué implica para el alcance global.
- Niveles de engagement y qué indican sobre la conexión audiencia-artista.
- Insights principales sobre el comportamiento del mercado musical actual.
""",

            "top_countries": f"""
Analiza los top países por cantidad de canciones:
{data_summary.get('top_countries', 'N/A')}

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Qué países dominan el ranking y por qué (industria musical, población, acceso a internet, cultura de consumo musical).
- Patrones geográficos observados (concentración en ciertas regiones).
- Implicaciones para artistas que buscan expandir su audiencia internacional.
""",

            "top_likes": f"""
Analiza los top países por total de likes:
{data_summary.get('top_likes', 'N/A')}

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Qué países generan más engagement y por qué (cultura de fans, tamaño de mercado, plataformas locales).
- Diferencias entre top por canciones vs top por likes (qué revela sobre la calidad de la interacción).
- Estrategias para artistas que buscan maximizar el engagement en regiones específicas.
""",

            "genre_engagement": f"""
Analiza las tasas de engagement por género:
{data_summary.get('genre_engagement', 'N/A')}

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Géneros con mayor y menor engagement y por qué (comunidades de fans más apasionadas, nichos específicos).
- Posibles explicaciones para estas diferencias (ritmo, lírica, cultura del género).
- Implicaciones para creadores de contenido al elegir un género.
""",

            "video_metrics": f"""
Analiza las métricas de video:
- Videos oficiales: {data_summary.get('official_pct', 0):.1f}% ({data_summary.get('official_views', 0):,.0f} avg views)
- Lyric videos: {data_summary.get('lyric_pct', 0):.1f}% ({data_summary.get('lyric_views', 0):,.0f} avg views)
- Live performances: {data_summary.get('live_pct', 0):.1f}% ({data_summary.get('live_views', 0):,.0f} avg views)
- Engagement promedio: {data_summary.get('avg_engagement', 0):.1f}%

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Qué tipo de video funciona mejor en términos de vistas y por qué (expectativas de la audiencia, producción, novedad).
- Preferencias de la audiencia según el tipo de contenido.
- Recomendaciones para artistas según sus objetivos (alcance masivo vs fidelización).
""",

            "engagement_by_type": f"""
Analiza las tasas de engagement por tipo de video:
- Official videos: {data_summary.get('official_engagement', 0):.2f}%
- Lyric videos: {data_summary.get('lyric_engagement', 0):.2f}%
- Live performances: {data_summary.get('live_engagement', 0):.2f}%

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Qué tipo de video genera mejor engagement (no solo vistas) y por qué.
- Por qué los lyric videos pueden tener mejor o peor engagement (concentración en la letra vs producción visual).
- Recomendaciones para artistas según su objetivo (engagement vs alcance).
""",

            "top_songs_views": f"""
Analiza las 10 canciones con más vistas:
{data_summary.get('top_songs_views_list', 'N/A')}

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Patrones comunes entre estas canciones (artistas, géneros, países, tendencias virales).
- Qué factores pueden explicar su éxito en vistas (marketing, colaboraciones, momento de lanzamiento).
- Implicaciones para artistas que buscan maximizar vistas.
""",

            "top_songs_likes": f"""
Analiza las 10 canciones con más likes:
{data_summary.get('top_songs_likes_list', 'N/A')}

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Relación entre likes y vistas (engagement rate) y qué indica sobre la calidad de la canción.
- Qué características tienen las canciones más queridas por el público (emocionales, pegadizas, con mensaje).
- Diferencias con el ranking de vistas y qué revela sobre el comportamiento del usuario.
""",

            "top_songs_engagement": f"""
Analiza las 10 canciones con mayor engagement (likes/views %):
{data_summary.get('top_songs_engagement_list', 'N/A')}

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Qué tipo de canciones generan más engagement proporcional (nichos, fandom leal, contenido emotivo).
- Estrategias para aumentar el engagement (call to action, comunidad, interacción).
- Relación con nichos de audiencia más comprometidos y cómo capitalizarlos.
""",

            "duration": f"""
Analiza la duración de videos:
- Duración promedio: {data_summary.get('avg_duration', 0):.1f} minutos
- Mediana: {data_summary.get('median_duration', 0):.1f} minutos
- Mínimo: {data_summary.get('min_duration', 0):.1f} min
- Máximo: {data_summary.get('max_duration', 0):.1f} min

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Rango típico de duración y cómo se compara con estándares de la industria.
- Implicaciones para creadores sobre la atención de la audiencia y retención.
- Estrategias de duración según el género o tipo de contenido.
""",

            "temporal": f"""
Analiza las tendencias temporales:
- Vistas por trimestre: {data_summary.get('quarterly_views', {})}
- Engagement por trimestre: {data_summary.get('quarterly_engagement', {})}

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Patrones estacionales observados (picos en ciertos trimestres, por ejemplo lanzamientos de fin de año).
- Evolución del engagement y posibles causas (cambios en algoritmo, comportamiento del usuario).
- Tendencias relevantes para la planificación de lanzamientos.
""",

            "collaborations": f"""
Analiza el impacto de las colaboraciones:
- Canciones solistas: {data_summary.get('solo_count', 0)} ({data_summary.get('solo_views', 0):,.0f} avg views, {data_summary.get('solo_engagement', 0):.1f}% engagement)
- Colaboraciones: {data_summary.get('collab_count', 0)} ({data_summary.get('collab_views', 0):,.0f} avg views, {data_summary.get('collab_engagement', 0):.1f}% engagement)

Proporciona un análisis explicativo (4-5 líneas) en español sobre:
- Si las colaboraciones tienen mejor rendimiento y por qué (sinergia de fans, diversidad de estilos).
- Posibles razones (alcance cruzado, novedad, producción conjunta).
- Estrategias recomendadas para artistas según su etapa de carrera.
""",

            "executive_summary": f"""
Genera un resumen ejecutivo detallado (30 líneas aproximadamente) en español del análisis completo de charts musicales con los siguientes datos clave:

DATOS GENERALES:
- Total canciones: {data_summary.get('total_songs', 'N/A')}
- Países representados: {data_summary.get('unique_countries', 'N/A')}
- Géneros musicales: {data_summary.get('unique_genres', 'N/A')}
- Total vistas: {data_summary.get('total_views', 0):,}
- Total likes: {data_summary.get('total_likes', 0):,}

TOP PAÍSES POR CANCIONES:
{data_summary.get('top_countries', 'N/A')}

TOP PAÍSES POR LIKES:
{data_summary.get('top_likes', 'N/A')}

ENGAGEMENT POR GÉNERO (Top 3):
{data_summary.get('genre_engagement_top', 'N/A')}

MÉTRICAS DE VIDEO:
- Tipo más efectivo: {data_summary.get('best_video_type', 'N/A')}
- Engagement promedio: {data_summary.get('avg_engagement', 0):.1f}%
- Duración promedio: {data_summary.get('avg_duration', 0):.1f} min

COLABORACIONES:
- {data_summary.get('collab_impact', 'N/A')}

Proporciona un resumen ejecutivo DETALLADO (30 líneas) en español que:
1. Resuma los hallazgos principales con datos concretos
2. Destaque las tendencias clave observadas (geográficas, de género, temporales)
3. Analice el rendimiento por tipo de contenido (video, colaboraciones)
4. Ofrezca conclusiones estratégicas y recomendaciones accionables para artistas, productores y estrategias de marketing musical
5. Sea rico en contenido, con un tono profesional pero accesible.
"""
        }
    else:
        prompts = {
            "introduction": f"""
Write an engaging and personalized introduction for a weekly YouTube music charts report, based on this data:

- Total songs analyzed: {data_summary.get('total_songs', 'N/A')}
- Countries represented: {data_summary.get('unique_countries', 'N/A')}
- Music genres: {data_summary.get('unique_genres', 'N/A')}
- Total views: {data_summary.get('total_views', 0):,}
- Total likes: {data_summary.get('total_likes', 0):,}
- Average views per song: {data_summary.get('avg_views', 0):,.0f}
- Average likes per song: {data_summary.get('avg_likes', 0):,.0f}

The introduction should:
- Be persuasive, inviting the reader to explore the report.
- Highlight the richness and diversity of the data (geographic, genre, interaction volume).
- Briefly mention what kind of insights will be found (country trends, genre engagement, collaboration performance, etc.).
- Be original and vary each week (not generic text).
- Be 6-8 lines long in English.

Do not use titles or markdown, just plain text in a single paragraph.
""",
            "general_stats": f"""
Analyze these general music statistics:
- Total songs: {data_summary.get('total_songs', 'N/A')}
- Unique countries: {data_summary.get('unique_countries', 'N/A')}
- Unique genres: {data_summary.get('unique_genres', 'N/A')}
- Total views: {data_summary.get('total_views', 0):,}
- Total likes: {data_summary.get('total_likes', 0):,}
- Average views: {data_summary.get('avg_views', 0):,.0f}
- Average likes: {data_summary.get('avg_likes', 0):,.0f}

Provide an explanatory analysis (4-5 lines) highlighting:
- Geographic and genre diversity and what it implies for global reach.
- Engagement levels and what they indicate about audience-artist connection.
- Key insights about current music market behavior.
""",

            "top_countries": f"""
Analyze the top countries by song count:
{data_summary.get('top_countries', 'N/A')}

Provide an explanatory analysis (4-5 lines) about:
- Which countries dominate the ranking and why (music industry size, population, internet access, music consumption culture).
- Observed geographic patterns (concentration in certain regions).
- Implications for artists looking to expand their international audience.
""",

            "top_likes": f"""
Analyze the top countries by total likes:
{data_summary.get('top_likes', 'N/A')}

Provide an explanatory analysis (4-5 lines) about:
- Which countries generate the most engagement and why (fan culture, market size, local platforms).
- Differences between top by songs vs top by likes (what it reveals about interaction quality).
- Strategies for artists aiming to maximize engagement in specific regions.
""",

            "genre_engagement": f"""
Analyze engagement rates by genre:
{data_summary.get('genre_engagement', 'N/A')}

Provide an explanatory analysis (4-5 lines) about:
- Genres with highest and lowest engagement and why (more passionate fan communities, niche specifics).
- Possible explanations for these differences (tempo, lyrics, genre culture).
- Implications for content creators when choosing a genre.
""",

            "video_metrics": f"""
Analyze video metrics:
- Official videos: {data_summary.get('official_pct', 0):.1f}% ({data_summary.get('official_views', 0):,.0f} avg views)
- Lyric videos: {data_summary.get('lyric_pct', 0):.1f}% ({data_summary.get('lyric_views', 0):,.0f} avg views)
- Live performances: {data_summary.get('live_pct', 0):.1f}% ({data_summary.get('live_views', 0):,.0f} avg views)
- Average engagement: {data_summary.get('avg_engagement', 0):.1f}%

Provide an explanatory analysis (4-5 lines) about:
- Which video type performs best in terms of views and why (audience expectations, production quality, novelty).
- Audience preferences based on content type.
- Recommendations for artists based on their goals (mass reach vs loyalty building).
""",

            "engagement_by_type": f"""
Analyze engagement rates by video type:
- Official videos: {data_summary.get('official_engagement', 0):.2f}%
- Lyric videos: {data_summary.get('lyric_engagement', 0):.2f}%
- Live performances: {data_summary.get('live_engagement', 0):.2f}%

Provide an explanatory analysis (4-5 lines) about:
- Which video type generates better engagement (not just views) and why.
- Why lyric videos may have higher or lower engagement (focus on lyrics vs visual production).
- Recommendations for artists based on their objective (engagement vs reach).
""",

            "top_songs_views": f"""
Analyze the top 10 songs by views:
{data_summary.get('top_songs_views_list', 'N/A')}

Provide an explanatory analysis (4-5 lines) about:
- Common patterns among these songs (artists, genres, countries, viral trends).
- Factors that may explain their success in views (marketing, collaborations, release timing).
- Implications for artists seeking to maximize views.
""",

            "top_songs_likes": f"""
Analyze the top 10 songs by likes:
{data_summary.get('top_songs_likes_list', 'N/A')}

Provide an explanatory analysis (4-5 lines) about:
- Relationship between likes and views (engagement rate) and what it indicates about song quality.
- Characteristics of the most loved songs by audiences (emotional, catchy, message-driven).
- Differences from the views ranking and what it reveals about user behavior.
""",

            "top_songs_engagement": f"""
Analyze the top 10 songs by engagement (likes/views %):
{data_summary.get('top_songs_engagement_list', 'N/A')}

Provide an explanatory analysis (4-5 lines) about:
- What type of songs generate higher proportional engagement (niches, loyal fandom, emotional content).
- Strategies to increase engagement (call to action, community building, interaction).
- Relationship with more committed audience niches and how to capitalize on them.
""",

            "duration": f"""
Analyze video duration:
- Average duration: {data_summary.get('avg_duration', 0):.1f} minutes
- Median: {data_summary.get('median_duration', 0):.1f} minutes
- Minimum: {data_summary.get('min_duration', 0):.1f} min
- Maximum: {data_summary.get('max_duration', 0):.1f} min

Provide an explanatory analysis (4-5 lines) about:
- Typical duration range and how it compares to industry standards.
- Implications for creators regarding audience attention span and retention.
- Duration strategies based on genre or content type.
""",

            "temporal": f"""
Analyze temporal trends:
- Views by quarter: {data_summary.get('quarterly_views', {})}
- Engagement by quarter: {data_summary.get('quarterly_engagement', {})}

Provide an explanatory analysis (4-5 lines) about:
- Observed seasonal patterns (peaks in certain quarters, e.g., year-end releases).
- Engagement evolution and possible causes (algorithm changes, user behavior shifts).
- Relevant trends for release planning.
""",

            "collaborations": f"""
Analyze the impact of collaborations:
- Solo songs: {data_summary.get('solo_count', 0)} ({data_summary.get('solo_views', 0):,.0f} avg views, {data_summary.get('solo_engagement', 0):.1f}% engagement)
- Collaborations: {data_summary.get('collab_count', 0)} ({data_summary.get('collab_views', 0):,.0f} avg views, {data_summary.get('collab_engagement', 0):.1f}% engagement)

Provide an explanatory analysis (4-5 lines) about:
- Whether collaborations perform better and why (fan synergy, style diversity).
- Possible reasons (cross-reach, novelty, joint production).
- Recommended strategies for artists based on their career stage.
""",

            "executive_summary": f"""
Generate a detailed executive summary (approximately 30 lines) of the complete music charts analysis with the following key data:

GENERAL DATA:
- Total songs: {data_summary.get('total_songs', 'N/A')}
- Countries represented: {data_summary.get('unique_countries', 'N/A')}
- Music genres: {data_summary.get('unique_genres', 'N/A')}
- Total views: {data_summary.get('total_views', 0):,}
- Total likes: {data_summary.get('total_likes', 0):,}

TOP COUNTRIES BY SONGS:
{data_summary.get('top_countries', 'N/A')}

TOP COUNTRIES BY LIKES:
{data_summary.get('top_likes', 'N/A')}

ENGAGEMENT BY GENRE (Top 3):
{data_summary.get('genre_engagement_top', 'N/A')}

VIDEO METRICS:
- Most effective type: {data_summary.get('best_video_type', 'N/A')}
- Average engagement: {data_summary.get('avg_engagement', 0):.1f}%
- Average duration: {data_summary.get('avg_duration', 0):.1f} min

COLLABORATIONS:
- {data_summary.get('collab_impact', 'N/A')}

Provide a DETAILED executive summary (30 lines) that:
1. Summarizes main findings with concrete data points
2. Highlights key observed trends (geographic, genre, temporal)
3. Analyzes content type performance (video, collaborations)
4. Offers strategic conclusions and actionable recommendations for artists, producers, and music marketing strategies
5. Is rich in content, with a professional yet accessible tone.
"""
        }

    prompt = prompts.get(section, f"Analyze this music data: {data_summary}")

    try:
        # Set max_tokens higher for introduction and executive_summary
        if section in ["introduction", "executive_summary"]:
            max_tokens = 2000  # Increased to allow for 30 lines
        else:
            max_tokens = 600
            
        response = requests.post(
            Config.DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are an expert music data analyst. Provide concise, insightful analysis. Use a professional yet accessible tone."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": max_tokens
            },
            timeout=30
        )

        if response.status_code == 200:
            insight = response.json()["choices"][0]["message"]["content"].strip()
            cache.save_insight(section, df, data_summary, insight)
            return insight
        else:
            return f"AI API error: {response.status_code} - {response.text[:200]}"

    except Exception as e:
        return f"AI insight unavailable: {str(e)}"


# ============================================================
# Database Operations
# ============================================================

def download_latest_db() -> Tuple[Path, int, int]:
    """Download the most recent database from GitHub repository."""
    api_url = f"https://api.github.com/repos/{Config.REPO_OWNER}/{Config.REPO_NAME}/contents/{Config.FOLDER_PATH}"

    print("Searching for databases on GitHub...")
    response = requests.get(api_url)

    if response.status_code != 200:
        raise Exception(f"Failed to access GitHub API: {response.status_code}")

    files = response.json()
    db_files = [f for f in files if f['name'].endswith('.db')]

    if not db_files:
        raise Exception("No .db files found in repository")

    def get_year_week(filename: str) -> Tuple[int, int]:
        match = re.search(r'(\d{4})-W(\d+)', filename)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return (0, 0)

    db_files.sort(key=lambda f: get_year_week(f['name']), reverse=True)

    latest = db_files[0]
    year, week = get_year_week(latest['name'])

    print(f"Found: {latest['name']} (Week {week}, {year})")
    print(f"Downloading...")

    db_response = requests.get(latest['download_url'])
    local_path = Path(latest['name'])

    with open(local_path, 'wb') as f:
        f.write(db_response.content)

    print(f"Saved to: {local_path}")

    return local_path, year, week


def get_local_db(week: Optional[str] = None) -> Tuple[Optional[Path], int, int]:
    """Find the most recent or specified database in local directory."""
    if week:
        db_path = Config.CHARTS_ARCHIVE_PATH / f"youtube_charts_{week}_enriched.db"
        if db_path.exists():
            year, w = week.split('-W')
            return db_path, int(year), int(w)
        return None, 0, 0
    
    db_files = list(Config.CHARTS_ARCHIVE_PATH.glob("youtube_charts_*.db"))

    if not db_files:
        return None, 0, 0

    def get_year_week(filename: Path) -> Tuple[int, int]:
        match = re.search(r'(\d{4})-W(\d+)', filename.name)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return (0, 0)

    db_files.sort(key=get_year_week, reverse=True)
    latest = db_files[0]
    year, week_num = get_year_week(latest)

    return latest, year, week_num


def load_data(db_path: Path) -> pd.DataFrame:
    """Load and prepare data from SQLite database."""
    conn = sqlite3.connect(db_path)

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    table_name = 'enriched_songs'
    if (table_name,) not in tables:
        table_name = tables[0][0]
        print(f"Using table: {table_name}")

    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()

    df['upload_date'] = pd.to_datetime(df['upload_date'], errors='coerce')
    df['upload_quarter'] = df['upload_date'].dt.quarter
    # Avoid division by zero: set engagement to 0 where views == 0
    df['engagement'] = np.where(df['views'] > 0, (df['likes'] / df['views'] * 100).round(2), 0.0)

    return df


# ============================================================
# Formatting Helpers
# ============================================================

def format_number(x: float) -> str:
    """Format large numbers with K/M/B suffixes."""
    if pd.isna(x):
        return "N/A"
    if x >= 1_000_000_000:
        return f"{x/1_000_000_000:.1f}B"
    elif x >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    elif x >= 1_000:
        return f"{x/1_000:.1f}K"
    return f"{x:,.0f}"


# ============================================================
# Notebook Generation with nbformat
# ============================================================

def get_section_titles(language: str) -> Dict[str, str]:
    """Get section titles in specified language."""
    if language == 'es':
        return {
            "title": "Análisis Enriquecido de Charts Musicales",
            "introduction": "## 1. Introducción",
            "setup": "## 2. Configuración y Carga de Datos",
            "preview": "## 3. Vista Previa de los Datos",
            "general_stats": "## 4. Estadísticas Generales",
            "country_analysis": "## 5. Análisis por País",
            "continent": "### 5.1. Distribución por Continente",
            "top_countries_songs": "### 5.2. Top Países por Cantidad de Canciones",
            "top_countries_likes": "### 5.3. Top Países por Total de Likes",
            "top_songs_country": "### 5.4. Top 5 Canciones por País",
            "genre_analysis": "## 6. Análisis por Género",
            "treemap": "### 6.1. Treemap de Distribución de Géneros",
            "engagement_genre": "### 6.2. Tasa de Engagement por Género",
            "country_genre_heatmap": "### 6.3. Heatmap País-Género",
            "song_metrics": "## 7. Métricas de Canciones",
            "top_views": "### 7.1. Top Canciones por Vistas",
            "top_likes": "### 7.2. Top Canciones por Likes",
            "top_engagement": "### 7.3. Top Canciones por Engagement",
            "video_metrics": "## 8. Métricas de Video",
            "views_by_type": "### 8.1. Vistas por Tipo de Video",
            "engagement_by_type": "### 8.2. Engagement por Tipo de Video",
            "duration_analysis": "### 8.3. Análisis de Duración",
            "channel_type": "### 8.4. Distribución por Tipo de Canal",
            "temporal_analysis": "## 9. Análisis Temporal",
            "views_evolution": "### 9.1. Evolución de Vistas por Trimestre",
            "engagement_evolution": "### 9.2. Evolución del Engagement por Trimestre",
            "release_distribution": "### 9.3. Distribución de Lanzamientos por Trimestre",
            "collaborations": "## 10. Análisis de Colaboraciones",
            "executive_summary": "## 11. Resumen Ejecutivo",
            "attribution": "## 12. Información y Atribución"
        }
    else:
        return {
            "title": "Enriched Music Charts Analysis",
            "introduction": "## 1. Introduction",
            "setup": "## 2. Setup and Data Loading",
            "preview": "## 3. Data Preview",
            "general_stats": "## 4. General Statistics",
            "country_analysis": "## 5. Country Analysis",
            "continent": "### 5.1. Continent Distribution",
            "top_countries_songs": "### 5.2. Top Countries by Song Count",
            "top_countries_likes": "### 5.3. Top Countries by Total Likes",
            "top_songs_country": "### 5.4. Top 5 Songs by Country",
            "genre_analysis": "## 6. Genre Analysis",
            "treemap": "### 6.1. Genre Distribution Treemap",
            "engagement_genre": "### 6.2. Engagement Rate by Genre",
            "country_genre_heatmap": "### 6.3. Country-Genre Distribution Heatmap",
            "song_metrics": "## 7. Song Metrics",
            "top_views": "### 7.1. Top Songs by Views",
            "top_likes": "### 7.2. Top Songs by Likes",
            "top_engagement": "### 7.3. Top Songs by Engagement",
            "video_metrics": "## 8. Video Metrics",
            "views_by_type": "### 8.1. Views by Video Type",
            "engagement_by_type": "### 8.2. Engagement by Video Type",
            "duration_analysis": "### 8.3. Video Duration Analysis",
            "channel_type": "### 8.4. Channel Type Distribution",
            "temporal_analysis": "## 9. Temporal Analysis",
            "views_evolution": "### 9.1. Views Evolution by Quarter",
            "engagement_evolution": "### 9.2. Engagement Evolution by Quarter",
            "release_distribution": "### 9.3. Release Distribution by Quarter",
            "collaborations": "## 10. Collaborations Analysis",
            "executive_summary": "## 11. Executive Summary",
            "attribution": "## 12. Information and Attribution"
        }


def generate_notebook(df: pd.DataFrame, db_info: Tuple[Path, int, int],
                      insights: Dict[str, str], output_path: Path, language: str) -> None:
    """
    Generate a Jupyter notebook with analysis cells and AI insights using nbformat.
    
    Args:
        df: DataFrame with enriched music data
        db_info: Tuple of (database_path, year, week)
        insights: Dictionary of AI insights by section
        output_path: Path where notebook will be saved
        language: Language code ('en' or 'es')
    """
    db_path, year, week = db_info
    db_filename = db_path.name
    titles = get_section_titles(language)

    # Create new notebook with nbformat
    nb = new_notebook()
    
    # Set notebook metadata
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.12.3"
        }
    }

    # Title cell
    nb.cells.append(new_markdown_cell(f"""# {titles['title']}
"""))

    # Add week/year information below title (before introduction)
    nb.cells.append(new_markdown_cell(f"""
**Week:** {year}-W{week:02d} | **Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}
"""))

    # Introduction (AI-generated)
    nb.cells.append(new_markdown_cell(titles['introduction']))
    if insights.get('introduction'):
        nb.cells.append(new_markdown_cell(insights['introduction']))
    else:
        nb.cells.append(new_markdown_cell("*No AI introduction available. Please configure DEEPSEEK_API_KEY to generate an engaging introduction.*"))

    # Setup and Data Loading
    nb.cells.append(new_markdown_cell(titles['setup']))
    nb.cells.append(new_code_cell(f"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import squarify
import sqlite3
import os
from scipy.stats import gaussian_kde
import warnings
warnings.filterwarnings('ignore')

# Configure matplotlib for inline display in notebook
%matplotlib inline
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 12
plt.rcParams['figure.dpi'] = 100

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("Reds")

YT_RED = '#FF0000'
YT_RED_DARK = '#CC0000'
YT_BG = '#FFFFFF'
YT_SURFACE = '#F9F9F9'
YT_TEXT = '#0F0F0F'
YT_GRAY = '#606060'
YT_GRID = '#E5E5E5'

def format_number(x):
    if pd.isna(x): return x
    if x >= 1_000_000_000: return f"{{x/1_000_000_000:.1f}}B"
    if x >= 1_000_000: return f"{{x/1_000_000:.1f}}M"
    if x >= 1_000: return f"{{x/1_000:.1f}}K"
    return f"{{x:,.0f}}"

# Load data - using relative path from notebook directory to repo root
# Notebook is in Notebook_EN/weekly/ or Notebook_ES/weekly/, database is in charts_archive/3_enrich-chart-data/
db_path = "../../charts_archive/3_enrich-chart-data/{db_filename}"
print(f"Loading data from: {{db_path}}")
conn = sqlite3.connect(db_path)

cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables found: {{[t[0] for t in tables]}}")

if not tables:
    raise ValueError(f"No tables found in database: {{db_path}}")

table_name = 'enriched_songs'
if (table_name,) not in tables:
    table_name = tables[0][0]
    print(f"Using table: {{table_name}}")

df = pd.read_sql_query(f"SELECT * FROM {{table_name}}", conn)
conn.close()

df['upload_date'] = pd.to_datetime(df['upload_date'], errors='coerce')
df['upload_quarter'] = df['upload_date'].dt.quarter
df['engagement'] = np.where(df['views'] > 0, (df['likes'] / df['views'] * 100).round(2), 0.0)

print(f"Loaded {{len(df)}} songs, {{df.shape[1]}} columns")
df.head()
"""))

    # Data Preview
    nb.cells.append(new_markdown_cell(titles['preview']))
    nb.cells.append(new_code_cell("df.head()"))

    # General Statistics
    nb.cells.append(new_markdown_cell(titles['general_stats']))
    nb.cells.append(new_code_cell(f"""
stats = pd.DataFrame({{
    'Total Songs': [{len(df)}],
    'Unique Countries': [{df['artist_country'].nunique()}],
    'Unique Genres': [{df['macro_genre'].nunique()}],
    'Total Views': [{int(df['views'].sum())}],
    'Total Likes': [{int(df['likes'].sum())}],
    'Total Comments': [{int(df['comment_count'].sum())}],
    'Avg Views': [{df['views'].mean():.0f}],
    'Avg Likes': [{df['likes'].mean():.0f}]
}})

print("GENERAL STATISTICS")
display(stats)
"""))

    if insights.get('general_stats'):
        nb.cells.append(new_markdown_cell(insights['general_stats']))

    # Country Analysis - Continent Distribution
    nb.cells.append(new_markdown_cell(titles['country_analysis']))
    nb.cells.append(new_markdown_cell(titles['continent']))
    nb.cells.append(new_code_cell("""
continents = {
    'North America': ['United States', 'Mexico', 'Canada', 'Puerto Rico'],
    'South America': ['Brazil', 'Argentina', 'Colombia', 'Chile', 'Peru', 'Venezuela'],
    'Europe': ['United Kingdom', 'Sweden', 'Germany', 'France', 'Spain', 'Italy', 'Netherlands', 'Turkey'],
    'Asia': ['India', 'South Korea', 'Japan', 'China', 'Indonesia', 'Pakistan', 'Philippines', 'Thailand', 'Vietnam'],
    'Africa': ['Nigeria', 'South Africa', 'Kenya', 'Ghana'],
    'Oceania': ['Australia', 'New Zealand'],
    'Middle East': ['Israel', 'UAE', 'Saudi Arabia']
}

def get_continent(country):
    for continent, countries in continents.items():
        if country in countries:
            return continent
    return 'Other'

df['continent'] = df['artist_country'].apply(get_continent)

continent_stats = df.groupby('continent').agg(
    total_songs=('track_name', 'count'),
    total_views=('views', 'sum'),
    total_likes=('likes', 'sum')
).reset_index().sort_values('total_songs', ascending=False)

print("\\nCONTINENT STATISTICS:")
display(continent_stats)

fig, ax = plt.subplots(figsize=(10, 7))
fig.patch.set_facecolor(YT_BG)
colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(continent_stats)))

wedges, texts, autotexts = ax.pie(
    continent_stats['total_songs'],
    labels=continent_stats['continent'],
    autopct='%1.1f%%',
    colors=colors,
    startangle=90,
    wedgeprops={'edgecolor': 'white', 'linewidth': 2}
)

for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontweight('bold')
    autotext.set_fontsize(10)

ax.set_title('Song Distribution by Continent', fontweight='bold', color=YT_TEXT, fontsize=14, pad=20)
plt.tight_layout()
plt.show()
"""))

    # Top Countries by Song Count (barh) - edgecolor removed
    nb.cells.append(new_markdown_cell(titles['top_countries_songs']))
    nb.cells.append(new_code_cell("""
top_countries = (df
    .groupby('artist_country')
    .agg(total_songs=('rank', 'count'), total_views=('views', 'sum'))
    .reset_index()
    .sort_values('total_songs', ascending=False)
    .head(10))

total = top_countries['total_songs'].sum()
top_countries['percentage'] = (top_countries['total_songs'] / total * 100).round(2)

print("\\nTOP 10 COUNTRIES BY SONG COUNT")
display(top_countries)

fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor(YT_BG)
ax.set_facecolor(YT_SURFACE)

colors = plt.cm.Reds(np.linspace(0.4, 1, len(top_countries)))[::-1]

bars = ax.barh(top_countries['artist_country'], top_countries['total_songs'],
               color=colors, edgecolor='none', height=0.65, alpha=0.9)

ax.set_xlabel('Number of Songs', fontsize=11, color=YT_GRAY)
ax.set_title('Top 10 Countries by Song Count', fontweight='bold', color=YT_TEXT, fontsize=14)
ax.invert_yaxis()
ax.spines[['top', 'right', 'left']].set_visible(False)
ax.spines['bottom'].set_color(YT_GRID)
ax.xaxis.grid(True, color=YT_GRID, linestyle='--', alpha=0.7)

for bar, val in zip(bars, top_countries['total_songs']):
    ax.text(val + 0.5, bar.get_y() + bar.get_height()/2, f'{int(val)}',
            va='center', fontsize=10, fontweight='bold', color=YT_TEXT)

plt.tight_layout()
plt.show()
"""))

    if insights.get('top_countries'):
        nb.cells.append(new_markdown_cell(insights['top_countries']))

    # Top Countries by Likes (barh) - edgecolor removed
    nb.cells.append(new_markdown_cell(titles['top_countries_likes']))
    nb.cells.append(new_code_cell("""
top_likes = (df
    .groupby('artist_country')['likes']
    .sum()
    .reset_index()
    .rename(columns={'likes': 'total_likes'})
    .sort_values('total_likes', ascending=False)
    .head(10))

def format_likes(x):
    if x >= 1_000_000: return f"{x/1_000_000:.1f}M"
    if x >= 1_000: return f"{x/1_000:.1f}K"
    return str(x)

top_likes['total_likes_fmt'] = top_likes['total_likes'].apply(format_likes)

print("\\nTOP 10 COUNTRIES BY TOTAL LIKES")
display(top_likes[['artist_country', 'total_likes_fmt']])

fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor(YT_BG)
ax.set_facecolor(YT_SURFACE)

colors = plt.cm.Reds(np.linspace(0.4, 1, len(top_likes)))[::-1]

bars = ax.barh(top_likes['artist_country'], top_likes['total_likes'],
               color=colors, edgecolor='none', height=0.65, alpha=0.9)

ax.set_xlabel('Total Likes', fontsize=11, color=YT_GRAY)
ax.set_title('Top 10 Countries by Total Likes', fontweight='bold', color=YT_TEXT, fontsize=14)
ax.invert_yaxis()
ax.spines[['top', 'right', 'left']].set_visible(False)
ax.spines['bottom'].set_color(YT_GRID)
ax.xaxis.grid(True, color=YT_GRID, linestyle='--', alpha=0.7)

for bar, val in zip(bars, top_likes['total_likes']):
    ax.text(val + 0.5e6, bar.get_y() + bar.get_height()/2,
            format_likes(val), va='center', fontsize=10, fontweight='bold', color=YT_TEXT)

plt.tight_layout()
plt.show()
"""))

    if insights.get('top_likes'):
        nb.cells.append(new_markdown_cell(insights['top_likes']))

    # Top 5 Songs by Country
    nb.cells.append(new_markdown_cell(titles['top_songs_country']))
    nb.cells.append(new_code_cell("""
print("\\n" + "="*80)
print("TOP 5 SONGS BY COUNTRY (Views & Likes)")
print("="*80)

top_countries_list = df['artist_country'].value_counts().head(10).index.tolist()

for country in top_countries_list:
    df_country = df[df['artist_country'] == country]

    print(f"\\n{country}:")

    top_views = df_country.nlargest(5, 'views')[['track_name', 'artist_names', 'views', 'likes', 'engagement']].copy()
    top_views['views'] = top_views['views'].apply(format_number)
    top_views['likes'] = top_views['likes'].apply(format_number)

    print("   Top 5 by views:")
    for _, row in top_views.iterrows():
        print(f"      - {row['track_name']} - {row['artist_names']}: {row['views']} views | {row['likes']} likes | {row['engagement']:.1f}% engagement")

    top_likes_country = df_country.nlargest(5, 'likes')[['track_name', 'artist_names', 'views', 'likes', 'engagement']].copy()
    top_likes_country['views'] = top_likes_country['views'].apply(format_number)
    top_likes_country['likes'] = top_likes_country['likes'].apply(format_number)

    print("   Top 5 by likes:")
    for _, row in top_likes_country.iterrows():
        print(f"      - {row['track_name']} - {row['artist_names']}: {row['likes']} likes | {row['views']} views | {row['engagement']:.1f}% engagement")
"""))

    # Genre Analysis
    nb.cells.append(new_markdown_cell(titles['genre_analysis']))
    nb.cells.append(new_code_cell("""
genre_stats = (df
    .groupby('macro_genre')
    .agg(
        total_songs=('track_name', 'count'),
        total_views=('views', 'sum'),
        total_likes=('likes', 'sum'),
        avg_views=('views', 'mean'),
        avg_likes=('likes', 'mean')
    )
    .reset_index()
    .sort_values('total_songs', ascending=False))

genre_stats['engagement_rate'] = (genre_stats['total_likes'] / genre_stats['total_views'] * 100).round(2)
genre_stats['engagement_rate'] = genre_stats['engagement_rate'].fillna(0)

print("\\nTOP 10 GENRES")
display(genre_stats.head(10)[['macro_genre', 'total_songs', 'engagement_rate']])
"""))

    # Treemap (static matplotlib version using squarify)
    nb.cells.append(new_markdown_cell(titles['treemap']))
    nb.cells.append(new_code_cell("""
# Prepare data for treemap (top 15 genres to avoid overcrowding)
treemap_data = genre_stats.head(15).copy()
sizes = treemap_data['total_songs'].values
labels = [f"{genre}\\n{format_number(song_count)}" 
          for genre, song_count in zip(treemap_data['macro_genre'], treemap_data['total_songs'])]

# Generate colors from Reds colormap
colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(sizes)))

fig, ax = plt.subplots(figsize=(14, 8))
fig.patch.set_facecolor(YT_BG)
ax.set_facecolor(YT_BG)

squarify.plot(sizes=sizes, label=labels, alpha=0.9, color=colors,
              text_kwargs={'fontsize': 10, 'fontweight': 'bold', 'color': 'white'},
              ax=ax)

ax.set_title('Genre Distribution by Song Count', fontweight='bold', color=YT_TEXT, fontsize=14, pad=20)
ax.axis('off')

plt.tight_layout()
plt.show()
"""))

    # Engagement by Genre (barh) - edgecolor removed
    nb.cells.append(new_markdown_cell(titles['engagement_genre']))
    nb.cells.append(new_code_cell("""
print("="*80)
print("ENGAGEMENT ANALYSIS BY GENRE")
print("="*80)

engagement_chart = genre_stats.sort_values('engagement_rate', ascending=False).head(10)

fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor(YT_BG)
ax.set_facecolor(YT_SURFACE)

colors = plt.cm.Reds(np.linspace(0.4, 1, len(engagement_chart)))[::-1]

bars = ax.barh(engagement_chart['macro_genre'], engagement_chart['engagement_rate'],
               color=colors, edgecolor='none', height=0.65, alpha=0.9)

ax.set_xlabel('Engagement Rate (%)', fontsize=11, color=YT_GRAY)
ax.set_title('Top 10 Genres by Engagement Rate (Likes/Views)',
             fontweight='bold', color=YT_TEXT, fontsize=14)
ax.invert_yaxis()
ax.spines[['top', 'right', 'left']].set_visible(False)
ax.spines['bottom'].set_color(YT_GRID)
ax.xaxis.grid(True, color=YT_GRID, linestyle='--', alpha=0.7)

for bar, val in zip(bars, engagement_chart['engagement_rate']):
    ax.text(val + 0.2, bar.get_y() + bar.get_height()/2, f'{val:.1f}%',
            va='center', fontsize=10, fontweight='bold', color=YT_TEXT)

avg_engagement = genre_stats['engagement_rate'].mean()
ax.axvline(x=avg_engagement, color=YT_RED, linestyle='--', linewidth=2, alpha=0.9)
ax.text(avg_engagement + 0.1, len(engagement_chart) - 0.5,
        f'Average: {avg_engagement:.1f}%',
        fontsize=9, color=YT_RED, fontweight='bold')

plt.tight_layout()
plt.show()

print(f"\\nENGAGEMENT STATISTICS")
print(f"   Average: {avg_engagement:.2f}%")
print(f"   Median: {genre_stats['engagement_rate'].median():.2f}%")
print(f"   Max: {genre_stats['engagement_rate'].max():.2f}% ({genre_stats.loc[genre_stats['engagement_rate'].idxmax(), 'macro_genre']})")
print(f"   Min: {genre_stats['engagement_rate'].min():.2f}% ({genre_stats.loc[genre_stats['engagement_rate'].idxmin(), 'macro_genre']})")
"""))

    if insights.get('genre_engagement'):
        nb.cells.append(new_markdown_cell(insights['genre_engagement']))

    # Country-Genre Heatmap (using matplotlib/seaborn instead of plotly)
    nb.cells.append(new_markdown_cell(titles['country_genre_heatmap']))
    nb.cells.append(new_code_cell("""
df_analysis = df[~df['artist_country'].isin(['Multi-country', 'Unknown'])]

if df_analysis.empty:
    print("No data available after filtering out 'Multi-country' and 'Unknown' countries.")
else:
    matrix = pd.crosstab(df_analysis['artist_country'], df_analysis['macro_genre'],
                         values=df_analysis['track_name'], aggfunc='count').fillna(0)

    top_countries = matrix.sum(axis=1).sort_values(ascending=False).head(12).index
    top_genres = genre_stats.nlargest(10, 'total_songs')['macro_genre'].tolist()
    top_genres = [g for g in top_genres if g in matrix.columns]

    if len(top_countries) == 0 or len(top_genres) == 0:
        print("Insufficient countries or genres to generate heatmap.")
    else:
        matrix_heatmap = matrix.loc[top_countries, top_genres]

        print("="*80)
        print("COUNTRY vs GENRE MATRIX (Top 12 countries × Top 10 genres)")
        print("="*80)
        display(matrix_heatmap)

        # Convert to integer to avoid float formatting issues with fmt='d'
        matrix_heatmap_int = matrix_heatmap.astype(int)
        
        plt.figure(figsize=(12, 8))
        sns.heatmap(matrix_heatmap_int, annot=True, fmt='d', cmap='Reds',
                    xticklabels=True, yticklabels=True, linewidths=0.5, linecolor='white')
        plt.title('Country vs Genre Distribution', fontsize=14, fontweight='bold')
        plt.xlabel('Genre', fontsize=12)
        plt.ylabel('Country', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()
"""))

    # Song Metrics
    nb.cells.append(new_markdown_cell(titles['song_metrics']))
    nb.cells.append(new_markdown_cell(titles['top_views']))
    nb.cells.append(new_code_cell("""
print("="*80)
print("TOP 10 SONGS BY VIEWS")
print("="*80)
display(df.nlargest(10, 'views')[['rank', 'track_name', 'artist_names', 'views', 'artist_country']])
"""))
    if insights.get('top_songs_views'):
        nb.cells.append(new_markdown_cell(insights['top_songs_views']))

    nb.cells.append(new_markdown_cell(titles['top_likes']))
    nb.cells.append(new_code_cell("""
print("="*80)
print("TOP 10 SONGS BY LIKES")
print("="*80)
display(df.nlargest(10, 'likes')[['rank', 'track_name', 'artist_names', 'likes', 'artist_country']])
"""))
    if insights.get('top_songs_likes'):
        nb.cells.append(new_markdown_cell(insights['top_songs_likes']))

    nb.cells.append(new_markdown_cell(titles['top_engagement']))
    nb.cells.append(new_code_cell("""
print("="*80)
print("TOP 10 SONGS BY ENGAGEMENT (Likes/Views %)")
print("="*80)
display(df.nlargest(10, 'engagement')[['rank', 'track_name', 'artist_names', 'engagement', 'artist_country']])
"""))
    if insights.get('top_songs_engagement'):
        nb.cells.append(new_markdown_cell(insights['top_songs_engagement']))

    # Video Metrics
    nb.cells.append(new_markdown_cell(titles['video_metrics']))
    nb.cells.append(new_code_cell("""
video_stats = {
    'Official Videos': df['is_official_video'].sum(),
    'Lyric Videos': df['is_lyric_video'].sum(),
    'Live Performances': df['is_live_performance'].sum(),
    'Collaborations': df['is_collaboration'].sum()
}

print("="*80)
print("VIDEO METRICS")
print("="*80)
for k, v in video_stats.items():
    print(f"   {k}: {v} ({v/len(df)*100:.1f}%)")
"""))

    # Views by Video Type
    nb.cells.append(new_markdown_cell(titles['views_by_type']))
    nb.cells.append(new_code_cell("""
df_video = df.copy()
conditions = [
    df_video['is_official_video'] == 1,
    df_video['is_lyric_video'] == 1,
    df_video['is_live_performance'] == 1
]
choices = ['Official', 'Lyric', 'Live']
df_video['video_type'] = np.select(conditions, choices, default='Other')

views_stats = df_video.groupby('video_type').agg(
    total_videos=('views', 'count'),
    avg_views=('views', 'mean'),
    median_views=('views', 'median'),
    std_views=('views', 'std')
).round(2).reset_index()

table_views = views_stats.copy()
table_views['total_videos'] = table_views['total_videos'].astype(int)
table_views['avg_views'] = table_views['avg_views'].apply(lambda x: f"{x:,.0f}")
table_views['median_views'] = table_views['median_views'].apply(lambda x: f"{x:,.0f}")
table_views['std_views'] = table_views['std_views'].apply(lambda x: f"{x:,.0f}")
table_views.columns = ['Video Type', 'Total Videos', 'Avg Views', 'Median Views', 'Std Dev']

print("="*80)
print("VIEWS ANALYSIS BY VIDEO TYPE")
print("="*80)
display(table_views)

fig, ax = plt.subplots(figsize=(8, 6))
fig.patch.set_facecolor('#F9F9F9')
ax.set_facecolor('#F9F9F9')
sns.barplot(data=df_video, x='video_type', y='views', ax=ax, color='#FC4B4C', errorbar='sd')
ax.set_title('Average Views by Video Type', fontweight='bold', fontsize=14)
ax.set_ylabel('Average Views', fontsize=12)
ax.set_xlabel('Video Type', fontsize=12)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
"""))
    if insights.get('video_metrics'):
        nb.cells.append(new_markdown_cell(insights['video_metrics']))

    # Engagement by Video Type
    nb.cells.append(new_markdown_cell(titles['engagement_by_type']))
    nb.cells.append(new_code_cell("""
# Compute engagement rates by video type
engagement_by_type = df_video.groupby('video_type')['engagement'].mean().reset_index()
engagement_by_type.columns = ['Video Type', 'Avg Engagement (%)']
display(engagement_by_type)

fig, ax = plt.subplots(figsize=(8, 6))
fig.patch.set_facecolor('#F9F9F9')
ax.set_facecolor('#F9F9F9')
sns.barplot(data=df_video, x='video_type', y='engagement', ax=ax, color='#FC4B4C', errorbar='sd')
ax.set_title('Average Engagement by Video Type', fontweight='bold', fontsize=14)
ax.set_ylabel('Engagement (%)', fontsize=12)
ax.set_xlabel('Video Type', fontsize=12)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
"""))
    if insights.get('engagement_by_type'):
        nb.cells.append(new_markdown_cell(insights['engagement_by_type']))

    # Duration Analysis
    nb.cells.append(new_markdown_cell(titles['duration_analysis']))
    nb.cells.append(new_code_cell("""
duration_minutes = df['duration_s'] / 60

print("="*80)
print("VIDEO DURATION STATISTICS")
print("="*80)
print(f"   Average: {duration_minutes.mean():.1f} minutes")
print(f"   Minimum: {df['duration_s'].min()} seconds")
print(f"   Maximum: {df['duration_s'].max()} seconds")
print(f"   Median: {df['duration_s'].median()} seconds")

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.patch.set_facecolor(YT_BG)

ax1 = axes[0]
ax1.set_facecolor(YT_SURFACE)
n, bins, patches = ax1.hist(duration_minutes, bins=15, edgecolor='white', alpha=0.7, density=True)

for patch in patches:
    patch.set_facecolor('#FE1B1F' if patch.get_height() > 0.2 else '#D8A7A7')

kde = gaussian_kde(duration_minutes)
x = np.linspace(duration_minutes.min(), duration_minutes.max(), 100)
ax1.plot(x, kde(x), color=YT_RED_DARK, linewidth=2.5, label='Density', alpha=0.9)

ax1.axvline(duration_minutes.mean(), color='#220F23', linestyle='--', linewidth=1.5, label=f'Mean: {duration_minutes.mean():.1f} min')
ax1.axvline(duration_minutes.median(), color='#821638', linestyle='--', linewidth=1.5, label=f'Median: {duration_minutes.median():.1f} min')

ax1.set_xlabel('Duration (minutes)', fontsize=10, color=YT_GRAY)
ax1.set_ylabel('Density', fontsize=10, color=YT_GRAY)
ax1.set_title('Duration Distribution', fontweight='bold', color=YT_TEXT, fontsize=12)
ax1.legend(loc='upper right', fontsize=9, facecolor=YT_SURFACE)
ax1.spines[['top', 'right']].set_visible(False)
ax1.grid(True, color=YT_GRID, linestyle='--', alpha=0.5)

ax2 = axes[1]
ax2.set_facecolor(YT_SURFACE)
bp = ax2.boxplot(duration_minutes, vert=False, patch_artist=True, widths=0.6,
                 boxprops=dict(facecolor=YT_RED, color=YT_RED_DARK, alpha=0.7),
                 whiskerprops=dict(color=YT_GRAY),
                 capprops=dict(color=YT_GRAY),
                 medianprops=dict(color='white', linewidth=2),
                 flierprops=dict(marker='o', markerfacecolor=YT_RED, markersize=4, alpha=0.5))
ax2.set_yticks([1])
ax2.set_yticklabels(['Duration'], fontsize=10)
ax2.set_xlabel('Duration (minutes)', fontsize=10, color=YT_GRAY)
ax2.set_title('Key Statistics', fontweight='bold', color=YT_TEXT, fontsize=12)
ax2.spines[['top', 'right']].set_visible(False)
ax2.grid(True, color=YT_GRID, linestyle='--', alpha=0.5, axis='x')

plt.tight_layout()
plt.show()

print(f"\\n DURATION STATISTICS:")
print("-"*80)
print(f"   Mean: {duration_minutes.mean():.1f} min | Median: {duration_minutes.median():.1f} min")
print(f"   Min: {duration_minutes.min():.1f} min | Max: {duration_minutes.max():.1f} min")
print(f"   Q1: {duration_minutes.quantile(0.25):.1f} min | Q3: {duration_minutes.quantile(0.75):.1f} min")
"""))
    if insights.get('duration'):
        nb.cells.append(new_markdown_cell(insights['duration']))

    # Channel Type Distribution (barh) - edgecolor removed
    nb.cells.append(new_markdown_cell(titles['channel_type']))
    nb.cells.append(new_code_cell("""
channel_counts = df['channel_type'].value_counts()

print("\\n" + "="*60)
print("CHANNEL TYPE DISTRIBUTION")
print("="*60)

for ch, count in channel_counts.items():
    print(f"   - {ch}: {count} songs ({count/len(df)*100:.1f}%)")

fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor(YT_BG)
ax.set_facecolor(YT_SURFACE)

colors = plt.cm.Reds(np.linspace(0.4, 0.9, len(channel_counts)))[::-1]

bars = ax.barh(channel_counts.index, channel_counts.values,
               color=colors, edgecolor='none', height=0.6, alpha=0.9)

ax.set_xlabel('Number of Songs', fontsize=11, color=YT_GRAY)
ax.set_title('Channel Type Distribution', fontweight='bold', color=YT_TEXT, fontsize=14)
ax.spines[['top', 'right', 'left']].set_visible(False)
ax.spines['bottom'].set_color(YT_GRID)
ax.xaxis.grid(True, color=YT_GRID, linestyle='--', alpha=0.7)

for bar, val in zip(bars, channel_counts.values):
    ax.text(val + 0.3, bar.get_y() + bar.get_height()/2,
            f'{val} ({val/len(df)*100:.1f}%)',
            va='center', fontsize=10, fontweight='bold', color=YT_TEXT)

plt.tight_layout()
plt.show()
"""))

    # Temporal Analysis
    nb.cells.append(new_markdown_cell(titles['temporal_analysis']))
    nb.cells.append(new_markdown_cell(titles['views_evolution']))
    nb.cells.append(new_code_cell("""
bg_color = '#F9F9F9'
# Updated color palette for better distinction
genre_palette = ['#751924', '#FF0000', '#282828', '#FFB347', '#FF6B6B']

top5_genres = genre_stats.nlargest(5, 'total_songs')['macro_genre'].tolist()
df_temporal = df[df['macro_genre'].isin(top5_genres)].copy()

temporal_views = df_temporal.groupby(['upload_quarter', 'macro_genre'])['views'].sum().reset_index()
temporal_engagement = df_temporal.groupby(['upload_quarter', 'macro_genre'])['engagement'].mean().reset_index()

fig1, ax1 = plt.subplots(figsize=(12, 6), facecolor=bg_color)
ax1.set_facecolor(bg_color)

sns.lineplot(data=temporal_views, x='upload_quarter', y='views', hue='macro_genre',
             marker='o', palette=genre_palette, linewidth=2.5, ax=ax1)

ax1.set_title('Views Evolution by Quarter (Top 5 Genres)', fontweight='bold', color='#282828', fontsize=14)
ax1.set_xlabel('Release Quarter', color='#282828', fontsize=12)
ax1.set_ylabel('Total Views', color='#282828', fontsize=12)
ax1.tick_params(colors='#282828', labelsize=10)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_color('#4A4A4A')
ax1.spines['bottom'].set_color('#4A4A4A')
ax1.grid(True, linestyle='--', alpha=0.3, color='#AAAAAA')

legend1 = ax1.get_legend()
if legend1:
    legend1.get_frame().set_facecolor(bg_color)
    legend1.get_frame().set_edgecolor('#E5E5E5')
    for text in legend1.get_texts():
        text.set_color('#282828')

plt.tight_layout()
plt.show()
"""))

    nb.cells.append(new_markdown_cell(titles['engagement_evolution']))
    nb.cells.append(new_code_cell("""
fig2, ax2 = plt.subplots(figsize=(12, 6), facecolor=bg_color)
ax2.set_facecolor(bg_color)

sns.lineplot(data=temporal_engagement, x='upload_quarter', y='engagement', hue='macro_genre',
             marker='o', palette=genre_palette, linewidth=2.5, ax=ax2)

ax2.set_title('Engagement Evolution by Quarter (Top 5 Genres)', fontweight='bold', color='#282828', fontsize=14)
ax2.set_xlabel('Release Quarter', color='#282828', fontsize=12)
ax2.set_ylabel('Engagement (%)', color='#282828', fontsize=12)
ax2.tick_params(colors='#282828', labelsize=10)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.spines['left'].set_color('#4A4A4A')
ax2.spines['bottom'].set_color('#4A4A4A')
ax2.grid(True, linestyle='--', alpha=0.3, color='#AAAAAA')

legend2 = ax2.get_legend()
if legend2:
    legend2.get_frame().set_facecolor(bg_color)
    legend2.get_frame().set_edgecolor('#E5E5E5')
    for text in legend2.get_texts():
        text.set_color('#282828')

plt.tight_layout()
plt.show()
"""))
    if insights.get('temporal'):
        nb.cells.append(new_markdown_cell(insights['temporal']))

    # Release Distribution by Quarter (vertical bar) - edgecolor removed
    nb.cells.append(new_markdown_cell(titles['release_distribution']))
    nb.cells.append(new_code_cell("""
season_counts = df['upload_quarter'].value_counts().sort_index()

fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor(YT_BG)
ax.set_facecolor(YT_SURFACE)

bars = ax.bar(season_counts.index, season_counts.values, color='#FC4B4C', edgecolor='none')
ax.set_xlabel('Quarter', fontsize=11, color=YT_GRAY)
ax.set_ylabel('Number of Songs', fontsize=11, color=YT_GRAY)
ax.set_title('Release Distribution by Quarter', fontweight='bold', color=YT_TEXT)
ax.spines[['top', 'right']].set_visible(False)
ax.spines['bottom'].set_color(YT_GRID)
ax.spines['left'].set_color(YT_GRID)
ax.grid(True, color=YT_GRID, linestyle='--', alpha=0.5)

for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
            f'{int(height)}', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.show()
"""))

    # Collaborations Analysis
    nb.cells.append(new_markdown_cell(titles['collaborations']))
    nb.cells.append(new_code_cell("""
collab_stats = df.groupby('is_collaboration').agg(
    count=('track_name', 'count'),
    avg_views=('views', 'mean'),
    avg_engagement=('engagement', 'mean')
).reset_index()

collab_stats['is_collaboration'] = collab_stats['is_collaboration'].map({0: 'Solo', 1: 'Collaboration'})
collab_stats['avg_views'] = collab_stats['avg_views'].apply(lambda x: f"{x:,.0f}")
collab_stats['avg_engagement'] = collab_stats['avg_engagement'].round(2).astype(str) + '%'

print("COLLABORATION STATISTICS")
display(collab_stats)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.patch.set_facecolor('#F9F9F9')
axes[0].set_facecolor('#F9F9F9')
axes[1].set_facecolor('#F9F9F9')

# Updated colors: Solo = '#282828' (dark gray), Collaboration = 'red'
sns.scatterplot(data=df, x='artist_count', y='views', hue='is_collaboration',
                palette={0: '#282828', 1: 'red'}, ax=axes[0], alpha=0.6)
axes[0].set_title('Views vs Number of Artists', fontweight='bold')
axes[0].set_xlabel('Number of Artists')
axes[0].set_ylabel('Views')

sns.scatterplot(data=df, x='artist_count', y='engagement', hue='is_collaboration',
                palette={0: '#282828', 1: 'red'}, ax=axes[1], alpha=0.6)
axes[1].set_title('Engagement vs Number of Artists', fontweight='bold')
axes[1].set_xlabel('Number of Artists')
axes[1].set_ylabel('Engagement (%)')

plt.tight_layout()
plt.show()
"""))
    if insights.get('collaborations'):
        nb.cells.append(new_markdown_cell(insights['collaborations']))

    # Executive Summary
    nb.cells.append(new_markdown_cell(titles['executive_summary']))
    if insights.get('executive_summary'):
        nb.cells.append(new_markdown_cell(insights['executive_summary']))
    else:
        nb.cells.append(new_markdown_cell("*No AI summary available. Please configure DEEPSEEK_API_KEY to generate insights.*"))

    # Attribution section (metadata table)
    nb.cells.append(new_markdown_cell(titles['attribution']))
    meta_table = f"""
| | |
|---|---|
| **📁 Data Source** | YouTube Charts enriched with country, genre, and video metrics |
| **📅 Week** | {year}-W{week} |
| **🕐 Generated** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| **👤 Author** | Alfonso Droguett |
| **🔗 LinkedIn** | [adroguetth](https://www.linkedin.com/in/adroguetth/) |
| **🌐 Portfolio** | [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/) |
| **📧 Email** | adroguett.consultor@gmail.com |
| **🤖 AI Analysis** | Powered by DeepSeek API |
"""
    nb.cells.append(new_markdown_cell(meta_table))

    # Write notebook using nbformat
    with open(output_path, 'w', encoding='utf-8') as f:
        nbf.write(nb, f)

    print(f"Notebook generated: {output_path}")


# ============================================================
# Main Execution
# ============================================================

def parse_week(week_str: str) -> Tuple[int, int]:
    """Parse week string into year and week number."""
    match = re.match(r'(\d{4})-W(\d{1,2})', week_str)
    if not match:
        raise ValueError(f"Invalid week format: {week_str}. Expected YYYY-WXX")
    year = int(match.group(1))
    week = int(match.group(2))
    return year, week


def get_data_summaries(df: pd.DataFrame) -> Dict[str, Dict]:
    """Pre-calculate all data summaries needed for AI insights."""
    # Top countries by song count
    top_countries_df = df['artist_country'].value_counts().head(10).reset_index()
    top_countries_df.columns = ['Country', 'Count']
    top_countries_str = "\n".join([f"   - {row['Country']}: {row['Count']} songs"
                                    for _, row in top_countries_df.iterrows()])

    # Top countries by likes
    top_likes_df = df.groupby('artist_country')['likes'].sum().sort_values(ascending=False).head(10)
    top_likes_str = "\n".join([f"   - {country}: {format_number(likes)} likes"
                                for country, likes in top_likes_df.items()])

    # Genre engagement
    genre_engagement = df.groupby('macro_genre')['engagement'].mean().sort_values(ascending=False).head(5)
    genre_engagement_str = "\n".join([f"   - {genre}: {val:.1f}%"
                                       for genre, val in genre_engagement.items()])

    genre_engagement_top = "\n".join([f"   - {genre}: {val:.1f}%"
                                       for genre, val in genre_engagement.head(3).items()])

    # Video type analysis
    official_count = df['is_official_video'].sum()
    lyric_count = df['is_lyric_video'].sum()
    live_count = df['is_live_performance'].sum()

    official_views = df[df['is_official_video'] == 1]['views'].mean() if official_count > 0 else 0
    lyric_views = df[df['is_lyric_video'] == 1]['views'].mean() if lyric_count > 0 else 0
    live_views = df[df['is_live_performance'] == 1]['views'].mean() if live_count > 0 else 0
    
    # Engagement by video type
    official_engagement = df[df['is_official_video'] == 1]['engagement'].mean() if official_count > 0 else 0
    lyric_engagement = df[df['is_lyric_video'] == 1]['engagement'].mean() if lyric_count > 0 else 0
    live_engagement = df[df['is_live_performance'] == 1]['engagement'].mean() if live_count > 0 else 0

    # Best video type
    video_views = {'Official': official_views, 'Lyric': lyric_views, 'Live': live_views}
    best_video_type = max(video_views, key=video_views.get)

    # Collaboration analysis
    solo_count = len(df[df['is_collaboration'] == 0])
    collab_count = len(df[df['is_collaboration'] == 1])
    solo_views = df[df['is_collaboration'] == 0]['views'].mean() if solo_count > 0 else 0
    collab_views = df[df['is_collaboration'] == 1]['views'].mean() if collab_count > 0 else 0
    solo_engagement = df[df['is_collaboration'] == 0]['engagement'].mean() if solo_count > 0 else 0
    collab_engagement = df[df['is_collaboration'] == 1]['engagement'].mean() if collab_count > 0 else 0

    if collab_views > solo_views and solo_count > 0:
        collab_impact = f"Collaborations have {((collab_views/solo_views - 1)*100):.0f}% more views than solo songs"
    elif solo_count > 0:
        collab_impact = f"Solo songs have {((solo_views/collab_views - 1)*100):.0f}% more views than collaborations"
    else:
        collab_impact = "No collaboration data available"

    # Duration stats
    avg_duration = df['duration_s'].mean() / 60
    median_duration = df['duration_s'].median() / 60
    min_duration = df['duration_s'].min() / 60
    max_duration = df['duration_s'].max() / 60

    # Quarterly stats
    quarterly_views = df.groupby('upload_quarter')['views'].sum().to_dict()
    quarterly_engagement = df.groupby('upload_quarter')['engagement'].mean().to_dict()

    # Top songs lists for insights
    top_views_songs = df.nlargest(10, 'views')[['track_name', 'artist_names']].to_string(index=False)
    top_likes_songs = df.nlargest(10, 'likes')[['track_name', 'artist_names']].to_string(index=False)
    top_engagement_songs = df.nlargest(10, 'engagement')[['track_name', 'artist_names']].to_string(index=False)

    return {
        "introduction": {
            "total_songs": len(df),
            "unique_countries": df['artist_country'].nunique(),
            "unique_genres": df['macro_genre'].nunique(),
            "total_views": int(df['views'].sum()),
            "total_likes": int(df['likes'].sum()),
            "avg_views": float(df['views'].mean()),
            "avg_likes": float(df['likes'].mean())
        },
        "general_stats": {
            "total_songs": len(df),
            "unique_countries": df['artist_country'].nunique(),
            "unique_genres": df['macro_genre'].nunique(),
            "total_views": int(df['views'].sum()),
            "total_likes": int(df['likes'].sum()),
            "avg_views": float(df['views'].mean()),
            "avg_likes": float(df['likes'].mean())
        },
        "top_countries": {"top_countries": top_countries_str},
        "top_likes": {"top_likes": top_likes_str},
        "genre_engagement": {"genre_engagement": genre_engagement_str},
        "video_metrics": {
            "official_pct": (official_count / len(df)) * 100 if len(df) > 0 else 0,
            "official_views": float(official_views),
            "lyric_pct": (lyric_count / len(df)) * 100 if len(df) > 0 else 0,
            "lyric_views": float(lyric_views),
            "live_pct": (live_count / len(df)) * 100 if len(df) > 0 else 0,
            "live_views": float(live_views),
            "avg_engagement": float(df['engagement'].mean())
        },
        "engagement_by_type": {
            "official_engagement": float(official_engagement),
            "lyric_engagement": float(lyric_engagement),
            "live_engagement": float(live_engagement)
        },
        "top_songs_views": {"top_songs_views_list": top_views_songs},
        "top_songs_likes": {"top_songs_likes_list": top_likes_songs},
        "top_songs_engagement": {"top_songs_engagement_list": top_engagement_songs},
        "temporal": {
            "quarterly_views": quarterly_views,
            "quarterly_engagement": quarterly_engagement
        },
        "duration": {
            "avg_duration": avg_duration,
            "median_duration": median_duration,
            "min_duration": min_duration,
            "max_duration": max_duration
        },
        "collaborations": {
            "solo_count": solo_count,
            "solo_views": float(solo_views),
            "solo_engagement": float(solo_engagement),
            "collab_count": collab_count,
            "collab_views": float(collab_views),
            "collab_engagement": float(collab_engagement)
        },
        "executive_summary": {
            "total_songs": len(df),
            "unique_countries": df['artist_country'].nunique(),
            "unique_genres": df['macro_genre'].nunique(),
            "total_views": int(df['views'].sum()),
            "total_likes": int(df['likes'].sum()),
            "top_countries": top_countries_str,
            "top_likes": top_likes_str,
            "genre_engagement_top": genre_engagement_top,
            "best_video_type": best_video_type,
            "avg_engagement": float(df['engagement'].mean()),
            "avg_duration": avg_duration,
            "collab_impact": collab_impact
        }
    }


def generate_both_notebooks(df: pd.DataFrame, db_path: Path, year: int, week: int, week_str: str) -> None:
    """Generate both English and Spanish notebooks."""
    db_info = (db_path, year, week)
    
    # Pre-calculate summaries once
    summaries = get_data_summaries(df)
    
    # Define sections to generate
    sections = [
        "introduction",
        "general_stats",
        "top_countries",
        "top_likes",
        "genre_engagement",
        "video_metrics",
        "engagement_by_type",
        "top_songs_views",
        "top_songs_likes",
        "top_songs_engagement",
        "temporal",
        "duration",
        "collaborations",
        "executive_summary"
    ]
    
    # Generate for each language
    for language in ['en', 'es']:
        print(f"\n{'='*60}")
        print(f"Generating {language.upper()} notebook...")
        print(f"{'='*60}")
        
        # Get insights for all sections
        insights = {}
        for section in sections:
            insight = get_ai_insight(section, summaries[section], df, language, week_str)
            insights[section] = insight
        
        # Set output path
        if language == 'en':
            output_path = Config.OUTPUT_EN_PATH / f"youtube_charts_{week_str}.ipynb"
        else:
            output_path = Config.OUTPUT_ES_PATH / f"youtube_charts_{week_str}.ipynb"
        
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate notebook
        generate_notebook(df, db_info, insights, output_path, language)
    
    print(f"\n{'='*60}")
    print("Both notebooks generated successfully!")
    print(f"  EN: {Config.OUTPUT_EN_PATH / f'youtube_charts_{week_str}.ipynb'}")
    print(f"  ES: {Config.OUTPUT_ES_PATH / f'youtube_charts_{week_str}.ipynb'}")
    print(f"{'='*60}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Generate weekly music charts analysis notebooks with AI insights'
    )
    parser.add_argument(
        '--week',
        type=str,
        help='Week to process (format: YYYY-WXX). If not specified, uses latest available'
    )
    parser.add_argument(
        '--language',
        type=str,
        choices=['en', 'es', 'both'],
        default='both',
        help='Language for notebook generation (default: both)'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        help='Path to specific database file. If not specified, auto-detects from week or latest'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Weekly Music Charts Analysis Notebook Generator")
    print("=" * 60)

    # Check API key
    if Config.DEEPSEEK_API_KEY:
        print(f"DeepSeek API key configured (starts with: {Config.DEEPSEEK_API_KEY[:10]}...)")
    else:
        print("DeepSeek API key not set. AI insights will be disabled.")
        print("   Set DEEPSEEK_API_KEY environment variable to enable AI analysis.")

    # Determine database path
    db_path = None
    year = 0
    week = 0
    week_str = ""
    
    if args.db_path:
        db_path = Path(args.db_path)
        if not db_path.exists():
            print(f"Error: Database file not found: {db_path}")
            sys.exit(1)
        match = re.search(r'(\d{4})-W(\d+)', db_path.name)
        if match:
            year = int(match.group(1))
            week = int(match.group(2))
            week_str = f"{year}-W{week:02d}"
        else:
            print(f"Warning: Could not extract week from filename: {db_path.name}")
            week_str = "unknown"
    elif args.week:
        week_str = args.week
        year, week = parse_week(week_str)
        db_path = Config.CHARTS_ARCHIVE_PATH / f"youtube_charts_{week_str}_enriched.db"
        if not db_path.exists():
            print(f"Local database not found: {db_path}")
            print("Attempting to download from GitHub...")
            try:
                db_path, year, week = download_latest_db()
                week_str = f"{year}-W{week:02d}"
            except Exception as e:
                print(f"Failed to download: {e}")
                sys.exit(1)
    else:
        print("\nLooking for latest database...")
        db_path, year, week = get_local_db()
        if db_path is None:
            print("No local database found. Attempting to download from GitHub...")
            try:
                db_path, year, week = download_latest_db()
            except Exception as e:
                print(f"Failed to download: {e}")
                sys.exit(1)
        week_str = f"{year}-W{week:02d}"
    
    print(f"\nUsing database: {db_path}")
    print(f"Week: {week_str}")
    
    # Load data
    print("\nLoading data...")
    df = load_data(db_path)
    print(f"   Loaded {len(df)} songs")
    
    # Generate notebooks based on language argument
    if args.language == 'both':
        generate_both_notebooks(df, db_path, year, week, week_str)
    elif args.language == 'en':
        summaries = get_data_summaries(df)
        sections = [
            "introduction",
            "general_stats", "top_countries", "top_likes", "genre_engagement",
            "video_metrics", "engagement_by_type",
            "top_songs_views", "top_songs_likes", "top_songs_engagement",
            "temporal", "duration", "collaborations", "executive_summary"
        ]
        insights = {}
        for section in sections:
            insights[section] = get_ai_insight(section, summaries[section], df, 'en', week_str)
        
        output_path = Config.OUTPUT_EN_PATH / f"youtube_charts_{week_str}.ipynb"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generate_notebook(df, (db_path, year, week), insights, output_path, 'en')
        print(f"\nEnglish notebook generated: {output_path}")
    else:  # 'es'
        summaries = get_data_summaries(df)
        sections = [
            "introduction",
            "general_stats", "top_countries", "top_likes", "genre_engagement",
            "video_metrics", "engagement_by_type",
            "top_songs_views", "top_songs_likes", "top_songs_engagement",
            "temporal", "duration", "collaborations", "executive_summary"
        ]
        insights = {}
        for section in sections:
            insights[section] = get_ai_insight(section, summaries[section], df, 'es', week_str)
        
        output_path = Config.OUTPUT_ES_PATH / f"youtube_charts_{week_str}.ipynb"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generate_notebook(df, (db_path, year, week), insights, output_path, 'es')
        print(f"\nSpanish notebook generated: {output_path}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
