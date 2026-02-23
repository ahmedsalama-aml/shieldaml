"""
ShieldAML — BNPL Fraud Detection Engine
Covers: Synthetic Identity, Account Cycling, Friendly Fraud,
        Merchant Collusion, First Payment Default, Device Fraud
Author: Ahmed Salama (CAMS)
"""

from datetime import datetime
import random

# ─── BNPL FRAUD TYPES ────────────────────────────────────────
BNPL_FRAUD_TYPES = {
    "synthetic_identity":    "Synthetic Identity Fraud — fake/combined identity detected",
    "account_cycling":       "Account Cycling — borrow, repay minimally, max out pattern",
    "friendly_fraud":        "Friendly Fraud — chargeback abuse suspected",
    "merchant_collusion":    "Merchant Collusion — fake merchant/customer relationship",
    "first_payment_default": "First Payment Default — no intent to repay detected",
    "device_fraud":          "Device Fraud — same device linked to multiple identities",
    "bot_application":       "Bot/Automated Application — non-human behavior detected",
    "velocity_abuse":        "Application Velocity Abuse — multiple applications detected",
}

BNPL_RED_FLAGS = {
    "new_phone_number":        "Phone number registered less than 30 days ago",
    "new_email":               "Email address created less than 7 days ago",
    "address_mismatch":        "Billing and delivery address never used before",
    "max_first_purchase":      "Maximum credit limit used on very first transaction",
    "early_limit_increase":    "Credit limit increase requested within first 30 days",
    "payment_stop":            "Payments stopped suddenly after 2-3 installments",
    "chargeback_history":      "Customer has prior chargeback on record",
    "device_multi_identity":   "Device linked to more than 2 different identities",
    "merchant_new_high_vol":   "New merchant with unusually high transaction volume",
    "merchant_customer_device":"Merchant and customer share same device fingerprint",
    "copy_paste_fields":       "All form fields filled via copy-paste (stolen data signal)",
    "vpn_detected":            "VPN or proxy detected during application",
    "night_application":       "Application submitted between midnight and 5am",
    "fast_form_completion":    "Application completed in under 60 seconds (bot signal)",
    "category_shift":          "Sudden shift in purchase categories",
    "instant_high_value":      "High-value electronics/jewelry on first purchase",
    "no_credit_history":       "No credit history found anywhere",
    "multiple_applications":   "More than 2 BNPL applications in 30 days",
}

# ─── FEATURE EXTRACTION ──────────────────────────────────────

def extract_bnpl_features(data: dict) -> dict:
    """Extract and normalize BNPL-specific features."""
    return {
        # Identity signals
        "phone_age_days":        int(data.get("phone_age_days", 90)),
        "email_age_days":        int(data.get("email_age_days", 90)),
        "has_credit_history":    bool(data.get("has_credit_history", True)),
        "address_verified":      bool(data.get("address_verified", True)),
        "id_age_match":          bool(data.get("id_age_match", True)),

        # Transaction signals
        "amount":                float(data.get("amount", 0)),
        "credit_limit":          float(data.get("credit_limit", 1000)),
        "is_first_purchase":     bool(data.get("is_first_purchase", False)),
        "purchase_category":     str(data.get("purchase_category", "general")).lower(),
        "prev_category":         str(data.get("prev_category", "general")).lower(),
        "merchant_age_days":     int(data.get("merchant_age_days", 180)),
        "merchant_monthly_vol":  float(data.get("merchant_monthly_vol", 10000)),

        # Payment behavior
        "missed_payments":       int(data.get("missed_payments", 0)),
        "total_installments":    int(data.get("total_installments", 0)),
        "paid_installments":     int(data.get("paid_installments", 0)),
        "days_since_first_pay":  int(data.get("days_since_first_pay", 90)),
        "limit_increase_days":   int(data.get("limit_increase_days", 999)),
        "chargeback_count":      int(data.get("chargeback_count", 0)),

        # Device & behavior signals
        "device_identity_count": int(data.get("device_identity_count", 1)),
        "same_device_merchant":  bool(data.get("same_device_merchant", False)),
        "vpn_detected":          bool(data.get("vpn_detected", False)),
        "form_seconds":          int(data.get("form_seconds", 180)),
        "copy_paste_fields":     bool(data.get("copy_paste_fields", False)),
        "application_hour":      int(data.get("application_hour", 12)),
        "applications_30d":      int(data.get("applications_30d", 1)),

        # Computed
        "limit_utilization":     float(data.get("amount", 0)) / max(float(data.get("credit_limit", 1000)), 1),
        "payment_rate":          float(data.get("paid_installments", 0)) / max(float(data.get("total_installments", 1)), 1),
    }

