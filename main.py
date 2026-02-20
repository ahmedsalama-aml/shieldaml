"""
ShieldAML — Main Server
Run locally:  uvicorn main:app --reload
Deploy:       Render.com / Railway.app
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.database import init_db, get_dashboard_stats
from backend.routes.transactions import router as tx_router
from backend.routes.alerts       import router as alert_router
from backend.routes.str_reports  import router as str_router
from backend.routes.kyc          import router as kyc_router

# ─── APP SETUP ────────────────────────────────────────────────
app = FastAPI(
    title       = "ShieldAML API",
    description = "AI-powered AML & Fraud Detection System — FATF & FRA 161/2024 Compliant",
    version     = "1.0.0",
    docs_url    = "/api/docs",
)

# Allow frontend to call backend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─── STARTUP ──────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    print("✅ ShieldAML started — Database ready")

# ─── ROUTES ───────────────────────────────────────────────────
app.include_router(tx_router)
app.include_router(alert_router)
app.include_router(str_router)
app.include_router(kyc_router)

# ─── DASHBOARD STATS ──────────────────────────────────────────
@app.get("/api/dashboard")
def dashboard():
    return get_dashboard_stats()

# ─── HEALTH CHECK ─────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status":  "online",
        "system":  "ShieldAML",
        "version": "1.0.0",
        "compliance": "FATF 2023 · FRA Law 161/2024",
    }

# ─── SERVE FRONTEND ───────────────────────────────────────────
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
