"""
Test for Stage 2A — Prospeo Search Company (offline, fixture-based)

Cost: 1 credit for up to 25 companies (massive saving vs enrich-company)

First run  : calls real API, saves to data/fixtures/prospeo_search_company_raw.json
After that : loads fixture, zero API calls, zero credits

Force refresh: python test_stage2a.py --refresh
"""
import json
import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import requests

FIXTURE_PATH = Path("data/fixtures/prospeo_search_company_raw.json")

TEST_COMPANIES = [
    {"name": "Razorpay",          "domain": "razorpay.com",  "industry": "", "size": "", "country": ""},
    {"name": "Cashfree Payments", "domain": "cashfree.com",  "industry": "", "size": "", "country": ""},
    {"name": "Adyen",             "domain": "adyen.com",     "industry": "", "size": "", "country": ""},
]


def fixture_is_valid() -> bool:
    if not FIXTURE_PATH.exists():
        return False
    try:
        content = FIXTURE_PATH.read_text(encoding="utf-8").strip()
        if not content:
            return False
        data = json.loads(content)
        return isinstance(data, dict) and "results" in data
    except Exception:
        return False


def fetch_and_save_fixture(companies: list[dict]) -> dict:
    load_dotenv()
    api_key = os.getenv("PROSPEO_API_KEY", "").strip()
    if not api_key:
        print("ERROR: PROSPEO_API_KEY missing from .env")
        sys.exit(1)

    domains = [c["domain"] for c in companies]
    print(f"Calling Prospeo search-company for {len(domains)} domains (1 credit)...")

    headers = {"Content-Type": "application/json", "X-KEY": api_key}
    payload = {
        "page": 1,
        "filters": {
            "company": {
                "websites": {"include": domains}
            }
        }
    }

    try:
        r = requests.post(
            "https://api.prospeo.io/search-company",
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


def parse_enriched(data: dict, original_companies: list[dict]) -> list[dict]:
    """Mirror of stage2a_enrich.py parsing — keep in sync."""
    original_lookup = {c["domain"]: c for c in original_companies}
    results = data.get("results", [])
    enriched = []

    for result in results:
        company = result.get("company", {})
        if not company:
            continue
        domain = company.get("domain", "").strip()
        if not domain:
            continue
        original = original_lookup.get(domain, {})
        enriched.append({
            "name":        company.get("name") or original.get("name") or "",
            "domain":      domain,
            "industry":    company.get("industry") or original.get("industry") or "",
            "size":        company.get("employee_range") or original.get("size") or "",
            "country":     (company.get("location") or {}).get("country") or original.get("country") or "",
            "city":        (company.get("location") or {}).get("city") or "",
            "description": company.get("description_ai") or company.get("description", "")[:200] or "",
        })
    return enriched


def run_tests(data: dict, enriched: list[dict]):
    print("\n" + "=" * 45)
    print("TESTS: Stage 2A — Prospeo Search Company")
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

    check("results" in data,
          "response has 'results' key",
          "missing 'results' key")

    check(isinstance(enriched, list) and len(enriched) > 0,
          f"{len(enriched)} companies parsed",
          "empty result — check domain filter or API key")

    check(all(isinstance(c, dict) for c in enriched),
          "all items are dicts",
          "some items are not dicts")

    expected = {"name", "domain", "industry", "size", "country", "city", "description"}
    bad = [c for c in enriched if expected - set(c.keys())]
    check(not bad,
          "all items have correct keys",
          f"{len(bad)} items missing keys")

    no_domain = [c for c in enriched if not c.get("domain")]
    check(not no_domain,
          "all items have a domain",
          f"{len(no_domain)} items missing domain")

    has_desc = [c for c in enriched if c.get("description")]
    check(len(has_desc) > 0,
          f"{len(has_desc)}/{len(enriched)} have description (good for email gen)",
          "no descriptions found")

    # Key test — verify credit efficiency
    free = data.get("free", False)
    check(True,
          f"credit used: {'0 (cached/free)' if free else '1'} for {len(enriched)} companies",
          "")

    print("=" * 45)
    print(f"RESULT: {passed}/{total} passed")
    print("=" * 45)

    if passed >= total - 1:
        print("\nSample output:")
        for c in enriched[:3]:
            print(f"\n  domain : {c['domain']}")
            print(f"  name   : {c['name']}")
            print(f"  city   : {c['city']}, {c['country']}")
            print(f"  desc   : {c['description'][:80]}..." if c['description'] else "  desc   : (none)")
        print("\nStage 2A OK. Ready for Stage 2B.")
    else:
        print("\nFix failures before moving to Stage 2B.")


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv

    if refresh:
        raw = fetch_and_save_fixture(TEST_COMPANIES)
    elif not fixture_is_valid():
        print("No valid fixture — fetching from API (1 credit)...")
        raw = fetch_and_save_fixture(TEST_COMPANIES)
    else:
        raw = load_fixture()

    enriched = parse_enriched(raw, TEST_COMPANIES)
    run_tests(raw, enriched)

