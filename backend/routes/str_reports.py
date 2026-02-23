"""
ShieldAML — STR Report Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import get_str_reports, create_str_report, submit_str_report, get_transaction
from backend.ml_model  import analyze_transaction

router = APIRouter(prefix="/api/str", tags=["STR Reports"])

class STRRequest(BaseModel):
    transaction_id: str

@router.get("/")
def list_str_reports(limit: int = 50):
    return {"reports": get_str_reports(limit)}

@router.post("/generate")
def generate_str(req: STRRequest):
    tx = get_transaction(req.transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    import json
    analysis = {
        "score":      tx["risk_score"],
        "risk_level": tx["risk_level"],
        "flags":      json.loads(tx["flags"] or "[]"),
        "recommendation": json.loads(tx["recommendation"] or "{}"),
        "tree_scores": json.loads(tx["tree_scores"] or "{}"),
    }
    str_id = create_str_report(req.transaction_id, analysis, tx)
    return {"success": True, "str_id": str_id}

@router.patch("/{str_id}/submit")
def submit(str_id: str):
    submit_str_report(str_id)
    return {"success": True, "message": f"STR {str_id} submitted to EIFIU"}
