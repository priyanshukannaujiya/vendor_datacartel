# VendorIQ - Backend Foundation

VendorIQ is an AI-Powered Supplier Qualification & Batch Intelligence Platform for skincare and cosmetics manufacturers.

This backend service is built with FastAPI, SQLAlchemy 2.x, Alembic, and PostgreSQL (Neon-compatible).

---

## 1. Project Purpose

When a supplier ships a raw-material batch, VendorIQ ingests supplier documents (COA, SDS, GMP certificate), validates them against material specifications, assesses supplier history and ML risk, provides AI explanations, and outputs deterministic qualification decisions (`APPROVED`, `REJECTED`, or `NEEDS_REVIEW`) with an audit trail.

This phase provides the **Developer 1 P0 Backend Foundation**:
- FastAPI application skeleton with centralized error handling and CORS
- Pydantic Settings configuration management
- SQLAlchemy 2.x database & Neon PostgreSQL connection management
- Alembic database migration environment
- Security & JWT authentication foundation (bcrypt password hashing, HS256 JWT tokens, `get_current_user` dependency)
- Standard health check endpoints

---

## 2. Environment Setup

### Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

### Create Virtual Environment
```bash
# Navigate to the backend directory
cd backend

# Create virtual environment
python -m venv venv
```

### Windows Activation (PowerShell)
```powershell
.\venv\Scripts\Activate.ps1
```

*(If running Command Prompt, use `.\venv\Scripts\activate.bat`)*

### Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 3. Configuration (.env)

Copy `.env.example` to create your local `.env`:
```powershell
copy .env.example .env
```

Configure your environment variables in `.env`:
- `DATABASE_URL`: Your Neon PostgreSQL connection string (e.g., `postgresql://user:password@ep-xyz.neon.tech/vendoriq?sslmode=require`)
- `JWT_SECRET`: A secure random secret key for signing JWT tokens
- `FRONTEND_URL`: URL of the frontend client (default: `http://localhost:5173`)
- `CORS_ORIGINS`: Additional allowed origins (e.g., `http://localhost:5173,http://localhost:3000`)
- `JWT_EXPIRE_MINUTES`: JWT token lifetime in minutes (default: `60`)
- `MAX_UPLOAD_MB`: Maximum file upload limit in MB (default: `10`)
- `UPLOAD_DIR`: Local directory for uploaded files (default: `./uploads`)

> **Note:** Never commit `.env` or real connection strings to version control. `.env` is ignored by `.gitignore`.

---

## 4. Running the FastAPI Application

Start the development server with hot reload:
```powershell
uvicorn app.main:app --reload
```

The service will start at `http://127.0.0.1:8000`.

Interactive documentation:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 5. Health Endpoint

Check application health:
```bash
curl http://127.0.0.1:8000/health
```

Expected Response:
```json
{
  "status": "healthy"
}
```

---

## 6. Running Tests

Run the test suite with pytest:
```powershell
pytest
```

---

## 7. Database Migrations (Alembic)

Once database models are defined in the next phase and your `DATABASE_URL` is configured in `.env`:

```powershell
# Generate a new migration based on models
alembic revision --autogenerate -m "create initial tables"

# Apply migrations to the database
alembic upgrade head

# Rollback migration by one revision
alembic downgrade -1
```
