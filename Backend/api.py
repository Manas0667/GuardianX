from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# DB imports
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from Backend.database import (
    fetch_recent_risk_scores,
    fetch_backup_history,
    fetch_recent_anomalies,
    fetch_system_logs
)

app = FastAPI()

# ✅ CORS (frontend connection fix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# 1. STATUS (MOST IMPORTANT)
# ─────────────────────────────────────────
@app.get("/api/status")
def get_status():
    data = fetch_recent_risk_scores(1)

    if not data:
        return {
            "score": 0,
            "decision": "WAIT",
            "connected": False
        }

    latest = data[0]

    return {
        "score": latest["score"],
        "decision": latest["decision"],
        "storage_pts": latest.get("storage_pts", 0),
        "file_pts": latest.get("file_pts", 0),
        "gap_pts": latest.get("gap_pts", 0),
        "cpu_pts": latest.get("cpu_pts", 0),
        "anomaly_pts": latest.get("anomaly_pts", 0),
        "connected": True
    }

# ─────────────────────────────────────────
# 2. BACKUP HISTORY
# ─────────────────────────────────────────
@app.get("/api/history")
def get_history(limit: int = 20):
    return fetch_backup_history(limit)

# ─────────────────────────────────────────
# 3. ANOMALIES
# ─────────────────────────────────────────
@app.get("/api/anomalies")
def get_anomalies(limit: int = 50):
    return fetch_recent_anomalies(limit)

# ─────────────────────────────────────────
# 4. HEALTH CHECK
# ─────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok"}
from pydantic import BaseModel
from backup_executor import run_backup   # ya jo function tum use kar rahe ho

class BackupRequest(BaseModel):
    type: str

@app.post("/api/backup")
def trigger_backup(req: BackupRequest):
    try:
        run_backup(req.type)   # incremental / full / etc
        return {"status": "started", "type": req.type}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    

@app.get("/api/schedule")
def get_schedule():
    return [
        {
            "name": "Nightly",
            "cron": "30 20 * * *",
            "time": "2:00 AM",
            "type": "incremental",
            "enabled": True
        },
        {
            "name": "Thursday",
            "cron": "30 19 ? * THU",
            "time": "1:00 AM",
            "type": "differential",
            "enabled": True
        },
        {
            "name": "WeeklyFull",
            "cron": "30 19 ? * SUN",
            "time": "1:00 AM",
            "type": "full",
            "enabled": True
        }
    ]
@app.get("/api/logs")
def get_logs():
    return fetch_system_logs(50) 