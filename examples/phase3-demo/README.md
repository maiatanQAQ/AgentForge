# Phase 3 demo — validating the workflow with a fix to a third-party repo

Three-role run against a **local checkout** of
[zcode-acp](https://github.com/william0wang/zcode-acp) (v0.37.1, Apache-2.0):
**planner (codex)** → **executor (ZCode via `acp:zcode`)** → **reviewer
(codex)**. The resulting patch lives in the local checkout only — nothing is
merged upstream; it is recorded here as evidence of what the workflow produced.

## Task

Fix the Windows node-resolution defect in `src/backend/resolve.ts`: on Windows
`candidateNodeBinaries()` returns an empty list (the Unix `which` probe and the
macOS Zed-bundle paths all miss), so `resolveZcodeCommand()` spawns the bundled
`zcode.cjs` raw and the process dies with `EFTYPE`. The fix must work without
the `ZCODE_NODE` workaround, must include regression tests, and must not grow
the repository's pre-existing Windows test-failure set.

## Baseline discipline

Before the run, the pristine clone's full vitest suite was recorded on this
machine: **67 failed / 1092 passed** tests across **13 platform-specific
suites** (none related to the file being fixed). The failing-suite list ships
as `baseline-failed-files.txt`; the reviewer's contract is "new tests pass +
typecheck passes + failing set does not grow".

## Run

```bash
git clone https://github.com/william0wang/zcode-acp.git   # into a scratch dir
cd zcode-acp && npm install
npx vitest run > ../baseline-vitest-full.txt              # record baseline

python scripts/run_workflow.py workflows/zcode-executor-real-task.yaml \
    --cwd <path-to-your-clone> \
    --prompt "Fix the Windows node-resolution defect in this repository as
described in your instructions."
```

## Verified outcome (see docs/results.md)

- `src/backend/resolve.ts`: +5 lines — `process.execPath` added as a Node
  candidate (sqlite gate unchanged).
- `tests/resolve.test.ts`: new, 7 cases (win32 repro, gate, precedence,
  passthrough, Unix non-regression); 7/7 pass; `tsc --noEmit` clean.
- Full-suite failing set identical to the baseline.
- Reviewer verdict: `APPROVED / PASS`, including a falsification check
  (reverting the fix makes the new Windows test fail with the old argv).
- Wall time ≈ 7.5 minutes for the entire three-role turn.
