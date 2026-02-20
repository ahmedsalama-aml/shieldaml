"""
ShieldAML — Random Forest Fraud Detection Engine
Author: Ahmed Salama (CAMS)
Compliant with: FATF Recommendations, Egyptian FRA Law 161/2024
"""

import random
import math
from datetime import datetime

# ─── CONSTANTS ───────────────────────────────────────────────
SANCTIONED_COUNTRIES = {'ir', 'kp', 'ru', 'sy', 'sd', 'by', 'cu', 'mm'}
HIGH_RISK_COUNTRIES  = {'ir', 'kp', 'ru', 'sy', 'sd', 'pk', 'af', 'by', 'cu', 'mm', 'iq', 'ly', 'ye', 'so'}
NORMAL_COUNTRIES     = {'ae', 'sa', 'eg', 'us', 'uk', 'de', 'fr', 'jp', 'sg', 'au', 'ca', 'ch', 'nl'}

REPORTING_THRESHOLD  = 10_000   # USD — mandatory reporting above this
STRUCTURING_LIMIT    = 9_500    # USD — structuring detection threshold

FATF_RED_FLAGS = {
    "sanctioned_country":     "Transaction to/from FATF sanctioned jurisdiction",
    "high_risk_country":      "Destination is FATF high-risk jurisdiction",
    "night_transaction":      "Transaction executed during unusual hours (00:00–05:59)",
    "threshold_breach":       "Amount exceeds mandatory reporting threshold ($10,000)",
    "structuring_suspected":  "Amount near reporting threshold — possible structuring",
    "new_account_large":      "Large transaction from recently opened account",
    "high_velocity":          "Abnormally high transaction frequency in 30-day period",
    "incomplete_kyc":         "Customer identity not fully verified (incomplete KYC)",
    "repeat_offender":        "Customer has prior suspicious activity on record",
    "crypto_highrisk":        "Cryptocurrency transfer to high-risk jurisdiction",
    "cash_threshold":         "Large cash transaction near reporting threshold",
    "pep_linked":             "Customer linked to Politically Exposed Person (PEP)",
    "round_amount":           "Suspiciously round transaction amount",
    "multiple_countries":     "Transactions to multiple countries in short period",
}

# ─── FEATURE EXTRACTION ──────────────────────────────────────

def extract_features(data: dict) -> dict:
    """Convert raw transaction input into ML features."""
    amount       = float(data.get("amount", 0))
    country      = str(data.get("country", "")).lower()
    tx_type      = str(data.get("type", "")).lower()
    hour         = int(data.get("hour", 12))
    tx_count     = int(data.get("tx_count_30d", 0))
    account_age  = int(data.get("account_age_months", 12))
    kyc_status   = int(data.get("kyc_status", 1))   # 0=incomplete,1=verified,2=edd
    prev_flagged = bool(data.get("previously_flagged", False))
    is_pep       = bool(data.get("is_pep", False))

    return {
        "amount":           amount,
        "country":          country,
        "tx_type":          tx_type,
        "hour":             hour,
        "tx_count":         tx_count,
        "account_age":      account_age,
        "kyc_status":       kyc_status,
        "prev_flagged":     prev_flagged,
        "is_pep":           is_pep,
        "is_sanctioned":    country in SANCTIONED_COUNTRIES,
        "is_high_risk":     country in HIGH_RISK_COUNTRIES,
        "is_night":         hour < 6,
        "above_threshold":  amount >= REPORTING_THRESHOLD,
        "near_threshold":   STRUCTURING_LIMIT <= amount < REPORTING_THRESHOLD,
        "is_new_account":   account_age < 3,
        "is_high_velocity": tx_count > 15,
        "is_round_amount":  amount > 1000 and amount % 1000 == 0,
        "kyc_incomplete":   kyc_status == 0,
    }

# ─── DECISION TREES ──────────────────────────────────────────

