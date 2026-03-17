# 🎵 Sistema de Inteligencia de Music Charts
![MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square) ![Automation](https://img.shields.io/badge/Automation-GitHub_Actions-blue?style=flat-square) ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white) ![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white) ![yt-dlp](https://img.shields.io/badge/yt--dlp-FF6F61?style=flat-square&logo=youtube&logoColor=white) ![YouTube API](https://img.shields.io/badge/YouTube_API-FF0000?style=flat-square&logo=youtube&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white)

Un pipeline completamente automatizado de principio a fin que descarga los charts musicales semanales de YouTube, enriquece cada artista con metadatos geográficos y de género, y luego aumenta cada entrada del chart con metadatos profundos de video de YouTube — todo ejecutándose en GitHub Actions, sin intervención manual requerida.

## 📥 Documentación

| Script                     | Propósito                                                    | Docs Inglés                                                  | Docs Español                                                 |
| :------------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| **1_download.py**          | Descarga charts semanales de YouTube (100 canciones) a SQLite | README · [PDF](https://drive.google.com/file/d/11ANLX6PbK_eIzvHLPqL1rm9NY9rOshhD/view?usp=sharing) | README · [PDF](https://drive.google.com/file/d/1SdLvJnxcKxmQYmLlwoYttHr2Izud4iE5/view?usp=sharing) |
| **2_build_artist_db.py**   | Enriquece artistas con país + género vía MusicBrainz, Wikipedia, Wikidata | README · [PDF](https://drive.google.com/file/d/1viUAxZ7k-qeYYbyvZf2OaP20AfLOgKh2/view?usp=drive_link) | README · [PDF](https://drive.google.com/file/d/1WBHBreKeVToTBygSyCuYsHQUr_zSl3BT/view?usp=drive_link) |
| **3_enrich_chart_data.py** | Agrega metadatos de video YouTube a cada entrada (sistema de 3 capas) | README                                                       | README                                                       |

> El README de cada script contiene análisis detallado del código, opciones de configuración y guías de solución de problemas. Este documento cubre el sistema en su conjunto.

## 🗂️ Arquitectura del Sistema

El pipeline procesa datos en tres etapas distintas, cada una construyendo sobre la salida de la anterior:
