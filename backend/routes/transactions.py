"""
ShieldAML — Transaction Routes
POST /api/transactions/analyze  — analyze a new transaction
GET  /api/transactions          — list all transactions
GET  /api/transactions/{id}     — get single transaction
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from backend.ml_model import analyze_transaction
from backend.database import save_transaction, get_transactions, get_transaction

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

class TransactionInput(BaseModel):
    transaction_id:      Optional[str]  = None
    customer_id:         Optional[str]  = None
    customer_name:       Optional[str]  = "Unknown Customer"
    amount:              float          = Field(..., gt=0, description="Transaction amount in USD")
    currency:            Optional[str]  = "USD"
    type:                str            = Field(..., description="wire|cash|crypto|insurance|internal")
    country:             str            = Field(..., description="ISO 2-letter country code")
    hour:                int            = Field(12, ge=0, le=23)
    tx_count_30d:        int            = Field(0, ge=0)
    account_age_months:  int            = Field(12, ge=0)
    kyc_status:          int            = Field(1, ge=0, le=2)
    previously_flagged:  bool           = False
    is_pep:              bool           = False

@router.post("/analyze")
def analyze(tx: TransactionInput):
    """Analyze a transaction and return full risk assessment."""
    data     = tx.dict()
    analysis = analyze_transaction(data)
    tx_id    = save_transaction(data, analysis)
    return {"success": True, "transaction_id": tx_id, "analysis": analysis}

@router.get("/")
def list_transactions(limit: int = 50, risk_level: Optional[str] = None):
    """List all transactions with optional risk_level filter."""
    return {"transactions": get_transactions(limit, risk_level)}

@router.get("/{tx_id}")
def get_one(tx_id: str):
    """Get a single transaction by ID."""
    tx = get_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx
