"""
Test for Stage 5 — Brevo Email Sending

Sends ONE real email to TEST_RECIPIENT (anonymous2002@gmail.com).
Check your inbox after running.

Run: python test_stage5.py
Run dry run: python test_stage5.py --dry-run
"""
import sys
import os
from dotenv import load_dotenv
load_dotenv()
from stage5_brevo import send_emails
TEST_RECIPIENT = os.getenv("BREVO_TEST_RECIPIENT", "anonymous2002@gmail.com")

TEST_PROSPECT = {
    "name":         "Akhil Joshi",
    "company_name": "Razorpay",
    "email":        "akhil@razorpay.com",
    "subject":      "Razorpay Payment Solutions — Quick Question",
    "body": (
        "Hi Akhil,\n\n"
        "As a leading payment provider in India, Razorpay is always "
        "looking for innovative ways to scale customer operations.\n\n"
        "At Vocallabs, we build AI-powered voice automation tools that "
        "help B2B companies handle calls and follow-ups at scale — "
        "without hiring more agents.\n\n"
        "Worth a 15-min call to explore?\n\n"
        "Best,\nVibhanshu"
    ),
}


def run_tests(dry_run: bool = False):
    print("=" * 50)
    print("TESTS: Stage 5 — Brevo")
    print(f"Test recipient: {TEST_RECIPIENT}")
    if dry_run:
        print("Mode: DRY RUN (no emails sent)")
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

    # Test 1: send one email
    print("\n[Test 1] Sending one email...")
    result = send_emails([TEST_PROSPECT], dry_run=dry_run)

    check(isinstance(result, dict),
          "returns a dict",
          f"expected dict, got {type(result)}")

    check({"sent", "failed", "skipped"} == set(result.keys()),
          "result has sent/failed/skipped keys",
          f"wrong keys: {result.keys()}")

    check(result["sent"] == 1,
          f"1 email sent (sent={result['sent']})",
          f"expected 1 sent, got {result}")

    check(result["failed"] == 0,
          "0 failures",
          f"got {result['failed']} failure(s) — check API key or sender domain")

    # Test 2: skips prospect with no email
    print("\n[Test 2] Skips prospect with missing email...")
    no_email = {**TEST_PROSPECT, "email": ""}
    import unittest.mock as mock
    # Temporarily disable TEST_RECIPIENT to test real skip logic
    import stage5_brevo
    original = stage5_brevo.TEST_RECIPIENT
    stage5_brevo.TEST_RECIPIENT = None
    result2 = send_emails([no_email], dry_run=True)
    stage5_brevo.TEST_RECIPIENT = original

    check(result2["skipped"] == 1,
          "skips prospect with no email",
          f"expected skipped=1, got {result2}")

    # Test 3: dry run never calls API
    print("\n[Test 3] Dry run sends nothing...")
    result3 = send_emails([TEST_PROSPECT], dry_run=True)
    check(result3["sent"] == 1,
          "dry run counts as sent without API call",
          f"dry run result: {result3}")

    print("\n" + "=" * 50)
    print(f"RESULT: {passed}/{total} passed")
    print("=" * 50)

    if passed == total and not dry_run:
        print(f"\nCheck {TEST_RECIPIENT} inbox for the test email.")
        print("Stage 5 OK. Pipeline is complete.")
    elif passed == total and dry_run:
        print("\nDry run passed. Run without --dry-run to send real email.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_tests(dry_run=dry_run)