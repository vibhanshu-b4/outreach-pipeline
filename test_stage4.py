"""
Test for Stage 4 — Ollama Email Generation

No API credits needed — runs fully local.
Ollama must be running: ollama serve

Run: python test_stage4.py
"""
import json
from stage4_emailgen import generate_email, generate_emails_for_all, YOUR_NAME, YOUR_COMPANY

TEST_PROSPECT = {
    "name":           "Akhil Joshi",
    "title":          "",
    "linkedin_url":   "https://www.linkedin.com/in/akhil-joshi-3055341b",
    "company_domain": "razorpay.com",
    "company_name":   "Razorpay",
    "email":          "akhil@razorpay.com",
}

TEST_COMPANY = {
    "name":        "Razorpay",
    "domain":      "razorpay.com",
    "industry":    "Software Development",
    "size":        "2001-5000",
    "country":     "India",
    "city":        "Bengaluru",
    "description": "Razorpay is a payment solution provider for online payments "
                   "in India, offering a complete payment and banking platform.",
}

TEST_PROSPECTS_MULTI = [
    TEST_PROSPECT,
    {
        "name":           "Neeraj Bagdia",
        "title":          "",
        "linkedin_url":   "https://www.linkedin.com/in/neerajbagdia",
        "company_domain": "cashfree.com",
        "company_name":   "Cashfree Payments",
        "email":          "neeraj@cashfree.com",
    },
]

TEST_COMPANIES_MULTI = [
    TEST_COMPANY,
    {
        "name":        "Cashfree Payments",
        "domain":      "cashfree.com",
        "industry":    "Financial Services",
        "size":        "501-1000",
        "country":     "India",
        "city":        "Bengaluru",
        "description": "Cashfree Payments is a complete payment and banking "
                       "platform for businesses in India.",
    },
]


def run_tests():
    print("=" * 50)
    print("TESTS: Stage 4 — Ollama Email Generation")
    print("=" * 50)
    passed = 0
    total  = 0

    def check(condition, pass_msg, fail_msg):
        nonlocal passed, total
        total += 1
        if condition:
            print(f"  PASS  {pass_msg}")
            passed += 1
        else:
            print(f"  FAIL  {fail_msg}")

    # --- Test 1: basic return type ---
    print("\n[Test 1] Single email generation...")
    result = generate_email(TEST_PROSPECT, TEST_COMPANY)

    check(isinstance(result, dict),
          "returns a dict",
          f"expected dict, got {type(result)}")

    check("subject" in result and "body" in result,
          "has both 'subject' and 'body' keys",
          f"missing keys — got: {list(result.keys())}")

    check(isinstance(result.get("subject"), str) and len(result["subject"]) > 0,
          "subject is a non-empty string",
          "subject is empty or wrong type")

    check(isinstance(result.get("body"), str) and len(result["body"]) > 0,
          "body is a non-empty string",
          "body is empty or wrong type")

    # --- Test 2: personalization checks ---
    print("\n[Test 2] Personalization checks...")
    body    = result.get("body", "")
    subject = result.get("subject", "")
    combined = (body + subject).lower()

    check("akhil" in combined or "razorpay" in combined,
          "email mentions recipient name or company",
          "email has no mention of name or company — not personalized")

    check(YOUR_NAME.lower() in body.lower(),
          f"email signed off with sender name ({YOUR_NAME})",
          f"sender name '{YOUR_NAME}' not found in body")

    check(len(body.split()) <= 120,
          f"body is concise ({len(body.split())} words)",
          f"body too long ({len(body.split())} words — aim for under 100)")

    # --- Test 3: no junk keys ---
    print("\n[Test 3] No extra keys...")
    extra = set(result.keys()) - {"subject", "body"}
    check(not extra,
          "no extra keys in output",
          f"unexpected extra keys: {extra}")

    # --- Test 4: fallback works without Ollama ---
    print("\n[Test 4] Fallback template (no Ollama needed)...")
    from stage4_emailgen import _fallback_template
    fallback = _fallback_template("Akhil", "Razorpay")
    check("subject" in fallback and "body" in fallback,
          "fallback returns subject and body",
          "fallback missing keys")
    check("Akhil" in fallback["body"],
          "fallback personalizes with first name",
          "fallback body missing first name")

    # --- Test 5: batch generation ---
    print("\n[Test 5] Batch email generation (2 prospects)...")
    batch = generate_emails_for_all(TEST_PROSPECTS_MULTI, TEST_COMPANIES_MULTI)
    check(len(batch) == 2,
          "returns 2 results for 2 prospects",
          f"expected 2, got {len(batch)}")
    check(all("subject" in p and "body" in p for p in batch),
          "all batch results have subject and body",
          "some batch results missing subject or body")
    check(all("email" in p for p in batch),
          "original prospect fields preserved in batch output",
          "prospect fields lost during batch generation")

    # --- Results ---
    print("\n" + "=" * 50)
    print(f"RESULT: {passed}/{total} passed")
    print("=" * 50)

    if passed == total:
        print("\nGenerated email preview:")
        print(f"\n  Subject : {result['subject']}")
        print(f"\n  Body:\n")
        for line in result["body"].split("\n"):
            print(f"    {line}")
        print("\nStage 4 OK. Ready for checkpoint.")
    else:
        print("\nFix failures above before moving to checkpoint.")


if __name__ == "__main__":
    print("Make sure Ollama is running before this test.")
    print("Start it with: ollama serve\n")
    run_tests()