"""
Routing eval — runs classification against the golden set and reports pass rate.

Pass criteria for a single example:
  - Predicted intent matches expected intent
  - Predicted confidence >= expected_min_confidence

Usage:
    python -m reference_agent.evals.routing.run_eval

Outputs structured JSON to stdout and a results file that skills can read.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from reference_agent.runner import classify_issue
from reference_agent.tools import github_issues


REPO_ROOT = Path(__file__).parent.parent.parent
PROMPT_DIR = REPO_ROOT / "prompts"
GOLDEN_PATH = REPO_ROOT / "evals" / "routing" / "golden.jsonl"
RESULTS_PATH = REPO_ROOT / "evals" / "routing" / "last_run.json"


def load_golden() -> list[dict]:
    with GOLDEN_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def run() -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set")

    env = Environment(
        loader=FileSystemLoader(PROMPT_DIR),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    client = Anthropic()

    import yaml
    with (REPO_ROOT / "agent.yaml").open() as f:
        manifest = yaml.safe_load(f)
    model = manifest["model"]

    golden = load_golden()
    results = []
    passes = 0

    for example in golden:
        issue = github_issues.call(issue_number=example["issue_number"])
        if "error" in issue:
            results.append({
                "issue_number": example["issue_number"],
                "passed": False,
                "reason": "fixture missing",
            })
            continue

        classification = classify_issue(client, env, issue, model, trace=[])

        intent_match = classification["intent"] == example["expected_intent"]
        confidence_ok = classification["confidence"] >= example["expected_min_confidence"]
        passed = intent_match and confidence_ok

        if passed:
            passes += 1

        results.append({
            "issue_number": example["issue_number"],
            "expected_intent": example["expected_intent"],
            "predicted_intent": classification["intent"],
            "predicted_confidence": classification["confidence"],
            "passed": passed,
            "notes": example.get("notes", ""),
        })

    pass_rate = passes / len(golden) if golden else 0.0
    summary = {
        "total": len(golden),
        "passed": passes,
        "pass_rate": pass_rate,
        "threshold": manifest["evals"]["routing"]["pass_threshold"],
        "meets_threshold": pass_rate >= manifest["evals"]["routing"]["pass_threshold"],
        "results": results,
    }

    RESULTS_PATH.write_text(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    summary = run()

    if args.quiet:
        print(json.dumps({
            "pass_rate": summary["pass_rate"],
            "passed": summary["passed"],
            "total": summary["total"],
            "meets_threshold": summary["meets_threshold"],
        }))
    else:
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
