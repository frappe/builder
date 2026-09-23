import { describe, expect, it, vi } from "vitest";
import RealTimeHandler from "./realtimeHandler";

vi.mock("./socket", () => ({ createSocket: () => ({ on: vi.fn(), off: vi.fn(), emit: vi.fn() }) }));

describe("RealTimeHandler doc subscriptions", () => {
	it("subscribes once for the first of several subscribers", () => {
		const handler = new RealTimeHandler();
		const emit = vi.spyOn(handler, "emit");

		handler.doc_subscribe("Builder Page", "home");
		handler.doc_subscribe("Builder Page", "home");

		expect(emit).toHaveBeenCalledTimes(1);
		expect(emit).toHaveBeenCalledWith("doc_subscribe", "Builder Page", "home");
	});

	it("keeps the subscription open while another subscriber still holds it", () => {
		const handler = new RealTimeHandler();
		handler.doc_subscribe("Builder Page", "home");
		handler.doc_subscribe("Builder Page", "home");
		const emit = vi.spyOn(handler, "emit");

		handler.doc_unsubscribe("Builder Page", "home");

		expect(emit).not.toHaveBeenCalled();
	});

	it("drops the subscription once the last subscriber unsubscribes", () => {
		const handler = new RealTimeHandler();
		handler.doc_subscribe("Builder Page", "home");
		handler.doc_subscribe("Builder Page", "home");
		const emit = vi.spyOn(handler, "emit");

		handler.doc_unsubscribe("Builder Page", "home");
		handler.doc_unsubscribe("Builder Page", "home");

		expect(emit).toHaveBeenCalledTimes(1);
		expect(emit).toHaveBeenCalledWith("doc_unsubscribe", "Builder Page", "home");
	});

	it("ignores an unsubscribe with no matching subscriber", () => {
		const handler = new RealTimeHandler();
		const emit = vi.spyOn(handler, "emit");

		handler.doc_unsubscribe("Builder Page", "home");

		expect(emit).not.toHaveBeenCalled();
	});
});
