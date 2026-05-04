"""
Conversation engine for the agent-spec meta-agent.

Takes a user-provided description, asks structured clarifying questions
through tool use, then produces a complete AgentSpec via forced tool_choice.

Built directly on the Anthropic SDK — no framework, no wrapper. The Platform
primitives exercised here are exactly the ones partner devs need to learn:

- Tool use with multiple tools (ask_user_question, submit_spec)
- Forced structured output via tool_choice
- Multi-turn conversation with tool_result feedback
- Stop-reason handling on each iteration

This is the "agent that builds agent specs" — a meta-agent that uses the
methodology in agent-skill-kit to scaffold new agents.
"""

import json
import os
import sys
from typing import Any

from anthropic import Anthropic

from scaffold_agent.spec import (
    AgentSpec, IntentSpec, ToolSpec, FlowSpec,
    validate_spec, spec_to_dict,
)


MODEL = "claude-sonnet-4-5"
MAX_CLARIFYING_TURNS = 4   # cap conversation length so it can't loop forever
MAX_TOKENS = 4096


# ---------------------------------------------------------------------------
# Tool definitions for the meta-agent's conversation
# ---------------------------------------------------------------------------

ASK_USER_QUESTION = {
    "name": "ask_user_question",
    "description": (
        "Ask the user one clarifying question. Use this when you need "
        "specific information to produce a high-quality agent spec — "
        "intents, tools, audience, or constraints. Do NOT use this for "
        "open-ended chat. Each question should be answerable in 1-2 "
        "sentences and should make a concrete decision."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": (
                    "The question to ask. Specific and answerable. Bad: "
                    "'What do you want?' Good: 'What are 2-3 in-scope "
                    "intents this agent should handle, vs out-of-scope "
                    "intents it should escalate?'"
                ),
            },
            "why_asking": {
                "type": "string",
                "description": (
                    "One sentence explaining why this answer matters for "
                    "the spec. Helps the user give a useful answer."
                ),
            },
        },
        "required": ["question", "why_asking"],
    },
}


SUBMIT_SPEC = {
    "name": "submit_spec",
    "description": (
        "Submit the final agent spec. Call this exactly once, after you "
        "have enough information to produce a coherent spec. Do not call "
        "this until you've asked at least one clarifying question — vague "
        "specs produce vague agents."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": (
                    "snake_case name for the agent, e.g. 'lead_triage' or "
                    "'support_ticket_router'. Lowercase, no spaces."
                ),
            },
            "description": {
                "type": "string",
                "description": "1-2 sentence description of what the agent does.",
            },
            "domain": {
                "type": "string",
                "description": "Short phrase describing the domain, e.g. 'B2B sales operations'.",
            },
            "audience": {
                "type": "string",
                "description": "Who or what calls this agent — humans, other agents, automation.",
            },
            "intents": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "snake_case, e.g. 'qualified_lead'"},
                        "description": {"type": "string", "description": "1-2 sentences for the classifier"},
                        "in_scope": {"type": "boolean", "description": "if False, agent escalates rather than handles"},
                        "signals": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "2-4 phrases the classifier should look for",
                        },
                    },
                    "required": ["name", "description", "in_scope", "signals"],
                },
            },
            "tools": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "snake_case"},
                        "purpose": {"type": "string"},
                        "when_to_use": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        "when_not_to_use": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        "inputs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                                "required": ["name", "type", "description"],
                            },
                        },
                        "output_shape": {"type": "string"},
                    },
                    "required": ["name", "purpose", "when_to_use", "when_not_to_use", "inputs", "output_shape"],
                },
            },
            "flows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "intent": {"type": "string", "description": "must match an in_scope intent name"},
                        "steps": {"type": "array", "items": {"type": "string"}, "minItems": 2},
                        "output_fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                                "required": ["name", "description"],
                            },
                        },
                    },
                    "required": ["intent", "steps", "output_fields"],
                },
            },
            "confidence_threshold": {
                "type": "number",
                "minimum": 0.5,
                "maximum": 0.95,
                "description": "below this, classification routes to unknown. Default 0.7.",
            },
            "eval_examples": {
                "type": "array",
                "minItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "the example case in 1 sentence"},
                        "expected_intent": {"type": "string"},
                        "notes": {"type": "string"},
                    },
                    "required": ["description", "expected_intent"],
                },
                "description": (
                    "3-5 starter golden-set examples for the routing eval. "
                    "Must cover four categories with at least one of each: "
                    "(a) clear-cut in-scope, (b) boundary between two in-scope "
                    "intents, (c) ambiguous case that should escalate to unknown, "
                    "(d) clear out-of-scope."
                ),
            },
        },
        "required": [
            "name", "description", "domain", "audience",
            "intents", "tools", "flows",
            "confidence_threshold", "eval_examples",
        ],
    },
}


