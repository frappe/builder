import type Block from "@/block";
import type { BuilderToken } from "@/types/doctypes";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { reactive, ref, type Ref } from "vue";

const { canvasStore } = vi.hoisted(() => {
	vi.stubGlobal("sessionStorage", {});
	return { canvasStore: { activeCanvas: null as any } };
});

vi.mock("@/data/builderToken", () => ({
	default: reactive({ data: [] as BuilderToken[], setValue: { submit: vi.fn() } }),
}));
vi.mock("@/router", () => ({ default: {} }));
vi.mock("@/stores/builderStore", () => ({ default: () => ({}) }));
vi.mock("@/stores/pageStore", () => ({ default: () => ({}) }));
vi.mock("@/stores/canvasStore", () => ({ default: () => canvasStore }));
vi.mock("@/utils/blockController", () => ({ default: {} }));
vi.mock("@/translation", () => ({ __: (text: string) => text }));
vi.mock("frappe-ui", () => ({ toast: { error: vi.fn() } }));
vi.mock("@/utils/helpers", () => ({
	generateId: () => "pause",
	getBlockString: JSON.stringify,
	getBlockInstance: JSON.parse,
}));
vi.mock("@vueuse/core", async (importOriginal) => ({
	...(await importOriginal<typeof import("@vueuse/core")>()),
	useDark: () => ref(false),
	useToggle: () => vi.fn(),
	useStorage: (_key: string, value: unknown) => ref(value),
}));

let tokens: ReturnType<typeof import("./useBuilderToken").useBuilderToken>;
let store: typeof import("@/data/builderToken").default & { data: BuilderToken[] };
let runCommand: typeof import("@/components/Commands").runCommand;
let useCanvasHistory: typeof import("./useCanvasHistory").useCanvasHistory;
let historyTimestamp: typeof import("./historyTimestamp").historyTimestamp;
let history: ReturnType<typeof useCanvasHistory> | undefined;

const token = (name = "primary") =>
	({ name, token_name: name, value: "#000000", dark_value: "", group: "" }) as BuilderToken;

beforeEach(async () => {
	vi.resetModules();
	vi.useFakeTimers();
	vi.setSystemTime(new Date("2026-11-04T00:00:00Z"));
	store = (await import("@/data/builderToken")).default as typeof store;
	store.data = [token()];
	vi.mocked(store.setValue.submit).mockReset().mockResolvedValue(null);
	tokens = (await import("./useBuilderToken")).useBuilderToken();
	({ useCanvasHistory } = await import("./useCanvasHistory"));
	({ historyTimestamp } = await import("./historyTimestamp"));
	({ runCommand } = await import("@/components/Commands"));
	canvasStore.activeCanvas = null;
});

afterEach(async () => {
	history?.dispose();
	history = undefined;
	await vi.runAllTimersAsync();
	vi.useRealTimers();
});

function setupCanvas() {
	const source = ref({ content: "before" });
	history = useCanvasHistory(source as unknown as Ref<Block>, ref(new Set<string>()));
	canvasStore.activeCanvas = { history };
	return source;
}

function editToken(value: string, pending = false) {
	const before = { ...store.data[0] };
	const after = { ...before, value };
	const at = historyTimestamp();
	store.data = [after];
	const commit = () => {
		tokens.pendingEditFlushes.delete(commit);
		tokens.recordTokenChange([{ name: before.name, before, after }], at);
		return tokens.updateVariable(after);
	};
	if (pending) tokens.pendingEditFlushes.add(commit);
	else return commit();
}

function deferredSaves() {
	const requests: { fields: Partial<BuilderToken>; finish: () => void; fail: () => void }[] = [];
	vi.mocked(store.setValue.submit).mockImplementation(
		(fields) =>
			new Promise((resolve, reject) => {
				requests.push({
					fields,
					finish: () => {
						store.data = store.data.map((item: BuilderToken) =>
							item.name === fields.name ? { ...item, ...fields } : item,
						);
						resolve(fields);
					},
					fail: () => reject(new Error("Save failed")),
				});
			}),
	);
	return requests;
}

