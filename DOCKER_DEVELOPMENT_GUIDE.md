# Docker Development Guide for ProGestock

## 🐳 Why Use Docker for Local Development?

### Benefits:
- ✅ **No Manual Setup**: No need to install Python, Node.js, or manage virtual environments
- ✅ **Consistent Environment**: Works the same on Windows, Mac, and Linux
- ✅ **Isolated**: Project dependencies don't conflict with other projects
- ✅ **One Command Start**: Run entire stack (frontend + backend) with one command
- ✅ **Easy Cleanup**: Delete containers to start fresh anytime
- ✅ **Team Consistency**: Everyone uses the same environment

### What You Need:
- **Docker Desktop** (includes Docker and Docker Compose)
- That's it! No Python, Node.js, or other tools needed

---

## 📥 Installing Docker Desktop

### Windows:
1. Download: https://www.docker.com/products/docker-desktop/
2. Run installer
3. Restart computer
4. Open Docker Desktop
5. Wait for "Docker Desktop is running" message

### Verify Installation:
```bash
docker --version
# Should show: Docker version 24.x.x or higher

docker-compose --version
# Should show: Docker Compose version 2.x.x or higher
```

---

## 🚀 Quick Start: Run Your Entire Project

### Step 1: Navigate to Backend Directory
```bash
cd C:\Users\Dell\Documents\ProGestock
```

**Note:** The docker-compose.dev.yml file is located in the backend directory and will orchestrate both backend and frontend services.

### Step 2: Start All Services
```bash
docker-compose -f docker-compose.dev.yml up --build
```

**What This Does:**
- Builds Docker images for frontend and backend
- Starts both services
- Shows combined logs from both
- Runs backend migrations automatically
- Enables hot reloading (code changes reflect immediately)

**Expected Output:**
```
[+] Running 2/2
 ✔ Container progestock-backend-dev   Created
 ✔ Container progestock-frontend-dev  Created
Attaching to progestock-backend-dev, progestock-frontend-dev
progestock-backend-dev   | Django version 4.2.x, using settings 'progestock_backend.settings'
progestock-backend-dev   | Starting development server at http://0.0.0.0:8000/
progestock-frontend-dev  | VITE v4.x.x  ready in xxx ms
progestock-frontend-dev  | ➜  Local:   http://localhost:5173/
```

### Step 3: Access Your Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Backend Admin**: http://localhost:8000/admin
- **Health Check**: http://localhost:8000/health/

### Step 4: Test Google Login
1. Open http://localhost:5173
2. Click "Sign in with Google"
3. Complete authentication
4. Should redirect to dashboard ✅
5. No 401 errors! ✅

---

## 🛠️ Common Docker Commands

### Start Services (detached mode - runs in background)
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Stop Services
```bash
docker-compose -f docker-compose.dev.yml down
```

### View Logs (all services)
```bash
docker-compose -f docker-compose.dev.yml logs -f
```

### View Logs (specific service)
```bash
# Backend logs only
docker-compose -f docker-compose.dev.yml logs -f backend

# Frontend logs only
docker-compose -f docker-compose.dev.yml logs -f frontend
```

### Restart Services
```bash
docker-compose -f docker-compose.dev.yml restart
```

### Rebuild Images (after changing Dockerfile or requirements)
```bash
docker-compose -f docker-compose.dev.yml build

# Or rebuild and start
docker-compose -f docker-compose.dev.yml up --build
```

### Stop and Remove Everything (clean slate)
```bash
docker-compose -f docker-compose.dev.yml down -v
```
**Warning**: `-v` deletes volumes (database data). Use carefully!

---

## 📁 Docker Files Explained

### 1. `docker-compose.dev.yml` (Main Orchestration File)
**Location**: `C:\Users\Dell\Documents\ProGestock\docker-compose.dev.yml`

**What It Does:**
- Defines both frontend and backend services
- Sets up networking between services
- Configures environment variables
- Mounts source code for hot reloading
- Exposes ports to host machine

**Key Configuration:**
```yaml
services:
  backend:
    ports:
      - "8000:8000"  # Expose backend to localhost:8000
    volumes:
      - ./progestock_backend:/app  # Mount code for hot reload
    environment:
      - DEBUG=True  # Local development mode
      - DATABASE_URL=sqlite:///db.sqlite3  # SQLite for simplicity

  frontend:
    ports:
      - "5173:5173"  # Expose frontend to localhost:5173
    volumes:
      - ./progestock-frontend/progestock-frontend:/app
    environment:
      - VITE_API_BASE_URL=http://localhost:8000  # Browser accesses backend via host
```

