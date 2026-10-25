"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright-core");

const baseUrl = process.env.VESICLESCOPE_BROWSER_BASE_URL || "http://127.0.0.1:8765";
const executablePath = process.env.VESICLESCOPE_BROWSER_EXECUTABLE;
const outputDirectory = process.env.VESICLESCOPE_BROWSER_ARTIFACT_DIR || "build/browser-review";
if (!executablePath) throw new Error("VESICLESCOPE_BROWSER_EXECUTABLE is required");
fs.mkdirSync(outputDirectory, { recursive: true });

const failures = [];
function check(condition, message) {
  if (!condition) failures.push(message);
}

async function exercise(browser, viewport, prefix) {
  const page = await browser.newPage({ viewport });
  const browserErrors = [];
  page.on("pageerror", error => browserErrors.push(String(error)));
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(message.text());
  });

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  check(
    (await page.locator("#serverStatus").innerText()).includes("Revision:"),
    `${prefix}: workspace did not load`,
  );

  await page.selectOption(
    "#measurementSelect",
    "synthetic-cortisol.measurements.json",
  );
  await page.selectOption(
    "#populationRunSelect",
    "synthetic-cortisol.population-run.json",
  );
  await page.locator("[data-measurement-target]").first().selectOption(
    "mean_concentration",
  );
  await page.click("#compareMeasurementModel");
  await page.waitForFunction(() =>
    document.querySelector("#measurementOverlayStatus")?.textContent.includes(
      "Showing discrete",
    ),
  );
  check(
    await page.locator("#measurementOverlayResults canvas").count() === 1,
    `${prefix}: exact-time overlay chart missing`,
  );
  check(
    (await page.locator("#measurementOverlayResults").innerText()).includes(
      "Residual (model − measured)",
    ),
    `${prefix}: residual audit missing`,
  );

  await page.click('[data-research-tab="populationView"]');
  check(
    (await page.locator("#leftTime").getAttribute("max")) === "1",
    `${prefix}: population slider does not expose stored snapshots`,
  );
  await page.locator("#leftTime").fill("0");
  await page.locator("#leftTime").dispatchEvent("input");
  check(
    (await page.locator("#leftStoredTime").innerText()).includes("0 min"),
    `${prefix}: population map did not update to stored time 0`,
  );

  await page.selectOption("#compareLeft", "synthetic-baseline-full-name.run.json");
  await page.selectOption("#compareRight", "synthetic-variant-full-name.run.json");
  await page.click("#compareRuns");
  await page.waitForFunction(
    () => getComputedStyle(document.querySelector("#comparison")).display !== "none",
  );
  check(
    (await page.locator("#compareLeftName").innerText()) ===
      "synthetic-baseline-full-name.run.json",
    `${prefix}: left full run name missing`,
  );
  check(
    (await page.locator("#compareRightName").innerText()) ===
      "synthetic-variant-full-name.run.json",
    `${prefix}: right full run name missing`,
  );
  check(
    (await page.locator("#comparisonChangedParameters").innerText()).includes(
      "Diffusion · changed",
    ),
    `${prefix}: changed parameter not highlighted`,
  );
  check(
    (await page.locator("#comparisonMapScale").innerText()).includes(
      "Stable shared scale across all stored snapshots",
    ),
    `${prefix}: stable shared scale not reported`,
  );
  await page.waitForFunction(() =>
    document.querySelector("#comparisonSpatialStatus")?.textContent.includes(
      "Positive values mean right minus left",
    ),
  );
  check(
    (await page.locator("#comparisonSpatialStatus").innerText()).includes(
      "Positive values mean right minus left",
    ),
    `${prefix}: difference sign convention missing`,
  );

  await page.check("#compareSync");
  await page.locator("#compareLeftTime").fill("1");
  await page.locator("#compareLeftTime").dispatchEvent("input");
  check(
    (await page.locator("#compareLeftStoredTime").innerText()).includes("10 min"),
    `${prefix}: left selected time did not update`,
  );
  check(
    (await page.locator("#compareRightStoredTime").innerText()).includes("10 min"),
    `${prefix}: synchronized right time did not follow the explicit rule`,
  );

  await page.click("#compareLeftPlay");
  check(
    (await page.locator("#compareLeftPlay").innerText()) === "Pause",
    `${prefix}: playback did not start`,
  );
  await page.waitForTimeout(1100);
  check(
    (await page.locator("#compareLeftStoredTime").innerText()).includes("20 min"),
    `${prefix}: playback did not advance through stored snapshots`,
  );
  await page.waitForTimeout(1000);
  check(
    (await page.locator("#compareLeftPlay").innerText()) === "Play",
    `${prefix}: playback did not stop at the final snapshot`,
  );

  check(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
    `${prefix}: horizontal viewport overflow detected`,
  );
  check(
    browserErrors.length === 0,
    `${prefix}: browser errors: ${browserErrors.join(" | ")}`,
  );
  // Element screenshots otherwise capture the desktop sticky header over the
  // section after Playwright scrolls the target into view. Keep the product
  // behavior intact while making the review artefact show only the target.
  await page.addStyleTag({ content: "header{position:static!important}" });
  await page.locator("#researchWorkspace").screenshot({
    path: path.join(outputDirectory, `${prefix}-research-workspace.png`),
  });
  await page.locator("#comparison").screenshot({
    path: path.join(outputDirectory, `${prefix}-run-comparison.png`),
  });
  await page.close();
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath });
  try {
    await exercise(browser, { width: 1440, height: 1000 }, "desktop");
    await exercise(browser, { width: 390, height: 844 }, "mobile");
  } finally {
    await browser.close();
  }
  if (failures.length) {
    throw new Error(`Browser acceptance failures:\n${failures.map(x => `- ${x}`).join("\n")}`);
  }
  console.log("Browser acceptance passed for desktop and mobile viewports.");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
