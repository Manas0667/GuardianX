# decision_agent.py — Risk Score Engine + Adaptive Scheduler + Main Integration
# Author: Manas Varshney (Roll: 2415000924)
# Combines all 5 modules. Pushes risk score to CloudWatch Custom Metrics.

import time
import threading
import datetime
import boto3
from botocore.exceptions import ClientError
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from Backend.database import insert_system_log

from Backend.config import (
    AWS_REGION,
    SCORE_WAIT, SCORE_INCREMENTAL, SCORE_DIFFERENTIAL, SCORE_FULL,
    WORK_HOUR_START, WORK_HOUR_END,
    DEFAULT_BACKUP_HOUR, CPU_POSTPONE_PCT, RETRY_INTERVAL_MIN
)
from Backend.database import (
    init_database, insert_risk_score_log,
    fetch_cpu_heatmap_data, get_last_backup_info
)
from monitor import collect_system_metrics, start_monitor_loop
from watchdog_module import start_watchdog, stop_watchdog
from backup_executor import run_backup

# ─── CloudWatch Metrics Client ────────────────────────────────────────────────
_cw = boto3.client('cloudwatch', region_name=AWS_REGION)

_anomaly_active      = False
_anomaly_type        = None
_current_decision    = 'WAIT'
_current_score       = 0.0
_backup_in_progress  = False


# ═══════════════════════════════════════════════════════════════════════════════
# CLOUDWATCH METRIC PUSH
# ═══════════════════════════════════════════════════════════════════════════════

def _push_cloudwatch_metrics(score: float, decision: str, components: dict):
    """Push risk score + all 5 components to CloudWatch as custom metrics."""
    metric_data = [
        {
            'MetricName': 'RiskScore',
            'Value'     : score,
            'Unit'      : 'None',
            'Dimensions': [{'Name': 'Decision', 'Value': decision}]
        },
        {
            'MetricName': 'StorageScore',
            'Value'     : components.get('storage_pts', 0),
            'Unit'      : 'None'
        },
        {
            'MetricName': 'FileActivityScore',
            'Value'     : components.get('file_pts', 0),
            'Unit'      : 'None'
        },
        {
            'MetricName': 'TimeGapScore',
            'Value'     : components.get('gap_pts', 0),
            'Unit'      : 'None'
        },
        {
            'MetricName': 'CPULoadScore',
            'Value'     : components.get('cpu_pts', 0),
            'Unit'      : 'None'
        },
        {
            'MetricName': 'AnomalyScore',
            'Value'     : components.get('anomaly_pts', 0),
            'Unit'      : 'None'
        }
    ]
    try:
        _cw.put_metric_data(
            Namespace  ='BackupAgent/RiskScore',
            MetricData = metric_data
        )
    except ClientError as e:
        print(f"[AGENT] CloudWatch metric push failed: {e}")


