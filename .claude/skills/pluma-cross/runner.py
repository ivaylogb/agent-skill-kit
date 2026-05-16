#!/usr/bin/env python3
"""Thin shell-out wrapper around the `pluma cross` CLI.

Validates inputs, then invokes `pluma cross`. The cross-match logic lives in
the CLI; this wrapper only checks that at least two complete tool input sets
are present and that every provided path exists. A clear error from this
wrapper is better than a cryptic failure from the CLI.

`pluma cross` runs each applicable sister tool through its input-hash cache.
Tools whose inputs were already run are cache hits (no model spend); only
non-cached tools spend tokens.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

CLI = "pluma"
INSTALL_HINT = (
    f"{CLI} is not on PATH. Install it from a clone of "
    "https://github.com/ivaylogb/pluma (plus the sister tool repos it "
    "orchestrates):\n"
    "  pip install -e .\n"
    "  export ANTHROPIC_API_KEY=sk-ant-..."
)

# Each tool needs BOTH of its flags present to count as a complete input set.
# pluma cross requires inputs for >= 2 tools.
TOOL_INPUT_SETS = {
    "funnel-researcher": ("funnel", "dropoff"),
    "integration-watcher": ("traces", "cohort"),
    "agent-researcher": ("eval_result", "target_agent"),
}


def _fail(msg: str, code: int = 2) -> int:
    print(f"[pluma-cross skill] {msg}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="pluma-cross-skill-runner",
        description="Shell-out to `pluma cross` for a cross-tool convergence report.",
    )
    p.add_argument("--product", required=True, type=Path,
                   help="Product artifact directory shared by every tool.")
    p.add_argument("--output-file", default=Path("./pluma-cross.md"), type=Path,
                   help="Where to write the cross-tool report (default: ./pluma-cross.md).")
    # funnel-researcher inputs
    p.add_argument("--funnel", default=None, type=Path, help="Funnel definition YAML.")
    p.add_argument("--dropoff", default=None, type=Path, help="Dropoff data JSON.")
    # integration-watcher inputs
    p.add_argument("--traces", default=None, type=Path, help="Trace stream JSONL.")
    p.add_argument("--cohort", default=None, type=Path, help="Cohort definition YAML.")
    # agent-researcher inputs
    p.add_argument("--eval-result", default=None, type=Path, help="Eval result JSON.")
    p.add_argument("--target-agent", default=None, type=Path, help="Target agent directory.")
    # passthrough
    p.add_argument("--model", default=None, help="Claude model override.")
    p.add_argument("--max-tokens", default=None, type=int, help="Max output tokens.")
    p.add_argument("--extra-file", action="append", default=[], type=Path,
                   help="Optional extra artifact file. Repeatable.")
    p.add_argument("--no-cache", action="store_true",
                   help="Bypass the input-hash cache (every tool re-runs and spends).")
    p.add_argument("--force", action="store_true",
                   help="Re-run even on a cache hit.")
    args = p.parse_args(argv)

    if shutil.which(CLI) is None:
        return _fail(INSTALL_HINT)
    if not args.product.is_dir():
        return _fail(f"product directory not found: {args.product}")

    # Validate every provided path, and count complete tool input sets.
    values = vars(args)
    file_inputs = ("funnel", "dropoff", "traces", "cohort", "eval_result")
    for name in file_inputs:
        val = values[name]
        if val is not None and not Path(val).is_file():
            return _fail(f"{name.replace('_', '-')} file not found: {val}")
    if args.target_agent is not None and not args.target_agent.is_dir():
        return _fail(f"target-agent directory not found: {args.target_agent}")
    for extra in args.extra_file:
        if not extra.is_file():
            return _fail(f"extra file not found: {extra}")

    complete = [
        tool for tool, (a, b) in TOOL_INPUT_SETS.items()
        if values[a] is not None and values[b] is not None
    ]
    if len(complete) < 2:
        return _fail(
            "pluma cross needs complete inputs for at least two tools "
            "(funnel-researcher: --funnel+--dropoff; integration-watcher: "
            "--traces+--cohort; agent-researcher: --eval-result+--target-agent). "
            f"Got: {complete or 'none'}."
        )

    cmd = [CLI, "cross",
           "--product", str(args.product),
           "--output-file", str(args.output_file)]
    if args.funnel:
        cmd += ["--funnel", str(args.funnel)]
    if args.dropoff:
        cmd += ["--dropoff", str(args.dropoff)]
    if args.traces:
        cmd += ["--traces", str(args.traces)]
    if args.cohort:
        cmd += ["--cohort", str(args.cohort)]
    if args.eval_result:
        cmd += ["--eval-result", str(args.eval_result)]
    if args.target_agent:
        cmd += ["--target-agent", str(args.target_agent)]
    for extra in args.extra_file:
        cmd += ["--extra-file", str(extra)]
    if args.model:
        cmd += ["--model", args.model]
    if args.max_tokens is not None:
        cmd += ["--max-tokens", str(args.max_tokens)]
    if args.no_cache:
        cmd += ["--no-cache"]
    if args.force:
        cmd += ["--force"]

    print(f"[pluma-cross skill] running ({len(complete)} tools: "
          f"{', '.join(complete)}): {' '.join(cmd)}", file=sys.stderr)
    completed = subprocess.run(cmd)
    if completed.returncode != 0:
        return _fail(f"`{CLI} cross` exited {completed.returncode}", completed.returncode)

    print(str(args.output_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
