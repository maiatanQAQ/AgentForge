"""Patch forge.py (empty-cwd warning) and gen_launcher.py (forge flow)."""

# 1) forge.py: empty-cwd warning after chdir
p = "scripts/forge.py"
s = open(p, encoding="utf-8").read()
anchor = "    os.chdir(os.path.abspath(args.cwd))  # session workspace = --cwd\n"
add = anchor + (
    '    if not any(os.scandir(".")):\n'
    '        print("⚠️ 工作目录为空：executor 将按任务从零创建文件；'
    '若任务引用了已有文件，请确认目录是否正确。")\n'
)
if anchor in s and "工作目录为空" not in s:
    s = s.replace(anchor, add, 1)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("forge: warning added")
else:
    print("forge: already patched or anchor missing:", "工作目录为空" in s)

# 2) gen_launcher.py: PYTHONUTF8 + forge flow
g = "scripts/gen_launcher.py"
s = open(g, encoding="utf-8").read()
changed = []

old = "set \"PYTHONUTF8=1\"\nset \"PYTHONIOENCODING=cp936\""
new = "set \"PYTHONUTF8=1\""
if old in s:
    s = s.replace(old, new)
    changed.append("drop IOENCODING")

old = 'if "%CHOICE%"=="1" goto :demo'
new = 'if not defined CHOICE exit /b 0\nif "%CHOICE%"=="1" goto :demo'
if old in s and "if not defined CHOICE" not in s:
    s = s.replace(old, new)
    changed.append("EOF guard")

old = ('set "PROMPT=Fix the bug in calc.js in this workspace: the add() function '
       'currently subtracts instead of adding. Acceptance contract: running '
       "'node calc.js 2 3' prints exactly 5, and 'node calc.js -1 1' prints 0.\"")
if old in s:
    s = s.replace(old, 'set "TASK=' + old[len('set "PROMPT='):] )
    changed.append("demo TASK var")

old = ("echo 任务描述（单行，含验收契约）—— 在下一行输入后回车（引号/括号均可）:")
new = "echo 任务描述（单行，含可验证的验收契约，可含引号/括号）—— 在下一行输入后回车:"
if old in s:
    s = s.replace(old, new)
    changed.append("hint text")

old = ('"%PY%" scripts\\run_workflow.py workflows\\codex-plans-zcode-executes.yaml '
       '--cwd "%WORKDIR%" --prompt "%PROMPT%"')
new = ('set "TASKARG="\n'
       'if defined TASK set "TASKARG=--task \\"%TASK%\\""\n'
       '"%PY%" scripts\\forge.py --cwd "%WORKDIR%" %TASKARG%')
if old in s:
    s = s.replace(old, new)
    changed.append("forge run line")

open(g, "w", encoding="utf-8", newline="\n").write(s)
print("gen_launcher changes:", changed)
