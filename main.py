import json
import sys
import time
from pathlib import Path

from stage1_ocean import get_lookalike_domains
from stage2a_enrich import enrich_companies
from stage2b_persons import find_decision_makers
from stage3_prospeo_enrich import enrich_persons
from stage4_emailgen import generate_emails_for_all
from stage5_brevo import send_emails
from checkpoint import show_checkpoint, save_checkpoint, load_checkpoint

# ── Terminal helpers ──────────────────────────────────────────────────────────

W = 62  # line width

def header(title: str):
    print(f"\n{'─' * W}")
    print(f"  {title}")
    print(f"{'─' * W}")

def stage_banner(num: str, title: str):
    print(f"\n{'═' * W}")
    print(f"  Stage {num}  │  {title}")
    print(f"{'═' * W}")

def ok(msg: str):      print(f"  ✓  {msg}")
def skip(msg: str):    print(f"  ↷  {msg}")
def warn(msg: str):    print(f"  ⚠  {msg}")
def done(num: str, msg: str, elapsed: float):
    print(f"\n  Stage {num} complete — {msg}  ({elapsed:.1f}s)")

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
    return len(load_json(path)) > 0


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline(seed_domain: str):
    t_total = time.time()
    header(f"OUTREACH PIPELINE  —  seed: {seed_domain}")
    checkpoint_state = load_checkpoint()

    # ── Stage 1: Ocean.io ────────────────────────────────────────────────────
    stage_banner("1", "Ocean.io — Lookalike company discovery")
    t = time.time()
    if data_exists("data/companies.json"):
        companies = load_json("data/companies.json")
        skip(f"Loaded {len(companies)} companies from cache  "
             f"(delete data/companies.json to refresh)")
    else:
        companies = get_lookalike_domains(seed_domain)
        if not companies:
            warn("No companies found — stopping pipeline.")
            sys.exit(1)
    done("1", f"{len(companies)} companies", time.time() - t)

    # ── Stage 2A: Prospeo search-company ────────────────────────────────────
    stage_banner("2A", "Prospeo — Company enrichment  (1 credit / 25 companies)")
    t = time.time()
    if data_exists("data/companies_enriched.json"):
        enriched = load_json("data/companies_enriched.json")
        skip(f"Loaded {len(enriched)} enriched companies from cache  "
             f"(delete data/companies_enriched.json to refresh)")
    else:
        enriched = enrich_companies(companies)
        if not enriched:
            warn("Enrichment failed — falling back to Ocean.io data")
            enriched = companies
        else:
            Path("data/companies_enriched.json").write_text(
                json.dumps(enriched, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            for c in enriched:
                checkpoint_state.setdefault(c.get("domain",""),{})["enriched"] = True
            save_checkpoint(checkpoint_state)
    done("2A", f"{len(enriched)} companies enriched", time.time() - t)

    # ── Stage 2B: Prospeo search-person ─────────────────────────────────────
    stage_banner("2B", "Prospeo — Decision maker discovery")
    t = time.time()
    if data_exists("data/prospects.json"):
        prospects = load_json("data/prospects.json")
        skip(f"Loaded {len(prospects)} prospects from cache  "
             f"(delete data/prospects.json to refresh)")
    else:
        prospects = find_decision_makers(enriched)
        if not prospects:
            warn("No decision makers found — stopping pipeline.")
            sys.exit(1)
        for p in prospects:
            checkpoint_state.setdefault(p.get("company_domain",""),{})["people_found"] = True
        save_checkpoint(checkpoint_state)
    done("2B", f"{len(prospects)} decision makers", time.time() - t)

    # ── Stage 3: Prospeo enrich-person ──────────────────────────────────────
    stage_banner("3", "Prospeo — Person enrichment  (email + title)")
    t = time.time()
    if data_exists("data/emails.json"):
        with_emails = load_json("data/emails.json")
        skip(f"Loaded {len(with_emails)} enriched persons from cache  "
             f"(delete data/emails.json to refresh)")
    else:
        with_emails = enrich_persons(prospects)
        if not with_emails:
            warn("No emails resolved — check Prospeo credits.")
            sys.exit(1)
        for p in with_emails:
            checkpoint_state.setdefault(p.get("company_domain",""),{})["email_found"] = True
        save_checkpoint(checkpoint_state)
    done("3", f"{len(with_emails)} emails resolved", time.time() - t)

    # ── Stage 4: Ollama ──────────────────────────────────────────────────────
    stage_banner("4", "Ollama — Personalised email generation  (local, free)")
    t = time.time()
    final_prospects = generate_emails_for_all(with_emails, enriched)
    if not final_prospects:
        warn("Email generation failed — stopping pipeline.")
        sys.exit(1)
    done("4", f"{len(final_prospects)} emails generated", time.time() - t)

    # ── Checkpoint ───────────────────────────────────────────────────────────
    stage_banner("✓", "Checkpoint — Review before sending")
    confirmed = show_checkpoint(final_prospects)

    if not confirmed:
        print(f"\n  Pipeline aborted — no emails sent.")
        return

    # ── Stage 5: Brevo ───────────────────────────────────────────────────────
    stage_banner("5", "Brevo — Sending emails")
    t = time.time()
    result = send_emails(final_prospects)
    done("5", f"{result['sent']} sent, {result['failed']} failed, "
         f"{result['skipped']} skipped", time.time() - t)

    # ── Final summary ────────────────────────────────────────────────────────
    total_time = time.time() - t_total
    print(f"\n{'═' * W}")
    print(f"  PIPELINE COMPLETE  —  {total_time:.1f}s total")
    print(f"{'═' * W}")
    print(f"  Companies found    : {len(companies)}")
    print(f"  Decision makers    : {len(prospects)}")
    print(f"  Emails resolved    : {len(with_emails)}")
    print(f"  Emails sent        : {result['sent']}")
    print(f"{'─' * W}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage  : python main.py <seed_domain>")
        print("Example: python main.py stripe.com\n")
        sys.exit(1)

    seed = sys.argv[1].strip().lower()
    seed = seed.replace("https://", "").replace("http://", "")
    seed = seed.replace("www.", "").rstrip("/")
    run_pipeline(seed)