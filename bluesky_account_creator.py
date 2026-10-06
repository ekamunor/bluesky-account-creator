#!/usr/bin/env python3
"""Bluesky account generation and management CLI."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from atproto import Client
from dotenv import load_dotenv

from avatar_manager import apply_free_avatar_to_account
from password_generator import generate_password


@dataclass
class AccountConfig:
    handle: str
    email: str
    password: str
    service: str = "https://bsky.social"
    invite_code: Optional[str] = None
    verification_code: Optional[str] = None


EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*$"
)


def load_env() -> None:
    load_dotenv(override=False)


def validate_email(email: str) -> None:
    if not EMAIL_RE.fullmatch(email):
        raise ValueError(f"Invalid email format: {email}")


def validate_handle(handle: str) -> None:
    if not handle or " " in handle:
        raise ValueError(f"Invalid handle: {handle!r}")
    if "." not in handle:
        raise ValueError(
            "Handle must look like a domain or handle identifier, e.g. myname.bsky.social"
        )


def build_account_config(
    handle: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    invite_code: Optional[str] = None,
    verification_code: Optional[str] = None,
    service: Optional[str] = None,
) -> AccountConfig:
    load_env()
    configured_handle = handle or os.getenv("BLUESKY_HANDLE")
    configured_email = email or os.getenv("BLUESKY_EMAIL")
    configured_password = password or os.getenv("BLUESKY_PASSWORD")
    configured_service = service or os.getenv("BLUESKY_SERVICE_URL", "https://bsky.social")
    configured_invite_code = invite_code if invite_code is not None else os.getenv("BLUESKY_INVITE_CODE")
    configured_verification_code = (
        verification_code if verification_code is not None else os.getenv("BLUESKY_VERIFICATION_CODE")
    )

    if not configured_handle:
        raise ValueError("A handle is required")
    if not configured_email:
        raise ValueError("An email is required")
    if not configured_password:
        raise ValueError("A password is required")

    config = AccountConfig(
        handle=configured_handle.strip(),
        email=configured_email.strip(),
        password=configured_password.strip(),
        service=configured_service.strip() or "https://bsky.social",
        invite_code=configured_invite_code.strip() if configured_invite_code else None,
        verification_code=configured_verification_code.strip() if configured_verification_code else None,
    )

    validate_email(config.email)
    validate_handle(config.handle)
    return config


def create_account(config: AccountConfig, retries: int = 4) -> Dict[str, Any]:
    payload = {
        "handle": config.handle,
        "email": config.email,
        "password": config.password,
    }

    if config.invite_code:
        payload["invite_code"] = config.invite_code
    if config.verification_code:
        payload["verification_code"] = config.verification_code

    attempt = 0
    while attempt < retries:
        try:
            client = Client()
            result = client.com.atproto.server.create_account(**payload)
            return {
                "status": "created",
                "handle": config.handle,
                "email": config.email,
                "password": config.password,
                "service": config.service,
                "result": result,
            }
        except Exception as exc:
            msg = str(exc).lower()
            if any(
                marker in msg
                for marker in [
                    "rate limit",
                    "timeout",
                    "temporarily",
                    "429",
                    "network",
                    "connection",
                    "service unavailable",
                    "503",
                ]
            ):
                attempt += 1
                wait = min(2 ** attempt, 30)
                print(f"Transient failure for {config.handle}: {exc}. Retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue

            if any(word in msg for word in ["verification", "email", "invite"]):
                raise RuntimeError(
                    "Account creation requires extra verification. Check the email flow or invite code."
                ) from exc

            raise

    raise RuntimeError(f"Account creation failed after {retries} attempts for {config.handle}")


def create_account_with_avatar(
    config: AccountConfig,
    avatar_style: str = "avataaars",
    display_name: str = "",
    description: str = "",
    retries: int = 4,
) -> Dict[str, Any]:
    created = create_account(config, retries=retries)
    try:
        avatar_result = apply_free_avatar_to_account(
            handle=config.handle,
            password=config.password,
            avatar_style=avatar_style,
            display_name=display_name,
            description=description,
            service_url=config.service,
        )
        created["avatar"] = avatar_result
    except Exception as exc:  # pragma: no cover
        created["avatar"] = {"status": "failed", "error": str(exc)}
    return created


def generate_account_rows(csv_path: str, output_path: str, count: int, password_length: int = 16) -> List[Dict[str, str]]:
    csv_path = Path(csv_path)
    output_path = Path(output_path)

    load_env()

    rows: List[Dict[str, str]] = []
    for i in range(count):
        unique = int(time.time() * 1000) + i
        handle = f"user{unique}.bsky.social"
        email = f"user{unique}@example.com"
        password = generate_password(length=password_length)
        rows.append(
            {
                "handle": handle,
                "email": email,
                "password": password,
                "invite_code": os.getenv("BLUESKY_INVITE_CODE", ""),
                "verification_code": os.getenv("BLUESKY_VERIFICATION_CODE", ""),
                "status": "pending",
            }
        )

    mode = "a" if csv_path.exists() else "w"
    fieldnames = ["handle", "email", "password", "invite_code", "verification_code", "status"]
    with csv_path.open(mode, newline="", encoding="utf-8") as handle_file:
        writer = csv.DictWriter(handle_file, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        for row in rows:
            writer.writerow(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out_file:
        json.dump(rows, out_file, indent=2)

    return rows


def create_accounts_from_csv(csv_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    results: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        expected = {"handle", "email", "password"}
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty")
        fieldnames = {name.strip().lower() for name in reader.fieldnames}
        missing = expected - fieldnames
        if missing:
            raise ValueError(f"CSV missing required columns: {sorted(missing)}")

        for row in reader:
            cleaned = {key.strip(): (value.strip() if isinstance(value, str) else value) for key, value in row.items()}
            if not cleaned.get("handle") or not cleaned.get("email") or not cleaned.get("password"):
                continue
            config = AccountConfig(
                handle=cleaned["handle"],
                email=cleaned["email"],
                password=cleaned["password"],
                service=os.getenv("BLUESKY_SERVICE_URL", "https://bsky.social"),
                invite_code=cleaned.get("invite_code") or os.getenv("BLUESKY_INVITE_CODE"),
                verification_code=cleaned.get("verification_code") or os.getenv("BLUESKY_VERIFICATION_CODE"),
            )
            try:
                result = create_account(config)
                results.append(result)
            except Exception as exc:
                results.append(
                    {
                        "status": "failed",
                        "handle": config.handle,
                        "email": config.email,
                        "password": config.password,
                        "error": str(exc),
                    }
                )
    return results


def export_account_storage(accounts: List[Dict[str, Any]], output_path: str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        json.dump(accounts, file, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and store Bluesky accounts")
    parser.add_argument("--csv", help="CSV file with handle,email,password[,invite_code,verification_code]")
    parser.add_argument("--generate", type=int, help="Generate N random accounts and save them to a CSV")
    parser.add_argument("--output", help="Output JSON or CSV destination")
    parser.add_argument("--password-length", type=int, default=16, help="Password length for generated accounts")
    parser.add_argument("--handle", help="Single handle")
    parser.add_argument("--email", help="Single email")
    parser.add_argument("--password", help="Single password")
    parser.add_argument("--invite-code", help="Invite code")
    parser.add_argument("--verification-code", help="Verification code")
    parser.add_argument("--avatar-style", default="avataaars", help="Free avatar style: avataaars, bottts, identicon, initials, lorelei, pixel-art, micah")
    parser.add_argument("--display-name", default="", help="Optional display name to set after account creation")
    parser.add_argument("--description", default="", help="Optional profile description to set after account creation")
    args = parser.parse_args()

    try:
        if args.csv:
            results = create_accounts_from_csv(args.csv)
            if args.output:
                export_account_storage(results, args.output)
            print(json.dumps(results, indent=2))
            return 0

        if args.generate is not None:
            if not args.output:
                raise ValueError("--output is required when using --generate")
            generated_rows = generate_account_rows(
                csv_path=args.output.replace(".json", ".csv"),
                output_path=args.output,
                count=args.generate,
                password_length=args.password_length,
            )
            print(json.dumps(generated_rows, indent=2))
            return 0

        config = build_account_config(
            handle=args.handle,
            email=args.email,
            password=args.password,
            invite_code=args.invite_code,
            verification_code=args.verification_code,
        )
        if args.avatar_style:
            result = create_account_with_avatar(
                config,
                avatar_style=args.avatar_style,
                display_name=args.display_name,
                description=args.description,
            )
        else:
            result = create_account(config)
        if args.output:
            export_account_storage([result], args.output)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
