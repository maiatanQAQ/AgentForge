"""AgentForge sitecustomize — loaded into every omnigent Python subprocess.

scripts/run_workflow.py puts this directory on PYTHONPATH before spawning
omnigent, so this module is imported by the interpreter at startup, before
omnigent's server code runs.

What it does (single, documented workaround — no machine-specific values):

  Disables omnigent's background session-title worker. In omnigent 0.14.0.dev0
  that worker runs its own model thread on a hard-coded OpenAI-family fallback
  model; against any non-OpenAI provider backend the request 401s and the
  retried failure poisons the main turn (observed on Windows + a custom
  codex provider). Session titles are cosmetic; disabling it is safe.

The file must define the module-level name via the SAME import path the
server uses (`omnigent.server.background_session_titles`), because the server
does `from ... import background_session_titles_enabled` at import time —
patching the module attribute here (before that import) is therefore enough.

Everything else (codex binary path, model provider pinning, bridge paths) is
handled by .env / ~/.omnigent/config.yaml — deliberately not in code.
"""


def _disable_background_titles() -> None:
    try:
        import omnigent.server.background_session_titles as _bst

        _bst.background_session_titles_enabled = lambda headers: False
    except Exception:
        # This process does not run the omnigent server (e.g. a plain harness
        # wrap) — nothing to patch.
        pass


_disable_background_titles()
