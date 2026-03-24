import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DB = os.path.join(BASE_DIR, "Backend", "agent.db")
WATCH = os.path.join(BASE_DIR, "test_files")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
TEMP_DIR = os.path.join(BASE_DIR, "temp")