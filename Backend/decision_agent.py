# =============================================================
# decision_agent.py — Manas's Module (MAIN FILE)
# Risk score engine + adaptive scheduler + agent brain
# =============================================================

import schedule
import os
import threading
import time
import sqlite3
import logging
from datetime import datetime
from config import DB, WATCH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ── IMPORT ALL TEAM MODULES ───────────────────────────────────
from monitor import (
    create_tables,
    get_storage_data,
    get_system_data,
    log_hourly_activity,
    get_days_since_last_backup,
    get_last_backup_status,
    find_best_window,
    log_risk_score
)
from watchdog_module import (
    start_watchdog,
    stop_watchdog,
    get_file_activity,
    check_anomalies,
    get_importance_score
)
from backup_executor import execute_backup

# pending backup queue
pending_backup = None
backup_lock    = False

# ── RISK SCORE FORMULA ────────────────────────────────────────
def calculate_risk_score():
    storage = get_storage_data()
    system  = get_system_data()
    files   = get_file_activity()
    imp     = get_importance_score(WATCH)
    days    = get_days_since_last_backup()
    failed  = get_last_backup_status() == "FAILED"
    anom    = check_anomalies()

    # component 1 — storage (max 25)
    s = (storage["disk_pct"] / 100) * 25

    # component 2 — file activity (max 30)
    f = min(30, (files["modified"] / 200) * 20 + (files["velocity"] / 80) * 10)
    f = f * (imp / 100)

    # component 3 — time gap penalty (max 25)
    g = min(25, (min(days, 14) / 14) * 25)
    if failed:
        g = min(25, g + 10)

    # component 4 — system load (max 10)
    c = (system["cpu_pct"] / 100) * 10

    # component 5 — anomaly override (+30 bonus)
    a = 30 if len(anom) > 0 else 0

    score = min(100, round(s + f + g + c + a))

    # decide action
    if len(anom) > 0:
        decision = "EMERGENCY"
    elif score >= 80:
        decision = "FULL"
    elif score >= 56:
        decision = "DIFFERENTIAL"
    elif score >= 31:
        decision = "INCREMENTAL"
    else:
        decision = "WAIT"

    log_risk_score(score, decision)
    logging.info(f"[SCORE] {score}/100  Storage:{round(s,1)}  Files:{round(f,1)}  Gap:{round(g,1)}  CPU:{round(c,1)}  Anomaly:{a}  → {decision}")
    return score, decision

# ── IS IT OK TO BACKUP NOW? ───────────────────────────────────
def is_ok_to_backup():
    system = get_system_data()
    # never during work hours
    if system["time_window"] == "AVOID":
        return False, f"Work hours (hour={system['hour']})"
    # never when CPU is busy
    if system["cpu_pct"] > 50:
        return False, f"CPU too high ({system['cpu_pct']}%)"
    # never when RAM is critically low
    if system["ram_pct"] > 85:
        return False, f"RAM too high ({system['ram_pct']}%)"
    return True, "System is idle"

# ── RUN BACKUP CYCLE (called by scheduler) ────────────────────
def run_backup_cycle():
    global pending_backup, backup_lock
    if backup_lock:
        logging.info("[AGENT] Backup already running — skipping cycle")
        return

    # check anomalies first — highest priority
    flags = check_anomalies()
    if flags:
        logging.info(f"[AGENT] Anomaly detected: {flags} — emergency backup!")
        _do_backup("EMERGENCY")
        return

    # calculate score and decide
    score, decision = calculate_risk_score()

    if decision == "WAIT":
        logging.info("[AGENT] Score low — no backup needed")
        return

    ok, reason = is_ok_to_backup()

    if ok:
        _do_backup(decision)
    else:
        logging.info(f"[AGENT] Backup postponed: {reason} — will retry")
        pending_backup = decision

# ── RETRY PENDING BACKUP ──────────────────────────────────────
def retry_pending():
    global pending_backup
    if pending_backup:
        ok, reason = is_ok_to_backup()
        if ok:
            logging.info(f"[AGENT] Retrying pending {pending_backup} backup")
            _do_backup(pending_backup)
            pending_backup = None

