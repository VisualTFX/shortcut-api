# Shortcut Email Alias API — Complete Setup Guide

> **See also:** [README.md](README.md) for an architecture overview · [README_API.md](README_API.md) for the full endpoint reference.

---

## Table of Contents

**Part 1 — Windows Setup for Public Usage**

1. [Prerequisites](#1-prerequisites)
2. [Step 1: Clone & Create Virtual Environment](#step-1-clone--create-virtual-environment)
3. [Step 2: Configure Environment](#step-2-configure-environment)
4. [Step 3: Set Up Gmail OAuth](#step-3-set-up-gmail-oauth)
5. [Step 4: Set Up Your Catch-All Domain](#step-4-set-up-your-catch-all-domain)
6. [Step 5: Run Locally](#step-5-run-locally)
7. [Step 6: Expose to the Internet (Public Usage)](#step-6-expose-to-the-internet-public-usage)
8. [Step 7: Run as a Windows Background Service](#step-7-run-as-a-windows-background-service)
9. [Step 8: (Optional) PostgreSQL Instead of SQLite](#step-8-optional-postgresql-instead-of-sqlite)
10. [Security Checklist](#security-checklist)

**Part 2 — iOS Shortcuts Integration**

11. [Overview](#overview)
12. [Step 1: Create the Shortcut](#step-1-create-the-shortcut)
13. [Step 2: Test the Shortcut](#step-2-test-the-shortcut)
14. [Quick Reference: Shortcut Variables](#quick-reference-shortcut-variables)
15. [Advanced: Add a Cancel Button](#advanced-add-a-cancel-button)
16. [Troubleshooting](#troubleshooting)

**Part 3 — Verifying Everything Works**

17. [End-to-End Verification](#end-to-end-verification)

---

# Part 1 — Windows Setup for Public Usage

## 1. Prerequisites

Before you begin, make sure you have all of the following:

### Required Software

| Software | Minimum Version | Download |
|---|---|---|
| **Python** | 3.12+ | https://www.python.org/downloads/ |
| **Git** | Any recent | https://git-scm.com/download/win |

During the Python installer, tick **"Add Python to PATH"** — this is required so PowerShell can find `python` and `pip`.

Verify both are installed:

```powershell
python --version   # Should print Python 3.12.x or higher
git --version      # Should print git version 2.x.x
```

### Required Accounts & Services

**A domain with catch-all email forwarding to Gmail**

The alias system works by generating random email addresses like `xk9mn2p4@mail-one4all.uk`. For this to work, your domain must have **catch-all routing** — meaning *any* address at your domain (`anything@yourdomain.com`) is silently accepted and forwarded to a single Gmail inbox. You do not need to create individual mailboxes for each alias.

If you already own a domain (e.g. via Namecheap, Cloudflare, Google Domains), you can configure catch-all forwarding in a few minutes. [Step 4](#step-4-set-up-your-catch-all-domain) covers this in detail.

> **Example:** This repo defaults to `mail-one4all.uk`. Replace all references to that domain with your own domain throughout this guide.

**A Google account (Gmail)**

The API monitors a Gmail inbox for incoming emails to your aliases and extracts verification codes from them. You need a Google account and a Google Cloud project with the Gmail API enabled.

**A Google Cloud Project**

Used to create OAuth 2.0 credentials so the API can read your Gmail inbox. [Step 3](#step-3-set-up-gmail-oauth) covers the full setup.

---

## Step 1: Clone & Create Virtual Environment

Open **PowerShell** (Windows key → type `PowerShell` → Enter) and run each command in order:

```powershell
# 1. Clone the repository
git clone https://github.com/VisualTFX/shortcut-api.git

# 2. Change into the project directory
cd shortcut-api

# 3. Create a Python virtual environment
python -m venv .venv

# 4. Activate the virtual environment
.venv\Scripts\activate
```

> **You will see `(.venv)` appear at the start of your PowerShell prompt.** This confirms the virtual environment is active. All subsequent commands in this guide assume the virtual environment is active.

```powershell
# 5. Install all dependencies
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, the Google API client, and all other packages listed in `requirements.txt`. Expect it to take 1–2 minutes.

---

## Step 2: Configure Environment

### 2a. Copy the example configuration

```powershell
copy .env.example .env
```

### 2b. Open `.env` in a text editor

```powershell
notepad .env
```

### 2c. Full `.env` variable reference

The table below explains **every variable**. Variables marked **Must Change** need to be updated before going public.

| Variable | Default | Change? | Description |
|---|---|---|---|
| `ALIAS_DOMAIN` | `mail-one4all.uk` | **Must Change** | Your catch-all domain. Replace with your own domain (e.g. `myaliases.com`). |
| `ALIAS_LENGTH` | `12` | Optional | Number of random characters in each alias. 12 is a good balance of readability and uniqueness. |
| `ALIAS_CHARSET` | `abcdefghjkmnpqrstuvwxyz23456789` | Leave | Safe charset — excludes visually ambiguous characters (`l`, `1`, `o`, `0`). |
| `ALIAS_PREFIX` | *(empty)* | Optional | Static prefix prepended to every alias, e.g. `sc-` → `sc-xk9mn2p4@yourdomain.com`. |
| `ALIAS_SUFFIX` | *(empty)* | Optional | Static suffix appended to the random part (before `@`). |
| `SESSION_TTL_SECONDS` | `600` | Optional | How long a session stays active (default: 10 minutes). Increase if users need more time. |
| `ALIAS_TIMEOUT_MINUTES` | `5` | Optional | Minutes to wait for a verification code before auto-cancelling the alias and session. The session will still respond to polling with a cancellation message. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./shortcut_api.db` | Optional | SQLite is fine for personal use. See [Step 8](#step-8-optional-postgresql-instead-of-sqlite) for PostgreSQL. |
| `GMAIL_CREDENTIALS_FILE` | `credentials.json` | Leave | Path to your downloaded Google OAuth credentials file. |
| `GMAIL_TOKEN_FILE` | `token.json` | Leave | Path where the OAuth access token is saved after first login. |
| `GMAIL_MONITORED_LABEL` | `INBOX` | Optional | Gmail label to watch. `INBOX` monitors all incoming mail. |
| `GMAIL_STRATEGY` | `polling` | Optional | `polling` checks Gmail on a timer. `watch` uses push notifications (requires Pub/Sub setup). |
| `GMAIL_POLL_INTERVAL_SECONDS` | `10` | Optional | How often (seconds) to poll Gmail. 10 is a good default. |
| `ADMIN_TOKEN` | `change-me` | **Must Change** | Protects all `/api/v1/admin/*` endpoints. Generate a secure value — see below. |
| `RATE_LIMIT_REQUESTS` | `30` | Optional | Maximum requests per window from a single IP. |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Optional | The sliding window for rate limiting (in seconds). |
| `RETENTION_ENABLED` | `false` | Optional | If `true`, raw email bodies are stored in the database. |
| `RETENTION_REDACT_BODY` | `true` | Optional | When `RETENTION_ENABLED=true`, redact email body after code extraction. |
| `RETENTION_DAYS` | `7` | Optional | How many days to keep retained messages. |
| `RECYCLE_ENABLED` | `false` | Leave | Whether to allow alias reuse. Leave `false` to guarantee every alias is unique forever. |
| `DISCORD_WEBHOOK_URL` | *(empty)* | Optional | Discord webhook URL for notifications when a verification code is received. Leave blank to disable. |
| `HOST` | `0.0.0.0` | Leave | Binds to all network interfaces. Required when running behind a tunnel or reverse proxy. |
| `PORT` | `8000` | Optional | Port the API listens on. |
| `LOG_LEVEL` | `INFO` | Optional | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

### 2d. Generate a secure `ADMIN_TOKEN`

Never leave `ADMIN_TOKEN` at its default `change-me` value when the API is publicly accessible. Generate a cryptographically secure token:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and paste it as the value of `ADMIN_TOKEN` in your `.env` file.

**Example `.env` after editing (replace values with your own):**

```dotenv
ALIAS_DOMAIN=myaliases.com
ALIAS_LENGTH=12
ALIAS_CHARSET=abcdefghjkmnpqrstuvwxyz23456789
ALIAS_PREFIX=
ALIAS_SUFFIX=

SESSION_TTL_SECONDS=600
ALIAS_TIMEOUT_MINUTES=5

DATABASE_URL=sqlite+aiosqlite:///./shortcut_api.db

GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
GMAIL_MONITORED_LABEL=INBOX
GMAIL_STRATEGY=polling
GMAIL_POLL_INTERVAL_SECONDS=10

ADMIN_TOKEN=your-generated-secure-token-here
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60

RETENTION_ENABLED=false
RETENTION_REDACT_BODY=true
RETENTION_DAYS=7

RECYCLE_ENABLED=false

DISCORD_WEBHOOK_URL=

HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

---

## Step 3: Set Up Gmail OAuth

The API needs permission to read your Gmail inbox. You grant this permission once through a browser-based OAuth flow. The credentials are saved to `token.json` and reused on every subsequent startup.

### 3a. Create a Google Cloud Project

1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Sign in with the **Google account whose Gmail inbox you want to monitor**
3. Click the project dropdown at the top of the page → click **New Project**
4. Enter a project name (e.g. `shortcut-api`) → click **Create**
5. Wait for the project to be created, then make sure it is selected in the project dropdown

### 3b. Enable the Gmail API

1. In the left sidebar, go to **APIs & Services → Library**
2. Search for **Gmail API**
3. Click the **Gmail API** result → click **Enable**

### 3c. Configure the OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Select **External** → click **Create**
3. Fill in the required fields:
   - **App name:** `Shortcut API` (or any name)
   - **User support email:** your Gmail address
   - **Developer contact information:** your Gmail address
4. Click **Save and Continue** through the Scopes and Test Users screens (you can leave them as-is)
5. On the **Summary** screen, click **Back to Dashboard**

> **Note:** For personal use, leaving the app in "Testing" mode is fine. Your own account will always be able to authorize it.

### 3d. Create OAuth 2.0 Client Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth 2.0 Client ID**
3. For **Application type**, select **Desktop app**
4. Enter a name (e.g. `shortcut-api-desktop`) → click **Create**
5. A dialog shows your **Client ID** and **Client Secret** — click **Download JSON**
6. Rename the downloaded file to exactly **`credentials.json`**
7. Move `credentials.json` into the root of the `shortcut-api` project folder (the same folder as `.env`)

### 3e. Run the OAuth Setup Script

With your virtual environment active and `credentials.json` in the project root:

```powershell
python scripts/gmail_auth.py
```

1. Your **default web browser will open** with a Google consent page
2. Sign in with the same Google account you used for the Cloud project
3. You may see a warning: *"Google hasn't verified this app"* — click **Advanced → Go to shortcut-api (unsafe)**
4. Grant the requested permissions:
   - **Read all resources and their metadata** (`gmail.readonly`)
   - **Manage drafts and send emails** / **Modify Gmail** (`gmail.modify`)
5. Click **Allow**

After consent, `token.json` is created in the project root. The script will print a confirmation.

> **Keep `token.json` secret.** It grants read access to your Gmail inbox. Add it to `.gitignore` if it isn't already.

The API will automatically refresh the access token before it expires. You will not need to repeat this step unless you revoke access or delete `token.json`.

---

## Step 4: Set Up Your Catch-All Domain

The alias system requires a domain where **every possible address** (`anything@yourdomain.com`) is accepted and forwarded to your Gmail inbox. This is called a **catch-all** email route.

### What "catch-all" means

Normally, `alice@example.com` and `bob@example.com` are separate mailboxes. With catch-all enabled, `absolutely-anything@example.com` is accepted — even if there is no specific mailbox for it — and delivered to your inbox.

When the API generates the alias `xk9mn2p4@yourdomain.com`, the signup website sends a verification email to that address. Because of catch-all routing, the email arrives in your Gmail inbox. The API then reads it and extracts the code.

### Option A: Cloudflare Email Routing (recommended, free)

Cloudflare offers free catch-all email forwarding for any domain managed in Cloudflare DNS.

1. Log in to [dash.cloudflare.com](https://dash.cloudflare.com/)
2. Select your domain → go to **Email → Email Routing**
3. Enable Email Routing (Cloudflare will add the required MX records automatically)
4. Click **Catch-all address → Edit**
5. Set action to **Send to** → enter your Gmail address
6. Click **Save**

All mail to any address at your domain now forwards to your Gmail inbox.

### Option B: Namecheap

1. Log in to Namecheap → go to **Domain List → Manage** for your domain
2. Click the **Mail** tab
3. Select **Email Forwarding** as the mail service
4. Add a catch-all entry: set the alias to `*` and forward to your Gmail address
5. Save

### Option C: Other Registrars / Mail Providers

Most domain registrars and mail hosting providers (Gandi, Porkbun, Hover, Zoho Mail, etc.) offer catch-all forwarding. Look for "catch-all" or "wildcard" in your mail settings and forward it to your Gmail address.

> **Propagation time:** DNS changes can take 5–30 minutes to propagate. Test by sending an email to a random address at your domain and checking that it arrives in Gmail.

---

## Step 5: Run Locally

With the virtual environment active:

```powershell
uvicorn app.main:app --reload
```

You should see output similar to:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Verify the server is healthy:

```powershell
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok"}
```

> The `--reload` flag restarts the server automatically when you change source files. **Remove it in production.**

---

## Step 6: Expose to the Internet (Public Usage)

For your iOS Shortcut to reach the API, it must be accessible via a public HTTPS URL. Choose one of the options below.

---

### Option A: Cloudflare Tunnel (Recommended — Free, Secure)

Cloudflare Tunnel creates a secure outbound-only connection from your machine to Cloudflare's edge, giving you a stable HTTPS URL with no port-forwarding or firewall changes required.

**Install `cloudflared`:**

1. Download the latest Windows release from [https://github.com/cloudflare/cloudflared/releases/latest](https://github.com/cloudflare/cloudflared/releases/latest) (download `cloudflared-windows-amd64.exe`)
2. Rename it to `cloudflared.exe`
3. Move it to `C:\Windows\System32\` so it is available in any terminal (or add its folder to your `PATH`)

**Authenticate with Cloudflare:**

```powershell
cloudflared tunnel login
```

A browser window opens — log in to your Cloudflare account and authorise the domain you want to use.

**Create a named tunnel:**

```powershell
cloudflared tunnel create shortcut-api
```

This creates a tunnel and saves a credentials file (e.g. `~/.cloudflared/<tunnel-id>.json`).

**Create a DNS route** (replace `yourdomain.com` with your domain):

```powershell
cloudflared tunnel route dns shortcut-api shortcut-api.yourdomain.com
```

**Create a configuration file** at `~/.cloudflared/config.yml`:

```yaml
tunnel: shortcut-api
credentials-file: C:\Users\YourName\.cloudflared\<tunnel-id>.json

ingress:
  - hostname: shortcut-api.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

Replace `<tunnel-id>` with the actual UUID printed when you created the tunnel, and update the `credentials-file` path to match your username.

**Start the tunnel** (in a separate PowerShell window, with uvicorn already running):

```powershell
cloudflared tunnel run shortcut-api
```

Your API is now accessible at `https://shortcut-api.yourdomain.com`. Test it:

```powershell
curl https://shortcut-api.yourdomain.com/health
```

---

### Option B: ngrok (Quick Testing)

ngrok is a quick way to get a public URL for testing, but the URL changes every time you restart unless you have a paid plan.

1. Download from [https://ngrok.com/download](https://ngrok.com/download) and install
2. Sign up for a free account and get your auth token
3. Authenticate: `ngrok config add-authtoken YOUR_TOKEN`
4. With uvicorn running, open a new terminal and run:

```powershell
ngrok http 8000
```

ngrok prints a line like:

```
Forwarding    https://abc123.ngrok.io -> http://localhost:8000
```

Use the `https://abc123.ngrok.io` URL in your Shortcut. **This URL changes every restart** on the free tier.

---

### Option C: VPS with nginx + Let's Encrypt

If you have a Linux VPS (DigitalOcean, Linode, Hetzner, etc.):

1. Deploy the app to the VPS (clone the repo, set up venv, configure `.env`, run uvicorn as a systemd service on port 8000)
2. Install nginx and configure a reverse proxy:

```nginx
server {
    server_name shortcut-api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. Issue a TLS certificate with Certbot:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d shortcut-api.yourdomain.com
```

---

### Option D: Railway / Render / Fly.io (PaaS)

These platforms manage infrastructure for you. General steps:

1. Push your code to a GitHub repository (or connect directly)
2. Set all environment variables from `.env` in the platform's dashboard
3. Set `DATABASE_URL` to a hosted PostgreSQL connection string (each platform provides free PostgreSQL add-ons)
4. Mount `credentials.json` and `token.json` as secrets or volume mounts
5. Set the start command to: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
6. Deploy — the platform provides a public HTTPS URL

> **Note on credentials:** Most PaaS platforms do not support persistent local files. Store the JSON content of `credentials.json` and `token.json` as base64-encoded environment variables and modify `app/integrations/gmail/auth.py` to decode them at startup, or use a secrets manager.

---

## Step 7: Run as a Windows Background Service

To keep the API running after you close PowerShell or reboot, install it as a Windows service using **NSSM** (Non-Sucking Service Manager).

### 7a. Download NSSM

1. Go to [https://nssm.cc/download](https://nssm.cc/download)
2. Download the latest release
3. Extract the archive and copy `nssm.exe` (from the `win64` folder) to `C:\Windows\System32\`

### 7b. Find the full path to uvicorn

```powershell
where.exe uvicorn
```

This prints something like:
`C:\Users\YourName\shortcut-api\.venv\Scripts\uvicorn.exe`

Note this path — you need it in the next step.

### 7c. Install the service

Open PowerShell **as Administrator** (right-click → Run as administrator):

```powershell
nssm install ShortcutAPI
```

A GUI window opens. Fill in the **Application** tab:

| Field | Value |
|---|---|
| **Path** | `C:\Users\YourName\shortcut-api\.venv\Scripts\uvicorn.exe` |
| **Startup directory** | `C:\Users\YourName\shortcut-api` |
| **Arguments** | `app.main:app --host 0.0.0.0 --port 8000` |

Switch to the **Environment** tab and paste your environment variables from `.env` (one `VARIABLE=value` per line), or point nssm to your `.env` file using an environment variable loader.

Click **Install service**.

### 7d. Start the service

```powershell
nssm start ShortcutAPI
```

Verify it is running:

```powershell
nssm status ShortcutAPI
# Should print: SERVICE_RUNNING
curl http://localhost:8000/health
```

### 7e. Other useful NSSM commands

```powershell
nssm stop ShortcutAPI        # Stop the service
nssm restart ShortcutAPI     # Restart the service
nssm edit ShortcutAPI        # Open the configuration GUI to change settings
nssm remove ShortcutAPI confirm  # Uninstall the service
```

The service will now start automatically on every Windows boot.

---

## Step 8: (Optional) PostgreSQL Instead of SQLite

SQLite is fine for single-user personal use. For higher traffic or reliability, switch to PostgreSQL.

### 8a. Install PostgreSQL on Windows

1. Download the installer from [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)
2. Run the installer — accept all defaults
3. Set a password for the `postgres` superuser when prompted (remember it)
4. Let the installer add PostgreSQL to your `PATH`

### 8b. Create the database

Open **SQL Shell (psql)** from the Start menu (or PowerShell after adding PostgreSQL to PATH):

```powershell
psql -U postgres
```

Inside the psql shell:

```sql
CREATE DATABASE shortcut_api;
CREATE USER shortcut WITH PASSWORD 'your-db-password';
GRANT ALL PRIVILEGES ON DATABASE shortcut_api TO shortcut;
\q
```

### 8c. Update `.env`

Replace the `DATABASE_URL` line in your `.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://shortcut:your-db-password@localhost:5432/shortcut_api
```

### 8d. Run database migrations

```powershell
alembic upgrade head
```

This creates all required tables. Restart the API and it will use PostgreSQL.

---

## Security Checklist

Before making the API publicly accessible, verify every item below:

- [ ] **Change `ADMIN_TOKEN`** — never leave it as `change-me`. Generate a secure token: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] **Use HTTPS only** — ensure your public URL uses `https://`. Cloudflare Tunnel, ngrok, and most PaaS platforms enforce this automatically.
- [ ] **Do not commit secrets** — add `credentials.json`, `token.json`, and `.env` to `.gitignore`
- [ ] **Restrict admin endpoints** — your `ADMIN_TOKEN` should be a long random string, kept only on your device or in a secrets manager
- [ ] **Review rate limiting** — the defaults (`30 requests / 60 seconds per IP`) are reasonable; tighten if needed
- [ ] **Firewall** — if running on a VPS, allow only ports 80 and 443 inbound; block direct access to port 8000
- [ ] **Keep token.json secure** — it grants read access to your Gmail inbox; never share it or check it into version control
- [ ] **Enable HTTPS-only on your domain** — in Cloudflare, enable "Always Use HTTPS" for your domain
- [ ] **Rotate credentials periodically** — revoke and re-issue `ADMIN_TOKEN` periodically, especially if you suspect it may have been exposed

---

# Part 2 — iOS Shortcuts Integration

## Overview

The flow when using the Shortcut:

```
1. Shortcut calls POST /api/v1/sessions
   └─► API creates a session and returns a unique email alias

2. Shortcut shows the alias to the user
   └─► User copies the alias and pastes it into the sign-up form

3. Shortcut polls GET /api/v1/sessions/{id}/result every 5 seconds
   └─► API is monitoring Gmail in the background
   └─► When an email arrives and a code is extracted, the result endpoint returns it

4. Shortcut copies the code to clipboard and shows a notification
   └─► User pastes the code into the verification field
```

---

## Step 1: Create the Shortcut

Open the **Shortcuts** app on your iPhone or iPad. Tap **+** to create a new shortcut. Tap the name at the top and rename it to **"Get Verification Code"**.

Add each action below **in order**. Tap **Add Action**, search for the action name, and configure it as described.

---

### Action 1 — Store your API base URL

**Action:** `Text`

Tap the text field and enter your API's public HTTPS base URL:

```
https://shortcut-api.yourdomain.com
```

Tap the result bubble → tap **Add to Variable** → name the variable `Base URL`.

---

### Action 2 — Create a session (POST /api/v1/sessions)

**Action:** `Get Contents of URL`

Configure it as follows:

| Field | Value |
|---|---|
| **URL** | Tap the URL field → tap **Variables** → select `Base URL` → then type `/api/v1/sessions` |
| **Method** | `POST` |
| **Headers** | Tap **Add new field** → Key: `Content-Type`, Value: `application/json` |
| **Request Body** | Select `JSON` → tap **Add new field** → Key: `source_label`, Value: `Shortcut` |

Tap the result bubble → tap **Add to Variable** → name the variable `Session Response`.

---

### Action 3 — Extract session_id

**Action:** `Get Dictionary Value`

| Field | Value |
|---|---|
| **Key** | `session_id` |
| **Dictionary** | `Session Response` |

Tap the result bubble → **Add to Variable** → name it `Session ID`.

---

### Action 4 — Extract client_token

**Action:** `Get Dictionary Value`

| Field | Value |
|---|---|
| **Key** | `client_token` |
| **Dictionary** | `Session Response` |

Tap the result bubble → **Add to Variable** → name it `Client Token`.

---

### Action 5 — Extract alias

**Action:** `Get Dictionary Value`

| Field | Value |
|---|---|
| **Key** | `alias` |
| **Dictionary** | `Session Response` |

Tap the result bubble → **Add to Variable** → name it `Alias`.

---

### Action 6 — Show the alias to the user

**Action:** `Show Alert`

| Field | Value |
|---|---|
| **Title** | `Your Alias Email` |
| **Message** | `Use this email to sign up:` → (new line) → tap **Variables** → select `Alias` |
| **Show Cancel Button** | Toggle **off** (so the Shortcut continues automatically) |

The user now sees the alias and can copy it to use in the sign-up form before tapping OK.

---

### Action 7 — Polling loop (check for the code up to 30 times)

**Action:** `Repeat`

Set the repeat count to `30`.

**Inside the repeat loop, add these actions:**

#### 7a — Poll the result endpoint

**Action:** `Get Contents of URL`

| Field | Value |
|---|---|
| **URL** | `Base URL` + `/api/v1/sessions/` + `Session ID` + `/result` |
| **Method** | `GET` |
| **Headers** | Tap **Add new field** → Key: `X-Client-Token`, Value: `Client Token` (variable) |

Tap the result bubble → **Add to Variable** → name it `Poll Response`.

#### 7b — Extract status from response

**Action:** `Get Dictionary Value`

| Field | Value |
|---|---|
| **Key** | `status` |
| **Dictionary** | `Poll Response` |

Tap the result bubble → **Add to Variable** → name it `Poll Status`.

#### 7c — Check if code was extracted

**Action:** `If`

| Field | Value |
|---|---|
| **Input** | `Poll Status` |
| **Condition** | `is` |
| **Value** | `extracted` |

**Inside the "If" block, add:**

1. **Action:** `Get Dictionary Value`
   - Key: `code`, Dictionary: `Poll Response`
   - Result → **Add to Variable** → name it `Code`

2. **Action:** `Copy to Clipboard`
   - Input: `Code` (variable)

3. **Action:** `Show Notification`
   - Title: `Verification Code`
   - Body: tap **Variables** → select `Code`

4. **Action:** `Exit Shortcut`

Tap **End If**.

#### 7d — Check if session expired or cancelled

**Action:** `If`

| Field | Value |
|---|---|
| **Input** | `Poll Status` |
| **Condition** | `is` |
| **Value** | `expired` |

Also add an **Otherwise** condition checking for `cancelled` — tap **Add Otherwise** inside the If action, set it to: `Poll Status` `is` `cancelled`.

**Inside this "If / Otherwise" block, add:**

1. **Action:** `Show Alert`
   - Title: `Session Ended`
   - Message: `The session has expired or was cancelled. Please try again.`

2. **Action:** `Exit Shortcut`

Tap **End If**.

#### 7e — Wait before the next poll

**Action:** `Wait`

| Field | Value |
|---|---|
| **Seconds** | `5` |

---

### Action 8 — Handle timeout (after the loop)

This action runs only if the code was not found within 30 × 5 = 150 seconds.

**Action:** `Show Alert`

| Field | Value |
|---|---|
| **Title** | `Timed Out` |
| **Message** | `No verification code was received within 2.5 minutes. Please check your email manually.` |

---

## Step 2: Test the Shortcut

1. Make sure your API server is running and accessible at your public URL
2. Tap the **Play** button (▶) to run the Shortcut
3. An alert appears with an email alias, e.g. `xk9mn2p4@yourdomain.com`
4. Go to any website that sends a verification code by email
5. Enter the alias as your email address and request the code
6. The Shortcut polls automatically; within 5–15 seconds, a notification appears with the code
7. The code is automatically copied to your clipboard — paste it into the verification field

---

## Quick Reference: Shortcut Variables

| Variable Name | Source | Description |
|---|---|---|
| `Base URL` | Manual text action | Your API's public HTTPS URL |
| `Session Response` | `POST /api/v1/sessions` result | Full JSON response from session creation |
| `Session ID` | Extracted from `Session Response` | UUID identifying the session |
| `Client Token` | Extracted from `Session Response` | Bearer token for authenticating subsequent requests |
| `Alias` | Extracted from `Session Response` | The generated email address to use for sign-up |
| `Poll Response` | `GET .../result` result | Full JSON response from the polling request |
| `Poll Status` | Extracted from `Poll Response` | Current session status: `waiting`, `extracted`, `expired`, `cancelled` |
| `Code` | Extracted from `Poll Response` | The verification code (available when status is `extracted`) |

---

## Advanced: Add a Cancel Button

You can allow users to cancel the wait early by adding a cancel button.

After **Action 6** (Show Alert showing the alias), add:

**Action:** `Show Alert`

| Field | Value |
|---|---|
| **Title** | `Waiting for Code…` |
| **Message** | `The Shortcut is monitoring your inbox. Tap Cancel to stop waiting.` |
| **Show Cancel Button** | Toggle **on** |

Then add an **If** action checking whether the user tapped Cancel:

- If the previous alert result `is` `Cancelled`:

  1. **Action:** `Get Contents of URL`
     - URL: `Base URL` + `/api/v1/sessions/` + `Session ID` + `/cancel`
     - Method: `POST`
     - Headers: `X-Client-Token: Client Token`

  2. **Action:** `Show Alert` → "Session cancelled."

  3. **Action:** `Exit Shortcut`

> **Note:** iOS Shortcuts does not have a truly asynchronous cancel. This pattern shows a prompt before the polling loop begins. For a more responsive cancel, you can add a similar prompt at the start of each loop iteration at the cost of extra taps.

---

## Troubleshooting

### "No verification code was received"

| Possible Cause | Fix |
|---|---|
| Gmail is not polling | Check the API logs for `Gmail polling` messages. Ensure `GMAIL_STRATEGY=polling` and `token.json` is present and valid. |
| Alias domain not forwarding | Send a test email to a random address at your domain. Check Gmail receives it. If not, revisit [Step 4](#step-4-set-up-your-catch-all-domain). |
| No matching parsing rule | The regex rules may not match the email format. Check admin parsing rules via `GET /api/v1/admin/parsing-rules` or add a custom rule. |
| Session expired before email arrived | Increase `SESSION_TTL_SECONDS` in `.env` and increase the repeat count in the Shortcut. |

### "Session expired" shown immediately

The API returned `status: expired` before a code was found. The default TTL is 600 seconds. This means either:
- The email arrived after the session expired — increase `SESSION_TTL_SECONDS`
- The wrong `session_id` was used — check the Shortcut's variable extraction step

### Wrong URL / "Connection refused"

- Verify the `Base URL` variable in the Shortcut exactly matches your public API URL (including `https://`)
- Test the URL in a browser: `https://shortcut-api.yourdomain.com/health` should return `{"status": "ok"}`
- Make sure the tunnel (Cloudflare / ngrok) is running

### "Unauthorized" (401) from the API

- The `X-Client-Token` header is missing or incorrect
- Check that `Client Token` is being correctly extracted from the session creation response
- Each session has its own unique `client_token` — ensure you're using the one from the same session

### Gmail OAuth token expired or revoked

If you see Gmail authentication errors in the API logs:

```powershell
# With virtual environment active:
python scripts/gmail_auth.py
```

Follow the browser consent flow again. A new `token.json` will be created.

### API not receiving emails from the correct alias

- Confirm your domain's catch-all route is active and forwarding to the correct Gmail address
- Confirm `ALIAS_DOMAIN` in `.env` matches your actual domain exactly
- Confirm `GMAIL_MONITORED_LABEL` is set to `INBOX` (default)

---

# Part 3 — Verifying Everything Works

An end-to-end test you can run entirely from PowerShell to confirm all components are working.

### 1. Start the server

```powershell
# In a terminal with the virtual environment active:
uvicorn app.main:app --reload
```

### 2. Verify the health endpoint

```powershell
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

### 3. Create a test session

```powershell
curl -X POST http://localhost:8000/api/v1/sessions `
  -H "Content-Type: application/json" `
  -d '{"source_label": "test"}'
```

Expected response:

```json
{
  "session_id": "abc123def456",
  "client_token": "raw-token-shown-once",
  "alias": "xk9mn2p4@yourdomain.com",
  "expires_at": "2024-01-01T12:10:00Z",
  "status": "waiting"
}
```

Save the `session_id`, `client_token`, and `alias` values.

### 4. Send an email to the alias

Send an email to the `alias` address returned in step 3. You can use any service that sends a verification code (or send a test email manually).

If you are testing without a real service, send an email directly to the alias from any email account. The email body should contain a number that matches your parsing rules (e.g. a 6-digit code).

### 5. Check the session status

```powershell
curl http://localhost:8000/api/v1/sessions/abc123def456/status `
  -H "X-Client-Token: raw-token-shown-once"
```

### 6. Poll for the result

```powershell
curl http://localhost:8000/api/v1/sessions/abc123def456/result `
  -H "X-Client-Token: raw-token-shown-once"
```

When the code is found, the response will include:

```json
{
  "session_id": "abc123def456",
  "status": "extracted",
  "code": "847291",
  "matched_message_summary": {
    "gmail_message_id": "...",
    "from_address": "noreply@example.com",
    "subject": "Your verification code"
  },
  "completed_at": "2024-01-01T12:03:45Z"
}
```

If `status` is still `waiting`, the Gmail worker has not yet polled. Wait up to `GMAIL_POLL_INTERVAL_SECONDS` (default 10 seconds) and try again.

### 7. Confirm the code in the API logs

The server terminal should show log lines similar to:

```
INFO:  Gmail poll: 1 new message(s)
INFO:  Session abc123def456 → code extracted: 847291
```

---

> **See also:** [README.md](README.md) for architecture and configuration reference · [README_API.md](README_API.md) for the full endpoint reference
