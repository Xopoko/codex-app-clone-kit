import { spawn } from "node:child_process";

const codex = process.env.CODEX_BIN || "/Applications/Codex.app/Contents/Resources/codex";
const codexHome = process.env.CODEX_HOME || "/Users/max/.codex-openrouter";
const cwd = process.env.PROBE_CWD || "/Users/max/Documents/Codex/doctor-neutral";

const child = spawn(codex, ["app-server", "--stdio"], {
  cwd,
  env: { ...process.env, CODEX_HOME: codexHome },
});

let buf = "";
let nextId = 1;
const pending = new Map();

child.stdout.on("data", (data) => {
  buf += data.toString("utf8");
  let idx;
  while ((idx = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, idx);
    buf = buf.slice(idx + 1);
    if (!line.trim()) continue;
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      continue;
    }
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  }
});

child.stderr.on("data", () => {});

function send(method, params) {
  return new Promise((resolve) => {
    const id = nextId++;
    pending.set(id, resolve);
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  });
}

const timeout = setTimeout(() => {
  child.kill();
  console.error("Timed out waiting for app-server.");
  process.exit(1);
}, 15000);

try {
  await send("initialize", { clientInfo: { name: "openrouter-probe", version: "1" }, capabilities: {} });
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "initialized", params: {} }) + "\n");
  const res = await send("model/list", { cursor: null, limit: 1000, includeHidden: true });
  const data = res.result?.data ?? [];
  console.log(JSON.stringify({
    returned: data.length,
    nextCursor: res.result?.nextCursor ?? null,
    first: data[0]?.model ?? null,
    last: data[data.length - 1]?.model ?? null,
  }, null, 2));
} finally {
  clearTimeout(timeout);
  child.kill();
}

