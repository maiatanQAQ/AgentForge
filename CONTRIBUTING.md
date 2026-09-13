# Contributing

Thanks for considering a contribution. AgentForge is intentionally small:
workflow examples, adapters and docs around the omnigent orchestrator. Keep
changes in that spirit.

## Filing issues

Include:

1. What you ran (workflow file, command line, `--prompt`).
2. Environment: OS, Node/Python versions, omnigent version, which CLIs fill
   which roles.
3. The smallest log excerpt that shows the failure — **redact API keys,
   tokens and personal paths first**.

## Pull requests

- One topic per PR; keep diffs minimal.
- Workflows live in `workflows/`, adapters in `adapters/`, drivers in
  `scripts/`. Do not bundle unrelated refactors.
- This repo contains **no upstream code** — do not commit vendored copies of
  omnigent, zcode-acp, or any agent CLI; reference them in docs instead.
- Never commit secrets: `.env`, `chat.db`, `auth.json`, logs, rollouts are
  gitignored; double-check diffs for paths and keys before opening the PR.
- Docs changes are as welcome as code changes — if you hit a failure mode
  not covered by `docs/architecture.md`, document it.

## Running the examples

```bash
# 1) environment: follow docs/setup.md (omnigent, Codex auth, ZCode + bridge)

# 2) smoke the ACP bridge
node tests/acp_smoke.mjs <workspace-dir> "Reply with exactly: ZCODE-OK"

# 3) run a workflow
python scripts/run_workflow.py workflows/codex-plans-zcode-executes.yaml \
    --cwd examples/phase2-demo/workspace \
    --prompt "Fix the bug in calc.js in this workspace: the add() function currently
subtracts instead of adding. Acceptance contract: running 'node calc.js 2 3'
prints exactly 5, and 'node calc.js -1 1' prints 0."
```

A healthy run ends with the reviewer's `最终判定：PASS` and exit code 0.
