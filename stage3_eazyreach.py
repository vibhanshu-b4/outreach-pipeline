import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

VERIFICATION_PRIORITY = ["verified", "probable"]
BASE_URL = "https://api.superflow.run"


def get_auth_token() -> str | None:
    """
    Fetches a fresh auth token from Eazyreach using CLIENT_ID + CLIENT_SECRET.
    Falls back to EAZYREACH_API_KEY if already set in .env.
    """
    # If a static token is already in .env, use it directly
    static_token = os.getenv("EAZYREACH_API_KEY", "").strip()
    if static_token:
        return static_token

    # Otherwise generate one from credentials
    client_id     = os.getenv("EAZYREACH_CLIENT_ID", "").strip()
    client_secret = os.getenv("EAZYREACH_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        print("ERROR: Set either EAZYREACH_API_KEY or both "
              "EAZYREACH_CLIENT_ID + EAZYREACH_CLIENT_SECRET in .env")
        return None

    try:
        r = requests.post(
            f"{BASE_URL}/b2b/createAuthToken/",
            json={"clientId": client_id, "clientSecret": client_secret},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        token = (
            data.get("authToken") or
            data.get("auth_token") or
            data.get("token")
        )
        if not token:
            print(f"ERROR: No token in auth response: {data}")
            return None
        return token
    except Exception as e:
        print(f"ERROR: Could not get Eazyreach auth token — {e}")
        return None


def resolve_emails(prospects: list[dict]) -> list[dict]:
    """
    Takes prospect list from Stage 2B.
    For each prospect, calls Eazyreach to get their work email.
    Returns only prospects where an email was found.
    Saves to data/emails.json
    """
    load_dotenv()

    auth_token = get_auth_token()
    if not auth_token:
        return []

    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {auth_token}",
    }

    resolved = []

    for i, prospect in enumerate(prospects):
        linkedin_url = prospect.get("linkedin_url", "").strip()
        name         = prospect.get("name", "Unknown")

        if not linkedin_url:
            print(f"[{i+1}/{len(prospects)}] {name} — no LinkedIn URL, skipping")
            continue

        print(f"[{i+1}/{len(prospects)}] Resolving {name}...", end=" ")

        try:
            response = requests.post(
                f"{BASE_URL}/b2b/linkedin-emails",
                headers=headers,
                json={"linkedinUrl": linkedin_url},
                timeout=30,
            )
        except requests.RequestException as exc:
            print(f"network error — {exc}, skipping")
            continue

        if response.status_code == 401:
            print("invalid auth token — stopping")
            break
        if response.status_code == 402:
            print("insufficient balance — top up Eazyreach credits and retry")
            break
        if response.status_code == 404:
            print("LinkedIn profile not found — skipping")
            continue
        if response.status_code == 400:
            print(f"bad request — {response.text[:100]}, skipping")
            continue
        if response.status_code != 200:
            print(f"status {response.status_code} — skipping")
            continue

        try:
            data = response.json()
        except ValueError:
            print("bad JSON — skipping")
            continue

        if data.get("status") != "success":
            print(f"status: {data.get('status', '?')} — skipping")
            continue

        emails = data.get("emails", [])
        if not emails:
            print("no emails returned — skipping")
            continue

        # Pick best email: prefer verified, fall back to probable
        chosen_email = None
        for priority in VERIFICATION_PRIORITY:
            for entry in emails:
                if entry.get("verification") == priority:
                    chosen_email = entry.get("email", "").strip()
                    break
            if chosen_email:
                break

        if not chosen_email:
            print("no usable email — skipping")
            continue

        print(f"found ({chosen_email})")
        resolved.append({**prospect, "email": chosen_email})
        time.sleep(0.5)

    if not resolved:
        print("No emails resolved")
        return []

    out_path = Path("data/emails.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2, ensure_ascii=False)

    print(f"\nEazyreach: {len(resolved)}/{len(prospects)} resolved "
          f"→ saved to data/emails.json")
    return resolved


if __name__ == "__main__":
    load_dotenv()
    test_prospects = [
        {
            "name":           "Akhil Joshi",
            "title":          "",
            "linkedin_url":   "https://www.linkedin.com/in/akhil-joshi-3055341b",
            "company_domain": "razorpay.com",
            "company_name":   "Razorpay",
        },
    ]
    result = resolve_emails(test_prospects)
    print(f"\nTotal resolved: {len(result)}")
    if result:
        print("Sample:", json.dumps(result[0], indent=2))