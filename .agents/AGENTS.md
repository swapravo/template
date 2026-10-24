# AGENTS.md — Technical Requirements Document
> **Scope**: All projects in this workspace follow these rules.
> **Purpose**: Enforce consistent architecture, prevent code sprawl, and make every project instantly navigable by humans and agents alike.
> Last updated: 2026-10-24

---

## 1. Tech Stack

### 1.1 Backend
- **Language**: Python 3.10
- **Framework**: FastAPI
- **Database driver**: `asyncpg` (no ORM)
- **Task queue**: Celery with Redis as broker and result backend
- **Package manager**: `pip` with a pinned `requirements.txt`

### 1.2 Frontend
- **Language**: TypeScript
- **Runtime**: Node.js (LTS)
- **Framework**: To be defined per project (Next.js preferred for apps)

### 1.3 Landing Pages
- **Framework**: Astro

### 1.4 Infrastructure
- **Database**: PostgreSQL 16
- **File Storage**: RustFS
- **Cache / Broker**: Redis

### 1.5 LLM
- **Provider**: OpenRouter (single provider — do not add others)
- **Model**: Controlled exclusively via `LLM_MODEL` in `config.py`
- **Switching models**: Change `LLM_MODEL` only — no other code changes required

---

## 2. Python Backend — File Responsibilities

Every file below has a **strict, exclusive scope**. Functions must live in exactly one file. When in doubt, refer to the rules in Section 3.

### 2.1 `main.py`
- FastAPI app instantiation
- Middleware registration (logging, rate limiting, CORS)
- Router mounting via `app.include_router(...)`
- Startup and shutdown lifecycle events (e.g. opening/closing the DB pool)
- **No business logic. No DB calls. No direct route handlers.**

### 2.2 `config.py`
- All configuration loaded from environment variables using `pydantic BaseSettings`
- Covers: `DATABASE_URL`, `REDIS_URL`, `RUSTFS_*`, `LLM_MODEL`, `OPENROUTER_API_KEY`, `SECRET_KEY`, app-level feature flags
- **Only file allowed to read `os.environ` or `.env`**
- All other files import from `config.py` — never from `os.environ` directly

```python
# Example shape
class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    RUSTFS_ENDPOINT: str
    RUSTFS_ACCESS_KEY: str
    RUSTFS_SECRET_KEY: str
    RUSTFS_BUCKET: str
    OPENROUTER_API_KEY: str
    LLM_MODEL: str = "openai/gpt-4o"  # Change this to switch models
    SECRET_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
```

### 2.3 `database.py`
- `asyncpg` connection pool initialisation and teardown
- **All** database query functions — reads, writes, deletes, upserts
- Functions are `async def` and return plain Python `dict`, `list[dict]`, or `None`
- Raw SQL only — no query builders, no ORM
- **No business logic. No Pydantic model construction. No HTTP calls.**

```python
# Example pattern
async def get_user_by_id(pool: asyncpg.Pool, user_id: str) -> dict | None:
    row = await pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    return dict(row) if row else None
```

### 2.4 `schemas.py`
- All Pydantic `BaseModel` classes for request bodies, response shapes, and internal data transfer objects
- All dataclasses used across the project
- **No database calls. No file I/O. No HTTP calls.**
- Every schema is pure: it validates and serializes data, nothing else

```python
# Example
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime
```

### 2.5 `schema.sql`
- Raw SQL source of truth for the entire database structure
- Contains: `CREATE TABLE`, `CREATE INDEX`, `CREATE ROLE`, constraints, triggers
- **No ORM. No migration tool. No Python.**
- Changes to DB structure go here first
- Use versioned comment blocks to track changes:

```sql
-- [2026-10-24] Initial schema
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.6 `tasks.py`
- All Celery task definitions using `@celery_app.task`
- Tasks are **thin dispatchers** — they call functions from other modules, they do not implement logic themselves
- Celery app instance is initialised here
- **No raw DB queries. No HTTP calls inline. No business logic.**

```python
# Example pattern
@celery_app.task
def send_welcome_email_task(user_id: str):
    # delegates to llm.py, utils.py, etc.
    user = asyncio.run(database.get_user_by_id(pool, user_id))
    llm.generate_welcome_email(user)
```

### 2.7 `llm.py`
- OpenRouter API client setup
- All prompt templates
- All LLM inference calls
- Reads `LLM_MODEL` and `OPENROUTER_API_KEY` from `config.py`
- **Only file allowed to call the OpenRouter API**
- Model is never hardcoded here — always `settings.LLM_MODEL`

```python
# Example pattern
async def complete(prompt: str, system: str = "") -> str:
    # calls OpenRouter, uses settings.LLM_MODEL
    ...
```

### 2.8 `storage.py`
- RustFS client initialisation
- All file operations: upload, download, delete, generate presigned URLs
- Reads `RUSTFS_*` settings from `config.py`
- **Only file allowed to call RustFS**
- Returns file URLs or raw bytes — never writes to local disk unless explicitly needed for temp processing

### 2.9 `sessions.py`
- Session creation, storage, retrieval, validation, and expiry
- Redis-backed session store
- Responsible for generating and verifying session tokens
- **No route logic. No DB calls (sessions live in Redis only).**

### 2.10 `rate_limit.py`
- Redis-backed rate limiting
- Implemented as FastAPI middleware and/or decorator
- Configurable limits (requests per window) drawn from `config.py`
- **No business logic. No DB calls.**

### 2.11 `request_log.py`
- FastAPI middleware for structured request/response logging
- Logs: method, path, status code, response time, user/session ID if available
- **Read-only — never modifies requests or responses.**
- **No DB calls. No business logic.**

### 2.12 `validation.py`
- Custom business-rule validators that go beyond Pydantic's built-in checks
- Examples: password strength rules, email domain blacklists, username character rules
- Functions are **pure** — they take a value and return `bool` or raise `ValueError`
- **No DB calls. No Pydantic models. No HTTP calls.**

### 2.13 `utils.py`
- Pure helper functions with no side effects
- Examples: string slugification, date formatting, UUID generation, hashing
- **No DB calls. No HTTP calls. No file I/O. No imports from other project modules.**
- Every function here must be unit-testable without mocks

### 2.14 `routers/`
- One file per **feature domain**
- Each router file contains only FastAPI route handlers for that domain
- Route handlers: validate input (via schemas), call functions from other modules, return responses
- **No raw SQL. No direct asyncpg calls. No `os.environ` access.**

```
routers/
├── users.py       # registration, login, profile CRUD
├── files.py       # file upload, download, delete
├── jobs.py        # trigger and status-check of background Celery tasks
└── health.py      # GET /health (liveness), GET /ready (readiness)
```

### 2.15 `tests/`
- Mirrors the module structure of the app
- Uses `pytest` and `pytest-asyncio`
- No production secrets in test files — use fixtures and `.env.test`
- Each module gets its own test file

```
tests/
├── conftest.py
├── test_routers/
│   ├── test_users.py
│   ├── test_files.py
│   └── test_health.py
├── test_database.py
├── test_tasks.py
├── test_llm.py
├── test_storage.py
├── test_sessions.py
├── test_validation.py
└── test_utils.py
```

---

## 3. Hard Rules

These rules are non-negotiable. Violations must be corrected before any code is considered complete.

### 3.1 Import Rules

| Forbidden | Correct |
|---|---|
| `import os; os.environ["KEY"]` outside `config.py` | `from config import settings; settings.KEY` |
| `import asyncpg` outside `database.py` | Call a function from `database.py` |
| Raw SQL string outside `database.py` | Add a function to `database.py` |
| `httpx` / `requests` call in a router | Route through `llm.py` or `storage.py` |
| `from openai import ...` outside `llm.py` | Call a function from `llm.py` |
| RustFS/S3 client outside `storage.py` | Call a function from `storage.py` |

### 3.2 Purity Rules
- `utils.py` functions must have **zero imports from other project modules**
- `validation.py` functions must be **pure** (no I/O, no network)
- `schemas.py` must never trigger I/O of any kind

### 3.3 Task Rules
- Celery tasks in `tasks.py` must not contain inline business logic
- Tasks call functions — they do not reimplement them
- Long-running tasks must update a status field in Redis or DB

### 3.4 Schema Rules
- All request and response types must be defined in `schemas.py` before being used in routers
- No ad-hoc `dict` returns from route handlers — always return a Pydantic model
- `schema.sql` is the **only** place DB structure is defined — never infer structure from code

### 3.5 LLM Rules
- `LLM_MODEL` in `config.py` is the **single control point** for switching models
- All prompt strings live in `llm.py` — not in routers, not in tasks
- Never hardcode a model name outside `config.py`

### 3.6 Config Rules
- `.env` is git-ignored — always
- `.env.example` is committed with all keys and placeholder values
- All secrets come from environment variables, never from source code

---

## 4. Naming Conventions

### 4.1 Python
- Files: `snake_case.py`
- Functions: `snake_case`
- Classes / Pydantic models: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Async functions: prefix with verb — `get_`, `create_`, `delete_`, `update_`, `send_`

### 4.2 Database (SQL)
- Tables: `snake_case`, plural nouns (e.g. `users`, `file_uploads`)
- Columns: `snake_case`
- Primary keys: always `id UUID`
- Timestamps: `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`
- Foreign keys: `{referenced_table_singular}_id` (e.g. `user_id`)
- Indexes: `idx_{table}_{column}` (e.g. `idx_users_email`)

### 4.3 API Routes
- Path: `kebab-case` (e.g. `/api/v1/file-uploads`)
- HTTP verbs follow REST conventions strictly
- Version prefix on all routes: `/api/v1/`

### 4.4 Environment Variables
- All caps, underscore-separated: `DATABASE_URL`, `LLM_MODEL`, `RUSTFS_BUCKET`
- Grouped by service prefix: `RUSTFS_*`, `OPENROUTER_*`, `REDIS_*`

---

## 5. Project Directory Layout

```
project-root/
├── .env                    # git-ignored
├── .env.example            # committed, all keys with placeholders
├── requirements.txt        # pinned dependencies
├── schema.sql              # DB source of truth
├── main.py
├── config.py
├── database.py
├── schemas.py
├── tasks.py
├── llm.py
├── storage.py
├── sessions.py
├── rate_limit.py
├── request_log.py
├── validation.py
├── utils.py
├── routers/
│   ├── __init__.py
│   ├── users.py
│   ├── files.py
│   ├── jobs.py
│   └── health.py
└── tests/
    ├── conftest.py
    ├── test_routers/
    ├── test_database.py
    ├── test_tasks.py
    ├── test_llm.py
    ├── test_storage.py
    ├── test_sessions.py
    ├── test_validation.py
    └── test_utils.py
```

---

## 6. What Goes Where — Quick Reference

| I need to... | File to edit |
|---|---|
| Add a new API endpoint | `routers/{feature}.py` |
| Add a new DB query | `database.py` |
| Add a new table or column | `schema.sql` |
| Add a new request/response type | `schemas.py` |
| Change the LLM model | `config.py` → `LLM_MODEL` |
| Add a new LLM prompt | `llm.py` |
| Add a background job | `tasks.py` (dispatcher) + relevant module (logic) |
| Add a file upload/download | `storage.py` |
| Add a new config variable | `config.py` + `.env.example` |
| Add a session utility | `sessions.py` |
| Add a reusable helper | `utils.py` (if pure) or `validation.py` (if business rule) |
| Add rate limiting to a route | `rate_limit.py` decorator on the route |
