import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


def enrich_companies(companies: list[dict]) -> list[dict]:
    """
    Takes list of dicts from Stage 1: {name, domain, industry, size, country}
    Calls Prospeo company enrichment for each domain.
    Returns enriched list with added: city, description
    Saves to data/companies.json (overwrites Stage 1 output with richer data)

    Why enrich if Stage 1 already has industry/size/country?
    Prospeo data is cleaner and adds city + description_ai for email context.
    """
    load_dotenv()
    api_key = os.getenv("PROSPEO_API_KEY")

    if not api_key:
        print("ERROR: PROSPEO_API_KEY missing from .env")
        return []

    url = "https://api.prospeo.io/enrich-company"
    headers = {
        "Content-Type": "application/json",
        "X-KEY": api_key,
    }

    enriched = []

    for i, company in enumerate(companies):
        domain = company.get("domain", "").strip()
        if not domain:
            continue

        print(f"[{i+1}/{len(companies)}] Enriching {domain}...", end=" ")

        try:
            response = requests.post(
                url,
                headers=headers,
                json={"data": {"company_website": domain}},
                timeout=30,
            )
        except requests.RequestException as exc:
            print(f"network error — {exc}, skipping")
            continue

        if response.status_code in (401, 403):
            print("Invalid API key — stopping")
            break
        if response.status_code == 429:
            print("rate limited — waiting 10s...")
            time.sleep(10)
            continue
        if response.status_code != 200:
            print(f"status {response.status_code} — skipping")
            continue

        try:
            data = response.json()
        except ValueError:
            print("bad JSON — skipping")
            continue

        if data.get("error"):
            print(f"API error — skipping")
            continue

        c = data.get("company", {})
        if not c:
            print("no company data — skipping")
            continue

        # Extract only what we need — lean output
        enriched.append({
            "name":        c.get("name") or company.get("name") or "",
            "domain":      c.get("domain") or domain,
            "industry":    c.get("industry") or company.get("industry") or "",
            "size":        c.get("employee_range") or company.get("size") or "",
            "country":     (c.get("location") or {}).get("country") or company.get("country") or "",
            "city":        (c.get("location") or {}).get("city") or "",
            "description": c.get("description_ai") or "",
        })
        print("done")

        # Small delay to avoid hammering the API
        time.sleep(0.5)

    if not enriched:
        print("No companies enriched")
        return []

    # Save — overwrites companies.json with richer version
    out_path = Path("data/companies.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    print(f"\nProspeo: {len(enriched)} companies enriched → saved to data/companies.json")
    return enriched


if __name__ == "__main__":
    # Quick standalone test with 2 companies
    test_input = [
        {"name": "Razorpay", "domain": "razorpay.com",
         "industry": "", "size": "", "country": "in"},
        {"name": "Cashfree", "domain": "cashfree.com",
         "industry": "", "size": "", "country": "in"},
    ]
    result = enrich_companies(test_input)
    print(f"\nTotal enriched: {len(result)}")
    if result:
        print("Sample:", json.dumps(result[0], indent=2))