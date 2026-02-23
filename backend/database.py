"""
ShieldAML — Database Layer
Uses SQLite for easy deployment (can be switched to PostgreSQL for production)
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "shieldaml.db"

# ─── CONNECTION ───────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ─── INITIALIZE TABLES ───────────────────────────────────────

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS transactions (
        id              TEXT PRIMARY KEY,
        customer_id     TEXT,
        customer_name   TEXT,
        amount          REAL,
        currency        TEXT DEFAULT 'USD',
        tx_type         TEXT,
        country         TEXT,
        hour            INTEGER,
        tx_count_30d    INTEGER,
        account_age     INTEGER,
        kyc_status      INTEGER,
        prev_flagged    INTEGER DEFAULT 0,
        is_pep          INTEGER DEFAULT 0,
        risk_score      INTEGER,
        risk_level      TEXT,
        flags           TEXT,
        recommendation  TEXT,
        tree_scores     TEXT,
        str_filed       INTEGER DEFAULT 0,
        created_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS alerts (
        id              TEXT PRIMARY KEY,
        transaction_id  TEXT,
        alert_type      TEXT,
        customer_name   TEXT,
        amount          REAL,
        description     TEXT,
        risk_level      TEXT,
        status          TEXT DEFAULT 'OPEN',
        created_at      TEXT,
        resolved_at     TEXT,
        FOREIGN KEY(transaction_id) REFERENCES transactions(id)
    );

    CREATE TABLE IF NOT EXISTS str_reports (
        id              TEXT PRIMARY KEY,
        transaction_id  TEXT,
        customer_name   TEXT,
        amount          REAL,
        risk_score      INTEGER,
        flags           TEXT,
        recommendation  TEXT,
        officer_name    TEXT DEFAULT 'Ahmed Salama',
        officer_cert    TEXT DEFAULT 'CAMS',
        status          TEXT DEFAULT 'DRAFT',
        submitted_at    TEXT,
        created_at      TEXT,
        FOREIGN KEY(transaction_id) REFERENCES transactions(id)
    );

    CREATE TABLE IF NOT EXISTS customers (
        id              TEXT PRIMARY KEY,
        name            TEXT,
        nationality     TEXT,
        occupation      TEXT,
        account_age     INTEGER,
        kyc_status      INTEGER DEFAULT 0,
        is_pep          INTEGER DEFAULT 0,
        risk_level      TEXT DEFAULT 'LOW',
        total_flagged   INTEGER DEFAULT 0,
        created_at      TEXT
    );
    """)

    conn.commit()
    conn.close()
    seed_demo_data()

# ─── SEED DEMO DATA ──────────────────────────────────────────

