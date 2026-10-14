import { beforeEach, describe, expect, it, vi } from "vitest";

const { call, toast, fetchInstallations } = vi.hoisted(() => ({
	call: vi.fn(),
	toast: { success: vi.fn(), error: vi.fn() },
	fetchInstallations: vi.fn(),
}));
vi.mock("frappe-ui", () => ({
	call,
	toast,
	frappeRequest: vi.fn(),
	getCachedResource: vi.fn(),
	createResource: () => ({ fetch: fetchInstallations, data: [{ name: "acme/cms", label: "CMS" }] }),
}));
vi.mock("@/extensions/devExtension", () => ({ devExtension: { value: null }, isDevExtension: () => false }));
vi.mock("@vueuse/core", () => ({ useStorage: () => ({ value: false }) }));

import { finishUpdate, updateFromHub, updatingExtensions } from "@/data/extensions";

describe("an extension update", () => {
	beforeEach(() => updatingExtensions.clear());

	it("reports its end with no details page mounted", async () => {
		await updateFromHub("acme/cms", "1.1.0", []);
		expect(updatingExtensions.has("acme/cms")).toBe(true);

		await finishUpdate({ extension: "acme/cms", error: "The download failed" });
		expect(updatingExtensions.has("acme/cms")).toBe(false);
		expect(toast.error).toHaveBeenCalledWith("CMS could not update: The download failed");
		expect(fetchInstallations).toHaveBeenCalled();
	});

	it("ends when the job ends before the start call answers", async () => {
		call.mockImplementationOnce(async () => {
			await finishUpdate({ extension: "acme/cms" });
		});
		await updateFromHub("acme/cms", "1.1.0", []);
		expect(updatingExtensions.has("acme/cms")).toBe(false);
	});

	it("ends when the start call fails", async () => {
		call.mockRejectedValueOnce(new Error('"acme/cms" is already updating.'));
		await expect(updateFromHub("acme/cms", "1.1.0", [])).rejects.toThrow("already updating");
		expect(updatingExtensions.has("acme/cms")).toBe(false);
	});
});