def tree_sanctions_amount(f: dict) -> float:
    """Tree 1: Focused on sanctions and transaction amount."""
    score = 0.0
    if f["is_sanctioned"]:    score += 45
    elif f["is_high_risk"]:   score += 20
    if f["amount"] > 100_000: score += 25
    elif f["amount"] > 50_000: score += 18
    elif f["amount"] > 10_000: score += 10
    if f["is_night"]:         score += 15
    if f["above_threshold"]:  score += 10
    return min(score, 100)

def tree_account_behavior(f: dict) -> float:
    """Tree 2: Focused on account age and behavioral patterns."""
    score = 0.0
    if f["is_new_account"]:   score += 30
    if f["is_high_velocity"]: score += 20
    if f["prev_flagged"]:     score += 30
    if f["kyc_incomplete"]:   score += 25
    if f["is_pep"]:           score += 20
    if f["is_round_amount"]:  score += 10
    return min(score, 100)

def tree_type_country_combo(f: dict) -> float:
    """Tree 3: Focused on transaction type + country combination."""
    score = 0.0
    if f["tx_type"] == "crypto" and f["is_high_risk"]:  score += 55
    if f["tx_type"] == "cash"   and f["near_threshold"]: score += 40
    if f["tx_type"] == "wire"   and f["is_sanctioned"]:  score += 50
    if f["tx_type"] == "insurance" and f["amount"] > 100_000: score += 25
    if f["tx_type"] == "crypto" and f["is_sanctioned"]:  score += 60
    if f["is_high_risk"] and f["is_night"]:              score += 20
    return min(score, 100)

def tree_kyc_velocity(f: dict) -> float:
    """Tree 4: Focused on KYC and transaction velocity."""
    score = 0.0
    if f["kyc_incomplete"] and f["amount"] > 5_000:  score += 40
    if f["is_high_velocity"] and f["is_new_account"]: score += 40
    if f["prev_flagged"] and f["amount"] > 10_000:  score += 35
    if f["is_pep"] and f["above_threshold"]:          score += 30
    if f["near_threshold"]:                           score += 15
    return min(score, 100)

def tree_anomaly_isolation(f: dict) -> float:
    """Tree 5: Isolation Forest — anomaly detection based on combined risk factors."""
    risk_signals = [
        f["is_night"],
        f["is_new_account"],
        f["amount"] > 25_000,
        f["is_high_risk"],
        f["prev_flagged"],
        f["kyc_incomplete"],
        f["is_high_velocity"],
        f["is_pep"],
    ]
    combo_score = sum(risk_signals) * 12
    if sum(risk_signals) >= 4: combo_score += 15   # Anomaly spike for 4+ signals
    return min(combo_score, 100)

# ─── RANDOM FOREST ENSEMBLE ───────────────────────────────────

def random_forest_predict(features: dict) -> dict:
    """
    Ensemble of 5 decision trees with weighted voting.
    Each tree focuses on a different fraud dimension.
    Final score = weighted average of all trees.
    """
    trees = {
        "Sanctions & Amount":    (tree_sanctions_amount(features),   0.25),
        "Account Behavior":      (tree_account_behavior(features),   0.20),
        "Type & Country Combo":  (tree_type_country_combo(features), 0.25),
        "KYC & Velocity":        (tree_kyc_velocity(features),       0.15),
        "Anomaly Detection":     (tree_anomaly_isolation(features),  0.15),
    }

    weighted_score = sum(score * weight for score, weight in trees.values())
    final_score    = round(min(weighted_score, 100))

    risk_level = (
        "CRITICAL" if final_score >= 80 else
        "HIGH"     if final_score >= 60 else
        "MEDIUM"   if final_score >= 35 else
        "LOW"
    )

    return {
        "score":      final_score,
        "risk_level": risk_level,
        "trees":      {name: round(score) for name, (score, _) in trees.items()},
    }

# ─── FLAG DETECTION ───────────────────────────────────────────

