# VendorIQ — AI-Powered Supplier Qualification & Batch Intelligence Platform

VendorIQ is an enterprise B2B SaaS platform for cosmetics, skincare, and pharmaceutical manufacturers. It unifies supplier document ingestion (COA, SDS, GMP), deterministic spec validation, machine learning batch risk prediction, Moonshot Kimi K3 scientific reasoning, autonomous qualification decision gating, and Google SMTP email delivery into a single cohesive system.

---

## 1. Final Deployment Architecture

```text
                       USERS
                         │
                         ▼
                ┌────────────────┐
                │ React Frontend │
                │    Vercel      │
                └───────┬────────┘
                        │
                     HTTPS/API
                        │
                        ▼
                ┌────────────────┐
                │ FastAPI Backend│
                │    Render      │
                └───────┬────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
       Neon          Kimi K3      Google SMTP
    PostgreSQL         API           Gmail
```

- **ONE React Frontend on Vercel** (`frontend/`)
- **ONE Unified FastAPI Backend on Render** (`backend/`)
- **Database**: Neon Serverless PostgreSQL
- **AI Reasoning**: Moonshot Kimi K3 API
- **Email Delivery**: Google SMTP (STARTTLS)

---

## 2. Integrated Modules Overview

| Module | Features Included |
|---|---|
| **Core Platform (P1)** | FastAPI, Neon PostgreSQL, JWT Auth, Multi-Tenant Company isolation, Vendors, Raw Materials, Batches CRUD |
| **Doc & ML Intelligence (P2)** | Document extraction (COA, SDS, GMP) via PyPDF & Regex, Deterministic Spec Validation, Random Forest Risk Prediction, Moonshot Kimi K3 Explanation |
| **Decision & Notification (P3)** | Autonomous Decision Engine (`APPROVED`, `REJECTED`, `NEEDS_REVIEW`), Google SMTP Emailer with retry mechanism, Audit Log Trail |
| **Integration & React SaaS (P4)** | Vite + React + TypeScript + Tailwind CSS SaaS UI, TanStack Query, Recharts, Centralized Axios Client, Render & Vercel deployment configurations |

---

## 3. Demo Test Scenarios

### Demo Vendor 1: ABC Ingredients Pvt Ltd
- **Material**: L-Ascorbic Acid (Spec: $\ge 99.0\%$)
- **Batch Number**: `VC-2026-104`
- **Extracted Purity**: `99.3%`
- **Supplier History**: 20 previous batches, 19 approved (95% approval rate), 97% on-time delivery
- **Result**: **LOW RISK** $\rightarrow$ **APPROVED** $\rightarrow$ **EMAIL SENT**

### Demo Vendor 2: XYZ Raw Materials
- **Material**: L-Ascorbic Acid (Spec: $\ge 99.0\%$)
- **Batch Number**: `VC-2026-205`
- **Extracted Purity**: `98.2%` (Below $\ge 99.0\%$ requirement)
- **Supplier History**: Poor historical rejection rate, missing/incomplete documentation
- **Result**: **HIGH RISK** $\rightarrow$ **REJECTED** $\rightarrow$ **EMAIL SENT**

---

## 4. Local Development Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### Backend Setup
```bash
cd backend
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Run migrations & populate demo seed data
python -m app.seed

# Start FastAPI
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health` $\rightarrow$ `{"status": "healthy"}`

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- UI Address: `http://localhost:5173`
- Default Admin Credentials: `admin@vendoriq.com` / `Password123!`

---

## 5. Render Deployment (FastAPI Backend)

1. Create a new **Web Service** on [Render](https://render.com).
2. Connect your GitHub repository.
3. Settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Set Environment Variables in Render Dashboard:
   ```env
   DATABASE_URL=postgresql://user:password@ep-xyz.neon.tech/vendoriq?sslmode=require
   JWT_SECRET=your_super_secret_jwt_key
   KIMI_API_KEY=your_moonshot_api_key
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_gmail_address@gmail.com
   SMTP_PASSWORD=your_gmail_app_password
   SMTP_FROM=your_gmail_address@gmail.com
   SMTP_FROM_NAME=VendorIQ
   FRONTEND_URL=https://your-vendoriq.vercel.app
   ```
5. Confirm deployment:
   ```bash
   curl https://your-backend.onrender.com/health
   # Returns: {"status": "healthy"}
   ```

---

## 6. Vercel Deployment (React Frontend)

1. Create a new project on [Vercel](https://vercel.com).
2. Connect your GitHub repository.
3. Configure project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Environment Variables:
   ```env
   VITE_API_URL=https://your-backend.onrender.com
   ```
5. Deploy. All deep links and client routing are handled via `vercel.json`.

---

## 7. Automated Testing

To run the complete backend integration and unit test suite:
```bash
cd backend
pytest
```
*49 passing tests across Auth, Vendors, Raw Materials, Batches, Validation, History, ML Prediction, Kimi AI, Decisions, and Google SMTP.*
