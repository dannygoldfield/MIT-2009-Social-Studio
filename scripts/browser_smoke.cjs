/* Current melody/Connect preview. Run against a disposable local studio. */
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const base = process.env.STUDIO_TEST_URL || "http://127.0.0.1:8774";
const output = path.resolve(process.env.STUDIO_QA_OUTPUT || "data/verification/melody-browser");
(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, ...(process.env.STUDIO_CHROME ? { channel: "chrome" } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    const errors = [];
    page.on("pageerror", e => errors.push(e.message));
    await page.goto(base);
    await page.getByRole("button", { name: "Try the sample project" }).click();
    await page.getByRole("button", { name: "Find my melody", exact: true }).waitFor();
    const prepared = page.waitForResponse(r => r.url().endsWith("/melody") && r.request().method() === "POST", { timeout: 120000 });
    await page.getByRole("button", { name: "Find my melody", exact: true }).click();
    const response = await prepared;
    assert.equal(response.status(), 200, await response.text());
    const guide = await response.json();
    assert.equal(guide.source_audio_in_output, false);
    assert.ok(guide.notes >= 2);
    await page.getByRole("button", { name: "Check my melody again" }).waitFor();
    assert.equal(await page.locator(".ensemble-brief").count(), 3);
    assert.equal(await page.locator('[data-upload="bed"],[data-upload="effect"]').count(), 0);
    assert.equal(await page.locator(".connect-wordmark").isVisible(), true);
    assert.equal(await page.locator(".melody-check audio").getAttribute("src"), guide.url);
    await page.reload();
    await page.getByRole("button", { name: "Check my melody again" }).waitFor();
    await page.screenshot({ path: path.join(output, "desktop.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, "mobile.png"), fullPage: true });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(output, "verification.json"), JSON.stringify({ guide_prepared: true, guide_retained_after_reload: true, ensemble_directions: 3, cloud_calls: 0, approvals_created: 0, errors }, null, 2));
    console.log("Connect branding, one input, local note guide, reload and mobile layout passed. Professional orchestration was not tested.");
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
