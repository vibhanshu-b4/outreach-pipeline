import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Email preference order
VERIFICATION_PRIORITY = ["verified", "probable"]


def resolve_emails(prospects: list[dict]) -> list[dict]:
    """
    Takes prospect list from Stage 2B: {name, title, linkedin_url,
                                         company_domain, company_name}
    For each prospect, calls Eazyreach to get their work email.
    Returns only prospects where an email was found.
    Saves to data/emails.json

    NOTE: title will be empty — personalization uses company/industry instead.
    """
    load_dotenv()
    auth_token = os.getenv("EAZYREACH_API_KEY")

    if not auth_token:
        print("ERROR: EAZYREACH_API_KEY missing from .env")
        return []

    url     = "https://api.superflow.run/b2b/linkedin-emails"
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
                url,
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
            print("insufficient balance — stopping")
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
            print(f"non-success status: {data.get('status')} — skipping")
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
            print("no usable email found — skipping")
            continue

        print(f"found ({chosen_email})")

        # Merge email into prospect dict — keep all existing fields
        enriched = {**prospect, "email": chosen_email}
        resolved.append(enriched)

        time.sleep(0.5)  # polite delay

    if not resolved:
        print("No emails resolved across all prospects")
        return []

    # Save to data/emails.json
    out_path = Path("data/emails.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2, ensure_ascii=False)

    print(f"\nEazyreach: {len(resolved)}/{len(prospects)} emails resolved "
          f"→ saved to data/emails.json")
    return resolved


if __name__ == "__main__":
    # Standalone test with prospects from Stage 2B fixture
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

        