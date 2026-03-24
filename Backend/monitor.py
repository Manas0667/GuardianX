# =============================================================
# monitor.py — Goldy's Module
# Collects disk, CPU, RAM data and logs to SQLite database
# =============================================================

import psutil
import sqlite3
import os
import logging
from datetime import datetime
from config import DB, WATCH

# ── CREATE ALL DATABASE TABLES ────────────────────────────────
def create_tables():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS activity_log(
        id        INTEGER PRIMARY KEY,
        timestamp TEXT,
        day       TEXT,
        hour      INTEGER,
        cpu       REAL,
        ram       REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS anomaly_log(
        id        INTEGER PRIMARY KEY,
        timestamp TEXT,
        type      TEXT,
        details   TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS backup_history(
        id        INTEGER PRIMARY KEY,
        timestamp TEXT,
        type      TEXT,
        status    TEXT,
        size_mb   REAL,
        location  TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS risk_score_log(
        id        INTEGER PRIMARY KEY,
        timestamp TEXT,
        score     INTEGER,
        decision  TEXT
    )""")
    conn.commit()
    conn.close()
    logging.info("[DB] agent.db tables created successfully")

# ── STORAGE DATA ──────────────────────────────────────────────
def get_storage_data():
    disk = psutil.disk_usage("/")
    io   = psutil.disk_io_counters()
    return {
        "disk_pct"  : round(disk.percent, 1),
        "free_gb"   : round(disk.free / (1024**3), 2),
        "total_gb"  : round(disk.total / (1024**3), 2),
        "write_mb"  : round(io.write_bytes / (1024**2), 1),
        "read_mb"   : round(io.read_bytes  / (1024**2), 1)
    }

# ── SYSTEM DATA ───────────────────────────────────────────────
def get_system_data():
    cpu  = psutil.cpu_percent(interval=1)
    ram  = psutil.virtual_memory()
    hour = datetime.now().hour
    day  = datetime.now().strftime("%A")

    if 1 <= hour <= 5:
        window = "BEST"
    elif hour <= 8 or hour >= 21:
        window = "OK"
    elif 9 <= hour <= 20:
        window = "AVOID"
    else:
        window = "OK"

    return {
        "cpu_pct"     : round(cpu, 1),
        "ram_pct"     : round(ram.percent, 1),
        "ram_free_gb" : round(ram.available / (1024**3), 2),
        "hour"        : hour,
        "day"         : day,
        "time_window" : window
    }

# ── LOG HOURLY ACTIVITY ───────────────────────────────────────
def log_hourly_activity():
    s    = get_system_data()
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT INTO activity_log(timestamp,day,hour,cpu,ram) VALUES(?,?,?,?,?)",
        (datetime.now().isoformat(), s["day"], s["hour"], s["cpu_pct"], s["ram_pct"])
    )
    conn.commit()
    conn.close()
    logging.info(f"[MONITOR] Logged — CPU:{s['cpu_pct']}%  RAM:{s['ram_pct']}%  Hour:{s['hour']}")

# ── DAYS SINCE LAST BACKUP ────────────────────────────────────
def get_days_since_last_backup():
    try:
        conn = sqlite3.connect(DB)
        row  = conn.execute(
            "SELECT timestamp FROM backup_history WHERE status='SUCCESS' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if not row:
            return 999
        last = datetime.fromisoformat(row[0])
        return round((datetime.now() - last).total_seconds() / 86400, 1)
    except:
        return 999

# ── LAST BACKUP STATUS ────────────────────────────────────────
def get_last_backup_status():
    try:
        conn = sqlite3.connect(DB)
        row  = conn.execute(
            "SELECT status FROM backup_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row[0] if row else "NONE"
    except:
        return "NONE"

# ── ACTIVITY PATTERN (7-day CPU heatmap) ─────────────────────
def get_activity_pattern():
    days    = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    pattern = {}
    try:
        conn = sqlite3.connect(DB)
        for day in days:
            rows = conn.execute(
                "SELECT hour, AVG(cpu) FROM activity_log WHERE day=? GROUP BY hour",
                (day,)
            ).fetchall()
            pattern[day] = {r[0]: round(r[1], 1) for r in rows}
        conn.close()
    except:
        pass
    return pattern

# ── FIND BEST BACKUP HOUR ─────────────────────────────────────
def find_best_window():
    day     = datetime.now().strftime("%A")
    pattern = get_activity_pattern()
    today   = pattern.get(day, {})
    if not today:
        return 2
    best_hour = min(today, key=today.get)
    return best_hour

# ── LOG RISK SCORE ────────────────────────────────────────────
def log_risk_score(score, decision):
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT INTO risk_score_log(timestamp,score,decision) VALUES(?,?,?)",
        (datetime.now().isoformat(), score, decision)
    )
    conn.commit()
    conn.close()

# ── TEST ──────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.info("\n=== MONITOR MODULE TEST ===\n")
    create_tables()
    logging.info("\n[STORAGE]", get_storage_data())
    logging.info("[SYSTEM] ", get_system_data())
    logging.info("[DAYS]    Days since last backup:", get_days_since_last_backup())
    logging.info("[WINDOW]  Best backup hour:", find_best_window(), ":00")
    log_hourly_activity()
    logging.info("\n[OK] monitor.py is working correctly!")