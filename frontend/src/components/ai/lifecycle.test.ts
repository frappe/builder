import { describe, expect, it } from "vitest";
import { RunEvents } from "./lifecycle";

describe("durable event ordering", () => {
	it("holds gaps and delivers each stream chunk once in order", async () => {
		const events = new RunEvents();
		const delivered: number[] = [];
		const deliver = (seq: number) => {
			if (events.accept({ run_id: "run", session_id: "chat", seq, journal: true }, () => deliver(seq)))
				delivered.push(seq);
		};
		deliver(3);
		deliver(1);
		deliver(3);
		deliver(2);
		await Promise.resolve();
		deliver(2);
		expect(delivered).toEqual([1, 2, 3]);
		expect(events.cursor("run")).toBe(3);
	});

	it("discards held events after a run is retired", async () => {
		const events = new RunEvents();
		let delivered = false;
		events.accept({ run_id: "run", session_id: "chat", seq: 2, journal: true }, () => {
			delivered = true;
		});
		events.finish("run");
		expect(events.accept({ run_id: "run", session_id: "chat", seq: 1, journal: true })).toBe(false);
		await Promise.resolve();
		expect(delivered).toBe(false);
	});
});
