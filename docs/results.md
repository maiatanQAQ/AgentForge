# Verified results

All runs were executed on Windows 11 (Git Bash), omnigent 0.14.0.dev0 from a
local clone, Codex CLI 0.153.4, ZCode CLI 0.16.5, zcode-acp-server 0.37.1.
Full logs are intentionally **not** part of this repository; this page records
the outcomes and the evidence locations. Dates are 2026-09-13.

## Phase 1 — orchestration baseline (codex / codex / codex)

- Workflow `workflows/plan-execute-review.yaml`: planner, worker and reviewer
  all on the codex harness.
- Task: create a classic FizzBuzz script; the reviewer re-ran it and concluded
  `最终判定：PASS`; the produced file passed an independent re-run outside the
  agent loop (15 lines, line 6 `Fizz`, line 10 `Buzz`, line 15 `FizzBuzz`).
- Purpose: establish the omnigent one-shot driver (timeout patch) before
  introducing a second vendor.

## Phase 2 — ZCode as executor via ACP

**Result: success.** `harness: acp:zcode` registered through the ACP bridge;
the executor role was served by a real ZCode backend process.

- Smoke: standalone ACP handshake (`tests/acp_smoke.mjs`) returned
  `ACP_SMOKE_OK` with a real streamed reply and usage accounting
  (`stopReason: "end_turn"`).
- Demo (`examples/phase2-demo`): planner (codex) wrote the acceptance
  contract, executor (ZCode) changed `calc.js` line 3 from `return a - b` to
  `return a + b` and verified with real command output, reviewer (codex)
  re-ran both acceptance commands independently and ended with
  `最终判定：PASS`. Driver exit code 0.
- Evidence that the executor was genuinely ZCode, not the codex harness:
  omnigent runner log maps the worker conversation to `harness=acp` while
  planner/reviewer map to `harness=codex`; the worker's model-IO transcript
  exists only on the ZCode side
  (`~/.zcode/cli/rollout/model-io-sess_*.jsonl`, with
  `"modelRef": {"providerId": "...", "modelId": "..."}` and ZCode-native tool
  call records), and the process chain
  (runner → adapter → bridge → `zcode.cjs app-server`) contains no codex
  process.

Integration issues found and fixed at config/adapter level (details in
`docs/architecture.md`): bridge Node-candidate gap on Windows (EFTYPE), the
ZCode CLI's mandatory headless model config, provider registry push semantics
(`provider_not_configured` misclassified as network errors), registry-order
default-model resolution, and the background-title worker 401 that poisoned
turns.

## Phase 3 — real development task on a third-party repository

**Result: success.** The AgentForge workflow was validated by applying a fix
to a **local checkout** of the
[zcode-acp](https://github.com/william0wang/zcode-acp) repository (v0.37.1,
Apache-2.0): the Windows node-resolution defect that the bridge itself hit
during Phase 2 (spawn EFTYPE). The change exists only in that local checkout —
nothing was merged upstream; the patch is included below as evidence of what
the workflow produced.

- Task framing: planner confirmed the root cause in `src/backend/resolve.ts`
  and issued a 7-point acceptance contract; the worker (ZCode) implemented the
  fix and wrote the tests; the reviewer (codex) independently re-ran the tests
  and typecheck, reviewed the diff, compared the full-suite failure set
  against a pre-recorded Windows baseline (67 pre-existing platform failures
  in 13 suites — unchanged by the fix), and performed a falsification check
  (removing the fix makes the new Windows regression test fail with the old
  spawn argv).
- Verdict: `APPROVED / PASS`. Wall time ≈ 7.5 minutes for the whole
  three-role turn.
- Core patch (excerpt, attributed to the AgentForge pipeline run; the
  upstream repo is Apache-2.0):

```diff
--- a/src/backend/resolve.ts
+++ b/src/backend/resolve.ts
@@ -53,6 +53,11 @@ function candidateNodeBinaries(): string[] {
   const cands: string[] = [];
   const envNode = process.env.ZCODE_NODE;
   if (envNode) cands.push(envNode);
+  // The interpreter running this bridge. On Windows there is no Unix `which`
+  // and none of the hardcoded Unix / Zed-bundle paths below exist, so without
+  // this candidate the bundled `.cjs` had no sqlite-capable Node to launch
+  // with and spawn died with EFTYPE. The sqlite gate still applies.
+  if (process.execPath) cands.push(process.execPath);
   cands.push("/opt/homebrew/bin/node", "/usr/local/bin/node");
```

- Plus a new `tests/resolve.test.ts` (7 cases: win32 repro, sqlite gate,
  `ZCODE_NODE` precedence, non-JS passthrough, Unix non-regression).

## Recorded limitations

- The desktop subscription endpoint (`zcode.z.ai/.../zcode-plan/anthropic`)
  requires a captcha-verified desktop session; headless runs must use a
  standard Anthropic/OpenAI-compatible endpoint (see docs/setup.md §4).
- The reviewer's macOS coverage in Phase 3 was simulated in tests, not
  executed on a real macOS host (stated in the reviewer's own verdict).
- omnigent's one-shot per-turn timeout is a hard-coded constant; AgentForge
  patches it in `scripts/run_workflow.py` (documented, no core changes).
