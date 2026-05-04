# watchdog_module.py — File System Event Monitor + Anomaly Detector
# Author: Chahat Jindal (Roll: 2415000464)
# Detects: file events, ransomware entropy, mass delete, extension mismatch,
#          write burst, odd-hour activity → RDS anomaly_log + SNS alerts

import os
import time
import math
import threading
import boto3
from collections import defaultdict, deque
from botocore.exceptions import ClientError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import (
    AWS_REGION, SNS_TOPIC_ARN,
    ENTROPY_THRESHOLD, MASS_DELETE_THRESHOLD,
    EXTENSION_MISMATCH_MAX, WRITE_BURST_MULTIPLIER,
    ODD_HOUR_FILE_COUNT, HIGH_ENTROPY_WHITELIST,
    FILE_IMPORTANCE, WATCH_PATH
)
from Backend.database import insert_anomaly_log

# ─── SNS Client ──────────────────────────────────────────────────────────────
_sns = boto3.client('sns', region_name=AWS_REGION)


def _send_sns_alert(anomaly_type: str, details: str):
    """Send email/SMS alert via SNS when anomaly detected."""
    if not SNS_TOPIC_ARN:
        print(f"[SNS] No topic ARN configured — skipping alert for {anomaly_type}")
        return
    try:
        _sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f'BACKUP AGENT ALERT: {anomaly_type}',
            Message=(
                f"Autonomous Backup Agent detected a threat!\n\n"
                f"Anomaly Type : {anomaly_type}\n"
                f"Details      : {details}\n"
                f"Time         : {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Action       : Emergency snapshot triggered with S3 Object Lock\n"
                f"Check dashboard: http://localhost:8501"
            )
        )
        print(f"[SNS] Alert sent — {anomaly_type}")
    except ClientError as e:
        print(f"[SNS] Failed to send alert: {e}")


# ─── Shannon Entropy ─────────────────────────────────────────────────────────

def _calculate_entropy(filepath: str) -> float:
    """Calculate Shannon entropy of a file. Encrypted files score 7.0+."""
    try:
        with open(filepath, 'rb') as f:
            data = f.read(65536)   # read first 64KB only for speed
        if not data:
            return 0.0
        freq   = defaultdict(int)
        for byte in data:
            freq[byte] += 1
        length  = len(data)
        entropy = 0.0
        for count in freq.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)
        return round(entropy, 3)
    except (PermissionError, FileNotFoundError, OSError):
        return 0.0


def _get_importance(filepath: str) -> int:
    ext = os.path.splitext(filepath)[1].lower()
    return FILE_IMPORTANCE.get(ext, 0)


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

