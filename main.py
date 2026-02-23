"""
ShieldAML — Main Server (Pure Python — works on Python 3.13)
AML Fraud Detection + BNPL Fraud Detection
"""
import json, sys, os, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
sys.path.insert(0, os.path.dirname(__file__))

from backend.ml_model import analyze_transaction, analyze_kyc
from backend.database import (
    init_db, get_dashboard_stats, save_transaction,
    get_transactions, get_transaction,
    get_alerts, resolve_alert,
    get_str_reports, create_str_report, submit_str_report
)
from backend.bnpl.bnpl_model import analyze_bnpl
from backend.bnpl.bnpl_database import (
    init_bnpl_tables, save_bnpl_application,
    get_bnpl_applications, get_bnpl_alerts, get_bnpl_stats
)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{args[1]}] {args[0]}")

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, ctype):
        try:
            with open(path, "rb") as f: body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_json({"error": "Not found"}, 404)

    def read_body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path   = self.path.split("?")[0].rstrip("/")
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))

        # ── AML ROUTES ──────────────────────────────────────
        if path == "/api/health":
            return self.send_json({"status":"online","system":"ShieldAML","version":"2.0.0",
                                   "modules":["AML","BNPL"],"compliance":"FATF 2023 · FRA Law 161/2024"})
        if path == "/api/dashboard":
            return self.send_json(get_dashboard_stats())
        if path == "/api/transactions":
            return self.send_json({"transactions": get_transactions(int(params.get("limit",50)), params.get("risk_level"))})
        if path.startswith("/api/transactions/"):
            tx = get_transaction(path.split("/api/transactions/")[1])
            return self.send_json(tx) if tx else self.send_json({"error":"Not found"},404)
        if path == "/api/alerts":
            return self.send_json({"alerts": get_alerts(params.get("status"), int(params.get("limit",50)))})
        if path == "/api/str":
            return self.send_json({"reports": get_str_reports()})

        # ── BNPL ROUTES ─────────────────────────────────────
        if path == "/api/bnpl/dashboard":
            return self.send_json(get_bnpl_stats())
        if path == "/api/bnpl/applications":
            return self.send_json({"applications": get_bnpl_applications(
                int(params.get("limit",50)), params.get("risk_level"))})
        if path == "/api/bnpl/alerts":
            return self.send_json({"alerts": get_bnpl_alerts(
                params.get("status"), int(params.get("limit",50)))})

        if path == "/api/docs":
            return self.send_json({
                "ShieldAML API": "v2.0.0",
                "modules": {
                    "AML": ["POST /api/transactions/analyze","GET /api/transactions",
                            "GET /api/alerts","POST /api/kyc/check","POST /api/str/generate"],
                    "BNPL":["POST /api/bnpl/analyze","GET /api/bnpl/applications",
                            "GET /api/bnpl/alerts","GET /api/bnpl/dashboard"]
                }
            })

        # Serve frontend
        fe = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
        if os.path.exists(fe): return self.send_file(fe, "text/html")
        self.send_json({"error":"Not found"},404)

    def do_POST(self):
        path = self.path.rstrip("/")
        body = self.read_body()
        try:
            # ── AML ─────────────────────────────────────────
            if path == "/api/transactions/analyze":
                analysis = analyze_transaction(body)
                tx_id    = save_transaction(body, analysis)
                return self.send_json({"success":True,"transaction_id":tx_id,"analysis":analysis})

            if path == "/api/kyc/check":
                return self.send_json({"success":True,"result":analyze_kyc(body)})

            if path == "/api/str/generate":
                tx = get_transaction(body.get("transaction_id",""))
                if not tx: return self.send_json({"error":"Transaction not found"},404)
                analysis = {"score":tx["risk_score"],"risk_level":tx["risk_level"],
                            "flags":json.loads(tx["flags"] or "[]"),
                            "recommendation":json.loads(tx["recommendation"] or "{}"),
                            "tree_scores":json.loads(tx["tree_scores"] or "{}")}
                return self.send_json({"success":True,
                    "str_id":create_str_report(body.get("transaction_id"), analysis, tx)})

            # ── BNPL ─────────────────────────────────────────
            if path == "/api/bnpl/analyze":
                analysis = analyze_bnpl(body)
                app_id   = save_bnpl_application(body, analysis)
                return self.send_json({"success":True,"application_id":app_id,"analysis":analysis})

        except Exception as e:
            return self.send_json({"error":str(e)},500)
        self.send_json({"error":"Not found"},404)

    def do_PATCH(self):
        path = self.path.rstrip("/")
        if "/api/alerts/" in path and path.endswith("/resolve"):
            resolve_alert(path.split("/api/alerts/")[1].replace("/resolve",""))
            return self.send_json({"success":True})
        if "/api/str/" in path and path.endswith("/submit"):
            submit_str_report(path.split("/api/str/")[1].replace("/submit",""))
            return self.send_json({"success":True})
        self.send_json({"error":"Not found"},404)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    init_db()
    init_bnpl_tables()
    print(f"✅ ShieldAML v2.0 started — AML + BNPL modules active")
    print(f"🚀 Running on http://0.0.0.0:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
