# database.py — Unified Database Layer
# Supports: AWS RDS PostgreSQL | Inhouse PostgreSQL | MongoDB (events) | SQLite
# Switches automatically based on DEPLOYMENT_MODE in config.py
# BTech CSE | Section 2CC | Group 31

import time
import sqlite3
import json
import datetime

from config import (
    DEPLOYMENT_MODE, SQLITE_PATH,
    RDS_HOST, RDS_PORT, RDS_DB, RDS_USER, RDS_PASSWORD,
    INHOUSE_PG_HOST, INHOUSE_PG_PORT, INHOUSE_PG_DB,
    INHOUSE_PG_USER, INHOUSE_PG_PASSWORD,
    MONGO_URI, MONGO_DB, MONGO_EVENTS_COLLECTION,
    USE_RDS, USE_INHOUSE, USE_MONGO
)

# ── Try importing drivers ────────────────────────────────────────
try:
    import psycopg2
    import psycopg2.extras
    PG_AVAILABLE = True
except ImportError:
    PG_AVAILABLE = False
    print("[DB] psycopg2 not installed. Run: pip install psycopg2-binary")

try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("[DB] pymongo not installed. Run: pip install pymongo  (needed for inhouse mode)")


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION — auto-selects based on DEPLOYMENT_MODE
# ═══════════════════════════════════════════════════════════════════════════════

def get_pg_connection():
    """
    Returns a PostgreSQL connection.
    Cloud: AWS RDS | Inhouse: local PostgreSQL
    """
    if not PG_AVAILABLE:
        raise RuntimeError("psycopg2 not installed — run: pip install psycopg2-binary")

    if DEPLOYMENT_MODE == 'cloud':
        conn = psycopg2.connect(
            host=RDS_HOST, port=RDS_PORT, dbname=RDS_DB,
            user=RDS_USER, password=RDS_PASSWORD,
            connect_timeout=10, sslmode='require'
        )
    else:  # inhouse
        conn = psycopg2.connect(
            host=INHOUSE_PG_HOST, port=INHOUSE_PG_PORT, dbname=INHOUSE_PG_DB,
            user=INHOUSE_PG_USER, password=INHOUSE_PG_PASSWORD,
            connect_timeout=10
        )
    return conn


def get_connection():
    """
    Main connection getter.
    Returns (connection, db_type) where db_type is 'rds' | 'inhouse_pg' | 'sqlite'
    """
    if (USE_RDS or USE_INHOUSE) and PG_AVAILABLE:
        try:
            conn = get_pg_connection()
            db_type = 'rds' if USE_RDS else 'inhouse_pg'
            return conn, db_type
        except Exception as e:
            print(f"[DB] PostgreSQL connection failed ({e}) — falling back to SQLite")

    # SQLite fallback
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn, 'sqlite'