# ─── FRAUD TYPE DETECTORS ────────────────────────────────────

def detect_synthetic_identity(f: dict) -> float:
    score = 0.0
    if f["phone_age_days"] < 30:   score += 35
    elif f["phone_age_days"] < 60: score += 15
    if f["email_age_days"] < 7:    score += 30
    elif f["email_age_days"] < 30: score += 15
    if not f["has_credit_history"]: score += 25
    if not f["address_verified"]:   score += 20
    if not f["id_age_match"]:       score += 30
    return min(score, 100)

def detect_account_cycling(f: dict) -> float:
    score = 0.0
    if f["limit_increase_days"] < 30:  score += 35
    if f["limit_utilization"] > 0.90:  score += 25
    if f["missed_payments"] > 0 and f["paid_installments"] <= 3: score += 40
    if f["payment_rate"] < 0.3 and f["total_installments"] > 3:  score += 30
    if f["purchase_category"] != f["prev_category"] and f["limit_utilization"] > 0.8: score += 20
    return min(score, 100)

def detect_friendly_fraud(f: dict) -> float:
    score = 0.0
    if f["chargeback_count"] >= 2:  score += 60
    elif f["chargeback_count"] == 1: score += 30
    if f["purchase_category"] in ("electronics", "jewelry", "luxury"): score += 20
    if f["is_first_purchase"] and f["chargeback_count"] > 0: score += 25
    if f["limit_utilization"] > 0.8 and f["chargeback_count"] > 0: score += 20
    return min(score, 100)

def detect_merchant_collusion(f: dict) -> float:
    score = 0.0
    if f["same_device_merchant"]:      score += 60
    if f["merchant_age_days"] < 30:    score += 35
    elif f["merchant_age_days"] < 90:  score += 15
    if f["merchant_monthly_vol"] > 50000 and f["merchant_age_days"] < 60: score += 30
    if f["is_first_purchase"] and f["merchant_age_days"] < 30: score += 20
    return min(score, 100)

def detect_first_payment_default(f: dict) -> float:
    score = 0.0
    if f["is_first_purchase"] and f["limit_utilization"] > 0.90: score += 45
    if not f["has_credit_history"] and f["amount"] > 500:        score += 30
    if f["phone_age_days"] < 30 and f["is_first_purchase"]:      score += 25
    if f["missed_payments"] >= 1 and f["paid_installments"] == 0: score += 50
    if f["application_hour"] < 5 and f["is_first_purchase"]:     score += 15
    return min(score, 100)

def detect_device_fraud(f: dict) -> float:
    score = 0.0
    if f["device_identity_count"] >= 5:  score += 70
    elif f["device_identity_count"] >= 3: score += 40
    elif f["device_identity_count"] >= 2: score += 20
    if f["vpn_detected"]:                 score += 25
    if f["copy_paste_fields"]:            score += 20
    if f["form_seconds"] < 30:            score += 35
    elif f["form_seconds"] < 60:          score += 20
    if f["applications_30d"] > 3:         score += 25
    return min(score, 100)

# ─── ENSEMBLE SCORING ────────────────────────────────────────