### 2. `progestock_backend/Dockerfile` (Backend Image)
**What It Does:**
- Uses Python 3.12 base image
- Installs system dependencies (gcc, postgresql-client)
- Installs Python packages from `requirements.txt`
- Copies Django project files
- Runs migrations and starts server on port 8000

**Key Points:**
- Base Image: `python:3.12-slim`
- Working Directory: `/app`
- Exposed Port: `8000`
- Command: Runs migrations then starts Django dev server

### 3. `progestock-frontend/progestock-frontend/Dockerfile` (Frontend Image)
**What It Does:**
- Uses Node.js 20 Alpine base image
- Installs npm dependencies
- Copies React/Vite project files
- Starts Vite dev server with `--host 0.0.0.0` (allows external access)

**Key Points:**
- Base Image: `node:20-alpine`
- Working Directory: `/app`
- Exposed Port: `5173`
- Command: `npm run dev -- --host 0.0.0.0`

### 4. `.dockerignore` Files
**Purpose**: Tells Docker which files to skip when building images

**Backend** `.dockerignore`:
- Ignores: `venv/`, `__pycache__/`, `db.sqlite3`, `.env`
- Why: These are generated locally or contain secrets

**Frontend** `.dockerignore`:
- Ignores: `node_modules/`, `dist/`, `.env.local`
- Why: `node_modules` is rebuilt in container, dist is build output

---

## 🔄 Development Workflow with Docker

### Daily Workflow

#### Morning Setup:
```bash
# Start both services
cd C:\Users\Dell\Documents\ProGestock
docker-compose -f docker-compose.dev.yml up -d

# View logs (optional)
docker-compose -f docker-compose.dev.yml logs -f
```

#### During Development:
- **Edit frontend code** → Vite hot reloads automatically ✅
- **Edit backend code** → Django auto-reloads automatically ✅
- **Edit settings.py** → Backend restarts automatically ✅
- **Install new Python package** → Need to rebuild:
  ```bash
  docker-compose -f docker-compose.dev.yml build backend
  docker-compose -f docker-compose.dev.yml up backend -d
  ```
- **Install new npm package** → Need to rebuild:
  ```bash
  docker-compose -f docker-compose.dev.yml build frontend
  docker-compose -f docker-compose.dev.yml up frontend -d
  ```

#### End of Day:
```bash
# Stop services (keeps data)
docker-compose -f docker-compose.dev.yml down

# Or just let them run overnight (uses minimal resources)
```

---

## 🐛 Running Management Commands

### Backend (Django) Commands

#### Run Migrations
```bash
docker-compose -f docker-compose.dev.yml exec backend python manage.py migrate
```

#### Create Superuser
```bash
docker-compose -f docker-compose.dev.yml exec backend python manage.py createsuperuser
```

#### Create New App
```bash
docker-compose -f docker-compose.dev.yml exec backend python manage.py startapp myapp
```

#### Run Tests
```bash
docker-compose -f docker-compose.dev.yml exec backend python manage.py test
```

#### Shell Access (Django Shell)
```bash
docker-compose -f docker-compose.dev.yml exec backend python manage.py shell
```

#### Bash Shell (Container Terminal)
```bash
docker-compose -f docker-compose.dev.yml exec backend bash
```

### Frontend (React/Vite) Commands

#### Install New Package
```bash
docker-compose -f docker-compose.dev.yml exec frontend npm install package-name
```

#### Build for Production
```bash
docker-compose -f docker-compose.dev.yml exec frontend npm run build
```

#### Run Linter
```bash
docker-compose -f docker-compose.dev.yml exec frontend npm run lint
```

#### Shell Access (Container Terminal)
```bash
docker-compose -f docker-compose.dev.yml exec frontend sh
```

---

## 🗄️ Database Management

### SQLite Database Location
**Inside Container**: `/app/db.sqlite3`
**On Host Machine**: `C:\Users\Dell\Documents\ProGestock\progestock_backend\db.sqlite3`

Because we mount the backend directory as a volume, the SQLite database file persists on your host machine.

### Reset Database
```bash
# Stop services
docker-compose -f docker-compose.dev.yml down

# Delete database file
rm C:\Users\Dell\Documents\ProGestock\progestock_backend\db.sqlite3

# Start services (migrations run automatically)
docker-compose -f docker-compose.dev.yml up -d

# Create superuser
docker-compose -f docker-compose.dev.yml exec backend python manage.py createsuperuser
```

