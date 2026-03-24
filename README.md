# GuardianX
# 🚀 GuardianX - Autonomous Backup Decision Agent

> “From reactive backups to intelligent decision-making — redefining data protection with automation and insight.”

---

## 🧠 Overview

The **Autonomous Backup Decision Agent** is an AI-inspired system that continuously monitors system activity, calculates risk levels, detects anomalies, and automatically decides the most appropriate backup strategy.

Instead of traditional static backups, this system uses a **dynamic, rule-based decision engine** to choose between:

- Full Backup  
- Differential Backup  
- Incremental Backup  
- No Backup (Wait)

It also provides a **real-time interactive dashboard** for monitoring, insights, and simulation.

---

## 🔥 Key Features

### 🧠 Intelligent Decision Engine
- Calculates risk score based on:
  - Disk usage  
  - CPU & RAM usage  
  - File activity  
  - Time since last backup  
  - Anomalies  

---

### 🚨 Anomaly Detection System
Detects suspicious behaviors such as:
- Mass file deletion  
- Ransomware-like entropy changes  
- File extension rename attacks  

---

### 📦 Automated Backup Execution
Automatically performs:
- Full Backup  
- Differential Backup  
- Incremental Backup  

Supports:
- Local storage  
- AWS S3 (optional)

---

### 📊 Interactive Dashboard (Streamlit)
- Real-time system monitoring  
- Risk score visualization  
- Backup history  
- Threat logs  
- AI decision insights  

---

### 🎯 What-If Simulation (Unique Feature)
Simulate system conditions like:
- CPU usage  
- File modifications  
- Days since last backup  

👉 Predicts:
- Risk Score  
- Backup Decision  

---

### 🧠 Adaptive Scheduler
- Learns system activity patterns  
- Chooses optimal backup timing  
- Uses CPU usage heatmap  

---

## 🏗️ Architecture
Frontend (Streamlit Dashboard)
↓
Backend (Decision Agent)
↓
Monitoring + Watchdog Modules
↓
SQLite Database (agent.db)
↓
Backup System (Local / AWS S3)

---

## 🛠️ Tech Stack

- **Python**
- **Streamlit** (Frontend UI)
- **SQLite** (Database)
- **psutil** (System Monitoring)
- **watchdog** (File Monitoring)
- **schedule** (Task Scheduling)
- **boto3** (AWS S3 Integration)
- **pandas**

---
