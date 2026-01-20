# 🚀 AuraTask - Intelligent Task Manager

> A high-intelligence task manager with proactive notifications and NLP-powered task creation.

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)
![Redis](https://img.shields.io/badge/Redis-Alpine-red.svg)

## ✨ Features

- **🧠 NLP-Powered Task Entry** - Create tasks using natural language
- **⚡ Real-Time Updates** - WebSocket-based live dashboard
- **📊 Urgency Scoring** - Dynamic priority-based task ranking
- **🔔 Proactive Notifications** - Email, Telegram, Discord alerts (1hr & 24hr before due)
- **🌙 Dark Glassmorphism UI** - Modern, responsive frontend

---

## 📋 Quick Start

### Prerequisites
- Python 3.12+
- MySQL 8.0 (local or Docker)
- Redis (local or Docker)

### 1. Clone & Setup
```bash
git clone <repository>
cd to_do_waalidsaab

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and update:

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=auratask
DB_USER=root
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# JWT
SECRET_KEY=your-super-secret-key-change-in-production

# Gmail SMTP (see Gmail Setup below)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
```

### 3. Run with Docker (Recommended)
```bash
docker-compose up -d
```

### 4. Run Locally (Development)
```bash
# Terminal 1: Start backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Serve frontend
cd frontend
python -m http.server 3000
```

### 5. Access
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

---

## 🧠 Smart Entry - NLP Syntax

Create tasks using natural language in the Smart Entry bar:

### Priority Tags
| Tag | Priority Level |
|-----|---------------|
| `#Urgent` | 🔴 URGENT |
| `#High` | 🟠 HIGH |
| `#Medium` | 🟡 MEDIUM |
| `#Low` | 🟢 LOW |

### Date/Time Expressions
```
"Submit report by Friday 5pm"
"Call mom tomorrow at noon"
"Team meeting in 2 hours"
"Review PR by end of day"
"Dentist appointment next Monday 10am"
```

### Examples
| Input | Parsed Result |
|-------|--------------|
| `Fix login bug #Urgent by tomorrow 5pm` | Title: "Fix login bug", Priority: URGENT, Due: Tomorrow 5PM |
| `Send invoice to client #High Friday` | Title: "Send invoice to client", Priority: HIGH, Due: Friday |
| `Buy groceries` | Title: "Buy groceries", Priority: MEDIUM, Due: +24 hours |

---

## 📧 Gmail App Password Setup

To enable email notifications, you need a Gmail App Password:

### Step 1: Enable 2-Factor Authentication
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable "2-Step Verification"

### Step 2: Generate App Password
1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Select app: "Mail"
3. Select device: "Other" → Enter "AuraTask"
4. Click "Generate"
5. Copy the 16-character password

### Step 3: Update `.env`
```env
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # App Password (without spaces)
SMTP_FROM_EMAIL=your_email@gmail.com
```

---

## 🔧 Database Migrations (Alembic)

### Generate Migration
```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback
```bash
alembic downgrade -1
```

---

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Restart services
docker-compose restart backend

# Stop all
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

---

## 📁 Project Structure

```
to_do_waalidsaab/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── crud/          # Database operations
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic (NLP, Urgency)
│   │   ├── workers/       # Celery tasks
│   │   └── main.py        # Application entry
│   ├── alembic/           # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── css/style.css      # Glassmorphism dark theme
│   ├── js/
│   │   ├── api.js         # API service
│   │   ├── websocket.js   # WebSocket client
│   │   └── app.js         # Main application
│   └── index.html
└── docker-compose.yml
```

---

## 🔗 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Get JWT token |
| GET | `/api/auth/me` | Get current user |
| GET | `/api/tasks/` | List all tasks |
| POST | `/api/tasks/` | Create task (NLP support) |
| PUT | `/api/tasks/{id}` | Update task |
| POST | `/api/tasks/{id}/complete` | Mark complete |
| POST | `/api/tasks/{id}/snooze` | Snooze task |
| DELETE | `/api/tasks/{id}` | Delete task |
| GET | `/api/notifications/settings` | Get notification prefs |
| PUT | `/api/notifications/settings` | Update notification prefs |

---

## 📜 License

MIT License - See LICENSE file for details.

---

Built with ❤️ using FastAPI, SQLAlchemy, Celery, and Vanilla JS.