def detect_flags(features: dict) -> list:
    """Identify all FATF red flags present in this transaction."""
    flags = []

    if features["is_sanctioned"]:
        flags.append({"code": "sanctioned_country", "severity": "CRITICAL",
                      "description": FATF_RED_FLAGS["sanctioned_country"],
                      "fatf_ref": "FATF Recommendation 6"})

    if features["is_high_risk"] and not features["is_sanctioned"]:
        flags.append({"code": "high_risk_country", "severity": "HIGH",
                      "description": FATF_RED_FLAGS["high_risk_country"],
                      "fatf_ref": "FATF Recommendation 19"})

    if features["is_night"]:
        flags.append({"code": "night_transaction", "severity": "MEDIUM",
                      "description": FATF_RED_FLAGS["night_transaction"],
                      "fatf_ref": "FATF Typologies Report 2023"})

    if features["above_threshold"]:
        flags.append({"code": "threshold_breach", "severity": "HIGH",
                      "description": FATF_RED_FLAGS["threshold_breach"],
                      "fatf_ref": "FRA Law 161/2024 Art. 14"})

    if features["near_threshold"]:
        flags.append({"code": "structuring_suspected", "severity": "HIGH",
                      "description": FATF_RED_FLAGS["structuring_suspected"],
                      "fatf_ref": "FATF Recommendation 3"})

    if features["is_new_account"] and features["amount"] > 5000:
        flags.append({"code": "new_account_large", "severity": "HIGH",
                      "description": FATF_RED_FLAGS["new_account_large"],
                      "fatf_ref": "FATF Recommendation 10"})

    if features["is_high_velocity"]:
        flags.append({"code": "high_velocity", "severity": "MEDIUM",
                      "description": FATF_RED_FLAGS["high_velocity"],
                      "fatf_ref": "FATF Typologies Report 2023"})

    if features["kyc_incomplete"]:
        flags.append({"code": "incomplete_kyc", "severity": "HIGH",
                      "description": FATF_RED_FLAGS["incomplete_kyc"],
                      "fatf_ref": "FATF Recommendation 10"})

    if features["prev_flagged"]:
        flags.append({"code": "repeat_offender", "severity": "HIGH",
                      "description": FATF_RED_FLAGS["repeat_offender"],
                      "fatf_ref": "FRA Law 161/2024 Art. 18"})

    if features["tx_type"] == "crypto" and features["is_high_risk"]:
        flags.append({"code": "crypto_highrisk", "severity": "CRITICAL",
                      "description": FATF_RED_FLAGS["crypto_highrisk"],
                      "fatf_ref": "FATF Recommendation 15"})

    if features["is_pep"]:
        flags.append({"code": "pep_linked", "severity": "HIGH",
                      "description": FATF_RED_FLAGS["pep_linked"],
                      "fatf_ref": "FATF Recommendation 12"})

    if features["is_round_amount"] and features["amount"] > 5000:
        flags.append({"code": "round_amount", "severity": "LOW",
                      "description": FATF_RED_FLAGS["round_amount"],
                      "fatf_ref": "FATF Typologies Report 2023"})

    if not flags:
        flags.append({"code": "clean", "severity": "NONE",
                      "description": "No significant FATF red flags detected",
                      "fatf_ref": "N/A"})

    return flags

# ─── RECOMMENDED ACTION ──────────────────────────────────────

