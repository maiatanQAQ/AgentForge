/**
 * Standalone ACP smoke test for zcode-acp-server.
 * Speaks ACP JSON-RPC over stdio: initialize -> session/new -> session/prompt,
 * printing every notification so the real ZCode activity is visible.
 * Usage: node acp_smoke.mjs [cwd] [prompt]
 */

import { spawn } from "node:child_process";

const cwd = process.argv[2] ?? process.cwd();
const prompt = process.argv[3] ?? "Reply with exactly: ZCODE-OK";
const BIN = process.env.ZCODE_ACP_BIN ?? "zcode-acp-server";
// On Windows, .cmd shims don't resolve without shell and .js files need node.
const [spawnBin, spawnArgs] = BIN.endsWith(".js")
  ? [process.execPath, [BIN]]
  : [BIN, []];

const child = spawn(spawnBin, spawnArgs, { cwd, stdio: ["pipe", "pipe", "pipe"] });
let nextId = 0;
const pending = new Map();

child.stdout.setEncoding("utf8");
let buf = "";
child.stdout.on("data", (chunk) => {
  buf += chunk;
  let idx;
  while ((idx = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, idx).trim();
    buf = buf.slice(idx + 1);
    if (!line) continue;
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      console.log("[non-json]", line.slice(0, 200));
      continue;
    }
    if (msg.id != null && (msg.result !== undefined || msg.error !== undefined)) {
      const p = pending.get(msg.id);
      if (p) {
        pending.delete(msg.id);
        p(msg);
      }
    } else if (msg.method) {
      const u = msg.params?.update ?? {};
      const kind = u.sessionUpdate ?? "";
      let brief = kind;
      if (kind === "agent_message_chunk") brief += ": " + (u.content?.text ?? "").slice(0, 120);
      if (kind === "tool_call") brief += `: ${u.title ?? u.kind ?? ""} ${u.rawInput ? JSON.stringify(u.rawInput).slice(0, 120) : ""}`;
      if (kind === "tool_call_update") brief += `: status=${u.status ?? ""}`;
      console.log("[update]", brief);
    }
  }
});

child.stderr.setEncoding("utf8");
child.stderr.on("data", (d) => console.log("[bridge-stderr]", d.trim().slice(0, 300)));

function request(method, params, timeoutMs = 180000) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, (msg) =>
      msg.error ? reject(new Error(`${method} error: ${JSON.stringify(msg.error).slice(0, 400)}`)) : resolve(msg.result),
    );
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
    setTimeout(() => {
      if (pending.has(id)) {
        pending.delete(id);
        reject(new Error(`${method} timed out after ${timeoutMs}ms`));
      }
    }, timeoutMs);
  });
}

const init = await request("initialize", {
  protocolVersion: 1,
  clientCapabilities: { fs: { readTextFile: true, writeTextFile: true } },
});
console.log("[init]", JSON.stringify(init).slice(0, 200));

const session = await request("session/new", { cwd, mcpServers: [] });
console.log("[session]", JSON.stringify(session).slice(0, 200));

let result;
try {
  result = await request("session/prompt", {
    sessionId: session.sessionId,
    prompt: [{ type: "text", text: prompt }],
  });
} catch (e) {
  console.log("[first-prompt-failed]", String(e).slice(0, 160));
  console.log("[retrying same session — second prompt]");
  result = await request("session/prompt", {
    sessionId: session.sessionId,
    prompt: [{ type: "text", text: prompt }],
  });
}
console.log("[prompt-result]", JSON.stringify(result));
console.log("ACP_SMOKE_OK");
child.kill();
process.exit(0);
