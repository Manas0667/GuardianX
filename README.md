# 🛡️ GuardianX — Intelligent Backup & Ransomware Detection System

## 🚀 Overview

GuardianX is an intelligent cloud-based system that continuously monitors system activity, detects anomalies such as ransomware behavior, and automatically triggers secure backups.

It combines **real-time monitoring**, **risk-based decision making**, and **cloud automation (AWS)** to ensure data safety and system resilience.

---

## 🎯 Key Features

* 🔍 **Real-Time File Monitoring**

  * Detects suspicious file activity using entropy analysis
  * Identifies ransomware-like behavior instantly

* 🧠 **Risk-Based Decision Engine**

  * Calculates dynamic risk score
  * Triggers:

    * `WAIT` (safe)
    * `INCREMENTAL BACKUP`
    * `EMERGENCY BACKUP`

* ☁️ **Cloud Integration (AWS)**

  * **S3** → Backup storage
  * **RDS (PostgreSQL)** → Logs & history
  * **Lambda** → Serverless compression

* 📦 **Smart Backup System**

  * Local + Cloud backup support
  * Automatic compression
  * SHA-256 integrity verification

* 📊 **Interactive Dashboard**

  * Live risk score updates
  * Anomaly detection alerts
  * Blinking emergency warnings 🚨

---

## 🏗️ Architecture

```
File System Monitoring
        ↓
 Anomaly Detection (Entropy)
        ↓
 Decision Agent (Risk Score)
        ↓
 Backup Executor
        ↓
 ┌───────────────┬───────────────┐
 │ AWS S3        │ RDS Database  │
 │ (Storage)     │ (Logs/History)│
 └───────────────┴───────────────┘
```

---

## ⚙️ Tech Stack

* **Backend:** Python (FastAPI)
* **Frontend:** HTML, CSS, JavaScript
* **Database:** PostgreSQL (AWS RDS)
* **Cloud:** AWS (S3, Lambda, EC2)
* **Monitoring:** Watchdog, System Metrics
* **Security:** SHA-256 hashing

---

## 📂 Project Structure

```
GuardianX/
│
├── Backend/
│   ├── decision_agent.py
│   ├── backup_executor.py
│   ├── monitor.py
│   ├── database.py
│   └── api.py
│
├── Frontend/
│   └── dashboard UI
│
├── requirements.txt
└── README.md
```

---

## 🧪 How It Works

1. System monitors file changes in real-time
2. Calculates entropy of files
3. Detects anomaly patterns (e.g., ransomware)
4. Updates risk score dynamically
5. Decision agent triggers backup automatically
6. Backup stored in S3 + logged in RDS

---

## ▶️ Run Locally

```bash
# Clone repo
git clone https://github.com/Manas0667/GuardianX.git

# Go to project
cd GuardianX

# Create virtual env
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend
python Backend/decision_agent.py
```

---

## 🌐 Deployment

* Backend deployed on **AWS EC2**
* Storage handled by **S3**
* Logs stored in **RDS**
* Optional: Lambda for async processing

---

## 🔐 Security

* Sensitive data handled via `.env`
* SHA-256 hashing for backup verification
* No credentials stored in code

---

## 📸 Demo Highlights

* 🚨 Ransomware detection in real-time
* ⚡ Automatic emergency backup trigger
* 📊 Live dashboard updates
* ☁️ Cloud storage integration

---

## 👨‍💻 Author

**Manas Varshney**
B.Tech CSE | Cloud & DevOps Enthusiast

---

## ⭐ Future Improvements

* Restore backup feature
* Email/SMS alerts
* Kubernetes deployment
* AI-based anomaly prediction

---

## 💡 Note

This project is built for educational and demonstration purposes, showcasing real-world cloud-integrated system design.

---