describe("token history persistence", () => {
	it("finishes the pending picker save before submitting undo", async () => {
		const requests = deferredSaves();
		editToken("#ffffff", true);
		runCommand("undo");
		await vi.advanceTimersByTimeAsync(0);
		expect(requests).toHaveLength(1);
		expect(requests[0].fields.value).toBe("#ffffff");
		requests[0].finish();
		await vi.advanceTimersByTimeAsync(0);
		expect(requests[1].fields.value).toBe("#000000");
		requests[1].finish();
		await vi.advanceTimersByTimeAsync(0);
		expect(store.data[0].value).toBe("#000000");
	});

	it("persists rapid undo and redo in order", async () => {
		const requests = deferredSaves();
		const save = editToken("#ffffff");
		runCommand("undo");
		runCommand("redo");
		await vi.advanceTimersByTimeAsync(0);
		for (let i = 0; i < 3; i++) {
			expect(requests).toHaveLength(i + 1);
			requests[i].finish();
			await vi.advanceTimersByTimeAsync(0);
		}
		await save;
		expect(requests.map(({ fields }) => fields.value)).toEqual(["#ffffff", "#000000", "#ffffff"]);
		expect(store.data[0].value).toBe("#ffffff");
	});

	it("queues the whole group edit before its undo", async () => {
		store.data = [token("a"), token("b")];
		const requests = deferredSaves();
		const changes = store.data.map((before: BuilderToken) => ({
			name: before.name,
			before,
			after: { ...before, group: "Brand" },
		}));
		tokens.recordTokenChange(changes);
		const saves = Promise.all(changes.map(({ after }) => tokens.updateVariable(after)));
		runCommand("undo");
		await vi.advanceTimersByTimeAsync(0);
		for (let i = 0; i < 4; i++) {
			expect(requests).toHaveLength(i + 1);
			requests[i].finish();
			await vi.advanceTimersByTimeAsync(0);
		}
		await saves;
		expect(requests.map(({ fields }) => [fields.name, fields.group])).toEqual([
			["a", "Brand"],
			["b", "Brand"],
			["a", ""],
			["b", ""],
		]);
		expect(store.data.map((item: BuilderToken) => item.group)).toEqual(["", ""]);
	});

	it("continues with undo after an earlier save fails", async () => {
		const requests = deferredSaves();
		const save = editToken("#ffffff");
		const failure = expect(save).rejects.toThrow("Save failed");
		runCommand("undo");
		await vi.advanceTimersByTimeAsync(0);
		requests[0].fail();
		await failure;
		await vi.advanceTimersByTimeAsync(0);
		expect(requests[1].fields.value).toBe("#000000");
		requests[1].finish();
		await vi.advanceTimersByTimeAsync(0);
		expect(store.data[0].value).toBe("#000000");
	});
});

describe("combined token and canvas history", () => {
	it("flushes a later canvas edit before choosing undo", async () => {
		const source = setupCanvas();
		await editToken("#ffffff");
		source.value.content = "after";
		runCommand("undo");
		await vi.advanceTimersByTimeAsync(101);
		expect(source.value.content).toBe("before");
		expect(store.data[0].value).toBe("#ffffff");
		runCommand("redo");
		expect(source.value.content).toBe("after");
	});

	it("keeps the original edit order when the token save is still pending", () => {
		const source = setupCanvas();
		editToken("#ffffff", true);
		history!.batch(() => {
			source.value.content = "after";
		});
		runCommand("undo");
		expect(source.value.content).toBe("before");
		expect(store.data[0].value).toBe("#ffffff");
	});

	it("preserves token redo when an earlier canvas edit was still pending", async () => {
		const source = setupCanvas();
		source.value.content = "after";
		await editToken("#ffffff");
		runCommand("undo");
		await vi.advanceTimersByTimeAsync(101);
		expect(source.value.content).toBe("after");
		expect(store.data[0].value).toBe("#000000");
		expect(tokens.lastTokenRedoAt()).toBeGreaterThan(0);
		runCommand("redo");
		expect(store.data[0].value).toBe("#ffffff");
	});

	it("undoes and redoes interleaved edits even in the same millisecond", () => {
		const source = setupCanvas();
		editToken("#ffffff");
		history!.batch(() => {
			source.value.content = "after";
		});
		runCommand("undo");
		runCommand("undo");
		expect([source.value.content, store.data[0].value]).toEqual(["before", "#000000"]);
		runCommand("redo");
		expect([source.value.content, store.data[0].value]).toEqual(["before", "#ffffff"]);
		runCommand("redo");
		expect([source.value.content, store.data[0].value]).toEqual(["after", "#ffffff"]);
	});

	it("does not record a preview when history is disabled", () => {
		const source = setupCanvas();
		history!.disable();
		source.value.content = "preview";
		runCommand("undo");
		expect(source.value.content).toBe("preview");
		expect(history!.undoStack.value).toHaveLength(0);
	});
});
