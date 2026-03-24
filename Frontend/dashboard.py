import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime
import random
def generate_ai_insight(score, decision):
    if score >= 80:
        return "🚨 Critical risk due to anomaly or high activity. Immediate FULL backup triggered."
    elif score >= 56:
        return "⚠ High activity detected. DIFFERENTIAL backup recommended."
    elif score >= 31:
        return "🔄 Moderate activity. INCREMENTAL backup sufficient."
    else:
        return "✅ System stable. No backup required."
DB = "../Backend/agent.db"

st.set_page_config(
    page_title="Backup Agent · Control",
    layout="wide",
    page_icon="⬡",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500&display=swap');

:root {
  --bg-base:      #F0FDFA;
  --bg-mid:       #CCFBF1;
  --bg-panel:     #FFFFFF;
  --border:       rgba(13,148,136,0.14);
  --border-glow:  rgba(56,189,248,0.45);
  --teal-dark:    #0D4B4B;
  --teal-primary: #0D9488;
  --teal-mid:     #14B8A6;
  --teal-light:   #5EEAD4;
  --sky:          #38BDF8;
  --sky-light:    #BAE6FD;
  --stripe:       #CCFBF1;
  --accent-red:   #E11D48;
  --text-primary: #0D4B4B;
  --text-soft:    #4B7E7A;
  --font-display: 'Syne', sans-serif;
  --font-mono:    'JetBrains Mono', monospace;
  --radius:       14px;
  --radius-sm:    8px;
  --shadow:       0 2px 16px rgba(13,74,74,0.08);
  --shadow-md:    0 4px 24px rgba(13,74,74,0.13);
}

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
  font-family: var(--font-display);
  color: var(--text-primary);
  background: var(--bg-base);
}
.stApp {
  background: var(--bg-base);
  background-image:
    radial-gradient(ellipse 70% 40% at 75% -5%, rgba(56,189,248,0.12) 0%, transparent 60%),
    radial-gradient(ellipse 50% 35% at 0% 100%, rgba(94,234,212,0.14) 0%, transparent 55%);
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* subtle teal grid */
.tech-grid {
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(rgba(13,148,136,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(13,148,136,0.05) 1px, transparent 1px);
  background-size: 48px 48px;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
  background: #FFFFFF !important;
  border-right: 1px solid rgba(13,148,136,0.12) !important;
  box-shadow: 2px 0 20px rgba(13,74,74,0.07) !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; background: #FFFFFF !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }

.sidebar-logo {
  padding: 28px 24px 22px;
  border-bottom: 1px solid rgba(13,148,136,0.10);
  background: linear-gradient(135deg, #0D4B4B 0%, #0D9488 100%);
}
.logo-hex { display:inline-flex;align-items:center;gap:10px;font-size:1.05rem;font-weight:800;color:#F0FDFA; }
.logo-icon { width:32px;height:32px;background:rgba(94,234,212,0.22);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px; }
.sidebar-section { padding:20px 16px 8px;font-size:0.6rem;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:var(--teal-primary);font-family:var(--font-mono); }
.nav-item { display:flex;align-items:center;gap:10px;padding:10px 16px;margin:2px 10px;border-radius:var(--radius-sm);font-size:0.82rem;font-weight:600;color:var(--text-soft);cursor:pointer;transition:all 0.2s;border:1px solid transparent; }
.nav-item:hover { background:var(--stripe);color:var(--teal-primary); }
.nav-item.active { background:rgba(13,148,136,0.09);color:var(--teal-primary);border-color:rgba(13,148,136,0.18); }
.nav-item.active::before { content:'';position:absolute;left:-10px;top:50%;transform:translateY(-50%);width:3px;height:60%;background:var(--teal-primary);border-radius:0 3px 3px 0;box-shadow:0 0 8px rgba(13,148,136,0.45); }
.nav-icon { font-size:1rem;width:20px;text-align:center; }
.sidebar-bottom { padding:16px;border-top:1px solid rgba(13,148,136,0.10);margin-top:20px; }
.user-pill { display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--stripe);border:1px solid rgba(13,148,136,0.14);border-radius:10px; }
.avatar { width:30px;height:30px;background:linear-gradient(135deg,#0D9488,#38BDF8);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.7rem;font-weight:700;color:white;flex-shrink:0; }
.user-name { font-size:0.78rem;font-weight:700;color:var(--teal-dark); }
.user-role { font-size:0.62rem;color:var(--text-soft);font-family:var(--font-mono); }

/* TOPBAR */
.topbar { display:flex;align-items:center;justify-content:space-between;padding:0 32px;height:64px;background:rgba(255,255,255,0.93);backdrop-filter:blur(20px);border-bottom:1px solid rgba(13,148,136,0.12);position:sticky;top:0;z-index:100;box-shadow:0 2px 14px rgba(13,74,74,0.07); }
.page-title { font-size:1rem;font-weight:800;color:var(--teal-dark); }
.breadcrumb { font-size:0.72rem;color:var(--text-soft);font-family:var(--font-mono); }
.breadcrumb span { color:var(--teal-primary);font-weight:600; }
.topbar-right { display:flex;align-items:center;gap:12px; }
.topbar-search { background:var(--stripe);border:1px solid rgba(13,148,136,0.16);border-radius:8px;padding:8px 14px;font-size:0.78rem;color:var(--text-soft);font-family:var(--font-mono);display:flex;align-items:center;gap:8px;cursor:pointer;transition:all 0.2s; }
.topbar-search:hover { border-color:var(--teal-primary);background:#fff;color:var(--teal-dark); }
.icon-btn { width:36px;height:36px;background:var(--stripe);border:1px solid rgba(13,148,136,0.16);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:0.9rem;cursor:pointer;transition:all 0.2s;position:relative; }
.icon-btn:hover { background:var(--bg-mid);border-color:var(--teal-primary);box-shadow:0 0 12px rgba(13,148,136,0.15); }
.notif-dot { position:absolute;top:6px;right:6px;width:7px;height:7px;background:var(--accent-red);border-radius:50%;border:1.5px solid #fff;box-shadow:0 0 6px rgba(225,29,72,0.5); }
.live-badge { display:flex;align-items:center;gap:6px;padding:6px 12px;background:rgba(13,148,136,0.08);border:1px solid rgba(13,148,136,0.22);border-radius:6px;font-size:0.68rem;font-family:var(--font-mono);color:var(--teal-primary);font-weight:600; }
.live-dot { width:6px;height:6px;background:var(--teal-primary);border-radius:50%;box-shadow:0 0 6px rgba(13,148,136,0.6);animation:pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1);}50%{opacity:0.45;transform:scale(0.8);} }

/* MAIN */
.main-content { padding:28px 32px;position:relative;z-index:1; }

/* STATUS RIBBON */
.status-ribbon { display:flex;align-items:center;gap:12px;padding:12px 20px;background:#fff;border:1px solid rgba(13,148,136,0.14);border-radius:var(--radius-sm);margin-bottom:24px;box-shadow:var(--shadow); }
.status-ribbon.critical { border-color:rgba(225,29,72,0.28);background:rgba(255,241,242,0.92); }
.status-ribbon.warning  { border-color:rgba(56,189,248,0.32);background:rgba(240,249,255,0.92); }
.status-ribbon.healthy  { border-color:rgba(13,148,136,0.22);background:rgba(240,253,250,0.92); }
.ribbon-dot { width:8px;height:8px;border-radius:50%;flex-shrink:0; }
.ribbon-dot.red   { background:var(--accent-red);box-shadow:0 0 8px rgba(225,29,72,0.5);animation:pulse 1.5s infinite; }
.ribbon-dot.amber { background:var(--sky);box-shadow:0 0 8px rgba(56,189,248,0.5);animation:pulse 2s infinite; }
.ribbon-dot.teal  { background:var(--teal-primary);box-shadow:0 0 8px rgba(13,148,136,0.45); }
.ribbon-text { font-size:0.82rem;font-weight:600;color:var(--text-primary);flex:1; }
.ribbon-time { font-family:var(--font-mono);font-size:0.68rem;color:var(--text-soft); }

/* SECTION HEADER */
.section-header { display:flex;align-items:center;justify-content:space-between;margin-bottom:16px; }
.section-title { font-size:0.65rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:var(--teal-primary);font-family:var(--font-mono);display:flex;align-items:center;gap:8px; }
.section-title::before { content:'';display:inline-block;width:20px;height:2px;background:linear-gradient(to right,var(--teal-primary),var(--sky));border-radius:2px; }

/* KPI CARDS */
.kpi-card { background:#fff;border:1px solid rgba(13,148,136,0.12);border-radius:var(--radius);padding:22px 24px;position:relative;overflow:hidden;cursor:default;transition:all 0.25s;box-shadow:var(--shadow); }
.kpi-card::before { content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:var(--radius) var(--radius) 0 0; }
.kpi-card.accent-cyan::before   { background:linear-gradient(to right,#38BDF8,#BAE6FD); }
.kpi-card.accent-violet::before { background:linear-gradient(to right,#0D9488,#14B8A6); }
.kpi-card.accent-teal::before   { background:linear-gradient(to right,#5EEAD4,#38BDF8); }
.kpi-card.accent-red::before    { background:linear-gradient(to right,#E11D48,#fb7185); }
.kpi-card:hover { transform:translateY(-3px);box-shadow:var(--shadow-md);border-color:rgba(13,148,136,0.26); }
.kpi-card.accent-cyan:hover   { box-shadow:0 8px 32px rgba(56,189,248,0.18); }
.kpi-card.accent-violet:hover { box-shadow:0 8px 32px rgba(13,148,136,0.18); }
.kpi-card.accent-teal:hover   { box-shadow:0 8px 32px rgba(94,234,212,0.22); }
.kpi-card.accent-red:hover    { box-shadow:0 8px 32px rgba(225,29,72,0.14); }
.kpi-top { display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px; }
.kpi-icon { width:42px;height:42px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.15rem; }
.kpi-icon.cyan   { background:rgba(56,189,248,0.12);border:1px solid rgba(56,189,248,0.22); }
.kpi-icon.violet { background:rgba(13,148,136,0.10);border:1px solid rgba(13,148,136,0.20); }
.kpi-icon.teal   { background:rgba(94,234,212,0.18);border:1px solid rgba(94,234,212,0.30); }
.kpi-icon.red    { background:rgba(225,29,72,0.08);border:1px solid rgba(225,29,72,0.18); }
.kpi-trend { font-family:var(--font-mono);font-size:0.65rem;padding:3px 8px;border-radius:20px;font-weight:600; }
.trend-up   { background:rgba(13,148,136,0.10);color:var(--teal-primary); }
.trend-down { background:rgba(225,29,72,0.08);color:var(--accent-red); }
.trend-flat { background:rgba(56,189,248,0.10);color:#0369a1; }
.kpi-value { font-size:2.2rem;font-weight:800;line-height:1;margin:0 0 4px 0;letter-spacing:-0.03em; }
.kpi-value.cyan   { color:#0369a1; }
.kpi-value.violet { color:var(--teal-primary); }
.kpi-value.teal   { color:var(--teal-mid); }
.kpi-value.red    { color:var(--accent-red); }
.kpi-label { font-size:0.72rem;font-weight:600;color:var(--text-soft);letter-spacing:0.06em;text-transform:uppercase;margin:0; }
.kpi-sub { font-size:0.7rem;color:var(--text-soft);font-family:var(--font-mono);margin-top:12px;padding-top:12px;border-top:1px solid rgba(13,148,136,0.10); }

/* GLASS PANEL */
.glass-panel { background:#fff;border:1px solid rgba(13,148,136,0.12);border-radius:var(--radius);padding:24px;box-shadow:var(--shadow);position:relative;overflow:hidden;height:100%; }
.glass-panel::before { content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(to right,var(--teal-primary),var(--sky),var(--teal-light));border-radius:var(--radius) var(--radius) 0 0; }
.panel-title { font-size:0.85rem;font-weight:700;color:var(--teal-dark);margin:0 0 4px 0; }
.panel-sub { font-size:0.68rem;color:var(--text-soft);font-family:var(--font-mono);margin:0 0 20px 0; }
.panel-divider { height:1px;background:rgba(13,148,136,0.10);margin:16px 0; }

/* ACTIVITY FEED */
.feed-item { display:flex;gap:12px;padding:11px 0;border-bottom:1px solid rgba(13,148,136,0.08);align-items:flex-start; }
.feed-item:last-child { border-bottom:none; }
.feed-dot-wrap { display:flex;flex-direction:column;align-items:center;gap:4px;padding-top:2px; }
.feed-dot { width:8px;height:8px;border-radius:50%;flex-shrink:0; }
.feed-dot.success { background:var(--teal-primary);box-shadow:0 0 6px rgba(13,148,136,0.4); }
.feed-dot.danger  { background:var(--accent-red);box-shadow:0 0 6px rgba(225,29,72,0.4); }
.feed-dot.info    { background:var(--sky);box-shadow:0 0 6px rgba(56,189,248,0.4); }
.feed-dot.warn    { background:var(--teal-mid);box-shadow:0 0 6px rgba(20,184,166,0.4); }
.feed-line { width:1px;flex:1;background:rgba(13,148,136,0.10);min-height:14px; }
.feed-body { flex:1;min-width:0; }
.feed-event { font-size:0.78rem;font-weight:600;color:var(--teal-dark);margin-bottom:2px; }
.feed-detail { font-size:0.67rem;color:var(--text-soft);font-family:var(--font-mono); }
.feed-time { font-size:0.62rem;color:var(--text-soft);font-family:var(--font-mono);white-space:nowrap;padding-top:2px; }

/* TABLE */
.cyber-table-wrap { overflow-x:auto;border-radius:var(--radius-sm);border:1px solid rgba(13,148,136,0.12); }
.cyber-table { width:100%;border-collapse:collapse;font-size:0.78rem; }
.cyber-table thead tr { background:linear-gradient(to right,rgba(13,148,136,0.06),rgba(56,189,248,0.04));border-bottom:1px solid rgba(13,148,136,0.14); }
.cyber-table thead th { padding:12px 16px;text-align:left;font-size:0.62rem;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:var(--teal-primary);font-family:var(--font-mono);white-space:nowrap; }
.cyber-table tbody tr { border-bottom:1px solid rgba(13,148,136,0.06);transition:background 0.15s; }
.cyber-table tbody tr:last-child { border-bottom:none; }
.cyber-table tbody tr:hover { background:rgba(240,253,250,0.80); }
.cyber-table tbody td { padding:11px 16px;color:var(--text-primary);vertical-align:middle; }
.cyber-table tbody td:first-child { font-family:var(--font-mono);font-size:0.7rem;color:var(--text-soft); }
.badge { display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:20px;font-size:0.65rem;font-family:var(--font-mono);font-weight:600;letter-spacing:0.05em; }
.badge::before { content:'';width:5px;height:5px;border-radius:50%; }
.badge-success { background:rgba(13,148,136,0.10);color:var(--teal-primary);border:1px solid rgba(13,148,136,0.22); }
.badge-success::before { background:var(--teal-primary); }
.badge-fail    { background:rgba(225,29,72,0.08);color:var(--accent-red);border:1px solid rgba(225,29,72,0.20); }
.badge-fail::before { background:var(--accent-red); }
.type-pill { display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.65rem;font-family:var(--font-mono);font-weight:700;letter-spacing:0.06em;text-transform:uppercase; }
.type-full         { background:rgba(13,74,74,0.08);color:var(--teal-dark);border:1px solid rgba(13,74,74,0.15); }
.type-incremental  { background:rgba(56,189,248,0.10);color:#0369a1;border:1px solid rgba(56,189,248,0.22); }
.type-differential { background:rgba(13,148,136,0.10);color:var(--teal-primary);border:1px solid rgba(13,148,136,0.22); }
.type-emergency    { background:rgba(225,29,72,0.08);color:var(--accent-red);border:1px solid rgba(225,29,72,0.20); }

/* ANOMALIES */
.anomaly-row { display:flex;align-items:flex-start;gap:12px;padding:12px;border-radius:8px;background:rgba(255,241,242,0.75);border:1px solid rgba(225,29,72,0.14);margin-bottom:8px;transition:all 0.2s; }
.anomaly-row:hover { background:rgba(255,228,230,0.92);border-color:rgba(225,29,72,0.28); }
.anomaly-icon { font-size:1rem;flex-shrink:0;margin-top:1px; }
.anomaly-type { font-size:0.75rem;font-weight:700;color:var(--accent-red);margin-bottom:2px; }
.anomaly-detail { font-size:0.68rem;color:var(--text-soft);font-family:var(--font-mono); }
.anomaly-time { font-size:0.62rem;color:var(--text-soft);font-family:var(--font-mono);margin-left:auto;white-space:nowrap; }

/* UTILS */
.empty-state { text-align:center;padding:40px 20px;color:var(--text-soft); }
.empty-icon { font-size:2rem;margin-bottom:10px;opacity:0.5; }
.empty-text { font-size:0.78rem;font-family:var(--font-mono); }
.glow-sep { height:1px;background:linear-gradient(to right,transparent,rgba(13,148,136,0.22),rgba(56,189,248,0.18),transparent);margin:28px 0; }
.dash-footer { text-align:center;padding:20px 32px;font-size:0.65rem;font-family:var(--font-mono);color:var(--text-soft);border-top:1px solid rgba(13,148,136,0.10);letter-spacing:0.08em;background:#fff; }

[data-testid="stMetric"] { display:none !important; }
.stDataFrame { display:none !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="tech-grid"></div>', unsafe_allow_html=True)

def get_df(query):
    try:
        conn = sqlite3.connect(DB)
        df   = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

df_risk   = get_df("SELECT score, decision FROM risk_score_log ORDER BY id DESC LIMIT 1")
score     = int(df_risk["score"].iloc[0])  if len(df_risk)  > 0 else 42
decision  = df_risk["decision"].iloc[0]    if len(df_risk)  > 0 else "INCREMENTAL"
df_hist   = get_df("SELECT * FROM backup_history ORDER BY id DESC LIMIT 1")
last_bk   = df_hist["timestamp"].iloc[0][:16] if len(df_hist) > 0 else "—"
last_type = df_hist["type"].iloc[0]           if len(df_hist) > 0 else "—"
df_anom   = get_df("SELECT * FROM anomaly_log ORDER BY id DESC LIMIT 10")
anom_cnt  = len(df_anom)
df_total  = get_df("SELECT COUNT(*) as c FROM backup_history WHERE status='SUCCESS'")
total_bk  = int(df_total["c"].iloc[0]) if len(df_total) > 0 else 0
df_scores = get_df("SELECT timestamp, score FROM risk_score_log ORDER BY id DESC LIMIT 30")
df_bk_full= get_df("SELECT timestamp, type, status, size_mb, location FROM backup_history ORDER BY id DESC LIMIT 15")
df_act    = get_df("SELECT day, hour, AVG(cpu) as avg_cpu FROM activity_log GROUP BY day, hour")

if score >= 80:   risk_cat,rd,rb = "critical","red","critical"
elif score >= 56: risk_cat,rd,rb = "warning","amber","warning"
else:             risk_cat,rd,rb = "healthy","teal","healthy"

now_str = datetime.now().strftime("%H:%M:%S")

with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-logo">
      <div class="logo-hex"><div class="logo-icon">⬡</div>BackupAI</div>
    </div>
    <div class="sidebar-section">Navigation</div>
    <div class="nav-item active" style="position:relative;"><span class="nav-icon">◈</span> Dashboard</div>
    <div class="nav-item"><span class="nav-icon">◉</span> Analytics</div>
    <div class="nav-item"><span class="nav-icon">◎</span> Reports</div>
    <div class="nav-item"><span class="nav-icon">⊕</span> Anomalies</div>
    <div class="sidebar-section" style="margin-top:4px;">System</div>
    <div class="nav-item"><span class="nav-icon">⊞</span> Storage</div>
    <div class="nav-item"><span class="nav-icon">◇</span> Settings</div>
    <div style="height:32px;"></div>
    <div class="sidebar-bottom">
      <div class="user-pill">
        <div class="avatar">MV</div>
        <div><div class="user-name">Manas Varshney</div><div class="user-role">admin · 2CC</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
<div class="topbar">
  <div>
    <div class="page-title">Control Center</div>
    <div class="breadcrumb">BackupAI / <span>Dashboard</span></div>
  </div>
  <div class="topbar-right">
    <div class="live-badge"><div class="live-dot"></div>LIVE · {now_str}</div>
    <div class="topbar-search">⌕&nbsp; Search...</div>
    <div class="icon-btn">🔔<div class="notif-dot"></div></div>
    <div class="icon-btn">⚙</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="glow-sep"></div>', unsafe_allow_html=True)

msgs = {
    "critical": f"⚠ CRITICAL — Risk score {score}/100 — Emergency {decision} backup triggered",
    "warning":  f"◈ HIGH ACTIVITY — Risk score {score}/100 — {decision} backup recommended",
    "healthy":  f"✓ SYSTEM NOMINAL — Risk score {score}/100 — All systems operational"
}
st.markdown(f"""
<div class="status-ribbon {rb}">
  <div class="ribbon-dot {rd}"></div>
  <span class="ribbon-text">{msgs[risk_cat]}</span>
  <span class="ribbon-time">{datetime.now().strftime("%d %b %Y · %H:%M")}</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-header"><span class="section-title">Key Performance Indicators</span></div>', unsafe_allow_html=True)
k1,k2,k3,k4 = st.columns(4, gap="small")

with k1:
    t = "trend-down" if score>=56 else "trend-up"
    st.markdown(f"""
    <div class="kpi-card accent-cyan">
      <div class="kpi-top"><div class="kpi-icon cyan">🛡</div><span class="kpi-trend {t}">{score}/100</span></div>
      <p class="kpi-value cyan">{score}</p>
      <p class="kpi-label">Risk Score</p>
      <p class="kpi-sub">Decision: <strong style="color:#0D4B4B">{decision}</strong></p>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""
    <div class="kpi-card accent-violet">
      <div class="kpi-top"><div class="kpi-icon violet">💾</div><span class="kpi-trend trend-up">↑ running</span></div>
      <p class="kpi-value violet">{total_bk}</p>
      <p class="kpi-label">Total Backups</p>
      <p class="kpi-sub">Successful completions</p>
    </div>""", unsafe_allow_html=True)
with k3:
    disp = last_type if last_type != "—" else "None"
    st.markdown(f"""
    <div class="kpi-card accent-teal">
      <div class="kpi-top"><div class="kpi-icon teal">⚡</div><span class="kpi-trend trend-flat">→ latest</span></div>
      <p class="kpi-value teal" style="font-size:1.4rem;margin-top:4px;">{disp}</p>
      <p class="kpi-label">Last Backup Type</p>
      <p class="kpi-sub">{last_bk}</p>
    </div>""", unsafe_allow_html=True)
with k4:
    ac = "accent-red" if anom_cnt>0 else "accent-teal"
    ic = "red" if anom_cnt>0 else "teal"
    tr = "trend-down" if anom_cnt>0 else "trend-up"
    lbl= f"↑ {anom_cnt} alerts" if anom_cnt>0 else "↓ all clear"
    st.markdown(f"""
    <div class="kpi-card {ac}">
      <div class="kpi-top"><div class="kpi-icon {ic}">⚠</div><span class="kpi-trend {tr}">{lbl}</span></div>
      <p class="kpi-value {ic}">{anom_cnt}</p>
      <p class="kpi-label">Anomalies</p>
      <p class="kpi-sub">All-time detections</p>
    </div>""", unsafe_allow_html=True)
# ================= AI INSIGHT =================
st.markdown('<div class="section-header"><span class="section-title">AI Insight Engine</span></div>', unsafe_allow_html=True)

insight = generate_ai_insight(score, decision)

st.markdown(f"""
<div class="glass-panel">
  <p class="panel-title">AI Decision Insight</p>
  <p class="panel-sub">Why this decision was taken</p>
  <div class="panel-divider"></div>
  <p style="font-size:0.85rem; line-height:1.6;">{insight}</p>
</div>
""", unsafe_allow_html=True)
# ================= WHAT IF SIMULATION =================
st.markdown('<div class="section-header"><span class="section-title">What-If Simulation</span></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    sim_cpu = st.slider("CPU Usage (%)", 0, 100, 30)

with col2:
    sim_files = st.slider("Files Modified", 0, 500, 50)

with col3:
    sim_days = st.slider("Days Since Backup", 0, 30, 5)

# simulate risk
sim_score = min(100, int((sim_cpu/100)*10 + (sim_files/200)*30 + (sim_days/14)*25))

if sim_score >= 80:
    sim_decision = "FULL"
elif sim_score >= 56:
    sim_decision = "DIFFERENTIAL"
elif sim_score >= 31:
    sim_decision = "INCREMENTAL"
else:
    sim_decision = "WAIT"

st.markdown(f"""
<div class="glass-panel">
  <p class="panel-title">Simulation Result</p>
  <p class="panel-sub">Predicted backup behavior</p>
  <div class="panel-divider"></div>
  <h2>Risk Score: {sim_score}/100</h2>
  <h3 style="color:#0D9488;">Decision: {sim_decision}</h3>
</div>
""", unsafe_allow_html=True)
# ================= DECISION ANALYTICS =================
st.markdown('<div class="section-header"><span class="section-title">Decision Analytics</span></div>', unsafe_allow_html=True)

df_decision = get_df("""
SELECT decision, COUNT(*) as count 
FROM risk_score_log 
GROUP BY decision
""")

if len(df_decision) > 0:
    st.bar_chart(df_decision.set_index("decision"))
else:
    st.info("No decision data available yet")

st.markdown('<div class="section-header"><span class="section-title">Live Intelligence</span></div>', unsafe_allow_html=True)
col_chart, col_ring, col_feed = st.columns([5,2,3], gap="small")

vals = df_scores.sort_values("timestamp")["score"].tolist() if len(df_scores)>0 else [random.randint(20,65) for _ in range(22)]

def sparkline_svg(vals, w=460, h=90):
    mn,mx = min(vals),max(vals); rng=mx-mn if mx!=mn else 1
    step  = w/max(len(vals)-1,1)
    pts   = [(i*step, h-((v-mn)/rng)*(h-18)-9) for i,v in enumerate(vals)]
    path  = "M"+" L".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    area  = path+f" L{pts[-1][0]:.1f},{h} L0,{h} Z"
    zc    = "#E11D48" if vals[-1]>=80 else "#38BDF8" if vals[-1]>=56 else "#0D9488"
    lx,ly = pts[-1]
    return f"""<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:{h}px;">
      <defs>
        <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="{zc}" stop-opacity="0.18"/>
          <stop offset="100%" stop-color="{zc}" stop-opacity="0.01"/>
        </linearGradient>
        <filter id="glow"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <path d="{area}" fill="url(#sg)"/>
      <path d="{path}" fill="none" stroke="{zc}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="{lx:.1f}" cy="{ly:.1f}" r="5" fill="white" stroke="{zc}" stroke-width="2.5" filter="url(#glow)"/>
    </svg>"""

with col_chart:
    lc = "#E11D48" if vals[-1]>=80 else "#0369a1" if vals[-1]>=56 else "#0D9488"
    st.markdown(f"""
    <div class="glass-panel" style="height:auto;">
      <p class="panel-title">Risk Score Trend</p>
      <p class="panel-sub">Last {len(vals)} readings · updates on every file event</p>
      <div class="panel-divider"></div>
      {sparkline_svg(vals)}
      <div style="display:flex;justify-content:space-between;margin-top:6px;">
        <span style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-soft)">← oldest</span>
        <span style="font-size:0.6rem;font-family:var(--font-mono);color:{lc};font-weight:600;">latest: {vals[-1]}/100 →</span>
      </div>
    </div>""", unsafe_allow_html=True)

with col_ring:
    circ=2*3.14159*42; dfc=circ*score/100; de=circ-dfc
    rc = "#E11D48" if score>=80 else "#38BDF8" if score>=56 else "#0D9488"
    rbg= "rgba(225,29,72,0.07)" if score>=80 else "rgba(56,189,248,0.07)" if score>=56 else "rgba(13,148,136,0.07)"
    st.markdown(f"""
    <div class="glass-panel" style="text-align:center;height:auto;">
      <p class="panel-title" style="text-align:center;">Risk Gauge</p>
      <p class="panel-sub" style="text-align:center;">composite score</p>
      <div class="panel-divider"></div>
      <svg viewBox="0 0 100 100" style="width:130px;height:130px;margin:0 auto;display:block;filter:drop-shadow(0 4px 12px {rc}2a)">
        <circle cx="50" cy="50" r="42" fill="{rbg}" stroke="rgba(13,148,136,0.14)" stroke-width="8"/>
        <circle cx="50" cy="50" r="42" fill="none" stroke="{rc}" stroke-width="8"
          stroke-linecap="round" stroke-dasharray="{dfc:.1f} {de:.1f}" transform="rotate(-90 50 50)"/>
        <text x="50" y="47" text-anchor="middle" fill="{rc}" font-size="18" font-weight="800" font-family="Syne,sans-serif">{score}</text>
        <text x="50" y="60" text-anchor="middle" fill="#4B7E7A" font-size="7" font-family="JetBrains Mono">/100</text>
      </svg>
      <p style="font-size:0.7rem;font-family:var(--font-mono);color:var(--text-soft);margin-top:10px;">{risk_cat.upper()}</p>
      <p style="font-size:0.82rem;font-weight:700;color:#0D4B4B;margin-top:4px;">{decision}</p>
    </div>""", unsafe_allow_html=True)

with col_feed:
    feed_items = []
    if len(df_bk_full)>0:
        for _,r in df_bk_full.head(4).iterrows():
            tp=r.get("type","?"); st2=r.get("status","?"); ts=str(r.get("timestamp",""))[:16]; sz=r.get("size_mb",0)
            feed_items.append(("success" if st2=="SUCCESS" else "danger", f"{tp} backup {st2.lower()}", f"{float(sz):.1f} MB", ts[-5:]))
    if len(df_anom)>0:
        for _,r in df_anom.head(3).iterrows():
            ts=str(r.get("timestamp",""))[:16]; tp=r.get("type","ANOMALY")
            feed_items.append(("danger", f"⚠ {tp}", str(r.get("details",""))[:38], ts[-5:]))
    if not feed_items:
        feed_items=[("info","Agent initialized","Watchdog active","—"),("success","DB connected","agent.db ready","—")]
    rows=""
    for i,(dot,ev,det,t) in enumerate(feed_items[:7]):
        line='<div class="feed-line"></div>' if i<len(feed_items)-1 else ''
        rows+=f"""<div class="feed-item">
          <div class="feed-dot-wrap"><div class="feed-dot {dot}"></div>{line}</div>
          <div class="feed-body"><div class="feed-event">{ev}</div><div class="feed-detail">{det}</div></div>
          <div class="feed-time">{t}</div></div>"""
    st.markdown(f"""
    <div class="glass-panel" style="height:auto;">
      <p class="panel-title">Activity Feed</p>
      <p class="panel-sub">Recent agent events</p>
      <div class="panel-divider"></div>{rows}
    </div>""", unsafe_allow_html=True)

st.markdown('<div class="glow-sep"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-header"><span class="section-title">Backup History & Threat Log</span></div>', unsafe_allow_html=True)
col_tbl, col_an = st.columns([6,4], gap="small")

with col_tbl:
    rows=""
    if len(df_bk_full)>0:
        for _,r in df_bk_full.iterrows():
            ts=str(r.get("timestamp",""))[:16]; tp=str(r.get("type","?")); st2=str(r.get("status","?"))
            sz=float(r.get("size_mb",0)); loc=str(r.get("location","—"))[:28]
            tc=f"type-{tp.lower().replace(' ','')}"; sc="badge-success" if st2=="SUCCESS" else "badge-fail"
            rows+=f"""<tr><td>{ts}</td><td><span class="type-pill {tc}">{tp}</span></td>
              <td><span class="badge {sc}">{st2}</span></td>
              <td style="font-family:var(--font-mono);font-size:0.72rem;">{sz:.1f} MB</td>
              <td style="font-family:var(--font-mono);font-size:0.68rem;color:var(--text-soft);">{loc}</td></tr>"""
    else:
        rows='<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">📂</div><div class="empty-text">No backups yet — run the agent</div></div></td></tr>'
    st.markdown(f"""
    <div class="glass-panel" style="height:auto;">
      <p class="panel-title">Backup Log</p><p class="panel-sub">Last 15 operations</p>
      <div class="panel-divider"></div>
      <div class="cyber-table-wrap">
        <table class="cyber-table">
          <thead><tr><th>Timestamp</th><th>Type</th><th>Status</th><th>Size</th><th>Location</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>""", unsafe_allow_html=True)

with col_an:
    icons={"MASS_DELETION":"🗑","RANSOMWARE":"🔐","RENAME_ATTACK":"✏","WRITE_BURST":"💥","ODD_HOUR":"🌙"}
    if len(df_anom)>0:
        ahtml=""
        for _,r in df_anom.head(6).iterrows():
            tp=str(r.get("type","ANOMALY")); det=str(r.get("details","—"))[:48]; ts=str(r.get("timestamp",""))[:16]; ico=icons.get(tp,"⚠")
            ahtml+=f"""<div class="anomaly-row"><div class="anomaly-icon">{ico}</div>
              <div style="flex:1;min-width:0;"><div class="anomaly-type">{tp.replace('_',' ')}</div><div class="anomaly-detail">{det}</div></div>
              <div class="anomaly-time">{ts[-5:]}</div></div>"""
    else:
        ahtml='<div class="empty-state"><div class="empty-icon">✅</div><div class="empty-text">No anomalies detected<br>System is clean</div></div>'
    st.markdown(f"""
    <div class="glass-panel" style="height:auto;">
      <p class="panel-title">Threat Log</p><p class="panel-sub">Security anomaly detections</p>
      <div class="panel-divider"></div>{ahtml}
    </div>""", unsafe_allow_html=True)

st.markdown('<div class="glow-sep"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-header"><span class="section-title">Adaptive Scheduler · CPU Heatmap</span></div>', unsafe_allow_html=True)

if len(df_act)>0:
    day_order=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    pivot=df_act.pivot(index="day",columns="hour",values="avg_cpu").fillna(0)
    pivot=pivot.reindex([d for d in day_order if d in pivot.index])
    hours=sorted(df_act["hour"].unique()); days=[d for d in day_order if d in pivot.index]
    cw,ch=38,30; svg_w=len(hours)*cw+90; svg_h=len(days)*ch+46

    def hcol(v):
        if v<20:   return "#E6FFF9","#0D9488"    # mint bg → teal text
        elif v<40: return "#CCFBF1","#0D4B4B"    # stripe bg → dark teal
        elif v<60: return "#BAE6FD","#0369a1"    # pale sky → blue
        elif v<80: return "#DBEAFE","#1e40af"    # light blue → dark blue
        else:      return "#FFE4E6","#E11D48"    # pink → red

    cells=""
    for ri,day in enumerate(days):
        for ci,hour in enumerate(hours):
            val=pivot.at[day,hour] if hour in pivot.columns else 0
            bg,tc=hcol(float(val)); x=ci*cw+85; y=ri*ch+32
            cells+=f'<rect x="{x}" y="{y}" width="{cw-2}" height="{ch-3}" rx="4" fill="{bg}" stroke="rgba(13,148,136,0.10)" stroke-width="1"/>'
            cells+=f'<text x="{x+cw//2-1}" y="{y+ch//2+3}" text-anchor="middle" fill="{tc}" font-size="8" font-weight="600" font-family="JetBrains Mono,monospace">{float(val):.0f}</text>'

    hlabels="".join(f'<text x="{ci*cw+85+cw//2-1}" y="22" text-anchor="middle" fill="#4B7E7A" font-size="7" font-family="JetBrains Mono">{h:02d}</text>' for ci,h in enumerate(hours))
    dlabels="".join(f'<text x="80" y="{ri*ch+32+ch//2+3}" text-anchor="end" fill="#0D9488" font-size="8" font-weight="600" font-family="JetBrains Mono">{d[:3]}</text>' for ri,d in enumerate(days))
    hsvg=f'<svg viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-height:260px;">{hlabels}{dlabels}{cells}</svg>'
    best=df_act.loc[df_act["avg_cpu"].idxmin()]
    best_info=f"⚡ Backup window: {int(best['hour']):02d}:00 on {best['day']} · avg {round(best['avg_cpu'],1)}% CPU"
else:
    hsvg='<div class="empty-state"><div class="empty-icon">🕐</div><div class="empty-text">No data yet — agent logs CPU every hour</div></div>'
    best_info="Collecting data…"

st.markdown(f"""
<div class="glass-panel" style="height:auto;">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:0;">
    <div><p class="panel-title">CPU Activity Pattern</p><p class="panel-sub">7-day heatmap — mint = idle · sky = medium · pink = high load</p></div>
    <div style="background:rgba(13,148,136,0.07);border:1px solid rgba(13,148,136,0.20);border-radius:8px;padding:8px 16px;font-size:0.72rem;font-family:var(--font-mono);color:#0D9488;font-weight:600;">{best_info}</div>
  </div>
  <div class="panel-divider"></div>{hsvg}
</div>""", unsafe_allow_html=True)

st.markdown(f"""
</div>
<div class="dash-footer">
  BACKUP AGENT · BTECH CSE · SECTION 2CC &nbsp;·&nbsp; LAST REFRESHED {datetime.now().strftime('%H:%M:%S')} &nbsp;·&nbsp; AUTO-REFRESH 5s
</div>""", unsafe_allow_html=True)

time.sleep(5)
st.rerun()