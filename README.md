<p align="center">
  <img src="https://img.shields.io/badge/AuraTask-⚡-purple?style=for-the-badge&logoColor=white" alt="AuraTask Logo"/>
</p>

<h1 align="center">⚡ AuraTask</h1>

<p align="center">
  <strong>Intelligent Task Manager with AI-Powered NLP & Proactive Notifications</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql&logoColor=white" alt="MySQL"/>
  <img src="https://img.shields.io/badge/Redis-Alpine-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis"/>
  <img src="https://img.shields.io/badge/Celery-5.3+-37814A?style=flat-square&logo=celery&logoColor=white" alt="Celery"/>
  <img src="https://img.shields.io/badge/Groq_AI-LLM-FF6B35?style=flat-square" alt="Groq AI"/>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-smart-entry">Smart Entry</a> •
  <a href="#-api-docs">API</a> •
  <a href="#-architecture">Architecture</a>
</p>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🧠 AI-Powered NLP with Groq
- **Natural Language Processing** using Groq AI (Llama 3.3 70B)
- **Python-Based Relative Time Parsing** - Accurate calculations for "in 62 minutes", "in 2 hours"
- **Priority Detection** - Automatically extracts urgency from context
- Say *"Submit report #Urgent by Friday 5pm"* and AuraTask understands it all

### ⚡ Real-Time Updates  
WebSocket-based live dashboard. See changes instantly across all your devices.

### 📊 Smart Urgency Scoring
Dynamic priority ranking algorithm that adapts based on:
- Due date proximity
- Priority level
- Task status

</td>
<td width="50%">

### 🔔 Intelligent Notifications
Get reminders at **3 perfect times**:
- ⏰ **24 hours before** - Plan ahead
- ⏰ **1 hour before** - Last chance prep
- � **AT DUE TIME** - Time's up!

**Multi-Channel Delivery:**
- 📧 Email (Gmail SMTP)
- 📱 Telegram Bot
- 🎮 Discord Webhooks

### 🔐 Enterprise-Grade Security
- **Field-Level Encryption** - Telegram/Discord credentials encrypted at rest (Fernet AES-128-CBC)
- **JWT Authentication** - Secure token-based auth
- **Settings Modal** - Easy credential management via ⚙️ Settings button

### 🌙 Modern Dark UI
Glassmorphism design with smooth animations and responsive layout.

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.12+ |
| MySQL | 8.0+ |
| Redis | Latest |

### Installation

```bash
# 1. Clone repository
git clone https://github.com/IBM07/To-Do-List-End-to-End-.git
cd To-Do-List-End-to-End-

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/Mac

# 3. Install dependencies
cd backend
pip install -r requirements.txt
```

### Configuration

```bash
# Copy example config
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Database
DB_HOST=localhost
DB_PASSWORD=your_secure_password

# JWT Secret (generate: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=your-secret-key-here

# Encryption Key (generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-encryption-key-here

# Gmail SMTP
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Optional: Server-level Telegram/Discord (for admin notifications)
# Users configure their own channels via Settings button in app
TELEGRAM_BOT_TOKEN=your_bot_token
```

### Run

<table>
<tr>
<th>🐳 Docker (Recommended)</th>
<th>💻 Local Development</th>
</tr>
<tr>
<td>

```bash
docker-compose up -d
```

</td>
<td>

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Celery Worker
celery -A app.workers.celery_app worker --loglevel=info --pool=solo

# Terminal 3: Celery Beat
celery -A app.workers.celery_app beat --loglevel=info

# Terminal 4: Frontend
cd frontend
python -m http.server 3000
```

</td>
</tr>
</table>

### Access

| Service | URL |
|---------|-----|
| 🌐 Frontend | http://localhost:3000 |
| 📚 API Docs | http://localhost:8000/docs |
| 📖 ReDoc | http://localhost:8000/redoc |

---

## 🧠 Smart Entry

Create tasks using natural language in the Smart Entry bar:

### Priority Tags

| Tag | Level | Color |
|-----|-------|-------|
| `#Urgent` | 🔴 URGENT | Red |
| `#High` | 🟠 HIGH | Orange |
| `#Medium` | 🟡 MEDIUM | Yellow |
| `#Low` | 🟢 LOW | Green |

### Time Expressions

**Groq AI understands natural dates:**
```
✅ "Submit report by Friday 5pm"
✅ "Call mom tomorrow at noon"  
✅ "Dentist appointment next Monday 10am"
```

**Python handles relative times (100% accurate!):**
```
✅ "Team meeting in 2 hours"
✅ "Review PR in 30 minutes"
✅ "Submit assignment in 62 minutes"  ← Precise calculation!
```

### Examples

| Input | Result |
|-------|--------|
| `Fix login bug #Urgent by tomorrow 5pm` | Title: "Fix login bug" • Priority: 🔴 URGENT • Due: Tomorrow 5PM |
| `Send invoice #High Friday` | Title: "Send invoice" • Priority: 🟠 HIGH • Due: Friday |
| `Buy groceries in 2 hours` | Title: "Buy groceries" • Priority: 🟡 MEDIUM • Due: +2 hours |

---

## ⚙️ Settings Modal

Configure your notification channels directly in the app via the **⚙️ Settings** button:

