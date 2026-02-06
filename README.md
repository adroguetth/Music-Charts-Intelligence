# 🎵 YouTube Charts Scraper: Automated Download

## 📥 Quick Downloads
| Document                  | Format                                                       |
| ------------------------- | ------------------------------------------------------------ |
| **🇬🇧 English Documentation** | [PDF](https://drive.google.com/file/d/1ma2nfd4FPaqC7cchyn2uoLFIc-PPaE8H/view?usp=sharing) |
| **🇪🇸 Spanish Documentation** | [PDF](https://drive.google.com/file/d/12RGAmiKzVgVhIRNfDY5stk_Ut-PZuOT2/view?usp=sharing) |

## 📋 General Description

This project consists of an automated system for weekly downloading and storing YouTube's most popular playlists. The `1_descargar.py` script is the first component in a series of tools designed for extracting, processing, and analyzing YouTube Charts data.

### Key Features

- **Complete Download**: Obtains full lists of 100 songs
- **Automation**: Weekly scheduling via GitHub Actions
- **Historical Storage**: SQLite database with weekly versioning
- **Backup System**: Automatic backups before updates
- **Robustness**: Multiple detection strategies and fallback mode
- **CI/CD Optimization**: Specifically configured for GitHub Actions

## 📊 Process Flow Diagram
<center>
<img src="https://drive.google.com/uc?id=1ZZeifoTgmbPdpEBcQot-spyROXOv0SJf" 
     width="40%" 
     alt="Diagrama reducido al 40%">
</center>

## 🔍 Detailed Analysis of `1_descargar.py`

### Code Structure

#### **1. Initial Configuration and Directories**

```python
# Main directories
OUTPUT_DIR = Path("data")
ARCHIVE_DIR = Path("charts_archive")
DATABASE_DIR = ARCHIVE_DIR / "databases"
BACKUP_DIR = ARCHIVE_DIR / "backups"
```

The script organizes data in a hierarchical structure:

- `data/`: Temporary and debugging data
- `charts_archive/`: Main archive
  - `databases/`: SQLite databases by week
  - `backups/`: Temporary backup copies

#### **2. Environment Detection**

```python
IS_GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS') == 'true'
```

The script automatically detects if running in GitHub Actions and adjusts:

- Longer timeouts
- Detailed logs for CI/CD
- Specific recovery strategies

#### **3. Dependency Installation System**

```python
def install_playwright():
    """Complete Playwright verification and installation"""
```

This function performs a three-level verification:

1. Playwright Python package
2. Chromium browser binaries
3. Operating system dependencies

#### **4. Web Scraping Strategies**

The script implements multiple approaches to locate the download button:

```python
# 1. Primary ID selector
download_button = await page.query_selector('#download-button')

# 2. aria-label selector (fallback 1)
download_button = await page.query_selector('[aria-label*="Download"]')

# 3. Text selector (fallback 2)
download_button = await page.query_selector('text=Download')
```

**Anti-detection features:**

- Custom user agent
- JavaScript injection to hide automation
- Realistic view and locale settings
- Custom HTTP headers

#### **5. SQLite Database Management**

```python
def update_sqlite_database(csv_path: Path, week_id: str):
```

**Update process:**

1. Create backup of existing database
2. Read and validate downloaded CSV
3. Add metadata (date, week, timestamp)
4. Use temporary table pattern to avoid data loss
5. Create optimized indexes
6. Update statistics

**`chart_data` table structure:**

| Column             | Type      | Description        |
| ------------------ | --------- | ------------------ |
| Rank               | `INTEGER` | Chart position     |
| Previous Rank      | `INTEGER` | Previous position  |
| Track Name         | `TEXT`    | Song name          |
| Artist Names       | `TEXT`    | Artist(s)          |
| Periods on Chart   | `INTEGER` | Weeks on chart     |
| Views              | `INTEGER` | View count         |
| Growth             | `TEXT`    | Growth percentage  |
| YouTube URL        | `TEXT`    | Video link         |
| download_date      | `TEXT`    | Download date      |
| download_timestamp | `TEXT`    | Complete timestamp |
| week_id            | `TEXT`    | Week identifier    |

#### **6. Backup and Cleanup System**

**Temporary backups:**

- Created before each update
- Naming: `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db`
- Retention: 7 days by default

**Old database cleanup:**

- Configurable retention (52 weeks by default)
- Deletion based on filename date
- Cleanup statistics in logs

#### **7. Fallback Mode**

When scraping is unavailable:

```python
def create_fallback_file():
    """Generates sample data with realistic structure"""
```

- 100 simulated records
- Structure identical to real CSV
- Consistent metadata
- For development and error recovery

#### **8. Reports and Statistics**

```python
def list_available_databases():
    """Displays statistics of all databases"""
```

Includes:

- Total number of databases
- Records per database
- Date range covered
- File sizes
- Total accumulated records

## ⚙️ GitHub Actions Workflow Analysis (`download-chart.yml`)

### **Workflow Structure**

```yaml
name: Download YouTube Chart
on:
  schedule:
    - cron: '0 12 * * 1'  # Monday 12:00 UTC
  workflow_dispatch:       # Manual execution
  push:                    # Trigger on changes
```

### **Jobs and Steps**

#### **Job: `download-and-store`**

- **Operating system**: Ubuntu Latest
- **Timeout**: 30 minutes
- **Permissions**: Repository write access

#### **Detailed Steps:**

1. **📚 Repository Checkout**

```yaml
uses: actions/checkout@v4
with:
  fetch-depth: 0  # Full history for git operations
```

2. **🐍 Python 3.12 Setup**

```yaml
uses: actions/setup-python@v5
with:
  cache: 'pip'  # Dependency caching
```

3. **📦 Dependency Installation**

   - Playwright and Chromium browser

   - Pandas, NumPy for processing

   - System dependencies

4. **📁 Directory Structure Creation**
   - Required directories for files

5. **🚀 Main Script Execution**

```yaml
env:
  GITHUB_ACTIONS: true  # Environment variable for detection
```

6. **✅ Results Verification**
   - Listing of generated files
   - Size statistics
   - Existence validation
7. **📤 Automatic Commit and Push**
   - Automatic user configuration
   - Only commits changes to `charts_archive/`
   - Message with date and week
   - Automatic push to main
8. **📦 Artifact Upload (only on failure)**
   - Data and files for debugging
   - Retention: 7 days
9. **📋 Final Report**
   - Detailed statistics
   - Trigger information
   - File sizes
   - Database count

### **Cron Scheduling**

```cron
'0 12 * * 1'  # Minute 0, Hour 12, Any day of month, Any month, Monday
```

- **Execution**: Every Monday at 12:00 UTC
- **Equivalent**: 13:00 CET (Central European Time)
- **Considerations**: YouTube updates charts on Sundays/Mondays

## 🚀 Installation and Local Setup

### **Prerequisites**

- Python 3.7 or higher
- Git installed
- Internet access for downloads

### **Step-by-Step Installation**

1. **Clone the Repository**

```bash
git clone <repository-url>
cd <project-directory>
```

2. **Create Virtual Environment (recommended)**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install Dependencies**

```bash
pip install -r requirements.txt

# Install Playwright browser
python -m playwright install chromium

# Install system dependencies (Linux)
python -m playwright install-deps
```

4. **Run Initial Test**

```bash
python scripts/1_descargar.py
```

### **Development Configuration**

1. **Optional Environment Variables**

```bash
# To simulate GitHub Actions environment
export GITHUB_ACTIONS=true

# For detailed debugging
export PWDEBUG=1
```

1. **Execution with Visualization**

```python
# Modify in script:
headless=False  # Instead of True
```

## 📁 Generated File Structure

```text
charts_archive/
├── latest_chart.csv              # Most recent CSV (always updated)
├── databases/
│   ├── youtube_charts_2025-W01.db
│   ├── youtube_charts_2025-W02.db
│   └── ... (one per week)
└── backups/
    ├── backup_2025-W01_20250106_120500.db
    └── ... (temporary backups)
```

### **Naming Convention**

- **Databases**: `youtube_charts_YYYY-WXX.db`
- **Backups**: `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db`
- **Weekly CSV**: `latest_chart.csv` (always overwritten)

## 🔧 Customization and Configuration

### **Adjustable Parameters in Script**

```python
# In 1_descargar.py
RETENTION_DAYS = 7      # Days to keep backups
RETENTION_WEEKS = 52    # Weeks to keep databases
TIMEOUT = 120000        # Timeout in milliseconds (2 minutes)
```

### **Workflow Configuration**

```yaml
# In download-chart.yml
env:
  RETENTION_DAYS: 30    # Days for artifacts

timeout-minutes: 30     # Total job timeout
```



## 🐛 Troubleshooting

### **Common Issues and Solutions**

1. **Error: "Playwright browsers not installed"**

```bash
# Manual solution
python -m playwright install chromium
python -m playwright install-deps
```

2. **Error: Timeout in GitHub Actions**
   - Check runner network connection
   - Increase timeout in YML
   - Review Playwright logs
3. **Error: Download button not found**
   - YouTube may have changed interface
   - Check screenshot in artifacts
   - Update selectors in code
4. **Error: Corrupt database**
   - Use automatic backups
   - Verify write permissions
   - Check disk space

### **Logs and Debugging**

**Available log levels:**

1. **Basic information**: Normal execution
2. **GitHub Actions debug**: With `GITHUB_ACTIONS=true`
3. **Error screenshot**: In artifacts when failing
4. **Detailed statistics**: Final report

## 📈 Monitoring and Maintenance

### **Health Indicators**

1. **Database size**: Grows ~100 records/week
2. **CSV size**: ~10-50KB per file
3. **Execution time**: 2-5 minutes normally
4. **Success rate**: Should be >95% under normal conditions

### **Recommended Alerts**

1. **Consecutive failure**: 2 or more consecutive failures
2. **Excessive time**: >10 minutes execution
3. **Incomplete data**: <100 records in CSV
4. **Disk space**: >1GB in `charts_archive/`

## 📄 License and Attribution

- **License**: MIT

- **Author**: Alfonso Droguett
  - 🔗 **LinkedIn:** [Alfonso Droguett](https://www.linkedin.com/in/adroguetth/)
  - 🌐 **Web portfolio:** [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/)
  - 📧 **Email:** [adroguett.consultor@gmail.com](mailto:adroguett.consultor@gmail.com)

- **Dependencies**:
  - Playwright (Apache 2.0)
  - Pandas (BSD 3-Clause)
  - NumPy (BSD)
  

## 🤝 Contribution

1. Report issues with complete logs
2. Propose improvements with use cases
3. Maintain compatibility with existing structure
4. Document changes in README
