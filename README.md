# Outreach Automation Pipeline

An end-to-end outreach automation system that:

1. Discovers companies similar to a target company.
2. Finds relevant decision makers.
3. Enriches contact information.
4. Generates personalized outreach emails using Ollama.
5. Sends emails through Brevo.

---

## Architecture

```text
Input Company
      ↓
Stage 1  → Ocean.io (Lookalike Companies)
      ↓
Stage 2A → Prospeo (Company Enrichment)
      ↓
Stage 2B → Prospeo (Decision Maker Discovery)
      ↓
Stage 3  → Prospeo (Person Enrichment)
      ↓
Stage 4  → Ollama (Email Generation)
      ↓
Checkpoint Review
      ↓
Stage 5  → Brevo (Email Delivery)
```

---

## Tech Stack

* Python
* Ocean.io API
* Prospeo API
* Ollama (Llama 3.2)
* Brevo API
* Cloudflare Email Routing
* Namecheap Domain

---

## Project Structure

```text
outreach_pipeline/
│
├── main.py
├── stage1_ocean.py
├── stage2_prospeo.py
├── stage3_prospeo_person.py
├── stage4_emailgen.py
├── stage5_brevo.py
├── checkpoint.py
│
├── test_stage1.py
├── test_stage2a.py
├── test_stage2b.py
├── test_stage3.py
├── test_stage4.py
├── test_stage5.py
│
├── data/
│   ├── fixtures/
│   └── *.json
│
├── requirements.txt
├── .env
└── README.md
```

---

## Pipeline Stages

### Stage 1 — Company Discovery

Uses Ocean.io to discover companies similar to the input company.

Output:

```text
Company Name
Domain
Industry
Size
Country
```

---

### Stage 2A — Company Enrichment

Uses Prospeo to enrich discovered companies.

Output:

```text
Industry
Description
Location
Company Metadata
```

---

### Stage 2B — Decision Maker Discovery

Uses Prospeo to find relevant contacts within enriched companies.

Output:

```text
Name
LinkedIn URL
Company
```

---

### Stage 3 — Person Enrichment

Uses Prospeo Person Enrichment to resolve:

```text
Professional Email
Job Title
Company Association
```

---

### Stage 4 — Personalized Email Generation

Uses a hybrid approach:

* Deterministic template
* Ollama (Llama 3.2) enhancement

Features:

* Personalized emails
* Company-aware messaging
* Template fallback if Ollama fails

---

### Checkpoint

Displays:

* Recipients
* Companies
* Emails
* Subject lines
* Email preview

Requires manual approval before sending.

---

### Stage 5 — Email Delivery

Uses Brevo Transactional Email API.

Features:

* HTML email generation
* Test-recipient override
* Dry-run mode
* Delivery logging

---

## Testing

Each stage was developed and validated independently using fixture-based tests.

Run:

```bash
python test_stage1.py
python test_stage2a.py
python test_stage2b.py
python test_stage3.py
python test_stage4.py
python test_stage5.py
```

Current Status:

```text
Stage 1  ✓ Passed
Stage 2A ✓ Passed
Stage 2B ✓ Passed
Stage 3  ✓ Passed
Stage 4  ✓ Passed
Stage 5  ✓ Passed
```

---

## Running

Install dependencies:

```bash
pip install -r requirements.txt
```

Make sure Ollama is running.
```bash
ollama serve
```

Run the full pipeline:

```bash
python main.py stripe.com
```

or

```bash
python main.py stripe
```

---

## Environment Variables

```env
OCEAN_API_KEY=

PROSPEO_API_KEY=

BREVO_API_KEY=

SENDER_NAME=
SENDER_EMAIL=

TEST_RECIPIENT=
```

---

## Safety Features

* Manual checkpoint before delivery
* Test-recipient override
* Dry-run support
* Cached API responses
* Stage-wise validation tests

---

## Future Improvements

* Multi-provider enrichment with automatic fallback.
* Follow-up email sequence generation.
* CRM integrations (HubSpot, Salesforce, Pipedrive).
* Analytics dashboard for opens, replies, and conversions.
* Prospect ranking based on relevance and seniority.
* Web-based dashboard for campaign management.
* A/B testing for outreach emails.
* Queue-based processing for improved scalability.
* Enhanced personalization using additional company and prospect context.

---

## Author

Vibhanshu Bhardwaj
