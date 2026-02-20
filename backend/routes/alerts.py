"""
ShieldAML — Alerts Routes
"""
from fastapi import APIRouter, HTTPException
from backend.database import get_alerts, resolve_alert

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

@router.get("/")
def list_alerts(status: str = None, limit: int = 50):
    return {"alerts": get_alerts(status, limit)}

@router.patch("/{alert_id}/resolve")
def resolve(alert_id: str):
    resolve_alert(alert_id)
    return {"success": True, "message": f"Alert {alert_id} resolved"}
