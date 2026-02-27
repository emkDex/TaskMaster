# TaskMaster Pro

A production-grade **Task Management REST API** built with **FastAPI**, **SQLAlchemy 2.x async**, and **PostgreSQL**. Features JWT authentication, real-time WebSocket notifications, full audit logging, and a clean layered architecture.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         HTTP / WebSocket                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    FastAPI Routes (app/api/v1/)                  │
│  auth · users · tasks · teams · comments · attachments          │
│  notifications · activity_logs · admin · websocket              │
└──────────────────────────────┬──────────────────────────────────┘
                               │ calls
┌──────────────────────────────▼──────────────────────────────────┐
│                   Service Layer (app/services/)                  │
│  AuthService · TaskService · TeamService                        │
│  NotificationService · ActivityService · WebSocketService       │
└──────────────────────────────┬──────────────────────────────────┘
                               │ calls
┌──────────────────────────────▼──────────────────────────────────┐
│                    CRUD Layer (app/crud/)                        │
│  CRUDBase[Model, Create, Update]                                │
│  CRUDUser · CRUDTask · CRUDTeam · CRUDComment                  │
│  CRUDAttachment · CRUDNotification                              │
└──────────────────────────────┬──────────────────────────────────┘
                               │ queries
┌──────────────────────────────▼──────────────────────────────────┐
│              SQLAlchemy 2.x Async ORM (app/models/)             │
│  User · Task · Team · TeamMember · Comment                      │
│  Attachment · Notification · ActivityLog                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                  PostgreSQL (asyncpg driver)                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

- **JWT Authentication** — Access tokens (15 min) + Refresh tokens (7 days) with rotation & revocation
- **Role-Based Access Control** — `user` and `admin` roles with fine-grained permission checks
- **Task Management** — Full CRUD with status/priority enums, tags (PostgreSQL ARRAY), soft-delete
- **Team Collaboration** — Teams with member roles (`member`, `manager`), ownership enforcement
- **Real-Time Notifications** — WebSocket push + persistent DB notifications
- **File Attachments** — Multipart upload with size validation
- **Activity Audit Log** — Immutable JSONB-backed audit trail for all actions
- **Rate Limiting** — `slowapi` on login endpoint (5 req/min per IP)
- **Pagination** — Generic `PaginatedResponse[T]` on all list endpoints
- **Alembic Migrations** — Async-compatible, explicit initial migration

---

## Project Structure

```
taskmaster/
├── alembic/
│   ├── versions/
│   │   └── 001_initial_tables.py
│   ├── env.py
│   └── alembic.ini
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py          # pydantic-settings
│   │   ├── security.py        # JWT + bcrypt
│   │   ├── dependencies.py    # FastAPI Depends()
│   │   └── exceptions.py      # Custom HTTP exceptions
│   ├── db/
│   │   ├── base.py            # SQLAlchemy Base
│   │   └── session.py         # Async engine + get_db
│   ├── models/                # ORM models
│   ├── schemas/               # Pydantic v2 schemas
│   ├── crud/                  # Generic + domain CRUD
│   ├── services/              # Business logic
│   └── api/v1/                # Route handlers
├── tests/
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ (or use Neon/Supabase/Railway)
- Docker & Docker Compose (optional)

### Local Development

```bash
# 1. Clone and enter the project
cd taskmaster

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL and secret keys

# 5. Run database migrations
alembic upgrade head

# 6. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Compose (Local Dev with PostgreSQL)

```bash
# Copy and configure environment
cp .env.example .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop
docker-compose down
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | ✅ | — | JWT access token signing key (min 32 chars) |
| `REFRESH_SECRET_KEY` | ✅ | — | JWT refresh token signing key (min 32 chars) |
| `ALGORITHM` | | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | `15` | Access token TTL in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | | `7` | Refresh token TTL in days |
| `ALLOWED_ORIGINS` | | `["*"]` | CORS allowed origins (JSON array) |
| `DEBUG` | | `False` | Enable SQLAlchemy query logging |
| `MAX_FILE_SIZE_MB` | | `10` | Maximum file upload size |
| `UPLOAD_DIR` | | `uploads/` | Local file storage directory |
| `RATE_LIMIT_LOGIN` | | `5/minute` | Login rate limit per IP |

---

## API Endpoints

### Authentication — `/api/v1/auth`

| Method | Path | Description |
|---|---|---|
| POST | `/register` | Register new user → 201 |
| POST | `/login` | Login → access + refresh token |
| POST | `/refresh` | Refresh access token |
| POST | `/logout` | Invalidate refresh token |

### Users — `/api/v1/users`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/me` | User | Get current user profile |
| PUT | `/me` | User | Update profile |
| PUT | `/me/password` | User | Change password |
| GET | `/` | Admin | List all users |
| GET | `/{user_id}` | Admin | Get user by ID |
| PATCH | `/{user_id}` | Admin | Update user role/status |
| DELETE | `/{user_id}` | Admin | Deactivate user |