class BackupWatchdogHandler(FileSystemEventHandler):

    def __init__(self, anomaly_callback=None):
        super().__init__()
        self.anomaly_callback     = anomaly_callback   # called when anomaly found
        self.changed_files        = []                 # all events this cycle
        self.lock                 = threading.Lock()

        # Counters for anomaly detectors
        self._delete_times        = deque()            # timestamps of deletes
        self._rename_times        = deque()            # timestamps of extension mismatches
        self._write_baseline      = 1.0                # MB/s baseline
        self._odd_hour_count      = 0
        self._odd_hour_reset_time = time.time()

    # ── Event Callbacks ───────────────────────────────────────────────────────

    def on_created(self, event):
        if event.is_directory:
            return
        self._record_change(event.src_path, 'create')

    def on_modified(self, event):
        if event.is_directory:
            return
        self._record_change(event.src_path, 'modify')
        self._check_entropy(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        self._record_change(event.src_path, 'delete')
        self._check_mass_deletion()

    def on_moved(self, event):
        if event.is_directory:
            return
        self._record_change(event.dest_path, 'rename')
        self._check_extension_mismatch(event.src_path, event.dest_path)

    # ── Change Recorder ───────────────────────────────────────────────────────

    def _record_change(self, filepath: str, event_type: str):
        importance = _get_importance(filepath)
        if importance == 0:   # skip .tmp, .log
            return
        with self.lock:
            self.changed_files.append({
                'path'      : filepath,
                'event'     : event_type,
                'importance': importance,
                'time'      : time.time()
            })
        # Odd-hour check
        self._check_odd_hour_activity()

    def get_and_reset_changes(self):
        """Called by decision_agent every 60s to get changed files list."""
        with self.lock:
            files = list(self.changed_files)
            self.changed_files = []
        return files

    # ═══════════════════════════════════════════════════════════════════════════
    # ANOMALY DETECTOR 1 — Ransomware Entropy
    # ═══════════════════════════════════════════════════════════════════════════

    def _check_entropy(self, filepath: str):
        ext = os.path.splitext(filepath)[1].lower()
        if ext in HIGH_ENTROPY_WHITELIST:
            return   # skip .zip .gz .rar etc — high entropy by nature

        entropy = _calculate_entropy(filepath)
        if entropy >= ENTROPY_THRESHOLD:
            details = f"Entropy={entropy} on {os.path.basename(filepath)}"
            print(f"[ANOMALY] RANSOMWARE_ENTROPY — {details}")

            insert_anomaly_log(
                anomaly_type ='RANSOMWARE_ENTROPY',
                details      = details,
                filepath     = filepath,
                entropy_score= entropy,
                severity     ='CRITICAL'
            )
            _send_sns_alert('RANSOMWARE_ENTROPY', details)

            if self.anomaly_callback:
                self.anomaly_callback('RANSOMWARE_ENTROPY', entropy)

    # ═══════════════════════════════════════════════════════════════════════════
    # ANOMALY DETECTOR 2 — Mass Deletion
    # ═══════════════════════════════════════════════════════════════════════════

    def _check_mass_deletion(self):
        now = time.time()
        self._delete_times.append(now)
        # Remove timestamps older than 60 seconds
        while self._delete_times and (now - self._delete_times[0]) > 60:
            self._delete_times.popleft()

        count = len(self._delete_times)
        if count >= MASS_DELETE_THRESHOLD:
            details = f"{count} files deleted in 60 seconds"
            print(f"[ANOMALY] MASS_DELETION — {details}")

            insert_anomaly_log(
                anomaly_type='MASS_DELETION',
                details     = details,
                severity    ='CRITICAL'
            )
            _send_sns_alert('MASS_DELETION', details)
            self._delete_times.clear()   # reset counter after alert

            if self.anomaly_callback:
                self.anomaly_callback('MASS_DELETION', count)

    # ═══════════════════════════════════════════════════════════════════════════
    # ANOMALY DETECTOR 3 — Extension Mismatch (ransomware renaming files)
    # ═══════════════════════════════════════════════════════════════════════════

    def _check_extension_mismatch(self, src: str, dst: str):
        src_ext = os.path.splitext(src)[1].lower()
        dst_ext = os.path.splitext(dst)[1].lower()

        if src_ext == dst_ext:
            return   # normal rename — no extension change

        now = time.time()
        self._rename_times.append(now)
        while self._rename_times and (now - self._rename_times[0]) > 30:
            self._rename_times.popleft()

        count = len(self._rename_times)
        if count >= EXTENSION_MISMATCH_MAX:
            details = f"{count} files renamed with different extension in 30s ({src_ext}→{dst_ext})"
            print(f"[ANOMALY] EXTENSION_MISMATCH — {details}")

            insert_anomaly_log(
                anomaly_type='EXTENSION_MISMATCH',
                details     = details,
                severity    ='HIGH'
            )
            _send_sns_alert('EXTENSION_MISMATCH', details)
            self._rename_times.clear()

            if self.anomaly_callback:
                self.anomaly_callback('EXTENSION_MISMATCH', count)

    # ═══════════════════════════════════════════════════════════════════════════
    # ANOMALY DETECTOR 4 — Write Burst (handled in decision_agent using psutil)
    # ═══════════════════════════════════════════════════════════════════════════

    def check_write_burst(self, current_speed_mbps: float):
        """Called by decision_agent with current disk write speed."""
        if self._write_baseline < 0.1:
            self._write_baseline = max(current_speed_mbps, 0.1)
            return

        ratio = current_speed_mbps / self._write_baseline
        if ratio >= WRITE_BURST_MULTIPLIER:
            details = (f"Write speed {current_speed_mbps:.1f}MB/s is "
                       f"{ratio:.1f}x above baseline {self._write_baseline:.1f}MB/s")
            print(f"[ANOMALY] WRITE_BURST — {details}")

            insert_anomaly_log(
                anomaly_type='WRITE_BURST',
                details     = details,
                severity    ='HIGH'
            )
            _send_sns_alert('WRITE_BURST', details)

            if self.anomaly_callback:
                self.anomaly_callback('WRITE_BURST', ratio)

        # Update rolling baseline (slow exponential average)
        self._write_baseline = 0.9 * self._write_baseline + 0.1 * current_speed_mbps

    # ═══════════════════════════════════════════════════════════════════════════
    # ANOMALY DETECTOR 5 — Odd-Hour Activity
    # ═══════════════════════════════════════════════════════════════════════════

    def _check_odd_hour_activity(self):
        import datetime
        hour = datetime.datetime.now().hour
        if not (0 <= hour < 6):    # only midnight to 6am
            self._odd_hour_count = 0
            return

        now = time.time()
        # Reset counter every hour
        if now - self._odd_hour_reset_time > 3600:
            self._odd_hour_count     = 0
            self._odd_hour_reset_time = now

        self._odd_hour_count += 1

        if self._odd_hour_count >= ODD_HOUR_FILE_COUNT:
            details = f"{self._odd_hour_count} files changed at {hour:02d}:xx (odd hour)"
            print(f"[ANOMALY] ODD_HOUR_ACTIVITY — {details}")

            insert_anomaly_log(
                anomaly_type='ODD_HOUR_ACTIVITY',
                details     = details,
                severity    ='MEDIUM'
            )
            self._odd_hour_count = 0   # reset

            if self.anomaly_callback:
                self.anomaly_callback('ODD_HOUR_ACTIVITY', 0)


# ═══════════════════════════════════════════════════════════════════════════════
# START / STOP API
# ═══════════════════════════════════════════════════════════════════════════════

_observer = None
_handler  = None

def start_watchdog(watch_path: str = WATCH_PATH, anomaly_callback=None):
    """
    Start the file system watcher.
    Returns the handler so decision_agent can poll changed_files.
    """
    global _observer, _handler
    _handler  = BackupWatchdogHandler(anomaly_callback=anomaly_callback)
    _observer = Observer()
    _observer.schedule(_handler, path=watch_path, recursive=True)
    _observer.start()
    print(f"[WATCHDOG] Monitoring: {os.path.abspath(watch_path)}")
    return _handler

def stop_watchdog():
    global _observer
    if _observer:
        _observer.stop()
        _observer.join()
        print("[WATCHDOG] Stopped.")


if __name__ == '__main__':
    def demo_callback(anomaly_type, value):
        print(f"  CALLBACK RECEIVED: {anomaly_type} = {value}")

    handler = start_watchdog('.', anomaly_callback=demo_callback)
    print("Watching current folder. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(5)
            changes = handler.get_and_reset_changes()
            if changes:
                print(f"[TEST] {len(changes)} file events recorded")
    except KeyboardInterrupt:
        stop_watchdog()
