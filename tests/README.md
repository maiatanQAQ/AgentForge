# Tests

## `acp_smoke.mjs` — standalone ACP handshake smoke

Speaks ACP JSON-RPC over stdio directly against `zcode-acp-server`:
`initialize` → `session/new` → `session/prompt`, printing every streamed
update so real ZCode activity is visible.

```bash
# from this repository root
node tests/acp_smoke.mjs <workspace-dir> "Reply with exactly: ZCODE-OK"

# Windows: point at the bridge explicitly if the bare package name
# cannot be spawned (npm .cmd shims are not resolvable without a shell):
ZCODE_ACP_BIN="C:/path/to/npm-global/node_modules/zcode-acp-server/dist/index.js" \
    node tests/acp_smoke.mjs . "Reply with exactly: ZCODE-OK"
```

Pass criteria: `[prompt-result]` contains `"stopReason":"end_turn"` and the
script prints `ACP_SMOKE_OK`.

This is a manual smoke utility, not an automated CI test — it drives a real
ZCode backend and consumes real model quota.
