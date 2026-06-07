import json
import requests


OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:latest"

YOUR_NAME    = "Vibhanshu"
YOUR_COMPANY = "Vocallabs"
YOUR_PITCH   = (
    "We build AI-powered voice automation tools that help B2B companies "
    "handle customer calls, follow-ups, and outreach at scale — "
    "without hiring more agents."
)


def generate_email(prospect: dict, company_data: dict | None = None) -> dict:
    """
    Generates a personalized cold outreach email using local Ollama.
    Returns dict: {subject, body}
    """
    name         = prospect.get("name", "there")
    first_name   = name.split()[0] if name else "there"
    company_name = prospect.get("company_name", "your company")

    industry    = ""
    description = ""
    city        = ""
    if company_data:
        industry    = company_data.get("industry", "")
        description = company_data.get("description", "")
        city        = company_data.get("city", "")

    context_parts = []
    if industry:
        context_parts.append(f"industry: {industry}")
    if city:
        context_parts.append(f"based in {city}")
    if description:
        first_sentence = description.split(".")[0].strip()
        if first_sentence:
            context_parts.append(f"about them: {first_sentence}")

    context = " | ".join(context_parts) if context_parts else "a growing tech company"

    prompt = f"""Write a cold B2B outreach email and return ONLY a JSON object.

SENDER: {YOUR_NAME}, {YOUR_COMPANY}
PITCH: {YOUR_PITCH}

RECIPIENT:
- First name: {first_name}
- Company: {company_name}
- Context: {context}

EMAIL RULES:
- Subject: max 8 words, mention their company or industry
- Body: 3 short paragraphs, max 80 words total
- Paragraph 1: one sentence referencing {company_name}
- Paragraph 2: one sentence about what {YOUR_COMPANY} does
- Paragraph 3: one clear call to action question
- Last line must be exactly: Best,\\n{YOUR_NAME}

OUTPUT FORMAT — return ONLY this JSON, nothing else:
{{"subject": "...", "body": "Hi {first_name},\\n\\n...\\n\\nBest,\\n{YOUR_NAME}"}}"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model":  OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "num_predict": 400,
                }
            },
            timeout=60,
        )
        response.raise_for_status()
        raw_text = response.json().get("response", "").strip()

        # Strip markdown fences if model wraps in ```json
        if "```" in raw_text:
            parts = raw_text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw_text = part
                    break

        raw_text = raw_text.strip()

        email_data = json.loads(raw_text)

        if "subject" not in email_data or "body" not in email_data:
            raise ValueError(f"Missing keys: {list(email_data.keys())}")

        body = email_data["body"].strip()

        # Enforce signature if model forgot it
        sign_off = f"Best,\n{YOUR_NAME}"
        if YOUR_NAME not in body:
            body = body.rstrip() + f"\n\n{sign_off}"

        return {
            "subject": email_data["subject"].strip(),
            "body":    body,
        }

    except requests.exceptions.ConnectionError:
        print(f"  WARNING: Ollama not running — using fallback template")
        return _fallback_template(first_name, company_name)

    except (json.JSONDecodeError, ValueError) as e:
        print(f"  WARNING: Could not parse Ollama response ({e}) — using fallback")
        return _fallback_template(first_name, company_name)

    except Exception as e:
        print(f"  WARNING: Unexpected error ({e}) — using fallback")
        return _fallback_template(first_name, company_name)


def _fallback_template(first_name: str, company_name: str) -> dict:
    return {
        "subject": f"Quick question for {company_name}",
        "body": (
            f"Hi {first_name},\n\n"
            f"I came across {company_name} and thought there might be "
            f"a good fit with what we're building at {YOUR_COMPANY}.\n\n"
            f"{YOUR_PITCH}\n\n"
            f"Worth a 15-min call to explore?\n\n"
            f"Best,\n{YOUR_NAME}"
        ),
    }


def generate_emails_for_all(
    prospects: list[dict],
    companies: list[dict] | None = None,
) -> list[dict]:
    """
    Runs generate_email() for every prospect.
    Merges company enrichment data by company_domain.
    Returns prospects with added 'subject' and 'body' keys.
    """
    company_lookup = {}
    if companies:
        for c in companies:
            domain = c.get("domain", "")
            if domain:
                company_lookup[domain] = c

    results = []
    for i, prospect in enumerate(prospects):
        name   = prospect.get("name", "Unknown")
        domain = prospect.get("company_domain", "")
        print(f"[{i+1}/{len(prospects)}] Generating email for {name}...", end=" ")

        company_data = company_lookup.get(domain)
        email        = generate_email(prospect, company_data)
        results.append({**prospect, **email})
        print("done")

    print(f"\nStage 4: {len(results)} emails generated")
    return results


if __name__ == "__main__":
    test_prospect = {
        "name":           "Akhil Joshi",
        "title":          "",
        "linkedin_url":   "https://www.linkedin.com/in/akhil-joshi-3055341b",
        "company_domain": "razorpay.com",
        "company_name":   "Razorpay",
        "email":          "akhil@razorpay.com",
    }
    test_company = {
        "name":        "Razorpay",
        "domain":      "razorpay.com",
        "industry":    "Software Development",
        "size":        "2001-5000",
        "country":     "India",
        "city":        "Bengaluru",
        "description": "Razorpay is a payment solution provider for online payments in India.",
    }

    result = generate_email(test_prospect, test_company)
    print(f"Subject: {result['subject']}")
    print(f"\nBody:\n{result['body']}")