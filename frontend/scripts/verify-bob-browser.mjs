// Run with BOB_PLAYWRIGHT_MODULE set when Playwright is installed outside this checkout.
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.BOB_PLAYWRIGHT_MODULE || "playwright");
const source = new URL("../../builder/ai/browser/", import.meta.url);
const [tabs, motion, checks, interactions] = await Promise.all(
	["tabs.js", "motion.js", "checks.js", "interactions.js"].map((name) =>
		fs.readFile(new URL(name, source), "utf8"),
	),
);
const browser = await chromium.launch({
	headless: true,
	executablePath: process.env.BOB_CHROMIUM || undefined,
	args: ["--no-sandbox"],
});
const report = {
	checks: [],
	limitations: [
		"Deterministic fixtures, not generated-site aesthetic evaluation",
		"200% reflow uses equivalent CSS viewport, not browser chrome zoom",
		"No paid media calls",
	],
};
const markup = `<!doctype html><html lang="en"><title>Recipe verification</title><style>body{margin:24px;font:16px Arial;color:#222;background:white}button{min-height:44px;padding:8px 20px}button:focus-visible{outline:3px solid blue}article{min-height:150px}footer{margin-top:6800px}</style><body><h1>Local studio</h1><div data-bob-tabs><div role="tablist" aria-label="Studio"><button id="first" role="tab" aria-controls="one">About</button><button id="second" role="tab" aria-controls="two">Classes</button></div><article id="one" role="tabpanel">Real first panel</article><article id="two" role="tabpanel">Real second panel</article></div><p data-bob-reveal>Visible before JavaScript</p><details><summary>Hours</summary>Monday to Friday</details><footer>Complete footer</footer></body></html>`;
try {
	const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
	await page.setContent(markup);
	assert(await page.locator("#one").isVisible());
	assert(await page.locator("#two").isVisible());
	assert(await page.getByText("Visible before JavaScript").isVisible());
	report.checks.push({ id: "progressive-enhancement", scenarios: ["V09", "V11"], passed: true });
	await page.addScriptTag({ content: tabs });
	await page.locator("#first").focus();
	await page.keyboard.press("ArrowRight");
	assert.equal(await page.locator("#second").getAttribute("aria-selected"), "true");
	assert(!(await page.locator("#one").isVisible()));
	await page.keyboard.press("Home");
	assert.equal(await page.locator("#first").getAttribute("aria-selected"), "true");
	await page.evaluate(() => {
		document.documentElement.dir = "rtl";
	});
	await page.keyboard.press("ArrowLeft");
	assert.equal(await page.locator("#second").getAttribute("aria-selected"), "true");
	await page.evaluate(() =>
		document.querySelector('[role="tablist"]').setAttribute("aria-orientation", "vertical"),
	);
	await page.keyboard.press("ArrowUp");
	assert.equal(await page.locator("#first").getAttribute("aria-selected"), "true");
	report.checks.push({ id: "tabs-keyboard-rtl-vertical", scenarios: ["V07", "V08"], passed: true });
	await page.addScriptTag({ content: tabs });
	await page.locator("#second").click();
	assert.equal(await page.locator("#second").getAttribute("aria-selected"), "true");
	await page.evaluate(() => window.__bobTabs.dispose());
	assert(await page.locator("#one").isVisible());
	assert(await page.locator("#two").isVisible());
	assert(!(await page.evaluate(() => Boolean(window.__bobTabs))));
	report.checks.push({ id: "repeat-install-dispose", scenarios: ["V12"], passed: true });
	await page.emulateMedia({ reducedMotion: "reduce" });
	await page.addScriptTag({ content: motion });
	await page.evaluate(
		() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
	);
	assert.equal(await page.evaluate(() => document.getAnimations().length), 0);
	assert(await page.getByText("Visible before JavaScript").isVisible());
	await page.evaluate(() => window.__bobMotion.dispose());
	report.checks.push({ id: "reduced-motion-visible", scenarios: ["V09", "V10", "V12"], passed: true });
	await page.getByText("Hours", { exact: true }).click();
	assert(await page.getByText("Monday to Friday").isVisible());
	await page.locator("footer").scrollIntoViewIfNeeded();
	assert(await page.locator("footer").isVisible());
	assert((await page.evaluate(checks)).documentHeight > 6000);
	report.checks.push({ id: "tall-footer-disclosure", scenarios: ["V02", "V09"], passed: true });
	for (const width of [320, 390, 640, 768, 1280]) {
		await page.setViewportSize({ width, height: 900 });
		const result = await page.evaluate(checks);
		assert.equal(result.viewport.width, width);
		assert(!result.issues.some((issue) => issue.code === "horizontal-overflow"));
	}
	report.checks.push({ id: "responsive-reflow", scenarios: ["V03", "V08"], passed: true });
	const interact = (step) => page.evaluate(`${interactions}(${JSON.stringify(step)})`);
	assert((await interact({ action: "click", selector: "summary" })).passed);
	assert(
		(
			await interact({
				action: "assert",
				selector: "details",
				state: "attribute",
				attribute: "open",
				value: "",
			})
		).passed === false,
	);
	assert((await interact({ action: "click", selector: "summary" })).passed);
	assert(
		(
			await interact({
				action: "assert",
				selector: "details",
				state: "attribute",
				attribute: "open",
				value: "",
			})
		).passed,
	);
	assert(!(await interact({ action: "click", selector: "#missing" })).passed);
	await page.setContent('<form><input name="name"><button type="submit">Save</button></form>');
	assert((await interact({ action: "fill", selector: "input", value: "Fixture" })).passed);
	assert((await interact({ action: "assert", selector: "input", state: "value", value: "Fixture" })).passed);
	assert(!(await interact({ action: "click", selector: "button" })).passed);
	report.checks.push({ id: "declarative-interaction-assertions", scenarios: ["V09", "F01"], passed: true });
	await page.setContent(
		'<!doctype html><html><body><h1>Bad fixture</h1><button></button><input><img src="data:image/png;base64,broken"><a href="#missing">Link</a><p style="color:rgb(245,245,245);background:white">Low contrast</p></body></html>',
	);
	const broken = await page.evaluate(checks);
	for (const code of [
		"missing-language",
		"missing-title",
		"missing-label",
		"unnamed-button",
		"broken-image",
		"missing-alt",
		"missing-link-target",
		"text-contrast",
	])
		assert(
			broken.issues.some((issue) => issue.code === code),
			code,
		);
	report.checks.push({
		id: "diagnostics-detect-known-defects",
		scenarios: ["V05", "F08", "A10"],
		passed: true,
	});
	report.passed = true;
} catch (error) {
	report.passed = false;
	report.error = error.stack;
	process.exitCode = 1;
} finally {
	await browser.close();
	const output = process.argv[2] || "/tmp/bob-browser-acceptance.json";
	await fs.writeFile(output, JSON.stringify(report, null, 2));
	console.log(JSON.stringify(report, null, 2));
}
