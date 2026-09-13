#!/usr/bin/env python
"""Interactive gated runner: 任务 -> 计划 -> 人工确认 -> 执行 -> 验收.

Flow:
  1. read the task (from --task or interactively)
  2. PLAN    — planner-only workflow (codex, read-only); the session web UI
     opens automatically so you can watch live
  3. GATE    — show the plan; Enter approves, `r` re-plans, `x` cancels
  4. EXECUTE — three-role workflow with the approved plan prepended; the
     executor's session opens in the browser too, and the reviewer inside the
     workflow independently verifies against the same contract

Run with the Python interpreter omnigent is installed with (docs/setup.md).
"""

import argparse
import io
import os
import re
import sys
import webbrowser
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def load_dotenv(path: Path) -> None:
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


class _StreamCapture(io.TextIOBase):
    """Tee for redirect_stdout: mirrors output to the console, collects clean
    lines, and opens the session web UI once the session URL shows up."""

    def __init__(self, out):
        self.out = out
        self.lines = []
        self.url = None
        self._partial = ""
        self._url_opened = False

    def write(self, s):
        self.out.write(s)
        self.out.flush()
        self._partial += s
        while "\n" in self._partial:
            raw, self._partial = self._partial.split("\n", 1)
            clean = _ANSI.sub("", raw.replace("\r", "")).rstrip()
            if self.url is None and clean.startswith("Omnigent session:"):
                self.url = clean.split(":", 1)[1].strip()
                try:
                    webbrowser.open(self.url)
                except Exception:
                    pass
                self._url_opened = True
            if clean:
                self.lines.append(clean)
        return len(s)

    def flush(self):
        self.out.flush()


def run_phase(workflow: Path, prompt: str, label: str) -> tuple[str, str | None]:
    """Run one omnigent turn; returns (final text, session url)."""
    print(f"\n[{label}] 启动（浏览器将自动打开本阶段实时会话；本窗口同步输出）...\n", flush=True)
    cap = _StreamCapture(sys.stdout)
    with redirect_stdout(cap):
        import omnigent.chat as chat  # noqa: E402

        chat._PER_TURN_TIMEOUT_S = float(os.environ.get("AGENTFORGE_TURN_TIMEOUT", "1800"))  # noqa: SLF001
        chat.run_chat(target=str(workflow.resolve()), client_tools=None, prompt=prompt, log=True)
    plan = "\n".join(l for l in cap.lines if not l.startswith(("omnigent:", "Omnigent session:"))).strip()
    return plan, cap.url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True, help="Working directory for the run")
    parser.add_argument(
        "--workflow",
        default="workflows/codex-plans-zcode-executes.yaml",
        help="Three-role workflow (plan is prepended to the task)",
    )
    parser.add_argument(
        "--plan-workflow",
        default="workflows/planner-only.yaml",
        help="Plan-only workflow for phase 1",
    )
    parser.add_argument("--task", default=None, help="Task text; omit to type interactively")
    parser.add_argument(
        "--turn-timeout",
        type=float,
        default=float(os.environ.get("AGENTFORGE_TURN_TIMEOUT", "1800")),
    )
    args = parser.parse_args()

    os.environ["PYTHONUTF8"] = "1"       # workflow YAMLs are UTF-8 (child processes)

    load_dotenv(REPO_ROOT / ".env")
    workflow_path = (REPO_ROOT / args.workflow).resolve()
    plan_workflow_path = (REPO_ROOT / args.plan_workflow).resolve()
    os.chdir(os.path.abspath(args.cwd))
    print("⚠️ 工作目录为空：executor 将按任务从零创建文件；若任务引用了已有文件，请确认目录是否正确。")

    task = (args.task or input("请输入任务描述（单行，含可验证的验收契约）: ")).strip()
    if not task:
        raise SystemExit("empty task")

    while True:
        plan, _ = run_phase(plan_workflow_path, task, "1/3 规划")
        if not plan:
            raise SystemExit("planner returned an empty plan")
        print("\n" + "=" * 60)
        print(plan)
        print("=" * 60)

        gate = input("\n[关卡] 回车=按此计划执行 | r=修改任务重新规划 | x=取消: ").strip().lower()
        if gate == "x":
            print("已取消。")
            return
        if gate == "r":
            task = input("请输入修改后的任务描述: ").strip()
            if not task:
                raise SystemExit("empty task")
            continue
        break

    full_prompt = (
        f"{task}\n\n"
        "## 已获用户批准的执行计划（严格按此执行；如执行中发现计划与现状冲突，"
        "在报告中说明而不是偏离计划）\n\n"
        f"{plan}"
    )
    _, url = run_phase(workflow_path, full_prompt, "2/3 执行+验收")
    if url:
        print(f"\n会话回放: {url}")
    print("\n[3/3] 完成。请检查上方 reviewer 判定与工作目录中的实际改动。")


if __name__ == "__main__":
    main()
