import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BREVO_API_URL  = "https://api.brevo.com/v3/smtp/email"
SENDER_NAME    = os.getenv("BREVO_SENDER_NAME",  "Vibhanshu")
SENDER_EMAIL   = os.getenv("BREVO_SENDER_EMAIL", "contact@vibhanshu.online")
TEST_RECIPIENT = os.getenv("BREVO_TEST_RECIPIENT", "")  # empty = send to real emails

FIXTURES_DIR   = Path("data/fixtures")


def _to_html(body: str) -> str:
    """Convert plain text body to clean HTML with proper paragraph spacing."""
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    html_paragraphs = "".join(
        f'<p style="margin: 0 0 16px 0; line-height: 1.6;">'
        f'{p.replace(chr(10), "<br>")}</p>'
        for p in paragraphs
    )
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; font-size: 15px;
                   color: #222222; max-width: 600px; margin: 0 auto; padding: 20px;">
        {html_paragraphs}
      </body>
    </html>
    """


def _save_response(index: int, payload: dict, response_data: dict) -> None:
    """Save Brevo API response to data/fixtures/brevo_response_{index}.json"""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "request":  payload,
        "response": response_data,
    }
    path = FIXTURES_DIR / f"brevo_response_{index}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


def send_emails(final_prospects: list[dict], dry_run: bool = False) -> dict:
    """
    Sends personalized outreach emails via Brevo.

    final_prospects : list of dicts with keys:
                      name, company_name, email, subject, body
    dry_run         : if True, prints what would be sent — no API calls

    Returns summary dict: {sent, failed, skipped}
    """
    api_key = os.getenv("BREVO_API_KEY", "").strip()

    if not api_key:
        print("ERROR: BREVO_API_KEY missing from .env")
        return {"sent": 0, "failed": 0, "skipped": len(final_prospects)}

    # ── DRY RUN banner ───────────────────────────────────────────────────────
    if dry_run:
        print("=" * 60)
        print("  ⚠  DRY RUN MODE — no emails will be sent")
        print("=" * 60)

    headers = {
        "Content-Type": "application/json",
        "api-key":      api_key,
    }

    sent    = 0
    failed  = 0
    skipped = 0
    total   = len(final_prospects)

    for i, prospect in enumerate(final_prospects, 1):
        name         = prospect.get("name", "there")
        company_name = prospect.get("company_name", "")
        real_email   = prospect.get("email", "").strip()
        subject      = prospect.get("subject", "").strip()
        body         = prospect.get("body", "").strip()

        # Decide actual recipient
        recipient_email = TEST_RECIPIENT if TEST_RECIPIENT else real_email

        # ── Console output ───────────────────────────────────────────────────
        print(f"\n[{i}/{total}] {name} @ {company_name}")
        print(f"  Real Recipient : {real_email}")
        if TEST_RECIPIENT:
            print(f"  Actual Target  : {recipient_email}  (test override)")
        else:
            print(f"  Actual Target  : {recipient_email}")
        print(f"  Subject        : {subject}")

        # ── Validation ───────────────────────────────────────────────────────
        if not recipient_email:
            print("  SKIP  no email address")
            skipped += 1
            continue

        if not subject or not body:
            print("  SKIP  missing subject or body")
            skipped += 1
            continue

        # ── Dry run ──────────────────────────────────────────────────────────
        if dry_run:
            print("  [DRY RUN] Would send — skipping API call")
            sent += 1
            continue

        # ── Build payload ────────────────────────────────────────────────────
        payload = {
            "sender":      {"name": SENDER_NAME, "email": SENDER_EMAIL},
            "to":          [{"email": recipient_email, "name": name}],
            "subject":     subject,
            "htmlContent": _to_html(body),
            "tags":        ["outreach-pipeline"],
        }

        # ── Send ─────────────────────────────────────────────────────────────
        try:
            response = requests.post(
                BREVO_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            print(f"  ERROR  network error — {exc}")
            failed += 1
            continue

        if response.status_code == 401:
            print("  ERROR  invalid Brevo API key — stopping")
            break
        if response.status_code == 429:
            print("  rate limited — waiting 10s...")
            time.sleep(10)
            continue
        if response.status_code not in (200, 201):
            print(f"  ERROR  status {response.status_code} — {response.text[:150]}")
            failed += 1
            continue

        # ── Success ──────────────────────────────────────────────────────────
        response_data = response.json()
        message_id    = response_data.get("messageId", "unknown")

        _save_response(i, payload, response_data)
        print(f"  Sent ✓  Message ID: {message_id}")
        sent += 1

        time.sleep(1)

    # ── Final summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  SEND SUMMARY")
    print("=" * 60)
    print(f"  Sent   : {sent}")
    print(f"  Failed : {failed}")
    print(f"  Skipped: {skipped}")
    print(f"  Total  : {total}")
    if dry_run:
        print("  Mode   : DRY RUN (nothing actually sent)")
    elif TEST_RECIPIENT:
        print(f"  Mode   : TEST (all sent to {TEST_RECIPIENT})")
    else:
        print("  Mode   : LIVE (sent to real recipients)")
    print("=" * 60)

    return {"sent": sent, "failed": failed, "skipped": skipped}


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv

    test_prospect = {
        "name":         "Akhil Joshi",
        "company_name": "Razorpay",
        "email":        "akhil.joshi@razorpay.com",
        "subject":      "Razorpay × Vocallabs — Quick Question",
        "body": (
            "Hi Akhil,\n\n"
            "I came across Razorpay and noticed your work as Associate Director there. "
            "Given Razorpay's focus in Software Development, I think there's a strong "
            "fit with what we're building at Vocallabs.\n\n"
            "We build AI-powered voice automation tools that help B2B companies handle "
            "customer calls, follow-ups, and outreach at scale without hiring more agents.\n\n"
            "Worth a 15-min call to explore?\n\n"
            "Best,\nVibhanshu"
        ),
    }

    result = send_emails([test_prospect], dry_run=dry_run)