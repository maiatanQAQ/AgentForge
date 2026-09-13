# Architecture

## Components

| Component | Role | Source |
| --- | --- | --- |
| omnigent | Orchestrator: sessions, sub-agent tools, harness abstraction | upstream (Apache-2.0) |
| Codex CLI (`codex` harness) | Planner and Reviewer roles | OpenAI (proprietary, invoked locally) |
| ZCode CLI (`acp:zcode` harness) | Executor role | Z.AI (proprietary, invoked locally) |
| zcode-acp-server | ACP bridge: translates omnigent's ACP client traffic to the ZCode `app-server` stdio protocol | community (Apache-2.0) |
| `adapters/zcode-acp/` | Environment adapter (Windows fixes) between omnigent and the bridge | this repo |
| `scripts/run_workflow.py` | One-shot driver: `.env`, turn-timeout patch, `run_chat` | this repo |

## Data flow

```
scripts/run_workflow.py
  ├── loads .env → process env (OMNIGENT_CODEX_PATH, ...)
  ├── PYTHONPATH=adapters/zcode-acp  → sitecustomize.py in every child python
  │     (disables omnigent's background-title worker — see failure modes)
  ├── patches omnigent.chat._PER_TURN_TIMEOUT_S (120s → configurable)
  └── omnigent.chat.run_chat(workflow.yaml, prompt)
        │  spawns local server + daemon + runner
        ├─ session [planner]  harness=codex   → codex.exe app-server (protocol)
        │     planner calls sub-agent tool "worker"
        ├─ session [worker]   harness=acp:zcode
        │     acp_executor → spawns adapters/zcode-acp/zcode-acp-adapter.mjs
        │       → node zcode-acp-server/dist/index.js   (ACP server)
        │         → node zcode.cjs app-server --stdio   (ZCode backend)
        │     ACP: initialize → session/new(cwd) → session/prompt
        │     ZCode edits files in the session cwd (yolo mode)
        │     backend provider registry pushed from ~/.zcode/v2/config.json
        └─ session [reviewer] harness=codex   → codex.exe app-server
              re-runs verification commands, issues PASS/FAIL
```

## Configuration layers (important!)

The trickiest part of this architecture is that **three different config
files are involved, and mixing them up produces the exact failures listed
below**.

### codex side

| File | Used by | Content |
| --- | --- | --- |
| `~/.codex/config.toml` | codex CLI + omnigent's per-session temp CODEX_HOME (copied verbatim) | `model_provider`, `[model_providers.*]` tables, `model_catalog_json` |
| `~/.omnigent/config.yaml` | omnigent provider system | `providers.*` (kind `cli-config` pins a codex provider table by name) |

Key rule: omnigent treats an API-key codex login as an "OpenAI subscription"
and forces `-c model_provider="openai"` **unless** a `cli-config` provider is
registered and marked default. With a non-OpenAI key behind `~/.codex/auth.json`
this is the difference between working and instant 401s.

### zcode side

| File | Used by | Content |
| --- | --- | --- |
| `~/.zcode/cli/config.json` | `zcode -p` and the backend's default model reference | `{"model": "provider/model"}` + `provider` registry |
| `~/.zcode/v2/config.json` | desktop app + the ACP bridge's provider-registry push | `provider.*` entries (kind/options.baseURL/options.apiKey/models) |

Key rules (verified experimentally, see `docs/results.md`):

1. The V4 backend does **not** auto-load providers from any config file. The
   bridge pushes a `workspace/updateProviderRegistry` payload built from the
   **v2** config after `session/create`. Without a pushed entry the turn fails
   with `provider_not_configured`, misclassified as a network error.
2. The backend resolves the session's **default model against the first
   provider in the pushed registry** — i.e. the first `provider.*` key in the
   v2 config. Put your intended executor provider **first**.
3. `~/.zcode/cli/config.json` is what makes the CLI's own headless mode
   (`zcode -p`) work at all; it is read by the CLI but not by the registry.

## Role isolation

- The planner/reviewer run on the `codex` harness; the executor runs on the
  `acp:zcode` harness. Each omnigent sub-agent session is a separate backend
  process (`harness=codex` / `harness=acp` in the runner log), so the
  executor's work is attributable to ZCode by construction.
- The planner prompt forbids file edits; the reviewer prompt forbids edits and
  requires re-running verification. Enforcement is prompt-level by design —
  the workflow relies on independent re-execution (the reviewer re-runs the
  acceptance commands itself) rather than on permission systems.

## Failure modes and their (config-level) fixes

| Symptom | Root cause | Fix |
| --- | --- | --- |
| `spawn EFTYPE` in the ACP bridge | Bridge's Node-candidate list is empty on Windows (Unix `which`, macOS Zed paths) | adapter sets `ZCODE_NODE` to its own interpreter |
| `Model config is missing` from `zcode -p` | `~/.zcode/cli/config.json` absent | create it (template in docs/setup.md) |
| Turn fails: `provider_not_configured` (logged as network error after retries) | provider registry not pushed / provider absent from **v2** config | add the provider entry to `~/.zcode/v2/config.json` |
| Wrong model used by the worker | registry order: backend defaults to the **first** pushed provider | put the intended executor provider first in v2 `provider` keys |
| 401 `Incorrect API key provided ... api.openai.com` on codex roles | omnigent forces `-c model_provider="openai"` for API-key logins | register a `cli-config` provider in `~/.omnigent/config.yaml` |
| Turn dies after ~2 min on non-OpenAI codex providers | background-title worker thread 401s and poisons the turn | `sitecustomize.py` disables it (loaded via PYTHONPATH) |
| One-shot run raises `Turn did not complete within 120s` | CLI hard-codes a per-turn timeout | `run_workflow.py` patches it (default 1800s) |
| `zcode.z.ai/...` plan endpoint returns `captcha verify failed` | vendor anti-abuse tied to the desktop session | use a standard API endpoint (Anthropic-compatible) instead |

None of these require modifying omnigent, the bridge, or ZCode — every fix is
config or adapter level, which is the design constraint of this repo.
