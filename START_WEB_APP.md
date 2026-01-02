# 🚀 Start Your Beautiful Web Application

**Complete setup to run your AutoGen Dev Assistant Web App**

---

## Step 1: Start Backend (Terminal 1)

```powershell
# Navigate to project root
cd C:\Users\Likith\OneDrive\Desktop\automaton

# Activate virtual environment
venv\Scripts\activate

# Start FastAPI backend
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Test it:** Open http://localhost:8000

---

## Step 2: Install Frontend Dependencies (One-time)

```powershell
# Open NEW terminal (keep backend running)
cd C:\Users\Likith\OneDrive\Desktop\automaton\frontend

# Install dependencies
npm install
```

This will install:
- React & ReactDOM
- TypeScript
- Vite (build tool)
- Tailwind CSS
- Monaco Editor (VS Code editor)
- Axios (HTTP client)

---

## Step 3: Start Frontend (Terminal 2)

```powershell
# In the frontend directory
npm run dev
```

**Expected Output:**
```
VITE v5.0.8  ready in 500 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

---

## Step 4: Open in Browser

**Navigate to:** http://localhost:5173

You should see a **beautiful, modern web application** with:
- 🎨 Gradient purple/pink design
- 💻 Code editor (Monaco - same as VS Code)
- 🔄 Real-time code analysis
- 📊 Results dashboard
- ⚡ Lightning-fast interface

---

## How to Use

### 1. Write Code
- Type or paste code in the left panel
- Select language (Python, JavaScript, TypeScript, Java)

### 2. Analyze
- Click "Analyze Code" button
- Watch real-time progress

### 3. View Results
- See code quality score
- View security score
- Read analysis summary
- Check issues found

---

## Screenshots

### Main Interface
```
┌─────────────────────────────────────────────────┐
│  AutoGen Development Assistant                  │
│  AI-Powered Code Review & Analysis              │
├───────────────┬─────────────────────────────────┤
│               │                                 │
│  Code Editor  │     Analysis Results            │
│  (Monaco)     │     • Code Quality: 8/10        │
│               │     • Security: 9/10            │
│  [Python ▼]   │     • Issues: 2                │
│               │     • Summary                   │
│  def hello(): │                                 │
│    print()    │                                 │
│               │                                 │
│  [Analyze]    │     [✓ Complete]               │
└───────────────┴─────────────────────────────────┘
```

---

## Troubleshooting

### Backend Error: "Module not found"

```powershell
# Install missing packages
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic-settings
```

### Frontend Error: "Cannot find module"

```powershell
# In frontend directory
npm install
```

### Port Already in Use

**Backend (port 8000):**
```powershell
# Change port in command
python -m uvicorn backend.main:app --reload --port 8001
```

**Frontend (port 5173):**
```powershell
# Change in vite.config.ts
server: { port: 3000 }
```

---

## Features

### ✅ What Works Now
- Beautiful modern UI with gradients
- Code editor with syntax highlighting
- Code submission to backend
- Results display with scores
- Responsive design
- Fast API integration

### 🔄 Coming Soon
- Real-time WebSocket updates
- User authentication
- Project management
- History tracking
- Multiple workflows
- Advanced analytics

---

## Architecture

```
Browser (localhost:5173)
    ↓
React Frontend (Vite)
    ↓ HTTP Request
FastAPI Backend (localhost:8000)
    ↓
AutoGen Agents (Existing CLI)
    ↓
Results back to Frontend
```

---

## Next Steps

1. **Try it out!** Submit some code and see the analysis
2. **Customize:** Edit colors in `frontend/src/App.tsx`
3. **Add features:** See [WEB_APP_IMPLEMENTATION_GUIDE.md](WEB_APP_IMPLEMENTATION_GUIDE.md)
4. **Deploy:** When ready, build with `npm run build`

---

## Commands Quick Reference

```powershell
# Backend
python -m uvicorn backend.main:app --reload

# Frontend
cd frontend
npm install        # One-time setup
npm run dev        # Development server
npm run build      # Production build

# Both at once (use 2 terminals)
Terminal 1: backend
Terminal 2: frontend
```

---

**Enjoy your beautiful web application!** 🎉

Any issues? Check the logs or see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
