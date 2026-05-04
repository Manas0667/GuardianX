# monitor.py — System Metrics + Self-Monitoring
# Author: Goldy Pandey (Roll: 2415000607)
# MENTOR CHANGES:
#   - Suggestion 1: Track open/active process files → give higher backup priority
#   - Suggestion 8: System does its OWN monitoring — CloudWatch is secondary only
#   - System log is stored in DB first, CloudWatch second
# BTech CSE | Section 2CC | Group 31

import time
import json
import os
import psutil
import boto3
import logging
import logging.handlers
from pathlib import Path
from botocore.exceptions import ClientError

from config import AWS_REGION, USE_AWS, LOCAL_LOG_DIR

# ── Setup Python logging (mentor suggestion 5: capture system logs) ──────────
os.makedirs(LOCAL_LOG_DIR, exist_ok=True)

_logger = logging.getLogger('guardianx')
_logger.setLevel(logging.DEBUG)

# File handler — rotating daily logs (backed up to S3)
_file_handler = logging.handlers.TimedRotatingFileHandler(
    filename=os.path.join(LOCAL_LOG_DIR, 'agent.log'),
    when='midnight',
    backupCount=7,        # keep 7 days locally
    encoding='utf-8'
)
_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
_logger.addHandler(_file_handler)

# Console handler
_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
_logger.addHandler(_console)


def log(level, message, module='monitor'):
    """
    MENTOR SUGGESTION 8 — Self-monitoring.
    The SYSTEM stores its own logs in:
    1. Local log file (always — works without internet)
    2. RDS system_log table (always — works without CloudWatch)
    3. CloudWatch Logs (secondary — nice to have, not required)
    """
    getattr(_logger, level.lower(), _logger.info)(f"[{module}] {message}")

    # Store in RDS system_log (primary monitoring)
    try:
        from Backend.database import insert_system_log
        insert_system_log(level.upper(), message, module)
    except Exception:
        pass  # never crash because of logging


# ── CloudWatch Logs (secondary — mentor said system should do own monitoring) ─
_cw_logs    = None
_cw_stream  = f'monitor-{int(time.time())}'
_cw_seq     = None
_CW_GROUP   = '/guardianx/monitor'

def _setup_cloudwatch_logs():
    global _cw_logs
    if not USE_AWS:
        return
    try:
        _cw_logs = boto3.client('logs', region_name=AWS_REGION)
        try:
            _cw_logs.create_log_group(logGroupName=_CW_GROUP)
            _cw_logs.put_retention_policy(logGroupName=_CW_GROUP, retentionInDays=30)
        except ClientError:
            pass
        try:
            _cw_logs.create_log_stream(logGroupName=_CW_GROUP, logStreamName=_cw_stream)
        except ClientError:
            pass
    except Exception as e:
        log('WARN', f"CloudWatch Logs unavailable: {e} — using local logs only")
        _cw_logs = None


def _push_to_cloudwatch(message: dict):
    """Push to CloudWatch AFTER local storage. Secondary only."""
    global _cw_seq
    if _cw_logs is None:
        return
    try:
        kwargs = {
            'logGroupName': _CW_GROUP,
            'logStreamName': _cw_stream,
            'logEvents': [{'timestamp': int(time.time() * 1000), 'message': json.dumps(message)}]
        }
        if _cw_seq:
            kwargs['sequenceToken'] = _cw_seq
        resp    = _cw_logs.put_log_events(**kwargs)
        _cw_seq = resp.get('nextSequenceToken')
    except Exception:
        pass  # CloudWatch failure must not affect the agent


# ═══════════════════════════════════════════════════════════════════════════════
# SUGGESTION 1 — Track actively running process files
# ═══════════════════════════════════════════════════════════════════════════════

def get_active_process_files():
    """
    MENTOR SUGGESTION 1: "Backup unka lenge jo operation perform ho raha hai"
    Returns set of file paths currently open by running processes.
    These files get highest importance in backup (override to score 10).
    """
    active_files = set()
    try:
        for proc in psutil.process_iter(['pid', 'name', 'open_files']):
            try:
                ofiles = proc.info.get('open_files') or []
                for f in ofiles:
                    if hasattr(f, 'path') and f.path:
                        active_files.add(f.path)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        log('DEBUG', f"Process file scan: {e}")
    return active_files


def get_running_python_scripts():
    """
    Specifically find which .py files are currently running.
    If agent.py is running → back up agent.py with priority.
    """
    running = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd = proc.info.get('cmdline') or []
                for part in cmd:
                    if part.endswith('.py') and os.path.isfile(part):
                        running.append(os.path.abspath(part))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        log('DEBUG', f"Python script scan: {e}")
    return running


# ═══════════════════════════════════════════════════════════════════════════════
# SUGGESTION 8 — Self-contained system monitoring
# Agent computes everything locally. CloudWatch gets data as a PUSH (secondary).
# ═══════════════════════════════════════════════════════════════════════════════

_prev_write_bytes = 0
_prev_write_time  = 0.0
_write_baseline   = 1.0  # MB/s baseline


