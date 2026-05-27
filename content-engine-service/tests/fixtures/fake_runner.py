from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--timeout", required=True)
    args = parser.parse_args()

    prompt = open(args.prompt_file).read()
    print(json.dumps({"dispatch_status": "ok", "output": f"runner output via {args.lane}/{args.tool}; prompt_chars={len(prompt)}", "receipt_id": "fake-receipt"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
