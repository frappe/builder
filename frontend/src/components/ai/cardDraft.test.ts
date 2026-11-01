import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref, type EffectScope, type Ref } from "vue";
import { optionReply, useCardDraft } from "./cardDraft";

let scopes: EffectScope[];
function draft(id: Ref<string>) {
	const scope = effectScope();
	scopes.push(scope);
	return scope.run(() => useCardDraft(() => id.value))!;
}
beforeEach(() => {
	const values = new Map<string, string>();
	vi.stubGlobal("localStorage", {
		getItem: (key: string) => values.get(key) ?? null,
		setItem: (key: string, value: string) => values.set(key, value),
	});
	scopes = [];
});
afterEach(() => {
	scopes.forEach((scope) => scope.stop());
	vi.unstubAllGlobals();
});

describe("photo replies", () => {
	it("includes the original full asset and its provenance", () => {
		const reply = optionReply({
			label: "Bread",
			description: "Warm morning light",
			image: "https://images/thumb.jpg",
			asset_url: "https://images/full.jpg",
			asset_id: "asset-1",
			credit: "Photographer",
			source_url: "https://source",
			license_url: "https://license",
		});
		expect(reply).toContain("Bread: Warm morning light");
		expect(reply).toContain("[image: https://images/full.jpg]");
		expect(reply).toContain("asset: asset-1");
		expect(reply).toContain("credit: Photographer");
		expect(reply).toContain("source: https://source");
		expect(reply).toContain("license: https://license");
		expect(reply).not.toContain("thumb.jpg");
	});
	it("retains legacy image choices", () => {
		expect(optionReply({ label: "Photo", image: "/files/photo.jpg" })).toBe(
			"Photo\n[image: /files/photo.jpg]",
		);
	});
});

describe("card draft recovery", () => {
	it("restores the step, selected options, uploads, input and explicit colors", () => {
		const id = ref("message-A");
		const first = draft(id);
		first.stepIndex.value = 2;
		first.selections[1] = new Set([0, 2]);
		first.inputs[3] = "Real bakery";
		first.uploads[4] = "/private/files/logo.png";
		first.colorSlots[5] = { 0: "#c4552d" };
		first.touchedColorSlots.add("5:0");
		scopes[0].stop();
		const restored = draft(id);
		expect(restored.stepIndex.value).toBe(2);
		expect([...restored.selections[1]]).toEqual([0, 2]);
		expect(restored.inputs[3]).toBe("Real bakery");
		expect(restored.uploads[4]).toBe("/private/files/logo.png");
		expect(restored.colorSlots[5][0]).toBe("#c4552d");
		expect(restored.touchedColorSlots.has("5:0")).toBe(true);
	});
	it("keeps drafts isolated when the same component displays another message", () => {
		const id = ref("A");
		const state = draft(id);
		state.inputs[0] = "A's answer";
		id.value = "B";
		expect(state.inputs[0]).toBeUndefined();
		state.inputs[0] = "B's answer";
		id.value = "A";
		expect(state.inputs[0]).toBe("A's answer");
	});
	it("keeps answering available if browser storage is disabled", () => {
		vi.stubGlobal("localStorage", {
			getItem: () => {
				throw new Error("blocked");
			},
			setItem: () => {
				throw new Error("blocked");
			},
		});
		const state = draft(ref("A"));
		expect(() => {
			state.inputs[0] = "Still works";
		}).not.toThrow();
		expect(state.inputs[0]).toBe("Still works");
	});
});

describe("preview-only selection contract", () => {
	it("passes the stable ID and library source without treating a preview as a page asset", () => {
		const reply = optionReply({
			label: "Studio",
			asset_id: "magnific:42",
			asset_url: "",
			image: "https://preview/thumb.jpg",
			source_url: "https://library/42",
			preview_only: true,
		});
		expect(reply).toContain("[asset: magnific:42]");
		expect(reply).toContain("[preview only; license/download and upload original]");
		expect(reply).toContain("https://library/42");
		expect(reply).not.toContain("https://preview/thumb.jpg");
		expect(reply).not.toContain("[image:");
	});
	it("does not fall back to a thumbnail when the original asset URL is explicitly empty", () => {
		expect(
			optionReply({ label: "Preview", asset_id: "magnific:1", asset_url: "", image: "https://preview/1" }),
		).not.toContain("https://preview/1");
	});
});