### Backup Database
```bash
# Copy from container to host
docker-compose -f docker-compose.dev.yml exec backend python manage.py dumpdata > backup.json

# Restore from backup
docker-compose -f docker-compose.dev.yml exec backend python manage.py loaddata backup.json
```

---

## 🔍 Debugging in Docker

### View Real-Time Logs
```bash
# All services
docker-compose -f docker-compose.dev.yml logs -f

# Just backend
docker-compose -f docker-compose.dev.yml logs -f backend

# Just frontend
docker-compose -f docker-compose.dev.yml logs -f frontend

# Last 100 lines
docker-compose -f docker-compose.dev.yml logs --tail=100
```

### Check Container Status
```bash
docker-compose -f docker-compose.dev.yml ps
```

**Expected Output:**
```
NAME                         STATUS              PORTS
progestock-backend-dev       Up 5 minutes        0.0.0.0:8000->8000/tcp
progestock-frontend-dev      Up 5 minutes        0.0.0.0:5173->5173/tcp
```

### Inspect Container
```bash
docker inspect progestock-backend-dev
docker inspect progestock-frontend-dev
```

### Check Resource Usage
```bash
docker stats
```

### Interactive Shell (for debugging)
```bash
# Backend
docker-compose -f docker-compose.dev.yml exec backend bash

# Frontend
docker-compose -f docker-compose.dev.yml exec frontend sh
```

---

## 🚨 Troubleshooting

### Issue 1: "Port already in use"
**Error**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution:**
```bash
# Check what's using the port
netstat -ano | findstr :8000

# Option 1: Kill the process
taskkill /PID <process_id> /F

# Option 2: Change port in docker-compose.dev.yml
ports:
  - "8001:8000"  # Change host port to 8001
```

### Issue 2: "Container keeps restarting"
**Check Logs:**
```bash
docker-compose -f docker-compose.dev.yml logs backend
```

**Common Causes:**
- Missing environment variables
- Database connection error
- Code syntax error
- Missing dependencies

### Issue 3: Code changes not reflecting
**Frontend:**
- Vite uses hot reload - should work automatically
- If not working:
  ```bash
  docker-compose -f docker-compose.dev.yml restart frontend
  ```

**Backend:**
- Django auto-reloads - should work automatically
- For `settings.py` changes, restart:
  ```bash
  docker-compose -f docker-compose.dev.yml restart backend
  ```

**If still not working:**
- Check volumes are mounted correctly in `docker-compose.dev.yml`
- Rebuild containers:
  ```bash
  docker-compose -f docker-compose.dev.yml up --build
  ```

