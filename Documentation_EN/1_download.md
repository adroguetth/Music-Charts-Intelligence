# 🎵 Script 1: Automated Data Acquisition from YouTube Charts

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Web Scraping](https://img.shields.io/badge/Web-Scraping-orange?style=flat-square) 

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white) [![Playwright](https://custom-icon-badges.demolab.com/badge/Playwright-2EAD33?logo=playwright&logoColor=white&style=flat-square)](https://playwright.dev) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white)

## 📥 Quick Downloads

| Document                     | Format                                                       |
| :--------------------------- | :----------------------------------------------------------- |
| **🇬🇧 English Documentation** | [PDF](https://drive.google.com/file/d/1SdLvJnxcKxmQYmLlwoYttHr2Izud4iE5/view?usp=sharing) |
| **🇪🇸 Spanish Documentation** | [PDF](https://drive.google.com/file/d/11ANLX6PbK_eIzvHLPqL1rm9NY9rOshhD/view?usp=sharing) |

## 📋 General Description

This script is the **first component** of the YouTube Charts intelligence system. It automates the weekly download of YouTube's official Top Songs chart (100 songs) and stores the data in a versioned SQLite database with full historical tracking.

The script uses **Playwright** for headless browser automation with sophisticated anti-detection measures, implements **multiple fallback selectors** to handle YouTube interface changes, and includes a **comprehensive backup system** to prevent data loss.

### Key Features

- **Complete Download**: Retrieves full 100-song CSV with all chart metrics (rank, views, growth, etc.)
- **Anti-Detection**: Custom user agent, JavaScript injection, realistic viewport settings
- **Multiple Selector Strategies**: 4 fallback methods to locate the download button
- **Versioned Storage**: Weekly SQLite databases with ISO week identifiers (YYYY-WXX)
- **Automatic Backup**: Creates backups before any database update
- **Smart Cleanup**: Auto-deletes old backups (7 days) and databases (52 weeks)
- **Fallback Mode**: Generates realistic sample data when scraping fails
- **CI/CD Optimized**: Specifically configured for GitHub Actions with detailed logging

## 📊 Process Flow Diagram

### **Legend**

| Color        | Type          | Description                                           |
| :----------- | :------------ | :---------------------------------------------------- |
| 🔵 Blue       | Input / Start | YouTube Charts webpage, configuration                 |
| 🟠 Orange     | Process       | Browser automation, file operations                   |
| 🔴 Red        | Decision      | Conditional branching (selector works?, file exists?) |
| 🟢 Green      | Storage       | SQLite databases, backups, CSV files                  |
| 🟣 Purple     | External      | GitHub Actions environment                            |
| 🟢 Dark Green | Output        | Final database, success report                        |

### **Diagram 1: Main Flow Overview**







## 🔍 Detailed Analysis of `1_download.py`

### Code Structure

#### **1. Initial Configuration and Directories**

```python
# Main directories
OUTPUT_DIR = Path("data")
ARCHIVE_DIR = Path("charts_archive/1_download-chart")
DATABASE_DIR = ARCHIVE_DIR / "databases"
BACKUP_DIR = ARCHIVE_DIR / "backup"
```

The script organizes data in a hierarchical structure:

| Directory                          | Purpose                          | Retention               |
| :--------------------------------- | :------------------------------- | :---------------------- |
| `data/`                            | Temporary and debugging data     | Ephemeral               |
| `charts_archive/1_download-chart/` | Main archive for downloaded data | Permanent               |
| `databases/`                       | SQLite databases by week         | 52 weeks (configurable) |
| `backup/`                          | Temporary backup copies          | 7 days (configurable)   |

#### **2. Dependency Installation System**

```python
def install_playwright():
    """Complete Playwright verification and installation"""
```

his function performs a **three-level verification**:

| Level | Check                     | Action if Missing                      |
| :---- | :------------------------ | :------------------------------------- |
| 1     | Playwright Python package | `pip install playwright pandas`        |
| 2     | Chromium browser binaries | `playwright install chromium`          |
| 3     | System dependencies       | `playwright install-deps` (Linux only) |

#### **3. Anti-Detection Measures**

The script implements multiple techniques to avoid bot detection:

```python
# Browser arguments
args=[
    '--disable-blink-features=AutomationControlled',  # Hide automation
    '--disable-features=IsolateOrigins',              # Reduce fingerprints
]

# JavaScript injection to mask automation
await context.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
""")

# Realistic user agent and headers
user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
```

#### **4. Multi-Selector Strategy**

The script attempts **4 different methods** to locate the download button:

| Priority | Selector                              | Description                                                  |
| :------- | :------------------------------------ | :----------------------------------------------------------- |
| 1        | `#download-button`                    | Most specific, ID-based selector                             |
| 2        | `paper-icon-button[title="download"]` | Title attribute fallback                                     |
| 3        | `button[aria-label*="download" i]`    | Aria-label pattern (case-insensitive)                        |
| 4        | Iterate all buttons                   | Search for keywords: 'download', 'descarga', 'export', 'csv' |

Each selector includes:

- Visibility check
- Scroll into view if needed
- 15-45 second timeout
- Screenshot capture on failure

#### **5. SQLite Database Management**

python

```
def update_sqlite_database(csv_path: Path, week_id: str):
```



**Update process with safety guarantees:**

| Step | Operation                   | Purpose                                                |
| :--- | :-------------------------- | :----------------------------------------------------- |
| 1    | Read CSV with Pandas        | Load data into DataFrame                               |
| 2    | Add metadata columns        | `download_date`, `week_id`, `timestamp`                |
| 3    | Create backup               | Before any modification                                |
| 4    | Create temporary table      | Avoid data loss during update                          |
| 5    | Delete old records for week | Clean replace (not append)                             |
| 6    | Insert new data             | From temporary table                                   |
| 7    | Create indexes              | Optimize queries: `idx_week`, `idx_rank`, `idx_artist` |

**`chart_data` Table Schema:**

| Column             | Type    | Description                           |
| :----------------- | :------ | :------------------------------------ |
| `Rank`             | INTEGER | Chart position (1-100)                |
| `Previous Rank`    | INTEGER | Position in previous week             |
| `Track Name`       | TEXT    | Song title                            |
| `Artist Names`     | TEXT    | Artist(s), may include collaborations |
| `Periods on Chart` | INTEGER | Weeks on chart                        |
| `Views`            | INTEGER | Total view count                      |
| `Growth`           | TEXT    | Week-over-week growth percentage      |
| `YouTube URL`      | TEXT    | Direct video link                     |
| `download_date`    | TEXT    | Date of download (YYYY-MM-DD)         |
| `download_time`    | TEXT    | Time of download (HH:MM:SS)           |
| `week_id`          | TEXT    | ISO week identifier (YYYY-WXX)        |
| `timestamp`        | TEXT    | Full timestamp (YYYYMMDD_HHMMSS)      |

#### **6. Backup and Cleanup System**

**Backup Creation:**

- Triggered before any database update
- Naming convention: `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db`
- Location: `charts_archive/1_download-chart/backup/`

**Cleanup Policies:**

| Item      | Retention | Configurable      |
| :-------- | :-------- | :---------------- |
| Backups   | 7 days    | `RETENTION_DAYS`  |
| Databases | 52 weeks  | `RETENTION_WEEKS` |

```python
def cleanup_old_backups(days: int = 7):
    """Remove backup files older than specified days."""
    
def cleanup_old_databases(weeks: int = 52):
    """Remove database files older than specified weeks."""
```

#### **7. Fallback Mode**

When scraping is unavailable (network issues, YouTube changes, etc.):

```python
def create_fallback_file():
    """Generates 100 realistic sample records"""
```

**Sample data structure:**

- 100 songs with realistic metrics
- Same CSV format as real YouTube Charts
- Includes all columns expected by downstream scripts
- Enables development and testing without live scraping

#### **8. Reporting and Statistics**

```python
def list_available_databases():
    """Displays statistics of all databases"""
```

Output includes:

- Number of databases
- Records per database
- Date range covered
- File sizes
- Total accumulated records

**Example output:**

```text
📦 Available databases (12):
   • 2025-W01: 100 records, 245.3 KB
     📅 2025-01-06 to 2025-01-06
   • 2025-W02: 100 records, 248.1 KB
     📅 2025-01-13 to 2025-01-13
   ...
   📊 TOTAL: 1,200 records in 12 databases
```

---

## ⚙️ GitHub Actions Workflow Analysis (`1_download-chart.yml`)

### Workflow Structure

```yaml
name: 1- Download YouTube Chart

on:
  schedule:
    # Run every Monday at 12:00 UTC
    - cron: '0 12 * * 1'
  
  # Allow manual workflow execution
  workflow_dispatch:
  
  # Trigger on push to main branch if Python scripts change
  push:
    branches:
      - main
    paths:
      - 'scripts/*.py'

env:
  # Number of days to retain artifacts
  RETENTION_DAYS: 30
```

### Job Steps

#### **1. 📚 Repository Checkout**

```yaml
- name: 📚 Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

#### **2. 🐍 Python 3.12 Setup**

```yaml
- name: 🐍 Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'
```

#### **3. 📦 Install Dependencies**

```yaml
- name: 📦 Install dependencies
  run: |
    pip install -r requirements.txt
    python -m playwright install chromium
    python -m playwright install-deps
```

#### **4. 🚀 Execute Main Script**

```yaml
- name: 🚀 Download YouTube Charts
  run: |
    python scripts/1_download.py
  env:
    GITHUB_ACTIONS: true
```

#### **5. ✅ Verify Results**

```yaml
- name: ✅ Verify results
  run: |
    echo "📂 Directory contents:"
    ls -la charts_archive/1_download-chart/
    echo "📊 Database files:"
    ls -la charts_archive/1_download-chart/databases/
```

#### **6. 📤 Commit and Push**

```yaml
- name: 📤 Commit and push
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add charts_archive/1_download-chart/
    git commit -m "📊 YouTube Chart Update $(date '+%Y-%m-%d') [Automated]" || echo "No changes"
    git push
```

#### **7. 📋 Final Report**

```yaml
- name: 📋 Summary
  run: |
    echo "=========================================="
    echo "✅ YouTube Charts Download Complete!"
    echo "📅 Week: $(python scripts/1_download.py --get-week)"
    echo "=========================================="
```

### Cron Schedule

```cron
'0 12 * * 1'  # Minute 0, Hour 12, Any day, Any month, Monday
```

- **Execution**: Every Monday at 12:00 UTC
- **Equivalent**: 13:00 CET / 08:00 EST
- **Rationale**: YouTube updates charts on Sunday/Monday

---

## 🚀 Installation and Local Setup

### Prerequisites

- Python 3.7 or higher (3.12 recommended)
- Git installed
- Internet access for downloads

### Step-by-Step Installation

#### 1. **Clone the Repository**

```bash
git clone https://github.com/adroguetth/Music-Charts-Intelligence.git
cd Music-Charts-Intelligence
```

#### 2. **Create Virtual Environment (recommended)**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

#### 3. **Install Dependencies**

```bash
pip install -r requirements.txt

# Install Playwright browser
python -m playwright install chromium

# Install system dependencies (Linux only)
python -m playwright install-deps
```

#### 4. **Run Initial Test**

```bash
python scripts/1_download.py
```

### Development Configuration

```bash
# Simulate GitHub Actions environment
export GITHUB_ACTIONS=true

# Enable visual debugging (non-headless mode)
export PWDEBUG=1

# Run with visible browser (edit script: headless=False)
```

---

## 📁 Generated File Structure

```text
charts_archive/
├── 1_download-chart/
│   ├── latest_chart.csv              # Most recent CSV (always updated)
│   ├── databases/
│   │   ├── youtube_charts_2025-W01.db
│   │   ├── youtube_charts_2025-W02.db
│   │   └── ... (one per week, 52 weeks retained)
│   └── backup/
│       ├── backup_2025-W01_20250106_120500.db
│       └── ... (temporary, 7 days retained)
```

### Naming Convention

| Type     | Pattern                              | Example                              |
| :------- | :----------------------------------- | :----------------------------------- |
| Database | `youtube_charts_YYYY-WXX.db`         | `youtube_charts_2025-W14.db`         |
| Backup   | `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db` | `backup_2025-W14_20250406_120500.db` |
| CSV      | `latest_chart.csv`                   | Always overwritten                   |

------

## 🔧 Customization and Configuration

### Adjustable Parameters in Script

```python
# In 1_download.py
RETENTION_DAYS = 7      # Days to keep backups (line ~550)
RETENTION_WEEKS = 52    # Weeks to keep databases (line ~580)
TIMEOUT = 120000        # Browser timeout in milliseconds
```

### Workflow Configuration

```yaml
# In .github/workflows/1_download-chart.yml
env:
  RETENTION_DAYS: 30    # GitHub artifact retention

timeout-minutes: 30     # Job timeout
```

---

## 🐛 Troubleshooting

### Common Issues and Solutions

| Error                                       | Likely Cause              | Solution                                    |
| :------------------------------------------ | :------------------------ | :------------------------------------------ |
| `Playwright browsers not installed`         | Missing Chromium          | `python -m playwright install chromium`     |
| `Timeout waiting for download button`       | YouTube interface changed | Check screenshot artifact, update selectors |
| `CSV has 0 rows`                            | Download failed           | Check network, use fallback mode            |
| `Database locked`                           | Concurrent access         | Wait or restart, check backup exists        |
| `ImportError: No module named 'playwright'` | Missing package           | `pip install playwright`                    |

### Debugging with Screenshots

When the download button cannot be found, the workflow automatically uploads a screenshot as an artifact. Download it from GitHub Actions → Artifacts → `screenshot-failure`.

------

## 📈 Monitoring and Maintenance

### Health Indicators

| Metric         | Expected    | Alert Threshold        |
| :------------- | :---------- | :--------------------- |
| Execution time | 2-5 minutes | >10 minutes            |
| CSV rows       | 100         | <100                   |
| Database size  | 200-300 KB  | <100 KB                |
| Success rate   | >95%        | 2 consecutive failures |

### Logging Levels

| Level      | When                  | Details                  |
| :--------- | :-------------------- | :----------------------- |
| Basic      | Normal execution      | Progress and results     |
| Debug      | `GITHUB_ACTIONS=true` | Full browser logs        |
| Screenshot | On failure            | Page screenshot uploaded |
| Trace      | `PWDEBUG=1`           | Interactive debugging    |

------

## 📄 License and Attribution

- **License**: MIT
- **Author**: Alfonso Droguett
  - 🔗 **LinkedIn:** [Alfonso Droguett](https://www.linkedin.com/in/adroguetth/)
  - 🌐 **Web portfolio:** [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/)
  - 📧 **Email:** adroguett.consultor@gmail.com
- **Dependencies**:
  - Playwright (Apache 2.0)
  - Pandas (BSD 3-Clause)
  - NumPy (BSD)

------

## 🤝 Contribution

1. Report issues with complete logs
2. Update selectors if YouTube changes interface
3. Maintain backward compatibility with database schema
4. Test changes locally before submitting PRs
5. Document new features in this README

------

**⭐ If this project is useful to you, please consider giving it a star on GitHub!**

