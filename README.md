# Outreach Automation Pipeline

An end-to-end outreach automation system that discovers similar companies, identifies decision makers, enriches contact information, generates personalized outreach emails, and sends them through Brevo.

The entire workflow runs from a single command:

```bash
python main.py stripe.com
```

---

# Architecture

```text
Input Company Domain
          │
          ▼
Stage 1: Similar Company Discovery
          │
          ▼
Stage 2A: Company Enrichment
          │
          ▼
Stage 2B: Decision Maker Discovery
          │
          ▼
Stage 3: Person Enrichment
          │
          ▼
Stage 4: Email Generation
          │
          ▼
Checkpoint Review
          │
          ▼
Stage 5: Email Sending
```

---

# Tech Stack

* Python
* Ocean.io API
* Prospeo API
* Ollama (Llama 3.2)
* Brevo API
* Cloudflare Email Routing
* Namecheap Domain + Mailbox

---

# Project Structure

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
├── data/
│   ├── companies.json
│   ├── companies_enriched.json
│   ├── prospects.json
│   ├── emails.json
│   └── fixtures/
│
├── requirements.txt
├── .env
└── README.md
```

---

# Stage 1 — Similar Company Discovery

## Goal

Find companies similar to the input company.

Example:

```bash
python main.py stripe.com
```

Input:

```text
stripe.com
```

Output:

```text
Adyen
Razorpay
Cashfree
Rapyd
...
```

## How It Works

The pipeline calls the Ocean.io Lookalike API.

Ocean returns companies that closely resemble the seed company based on:

* Industry
* Company profile
* Business model
* Market positioning

Results are stored in:

```text
data/companies.json
```

Caching is used to avoid consuming API credits repeatedly.

---

# Stage 2A — Company Enrichment

## Goal

Gather additional context about discovered companies.

For each company, Prospeo enriches:

* Industry
* Company description
* Size
* Location
* Domain

Example:

```json
{
  "name": "Razorpay",
  "industry": "Software Development",
  "country": "India",
  "description": "Payment solution provider..."
}
```

Results are stored in:

```text
data/companies_enriched.json
```

This information is later used for email personalization.

---

# Stage 2B — Decision Maker Discovery

## Goal

Identify relevant contacts inside target companies.

The pipeline searches for decision makers such as:

* Founder
* CEO
* VP
* Director
* Head of Sales
* Head of Growth
* Partnerships Lead

Example:

```json
{
  "name": "Akhil Joshi",
  "title": "Associate Director",
  "company_name": "Razorpay"
}
```

Results are stored in:

```text
data/prospects.json
```

---

# Stage 3 — Person Enrichment

## Goal

Resolve contact information for discovered prospects.

Prospeo Person Enrichment is used to enrich contacts with:

* Professional email
* Updated title
* Company association

Example:

```json
{
  "name": "Akhil Joshi",
  "email": "akhil.joshi@razorpay.com",
  "title": "Associate Director"
}
```

Results are stored in:

```text
data/emails.json
```

---

# Stage 4 — Personalized Email Generation

## Goal

Generate personalized outreach emails.

## Hybrid Approach

The system uses:

### Step 1 — Deterministic Template

A structured outreach template is created using:

* Prospect name
* Company name
* Job title
* Industry
* Company description

This guarantees consistency and prevents hallucinations.

### Step 2 — Ollama Enhancement

The template is then passed to:

```text
Llama 3.2 via Ollama
```

Ollama rewrites the message to sound:

* More natural
* More conversational
* More human

while preserving all factual information.

If Ollama is unavailable, the system automatically falls back to the original template.

Example:

```text
Hi Akhil,

I came across Razorpay and noticed your work as Associate Director.

Given Razorpay's focus in Software Development, I think there's a strong fit with what we're building at Vocallabs.

We build AI voice agents that help businesses automate customer support, lead qualification, and outbound engagement through natural, human-like conversations.

Worth a 15-minute conversation?

Best,
Vibhanshu
```

---

# Checkpoint Stage

## Goal

Prevent accidental outreach.

Before sending any email, the system pauses and displays:

* Recipient list
* Company names
* Email addresses
* Subject lines
* Email preview

Example:

```text
Proceed with sending 4 emails? (y/n)
```

No emails are sent without explicit user approval.

---

# Stage 5 — Email Delivery

## Goal

Send personalized emails through Brevo.

The pipeline:

1. Converts plain text emails to HTML.
2. Sends emails using Brevo Transactional Email API.
3. Tracks responses.
4. Displays delivery status.

Example:

```text
Sent ✓
Message ID: <brevo-id>
```

---

# Safety Features

## Test Recipient Override

For demonstrations and testing:

```env
TEST_RECIPIENT=your-email@gmail.com
```

All emails are redirected to a safe inbox.

Real executive emails are never contacted during development.

---

## Dry Run Mode

The pipeline supports dry-run execution.

```python
send_emails(prospects, dry_run=True)
```

This displays the emails without sending them.

---

## Checkpoint Confirmation

Every outreach batch requires manual approval before delivery.

---

# Environment Variables

```env
OCEAN_API_KEY=

PROSPEO_API_KEY=

BREVO_API_KEY=

SENDER_NAME=Vibhanshu
SENDER_EMAIL=contact@vibhanshu.online

TEST_RECIPIENT=your-email@gmail.com
```

---

# Running the Project

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python main.py stripe.com
```

---

# Caching

API results are cached to reduce:

* API costs
* Duplicate requests
* Processing time

Cached files:

```text
data/companies.json
data/companies_enriched.json
data/prospects.json
data/emails.json
```

Delete a cache file to force a fresh API request.

---

# Design Decisions

### Why Templates + Ollama?

Using a deterministic template guarantees:

* Consistency
* Personalization
* No fabricated claims

Ollama is used only to improve wording and readability.

### Why a Checkpoint?

Sending emails automatically to real decision makers can be risky.

The checkpoint ensures:

* Human review
* Safe testing
* Better outreach quality

### Why Test Recipient Override?

The project is demonstrated using real prospect data.

Redirecting all emails to a test inbox prevents accidental outreach during development and demos.

---

# Future Improvements

* Multi-threaded enrichment
* CRM integrations
* Email open tracking
* Follow-up sequence generation
* Analytics dashboard
* Reply classification
* A/B testing of outreach messages

---

# Author

Vibhanshu Bhardwaj

Built as part of the Vocallabs / Subspace SDE Intern Assessment.
