"""Simple command-line runner for the detector."""
import argparse
from scamshield import is_scam


def main():
    parser = argparse.ArgumentParser(description="Run ScamShield detector on text or a file")
    parser.add_argument("--file", "-f", help="Path to a file to scan")
    parser.add_argument("--text", "-t", help="A single text string to scan")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            content = fh.read()
    else:
        content = args.text or ""

    result = is_scam(content)
    print("SCAM" if result else "OK")


if __name__ == "__main__":
    main()
