"""
Test for Stage 3 — Prospeo Person Enrichment (offline, fixture-based)

First run  : calls real API for 1 person, saves to data/fixtures/prospeo_person_raw.json
After that : loads fixture, zero API calls, zero credits

Force refresh: python test_stage3.py --refresh
Cost: 1 credit on first run only.
"""
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

FIXTURE_PATH = Path("data/fixtures/prospeo_person_raw.json")

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
        return isinstance(data, dict) and "person" in data
    except Exception:
        return False


def fetch_and_save_fixture(prospect: dict) -> dict:
    load_dotenv()
    api_key = os.getenv("PROSPEO_API_KEY", "").strip()
    if not api_key:
        print("ERROR: PROSPEO_API_KEY missing from .env")
        sys.exit(1)

    print(f"Calling Prospeo enrich-person (1 credit)...")
    headers = {"Content-Type": "application/json", "X-KEY": api_key}
    payload = {
        "only_verified_email": False,
        "data": {"linkedin_url": prospect["linkedin_url"]}
    }

    try:
        r = requests.post(
            "https://api.prospeo.io/enrich-person",
            headers=headers,
            json=payload,
            timeout=30,
        )
        data = r.json()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FIXTURE_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved to {FIXTURE_PATH} — future runs free.")
    return data


def load_fixture() -> dict:
    print(f"Using fixture: {FIXTURE_PATH} (no API call)")
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_person(data: dict, prospect: dict) -> dict | None:
    """Mirror of stage3_prospeo_enrich.py parsing — keep in sync."""
    if data.get("error"):
        return None
    person = data.get("person")
    if not person:
        return None

    email_obj = person.get("email") or {}
    email     = email_obj.get("email", "").strip()
    revealed  = email_obj.get("revealed", False)

    if not email or not revealed:
        return None

    title = (person.get("current_job_title") or "").strip()
    return {**prospect, "email": email, "title": title}


def run_tests(data: dict, enriched: dict | None):
    print("\n" + "=" * 45)
    print("TESTS: Stage 3 — Prospeo Person Enrichment")
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

    check(not data.get("error"),
          "no error in response",
          f"API error: {data.get('error_code', '?')}")

    check("person" in data,
          "response has 'person' key",
          "missing 'person' key in response")

    person = data.get("person") or {}
    email_obj = person.get("email") or {}

    check("email" in email_obj,
          "person.email object exists",
          "no email object in person")

    check(email_obj.get("revealed") == True,
          "email is revealed",
          "email not revealed — check Prospeo plan or credit settings")

    check(bool(email_obj.get("email")),
          f"email string present: {email_obj.get('email', '')}",
          "email string is empty")

    check(email_obj.get("status") in ("VERIFIED", "PROBABLE"),
          f"email status is valid: {email_obj.get('status')}",
          f"unexpected email status: {email_obj.get('status')}")

    check(bool(person.get("current_job_title")),
          f"title found: {person.get('current_job_title')}",
          "no current_job_title — email personalization will use company context only")

    check(enriched is not None,
          "parse_person() extracted data successfully",
          "parse_person() returned None — check field paths")

    if enriched:
        check("@" in enriched.get("email", ""),
              "email looks valid",
              f"email looks invalid: {enriched.get('email')}")

    print("=" * 45)
    print(f"RESULT: {passed}/{total} passed")
    print("=" * 45)

    if enriched:
        print(f"\nEnriched result:")
        print(f"  name   : {enriched['name']}")
        print(f"  email  : {enriched['email']}")
        print(f"  title  : {enriched['title']}")
        print(f"  company: {enriched['company_name']}")
        print("\nStage 3 OK. Ready for Stage 4.")
    else:
        print("\nNo email extracted. Check fixture for details:")
        print(json.dumps(data.get("person", {}).get("email", {}), indent=2))


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv

    if refresh:
        raw = fetch_and_save_fixture(TEST_PROSPECT)
    elif not fixture_is_valid():
        print("No valid fixture — fetching from API (1 credit)...")
        raw = fetch_and_save_fixture(TEST_PROSPECT)
    else:
        raw = load_fixture()

    enriched = parse_person(raw, TEST_PROSPECT)
    run_tests(raw, enriched)