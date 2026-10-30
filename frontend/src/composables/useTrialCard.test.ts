import type { BillingTrial } from "@frappe/cloud-sdk/api";
import { describe, expect, it, vi } from "vitest";

vi.hoisted(() => vi.stubGlobal("window", {}));
vi.mock("frappe-ui", () => ({ toast: { error: vi.fn() } }));

import { getTrialCardContent } from "./useTrialCard";

const activeTrial = (fields: Partial<BillingTrial> = {}): BillingTrial => ({
	state: "Active",
	ends_on: "2026-11-10",
	days_left: 10,
	deletes_on: "2026-11-17",
	...fields,
});

describe("trial card content", () => {
	it("counts down an active trial in gray", () => {
		const content = getTrialCardContent(activeTrial());

		expect(content).toMatchObject({ theme: "gray", title: "Your trial ends in 10 days", dismissible: true });
	});

	it("turns amber from three days left", () => {
		expect(getTrialCardContent(activeTrial({ days_left: 3 })).theme).toBe("amber");
		expect(getTrialCardContent(activeTrial({ days_left: 1 })).title).toBe("Your trial ends tomorrow");
		expect(getTrialCardContent(activeTrial({ days_left: 0 })).title).toBe("Your trial ends today");
	});

	it("asks to manage billing when the plan is over the spending limit", () => {
		const content = getTrialCardContent(activeTrial({ held: true }));

		expect(content).toMatchObject({ theme: "amber", actionLabel: "Manage billing" });
	});

	it("keeps an ended trial on screen with its deletion date", () => {
		const content = getTrialCardContent(activeTrial({ state: "Ended", days_left: 0 }));

		expect(content).toMatchObject({ theme: "red", title: "Your trial has ended", dismissible: false });
		expect(content.description).toContain("Your site will be deleted on");
	});

	it("leaves out the date when Central has not set one", () => {
		const content = getTrialCardContent(activeTrial({ state: "Ended", deletes_on: null }));

		expect(content.description).toBe("Choose a plan to keep using your site.");
	});
});