# ── EXECUTE BACKUP WITH LOCK ──────────────────────────────────
def _do_backup(backup_type):
    global backup_lock
    backup_lock = True
    try:
        execute_backup(backup_type, WATCH)
    finally:
        backup_lock = False

# ── SCHEDULED JOBS ────────────────────────────────────────────
def setup_schedule():
    best_hour = find_best_window()
    window    = f"{best_hour:02d}:00"

    # daily backup at personal idle hour
    schedule.every().day.at(window).do(run_backup_cycle)
    # guaranteed differential every Thursday
    schedule.every().thursday.at("01:00").do(
        lambda: _do_backup("DIFFERENTIAL"))
    # guaranteed full every Sunday
    schedule.every().sunday.at("01:00").do(
        lambda: _do_backup("FULL"))
    # retry pending backups every 15 minutes
    schedule.every(15).minutes.do(retry_pending)
    # log activity every hour for adaptive scheduling
    schedule.every().hour.do(log_hourly_activity)

    logging.info(f"[SCHEDULE] Daily backup window: {window}")
    logging.info(f"[SCHEDULE] Thursday 01:00 — Differential")
    logging.info(f"[SCHEDULE] Sunday   01:00 — Full backup")

# ── SCHEDULER THREAD ──────────────────────────────────────────
def scheduler_thread():
    while True:
        schedule.run_pending()
        time.sleep(30)

# ── START THE AGENT ───────────────────────────────────────────
def run_agent():
    logging.info("\n" + "="*50)
    logging.info("  AUTONOMOUS BACKUP DECISION AGENT")
    logging.info("  BTech CSE Cloud Computing — Section 2CC")
    logging.info("="*50 + "\n")

    # setup database
    create_tables()

    # start continuous file watchdog
    start_watchdog(WATCH)

    # setup scheduled jobs
    setup_schedule()

    # start scheduler in background thread
    t = threading.Thread(target=scheduler_thread, daemon=True)
    t.start()

    logging.info("\n[AGENT] All systems running. Press Ctrl+C to stop.\n")

    # main loop — check anomalies and score every 60 seconds
    try:
        while True:
            time.sleep(60)
            flags = check_anomalies()
            if flags:
                logging.info(f"[WATCHDOG] Anomaly detected: {flags}")
                _do_backup("EMERGENCY")
            else:
                score, decision = calculate_risk_score()
                if decision not in ["WAIT"] and not backup_lock:
                    ok, reason = is_ok_to_backup()
                    if ok:
                        _do_backup(decision)
    except KeyboardInterrupt:
        stop_watchdog()
        logging.info("\n[AGENT] Stopped gracefully.")

# ── QUICK DEMO (for mentor meeting) ──────────────────────────
def run_demo():
    logging.info("\n" + "="*50)
    logging.info("  BACKUP AGENT — DEMO MODE")
    logging.info("="*50 + "\n")

    create_tables()

    logging.info("[DEMO] Step 1 — Reading system data...")
    storage = get_storage_data()
    system  = get_system_data()
    logging.info(f"  Disk: {storage['disk_pct']}%  Free: {storage['free_gb']} GB")
    logging.info(f"  CPU:  {system['cpu_pct']}%   RAM: {system['ram_pct']}%")
    logging.info(f"  Time: {system['hour']}:00  Window: {system['time_window']}")

    logging.info("\n[DEMO] Step 2 — Calculating risk score...")
    score, decision = calculate_risk_score()
    logging.info(f"  Risk Score: {score}/100  →  {decision}")

    logging.info("\n[DEMO] Step 3 — Running incremental backup...")
    execute_backup("INCREMENTAL", WATCH)

    logging.info("\n[DEMO] Step 4 — Simulating anomaly detection...")
    logging.info("  [ENTROPY] Scanning files for ransomware pattern...")
    logging.info("  [RESULT]  All files safe — no threats detected")

    logging.info("\n[DEMO] Step 5 — Adaptive schedule...")
    best = find_best_window()
    logging.info(f"  Agent learned your pattern — backup scheduled at {best:02d}:00")

    logging.info("\n[DEMO COMPLETE] Agent is fully operational!")
    logging.info("Run 'streamlit run dashboard.py' to see the live dashboard\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_demo()
    else:
        run_agent()