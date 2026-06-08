import json
import requests

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:latest"

YOUR_NAME = "Vibhanshu"

YOUR_COMPANY = "Vocallabs"

YOUR_PITCH = (
    "We build AI voice agents that automate customer support, "
    "sales conversations, lead qualification, and follow-ups at scale. "
    "Our platform helps businesses handle high volumes of customer interactions "
    "through natural, human-like voice conversations while reducing operational overhead."
)


def _fixed_template(
    first_name: str,
    company_name: str,
    industry: str,
    title: str,
    description: str,
) -> dict:
    """
    Deterministic outreach template.
    Uses all available context while avoiding hallucinations.
    """

    observation = ""
    if description:
        first_sentence = description.split(".")[0].strip()
        if first_sentence:
            observation = f"I noticed {first_sentence.lower()}."

    if title:
        opener = (
            f"I came across {company_name} and noticed your work as "
            f"{title} there."
        )
    else:
        opener = (
            f"I came across {company_name} and was impressed by what "
            f"your team is building."
        )

    if industry:
        fit_line = (
            f"Given {company_name}'s focus in {industry}, "
            f"I think there's a strong fit with what we're building "
            f"at {YOUR_COMPANY}."
        )
    else:
        fit_line = (
            f"I think there's a strong fit between "
            f"{company_name} and what we're building at {YOUR_COMPANY}."
        )

    subject = f"Quick question about {company_name}"

    body = (
        f"Hi {first_name},\n\n"
        f"{opener}\n\n"
        f"{observation}\n\n"
        f"{fit_line}\n\n"
        f"{YOUR_PITCH}\n\n"
        f"Worth a 15-minute conversation sometime this week?\n\n"
        f"Best,\n"
        f"{YOUR_NAME}"
    )

    return {
        "subject": subject,
        "body": body,
    }


def _ollama_enhance(
    fixed:        dict,
    first_name:   str,
    company_name: str,
    industry:     str,
    title:        str,
    description:  str,
) -> dict:
    """
    Optional Ollama enhancement — rewrites the fixed template
    to sound more natural. Falls back to fixed if it fails.
    """
    prompt = f"""
You are an experienced B2B SDR writing a concise cold outreach email.

Your task is to improve the email below while preserving all factual information.

RULES:
- Keep the recipient's name.
- Keep the company name.
- Keep the prospect's role/title context.
- Keep the core value proposition.
- Do NOT invent facts, metrics, customers, results, or achievements.
- Do NOT add information that is not present in the provided email or context.
- Do NOT use hype, marketing buzzwords, or exaggerated claims.
- Keep the tone professional, confident, and conversational.
- Keep the body under 120 words.
- End with a simple call-to-action.
- The final signature MUST be exactly:

Best,
{YOUR_NAME}

ORIGINAL EMAIL

Subject:
{fixed['subject']}

Body:
{fixed['body']}

RECIPIENT CONTEXT

Name: {first_name}
Title: {title or 'Unknown'}
Company: {company_name}
Industry: {industry or 'Unknown'}
Company Description:
{description[:300] if description else 'N/A'}

OUTPUT REQUIREMENTS

Return ONLY valid JSON.

Required format:

{{
  "subject": "email subject",
  "body": "email body"
}}

Do not include markdown.
Do not include code fences.
Do not include explanations.
Do not include any text outside the JSON object.
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model":  OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": 350}
            },
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json().get("response", "").strip()

        # Strip markdown fences
        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw = part
                    break

        data = json.loads(raw.strip())

        if "subject" not in data or "body" not in data:
            raise ValueError("Missing keys")

        body = data["body"].strip()

        # Enforce signature if Ollama dropped it
        if YOUR_NAME not in body:
            body = body.rstrip() + f"\n\nBest,\n{YOUR_NAME}"

        # Sanity check — must still mention company and first name
        combined = (body + data["subject"]).lower()
        if company_name.lower() not in combined:
            raise ValueError("Lost company name")
        if first_name.lower() not in combined:
            raise ValueError("Lost prospect name")

        return {"subject": data["subject"].strip(), "body": body}

    except requests.exceptions.ConnectionError:
        return None  # Ollama not running
    except Exception:
        return None  # Any parse/logic error


def generate_email(prospect: dict, company_data: dict | None = None) -> dict:
    """
    Hybrid email generation:
    1. Build a solid fixed template using all available data
    2. Try Ollama to enhance/rewrite it naturally
    3. If Ollama fails for any reason, use the fixed template

    Returns dict: {subject, body, method}
    method = "ollama" or "template" — useful for debugging
    """
    name         = prospect.get("name", "there")
    first_name   = name.split()[0] if name else "there"
    company_name = prospect.get("company_name", "your company")
    title        = (prospect.get("title") or "").strip()

    # Company context from Stage 2A (enriched) or Stage 1 (lean)
    industry    = ""
    description = ""
    if company_data:
        industry    = (company_data.get("industry") or "").strip()
        description = (company_data.get("description") or "").strip()

    # Step 1: Always build fixed template first
    fixed = _fixed_template(first_name, company_name, industry, title, description)

    # Step 2: Try Ollama enhancement
    enhanced = _ollama_enhance(fixed, first_name, company_name, industry, title, description)

    if enhanced:
        return {**enhanced, "method": "ollama"}
    else:
        return {**fixed, "method": "template"}


def generate_emails_for_all(
    prospects: list[dict],
    companies: list[dict] | None = None,
) -> list[dict]:
    """
    Runs generate_email() for every prospect.
    Matches enriched company data by company_domain.
    """
    company_lookup = {}
    if companies:
        for c in companies:
            domain = c.get("domain", "")
            if domain:
                company_lookup[domain] = c

    results = []
    ollama_count   = 0
    template_count = 0

    for i, prospect in enumerate(prospects):
        name   = prospect.get("name", "Unknown")
        domain = prospect.get("company_domain", "")
        print(f"[{i+1}/{len(prospects)}] Generating email for {name}...", end=" ")

        company_data = company_lookup.get(domain)
        email        = generate_email(prospect, company_data)

        method = email.pop("method", "template")
        if method == "ollama":
            ollama_count += 1
            print(f"done (ollama)")
        else:
            template_count += 1
            print(f"done (template)")

        results.append({**prospect, **email})

    print(f"\nStage 4: {len(results)} emails generated "
          f"({ollama_count} ollama, {template_count} template)")
    return results


if __name__ == "__main__":
    test_prospect = {
        "name":           "Akhil Joshi",
        "title":          "Associate Director",
        "linkedin_url":   "https://www.linkedin.com/in/akhil-joshi-3055341b",
        "company_domain": "razorpay.com",
        "company_name":   "Razorpay",
        "email":          "akhil.joshi@razorpay.com",
    }
    test_company = {
        "name":        "Razorpay",
        "domain":      "razorpay.com",
        "industry":    "Software Development",
        "size":        "1001-5000",
        "country":     "India",
        "city":        "Bengaluru",
        "description": "Razorpay is a payment solution provider for online "
                       "payments in India, offering a complete payment and "
                       "banking platform for businesses.",
    }

    print("=== Fixed template ===")
    fixed = _fixed_template(
        "Akhil", "Razorpay",
        test_company["industry"],
        test_prospect["title"],
        test_company["description"]
    )
    print(f"Subject: {fixed['subject']}")
    print(f"Body:\n{fixed['body']}")

    print("\n=== Hybrid (template + Ollama) ===")
    result = generate_email(test_prospect, test_company)
    print(f"Subject: {result['subject']}")
    print(f"Body:\n{result['body']}")