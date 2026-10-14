import { describe, expect, it, vi } from "vitest";

const { windowListeners, channelListeners, emit, runSlot } = vi.hoisted(() => {
	const windowListeners: Record<string, (event: unknown) => void> = {};
	vi.stubGlobal("window", { addEventListener: (type: string, listener: () => void) => (windowListeners[type] = listener) });
	vi.stubGlobal("document", { documentElement: { setAttribute: () => {} } });
	return {
		windowListeners,
		channelListeners: {} as Record<string, (payload?: unknown) => unknown>,
		emit: vi.fn(),
		runSlot: vi.fn(),
	};
});
vi.mock("../../../../extension-sdk/src/shared/transport/createPortChannel", () => ({
	createPortChannel: () => ({ listen: (name: string, handler: () => unknown) => (channelListeners[name] = handler), emit }),
}));
vi.mock("../../../../extension-sdk/src/runtime/slots", () => ({ runSlot, closeSlot: vi.fn(), setActiveSlot: vi.fn() }));
vi.mock("../../../../extension-sdk/src/runtime/actions", () => ({ handleRequest: vi.fn() }));

import { listenForHandshake } from "../../../../extension-sdk/src/runtime/connect";
import { PROTOCOL_VERSION } from "../../../../extension-sdk/src/shared/types";

describe("a kept dialog or popover frame", () => {
	it("opens again after a mount fails", async () => {
		const error = vi.spyOn(console, "error").mockImplementation(() => {});
		runSlot.mockRejectedValueOnce(new Error("The slot broke"));
		listenForHandshake();
		windowListeners.message({
			// a test module has a file URL, whose origin is "null"
			origin: "null",
			data: { type: "connect", v: PROTOCOL_VERSION, slot: "dialog", entryUrl: import.meta.url, props: {} },
			ports: [{}],
		});
		await vi.waitFor(() => expect(error).toHaveBeenCalled());
		expect(emit).not.toHaveBeenCalledWith("slot.ready");

		await channelListeners["slot.open"]({ entryName: "next" });
		expect(runSlot).toHaveBeenLastCalledWith({ entryName: "next" });
		expect(emit).toHaveBeenCalledWith("slot.ready");
	});
});