### Tasks — `/api/v1/tasks`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | User | List tasks (paginated + filtered) |
| POST | `/` | User | Create task |
| GET | `/{task_id}` | User | Get task |
| PUT | `/{task_id}` | Owner/Manager/Admin | Update task |
| DELETE | `/{task_id}` | Owner/Manager/Admin | Archive task |
| POST | `/{task_id}/assign` | Owner/Manager/Admin | Assign task |
| GET | `/team/{team_id}` | Member | List team tasks |

**Task Filter Query Params:** `status`, `priority`, `assigned_to_id`, `team_id`, `is_archived`, `due_date_from`, `due_date_to`, `search`, `page`, `size`

### Teams — `/api/v1/teams`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/` | User | Create team |
| GET | `/` | User | List my teams |
| GET | `/{team_id}` | Member | Get team with members |
| PUT | `/{team_id}` | Owner/Admin | Update team |
| DELETE | `/{team_id}` | Owner/Admin | Delete team |
| POST | `/{team_id}/members` | Manager/Admin | Add member |
| PATCH | `/{team_id}/members/{user_id}` | Owner/Admin | Update member role |
| DELETE | `/{team_id}/members/{user_id}` | Manager/Admin | Remove member |

### Comments — `/api/v1/tasks/{task_id}/comments`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | User | List comments |
| POST | `/` | User | Add comment |
| PUT | `/{comment_id}` | Author/Admin | Edit comment |
| DELETE | `/{comment_id}` | Author/Admin | Delete comment |

### Attachments — `/api/v1/tasks/{task_id}/attachments`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | User | List attachments |
| POST | `/` | User | Upload file (multipart/form-data) |
| DELETE | `/{attachment_id}` | Uploader/Admin | Delete attachment |

### Notifications — `/api/v1/notifications`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | User | List my notifications |
| PUT | `/read-all` | User | Mark all as read |
| PUT | `/{notification_id}/read` | User | Mark one as read |

### Activity Logs — `/api/v1/activity`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | User | My activity |
| GET | `/task/{task_id}` | User | Task activity |
| GET | `/admin` | Admin | All system activity |

### Admin — `/api/v1/admin`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/stats` | Admin | Dashboard statistics |
| GET | `/users` | Admin | Full user list |
| GET | `/tasks` | Admin | All tasks |

### WebSocket — `/ws/{user_id}?token=<access_token>`

Real-time notification delivery. Heartbeat ping/pong every 30 seconds.

---

## Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback all
alembic downgrade base

# Check current revision
alembic current

# View migration history
alembic history
```

---

## Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

Tests use an **in-memory SQLite** database via `aiosqlite` — no external database required.

---

## Deployment

### Render

1. Create a new **Web Service** pointing to this repository
2. Set **Build Command**: `pip install -r requirements.txt`
3. Set **Start Command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables from `.env.example`
5. Use a **Neon** or **Supabase** PostgreSQL database

### Railway

1. Create a new project and connect your repository
2. Add a **PostgreSQL** plugin — Railway auto-injects `DATABASE_URL`
3. Set remaining environment variables
4. Deploy — Railway auto-detects the `Dockerfile`

### Fly.io

```bash
# Install flyctl and login
fly auth login

# Launch app
fly launch

# Set secrets
fly secrets set SECRET_KEY=... REFRESH_SECRET_KEY=... DATABASE_URL=...

# Deploy
fly deploy
```

---

## Security Notes

- Passwords are hashed with **bcrypt** (cost factor 12)
- Refresh tokens are stored as **SHA-256 hashes** — never the raw token
- Sensitive data (passwords, tokens) is **never logged**
- All inputs are validated by **Pydantic v2** schemas
- Rate limiting on login prevents brute-force attacks
- UUIDs are used everywhere — no sequential integer IDs exposed

---

## License

MIT
