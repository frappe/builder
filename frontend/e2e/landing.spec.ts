import { expect, test } from "./fixtures";

test.describe("Builder Dashboard", () => {
	test("Open builder page", async ({ page, baseURL }) => {
		await page.goto(`${baseURL}/builder/home`);
		await expect(page).toHaveURL(/builder/);
	});
});
