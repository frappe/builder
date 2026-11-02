const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

const pageUrl = process.argv[2];
assert(pageUrl, "Pass the published engagement page URL");
const output = process.env.BOB_EVIDENCE_DIR || "/tmp/bob-published-tokens";
const tokens = {
  "--engagement-body": "DM Sans",
  "--engagement-display": "Cormorant Infant",
  "--engagement-paper": "#F7F3EC",
  "--engagement-ink": "#3E3932",
  "--engagement-muted": "#746B60",
  "--engagement-olive": "#636A51",
};

async function verify() {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_EXECUTABLE || undefined,
    args: ["--no-sandbox"],
  });
  const evidence = {
    routes: [],
    viewports: [],
    errors: [],
    failedRequests: [],
  };
  try {
    const context = await browser.newContext({ colorScheme: "light" });
    for (const route of ["tokens.css", "variables.css"]) {
      const response = await context.request.get(
        new URL(`/builder_assets/${route}`, pageUrl).href,
      );
      const css = await response.text();
      assert.equal(response.status(), 200, route);
      assert.match(response.headers()["content-type"], /^text\/css/, route);
      assert.match(css, /^:root\s*\{/, route);
      assert(
        !css.includes("{%") && !css.includes("{{"),
        `${route} must be rendered`,
      );
      for (const name of Object.keys(tokens))
        assert(css.includes(`${name}:`), name);
      evidence.routes.push({
        route,
        status: response.status(),
        rendered: true,
      });
    }
    for (const route of ["Button/button.png", "Hero 1/hero_1.png"]) {
      const response = await context.request.get(
        new URL(`/builder_assets/${route}`, pageUrl).href,
      );
      assert.equal(response.status(), 200, route);
      assert.match(response.headers()["content-type"], /^image\/png/, route);
      evidence.routes.push({ route, status: response.status() });
    }
    const page = await context.newPage();
    page.on("pageerror", (error) => evidence.errors.push(error.message));
    page.on("requestfailed", (request) =>
      evidence.failedRequests.push(request.url()),
    );
    page.on("response", (response) => {
      if (response.status() >= 400)
        evidence.failedRequests.push(`${response.status()} ${response.url()}`);
    });
    await page.route("**/api/method/builder.ai.api.run*", (route) =>
      route.abort(),
    );
    for (const width of [1440, 768, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(pageUrl, { waitUntil: "networkidle" });
      await page.evaluate(() => document.fonts.ready);
      const computed = await page.evaluate((names) => {
        const root = getComputedStyle(document.documentElement);
        const heading = getComputedStyle(document.querySelector("h1"));
        return {
          tokens: Object.fromEntries(
            names.map((name) => [name, root.getPropertyValue(name).trim()]),
          ),
          headingFont: heading.fontFamily,
          bodyFont: getComputedStyle(document.body).fontFamily,
          ink: heading.color,
          paper: root.backgroundColor,
          overflow: document.documentElement.scrollWidth > innerWidth,
          imagesLoaded: [...document.images].every(
            (image) => image.complete && image.naturalWidth > 0,
          ),
          loadedFonts: [...document.fonts]
            .filter((font) => font.status === "loaded")
            .map((font) => font.family),
        };
      }, Object.keys(tokens));
      assert.deepEqual(computed.tokens, tokens);
      assert.match(computed.headingFont, /Cormorant Infant/);
      assert.match(computed.bodyFont, /DM Sans/);
      assert.equal(computed.ink, "rgb(62, 57, 50)");
      assert.equal(computed.paper, "rgb(247, 243, 236)");
      assert.equal(computed.overflow, false);
      assert.equal(computed.imagesLoaded, true);
      assert(computed.loadedFonts.includes("Cormorant Infant"));
      assert(computed.loadedFonts.includes("DM Sans"));
      await page.screenshot({
        path: path.join(output, `engagement-${width}.png`),
        fullPage: true,
      });
      evidence.viewports.push({ width, ...computed });
    }
    assert.deepEqual(evidence.errors, []);
    assert.deepEqual(evidence.failedRequests, []);
    fs.writeFileSync(
      path.join(output, "results.json"),
      `${JSON.stringify(evidence, null, 2)}\n`,
    );
    console.log(JSON.stringify(evidence, null, 2));
  } finally {
    await browser.close();
  }
}

verify().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
