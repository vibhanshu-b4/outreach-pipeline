import json
from pathlib import Path
from tabulate import tabulate


def load_json(path: str) -> list:
    """Safely load a JSON file, return empty list if missing or broken."""
    try:
        p = Path(path)
        if not p.exists():
            return []
        content = p.read_text(encoding="utf-8").strip()
        if not content:
            return []
        return json.loads(content)
    except Exception:
        return []


def show_checkpoint(final_prospects: list[dict]) -> bool:
    """
    Displays a full summary of the pipeline run before any emails are sent.

    final_prospects: list of dicts with keys:
        name, title, linkedin_url, company_domain, company_name,
        email, subject, body

    Returns True if user confirms, False if aborted.
    """
    # ── Pipeline stats ──────────────────────────────────────────────────────
    companies = load_json("data/companies.json")
    prospects = load_json("data/prospects.json")

    print("\n" + "=" * 60)
    print("  OUTREACH PIPELINE — CHECKPOINT")
    print("=" * 60)
    print(f"  Companies discovered   : {len(companies)}")
    print(f"  Decision makers found  : {len(prospects)}")
    print(f"  Emails resolved        : {len(final_prospects)}")
    print("=" * 60)

    if not final_prospects:
        print("\n  No contacts to show. Pipeline produced no results.")
        print("  Check logs for errors in earlier stages.")
        return False

    # ── Summary table ───────────────────────────────────────────────────────
    table_rows = []
    for i, p in enumerate(final_prospects, 1):
        subject = p.get("subject", "")
        # Truncate subject for table display
        subject_preview = subject[:40] + "..." if len(subject) > 40 else subject
        table_rows.append([
            i,
            p.get("name", ""),
            p.get("company_name", ""),
            p.get("email", ""),
            subject_preview,
        ])

    print("\n  CONTACTS READY FOR OUTREACH:\n")
    print(tabulate(
        table_rows,
        headers=["#", "Name", "Company", "Email", "Subject"],
        tablefmt="rounded_outline",
        maxcolwidths=[4, 20, 20, 30, 43],
    ))

    print(f"\n  Total: {len(final_prospects)} contact(s) ready")

    # ── Full email preview ──────────────────────────────────────────────────
    first = final_prospects[0]
    print("\n" + "-" * 60)
    print("  EMAIL PREVIEW (first contact)")
    print("-" * 60)
    print(f"  To      : {first.get('email', '')}")
    print(f"  Subject : {first.get('subject', '')}")
    print(f"  Body:\n")
    for line in first.get("body", "").split("\n"):
        print(f"    {line}")
    print("-" * 60)

    # ── Confirmation prompt ─────────────────────────────────────────────────
    print()
    try:
        answer = input("  Proceed with sending to all contacts? (y/n): ").strip().lower()
    except KeyboardInterrupt:
        print("\n\n  Aborted (keyboard interrupt).")
        return False

    if answer == "y":
        print("\n  Confirmed. Handing off to send stage...")
        return True
    else:
        print("\n  Aborted. No emails sent.")
        return False


def save_checkpoint(state: dict) -> None:
    """
    Save pipeline progress state to data/checkpoint.json
    Prevents duplicate work on re-runs.

    state format:
    {
      "razorpay.com": {
        "enriched": true,
        "people_found": true,
        "email_found": true
      }
    }
    """
    path = Path("data/checkpoint.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_checkpoint() -> dict:
    """Load saved checkpoint state. Returns empty dict if none exists."""
    try:
        path = Path("data/checkpoint.json")
        if not path.exists():
            return {}
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return {}
        return json.loads(content)
    except Exception:
        return {}


if __name__ == "__main__":
    # Standalone test with fake data
    test_prospects = [
        {
            "name":           "Akhil Joshi",
            "title":          "",
            "linkedin_url":   "https://www.linkedin.com/in/akhil-joshi-3055341b",
            "company_domain": "razorpay.com",
            "company_name":   "Razorpay",
            "email":          "akhil@razorpay.com",
            "subject":        "Razorpay Payment Solutions Automation",
            "body":           "Hi Akhil,\n\nAs a leading payment provider in India, "
                              "Razorpay is always looking for ways to improve.\n\n"
                              "We help B2B companies automate customer calls at scale.\n\n"
                              "Worth a 15-min call?\n\nBest,\nVibhanshu",
        },
        {
            "name":           "Neeraj Bagdia",
            "title":          "",
            "linkedin_url":   "https://www.linkedin.com/in/neerajbagdia",
            "company_domain": "cashfree.com",
            "company_name":   "Cashfree Payments",
            "email":          "neeraj@cashfree.com",
            "subject":        "Quick question for Cashfree Payments",
            "body":           "Hi Neeraj,\n\nI came across Cashfree Payments and "
                              "thought there might be a good fit.\n\n"
                              "We help B2B companies automate outreach at scale.\n\n"
                              "Worth a 15-min call?\n\nBest,\nVibhanshu",
        },
    ]

    result = show_checkpoint(test_prospects)
    print(f"\nCheckpoint returned: {result}")

