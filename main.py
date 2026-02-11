from fastapi import FastAPI, UploadFile, File, HTTPException
import pandas as pd
import requests
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# Database connection
DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

# API Configuration
API_URL = os.getenv("API_URL")
TOKEN = os.getenv("DVARA_TOKEN")

def create_table_if_not_exists(table_name):
    """Create table if it doesn't exist"""
    try:
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            customer_id VARCHAR(50) PRIMARY KEY,
            full_name VARCHAR(255),
            email_address VARCHAR(255),
            mobile_number VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        with engine.connect() as conn:
            conn.execute(text(create_table_query))
            conn.commit()
        
        print(f"✅ Table '{table_name}' ready")
    except Exception as e:
        print(f"⚠️ Could not create table: {e}")

def get_database_fields(table_name):
    """Fetch actual field names from your database table"""
    try:
        create_table_if_not_exists(table_name)
        
        with engine.connect() as conn:
            result = conn.execute(text(f"DESCRIBE {table_name}"))
            fields = [row[0] for row in result if row[0] != 'created_at']
            return fields
    except Exception as e:
        print(f"⚠️ Could not fetch database fields: {e}")
        return ["customer_id", "full_name", "email_address", "mobile_number"]

def call_llm(excel_columns, database_fields):
    """Call the LLM API for field mapping using form-data"""
    
    # Create the task payload
    task_data = {
        "excel_columns": excel_columns,
        "database_fields": database_fields
    }
    
    # Convert to JSON string for form-data
    task_json_string = json.dumps(task_data)
    
    print("📤 Sending to LLM (form-data):")
    print(f"   task = {task_json_string}")
    
    # Send as form-data
    form_data = {
        "task": task_json_string
    }
    
    # Headers for form-data (no Content-Type needed)
    headers_for_form = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    try:
        response = requests.post(
            API_URL, 
            headers=headers_for_form,
            data=form_data,  # Using 'data' for form-data, not 'json'
            timeout=30
        )
        
        if response.status_code == 403:
            raise HTTPException(status_code=403, detail="Token expired. Update DVARA_TOKEN in .env")
        
        response.raise_for_status()
        
        result = response.json()
        print("📥 Full API Response:", json.dumps(result, indent=2))
        
        # Check if workflow succeeded
        if result.get("status") != "completed":
            error_msg = result.get("error", "Unknown error")
            raise HTTPException(status_code=500, detail=f"Workflow failed: {error_msg}")
        
        # Extract mapping from nested result.result structure
        mapping_data = result.get("result", {}).get("result", {})
        
        # Remove any extra fields like 'is_valid'
        if "is_valid" in mapping_data:
            del mapping_data["is_valid"]
        
        print("🔗 Extracted Mapping:", mapping_data)
        
        if not mapping_data:
            raise HTTPException(status_code=500, detail="Empty mapping returned from LLM")
            
        return mapping_data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM API failed: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid JSON response: {str(e)}")

@app.post("/upload/")
async def upload_excel(
    file: UploadFile = File(...), 
    table_name: str = "llm_mapping",
    insert_to_db: bool = False
):
    """Upload Excel and map fields automatically"""
    
    try:
        # Read Excel
        df = pd.read_excel(file.file)
        excel_columns = df.columns.tolist()
        
        print(f"\n{'='*60}")
        print(f"📊 Excel Columns: {excel_columns}")
        print(f"📊 Total Rows: {len(df)}")
        
        # Get database fields
        database_fields = get_database_fields(table_name)
        print(f"🗄️  Database Fields: {database_fields}")
        
        # Get mapping from LLM
        mapping = call_llm(excel_columns, database_fields)
        
        print(f"🔗 Final Mapping: {mapping}")
        
        # Rename columns
        df.rename(columns=mapping, inplace=True)
        
        print(f"✅ Renamed Columns: {df.columns.tolist()}")
        
        # Insert to database if requested
        rows_inserted = 0
        if insert_to_db:
            try:
                df.to_sql(table_name, engine, if_exists='append', index=False)
                rows_inserted = len(df)
                print(f"✅ {rows_inserted} rows inserted into {table_name}")
            except Exception as e:
                print(f"⚠️ Database insert failed: {e}")
                return {
                    "status": "partial_success",
                    "message": "Mapping successful but database insert failed",
                    "error": str(e),
                    "mapping": mapping,
                    "preview": df.head(5).to_dict('records')
                }
        
        print(f"{'='*60}\n")
        
        return {
            "status": "success",
            "original_columns": excel_columns,
            "database_fields": database_fields,
            "mapping": mapping,
            "renamed_columns": df.columns.tolist(),
            "total_rows": len(df),
            "rows_inserted": rows_inserted,
            "preview": df.head(5).to_dict('records')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {
        "status": "Field Mapper API is running",
        "version": "2.0",
        "endpoints": {
            "upload": "/upload/?table_name=your_table&insert_to_db=false",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    """Check if API and database are accessible"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {
            "database": "connected",
            "status": "healthy",
            "token_set": bool(TOKEN)
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}