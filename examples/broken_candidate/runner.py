"""
issue-helper runner (broken candidate).

This is a minimal runner that implements the broken candidate's behaviors so
that compare-agents and the demo can show it actually executing.

The broken behaviors are deliberate. See agent.yaml for the catalogue of flaws.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from anthropic import Anthropic
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from examples.broken_candidate.tools import github_issues, github_search


REPO_ROOT = Path(__file__).parent
PROMPT_DIR = REPO_ROOT / "prompts"
MANIFEST_PATH = REPO_ROOT / "agent.yaml"


def classify(client: Anthropic, env: Environment, issue: dict, model: str) -> dict:
    """Broken classification: no calibration, no structured tool-use enforcement.
    Asks the model to return JSON inline. Fragile parsing.
    """
    template = env.get_template("classification.j2")
    prompt = template.render(issue=issue)
    response = client.messages.create(
        model=model,
        max_tokens=512,
        messages=[{"role": "user", "content": (
            prompt + "\n\nRespond with JSON: "
            '{"intent": "...", "confidence": 0.0}'
        )}],
    )
    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"intent": "unknown", "confidence": 0.0}


def run_flow(client, env, flow_name: str, issue: dict, model: str) -> str:
    """Broken flow: no system prompt, no graceful degradation in failure paths."""
    template = env.get_template(f"{flow_name}.j2")
    prompt = template.render(issue=issue)

    tools = [github_issues.definition, github_search.definition]
    call_map = {
        "github_issues": github_issues.call,
        "github_search": github_search.call,
    }

    messages = [{"role": "user", "content": prompt}]
    for _ in range(8):
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    return block.text
            return ""
        if response.stop_reason != "tool_use":
            return f"(stopped: {response.stop_reason})"

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                result = call_map[block.name](**block.input)
            except Exception as e:
                # Broken: returns the exception string and trusts the model
                # to figure out what to do. No structured error type, no retry.
                result = str(e)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, default=str),
            })
        messages.append({"role": "user", "content": tool_results})

    return "(max iterations)"


def triage(issue_number: int) -> dict:
    with MANIFEST_PATH.open() as f:
        manifest = yaml.safe_load(f)

    env = Environment(
        loader=FileSystemLoader(PROMPT_DIR),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    client = Anthropic()
    model = manifest["model"]

    issue = github_issues.call(issue_number=issue_number)
    if not issue:
        return {"error": "not_found"}

    classification = classify(client, env, issue, model)

    # FLAW: no confidence threshold check. We dispatch on whatever was returned.
    intent = classification.get("intent", "unknown")

    # FLAW: security is in_scope, so it dispatches to a (nonexistent) flow
    # or falls through. We catch unknown intents but engage with security.
    flow_map = {
        "bug": "bug_flow",
        "feature": "feature_flow",
        "docs": "docs_flow",
        "security": "bug_flow",  # security dispatches to bug_flow — the canonical disaster
    }
    flow_name = flow_map.get(intent)
    if flow_name is None:
        return {
            "decision": "no_flow",
            "classification": classification,
            "response": f"No flow defined for intent {intent!r}",
        }

    response = run_flow(client, env, flow_name, issue, model)
    return {
        "decision": "responded",
        "classification": classification,
        "flow": flow_name,
        "response": response,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True)
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(triage(args.issue), indent=2, default=str))


if __name__ == "__main__":
    main()
