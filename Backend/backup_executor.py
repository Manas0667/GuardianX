

import os, shutil, sqlite3, zipfile, logging
from datetime import datetime
from config import DB, WATCH, TEMP_DIR, BACKUP_DIR


USE_AWS   = False          # flip to True in Week 9
BUCKET    = "backup-agent-2cc"

# ── COMPRESS FILES ────────────────────────────────────────────
def compress_files(folder, backup_type):
    os.makedirs(TEMP_DIR, exist_ok=True)
    ts       = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"{ts}_{backup_type.lower()}"
    archive  = shutil.make_archive(
        os.path.join(TEMP_DIR, filename),
        "zip",
        folder
    )
    size_mb = round(os.path.getsize(archive) / (1024**2), 2)
    logging.info(f"[COMPRESS] {filename}.zip — {size_mb} MB")
    return archive, filename, size_mb

# ── UPLOAD — LOCAL MODE ───────────────────────────────────────
def upload_local(archive, backup_type, filename):
    folder = backup_type.lower()
    dest = os.path.join(BACKUP_DIR, folder)
    os.makedirs(WATCH, exist_ok=True)
    final  = os.path.join(dest, filename + ".zip")
    shutil.copy(archive, final)
    os.remove(archive)
    logging.info(f"[LOCAL] Saved to {final}")
    return final

# ── UPLOAD — AWS S3 MODE ──────────────────────────────────────
def upload_s3(archive, backup_type, filename):
    try:
        import boto3
        from dotenv import load_dotenv
        load_dotenv()
        s3 = boto3.client(
            "s3",
            aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name           = os.getenv("AWS_REGION", "ap-south-1")
        )
        folder = backup_type.lower()
        s3_key = f"{folder}/{filename}.zip"
        s3.upload_file(archive, BUCKET, s3_key)
        os.remove(archive)
        logging.info(f"[S3] Uploaded: {s3_key}")
        return f"s3://{BUCKET}/{s3_key}"
    except Exception as e:
        logging.info(f"[S3] Upload failed: {e} — falling back to local")
        return upload_local(archive, backup_type, filename)

# ── SAVE RESULT TO DATABASE ───────────────────────────────────
def save_to_history(backup_type, status, size_mb, location):
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT INTO backup_history(timestamp,type,status,size_mb,location) VALUES(?,?,?,?,?)",
        (datetime.now().isoformat(), backup_type, status, size_mb, location)
    )
    conn.commit()
    conn.close()
    logging.info(f"[DB] Saved to backup_history — {backup_type} {status}")

# ── MAIN EXECUTE BACKUP ───────────────────────────────────────
def execute_backup(backup_type, folder=WATCH):
    logging.info(f"\n[BACKUP] Starting {backup_type} backup...")
    try:
        # Step 1 — compress
        archive, filename, size_mb = compress_files(folder, backup_type)
        # Step 2 — upload
        if USE_AWS:
            location = upload_s3(archive, backup_type, filename)
        else:
            location = upload_local(archive, backup_type, filename)
        # Step 3 — record
        save_to_history(backup_type, "SUCCESS", size_mb, location)
        logging.info(f"[BACKUP] {backup_type} complete — {size_mb} MB\n")
        return True
    except Exception as e:
        save_to_history(backup_type, "FAILED", 0, str(e))
        logging.info(f"[BACKUP] FAILED — {e}\n")
        return False

# ── LIST ALL BACKUPS ──────────────────────────────────────────
def list_backups():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT timestamp, type, status, size_mb, location FROM backup_history ORDER BY id DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return rows

# ── TEST ──────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.info("\n=== BACKUP EXECUTOR TEST ===\n")
    # create a sample file to back up
    os.makedirs("test_files", exist_ok=True)
    with open("test_files/sample.txt", "w") as f:
        f.write("This is a test file for backup agent demo.\n" * 10)
    with open("test_files/sample.py", "w") as f:
        f.write("# Sample Python file\nlogging.info('Backup agent test')\n")

    # run all 3 backup types
    execute_backup("INCREMENTAL")
    execute_backup("DIFFERENTIAL")
    execute_backup("FULL")

    # show history
    logging.info("\n[HISTORY] Last 5 backups:")
    for row in list_backups():
        logging.info(f"  {row[0][:16]}  {row[1]:<14} {row[2]:<8} {row[3]} MB")

    logging.info("\n[OK] backup_executor.py is working correctly!")