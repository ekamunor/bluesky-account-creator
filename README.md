# Bluesky Account Creator

This project allows registration of Bluesky accounts through the AT Protocol and supports a simple workflow for generating, storing, and exporting credentials.

## Features

- Create one account from environment variables or CLI arguments
- Bulk-create accounts from CSV
- Generate random secure passwords
- Save generated or created credentials to JSON
- Optional invite and verification codes

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Environment variables

```env
BLUESKY_HANDLE=myname.bsky.social
BLUESKY_EMAIL=you@example.com
BLUESKY_PASSWORD=StrongPassword123!
BLUESKY_SERVICE_URL=https://bsky.social
BLUESKY_INVITE_CODE=
BLUESKY_VERIFICATION_CODE=
```

## Run one account

```bash
python bluesky_account_creator.py --handle myname.bsky.social --email me@example.com --password StrongPassword123!
```

## Bulk from CSV

CSV format:

```csv
handle,email,password,invite_code,verification_code
alice.bsky.social,alice@example.com,Password123!,,
```

```bash
python bluesky_account_creator.py --csv accounts.csv --output results.json
```

## Generate accounts

```bash
python bluesky_account_creator.py --generate 10 --output generated_accounts.json
```

This will generate random accounts and save them to JSON and a CSV file next to the output.

## Notes

- Follow rate limits and anti-abuse protections.
- Some Bluesky services require invite codes or email verification.
- Store generated credentials securely and avoid logging them in plaintext unnecessarily.
