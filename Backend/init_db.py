import sqlite3
from config import DB, WATCH

conn = sqlite3.connect(DB)

conn.execute('''CREATE TABLE IF NOT EXISTS activity_log(
timestamp TEXT, day TEXT, hour INTEGER, cpu REAL, ram REAL)''')

conn.execute('''CREATE TABLE IF NOT EXISTS anomaly_log(
timestamp TEXT, type TEXT, details TEXT)''')

conn.execute('''CREATE TABLE IF NOT EXISTS backup_history(
id INTEGER PRIMARY KEY AUTOINCREMENT,
timestamp TEXT, type TEXT, status TEXT, size_mb REAL, location TEXT)''')

conn.execute('''CREATE TABLE IF NOT EXISTS risk_score_log(
id INTEGER PRIMARY KEY AUTOINCREMENT,
timestamp TEXT,
score INTEGER,
decision TEXT
)''')

conn.commit()
conn.close()

print("DB Ready ✅")