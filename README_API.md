# Shortcut Email Alias API — Endpoint Reference

This document provides a comprehensive reference for every API endpoint exposed by the Shortcut Email Alias backend. For setup, deployment, and architecture details see [README.md](README.md).

**Base URL (default local):** `http://localhost:8000`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Common Error Responses](#common-error-responses)
3. [Session Status Values](#session-status-values)
4. [Alias Status Values](#alias-status-values)
5. [Health](#health)
6. [Public Session Endpoints](#public-session-endpoints)
   - [Create Session](#1-create-session)
   - [Get Session Status](#2-get-session-status)
   - [Get Session Result](#3-get-session-result)
   - [Cancel Session](#4-cancel-session)
7. [Admin — Parsing Rules](#admin--parsing-rules)
   - [Create Parsing Rule](#5-create-parsing-rule)
   - [List Parsing Rules](#6-list-parsing-rules)
   - [Update Parsing Rule](#7-update-parsing-rule)
8. [Admin — Gmail](#admin--gmail)
   - [Trigger Gmail Sync](#8-trigger-gmail-sync)
   - [Renew Gmail Watch](#9-renew-gmail-watch)
9. [Admin — Sessions](#admin--sessions)
   - [List All Sessions](#10-list-all-sessions)
10. [Admin — Messages](#admin--messages)
    - [List Incoming Messages](#11-list-incoming-messages)
11. [Admin — Aliases](#admin--aliases)
    - [List Aliases](#12-list-aliases)
12. [Admin — Cleanup](#admin--cleanup)
    - [Run Cleanup](#13-run-cleanup)
13. [Interactive Docs](#interactive-docs)

---

## Authentication

### Public endpoints — `X-Client-Token`

Session endpoints (except `POST /api/v1/sessions`) require a client token that is issued at session creation time.

| Header | Value |
|--------|-------|
| `X-Client-Token` | Raw token returned in the `client_token` field of `POST /api/v1/sessions` |

The token is shown **only once** at creation time. Store it securely. Supplying a missing or invalid token returns `401 Unauthorized`.

### Admin endpoints — `X-Admin-Token`

All `/api/v1/admin/*` endpoints require an admin token that matches the `ADMIN_TOKEN` environment variable configured on the server.

| Header | Value |
|--------|-------|
| `X-Admin-Token` | Value of the `ADMIN_TOKEN` environment variable |

Supplying a missing or invalid admin token returns `403 Forbidden`.

---

## Common Error Responses

| HTTP Status | When it occurs |
|-------------|----------------|
| `401 Unauthorized` | `X-Client-Token` header is missing or does not match any session |
| `403 Forbidden` | `X-Admin-Token` header is missing or incorrect |
| `404 Not Found` | The requested resource (session, rule, …) does not exist |
| `422 Unprocessable Entity` | Request body or query parameters fail validation (FastAPI default) |

---

## Session Status Values

The `SessionStatus` enum describes the lifecycle of a verification session.

| Value | Meaning |
|-------|---------|
| `reserved` | Alias has been reserved; session object created but not yet active |
| `waiting` | Session is active and polling for an incoming verification email |
| `received` | A matching email has been received; code extraction in progress |
| `extracted` | Verification code was successfully extracted |
| `expired` | Session reached its TTL without a successful result |
| `failed` | An internal error occurred during processing |
| `cancelled` | The client explicitly cancelled the session |

---

## Alias Status Values

The `AliasStatus` enum describes the lifecycle of a generated email alias.

| Value | Meaning |
|-------|---------|
| `reserved` | Alias is reserved but not yet in active use |
| `waiting` | Alias is active and awaiting an incoming email |
| `received` | An email has arrived at this alias |
| `extracted` | A code was extracted from the email delivered to this alias |
| `expired` | Alias expired without successful extraction |
| `failed` | Processing failed for this alias |
| `retired` | Alias has been permanently retired and will not be reused |

---

## Health

### GET `/health`

Performs a lightweight health check across all system components. No authentication required.

**Response 200 — `HealthResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Overall system status: `"ok"` or `"degraded"` |
| `app` | `ComponentHealth` | Application-level status |
| `db` | `ComponentHealth` | Database connectivity status |
| `gmail` | `ComponentHealth` | Gmail integration status |
| `worker` | `ComponentHealth` | Background worker status |

**`ComponentHealth` object**

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `"ok"` or `"error"` |
| `detail` | `string \| null` | Human-readable detail message when status is not `"ok"` |

The overall `status` is `"ok"` only when both `db` and `gmail` components report `"ok"`. Any degraded component results in `"degraded"`.

**curl example**

```bash
curl http://localhost:8000/health
```

**Example response**

```json
{
  "status": "ok",
  "app": { "status": "ok", "detail": null },
  "db":  { "status": "ok", "detail": null },
  "gmail": { "status": "ok", "detail": null },
  "worker": { "status": "ok", "detail": null }
}
```

**Example degraded response**

```json
{
  "status": "degraded",
  "app": { "status": "ok", "detail": null },
  "db":  { "status": "error", "detail": "Connection refused" },
  "gmail": { "status": "ok", "detail": null },
  "worker": { "status": "ok", "detail": null }
}
```

**Possible error codes:** None (always returns 200).

---

## Public Session Endpoints

These endpoints are called by the iOS Shortcut (or any HTTP client) to manage verification sessions.

---

### 1. Create Session

**`POST /api/v1/sessions`**

Creates a new alias-based verification session. The response contains a one-time `client_token` that must be stored by the caller and used as `X-Client-Token` on all subsequent calls for this session.

**Authentication:** None required.

**Request body (`SessionCreate`)** — all fields optional

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `domain` | `string` | No | server default | Custom alias domain override (e.g. `mail-one4all.uk`) |
| `alias_length` | `integer` | No | server default | Length of the random part of the alias (min: 4, max: 64) |
| `source_label` | `string` | No | `null` | Human-readable label for tracking (e.g. `"Uber signup"`) |
| `metadata` | `object` | No | `null` | Arbitrary key-value pairs stored with the session |

**Response 201 — `SessionCreateResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `string` | Public identifier for this session |
| `client_token` | `string` | Raw bearer token — **shown only once**, store immediately |
| `alias` | `string` | Generated email alias (e.g. `xk9mn2p4@mail-one4all.uk`) |
| `expires_at` | `datetime` | ISO 8601 UTC timestamp when the session expires |
| `status` | `SessionStatus` | Current status (`"waiting"` on creation) |

**curl example**

```bash
curl -s -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "source_label": "Uber signup",
    "alias_length": 8
  }'
```

**Example response**

```json
{
  "session_id": "sess_abc123xyz",
  "client_token": "ct_rawTokenShownOnlyOnce",
  "alias": "xk9mn2p4@mail-one4all.uk",
  "expires_at": "2026-03-28T03:42:39Z",
  "status": "waiting"
}
```

**Possible error codes:** `422` (invalid body fields).

---

### 2. Get Session Status

**`GET /api/v1/sessions/{session_id}/status`**

Returns the current status of a session. Useful for polling from an iOS Shortcut to detect when a code has arrived.

**Authentication:** `X-Client-Token` header required.

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | `string` | Session identifier returned by Create Session |

**Response 200 — `SessionStatusResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `string` | Session identifier |
| `status` | `SessionStatus` | Current session status |
| `alias` | `string` | Email alias associated with this session |
| `expires_at` | `datetime` | ISO 8601 UTC expiration timestamp |
| `last_checked_at` | `datetime \| null` | Last time the worker polled for this session |
| `code_found` | `boolean` | `true` if a verification code has been extracted |
| `completed` | `boolean` | `true` if the session is in a terminal state |

**curl example**

```bash
curl -s http://localhost:8000/api/v1/sessions/sess_abc123xyz/status \
  -H "X-Client-Token: ct_rawTokenShownOnlyOnce"
```

**Example response**

```json
{
  "session_id": "sess_abc123xyz",
  "status": "extracted",
  "alias": "xk9mn2p4@mail-one4all.uk",
  "expires_at": "2026-03-28T03:42:39Z",
  "last_checked_at": "2026-03-28T02:45:00Z",
  "code_found": true,
  "completed": true
}
```

**Possible error codes:** `401` (missing/invalid token), `404` (session not found).

---

### 3. Get Session Result

**`GET /api/v1/sessions/{session_id}/result`**

Returns the extracted verification code for a completed session, along with a summary of the matched email message.

**Authentication:** `X-Client-Token` header required.

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | `string` | Session identifier returned by Create Session |

**Response 200 — `SessionResultResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `string` | Session identifier |
| `status` | `SessionStatus` | Current session status |
| `code` | `string \| null` | Extracted verification code, or `null` if not yet available |
| `matched_message_summary` | `MessageSummary \| null` | Details of the email that contained the code |
| `completed_at` | `datetime \| null` | ISO 8601 UTC timestamp when extraction completed |

**`MessageSummary` object**

| Field | Type | Description |
|-------|------|-------------|
| `gmail_message_id` | `string` | Internal Gmail message ID |
| `from_address` | `string \| null` | Sender email address |
| `subject` | `string \| null` | Email subject line |
| `internal_date` | `datetime \| null` | Timestamp of the email as reported by Gmail |

**curl example**

```bash
curl -s http://localhost:8000/api/v1/sessions/sess_abc123xyz/result \
  -H "X-Client-Token: ct_rawTokenShownOnlyOnce"
```

**Example response**

```json
{
  "session_id": "sess_abc123xyz",
  "status": "extracted",
  "code": "483921",
  "matched_message_summary": {
    "gmail_message_id": "18e4b2c3d1a5f6b7",
    "from_address": "no-reply@uber.com",
    "subject": "Your Uber verification code",
    "internal_date": "2026-03-28T02:44:55Z"
  },
  "completed_at": "2026-03-28T02:45:01Z"
}
```

**Example response (code not yet available)**

```json
{
  "session_id": "sess_abc123xyz",
  "status": "waiting",
  "code": null,
  "matched_message_summary": null,
  "completed_at": null
}
```

**Possible error codes:** `401` (missing/invalid token), `404` (session not found).

---

### 4. Cancel Session

**`POST /api/v1/sessions/{session_id}/cancel`**

Cancels an active session. The alias is released and no further processing will occur for this session.

**Authentication:** `X-Client-Token` header required.

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | `string` | Session identifier returned by Create Session |

**Response 200 — `SessionCancelResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `string` | Session identifier |
| `status` | `SessionStatus` | Updated status (will be `"cancelled"`) |

**curl example**

```bash
curl -s -X POST http://localhost:8000/api/v1/sessions/sess_abc123xyz/cancel \
  -H "X-Client-Token: ct_rawTokenShownOnlyOnce"
```

**Example response**

```json
{
  "session_id": "sess_abc123xyz",
  "status": "cancelled"
}
```

**Possible error codes:** `401` (missing/invalid token), `404` (session not found).

---

## Admin — Parsing Rules

Parsing rules define how the worker extracts verification codes from incoming email bodies using regular expressions. All endpoints require `X-Admin-Token`.

---

### 5. Create Parsing Rule

**`POST /api/v1/admin/parsing-rules`**

Creates a new regex-based parsing rule.

**Authentication:** `X-Admin-Token` header required.

**Request body (`ParsingRuleCreate`)**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `string` | **Yes** | — | Human-readable rule name |
| `enabled` | `boolean` | No | `true` | Whether the rule is active |
| `priority` | `integer` | No | `100` | Evaluation order (lower = higher priority, min: 0) |
| `sender_pattern` | `string` | No | `null` | Regex matched against the sender email address |
| `subject_pattern` | `string` | No | `null` | Regex matched against the email subject |
| `body_regex` | `string` | **Yes** | — | Regex applied to the email body to extract the code |
| `code_capture_group` | `integer` | No | `1` | Capture group index that contains the code (min: 1) |
| `description` | `string` | No | `null` | Optional human-readable description |

**Response 201 — `ParsingRuleOut`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Auto-assigned rule ID |
| `name` | `string` | Rule name |
| `enabled` | `boolean` | Whether rule is active |
| `priority` | `integer` | Rule priority |
| `sender_pattern` | `string \| null` | Sender regex filter |
| `subject_pattern` | `string \| null` | Subject regex filter |
| `body_regex` | `string` | Body extraction regex |
| `code_capture_group` | `integer` | Capture group index |
| `description` | `string \| null` | Description |
| `created_at` | `datetime` | ISO 8601 creation timestamp |
| `updated_at` | `datetime` | ISO 8601 last-update timestamp |

**curl example**

```bash
curl -s -X POST http://localhost:8000/api/v1/admin/parsing-rules \
  -H "X-Admin-Token: my-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Generic 6-digit code",
    "body_regex": "\\b([0-9]{6})\\b",
    "priority": 50,
    "description": "Matches any standalone 6-digit number in the body"
  }'
```

**Example response**

```json
{
  "id": 3,
  "name": "Generic 6-digit code",
  "enabled": true,
  "priority": 50,
  "sender_pattern": null,
  "subject_pattern": null,
  "body_regex": "\\b([0-9]{6})\\b",
  "code_capture_group": 1,
  "description": "Matches any standalone 6-digit number in the body",
  "created_at": "2026-03-28T02:42:39Z",
  "updated_at": "2026-03-28T02:42:39Z"
}
```

**Possible error codes:** `403` (invalid admin token), `422` (invalid body fields).

---

### 6. List Parsing Rules

**`GET /api/v1/admin/parsing-rules`**

Returns all parsing rules ordered by `priority` ascending (lowest priority number evaluated first).

**Authentication:** `X-Admin-Token` header required.

**Response 200** — array of `ParsingRuleOut` (see schema in [Create Parsing Rule](#5-create-parsing-rule)).

**curl example**

```bash
curl -s http://localhost:8000/api/v1/admin/parsing-rules \
  -H "X-Admin-Token: my-admin-secret"
```

**Example response**

```json
[
  {
    "id": 1,
    "name": "Uber OTP",
    "enabled": true,
    "priority": 10,
    "sender_pattern": "no-reply@uber\\.com",
    "subject_pattern": null,
    "body_regex": "Your code is (\\d{4})",
    "code_capture_group": 1,
    "description": "Extracts 4-digit Uber codes",
    "created_at": "2026-03-01T10:00:00Z",
    "updated_at": "2026-03-01T10:00:00Z"
  },
  {
    "id": 3,
    "name": "Generic 6-digit code",
    "enabled": true,
    "priority": 50,
    "sender_pattern": null,
    "subject_pattern": null,
    "body_regex": "\\b([0-9]{6})\\b",
    "code_capture_group": 1,
    "description": "Matches any standalone 6-digit number in the body",
    "created_at": "2026-03-28T02:42:39Z",
    "updated_at": "2026-03-28T02:42:39Z"
  }
]
```

**Possible error codes:** `403` (invalid admin token).

---

### 7. Update Parsing Rule

**`PATCH /api/v1/admin/parsing-rules/{rule_id}`**

Partially updates an existing parsing rule. Only fields provided in the request body are modified.

**Authentication:** `X-Admin-Token` header required.

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | `integer` | ID of the rule to update |

**Request body (`ParsingRuleUpdate`)** — all fields optional

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | New rule name |
| `enabled` | `boolean` | Enable or disable the rule |
| `priority` | `integer` | New priority value (min: 0) |
| `sender_pattern` | `string \| null` | New sender regex (pass `null` to clear) |
| `subject_pattern` | `string \| null` | New subject regex (pass `null` to clear) |
| `body_regex` | `string` | New body extraction regex |
| `code_capture_group` | `integer` | New capture group index (min: 1) |
| `description` | `string \| null` | New description (pass `null` to clear) |

**Response 200 — `ParsingRuleOut`** (updated rule, see schema above).

**curl example**

```bash
curl -s -X PATCH http://localhost:8000/api/v1/admin/parsing-rules/3 \
  -H "X-Admin-Token: my-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

**Example response**

```json
{
  "id": 3,
  "name": "Generic 6-digit code",
  "enabled": false,
  "priority": 50,
  "sender_pattern": null,
  "subject_pattern": null,
  "body_regex": "\\b([0-9]{6})\\b",
  "code_capture_group": 1,
  "description": "Matches any standalone 6-digit number in the body",
  "created_at": "2026-03-28T02:42:39Z",
  "updated_at": "2026-03-28T02:50:00Z"
}
```

**Possible error codes:** `403` (invalid admin token), `404` (rule not found), `422` (invalid body fields).

---

## Admin — Gmail

Endpoints for manually controlling the Gmail integration. All require `X-Admin-Token`.

---

### 8. Trigger Gmail Sync

**`POST /api/v1/admin/gmail/sync-now`**

Triggers an immediate Gmail polling cycle outside of the normal worker schedule. Returns the number of messages processed.

**Authentication:** `X-Admin-Token` header required.

**Request body:** None.

**Response 200**

| Field | Type | Description |
|-------|------|-------------|
| `processed` | `integer` | Number of messages fetched and processed in this sync cycle |

**curl example**

```bash
curl -s -X POST http://localhost:8000/api/v1/admin/gmail/sync-now \
  -H "X-Admin-Token: my-admin-secret"
```

**Example response**

```json
{ "processed": 4 }
```

**Possible error codes:** `403` (invalid admin token).

---

### 9. Renew Gmail Watch

**`POST /api/v1/admin/watch/renew`**

Renews the Gmail push notification watch subscription. Gmail watches expire every ~7 days; call this endpoint to extend the subscription without restarting the server.

**Authentication:** `X-Admin-Token` header required.

**Request body:** None.

**Response 200**

| Field | Type | Description |
|-------|------|-------------|
| `history_id` | `string \| integer` | Gmail history ID at the point the watch was renewed |

**curl example**

```bash
curl -s -X POST http://localhost:8000/api/v1/admin/watch/renew \
  -H "X-Admin-Token: my-admin-secret"
```

**Example response**

```json
{ "history_id": "1234567" }
```

**Possible error codes:** `403` (invalid admin token).

---

## Admin — Sessions

### 10. List All Sessions

**`GET /api/v1/admin/sessions`**

Returns a paginated list of all verification sessions across all clients.

**Authentication:** `X-Admin-Token` header required.

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | `integer` | `0` | Number of records to skip (offset) |
| `limit` | `integer` | `50` | Maximum number of records to return |

**Response 200** — array of `SessionStatusResponse`

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `string` | Session identifier |
| `status` | `SessionStatus` | Current session status |
| `alias` | `string` | Email alias associated with the session |
| `expires_at` | `datetime` | Session expiration timestamp |
| `last_checked_at` | `datetime \| null` | Last worker poll time |
| `code_found` | `boolean` | Whether a code was extracted |
| `completed` | `boolean` | Whether the session is in a terminal state |

**curl example**

```bash
curl -s "http://localhost:8000/api/v1/admin/sessions?skip=0&limit=10" \
  -H "X-Admin-Token: my-admin-secret"
```

**Example response**

```json
[
  {
    "session_id": "sess_abc123xyz",
    "status": "extracted",
    "alias": "xk9mn2p4@mail-one4all.uk",
    "expires_at": "2026-03-28T03:42:39Z",
    "last_checked_at": "2026-03-28T02:45:00Z",
    "code_found": true,
    "completed": true
  },
  {
    "session_id": "sess_def456uvw",
    "status": "waiting",
    "alias": "ab3cd5ef@mail-one4all.uk",
    "expires_at": "2026-03-28T04:00:00Z",
    "last_checked_at": null,
    "code_found": false,
    "completed": false
  }
]
```

**Possible error codes:** `403` (invalid admin token).

---

## Admin — Messages

### 11. List Incoming Messages

**`GET /api/v1/admin/messages`**

Returns a paginated list of all incoming email messages received by the system.

**Authentication:** `X-Admin-Token` header required.

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | `integer` | `0` | Number of records to skip (offset) |
| `limit` | `integer` | `50` | Maximum number of records to return |

**Response 200** — array of `IncomingMessageOut`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Internal database ID |
| `gmail_message_id` | `string` | Gmail message identifier |
| `thread_id` | `string \| null` | Gmail thread identifier |
| `to_address` | `string` | The `To:` address the message was delivered to |
| `delivered_alias` | `string` | The alias that received this message |
| `from_address` | `string \| null` | Sender email address |
| `subject` | `string \| null` | Email subject line |
| `internal_date` | `datetime \| null` | Gmail internal timestamp of the email |
| `snippet` | `string \| null` | Gmail-provided short snippet of the body |
| `parsed_code` | `string \| null` | Extracted verification code (if any) |
| `parsed_at` | `datetime \| null` | When the code was extracted |
| `session_id` | `string \| null` | Associated session ID (if matched) |
| `created_at` | `datetime` | When the record was stored in the database |

**curl example**

```bash
curl -s "http://localhost:8000/api/v1/admin/messages?skip=0&limit=5" \
  -H "X-Admin-Token: my-admin-secret"
```

**Example response**

```json
[
  {
    "id": 42,
    "gmail_message_id": "18e4b2c3d1a5f6b7",
    "thread_id": "18e4b2c3d1a5f6b0",
    "to_address": "xk9mn2p4@mail-one4all.uk",
    "delivered_alias": "xk9mn2p4@mail-one4all.uk",
    "from_address": "no-reply@uber.com",
    "subject": "Your Uber verification code",
    "internal_date": "2026-03-28T02:44:55Z",
    "snippet": "Your verification code is 483921. It expires in 10 minutes.",
    "parsed_code": "483921",
    "parsed_at": "2026-03-28T02:45:01Z",
    "session_id": "sess_abc123xyz",
    "created_at": "2026-03-28T02:45:00Z"
  }
]
```

**Possible error codes:** `403` (invalid admin token).

---

## Admin — Aliases

### 12. List Aliases

**`GET /api/v1/admin/aliases`**

Returns a paginated list of all email aliases managed by the system.

**Authentication:** `X-Admin-Token` header required.

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | `integer` | `0` | Number of records to skip (offset) |
| `limit` | `integer` | `50` | Maximum number of records to return |

**Response 200** — array of `AliasOut`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Internal database ID |
| `local_part` | `string` | The part before `@` (e.g. `xk9mn2p4`) |
| `domain` | `string` | The domain part (e.g. `mail-one4all.uk`) |
| `full_address` | `string` | Complete email address (e.g. `xk9mn2p4@mail-one4all.uk`) |
| `status` | `AliasStatus` | Current alias lifecycle status |
| `created_at` | `datetime` | When the alias was created |
| `reserved_at` | `datetime \| null` | When the alias was reserved |
| `used_at` | `datetime \| null` | When the alias first received a message |
| `expired_at` | `datetime \| null` | When the alias expired |
| `retired_at` | `datetime \| null` | When the alias was retired |
| `was_recycled` | `boolean` | Whether this alias was previously used and recycled |

**curl example**

```bash
curl -s "http://localhost:8000/api/v1/admin/aliases?skip=0&limit=10" \
  -H "X-Admin-Token: my-admin-secret"
```

**Example response**

```json
[
  {
    "id": 7,
    "local_part": "xk9mn2p4",
    "domain": "mail-one4all.uk",
    "full_address": "xk9mn2p4@mail-one4all.uk",
    "status": "retired",
    "created_at": "2026-03-28T02:42:00Z",
    "reserved_at": "2026-03-28T02:42:00Z",
    "used_at": "2026-03-28T02:44:55Z",
    "expired_at": null,
    "retired_at": "2026-03-28T02:45:02Z",
    "was_recycled": false
  }
]
```

**Possible error codes:** `403` (invalid admin token).

---

## Admin — Cleanup

### 13. Run Cleanup

**`POST /api/v1/admin/cleanup`**

Manually triggers the expired session cleanup job. This job is also run automatically by the background cleanup worker, but this endpoint lets you invoke it on demand.

**Authentication:** `X-Admin-Token` header required.

**Request body:** None.

**Response 200** — cleanup result object

The response is a dictionary describing what was cleaned up. Fields may vary but typically include counts of expired sessions and aliases that were processed.

**curl example**

```bash
curl -s -X POST http://localhost:8000/api/v1/admin/cleanup \
  -H "X-Admin-Token: my-admin-secret"
```

**Example response**

```json
{
  "expired_sessions": 3,
  "retired_aliases": 3
}
```

**Possible error codes:** `403` (invalid admin token).

---

## Interactive Docs

FastAPI automatically generates interactive API documentation. When the server is running, open the following URLs in your browser:

| UI | URL | Description |
|----|-----|-------------|
| **Swagger UI** | `http://localhost:8000/docs` | Interactive explorer — try requests directly from the browser |
| **ReDoc** | `http://localhost:8000/redoc` | Clean, read-only reference UI |
| **OpenAPI JSON** | `http://localhost:8000/openapi.json` | Raw OpenAPI 3.x schema for code generation or import into tools like Postman/Insomnia |
