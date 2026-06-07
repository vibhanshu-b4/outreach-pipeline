"""
Test for Stage 3 — Eazyreach Email Resolution (offline, fixture-based)

First run  : calls real API for 1 LinkedIn URL, saves to data/fixtures/eazyreach_raw.json
After that : loads fixture, zero API calls, zero credits

Force refresh: python test_stage3.py --refresh

NOTE: Only tests 1 profile to save credits.
"""
import json
import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import requests

FIXTURE_PATH = Path("data/fixtures/eazyreach_raw.json")

# Test with ONE profile only — Eazyreach charges per lookup
TEST_PROSPECT = {
    "name":           "Akhil Joshi",
    "title":          "",
    "linkedin_url":   "https://www.linkedin.com/in/akhil-joshi-3055341b",
    "company_domain": "razorpay.com",
    "company_name":   "Razorpay",
}


def fixture_is_valid() -> bool:
    if not FIXTURE_PATH.exists():
        return False
    try:
        content = FIXTURE_PATH.read_text(encoding="utf-8").strip()
        if not content:
            return False
        data = json.loads(content)
        # fixture is a single raw API response dict
        return isinstance(data, dict) and "status" in data
    except Exception:
        return False


def fetch_and_save_fixture(prospect: dict) -> dict:
    load_dotenv()
    auth_token = os.getenv("EAZYREACH_API_KEY")
    if not auth_token:
        print("ERROR: EAZYREACH_API_KEY missing from .env")
        sys.exit(1)

    print(f"Calling Eazyreach for 1 profile (credits used)...")
    print(f"  Profile: {prospect['linkedin_url']}")

    url     = "https://api.superflow.run/b2b/linkedin-emails"
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {auth_token}",
    }

    try:
        r = requests.post(
            url,
            headers=headers,
            json={"linkedinUrl": prospect["linkedin_url"]},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FIXTURE_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Fixture saved to {FIXTURE_PATH} — future runs free.")
    return data


def load_fixture() -> dict:
    print(f"Using fixture: {FIXTURE_PATH} (no API call)")
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_email(data: dict) -> str | None:
    """Mirror of resolve_emails() picking logic — keep in sync."""
    if data.get("status") != "success":
        return None
    emails = data.get("emails", [])
    for priority in ["verified", "probable"]:
        for entry in emails:
            if entry.get("verification") == priority:
                return entry.get("email", "").strip() or None
    return None


def run_tests(data: dict, chosen_email: str | None):
    print("\n" + "=" * 45)
    print("TESTS: Stage 3 — Eazyreach Email Resolution")
    print("=" * 45)
    passed = 0
    total  = 0

    def check(condition, pass_msg, fail_msg):
        nonlocal passed, total
        total += 1
        if condition:
            print(f"  PASS  {pass_msg}")
            passed += 1
        else:
            print(f"  FAIL  {fail_msg}")

    check(isinstance(data, dict),
          "response is a dict",
          f"expected dict, got {type(data)}")

    check(data.get("status") == "success",
          "status is 'success'",
          f"status is '{data.get('status')}' — check auth token or LinkedIn URL")

    emails = data.get("emails", [])
    check(isinstance(emails, list),
          "emails field is a list",
          f"expected list, got {type(emails)}")

    check(len(emails) > 0,
          f"{len(emails)} email(s) returned",
          "no emails in response — profile may have no findable email")

    if emails:
        has_email_field = all("email" in e for e in emails)
        check(has_email_field,
              "all email objects have 'email' field",
              "some email objects missing 'email' field")

        has_verification = all("verification" in e for e in emails)
        check(has_verification,
              "all email objects have 'verification' field",
              "some email objects missing 'verification' field")

        valid_verifications = {"verified", "probable"}
        bad_v = [e for e in emails if e.get("verification") not in valid_verifications]
        check(not bad_v,
              f"all verification values are 'verified' or 'probable'",
              f"{len(bad_v)} emails have unexpected verification value")
    else:
        # Skip email field checks if no emails
        for _ in range(3):
            total += 1
            print(f"  SKIP  (no emails to check)")

    check(chosen_email is not None,
          f"best email selected: {chosen_email}",
          "could not select any email — check picking logic")

    print("=" * 45)
    print(f"RESULT: {passed}/{total} passed")
    print("=" * 45)

    if chosen_email:
        print(f"\nEmail resolved for {TEST_PROSPECT['name']}:")
        print(f"  email : {chosen_email}")
        print(f"  source: Eazyreach")
        print("\nAll verifications in response:")
        for e in data.get("emails", []):
            print(f"  {e.get('verification'):<10} {e.get('email')}")
        print("\nStage 3 OK. Ready for Stage 4 (email generation).")
    else:
        print("\nNo email found. Check the raw fixture for details.")
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv

    if refresh:
        print("--refresh: fetching from API...")
        raw = fetch_and_save_fixture(TEST_PROSPECT)
    elif not fixture_is_valid():
        print("No valid fixture — fetching from API (one time)...")
        raw = fetch_and_save_fixture(TEST_PROSPECT)
    else:
        raw = load_fixture()

    email = parse_email(raw)
    run_tests(raw, email)

    