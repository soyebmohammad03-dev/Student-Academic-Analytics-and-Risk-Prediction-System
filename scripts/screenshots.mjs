#!/usr/bin/env node
// Capture README screenshots from the RUNNING application (real API data).
//
// Prerequisites: API on :8000 with data and models, production frontend on :3000
// (`npm run build && npm start` in frontend/), Google Chrome installed.
// Usage: node scripts/screenshots.mjs [outDir]   (default docs/assets/screenshots)
//
// Uses the Chrome DevTools Protocol over Node's built-in WebSocket; no dependencies.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const OUT = resolve(process.argv[2] ?? "docs/assets/screenshots");
const BASE = process.env.APP_URL ?? "http://localhost:3000";
const CHROME =
  process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9333;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const chrome = spawn(
  CHROME,
  [
    "--headless=new",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${join(tmpdir(), "saarps-shots")}`,
    "--hide-scrollbars",
    "--no-first-run",
    "about:blank",
  ],
  { stdio: "ignore" },
);

async function target() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch {
      /* Chrome still starting */
    }
    await sleep(200);
  }
  throw new Error("Chrome did not start");
}

const ws = new WebSocket(await target());
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  }
});
function send(method, params = {}) {
  const msgId = ++id;
  ws.send(JSON.stringify({ id: msgId, method, params }));
  return new Promise((r) => pending.set(msgId, r)).then((m) => {
    if (m.error) throw new Error(`${method}: ${m.error.message}`);
    return m.result;
  });
}
const evaluate = (expression) =>
  send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }).then(
    (r) => r.result?.value,
  );

async function waitFor(expression, timeout = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await evaluate(expression)) return;
    await sleep(250);
  }
  throw new Error(`Timed out waiting for: ${expression}`);
}

async function shot(name, { path, width = 1440, height = 900, theme = "light", prepare, ready }) {
  await send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width < 600,
  });
  await send("Emulation.setEmulatedMedia", {
    features: [{ name: "prefers-color-scheme", value: theme }],
  });
  await send("Page.navigate", { url: `${BASE}${path}` });
  await waitFor(`document.readyState === "complete"`);
  await waitFor(`!document.querySelector('[aria-busy="true"]')`);
  if (prepare) await evaluate(prepare);
  if (ready) await waitFor(ready, 30000);
  await sleep(800);
  const { data } = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(OUT, `${name}.png`), Buffer.from(data, "base64"));
  console.log(`✓ ${name}.png`);
}

mkdirSync(OUT, { recursive: true });
await send("Page.enable");
await send("Runtime.enable");
try {
  await shot("dashboard", { path: "/?cohort=math&scenario=early" });
  await shot("model-comparison", {
    path: "/model-comparison?cohort=math&scenario=early",
    prepare: `document.querySelector('h2')?.closest('section')?.nextElementSibling?.scrollIntoView(); window.scrollBy(0, -24)`,
  });
  await shot("prediction", {
    path: "/prediction?cohort=math&scenario=mid_year",
    prepare: `(async () => {
      [...document.querySelectorAll("button")].find((b) => b.textContent === "Load record").click();
      await new Promise((r) => setTimeout(r, 1500));
      document.querySelector('button[type="submit"]').click();
    })()`,
    ready: `(() => { const h = [...document.querySelectorAll("h2")].find((e) => e.textContent === "Results");
      if (!h || !document.body.innerText.includes("Students with the same values")) return false;
      h.scrollIntoView(); window.scrollBy(0, -24); return true; })()`,
  });
  await shot("interpretability", {
    path: "/interpretability?cohort=portuguese&scenario=early",
    ready: `document.body.innerText.includes("Same record, different scenarios")`,
  });
  await shot("risk-analysis", { path: "/risk-analysis?cohort=math", theme: "dark" });
  await shot("eda", { path: "/eda?cohort=portuguese", theme: "dark" });
  await shot("mobile-dashboard", { path: "/?cohort=math", width: 390, height: 844 });
} finally {
  ws.close();
  chrome.kill();
}
