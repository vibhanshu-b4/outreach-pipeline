"""
Test for Stage 1 — Ocean.io (offline, fixture-based)

First run  : calls real API once, saves to data/fixtures/ocean_raw.json
After that : loads fixture, zero API calls, zero credits

Force refresh: python test_stage1.py --refresh
"""
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

FIXTURE_PATH = Path("data/fixtures/ocean_raw.json")


def fixture_is_valid() -> bool:
    if not FIXTURE_PATH.exists():
        return False
    try:
        content = FIXTURE_PATH.read_text(encoding="utf-8").strip()
        if not content:
            return False
        data = json.loads(content)
        companies = data.get("companies", data.get("results", []))
        return isinstance(companies, list) and len(companies) > 0
    except Exception:
        return False


def fetch_and_save_fixture(seed_domain: str) -> dict:
    load_dotenv()
    api_key = os.getenv("OCEAN_API_KEY")
    if not api_key:
        print("ERROR: OCEAN_API_KEY missing from .env")
        sys.exit(1)

    print("Calling Ocean.io API (one-time, credits used)...")
    url = "https://api.ocean.io/v3/search/companies"
    headers = {"X-Api-Token": api_key}
    body = {"companiesFilters": {"lookalikeDomains": [seed_domain]}}

    try:
        r = requests.post(url, headers=headers, json=body, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    data = r.json()
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FIXTURE_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved to {FIXTURE_PATH} — all future runs free.")
    return data


def load_fixture() -> dict:
    print(f"Using fixture: {FIXTURE_PATH} (no API call)")
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_companies(data: dict) -> list[dict]:
    """Mirror of _parse_and_save in stage1_ocean.py — keep in sync."""
    raw_list = []
    if isinstance(data, dict):
        raw_list = data.get("companies", data.get("results", []))
    if not isinstance(raw_list, list):
        return []

    out = []
    for item in raw_list:
        company = item.get("company", {}) if isinstance(item, dict) else {}
        if not isinstance(company, dict):
            continue
        domain = company.get("domain", "").strip()
        if not domain:
            continue
        out.append({
            "name":     company.get("name") or "",
            "domain":   domain,
            "industry": company.get("linkedinIndustry") or "",
            "size":     company.get("companySize") or "",
            "country":  company.get("primaryCountry") or "",
        })
    return out


def run_tests(companies: list[dict]):
    print("\n" + "=" * 45)
    print("TESTS: Stage 1 — Ocean.io")
    print("=" * 45)
    passed = 0
    total = 0

    def check(condition, pass_msg, fail_msg):
        nonlocal passed, total
        total += 1
        if condition:
            print(f"  PASS  {pass_msg}")
            passed += 1
        else:
            print(f"  FAIL  {fail_msg}")

    check(isinstance(companies, list),
          "result is a list",
          f"expected list, got {type(companies)}")

    check(len(companies) > 0,
          f"{len(companies)} companies returned",
          "empty list — check fixture or API key")

    check(all(isinstance(c, dict) for c in companies),
          "every item is a dict",
          "some items are not dicts")

    no_domain = [c for c in companies if not c.get("domain")]
    check(not no_domain,
          "every item has a domain",
          f"{len(no_domain)} items missing domain")

    expected = {"name", "domain", "industry", "size", "country"}
    bad = [c for c in companies if expected - set(c.keys())]
    check(not bad,
          "all items have exactly {name, domain, industry, size, country}",
          f"{len(bad)} items have wrong/missing keys")

    no_junk = all(set(c.keys()) == expected for c in companies)
    check(no_junk,
          "no extra keys leaked in (data is lean)",
          "some items have extra keys — check _parse_and_save()")

    domains = [c["domain"] for c in companies]
    check(len(domains) == len(set(domains)),
          "no duplicate domains",
          "duplicate domains found")

    print("=" * 45)
    print(f"RESULT: {passed}/{total} passed")
    print("=" * 45)

    if passed == total:
        print("\nSample output (first 3):")
        for c in companies[:3]:
            print(f"  {c['domain']:<30} {c['name']:<20} {c['industry']}")
        print("\nStage 1 OK. Ready for Stage 2A.")
    else:
        print("\nFix failures above before moving to Stage 2A.")


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv

    if refresh:
        print("--refresh: fetching fresh data from API...")
        raw = fetch_and_save_fixture("stripe.com")
    elif not fixture_is_valid():
        print("No valid fixture — fetching from API (one time)...")
        raw = fetch_and_save_fixture("stripe.com")
    else:
        raw = load_fixture()

    companies = parse_companies(raw)
    run_tests(companies)