# 🤖 LLM-Based Loan Applicant Field Mapping API

A FastAPI backend service that automatically maps **Excel loan applicant data** to a structured database schema using an **LLM (AI) API**.

This system is designed for **fintech / loan processing companies** to ingest field-agent data with different formats and convert it into standardized database fields.

---

## 🚀 Features

* Upload Excel files via API
* Detect Excel column names automatically
* Fetch real database table fields dynamically
* AI-powered field mapping using LLM API
* Automatically rename Excel columns
* Optional insertion into MySQL database
* Auto table creation if not exists
* Health check endpoint

---

## 🏦 Loan Applicant Data Schema

The system maps data into this standardized structure:

* applicant_id
* applicant_name
* phone_number
* email
* aadhaar_number
* pan_number
* loan_amount
* loan_purpose
* employment_type
* monthly_income
* loan_status

---

## 🛠️ Tech Stack

* FastAPI
* Pandas
* MySQL
* SQLAlchemy
* Requests
* Python-dotenv
* External LLM API

---

## 📂 Project Structure

```
project/
│
├── main.py
├── requirements.txt
├── .env
└── README.md
```

---

## ⚙️ Environment Variables

Create a `.env` file:

```
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_database_name

API_URL=https://your-llm-api-url
DVARA_TOKEN=your_api_token
```

---

## 📦 Installation

### 1️⃣ Clone Repository

```
git clone https://github.com/Snehahanji/LLM-field-mapping.git
cd LLM-field-mapping
```

---

### 2️⃣ Create Virtual Environment

```
python -m venv venv
```

Activate:

Windows:

```
venv\Scripts\activate
```

Mac/Linux:

```
source venv/bin/activate
```

---

### 3️⃣ Install Dependencies

```
pip install -r requirements.txt
```

---

## ▶️ Running the Application

```
uvicorn main:app --reload
```

App runs at:

```
http://127.0.0.1:8000
```

Swagger Docs:

```
http://127.0.0.1:8000/docs
```

---

## 📡 API Endpoints

### Root Endpoint

```
GET /
```

Returns API status.

---

### Upload Excel

```
POST /upload/
```

Query Parameters:

| Parameter    | Type    | Default         | Description        |
| ------------ | ------- | --------------- | ------------------ |
| table_name   | string  | loan_applicants | Target DB table    |
| insert_to_db | boolean | false           | Insert mapped data |

---

### Health Check

```
GET /health
```

Checks database connectivity and token status.

---

## ⚙️ How It Works

### Step 1 — Upload Excel

Pandas reads the uploaded file.

### Step 2 — Fetch Database Fields

Table is created automatically if it does not exist.

### Step 3 — Call LLM API

Excel columns and database fields are sent to AI.

### Step 4 — Receive Mapping

LLM returns column-to-field mapping.

### Step 5 — Rename Columns

Excel columns are renamed using AI mapping.

### Step 6 — Optional Database Insert

Mapped data is inserted into MySQL.

---

## 📊 Example Mapping

Input Excel Columns:

```
["ID", "Name", "Mobile"]
```

Database Fields:

```
["applicant_id", "applicant_name", "phone_number"]
```

LLM Output:

```
{
  "ID": "applicant_id",
  "Name": "applicant_name",
  "Mobile": "phone_number"
}
```

---

## ❌ Error Handling

| Error      | Meaning               |
| ---------- | --------------------- |
| 403        | Token expired         |
| 500        | LLM API failure       |
| 500        | Database insert error |
| JSON Error | Invalid API response  |

---

## 🔮 Future Improvements

* Support CSV & XML upload
* Authentication system
* Logging & monitoring
* Docker deployment
* Credit score API integration
* Loan approval workflow engine

---

## 👩‍💻 Author

**Sneha Hanji**
LLM + FastAPI Integration Project

