import { ref } from "vue";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/utils/helpers", () => ({
	generateId: () => Math.random().toString(36).slice(2),
	getBlockString: (block: any) => JSON.stringify(block),
	getBlockInstance: (value: string) => JSON.parse(value),
}));

const { useCanvasHistory } = await import("./useCanvasHistory");

function setup(initial = { text: "a" }) {
	const source = ref(initial) as any;
	const selectedBlockIds = ref(new Set<string>());
	const history = useCanvasHistory(source, selectedBlockIds);
	return { source, selectedBlockIds, history };
}

async function flush() {
	await new Promise((resolve) => setTimeout(resolve, 150));
}

describe("useCanvasHistory", () => {
	it("commits a debounced change and undoes it", async () => {
		const { source, history } = setup({ text: "a" });
		source.value = { text: "b" };
		await flush();

		expect(history.canUndo()).toBe(true);
		history.undo();
		expect(source.value).toEqual({ text: "a" });
		expect(history.canRedo()).toBe(true);

		history.redo();
		expect(source.value).toEqual({ text: "b" });
	});

	it("drops the redo stack once a new change is committed", async () => {
		const { source, history } = setup({ text: "a" });
		source.value = { text: "b" };
		await flush();
		history.undo();
		expect(history.canRedo()).toBe(true);

		source.value = { text: "c" };
		await flush();
		expect(history.canRedo()).toBe(false);
	});

	it("ignores changes made through setSource itself", async () => {
		const { source, history } = setup({ text: "a" });
		source.value = { text: "b" };
		await flush();
		history.undo();
		await flush();
		expect(history.canUndo()).toBe(false);
	});

	it("does nothing when disabled", async () => {
		const { source, history } = setup({ text: "a" });
		history.disable();
		source.value = { text: "b" };
		await flush();
		expect(history.canUndo()).toBe(false);

		history.enable();
		source.value = { text: "c" };
		await flush();
		expect(history.canUndo()).toBe(true);
	});

	it("does not record changes made while paused", async () => {
		const { source, history } = setup({ text: "a" });
		const pauseId = history.pause();
		source.value = { text: "b" };
		await flush();
		expect(history.canUndo()).toBe(false);

		history.resume(pauseId, true);
		expect(history.canUndo()).toBe(true);
	});

	it("keeps tracking paused until every nested pause is resumed", async () => {
		const { source, history } = setup({ text: "a" });
		const outer = history.pause();
		const inner = history.pause();
		source.value = { text: "b" };
		await flush();

		history.resume(inner, true);
		expect(history.canUndo()).toBe(false);

		history.resume(outer, true);
		expect(history.canUndo()).toBe(true);
	});

	it("batch commits the change even if the callback throws", () => {
		const { source, history } = setup({ text: "a" });
		expect(() =>
			history.batch(() => {
				source.value = { text: "b" };
				throw new Error("boom");
			}),
		).toThrow("boom");

		expect(history.canUndo()).toBe(true);
		history.undo();
		expect(source.value).toEqual({ text: "a" });
	});

	it("clears both stacks on dispose", async () => {
		const { source, history } = setup({ text: "a" });
		source.value = { text: "b" };
		await flush();
		history.undo();
		expect(history.canRedo()).toBe(true);

		history.dispose();
		expect(history.canUndo()).toBe(false);
		expect(history.canRedo()).toBe(false);
	});
});