def get_recommendation(risk_level: str, flags: list) -> dict:
    """Generate compliance recommendation based on risk level."""
    actions = {
        "CRITICAL": {
            "action":    "FREEZE & REPORT",
            "steps": [
                "Immediately freeze the transaction",
                "File STR with Egyptian Financial Intelligence Unit (EIFIU) within 24 hours",
                "Escalate to MLRO and senior management",
                "Apply Enhanced Due Diligence (EDD) on customer",
                "Document all findings with audit trail",
                "Do NOT tip off the customer (tipping-off offence under FRA 161/2024)",
            ],
            "str_required": True,
            "edd_required": True,
        },
        "HIGH": {
            "action":    "REVIEW & ESCALATE",
            "steps": [
                "Place transaction on hold pending review",
                "Escalate to compliance supervisor",
                "Apply Enhanced Due Diligence (EDD)",
                "Consider filing STR if suspicion confirmed",
                "Request additional documentation from customer",
            ],
            "str_required": False,
            "edd_required": True,
        },
        "MEDIUM": {
            "action":    "ENHANCED MONITORING",
            "steps": [
                "Allow transaction but flag for monitoring",
                "Apply Standard Customer Due Diligence (CDD)",
                "Request source of funds documentation",
                "Increase monitoring frequency for this customer",
            ],
            "str_required": False,
            "edd_required": False,
        },
        "LOW": {
            "action":    "PROCEED — STANDARD MONITORING",
            "steps": [
                "Transaction may proceed",
                "Apply standard CDD procedures",
                "Continue routine monitoring",
            ],
            "str_required": False,
            "edd_required": False,
        },
    }
    return actions.get(risk_level, actions["LOW"])

# ─── MAIN ANALYZE FUNCTION ───────────────────────────────────

def analyze_transaction(data: dict) -> dict:
    """
    Full transaction analysis pipeline.
    Input:  raw transaction dict
    Output: complete risk assessment
    """
    features       = extract_features(data)
    prediction     = random_forest_predict(features)
    flags          = detect_flags(features)
    recommendation = get_recommendation(prediction["risk_level"], flags)

    return {
        "transaction_id": data.get("transaction_id", f"TXN-{random.randint(10000,99999)}"),
        "timestamp":      datetime.utcnow().isoformat(),
        "score":          prediction["score"],
        "risk_level":     prediction["risk_level"],
        "tree_scores":    prediction["trees"],
        "flags":          flags,
        "flag_count":     len([f for f in flags if f["code"] != "clean"]),
        "recommendation": recommendation,
        "model_version":  "ShieldAML-RF-v1.0",
        "compliance_ref": "FATF 2023 · FRA Law 161/2024 · UN Sanctions",
    }

# ─── KYC ANALYSIS ────────────────────────────────────────────

SANCTIONS_LIST = [
    "kim jong", "putin vladimir", "khamenei", "al-bashir", "lukashenko",
    "maduro nicolas", "al-assad", "gaddafi",
]

def analyze_kyc(data: dict) -> dict:
    """Customer KYC risk assessment."""
    name       = str(data.get("name", "")).lower()
    nationality = str(data.get("nationality", "")).lower()
    occupation  = str(data.get("occupation", "")).lower()
    country     = str(data.get("country", "")).lower()

    pep_keywords  = ["minister", "president", "senator", "official", "politician",
                     "ambassador", "governor", "parliament", "general", "director general"]
    is_pep        = any(kw in occupation for kw in pep_keywords)
    sanctions_hit = any(name_part in name for name_part in SANCTIONS_LIST)
    high_risk_nat = nationality in [c.lower() for c in HIGH_RISK_COUNTRIES]

    risk_score = 0
    if sanctions_hit: risk_score += 90
    if is_pep:        risk_score += 40
    if high_risk_nat: risk_score += 25

    risk_level = (
        "CRITICAL" if risk_score >= 80 else
        "HIGH"     if risk_score >= 40 else
        "MEDIUM"   if risk_score >= 20 else
        "LOW"
    )

    cdd_level = "EDD" if risk_level in ("CRITICAL", "HIGH") else "Standard CDD"

    return {
        "customer_name":    data.get("name"),
        "risk_score":       min(risk_score, 100),
        "risk_level":       risk_level,
        "sanctions_match":  sanctions_hit,
        "is_pep":           is_pep,
        "high_risk_nationality": high_risk_nat,
        "cdd_level":        cdd_level,
        "str_required":     sanctions_hit,
        "timestamp":        datetime.utcnow().isoformat(),
    }