def seed_demo_data():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM transactions")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    demo_transactions = [
        ("TXN-8821", "CUS-001", "Mohammed Al-Rashid", 125000, "wire",       "ir", 3,  8,  2, 0, True,  False, 89, "CRITICAL"),
        ("TXN-8819", "CUS-002", "Sara Ahmed Corp",     8400,  "cash",       "eg", 14, 3,  6, 0, False, False, 72, "HIGH"),
        ("TXN-8814", "CUS-003", "Gulf Traders LLC",   45000,  "crypto",     "ru", 22, 22, 4, 1, False, False, 68, "HIGH"),
        ("TXN-8810", "CUS-004", "Nour Investment",     2200,  "insurance",  "ae", 11, 5, 18, 1, False, False, 41, "MEDIUM"),
        ("TXN-8805", "CUS-005", "Cairo Export Co",      890,  "wire",       "uk",  9, 2, 24, 1, False, False, 12, "LOW"),
        ("TXN-8803", "CUS-006", "Ahmed Hassan",        3100,  "internal",   "eg", 10, 1, 36, 1, False, False,  8, "LOW"),
        ("TXN-8799", "CUS-007", "Al-Noor Holdings",   67000,  "wire",       "sa",  7, 12, 8, 2, True,  True,  81, "CRITICAL"),
        ("TXN-8795", "CUS-008", "Phoenix Trading",     9800,  "cash",       "eg", 16, 7, 12, 0, False, False, 65, "HIGH"),
    ]

    now = datetime.utcnow()
    for i, tx in enumerate(demo_transactions):
        created = (now - timedelta(hours=i*2)).isoformat()
        flags_json = json.dumps([{"code": "demo_flag", "severity": tx[13], "description": "Demo transaction"}])
        rec_json   = json.dumps({"action": "REVIEW", "str_required": tx[13] in ("CRITICAL",)})
        trees_json = json.dumps({"Sanctions & Amount": tx[12]-5, "Account Behavior": tx[12]-10,
                                  "Type & Country Combo": tx[12]+5, "KYC & Velocity": tx[12]-8,
                                  "Anomaly Detection": tx[12]-3})
        c.execute("""
            INSERT INTO transactions
            (id,customer_id,customer_name,amount,tx_type,country,hour,tx_count_30d,
             account_age,kyc_status,prev_flagged,is_pep,risk_score,risk_level,
             flags,recommendation,tree_scores,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (tx[0],tx[1],tx[2],tx[3],tx[4],tx[5],tx[6],tx[7],
              tx[8],tx[9],int(tx[10]),int(tx[11]),tx[12],tx[13],
              flags_json, rec_json, trees_json, created))

    demo_alerts = [
        ("ALT-001","TXN-8821","Sanctions Match",    "Mohammed Al-Rashid", 125000, "Wire transfer to Iran — sanctioned country",        "CRITICAL", "OPEN"),
        ("ALT-002","TXN-8795","Structuring",         "Phoenix Trading",     9800, "Cash deposit just below $10K reporting threshold",   "HIGH",     "OPEN"),
        ("ALT-003","TXN-8819","Incomplete KYC",      "Sara Ahmed Corp",     8400, "Customer KYC incomplete — identity unverified",       "HIGH",     "OPEN"),
        ("ALT-004","TXN-8799","PEP Linked",          "Al-Noor Holdings",   67000, "Transaction linked to Politically Exposed Person",    "CRITICAL", "OPEN"),
        ("ALT-005","TXN-8814","High Velocity",       "Gulf Traders LLC",   45000, "22 transactions in 30 days — unusual velocity",      "HIGH",     "OPEN"),
        ("ALT-006","TXN-8810","Enhanced Monitoring", "Nour Investment",     2200, "Previously flagged customer — enhanced monitoring",   "MEDIUM",   "OPEN"),
    ]

    for i, al in enumerate(demo_alerts):
        created = (now - timedelta(hours=i*1.5)).isoformat()
        c.execute("""
            INSERT INTO alerts (id,transaction_id,alert_type,customer_name,amount,description,risk_level,status,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (*al, created))

    demo_str = [
        ("STR-2025-041","TXN-8821","Mohammed Al-Rashid",125000,89,"SUBMITTED"),
        ("STR-2025-040","TXN-8795","Phoenix Trading",    9800, 65,"DRAFT"),
        ("STR-2025-039","TXN-8799","Al-Noor Holdings",  67000, 81,"SUBMITTED"),
    ]
    for s in demo_str:
        c.execute("""
            INSERT INTO str_reports (id,transaction_id,customer_name,amount,risk_score,status,created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (*s, now.isoformat()))

    conn.commit()
    conn.close()
    print("✅ Demo data seeded successfully")

# ─── TRANSACTION CRUD ─────────────────────────────────────────

def save_transaction(data: dict, analysis: dict) -> str:
    conn = get_db()
    c    = conn.cursor()
    tx_id = analysis["transaction_id"]
    c.execute("""
        INSERT OR REPLACE INTO transactions
        (id,customer_id,customer_name,amount,currency,tx_type,country,hour,
         tx_count_30d,account_age,kyc_status,prev_flagged,is_pep,
         risk_score,risk_level,flags,recommendation,tree_scores,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        tx_id,
        data.get("customer_id",""),
        data.get("customer_name","Unknown"),
        data.get("amount",0),
        data.get("currency","USD"),
        data.get("type",""),
        data.get("country",""),
        data.get("hour",12),
        data.get("tx_count_30d",0),
        data.get("account_age_months",12),
        data.get("kyc_status",1),
        int(data.get("previously_flagged",False)),
        int(data.get("is_pep",False)),
        analysis["score"],
        analysis["risk_level"],
        json.dumps(analysis["flags"]),
        json.dumps(analysis["recommendation"]),
        json.dumps(analysis["tree_scores"]),
        analysis["timestamp"],
    ))

    # Auto-create alert for HIGH+ risk
    if analysis["risk_level"] in ("HIGH","CRITICAL"):
        top_flag = analysis["flags"][0] if analysis["flags"] else {}
        alert_id = f"ALT-{random.randint(100,999)}"
        c.execute("""
            INSERT INTO alerts (id,transaction_id,alert_type,customer_name,amount,description,risk_level,status,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            alert_id, tx_id,
            top_flag.get("code","Risk Detected").replace("_"," ").title(),
            data.get("customer_name","Unknown"),
            data.get("amount",0),
            top_flag.get("description","Suspicious activity detected"),
            analysis["risk_level"],
            "OPEN",
            analysis["timestamp"],
        ))

    conn.commit()
    conn.close()
    return tx_id

def get_transactions(limit=50, risk_level=None):
    conn = get_db()
    c    = conn.cursor()
    if risk_level:
        c.execute("SELECT * FROM transactions WHERE risk_level=? ORDER BY created_at DESC LIMIT ?", (risk_level, limit))
    else:
        c.execute("SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_transaction(tx_id: str):
    conn = get_db()
    c    = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE id=?", (tx_id,))
    row  = c.fetchone()
    conn.close()
    return dict(row) if row else None

# ─── ALERTS CRUD ──────────────────────────────────────────────

def get_alerts(status=None, limit=50):
    conn = get_db()
    c    = conn.cursor()
    if status:
        c.execute("SELECT * FROM alerts WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, limit))
    else:
        c.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def resolve_alert(alert_id: str):
    conn = get_db()
    c    = conn.cursor()
    c.execute("UPDATE alerts SET status='RESOLVED', resolved_at=? WHERE id=?",
              (datetime.utcnow().isoformat(), alert_id))
    conn.commit()
    conn.close()

# ─── STR REPORTS CRUD ────────────────────────────────────────

def create_str_report(tx_id: str, analysis: dict, tx_data: dict) -> str:
    conn    = get_db()
    c       = conn.cursor()
    str_id  = f"STR-{datetime.utcnow().strftime('%Y')}-{random.randint(100,999)}"
    c.execute("""
        INSERT INTO str_reports
        (id,transaction_id,customer_name,amount,risk_score,flags,recommendation,status,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        str_id, tx_id,
        tx_data.get("customer_name","Unknown"),
        tx_data.get("amount",0),
        analysis["score"],
        json.dumps(analysis["flags"]),
        json.dumps(analysis["recommendation"]),
        "DRAFT",
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()
    return str_id

def get_str_reports(limit=50):
    conn = get_db()
    c    = conn.cursor()
    c.execute("SELECT * FROM str_reports ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def submit_str_report(str_id: str):
    conn = get_db()
    c    = conn.cursor()
    c.execute("UPDATE str_reports SET status='SUBMITTED', submitted_at=? WHERE id=?",
              (datetime.utcnow().isoformat(), str_id))
    conn.commit()
    conn.close()

# ─── DASHBOARD STATS ─────────────────────────────────────────

def get_dashboard_stats() -> dict:
    conn = get_db()
    c    = conn.cursor()

    c.execute("SELECT COUNT(*) FROM transactions WHERE risk_level IN ('HIGH','CRITICAL')")
    high = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM transactions WHERE risk_level='MEDIUM'")
    medium = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM transactions WHERE risk_level='LOW'")
    cleared = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE risk_level IN ('HIGH','CRITICAL')")
    flagged_amount = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM alerts WHERE status='OPEN'")
    open_alerts = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM str_reports")
    str_count = c.fetchone()[0]

    conn.close()
    return {
        "high_risk":      high,
        "medium_risk":    medium,
        "cleared":        cleared,
        "flagged_amount": round(flagged_amount, 2),
        "open_alerts":    open_alerts,
        "str_reports":    str_count,
        "total":          high + medium + cleared,
    }
