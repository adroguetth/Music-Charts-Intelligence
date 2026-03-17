# 🎵 Sistema de Inteligencia de Music Charts

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
