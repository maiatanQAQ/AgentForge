# AgentForge

**Version:** v0.1.1 · **License:** Apache-2.0

AgentForge is a general multi-agent orchestration framework built on
[omnigent](https://github.com/omnigent-ai/omnigent) (Apache-2.0). It runs a
**planner → executor → reviewer** workflow in which the three roles are filled
by pluggable coding-agent CLIs, with role separation enforced by the
orchestrator rather than by prompt discipline alone:

```
                        ┌────────────────────────┐
   task (one prompt) →  │  Planner               │  explores the workspace,
                        │  "参谋 / tech lead"     │  writes an acceptance contract
                        └───────────┬────────────┘
                                    │ delegates via omnigent sub-agent tools
                                    ▼
                        ┌────────────────────────┐
                        │  Executor              │  modifies files, runs the
                        │  "执行官"               │  verification commands
                        └───────────┬────────────┘
                                    │ hands back a change report
                                    ▼
                        ┌────────────────────────┐
                        │ Reviewer               │  re-runs verification,
                        │  independent of worker │  verdict: PASS / FAIL
                        └────────────────────────┘
```

The configuration **validated and shipped in this release** pairs the
**Codex CLI** (planner and reviewer) with the **ZCode CLI** (executor, via the
Agent Client Protocol) — see `docs/results.md`. These are examples of the
pluggable role system, not a vendor lock-in: any coding-agent CLI with an
omnigent harness or an ACP bridge can fill any role.

The three roles run as three isolated omnigent sessions with three different
harnesses (`codex`, `acp:zcode`, `codex`), so role separation is enforced by
the orchestrator — the executor physically cannot be "the same agent pretending".

- **Codex CLI** (OpenAI) — planner and reviewer *in the validated
  configuration*. Auth, tool plumbing and the one-shot driver integration are
  omnigent-native.
- **ZCode CLI** (Z.AI) — executor *in the validated configuration*, connected
  through the open
  [Agent Client Protocol](https://agentclientprotocol.com/) via the community
  [zcode-acp-server](https://github.com/william0wang/zcode-acp) bridge and a
  small adapter in this repo (`adapters/zcode-acp/`).
- Any model behind those CLIs works; the verified runs used third-party
  endpoints (DeepSeek's Anthropic-compatible API) — see `docs/results.md`.
- Other CLIs (Gemini CLI, Claude Code, opencode, …) can fill the same roles
  through omnigent's harness registry or an ACP bridge; they are unvalidated
  in this release and therefore not shipped as examples.

## Repository layout

```
AgentForge/
├── README.md                     this file
├── LICENSE                       Apache-2.0
├── .env.example                  environment template (copy to .env)
├── config.example.yaml           omnigent config additions (merge into ~/.omnigent/config.yaml)
├── docs/
│   ├── architecture.md           how the pieces fit, config layers, failure modes
│   ├── setup.md                  step-by-step environment setup (Windows-first)
│   └── results.md                verified outcomes of the validation phases
├── adapters/zcode-acp/
│   ├── zcode-acp-adapter.mjs     omnigent `acp.agents` adapter for the ACP bridge
│   └── sitecustomize.py          subprocess patch: disables the background-title worker
├── workflows/
│   ├── planner-only.yaml                   plan-only pass (human gate input)
│   ├── plan-execute-review.yaml            baseline: codex / codex / codex
│   ├── codex-plans-zcode-executes.yaml     ZCode executor demo
│   └── zcode-executor-real-task.yaml       real-repo bug fix task
├── examples/
│   ├── phase2-demo/              ZCode-as-executor demo (calc.js bug fix)
│   └── phase3-demo/              real-repo task with baseline comparison
├── scripts/
│   ├── forge.py                  interactive gated runner (plan -> 确认 -> execute)
│   └── run_workflow.py           one-shot driver (.env, timeout patch)
└── tests/
    └── acp_smoke.mjs             standalone ACP handshake smoke test
```

## Prerequisites

- **Node.js ≥ 22** (ZCode CLI and the ACP bridge need `node:sqlite`)
- **Python 3.12** and [uv](https://docs.astral.sh/uv/) (omnigent is installed as a `uv tool`)
- **omnigent** (`uv tool install omnigent`, or from a local clone)
- **Codex CLI** installed and authenticated (desktop-app bundle or npm package)
- **ZCode** desktop app installed and logged in, plus the ACP bridge:
  `npm install -g zcode-acp-server`
- Works on **Windows natively** (verified on Windows 11); macOS/Linux notes in
  `docs/setup.md`.

## Quick start

```bash
# 0) one-time environment setup — follow docs/setup.md, in particular:
#    - merge config.example.yaml blocks into ~/.omnigent/config.yaml
#    - create ~/.zcode/cli/config.json (ZCode CLI model provider)
#    - cp .env.example .env   (fill OMNIGENT_CODEX_PATH if codex is not on PATH)

# 1) smoke-test the ACP bridge alone
node tests/acp_smoke.mjs <workspace-dir> "Reply with exactly: ZCODE-OK"

# 2) run the ZCode-executor demo (Phase 2)
python scripts/run_workflow.py workflows/codex-plans-zcode-executes.yaml \
    --cwd examples/phase2-demo/workspace \
    --prompt "Fix the bug in calc.js in this workspace: the add() function currently
subtracts instead of adding. Acceptance contract: running 'node calc.js 2 3'
prints exactly 5, and 'node calc.js -1 1' prints 0."

# 3) run the real-repo task (Phase 3) — see examples/phase3-demo/README.md
```

A successful run prints the planner's contract, the executor's change report
and ends with the reviewer's `最终判定：PASS`.

## Windows support

Verified end-to-end on Windows 11 (Git Bash + PowerShell):

- omnigent's one-shot path, `codex` harness and the `acp:zcode` harness all
  run natively; no WSL or tmux required.
- Known Windows-specific pitfalls and their config-level fixes are documented
  in `docs/setup.md` (codex CLI not on PATH, non-OpenAI provider 401s, the
  ACP bridge's empty Node-candidate list, ZCode's model-config split between
  two config files).
- The omnigent background-title worker is disabled by
  `adapters/zcode-acp/sitecustomize.py` (it 401s against non-OpenAI backends
  and poisons turns) — see `docs/architecture.md`.

## Results

See `docs/results.md` for the recorded validation phases: ACP integration
(Phase 2) and a validation run that applied a real bug fix to a local checkout
of a third-party repository (Phase 3), including the exact evidence that the
executor role was genuinely ZCode.

## License

Apache-2.0 — see [LICENSE](LICENSE). Upstream projects keep their own licenses:
omnigent and zcode-acp (Apache-2.0), Codex CLI and ZCode are proprietary tools
invoked as local processes.
