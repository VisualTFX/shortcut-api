# Shortcut Email Alias API

A production-ready backend service for an iOS Shortcut that:

1. Generates one-time email aliases on your custom domain (`mail-one4all.uk`)
2. Monitors Gmail for incoming emails to those aliases
3. Extracts verification codes from email bodies using configurable regex rules
4. Returns the code to your Shortcut via a simple REST API

---

## Architecture

```
iOS Shortcut
    │
    ▼
POST /api/v1/sessions     ──►  Generate alias, create session
GET  /api/v1/sessions/{id}/status   (polls every few seconds)
GET  /api/v1/sessions/{id}/result   (when code found)
    │
    ▼
FastAPI Backend
    ├── Alias Service        generates & permanently records aliases
    ├── Session Service      lifecycle management + auth
    ├── Gmail Worker         polls or receives push notifications
    ├── Parsing Engine       regex-based code extraction
    └── PostgreSQL / SQLite  permanent alias history
```

---

## Quick Start — Windows (Local Dev)

### Prerequisites

- Python 3.12+
- Git

### 1. Clone and set up

```powershell
git clone <repo-url>
cd shortcut-api

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure

```powershell
copy .env.example .env
# Edit .env with your preferred values
```

The default `.env` uses SQLite — no database setup required.

### 3. Set up Gmail OAuth

```powershell
# Follow the Google Cloud setup instructions below, then:
python scripts/gmail_auth.py
```

### 4. Run

```powershell
uvicorn app.main:app --reload
```

API is now available at `http://localhost:8000`

---

## Google Cloud / Gmail Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the **Gmail API**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Desktop app**
6. Download the JSON and save as `credentials.json` in your project root
7. Run `python scripts/gmail_auth.py` — a browser window will open for consent
8. The token is saved to `token.json` — keep it secret

Minimum required scopes (configured automatically):
- `gmail.readonly`
- `gmail.modify`

---

## Docker / Cloud Deployment

### Docker Compose (PostgreSQL)

```bash
# Copy and edit environment
cp .env.example .env

# Add your Gmail credentials
cp /path/to/credentials.json .
cp /path/to/token.json .       # if already authenticated

# Start everything
docker compose up -d
```

### Railway / Render / Fly.io

1. Set all environment variables from `.env.example` in the platform dashboard
2. Set `DATABASE_URL` to your hosted PostgreSQL connection string
3. Mount `credentials.json` and `token.json` as secrets/volumes
4. Deploy

---

## Configuration Reference (`.env`)

| Variable | Default | Description |
|---|---|---|
| `ALIAS_DOMAIN` | `mail-one4all.uk` | Your catch-all email domain |
| `ALIAS_LENGTH` | `12` | Random part length |
| `ALIAS_CHARSET` | `abcdefghjkmnpqrstuvwxyz23456789` | No ambiguous chars |
| `SESSION_TTL_SECONDS` | `600` | Session expiry (10 min) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./shortcut_api.db` | DB connection string |
| `GMAIL_STRATEGY` | `polling` | `polling` or `watch` |
| `GMAIL_POLL_INTERVAL_SECONDS` | `10` | Polling frequency |
| `ADMIN_TOKEN` | `change-me` | Admin endpoint protection |
| `RETENTION_ENABLED` | `false` | Store raw email bodies |
| `RECYCLE_ENABLED` | `false` | Allow alias reuse |

---

## API Reference

### Public (iOS Shortcut) Endpoints

#### Create a session

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{}'
```

Response:
```json
{
  "session_id": "abc123def456",
  "client_token": "raw-token-shown-once",
  "alias": "xk9mn2p4@mail-one4all.uk",
  "expires_at": "2024-01-01T12:10:00Z",
  "status": "waiting"
}
```

#### Check status

```bash
curl http://localhost:8000/api/v1/sessions/abc123def456/status \
  -H "X-Client-Token: raw-token-shown-once"
```

#### Get result (poll until `code_found: true`)

```bash
curl http://localhost:8000/api/v1/sessions/abc123def456/result \
  -H "X-Client-Token: raw-token-shown-once"
```

Response when code found:
```json
{
  "session_id": "abc123def456",
  "status": "extracted",
  "code": "6601",
  "matched_message_summary": {
    "gmail_message_id": "...",
    "from_address": "noreply@uber.com",
    "subject": "Welcome to Uber"
  },
  "completed_at": "2024-01-01T12:03:45Z"
}
```

#### Cancel session

