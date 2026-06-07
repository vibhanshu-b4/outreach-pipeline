import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
BREVO_API_URL  = "https://api.brevo.com/v3/smtp/email"
SENDER_NAME    = "Vibhanshu"
SENDER_EMAIL   = "contact@vibhanshu.online"

# Override recipient — set to None to send to real emails
TEST_RECIPIENT = "anonymous2002@gmail.com"


def send_emails(final_prospects: list[dict], dry_run: bool = False) -> dict:
    """
    Sends personalized outreach emails via Brevo.

    final_prospects: list of dicts with keys:
        name, company_name, email, subject, body

    dry_run: if True, prints what would be sent without calling API.

    Returns summary dict: {sent, failed, skipped}
    """
    load_dotenv()
    api_key = os.getenv("BREVO_API_KEY", "").strip()

    if not api_key:
        print("ERROR: BREVO_API_KEY missing from .env")
        return {"sent": 0, "failed": 0, "skipped": len(final_prospects)}

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    sent    = 0
    failed  = 0
    skipped = 0

    for i, prospect in enumerate(final_prospects):
        name         = prospect.get("name", "there")
        company_name = prospect.get("company_name", "")
        real_email   = prospect.get("email", "").strip()
        subject      = prospect.get("subject", "").strip()
        body         = prospect.get("body", "").strip()

        # Decide recipient
        recipient_email = TEST_RECIPIENT if TEST_RECIPIENT else real_email

        if not recipient_email:
            print(f"[{i+1}/{len(final_prospects)}] {name} — no email address, skipping")
            skipped += 1
            continue

        if not subject or not body:
            print(f"[{i+1}/{len(final_prospects)}] {name} — missing subject or body, skipping")
            skipped += 1
            continue

        # Convert plain text body to simple HTML
        html_body = body.replace("\n", "<br>")
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; font-size: 15px; color: #222; max-width: 600px;">
            {html_body}
          </body>
        </html>
        """

        # Show what we're sending
        target_label = (
            f"{recipient_email} (test — real: {real_email})"
            if TEST_RECIPIENT else real_email
        )
        print(f"[{i+1}/{len(final_prospects)}] {name} @ {company_name} → {target_label}")
        print(f"  Subject: {subject}")

        if dry_run:
            print(f"  [DRY RUN] Would send — skipping actual API call")
            sent += 1
            continue

        payload = {
            "sender": {
                "name":  SENDER_NAME,
                "email": SENDER_EMAIL,
            },
            "to": [
                {"email": recipient_email, "name": name}
            ],
            "subject": subject,
            "htmlContent": html_body,
            # Tag for tracking in Brevo dashboard
            "tags": ["outreach-pipeline"],
        }

        try:
            response = requests.post(
                BREVO_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            print(f"  ERROR: Network error — {exc}")
            failed += 1
            continue

        if response.status_code == 401:
            print("  ERROR: Invalid Brevo API key — stopping")
            break
        if response.status_code == 429:
            print("  Rate limited — waiting 10s...")
            time.sleep(10)
            continue
        if response.status_code not in (200, 201):
            print(f"  ERROR: Status {response.status_code} — {response.text[:150]}")
            failed += 1
            continue

        print(f"  Sent ✓")
        sent += 1
        time.sleep(1)  # polite delay between sends

    return {"sent": sent, "failed": failed, "skipped": skipped}


if __name__ == "__main__":
    # Standalone test — sends one real email to TEST_RECIPIENT
    load_dotenv()

    test_prospect = {
        "name":         "Akhil Joshi",
        "company_name": "Razorpay",
        "email":        "akhil@razorpay.com",  # won't be used — TEST_RECIPIENT overrides
        "subject":      "Razorpay Payment Solutions Automation",
        "body": (
            "Hi Akhil,\n\n"
            "As a leading payment provider in India, Razorpay is always "
            "looking for ways to scale.\n\n"
            "We help B2B companies automate customer calls without hiring "
            "more agents.\n\n"
            "Worth a 15-min call?\n\n"
            "Best,\nVibhanshu"
        ),
    }

    print("Sending test email to:", TEST_RECIPIENT)
    result = send_emails([test_prospect])
    print(f"\nResult: {result}")
    