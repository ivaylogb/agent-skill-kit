"""
CLI for scaffold-agent.

    python -m scaffold_agent describe "An agent that triages sales leads" \\
        --output ./generated

The describe command runs the meta-agent's conversation, asks the user
clarifying questions, then writes a complete agent directory.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from scaffold_agent.meta_agent import run_meta_agent
from scaffold_agent.spec import spec_to_dict, validate_spec
from scaffold_agent.templates import generate


def cmd_describe(description: str, output_dir: Path, verbose: bool = False) -> int:
    """Run the meta-agent and generate an agent into output_dir."""
    print(f"\n=== scaffold-agent ===")
    print(f"Description: {description}\n")

    try:
        spec, validation_errors = run_meta_agent(description, verbose=verbose)
    except RuntimeError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1

    print(f"\n=== spec produced ===")
    print(f"Name: {spec.name}")
    print(f"Description: {spec.description}")
    print(f"Domain: {spec.domain}")
    print(f"Intents: {[(i.name, 'in' if i.in_scope else 'out') for i in spec.intents]}")
    print(f"Tools: {[t.name for t in spec.tools]}")
    print(f"Flows: {[f.intent for f in spec.flows]}")
    print(f"Eval examples: {len(spec.eval_examples)}")

    if validation_errors:
        print(f"\n=== validation: {len(validation_errors)} issue(s) ===", file=sys.stderr)
        for err in validation_errors:
            print(f"  - {err}", file=sys.stderr)
        # We still generate — validation errors are warn-level for most cases.
        # Critical structural issues (no in-scope intent, etc.) would fail
        # downstream as schema errors.
        print("\nProceeding to generate (warnings only).\n", file=sys.stderr)

    target = output_dir / spec.name
    print(f"\n=== generating into {target} ===")
    files = generate(spec, target)
    print(f"Wrote {len(files)} files.\n")

    print(f"To run the generated agent:")
    print(f"  cd {target.parent}")
    print(f"  export ANTHROPIC_API_KEY=...")
    print(f"  python -m {spec.name}.runner --input '<example>'")
    return 0


def cmd_describe_from_spec(spec_path: Path, output_dir: Path) -> int:
    """Generate from a JSON spec file (used for testing — skips the conversation)."""
    with spec_path.open() as f:
        data = json.load(f)

    from scaffold_agent.spec import AgentSpec, IntentSpec, ToolSpec, FlowSpec
    spec = AgentSpec(
        name=data["name"],
        description=data["description"],
        domain=data["domain"],
        audience=data["audience"],
        intents=[IntentSpec(**i) for i in data["intents"]],
        tools=[ToolSpec(**t) for t in data["tools"]],
        flows=[FlowSpec(**f) for f in data["flows"]],
        confidence_threshold=data.get("confidence_threshold", 0.7),
        eval_examples=data.get("eval_examples", []),
    )

    errors = validate_spec(spec)
    if errors:
        for err in errors:
            print(f"validation: {err}", file=sys.stderr)

    target = output_dir / spec.name
    files = generate(spec, target)
    print(f"Generated {len(files)} files into {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scaffold-agent")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_describe = sub.add_parser("describe", help="Build an agent from a natural-language description")
    p_describe.add_argument("description", help="One-line description of the agent")
    p_describe.add_argument("--output", type=Path, default=Path("./generated"),
                            help="Directory to write the generated agent (default: ./generated)")
    p_describe.add_argument("--verbose", action="store_true", help="Verbose meta-agent logs to stderr")

    p_from_spec = sub.add_parser("from-spec", help="Generate from a JSON spec file (skips conversation)")
    p_from_spec.add_argument("spec_path", type=Path, help="Path to JSON spec file")
    p_from_spec.add_argument("--output", type=Path, default=Path("./generated"))

    args = parser.parse_args(argv)

    if args.cmd == "describe":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY not set", file=sys.stderr)
            return 1
        return cmd_describe(args.description, args.output, verbose=args.verbose)

    if args.cmd == "from-spec":
        return cmd_describe_from_spec(args.spec_path, args.output)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
