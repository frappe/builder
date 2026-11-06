import { effectScope, nextTick, reactive, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AI_STATE_POLL_INTERVAL, useAIStatePoll } from "./useAIStatePoll";

function setup(aiConfigured: boolean | null, open = true) {
	const isOpen = ref(open);
	const state = reactive({ aiConfigured, refreshAIState: vi.fn() });
	const scope = effectScope();
	scope.run(() => useAIStatePoll(() => isOpen.value, state));
	return { isOpen, state, scope };
}

describe("useAIStatePoll", () => {
	beforeEach(() => vi.useFakeTimers());
	afterEach(() => vi.useRealTimers());

	it("asks at once and then on each interval while Bob is open and AI is off", () => {
		const { state } = setup(false);
		expect(state.refreshAIState).toHaveBeenCalledTimes(1);
		vi.advanceTimersByTime(AI_STATE_POLL_INTERVAL * 2);
		expect(state.refreshAIState).toHaveBeenCalledTimes(3);
	});

	it("stops once AI is configured", async () => {
		const { state } = setup(false);
		state.aiConfigured = true;
		await nextTick();
		vi.advanceTimersByTime(AI_STATE_POLL_INTERVAL * 2);
		expect(state.refreshAIState).toHaveBeenCalledTimes(1);
	});

	it("waits while Bob is closed and asks when it opens", async () => {
		const { isOpen, state } = setup(false, false);
		vi.advanceTimersByTime(AI_STATE_POLL_INTERVAL * 2);
		expect(state.refreshAIState).not.toHaveBeenCalled();
		isOpen.value = true;
		await nextTick();
		expect(state.refreshAIState).toHaveBeenCalledTimes(1);
	});

	it("does not ask before the first answer arrives", () => {
		const { state } = setup(null);
		vi.advanceTimersByTime(AI_STATE_POLL_INTERVAL * 2);
		expect(state.refreshAIState).not.toHaveBeenCalled();
	});

	it("stops when the panel goes away", () => {
		const { state, scope } = setup(false);
		scope.stop();
		vi.advanceTimersByTime(AI_STATE_POLL_INTERVAL * 2);
		expect(state.refreshAIState).toHaveBeenCalledTimes(1);
	});
});
