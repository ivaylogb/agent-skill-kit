#!/usr/bin/env python3
"""Thin shell-out wrapper around the `agent-researcher` CLI.

Validates inputs, then invokes `agent-researcher diagnose`. No diagnostic
logic lives here — the installed CLI does the work. A clear error from this
wrapper is better than a cryptic failure from the CLI.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

CLI = "agent-researcher"
INSTALL_HINT = (
    f"{CLI} is not on PATH. Install it from a clone of "
    "https://github.com/ivaylogb/agent-researcher:\n"
    "  pip install -e .\n"
    "  export ANTHROPIC_API_KEY=sk-ant-..."
)


def _fail(msg: str, code: int = 2) -> int:
    print(f"[agent-researcher skill] {msg}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="agent-researcher-skill-runner",
        description="Shell-out to `agent-researcher diagnose` for a failing eval scenario.",
    )
    p.add_argument("--target-agent", required=True, type=Path,
                   help="Path to the target agent's directory.")
    p.add_argument("--eval-result", required=True, type=Path,
                   help="Path to the eval result JSON.")
    p.add_argument("--output-file", default=Path("./hypotheses.md"), type=Path,
                   help="Where to write the hypotheses report (default: ./hypotheses.md).")
    p.add_argument("--scenario-id", default=None,
                   help="Specific scenario_id to investigate. Defaults to the first failure.")
    p.add_argument("--scenario-input", default=None,
                   help="The user message for the failing scenario.")
    p.add_argument("--scenario-input-file", default=None, type=Path,
                   help="File containing the user message (alternative to --scenario-input).")
    p.add_argument("--model", default=None, help="Claude model override.")
    args = p.parse_args(argv)

    if shutil.which(CLI) is None:
        return _fail(INSTALL_HINT)
    if not args.target_agent.is_dir():
        return _fail(f"target agent directory not found: {args.target_agent}")
    if not args.eval_result.is_file():
        return _fail(f"eval result JSON not found: {args.eval_result}")
    if args.scenario_input_file is not None and not args.scenario_input_file.is_file():
        return _fail(f"scenario input file not found: {args.scenario_input_file}")

    cmd = [
        CLI, "diagnose",
        "--target-agent", str(args.target_agent),
        "--eval-result", str(args.eval_result),
        "--output-file", str(args.output_file),
    ]
    if args.scenario_id:
        cmd += ["--scenario-id", args.scenario_id]
    if args.scenario_input:
        cmd += ["--scenario-input", args.scenario_input]
    if args.scenario_input_file:
        cmd += ["--scenario-input-file", str(args.scenario_input_file)]
    if args.model:
        cmd += ["--model", args.model]

    print(f"[agent-researcher skill] running: {' '.join(cmd)}", file=sys.stderr)
    completed = subprocess.run(cmd)
    if completed.returncode != 0:
        return _fail(f"`{CLI} diagnose` exited {completed.returncode}", completed.returncode)

    print(str(args.output_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
