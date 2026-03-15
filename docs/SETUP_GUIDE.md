# CryptoSwarms Complete Setup Guide

This guide is the canonical runbook to get the app and dashboard running locally.

## 1) Prerequisites

- OS: Windows 11 + PowerShell 7 (project is currently Windows-first in scripts/Makefile).
- Python: 3.12+ (3.13 is used in existing examples).
- Node.js: v20+ (for the React frontend).
- Docker Desktop: latest stable, with Compose v2 enabled.
- Git.
- Optional for local LLM service:
  - NVIDIA GPU + NVIDIA Container Toolkit (for `sglang` container).

## 2) Clone and enter project

```powershell
git clone https://github.com/Thwinlimhan/CryptoSwarms.git
cd CryptoSwarms
```

## 3) Configure environment

Create local env file from template:

```powershell
Copy-Item .env.example .env
```

Minimum values to verify in `.env`:

- `API_KEY`: Set a random string (required for API security).
- `CORS_ORIGINS`: `http://localhost:5173,http://127.0.0.1:5173`.
- `DB_PASSWORD`
- `NEO4J_PASSWORD`
- `MC_USER`
- `MC_PASS`
- `MC_API_KEY`
- `DEEPFLOW_ENABLED=false` (keep disabled unless you run observability profile)

## 4) Python environment (Backend)

```powershell
C:\Users\thwin\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e . pytest
```

## 5) Node.js environment (Frontend)

```powershell
cd frontend
npm install
```

## 6) Start Core Services (Infrastructure)

Start required datastores and upstream tools:

```powershell
docker compose up -d redis timescaledb mission-control
```

## 7) Start Application Components

### A) Start Backend API
```powershell
# From root directory
.\.venv\Scripts\python.exe -m api.main
```
To enable HTTPS, set `SSL_CERTFILE` and `SSL_KEYFILE` in `.env`.

### B) Start Frontend Dashboard
```powershell
# From frontend directory
npm run dev
```

## 8) Access Points

- **React Operator Dashboard**: `http://localhost:5173`
- **EV Master Hub**: `http://localhost:5173/ev`
- **API Docs (Swagger)**: `http://localhost:8000/docs`
- **Mission Control upstream**: `http://localhost:3000`

## 9) Validate Installation

Run backend tests:
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run frontend build check:
```powershell
cd frontend
npm run build
```

## 10) Troubleshooting

### A) API Auth Errors
Ensure `X-API-Key` is configured in your request headers or the frontend settings matches the `API_KEY` in `.env`.

### B) Database Connection pooling
If you see connection errors, ensure `timescaledb` is fully healthy in Docker before starting the API.

## 11) Stop and Clean Up

```powershell
docker compose down
```
To remove volumes (destructive):
```powershell
docker compose down -v
```