def get_mongo_collection():
    """
    Returns MongoDB collection for raw watchdog events.
    Only used in inhouse mode. Falls back to None if unavailable.
    """
    if not USE_MONGO or not MONGO_AVAILABLE:
        return None
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.server_info()  # test connection
        return client[MONGO_DB][MONGO_EVENTS_COLLECTION]
    except Exception as e:
        print(f"[DB] MongoDB unavailable ({e}) — watchdog events will use PostgreSQL only")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA SETUP
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS activity_log (
    id          SERIAL PRIMARY KEY,
    timestamp   DOUBLE PRECISION NOT NULL,
    day_of_week INTEGER,
    hour        INTEGER,
    cpu_pct     REAL,
    ram_pct     REAL,
    disk_pct    REAL,
    free_gb     REAL,
    write_speed REAL,
    open_files  INTEGER DEFAULT 0,
    machine_id  TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS anomaly_log (
    id            SERIAL PRIMARY KEY,
    timestamp     DOUBLE PRECISION NOT NULL,
    anomaly_type  TEXT NOT NULL,
    details       TEXT,
    filepath      TEXT,
    entropy_score REAL,
    severity      TEXT DEFAULT 'HIGH',
    machine_id    TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS backup_history (
    id             SERIAL PRIMARY KEY,
    timestamp      DOUBLE PRECISION NOT NULL,
    backup_type    TEXT NOT NULL,
    status         TEXT NOT NULL,
    size_mb        REAL DEFAULT 0,
    location       TEXT,
    duration_sec   REAL DEFAULT 0,
    files_count    INTEGER DEFAULT 0,
    error_msg      TEXT,
    sha256_hash    TEXT,
    compressed_by  TEXT DEFAULT 'local',
    machine_id     TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS risk_score_log (
    id            SERIAL PRIMARY KEY,
    timestamp     DOUBLE PRECISION NOT NULL,
    score         REAL NOT NULL,
    decision      TEXT NOT NULL,
    storage_pts   REAL DEFAULT 0,
    file_pts      REAL DEFAULT 0,
    gap_pts       REAL DEFAULT 0,
    cpu_pts       REAL DEFAULT 0,
    anomaly_pts   REAL DEFAULT 0,
    machine_id    TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS system_log (
    id          SERIAL PRIMARY KEY,
    timestamp   DOUBLE PRECISION NOT NULL,
    level       TEXT NOT NULL,
    module      TEXT,
    message     TEXT NOT NULL,
    machine_id  TEXT DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_activity_ts    ON activity_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_anomaly_ts     ON anomaly_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_backup_ts      ON backup_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_risk_ts        ON risk_score_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_syslog_ts      ON system_log(timestamp);
"""

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL, day_of_week INTEGER, hour INTEGER,
    cpu_pct REAL, ram_pct REAL, disk_pct REAL, free_gb REAL,
    write_speed REAL, open_files INTEGER DEFAULT 0, machine_id TEXT DEFAULT 'default'
);
CREATE TABLE IF NOT EXISTS anomaly_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL, anomaly_type TEXT, details TEXT, filepath TEXT,
    entropy_score REAL, severity TEXT DEFAULT 'HIGH', machine_id TEXT DEFAULT 'default'
);
CREATE TABLE IF NOT EXISTS backup_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL, backup_type TEXT, status TEXT, size_mb REAL DEFAULT 0,
    location TEXT, duration_sec REAL DEFAULT 0, files_count INTEGER DEFAULT 0,
    error_msg TEXT, sha256_hash TEXT, compressed_by TEXT DEFAULT 'local',
    machine_id TEXT DEFAULT 'default'
);
CREATE TABLE IF NOT EXISTS risk_score_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL, score REAL, decision TEXT,
    storage_pts REAL DEFAULT 0, file_pts REAL DEFAULT 0,
    gap_pts REAL DEFAULT 0, cpu_pts REAL DEFAULT 0,
    anomaly_pts REAL DEFAULT 0, machine_id TEXT DEFAULT 'default'
);
CREATE TABLE IF NOT EXISTS system_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL, level TEXT, module TEXT, message TEXT,
    machine_id TEXT DEFAULT 'default'
);
"""


def init_database():
    """Create all tables. Call once at startup."""
    conn, db_type = get_connection()
    try:
        cur = conn.cursor()
        if db_type in ('rds', 'inhouse_pg'):
            for stmt in SCHEMA_PG.strip().split(';'):
                stmt = stmt.strip()
                if stmt:
                    try:
                        cur.execute(stmt)
                    except Exception as e:
                        if 'already exists' not in str(e).lower():
                            print(f"[DB] Schema warn: {e}")
        else:
            conn.executescript(SCHEMA_SQLITE)
        conn.commit()
        print(f"[DB] Tables initialized — mode: {DEPLOYMENT_MODE.upper()} ({db_type})")
    finally:
        conn.close()

    # MongoDB: create index on timestamp for events collection
    if USE_MONGO:
        col = get_mongo_collection()
        if col is not None:
            col.create_index('timestamp')
            col.create_index('event_type')
            print("[DB] MongoDB events collection ready")


# ═══════════════════════════════════════════════════════════════════════════════
# WRITE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _ph(db_type):
    """Return placeholder character for this DB type."""
    return '%s' if db_type in ('rds', 'inhouse_pg') else '?'


def _machine_id():
    """Get this machine's ID from config."""
    try:
        from config import MACHINE_ID
        return MACHINE_ID
    except ImportError:
        import socket
        return socket.gethostname()


def insert_activity_log(cpu_pct, ram_pct, disk_pct, free_gb,
                        write_speed=0.0, open_files=0):
    now = time.time()
    dt  = datetime.datetime.fromtimestamp(now)
    conn, db_type = get_connection()
    p = _ph(db_type)
    try:
        conn.cursor().execute(
            f"INSERT INTO activity_log (timestamp,day_of_week,hour,cpu_pct,ram_pct,"
            f"disk_pct,free_gb,write_speed,open_files,machine_id) "
            f"VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p})",
            (now, dt.weekday(), dt.hour, cpu_pct, ram_pct,
             disk_pct, free_gb, write_speed, open_files, _machine_id())
        )
        conn.commit()
    finally:
        conn.close()


def insert_anomaly_log(anomaly_type, details='', filepath='',
                       entropy_score=0.0, severity='HIGH'):
    conn, db_type = get_connection()
    p = _ph(db_type)
    try:
        conn.cursor().execute(
            f"INSERT INTO anomaly_log (timestamp,anomaly_type,details,filepath,"
            f"entropy_score,severity,machine_id) VALUES ({p},{p},{p},{p},{p},{p},{p})",
            (time.time(), anomaly_type, details, filepath,
             entropy_score, severity, _machine_id())
        )
        conn.commit()
    finally:
        conn.close()

    # Also write to MongoDB if inhouse mode
    if USE_MONGO:
        col = get_mongo_collection()
        if col is not None:
            try:
                col.insert_one({
                    'event_type': 'anomaly',
                    'anomaly_type': anomaly_type,
                    'details': details,
                    'filepath': filepath,
                    'entropy_score': entropy_score,
                    'severity': severity,
                    'timestamp': time.time(),
                    'machine_id': _machine_id()
                })
            except Exception as e:
                print(f"[DB] MongoDB anomaly log failed: {e}")


def insert_backup_history(backup_type, status, size_mb=0.0, location='',
                          duration_sec=0.0, files_count=0, error_msg='',
                          sha256_hash='', compressed_by='local'):
    conn, db_type = get_connection()
    p = _ph(db_type)
    try:
        conn.cursor().execute(
            f"INSERT INTO backup_history (timestamp,backup_type,status,size_mb,location,"
            f"duration_sec,files_count,error_msg,sha256_hash,compressed_by,machine_id) "
            f"VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})",
            (time.time(), backup_type, status, size_mb, location,
             duration_sec, files_count, error_msg, sha256_hash,
             compressed_by, _machine_id())
        )
        conn.commit()
    finally:
        conn.close()


def insert_risk_score_log(score, decision, storage_pts, file_pts,
                          gap_pts, cpu_pts, anomaly_pts):
    conn, db_type = get_connection()
    p = _ph(db_type)
    try:
        conn.cursor().execute(
            f"INSERT INTO risk_score_log (timestamp,score,decision,storage_pts,"
            f"file_pts,gap_pts,cpu_pts,anomaly_pts,machine_id) "
            f"VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p})",
            (time.time(), score, decision, storage_pts, file_pts,
             gap_pts, cpu_pts, anomaly_pts, _machine_id())
        )
        conn.commit()
    finally:
        conn.close()


def insert_system_log(level, message, module='agent'):
    """
    Store system log entries in DB.
    This is the SELF-MONITORING (mentor suggestion 8).
    """
    conn, db_type = get_connection()
    p = _ph(db_type)
    try:
        conn.cursor().execute(
            f"INSERT INTO system_log (timestamp,level,module,message,machine_id) "
            f"VALUES ({p},{p},{p},{p},{p})",
            (time.time(), level, module, message, _machine_id())
        )
        conn.commit()
    except Exception:
        pass  # never crash the agent because of a log write failure
    finally:
        conn.close()


def insert_watchdog_event(event_type, filepath, details=None):
    """
    Raw watchdog event → MongoDB (inhouse) or PostgreSQL system_log (cloud).
    MongoDB handles unstructured JSON — perfect for raw events.
    """
    if USE_MONGO:
        col = get_mongo_collection()
        if col is not None:
            try:
                col.insert_one({
                    'event_type': event_type,
                    'filepath': filepath,
                    'details': details or {},
                    'timestamp': time.time(),
                    'machine_id': _machine_id()
                })
                return
            except Exception as e:
                print(f"[DB] MongoDB event insert failed: {e}")
    # Fallback: store as system_log entry
    insert_system_log('EVENT', f"{event_type}: {filepath}", module='watchdog')


# ═══════════════════════════════════════════════════════════════════════════════
# READ HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _rows_to_dicts(cur, rows, db_type):
    if db_type in ('rds', 'inhouse_pg'):
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    else:
        return [dict(zip([c[0] for c in cur.description], r)) for r in rows]


def fetch_recent_risk_scores(limit=100):
    conn, db_type = get_connection()
    p = _ph(db_type)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM risk_score_log ORDER BY timestamp DESC LIMIT {p}", (limit,))
        return _rows_to_dicts(cur, cur.fetchall(), db_type)
    finally:
        conn.close()


def fetch_recent_anomalies(limit=50):
    conn, db_type = get_connection()
    p = _ph(db_type)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM anomaly_log ORDER BY timestamp DESC LIMIT {p}", (limit,))
        return _rows_to_dicts(cur, cur.fetchall(), db_type)
    finally:
        conn.close()


def fetch_backup_history(limit=50):
    conn, db_type = get_connection()
    p = _ph(db_type)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM backup_history ORDER BY timestamp DESC LIMIT {p}", (limit,))
        return _rows_to_dicts(cur, cur.fetchall(), db_type)
    finally:
        conn.close()


def fetch_system_logs(limit=200, level=None):
    """Fetch system logs from DB — used by dashboard to display agent logs."""
    conn, db_type = get_connection()
    p = _ph(db_type)
    try:
        cur = conn.cursor()
        if level:
            cur.execute(
                f"SELECT * FROM system_log WHERE level={p} ORDER BY timestamp DESC LIMIT {p}",
                (level, limit)
            )
        else:
            cur.execute(f"SELECT * FROM system_log ORDER BY timestamp DESC LIMIT {p}", (limit,))
        return _rows_to_dicts(cur, cur.fetchall(), db_type)
    finally:
        conn.close()


def fetch_cpu_heatmap_data():
    conn, db_type = get_connection()
    week_ago = time.time() - 7 * 86400
    try:
        cur = conn.cursor()
        if db_type in ('rds', 'inhouse_pg'):
            cur.execute(
                "SELECT day_of_week,hour,AVG(cpu_pct) as avg_cpu FROM activity_log "
                "WHERE timestamp > %s GROUP BY day_of_week,hour ORDER BY day_of_week,hour",
                (week_ago,)
            )
        else:
            cur.execute(
                "SELECT day_of_week,hour,AVG(cpu_pct) as avg_cpu FROM activity_log "
                "WHERE timestamp > ? GROUP BY day_of_week,hour ORDER BY day_of_week,hour",
                (week_ago,)
            )
        return cur.fetchall()
    finally:
        conn.close()


def get_last_backup_info():
    conn, db_type = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT timestamp,status FROM backup_history ORDER BY timestamp DESC LIMIT 1")
        row = cur.fetchone()
        if row is None:
            return 14.0, 'never'
        ts     = row[0] if db_type == 'sqlite' else row['timestamp'] if hasattr(row, 'keys') else row[0]
        status = row[1] if db_type == 'sqlite' else row['status'] if hasattr(row, 'keys') else row[1]
        return round((time.time() - float(ts)) / 86400, 2), status
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# MIGRATION: SQLite → PostgreSQL (cloud or inhouse)
# ═══════════════════════════════════════════════════════════════════════════════

def migrate_sqlite_to_postgres():
    """
    Migrate existing guardianx.db data to PostgreSQL (RDS or inhouse).
    Run: python database.py migrate
    """
    import sqlite3 as sl
    print(f"[MIGRATE] SQLite → PostgreSQL ({DEPLOYMENT_MODE})...")
    src = sl.connect(SQLITE_PATH)
    src.row_factory = sl.Row
    dst, db_type = get_connection()

    tables = ['activity_log', 'anomaly_log', 'backup_history', 'risk_score_log', 'system_log']
    for table in tables:
        try:
            rows = src.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                print(f"  [SKIP] {table} empty")
                continue
            cols  = rows[0].keys()
            ph    = ','.join(['%s'] * len(cols))
            col_s = ','.join(cols)
            data  = [tuple(r) for r in rows]
            dst_cur = dst.cursor()
            psycopg2.extras.execute_batch(
                dst_cur,
                f"INSERT INTO {table} ({col_s}) VALUES ({ph}) ON CONFLICT DO NOTHING",
                data
            )
            dst.commit()
            print(f"  [OK] {table}: {len(rows)} rows")
        except Exception as e:
            print(f"  [FAIL] {table}: {e}")

    src.close()
    dst.close()
    print("[MIGRATE] Done!")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'migrate':
        migrate_sqlite_to_postgres()
    else:
        init_database()
        print(f"[DB] Ready — mode: {DEPLOYMENT_MODE}")