def _get_write_speed_mbps():
    global _prev_write_bytes, _prev_write_time
    try:
        stats = psutil.disk_io_counters()
        now   = time.time()
        speed = 0.0
        if _prev_write_time > 0:
            elapsed = now - _prev_write_time
            if elapsed > 0:
                speed = (stats.write_bytes - _prev_write_bytes) / elapsed / (1024 * 1024)
        _prev_write_bytes = stats.write_bytes
        _prev_write_time  = now
        return round(speed, 3)
    except Exception:
        return 0.0


def collect_system_metrics() -> dict:
    """
    PRIMARY monitoring — runs entirely locally.
    The system monitors ITSELF. CloudWatch is just a display layer.

    Returns complete metrics dict with:
    - Standard disk/cpu/ram
    - Active process file count (mentor suggestion 1)
    - Write speed for burst detection
    """
    disk          = psutil.disk_usage('/')
    cpu           = psutil.cpu_percent(interval=1)
    ram           = psutil.virtual_memory()
    write_speed   = _get_write_speed_mbps()
    active_files  = get_active_process_files()
    running_pys   = get_running_python_scripts()

    metrics = {
        'disk_pct'        : round(disk.percent, 1),
        'free_gb'         : round(disk.free / (1024**3), 2),
        'cpu_pct'         : round(cpu, 1),
        'ram_pct'         : round(ram.percent, 1),
        'ram_used_gb'     : round(ram.used / (1024**3), 2),
        'write_mbps'      : write_speed,
        'open_files_count': len(active_files),
        'running_py_files': running_pys,
        'active_files'    : list(active_files)[:20],  # first 20 for storage
        'timestamp'       : time.time()
    }

    # ── STEP 1: Write to RDS (primary — always works) ─────────────
    try:
        from Backend.database import insert_activity_log
        insert_activity_log(
            cpu_pct     = metrics['cpu_pct'],
            ram_pct     = metrics['ram_pct'],
            disk_pct    = metrics['disk_pct'],
            free_gb     = metrics['free_gb'],
            write_speed = metrics['write_mbps'],
            open_files  = metrics['open_files_count']
        )
    except Exception as e:
        log('ERROR', f"RDS write failed: {e}")

    # ── STEP 2: Write to local log file (always works offline) ─────
    log('INFO',
        f"CPU:{metrics['cpu_pct']}% RAM:{metrics['ram_pct']}% "
        f"Disk:{metrics['disk_pct']}% OpenFiles:{metrics['open_files_count']} "
        f"Write:{metrics['write_mbps']}MB/s ActivePy:{len(running_pys)}",
        module='monitor')

    # ── STEP 3: Push to CloudWatch (secondary — nice to have) ──────
    if USE_AWS:
        try:
            cw = boto3.client('cloudwatch', region_name=AWS_REGION)
            cw.put_metric_data(
                Namespace='GuardianX/System',
                MetricData=[
                    {'MetricName': 'CPU',       'Value': metrics['cpu_pct'],        'Unit': 'Percent'},
                    {'MetricName': 'RAM',        'Value': metrics['ram_pct'],        'Unit': 'Percent'},
                    {'MetricName': 'DiskUsage',  'Value': metrics['disk_pct'],       'Unit': 'Percent'},
                    {'MetricName': 'WriteSpeed', 'Value': metrics['write_mbps'],     'Unit': 'None'},
                    {'MetricName': 'OpenFiles',  'Value': metrics['open_files_count'],'Unit': 'Count'},
                ]
            )
        except Exception as e:
            log('DEBUG', f"CloudWatch push skipped: {e} — data already in RDS")

    return metrics


def check_write_burst(current_speed: float) -> bool:
    """Check if write speed is 5x above baseline — anomaly detector 4."""
    global _write_baseline
    is_burst = False
    if _write_baseline > 0.1 and current_speed / _write_baseline >= 5:
        is_burst = True
        log('WARN', f"Write burst: {current_speed:.1f}MB/s ({current_speed/_write_baseline:.1f}x baseline)")
    # Update rolling baseline
    _write_baseline = 0.9 * _write_baseline + 0.1 * max(current_speed, 0.1)
    return is_burst


def start_monitor_loop(interval_seconds: int = 60):
    """Background monitoring loop — self-contained, no CloudWatch dependency."""
    _setup_cloudwatch_logs()
    log('INFO', f"Monitor started — interval {interval_seconds}s | Mode: local+RDS+CW(secondary)")
    while True:
        try:
            collect_system_metrics()
        except Exception as e:
            log('ERROR', f"Monitor loop error: {e}")
        time.sleep(interval_seconds)


if __name__ == '__main__':
    _setup_cloudwatch_logs()
    log('INFO', "Running single metrics collection...")
    m = collect_system_metrics()
    print(f"\nActive process files: {m['open_files_count']}")
    print(f"Running .py scripts:  {m['running_py_files']}")
    print(f"Disk: {m['disk_pct']}%  CPU: {m['cpu_pct']}%  RAM: {m['ram_pct']}%")