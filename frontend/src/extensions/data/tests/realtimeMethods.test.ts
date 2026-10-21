import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * The socket and the bridge are mocked. Under test is which frames hear a
 * Frappe list update, and how often the host joins a room.
 */
const { realtime, channels, teardowns } = vi.hoisted(() => ({
	realtime: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
	channels: new Map<string, Array<{ emit: ReturnType<typeof vi.fn> }>>(),
	teardowns: new Map<string, Array<() => void>>(),
}));

vi.mock("@/stores/builderStore", () => ({ default: () => ({ realtime }) }));
vi.mock("../../bridge/bridge", () => ({
	bridge: {
		getChannels: (extension: string) => channels.get(extension) ?? [],
		registerTeardown: (extension: string, cleanup: () => void) =>
			teardowns.set(extension, [...(teardowns.get(extension) ?? []), cleanup]),
	},
}));

import { realtimeMethods } from "../realtimeMethods";

const extension = (name: string) => ({ name, label: name, entryUrl: "/main.js", permissions: [] });

const subscribe = (name: string, doctype: string) =>
	realtimeMethods["data.subscribe"].run({ doctype }, extension(name) as never);

const frame = (name: string) => {
	const channel = { emit: vi.fn() };
	channels.set(name, [channel]);
	return channel;
};

const handler = (event: string) => realtime.on.mock.calls.find(([name]) => name === event)?.[1];

const announce = (doctype: string, name: string) => handler("list_update")({ doctype, name });

const stop = (name: string) => teardowns.get(name)?.forEach((cleanup) => cleanup());

describe("data.subscribe", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		channels.clear();
		["acme/cms", "acme/crm"].forEach(stop);
		teardowns.clear();
	});

	it("joins the doctype's room once", () => {
		subscribe("acme/cms", "CMS Post");
		subscribe("acme/cms", "CMS Post");

		expect(realtime.emit).toHaveBeenCalledTimes(1);
		expect(realtime.emit).toHaveBeenCalledWith("doctype_subscribe", "CMS Post");
	});

	it("forwards an update only to the extensions that watch its doctype", () => {
		const cms = frame("acme/cms");
		const crm = frame("acme/crm");
		subscribe("acme/cms", "CMS Post");
		subscribe("acme/crm", "Lead");

		announce("CMS Post", "post-1");

		expect(cms.emit).toHaveBeenCalledWith("data.changed", {
			doctype: "CMS Post",
			name: "post-1",
			operation: "change",
		});
		expect(crm.emit).not.toHaveBeenCalled();
	});

	it("joins the watched rooms again on each new connection", () => {
		subscribe("acme/cms", "CMS Post");
		subscribe("acme/crm", "Lead");
		realtime.emit.mockClear();

		handler("connect")();

		expect(realtime.emit).toHaveBeenCalledWith("doctype_subscribe", "CMS Post");
		expect(realtime.emit).toHaveBeenCalledWith("doctype_subscribe", "Lead");
	});

	it("stops listening when the last watching extension stops", () => {
		subscribe("acme/cms", "CMS Post");

		stop("acme/cms");

		expect(realtime.off).toHaveBeenCalledWith("list_update", expect.any(Function));
		expect(realtime.off).toHaveBeenCalledWith("connect", expect.any(Function));
	});
});
