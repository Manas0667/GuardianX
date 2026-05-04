# config.py — GuardianX Central Configuration
# MENTOR CORRECTION: Backup DATA not CODE
# BTech CSE | Section 2CC | Group 31

import os
from dotenv import load_dotenv
load_dotenv()

# ═══════════════════════════════════════════════════════════════
# DEPLOYMENT MODE
# 'cloud'   = AWS RDS + S3 + Lambda + CloudWatch
# 'inhouse' = Local PostgreSQL + Local MongoDB
# 'local'   = SQLite + local backups
# ═══════════════════════════════════════════════════════════════
DEPLOYMENT_MODE = os.getenv('DEPLOYMENT_MODE', 'cloud')

# ── AWS Settings ────────────────────────────────────────────────
AWS_REGION      = 'ap-south-1'
S3_BUCKET       = 'backup-agent-2cc'
SNS_TOPIC_ARN   = os.getenv('SNS_TOPIC_ARN', '')
LAMBDA_FUNCTION = "BackupDecisionAgent"

# ── AWS Credentials ─────────────────────────────────────────────
AWS_ACCESS_KEY  = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_KEY  = os.getenv('AWS_SECRET_ACCESS_KEY', '')

# ── RDS PostgreSQL ───────────────────────────────────────────────
RDS_HOST     = os.getenv('RDS_HOST', '')
RDS_PORT     = int(os.getenv('RDS_PORT', 5432))
RDS_DB       = os.getenv('RDS_DB', 'guardianx')
RDS_USER     = os.getenv('RDS_USER', 'guardianadmin')
RDS_PASSWORD = os.getenv('RDS_PASSWORD', '')

# ── Inhouse PostgreSQL ───────────────────────────────────────────
INHOUSE_PG_HOST     = os.getenv('INHOUSE_PG_HOST', 'localhost')
INHOUSE_PG_PORT     = int(os.getenv('INHOUSE_PG_PORT', 5432))
INHOUSE_PG_DB       = os.getenv('INHOUSE_PG_DB', 'guardianx')
INHOUSE_PG_USER     = os.getenv('INHOUSE_PG_USER', 'postgres')
INHOUSE_PG_PASSWORD = os.getenv('INHOUSE_PG_PASSWORD', 'postgres')

# ── MongoDB (inhouse) ────────────────────────────────────────────
MONGO_URI                = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB                 = 'guardianx_events'
MONGO_EVENTS_COLLECTION  = 'watchdog_events'

# ── SQLite ───────────────────────────────────────────────────────
SQLITE_PATH = 'guardianx.db'

# ── Storage ──────────────────────────────────────────────────────
LOCAL_BACKUP_DIR = 'backups/'
LOCAL_LOG_DIR    = 'logs/'

# ═══════════════════════════════════════════════════════════════
# MENTOR CORRECTION — WHAT TO BACKUP
#
# BACKUP:  DATA files — CSV, XLSX, logs, JSON data
#          RDS tables — exported as CSV (activity_log, risk_score_log, etc.)
#          System log files — logs/*.log
#
# DO NOT BACKUP:
#   .py  — Source code is on GitHub, can be regenerated
#   .html/.css/.js — Frontend code, on GitHub
#   .db/.sqlite — Data is already in RDS PostgreSQL
#   .pyc — Compiled Python, auto-generated
#
# REASON:
#   Mentor said "backup jo data hai" — data means user files,
#   database exports, and logs. NOT the code files.
# ═══════════════════════════════════════════════════════════════

BACKUP_EXTENSIONS = {
    # ── DATA FILES (mentor emphasis) ──────────────────────────
    '.csv',   # User data files — MOST IMPORTANT
    '.xlsx',  # Excel data files
    '.xls',   # Excel data files
    # ── DOCUMENTS ──────────────────────────────────────────────
    '.docx',  # Word documents
    '.doc',
    '.pptx',  # Presentations
    '.ppt',
    '.pdf',   # PDF reports
    # ── LOGS (mentor suggestion 5) ─────────────────────────────
    '.log',   # System log files from logs/ folder
    # ── DATA FORMATS ───────────────────────────────────────────
    '.json',  # Config data and exported data (NOT code)
    '.txt',   # Text data files
    # ── CONFIG (user-specific) ─────────────────────────────────
    '.env',   # Environment config (has real credentials)
    '.yaml',
    '.yml',
    '.ini',
    '.cfg',
}

