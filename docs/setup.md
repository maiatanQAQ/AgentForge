# Setup (Windows-first)

Verified on Windows 11 + Git Bash + PowerShell. macOS/Linux notes at the end.

## 1. Base toolchain

- Node.js ≥ 22 (`node:sqlite` is required by the ZCode CLI and the bridge)
- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- git

## 2. omnigent

```bash
uv tool install omnigent          # from PyPI
# or from a local clone:
# uv tool install /path/to/omnigent
omnigent --version
```

Run omnigent with the Python interpreter of its tool venv (see
`uv tool dir`), or make sure `omnigent`/`python` resolve consistently.

## 3. Codex CLI (planner / reviewer)

The Codex desktop app bundles its CLI but does not add it to PATH. Either:

- put a shim named `codex` on PATH that calls the bundled binary
  (`%LOCALAPPDATA%\OpenAI\Codex\bin\<build-hash>\codex.exe`), **or**
- set `OMNIGENT_CODEX_PATH` in `.env` (see `.env.example`) to the same path.

Authenticate once (`codex login` or the desktop app). Verify:

```bash
codex --version
codex login status
```

### Non-OpenAI model routing (optional)

If your codex key routes through a custom provider table in
`~/.codex/config.toml` (e.g. a third-party Anthropic/OpenAI-compatible relay),
register it in `~/.omnigent/config.yaml` as `kind: cli-config` — see
`config.example.yaml` block 2. Without this, omnigent forces the built-in
`openai` provider and your key will 401.

## 4. ZCode (executor)

1. Install the ZCode desktop app and sign in (creates `~/.zcode/v2/config.json`
   and shared credentials).
2. The CLI ships inside the app bundle
   (`%LOCALAPPDATA%\Programs\ZCode\resources\glm\zcode.cjs` on Windows) — the
   bridge finds it automatically; no PATH entry needed.
3. Install the ACP bridge:

   ```bash
   npm install -g zcode-acp-server
   ```

4. Create `~/.zcode/cli/config.json` so the CLI's headless mode works —
   replace the key with one that is valid for the endpoint you choose:

   ```json
   {
     "provider": {
       "deepseek": {
         "kind": "anthropic",
         "name": "DeepSeek (anthropic-compat)",
         "options": {
           "baseURL": "https://api.deepseek.com/anthropic",
           "apiKey": "YOUR_KEY"
         },
         "models": { "deepseek-v4-flash": {} }
       }
     },
     "model": "deepseek/deepseek-v4-flash"
   }
   ```

   Any Anthropic- or OpenAI-compatible endpoint works; the desktop
   subscription endpoint (`zcode.z.ai/...`) additionally requires a
   captcha-verified desktop session and cannot be driven headlessly.

5. Register the same provider for the **bridge** in `~/.zcode/v2/config.json`
   (merge into the existing `provider` object — keep a backup of the file):

   ```json
   "deepseek": {
     "name": "DeepSeek (ACP)",
     "kind": "anthropic",
     "options": { "baseURL": "https://api.deepseek.com/anthropic", "apiKey": "YOUR_KEY" },
     "enabled": true,
     "source": "custom",
     "models": { "deepseek-v4-flash": { "name": "deepseek-v4-flash" } }
   }
   ```

   **Key order matters**: the backend resolves a session's default model
   against the *first* pushed provider, and the bridge pushes providers in
   v2-config key order. Put the executor's provider **first**.

6. To use GLM instead of DeepSeek: swap both entries to a GLM endpoint/key
   you are entitled to (e.g. `https://open.bigmodel.cn/api/anthropic`) and set
   `model` accordingly. Do not use the `zcode.z.ai/...` plan endpoint
   headlessly (captcha).

## 5. AgentForge config

1. Merge the blocks from `config.example.yaml` into `~/.omnigent/config.yaml`
   (ZCode ACP agent + optional cli-config provider). Replace `<REPO_ROOT>`.
2. `cp .env.example .env` and set `OMNIGENT_CODEX_PATH` if needed.
3. Restart any running daemon: `omnigent stop`.

## 6. Smoke tests

```bash
# A) bridge alone (ACP handshake + one real ZCode turn)
node tests/acp_smoke.mjs <workspace-dir> "Reply with exactly: ZCODE-OK"
#    on Windows, point it at the bridge explicitly if needed:
#    ZCODE_ACP_BIN="C:/.../npm-global/node_modules/zcode-acp-server/dist/index.js"

# B) through omnigent (registers as acp:zcode)
omnigent run --harness acp:zcode -p "Reply with exactly: ACP-ZCODE-OK"

# C) codex harness through omnigent
omnigent run --harness codex -p "Reply with exactly: OK"
```

## 7. Run a workflow

```bash
python scripts/run_workflow.py workflows/codex-plans-zcode-executes.yaml \
    --cwd examples/phase2-demo/workspace \
    --prompt "Fix the bug in calc.js in this workspace: the add() function currently
subtracts instead of adding. Acceptance contract: running 'node calc.js 2 3'
prints exactly 5, and 'node calc.js -1 1' prints 0."
```

Run with the Python interpreter omnigent is installed with (the `uv tool`
venv) so `import omnigent` resolves.

## macOS / Linux notes

- The ACP bridge's Node discovery relies on Unix `which`, which exists there;
  `ZCODE_NODE` is usually unnecessary.
- omnigent's native terminal harnesses and sandboxing work on macOS/Linux but
  not on Windows — AgentForge only uses SDK/ACP-style harnesses, so this does
  not matter here.
- The ZCode CLI bundle path differs (`/Applications/ZCode.app/...`).

## Troubleshooting

See the failure-mode table at the end of `docs/architecture.md` — every entry
there was observed in real runs and has a config-level fix.
