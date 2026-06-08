import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

PROSPEO_URL     = "https://api.prospeo.io/enrich-person"
MAX_PER_COMPANY = 1  # 1 person per company — saves credits


def enrich_persons(prospects: list[dict]) -> list[dict]:
    """
    Takes prospect list from Stage 2B.
    Calls Prospeo enrich-person for each LinkedIn URL.
    Extracts email + current_job_title.

    Credit cost: 1 per email found.
    MAX_PER_COMPANY = 1 limits to 1 person per company.
    Saves progress after each successful enrich — no data lost on crash.

    Response structure:
      data["person"]["email"]["email"]       → email string
      data["person"]["email"]["status"]      → VERIFIED or PROBABLE
      data["person"]["email"]["revealed"]    → must be True
      data["person"]["current_job_title"]    → job title
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

    out_path = Path("data/emails.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Load any previously saved results (resume support)
    resolved = []
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            if isinstance(existing, list) and existing:
                resolved = existing
                print(f"Resuming — {len(resolved)} already resolved, continuing...")
        except Exception:
            pass

    # Track already resolved LinkedIn URLs to skip duplicates
    done_urls     = {p["linkedin_url"] for p in resolved if p.get("linkedin_url")}
    # Track how many people taken per company
    company_count = {}
    for p in resolved:
        d = p.get("company_domain", "")
        company_count[d] = company_count.get(d, 0) + 1

    total    = len(prospects)
    skipped  = 0

    for i, prospect in enumerate(prospects):
        linkedin_url = prospect.get("linkedin_url", "").strip()
        name         = prospect.get("name", "Unknown")
        domain       = prospect.get("company_domain", "")

        # Skip if already resolved
        if linkedin_url in done_urls:
            continue

        # Enforce max per company
        if company_count.get(domain, 0) >= MAX_PER_COMPANY:
            skipped += 1
            continue

        print(f"[{i+1}/{total}] Enriching {name}...", end=" ")

        payload = {
            "only_verified_email": False,
            "data": {"linkedin_url": linkedin_url}
        }

        try:
            response = requests.post(
                PROSPEO_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
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
        if response.status_code == 400:
            try:
                err = response.json()
            except Exception:
                err = {}
            code = err.get("error_code", "?")
            if code == "NO_MATCH":
                print("no match — skipping")
            elif code == "INSUFFICIENT_CREDITS":
                print("insufficient credits — stopping")
                break
            else:
                print(f"error {code} — skipping")
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
            print(f"API error: {data.get('error_code', '?')} — skipping")
            continue

        person = data.get("person")
        if not person:
            print("no person data — skipping")
            continue

        email_obj = person.get("email") or {}
        email     = email_obj.get("email", "").strip()
        revealed  = email_obj.get("revealed", False)
        status    = email_obj.get("status", "")

        if not email or not revealed:
            print("email not revealed — skipping")
            continue

        title = (person.get("current_job_title") or "").strip()
        print(f"found ({email}) [{status}]")

        resolved.append({
            **prospect,
            "email": email,
            "title": title,
        })

        # Update tracking
        done_urls.add(linkedin_url)
        company_count[domain] = company_count.get(domain, 0) + 1

        # Save after every successful enrich — no data lost on crash
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(resolved, f, indent=2, ensure_ascii=False)

        time.sleep(1.5)  # stay under 20/min rate limit

    if not resolved:
        print("No persons enriched")
        return []

    print(f"\nProspeo enrich: {len(resolved)} enriched, "
          f"{skipped} skipped (MAX_PER_COMPANY={MAX_PER_COMPANY})"
          f" → saved to data/emails.json")
    return resolved


if __name__ == "__main__":
    load_dotenv()
    test_prospects = [
        {
            "name":           "Akhil Joshi",
            "title":          "",
            "linkedin_url":   "https://www.linkedin.com/in/akhil-joshi-3055341b",
            "company_domain": "razorpay.com",
            "company_name":   "Razorpay",
        },
    ]
    result = enrich_persons(test_prospects)
    print(f"\nTotal: {len(result)}")
    if result:
        print("Sample:", json.dumps(result[0], indent=2))