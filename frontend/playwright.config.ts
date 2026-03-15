import { defineConfig } from "@playwright/test";

export default defineConfig({
	testDir: "./e2e",
	timeout: 30_000,
	retries: process.env.CI ? 2 : 0,
	use: {
		baseURL: "http://builder.test:8000",
		headless: !!process.env.CI,
		screenshot: "only-on-failure",
		trace: "on-first-retry",
	},
});
