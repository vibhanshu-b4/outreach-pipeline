import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

PROSPEO_URL = "https://api.prospeo.io/search-company"
PAGE_SIZE   = 25  # Prospeo returns max 25 per page


def enrich_companies(companies: list[dict]) -> list[dict]:
    """
    Takes company list from Stage 1: {name, domain, industry, size, country}
    Uses Prospeo search-company with website filter to get enriched data.

    Credit cost: 1 credit per 25 companies (vs 1 per company with enrich-company)
    10 companies = 1 credit, 50 companies = 2 credits

    Adds to each company: description, city
    Saves to data/companies_enriched.json
    """
    load_dotenv()
    api_key = os.getenv("PROSPEO_API_KEY", "").strip()

    if not api_key:
        print("ERROR: PROSPEO_API_KEY missing from .env")
        return []

    headers = {
        "Content-Type": "application/json",
        "X-KEY":        api_key,
    }

    # Extract domains from company list
    domains = [c.get("domain", "").strip() for c in companies if c.get("domain")]

    if not domains:
        print("No domains to enrich")
        return []

    # Build a lookup from domain → original company data
    original_lookup = {c["domain"]: c for c in companies if c.get("domain")}

    enriched = []
    total_pages = (len(domains) + PAGE_SIZE - 1) // PAGE_SIZE

    for page_num in range(total_pages):
        # Send up to 25 domains per request
        batch = domains[page_num * PAGE_SIZE:(page_num + 1) * PAGE_SIZE]

        print(f"Fetching page {page_num + 1}/{total_pages} "
              f"({len(batch)} companies)...", end=" ")

        payload = {
            "page": 1,
            "filters": {
                "company": {
                    "websites": {
                        "include": batch
                    }
                }
            }
        }

        try:
            response = requests.post(
                PROSPEO_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            print(f"network error — {exc}, skipping batch")
            continue

        if response.status_code == 401:
            print("invalid API key — stopping")
            break
        if response.status_code == 429:
            print("rate limited — waiting 15s...")
            time.sleep(15)
            continue
        if response.status_code == 400:
            try:
                err = response.json()
            except Exception:
                err = {}
            code = err.get("error_code", "?")
            print(f"error {code} — skipping batch")
            continue
        if response.status_code != 200:
            print(f"status {response.status_code} — skipping batch")
            continue

        try:
            data = response.json()
        except ValueError:
            print("bad JSON — skipping batch")
            continue

        if data.get("error"):
            print(f"API error: {data.get('error_code')} — skipping batch")
            continue

        results = data.get("results", [])
        free    = data.get("free", False)
        print(f"{len(results)} returned {'(free/cached)' if free else ''}")

        for result in results:
            company = result.get("company", {})
            if not company:
                continue

            domain = (company.get("domain") or "").strip()
            if not domain:
                continue

            # Get original data as fallback for missing fields
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

        time.sleep(1.0)  # polite delay between pages

    if not enriched:
        print("No companies enriched")
        return []

    # Save to separate file — never overwrites companies.json
    out_path = Path("data/companies_enriched.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    print(f"\nStage 2A: {len(enriched)} companies enriched "
          f"→ saved to data/companies_enriched.json")
    return enriched


if __name__ == "__main__":
    # Test with 3 companies — costs 1 credit
    test_companies = [
        {"name": "Razorpay",          "domain": "razorpay.com",  "industry": "", "size": "", "country": ""},
        {"name": "Cashfree Payments", "domain": "cashfree.com",  "industry": "", "size": "", "country": ""},
        {"name": "Adyen",             "domain": "adyen.com",     "industry": "", "size": "", "country": ""},
    ]
    result = enrich_companies(test_companies)
    print(f"\nTotal: {len(result)}")
    if result:
        print("Sample:", json.dumps(result[0], indent=2))

        