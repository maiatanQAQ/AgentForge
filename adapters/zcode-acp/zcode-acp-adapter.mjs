#!/usr/bin/env node
/**
 * zcode-acp-adapter — omnigent `acp.agents` adapter for zcode-acp-server.
 *
 * Register in ~/.omnigent/config.yaml (see config.example.yaml at the repo
 * root):
 *
 *   acp:
 *     agents:
 *       - name: ZCode
 *         command: node <REPO_ROOT>/adapters/zcode-acp/zcode-acp-adapter.mjs
 *         omnigent_mcp: false
 *
 * Why this adapter exists (both are environment issues, worked around here
 * instead of in any upstream code):
 *
 * 1. On Windows, zcode-acp-server's Node-candidate list comes up empty
 *    (`which` does not exist and the Zed-bundle paths are macOS-only), so the
 *    bridge spawns the bundled `zcode.cjs` raw and dies with EFTYPE. Setting
 *    ZCODE_NODE to a sqlite-capable Node fixes it; this adapter sets it to
 *    the interpreter running the adapter itself.
 *
 * 2. omnigent's ACP spawn environment is deny-by-default, so any required
 *    variables must be injected here rather than exported in the shell that
 *    launched omnigent.
 *
 * Model/provider configuration lives OUTSIDE this file:
 *   ~/.zcode/v2/config.json  — provider registry the bridge pushes to the
 *                              ZCode backend after session/create; the FIRST
 *                              provider entry becomes the backend's default
 *                              session model.
 *   ~/.zcode/cli/config.json — the CLI's default model reference
 *                              (`"model": "provider/model"`).
 * See docs/setup.md for both templates.
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

async function main() {
  let bridge = null;
  if (process.env.ZCODE_ACP_BRIDGE && existsSync(process.env.ZCODE_ACP_BRIDGE)) {
    bridge = process.env.ZCODE_ACP_BRIDGE;
  } else {
    const require = createRequire(import.meta.url);
    try {
      bridge = require.resolve("zcode-acp-server/dist/index.js");
    } catch {
      try {
        const { execFileSync } = await import("node:child_process");
        const root = execFileSync("npm", ["root", "-g"], { encoding: "utf8" }).trim();
        const candidate = path.join(root, "zcode-acp-server", "dist", "index.js");
        if (existsSync(candidate)) bridge = candidate;
      } catch {
        /* npm unavailable */
      }
    }
  }
  if (!bridge) {
    console.error(
      "[zcode-acp-adapter] cannot locate zcode-acp-server/dist/index.js.\n" +
        "Install it (`npm install -g zcode-acp-server`) or set ZCODE_ACP_BRIDGE\n" +
        "to its dist/index.js — see docs/setup.md.",
    );
    process.exit(1);
  }

  const env = { ...process.env, ZCODE_NODE: process.execPath };
  const child = spawn(process.execPath, [bridge], { env, stdio: "inherit" });
  for (const sig of ["SIGINT", "SIGTERM"]) {
    process.on(sig, () => child.kill(sig));
  }
  child.on("exit", (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
}

await main();