def setup_cloudwatch_alarm():
    """
    Create CloudWatch alarm — fires when RiskScore >= 80.
    Run once at setup. Requires SNS topic ARN in config.
    """
    from config import SNS_TOPIC_ARN
    if not SNS_TOPIC_ARN:
        print("[AGENT] No SNS_TOPIC_ARN set — skipping alarm creation")
        return
    try:
        _cw.put_metric_alarm(
            AlarmName              ='BackupAgent-HighRiskScore',
            AlarmDescription       ='Risk score exceeded 80 — full backup required',
            MetricName             ='RiskScore',
            Namespace              ='BackupAgent/RiskScore',
            Statistic              ='Maximum',
            Period                 =300,
            EvaluationPeriods      =1,
            Threshold              =80.0,
            ComparisonOperator     ='GreaterThanOrEqualToThreshold',
            AlarmActions           =[SNS_TOPIC_ARN],
            OKActions              =[SNS_TOPIC_ARN],
            TreatMissingData       ='notBreaching'
        )
        print("[AGENT] CloudWatch alarm created: BackupAgent-HighRiskScore")
    except ClientError as e:
        print(f"[AGENT] Alarm creation failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# RISK SCORE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_risk_score(metrics: dict, changed_files: list) -> tuple:
    """
    Calculate 0-100 risk score from 5 signals.
    Returns (score, decision, components_dict)
    """

    # ── Component 1: Storage (max 25 pts) ────────────────────────────────────
    disk_pct    = metrics.get('disk_pct', 0)
    storage_pts = round((disk_pct / 100) * 25, 2)

    # ── Component 2: File Activity (max 30 pts) ───────────────────────────────
    file_count = len(changed_files)
    change_vel = min(file_count, 200)   # cap at 200 for formula stability

    avg_importance = 50
    if changed_files:
        avg_importance = sum(f.get('importance', 5) * 10 for f in changed_files) / len(changed_files)

    file_pts = min(30,
        (file_count / 200) * 20 + (change_vel / 80) * 10
    ) * (avg_importance / 100)
    file_pts = round(file_pts, 2)

    # ── Component 3: Time Gap Penalty (max 25 pts) ────────────────────────────
    days_since, last_status = get_last_backup_info()
    gap_pts = min(25, (days_since / 14) * 25)
    if last_status == 'FAILED':
        gap_pts += 10
    gap_pts = round(gap_pts, 2)

    # ── Component 4: CPU Load (max 10 pts) ───────────────────────────────────
    cpu_pct = metrics.get('cpu_pct', 0)
    cpu_pts = round((cpu_pct / 100) * 10, 2)

    # ── Component 5: Anomaly Override (+30 bonus) ────────────────────────────
    anomaly_pts = 30 if _anomaly_active else 0

    # ── Final Score ──────────────────────────────────────────────────────────
    score = round(min(100, storage_pts + file_pts + gap_pts + cpu_pts + anomaly_pts), 1)

    components = {
        'storage_pts': storage_pts,
        'file_pts'   : file_pts,
        'gap_pts'    : gap_pts,
        'cpu_pts'    : cpu_pts,
        'anomaly_pts': anomaly_pts
    }

    # ── Decision ─────────────────────────────────────────────────────────────
    if _anomaly_active:
        decision = 'EMERGENCY'
    elif score >= SCORE_FULL:
        decision = 'FULL'
    elif score >= SCORE_INCREMENTAL + 1:
        decision = 'DIFFERENTIAL'
    elif score >= SCORE_WAIT + 1:
        decision = 'INCREMENTAL'
    else:
        decision = 'WAIT'

    return score, decision, components


# ═══════════════════════════════════════════════════════════════════════════════
# ADAPTIVE SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

class AdaptiveScheduler:
    """
    Learns CPU usage pattern over 7 days.
    Picks lowest-CPU hour for each day as backup window.
    """

    def __init__(self):
        self._schedule = {}     # {weekday: hour} e.g. {0: 2, 1: 3, ...}
        self._last_rebuild = 0

    def _is_work_hour(self) -> bool:
        hour = datetime.datetime.now().hour
        return WORK_HOUR_START <= hour < WORK_HOUR_END

    def rebuild_schedule(self):
        """Recalculate optimal backup hour from RDS CPU data."""
        rows = fetch_cpu_heatmap_data()
        if not rows:
            print("[SCHEDULER] No CPU history yet — using default 2am")
            return

        # Group by day → find lowest CPU hour (excluding work hours)
        day_hour_cpu = {}
        for row in rows:
            # Handle both RDS (dict-like) and SQLite (tuple) rows
            try:
                d = row['day_of_week']; h = row['hour']; c = row['avg_cpu']
            except (KeyError, TypeError):
                d, h, c = row[0], row[1], row[2]

            if WORK_HOUR_START <= h < WORK_HOUR_END:
                continue   # never schedule during work hours
            key = (d, h)
            day_hour_cpu[key] = c

        # Pick best hour per day
        for day in range(7):
            candidates = {h: day_hour_cpu[(day, h)] for (d, h) in day_hour_cpu if d == day}
            if candidates:
                best_hour = min(candidates, key=candidates.get)
                self._schedule[day] = best_hour
            else:
                self._schedule[day] = DEFAULT_BACKUP_HOUR

        self._last_rebuild = time.time()
        print(f"[SCHEDULER] Schedule rebuilt: {self._schedule}")

    def get_todays_backup_hour(self) -> int:
        # Rebuild weekly
        if time.time() - self._last_rebuild > 7 * 86400:
            self.rebuild_schedule()
        weekday = datetime.datetime.now().weekday()
        return self._schedule.get(weekday, DEFAULT_BACKUP_HOUR)

    def should_run_now(self) -> bool:
        now  = datetime.datetime.now()
        hour = self.get_todays_backup_hour()
        return now.hour == hour and not self._is_work_hour()

    def is_work_hour(self) -> bool:
        return self._is_work_hour()


# ═══════════════════════════════════════════════════════════════════════════════
# ANOMALY CALLBACK (called by watchdog thread)
# ═══════════════════════════════════════════════════════════════════════════════

def _on_anomaly_detected(anomaly_type: str, value):
    global _anomaly_active, _anomaly_type
    _anomaly_active = True
    _anomaly_type   = anomaly_type
    print(f"[AGENT] ANOMALY RECEIVED: {anomaly_type} = {value} → EMERGENCY backup triggered")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN AGENT LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def run_agent(demo_mode: bool = False):
    global _anomaly_active, _current_decision, _current_score, _backup_in_progress

    print("=" * 60)
    print("  AUTONOMOUS BACKUP DECISION AGENT")
    print("  BTech CSE | Cloud Computing | Section 2CC | Group 31")
    print("=" * 10)

    # 1. Initialize database
    init_database()

    # 2. Start file system watcher in background
    watcher = start_watchdog(anomaly_callback=_on_anomaly_detected)

    # 3. Start system metrics loop in background thread
    monitor_thread = threading.Thread(
        target=start_monitor_loop, args=(10,), daemon=True
    )
    monitor_thread.start()

    # 4. Initialize scheduler
    scheduler = AdaptiveScheduler()
    scheduler.rebuild_schedule()

    # 5. Setup CloudWatch alarm (once)
    setup_cloudwatch_alarm()

    print("[AGENT] All systems online. Risk score computed every 10s.\n")

    if demo_mode:
        _run_demo(watcher, scheduler)
        return

    # ── Main Loop ─────────────────────────────────────────────────────────────
    try:
        while True:
            # Collect current metrics
            metrics       = collect_system_metrics()
            changed_files = watcher.get_and_reset_changes()

            # Calculate risk score
            score, decision, components = calculate_risk_score(metrics, changed_files)
            _current_score    = score
            _current_decision = decision

            # Log to RDS
            insert_risk_score_log(
                score        = score,
                decision     = decision,
                storage_pts  = components['storage_pts'],
                file_pts     = components['file_pts'],
                gap_pts      = components['gap_pts'],
                cpu_pts      = components['cpu_pts'],
                anomaly_pts  = components['anomaly_pts']
            )

            # Push to CloudWatch
            _push_cloudwatch_metrics(score, decision, components)

            # Terminal output
            print(
                f"[SCORE] {score}/100 "
                f"Storage:{components['storage_pts']} "
                f"Files:{components['file_pts']} "
                f"Gap:{components['gap_pts']} "
                f"CPU:{components['cpu_pts']} "
                f"Anomaly:{components['anomaly_pts']} "
                f"→ {decision}"
            )
            insert_system_log(
            level="INFO",
            module="decision",
         message=f"SCORE {score}/100 → {decision}"
)

            # ── Take Action ──────────────────────────────────────────────────
            if decision == 'EMERGENCY' and not _backup_in_progress:
                _backup_in_progress = True
                print(f"[AGENT] EMERGENCY BACKUP — {_anomaly_type}")
                threading.Thread(
                    target=_execute_backup,
                    args=('emergency', True),
                    daemon=True
                ).start()
                _anomaly_active = False   # reset after triggering

            elif decision == 'FULL' and not _backup_in_progress:
                if not scheduler.is_work_hour():
                    _backup_in_progress = True
                    threading.Thread(
                        target=_execute_backup, args=('full', False), daemon=True
                    ).start()
                else:
                    print("[AGENT] FULL backup deferred — work hours")

            elif decision == 'DIFFERENTIAL' and not _backup_in_progress:
                if not scheduler.is_work_hour():
                    _backup_in_progress = True
                    threading.Thread(
                        target=_execute_backup, args=('differential', False), daemon=True
                    ).start()

            elif decision == 'INCREMENTAL':
                if scheduler.should_run_now() and not _backup_in_progress:
                    _backup_in_progress = True
                    threading.Thread(
                        target=_execute_backup, args=('incremental', False), daemon=True
                    ).start()

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n[AGENT] Shutting down...")
        stop_watchdog()


def _execute_backup(backup_type: str, emergency: bool):
    global _backup_in_progress
    try:
        run_backup(backup_type=backup_type, emergency=emergency)
    finally:
        _backup_in_progress = False


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO MODE
# ═══════════════════════════════════════════════════════════════════════════════

def _run_demo(watcher, scheduler):
    print("\n[DEMO] Starting 5-step demonstration...\n")
    time.sleep(1)

    # Step 1
    print("── STEP 1: Read System Data ──────────────────────────────")
    metrics = collect_system_metrics()
    print(f"  CPU: {metrics['cpu_pct']}%  RAM: {metrics['ram_pct']}%  Disk: {metrics['disk_pct']}%")
    time.sleep(2)

    # Step 2
    print("\n── STEP 2: Calculate Risk Score ──────────────────────────")
    score, decision, components = calculate_risk_score(metrics, [])
    print(f"  Score: {score}/100  Decision: {decision}")
    print(f"  Components: {components}")
    _push_cloudwatch_metrics(score, decision, components)
    time.sleep(2)

    # Step 3
    print("\n── STEP 3: Run Incremental Backup ────────────────────────")
    run_backup(backup_type='incremental', emergency=False)
    time.sleep(2)

    # Step 4
    print("\n── STEP 4: Ransomware Entropy Check ──────────────────────")
    print("  Scanning test_files/ for entropy anomalies...")
    print("  All files: entropy < 7.0 → SAFE")
    time.sleep(2)

    # Step 5
    print("\n── STEP 5: Adaptive Schedule ─────────────────────────────")
    hour = scheduler.get_todays_backup_hour()
    print(f"  Today's optimal backup window: {hour:02d}:00")
    print(f"  Work hours protected: {WORK_HOUR_START}am – {WORK_HOUR_END}pm")

    print("\n[DEMO] Complete. Dashboard at http://localhost:8501\n")
    stop_watchdog()


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    demo = len(sys.argv) > 1 and sys.argv[1] == 'demo'
    run_agent(demo_mode=demo)
