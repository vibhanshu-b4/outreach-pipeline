import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Fields we actually need downstream — nothing else
# domain     → Stage 2B: Prospeo person search key
# name       → Stage 4: email personalization
# industry   → Stage 4: email personalization
# size       → Stage 4: email personalization
# country    → Stage 4: email personalization

def get_lookalike_domains(seed_domain: str) -> list[dict]:
    """
    Call Ocean.io lookalike API.
    Returns lean list of dicts: {name, domain, industry, size, country}
    Saves to data/companies.json
    """
    load_dotenv()
    api_key = os.getenv("OCEAN_API_KEY")

    if not api_key:
        print("ERROR: OCEAN_API_KEY is missing from .env")
        return []

    url = "https://api.ocean.io/v3/search/companies"
    headers = {"X-Api-Token": api_key}
    body = {
        "companiesFilters": {
            "lookalikeDomains": [seed_domain],
        },
    }

    # --- API call ---
    try:
        response = requests.post(url, headers=headers, json=body, timeout=30)
    except requests.RequestException as exc:
        print(f"Network error: {exc}")
        return []

    if response.status_code in (401, 403):
        print("ERROR: Invalid API key — check OCEAN_API_KEY in .env")
        return []
    if response.status_code == 429:
        print("ERROR: Rate limited — wait a minute and retry")
        return []
    if response.status_code != 200:
        print(f"ERROR: Status {response.status_code} — {response.text[:200]}")
        return []

    try:
        data = response.json()
    except ValueError as exc:
        print(f"ERROR: Could not parse JSON: {exc}")
        return []

    # --- Save raw response for debugging/fixtures ---
    raw_path = Path("data/fixtures/ocean_raw.json")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return _parse_and_save(data)


def _parse_and_save(data: dict) -> list[dict]:
    """
    Parse raw Ocean.io response.
    Response shape:
      data["companies"] → list of result objects
      result["company"] → the actual company object
      company["domain"], company["name"], company["linkedinIndustry"],
      company["companySize"], company["primaryCountry"]
    """
    # Ocean.io returns key "companies" (confirmed from real response)
    raw_list = []
    if isinstance(data, dict):
        raw_list = data.get("companies", data.get("results", []))
    if not isinstance(raw_list, list) or not raw_list:
        print("No results returned from Ocean.io")
        return []

    companies = []
    for item in raw_list:
        # each item has a nested "company" object
        company = item.get("company", {}) if isinstance(item, dict) else {}
        if not isinstance(company, dict):
            continue

        domain = company.get("domain", "").strip()
        if not domain:
            continue  # useless without a domain

        # Extract ONLY what downstream stages need
        companies.append({
            "name":     company.get("name") or "",
            "domain":   domain,
            "industry": company.get("linkedinIndustry") or "",
            "size":     company.get("companySize") or "",
            "country":  company.get("primaryCountry") or "",
        })

    if not companies:
        print("No valid companies extracted")
        return []

    # Save lean version to data/companies.json
    out_path = Path("data/companies.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)

    print(f"Ocean.io: {len(companies)} companies → saved to data/companies.json")
    return companies


if __name__ == "__main__":
    results = get_lookalike_domains("stripe.com")
    print(f"\nTotal: {len(results)} companies")
    if results:
        print("Sample:", json.dumps(results[0], indent=2))