### Issue 4: "Cannot connect to backend"
**Check:**
1. Backend container is running:
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   ```

2. Backend is healthy:
   ```bash
   curl http://localhost:8000/health/
   ```

3. Frontend env variable is correct:
   - Should be: `VITE_API_BASE_URL=http://localhost:8000`
   - Not: `http://backend:8000` (that's for container-to-container)

4. CORS settings allow localhost:
   - Check `settings.py` → `CORS_ALLOWED_ORIGINS` includes `http://localhost:5173`

### Issue 5: "Docker Daemon not running"
**Error**: `Cannot connect to the Docker daemon`

**Solution:**
1. Open Docker Desktop
2. Wait for "Docker Desktop is running"
3. Try command again

### Issue 6: Slow performance on Windows
**Issue**: Docker can be slower on Windows (especially with volumes)

**Solutions:**
- Use WSL 2 backend (Settings → General → Use WSL 2)
- Put project in WSL filesystem for better performance
- Increase Docker Desktop resources (Settings → Resources)

---

## 🎯 Docker vs Manual Setup Comparison

| Aspect | Manual Setup | Docker Setup |
|--------|-------------|--------------|
| **Initial Setup Time** | 15-30 minutes | 5 minutes |
| **Prerequisites** | Python, Node.js, pip, npm | Docker Desktop only |
| **Consistency** | Varies by machine | Same everywhere |
| **Isolation** | System-wide packages | Containerized |
| **Team Onboarding** | Setup docs needed | One command |
| **Cleanup** | Manual uninstall | Delete containers |
| **Port Conflicts** | Common | Rare |
| **Hot Reload** | ✅ Works | ✅ Works |
| **Debugging** | Easier | Slightly harder |

---

## 📚 Advanced: Production Docker Setup

Your project already has `docker-compose.yml` for a more complete production-like setup:

### Features:
- PostgreSQL database (instead of SQLite)
- Redis for caching and Celery broker
- Celery worker for async tasks
- Persistent volumes for data
- Health checks

### To Use:
```bash
# Use the full stack
docker-compose up -d

# This runs:
# - PostgreSQL on port 5432
# - Redis on port 6379
# - Django backend on port 8000
# - Celery worker
```

**When to use this:**
- Testing with PostgreSQL locally
- Developing async tasks with Celery
- Closer to production environment
- Before deploying to production

---

## 🎓 Docker Concepts Explained

### Images vs Containers
- **Image**: Blueprint (like a class in OOP)
- **Container**: Running instance (like an object)
- Build image once, run many containers from it

### Volumes
**Purpose**: Persist data and sync code

**Types**:
```yaml
volumes:
  # Bind mount (syncs host ↔ container)
  - ./progestock_backend:/app

  # Named volume (persists in Docker)
  - postgres_data:/var/lib/postgresql/data

  # Anonymous volume (prevents overwrite)
  - /app/node_modules
```

### Networks
**Purpose**: Allow containers to communicate

```yaml
networks:
  progestock-network:
    driver: bridge
```

- Backend and frontend can reach each other using service names
- `backend` container can ping `frontend` container by name

### Environment Variables
**Priority** (highest to lowest):
1. Command line: `docker run -e VAR=value`
2. docker-compose.yml: `environment:` section
3. env_file: `.env` file
4. Dockerfile: `ENV` directive

---

## ✅ Verification Checklist

### After First Setup:
- [ ] Docker Desktop installed and running
- [ ] Both services started successfully
- [ ] Backend accessible at http://localhost:8000
- [ ] Health check returns healthy: http://localhost:8000/health/
- [ ] Frontend accessible at http://localhost:5173
- [ ] Can log in with Google (no 401 errors)
- [ ] Code changes trigger hot reload
- [ ] Can access Django admin: http://localhost:8000/admin

### Daily Checklist:
- [ ] Docker Desktop is running
- [ ] Services started: `docker-compose -f docker-compose.dev.yml up -d`
- [ ] No error containers: `docker-compose -f docker-compose.dev.yml ps`
- [ ] Logs look normal: `docker-compose -f docker-compose.dev.yml logs --tail=20`

---

## 🎉 Success!

If you can:
1. ✅ Run `docker-compose -f docker-compose.dev.yml up -d`
2. ✅ Access frontend at http://localhost:5173
3. ✅ Log in with Google without errors
4. ✅ Edit code and see changes immediately

**You're successfully using Docker for local development!** 🐳

---

## 🆘 Need Help?

### Useful Commands for Support:
```bash
# Show Docker version
docker --version
docker-compose --version

# Show running containers
docker ps

# Show all containers (including stopped)
docker ps -a

# Show Docker disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

### Docker Desktop Logs:
- Windows: `%LOCALAPPDATA%\Docker\log.txt`
- Mac: `~/Library/Containers/com.docker.docker/Data/log`

### Common Resources:
- Docker Docs: https://docs.docker.com/
- Docker Compose Docs: https://docs.docker.com/compose/
- Django in Docker: https://docs.docker.com/samples/django/
- Vite in Docker: https://vitejs.dev/guide/

---

## 💡 Pro Tips

### Tip 1: Use Docker Desktop Dashboard
- Visual interface for managing containers
- See logs, stats, and files
- Start/stop containers with clicks

### Tip 2: Create Aliases
Add to your shell profile:
```bash
alias dup="docker-compose -f docker-compose.dev.yml up -d"
alias ddown="docker-compose -f docker-compose.dev.yml down"
alias dlogs="docker-compose -f docker-compose.dev.yml logs -f"
```

### Tip 3: Use .dockerignore
Keep images small by ignoring unnecessary files:
- Build artifacts
- Local dependencies
- Secrets and credentials

### Tip 4: Layer Caching
Order Dockerfile commands from least-to-most changing:
```dockerfile
# Copy requirements first (changes rarely)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code last (changes often)
COPY . .
```

### Tip 5: Multi-Stage Builds (for production)
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

---

## 🔗 Quick Reference Card

```bash
# Start services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down

# Rebuild
docker-compose -f docker-compose.dev.yml up --build

# Django commands
docker-compose -f docker-compose.dev.yml exec backend python manage.py <command>

# Shell access
docker-compose -f docker-compose.dev.yml exec backend bash
docker-compose -f docker-compose.dev.yml exec frontend sh

# Clean restart
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up --build -d
```

---

**Happy Dockerizing! 🐳🚀**
