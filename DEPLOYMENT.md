# VendorIQ Cloud Deployment Guide

This guide details how to deploy the **VendorIQ** platform to production with the **Backend on Render** and the **Frontend on Vercel**.

---

## 1. Backend Deployment on Render

### Step 1: Create a New Web Service
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository: `priyanshukannaujiya/vendor_datacartel` (or your fork/repo).

### Step 2: Configure Service Settings
- **Name**: `vendoriq-backend`
- **Region**: Choose the region closest to your Neon PostgreSQL database (e.g., Frankfurt / Oregon / Ohio).
- **Branch**: `main`
- **Root Directory**: `backend`
- **Runtime**: `Python 3`
- **Build Command**:
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- **Instance Type**: Free or Starter

> **Note**: A pre-configured `render.yaml` blueprint is also included in the repository root if you prefer one-click Blueprint deployment (**New +** → **Blueprint**).

### Step 3: Configure Environment Variables on Render
Under **Environment Variables**, add the following:

| Key | Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+psycopg2://neondb_owner:...@...neon.tech/neondb?sslmode=require` | Your Neon serverless PostgreSQL connection string |
| `JWT_SECRET` | *(Click "Generate" or enter a secure 64-char key)* | Secret key for signing JWT tokens |
| `FRONTEND_URL` | `https://your-frontend.vercel.app` | Your Vercel frontend production URL |
| `KIMI_API_KEY` | *(Your Moonshot AI API key)* | Kimi K3 reasoning engine key |
| `SMTP_HOST` | `smtp.gmail.com` | Google SMTP server |
| `SMTP_PORT` | `587` | Google SMTP TLS port |
| `SMTP_USERNAME` | `your-email@gmail.com` | Google SMTP / App Password account |
| `SMTP_PASSWORD` | `your-16-char-app-password` | Google 16-character App Password |
| `SMTP_FROM` | `your-email@gmail.com` | From email address |
| `SMTP_FROM_NAME` | `VendorIQ AI Platform` | Email sender display name |

### Step 4: Deploy & Verify
1. Click **Create Web Service**.
2. Once deployed, Render will provide your public backend URL:
   `https://vendoriq-backend.onrender.com`
3. Test health check in your browser:
   `https://vendoriq-backend.onrender.com/api/health` → `{"status": "healthy"}`
4. Access Swagger API documentation:
   `https://vendoriq-backend.onrender.com/docs`

---

## 2. Frontend Deployment on Vercel

### Step 1: Import Project in Vercel
1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository.

### Step 2: Configure Project Settings
- **Framework Preset**: `Vite`
- **Root Directory**: Click **Edit** and select `frontend` (Important!).
- **Build Command**: `npm run build` (auto-detected)
- **Output Directory**: `dist` (auto-detected)

### Step 3: Add Environment Variables on Vercel
Under the **Environment Variables** section, add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `https://vendoriq-backend.onrender.com` | Your live Render backend URL (no trailing slash) |

### Step 4: Deploy & Verify
1. Click **Deploy**.
2. Once the build completes, Vercel will assign your domain:
   `https://your-project-name.vercel.app`
3. Test login with your existing credentials or create a new vendor/account.
4. Try uploading documents, running AI risk predictions, approving batches, and receiving email notifications.

---

## 3. Post-Deployment Verification Checklist

- [ ] Backend health check responds at `https://vendoriq-backend.onrender.com/api/health`
- [ ] Vercel frontend loads without CORS errors in browser DevTools console
- [ ] Vendor registration triggers automated onboarding email
- [ ] PDF document upload parses purity and triggers ML risk predictions
- [ ] 1-Click Approve / Reject triggers HTML certificate dispatch to vendor email
