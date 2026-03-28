"""
Gmail OAuth initial setup script.

Run once to obtain and store the OAuth token:

    python scripts/gmail_auth.py

Prerequisites:
1. Create a Google Cloud project at https://console.cloud.google.com/
2. Enable the Gmail API
3. Create OAuth 2.0 Desktop credentials
4. Download the credentials JSON and save as credentials.json (or set
   GMAIL_CREDENTIALS_FILE in .env)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.integrations.gmail.auth import get_credentials, SCOPES


def main() -> None:
    print("Gmail OAuth setup")
    print(f"Scopes: {SCOPES}")
    try:
        creds = get_credentials()
        print(f"Authentication successful!")
        print(f"Token stored. Expiry: {creds.expiry}")
    except FileNotFoundError as exc:
        print(f"\nError: {exc}")
        print(
            "\nSteps:\n"
            "1. Go to https://console.cloud.google.com/\n"
            "2. Create a project and enable the Gmail API\n"
            "3. Create OAuth 2.0 Desktop client credentials\n"
            "4. Download the JSON and save as credentials.json in your project root\n"
            "5. Re-run this script\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
