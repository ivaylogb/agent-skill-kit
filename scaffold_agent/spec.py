"""
Schema for the agent spec that the meta-agent produces.

The spec is the output of the conversation phase (where the meta-agent
clarifies what the user wants) and the input to the template phase (where
files are written to disk based on the spec).

Defining the schema explicitly does two things:
1. Forces the meta-agent to make every architectural decision deliberately.
   Vague specs produce vague agents.
2. Lets us validate before we generate files. A malformed spec fails fast
   instead of writing 12 broken files to disk.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntentSpec:
    """A single intent the agent will classify into."""
    name: str                       # e.g., "qualified_lead", "needs_more_info"
    description: str                # 1-2 sentences for the classification prompt
    in_scope: bool                  # if False, agent escalates rather than handles
    signals: list[str] = field(default_factory=list)
                                    # 2-4 phrases the classifier should look for


@dataclass
class ToolSpec:
    """A tool the agent will use."""
    name: str                       # snake_case, e.g., "lead_lookup"
    purpose: str                    # one sentence
    when_to_use: list[str]          # 2-3 cases (Platform best practice)
    when_not_to_use: list[str]      # 1-2 cases — the failure mode the model needs to know
    inputs: list[dict[str, str]]    # [{"name": ..., "type": ..., "description": ...}]
    output_shape: str               # short prose describing what call() returns


@dataclass
class FlowSpec:
    """An intent-specific flow the agent dispatches to."""
    intent: str                     # matches IntentSpec.name (must be in_scope)
    steps: list[str]                # 3-5 high-level steps the flow performs
    output_fields: list[dict[str, str]]
                                    # [{"name": ..., "description": ...}] — fields in
                                    # the structured output


@dataclass
class AgentSpec:
    """Full spec for a generated agent. Output of the meta-agent conversation."""
    name: str                       # snake_case, e.g., "lead_triage"
    description: str                # 1-2 sentence agent purpose
    domain: str                     # one phrase, e.g., "B2B sales operations"
    audience: str                   # who calls this agent — humans, other agents, automation
    intents: list[IntentSpec]
    tools: list[ToolSpec]
    flows: list[FlowSpec]
    confidence_threshold: float = 0.7
                                    # below this, classification routes to unknown
    eval_examples: list[dict[str, Any]] = field(default_factory=list)
                                    # 5-10 starter examples for routing/golden.jsonl


def validate_spec(spec: AgentSpec) -> list[str]:
    """
    Returns a list of validation errors. Empty list means the spec is valid.

    These are structural checks — does the spec describe a coherent agent?
    Quality checks (are the intents well-chosen? are the tools necessary?)
    are out of scope; those depend on the domain.
    """
    errors: list[str] = []

    # Name must be snake_case and non-empty
    if not spec.name or not spec.name.replace("_", "").isalnum():
        errors.append(f"name must be snake_case alphanumeric, got: {spec.name!r}")
    if not spec.name.islower():
        errors.append(f"name must be lowercase, got: {spec.name!r}")

    # Must have at least one in-scope intent
    in_scope_intents = [i for i in spec.intents if i.in_scope]
    if not in_scope_intents:
        errors.append("at least one intent must be in_scope")

    # Every flow's intent must match an in-scope intent
    in_scope_names = {i.name for i in in_scope_intents}
    flow_intents = {f.intent for f in spec.flows}
    for flow_intent in flow_intents:
        if flow_intent not in in_scope_names:
            errors.append(
                f"flow references intent {flow_intent!r} which is not in_scope"
            )

    # Every in-scope intent should have a flow (warn-level — we still proceed)
    for intent in in_scope_intents:
        if intent.name not in flow_intents:
            errors.append(
                f"in-scope intent {intent.name!r} has no flow — agent will have no path to handle it"
            )

    # Confidence threshold must be in (0, 1)
    if not (0 < spec.confidence_threshold < 1):
        errors.append(
            f"confidence_threshold must be between 0 and 1, got: {spec.confidence_threshold}"
        )

    # Tool names must be unique
    tool_names = [t.name for t in spec.tools]
    if len(tool_names) != len(set(tool_names)):
        errors.append("duplicate tool names")

    # Intent names must be unique
    intent_names = [i.name for i in spec.intents]
    if len(intent_names) != len(set(intent_names)):
        errors.append("duplicate intent names")

    return errors


def spec_to_dict(spec: AgentSpec) -> dict[str, Any]:
    """Convert spec to plain dict for serialization or LLM consumption."""
    from dataclasses import asdict
    return asdict(spec)
