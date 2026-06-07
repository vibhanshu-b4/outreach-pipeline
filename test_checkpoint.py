"""
Test for Checkpoint — run with: python test_checkpoint.py
No API calls, no credits. Uses fake data.
"""
from checkpoint import show_checkpoint, save_checkpoint, load_checkpoint
from pathlib import Path
import json

FAKE_PROSPECTS = [
    {
        "name":           "Akhil Joshi",
        "title":          "",
        "linkedin_url":   "https://www.linkedin.com/in/akhil-joshi-3055341b",
        "company_domain": "razorpay.com",
        "company_name":   "Razorpay",
        "email":          "akhil@razorpay.com",
        "subject":        "Razorpay Payment Solutions Automation",
        "body":           "Hi Akhil,\n\nAs a leading payment provider in India, "
                          "Razorpay is always looking for ways to scale.\n\n"
                          "We help B2B companies automate customer calls without "
                          "hiring more agents.\n\nWorth a 15-min call?\n\nBest,\nVibhanshu",
    },
    {
        "name":           "Neeraj Bagdia",
        "title":          "",
        "linkedin_url":   "https://www.linkedin.com/in/neerajbagdia",
        "company_domain": "cashfree.com",
        "company_name":   "Cashfree Payments",
        "email":          "neeraj@cashfree.com",
        "subject":        "Quick question for Cashfree Payments",
        "body":           "Hi Neeraj,\n\nI came across Cashfree Payments and "
                          "thought there might be a fit.\n\n"
                          "We help B2B companies automate outreach at scale.\n\n"
                          "Worth a 15-min call?\n\nBest,\nVibhanshu",
    },
]


def run_tests():
    print("=" * 50)
    print("TESTS: Checkpoint")
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

    # Test 1: save and load checkpoint state
    print("\n[Test 1] save_checkpoint / load_checkpoint...")
    test_state = {
        "razorpay.com":  {"enriched": True, "people_found": True, "email_found": True},
        "cashfree.com":  {"enriched": True, "people_found": True, "email_found": False},
    }
    save_checkpoint(test_state)
    loaded = load_checkpoint()

    check(loaded == test_state,
          "checkpoint saves and loads correctly",
          f"mismatch — saved: {test_state}, loaded: {loaded}")

    check(Path("data/checkpoint.json").exists(),
          "data/checkpoint.json file created",
          "checkpoint file not found on disk")

    # Test 2: load_checkpoint returns empty dict when file missing
    print("\n[Test 2] load_checkpoint with no file...")
    temp = Path("data/checkpoint.json")
    temp.rename("data/checkpoint_backup.json")
    empty = load_checkpoint()
    Path("data/checkpoint_backup.json").rename("data/checkpoint.json")

    check(empty == {},
          "returns empty dict when no checkpoint file",
          f"expected {{}}, got {empty}")

    # Test 3: show_checkpoint with empty list
    print("\n[Test 3] show_checkpoint with empty prospects...")
    # Redirect to avoid interactive prompt
    import io, sys
    captured = io.StringIO()
    sys.stdout = captured
    result_empty = show_checkpoint([])
    sys.stdout = sys.__stdout__
    output = captured.getvalue()

    check(result_empty == False,
          "returns False for empty prospects list",
          f"expected False, got {result_empty}")

    check("No contacts" in output,
          "prints helpful message for empty list",
          "no helpful message shown for empty list")

    # Test 4: show_checkpoint display (skip actual y/n prompt in test)
    print("\n[Test 4] show_checkpoint display (auto-answering 'n')...")
    import unittest.mock as mock
    with mock.patch("builtins.input", return_value="n"):
        result_n = show_checkpoint(FAKE_PROSPECTS)

    check(result_n == False,
          "returns False when user answers 'n'",
          f"expected False, got {result_n}")

    # Test 5: show_checkpoint returns True on 'y'
    print("\n[Test 5] show_checkpoint returns True on 'y'...")
    with mock.patch("builtins.input", return_value="y"):
        result_y = show_checkpoint(FAKE_PROSPECTS)

    check(result_y == True,
          "returns True when user answers 'y'",
          f"expected True, got {result_y}")

    print("\n" + "=" * 50)
    print(f"RESULT: {passed}/{total} passed")
    print("=" * 50)

    if passed == total:
        print("\nCheckpoint OK. Ready to wire main.py.")
    else:
        print("\nFix failures above.")


if __name__ == "__main__":
    run_tests()