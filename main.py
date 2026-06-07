import json
import sys
from pathlib import Path

from stage1_ocean import get_lookalike_domains
from stage2a_enrich import enrich_companies
from stage2b_persons import find_decision_makers
from stage3_eazyreach import resolve_emails
from stage4_emailgen import generate_emails_for_all
from checkpoint import show_checkpoint, save_checkpoint, load_checkpoint


def separator(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def load_json(path: str) -> list:
    try:
        p = Path(path)
        if not p.exists():
            return []
        content = p.read_text(encoding="utf-8").strip()
        if not content or content == "[]":
            return []
        return json.loads(content)
    except Exception:
        return []


def data_exists(path: str) -> bool:
    """Returns True if file exists and has at least one record."""
    data = load_json(path)
    return len(data) > 0


def run_pipeline(seed_domain: str):
    separator(f"OUTREACH PIPELINE — seed: {seed_domain}")

    checkpoint_state = load_checkpoint()

    # ── Stage 1: Ocean.io ────────────────────────────────────────────────────
    separator("Stage 1 — Ocean.io: Finding lookalike companies")

    if data_exists("data/companies.json"):
        companies = load_json("data/companies.json")
        print(f"Skipping — loaded {len(companies)} companies from data/companies.json")
        print("(Delete data/companies.json to force a fresh fetch)")
    else:
        companies = get_lookalike_domains(seed_domain)
        if not companies:
            print("Pipeline stopped: no companies found.")
            sys.exit(1)

    print(f"\nStage 1 complete: {len(companies)} companies.")

    # ── Stage 2A: Prospeo enrich ─────────────────────────────────────────────
    separator("Stage 2A — Prospeo: Company enrichment")

    if data_exists("data/companies_enriched.json"):
        enriched = load_json("data/companies_enriched.json")
        print(f"Skipping — loaded {len(enriched)} enriched companies from data/companies_enriched.json")
        print("(Delete data/companies_enriched.json to force fresh enrichment)")
    else:
        enriched = enrich_companies(companies)
        if not enriched:
            print("Pipeline stopped: enrichment failed.")
            sys.exit(1)
        # Save to a SEPARATE file so companies.json is never overwritten
        Path("data/companies_enriched.json").write_text(
            json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        for c in enriched:
            checkpoint_state.setdefault(c.get("domain", ""), {})["enriched"] = True
        save_checkpoint(checkpoint_state)

    print(f"\nStage 2A complete: {len(enriched)} companies enriched.")

    # ── Stage 2B: Prospeo people ─────────────────────────────────────────────
    separator("Stage 2B — Prospeo: Finding decision makers")

    if data_exists("data/prospects.json"):
        prospects = load_json("data/prospects.json")
        print(f"Skipping — loaded {len(prospects)} prospects from data/prospects.json")
        print("(Delete data/prospects.json to force a fresh search)")
    else:
        prospects = find_decision_makers(enriched)
        if not prospects:
            print("Pipeline stopped: no decision makers found.")
            sys.exit(1)
        for p in prospects:
            checkpoint_state.setdefault(p.get("company_domain", ""), {})["people_found"] = True
        save_checkpoint(checkpoint_state)

    print(f"\nStage 2B complete: {len(prospects)} prospects.")

    # ── Stage 3: Eazyreach emails ────────────────────────────────────────────
    separator("Stage 3 — Eazyreach: Resolving work emails")

    if data_exists("data/emails.json"):
        with_emails = load_json("data/emails.json")
        print(f"Skipping — loaded {len(with_emails)} emails from data/emails.json")
        print("(Delete data/emails.json to force fresh resolution)")
    else:
        with_emails = resolve_emails(prospects)
        if not with_emails:
            print("\nWARNING: No emails resolved.")
            print("Eazyreach balance may be zero — top up credits and retry.")
            sys.exit(1)
        for p in with_emails:
            checkpoint_state.setdefault(p.get("company_domain", ""), {})["email_found"] = True
        save_checkpoint(checkpoint_state)

    print(f"\nStage 3 complete: {len(with_emails)} emails resolved.")

    # ── Stage 4: Ollama email gen ────────────────────────────────────────────
    separator("Stage 4 — Ollama: Generating personalized emails")
    final_prospects = generate_emails_for_all(with_emails, enriched)

    if not final_prospects:
        print("Pipeline stopped: email generation failed.")
        sys.exit(1)

    print(f"\nStage 4 complete: {len(final_prospects)} emails generated.")

    # ── Stage 5: Checkpoint ──────────────────────────────────────────────────
    separator("Stage 5 — Checkpoint: Review before sending")
    confirmed = show_checkpoint(final_prospects)

    if confirmed:
        print("\n  Pipeline complete.")
        print("  (Brevo send stage not implemented — stopping here as planned.)")
    else:
        print("\n  Pipeline aborted. No emails sent.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <seed_domain>")
        print("Example: python main.py stripe.com")
        sys.exit(1)

    seed_domain = sys.argv[1].strip().lower()
    seed_domain = seed_domain.replace("https://", "").replace("http://", "")
    seed_domain = seed_domain.replace("www.", "").rstrip("/")

    run_pipeline(seed_domain)