# ---------------------------------------------------------------------------
# System prompt for the meta-agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a meta-agent that helps users design new Claude-based agents. Your job is to take a one-line description and produce a complete agent spec following an opinionated methodology.

The methodology comes from the agent-skill-kit project. The principles you must encode in every spec you produce:

1. **Calibrated routing.** Every classification has a confidence score. Below threshold, the agent escalates rather than guesses.
2. **Explicit out-of-scope handling.** Some intents must be classified but never handled directly — they get routed to humans. Common examples: security disclosures, legal questions, billing escalations.
3. **Tools are prompts.** Tool descriptions must include what the tool does, when to use it, and CRITICALLY when NOT to use it. The "when not to use" guidance is what prevents misfires.
4. **Eval first.** Every agent ships with a starter routing eval. The user provides 3-5 example cases and you turn them into a golden set.
5. **Visible reasoning, structured output.** Flows produce structured output (named fields with descriptions), not free-form text.

## Your loop

1. Read the user's description.
2. If it's specific enough to produce a high-quality spec, skip to step 4. Most descriptions are not specific enough.
3. Use `ask_user_question` to ask 1-3 clarifying questions, ONE AT A TIME. Wait for the user's answer before asking the next. Good questions cover:
   - What are the in-scope vs out-of-scope intents?
   - What tools does the agent need? (be specific about what data/services)
   - Who or what calls this agent?
   - Any compliance or safety constraints?
4. Once you have enough information, call `submit_spec` with the complete agent spec. ONE call only. The spec must be self-consistent: every flow's intent must match an in-scope intent name; every tool must have when-not-to-use guidance.

## Important rules

- Ask AT MOST 3 clarifying questions. If you've asked 3 and still don't have enough, do your best with what you have.
- Do NOT ask questions you can answer yourself. If the user said "sales leads," you don't need to ask "what kind of business?"
- Every intent you mark `in_scope: true` must have a corresponding flow in the `flows` array.
- Every tool description must include genuine "when NOT to use" guidance — not boilerplate. Think about what failure mode the model could fall into and tell it to avoid that.
- The eval examples must cover four kinds of cases. Include at least one of each:
  1. A clear-cut in-scope case (one intent obviously applies, signals are strong).
  2. A boundary case between two in-scope intents (signals could point either way; the golden answer is one of them with reasoning).
  3. An ambiguous case that should escalate to `unknown` (mixed or insufficient signals — confidence below threshold).
  4. A clear out-of-scope case (one of the out-of-scope intents).
  Generic "good example" listings are not enough — each example needs to test a different kind of decision.
- Names must be snake_case lowercase.

