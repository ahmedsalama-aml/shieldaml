# 🛡 ShieldAML — Complete Deployment Guide
**By Ahmed Salama | CAMS | AML & Fraud Detection System**
Compliant with: FATF 2023 · Egyptian FRA Law 161/2024 · UN Sanctions

---

## 🚀 Deploy to Render.com (FREE — No coding required)

Follow these steps EXACTLY. Takes about 10 minutes.

---

### STEP 1 — Create a GitHub Account
1. Go to **github.com**
2. Click "Sign Up" — create a free account
3. Verify your email

---

### STEP 2 — Upload Your Project to GitHub
1. Go to **github.com/new** to create a new repository
2. Name it: `shieldaml`
3. Set to **Public**
4. Click "Create repository"
5. Upload ALL the project files (drag and drop the entire shieldaml folder)
6. Click "Commit changes"

---

### STEP 3 — Deploy on Render.com
1. Go to **render.com** and sign up for free
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account
4. Select your `shieldaml` repository
5. Fill in these settings:

| Setting | Value |
|---------|-------|
| Name | shieldaml |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

6. Click **"Create Web Service"**
7. Wait 2-3 minutes for it to deploy
8. Render gives you a URL like: `https://shieldaml.onrender.com`

**That's it — your system is live on the internet! 🎉**

---

## 🔌 How to Connect a Client's System (Integration Guide)

### Option A — API Integration (Most Common)
Your client's IT team adds ONE line to their system that sends each transaction to ShieldAML:

```python
# What the client's developer adds to their system
import requests

def check_transaction(transaction):
    response = requests.post(
        "https://shieldaml.onrender.com/api/transactions/analyze",
        json={
            "customer_id":        transaction.customer_id,
            "customer_name":      transaction.customer_name,
            "amount":             transaction.amount,
            "type":               "wire",      # wire/cash/crypto/insurance/internal
            "country":            transaction.destination_country,
            "hour":               transaction.hour,
            "tx_count_30d":       transaction.monthly_count,
            "account_age_months": transaction.account_age,
            "kyc_status":         1,           # 0=incomplete, 1=verified, 2=edd
            "previously_flagged": False,
            "is_pep":             False,
        }
    )
    result = response.json()
    risk   = result["analysis"]["risk_level"]   # LOW / MEDIUM / HIGH / CRITICAL
    score  = result["analysis"]["score"]        # 0-100

    if risk in ("HIGH", "CRITICAL"):
        # Flag in their system
        flag_transaction(transaction.id, score)

    return result
```

That's literally all the client needs to do. Their system calls yours, gets a risk score back in milliseconds.

---

### Option B — File Upload (No IT needed)
Client exports transactions as Excel/CSV → You run analysis → You send back risk report.

Use this script to process their file:

```python
import pandas as pd
import requests
import json

# Load client's transaction file
df = pd.read_csv("client_transactions.csv")  # or .xlsx

results = []
for _, row in df.iterrows():
    response = requests.post(
        "https://shieldaml.onrender.com/api/transactions/analyze",
        json={
            "customer_id":   str(row.get("customer_id", "")),
            "customer_name": str(row.get("name", "Unknown")),
            "amount":        float(row.get("amount", 0)),
            "type":          str(row.get("type", "wire")),
            "country":       str(row.get("country", "eg")),
            "hour":          int(row.get("hour", 12)),
            "tx_count_30d":  int(row.get("tx_count", 0)),
            "account_age_months": int(row.get("account_age", 12)),
            "kyc_status":    int(row.get("kyc_status", 1)),
        }
    )
    data = response.json()["analysis"]
    results.append({
        "transaction_id": data["transaction_id"],
        "risk_score":     data["score"],
        "risk_level":     data["risk_level"],
        "top_flag":       data["flags"][0]["description"] if data["flags"] else "",
        "action":         data["recommendation"]["action"],
        "str_required":   data["recommendation"]["str_required"],
    })

# Save risk report
output = pd.DataFrame(results)
output.to_excel("risk_report.xlsx", index=False)
print(f"✅ Processed {len(results)} transactions. Report saved.")
```

---

## 📡 Full API Reference

| Method | Endpoint | What it does |
|--------|----------|-------------|
| GET | `/api/health` | Check if system is running |
| GET | `/api/dashboard` | Get KPI statistics |
| POST | `/api/transactions/analyze` | Analyze a transaction |
| GET | `/api/transactions/` | List all transactions |
| GET | `/api/transactions/{id}` | Get one transaction |
| GET | `/api/alerts/` | List all alerts |
| PATCH | `/api/alerts/{id}/resolve` | Resolve an alert |
| POST | `/api/kyc/check` | Screen a customer |
| POST | `/api/str/generate` | Generate STR report |
| GET | `/api/str/` | List all STR reports |
| PATCH | `/api/str/{id}/submit` | Submit STR to regulator |
| GET | `/api/docs` | Interactive API documentation |

---

## 💰 Pricing You Can Charge Clients

| Package | What's included | Monthly Price |
|---------|----------------|---------------|
| **Starter** | Up to 1,000 transactions/month · Dashboard access · Email alerts | $500/month |
| **Professional** | Up to 10,000 transactions/month · API integration · STR reports | $1,500/month |
| **Enterprise** | Unlimited · Custom integration · Training · Priority support | $3,000+/month |

**First client tip:** Offer a free 30-day pilot. Once they see it catching real risks, they will pay.

---

## 🏗️ Project Structure

```
shieldaml/
├── main.py                    ← FastAPI server entry point
├── requirements.txt           ← Python dependencies
├── backend/
│   ├── ml_model.py           ← Random Forest + Isolation Forest engine
│   ├── database.py           ← SQLite database (all data storage)
│   └── routes/
│       ├── transactions.py   ← Transaction analysis API
│       ├── alerts.py         ← Alerts management API
│       ├── str_reports.py    ← STR report generation API
│       └── kyc.py            ← KYC screening API
└── frontend/
    └── index.html            ← Full dashboard (auto-served by backend)
```

---

## 🔒 Security Notes for Production

When you have paying clients, upgrade these:
1. Move from SQLite to PostgreSQL (Render offers free PostgreSQL)
2. Add API key authentication (so only your clients can use it)
3. Add HTTPS (Render does this automatically)
4. Add rate limiting (prevent abuse)

---

## 📞 Support

System built by: **Ahmed Salama | CAMS**
Email: ahmed.25salama@gmail.com
Compliance: FATF 2023 · Egyptian FRA Law 161/2024
