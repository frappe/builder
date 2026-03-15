import { test as base } from "@playwright/test";

export const test = base.extend({
	// Auto-login before each test
	page: async ({ page, baseURL }, use) => {
		await page.request.post(`${baseURL}/api/method/login`, {
			form: { usr: "Administrator", pwd: "admin" },
		});
		await use(page);
	},
});

export { expect } from "@playwright/test";
