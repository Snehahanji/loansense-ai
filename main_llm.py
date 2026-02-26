from fastapi import FastAPI, UploadFile, File
import pandas as pd
import requests
import json
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# ================= DATABASE =================
DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

MAPPING_API_URL = os.getenv("API_URL")          # Field mapping LLM
REPAIR_API_URL  = os.getenv("REPAIR_API_URL")   # Unjumbling LLM (Langfuse/sneha1)
TOKEN           = os.getenv("DVARA_TOKEN")

# ================= CONTROLLED LISTS =================
LOAN_PURPOSES = ["education", "home renovation", "car", "business", "personal", "medical"]
EMPLOYMENT_TYPES = ["salaried", "self employed", "unemployed"]

DB_FIELDS = [
    "applicant_id", "applicant_name", "phone_number", "email",
    "aadhaar_number", "pan_number", "loan_amount",
    "loan_purpose", "employment_type", "monthly_income"
]

# =========================================================
# CREATE TABLE
# =========================================================
def create_table():
    query = """
    CREATE TABLE IF NOT EXISTS loan_applicants (
        applicant_id    VARCHAR(50)    PRIMARY KEY,
        applicant_name  VARCHAR(255),
        phone_number    VARCHAR(20),
        email           VARCHAR(255),
        aadhaar_number  VARCHAR(20),
        pan_number      VARCHAR(20),
        loan_amount     DECIMAL(12,2),
        loan_purpose    VARCHAR(255),
        employment_type VARCHAR(100),
        monthly_income  DECIMAL(12,2),
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    with engine.connect() as conn:
        conn.execute(text(query))
        conn.commit()

# =========================================================
# VALIDATORS
# =========================================================
def valid_id(v):
    return bool(re.match(r"^A\d+$", str(v).strip()))

def valid_email(v):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$", str(v).strip()))

def valid_phone(v):
    s = str(v).strip()
    return s.isdigit() and len(s) == 10 and s[0] in "6789"

def valid_aadhaar(v):
    s = str(v).strip()
    return s.isdigit() and len(s) == 12

def valid_pan(v):
    return bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", str(v).strip().upper()))

def valid_loan_amount(v):
    try:
        return 500000 <= int(str(v).strip()) <= 10000000
    except:
        return False

def valid_monthly_income(v):
    try:
        return 25000 <= int(str(v).strip()) <= 1000000
    except:
        return False

def valid_name(v):
    parts = str(v).strip().split()
    return (
        len(parts) >= 1
        and bool(re.match(r"^[A-Za-z ]+$", str(v).strip()))
        and all(len(p) >= 2 for p in parts)
    )

def is_null(v):
    return str(v).strip() in ("nan", "None", "NaT", "none", "null", "")

# =========================================================
# ID GENERATOR
# =========================================================
_used_ids = set()

def next_id():
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT applicant_id FROM loan_applicants")).fetchall()
            db_ids = {int(r[0][1:]) for r in rows if re.match(r"^A[0-9]+$", r[0])}
    except Exception:
        db_ids = set()
    all_used = db_ids | _used_ids
    start = max(all_used) + 1 if all_used else 101
    n = start
    while n in all_used:
        n += 1
    _used_ids.add(n)
    return f"A{n}"

# =========================================================
# API 1 — FIELD MAPPING LLM
# =========================================================
def call_llm_mapping(cols, fields, rows):
    task = {
        "excel_columns": cols,
        "database_fields": fields,
        "data_rows": rows
    }
    r = requests.post(
        MAPPING_API_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        data={"task": json.dumps(task)},
        timeout=60
    )
    raw = r.json()
    print("MAPPING RAW:", raw)

    mp = {}
    if "result" in raw:
        res = raw["result"]
        if isinstance(res, dict):
            if "mapping" in res:
                mp = res["mapping"]
            elif "result" in res:
                mp = res["result"]
    if "mapping" in raw:
        mp = raw["mapping"]
    if isinstance(mp, str):
        try:
            mp = json.loads(mp)
        except:
            mp = {}
    if not isinstance(mp, dict):
        mp = {}

    return {k: v for k, v in mp.items() if k != "is_valid"}

# =========================================================
# API 2 — LLM UNJUMBLING (Langfuse/sneha1)
# =========================================================
def call_llm_repair(row: dict) -> dict:
    """Send one raw row to the Langfuse repair prompt and get cleaned fields back."""
    r = requests.post(
        REPAIR_API_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        data={"task": json.dumps(row)},
        timeout=60
    )
    raw = r.json()
    print("REPAIR RAW:", raw)

    result = raw.get("result", {}).get("result", "")

    # Strip markdown fences if present
    if isinstance(result, str):
        result = re.sub(r"```json|```", "", result).strip()
        try:
            return json.loads(result)
        except:
            return {}

    if isinstance(result, dict):
        return result

    return {}

# =========================================================
# POST-REPAIR VALIDATION & FALLBACK
# =========================================================
def validate_and_fix(df: pd.DataFrame) -> pd.DataFrame:
    """After LLM repair, run a final rule-based pass to catch any remaining issues."""
    for i in df.index:
        # applicant_id — assign new if invalid
        aid = str(df.at[i, "applicant_id"]).strip()
        if not valid_id(aid):
            df.at[i, "applicant_id"] = next_id()
        else:
            try:
                _used_ids.add(int(aid[1:]))
            except:
                pass

        # phone
        if not valid_phone(str(df.at[i, "phone_number"])):
            df.at[i, "phone_number"] = None

        # email
        if not valid_email(str(df.at[i, "email"])):
            df.at[i, "email"] = None

        # aadhaar
        if not valid_aadhaar(str(df.at[i, "aadhaar_number"])):
            df.at[i, "aadhaar_number"] = None

        # pan
        pan = str(df.at[i, "pan_number"]).strip().upper()
        df.at[i, "pan_number"] = pan if valid_pan(pan) else None

        # loan_amount
        if not valid_loan_amount(str(df.at[i, "loan_amount"])):
            df.at[i, "loan_amount"] = None

        # monthly_income
        if not valid_monthly_income(str(df.at[i, "monthly_income"])):
            df.at[i, "monthly_income"] = None

        # loan_purpose
        lp = str(df.at[i, "loan_purpose"]).strip().lower()
        df.at[i, "loan_purpose"] = lp.title() if lp in LOAN_PURPOSES else None

        # employment_type
        et = str(df.at[i, "employment_type"]).strip().lower()
        df.at[i, "employment_type"] = et.title() if et in EMPLOYMENT_TYPES else None

        # name
        if not valid_name(str(df.at[i, "applicant_name"])):
            df.at[i, "applicant_name"] = None

    return df

# =========================================================
# ENSURE COLUMNS
# =========================================================
def ensure_columns(df):
    for col in DB_FIELDS:
        if col not in df.columns:
            df[col] = None
    return df[DB_FIELDS]

# =========================================================
# QUALITY METRICS
# =========================================================
def compute_quality(df: pd.DataFrame) -> dict:
    total = len(df)
    if total == 0:
        return {}

    validators = {
        "applicant_id":   valid_id,
        "applicant_name": valid_name,
        "phone_number":   valid_phone,
        "email":          valid_email,
        "aadhaar_number": valid_aadhaar,
        "pan_number":     valid_pan,
        "loan_amount":    valid_loan_amount,
        "loan_purpose":   lambda v: str(v).strip().lower() in LOAN_PURPOSES,
        "employment_type":lambda v: str(v).strip().lower() in EMPLOYMENT_TYPES,
        "monthly_income": valid_monthly_income,
    }

    field_scores = {}
    for field, validator in validators.items():
        if field not in df.columns:
            field_scores[field] = 0
            continue
        valid_count = df[field].apply(
            lambda v: False if is_null(str(v)) else validator(str(v))
        ).sum()
        field_scores[field] = round((valid_count / total) * 100, 1)

    overall = round(sum(field_scores.values()) / len(field_scores), 1)
    return {"overall": overall, "fields": field_scores}

# =========================================================
# UPSERT
# =========================================================
def upsert(df):
    ins, upd = 0, 0
    with engine.begin() as conn:
        for _, r in df.iterrows():
            d = {k: (None if is_null(str(v)) else v) for k, v in r.to_dict().items()}
            exists = conn.execute(
                text("SELECT COUNT(*) FROM loan_applicants WHERE applicant_id=:id"),
                {"id": d["applicant_id"]}
            ).scalar()

            if exists:
                conn.execute(text("""
                UPDATE loan_applicants SET
                  applicant_name=:applicant_name, phone_number=:phone_number,
                  email=:email, aadhaar_number=:aadhaar_number,
                  pan_number=:pan_number, loan_amount=:loan_amount,
                  loan_purpose=:loan_purpose, employment_type=:employment_type,
                  monthly_income=:monthly_income
                WHERE applicant_id=:applicant_id
                """), d)
                upd += 1
            else:
                conn.execute(text("""
                INSERT INTO loan_applicants (
                  applicant_id, applicant_name, phone_number, email,
                  aadhaar_number, pan_number, loan_amount,
                  loan_purpose, employment_type, monthly_income, created_at
                ) VALUES (
                  :applicant_id, :applicant_name, :phone_number, :email,
                  :aadhaar_number, :pan_number, :loan_amount,
                  :loan_purpose, :employment_type, :monthly_income, NOW()
                )
                """), d)
                ins += 1
    return ins, upd

# =========================================================
# CORE PIPELINE
# =========================================================
def run_pipeline(original_df: pd.DataFrame):
    """
    Full pipeline:
      1. Call API 1 → field mapping (rename columns)
      2. Call API 2 (per row) → LLM unjumbling
      3. Rule-based final validation pass
    Returns: (cleaned_df, mapping, quality_metrics)
    """
    _used_ids.clear()

    # --- STEP 1: Field Mapping ---
    mp = call_llm_mapping(
        original_df.columns.tolist(),
        DB_FIELDS,
        original_df.head(5).to_dict("records")  # send sample rows for context
    )

    # Rename columns per mapping
    mapped_df = original_df.copy()
    mapped_df.rename(columns=mp, inplace=True)
    mapped_df = ensure_columns(mapped_df)

    # --- STEP 2: LLM Unjumbling (row by row) ---
    repaired_rows = []
    errors = []

    for idx, row in original_df.iterrows():
        try:
            cleaned = call_llm_repair(row.to_dict())
            if cleaned:
                repaired_rows.append(cleaned)
            else:
                # Fallback: use mapped row as-is
                repaired_rows.append(mapped_df.loc[idx].to_dict())
        except Exception as e:
            errors.append({"row": idx, "error": str(e)})
            repaired_rows.append(mapped_df.loc[idx].to_dict())

    df = pd.DataFrame(repaired_rows)
    df = ensure_columns(df)

    # --- STEP 3: Final rule-based validation ---
    df = validate_and_fix(df)
    df.reset_index(drop=True, inplace=True)

    quality = compute_quality(df)

    return df, mp, quality, errors

# =========================================================
# VALIDATE ENDPOINT
# =========================================================
@app.post("/validate/")
async def validate(file: UploadFile = File(...)):
    original_df = pd.read_excel(file.file, dtype=str)
    original_df.reset_index(drop=True, inplace=True)
    create_table()

    df, mp, quality, errors = run_pipeline(original_df)

    return {
        "status": "validated",
        "mapping": mp,
        "quality": quality,
        "errors": errors,
        "total_rows": len(df),
        "preview": df.head(20).fillna("").to_dict("records"),
        "original_preview": original_df.head(20).fillna("").to_dict("records")
    }

# =========================================================
# UPLOAD ENDPOINT (full pipeline — fallback if no validate first)
# =========================================================
@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    original_df = pd.read_excel(file.file, dtype=str)
    original_df.reset_index(drop=True, inplace=True)
    create_table()

    df, mp, quality, errors = run_pipeline(original_df)
    ins, upd = upsert(df)

    return {
        "status": "success",
        "inserted": ins,
        "updated": upd,
        "quality": quality,
        "errors": errors,
        "total_rows": len(df)
    }

# =========================================================
# UPLOAD-VALIDATED ENDPOINT
# Accepts already-cleaned rows from the frontend session state.
# No re-processing — straight to DB upsert.
# =========================================================
from fastapi import Body

@app.post("/upload-validated/")
async def upload_validated(payload: dict = Body(...)):
    """
    Expects: { "rows": [...], "quality": {...} }
    Rows must already be cleaned/validated by the /validate/ pipeline.
    """
    rows = payload.get("rows", [])
    quality = payload.get("quality", {})

    if not rows:
        return {"status": "error", "message": "No rows provided"}

    create_table()

    df = pd.DataFrame(rows)
    df = ensure_columns(df)

    # Replace empty strings with None for DB
    df = df.replace("", None)

    ins, upd = upsert(df)

    return {
        "status": "success",
        "inserted": ins,
        "updated": upd,
        "quality": quality,
        "total_rows": len(df)
    }

# =========================================================
# STATS ENDPOINT
# =========================================================
@app.get("/stats/")
def stats():
    try:
        with engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM loan_applicants")).scalar()
            by_purpose = conn.execute(text(
                "SELECT loan_purpose, COUNT(*) as cnt FROM loan_applicants GROUP BY loan_purpose"
            )).fetchall()
            by_employment = conn.execute(text(
                "SELECT employment_type, COUNT(*) as cnt FROM loan_applicants GROUP BY employment_type"
            )).fetchall()
            avg_loan = conn.execute(text(
                "SELECT AVG(loan_amount) FROM loan_applicants WHERE loan_amount IS NOT NULL"
            )).scalar()
            avg_income = conn.execute(text(
                "SELECT AVG(monthly_income) FROM loan_applicants WHERE monthly_income IS NOT NULL"
            )).scalar()
        return {
            "total_applicants": total,
            "by_purpose": [{"purpose": r[0], "count": r[1]} for r in by_purpose],
            "by_employment": [{"type": r[0], "count": r[1]} for r in by_employment],
            "avg_loan_amount": round(float(avg_loan), 2) if avg_loan else 0,
            "avg_monthly_income": round(float(avg_income), 2) if avg_income else 0,
        }
    except Exception as e:
        return {"error": str(e)}

# =========================================================
# ROOT
# =========================================================
@app.get("/")
def root():
    return {"msg": "Loan Applicant AI Ingestion System — Dual LLM Pipeline"}