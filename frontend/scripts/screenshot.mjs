// Takes a screenshot of the running dev server and saves it under docs,
// mirroring the frontend's src path of the screenshotted view.
// Usage: node scripts/screenshot.mjs <docs-relative-path> [route] [url]
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const [relPath, route = "/", baseUrl = "http://localhost:5173"] = process.argv.slice(2);
if (!relPath) {
  console.error("Usage: node scripts/screenshot.mjs <docs-relative-path> [route] [url]");
  process.exit(1);
}

const root = dirname(fileURLToPath(import.meta.url));
const outPath = resolve(root, "../../docs", relPath);
mkdirSync(dirname(outPath), { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.goto(new URL(route, baseUrl).toString(), { waitUntil: "networkidle" });
await page.screenshot({ path: outPath, fullPage: true });
await browser.close();

console.log(`Saved ${outPath}`);