```bash
curl -X POST http://localhost:8000/api/v1/sessions/abc123def456/cancel \
  -H "X-Client-Token: raw-token-shown-once"
```

#### Health check

```bash
curl http://localhost:8000/health
```

---

### Admin Endpoints

All require `X-Admin-Token` header (set `ADMIN_TOKEN` in `.env`).

```bash
# List all sessions
curl http://localhost:8000/api/v1/admin/sessions \
  -H "X-Admin-Token: your-admin-token"

# List parsing rules
curl http://localhost:8000/api/v1/admin/parsing-rules \
  -H "X-Admin-Token: your-admin-token"

# Trigger Gmail sync now
curl -X POST http://localhost:8000/api/v1/admin/gmail/sync-now \
  -H "X-Admin-Token: your-admin-token"

# Run cleanup
curl -X POST http://localhost:8000/api/v1/admin/cleanup \
  -H "X-Admin-Token: your-admin-token"
```

---

## iOS Shortcut Request Flow

Here is the recommended Shortcut logic:

```
1. HTTP Request:
   Method: POST
   URL: https://your-api.example.com/api/v1/sessions
   Body: {"source_label": "Uber signup"}
   → Store session_id and client_token

2. Show Alert: "Use this email: [alias]"
   (User copies alias and uses it in sign-up form)

3. Repeat Until (up to 60 iterations, 5 second wait):
   HTTP Request:
     Method: GET
     URL: https://your-api.example.com/api/v1/sessions/[session_id]/result
     Headers: X-Client-Token: [client_token]
   If result.status == "extracted":
     → Show Notification: "Code: [result.code]"
     → Copy to Clipboard: [result.code]
     → Exit loop
   If result.status == "expired" or "cancelled":
     → Show Alert: "Session expired"
     → Exit loop
   Wait 5 seconds

4. (Optional) Cancel on early exit:
   HTTP Request:
     Method: POST
     URL: .../sessions/[session_id]/cancel
     Headers: X-Client-Token: [client_token]
```

---

## Gmail Integration Modes

### Polling (default, recommended for simplicity)

```env
GMAIL_STRATEGY=polling
GMAIL_POLL_INTERVAL_SECONDS=10
```

The worker polls Gmail every 10 seconds for new messages.

### Push/Watch (lower latency, requires Google Cloud Pub/Sub)

```env
GMAIL_STRATEGY=watch
```

Requires a Google Cloud Pub/Sub topic and a public HTTPS endpoint. See
[Gmail Push Notifications](https://developers.google.com/gmail/api/guides/push) for setup.

---

## Alias Non-Reuse Guarantee

- Every generated alias is immediately inserted into the `aliases` table with a `UNIQUE` constraint on `full_address`
- If a collision occurs (same random string generated again), `IntegrityError` is caught and a new alias is generated
- Aliases are **never deleted** — expired, failed, and cancelled aliases remain as permanent history
- Even with `RECYCLE_ENABLED=false` (default), old aliases cannot be reassigned
- The database is the single source of truth — no in-memory sets

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

## Project Structure

```
app/
  main.py              FastAPI app + lifespan
  api/v1/
    endpoints/
      sessions.py      Public Shortcut-facing endpoints
      admin.py         Admin endpoints
      health.py        Health check
  core/
    config.py          Settings via pydantic-settings
    security.py        Token generation + hashing
    logging.py         Structured logging
  db/
    base.py            SQLAlchemy declarative base
    session.py         Async session factory
  models/              ORM models (Alias, VerificationSession, ...)
  schemas/             Pydantic request/response schemas
  services/
    alias_service.py   Alias generation with uniqueness guarantee
    session_service.py Session lifecycle
    cleanup_service.py Expired session cleanup
  integrations/gmail/
    auth.py            OAuth credential management
    client.py          Gmail API wrapper with retry
    processor.py       Message parsing and DB storage
    watcher.py         Watch/push management
  parsing/
    engine.py          Regex rule engine
    default_rules.py   Built-in parsing rules
  workers/
    gmail_worker.py    Background Gmail polling/watch loop
    cleanup_worker.py  Background session expiry loop
  utils/
    tokens.py          Public ID generation
tests/
  conftest.py
  test_alias_service.py
  test_session_service.py
  test_parsing_engine.py
  test_api_sessions.py
  test_gmail_processor.py
alembic/               Database migrations
scripts/
  gmail_auth.py        OAuth setup
  seed_rules.py        Seed default parsing rules
```
