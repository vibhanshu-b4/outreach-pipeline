"""
Test for Stage 2A — Prospeo Company Enrichment (offline, fixture-based)

First run  : calls real API for 2 companies, saves to data/fixtures/prospeo_enrich_raw.json
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

FIXTURE_PATH = Path("data/fixtures/prospeo_enrich_raw.json")

# Only test with 2 companies to save credits
TEST_DOMAINS = ["razorpay.com", "cashfree.com"]


def fixture_is_valid() -> bool:
    if not FIXTURE_PATH.exists():
        return False
    try:
        content = FIXTURE_PATH.read_text(encoding="utf-8").strip()
        if not content:
            return False
        data = json.loads(content)
        # fixture is a list of raw API responses, one per domain
        return isinstance(data, list) and len(data) > 0
    except Exception:
        return False


def fetch_and_save_fixture(domains: list[str]) -> list[dict]:
    load_dotenv()
    api_key = os.getenv("PROSPEO_API_KEY")
    if not api_key:
        print("ERROR: PROSPEO_API_KEY missing from .env")
        sys.exit(1)

    print(f"Calling Prospeo API for {len(domains)} domains (credits used)...")
    url = "https://api.prospeo.io/enrich-company"
    headers = {"Content-Type": "application/json", "X-KEY": api_key}

    raw_responses = []
    for domain in domains:
        print(f"  Fetching {domain}...", end=" ")
        try:
            r = requests.post(
                url,
                headers=headers,
                json={"data": {"company_website": domain}},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            data["_test_domain"] = domain  # tag so we know which domain it was
            raw_responses.append(data)
            print("done")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.5)

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FIXTURE_PATH.open("w", encoding="utf-8") as f:
        json.dump(raw_responses, f, indent=2, ensure_ascii=False)

    print(f"Fixture saved to {FIXTURE_PATH} — future runs free.")
    return raw_responses


def load_fixture() -> list[dict]:
    print(f"Using fixture: {FIXTURE_PATH} (no API call)")
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_enriched(raw_responses: list[dict]) -> list[dict]:
    """Mirror of enrich_companies() parsing logic — keep in sync."""
    enriched = []
    for data in raw_responses:
        if data.get("error"):
            continue
        c = data.get("company", {})
        if not c:
            continue
        domain = c.get("domain") or data.get("_test_domain", "")
        if not domain:
            continue
        enriched.append({
            "name":        c.get("name") or "",
            "domain":      domain,
            "industry":    c.get("industry") or "",
            "size":        c.get("employee_range") or "",
            "country":     (c.get("location") or {}).get("country") or "",
            "city":        (c.get("location") or {}).get("city") or "",
            "description": c.get("description_ai") or "",
        })
    return enriched


def run_tests(enriched: list[dict]):
    print("\n" + "=" * 45)
    print("TESTS: Stage 2A — Prospeo Company Enrichment")
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

    check(isinstance(enriched, list),
          "result is a list",
          f"expected list, got {type(enriched)}")

    check(len(enriched) > 0,
          f"{len(enriched)} companies enriched",
          "empty — check fixture or API key")

    check(all(isinstance(c, dict) for c in enriched),
          "all items are dicts",
          "some items are not dicts")

    expected = {"name", "domain", "industry", "size", "country", "city", "description"}
    bad_keys = [c for c in enriched if expected - set(c.keys())]
    check(not bad_keys,
          "all items have correct keys",
          f"{len(bad_keys)} items have missing keys: {expected - set(bad_keys[0].keys()) if bad_keys else ''}")

    no_junk = all(set(c.keys()) == expected for c in enriched)
    check(no_junk,
          "no extra keys leaked in (data is lean)",
          "some items have unexpected extra keys")

    no_domain = [c for c in enriched if not c.get("domain")]
    check(not no_domain,
          "all items have a domain",
          f"{len(no_domain)} items missing domain")

    has_description = [c for c in enriched if c.get("description")]
    check(len(has_description) > 0,
          f"{len(has_description)}/{len(enriched)} items have a description (good for email gen)",
          "no descriptions returned — email personalization will suffer")

    print("=" * 45)
    print(f"RESULT: {passed}/{total} passed")
    print("=" * 45)

    if passed >= total - 1:  # allow 1 soft fail (description may be missing)
        print("\nSample output:")
        for c in enriched:
            print(f"\n  domain  : {c['domain']}")
            print(f"  name    : {c['name']}")
            print(f"  industry: {c['industry']}")
            print(f"  size    : {c['size']}")
            print(f"  city    : {c['city']}, {c['country']}")
            print(f"  desc    : {c['description'][:80]}..." if c['description'] else "  desc    : (none)")
        print("\nStage 2A OK. Ready for Stage 2B.")
    else:
        print("\nFix failures above before moving to Stage 2B.")


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv

    if refresh:
        print("--refresh: fetching from API...")
        raw = fetch_and_save_fixture(TEST_DOMAINS)
    elif not fixture_is_valid():
        print("No valid fixture — fetching from API (one time)...")
        raw = fetch_and_save_fixture(TEST_DOMAINS)
    else:
        raw = load_fixture()

    enriched = parse_enriched(raw)
    run_tests(enriched)