# Changelog

All notable changes to AgentForge are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning is
 SemVer-flavored (`vMAJOR.MINOR.PATCH-PRERELEASE`).

## v0.1.1 — 2026-09-13

### Fixed

- `scripts/run_workflow.py`: the `--cwd` argument is now applied — the session
  workspace (and therefore the executor's working directory) is the directory
  given on the command line; previously the argument was parsed but ignored,
  so the executor ran in the repository root.
- `examples/phase2-demo`: the `calc.js.buggy` fixture shipped in v0.1.0-alpha
  accidentally contained the fixed version; it is again the actual buggy input.

### Added

- `adapters/zcode-acp/package.json` + lockfile — pinning the
  `zcode-acp-server` bridge for a deterministic local install
  (`npm install` inside `adapters/zcode-acp/`), which the adapter resolves
  via `require.resolve` when no global install is visible.

## v0.1.0-alpha — 2026-09-13

First public pre-release. Everything below was validated end-to-end on
Windows 11; see `docs/results.md` for outcomes and evidence.

### Added

- **planner / worker / reviewer workflow** — a three-role omnigent workflow
  where role separation is enforced by the orchestrator (three isolated
  sessions with independent harnesses), including the one-shot driver
  `scripts/run_workflow.py` (.env loading, per-turn timeout patch).
- **omnigent orchestration integration** — reference configuration for
  sessions, sub-agent delegation and harness selection
  (`config.example.yaml`, `docs/setup.md`).
- **ACP executor adapter** — `adapters/zcode-acp/zcode-acp-adapter.mjs`
  connects any ACP-compatible agent to the executor role; resolves the
  `zcode-acp-server` bridge and fixes its Windows Node discovery at the
  environment level. `adapters/zcode-acp/sitecustomize.py` disables
  omnigent's background-title worker in subprocesses (it 401s and poisons
  turns against non-OpenAI providers).
- **ZCode executor example** — `examples/phase2-demo`: Codex plans, ZCode
  edits code through the ACP bridge, Codex reviews (`最终判定：PASS`).
- **Windows validation** — the whole pipeline runs natively on Windows 11
  (no WSL/tmux); platform pitfalls and their config-level fixes are
  documented in `docs/architecture.md` and `docs/setup.md`.
- **Phase 2 ACP validation** — recorded evidence that the executor role is a
  real ZCode backend (process chain, `harness=acp` mapping, ZCode-side
  model-IO transcripts).
- **Phase 3 real repository validation** — the workflow was validated by
  applying a bug fix to a local checkout of the third-party `zcode-acp`
  repository: root-cause confirmation, a 5-line fix plus 7 regression tests,
  independent typecheck/test re-run and falsification check by the reviewer,
  compared against a pre-recorded Windows baseline
  (`examples/phase3-demo/`).

### Known limitations

- The desktop subscription endpoint of ZCode cannot be driven headlessly
  (captcha-verified desktop sessions); use a standard API endpoint.
- Only the Codex/ZCode pairing is validated; other CLIs are expected to work
  through omnigent's harness registry or an ACP bridge but are unvalidated.
- macOS/Linux are expected to work (the ACP bridge's Node discovery is
  Unix-friendly there) but were not exercised in this release.
