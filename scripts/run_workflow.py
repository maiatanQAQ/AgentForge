#!/usr/bin/env python
"""Generic one-shot driver for AgentForge workflows on omnigent.

Usage (run with the Python interpreter omnigent is installed with, e.g. the
`uv tool` venv — see docs/setup.md):

    python scripts/run_workflow.py <workflow.yaml> \
        --cwd <workspace dir> \
        --prompt "the task for the planner"

What it does:

1. Loads `.env` from the repository root (KEY=VALUE lines) into the process
   environment — before any omnigent process is spawned.
2. Puts `adapters/zcode-acp/` on PYTHONPATH so its `sitecustomize.py` runs in
   every omnigent subprocess (background-title workaround).
3. Raises omnigent's one-shot per-turn timeout (the CLI hard-codes 120s,
   which is too short for multi-role workflows where planner, executor and
   reviewer all run inside a single turn).
4. Calls the official `omnigent.chat.run_chat` entry — one-shot, exits when
   the turn finishes.
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    """Minimal KEY=VALUE loader (no external dependency)."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", help="Path to the workflow YAML")
    parser.add_argument("--cwd", default=".", help="Working directory for the run (default: .)")
    parser.add_argument("--prompt", default=None, help="Task text sent to the planner; omit to type it interactively")
    parser.add_argument(
        "--turn-timeout",
        type=float,
        default=float(os.environ.get("AGENTFORGE_TURN_TIMEOUT", "1800")),
        help="Per-turn timeout in seconds (default: 1800 or AGENTFORGE_TURN_TIMEOUT)",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    # sitecustomize.py (background-title workaround) must be importable by
    # every omnigent subprocess; PYTHONPATH reaches server, daemon and runner.
    sitecustomize_dir = str(REPO_ROOT / "adapters" / "zcode-acp")
    existing = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = (
        f"{sitecustomize_dir}{os.pathsep}{existing}" if existing else sitecustomize_dir
    )

    workflow_path = Path(args.workflow).resolve()  # resolve BEFORE chdir
    os.chdir(os.path.abspath(args.cwd))  # session workspace = --cwd
    prompt = args.prompt
    if prompt is None:
        # read interactively: no cmd.exe involvement, so quotes/parens/& are safe
        prompt = input("请输入任务描述（单行，含可验证的验收契约）: ").strip()
        if not prompt:
            raise SystemExit("empty task")

    os.environ.setdefault("PYTHONUTF8", "1")  # workflow YAMLs are UTF-8

    import omnigent.chat as chat  # noqa: E402  (import after .env)

    chat._PER_TURN_TIMEOUT_S = args.turn_timeout  # noqa: SLF001 — documented patch point

    chat.run_chat(
        target=str(workflow_path),
        client_tools=None,
        prompt=prompt,
        log=True,
    )


if __name__ == "__main__":
    main()
