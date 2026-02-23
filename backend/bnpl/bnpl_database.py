"""
ShieldAML — BNPL Database Layer
"""
import sqlite3, json, random
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "shieldaml.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_bnpl_tables():
    conn = get_db()
    c    = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS bnpl_applications (
        id                  TEXT PRIMARY KEY,
        customer_name       TEXT,
        amount              REAL,
        credit_limit        REAL,
        purchase_category   TEXT,
        merchant_name       TEXT,
        risk_score          INTEGER,
        risk_level          TEXT,
        primary_fraud       TEXT,
        flags               TEXT,
        recommendation      TEXT,
        tree_scores         TEXT,
        blocked             INTEGER DEFAULT 0,
        created_at          TEXT
    );

    CREATE TABLE IF NOT EXISTS bnpl_alerts (
        id              TEXT PRIMARY KEY,
        application_id  TEXT,
        fraud_type      TEXT,
        customer_name   TEXT,
        amount          REAL,
        description     TEXT,
        risk_level      TEXT,
        status          TEXT DEFAULT 'OPEN',
        created_at      TEXT
    );
    """)

    # Seed demo data
    c.execute("SELECT COUNT(*) FROM bnpl_applications")
    if c.fetchone()[0] == 0:
        _seed_bnpl_demo(c)

    conn.commit()
    conn.close()

def _seed_bnpl_demo(c):
    now = datetime.utcnow()
    demos = [
        ("BNPL-8821","Mohammed Al-Rashid",  4500,5000,"electronics","TechStore Egypt",  88,"CRITICAL","Device Fraud"),
        ("BNPL-8819","Sara Ahmed",           890,1000,"fashion",     "StyleHub",         72,"HIGH",    "Synthetic Identity"),
        ("BNPL-8814","Gulf Trading Co",     2200,2500,"jewelry",     "LuxuryMart",       65,"HIGH",    "Friendly Fraud"),
        ("BNPL-8810","Nour Hassan",          450,1000,"general",     "HomeGoods",        38,"MEDIUM",  "Account Cycling"),
        ("BNPL-8805","Cairo Retail LLC",     120, 500,"fashion",     "FashionWorld",      9,"LOW",     "None Detected"),
    ]
    for d in demos:
        flags_json = json.dumps([{"code":"demo","severity":d[7],"description":f"{d[8]} detected","ref":"FATF 2023"}])
        trees_json = json.dumps({"Synthetic Identity":d[6]-10,"Account Cycling":d[6]-15,
                                  "Friendly Fraud":d[6]-5,"Merchant Collusion":d[6]-20,
                                  "First Payment Default":d[6]-8,"Device Fraud":d[6]-3})
        rec_json   = json.dumps({"action":"REVIEW","str_required":d[7]=="CRITICAL","block_transaction":d[7]=="CRITICAL"})
        c.execute("""INSERT INTO bnpl_applications
            (id,customer_name,amount,credit_limit,purchase_category,merchant_name,
             risk_score,risk_level,primary_fraud,flags,recommendation,tree_scores,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (*d[:9], flags_json, rec_json, trees_json, now.isoformat()))

    alerts = [
        ("BALT-001","BNPL-8821","Device Fraud",       "Mohammed Al-Rashid",4500,"Device linked to 5 identities",  "CRITICAL"),
        ("BALT-002","BNPL-8819","Synthetic Identity",  "Sara Ahmed",         890,"Phone registered 3 days ago",    "HIGH"),
        ("BALT-003","BNPL-8814","Friendly Fraud",      "Gulf Trading Co",   2200,"2 prior chargebacks on record",  "HIGH"),
        ("BALT-004","BNPL-8810","Account Cycling",     "Nour Hassan",        450,"Limit increase after 15 days",   "MEDIUM"),
    ]
    for a in alerts:
        c.execute("""INSERT INTO bnpl_alerts
            (id,application_id,fraud_type,customer_name,amount,description,risk_level,created_at)
            VALUES (?,?,?,?,?,?,?,?)""", (*a, now.isoformat()))

def save_bnpl_application(data: dict, analysis: dict) -> str:
    conn = get_db()
    c    = conn.cursor()
    app_id = analysis["application_id"]
    blocked = 1 if analysis["recommendation"].get("block_transaction") else 0

    c.execute("""INSERT OR REPLACE INTO bnpl_applications
        (id,customer_name,amount,credit_limit,purchase_category,merchant_name,
         risk_score,risk_level,primary_fraud,flags,recommendation,tree_scores,blocked,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        app_id,
        data.get("customer_name","Unknown"),
        data.get("amount",0),
        data.get("credit_limit",1000),
        data.get("purchase_category","general"),
        data.get("merchant_name","Unknown Merchant"),
        analysis["score"],
        analysis["risk_level"],
        analysis["primary_fraud"],
        json.dumps(analysis["flags"]),
        json.dumps(analysis["recommendation"]),
        json.dumps(analysis["tree_scores"]),
        blocked,
        analysis["timestamp"],
    ))

    if analysis["risk_level"] in ("HIGH","CRITICAL"):
        top_flag = analysis["flags"][0] if analysis["flags"] else {}
        c.execute("""INSERT INTO bnpl_alerts
            (id,application_id,fraud_type,customer_name,amount,description,risk_level,status,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""", (
            f"BALT-{random.randint(100,999)}", app_id,
            analysis["primary_fraud"],
            data.get("customer_name","Unknown"),
            data.get("amount",0),
            top_flag.get("description","Suspicious BNPL activity"),
            analysis["risk_level"], "OPEN",
            analysis["timestamp"],
        ))

    conn.commit()
    conn.close()
    return app_id

def get_bnpl_applications(limit=50, risk_level=None):
    conn = get_db()
    c    = conn.cursor()
    if risk_level:
        c.execute("SELECT * FROM bnpl_applications WHERE risk_level=? ORDER BY created_at DESC LIMIT ?", (risk_level,limit))
    else:
        c.execute("SELECT * FROM bnpl_applications ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_bnpl_alerts(status=None, limit=50):
    conn = get_db()
    c    = conn.cursor()
    if status:
        c.execute("SELECT * FROM bnpl_alerts WHERE status=? ORDER BY created_at DESC LIMIT ?", (status,limit))
    else:
        c.execute("SELECT * FROM bnpl_alerts ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_bnpl_stats():
    conn = get_db()
    c    = conn.cursor()
    c.execute("SELECT COUNT(*) FROM bnpl_applications WHERE risk_level IN ('HIGH','CRITICAL')")
    high = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bnpl_applications WHERE risk_level='MEDIUM'")
    medium = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bnpl_applications WHERE risk_level='LOW'")
    low = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bnpl_applications WHERE blocked=1")
    blocked = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(amount),0) FROM bnpl_applications WHERE blocked=1")
    saved = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bnpl_alerts WHERE status='OPEN'")
    open_alerts = c.fetchone()[0]
    conn.close()
    return {"high_risk":high,"medium_risk":medium,"low_risk":low,
            "blocked":blocked,"fraud_prevented_amount":round(saved,2),
            "open_alerts":open_alerts,"total":high+medium+low}
