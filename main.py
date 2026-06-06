def run_pipeline(seed_domain):
	print(f"Starting pipeline for: {seed_domain}")


if __name__ == "__main__":
	import sys

	seed_domain = sys.argv[1] if len(sys.argv) > 1 else None
	run_pipeline(seed_domain)