1. **Login** to your account
2. Click the **⚙️ icon** (top right corner)
3. Enter your credentials:
   - **Telegram Chat ID** - Get from [@userinfobot](https://t.me/userinfobot)
   - **Discord Webhook URL** - Create in your server settings
4. Click **Save Settings**

Your credentials are **encrypted at rest** using Fernet (AES-128-CBC) - not even the database admin can read them!

---

## 🔔 Notification Channels

### 📧 Email (Gmail)

Configure server-wide in `.env`:

1. Enable [2-Step Verification](https://myaccount.google.com/security)
2. Generate [App Password](https://myaccount.google.com/apppasswords)
3. Add to `.env`:
   ```env
   SMTP_USER=your_email@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
   ```

### 📱 Telegram

**Option 1: Server Bot (in `.env`)**
```env
TELEGRAM_BOT_TOKEN=your_bot_token
```

**Option 2: Per-User (via ⚙️ Settings Modal)**
- Get your Chat ID from [@userinfobot](https://t.me/userinfobot)
- Configure in app ⚙️ Settings
- Your chat ID is **encrypted** in the database ✅

### 🎮 Discord

**Per-User via ⚙️ Settings Modal:**
- Create Webhook in your Discord server
- Configure in app ⚙️ Settings  
- Your webhook URL is **encrypted** in the database ✅

---

## 📚 API Docs

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | Get JWT token |
| `GET` | `/api/auth/me` | Get current user |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tasks/` | List all tasks |
| `POST` | `/api/tasks/` | Create task (NLP) |
| `PUT` | `/api/tasks/{id}` | Update task |
| `POST` | `/api/tasks/{id}/complete` | Mark complete |
| `POST` | `/api/tasks/{id}/snooze` | Snooze task |
| `DELETE` | `/api/tasks/{id}` | Delete task |

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/notifications/settings` | Get preferences |
| `PUT` | `/api/notifications/settings` | Update preferences |
| `POST` | `/api/notifications/test` | Send test notification |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Port 3000)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  index.html │  │   app.js    │  │ websocket.js│              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BACKEND - FastAPI (Port 8000)                  │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐    │
│  │  Auth   │  │  Tasks   │  │ WebSocket │  │ Notifications│    │
│  │  API    │  │  API     │  │  Handler  │  │    API       │    │
│  └────┬────┘  └────┬─────┘  └─────┬─────┘  └──────┬───────┘    │
│       └────────────┼──────────────┼───────────────┘             │
│                    ▼              ▼                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Services Layer                              │    │
│  │  ┌───────────┐  ┌──────────────┐  ┌─────────────────┐   │    │
│  │  │ Groq AI   │  │   Urgency    │  │  Notification   │   │    │
│  │  │ NLP Parser│  │   Scorer     │  │   Scheduler     │   │    │
│  │  └───────────┘  └──────────────┘  └─────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌────────────────┐
        │  MySQL   │  │  Redis   │  │ Celery Workers │
        │ Database │  │  Broker  │  │  (Beat/Worker) │
        └──────────┘  └──────────┘  └───────┬────────┘
                                             │
                      ┌──────────────────────┼──────────────────┐
                      ▼                      ▼                  ▼
                ┌──────────┐          ┌──────────┐       ┌──────────┐
                │  Email   │          │ Telegram │       │ Discord  │
                │   SMTP   │          │   Bot    │       │ Webhook  │
                └──────────┘          └──────────┘       └──────────┘
```

---

## 📁 Project Structure

```
📦 To-Do-List-End-to-End-
├── 📂 backend/
│   ├── 📂 app/
│   │   ├── 📂 api/          # FastAPI routes
│   │   ├── 📂 crud/         # Database operations
│   │   ├── 📂 models/       # SQLAlchemy models
│   │   ├── 📂 schemas/      # Pydantic schemas
│   │   ├── 📂 services/     # Business logic
│   │   ├── 📂 utils/        # Utilities (encryption)
│   │   ├── 📂 workers/      # Celery tasks
│   │   └── 📄 main.py       # App entry point
│   ├── 📂 alembic/          # DB migrations
│   ├── 📄 Dockerfile
│   └── 📄 requirements.txt
├── 📂 frontend/
│   ├── 📂 css/              # Glassmorphism styles
│   ├── 📂 js/               # Application logic
│   └── 📄 index.html
├── 📄 docker-compose.yml
└── 📄 README.md
```

---

## 🔧 Development

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Docker Commands

```bash
docker-compose up -d          # Start all
docker-compose logs -f backend # View logs
docker-compose restart backend # Restart
docker-compose down           # Stop all
docker-compose up -d --build  # Rebuild
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ using <strong>FastAPI</strong>, <strong>SQLAlchemy</strong>, <strong>Celery</strong>, <strong>Groq AI</strong>, and <strong>Vanilla JS</strong>
</p>

<p align="center">
  <a href="https://github.com/IBM07/To-Do-List-End-to-End-">⭐ Star this repo</a> •
  <a href="https://github.com/IBM07/To-Do-List-End-to-End-/issues">🐛 Report Bug</a> •
  <a href="https://github.com/IBM07/To-Do-List-End-to-End-/issues">✨ Request Feature</a>
</p>