# ── Files to NEVER backup ─────────────────────────────────────
SKIP_EXTENSIONS = {
    # Code — on GitHub, not data
    '.py',    # Python source code — NOT data
    '.js',    # JavaScript code — NOT data
    '.html',  # HTML code — NOT data
    '.css',   # CSS code — NOT data
    '.java',  # Java code — NOT data
    '.sql',   # SQL scripts — NOT data
    # Database files — data already in RDS
    '.db',
    '.sqlite',
    '.sqlite3',
    # Build artifacts
    '.pyc',
    '.pyo',
    '.tmp',
    '.cache',
    '.zip',   # Don't backup zip files (infinite loop)
    '.gz',
}

# ── Directories to always skip ────────────────────────────────
SKIP_DIRS = {
    '__pycache__', '.git', 'venv', '.venv', 'node_modules',
    'backups', '.idea', '.vscode', 'dist', 'build',
    'temp', '.env',
}

# ── WHICH RDS TABLES TO EXPORT AS CSV ────────────────────────
# These will be exported from RDS and included in backup
RDS_EXPORT_TABLES = [
    'activity_log',    # CPU/RAM/Disk readings — ACTUAL DATA
    'risk_score_log',  # Risk scores and decisions — ACTUAL DATA
    'anomaly_log',     # Detected anomalies — ACTUAL DATA
    'backup_history',  # Backup records — ACTUAL DATA
    'system_log',      # Agent logs — ACTUAL DATA
]

# How many rows to export per table (0 = all rows)
RDS_EXPORT_ROWS = {
    'activity_log'   : 10000,  # Last 10,000 readings
    'risk_score_log' : 5000,   # Last 5,000 scores
    'anomaly_log'    : 0,      # All anomalies (usually small)
    'backup_history' : 0,      # All backup records
    'system_log'     : 5000,   # Last 5,000 log entries
}

# ── File importance weights ───────────────────────────────────
# Higher = backed up first = more important
FILE_IMPORTANCE = {
    # HIGHEST — data that cannot be regenerated
    '.csv':  10,   # User data files — most critical
    '.xlsx': 10,   # Excel data — most critical
    '.xls':  10,   # Excel data
    '.log':  9,    # System logs — critical for audit
    # HIGH — documents
    '.docx': 8,
    '.pdf':  8,
    '.pptx': 7,
    '.env':  7,    # Has real credentials
    # MEDIUM
    '.txt':  6,
    '.json': 6,
    '.yaml': 5,
    '.yml':  5,
    '.ini':  4,
    '.cfg':  4,
    # SKIP (code files)
    '.py':   0,    # CODE — not data
    '.js':   0,    # CODE — not data
    '.html': 0,    # CODE — not data
    '.css':  0,    # CODE — not data
    '.db':   0,    # in RDS
    '.sqlite': 0,  # in RDS
    '.pyc':  0,
    '.tmp':  0,
}

HIGH_ENTROPY_WHITELIST = {'.zip', '.gz', '.rar', '.7z', '.pdf', '.mp4', '.xlsx', '.docx'}

# ── Risk score thresholds ─────────────────────────────────────
SCORE_WAIT        = 30
SCORE_INCREMENTAL = 55
SCORE_DIFFERENTIAL= 79
SCORE_FULL        = 80

# ── Anomaly thresholds ────────────────────────────────────────
ENTROPY_THRESHOLD      = 7.0
MASS_DELETE_THRESHOLD  = 20
EXTENSION_MISMATCH_MAX = 10
WRITE_BURST_MULTIPLIER = 5
ODD_HOUR_FILE_COUNT    = 50

# ── Scheduler ─────────────────────────────────────────────────
WORK_HOUR_START    = 9
WORK_HOUR_END      = 20
DEFAULT_BACKUP_HOUR= 2
CPU_POSTPONE_PCT   = 50
RETRY_INTERVAL_MIN = 15

# ── Watch path ────────────────────────────────────────────────
WATCH_PATH = os.getenv('WATCH_PATH', '.')

# ── Derived flags ─────────────────────────────────────────────
USE_RDS             = DEPLOYMENT_MODE == 'cloud'
USE_AWS             = DEPLOYMENT_MODE == 'cloud'
USE_INHOUSE         = DEPLOYMENT_MODE == 'inhouse'
USE_LOCAL           = DEPLOYMENT_MODE == 'local'
USE_MONGO           = DEPLOYMENT_MODE == 'inhouse'
USE_LAMBDA_COMPRESS = DEPLOYMENT_MODE == 'cloud'

print(f"[CONFIG] Mode: {DEPLOYMENT_MODE.upper()} | "
      f"DB: {'RDS' if USE_RDS else 'InhousePG' if USE_INHOUSE else 'SQLite'} | "
      f"Storage: {'S3' if USE_AWS else 'LocalFS'} | "
      f"Backup: DATA files + RDS CSV exports + logs (NOT .py code)")