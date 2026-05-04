# backup_executor.py — MENTOR-CORRECTED VERSION
# WHAT CHANGED:
#   - .py, .html, .css, .js files are NO LONGER backed up (code, not data)
#   - RDS tables are exported as CSV and included in backup
#   - System logs from logs/ folder are always included
#   - Active process files (open by running programs) get priority 10
# BTech CSE | Section 2CC | Group 31w
import hashlib
import os
import csv
import time
import json
import hashlib
import datetime
import tempfile
import zipfile
import shutil
import boto3


def get_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()
from botocore.exceptions import ClientError

from config import (
    AWS_REGION, S3_BUCKET, USE_AWS, USE_LAMBDA_COMPRESS,
    LOCAL_BACKUP_DIR, LOCAL_LOG_DIR,
    BACKUP_EXTENSIONS, SKIP_EXTENSIONS, SKIP_DIRS,
    FILE_IMPORTANCE, LAMBDA_FUNCTION,
    RDS_EXPORT_TABLES, RDS_EXPORT_ROWS,
    USE_RDS
)
from database import insert_backup_history


# ── AWS clients ───────────────────────────────────────────────
_s3  = boto3.client('s3',     region_name=AWS_REGION) if USE_AWS else None
_lam = boto3.client('lambda', region_name=AWS_REGION) if USE_LAMBDA_COMPRESS else None


# ═══════════════════════════════════════════════════════════════
# STEP 1: EXPORT RDS TABLES AS CSV
# Mentor said: "RDS mein jo data hai uska backup lo"
# We export each table to a CSV file, then zip them
# ═══════════════════════════════════════════════════════════════