def bnpl_random_forest(features: dict) -> dict:
    """
    BNPL-specific Random Forest ensemble.
    6 specialized trees — one per fraud type.
    """
    trees = {
        "Synthetic Identity":    (detect_synthetic_identity(features),    0.20),
        "Account Cycling":       (detect_account_cycling(features),       0.18),
        "Friendly Fraud":        (detect_friendly_fraud(features),        0.15),
        "Merchant Collusion":    (detect_merchant_collusion(features),    0.17),
        "First Payment Default": (detect_first_payment_default(features), 0.18),
        "Device Fraud":          (detect_device_fraud(features),          0.12),
    }

    weighted = sum(score * weight for score, weight in trees.values())
    final    = round(min(weighted, 100))

    risk_level = (
        "CRITICAL" if final >= 75 else
        "HIGH"     if final >= 55 else
        "MEDIUM"   if final >= 30 else
        "LOW"
    )

    return {
        "score":      final,
        "risk_level": risk_level,
        "trees":      {name: round(score) for name, (score, _) in trees.items()},
    }

# ─── FLAG DETECTION ──────────────────────────────────────────

def detect_bnpl_flags(f: dict) -> list:
    flags = []

    if f["phone_age_days"] < 30:
        flags.append({"code":"new_phone_number","severity":"HIGH",
                      "description": BNPL_RED_FLAGS["new_phone_number"],"ref":"FATF Rec. 10"})
    if f["email_age_days"] < 7:
        flags.append({"code":"new_email","severity":"HIGH",
                      "description": BNPL_RED_FLAGS["new_email"],"ref":"FATF Rec. 10"})
    if not f["has_credit_history"]:
        flags.append({"code":"no_credit_history","severity":"MEDIUM",
                      "description": BNPL_RED_FLAGS["no_credit_history"],"ref":"FATF Rec. 10"})
    if not f["id_age_match"]:
        flags.append({"code":"address_mismatch","severity":"HIGH",
                      "description": BNPL_RED_FLAGS["address_mismatch"],"ref":"FATF Rec. 10"})
    if f["is_first_purchase"] and f["limit_utilization"] > 0.90:
        flags.append({"code":"max_first_purchase","severity":"HIGH",
                      "description": BNPL_RED_FLAGS["max_first_purchase"],"ref":"FATF Typologies 2023"})
    if f["limit_increase_days"] < 30:
        flags.append({"code":"early_limit_increase","severity":"HIGH",
                      "description": BNPL_RED_FLAGS["early_limit_increase"],"ref":"FATF Typologies 2023"})
    if f["missed_payments"] > 0 and f["paid_installments"] <= 3:
        flags.append({"code":"payment_stop","severity":"CRITICAL",
                      "description": BNPL_RED_FLAGS["payment_stop"],"ref":"FRA Law 161/2024"})
    if f["chargeback_count"] >= 1:
        flags.append({"code":"chargeback_history","severity":"HIGH",
                      "description": BNPL_RED_FLAGS["chargeback_history"],"ref":"FATF Typologies 2023"})
    if f["device_identity_count"] >= 3:
        flags.append({"code":"device_multi_identity","severity":"CRITICAL",
                      "description": BNPL_RED_FLAGS["device_multi_identity"],"ref":"FATF Rec. 16"})
    if f["same_device_merchant"]:
        flags.append({"code":"merchant_customer_device","severity":"CRITICAL",
                      "description": BNPL_RED_FLAGS["merchant_customer_device"],"ref":"FATF Typologies 2023"})
    if f["vpn_detected"]:
        flags.append({"code":"vpn_detected","severity":"MEDIUM",
                      "description": BNPL_RED_FLAGS["vpn_detected"],"ref":"FATF Rec. 16"})
    if f["form_seconds"] < 60:
        flags.append({"code":"fast_form_completion","severity":"MEDIUM",
                      "description": BNPL_RED_FLAGS["fast_form_completion"],"ref":"FATF Typologies 2023"})
    if f["copy_paste_fields"]:
        flags.append({"code":"copy_paste_fields","severity":"HIGH",
                      "description": BNPL_RED_FLAGS["copy_paste_fields"],"ref":"FATF Rec. 10"})
    if f["application_hour"] < 5:
        flags.append({"code":"night_application","severity":"LOW",
                      "description": BNPL_RED_FLAGS["night_application"],"ref":"FATF Typologies 2023"})
    if f["applications_30d"] > 3:
        flags.append({"code":"multiple_applications","severity":"HIGH",
                      "description": BNPL_RED_FLAGS["multiple_applications"],"ref":"FATF Rec. 20"})
    if f["merchant_age_days"] < 30:
        flags.append({"code":"merchant_new_high_vol","severity":"HIGH",
                      "description": BNPL_RED_FLAGS["merchant_new_high_vol"],"ref":"FATF Typologies 2023"})
    if f["purchase_category"] in ("electronics","jewelry","luxury") and f["is_first_purchase"]:
        flags.append({"code":"instant_high_value","severity":"MEDIUM",
                      "description": BNPL_RED_FLAGS["instant_high_value"],"ref":"FATF Typologies 2023"})

    if not flags:
        flags.append({"code":"clean","severity":"NONE",
                      "description":"No BNPL fraud indicators detected","ref":"N/A"})
    return flags

