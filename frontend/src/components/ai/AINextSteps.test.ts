// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { compileScript, parse } from "@vue/compiler-sfc";
import ts from "typescript";
import * as Vue from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ChatMessage } from "./types";

const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "AINextSteps.vue"), "utf8");
const compiled = compileScript(parse(source).descriptor, { id: "next-steps-test", inlineTemplate: true });
const js = ts.transpileModule(compiled.content, {
	compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const exports: any = {};
const Button = Vue.defineComponent({
	inheritAttrs: false,
	setup:
		(_, { attrs, slots }) =>
		() =>
			Vue.h("button", attrs, slots.default?.()),
});
new Function("require", "exports", js)((id: string) => (id === "vue" ? Vue : { Button }), exports);
let app: Vue.App;
let host: HTMLDivElement;
const selected = vi.fn();

function mount(metadata: Record<string, unknown>) {
	host = document.createElement("div");
	document.body.append(host);
	const message: ChatMessage = {
		id: "reply",
		role: "assistant",
		content: "A developer portfolio with contact details and images.",
		metadata: { status: "complete", ...metadata },
	};
	app = Vue.createApp(exports.default, { message, onSelect: selected });
	app.mount(host);
}
afterEach(() => {
	app.unmount();
	host.remove();
	selected.mockClear();
});

describe("model-authored next steps", () => {
	it("does not invent chips from keywords in old replies", () => {
		mount({});
		expect(host.querySelector("[role=group]")).toBeNull();
	});

	it("renders saved suggestions and emits the editable prompt on selection", async () => {
		const step = { label: "Add visit hours", prompt: "Ask me for my studio's real opening hours." };
		mount({ nextSteps: [step] });
		const button = [...host.querySelectorAll("button")].find((b) => b.textContent === step.label)!;
		button.click();
		expect(selected).toHaveBeenCalledExactlyOnceWith(step);
		host.querySelector<HTMLButtonElement>('[aria-label="Dismiss suggestions"]')!.click();
		await Vue.nextTick();
		expect(host.querySelector("[role=group]")).toBeNull();
	});

	it("ignores malformed metadata and limits the number of chips", () => {
		mount({
			nextSteps: [
				null,
				{ label: 123 },
				{ label: "Blank", prompt: " " },
				...[1, 2, 3, 4].map((i) => ({ label: `Step ${i}`, prompt: `Request ${i}` })),
			],
		});
		expect(host.querySelectorAll("button")).toHaveLength(4);
		expect(host.textContent).not.toContain("Step 4");
	});

	it("does not show suggestions for an incomplete turn", () => {
		mount({ status: "error", nextSteps: [{ label: "Continue", prompt: "Continue" }] });
		expect(host.querySelector("[role=group]")).toBeNull();
	});
});
