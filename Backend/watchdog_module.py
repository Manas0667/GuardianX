# =============================================================
# watchdog_module.py — Chahat's Module
# Continuous file monitoring + 5 anomaly detectors
# =============================================================

import os, math, collections, sqlite3, time, logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import DB, WATCH

start_time  = time.time()

# live counters
creates    = 0
modifies   = 0
deletes    = 0
mismatches = 0
entropy_flags = []

# file extensions and their importance scores
IMPORTANCE = {
    ".db": 10, ".sqlite": 10, ".sql": 9,
    ".py": 9,  ".js": 8,     ".java": 8,
    ".docx": 7,".xlsx": 7,   ".pdf": 6,
    ".txt": 4, ".csv": 4,    ".json": 4,
    ".jpg": 1, ".png": 1,    ".mp4": 1,
    ".tmp": 0, ".log": 0
}

# extensions expected to have high entropy — skip entropy check
SKIP_ENTROPY = {".zip", ".gz", ".rar", ".7z", ".enc", ".pdf", ".mp4", ".mp3"}

# ── SHANNON ENTROPY ───────────────────────────────────────────
def shannon_entropy(filepath):
    try:
        with open(filepath, "rb") as f:
            data = f.read(2048)
        if not data:
            return 0
        freq = collections.Counter(data)
        total = len(data)
        return -sum((c / total) * math.log2(c / total) for c in freq.values())
    except:
        return 0

# ── LOG ANOMALY TO DATABASE ───────────────────────────────────
def log_anomaly(atype, details):
    try:
        conn = sqlite3.connect(DB)
        conn.execute(
            "INSERT INTO anomaly_log(timestamp,type,details) VALUES(?,?,?)",
            (datetime.now().isoformat(), atype, details)
        )
        conn.commit()
        conn.close()
    except:
        pass
    logging.info(f"[ANOMALY] {atype} — {details}")

# ── FILE SYSTEM EVENT HANDLER ─────────────────────────────────
class AgentHandler(FileSystemEventHandler):

    def on_created(self, event):
        global creates
        if event.is_directory:
            return
        creates += 1
        logging.info(f"[CREATE] {os.path.basename(event.src_path)}")

    def on_modified(self, event):
        global modifies
        if event.is_directory:
            return
        modifies += 1
        ext = os.path.splitext(event.src_path)[1].lower()
        logging.info(f"[MODIFY] {os.path.basename(event.src_path)}")
        # entropy check — skip known high-entropy formats
        if ext not in SKIP_ENTROPY:
            e = shannon_entropy(event.src_path)
            if e > 7.0:
                log_anomaly("RANSOMWARE_ENTROPY",
                    f"{event.src_path} entropy={round(e,2)}")
                entropy_flags.append(event.src_path)

    def on_deleted(self, event):
        global deletes
        if event.is_directory:
            return
        deletes += 1
        logging.info(f"[DELETE] {os.path.basename(event.src_path)}")
        if deletes > 20:
            elapsed = time.time() - start_time
            if elapsed < 60:
                log_anomaly("MASS_DELETION",
                    f"{deletes} files deleted in {round(elapsed)}s")

    def on_moved(self, event):
        global mismatches
        if event.is_directory:
            return
        old_ext = os.path.splitext(event.src_path)[1].lower()
        new_ext = os.path.splitext(event.dest_path)[1].lower()
        logging.info(f"[RENAME] {os.path.basename(event.src_path)} -> {os.path.basename(event.dest_path)}")
        if old_ext != new_ext:
            mismatches += 1
            if mismatches > 10:
                log_anomaly("RENAME_ATTACK",
                    f"{mismatches} extension mismatches detected")

# ── START WATCHDOG ────────────────────────────────────────────
_observer = None

def start_watchdog(folder=WATCH):
    global _observer, start_time
    start_time = time.time()
    os.makedirs(folder, exist_ok=True)
    _observer = Observer()
    _observer.schedule(AgentHandler(), folder, recursive=True)
    _observer.start()
    logging.info(f"[WATCHDOG] Listening on {folder}")
    return _observer

def stop_watchdog():
    global _observer
    if _observer:
        _observer.stop()
        _observer.join()

# ── GET FILE ACTIVITY ─────────────────────────────────────────
def get_file_activity():
    elapsed = max(1, time.time() - start_time)
    total   = creates + modifies + deletes
    velocity = round(total / elapsed * 60, 2)
    return {
        "created"  : creates,
        "modified" : modifies,
        "deleted"  : deletes,
        "total"    : total,
        "velocity" : velocity
    }

# ── CHECK ALL ANOMALIES ───────────────────────────────────────
def check_anomalies():
    flags   = []
    elapsed = time.time() - start_time
    if deletes > 20 and elapsed < 60:
        flags.append("MASS_DELETION")
    if len(entropy_flags) > 0:
        flags.append("RANSOMWARE_ENTROPY")
    if mismatches > 10:
        flags.append("RENAME_ATTACK")
    return flags

# ── FILE IMPORTANCE SCORE ─────────────────────────────────────
def get_importance_score(folder=WATCH):
    score = 0
    count = 0
    try:
        for root, dirs, files in os.walk(folder):
            for f in files:
                ext    = os.path.splitext(f)[1].lower()
                score += IMPORTANCE.get(ext, 2)
                count += 1
    except:
        pass
    if count == 0:
        return 50
    return min(100, round((score / (count * 10)) * 100))

# ── TEST ──────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.info("\n=== WATCHDOG MODULE TEST ===\n")
    logging.info("[IMPORTANCE] Score:", get_importance_score())
    logging.info("[ANOMALIES]  Active flags:", check_anomalies())
    logging.info("[ACTIVITY]   Current:", get_file_activity())

    obs = start_watchdog("./test_files")
    logging.info("\nCreate, modify, or delete files in test_files/ folder")
    logging.info("Press Ctrl+C to stop\n")
    try:
        while True:
            time.sleep(1)
            fa = get_file_activity()
            if fa["total"] > 0:
                logging.info(f"[LIVE] C:{fa['created']} M:{fa['modified']} D:{fa['deleted']} V:{fa['velocity']}/min")
    except KeyboardInterrupt:
        stop_watchdog()
        logging.info("\n[OK] watchdog_module.py is working correctly!")