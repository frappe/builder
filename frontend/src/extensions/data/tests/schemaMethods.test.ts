import { beforeEach, describe, expect, it, vi } from "vitest";
import { schemaMethods } from "../schemaMethods";

const { confirmSchema, invoke } = vi.hoisted(() => ({ confirmSchema: vi.fn(), invoke: vi.fn() }));
vi.mock("../confirmations", () => ({ confirmSchema }));
vi.mock("../documentMethods", () => ({ invoke }));

const extension = {
	name: "acme/cms",
	label: "CMS",
	entryUrl: "/main.js",
	permissions: ["schema.write" as const],
};
const update = (params: unknown) => schemaMethods["schema.updateDoctype"].run(params, extension);

describe("schema field removal", () => {
	beforeEach(() => vi.resetAllMocks());

	it("keeps normal additive updates free of a removal prompt", async () => {
		await update({ doctype: "CMS Posts", fields: [{ fieldname: "body", fieldtype: "Text Editor" }] });
		expect(confirmSchema).not.toHaveBeenCalled();
		expect(invoke).toHaveBeenCalledWith(
			"builder.extensions.schema.update_doctype",
			expect.objectContaining({ remove_fields: [] }),
		);
	});

	it("confirms explicit removals before sending them to the server", async () => {
		confirmSchema.mockResolvedValue(true);
		await update({ doctype: "CMS Posts", fields: [], removeFields: ["body"] });
		expect(confirmSchema).toHaveBeenCalledWith(extension, "CMS Posts", "remove field", "body");
		expect(invoke).toHaveBeenCalledWith("builder.extensions.schema.update_doctype", {
			extension: "acme/cms",
			doctype: "CMS Posts",
			fields: [],
			remove_fields: ["body"],
		});
	});

	it("leaves the schema alone when removal is denied", async () => {
		confirmSchema.mockResolvedValue(false);
		await expect(update({ doctype: "CMS Posts", fields: [], removeFields: ["body"] })).rejects.toThrow(
			"did not allow",
		);
		expect(invoke).not.toHaveBeenCalled();
	});

	it.each(["body", [1], [""]])("rejects malformed removal names before asking", async (removeFields) => {
		await expect(update({ doctype: "CMS Posts", fields: [], removeFields })).rejects.toThrow();
		expect(confirmSchema).not.toHaveBeenCalled();
		expect(invoke).not.toHaveBeenCalled();
	});
});
