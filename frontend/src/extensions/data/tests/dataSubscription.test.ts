import { beforeEach, describe, expect, it, vi } from "vitest";
import { data } from "../../../../extension-sdk/src/runtime/methods/data";

const { listen, stop } = vi.hoisted(() => ({ listen: vi.fn(), stop: vi.fn() }));
vi.mock("../../../../extension-sdk/src/runtime/connect", () => ({ getChannel: () => ({ listen }) }));

describe("data subscriptions", () => {
	beforeEach(() => {
		vi.resetAllMocks();
		listen.mockReturnValue(stop);
	});

	it("filters by doctype and returns the listener cleanup", () => {
		const changed = vi.fn();
		const unsubscribe = data.subscribe("CMS Posts", changed);
		expect(listen).toHaveBeenCalledWith("data.changed", expect.any(Function));
		const receive = listen.mock.calls[0][1];
		receive({ doctype: "User", name: "Administrator", operation: "update" });
		expect(changed).not.toHaveBeenCalled();
		const change = { doctype: "CMS Posts", name: "post", operation: "update" };
		receive(change);
		expect(changed).toHaveBeenCalledExactlyOnceWith(change);
		unsubscribe();
		expect(stop).toHaveBeenCalledOnce();
	});
});
