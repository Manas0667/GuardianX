import psycopg2
from config import RDS_HOST, RDS_PORT, RDS_DB, RDS_USER, RDS_PASSWORD

def fix_schema():
    try:
        conn = psycopg2.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            database=RDS_DB,
            user=RDS_USER,
            password=RDS_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("✅ Connected to RDS")

        # ─────────────────────────────────────────
        # activity_log fixes
        # ─────────────────────────────────────────
        try:
            cur.execute("ALTER TABLE activity_log ADD COLUMN open_files INT;")
            print("✔ Added open_files to activity_log")
        except Exception as e:
            print("⚠️ open_files:", e)

        try:
            cur.execute("ALTER TABLE activity_log ADD COLUMN machine_id TEXT;")
            print("✔ Added machine_id to activity_log")
        except Exception as e:
            print("⚠️ machine_id:", e)

        # ─────────────────────────────────────────
        # risk_score_log fixes
        # ─────────────────────────────────────────
        try:
            cur.execute("ALTER TABLE risk_score_log ADD COLUMN machine_id TEXT;")
            print("✔ Added machine_id to risk_score_log")
        except Exception as e:
            print("⚠️ risk_score_log:", e)

        # ─────────────────────────────────────────
        # backup_history fixes
        # ─────────────────────────────────────────
        try:
            cur.execute("ALTER TABLE backup_history ADD COLUMN sha256_hash TEXT;")
            print("✔ Added sha256_hash to backup_history")
        except Exception as e:
            print("⚠️ sha256_hash:", e)

        # (optional future-proof)
        try:
            cur.execute("ALTER TABLE backup_history ADD COLUMN error_msg TEXT;")
            print("✔ Added error_msg to backup_history")
        except Exception as e:
            print("⚠️ error_msg:", e)

        cur.close()
        conn.close()

        print("🎉 ALL SCHEMA FIXED SUCCESSFULLY")

    except Exception as e:
        print("❌ Connection failed:", e)


if __name__ == "__main__":
    fix_schema()