# ─── RECOMMENDATION ──────────────────────────────────────────

def get_bnpl_recommendation(risk_level: str, trees: dict) -> dict:
    top_fraud = max(trees, key=trees.get)
    actions = {
        "CRITICAL": {
            "action": "BLOCK & INVESTIGATE",
            "steps": [
                "Block transaction immediately",
                f"Primary fraud type detected: {top_fraud}",
                "Freeze customer account pending investigation",
                "Escalate to fraud team within 1 hour",
                "File STR if money laundering suspected",
                "Preserve all device and session data for investigation",
                "Do NOT inform customer — preserve investigation integrity",
            ],
            "str_required": True, "block_transaction": True,
        },
        "HIGH": {
            "action": "HOLD & VERIFY",
            "steps": [
                "Hold transaction pending manual review",
                f"Primary concern: {top_fraud}",
                "Request additional identity verification from customer",
                "Verify merchant legitimacy independently",
                "Review full customer application data",
                "Decision required within 4 hours",
            ],
            "str_required": False, "block_transaction": False,
        },
        "MEDIUM": {
            "action": "MONITOR & VERIFY",
            "steps": [
                "Allow transaction with enhanced monitoring",
                f"Watch for: {top_fraud}",
                "Set account for elevated monitoring for 30 days",
                "Request proof of delivery on completion",
                "Flag for review if next transaction also flags",
            ],
            "str_required": False, "block_transaction": False,
        },
        "LOW": {
            "action": "PROCEED",
            "steps": [
                "Transaction appears legitimate",
                "Continue standard monitoring",
                "No immediate action required",
            ],
            "str_required": False, "block_transaction": False,
        },
    }
    return actions.get(risk_level, actions["LOW"])

# ─── MAIN ANALYZE FUNCTION ───────────────────────────────────

def analyze_bnpl(data: dict) -> dict:
    """Full BNPL fraud analysis pipeline."""
    features       = extract_bnpl_features(data)
    prediction     = bnpl_random_forest(features)
    flags          = detect_bnpl_flags(features)
    recommendation = get_bnpl_recommendation(prediction["risk_level"], prediction["trees"])

    # Determine primary fraud type
    primary_fraud = max(prediction["trees"], key=prediction["trees"].get)
    primary_score = prediction["trees"][primary_fraud]

    return {
        "application_id":  data.get("application_id", f"BNPL-{random.randint(10000,99999)}"),
        "customer_name":   data.get("customer_name", "Unknown"),
        "timestamp":       datetime.utcnow().isoformat(),
        "score":           prediction["score"],
        "risk_level":      prediction["risk_level"],
        "primary_fraud":   primary_fraud if primary_score > 20 else "None Detected",
        "tree_scores":     prediction["trees"],
        "flags":           flags,
        "flag_count":      len([f for f in flags if f["code"] != "clean"]),
        "recommendation":  recommendation,
        "model":           "ShieldAML-BNPL-RF-v1.0",
        "compliance_ref":  "FATF 2023 · FRA Law 161/2024 · CBE BNPL Guidelines",
    }
