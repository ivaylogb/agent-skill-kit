#!/usr/bin/env python3
"""Thin shell-out wrapper around the `funnel-researcher` CLI.

Validates inputs, then invokes `funnel-researcher diagnose`. No diagnostic
logic lives here — the installed CLI does the work. A clear error from this
wrapper is better than a cryptic failure from the CLI.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

CLI = "funnel-researcher"
INSTALL_HINT = (
    f"{CLI} is not on PATH. Install it from a clone of "
    "https://github.com/ivaylogb/funnel-researcher:\n"
    "  pip install -e .\n"
    "  export ANTHROPIC_API_KEY=sk-ant-..."
)


def _fail(msg: str, code: int = 2) -> int:
    print(f"[funnel-researcher skill] {msg}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="funnel-researcher-skill-runner",
        description="Shell-out to `funnel-researcher diagnose` for a funnel-step dropoff.",
    )
    p.add_argument("--funnel", required=True, type=Path,
                   help="Path to the funnel definition YAML.")
    p.add_argument("--dropoff", required=True, type=Path,
                   help="Path to the dropoff data JSON.")
    p.add_argument("--product", required=True, type=Path,
                   help="Path to the product artifact directory (docs, SDK, errors).")
    p.add_argument("--output-file", default=Path("./funnel-hypotheses.md"), type=Path,
                   help="Where to write the hypotheses report (default: ./funnel-hypotheses.md).")
    p.add_argument("--extra-file", action="append", default=[], type=Path,
                   help="Optional extra artifact file. Repeatable.")
    p.add_argument("--model", default=None, help="Claude model override.")
    p.add_argument("--max-tokens", default=None, type=int, help="Max output tokens.")
    args = p.parse_args(argv)

    if shutil.which(CLI) is None:
        return _fail(INSTALL_HINT)
    if not args.funnel.is_file():
        return _fail(f"funnel definition not found: {args.funnel}")
    if not args.dropoff.is_file():
        return _fail(f"dropoff data not found: {args.dropoff}")
    if not args.product.is_dir():
        return _fail(f"product directory not found: {args.product}")
    for extra in args.extra_file:
        if not extra.is_file():
            return _fail(f"extra file not found: {extra}")

    cmd = [
        CLI, "diagnose",
        "--funnel", str(args.funnel),
        "--dropoff", str(args.dropoff),
        "--product", str(args.product),
        "--output-file", str(args.output_file),
    ]
    for extra in args.extra_file:
        cmd += ["--extra-file", str(extra)]
    if args.model:
        cmd += ["--model", args.model]
    if args.max_tokens is not None:
        cmd += ["--max-tokens", str(args.max_tokens)]

    print(f"[funnel-researcher skill] running: {' '.join(cmd)}", file=sys.stderr)
    completed = subprocess.run(cmd)
    if completed.returncode != 0:
        return _fail(f"`{CLI} diagnose` exited {completed.returncode}", completed.returncode)

    print(str(args.output_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
