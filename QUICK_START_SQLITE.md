# Quick Start Guide - SQLite Edition (No Docker)

**Simple setup for development using SQLite instead of PostgreSQL**

---

## Prerequisites

✅ Python 3.10+
✅ Node.js 18+ (for frontend)
✅ **No Docker needed!**

---

## Backend Setup (5 minutes)

### Step 1: Install Backend Dependencies

```powershell
# Make sure you're in the project root
cd C:\Users\Likith\OneDrive\Desktop\automaton

# Activate virtual environment (if not already active)
venv\Scripts\activate

# Install backend requirements
pip install fastapi[all] uvicorn sqlalchemy aiosqlite python-jose passlib python-multipart pydantic-settings
```

### Step 2: Run Backend

```powershell
# Run FastAPI server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Step 3: Test API

Open in browser: http://localhost:8000

You should see:
```json
{
  "message": "AutoGen Development Assistant API",
  "version": "1.0.0",
  "docs": "/api/v1/docs"
}
```

**API Documentation:** http://localhost:8000/api/v1/docs

---

## Frontend Setup (5 minutes)

### Step 1: Create React App

```powershell
# Create frontend with Vite
npm create vite@latest frontend -- --template react-ts

# Navigate to frontend
cd frontend

# Install dependencies
npm install
```

### Step 2: Install Additional Packages

```powershell
npm install axios @tanstack/react-query zustand react-router-dom
```

### Step 3: Run Frontend

```powershell
npm run dev
```

Frontend will be available at: http://localhost:5173

---

## What You Have Now

```
✅ Backend API running on http://localhost:8000
✅ SQLite database (autogen_dev.db) created automatically
✅ API documentation at http://localhost:8000/api/v1/docs
✅ Frontend dev server ready at http://localhost:5173
✅ No Docker, PostgreSQL, or Redis needed!
```

---

## Database File

The SQLite database is created automatically:
- **Location:** `C:\Users\Likith\OneDrive\Desktop\automaton\autogen_dev.db`
- **Size:** ~50KB (initially)
- **Tool to view:** [DB Browser for SQLite](https://sqlitebrowser.org/)

---

## Testing the API

### 1. Health Check

```powershell
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development"
}
```

### 2. Interactive API Docs

Open: http://localhost:8000/api/v1/docs

You can test all endpoints directly in the browser!

---

## Next Steps

### 1. Create Your First User (API Docs)

1. Go to http://localhost:8000/api/v1/docs
2. Find `POST /api/v1/auth/register`
3. Click "Try it out"
4. Enter:
   ```json
   {
     "email": "test@example.com",
     "username": "testuser",
     "password": "password123",
     "full_name": "Test User"
   }
   ```
5. Click "Execute"

### 2. Submit Code for Review

1. Find `POST /api/v1/code-review` in API docs
2. Submit code:
   ```json
   {
     "code": "def hello():\n    print('Hello World')",
     "language": "python",
     "focus_areas": ["security", "performance"]
   }
   ```

### 3. Build Frontend Pages

See [WEB_APP_IMPLEMENTATION_GUIDE.md](WEB_APP_IMPLEMENTATION_GUIDE.md) for frontend components.

---

## Troubleshooting

### "Module not found" errors

```powershell
# Install missing packages
pip install -r backend/requirements.txt
```

### Database errors

```powershell
# Delete database and restart (resets everything)
rm autogen_dev.db
uvicorn backend.main:app --reload
```

### Port already in use

```powershell
# Change port
uvicorn backend.main:app --reload --port 8001
```

---

## Production Migration

When ready for production, you can easily switch to PostgreSQL:

1. Install Docker Desktop
2. Update `backend/core/config.py`:
   ```python
   DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/autogen_dev"
   ```
3. Run `docker compose up -d postgres`
4. Your data stays separate (SQLite vs PostgreSQL)

---

## Summary

✅ **Backend running** - http://localhost:8000
✅ **SQLite database** - autogen_dev.db
✅ **No external dependencies** - Pure Python!
✅ **Fast development** - Changes reload automatically
✅ **API documentation** - Built-in Swagger UI

**You're ready to start building!** 🚀
