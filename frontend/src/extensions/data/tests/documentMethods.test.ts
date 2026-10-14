import { beforeEach, describe, expect, it, vi } from "vitest";
import { documentMethods } from "../documentMethods";

const { submit, getChannels, panel, dialog, refreshEditor } = vi.hoisted(() => ({
	submit: vi.fn(),
	getChannels: vi.fn(),
	panel: { emit: vi.fn() },
	dialog: { emit: vi.fn() },
	refreshEditor: vi.fn(),
}));
vi.mock("frappe-ui", () => ({ createResource: () => ({ submit }) }));
vi.mock("../../bridge/bridge", () => ({ bridge: { getChannels } }));
vi.mock("../editorRefresh", () => ({ refreshEditor }));

const extension = {
	name: "acme/cms",
	label: "CMS",
	entryUrl: "/main.js",
	permissions: ["data.access" as const],
};

describe("document change notifications", () => {
	beforeEach(() => {
		vi.resetAllMocks();
		getChannels.mockReturnValue([panel, dialog]);
		submit.mockResolvedValue({ name: "post", title: "Saved" });
	});

	it.each(["insert", "update", "delete"])(
		"notifies every frame of the writing extension after %s",
		async (operation) => {
			await documentMethods[`data.${operation}`].run(
				{ doctype: "CMS Posts", name: "post", doc: { title: "Saved" } },
				extension,
			);
			expect(getChannels).toHaveBeenCalledWith(extension.name);
			for (const channel of [panel, dialog]) {
				expect(channel.emit).toHaveBeenCalledWith("data.changed", {
					doctype: "CMS Posts",
					name: "post",
					operation,
				});
			}
			expect(refreshEditor.mock.invocationCallOrder[0]).toBeLessThan(panel.emit.mock.invocationCallOrder[0]);
		},
	);

	it("does not notify after a refused write", async () => {
		submit.mockRejectedValue(new Error("Permission denied"));
		await expect(
			documentMethods["data.update"].run({ doctype: "CMS Posts", name: "post", doc: {} }, extension),
		).rejects.toThrow("Permission denied");
		expect(getChannels).not.toHaveBeenCalled();
	});

	it("supports another extension and any writable DocType", async () => {
		const tasks = { ...extension, name: "acme/tasks" };
		await documentMethods["data.update"].run({ doctype: "ToDo", name: "task", doc: { status: "Closed" } }, tasks);
		expect(getChannels).toHaveBeenCalledWith(tasks.name);
		expect(panel.emit).toHaveBeenCalledWith("data.changed", { doctype: "ToDo", name: "task", operation: "update" });
	});

	it("does not notify for reads", async () => {
		await documentMethods["data.getDoc"].run({ doctype: "CMS Posts", name: "post" }, extension);
		expect(getChannels).not.toHaveBeenCalled();
	});
});
