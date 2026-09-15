import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { bridge } from "../bridge";
import { READY_TIMEOUT_MS, isEntryFrameReady, markEntryFrameReady, waitForEntryFrame } from "../entryFrames";

const EXTENSION = "acme/icons";

describe("entry frame readiness", () => {
	beforeEach(() => vi.useFakeTimers());

	afterEach(() => {
		bridge.teardown(EXTENSION);
		vi.useRealTimers();
	});

	it("waits until the frame says it is ready", () => {
		waitForEntryFrame(EXTENSION);
		expect(isEntryFrameReady(EXTENSION)).toBe(false);

		markEntryFrameReady(EXTENSION);
		expect(isEntryFrameReady(EXTENSION)).toBe(true);
	});

	it("stops waiting for a frame that never says so", () => {
		waitForEntryFrame(EXTENSION);
		vi.advanceTimersByTime(READY_TIMEOUT_MS - 1);
		expect(isEntryFrameReady(EXTENSION)).toBe(false);

		vi.advanceTimersByTime(1);
		expect(isEntryFrameReady(EXTENSION)).toBe(true);
	});

	it("forgets a frame on teardown, and cancels its cap", () => {
		waitForEntryFrame(EXTENSION);
		markEntryFrameReady(EXTENSION);
		bridge.teardown(EXTENSION);
		expect(isEntryFrameReady(EXTENSION)).toBe(false);

		vi.advanceTimersByTime(READY_TIMEOUT_MS);
		expect(isEntryFrameReady(EXTENSION)).toBe(false);
	});

	it("waits again for a frame that connects after a failed handshake", () => {
		markEntryFrameReady(EXTENSION);
		waitForEntryFrame(EXTENSION);
		expect(isEntryFrameReady(EXTENSION)).toBe(false);
	});
});
