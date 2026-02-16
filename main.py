from fastapi import FastAPI, UploadFile, File, HTTPException
import pandas as pd
import requests
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# ================= DATABASE CONNECTION =================
DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

# ================= API CONFIG =================
API_URL = os.getenv("API_URL")
TOKEN = os.getenv("DVARA_TOKEN")


# =========================================================
# CREATE LOAN APPLICANT TABLE
# =========================================================
def create_table_if_not_exists(table_name):
    """Create loan applicant table if it doesn't exist"""
    try:
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            applicant_id VARCHAR(50) PRIMARY KEY,
            applicant_name VARCHAR(255),
            phone_number VARCHAR(20),
            email VARCHAR(255),
            aadhaar_number VARCHAR(20),
            pan_number VARCHAR(20),
            loan_amount DECIMAL(12,2),
            loan_purpose VARCHAR(255),
            employment_type VARCHAR(100),
            monthly_income DECIMAL(12,2),
            loan_status VARCHAR(50) DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        with engine.connect() as conn:
            conn.execute(text(create_table_query))
            conn.commit()

        print(f"✅ Loan applicant table '{table_name}' ready")

    except Exception as e:
        print(f"⚠️ Could not create table: {e}")


# =========================================================
# GET DATABASE FIELDS
# =========================================================
def get_database_fields(table_name):
    """Fetch actual field names from database"""
    try:
        create_table_if_not_exists(table_name)

        with engine.connect() as conn:
            result = conn.execute(text(f"DESCRIBE {table_name}"))
            fields = [row[0] for row in result if row[0] not in ['created_at', 'loan_status']]
            return fields

    except Exception as e:
        print(f"⚠️ Could not fetch fields: {e}")

        # fallback fields
        return [
            "applicant_id",
            "applicant_name",
            "phone_number",
            "email",
            "aadhaar_number",
            "pan_number",
            "loan_amount",
            "loan_purpose",
            "employment_type",
            "monthly_income"
        ]


# =========================================================
# CALL LLM API
# =========================================================
def call_llm(excel_columns, database_fields):
    """Call LLM for mapping"""

    task_data = {
        "excel_columns": excel_columns,
        "database_fields": database_fields
    }

    form_data = {"task": json.dumps(task_data)}

    headers = {"Authorization": f"Bearer {TOKEN}"}

    try:
        response = requests.post(API_URL, headers=headers, data=form_data, timeout=30)

        if response.status_code == 403:
            raise HTTPException(status_code=403, detail="Token expired")

        response.raise_for_status()
        result = response.json()

        if result.get("status") != "completed":
            raise HTTPException(status_code=500, detail="LLM workflow failed")

        mapping = result.get("result", {}).get("result", {})

        if "is_valid" in mapping:
            del mapping["is_valid"]

        if not mapping:
            raise HTTPException(status_code=500, detail="Empty mapping returned")

        return mapping

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# UPLOAD ENDPOINT
# =========================================================
@app.post("/upload/")
async def upload_excel(
        file: UploadFile = File(...),
        table_name: str = "loan_applicants",
        insert_to_db: bool = False
):
    """Upload Excel and auto-map fields"""

    try:
        df = pd.read_excel(file.file)
        excel_columns = df.columns.tolist()

        print("📊 Excel Columns:", excel_columns)

        database_fields = get_database_fields(table_name)
        print("🗄️ DB Fields:", database_fields)

        mapping = call_llm(excel_columns, database_fields)

        print("🔗 Mapping:", mapping)

        # Rename columns
        df.rename(columns=mapping, inplace=True)

        rows_inserted = 0

        if insert_to_db:
            df.to_sql(table_name, engine, if_exists="append", index=False)
            rows_inserted = len(df)

        return {
            "status": "success",
            "mapping": mapping,
            "rows": len(df),
            "rows_inserted": rows_inserted,
            "preview": df.head(5).to_dict("records")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# HEALTH CHECK
# =========================================================
@app.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return {"status": "healthy", "database": "connected"}

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# =========================================================
# ROOT
# =========================================================
@app.get("/")
def root():
    return {
        "message": "Loan Applicant Field Mapping API",
        "version": "3.0",
        "endpoints": {
            "upload": "/upload/",
            "docs": "/docs",
            "health": "/health"
        }
    }
