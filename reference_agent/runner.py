"""
issue-triage agent runner.

Loads the system prompt and flow-specific prompts via Jinja2, registers the
three tools, executes the classify-then-dispatch loop, and returns a
structured triage_decision.

This is intentionally written against the Anthropic SDK directly rather than
through any framework abstraction — the patterns this repo teaches are easier
to see when nothing is hidden by a wrapper.

Usage:
    python -m reference_agent.runner --issue 101
    python -m reference_agent.runner --issue 104  # security disclosure
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

# Local imports — the three tools, each exposing `definition` + `call`
from reference_agent.tools import codeowners_lookup, github_issues, github_search


REPO_ROOT = Path(__file__).parent
PROMPT_DIR = REPO_ROOT / "prompts"
MANIFEST_PATH = REPO_ROOT / "agent.yaml"


def load_manifest() -> dict[str, Any]:
    """Read agent.yaml. Skills also read this; keep the format stable."""
    with MANIFEST_PATH.open() as f:
        return yaml.safe_load(f)


def load_prompts() -> Environment:
    """Jinja2 environment with strict undefined so missing vars fail loudly."""
    return Environment(
        loader=FileSystemLoader(PROMPT_DIR),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


def build_tool_registry() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Returns (tool_definitions, tool_call_map).

    tool_definitions is the list of definition dicts passed to the model.
    tool_call_map dispatches a tool name to its `call` function.
    """
    tools = [github_issues, github_search, codeowners_lookup]
    definitions = [t.definition for t in tools]
    call_map = {t.definition["name"]: t.call for t in tools}
    return definitions, call_map


def classify_issue(
    client: Anthropic,
    env: Environment,
    issue: dict[str, Any],
    model: str,
    trace: list[str],
) -> dict[str, Any]:
    """
    Run the classification prompt and return {intent, confidence, reasoning}.

    Uses structured tool-use rather than JSON-in-prose. The model is given a
    single tool, `submit_classification`, with a strict schema. Forcing the
    model to call this tool eliminates the JSON-parsing fragility that
    haunts prose-based structured output.

    This is the pattern partner devs should adopt for any structured
    classification step. Model output you have to parse is a footgun.
    """
    classification_tool = {
        "name": "submit_classification",
        "description": (
            "Submit your classification of the issue. You must call this "
            "tool exactly once. Do not produce a final text response — call "
            "this tool with your decision."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [
                        "bug", "feature", "docs",
                        "security", "paid_support", "code_review",
                        "unknown",
                    ],
                    "description": "The classified intent.",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": (
                        "Calibrated confidence between 0 and 1. Below 0.7 "
                        "the agent will route to unknown regardless of "
                        "intent — be honest about uncertainty."
                    ),
                },
                "reasoning": {
                    "type": "string",
                    "description": (
                        "2-3 sentences explaining the signals used and "
                        "any considered alternatives."
                    ),
                },
            },
            "required": ["intent", "confidence", "reasoning"],
        },
    }

    template = env.get_template("classification.j2")
    prompt = template.render(issue=issue)
    trace.append(f"[classify] Sending classification prompt for issue #{issue['number']}")

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        tools=[classification_tool],
        tool_choice={"type": "tool", "name": "submit_classification"},
        messages=[{"role": "user", "content": prompt}],
    )

    # With tool_choice forcing the named tool, we expect exactly one tool_use block
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_classification":
            result = dict(block.input)
            trace.append(
                f"[classify] intent={result['intent']} "
                f"confidence={result['confidence']:.2f}"
            )
            return result

    # Fail safely if for some reason the model didn't call the tool
    trace.append("[classify] Model did not call submit_classification; escalating")
    return {
        "intent": "unknown",
        "confidence": 0.0,
        "reasoning": "Classification tool was not called by the model.",
    }


