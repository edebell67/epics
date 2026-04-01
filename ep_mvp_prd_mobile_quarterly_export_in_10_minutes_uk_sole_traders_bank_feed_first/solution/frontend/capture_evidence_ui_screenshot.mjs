import { spawn } from "node:child_process";
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import http from "node:http";

const chromePath = process.argv[2];
const url = process.argv[3];
const outputPath = process.argv[4];

if (!chromePath || !url || !outputPath) {
  console.error("usage: node capture_evidence_ui_screenshot.mjs <chromePath> <url> <outputPath>");
  process.exit(1);
}

const debugPort = 9333;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function httpGetJson(targetUrl) {
  return new Promise((resolve, reject) => {
    http.get(targetUrl, (response) => {
      let body = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => {
        body += chunk;
      });
      response.on("end", () => {
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(error);
        }
      });
    }).on("error", reject);
  });
}

async function waitForDebugger() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      return await httpGetJson(`http://127.0.0.1:${debugPort}/json/version`);
    } catch {
      await sleep(250);
    }
  }
  throw new Error("chrome_debugger_not_ready");
}

async function captureScreenshot(browserWsUrl) {
  const socket = new WebSocket(browserWsUrl);
  let id = 0;
  const pending = new Map();

  function send(method, params = {}, sessionId) {
    id += 1;
    const messageId = id;
    const payload = { id: messageId, method, params };
    if (sessionId) {
      payload.sessionId = sessionId;
    }
    socket.send(JSON.stringify(payload));
    return new Promise((resolve, reject) => {
      pending.set(messageId, { resolve, reject });
    });
  }

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) {
        reject(new Error(message.error.message || "cdp_error"));
      } else {
        resolve(message.result);
      }
    }
  });

  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });

  const { targetId } = await send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });

  await send("Page.enable", {}, sessionId);
  await send("Emulation.setDeviceMetricsOverride", {
    width: 390,
    height: 844,
    deviceScaleFactor: 3,
    mobile: true,
    screenWidth: 390,
    screenHeight: 844
  }, sessionId);
  await send("Runtime.enable", {}, sessionId);
  await send("Page.navigate", { url }, sessionId);
  await sleep(3500);
  const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true }, sessionId);

  socket.close();
  return screenshot.data;
}

async function main() {
  const userDataDir = await mkdtemp(join(tmpdir(), "evidence-ui-chrome-"));
  await mkdir(join(userDataDir, "Default"), { recursive: true });

  const chrome = spawn(chromePath, [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--no-first-run",
    "--no-default-browser-check",
    `--user-data-dir=${userDataDir}`,
    `--remote-debugging-port=${debugPort}`,
    "about:blank"
  ], {
    stdio: "ignore"
  });

  try {
    const version = await waitForDebugger();
    const base64 = await captureScreenshot(version.webSocketDebuggerUrl);
    await writeFile(outputPath, Buffer.from(base64, "base64"));
    console.log(`SCREENSHOT_WRITTEN=${outputPath}`);
  } finally {
    chrome.kill("SIGTERM");
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
