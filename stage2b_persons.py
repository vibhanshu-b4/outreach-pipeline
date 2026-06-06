import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Exact Prospeo ENUM values — must match precisely
TARGET_SENIORITY = ["C-Suite", "Founder/Owner", "Vice President", "Director"]

# Max people per company — keeps credit usage predictable
MAX_PER_COMPANY = 2


def find_decision_makers(enriched_companies: list[dict]) -> list[dict]:
    """
    Takes enriched company list from Stage 2A.
    For each domain, searches Prospeo for decision-maker contacts.
    Returns list of prospect dicts: name, title, linkedin_url,
                                    company_domain, company_name
    Saves to data/prospects.json

    NOTE: Prospeo search-person does not return emails or full titles.
    linkedin_url is what matters here — Stage 3 uses it to find emails.
    """
    load_dotenv()
    api_key = os.getenv("PROSPEO_API_KEY")

    if not api_key:
        print("ERROR: PROSPEO_API_KEY missing from .env")
        return []

    url = "https://api.prospeo.io/search-person"
    headers = {
        "Content-Type": "application/json",
        "X-KEY": api_key,
    }

    all_prospects = []

    for i, company in enumerate(enriched_companies):
        domain = company.get("domain", "").strip()
        name   = company.get("name", domain)

        if not domain:
            continue

        print(f"[{i+1}/{len(enriched_companies)}] Searching {domain}...", end=" ")

        payload = {
            "page": 1,
            "filters": {
                "company": {
                    "websites": {"include": [domain]}
                },
                "person_seniority": {
                    "include": TARGET_SENIORITY
                }
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.RequestException as exc:
            print(f"network error — {exc}, skipping")
            continue

        if response.status_code == 401:
            print("invalid API key — stopping")
            break
        if response.status_code == 429:
            print("rate limited — waiting 15s...")
            time.sleep(15)
            continue
        if response.status_code != 200:
            print(f"status {response.status_code}: {response.text[:150]} — skipping")
            continue

        try:
            data = response.json()
        except ValueError:
            print("bad JSON — skipping")
            continue

        if data.get("error"):
            code = data.get("error_code", "")
            print(f"API error {code} — skipping")
            continue

        results = data.get("results", [])
        if not results:
            print("0 results — skipping")
            continue

        found = 0
        for result in results:
            if found >= MAX_PER_COMPANY:
                break

            person = result.get("person", {})
            if not isinstance(person, dict):
                continue

            # linkedin_url is the critical field — Stage 3 needs it
            linkedin_url = (person.get("linkedin_url") or "").strip()
            if not linkedin_url:
                continue

            first     = (person.get("first_name") or "").strip()
            last      = (person.get("last_name") or "").strip()
            full_name = f"{first} {last}".strip() or "Unknown"

            # job_title may be None in search results — that's OK
            title = (person.get("job_title") or "").strip()

            # seniority is reliable even when job_title is None
            seniority = (person.get("seniority") or "").strip()

            all_prospects.append({
                "name":           full_name,
                "title":          title or seniority,  # fallback to seniority
                "linkedin_url":   linkedin_url,
                "company_domain": domain,
                "company_name":   name,
            })
            found += 1

        print(f"{found} prospect(s) found")
        time.sleep(0.5)

    if not all_prospects:
        print("No prospects found across all companies")
        return []

    out_path = Path("data/prospects.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(all_prospects, f, indent=2, ensure_ascii=False)

    print(f"\nProspeo: {len(all_prospects)} prospects → saved to data/prospects.json")
    return all_prospects


if __name__ == "__main__":
    test_companies = [
        {"name": "Razorpay",          "domain": "razorpay.com"},
        {"name": "Cashfree Payments", "domain": "cashfree.com"},
    ]
    result = find_decision_makers(test_companies)
    print(f"\nTotal: {len(result)}")
    if result:
        print("Sample:", json.dumps(result[0], indent=2))