"""
The single required CLI command.

Usage:
    python cli.py analyze --input sample_request.json --output out.json

This script does NOT contain any detection logic itself -- it's a thin
client that reads a JSON file, POSTs it to the already-running API,
and writes the response to a file. This mirrors how a real CLI tool
(like `curl`, or `aws` CLI) works: it's a convenience wrapper around
an API, not a reimplementation of the server's logic.
"""

import argparse
import json
import sys

import requests


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SentraGuard CLI - analyze a prompt via the running API"
    )
    parser.add_argument(
        "command", choices=["analyze"], help="The action to perform"
    )
    parser.add_argument(
        "--input", required=True, help="Path to input JSON file"
    )
    parser.add_argument(
        "--output", required=True, help="Path to write the output JSON file"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the running API (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    try:
        with open(args.input, "r") as f:
            payload = json.load(f)
    except FileNotFoundError:
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: input file is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        response = requests.post(f"{args.api_url}/analyze", json=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}", file=sys.stderr)
        sys.exit(1)

    result = response.json()

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Analysis complete. Decision: {result['decision']} "
          f"(risk_score={result['risk_score']}). Wrote result to {args.output}")


if __name__ == "__main__":
    main()