You are not chatting. You are designing an agent. Be terse, technical, deliberate.\
"""


# ---------------------------------------------------------------------------
# Conversation runner
# ---------------------------------------------------------------------------

def run_meta_agent(initial_description: str, verbose: bool = False) -> tuple[AgentSpec, list[str]]:
    """
    Run the meta-agent conversation. Returns (spec, validation_errors).

    Architecture: a tool-use loop. The model can do exactly two things:
    - Ask the user a clarifying question (`ask_user_question`).
    - Submit the final spec (`submit_spec`).

    The user answers questions via stdin. Submitting the spec ends the loop.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set")

    client = Anthropic()
    tools = [ASK_USER_QUESTION, SUBMIT_SPEC]

    # The conversation starts with the user's description as the opening message.
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": initial_description}
    ]

    questions_asked = 0
    spec: AgentSpec | None = None

    for turn in range(MAX_CLARIFYING_TURNS + 2):  # +2 for the spec submission turns
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        if verbose:
            _log_turn(turn, response)

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Model produced text without a tool call. This shouldn't happen
            # given the instructions, but handle gracefully.
            print(
                "\n[meta-agent] Model produced text without a tool call. "
                "Treating as end of conversation.",
                file=sys.stderr,
            )
            break

        if response.stop_reason != "tool_use":
            print(
                f"\n[meta-agent] Unexpected stop_reason: {response.stop_reason}",
                file=sys.stderr,
            )
            break

        # Process each tool_use block. There can be more than one in a turn,
        # though we steer the model toward one at a time.
        tool_results: list[dict[str, Any]] = []
        spec_submitted = False

        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name == "ask_user_question":
                if questions_asked >= MAX_CLARIFYING_TURNS:
                    # Refuse — model is over budget. Tell it to submit.
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": (
                            "You have asked the maximum number of clarifying "
                            "questions. Submit the spec now with the information "
                            "you have."
                        ),
                    })
                    continue

                question = block.input.get("question", "")
                why = block.input.get("why_asking", "")
                answer = _ask_user(question, why, questions_asked + 1)
                questions_asked += 1
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": answer,
                })

            elif block.name == "submit_spec":
                spec = _spec_from_tool_input(block.input)
                spec_submitted = True
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Spec received. Conversation complete.",
                })

            else:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"Unknown tool: {block.name}",
                    "is_error": True,
                })

        messages.append({"role": "user", "content": tool_results})

        if spec_submitted:
            break

    if spec is None:
        raise RuntimeError(
            "meta-agent never submitted a spec. "
            "Try a more specific description."
        )

    errors = validate_spec(spec)
    return spec, errors


def _ask_user(question: str, why_asking: str, question_num: int) -> str:
    """Ask the user a question and return their answer."""
    print(f"\n[Q{question_num}] {question}")
    print(f"      ({why_asking})")
    try:
        answer = input("> ").strip()
    except EOFError:
        answer = ""
    if not answer:
        return "(no answer provided)"
    return answer


def _spec_from_tool_input(tool_input: dict[str, Any]) -> AgentSpec:
    """Convert the structured tool_input into an AgentSpec dataclass."""
    intents = [
        IntentSpec(
            name=i["name"],
            description=i["description"],
            in_scope=i["in_scope"],
            signals=i.get("signals", []),
        )
        for i in tool_input.get("intents", [])
    ]
    tools = [
        ToolSpec(
            name=t["name"],
            purpose=t["purpose"],
            when_to_use=t["when_to_use"],
            when_not_to_use=t["when_not_to_use"],
            inputs=t["inputs"],
            output_shape=t["output_shape"],
        )
        for t in tool_input.get("tools", [])
    ]
    flows = [
        FlowSpec(
            intent=f["intent"],
            steps=f["steps"],
            output_fields=f["output_fields"],
        )
        for f in tool_input.get("flows", [])
    ]
    return AgentSpec(
        name=tool_input["name"],
        description=tool_input["description"],
        domain=tool_input["domain"],
        audience=tool_input["audience"],
        intents=intents,
        tools=tools,
        flows=flows,
        confidence_threshold=tool_input.get("confidence_threshold", 0.7),
        eval_examples=tool_input.get("eval_examples", []),
    )


def _log_turn(turn: int, response: Any) -> None:
    print(f"\n--- meta-agent turn {turn} ---", file=sys.stderr)
    print(f"stop_reason: {response.stop_reason}", file=sys.stderr)
    for block in response.content:
        if block.type == "text":
            print(f"[text] {block.text[:200]}", file=sys.stderr)
        elif block.type == "tool_use":
            print(f"[tool_use] {block.name}", file=sys.stderr)
            print(f"  input: {json.dumps(block.input)[:300]}", file=sys.stderr)
