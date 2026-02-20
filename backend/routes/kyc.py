"""
ShieldAML — KYC Routes
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.ml_model import analyze_kyc

router = APIRouter(prefix="/api/kyc", tags=["KYC"])

class KYCInput(BaseModel):
    name:        str
    nationality: Optional[str] = ""
    occupation:  Optional[str] = ""
    country:     Optional[str] = ""
    dob:         Optional[str] = ""
    id_number:   Optional[str] = ""

@router.post("/check")
def check_kyc(data: KYCInput):
    result = analyze_kyc(data.dict())
    return {"success": True, "result": result}