def export_rds_tables_to_csv(export_dir: str) -> list:
    """
    Export RDS PostgreSQL tables to CSV files.
    These CSV files are the ACTUAL DATA backup.

    Returns list of exported file paths.
    """
    if not USE_RDS:
        print("[BACKUP] RDS not enabled — skipping table export")
        return []

    try:
        import psycopg2
        from config import RDS_HOST, RDS_PORT, RDS_DB, RDS_USER, RDS_PASSWORD
        conn = psycopg2.connect(
            host=RDS_HOST, port=RDS_PORT, dbname=RDS_DB,
            user=RDS_USER, password=RDS_PASSWORD,
            sslmode='require', connect_timeout=10
        )
    except Exception as e:
        print(f"[BACKUP] RDS connect failed for CSV export: {e}")
        return []

    exported = []
    os.makedirs(export_dir, exist_ok=True)

    for table in RDS_EXPORT_TABLES:
        try:
            cur = conn.cursor()
            limit = RDS_EXPORT_ROWS.get(table, 0)

            # Build query — latest rows first
            if limit > 0:
                q = f"SELECT * FROM {table} ORDER BY timestamp DESC LIMIT {limit}"
            else:
                q = f"SELECT * FROM {table} ORDER BY timestamp DESC"

            cur.execute(q)
            rows = cur.fetchall()
            headers = [desc[0] for desc in cur.description]

            # Write to CSV
            csv_path = os.path.join(export_dir, f"{table}.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)

            file_size_kb = os.path.getsize(csv_path) / 1024
            print(f"[BACKUP] RDS export: {table}.csv → {len(rows)} rows ({file_size_kb:.1f} KB)")
            exported.append(csv_path)
            cur.close()

        except Exception as e:
            print(f"[BACKUP] Failed to export {table}: {e}")

    conn.close()
    return exported


# ═══════════════════════════════════════════════════════════════
# STEP 2: COLLECT DATA FILES FROM FILESYSTEM
# Only backs up DATA files (CSV, XLSX, logs, docs)
# SKIPS all code files (.py, .html, .css, .js)
# ═══════════════════════════════════════════════════════════════

def collect_files(backup_type: str, last_backup_ts: float = 0,
                  active_files: set = None) -> list:
    """
    Collect DATA files for backup — NOT code files.

    What gets collected:
    - .csv, .xlsx, .xls  → User data files (most important)
    - .log               → System logs from logs/ folder
    - .docx, .pdf        → Documents
    - .env               → Environment config (has credentials)
    - .json, .txt        → Data files

    What gets SKIPPED:
    - .py  → Python code (on GitHub, not data)
    - .html, .css, .js  → Frontend code (not data)
    - .db, .sqlite       → Data is in RDS already
    - .pyc, .tmp         → Useless files
    """
    active_files = active_files or set()
    result = []
    watch_path = os.path.abspath('.')

    for root, dirs, files in os.walk(watch_path):
        # Skip forbidden directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in files:
            fpath = os.path.join(root, fname)
            ext   = os.path.splitext(fname)[1].lower()

            # NEVER backup these
            if ext in SKIP_EXTENSIONS:
                continue

            # Check if it's a log file from logs/ folder — always include
            is_log = (ext == '.log' or
                      fpath.startswith(os.path.abspath(LOCAL_LOG_DIR)))

            # For non-log files — must be in BACKUP_EXTENSIONS
            if not is_log and ext not in BACKUP_EXTENSIONS:
                continue

            # Time filter for incremental/differential
            if backup_type in ('incremental', 'differential') and last_backup_ts > 0:
                try:
                    if os.path.getmtime(fpath) < last_backup_ts:
                        continue
                except OSError:
                    continue

            # Importance score
            is_active  = fpath in active_files
            importance = 10 if is_active else FILE_IMPORTANCE.get(ext, 1)
            if importance == 0:
                continue

            try:
                size = os.path.getsize(fpath)
            except OSError:
                continue

            result.append({
                'path'      : fpath,
                'importance': importance,
                'size_bytes': size,
                'is_active' : is_active,
                'is_log'    : is_log,
                'ext'       : ext,
            })

    # Sort by importance — most important files first
    result.sort(key=lambda f: f['importance'], reverse=True)

    # Summary
    active_count = sum(1 for f in result if f['is_active'])
    log_count    = sum(1 for f in result if f['is_log'])
    csv_count    = sum(1 for f in result if f['ext'] in ('.csv', '.xlsx', '.xls'))
    doc_count    = sum(1 for f in result if f['ext'] in ('.docx', '.pdf', '.txt'))

    print(f"[BACKUP] Files collected: {len(result)} total")
    print(f"[BACKUP]   → {csv_count} data files (.csv/.xlsx)")
    print(f"[BACKUP]   → {log_count} log files (.log)")
    print(f"[BACKUP]   → {doc_count} documents (.docx/.pdf/.txt)")
    print(f"[BACKUP]   → {active_count} active process files (priority 10)")
    print(f"[BACKUP]   → Skipped: .py .html .css .js (code files, not data)")
    print(f"[BACKUP]   → Skipped: .db .sqlite (data is in RDS)")

    return result


# ═══════════════════════════════════════════════════════════════
# SHA-256 Integrity Check
# ═══════════════════════════════════════════════════════════════

def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ''


# ═══════════════════════════════════════════════════════════════
# LOCAL COMPRESSION (Lambda fallback)
# ═══════════════════════════════════════════════════════════════

def _compress_locally(files: list, rds_csvs: list, backup_type: str) -> tuple:
    """
    Compress data files + RDS CSV exports into one zip.
    Returns (zip_path, size_mb, file_count, sha256)
    """
    ts_str  = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    zipname = f"{ts_str}_{backup_type}.zip"
    tmpdir  = tempfile.mkdtemp()
    zippath = os.path.join(tmpdir, zipname)

    count = 0
    with zipfile.ZipFile(zippath, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:

        # 1. RDS CSV exports (most important — actual data)
        for csv_path in rds_csvs:
            try:
                arcname = 'rds_data/' + os.path.basename(csv_path)
                zf.write(csv_path, arcname)
                count += 1
            except Exception as e:
                print(f"[BACKUP] Skipped RDS CSV {csv_path}: {e}")

        # 2. Data files from filesystem
        for file_info in files:
            try:
                arcname = 'files/' + os.path.relpath(file_info['path']).replace('\\', '/')
                zf.write(file_info['path'], arcname)
                count += 1
            except Exception as e:
                print(f"[BACKUP] Skipped {file_info['path']}: {e}")

    size_mb  = round(os.path.getsize(zippath) / (1024 * 1024), 3)
    checksum = sha256_of_file(zippath)
    print(f"[BACKUP] Compressed: {size_mb}MB, {count} files ({len(rds_csvs)} RDS CSV exports + {count-len(rds_csvs)} data files)")
    print(f"[BACKUP] SHA-256: {checksum[:32]}...")
    return zippath, size_mb, count, checksum


# ═══════════════════════════════════════════════════════════════
# LAMBDA ASYNC COMPRESSION
# ═══════════════════════════════════════════════════════════════

def _upload_raw_to_s3_temp(files: list, rds_csvs: list, backup_type: str) -> str:
    """Upload raw files + RDS CSVs to S3 temp prefix for Lambda processing."""
    ts_str    = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    s3_prefix = f"temp/{ts_str}_{backup_type}/"

    total = len(files) + len(rds_csvs)
    print(f"[BACKUP] Uploading {total} files to S3 temp: {s3_prefix}")
    print(f"[BACKUP]   → {len(rds_csvs)} RDS CSV exports")
    print(f"[BACKUP]   → {len(files)} data files")

    uploaded = 0

    # Upload RDS CSVs first (priority)
    for csv_path in rds_csvs:
        try:
            s3_key = s3_prefix + 'rds_data/' + os.path.basename(csv_path)
            _s3.upload_file(csv_path, S3_BUCKET, s3_key)
            uploaded += 1
        except Exception as e:
            print(f"[BACKUP] Skipped RDS CSV {csv_path}: {e}")

    # Upload data files
    for file_info in files:
        try:
            rel    = os.path.relpath(file_info['path'])
            s3_key = s3_prefix + 'files/' + rel.replace('\\', '/')
            _s3.upload_file(file_info['path'], S3_BUCKET, s3_key)
            uploaded += 1
        except Exception as e:
            print(f"[BACKUP] Skipped {file_info['path']}: {e}")

    print(f"[BACKUP] Uploaded {uploaded}/{total} to temp prefix")
    return s3_prefix


def _invoke_lambda(s3_prefix: str, backup_type: str, machine_id: str) -> dict:
    """Invoke Lambda for async compression."""
    payload = {
        'backup_type': backup_type,
        's3_prefix'  : s3_prefix,
        'machine_id' : machine_id,
    }
    print(f"[BACKUP] Invoking Lambda: {LAMBDA_FUNCTION}")
    try:
        _lam.invoke(
            FunctionName   = LAMBDA_FUNCTION,
            InvocationType = 'Event',
            Payload        = json.dumps(payload).encode()
        )
        print(f"[BACKUP] Lambda invoked — compression running on AWS (async)")
        return {'status': 'LAMBDA_TRIGGERED', 'compressed_by': 'lambda'}
    except ClientError as e:
        print(f"[BACKUP] Lambda failed: {e} — falling back to local")
        return {'status': 'LAMBDA_FAILED', 'error': str(e)}


def _upload_zip_to_s3(zip_path: str, backup_type: str, emergency: bool = False) -> str:
    """Upload compressed zip to S3 final location."""
    filename = os.path.basename(zip_path)
    s3_key   = f"{backup_type}/{filename}"
    storage  = 'STANDARD_IA' if backup_type == 'differential' else 'STANDARD'

    _s3.upload_file(zip_path, S3_BUCKET, s3_key, ExtraArgs={'StorageClass': storage})
    s3_uri = f"s3://{S3_BUCKET}/{s3_key}"

    if emergency:
        try:
            obj = _s3.head_object(Bucket=S3_BUCKET, Key=s3_key)
            ver = obj.get('VersionId')
            if ver:
                _s3.put_object_retention(
                    Bucket=S3_BUCKET, Key=s3_key, VersionId=ver,
                    Retention={
                        'Mode': 'COMPLIANCE',
                        'RetainUntilDate': datetime.datetime.utcnow() + datetime.timedelta(days=365)
                    }
                )
                print(f"[BACKUP] Object Lock applied — emergency backup immutable for 1 year")
        except Exception as e:
            print(f"[BACKUP] Object Lock warning: {e}")

    return s3_uri


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def run_backup(backup_type: str = 'incremental',
               emergency: bool = False,
               last_backup_ts: float = 0,
               active_files: set = None,
               trigger: str = '') -> dict:
    """
    MENTOR-CORRECTED backup flow:

    1. Export RDS tables to CSV          ← ACTUAL DATA (activity_log, risk_score_log, etc.)
    2. Collect data files from disk      ← .csv, .xlsx, .log, .docx, .pdf (NOT .py)
    3. Compress everything into one zip
    4. Upload to S3 (or local folder)
    5. Log result to RDS backup_history

    ZIP structure:
      rds_data/
        activity_log.csv      ← CPU/RAM/Disk readings from RDS
        risk_score_log.csv    ← Risk score history from RDS
        anomaly_log.csv       ← Detected anomalies from RDS
        backup_history.csv    ← Backup records from RDS
        system_log.csv        ← Agent logs from RDS
      files/
        logs/agent.log        ← Local system log file
        [any .csv/.xlsx user data files found]
        [any .docx/.pdf documents found]
    """
    start = time.time()
    print(f"\n[BACKUP] ═══════════════════════════════════════════════")
    print(f"[BACKUP] Starting {backup_type.upper()} | Mode: {'Lambda' if USE_LAMBDA_COMPRESS else 'Local'}")
    print(f"[BACKUP] Backup strategy: RDS data export + filesystem data files")
    print(f"[BACKUP] ═══════════════════════════════════════════════")

    # Get active process files (mentor suggestion 1)
    from monitor import get_active_process_files
    active = active_files or get_active_process_files()

    # ── STEP 1: Export RDS tables to CSV ─────────────────────
    tmpdir = tempfile.mkdtemp()
    rds_csv_dir = os.path.join(tmpdir, 'rds_exports')

    print(f"\n[BACKUP] Step 1: Exporting RDS tables to CSV...")
    rds_csvs = export_rds_tables_to_csv(rds_csv_dir)
    print(f"[BACKUP] Exported {len(rds_csvs)} RDS table CSV files")

    # ── STEP 2: Collect data files ────────────────────────────
    print(f"\n[BACKUP] Step 2: Collecting data files (NOT code)...")
    files = collect_files(backup_type, last_backup_ts, active)

    # If nothing to backup at all, still backup RDS exports
    if not files and not rds_csvs:
        print("[BACKUP] Nothing to back up — skipping")
        insert_backup_history(backup_type, 'SKIPPED', compressed_by='none')
        return {'status': 'SKIPPED'}

    if not files:
        print("[BACKUP] No data files found on disk — backing up RDS exports only")

    # ── STEP 3: Compress + upload ─────────────────────────────
    print(f"\n[BACKUP] Step 3: Compressing...")

    if USE_LAMBDA_COMPRESS and USE_AWS and _lam is not None:
        # Try Lambda path
        s3_prefix = _upload_raw_to_s3_temp(files, rds_csvs, backup_type)
        result    = _invoke_lambda(s3_prefix, backup_type, _machine_id())
        duration  = round(time.time() - start, 2)

        if result['status'] == 'LAMBDA_TRIGGERED':
            insert_backup_history(
                backup_type, 'LAMBDA_TRIGGERED',
                size_mb=0, location=s3_prefix,
                duration_sec=duration, files_count=len(files) + len(rds_csvs),
                compressed_by='lambda'
            )
            print(f"[BACKUP] Lambda triggered in {duration}s")
            shutil.rmtree(tmpdir, ignore_errors=True)
            return {'status': 'LAMBDA_TRIGGERED', 'rds_exports': len(rds_csvs), 'files': len(files)}

        print(f"[BACKUP] Lambda failed — falling back to local compression")

    # Local compression
    zip_path, size_mb, count, checksum = _compress_locally(files, rds_csvs, backup_type)
    sha256_hash = get_sha256(zip_path)
    duration = round(time.time() - start, 2)

    if USE_AWS and _s3 is not None:
        try:
            location = _upload_zip_to_s3(zip_path, backup_type, emergency)
            print(f"[BACKUP] Uploaded to S3: {location}")
        except Exception as e:
            print(f"[BACKUP] S3 upload failed: {e}")
            location = zip_path
    else:
        # Save locally
        os.makedirs(LOCAL_BACKUP_DIR, exist_ok=True)
        dest     = os.path.join(LOCAL_BACKUP_DIR, os.path.basename(zip_path))
        shutil.move(zip_path, dest)
        location = dest

    # Cleanup temp
    shutil.rmtree(tmpdir, ignore_errors=True)

    # ── STEP 4: Log to RDS ────────────────────────────────────
    insert_backup_history(
        backup_type, 'SUCCESS', size_mb, location,
        duration, count,
      
        compressed_by= 'local',
        sha256_hash=sha256_hash
    )

    print(f"[BACKUP] ═══════════════════════════════════════════════")
    print(f"[BACKUP] SUCCESS — {size_mb}MB in {duration}s")
    print(f"[BACKUP]   → Location : {location}")
    print(f"[BACKUP]   → Contents : {len(rds_csvs)} RDS CSV exports + {len(files)} data files")
    print(f"[BACKUP]   → SHA-256  : {checksum[:32]}...")
    print(f"[BACKUP] ═══════════════════════════════════════════════")

    return {
        'status'      : 'SUCCESS',
        'size_mb'     : size_mb,
        'location'    : location,
        'rds_exports' : len(rds_csvs),
        'files'       : len(files),
        'total_items' : count,
        'duration'    : duration,
        'sha256'      : checksum
    }


def _machine_id():
    try:
        from config import MACHINE_ID
        return MACHINE_ID
    except (ImportError, AttributeError):
        import socket
        return socket.gethostname()


if __name__ == '__main__':
    print("[BACKUP] Running test incremental backup...")
    result = run_backup('incremental')
    print(f"\n[BACKUP] Result: {result}")
    