def run_flow_with_tools(
    client: Anthropic,
    env: Environment,
    flow_name: str,
    issue: dict[str, Any],
    classification: dict[str, Any],
    tool_definitions: list[dict[str, Any]],
    tool_call_map: dict[str, Any],
    model: str,
    trace: list[str],
    max_iterations: int = 10,
) -> str:
    """
    Run a flow prompt with tool-use enabled. Returns the final text response.

    Standard agent loop: model produces tool calls, we execute them and feed
    results back, repeat until end_turn.
    """
    flow_template = env.get_template(f"{flow_name}.j2")
    flow_prompt = flow_template.render(issue=issue, classification=classification)

    system_template = env.get_template("system.j2")
    system_prompt = system_template.render()

    messages: list[dict[str, Any]] = [{"role": "user", "content": flow_prompt}]
    trace.append(f"[flow] Entered {flow_name}")

    for iteration in range(max_iterations):
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            tools=tool_definitions,
            messages=messages,
        )

        # Append the assistant turn to history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Done — extract final text
            for block in response.content:
                if block.type == "text":
                    return block.text
            return "(no text in final response)"

        if response.stop_reason != "tool_use":
            trace.append(f"[flow] Unexpected stop_reason: {response.stop_reason}")
            return f"(unexpected stop_reason: {response.stop_reason})"

        # Execute each tool call and collect results
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_name = block.name
            tool_input = block.input
            trace.append(f"[tool] {tool_name}({json.dumps(tool_input)})")

            try:
                fn = tool_call_map[tool_name]
                result = fn(**tool_input)
                result_text = json.dumps(result, default=str)
            except Exception as e:
                result_text = json.dumps({"error": "tool_exception", "detail": str(e)})
                trace.append(f"[tool] EXCEPTION in {tool_name}: {e}")

            trace.append(f"[tool] {tool_name} result: {result_text[:200]}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_text,
            })

        messages.append({"role": "user", "content": tool_results})

    trace.append(f"[flow] Hit max_iterations={max_iterations}")
    return "(agent exceeded max iterations)"


def triage(issue_number: int) -> dict[str, Any]:
    """Main entry point. Returns a structured triage_decision dict."""
    manifest = load_manifest()
    env = load_prompts()
    client = Anthropic()
    model = manifest["model"]
    threshold = manifest["routing"]["confidence_threshold"]

    trace: list[str] = []

    # Step 1: Fetch the issue (this is itself a tool call, but we do it
    # directly because the agent needs the issue to even start)
    issue = github_issues.call(issue_number=issue_number)
    if "error" in issue:
        return {
            "decision": "error",
            "error": issue["error"],
            "trace": [f"[fetch] Issue #{issue_number} not found"],
        }

    trace.append(f"[fetch] Loaded issue #{issue['number']}: {issue['title'][:80]}")

    # Step 2: Classify
    classification = classify_issue(client, env, issue, model, trace)

    # Step 3: Branch on classification
    out_of_scope = manifest["intents"]["out_of_scope"]

    if classification["intent"] in out_of_scope:
        trace.append(f"[route] Out-of-scope intent: {classification['intent']}")
        return _produce_handoff(
            client, env, issue, classification, model, trace,
            escalation_reason="out_of_scope",
        )

    if classification["confidence"] < threshold:
        trace.append(
            f"[route] Low confidence ({classification['confidence']:.2f} < {threshold}); escalating"
        )
        classification["intent"] = "unknown"
        return _produce_handoff(
            client, env, issue, classification, model, trace,
            escalation_reason="low_confidence",
        )

    # Step 4: Dispatch to flow
    flow_map = {"bug": "bug_flow", "feature": "feature_flow", "docs": "docs_flow"}
    flow_name = flow_map.get(classification["intent"])
    if flow_name is None:
        trace.append(f"[route] No flow for intent {classification['intent']}; escalating")
        return _produce_handoff(
            client, env, issue, classification, model, trace,
            escalation_reason="policy",
        )

    tool_definitions, tool_call_map = build_tool_registry()
    final_text = run_flow_with_tools(
        client, env, flow_name, issue, classification,
        tool_definitions, tool_call_map, model, trace,
    )

    return {
        "decision": "handled_by_flow",
        "flow": flow_name,
        "classification": classification,
        "final_response": final_text,
        "trace": trace,
    }


def _produce_handoff(
    client: Anthropic,
    env: Environment,
    issue: dict[str, Any],
    classification: dict[str, Any],
    model: str,
    trace: list[str],
    escalation_reason: str,
) -> dict[str, Any]:
    """Render the handoff template and ask the model to fill it in."""
    template = env.get_template("handoff.j2")
    handoff_prompt = template.render(
        issue=issue,
        classification=classification,
        escalation_reason=escalation_reason,
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": handoff_prompt}],
    )
    text = response.content[0].text.strip()
    trace.append(f"[handoff] Produced handoff for {escalation_reason}")

    return {
        "decision": "handoff",
        "escalation_reason": escalation_reason,
        "classification": classification,
        "handoff": text,
        "trace": trace,
    }


def main():
    parser = argparse.ArgumentParser(description="Run issue-triage on a fixture issue")
    parser.add_argument("--issue", type=int, required=True, help="Issue number to triage")
    parser.add_argument("--show-trace", action="store_true", help="Print the trace")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    result = triage(args.issue)

    print(json.dumps(
        {k: v for k, v in result.items() if k != "trace"},
        indent=2,
        default=str,
    ))

    if args.show_trace:
        print("\n--- trace ---", file=sys.stderr)
        for line in result["trace"]:
            print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
