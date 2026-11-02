// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { compileScript, parse } from "@vue/compiler-sfc";
import ts from "typescript";
import * as Vue from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as answers from "./cardAnswers";
import * as drafts from "./cardDraft";
import * as previews from "./cardPreview";

// Execute the real SFC handlers with its UI dependencies stubbed, without requiring
// a second Vite configuration or starting the Builder app.
const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "AIUISpec.vue"), "utf8");
const compiled = compileScript(parse(source).descriptor, { id: "card-test" });
const js = ts.transpileModule(compiled.content, {
	compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const exports: any = {};
new Function("require", "exports", js)((id: string) => {
	if (id === "vue") return Vue;
	if (id === "./cardAnswers") return answers;
	if (id === "./cardDraft") return drafts;
	if (id === "./cardPreview") return previews;
	return {};
}, exports);
let scope: Vue.EffectScope;
beforeEach(() => {
	localStorage.clear();
	scope = Vue.effectScope();
});
afterEach(() => scope.stop());

describe("card submissions", () => {
	it("keeps full photo identity in a multistep model reply and a concise display label", () => {
		const photo = {
			label: "Morning",
			description: "Sunlit bread",
			image: "https://photo/thumb",
			asset_url: "https://photo/original",
		};
		const props = {
			messageId: "card",
			interactive: true,
			ui: [
				{ kind: "choices", label: "Photo", options: [photo] },
				{ kind: "input", label: "Business" },
				{ kind: "actions", buttons: [{ label: "Build" }] },
			],
		};
		const emit = vi.fn();
		const card = scope.run(() => exports.default.setup(props, { expose: () => {}, emit }));
		card.onOptionClick(0, props.ui[0], 0, photo);
		card.inputs[1] = "Real bakery";
		card.submitCollected("Build");
		expect(emit).toHaveBeenCalledWith(
			"submit",
			expect.stringContaining("Photo: Morning: Sunlit bread\n[image: https://photo/original]"),
			"Morning · Real bakery",
			expect.objectContaining({
				cardId: "card",
				answers: expect.arrayContaining([
					expect.objectContaining({ fieldId: "field-1", value: "Real bakery" }),
				]),
			}),
		);
		expect(emit.mock.calls[0][1]).toContain("Business: Real bakery");
		expect(emit.mock.calls[0][1]).not.toContain("https://photo/thumb");
	});

	it("recovers the actual card's half-completed form after remount", () => {
		const props = {
			messageId: "card-recovery",
			interactive: true,
			ui: [
				{ kind: "input", label: "Business" },
				{ kind: "input", label: "Audience" },
			],
		};
		const first = scope.run(() => exports.default.setup(props, { expose: () => {}, emit: vi.fn() }));
		first.inputs[0] = "Real bakery";
		first.goNext();
		scope.stop();
		scope = Vue.effectScope();
		const restored = scope.run(() => exports.default.setup(props, { expose: () => {}, emit: vi.fn() }));
		expect(restored.inputs[0]).toBe("Real bakery");
		expect(restored.stepIndex.value).toBe(1);
	});
});

describe("asset picker selection", () => {
	it("emits the inventory marker for single picks without submitting the preview URL", () => {
		const option = {
			label: "Studio",
			asset_id: "magnific:42",
			image: "https://preview/42",
			asset_url: "",
			preview_only: true,
			source_url: "https://library/42",
		};
		const props = { messageId: "single", interactive: true, ui: [{ kind: "choices", options: [option] }] };
		const emit = vi.fn();
		const card = scope.run(() => exports.default.setup(props, { expose: () => {}, emit }));
		card.onOptionClick(0, props.ui[0], 0, option);
		expect(emit).toHaveBeenCalledWith(
			"submit",
			expect.stringContaining("[asset: magnific:42]"),
			"Studio",
			expect.objectContaining({ cardId: "single" }),
		);
		expect(emit.mock.calls[0][1]).not.toContain("https://preview/42");
		expect(emit.mock.calls[0][1]).toContain("https://library/42");
	});

	it("recovers multiple selected asset IDs and supplies a usable submit for a choices-only card", () => {
		const options = [
			{
				label: "Preview",
				asset_id: "magnific:42",
				asset_url: "",
				image: "https://preview/42",
				preview_only: true,
			},
			{
				label: "Free photo",
				asset_id: "unsplash:1",
				asset_url: "https://original/1",
				image: "https://thumbnail/1",
			},
		];
		const props = { messageId: "multi", interactive: true, ui: [{ kind: "choices", multi: true, options }] };
		let card = scope.run(() => exports.default.setup(props, { expose: () => {}, emit: vi.fn() }));
		options.forEach((option, index) => card.onOptionClick(0, props.ui[0], index, option));
		expect(card.needsSubmit.value).toBe(true);
		scope.stop();
		scope = Vue.effectScope();
		const emit = vi.fn();
		card = scope.run(() => exports.default.setup(props, { expose: () => {}, emit }));
		card.submitCollected("Use these");
		const reply = emit.mock.calls[0][1];
		expect(reply).toContain("[asset: magnific:42]");
		expect(reply).toContain("[asset: unsplash:1]");
		expect(reply).toContain("[image: https://original/1]");
		expect(reply).not.toContain("https://preview/42");
		expect(reply).not.toContain("https://thumbnail/1");
	});
});
