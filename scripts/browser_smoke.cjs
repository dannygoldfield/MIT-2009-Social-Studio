/* Optional full-size browser test. Requires a disposable running studio. */
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const base = process.env.STUDIO_TEST_URL || "http://127.0.0.1:8774";
const output = path.resolve(
  process.env.STUDIO_QA_OUTPUT || "data/verification/browser",
);
const audio = process.env.STUDIO_TEST_AUDIO;
const photos = JSON.parse(process.env.STUDIO_TEST_PHOTOS || "[]");
(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.STUDIO_CHROME ? { channel: "chrome" } : {}),
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1100 },
      acceptDownloads: true,
    });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(base);
    if (audio) {
      await page.getByRole("button", { name: "Start a project" }).click();
      await page
        .getByLabel("Your name", { exact: true })
        .fill("Automated browser test — not human approval");
      await page
        .getByLabel("Project name", { exact: true })
        .fill("Verification · real 2.009 material");
      await page.getByRole("button", { name: "Create project" }).click();
      await page.locator('input[data-upload="reference"]').setInputFiles(audio);
      await page
        .getByRole("button", { name: "Generate 3 + Original Mix" })
        .waitFor();
      await page.waitForFunction(
        () =>
          document.querySelector('button[data-action="generate"]')?.disabled ===
          false,
      );
    } else {
      await page
        .getByRole("button", { name: "Try the sample project" })
        .click();
      await page
        .getByRole("button", { name: "Generate 3 + Original Mix" })
        .waitFor();
    }
    const pid = await page.evaluate(() =>
      localStorage.getItem("studio-project"),
    );
    fs.writeFileSync(path.join(output, "project-id.txt"), pid);
    for (const stage of ["audio", "video", "text", "assembly"]) {
      if (stage === "video" && photos.length) {
        await page.locator('input[data-upload="photo"]').setInputFiles(photos);
        await page.waitForFunction(
          (n) => document.querySelectorAll("[data-photo]").length === n,
          photos.length,
        );
      }
      if (stage === "text") await page.locator("#keyword").fill("CONNECT");
      const generationResponse = page.waitForResponse(
        (r) => r.url().endsWith("/generate") && r.request().method() === "POST",
      );
      await page.locator('button[data-action="generate"]').click();
      const started = await generationResponse;
      assert.equal(started.status(), 202, await started.text());
      const requested = await started.json();
      const deadline = Date.now() + 600000;
      while (true) {
        const details = await (
          await page.request.get(base + "/api/projects/" + pid)
        ).json();
        const job = details.jobs.find((j) => j.id === requested.job_id);
        if (job?.status === "failed") throw new Error(job.error);
        if (job?.status === "done") break;
        if (Date.now() > deadline) throw new Error("Generation timed out");
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
      await page.waitForFunction(
        () =>
          document.querySelectorAll(
            ".candidate-grid .stars button:not(:disabled)",
          ).length === 15,
        {},
        { timeout: 10000 },
      );
      await page.screenshot({
        path: path.join(output, `${stage}.png`),
        fullPage: true,
      });
      const card = page.locator(".candidate-grid .candidate").first();
      await card.locator('[data-stars="5"]').click();
      await page
        .locator(".candidate-grid .candidate")
        .first()
        .locator("[data-select]:not(:disabled)")
        .click();
      console.log(`${stage}: generated, compared, rated, selected`);
      if (stage !== "assembly")
        await page.locator(".advance [data-stage]").click();
    }
    await page
      .locator("#explanation")
      .fill(
        "AUTOMATED VERIFICATION ONLY: checks the approval and export pathway. This is not a human creative approval.",
      );
    await page.locator("#confirm-approval").check();
    await page.locator("[data-approve]").click();
    await page.locator("[data-export]").waitFor();
    const downloadPromise = page.waitForEvent("download");
    await page.locator("[data-export]").click();
    const download = await downloadPromise;
    await download.saveAs(path.join(output, "verified-export.zip"));
    await page.reload();
    await page.locator("[data-export]").waitFor();
    assert.match(
      await page.locator("main").innerText(),
      /AUTOMATED VERIFICATION ONLY/,
    );
    await page.screenshot({
      path: path.join(output, "approved.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: path.join(output, "mobile.png"),
      fullPage: true,
    });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
      "Mobile page overflows horizontally",
    );
    assert.deepEqual(errors, [], "Browser JavaScript errors");
    const details = await (
      await page.request.get(base + "/api/projects/" + pid)
    ).json();
    fs.writeFileSync(
      path.join(output, "verification.json"),
      JSON.stringify(
        {
          project_id: pid,
          jobs: details.jobs.map((j) => ({
            status: j.status,
            seconds: j.elapsed_seconds,
          })),
          candidates: details.candidates.length,
          approvals: details.approvals.length,
          errors,
        },
        null,
        2,
      ),
    );
    console.log("approval, export, reload, mobile layout: passed");
  } catch (error) {
    const p = browser.contexts()[0]?.pages()[0];
    if (p) {
      await p.screenshot({
        path: path.join(output, "error.png"),
        fullPage: true,
      });
      console.error(
        await p.evaluate(() => ({
          pending,
          stage,
          signature: lastJobSignature,
          notice: document.querySelector("#notice").textContent,
        })),
      );
    }
    throw error;
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
