# Phase 2 demo — ZCode as executor

Three-role run: **planner (codex)** → **executor (ZCode via `acp:zcode`)** →
**reviewer (codex)**.

## Task

The workspace contains `workspace/calc.js` with a deliberately broken `add()`
function (it subtracts). The planner writes the acceptance contract, the
executor fixes the file, the reviewer re-runs the acceptance commands.

The buggy fixture is provided as `workspace/calc.js.buggy` — copy it to
`workspace/calc.js` to reset the demo.

## Run

```bash
python scripts/run_workflow.py workflows/codex-plans-zcode-executes.yaml \
    --cwd examples/phase2-demo/workspace \
    --prompt "Fix the bug in calc.js in this workspace: the add() function currently
subtracts instead of adding. Acceptance contract: running 'node calc.js 2 3'
prints exactly 5, and 'node calc.js -1 1' prints 0."
```

## Expected outcome (verified run, see docs/results.md)

- The executor report names the changed line (`calc.js:3`,
  `return a - b` → `return a + b`) and includes the real verification output
  (`5` and `0`).
- The reviewer re-runs both commands independently and ends with
  `最终判定：PASS`.
- Driver exit code 0.
